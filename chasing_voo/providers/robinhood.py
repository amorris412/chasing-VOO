"""Optional Robinhood provider via the unofficial ``robin_stocks`` library.

SECURITY / RISK NOTES — read before using:

* ``robin_stocks`` is an **unofficial** API. Robinhood can change or block it,
  and automated logins may trip account-security flags. Use at your own risk.
* Credentials are read **only** from environment variables (typically your
  local, git-ignored ``.env``). They are never printed, logged, or committed.
* This provider is imported lazily and ``robin_stocks`` is an *optional*
  dependency — install it with ``pip install -e '.[robinhood]'`` only if you
  choose this path.
* A safer alternative that needs no stored password is the official Robinhood
  MCP server (see the README): let an AI agent read your equity over OAuth and
  hand the number to ``chasing-voo record``.

Required environment variables:
    RH_USERNAME  — Robinhood login email
    RH_PASSWORD  — Robinhood password
    RH_MFA_CODE  — (optional) current TOTP code, if you handle MFA yourself
    RH_TOTP_SECRET — (optional) TOTP secret to auto-generate the MFA code
"""

from __future__ import annotations

import os

from .base import PortfolioProvider


class RobinhoodProvider(PortfolioProvider):
    name = "robinhood"

    def get_equity(self) -> float:
        username = os.getenv("RH_USERNAME")
        password = os.getenv("RH_PASSWORD")
        if not username or not password:
            raise RuntimeError(
                "RH_USERNAME and RH_PASSWORD must be set (in your local .env) "
                "to use the Robinhood provider."
            )

        try:
            import robin_stocks.robinhood as rh
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "robin_stocks is not installed. Install the optional extra: "
                "pip install -e '.[robinhood]'"
            ) from exc

        mfa_code = self._resolve_mfa_code()
        # Do not log the response; it can contain account identifiers.
        rh.login(username, password, mfa_code=mfa_code)
        try:
            profile = rh.profiles.load_portfolio_profile()
            equity = profile.get("equity") or profile.get("extended_hours_equity")
            if equity is None:
                raise RuntimeError("Robinhood returned no equity value.")
            return float(equity)
        finally:
            # Always drop the session so no auth token lingers in memory.
            try:
                rh.logout()
            except Exception:  # pragma: no cover
                pass

    @staticmethod
    def _resolve_mfa_code():
        code = os.getenv("RH_MFA_CODE")
        if code:
            return code.strip()
        secret = os.getenv("RH_TOTP_SECRET")
        if secret:
            try:
                import pyotp
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "RH_TOTP_SECRET is set but pyotp is not installed. "
                    "Install the optional extra: pip install -e '.[robinhood]'"
                ) from exc
            return pyotp.TOTP(secret.strip()).now()
        return None
