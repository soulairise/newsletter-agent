#!/usr/bin/env bash
# 뉴스레터 에이전트 실행
#   ./run.sh          → dry-run (보내지 않음)
#   ./run.sh --send   → 실제로 디스코드에 발행
set -euo pipefail
cd "$(dirname "$0")"

for f in ~/.config/harness-lab/env ~/.config/newsletter-agent/env; do
  [ -f "$f" ] && . "$f"
done

: "${OPENAI_API_KEY:?OPENAI_API_KEY 가 없습니다 — ~/.config/harness-lab/env 를 확인하세요}"

if [ "${1:-}" = "--send" ]; then
  : "${DISCORD_WEBHOOK_URL:?DISCORD_WEBHOOK_URL 이 없습니다 — ~/.config/newsletter-agent/env 를 만드세요}"
  export DRY_RUN=0
  echo "▶ 실제 발행 모드"
else
  export DRY_RUN=1
  echo "▶ dry-run 모드 (보내지 않음). 실제로 보내려면 ./run.sh --send"
fi

exec uv run python run.py
