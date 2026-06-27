#!/usr/bin/env python3
"""Schwab token-health watchdog for the athena-market-data app.

Prints an alert ONLY when the 7-day refresh token is close to expiry (or already
expired / not configured). Stays SILENT (no output) when the token is healthy,
so the no_agent cron job sends nothing on healthy days.

Alert threshold: refresh token expiring within 36 hours.

Exit code is always 0; the message (if any) is the cron payload.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ALERT_WITHIN_HOURS = 36


def _load_env() -> None:
    env_path = Path.home() / ".athena" / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("SCHWAB_") and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    _load_env()
    sys.path.insert(0, str(Path.home() / ".athena" / "plugins"))
    try:
        from schwab_marketdata import oauth
    except Exception as exc:  # plugin missing / import error -> surface it
        print(f"⚠️ Schwab token-health check could not run: {exc}")
        return 0

    h = oauth.token_health()

    if not h.get("configured"):
        print("🔑 Schwab (athena-market-data): NOT CONFIGURED — no tokens stored. "
              "Run the OAuth consent flow to enable market data.")
        return 0

    if not h.get("refresh_valid"):
        print("🔴 Schwab (athena-market-data): REFRESH TOKEN EXPIRED. "
              "Market data is down until you re-run the consent (CAG/LMS) flow. "
              "Ask Athena to start the Schwab re-consent.")
        return 0

    days = h.get("refresh_expires_in_days", 0)
    hours = h.get("refresh_expires_in_sec", 0) / 3600.0
    if hours <= ALERT_WITHIN_HOURS:
        print(f"🟠 Schwab (athena-market-data): refresh token expires in "
              f"~{days} day(s) ({hours:.0f}h). Re-consent soon to avoid a market-"
              f"data outage. Ask Athena to start the Schwab re-consent flow.")
        return 0

    # Healthy -> stay silent (no message delivered).
    return 0


if __name__ == "__main__":
    sys.exit(main())
