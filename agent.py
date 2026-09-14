"""뉴스레터 에이전트 — 수집 · 선별 · 취재 · 검수 · 발행

설계 규칙 (교안 2강)
  · 빈 노드 다섯 개로 뼈대를 먼저 세우고 한 섹션에 하나씩 채운다
  · 노드는 자기가 바꾼 키만 돌려준다 (부분 업데이트)
  · 리듀서는 '합쳐야 하는 키'에만 붙인다 — drafted(팬아웃), log(전 노드)
    collected·picked·verified 는 한 노드가 쓰고 다음이 읽으므로 덮어쓰기
  · build() 는 노드를 globals() 에서 이름으로 찾는다 → 같은 이름으로 재정의하면 갈아 끼워진다
"""
from __future__ import annotations

import operator
from typing import Annotated, Any
from typing_extensions import TypedDict

import feedparser, requests
from datetime import datetime, timezone, timedelta

from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

import json
import os
import re
from pathlib import Path

import trafilatura

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from sources import SOURCES, UA, PER_SOURCE_CAP

MODEL = "gpt-4.1-mini"
CHUNK = 20          # 예선 묶음 크기 — 모델이 한 화면에서 흘리지 않고 볼 수 있는 크기
SEMI_KEEP = 8       # 묶음당 예선 통과 수 (본선 5건보다 넉넉히 → '묶음 운' 완화)
TIER1_CAP = 3       # 1차 소스 자동 통과 상한 (면제만으로 자리가 다 차지 않게)
FINAL_N = 5
OUTLET_CAP = 2       # 한 매체가 최종 발행에서 차지할 수 있는 최대 건수
BRAND = os.getenv("NEWSLETTER_BRAND", "소울라이즈 AI 브리핑")   # 디스코드에 뜨는 발행자 이름


# ── 기사 한 건의 그릇 (교안 2강) ─────────────────────────────
#   수집이 채우는 칸 : title · url · source · at · summary · tier
#   취재가 붙이는 칸 : headline · summary · why · topic
#   ※ body(본문)는 State 에 올리지 않는다 — 발행에 쓰지 않고 한도만 먹는다


class NewsState(TypedDict):
    hours: int                                    # 수집 시간 창 (설정값)
    collected: list[dict[str, Any]]               # ① 수집 결과      (덮어쓰기)
    picked: list[dict[str, Any]]                  # ② 선별 통과      (덮어쓰기)
    drafted: Annotated[list[dict[str, Any]], operator.add]   # ③ 취재 (팬아웃 → 합침)
    verified: list[dict[str, Any]]                # ④ 검수 통과      (덮어쓰기)
    log: Annotated[list[str], operator.add]       # 모든 노드가 한 줄씩 (합침)


# ── 빈 노드 다섯 개 ──────────────────────────────────────────
def collect(state: NewsState):
    """소스를 돌며 시간 창 안의 글을 모으고 중복을 거른다. 한 곳이 죽어도 나머지는 모은다."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=state["hours"])
    seen: set[str] = set()
    items: list[dict] = []
    total = in_window = dup = 0
    dead: list[str] = []
    per_source: dict[str, int] = {}

    for name, url, tier in SOURCES:
        try:
            r = requests.get(url, headers=UA, timeout=15)
            feed = feedparser.parse(r.content)
            if not feed.entries:
                dead.append(f"{name}(빈 피드)")
                continue
            for e in feed.entries:
                total += 1
                t = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
                at = datetime(*t[:6], tzinfo=timezone.utc) if t else None
                if not at or at < cutoff:          # 시간 창 · 날짜 없는 항목도 여기서 버림
                    continue
                in_window += 1
                link = getattr(e, "link", "")
                if not link:
                    continue
                key = link.split("?")[0]           # utm 꼬리표를 떼고 비교
                if key in seen:
                    dup += 1
                    continue
                if per_source.get(name, 0) >= PER_SOURCE_CAP:
                    continue                       # 소스별 상한
                seen.add(key)
                per_source[name] = per_source.get(name, 0) + 1
                items.append({
                    "title": getattr(e, "title", "").strip(),
                    "url": link,
                    "source": name,
                    "tier": tier,
                    "at": at.isoformat(),
                    "summary": getattr(e, "summary", "")[:600],
                })
        except Exception as err:                    # 소스 하나의 실패를 격리한다
            dead.append(f"{name}({type(err).__name__})")

    log = [f"① 수집 전체 {total} → 창({state['hours']}h) {in_window} "
           f"→ 중복 -{dup} → 소스상한 적용 → 후보 {len(items)}건"]
    if dead:                                        # 조용한 실패를 막는 한 줄
        log.append(f"   ⚠️ 죽은 소스: {', '.join(dead)}")
    return {"collected": items, "log": log}


# ── 구조화 출력 스키마 (7강) — 필드 설명이 곧 지시가 된다
class Pick(BaseModel):
    index: int = Field(description="후보 목록에서의 번호")
    event: str = Field(description="이 기사가 다루는 사건의 짧은 라벨. 같은 사건이면 반드시 같은 라벨")
    reason: str = Field(description="고른 이유 한 줄")


class Shortlist(BaseModel):
    picks: list[Pick]


class Dropped(BaseModel):
    title: str = Field(description="탈락시킨 기사의 제목 앞부분")
    reason: str = Field(description="탈락 이유 한 줄 (중복·중요도 낮음·홍보성 등)")


class Final(BaseModel):
    picks: list[Pick]
    dropped: list[Dropped] = Field(default_factory=list, description="아깝게 탈락시킨 기사 최대 3건")


def _llm():
    return ChatOpenAI(model=MODEL, temperature=0)


def _rank(cands: list[dict], keep: int, schema, 지시: str):
    """후보를 한 화면에 놓고 상대평가시킨다."""
    목록 = "\n".join(f"{i}. [{c['source']}] {c['title']}" for i, c in enumerate(cands))
    prompt = (
        "당신은 국내 개발팀을 위한 AI 뉴스레터 편집자입니다.\n"
        f"{지시}\n"
        "반드시 AI·머신러닝·개발도구·반도체 등 기술 주제의 기사만 고르세요.\n"
        "정치·국제정세·사건사고·주가·인사 기사는 기술과 직접 관련이 없으면 제외하세요.\n"
        "같은 사건을 다룬 기사는 하나만 고르고, event 라벨을 같게 붙이세요.\n"
        "홍보·채용공고·행사안내는 고르지 마세요.\n\n"
        f"후보:\n{목록}"
    )
    return _llm().with_structured_output(schema).invoke(prompt)


def select(state: NewsState):
    """예선(묶음별) → 본선(한 화면). 1차 소스는 경쟁 면제하되 상한을 둔다."""
    cands = state["collected"]
    if not cands:
        return {"picked": [], "log": ["② 선별 0 → 0건 (후보 없음)"]}

    log = []
    # ── 1차 소스 자동 통과 (경쟁 면제 · 검사 면제 아님)
    tier1 = [c for c in cands if c["tier"] == 1][:TIER1_CAP]
    rest = [c for c in cands if c not in tier1]

    # ── 예선: 묶음으로 쪼개 각각 SEMI_KEEP 건
    semi: list[dict] = []
    for i in range(0, len(rest), CHUNK):
        chunk = rest[i:i + CHUNK]
        try:
            out = _rank(chunk, SEMI_KEEP,
                        Shortlist, f"이 중 중요한 {SEMI_KEEP}건을 고르세요.")
            got = [chunk[p.index] | {"event": p.event} for p in out.picks
                   if 0 <= p.index < len(chunk)][:SEMI_KEEP]
            semi += got
            log.append(f"   예선 묶음 {len(chunk)}건 → {len(got)}건")
        except Exception as e:
            log.append(f"   ⚠️ 예선 묶음 실패({type(e).__name__}) — {len(chunk)}건 탈락")

    pool = tier1 + semi
    log.insert(0, f"② 예선 통과 {len(pool)}건 (1차 소스 자동통과 {len(tier1)}건 포함)")

    # ── 본선: 한 화면에서 최종 선별
    try:
        out = _rank(pool, FINAL_N, Final, f"이 중 오늘 발행할 상위 {FINAL_N}건을 고르세요.")
        picks = []
        used_events: set[str] = set()
        outlet_n: dict[str, int] = {}
        for p in out.picks:
            if not (0 <= p.index < len(pool)):
                continue
            c = pool[p.index]
            if p.event in used_events:        # 프롬프트 부탁을 코드로 한 번 더 강제
                log.append(f"   − 같은 사건 중복 제외: {c['title'][:36]}")
                continue
            if outlet_n.get(c["source"], 0) >= OUTLET_CAP:
                log.append(f"   − 매체 상한({OUTLET_CAP}) 제외: [{c['source']}] {c['title'][:30]}")
                continue
            outlet_n[c["source"]] = outlet_n.get(c["source"], 0) + 1
            used_events.add(p.event)
            picks.append(pool[p.index] | {"event": p.event, "why_picked": p.reason})
            if len(picks) == FINAL_N:
                break
        for d in out.dropped[:3]:
            log.append(f"   − 탈락: {d.title[:36]} — {d.reason}")
    except Exception as e:
        picks = pool[:FINAL_N]
        log.append(f"   ⚠️ 본선 실패({type(e).__name__}) — 예선 순서대로 {len(picks)}건")

    log.append(f"② 본선 → {len(picks)}건")
    return {"picked": picks, "log": log}


MIN_BODY = 600      # G1 관문 기준선 — 이보다 짧으면 요약을 지어내게 된다


class Draft(BaseModel):
    headline: str = Field(description="한국어 헤드라인 한 줄. 40자 이내")
    summary: str = Field(description="한국어 세 문장 요약. '~합니다'체. 원문에 있는 내용만")
    why: str = Field(description="국내 개발팀에게 왜 중요한가 한 문장. 요약에 있는 내용만 근거로")
    topic: Literal["모델", "도구", "산업", "정책", "연구"] = Field(
        description="다섯 중 하나만. 다른 값은 허용되지 않는다")


def fetch_body(url: str) -> str:
    """원문 주소로 한 번 더 가서 본문을 뽑는다 (4강 G1)."""
    try:
        html = requests.get(url, headers=UA, timeout=20).text
        return trafilatura.extract(html) or ""
    except Exception:
        return ""


def draft_one(state: dict):
    """워커 — 기사 하나만 안다. 전체 상황을 모른다."""
    item = state["item"]
    body = fetch_body(item["url"])
    if len(body) < MIN_BODY:
        return {"drafted": [], "log": [f"   − 본문 부족({len(body)}자) 제외: {item['title'][:40]}"]}
    try:
        out = _llm().with_structured_output(Draft).invoke(
            "당신은 국내 개발팀을 위한 AI 뉴스레터 기자입니다.\n"
            "아래 원문만을 근거로 쓰세요. 원문에 없는 사실을 덧붙이지 마세요.\n"
            "반드시 한국어로 쓰세요.\n\n"
            f"제목: {item['title']}\n원문:\n{body[:6000]}"
        )
    except Exception as e:
        return {"drafted": [], "log": [f"   − 취재 실패({type(e).__name__}): {item['title'][:40]}"]}

    # 프롬프트는 요청이지 보장이 아니다 — 한국어 여부는 코드로 센다 (8강)
    if not re.search(r"[가-힣]", out.summary):
        try:
            out = _llm().with_structured_output(Draft).invoke(
                "반드시 한국어로 다시 쓰세요. 영어로 쓰면 안 됩니다.\n\n"
                f"제목: {item['title']}\n원문:\n{body[:6000]}")
        except Exception:
            pass

    return {"drafted": [item | {"headline": out.headline, "summary": out.summary,
                                "why": out.why, "topic": out.topic, "body": body}],
            "log": []}


def fan_out(state: NewsState):
    """조건부 엣지가 노드 이름 대신 Send 리스트를 돌려주면 그 개수만큼 워커가 뜬다."""
    if not state["picked"]:
        return "verify"
    return [Send("draft_one", {"item": it}) for it in state["picked"]]


def draft(state: NewsState):
    """팬아웃 결과를 받아 건수만 로그에 남기는 합류 지점."""
    return {"log": [f"③ 취재 {len(state['drafted'])}건"]}


class Verdict(BaseModel):
    ok: bool = Field(description="요약의 각 주장이 원문에서 뒷받침되면 true")
    problems: list[str] = Field(default_factory=list, description="원문에 근거가 없는 대목")


def verify(state: NewsState):
    """요약이 원문을 벗어났는지 LLM 으로 대조한다.

    · 대조 대상은 headline·summary 뿐 — why 는 독자 관점의 해석이라 원문에 근거가 없다(8강)
    · 문자열 숫자 대조는 쓰지 않는다 — three months→3개월, $60M→6000만 을 오탐한다(9강)
    · 불합격은 버리고 로그에 남긴다. 다시 쓰지 않는다 — 통과한 만큼만 발행한다
    · drafted 에는 리듀서가 붙어 있어 줄이는 일을 못 한다 → verified 라는 새 키에 담는다
    """
    drafts = state["drafted"]
    if not drafts:
        return {"verified": [], "log": ["④ 검수 0건 (취재 결과 없음)"]}

    passed, log = [], []
    for d in drafts:
        try:
            v = _llm().with_structured_output(Verdict).invoke(
                "아래 요약의 각 주장이 원문에서 뒷받침되는지 판정하세요.\n"
                "번역이나 단위 환산(예: three months→3개월, $60 million→6000만 달러)은 문제가 아닙니다.\n"
                "원문에 없는 사실·숫자·과장 표현만 문제로 지적하세요.\n\n"
                f"[헤드라인] {d['headline']}\n[요약] {d['summary']}\n\n[원문]\n{d['body'][:6000]}"
            )
        except Exception as e:
            log.append(f"   − 검수 실패({type(e).__name__}) 제외: {d['headline'][:36]}")
            continue
        if v.ok:
            passed.append({k: val for k, val in d.items() if k != "body"})
        else:
            log.append(f"   ✗ 불합격: {d['headline'][:32]} — {'; '.join(v.problems[:2])[:70]}")

    log.insert(0, f"④ 검수 {len(passed)}/{len(drafts)}건 합격")
    return {"verified": passed, "log": log}


# ── 발행 (10강) ──────────────────────────────────────────────
EMBED_MAX, TITLE_MAX, DESC_MAX, TOTAL_MAX = 10, 256, 4096, 6000
COLORS = {"모델": 0x0B6E77, "도구": 0x4C6EF5, "산업": 0xF08C00,
          "정책": 0xE03131, "연구": 0x2F9E44}


def build_embeds(items: list[dict]) -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    head = {"title": f"🗞️ {BRAND} · {today}",
            "description": (f"오늘 {len(items)}건을 골랐습니다." if items
                            else "오늘은 조용합니다. 발행할 만한 소식이 없었습니다."),
            "color": 0x495057}
    embeds = [head]
    for i, a in enumerate(items[:EMBED_MAX - 1], 1):
        desc = f"{a['summary']}\n\n💡 **{a['why']}**"
        embeds.append({
            "title": f"{i}. {a['headline']}"[:TITLE_MAX],
            "description": desc[:DESC_MAX],
            "url": a["url"],
            "color": COLORS.get(a.get("topic", ""), 0x495057),
            "footer": {"text": f"{a['source']} · {a.get('topic', '')}"},
        })
    # 합계 한도를 넘으면 400 이 돌아오고 아무것도 발행되지 않는다 → 미리 자른다
    while sum(len(json.dumps(e, ensure_ascii=False)) for e in embeds) > TOTAL_MAX and len(embeds) > 1:
        embeds.pop()
    return embeds


def publish(state: NewsState):
    """검수를 통과한 만큼 그대로 보낸다. 0건이면 '조용합니다' 한 장만 보낸다."""
    items = state["verified"]
    embeds = build_embeds(items)
    dry = os.getenv("DRY_RUN", "1") != "0"        # 기본은 보내지 않음
    url = os.getenv("DISCORD_WEBHOOK_URL", "")

    if dry:
        line = f"⑤ 발행 [dry-run] embed {len(embeds)}장 · {sum(len(json.dumps(e, ensure_ascii=False)) for e in embeds)}자 — 보내지 않음"
    elif not url:
        line = "⑤ 발행 ⚠️ DISCORD_WEBHOOK_URL 이 없어 보내지 못했습니다"
    else:
        try:
            r = requests.post(url, json={"username": BRAND, "embeds": embeds}, timeout=20)
            line = (f"⑤ 발행 {len(items)}건 전송 · HTTP {r.status_code}"
                    + ("" if r.status_code == 204 else f" · {r.text[:120]}"))
        except Exception as e:
            line = f"⑤ 발행 실패({type(e).__name__})"

    # ── 지표 남기기 (12강) — 실행마다 한 줄씩 append
    Path("store").mkdir(exist_ok=True)
    with open("store/metrics.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "at": datetime.now(timezone.utc).isoformat(),
            "collected": len(state["collected"]), "picked": len(state["picked"]),
            "drafted": len(state["drafted"]), "verified": len(items),
            "verify_fail": len(state["drafted"]) - len(items),
            "sources": sorted({a["source"] for a in items}),
            "dry_run": dry,
        }, ensure_ascii=False) + "\n")

    return {"log": [line]}


# ── 그래프 ───────────────────────────────────────────────────
NODES = ["collect", "select", "draft", "verify", "publish"]


def build():
    """노드를 이름으로 찾아 잇는다. 같은 이름으로 다시 정의하면 그것이 들어간다."""
    b = StateGraph(NewsState)
    for name in NODES:
        b.add_node(name, globals()[name])
    b.add_node("draft_one", draft_one)

    b.add_edge(START, "collect")
    b.add_edge("collect", "select")
    # 팬아웃 경계 — 여기 앞은 모아서 한 번에, 뒤는 건별로 나뉜다
    b.add_conditional_edges("select", fan_out, ["draft_one", "verify"])
    b.add_edge("draft_one", "draft")
    b.add_edge("draft", "verify")
    b.add_edge("verify", "publish")
    b.add_edge("publish", END)
    return b


INIT: NewsState = {"hours": 24, "collected": [], "picked": [],
                   "drafted": [], "verified": [], "log": []}


if __name__ == "__main__":
    result = build().compile().invoke(INIT)
    print("─" * 74)
    for line in result["log"]:
        print("  " + line)
    print("─" * 74)
    if result["verified"]:
        print("\n  ══ 오늘의 브리핑 ══\n")
        for i, a in enumerate(result["verified"], 1):
            print(f"  {i}. [{a['topic']}] {a['headline']}")
            print(f"     {a['summary']}")
            print(f"     💡 {a['why']}")
            print(f"     🔗 {a['source']} · {a['url']}\n")
