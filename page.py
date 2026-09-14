"""브리핑을 HTML 로 내보낸다 — 고정 주소 + 회차 보관.

방장봇 알림메시지는 고정 문구만 보낼 수 있다.
그래서 문구에 고정 주소를 넣고, 그 주소 뒤의 내용을 매일 갈아 끼운다.

  docs/<profile>/index.html          ← 고정 주소. 방장봇이 가리킬 곳
  docs/<profile>/YYYY-MM-DD.html     ← 회차 보관
  docs/index.html                    ← 전체 입구
"""
from __future__ import annotations
import html
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DOCS = Path("docs")
KST = timezone(timedelta(hours=9))

CSS = """
:root{--ink:#1c1917;--soft:#78716c;--line:#e7e5e4;--bg:#faf9f7;--accent:#0b6e77}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:400 17px/1.75 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard",sans-serif;
     -webkit-text-size-adjust:100%}
.wrap{max-width:44rem;margin:0 auto;padding:2.2rem 1.15rem 4rem}
header{border-bottom:1px solid var(--line);padding-bottom:1.3rem;margin-bottom:2rem}
h1{margin:0 0 .35rem;font-size:1.45rem;letter-spacing:-.02em}
.date{color:var(--soft);font-size:.95rem}
article{padding:1.5rem 0;border-bottom:1px solid var(--line)}
article:last-of-type{border-bottom:0}
h2{margin:0 0 .6rem;font-size:1.16rem;line-height:1.5;letter-spacing:-.01em}
h2 a{color:var(--ink);text-decoration:none}
h2 a:hover{color:var(--accent)}
.topic{display:inline-block;font-size:.76rem;padding:.16rem .5rem;border-radius:999px;
       background:#0b6e7714;color:var(--accent);margin-bottom:.55rem;letter-spacing:.02em}
p{margin:0 0 .8rem}
.why{background:#fff;border-left:3px solid var(--accent);padding:.75rem .9rem;
     border-radius:0 6px 6px 0;font-size:.97rem}
.src{color:var(--soft);font-size:.88rem}
.src a{color:var(--soft)}
.quiet{color:var(--soft);padding:2.5rem 0;text-align:center}
footer{margin-top:2.5rem;padding-top:1.3rem;border-top:1px solid var(--line);
       color:var(--soft);font-size:.86rem}
footer a{color:var(--soft)}
ul.past{list-style:none;padding:0;margin:.6rem 0 0}
ul.past li{padding:.3rem 0}
@media(max-width:420px){.wrap{padding:1.6rem .95rem 3rem}h1{font-size:1.3rem}h2{font-size:1.1rem}}
@media(prefers-color-scheme:dark){
  :root{--ink:#e7e5e4;--soft:#a8a29e;--line:#292524;--bg:#1c1917;--accent:#5eb8c0}
  .why{background:#292524}
}
"""


def _shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head><body><div class="wrap">{body}</div></body></html>"""


def render_issue(brand: str, items: list[dict], when: datetime) -> str:
    d = when.astimezone(KST)
    head = (f'<header><h1>{html.escape(brand)}</h1>'
            f'<div class="date">{d.strftime("%Y년 %m월 %d일")}</div></header>')
    if not items:
        body = '<div class="quiet">오늘은 조용합니다.<br>발행할 만한 소식이 없었습니다.</div>'
    else:
        parts = []
        for a in items:
            parts.append(
                '<article>'
                f'<div class="topic">{html.escape(a.get("topic",""))}</div>'
                f'<h2><a href="{html.escape(a["url"])}" target="_blank" rel="noopener">'
                f'{html.escape(a["headline"])}</a></h2>'
                f'<p>{html.escape(a["summary"])}</p>'
                f'<p class="why">💡 {html.escape(a["why"])}</p>'
                f'<p class="src">{html.escape(a["source"])} · '
                f'<a href="{html.escape(a["url"])}" target="_blank" rel="noopener">원문 보기</a></p>'
                '</article>')
        body = "".join(parts)
    foot = ('<footer>소울라이즈 · 매일 아침 자동 발행<br>'
            '<a href="archive.html">지난 회차 보기</a></footer>')
    return _shell(f"{brand} · {d.strftime('%m/%d')}", head + body + foot)


def render_archive(brand: str, profile: str) -> str:
    d = DOCS / profile
    past = sorted((f.stem for f in d.glob("20*.html")), reverse=True)
    li = "".join(f'<li><a href="{p}.html">{p}</a></li>' for p in past) or '<li class="src">아직 없습니다</li>'
    body = (f'<header><h1>{html.escape(brand)}</h1>'
            f'<div class="date">지난 회차 {len(past)}건</div></header>'
            f'<ul class="past">{li}</ul>'
            '<footer><a href="index.html">최신 회차로</a></footer>')
    return _shell(f"{brand} · 지난 회차", body)


def render_home(profiles: dict[str, str]) -> str:
    li = "".join(f'<li><a href="{p}/">{html.escape(b)}</a></li>' for p, b in profiles.items())
    body = ('<header><h1>소울라이즈 브리핑</h1>'
            '<div class="date">매일 아침 자동 발행</div></header>'
            f'<ul class="past">{li}</ul>')
    return _shell("소울라이즈 브리핑", body)


def publish_page(profile: str, brand: str, items: list[dict]) -> tuple[str, int]:
    """오늘치를 고정 주소와 회차 파일에 쓴다. (경로, 회차 수) 를 돌려준다."""
    now = datetime.now(timezone.utc)
    d = DOCS / profile
    d.mkdir(parents=True, exist_ok=True)
    (d / ".nojekyll").write_text("", encoding="utf-8")   # Jekyll 처리를 건너뛴다

    page = render_issue(brand, items, now)
    stamp = now.astimezone(KST).strftime("%Y-%m-%d")
    (d / f"{stamp}.html").write_text(page, encoding="utf-8")
    (d / "index.html").write_text(page, encoding="utf-8")
    (d / "archive.html").write_text(render_archive(brand, profile), encoding="utf-8")

    # 전체 입구는 존재하는 프로필만 모아 다시 만든다
    from sources import PROFILES
    have = {p: PROFILES[p]["brand"] for p in PROFILES if (DOCS / p / "index.html").exists()}
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "index.html").write_text(render_home(have), encoding="utf-8")

    return str(d / "index.html"), len(list(d.glob("20*.html")))
