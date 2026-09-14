"""4강 — 소스를 재고 고르기. 관문 G1(본문) · G2(생존) · G3(접근)"""
import time, feedparser, requests
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

CANDIDATES = [
    ("TechCrunch",   "https://techcrunch.com/feed/",                    2),
    ("The Verge",    "https://www.theverge.com/rss/index.xml",          2),
    ("VentureBeat",  "https://venturebeat.com/category/ai/feed/",       2),
    ("OpenAI",       "https://openai.com/news/rss.xml",                 1),
    ("DeepMind",     "https://deepmind.google/blog/rss.xml",            1),
    ("HuggingFace",  "https://huggingface.co/blog/feed.xml",            1),
    ("AI타임스",      "https://www.aitimes.com/rss/allArticle.xml",      2),
    ("전자신문",      "https://rss.etnews.com/Section901.xml",           2),
    ("Hacker News",  "https://hnrss.org/newest?q=AI&points=100",        2),
]
UA = {"User-Agent": "Mozilla/5.0 (newsletter-agent; study project)"}

def age_hours(e):
    t = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
    if not t: return None
    return (datetime.now(timezone.utc) - datetime(*t[:6], tzinfo=timezone.utc)).total_seconds() / 3600

def g3_access(url):
    """robots.txt 판정.

    RobotFileParser.read() 는 파이썬 기본 UA 를 쓰는데, 그 UA 를 403 으로 막는 사이트가 있다.
    그러면 파서가 401/403 을 '전부 금지'로 해석해 실제로는 허용인 사이트를 탈락시킨다.
    (openai.com 이 그 경우였다 — robots.txt 본문은 Allow: / 인데 False 가 나왔다.)
    그래서 requests 로 직접 받아 파서에 먹인다.
    """
    p = urlparse(url)
    try:
        r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers=UA, timeout=10)
        if r.status_code == 404:
            return True                      # robots.txt 가 없으면 제한 없음
        if r.status_code != 200:
            return None                      # 판정 보류
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch("*", url)
    except Exception:
        return None

print(f"  {'소스':<14}{'tier':<6}{'건수':<7}{'요약평균':<10}{'최신글':<12}{'robots':<9}판정")
print("  " + "─" * 78)
keep = []
for name, url, tier in CANDIDATES:
    try:
        r = requests.get(url, headers=UA, timeout=15)
        d = feedparser.parse(r.content)
        n = len(d.entries)
        if n == 0:
            print(f"  {name:<14}{tier:<6}{'0':<7}{'—':<10}{'—':<12}{'—':<9}❌ G2 피드 비었음"); continue
        slen = sum(len(getattr(e, "summary", "")) for e in d.entries[:10]) // min(10, n)
        ages = [a for a in (age_hours(e) for e in d.entries[:10]) if a is not None]
        newest = min(ages) if ages else None
        ok3 = g3_access(url)
        g2 = newest is not None and newest < 24 * 14      # 14일 안에 새 글
        verdict = "✅ 채택" if (g2 and ok3 is not False) else ("❌ G2 뜸함" if not g2 else "❌ G3 차단")
        if g2 and ok3 is not False: keep.append((name, url, tier))
        na = f"{newest:.0f}h" if newest is not None else "날짜없음"
        rb = {True: "허용", False: "금지", None: "확인불가"}[ok3]
        print(f"  {name:<14}{tier:<6}{n:<7}{slen:<10}{na:<12}{rb:<9}{verdict}")
    except Exception as e:
        print(f"  {name:<14}{tier:<6}{'—':<7}{'—':<10}{'—':<12}{'—':<9}❌ {type(e).__name__}")
    time.sleep(0.3)

print(f"\n  채택 {len(keep)}곳 / 후보 {len(CANDIDATES)}곳")
print("\n  SOURCES = [")
for n, u, t in keep: print(f'      ("{n}", "{u}", {t}),')
print("  ]")
