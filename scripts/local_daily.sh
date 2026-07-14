#!/usr/bin/env bash
#
# local_daily.sh — hands-off daily update on YOUR machine (no stored password).
#
# Uses the Robinhood MCP through a headless Claude Code run to read your equity
# and the index closes, then records them into the LOCAL database (data/).
# Nothing financial ever leaves your machine and no credentials are stored — the
# Robinhood login stays inside its own OAuth token, managed by Claude Code.
#
# One-time setup:
#   1. Install the Claude Code CLI and sign in.
#   2. Add + authenticate the Robinhood MCP (a browser opens for OAuth):
#        claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
#        claude            # then in the prompt:  /mcp -> robinhood-trading -> authenticate
#   3. From the repo root:  pip install -e '.[dashboard]'
#
# Then schedule this script daily — see docs/LOCAL_AUTOMATION.md.
#
set -euo pipefail
cd "$(dirname "$0")/.."

read -r -d '' PROMPT <<'EOP' || true
Non-interactive daily portfolio update. Do exactly this and nothing else:
1. Using the robinhood-trading MCP: call get_accounts and pick the default
   account (is_default=true); call get_portfolio for it and read total_value;
   call get_equity_quotes for VOO, DIA and QQQ — for each use the official close
   (results[].close.price) when its date is today, otherwise quote.last_trade_price.
2. Run one shell command:
   python -m chasing_voo.auto --equity <total_value> \
     --benchmark VOO=<voo> --benchmark DIA=<dia> --benchmark QQQ=<qqq>
3. Print the output of: chasing-voo status
EOP

# --allowedTools keeps the run non-interactive (no permission prompts) and
# limited to exactly the tools it needs.
claude -p "$PROMPT" \
  --allowedTools "Bash,mcp__robinhood-trading__get_accounts,mcp__robinhood-trading__get_portfolio,mcp__robinhood-trading__get_equity_quotes"
