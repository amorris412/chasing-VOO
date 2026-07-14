# 📈 chasing-VOO

*Are you actually beating the index?*

A small, local, privacy-first tool that tracks your portfolio against a market
index (**VOO** — Vanguard's S&P 500 ETF — by default) and answers the only
question that matters for a stock-picker: **am I beating the market, and how
often?**

It records a daily snapshot of your portfolio value, pulls the benchmark's
close, and computes:

- **Daily result** — did you beat the index today?
- **Win rate** — the share of days you out-return the index.
- **Cumulative return** — you vs the index since day one.
- **Lead / lag** — how far ahead of (or behind) the index you are overall.

Everything runs on your machine. Your financial history lives in a local SQLite
file that is **never** committed or sent anywhere.

---

## Why this is more honest than a naive tracker

If you deposit $1,000, your account value jumps — but that's not *return*, it's
cash you added. Comparing raw equity to the index would flatter you on deposit
days and punish you on withdrawal days. chasing-VOO lets you record the day's
**net deposits/withdrawals** and strips them out of the return math:

```
daily_return = (equity_today − net_deposits_today) / equity_yesterday − 1
```

So a pure-deposit day shows ~0% return, and the comparison against VOO stays
fair.

---

## Quick start

```bash
# 1. Install (core + local dashboard)
pip install -e '.[dashboard]'

# 2. Connect Robinhood once (OAuth — no password stored). See Automation below.
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
#    then authenticate:  /mcp  ->  robinhood-trading  ->  authenticate

# 3. Record today automatically (schedule this daily — see Automation)
python -m chasing_voo.auto --equity <equity from the MCP>

# 4. See where you stand
chasing-voo status

# 5. Open the visual (read-only) dashboard
streamlit run dashboard/app.py
```

The dashboard is **read-only**. Snapshots are recorded automatically (see
Automation below) — there is no manual data entry.

---

## Automation (no manual entry)

The daily updater is a single, non-interactive entrypoint:

```bash
# Equity supplied by an agent/MCP (recommended — no stored credentials):
python -m chasing_voo.auto --equity 12500.42

# Or fully headless via a configured provider:
PORTFOLIO_PROVIDER=robinhood python -m chasing_voo.auto
```

It records one snapshot for today (VOO close fetched automatically) and exits
0 on success, so it drops straight into any scheduler.

### Recommended: official Robinhood MCP (OAuth, no stored password)

Robinhood publishes an official, OAuth-based MCP server. An agent reads your
equity over OAuth and passes the number to the updater — **no password is ever
stored in this project**.

```bash
# One-time setup:
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
# then authenticate once:  /mcp  ->  robinhood-trading  ->  authenticate
```

To run it unattended, schedule a headless agent call daily (e.g. via cron or a
scheduled Claude run) that fetches equity from the `robinhood-trading` MCP and
pipes it into the updater:

```bash
claude -p "Read my total portfolio equity from the robinhood-trading MCP, then \
run: python -m chasing_voo.auto --equity <that number>"
```

The OAuth token is cached and refreshed, so after the one-time authentication
this runs without prompts. If the token ever expires you re-authenticate once
with `/mcp`.

### Alternative: `robin_stocks` (fully headless, unofficial API)

No agent needed, but it stores credentials locally and uses an unofficial API
— see the security notes.

```bash
pip install -e '.[robinhood]'
cp .env.example .env               # fill in RH_* values (never commit .env)
# set PORTFOLIO_PROVIDER=robinhood in .env, then schedule:
python -m chasing_voo.auto
```

### Scheduling examples

```cron
# crontab -e — weekdays at 4:30pm ET, after market close (adjust for your TZ)
30 16 * * 1-5  cd /path/to/chasing-VOO && /path/to/python -m chasing_voo.auto --equity ...
```

On macOS a launchd agent works the same way. The updater is idempotent — one
row per day — so re-running is safe.

---

## ⚠️ Security notes (this repo is public — read this)

- **Never commit secrets.** `.env`, `*.sqlite3`, and `*.csv` are git-ignored.
  Only `.env.example` (placeholders) is tracked. Double-check `git status`
  before every commit.
- `robin_stocks` is an **unofficial** API. Automated logins can trip account
  security and may stop working if Robinhood changes things. Prefer manual
  entry or the official MCP path unless you understand the tradeoff.
- Credentials are read only from environment variables and are never printed,
  logged, or written to disk by this project.
- Your portfolio history is personal financial data. It stays in the local
  `data/` folder, which is git-ignored.

---

## Configuration

All config is via environment variables (optionally a local `.env`). See
[`.env.example`](.env.example).

| Variable | Default | Purpose |
|---|---|---|
| `BENCHMARK_TICKER` | `VOO` | Index to beat (e.g. `SPY`, `QQQ`, `VTI`). |
| `PORTFOLIO_PROVIDER` | `manual` | `manual` or `robinhood`. |
| `CHASING_VOO_DB` | `data/chasing_voo.sqlite3` | Local database path. |
| `RH_USERNAME` / `RH_PASSWORD` | — | Only for the `robinhood` provider. |
| `RH_MFA_CODE` / `RH_TOTP_SECRET` | — | MFA for the `robinhood` provider. |

---

## CLI reference

```
chasing-voo record --equity <amount> [--flow <deposits>] [--date YYYY-MM-DD]
chasing-voo fetch  [--flow <deposits>] [--date YYYY-MM-DD]   # uses configured provider
chasing-voo status                                            # headline summary
chasing-voo export [--out history.csv]                        # full metrics table
```

---

## Project layout

```
chasing_voo/
  config.py        # env-based configuration
  models.py        # Snapshot dataclass
  storage.py       # SQLite persistence (stdlib only)
  benchmark.py     # yfinance benchmark prices (public data)
  metrics.py       # returns, win rate, cumulative & relative performance
  cli.py           # command-line interface
  providers/       # pluggable portfolio-equity sources
dashboard/app.py   # local Streamlit dashboard
tests/             # pytest suite for metrics & storage
```

## Development

```bash
pip install -e '.[dev]'
pytest
```

## Disclaimer

For personal tracking and educational use only. Not financial advice. Market
data via Yahoo Finance (`yfinance`) is provided as-is.

## License

MIT — see [LICENSE](LICENSE).
