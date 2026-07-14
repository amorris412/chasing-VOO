#!/usr/bin/env bash
#
# cloud_update.sh — record one daily snapshot into the PRIVATE data repo.
#
# Designed for the scheduled cloud run: an agent reads your equity (and net
# deposits) from the Robinhood MCP, then calls this script to persist them.
# Your financial history lives ONLY in the private data repo — never in the
# public code repo.
#
# Usage:
#   EQUITY=12500.42 FLOW=0 DATA_REPO_DIR=/path/to/chasing-VOO-data \
#     scripts/cloud_update.sh
#
# Env vars:
#   EQUITY        (required) total portfolio value in USD
#   BENCHMARKS    (optional) comma list of index closes, e.g.
#                 "VOO=689.62,DIA=523.27,QQQ=718.42". Supply these from the same
#                 broker/MCP that gave you EQUITY so the run needs no external
#                 market-data call. Any configured index left out is fetched
#                 from Yahoo instead.
#   FLOW          (optional) net deposits that day in USD (default 0)
#   DATA_REPO_DIR (required) path to a checkout of the PRIVATE data repo
#   DATE          (optional) YYYY-MM-DD (default: today)
#
set -euo pipefail

: "${EQUITY:?set EQUITY to the current portfolio value}"
: "${DATA_REPO_DIR:?set DATA_REPO_DIR to the private data repo checkout}"
FLOW="${FLOW:-0}"

# Store the database inside the private data repo.
export CHASING_VOO_DB="${DATA_REPO_DIR}/chasing_voo.sqlite3"

# Pass benchmark prices to the updater via its env var.
[[ -n "${BENCHMARKS:-}" ]] && export CHASING_VOO_BENCHMARKS="${BENCHMARKS}"

# Get the latest data before appending (avoid clobbering a prior run).
git -C "${DATA_REPO_DIR}" pull --ff-only origin main >/dev/null 2>&1 || true

# Record the snapshot.
EXTRA_ARGS=()
[[ -n "${DATE:-}" ]] && EXTRA_ARGS+=(--date "${DATE}")
python -m chasing_voo.auto --equity "${EQUITY}" --flow "${FLOW}" "${EXTRA_ARGS[@]}"

# Also write a human-readable CSV so the history is diff-friendly in git.
chasing-voo export --out "${DATA_REPO_DIR}/history.csv"

# Commit and push to the private data repo.
git -C "${DATA_REPO_DIR}" add -A
if git -C "${DATA_REPO_DIR}" diff --cached --quiet; then
  echo "cloud_update: no changes to commit."
else
  git -C "${DATA_REPO_DIR}" commit -q -m "data: snapshot ${DATE:-$(date +%F)}"
  git -C "${DATA_REPO_DIR}" push -q origin main
  echo "cloud_update: pushed snapshot to private data repo."
fi
