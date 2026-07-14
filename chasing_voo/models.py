"""Core data types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Snapshot:
    """A single daily observation.

    Attributes:
        day: The calendar date of the observation.
        equity: Total portfolio value (cash + positions) at close, in USD.
        benchmark_close: Closing price of the benchmark ticker on ``day``.
        net_flow: Net external cash moved *into* the account that day
            (deposits positive, withdrawals negative). Used to strip deposits
            out of the return calculation so the comparison against the index
            is fair — a deposit is not investment performance.
    """

    day: date
    equity: float
    benchmark_close: float
    net_flow: float = 0.0
