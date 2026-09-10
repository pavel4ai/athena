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


class RefreshTokenInvalid(RuntimeError):
    """Raised when Schwab rejects the refresh token (invalid_grant) — the user
    must re-run the full CAG/LMS consent flow (spec §13). Distinct from a
    transient network error so callers can trigger re-consent, not blind retry.
    """


def _athena_home() -> Path:
    """Profile-aware ATHENA_HOME (mirrors athena_constants.get_athena_home)."""
    env = os.getenv("ATHENA_HOME")
    if env:
        return Path(env)
    return Path.home() / ".athena"


@dataclass(frozen=True)
class AppConfig:
    """Identifies one Schwab OAuth app: which env vars hold its credentials and
    which on-disk file stores its tokens. Two apps coexist without collision:
      - marketdata: SCHWAB_APP_KEY/SECRET      -> tokens.json        (quotes)
      - trader:     SCHWAB_TRADER_APP_KEY/SECRET -> trader_tokens.json (orders)
    """
    name: str
    key_env: str
    secret_env: str
    token_filename: str


MARKETDATA_APP = AppConfig("marketdata", "SCHWAB_APP_KEY",
                           "SCHWAB_APP_SECRET", "tokens.json")
TRADER_APP = AppConfig("trader", "SCHWAB_TRADER_APP_KEY",
                       "SCHWAB_TRADER_APP_SECRET", "trader_tokens.json")


def _token_path(app: AppConfig = MARKETDATA_APP) -> Path:
    p = _athena_home() / "athena_invest" / "schwab" / app.token_filename
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
    def from_token_response(cls, body: Dict[str, Any],
                            prev: Optional["TokenSet"] = None) -> "TokenSet":
        """Build a TokenSet from a token endpoint response.

        The refresh-token window is anchored to when the refresh token was
        FIRST issued, not to each refresh. Schwab's refresh endpoint returns a
        refresh_token on every call, but reusing/rotating it does NOT reset the
        hard 7-day expiry — so we only start a fresh 7-day clock when the
        refresh token value actually changes (a genuine new consent/rotation).
        Otherwise we carry forward the previous window. This prevents the
        health check from falsely reporting "valid for 7 more days" after every
        30-minute access refresh, which masked a revoked token (invalid_grant).
        """
        now = time.time()
        new_refresh = body["refresh_token"]
        if prev is not None and new_refresh == prev.refresh_token:
            # Same refresh token: keep the original hard expiry.
            refresh_expires_at = prev.refresh_expires_at
        else:
            # First issue or a genuinely rotated refresh token: new 7-day clock.
            refresh_expires_at = now + REFRESH_TOKEN_TTL
        return cls(
            access_token=body["access_token"],
            refresh_token=new_refresh,
            access_expires_at=now + int(body.get("expires_in", ACCESS_TOKEN_TTL)),
            refresh_expires_at=refresh_expires_at,
            id_token=body.get("id_token"),
            scope=body.get("scope", "api"),
        )


def _app_credentials(app: AppConfig = MARKETDATA_APP) -> tuple:
    key = os.getenv(app.key_env)
    secret = os.getenv(app.secret_env)
    callback = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")
    if not key or not secret:
        raise RuntimeError(f"{app.key_env} / {app.secret_env} not set in ~/.athena/.env")
    return key, secret, callback


def _basic_auth_header(app: AppConfig = MARKETDATA_APP) -> str:
    key, secret, _ = _app_credentials(app)
    raw = f"{key}:{secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


# --------------------------------------------------------------------------- #
# OAuth flow steps
# --------------------------------------------------------------------------- #
def _state_path(app: AppConfig) -> Path:
    return _schwab_dir_for(app) / f".oauth_state_{app.name}.json"


def _schwab_dir_for(app: AppConfig) -> Path:
    p = _athena_home() / "athena_invest" / "schwab"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_authorization_url(app: AppConfig = MARKETDATA_APP,
                            use_state: bool = True) -> str:
    """Step 1: the URL the user opens to consent (CAG/LMS).

    Includes response_type=code and a random, single-use `state` (CSRF/replay
    protection per the OAuth spec §4/§15). Schwab tolerates these extra params
    (verified) and echoes `state` back on the callback. `scope=api` is sent to
    match Schwab's token scope. The state is persisted (0600) so the callback
    can be verified in a later step/session, then consumed once.
    """
    import secrets
    key, _, callback = _app_credentials(app)
    params = {"response_type": "code", "client_id": key,
              "redirect_uri": callback, "scope": "api"}
    if use_state:
        state = secrets.token_urlsafe(24)
        p = _state_path(app)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, json.dumps({"state": state, "created": time.time()}).encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        params["state"] = state
    qs = urllib.parse.urlencode(params)
    return f"{OAUTH_BASE}/authorize?{qs}"


def verify_state(returned_state: Optional[str], app: AppConfig = MARKETDATA_APP,
                 consume: bool = True) -> bool:
    """Validate the `state` returned on the OAuth callback (spec §7/§15.2).

    Returns True only if a stored state exists and matches exactly. Single-use:
    on a match the stored state is consumed (deleted) to prevent replay. If no
    state was stored (build_authorization_url called with use_state=False),
    returns True (nothing to check) — callers that require state should pass
    use_state=True when building the URL.
    """
    p = _state_path(app)
    if not p.exists():
        return True  # no state was issued -> nothing to verify
    try:
        stored = json.loads(p.read_text()).get("state")
    except (ValueError, OSError):
        return False
    ok = bool(returned_state) and returned_state == stored
    if ok and consume:
        try:
            p.unlink()
        except OSError:
            pass
    return ok


def exchange_code_for_tokens(code: str, app: AppConfig = MARKETDATA_APP,
                             returned_state: Optional[str] = None,
                             require_state: bool = False) -> TokenSet:
    """Step 2: exchange the authorization code for the initial token set.

    The `code` from the redirect URL must be URL-decoded first (%40 -> @).
    If require_state=True, the callback `state` MUST match the one issued by
    build_authorization_url (CSRF/replay protection) or we refuse to exchange.
    """
    if require_state and not verify_state(returned_state, app):
        raise RuntimeError(
            "OAuth state mismatch — refusing to exchange code (possible CSRF/"
            "replay). Restart the consent flow with a fresh authorization URL.")
    _, _, callback = _app_credentials(app)
    decoded = urllib.parse.unquote(code)
    resp = httpx.post(
        f"{OAUTH_BASE}/token",
        headers={"Authorization": _basic_auth_header(app),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": decoded,
              "redirect_uri": callback},
        timeout=30,
    )
    resp.raise_for_status()
    ts = TokenSet.from_token_response(resp.json())
    save_tokens(ts, app)
    return ts


def refresh_access_token(ts: TokenSet, app: AppConfig = MARKETDATA_APP) -> TokenSet:
    """Step 4: use the refresh token to mint a new access token.

    Per the OAuth spec: a failed refresh with `invalid_grant` (revoked / expired
    / password-reset) means the refresh token is dead and the user MUST re-run
    the full consent flow. We surface that as a clear, actionable error rather
    than a raw HTTP 400 so callers/alerts can trigger re-consent.
    """
    if not ts.refresh_valid():
        raise RuntimeError(
            "Schwab refresh token expired (7-day limit). Re-run the CAG/LMS "
            "consent flow: build_authorization_url() -> exchange_code_for_tokens()."
        )
    resp = httpx.post(
        f"{OAUTH_BASE}/token",
        headers={"Authorization": _basic_auth_header(app),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": ts.refresh_token},
        timeout=30,
    )
    if resp.status_code == 400:
        body = ""
        try:
            body = resp.text
        except Exception:
            pass
        if "invalid_grant" in body:
            raise RefreshTokenInvalid(
                "Schwab refresh token invalid/revoked (invalid_grant). The 7-day "
                "clock may say valid, but Schwab rejected it — you MUST re-run the "
                "CAG/LMS consent flow to mint a new token.")
    resp.raise_for_status()
    new = TokenSet.from_token_response(resp.json(), prev=ts)
    save_tokens(new, app)
    return new


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def save_tokens(ts: TokenSet, app: AppConfig = MARKETDATA_APP) -> None:
    """Atomic + durable write: temp file -> fsync -> os.replace.

    A crash mid-write can never truncate/lose the token file (money-safety
    Principle 2). The temp file is created 0600 in the same directory so the
    rename stays on one filesystem and permissions never widen.
    """
    path = _token_path(app)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    data = json.dumps(ts.to_dict(), indent=2)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_tokens(app: AppConfig = MARKETDATA_APP) -> Optional[TokenSet]:
    path = _token_path(app)
    if not path.exists():
        return None
    try:
        return TokenSet(**json.loads(path.read_text()))
    except (ValueError, TypeError, KeyError):
        logger.warning("Schwab token file corrupt/incompatible: %s", path)
        return None


def get_valid_access_token(app: AppConfig = MARKETDATA_APP) -> str:
    """Return a currently-valid access token, refreshing if needed."""
    ts = load_tokens(app)
    if ts is None:
        raise RuntimeError(
            f"No Schwab {app.name} tokens stored. Complete the OAuth consent flow first.")
    if ts.access_valid():
        return ts.access_token
    ts = refresh_access_token(ts, app)
    return ts.access_token


def token_health(probe: bool = False, app: AppConfig = MARKETDATA_APP) -> Dict[str, Any]:
    """Status for the token-health cron job.

    By default this is a cheap CLOCK-ONLY check against the stored expiry
    timestamps. Those timestamps are only a local guess — Schwab can revoke or
    rotate a refresh token server-side at any time, and the clock keeps saying
    "valid" long after the token stopped working (observed as a 400
    invalid_grant on the next real refresh).

    Pass probe=True to actually verify with Schwab: if the access token is live
    we accept it as proof the credential chain works; otherwise we attempt a
    real refresh. A failed probe reports refresh_valid=False + needs_consent
    with the server error, so the alerting cron catches a dead token BEFORE the
    Sentinel relies on stale market data.
    """
    ts = load_tokens(app)
    if ts is None:
        return {"configured": False, "needs_consent": True, "probed": probe, "app": app.name}
    now = time.time()
    result = {
        "configured": True,
        "app": app.name,
        "access_valid": ts.access_valid(),
        "refresh_valid": ts.refresh_valid(),
        "access_expires_in_sec": max(0, int(ts.access_expires_at - now)),
        "refresh_expires_in_sec": max(0, int(ts.refresh_expires_at - now)),
        "refresh_expires_in_days": round(max(0, ts.refresh_expires_at - now) / 86400, 2),
        "needs_consent": not ts.refresh_valid(),
        "probed": False,
    }
    if not probe:
        return result

    # Real verification. A currently-valid access token already proves the
    # credential works, so don't burn a refresh needlessly. Otherwise attempt a
    # real refresh and report the truth (this rotates/persists tokens on success).
    result["probed"] = True
    if ts.access_valid():
        result["probe_ok"] = True
        return result
    try:
        new = refresh_access_token(ts, app)
        now = time.time()
        result.update({
            "probe_ok": True,
            "access_valid": True,
            "refresh_valid": new.refresh_valid(),
            "access_expires_in_sec": max(0, int(new.access_expires_at - now)),
            "refresh_expires_in_sec": max(0, int(new.refresh_expires_at - now)),
            "refresh_expires_in_days": round(max(0, new.refresh_expires_at - now) / 86400, 2),
            "needs_consent": False,
        })
    except RefreshTokenInvalid as exc:
        # Schwab explicitly rejected the refresh token -> re-consent required.
        result.update({
            "probe_ok": False,
            "refresh_valid": False,
            "needs_consent": True,
            "probe_error": f"invalid_grant: {exc}",
        })
    except httpx.HTTPStatusError as exc:
        body = ""
        try:
            body = exc.response.text[:300]
        except Exception:
            pass
        result.update({
            "probe_ok": False,
            "refresh_valid": False,
            "needs_consent": True,
            "probe_error": f"HTTP {exc.response.status_code}: {body}",
        })
    except Exception as exc:  # network/other — don't falsely flag revoked
        result.update({
            "probe_ok": False,
            "probe_error": f"{type(exc).__name__}: {exc}",
        })
    return result


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
