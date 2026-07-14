"""Portfolio equity providers.

A provider's only job is to answer one question: *what is my portfolio worth
right now?* Everything else (benchmark prices, storage, metrics) is provider-
independent, so adding a new brokerage is just a new small class here.
"""

from __future__ import annotations

from .base import PortfolioProvider
from .manual import ManualProvider


def get_provider(name: str) -> PortfolioProvider:
    """Return a provider instance by name.

    Supported:
        "manual"    -> ManualProvider (default; you supply the number)
        "robinhood" -> RobinhoodProvider (optional; needs local credentials)
    """
    name = (name or "manual").lower().strip()
    if name == "manual":
        return ManualProvider()
    if name == "robinhood":
        # Imported lazily so the optional robin_stocks dependency is only
        # required when this provider is actually selected.
        from .robinhood import RobinhoodProvider

        return RobinhoodProvider()
    raise ValueError(
        f"Unknown provider {name!r}. Use 'manual' or 'robinhood'."
    )


__all__ = ["PortfolioProvider", "ManualProvider", "get_provider"]
