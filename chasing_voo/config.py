"""Configuration loading.

All configuration comes from environment variables (optionally loaded from a
local, git-ignored ``.env`` file). Nothing sensitive is ever hard-coded or
committed — see ``.env.example`` for the full list of keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

# Load a local .env if python-dotenv is installed. This is best-effort: the app
# works fine with real environment variables and never requires a .env file.
try:  # pragma: no cover - trivial import guard
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


# Repo root (two levels up from this file: chasing_voo/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parent.parent

# The indices you can compare against, as (ticker, display label). ETFs are used
# as liquid proxies: VOO≈S&P 500, DIA≈Dow, QQQ≈Nasdaq-100. The first entry is the
# "primary" benchmark (the project is named after VOO). Override the set with the
# BENCHMARK_TICKERS env var (comma-separated tickers).
DEFAULT_BENCHMARKS: List[Tuple[str, str]] = [
    ("VOO", "S&P 500"),
    ("DIA", "Dow"),
    ("QQQ", "Nasdaq"),
]

_LABELS: Dict[str, str] = {t: label for t, label in DEFAULT_BENCHMARKS}


def _default_db_path() -> Path:
    return REPO_ROOT / "data" / "chasing_voo.sqlite3"


def _load_benchmarks() -> List[Tuple[str, str]]:
    raw = os.getenv("BENCHMARK_TICKERS")
    if not raw:
        return list(DEFAULT_BENCHMARKS)
    out: List[Tuple[str, str]] = []
    for tok in raw.split(","):
        ticker = tok.strip().upper()
        if ticker:
            out.append((ticker, _LABELS.get(ticker, ticker)))
    return out or list(DEFAULT_BENCHMARKS)


@dataclass(frozen=True)
class Config:
    """Runtime configuration for chasing-VOO."""

    benchmarks: List[Tuple[str, str]] = field(default_factory=lambda: list(DEFAULT_BENCHMARKS))
    db_path: Path = None  # type: ignore[assignment]
    provider: str = "manual"

    @property
    def tickers(self) -> List[str]:
        return [t for t, _ in self.benchmarks]

    @property
    def primary_ticker(self) -> str:
        return self.benchmarks[0][0] if self.benchmarks else "VOO"

    def label(self, ticker: str) -> str:
        return _LABELS.get(ticker, ticker)

    @classmethod
    def load(cls) -> "Config":
        db_env = os.getenv("CHASING_VOO_DB")
        db_path = Path(db_env).expanduser() if db_env else _default_db_path()
        return cls(
            benchmarks=_load_benchmarks(),
            db_path=db_path,
            provider=os.getenv("PORTFOLIO_PROVIDER", "manual").lower().strip(),
        )
