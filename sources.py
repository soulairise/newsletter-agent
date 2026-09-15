"""audience.yaml 을 읽어 프로필 설정을 제공한다.

설정을 코드에서 분리한 이유 — 독자·중요도 기준·제외 조건은
파이프라인을 고치지 않고 바꾸는 값이기 때문이다.
새 분야로 옮길 때 audience.yaml 에 프로필을 하나 더 적으면 된다.
"""
import os
from pathlib import Path

import yaml

_CFG = yaml.safe_load((Path(__file__).parent / "audience.yaml").read_text(encoding="utf-8"))
_D = _CFG["defaults"]

UA = {"User-Agent": "Mozilla/5.0 (newsletter-agent; study project)"}

PROFILES = {
    name: {
        "brand": p["brand"],
        "reader": p["reader"],
        "hours": p["hours"],
        "topics": p["topics"],
        "focus": p["focus"].strip(),
        "exclude": p["exclude"].strip(),
        "sources": [(s["name"], s["url"], s["tier"]) for s in p["sources"]],
    }
    for name, p in _CFG["profiles"].items()
}

PROFILE = os.getenv("NEWSLETTER_PROFILE", "ai")
if PROFILE not in PROFILES:
    raise SystemExit(f"알 수 없는 프로필: {PROFILE} (가능: {', '.join(PROFILES)})")

CFG = PROFILES[PROFILE]
SOURCES = CFG["sources"]

PER_SOURCE_CAP = _D["per_source_cap"]
CHUNK = _D["chunk"]
SEMI_KEEP = _D["semi_keep"]
TIER1_CAP = _D["tier1_cap"]
FINAL_N = _D["final_n"]
OUTLET_CAP = _D["outlet_cap"]
G4_PASS_RATE = _D["g4_pass_rate"]
