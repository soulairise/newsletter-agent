"""채택된 소스 목록 (measure_sources.py 로 G1·G2·G3 관문을 통과한 곳)

tier 1 = 1차 소스(당사자 발표) — 선별 경쟁에서 면제하되 검사는 받는다
tier 2 = 2차 소스(매체) — 경쟁을 거친다
"""
SOURCES = [
    ("TechCrunch",  "https://techcrunch.com/feed/",                2),
    ("The Verge",   "https://www.theverge.com/rss/index.xml",      2),
    ("OpenAI",      "https://openai.com/news/rss.xml",             1),
    ("DeepMind",    "https://deepmind.google/blog/rss.xml",        1),
    ("HuggingFace", "https://huggingface.co/blog/feed.xml",        1),
    ("AI타임스",     "https://www.aitimes.com/rss/allArticle.xml",   2),
    ("전자신문",     "https://rss.etnews.com/Section901.xml",        2),
    ("Hacker News", "https://hnrss.org/newest?q=AI&points=100",     2),
]

UA = {"User-Agent": "Mozilla/5.0 (newsletter-agent; study project)"}
PER_SOURCE_CAP = 25    # 소스 하나가 후보를 독점하지 않도록
