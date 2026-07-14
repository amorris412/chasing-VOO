"""Command-line interface for chasing-VOO.

Examples::

    # Record today's equity (manual entry) — benchmark close fetched for you
    chasing-voo record --equity 12500.42

    # Record a deposit day so the return math stays honest
    chasing-voo record --equity 13600.00 --flow 1000

    # Auto-fetch equity from Robinhood (optional provider)
    chasing-voo fetch

    # Show the headline summary
    chasing-voo status

    # Export the full metrics table to CSV
    chasing-voo export --out history.csv
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Optional

from . import __version__
from .benchmark import close_on, latest_close
from .config import Config
from .metrics import summarize, to_frame
from .models import Snapshot
from .providers import get_provider
from .storage import Storage


def _parse_day(value: Optional[str]) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _benchmark_close_for(cfg: Config, day: date) -> float:
    """Get the benchmark close for a day, falling back to the latest price."""
    close = close_on(cfg.benchmark_ticker, day)
    if close is None:
        # Market closed that day (weekend/holiday) — use most recent close.
        close = latest_close(cfg.benchmark_ticker)
    return close


def cmd_record(cfg: Config, args: argparse.Namespace) -> int:
    day = _parse_day(args.date)
    close = _benchmark_close_for(cfg, day)
    snap = Snapshot(
        day=day,
        equity=float(args.equity),
        benchmark_close=close,
        net_flow=float(args.flow),
    )
    with Storage(cfg.db_path) as store:
        store.upsert(snap)
    print(
        f"Recorded {day}: equity=${snap.equity:,.2f} "
        f"{cfg.benchmark_ticker}=${snap.benchmark_close:,.2f}"
        + (f" flow=${snap.net_flow:,.2f}" if snap.net_flow else "")
    )
    return 0


def cmd_fetch(cfg: Config, args: argparse.Namespace) -> int:
    day = _parse_day(args.date)
    provider = get_provider(cfg.provider)
    if provider.name == "manual":
        print(
            "Provider is 'manual' — nothing to auto-fetch. Use "
            "`chasing-voo record --equity <amount>`, or set PORTFOLIO_PROVIDER."
        )
        return 1
    equity = provider.get_equity()
    close = _benchmark_close_for(cfg, day)
    snap = Snapshot(
        day=day, equity=equity, benchmark_close=close, net_flow=float(args.flow)
    )
    with Storage(cfg.db_path) as store:
        store.upsert(snap)
    print(
        f"Fetched via {provider.name} — {day}: equity=${equity:,.2f} "
        f"{cfg.benchmark_ticker}=${close:,.2f}"
    )
    return 0


def cmd_status(cfg: Config, args: argparse.Namespace) -> int:
    with Storage(cfg.db_path) as store:
        snaps = store.all()
    s = summarize(snaps)
    if s.days_tracked == 0:
        print("No data yet. Record your first day with `chasing-voo record`.")
        return 0

    print(f"chasing-VOO — benchmark {cfg.benchmark_ticker}")
    print("=" * 40)
    print(f"Days tracked      : {s.days_tracked}  ({s.comparable_days} comparable)")
    print(f"Latest day        : {s.latest_day}")
    if s.latest_equity is not None:
        print(f"Portfolio value   : ${s.latest_equity:,.2f}")
    print("-" * 40)
    print(f"Today  you        : {_pct(s.port_daily_ret)}")
    print(f"Today  {cfg.benchmark_ticker:<10}: {_pct(s.bench_daily_ret)}")
    if s.beat_today is not None:
        print(f"Beat today?       : {'YES ✅' if s.beat_today else 'no ❌'}")
    print("-" * 40)
    print(f"Win rate          : {_pct(s.win_rate)} of comparable days")
    print(f"Cumulative you    : {_pct(s.port_cum_ret)}")
    print(f"Cumulative {cfg.benchmark_ticker:<6}: {_pct(s.bench_cum_ret)}")
    verdict = "AHEAD 🎉" if (s.excess_cum_ret or 0) >= 0 else "behind"
    print(f"vs index          : {_pct(s.excess_cum_ret)}  ({verdict})")
    return 0


def cmd_export(cfg: Config, args: argparse.Namespace) -> int:
    with Storage(cfg.db_path) as store:
        snaps = store.all()
    df = to_frame(snaps)
    if args.out:
        df.to_csv(args.out)
        print(f"Wrote {len(df)} rows to {args.out}")
    else:
        print(df.to_csv())
    return 0


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.2f}%"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chasing-voo",
        description="Track whether your portfolio is beating the index.",
    )
    parser.add_argument("--version", action="version", version=f"chasing-voo {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_record = sub.add_parser("record", help="Record a day's equity (manual entry)")
    p_record.add_argument("--equity", type=float, required=True, help="Portfolio value in USD")
    p_record.add_argument("--flow", type=float, default=0.0, help="Net deposits that day (USD)")
    p_record.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    p_record.set_defaults(func=cmd_record)

    p_fetch = sub.add_parser("fetch", help="Auto-fetch equity from the configured provider")
    p_fetch.add_argument("--flow", type=float, default=0.0, help="Net deposits that day (USD)")
    p_fetch.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    p_fetch.set_defaults(func=cmd_fetch)

    p_status = sub.add_parser("status", help="Show the headline summary")
    p_status.set_defaults(func=cmd_status)

    p_export = sub.add_parser("export", help="Export the full metrics table to CSV")
    p_export.add_argument("--out", help="Output CSV path (default: stdout)")
    p_export.set_defaults(func=cmd_export)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = Config.load()
    try:
        return args.func(cfg, args)
    except Exception as exc:  # surface a clean message, not a traceback
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
