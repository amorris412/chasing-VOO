# Personal cloud VM setup

Run the daily update on a small always-on Linux box you own — off any employer
device, on 24/7, fully under your control.

## 1. Get a free-tier VM

Any of these give you an always-free (or near-free) Linux VM. A daily cron job
needs almost nothing, so the smallest shape is fine.

| Provider | Free shape | Notes |
|---|---|---|
| **Oracle Cloud** | Always Free (Ampere A1 or E2 Micro) | Most generous; truly always free. ARM Ampere availability varies by region. |
| **Google Cloud** | `e2-micro` in us-west1/central1/east1 | Reliable always-free; needs a billing account. |
| **AWS** | `t2.micro` (12 months) | Free for the first year only. |

Pick **Ubuntu 22.04 or 24.04 LTS**, add your SSH public key, and launch. You
only need **outbound** internet (the defaults are fine) — no inbound ports.

> Security: this VM will hold a Robinhood credential. Keep it patched, use SSH
> keys (not passwords), and don't open inbound ports you don't need.

## 2. Bootstrap the box

SSH in, then:

```bash
curl -fsSL https://raw.githubusercontent.com/amorris412/chasing-VOO/main/scripts/vm_setup.sh | bash
```

This installs Python, the Claude Code CLI, clones the repo to `~/chasing-VOO`,
and installs the app into a virtualenv. Your data will live in
`~/chasing-VOO/data/` (git-ignored — it never leaves the box).

## 3. Authenticate — pick ONE method

A VM has no browser, and the Robinhood login is OAuth. Two ways to handle that:

### Method A — Official Robinhood MCP (no stored password) ✅ recommended

Reliable official API, nothing but an OAuth token on disk (revocable from
Robinhood). The one-time login uses your existing browser via an SSH tunnel.

```bash
# 1. Sign the VM's Claude Code into your account (headless-friendly token):
#    run this on ANY machine with a browser, then paste the token onto the VM.
claude setup-token
#    -> export it on the VM:  export CLAUDE_CODE_OAUTH_TOKEN=<token>
#       (add that line to ~/.bashrc so cron/systemd see it)

# 2. Add the Robinhood MCP on the VM:
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading

# 3. Authenticate it. Claude prints an OAuth URL whose redirect is
#    http://localhost:<PORT>/... . From YOUR machine, reconnect with that port
#    forwarded so the browser callback reaches the VM:
#        ssh -L <PORT>:localhost:<PORT> user@your-vm
#    then on the VM run `claude`, do:  /mcp -> robinhood-trading -> authenticate,
#    open the printed URL in your local browser, finish the Robinhood login.
```

Leave `PORTFOLIO_PROVIDER` unset (default). The daily job then runs
`scripts/local_daily.sh` (headless `claude -p` → MCP).

> If the SSH port-forward step is more than you want to deal with, use Method B.

### Method B — robin_stocks (fully headless) 

No browser at all, but it stores your credentials on the VM and uses Robinhood's
*unofficial* API (which can change or trip account-security checks).

```bash
cd ~/chasing-VOO
cp .env.example .env
chmod 600 .env
# Edit .env:
#   PORTFOLIO_PROVIDER=robinhood
#   RH_USERNAME=you@example.com
#   RH_PASSWORD=...
#   RH_TOTP_SECRET=...        # your authenticator secret, so MFA is automatic
```

The daily job then runs `python -m chasing_voo.auto` (robin_stocks for equity,
Yahoo Finance for the index closes).

## 4. Schedule it

### systemd timer (recommended on a VM — survives reboots)

```bash
mkdir -p ~/.config/systemd/user
cp ~/chasing-VOO/scripts/systemd/chasing-voo.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now chasing-voo.timer
# Let it run even when you're not logged in:
sudo loginctl enable-linger "$USER"
# Check it:
systemctl --user list-timers | grep chasing
```

### …or plain cron

```cron
# crontab -e — 4:15pm New York time; set the box's TZ or convert to UTC.
15 16 * * 1-5  cd $HOME/chasing-VOO && /bin/bash scripts/vm_daily.sh >> /tmp/chasing-voo.log 2>&1
```

Run once by hand first to confirm: `bash ~/chasing-VOO/scripts/vm_daily.sh`.

## 5. See the dashboard

The dashboard is optional and can run anywhere that has the data. Two options:

- **On the VM**, reachable via SSH tunnel (no public port):
  ```bash
  # on the VM:
  streamlit run dashboard/app.py --server.address 127.0.0.1
  # from your machine:
  ssh -L 8501:localhost:8501 user@your-vm    # then open http://localhost:8501
  ```
- **Back up `data/`** to your private `chasing-VOO-data` repo and view it from
  wherever you like (optional).

## Deposits / withdrawals

Neither method auto-detects transfers. On a day you move money, record it:

```bash
python -m chasing_voo.auto --equity <value> --flow <net deposits> \
  --benchmark VOO=<p> --benchmark DIA=<p> --benchmark QQQ=<p>
```

## Troubleshooting

- **Timer never fires when logged out** → `sudo loginctl enable-linger "$USER"`.
- **Method A cron can't find the token** → ensure `CLAUDE_CODE_OAUTH_TOKEN` is
  exported in the environment the timer/cron runs in (systemd: add it to the
  unit's `Environment=` or the `.env` EnvironmentFile).
- **Method A token expired** → re-run the `/mcp` authenticate step (SSH tunnel).
- **Method B login fails** → Robinhood likely wants device verification; set
  `RH_TOTP_SECRET` so MFA is automatic, and confirm the login from the app once.
