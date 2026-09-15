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
        "hours": 336,          # 14일. 소스를 3곳으로 좁혀 후보가 줄어 창을 넓혔다
        "topics": ["아사나", "호흡", "명상", "해부학", "연구"],
        # '과학 연구'를 나열에 넣었더니 모델이 그것을 필수 조건으로 읽어
        # 실제 수련법 기사를 탈락시켰다. 아래처럼 '다음 중 하나라도' 로 못 박는다.
        "focus": ("요가와 명상 수련 — 아래 중 하나라도 해당하면 적합하다: "
                  "아사나(자세) 설명이나 시퀀스, 호흡법, 명상 방법과 태도, "
                  "마음챙김 실천, 요가 해부학과 부상 예방, "
                  "수련이 몸과 마음에 미치는 영향을 다룬 연구, 수련자의 경험과 통찰"),
        "exclude": ("특정 종교의 교리·종단 소식·법회·사찰 행사·종교 인물 기사와 "
                    "일반 건강·다이어트·제품 홍보 기사는"),
        "reader": "요가를 가르치거나 꾸준히 수련하는 사람",
        # G4 적합 관문(gate_g4.py)으로 재서 적중률 30% 이상만 남겼다.
        # tier 1 을 두지 않았다 — 이 분야에는 '당사자 발표'에 해당하는 소스가 없다.
        # 잡지(Tricycle·Lion's Roar)를 1차 소스로 두면 적중률 30%짜리가 경쟁 없이 통과한다.
        # G4 를 '불교 제외 · 요가/명상 실천' 기준으로 다시 돌려 고른 곳.
        # 기존 불교 매체 4곳은 전부 탈락했다 (Tricycle 0%, Lion's Roar 20%,
        # 불교신문 기획 15%, 현대불교 신행 15%).
        "sources": [
            ("Yoga Journal",  "https://www.yogajournal.com/feed/",  2),   # 50%
            ("Mindful.org",   "https://www.mindful.org/feed/",      2),   # 40%
            ("Yoga Medicine", "https://yogamedicine.com/feed/",     2),   # 40%
        ],
    },
}

PROFILE = os.getenv("NEWSLETTER_PROFILE", "ai")
if PROFILE not in PROFILES:
    raise SystemExit(f"알 수 없는 프로필: {PROFILE} (가능: {', '.join(PROFILES)})")

CFG = PROFILES[PROFILE]
SOURCES = CFG["sources"]
PER_SOURCE_CAP = 25
