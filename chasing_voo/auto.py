"""Automated daily updater — the entrypoint for hands-off, no-manual-entry use.

Records one day with **no interactive input**. Portfolio equity comes from
``--equity`` / ``CHASING_VOO_EQUITY`` (how the Robinhood connector feeds it — no
stored credentials) or the configured provider. Benchmark prices come from
``--benchmark TICKER=PRICE`` (repeatable) / ``CHASING_VOO_BENCHMARKS`` when
supplied by the same connector, otherwise from Yahoo Finance.

Examples::

    # Connector-supplied equity + index prices (no external market-data call)
    python -m chasing_voo.auto --equity 207851.45 \
        --benchmark VOO=689.62 --benchmark DIA=523.27 --benchmark QQQ=718.42

    # Fully headless via a configured provider + Yahoo for benchmarks
    PORTFOLIO_PROVIDER=robinhood python -m chasing_voo.auto
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from typing import Dict, List, Optional

from .config import Config
from .models import Snapshot
from .providers import get_provider
from .storage import Storage


def _resolve_equity(cfg: Config, explicit: Optional[float]) -> float:
    if explicit is not None:
        return float(explicit)
    env_value = os.getenv("CHASING_VOO_EQUITY")
    if env_value:
        return float(env_value)
    provider = get_provider(cfg.provider)
    if provider.name == "manual":
        raise RuntimeError(
            "No equity value supplied and provider is 'manual'. Pass --equity "
            "(or set CHASING_VOO_EQUITY), or set PORTFOLIO_PROVIDER."
        )
    return float(provider.get_equity())


def _parse_pairs(pairs: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Bad --benchmark value {item!r}; expected TICKER=PRICE.")
        ticker, price = item.split("=", 1)
        out[ticker.strip().upper()] = float(price)
    return out


def _resolve_benchmarks(cfg: Config, args: argparse.Namespace, day: date) -> Dict[str, float]:
    """Determine {ticker: close} from CLI args, env, or a Yahoo fetch."""
    benchmarks: Dict[str, float] = {}
    if args.benchmark:
        benchmarks.update(_parse_pairs(args.benchmark))
    env_b = os.getenv("CHASING_VOO_BENCHMARKS")
    if env_b:
        benchmarks.update(_parse_pairs([p for p in env_b.split(",") if p.strip()]))
    if args.benchmark_close is not None:
        benchmarks.setdefault(cfg.primary_ticker, float(args.benchmark_close))

    # Any configured ticker still missing a price is fetched from Yahoo.
    missing = [t for t in cfg.tickers if t not in benchmarks]
    if missing:
        from .benchmark import close_on, latest_close

        for t in missing:
            close = close_on(t, day)
            benchmarks[t] = close if close is not None else latest_close(t)
    return benchmarks


def run(
    cfg: Config,
    equity: Optional[float],
    flow: float,
    day: date,
    args: argparse.Namespace,
) -> tuple:
    resolved = _resolve_equity(cfg, equity)
    benchmarks = _resolve_benchmarks(cfg, args, day)
    with Storage(cfg.db_path) as store:
        store.record_day(day, resolved, benchmarks, net_flow=flow)
    return resolved, benchmarks


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chasing-voo-auto",
        description="Record one daily snapshot with no manual interaction.",
    )
    parser.add_argument("--equity", type=float, default=None, help="Portfolio value in USD")
    parser.add_argument("--flow", type=float, default=0.0, help="Net deposits that day (USD)")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--benchmark",
        action="append",
        default=[],
        metavar="TICKER=PRICE",
        help="Benchmark close, e.g. VOO=689.62 (repeatable).",
    )
    parser.add_argument(
        "--benchmark-close",
        type=float,
        default=None,
        help="Shorthand for the primary benchmark's price.",
    )
    args = parser.parse_args(argv)

    cfg = Config.load()
    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    try:
        equity, benchmarks = run(cfg, args.equity, float(args.flow), day, args)
    except Exception as exc:
        print(f"chasing-voo auto: FAILED — {exc}", file=sys.stderr)
        return 1
    bench_str = " ".join(f"{t}=${p:,.2f}" for t, p in benchmarks.items())
    print(f"chasing-voo auto: recorded {day} — equity=${equity:,.2f} | {bench_str}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
