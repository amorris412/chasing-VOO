"""Core data types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Snapshot:
    """A single daily portfolio observation.

    Attributes:
        day: The calendar date of the observation.
        equity: Total portfolio value (cash + positions) at close, in USD.
        net_flow: Net external cash moved *into* the account that day (deposits
            positive, withdrawals negative). Stripped out of returns so the
            comparison against an index is fair — a deposit is not performance.
    """

    day: date
    equity: float
    net_flow: float = 0.0


@dataclass(frozen=True)
class BenchmarkClose:
    """A benchmark index's closing price on a given day."""

    day: date
    ticker: str
    close: float
