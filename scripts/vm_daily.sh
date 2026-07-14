#!/usr/bin/env bash
#
# vm_daily.sh — the daily job a VM scheduler (systemd timer / cron) runs.
#
# Picks the fetch method from PORTFOLIO_PROVIDER (loaded from .env):
#   robinhood -> headless robin_stocks for equity + Yahoo for index closes.
#   otherwise -> official Robinhood MCP via a headless `claude -p` run.
#
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
[ -f .venv/bin/activate ] && . .venv/bin/activate

if [ "${PORTFOLIO_PROVIDER:-manual}" = "robinhood" ]; then
  python -m chasing_voo.auto
else
  bash scripts/local_daily.sh
fi
