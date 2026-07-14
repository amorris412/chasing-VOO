"""Fetch benchmark (index) prices from Yahoo Finance via yfinance.

Only public market data is fetched here — no credentials involved.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional

import pandas as pd


def latest_close(ticker: str) -> float:
    """Return the most recent available closing price for ``ticker``."""
    import yfinance as yf

    hist = yf.Ticker(ticker).history(period="5d")
    if hist.empty:
        raise RuntimeError(f"No price data returned for {ticker!r}.")
    return float(hist["Close"].iloc[-1])


def close_on(ticker: str, day: date) -> Optional[float]:
    """Return the closing price for ``ticker`` on a specific day, if it traded.

    Returns ``None`` for weekends/holidays where the market was closed.
    """
    import yfinance as yf

    start = day.isoformat()
    end = (pd.Timestamp(day) + pd.Timedelta(days=1)).date().isoformat()
    hist = yf.Ticker(ticker).history(start=start, end=end)
    if hist.empty:
        return None
    return float(hist["Close"].iloc[-1])


def close_history(ticker: str, start: date, end: date) -> Dict[date, float]:
    """Return a {date: close} map for ``ticker`` over [start, end] inclusive."""
    import yfinance as yf

    end_exclusive = (pd.Timestamp(end) + pd.Timedelta(days=1)).date()
    hist = yf.Ticker(ticker).history(
        start=start.isoformat(), end=end_exclusive.isoformat()
    )
    result: Dict[date, float] = {}
    for ts, row in hist.iterrows():
        result[ts.date()] = float(row["Close"])
    return result
