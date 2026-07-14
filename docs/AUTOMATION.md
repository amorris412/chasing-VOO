# Automation architecture (cloud)

Fully hands-off tracking, no manual entry. Here's how the pieces fit together
and why the data is split across two repos.

```
┌─────────────────────────────┐     daily (weekdays, after close)
│  Scheduled cloud run (agent)│ ◀───────────────────────────────
│                             │
│  1. Robinhood MCP (OAuth)   │  reads equity + net deposits
│         │                   │
│         ▼                   │
│  2. scripts/cloud_update.sh │  records snapshot + VOO close
│         │                   │
│         ▼                   │
│  3. git push  ──────────────┼──▶  chasing-VOO-data  (PRIVATE)
└─────────────────────────────┘        └── chasing_voo.sqlite3
                                        └── history.csv
        code lives in
   chasing-VOO (PUBLIC) ──────────────▶  cloned read-only by the run
```

## Why two repos

`chasing-VOO` is **public**, so it must never contain your portfolio history.
Your daily numbers live in a separate **private** repo, `chasing-VOO-data`.
The code repo is open; the money data is not.

## What runs each day

`scripts/cloud_update.sh`:

1. Pulls the latest `chasing-VOO-data`.
2. Runs `python -m chasing_voo.auto --equity <n> --flow <n>` with the values
   the agent read from the Robinhood MCP (equity, and net deposits/withdrawals
   detected from your transfer history so returns stay honest).
3. Writes both `chasing_voo.sqlite3` and a diff-friendly `history.csv`.
4. Commits and pushes to the private data repo.

## Deposit / withdrawal detection

Each run asks the Robinhood MCP for account transfers dated that day and passes
the net amount as `--flow`. A pure-deposit day then shows ~0% return instead of
a fake spike. If transfer data is unavailable for a given day, `--flow`
defaults to 0 and you can backfill later.

## Viewing the dashboard

The dashboard is local. To see it with the latest cloud-updated data:

```bash
git clone https://github.com/<you>/chasing-VOO-data   # private, one time
# then, whenever you want to look:
git -C chasing-VOO-data pull
CHASING_VOO_DB=$(pwd)/chasing-VOO-data/chasing_voo.sqlite3 \
  streamlit run dashboard/app.py
```

## Token lifetime

The Robinhood MCP uses OAuth; the token is cached and refreshed, so scheduled
runs are unattended after the one-time `/mcp` authentication. If a run reports
an auth error, re-authenticate once with `/mcp` and it resumes.
