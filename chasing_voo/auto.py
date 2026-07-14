"""Automated daily updater — the entrypoint for hands-off, no-manual-entry use.

It records one snapshot for a day with **no interactive input**. The portfolio
equity comes from one of (in priority order):

1. ``--equity`` on the command line, or the ``CHASING_VOO_EQUITY`` env var.
   This is how the **Robinhood MCP** path feeds data in: an agent reads your
   equity over OAuth and passes the number here — no credentials stored.
2. Otherwise, the configured provider's ``get_equity()`` (e.g. the optional
   ``robinhood`` provider via ``robin_stocks``, for a fully headless cron).

The benchmark (VOO) close is always fetched automatically from public data.

Examples::

    # MCP / agent-supplied value (recommended: no stored credentials)
    python -m chasing_voo.auto --equity 12500.42

    # Fully headless via the configured provider
    PORTFOLIO_PROVIDER=robinhood python -m chasing_voo.auto

Exit code is 0 on success, non-zero on failure, so it plays well with cron,
launchd, CI, or a scheduled agent run.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from typing import Optional

from .benchmark import close_on, latest_close
from .config import Config
from .models import Snapshot
from .providers import get_provider
from .storage import Storage


def _resolve_equity(cfg: Config, explicit: Optional[float]) -> float:
    """Return the equity to record, from explicit value, env, or provider."""
    if explicit is not None:
        return float(explicit)
    env_value = os.getenv("CHASING_VOO_EQUITY")
    if env_value:
        return float(env_value)
    provider = get_provider(cfg.provider)
    if provider.name == "manual":
        raise RuntimeError(
            "No equity value supplied and provider is 'manual'. Pass --equity "
            "(or set CHASING_VOO_EQUITY), or set PORTFOLIO_PROVIDER to an "
            "automatic provider."
        )
    return float(provider.get_equity())


def _benchmark_close_for(cfg: Config, day: date) -> float:
    close = close_on(cfg.benchmark_ticker, day)
    return close if close is not None else latest_close(cfg.benchmark_ticker)


def run(cfg: Config, equity: Optional[float], flow: float, day: date) -> Snapshot:
    resolved = _resolve_equity(cfg, equity)
    close = _benchmark_close_for(cfg, day)
    snap = Snapshot(day=day, equity=resolved, benchmark_close=close, net_flow=flow)
    with Storage(cfg.db_path) as store:
        store.upsert(snap)
    return snap


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chasing-voo-auto",
        description="Record one daily snapshot with no manual interaction.",
    )
    parser.add_argument("--equity", type=float, default=None, help="Portfolio value in USD")
    parser.add_argument("--flow", type=float, default=0.0, help="Net deposits that day (USD)")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    args = parser.parse_args(argv)

    cfg = Config.load()
    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    try:
        snap = run(cfg, args.equity, float(args.flow), day)
    except Exception as exc:
        print(f"chasing-voo auto: FAILED — {exc}", file=sys.stderr)
        return 1
    print(
        f"chasing-voo auto: recorded {snap.day} — equity=${snap.equity:,.2f} "
        f"{cfg.benchmark_ticker}=${snap.benchmark_close:,.2f}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
