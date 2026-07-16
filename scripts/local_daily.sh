#!/usr/bin/env bash
#
# local_daily.sh — hands-off daily update (no stored password).
#
# Uses the Robinhood MCP through a headless Claude Code run to read your equity
# and the index closes. The Robinhood login stays inside its own OAuth token,
# managed by Claude Code — nothing is stored by this script.
#
# Where the data goes:
#   - If DATA_REPO_DIR is set, records into that private data repo's database
#     and commits + pushes (pull-record-push, same as scripts/cloud_update.sh).
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

# Make CHASING_VOO_DB visible to every Bash call the headless run makes below
# (including the final `chasing-voo status`), so they all agree on the same file.
if [[ -n "${DATA_REPO_DIR:-}" ]]; then
  export CHASING_VOO_DB="${DATA_REPO_DIR}/chasing_voo.sqlite3"
fi

read -r -d '' PROMPT <<'EOP' || true
Non-interactive daily portfolio update. Do exactly this and nothing else:
1. Using the robinhood-trading MCP: call get_accounts and pick the default
   account (is_default=true); call get_portfolio for it and read total_value;
   call get_equity_quotes for VOO, DIA and QQQ — for each use the official close
   (results[].close.price) when its date is today, otherwise quote.last_trade_price.
2. Check the environment variable DATA_REPO_DIR.
   - If it IS set, run:
       EQUITY=<total_value> BENCHMARKS="VOO=<voo>,DIA=<dia>,QQQ=<qqq>" FLOW=0 \
         bash scripts/cloud_update.sh
     (this pulls the latest data repo, records the day, commits, and pushes)
   - If it is NOT set, run instead:
       python -m chasing_voo.auto --equity <total_value> \
         --benchmark VOO=<voo> --benchmark DIA=<dia> --benchmark QQQ=<qqq>
3. Print the output of: chasing-voo status
EOP

# --allowedTools keeps the run non-interactive (no permission prompts) and
# limited to exactly the tools it needs.
claude -p "$PROMPT" \
  --allowedTools "Bash,mcp__robinhood-trading__get_accounts,mcp__robinhood-trading__get_portfolio,mcp__robinhood-trading__get_equity_quotes"
