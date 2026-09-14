"""13강 — 내 분야로 옮기기. 요가·명상 소스 후보를 G1·G2·G3 로 잰다."""
import time, feedparser, requests
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

CANDIDATES = [
    ("Yoga Journal",   "https://www.yogajournal.com/feed/",                     2),
    ("Yoga Basics",    "https://www.yogabasics.com/feed/",                      2),
    ("EkhartYoga",     "https://www.ekhartyoga.com/articles/feed",              2),
    ("Yoga Interntl",  "https://yogainternational.com/rss/",                    2),
    ("Tricycle",       "https://tricycle.org/feed/",                            1),
    ("Lion's Roar",    "https://www.lionsroar.com/feed/",                       1),
    ("Mindful.org",    "https://www.mindful.org/feed/",                         2),
    ("Greater Good",   "https://greatergood.berkeley.edu/feeds/all_articles",   1),
    ("Insight Timer",  "https://insighttimer.com/blog/feed/",                   2),
    ("Buddhistdoor",   "https://www.buddhistdoor.net/feed/",                    2),
    ("불교신문",        "https://www.ibulgyo.com/rss/allArticle.xml",            2),
    ("법보신문",        "https://www.beopbo.com/rss/allArticle.xml",             2),
    ("현대불교",        "https://www.hyunbulnews.com/rss/allArticle.xml",        2),
]
UA = {"User-Agent": "Mozilla/5.0 (newsletter-agent; study project)"}

def age_hours(e):
    t = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
    if not t: return None
    return (datetime.now(timezone.utc) - datetime(*t[:6], tzinfo=timezone.utc)).total_seconds()/3600

def g3(url):
    p = urlparse(url)
    try:
        r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers=UA, timeout=10)
        if r.status_code == 404: return True
        if r.status_code != 200: return None
        rp = RobotFileParser(); rp.parse(r.text.splitlines())
        return rp.can_fetch("*", url)
    except Exception: return None

print(f"  {'소스':<16}{'tier':<6}{'건수':<7}{'요약평균':<10}{'최신글':<11}{'robots':<9}판정")
print("  " + "─" * 80)
keep = []
for name, url, tier in CANDIDATES:
    try:
        r = requests.get(url, headers=UA, timeout=20)
        d = feedparser.parse(r.content)
        n = len(d.entries)
        if n == 0:
            print(f"  {name:<16}{tier:<6}{'0':<7}{'—':<10}{'—':<11}{'—':<9}❌ 피드 비었음 (HTTP {r.status_code})"); continue
        slen = sum(len(getattr(e, "summary", "")) for e in d.entries[:10]) // min(10, n)
        ages = [a for a in (age_hours(e) for e in d.entries[:10]) if a is not None]
        newest = min(ages) if ages else None
        ok3 = g3(url)
        alive = newest is not None and newest < 24*30      # 30일 안에 새 글 (요가는 뉴스보다 느리다)
        ok = alive and ok3 is not False
        if ok: keep.append((name, url, tier))
        na = f"{newest:.0f}h" if newest is not None else "날짜없음"
        rb = {True:"허용", False:"금지", None:"확인불가"}[ok3]
        v = "✅ 채택" if ok else ("❌ G2 뜸함" if not alive else "❌ G3 차단")
        print(f"  {name:<16}{tier:<6}{n:<7}{slen:<10}{na:<11}{rb:<9}{v}")
    except Exception as e:
        print(f"  {name:<16}{tier:<6}{'—':<7}{'—':<10}{'—':<11}{'—':<9}❌ {type(e).__name__}")
    time.sleep(0.3)

print(f"\n  채택 {len(keep)}곳 / 후보 {len(CANDIDATES)}곳\n")
for n,u,t in keep: print(f'      ("{n}", "{u}", {t}),')
