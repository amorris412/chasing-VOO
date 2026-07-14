"""Configuration loading.

All configuration comes from environment variables (optionally loaded from a
local, git-ignored ``.env`` file). Nothing sensitive is ever hard-coded or
committed — see ``.env.example`` for the full list of keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Load a local .env if python-dotenv is installed. This is best-effort: the app
# works fine with real environment variables and never requires a .env file.
try:  # pragma: no cover - trivial import guard
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


# Repo root (two levels up from this file: chasing_voo/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parent.parent


def _default_db_path() -> Path:
    return REPO_ROOT / "data" / "chasing_voo.sqlite3"


@dataclass(frozen=True)
class Config:
    """Runtime configuration for chasing-VOO."""

    # Ticker used as the "index" you're trying to beat. Defaults to VOO
    # (Vanguard S&P 500 ETF) to match the project's name; override with
    # BENCHMARK_TICKER (e.g. SPY, QQQ, VTI).
    benchmark_ticker: str = "VOO"

    # Where the local SQLite database lives.
    db_path: Path = None  # type: ignore[assignment]

    # Which provider supplies your portfolio equity: "manual" (default, always
    # safe) or "robinhood" (optional, requires local credentials in .env).
    provider: str = "manual"

    @classmethod
    def load(cls) -> "Config":
        db_env = os.getenv("CHASING_VOO_DB")
        db_path = Path(db_env).expanduser() if db_env else _default_db_path()
        return cls(
            benchmark_ticker=os.getenv("BENCHMARK_TICKER", "VOO").upper().strip(),
            db_path=db_path,
            provider=os.getenv("PORTFOLIO_PROVIDER", "manual").lower().strip(),
        )
