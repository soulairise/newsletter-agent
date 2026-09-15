"""파이프라인 실행 스크립트.

  python run.py                      # 설정된 프로필로 실행
  NEWSLETTER_PROFILE=yoga python run.py
  DRY_RUN=0 python run.py            # 실제 발행

환경변수
  NEWSLETTER_PROFILE  yoga | ai   (기본 ai)
  DRY_RUN             1 이면 보내지 않음 (기본 1)
  OPENAI_API_KEY      선별·취재·검수에 필요
  DISCORD_WEBHOOK_URL 발행에 필요
"""
import os
import sys

from graph import build, INIT
from sources import CFG, PROFILE


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 없습니다.", file=sys.stderr)
        return 1

    result = build().compile().invoke(INIT)

    print("─" * 74)
    for line in result["log"]:
        print("  " + line)
    print("─" * 74)

    if result["verified"]:
        print(f"\n  ══ {CFG['brand']} ══\n")
        for i, a in enumerate(result["verified"], 1):
            print(f"  {i}. [{a['topic']}] {a['headline']}")
            print(f"     {a['summary']}")
            print(f"     💡 {a['why']}")
            print(f"     🔗 {a['source']} · {a['url']}\n")
    else:
        print(f"\n  {PROFILE}: 오늘은 발행할 것이 없습니다.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
