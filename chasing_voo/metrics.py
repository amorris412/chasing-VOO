"""Performance metrics: returns, win rate, cumulative & relative performance.

The heart of chasing-VOO. Given daily portfolio snapshots and one or more
benchmark price series it answers, for any date window:

* How did I do today vs each index?
* What fraction of days do I beat each index (my "win rate")?
* What's my cumulative return over the window, vs each index?
* Am I ahead of or behind each index?

Two correctness details the naive approach misses:

* **Deposits are not performance.** Daily return strips external cash flow:
  ``(equity_t - net_flow_t) / equity_{t-1} - 1``.
* **Windows are rebased.** "Last 30 days" starts each cumulative curve at 0 on
  the window's first day, so the comparison is about the window, not all time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence

import pandas as pd

from .models import BenchmarkClose, Snapshot


def build_frame(
    snapshots: Sequence[Snapshot],
    benchmark_closes: Sequence[BenchmarkClose],
) -> pd.DataFrame:
    """Full-history frame indexed by day.

    Columns: ``equity``, ``net_flow``, ``port_ret`` (flow-adjusted daily return),
    and for each ticker ``close__<T>`` and ``ret__<T>`` (daily return).
    """
    if not snapshots:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "day": [s.day for s in snapshots],
            "equity": [s.equity for s in snapshots],
            "net_flow": [s.net_flow for s in snapshots],
        }
    ).sort_values("day").set_index("day")

    if benchmark_closes:
        b = pd.DataFrame(
            {
                "day": [c.day for c in benchmark_closes],
                "ticker": [c.ticker for c in benchmark_closes],
                "close": [c.close for c in benchmark_closes],
            }
        )
        piv = b.pivot_table(index="day", columns="ticker", values="close", aggfunc="last")
        piv.columns = [f"close__{t}" for t in piv.columns]
        df = df.join(piv)

    df["port_ret"] = (df["equity"] - df["net_flow"]) / df["equity"].shift(1) - 1
    for col in [c for c in df.columns if c.startswith("close__")]:
        df[f"ret__{col[len('close__'):]}"] = df[col].pct_change()
    return df


def tickers_in(df: pd.DataFrame) -> List[str]:
    return [c[len("close__"):] for c in df.columns if c.startswith("close__")]


@dataclass(frozen=True)
class BenchmarkView:
    ticker: str
    cum: pd.Series          # rebased cumulative return over the window (fraction)
    cum_total: Optional[float]
    daily_today: Optional[float]
    win_rate: Optional[float]
    excess: Optional[float]  # portfolio cum minus this benchmark's cum
    beat_today: Optional[bool]
    comparable_days: int


@dataclass(frozen=True)
class WindowView:
    index: pd.Index          # the days in the window
    port_cum: pd.Series      # rebased cumulative portfolio return (fraction)
    port_cum_total: Optional[float]
    port_daily_today: Optional[float]
    latest_equity: Optional[float]
    days: int
    latest_day: Optional[str]
    benchmarks: Dict[str, BenchmarkView]


def _rebased_cum(returns: pd.Series) -> pd.Series:
    """Compound daily returns within a window, with the first row as baseline 0."""
    r = returns.copy()
    if len(r):
        r.iloc[0] = 0.0  # window start is the baseline
    return (1 + r.fillna(0)).cumprod() - 1


def window_view(
    df: pd.DataFrame,
    tickers: Sequence[str],
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> WindowView:
    """Compute all metrics for the selected tickers over [start, end]."""
    if df.empty:
        return WindowView(pd.Index([]), pd.Series(dtype=float), None, None, None, 0, None, {})

    w = df
    if start is not None:
        w = w[w.index >= start]
    if end is not None:
        w = w[w.index <= end]
    if w.empty:
        return WindowView(pd.Index([]), pd.Series(dtype=float), None, None, None, 0, None, {})

    port_cum = _rebased_cum(w["port_ret"])
    port_cum_total = float(port_cum.iloc[-1]) if len(port_cum) else None
    port_daily_today = _opt(w["port_ret"].iloc[-1]) if len(w) > 1 else None

    benchmarks: Dict[str, BenchmarkView] = {}
    for t in tickers:
        ret_col = f"ret__{t}"
        if ret_col not in w.columns:
            continue
        bench_cum = _rebased_cum(w[ret_col])
        cum_total = float(bench_cum.iloc[-1]) if len(bench_cum) else None

        # Comparable days: in-window rows (excluding the baseline first row)
        # where both the portfolio and this benchmark have a daily return.
        comparable = w["port_ret"].notna() & w[ret_col].notna()
        if len(comparable):
            comparable.iloc[0] = False
        beat = w["port_ret"] > w[ret_col]
        n_comparable = int(comparable.sum())
        win_rate = float(beat[comparable].mean()) if n_comparable else None
        beat_today = bool(beat.iloc[-1]) if len(w) and comparable.iloc[-1] else None
        excess = (
            port_cum_total - cum_total
            if port_cum_total is not None and cum_total is not None
            else None
        )
        benchmarks[t] = BenchmarkView(
            ticker=t,
            cum=bench_cum,
            cum_total=cum_total,
            daily_today=_opt(w[ret_col].iloc[-1]) if len(w) > 1 else None,
            win_rate=win_rate,
            excess=excess,
            beat_today=beat_today,
            comparable_days=n_comparable,
        )

    return WindowView(
        index=w.index,
        port_cum=port_cum,
        port_cum_total=port_cum_total,
        port_daily_today=port_daily_today,
        latest_equity=_opt(w["equity"].iloc[-1]),
        days=int(len(w)),
        latest_day=str(w.index[-1]),
        benchmarks=benchmarks,
    )


def _opt(value) -> Optional[float]:
    return float(value) if pd.notna(value) else None
