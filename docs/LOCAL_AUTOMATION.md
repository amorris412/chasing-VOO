# Local automation (recommended)

Fully hands-off tracking that runs on **your machine**, with **no stored
password** and **no financial data ever leaving your computer**.

## Why local

The official Robinhood connection is OAuth-based and tied to an interactive
Claude session — it works great when Claude fetches your data during a chat, but
a *scheduled cloud* job can't hold that session. Running the daily job locally
solves this: the OAuth token lives on your machine (authenticated once in a real
browser) and a headless Claude run reuses it every day.

```
  cron / launchd  ──daily──▶  scripts/local_daily.sh
                                   │  headless `claude -p`
                                   ▼
                          robinhood-trading MCP (OAuth)
                                   │  equity + VOO/DIA/QQQ closes
                                   ▼
                          python -m chasing_voo.auto   ──▶  data/chasing_voo.sqlite3
                                                              (local, git-ignored)
                                   ▼
                          streamlit run dashboard/app.py
```

## One-time setup

```bash
# 1. Clone the code and install
git clone https://github.com/amorris412/chasing-VOO && cd chasing-VOO
pip install -e '.[dashboard]'

# 2. Install the Claude Code CLI (https://claude.com/claude-code) and sign in.

# 3. Add + authenticate the Robinhood MCP — a browser opens for the OAuth login:
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
claude          # then, in the prompt:  /mcp  ->  robinhood-trading  ->  authenticate

# 4. Test the daily runner once by hand:
bash scripts/local_daily.sh
```

That last command should read your portfolio + the three index closes and print
a `chasing-voo status` summary. Your data is written to `data/chasing_voo.sqlite3`
(git-ignored — it never gets committed).

## Schedule it

Pick a time shortly after the US market close (4:00pm ET), in **your** timezone.

### macOS / Linux (cron)

```cron
# crontab -e — 4:15pm on weekdays (adjust the hour for your timezone)
15 16 * * 1-5  cd /full/path/to/chasing-VOO && /bin/bash scripts/local_daily.sh >> /tmp/chasing-voo.log 2>&1
```

### macOS (launchd, survives sleep better)

Create `~/Library/LaunchAgents/com.chasingvoo.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.chasingvoo.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/full/path/to/chasing-VOO/scripts/local_daily.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer><key>Weekday</key><integer>1</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer><key>Weekday</key><integer>2</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer><key>Weekday</key><integer>3</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer><key>Weekday</key><integer>4</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer><key>Weekday</key><integer>5</integer></dict>
  </array>
  <key>WorkingDirectory</key><string>/full/path/to/chasing-VOO</string>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.chasingvoo.daily.plist
```

## View the dashboard

```bash
streamlit run dashboard/app.py
```

It reads the same local `data/` database the runner writes to.

## Deposits / withdrawals

Robinhood's connection exposes no transfer history, so the runner records
`net_flow = 0`. On any day you move money in or out, record that day yourself so
returns stay honest:

```bash
python -m chasing_voo.auto --equity <value> --flow <net deposits> \
  --benchmark VOO=<p> --benchmark DIA=<p> --benchmark QQQ=<p>
```

## If the OAuth token expires

Re-authenticate once — `claude` → `/mcp` → `robinhood-trading` → authenticate —
and the daily job resumes. No other change needed.

## Alternative: no Claude Code (headless `robin_stocks`)

If you'd rather not depend on the Claude CLI, the `robinhood` provider fetches
headlessly via the unofficial `robin_stocks` API — but it stores your
credentials locally in `.env`. See the main README's security notes before
choosing this.

```bash
pip install -e '.[robinhood]'
cp .env.example .env      # fill in RH_* (never commit .env)
# set PORTFOLIO_PROVIDER=robinhood, then schedule:
python -m chasing_voo.auto
```

## Optional: back up your data

Local automation keeps everything on your machine. If you want an off-machine
backup or to view from a second computer, you can still push `data/` to your
private `chasing-VOO-data` repo — but it's entirely optional.
