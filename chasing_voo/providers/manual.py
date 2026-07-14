"""Manual provider — you supply the equity value.

This is the default and the safest option: no credentials, no third-party API,
nothing that can break or leak. You read the number off your brokerage app and
type it in (via the CLI ``record`` command or the dashboard).
"""

from __future__ import annotations

from .base import PortfolioProvider


class ManualProvider(PortfolioProvider):
    name = "manual"

    def get_equity(self) -> float:
        # The manual provider never fetches on its own; callers pass the value
        # in directly (e.g. `chasing-voo record --equity 12345.67`).
        raise NotImplementedError(
            "ManualProvider has no automatic source. Provide the equity value "
            "explicitly, e.g. `chasing-voo record --equity <amount>`."
        )
