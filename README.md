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

# 2. Record today's portfolio value (read it from your brokerage app)
chasing-voo record --equity 12500.42

# ...on a day you deposited money, note it so returns stay honest:
chasing-voo record --equity 13600.00 --flow 1000

# 3. See where you stand
chasing-voo status

# 4. Open the visual dashboard
streamlit run dashboard/app.py
```

The dashboard has a sidebar form, so once it's open you can record days there
instead of the CLI.

---

## Getting your portfolio value in

You choose how much automation you want. **Manual is the default and the safest
— no credentials, nothing that can leak or break.**

### 1. Manual (default, recommended)

Read the number off your brokerage app and enter it via `chasing-voo record`
or the dashboard sidebar. Takes five seconds a day.

### 2. Official Robinhood MCP (automation, no stored password)

Robinhood publishes an official, OAuth-based MCP server. In a Claude Code
session you can add it and let the agent read your equity, then record it — no
password ever stored in this project:

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
# then in the CLI:  /mcp  -> select robinhood-trading -> authenticate
```

Ask the agent to fetch your portfolio equity and run
`chasing-voo record --equity <that value>`. This keeps auth inside Robinhood's
OAuth flow rather than in a config file.

### 3. `robin_stocks` auto-fetch (optional, advanced)

An unofficial API. Convenient but riskier — see the security notes below.

```bash
pip install -e '.[robinhood]'
cp .env.example .env          # then fill in RH_* values in .env (never commit it)
# set PORTFOLIO_PROVIDER=robinhood in .env
chasing-voo fetch
```

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
