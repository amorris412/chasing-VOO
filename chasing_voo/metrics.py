"""Performance metrics: returns, win rate, cumulative & relative performance.

This is the heart of chasing-VOO. Given a series of daily snapshots it answers:

* How did I do today vs the index?
* What fraction of days do I beat the index (my "win rate")?
* What's my cumulative return since day one, vs the index?
* Am I ahead of or behind the index overall?

A key correctness detail the naive approach misses: **deposits are not
performance**. If you wire $1,000 into the account, your equity jumps but you
didn't "return" anything. We strip external cash flows out of the daily return
using a simple flow-adjusted formula::

    daily_return_t = (equity_t - net_flow_t) / equity_{t-1} - 1

so a day where you only deposited cash shows ~0% return, not a huge fake gain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

from .models import Snapshot


def to_frame(snapshots: Sequence[Snapshot]) -> pd.DataFrame:
    """Turn snapshots into a tidy, chronologically-sorted DataFrame with metrics.

    Returned columns:
        equity, benchmark_close, net_flow,
        port_daily_ret, bench_daily_ret, beat, beat_cumrate,
        port_cum_ret, bench_cum_ret, excess_cum_ret
    """
    if not snapshots:
        return pd.DataFrame(
            columns=[
                "equity",
                "benchmark_close",
                "net_flow",
                "port_daily_ret",
                "bench_daily_ret",
                "beat",
                "beat_cumrate",
                "port_cum_ret",
                "bench_cum_ret",
                "excess_cum_ret",
            ]
        )

    df = pd.DataFrame(
        {
            "day": [s.day for s in snapshots],
            "equity": [s.equity for s in snapshots],
            "benchmark_close": [s.benchmark_close for s in snapshots],
            "net_flow": [s.net_flow for s in snapshots],
        }
    )
    df = df.sort_values("day").set_index("day")

    prev_equity = df["equity"].shift(1)
    # Flow-adjusted daily portfolio return (deposits/withdrawals removed).
    df["port_daily_ret"] = (df["equity"] - df["net_flow"]) / prev_equity - 1
    df["bench_daily_ret"] = df["benchmark_close"].pct_change()

    # "Beat" the index on days where both daily returns are defined.
    both_defined = df["port_daily_ret"].notna() & df["bench_daily_ret"].notna()
    df["beat"] = (df["port_daily_ret"] > df["bench_daily_ret"]).where(both_defined)

    # Running win rate over comparable days.
    beats = df["beat"].fillna(False).astype(int)
    comparable = both_defined.astype(int)
    df["beat_cumrate"] = beats.cumsum() / comparable.cumsum().replace(0, np.nan)

    # Cumulative portfolio return, compounding flow-adjusted daily returns so
    # deposits don't inflate the curve. Starts at 0 on day one.
    growth = (1 + df["port_daily_ret"].fillna(0)).cumprod()
    df["port_cum_ret"] = growth - 1

    baseline_bench = df["benchmark_close"].iloc[0]
    df["bench_cum_ret"] = df["benchmark_close"] / baseline_bench - 1

    df["excess_cum_ret"] = df["port_cum_ret"] - df["bench_cum_ret"]
    return df


@dataclass(frozen=True)
class Summary:
    """Headline numbers for display."""

    days_tracked: int
    comparable_days: int
    latest_day: Optional[str]

    port_daily_ret: Optional[float]
    bench_daily_ret: Optional[float]
    beat_today: Optional[bool]

    win_rate: Optional[float]
    port_cum_ret: Optional[float]
    bench_cum_ret: Optional[float]
    excess_cum_ret: Optional[float]

    latest_equity: Optional[float]


def summarize(snapshots: Sequence[Snapshot]) -> Summary:
    """Compute the headline summary from a series of snapshots."""
    df = to_frame(snapshots)
    if df.empty:
        return Summary(
            days_tracked=0,
            comparable_days=0,
            latest_day=None,
            port_daily_ret=None,
            bench_daily_ret=None,
            beat_today=None,
            win_rate=None,
            port_cum_ret=None,
            bench_cum_ret=None,
            excess_cum_ret=None,
            latest_equity=None,
        )

    last = df.iloc[-1]
    comparable_days = int(df["beat"].notna().sum())
    win_rate = float(df["beat_cumrate"].iloc[-1]) if comparable_days else None
    beat_today = bool(last["beat"]) if pd.notna(last["beat"]) else None

    return Summary(
        days_tracked=int(len(df)),
        comparable_days=comparable_days,
        latest_day=str(df.index[-1]),
        port_daily_ret=_opt(last["port_daily_ret"]),
        bench_daily_ret=_opt(last["bench_daily_ret"]),
        beat_today=beat_today,
        win_rate=win_rate,
        port_cum_ret=_opt(last["port_cum_ret"]),
        bench_cum_ret=_opt(last["bench_cum_ret"]),
        excess_cum_ret=_opt(last["excess_cum_ret"]),
        latest_equity=_opt(last["equity"]),
    )


def _opt(value) -> Optional[float]:
    return float(value) if pd.notna(value) else None
