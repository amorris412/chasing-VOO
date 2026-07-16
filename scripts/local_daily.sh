#!/usr/bin/env bash
#
# local_daily.sh — hands-off daily update (no stored password).
#
# Uses the Robinhood MCP through a headless Claude Code run to READ your equity
# and the index closes (that's all the agent does). This script itself then
# deterministically decides where to record — never left to the agent to
# branch on, since that's not reliable for an unattended nightly job.
#
# Where the data goes:
#   - If DATA_REPO_DIR is set, records into that private data repo's database
#     and commits + pushes (pull-record-push, via scripts/cloud_update.sh).
#     Set this to keep one continuous history backed up off-machine, e.g.:
#       export DATA_REPO_DIR=$HOME/chasing-VOO-data
#   - Otherwise records into this repo's local data/ folder (never committed).
#
# One-time setup:
#   1. Install the Claude Code CLI and sign in.
#   2. Add + authenticate the Robinhood MCP (a browser opens for OAuth):
#        claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
#        claude            # then in the prompt:  /mcp -> robinhood-trading -> authenticate
#   3. From the repo root:  pip install -e '.[dashboard]'
#
# Then schedule this script daily — see docs/LOCAL_AUTOMATION.md / docs/CLOUD_VM.md.
#
set -euo pipefail
cd "$(dirname "$0")/.."

read -r -d '' PROMPT <<'EOP' || true
Non-interactive read-only fetch. Do exactly this and nothing else — do NOT run
any shell commands, do NOT record anything:
1. Using the robinhood-trading MCP: call get_accounts and pick the default
   account (is_default=true); call get_portfolio for it and read total_value;
   call get_equity_quotes for VOO, DIA and QQQ — for each use the official close
   (results[].close.price) when its date is today, otherwise quote.last_trade_price.
2. Output EXACTLY ONE final line, with no other text on that line, in this
   literal format (replace the placeholders with the numbers, plain decimals,
   no currency symbols or commas):
   CHASINGVOO_RESULT EQUITY=<total_value> VOO=<voo_price> DIA=<dia_price> QQQ=<qqq_price>
EOP

# The agent only fetches and prints; this script parses + records deterministically.
OUTPUT="$(claude -p "$PROMPT" \
  --allowedTools "mcp__robinhood-trading__get_accounts,mcp__robinhood-trading__get_portfolio,mcp__robinhood-trading__get_equity_quotes")"

echo "$OUTPUT"

RESULT_LINE="$(printf '%s\n' "$OUTPUT" | grep -o 'CHASINGVOO_RESULT.*' | tail -1)"
if [[ -z "$RESULT_LINE" ]]; then
  echo "local_daily.sh: FAILED — no CHASINGVOO_RESULT line in agent output; nothing recorded." >&2
  exit 1
fi

EQUITY="$(printf '%s\n' "$RESULT_LINE" | grep -oE 'EQUITY=[0-9.]+' | cut -d= -f2)"
VOO="$(printf '%s\n' "$RESULT_LINE" | grep -oE 'VOO=[0-9.]+' | cut -d= -f2)"
DIA="$(printf '%s\n' "$RESULT_LINE" | grep -oE 'DIA=[0-9.]+' | cut -d= -f2)"
QQQ="$(printf '%s\n' "$RESULT_LINE" | grep -oE 'QQQ=[0-9.]+' | cut -d= -f2)"

if [[ -z "$EQUITY" || -z "$VOO" || -z "$DIA" || -z "$QQQ" ]]; then
  echo "local_daily.sh: FAILED — could not parse all fields from: $RESULT_LINE" >&2
  exit 1
fi

if [[ -n "${DATA_REPO_DIR:-}" ]]; then
  EQUITY="$EQUITY" BENCHMARKS="VOO=${VOO},DIA=${DIA},QQQ=${QQQ}" FLOW="${FLOW:-0}" \
    DATA_REPO_DIR="$DATA_REPO_DIR" bash scripts/cloud_update.sh
  export CHASING_VOO_DB="${DATA_REPO_DIR}/chasing_voo.sqlite3"
else
  python -m chasing_voo.auto --equity "$EQUITY" \
    --benchmark "VOO=${VOO}" --benchmark "DIA=${DIA}" --benchmark "QQQ=${QQQ}" \
    --flow "${FLOW:-0}"
fi

chasing-voo status
