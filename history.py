"""발행 이력 — 같은 글을 두 번 보내지 않기 위한 장치.

요가 프로필은 시간 창이 7일이라, 이력이 없으면 같은 기사가 일주일 내내
후보로 올라와 반복 발행된다. 창의 2배 기간만 보관하고 그보다 오래된 것은 버린다.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

STORE = Path("store/published.jsonl")


def load_sent(profile: str, keep_hours: int) -> set[str]:
    """이 프로필에서 최근에 발행한 기사 키 집합."""
    if not STORE.exists():
        return set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=keep_hours)
    out: set[str] = set()
    for line in STORE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue                       # 깨진 줄은 건너뛴다
        if r.get("profile") != profile:
            continue
        try:
            at = datetime.fromisoformat(r["at"])
        except Exception:
            continue
        if at >= cutoff:
            out.add(r["key"])
    return out


def record(profile: str, items: list[dict]) -> None:
    """실제로 보낸 것만 남긴다. dry-run 은 기록하지 않는다."""
    if not items:
        return
    STORE.parent.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with STORE.open("a", encoding="utf-8") as f:
        for a in items:
            f.write(json.dumps({
                "profile": profile, "at": now, "key": a["key"],
                "url": a["url"], "headline": a.get("headline", ""),
                "source": a.get("source", ""),
            }, ensure_ascii=False) + "\n")


def prune(keep_hours: int) -> int:
    """오래된 줄을 실제로 지워 파일이 무한히 커지지 않게 한다."""
    if not STORE.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=keep_hours * 2)
    kept, dropped = [], 0
    for line in STORE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            at = datetime.fromisoformat(json.loads(line)["at"])
        except Exception:
            dropped += 1; continue
        if at >= cutoff:
            kept.append(line)
        else:
            dropped += 1
    STORE.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return dropped
