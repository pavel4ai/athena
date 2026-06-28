"""Schwab market-data plugin — token-gated Level 1 quote tools for Athena.

Exposes market-data tools that the Athena Schwab agent (and Analyst/Scout via
read-only quotes) can call. All tools are GATED on Schwab credentials being
configured: until the OAuth/REST layer is wired and a token is available, the
tools report unavailability instead of fabricating quotes.

The heavy lifting (WebSocket protocol, field decoding, symbol formatting) lives
in:
  - fields.py    : numbered-field -> named-field decoders + response codes
  - streamer.py  : SchwabStreamerClient + CredentialProvider interface
  - symbols.py   : Schwab symbol formatting per asset class

This plugin does NOT modify any Athena core file.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level singletons so we never open >1 streamer connection (Schwab limit).
_PROVIDER = None
_CLIENT = None


def _get_provider():
    """Return the active CredentialProvider.

    Uses the real OAuth-backed provider when app credentials are present and a
    valid (refresh-token) consent exists; otherwise the stub that refuses
    cleanly so the agent stays preview-only instead of fabricating data.
    """
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    if _credentials_present():
        from .oauth import RealCredentialProvider
        _PROVIDER = RealCredentialProvider()
    else:
        from .streamer import CredentialProvider
        _PROVIDER = CredentialProvider()  # stub
    return _PROVIDER


def _credentials_present() -> bool:
    """True only when the Schwab app credentials exist as secrets.

    Gates tool visibility. We check for the app key/secret env vars; the real
    provider will additionally verify a live token + user-preference fetch.
    """
    return bool(os.getenv("SCHWAB_APP_KEY") and os.getenv("SCHWAB_APP_SECRET"))


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        from .streamer import SchwabStreamerClient
        _CLIENT = SchwabStreamerClient(_get_provider())
    return _CLIENT


async def _snapshot(symbols: List[str], service: Optional[str], timeout: float) -> Dict[str, Any]:
    """Connect, subscribe, collect one decoded update per symbol, return it."""
    from .symbols import service_for_symbol

    if not service:
        # group by inferred service if mixed; for simplicity require one service
        services = {service_for_symbol(s) for s in symbols}
        if len(services) > 1:
            return {"error": "Mixed asset classes; call once per service.",
                    "services_detected": sorted(services)}
        service = services.pop()

    client = _get_client()
    collected: Dict[str, Dict[str, Any]] = {}
    done = asyncio.Event()
    wanted = {s.upper() for s in symbols}

    async def handler(decoded: list) -> None:
        for block in decoded:
            if block["service"] != service:
                continue
            for row in block["rows"]:
                key = (row.get("key") or row.get("symbol") or "").upper()
                if key in wanted:
                    collected[key] = row
            if wanted <= set(collected):
                done.set()

    client.on_data(handler)
    await client.connect()
    await client.subscribe(service, symbols)
    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass  # return whatever arrived
    return {"service": service, "quotes": collected,
            "received": len(collected), "requested": len(symbols)}


def schwab_quote(args: Dict[str, Any], **kwargs) -> str:
    """Tool handler: market-data quotes for one or more symbols.

    Uses the Market Data Production REST endpoint by default (works for
    data-only apps; no Trader entitlement / User Preference needed). The
    WebSocket streamer path is available via transport="stream" for apps that
    carry Trader API entitlement.
    """
    symbols = args.get("symbols") or []
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbols:
        return json.dumps({"success": False, "error": "No symbols provided."})
    if not _credentials_present():
        return json.dumps({
            "success": False, "available": False,
            "error": ("Schwab credentials not configured. Operating preview-only."),
        })

    transport = (args.get("transport") or "rest").lower()
    try:
        if transport == "stream":
            service = args.get("service")
            timeout = float(args.get("timeout", 8))
            result = asyncio.run(_snapshot(symbols, service, timeout))
            return json.dumps({"success": True, "transport": "stream", **result})
        # default: REST market data
        from . import rest_marketdata as rmd
        raw = rmd.get_quotes(symbols)
        quotes = rmd.simplify_quotes(raw)
        return json.dumps({"success": True, "transport": "rest",
                           "quotes": quotes, "received": len(quotes),
                           "requested": len(symbols)})
    except Exception as exc:
        logger.exception("schwab_quote failed")
        msg = str(exc)
        hint = ""
        if "401" in msg or "Unauthorized" in msg:
            hint = (" (401: this app may lack the required entitlement, or the "
                    "token needs re-consent.)")
        return json.dumps({"success": False, "error": msg + hint})


SCHWAB_QUOTE_SCHEMA = {
    "name": "schwab_quote",
    "description": (
        "Get Level 1 market-data snapshot quotes from the Schwab Streamer for "
        "one or more symbols (equities/ETFs, options, futures, futures-options, "
        "forex). Returns decoded named fields (bid/ask/last/volume/etc.). "
        "Read-only market data — never places orders. Requires Schwab "
        "credentials; reports unavailable if not configured."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array", "items": {"type": "string"},
                "description": "Schwab-standard symbols, e.g. ['AAPL','SPY'] or "
                               "['/ESZ25'] or ['EUR/USD'].",
            },
            "service": {
                "type": "string",
                "enum": ["LEVELONE_EQUITIES", "LEVELONE_OPTIONS",
                         "LEVELONE_FUTURES", "LEVELONE_FUTURES_OPTIONS",
                         "LEVELONE_FOREX"],
                "description": "Streamer service (only used when transport='stream').",
            },
            "transport": {
                "type": "string", "enum": ["rest", "stream"],
                "description": "rest (default; Market Data Production REST) or "
                               "stream (WebSocket; needs Trader API entitlement).",
            },
            "timeout": {"type": "number", "description": "Stream wait seconds (default 8)."},
        },
        "required": ["symbols"],
    },
}


def schwab_accounts(args: Dict[str, Any], **kwargs) -> str:
    """Tool handler: read accounts + positions (read-only, unthrottled)."""
    if not _credentials_present():
        return json.dumps({"success": False, "available": False,
                           "error": "Schwab credentials not configured."})
    try:
        from . import trader
        fields = args.get("fields", "positions")
        acct_hash = args.get("account_hash")
        if acct_hash:
            data = trader.get_account(acct_hash, fields=fields)
        else:
            data = trader.get_accounts(fields=fields)
        return json.dumps({"success": True, "accounts": data})
    except Exception as exc:
        logger.exception("schwab_accounts failed")
        return json.dumps({"success": False, "error": str(exc)})


def schwab_token_health(args: Dict[str, Any], **kwargs) -> str:
    """Tool handler: report OAuth token health for the re-auth cron/alerts."""
    try:
        from .oauth import token_health
        return json.dumps({"success": True, **token_health()})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


SCHWAB_ACCOUNTS_SCHEMA = {
    "name": "schwab_accounts",
    "description": (
        "Read Schwab account balances and positions (read-only, unthrottled). "
        "Pass account_hash for one account, omit for all. Used for portfolio "
        "reconciliation. Never places orders."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "account_hash": {"type": "string",
                             "description": "Encrypted account id (from accountNumbers). Optional."},
            "fields": {"type": "string", "description": "e.g. 'positions' (default)."},
        },
    },
}

SCHWAB_TOKEN_HEALTH_SCHEMA = {
    "name": "schwab_token_health",
    "description": (
        "Check Schwab OAuth token health: whether the access token is valid, "
        "whether the 7-day refresh token is still valid, and how long until it "
        "expires. Use to decide if a manual re-consent (CAG/LMS) is needed."
    ),
    "parameters": {"type": "object", "properties": {}},
}


def schwab_place_order(args: Dict[str, Any], **kwargs) -> str:
    """Place an order. Routes to MOCK broker (paper) or LIVE Trader API per mode.

    SAFETY: this is the execution endpoint. The orchestrator must have a recorded
    human approval before calling it (the agent spec enforces the approval gate).
    In mock mode it simulates fills on live quotes; in live mode it hits Schwab.
    """
    if not _credentials_present():
        return json.dumps({"success": False, "available": False,
                           "error": "Schwab credentials not configured."})
    cohort = args.get("cohort")
    order = args.get("order")
    account_hash = args.get("account_hash", f"MOCK-{cohort}")
    if not order:
        return json.dumps({"success": False, "error": "Missing 'order' payload."})
    try:
        from . import trader, mode
        # Validate the order shape regardless of mode (instruction matrix etc.)
        v = trader.validate_order(order)
        if not v["valid"]:
            return json.dumps({"success": False, "error": "Invalid order", "details": v["errors"]})
        if mode.is_mock():
            if not cohort:
                return json.dumps({"success": False, "error": "Mock mode needs 'cohort'."})
            from .mock_broker import MockBroker
            result = MockBroker(cohort).place_order(account_hash, order)
            return json.dumps({"success": True, "mode": "mock", **result})
        # live
        result = trader.place_order(account_hash, order)
        return json.dumps({"success": True, "mode": "live", **result})
    except Exception as exc:
        logger.exception("schwab_place_order failed")
        return json.dumps({"success": False, "error": str(exc)})


def schwab_mock_admin(args: Dict[str, Any], **kwargs) -> str:
    """Mock-mode admin: get/set mode, fund a cohort, read mock account, process
    working orders. action one of: get_mode|set_mode|fund|account|process|reset."""
    try:
        from . import mode
        action = (args.get("action") or "get_mode").lower()
        if action == "get_mode":
            return json.dumps({"success": True, "mode": mode.get_mode()})
        if action == "set_mode":
            return json.dumps({"success": True, **mode.set_mode(args.get("mode", "mock"))})

        from .mock_broker import MockBroker, _mock_dir
        cohort = args.get("cohort")
        if action in ("fund", "account", "process", "reset") and not cohort:
            return json.dumps({"success": False, "error": "cohort required."})
        if action == "fund":
            b = MockBroker(cohort); b.fund(float(args.get("cash", 0)))
            return json.dumps({"success": True, "cohort": cohort, "cash": b.state["cash"]})
        if action == "account":
            return json.dumps({"success": True, **MockBroker(cohort).get_account()})
        if action == "process":
            return json.dumps({"success": True, "filled": MockBroker(cohort).process_working_orders()})
        if action == "reset":
            p = _mock_dir() / f"{cohort}.json"
            existed = p.exists()
            if existed:
                p.unlink()
            return json.dumps({"success": True, "reset": cohort, "existed": existed})
        return json.dumps({"success": False, "error": f"Unknown action {action}"})
    except Exception as exc:
        logger.exception("schwab_mock_admin failed")
        return json.dumps({"success": False, "error": str(exc)})


SCHWAB_PLACE_ORDER_SCHEMA = {
    "name": "schwab_place_order",
    "description": (
        "Place a Schwab order. Routes to the MOCK paper broker or the LIVE Trader "
        "API depending on the current mode (mock by default). REQUIRES a recorded "
        "human approval upstream — this is the execution step. Mock fills use live "
        "quotes (market at ask/bid, limit when crossable). Provide a validated "
        "order payload (use the trader order builder shape)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "cohort": {"type": "string", "description": "Cohort name (required in mock)."},
            "account_hash": {"type": "string", "description": "Live account hash (live mode)."},
            "order": {"type": "object", "description": "Schwab order payload (orderType, orderLegCollection, ...)."},
        },
        "required": ["order"],
    },
}

SCHWAB_MOCK_ADMIN_SCHEMA = {
    "name": "schwab_mock_admin",
    "description": (
        "Manage pre-flight mock/paper trading: get/set broker mode (mock|live), "
        "fund a mock cohort with starting cash, read a mock account (cash + "
        "positions + NAV on live prices), process working limit orders, or reset "
        "a cohort's mock state. Use to run Athena hands-off in pre-flight."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string",
                       "enum": ["get_mode", "set_mode", "fund", "account", "process", "reset"]},
            "mode": {"type": "string", "enum": ["mock", "live"], "description": "For set_mode."},
            "cohort": {"type": "string", "description": "Cohort name."},
            "cash": {"type": "number", "description": "Starting cash for fund."},
        },
        "required": ["action"],
    },
}


def register(ctx) -> None:
    """Plugin entry point — register the token-gated market-data + account tools."""
    ctx.register_tool(
        name="schwab_quote",
        toolset="schwab",
        schema=SCHWAB_QUOTE_SCHEMA,
        handler=schwab_quote,
        check_fn=_credentials_present,   # zero footprint until credentials exist
        requires_env=["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"],
        description="Schwab Level 1 market-data snapshot quotes (read-only).",
        emoji="📈",
    )
    ctx.register_tool(
        name="schwab_accounts",
        toolset="schwab",
        schema=SCHWAB_ACCOUNTS_SCHEMA,
        handler=schwab_accounts,
        check_fn=_credentials_present,
        requires_env=["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"],
        description="Schwab account balances and positions (read-only).",
        emoji="🏦",
    )
    ctx.register_tool(
        name="schwab_token_health",
        toolset="schwab",
        schema=SCHWAB_TOKEN_HEALTH_SCHEMA,
        handler=schwab_token_health,
        check_fn=_credentials_present,
        requires_env=["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"],
        description="Schwab OAuth token health / re-auth check.",
        emoji="🔑",
    )
    ctx.register_tool(
        name="schwab_place_order",
        toolset="schwab",
        schema=SCHWAB_PLACE_ORDER_SCHEMA,
        handler=schwab_place_order,
        check_fn=_credentials_present,
        requires_env=["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"],
        description="Place a Schwab order (mock paper or live, per mode).",
        emoji="🧾",
    )
    ctx.register_tool(
        name="schwab_mock_admin",
        toolset="schwab",
        schema=SCHWAB_MOCK_ADMIN_SCHEMA,
        handler=schwab_mock_admin,
        check_fn=_credentials_present,
        requires_env=["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"],
        description="Manage pre-flight mock/paper trading + broker mode.",
        emoji="🧪",
    )
    logger.info("schwab_marketdata plugin registered (gated=%s)", _credentials_present())

    # Bloomberg-style live ticker bar in the CLI (gated on Schwab creds + live
    # data). Safe no-op in the gateway or when credentials are absent.
    try:
        if _credentials_present():
            from . import ticker
            if ticker.register_with_cli():
                ticker.start_ticker()
                logger.info("schwab_marketdata: live ticker bar enabled.")
    except Exception as exc:
        logger.debug("schwab_marketdata: ticker setup skipped: %s", exc)
