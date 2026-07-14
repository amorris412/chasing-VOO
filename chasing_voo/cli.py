"""Command-line interface for chasing-VOO.

Examples::

    chasing-voo record --equity 12500.42 --benchmark VOO=689.62   # record a day
    chasing-voo status                                            # headline summary
    chasing-voo export --out history.csv                          # metrics table
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Optional

from . import __version__
from .config import Config
from .metrics import build_frame, window_view
from .storage import Storage


def _load_frame(cfg: Config):
    with Storage(cfg.db_path) as store:
        return build_frame(store.snapshots(), store.benchmark_closes())


def cmd_record(cfg: Config, args: argparse.Namespace) -> int:
    # Reuse the auto updater's benchmark resolution (args, env, or Yahoo).
    from . import auto

    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    equity, benchmarks = auto.run(cfg, args.equity, float(args.flow), day, args)
    bench_str = " ".join(f"{t}=${p:,.2f}" for t, p in benchmarks.items())
    print(f"Recorded {day}: equity=${equity:,.2f} | {bench_str}")
    return 0


def cmd_status(cfg: Config, args: argparse.Namespace) -> int:
    df = _load_frame(cfg)
    view = window_view(df, cfg.tickers)
    if view.days == 0:
        print("No data yet. Record your first day with `chasing-voo record`.")
        return 0

    print(f"chasing-VOO — {view.latest_day}")
    print("=" * 46)
    if view.latest_equity is not None:
        print(f"Portfolio value : ${view.latest_equity:,.2f}")
    print(f"Days tracked    : {view.days}")
    print(f"You (cumulative): {_pct(view.port_cum_total)}"
          + (f"   today {_pct(view.port_daily_today)}" if view.port_daily_today is not None else ""))
    print("-" * 46)
    header = f"{'Index':<10}{'you cum':>10}{'idx cum':>10}{'vs idx':>10}{'win':>8}"
    print(header)
    for t in cfg.tickers:
        bv = view.benchmarks.get(t)
        if not bv:
            continue
        label = cfg.label(t)
        verdict = ""
        if bv.beat_today is not None:
            verdict = "  ✅ beat today" if bv.beat_today else "  ❌ trail today"
        print(
            f"{label:<10}{_pct(view.port_cum_total):>10}{_pct(bv.cum_total):>10}"
            f"{_pct(bv.excess):>10}{_pct(bv.win_rate):>10}{verdict}"
        )
    return 0


def cmd_export(cfg: Config, args: argparse.Namespace) -> int:
    df = _load_frame(cfg)
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

    p_record = sub.add_parser("record", help="Record a day (benchmarks via --benchmark or Yahoo)")
    p_record.add_argument("--equity", type=float, required=True, help="Portfolio value in USD")
    p_record.add_argument("--flow", type=float, default=0.0, help="Net deposits that day (USD)")
    p_record.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    p_record.add_argument("--benchmark", action="append", default=[], metavar="TICKER=PRICE",
                          help="Benchmark close, e.g. VOO=689.62 (repeatable)")
    p_record.add_argument("--benchmark-close", type=float, default=None,
                          help="Shorthand for the primary benchmark's price")
    p_record.set_defaults(func=cmd_record)

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
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
