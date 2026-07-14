"""Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PortfolioProvider(ABC):
    """Supplies the current total value (equity) of your portfolio in USD."""

    #: Human-readable name, used in CLI output.
    name: str = "provider"

    @abstractmethod
    def get_equity(self) -> float:
        """Return current total portfolio equity in USD."""
        raise NotImplementedError
