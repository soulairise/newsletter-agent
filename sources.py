"""소스 목록 — 분야(프로필)별로 나눠 둔다.

NEWSLETTER_PROFILE 환경변수로 고른다. 기본은 ai.
각 목록은 measure_sources.py / measure_yoga.py 로 G1·G2·G3 관문을 재서 채택한 것.

tier 1 = 1차 소스(당사자·원전) — 선별 경쟁 면제, 검사는 받음
tier 2 = 2차 소스(매체) — 경쟁을 거침
"""
import os

UA = {"User-Agent": "Mozilla/5.0 (newsletter-agent; study project)"}

PROFILES = {
    # ── AI 업계: 매체가 하루 수십 건을 쏟아낸다 → 24시간 창
    "ai": {
        "brand": "소울라이즈 AI 브리핑",
        "hours": 24,
        "topics": ["모델", "도구", "산업", "정책", "연구"],
        "focus": "AI·머신러닝·개발도구·반도체 등 기술 주제",
        "exclude": "정치·국제정세·사건사고·주가·인사 기사는 기술과 직접 관련이 없으면",
        "reader": "국내 개발팀",
        "sources": [
            ("TechCrunch",  "https://techcrunch.com/feed/",                2),   # 45%
            ("The Verge",   "https://www.theverge.com/rss/index.xml",      2),   # 60%
            ("OpenAI",      "https://openai.com/news/rss.xml",             1),   # 65%
            ("DeepMind",    "https://deepmind.google/blog/rss.xml",        1),   # 85%
            ("HuggingFace", "https://huggingface.co/blog/feed.xml",        1),   # 90%
            ("AI타임스",     "https://www.aitimes.com/rss/allArticle.xml",   2),   # 80%
            ("전자신문",     "https://rss.etnews.com/Section901.xml",        2),   # 30%
            ("Hacker News", "https://hnrss.org/newest?q=AI&points=100",     2),   # 75%
        ],
    },

    # ── 요가·명상: 해외 매체는 주 1~2회, 국내 불교지는 매일 → 창을 넓힌다
    "yoga": {
        "brand": "소울라이즈 수련 브리핑",
        "hours": 168,          # 7일. 24시간으로는 후보가 거의 안 모인다
        "topics": ["수련", "명상", "경전", "해부학", "현장"],
        "focus": "요가·명상·수행·불교·마음챙김·몸과 호흡 주제",
        "exclude": "종단 인사·행정·부동산·정치 기사는 수련과 직접 관련이 없으면",
        "reader": "요가를 가르치거나 꾸준히 수련하는 사람",
        # G4 적합 관문(gate_g4.py)으로 재서 적중률 30% 이상만 남겼다.
        # tier 1 을 두지 않았다 — 이 분야에는 '당사자 발표'에 해당하는 소스가 없다.
        # 잡지(Tricycle·Lion's Roar)를 1차 소스로 두면 적중률 30%짜리가 경쟁 없이 통과한다.
        "sources": [
            ("Yoga Journal",  "https://www.yogajournal.com/feed/",         2),   # 80%
            ("Lion's Roar",   "https://www.lionsroar.com/feed/",           2),   # 50%
            ("Mindful.org",   "https://www.mindful.org/feed/",             2),   # 50%
            ("불교신문 기획",   "https://www.ibulgyo.com/rss/S1N6.xml",       2),   # 35%
            ("Tricycle",      "https://tricycle.org/feed/",                2),   # 30%
            ("현대불교 신행",   "https://www.hyunbulnews.com/rss/S1N2.xml",   2),   # 30%
        ],
    },
}

PROFILE = os.getenv("NEWSLETTER_PROFILE", "ai")
if PROFILE not in PROFILES:
    raise SystemExit(f"알 수 없는 프로필: {PROFILE} (가능: {', '.join(PROFILES)})")

CFG = PROFILES[PROFILE]
SOURCES = CFG["sources"]
PER_SOURCE_CAP = 25
