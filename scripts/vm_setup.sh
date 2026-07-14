#!/usr/bin/env bash
#
# vm_setup.sh — bootstrap a fresh Ubuntu (22.04/24.04) VM for chasing-VOO.
#
# Installs system dependencies, the Claude Code CLI, clones the repo, and
# installs the app into a virtualenv. Run once on a new personal VM:
#
#   curl -fsSL https://raw.githubusercontent.com/amorris412/chasing-VOO/main/scripts/vm_setup.sh | bash
#   # (or clone the repo first and run: bash scripts/vm_setup.sh)
#
# Afterwards, authenticate and schedule per docs/CLOUD_VM.md.
#
set -euo pipefail

echo "[1/5] System packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git curl ca-certificates

echo "[2/5] Node.js (for the Claude Code CLI)..."
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

echo "[3/5] Claude Code CLI..."
sudo npm install -g @anthropic-ai/claude-code || true

echo "[4/5] Clone + install chasing-VOO..."
cd "$HOME"
[ -d chasing-VOO ] || git clone https://github.com/amorris412/chasing-VOO
cd chasing-VOO
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e '.[dashboard,robinhood]'

echo "[5/5] Done. Repo at: $HOME/chasing-VOO"
cat <<'NOTE'

Next — pick ONE authentication method (see docs/CLOUD_VM.md):
  A) Official Robinhood MCP  — no stored password; one-time browser step via SSH
     port-forward. Most secure + reliable.
  B) robin_stocks            — fully headless; stores credentials in a chmod-600
     .env on this VM. Simplest, but an unofficial API.

Then install the systemd timer (steps in docs/CLOUD_VM.md).
NOTE
