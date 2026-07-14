# 📈 chasing-VOO

*Are you actually beating the index?*

A small, local, privacy-first tool that tracks your portfolio against the major
market indices — **S&P 500 (VOO)**, **Dow (DIA)**, and **Nasdaq (QQQ)** — and
answers the only question that matters for a stock-picker: **am I beating the
market, and how often?**

It records a daily snapshot of your portfolio value, pulls each index's close,
and computes, for any date range:

- **Daily result** — did you beat each index today?
- **Win rate** — the share of days you out-return each index.
- **Cumulative return** — you vs each index over the selected window.
- **Lead / lag** — how far ahead of (or behind) each index you are.

The dashboard lets you **toggle which indices** to compare against and pick a
**date range** (last 7 / 30 / 90 days, all time, or custom). Everything runs on
your machine; your financial history lives in a local SQLite file that is
**never** committed or sent anywhere.

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

The daily updater is a single, non-interactive entrypoint that records one
idempotent snapshot and exits 0, so it drops into any scheduler:

```bash
python -m chasing_voo.auto --equity 12500.42 \
  --benchmark VOO=689.62 --benchmark DIA=523.27 --benchmark QQQ=718.42
```

### Recommended: local, via the Robinhood MCP (OAuth, no stored password)

Run it on **your machine** with a headless Claude Code call that reads your
equity + index closes from the official Robinhood MCP — **no password stored,
and your data never leaves your computer**. This is the reliable hands-off path
(a *cloud* schedule can't hold the OAuth session; a local one can).

```bash
# one-time
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
claude          # then:  /mcp -> robinhood-trading -> authenticate
# test it
bash scripts/local_daily.sh
```

Then schedule `scripts/local_daily.sh` with cron or launchd. **Full setup,
scheduling, and troubleshooting: [`docs/LOCAL_AUTOMATION.md`](docs/LOCAL_AUTOMATION.md).**

**Prefer an always-on box instead of your laptop?** Run it on a small personal
free-tier cloud VM (recommended if you rarely have a personal machine on) —
step-by-step provisioning, headless authentication, and a systemd timer are in
[`docs/CLOUD_VM.md`](docs/CLOUD_VM.md).

### Alternative: `robin_stocks` (fully headless, unofficial API)

No Claude CLI needed, but it stores credentials locally and uses an unofficial
API — see the security notes.

```bash
pip install -e '.[robinhood]'
cp .env.example .env               # fill in RH_* values (never commit .env)
# set PORTFOLIO_PROVIDER=robinhood in .env, then schedule:
python -m chasing_voo.auto
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
| `BENCHMARK_TICKERS` | `VOO,DIA,QQQ` | Indices to compare against (comma-separated). |
| `PORTFOLIO_PROVIDER` | `manual` | `manual` or `robinhood`. |
| `CHASING_VOO_DB` | `data/chasing_voo.sqlite3` | Local database path. |
| `CHASING_VOO_EQUITY` | — | Portfolio value for a headless run (see Automation). |
| `CHASING_VOO_BENCHMARKS` | — | Index closes, e.g. `VOO=689.62,DIA=523.27,QQQ=718.42`. |
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
