"""G4 적합 관문 — 이 소스가 우리 주제의 글을 실제로 쓰는가.

G1(본문)·G2(생존)·G3(접근)은 '가져올 수 있는가'를 묻는다.
G4는 '가져와서 쓸모가 있는가'를 묻는다. 이게 빠져 있어서
종단 소식지를 요가 브리핑 소스로 채택하는 일이 일어났다.

재는 법: 최근 제목 20건을 선별 노드와 같은 기준으로 판정시켜 적중률을 본다.
        키워드 매칭이 아니라 같은 기준을 써야 실제 동작을 예측한다.
"""
from __future__ import annotations
import sys, requests, feedparser
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from sources import UA, PROFILES

SAMPLE = 20
from sources import G4_PASS_RATE as PASS_RATE


class Fit(BaseModel):
    fit_indexes: list[int] = Field(description="주제에 맞는 기사의 번호만")
    note: str = Field(description="이 매체가 주로 무엇을 다루는지 한 줄")


def measure(profile: str, extra: list[tuple[str, str, int]] | None = None):
    cfg = PROFILES[profile]
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0).with_structured_output(Fit)
    srcs = list(cfg["sources"]) + list(extra or [])

    print(f"\n  ══ [{profile}] {cfg['focus']} ══")
    print(f"  {'소스':<16}{'표본':<7}{'적합':<7}{'적중률':<9}판정 · 이 매체의 성격")
    print("  " + "─" * 92)
    keep, drop = [], []
    for name, url, tier in srcs:
        try:
            d = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
        except Exception as e:
            print(f"  {name:<16}{'—':<7}{'—':<7}{'—':<9}❌ {type(e).__name__}"); continue
        titles = [getattr(e, "title", "").strip() for e in d.entries[:SAMPLE]]
        titles = [t for t in titles if t]
        if not titles:
            print(f"  {name:<16}{'0':<7}{'—':<7}{'—':<9}❌ 제목 없음"); continue
        목록 = "\n".join(f"{i}. {t}" for i, t in enumerate(titles))
        try:
            out = llm.invoke(
                f"아래는 '{name}' 매체의 최근 기사 제목입니다.\n"
                f"이 중 **{cfg['focus']}** 에 해당하는 기사의 번호만 고르세요.\n"
                f"{cfg['exclude']} 제외합니다.\n\n{목록}")
        except Exception as e:
            print(f"  {name:<16}{len(titles):<7}{'—':<7}{'—':<9}❌ 판정 실패({type(e).__name__})"); continue
        n = len({i for i in out.fit_indexes if 0 <= i < len(titles)})
        rate = n / len(titles)
        ok = rate >= PASS_RATE
        (keep if ok else drop).append((name, url, tier, rate))
        mark = "✅ 채택" if ok else "❌ 부적합"
        print(f"  {name:<16}{len(titles):<7}{n:<7}{rate*100:>5.0f}%   {mark} · {out.note[:44]}")

    print(f"\n  채택 {len(keep)}곳 / 탈락 {len(drop)}곳  (기준 적중률 {PASS_RATE*100:.0f}%)")
    if drop:
        print("  탈락: " + ", ".join(f"{n}({r*100:.0f}%)" for n, _, _, r in drop))
    print("\n  " + "─" * 92)
    for n, u, t, r in sorted(keep, key=lambda x: -x[3]):
        print(f'      ("{n}", "{u}", {t}),        # 적중률 {r*100:.0f}%')
    return keep, drop


if __name__ == "__main__":
    for prof in (sys.argv[1:] or ["ai", "yoga"]):
        measure(prof)
