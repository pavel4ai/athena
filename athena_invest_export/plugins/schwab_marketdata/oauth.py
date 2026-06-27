"""Schwab OAuth 2.0 + token management (Trader API, 3-legged flow).

Implements:
  - Authorization URL builder (Step 1: CAG/LMS consent).
  - Authorization-code -> token exchange (Step 2).
  - Token refresh (Step 4).
  - Secure on-disk token storage under the active profile's ATHENA_HOME.
  - A RealCredentialProvider that gives the streamer a fresh access token plus
    the GET User Preference streamer-connection values.

Token facts (from the Schwab spec):
  access_token  : valid 30 minutes  -> refreshed proactively.
  refresh_token : valid 7 days      -> on expiry, full CAG/LMS restart needed.

Auth to the token endpoint: HTTP Basic base64(client_id:client_secret),
Content-Type application/x-www-form-urlencoded.

Secrets (SCHWAB_APP_KEY, SCHWAB_APP_SECRET, SCHWAB_CALLBACK_URL) live in
~/.athena/.env per Athena policy. Tokens are stored in
$ATHENA_HOME/athena_invest/schwab/tokens.json (chmod 600).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from .streamer import CredentialProvider, StreamerInfo

logger = logging.getLogger(__name__)

OAUTH_BASE = "https://api.schwabapi.com/v1/oauth"
TRADER_BASE = "https://api.schwabapi.com/trader/v1"
ACCESS_TOKEN_TTL = 1800       # 30 min
REFRESH_TOKEN_TTL = 7 * 86400  # 7 days
# Refresh the access token this many seconds before it actually expires.
ACCESS_REFRESH_SKEW = 300


def _athena_home() -> Path:
    """Profile-aware ATHENA_HOME (mirrors athena_constants.get_athena_home)."""
    env = os.getenv("ATHENA_HOME")
    if env:
        return Path(env)
    return Path.home() / ".athena"


def _token_path() -> Path:
    p = _athena_home() / "athena_invest" / "schwab" / "tokens.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    access_expires_at: float   # epoch seconds
    refresh_expires_at: float  # epoch seconds
    id_token: Optional[str] = None
    scope: str = "api"

    def access_valid(self) -> bool:
        return time.time() < (self.access_expires_at - ACCESS_REFRESH_SKEW)

    def refresh_valid(self) -> bool:
        return time.time() < self.refresh_expires_at

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_token_response(cls, body: Dict[str, Any]) -> "TokenSet":
        now = time.time()
        return cls(
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            access_expires_at=now + int(body.get("expires_in", ACCESS_TOKEN_TTL)),
            refresh_expires_at=now + REFRESH_TOKEN_TTL,
            id_token=body.get("id_token"),
            scope=body.get("scope", "api"),
        )


def _app_credentials() -> tuple:
    key = os.getenv("SCHWAB_APP_KEY")
    secret = os.getenv("SCHWAB_APP_SECRET")
    callback = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")
    if not key or not secret:
        raise RuntimeError("SCHWAB_APP_KEY / SCHWAB_APP_SECRET not set in ~/.athena/.env")
    return key, secret, callback


def _basic_auth_header() -> str:
    key, secret, _ = _app_credentials()
    raw = f"{key}:{secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


# --------------------------------------------------------------------------- #
# OAuth flow steps
# --------------------------------------------------------------------------- #
def build_authorization_url() -> str:
    """Step 1: the URL the user opens to consent (CAG/LMS)."""
    key, _, callback = _app_credentials()
    qs = urllib.parse.urlencode({"client_id": key, "redirect_uri": callback})
    return f"{OAUTH_BASE}/authorize?{qs}"


def exchange_code_for_tokens(code: str) -> TokenSet:
    """Step 2: exchange the authorization code for the initial token set.

    The `code` from the redirect URL must be URL-decoded first (%40 -> @).
    """
    _, _, callback = _app_credentials()
    decoded = urllib.parse.unquote(code)
    resp = httpx.post(
        f"{OAUTH_BASE}/token",
        headers={"Authorization": _basic_auth_header(),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": decoded,
              "redirect_uri": callback},
        timeout=30,
    )
    resp.raise_for_status()
    ts = TokenSet.from_token_response(resp.json())
    save_tokens(ts)
    return ts


def refresh_access_token(ts: TokenSet) -> TokenSet:
    """Step 4: use the refresh token to mint a new access token."""
    if not ts.refresh_valid():
        raise RuntimeError(
            "Schwab refresh token expired (7-day limit). Re-run the CAG/LMS "
            "consent flow: build_authorization_url() -> exchange_code_for_tokens()."
        )
    resp = httpx.post(
        f"{OAUTH_BASE}/token",
        headers={"Authorization": _basic_auth_header(),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": ts.refresh_token},
        timeout=30,
    )
    resp.raise_for_status()
    new = TokenSet.from_token_response(resp.json())
    save_tokens(new)
    return new


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def save_tokens(ts: TokenSet) -> None:
    path = _token_path()
    path.write_text(json.dumps(ts.to_dict(), indent=2))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_tokens() -> Optional[TokenSet]:
    path = _token_path()
    if not path.exists():
        return None
    try:
        return TokenSet(**json.loads(path.read_text()))
    except (ValueError, TypeError, KeyError):
        logger.warning("Schwab token file corrupt/incompatible: %s", path)
        return None


def get_valid_access_token() -> str:
    """Return a currently-valid access token, refreshing if needed."""
    ts = load_tokens()
    if ts is None:
        raise RuntimeError("No Schwab tokens stored. Complete the OAuth consent flow first.")
    if ts.access_valid():
        return ts.access_token
    ts = refresh_access_token(ts)
    return ts.access_token


def token_health() -> Dict[str, Any]:
    """Status for the token-health cron job."""
    ts = load_tokens()
    if ts is None:
        return {"configured": False, "needs_consent": True}
    now = time.time()
    return {
        "configured": True,
        "access_valid": ts.access_valid(),
        "refresh_valid": ts.refresh_valid(),
        "access_expires_in_sec": max(0, int(ts.access_expires_at - now)),
        "refresh_expires_in_sec": max(0, int(ts.refresh_expires_at - now)),
        "refresh_expires_in_days": round(max(0, ts.refresh_expires_at - now) / 86400, 2),
        "needs_consent": not ts.refresh_valid(),
    }


# --------------------------------------------------------------------------- #
# Real credential provider for the streamer (GET User Preference)
# --------------------------------------------------------------------------- #
class RealCredentialProvider(CredentialProvider):
    """Provides streamer connection info using live tokens + GET User Preference."""

    def is_configured(self) -> bool:
        ts = load_tokens()
        return ts is not None and ts.refresh_valid()

    async def get_streamer_info(self) -> StreamerInfo:
        token = get_valid_access_token()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{TRADER_BASE}/userPreference",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            pref = resp.json()
        streamer = (pref.get("streamerInfo") or [{}])[0]
        return StreamerInfo(
            websocket_url=streamer.get("streamerSocketUrl", ""),
            access_token=token,
            schwab_client_customer_id=streamer.get("schwabClientCustomerId", ""),
            schwab_client_correl_id=streamer.get("schwabClientCorrelId", ""),
            schwab_client_channel=streamer.get("schwabClientChannel", ""),
            schwab_client_function_id=streamer.get("schwabClientFunctionId", ""),
        )
