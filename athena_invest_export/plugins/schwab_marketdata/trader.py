"""Schwab Trader API REST layer — accounts, positions, transactions, orders.

Read paths (GET) are unthrottled. Order mutations (POST/PUT/DELETE) are
throttled 0-120/min/account by Schwab and ALWAYS require explicit human
approval upstream (Athena Schwab never auto-places). This module only builds and
sends what it is told to; the approval gate lives in the orchestrator.

Order entry is limited by Schwab to assetType EQUITY and OPTION. Futures order
placement is NOT supported -> propose-only (enforced in build_single_order).

Symbology (options): "XYZ   240315C00500000"
  6-char padded underlying | YYMMDD | C/P | 5+3 strike.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from .oauth import TRADER_BASE, TRADER_APP, get_valid_access_token

logger = logging.getLogger(__name__)

# Instruction validity matrix (Schwab spec).
EQUITY_INSTRUCTIONS = {"BUY", "SELL", "BUY_TO_COVER", "SELL_SHORT"}
OPTION_INSTRUCTIONS = {"BUY_TO_OPEN", "BUY_TO_CLOSE", "SELL_TO_OPEN", "SELL_TO_CLOSE"}

VALID_ORDER_TYPES = {
    "MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP", "TRAILING_STOP_LIMIT",
    "CABINET", "NON_MARKETABLE", "MARKET_ON_CLOSE", "EXERCISE", "LIMIT_ON_CLOSE",
    "NET_DEBIT", "NET_CREDIT", "NET_ZERO",
}
VALID_DURATIONS = {"DAY", "GOOD_TILL_CANCEL", "FILL_OR_KILL",
                   "IMMEDIATE_OR_CANCEL", "END_OF_WEEK", "END_OF_MONTH",
                   "NEXT_END_OF_MONTH"}
VALID_SESSIONS = {"NORMAL", "AM", "PM", "SEAMLESS"}
# orderStrategyType values Schwab accepts (SINGLE + the conditional strategies).
VALID_ORDER_STRATEGY_TYPES = {"SINGLE", "OCO", "TRIGGER"}
# assetTypes valid for ORDER ENTRY (Schwab: EQUITY + OPTION only).
VALID_ORDER_ASSET_TYPES = {"EQUITY", "OPTION"}


def _headers(write: bool = False) -> Dict[str, str]:
    # Trader API uses the SEPARATE trading-app tokens (SCHWAB_TRADER_APP_*),
    # NOT the market-data app. The market-data app is entitled to quotes only
    # (order limit 0) and would 401 on any /trader/v1 call.
    #
    # CRITICAL: only send `Content-Type: application/json` on requests that
    # actually carry a JSON body (POST/PUT). Schwab's API gateway REJECTS a
    # bodyless GET/DELETE that carries `Content-Type: application/json` with a
    # 400 whose body confusingly reads `status: 500 Internal Server Error` —
    # this presents as intermittent "flapping" but is deterministic on the
    # header. Read requests advertise `Accept` only. (Diagnosed 2026-07-08:
    # /accounts/accountNumbers 400'd 6/6 with Content-Type and 200'd 6/6
    # without, same token, same second.)
    h = {"Authorization": f"Bearer {get_valid_access_token(TRADER_APP)}",
         "Accept": "application/json"}
    if write:
        h["Content-Type"] = "application/json"
    return h


# --------------------------------------------------------------------------- #
# Read endpoints (unthrottled)
# --------------------------------------------------------------------------- #
def get_account_numbers() -> List[Dict[str, str]]:
    """Map plain account numbers to their encrypted hashValue (used in URLs)."""
    r = httpx.get(f"{TRADER_BASE}/accounts/accountNumbers", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def get_accounts(fields: str = "positions") -> List[Dict[str, Any]]:
    r = httpx.get(f"{TRADER_BASE}/accounts", headers=_headers(),
                  params={"fields": fields}, timeout=30)
    r.raise_for_status()
    return r.json()


def get_account(account_hash: str, fields: str = "positions") -> Dict[str, Any]:
    r = httpx.get(f"{TRADER_BASE}/accounts/{account_hash}", headers=_headers(),
                  params={"fields": fields}, timeout=30)
    r.raise_for_status()
    return r.json()


def get_orders(account_hash: str, from_time: str, to_time: str,
               status: Optional[str] = None) -> List[Dict[str, Any]]:
    params = {"fromEnteredTime": from_time, "toEnteredTime": to_time}
    if status:
        params["status"] = status
    r = httpx.get(f"{TRADER_BASE}/accounts/{account_hash}/orders",
                  headers=_headers(), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_order(account_hash: str, order_id: str) -> Dict[str, Any]:
    r = httpx.get(f"{TRADER_BASE}/accounts/{account_hash}/orders/{order_id}",
                  headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def get_all_orders(from_time: str, to_time: str,
                   status: Optional[str] = None) -> List[Dict[str, Any]]:
    """GET /orders — all orders across ALL linked accounts (unthrottled read)."""
    params = {"fromEnteredTime": from_time, "toEnteredTime": to_time}
    if status:
        params["status"] = status
    r = httpx.get(f"{TRADER_BASE}/orders", headers=_headers(),
                  params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_transactions(account_hash: str, start: str, end: str,
                     types: str = "TRADE") -> List[Dict[str, Any]]:
    r = httpx.get(f"{TRADER_BASE}/accounts/{account_hash}/transactions",
                  headers=_headers(),
                  params={"startDate": start, "endDate": end, "types": types},
                  timeout=30)
    r.raise_for_status()
    return r.json()


def get_transaction(account_hash: str, transaction_id: str) -> Dict[str, Any]:
    """GET /accounts/{n}/transactions/{id} — one transaction (unthrottled read)."""
    r = httpx.get(f"{TRADER_BASE}/accounts/{account_hash}/transactions/{transaction_id}",
                  headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def get_user_preference() -> Dict[str, Any]:
    """GET /userPreference — account nicknames, streamer info, trading prefs."""
    r = httpx.get(f"{TRADER_BASE}/userPreference", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------- #
# Order payload builders (validated; never auto-sent)
# --------------------------------------------------------------------------- #
def _validate_leg(instruction: str, asset_type: str) -> None:
    asset_type = asset_type.upper()
    instruction = instruction.upper()
    if asset_type == "EQUITY":
        if instruction not in EQUITY_INSTRUCTIONS:
            raise ValueError(f"Instruction {instruction} invalid for EQUITY. "
                             f"Allowed: {sorted(EQUITY_INSTRUCTIONS)}")
    elif asset_type == "OPTION":
        if instruction not in OPTION_INSTRUCTIONS:
            raise ValueError(f"Instruction {instruction} invalid for OPTION. "
                             f"Allowed: {sorted(OPTION_INSTRUCTIONS)}")
    elif asset_type in ("FUTURE", "FUTURE_OPTION"):
        raise ValueError("Schwab Trader API does not support futures order entry "
                         "— route futures as propose-only / manual placement.")
    else:
        raise ValueError(f"Unsupported assetType for order entry: {asset_type}")


def build_single_order(symbol: str, asset_type: str, instruction: str,
                       quantity: int, order_type: str = "MARKET",
                       price: Optional[float] = None,
                       stop_price: Optional[float] = None,
                       duration: str = "DAY", session: str = "NORMAL") -> Dict[str, Any]:
    """Build a validated SINGLE order payload (EQUITY or OPTION)."""
    _validate_leg(instruction, asset_type)
    order_type = order_type.upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(f"Invalid orderType {order_type}")
    if duration.upper() not in VALID_DURATIONS:
        raise ValueError(f"Invalid duration {duration}")
    if session.upper() not in VALID_SESSIONS:
        raise ValueError(f"Invalid session {session}")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if order_type in ("LIMIT", "STOP_LIMIT", "NET_DEBIT", "NET_CREDIT") and price is None:
        raise ValueError(f"{order_type} requires a price")
    if order_type in ("STOP", "STOP_LIMIT") and stop_price is None:
        raise ValueError(f"{order_type} requires a stopPrice")

    order: Dict[str, Any] = {
        "orderType": order_type,
        "session": session.upper(),
        "duration": duration.upper(),
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [{
            "instruction": instruction.upper(),
            "quantity": quantity,
            "instrument": {"symbol": symbol, "assetType": asset_type.upper()},
        }],
    }
    if price is not None:
        order["price"] = str(price)
    if stop_price is not None:
        order["stopPrice"] = str(stop_price)
    return order


def validate_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """Re-validate any order payload (incl. multi-leg / conditional) before send.

    Full structural conformance to the Schwab Trader API order spec — fail LOUD
    locally rather than shipping a malformed order and relying on a server 400:
      - orderStrategyType in {SINGLE, OCO, TRIGGER}
      - every leg has instruction / instrument.symbol / positive integer quantity
      - instrument.assetType in {EQUITY, OPTION} and instruction matches the
        Schwab instruction×assetType matrix
      - orderType (when present) is a valid type
      - a node must carry legs OR childOrderStrategies (never neither); an OCO
        node must carry childOrderStrategies; recursion validates children too

    Returns {"valid": bool, "errors": [...]} without raising, so callers can
    surface problems in a preview.
    """
    errors: List[str] = []

    def _check_node(o: Dict[str, Any], path: str = "order") -> None:
        if not isinstance(o, dict):
            errors.append(f"{path}: not an object")
            return

        strat = str(o.get("orderStrategyType", "")).upper()
        if strat and strat not in VALID_ORDER_STRATEGY_TYPES:
            errors.append(f"{path}: invalid orderStrategyType {strat!r} "
                          f"(allowed {sorted(VALID_ORDER_STRATEGY_TYPES)})")

        otype = str(o.get("orderType", "")).upper()
        if otype and otype not in VALID_ORDER_TYPES:
            errors.append(f"{path}: invalid orderType {otype!r}")

        dur = str(o.get("duration", "")).upper()
        if dur and dur not in VALID_DURATIONS:
            errors.append(f"{path}: invalid duration {dur!r}")

        sess = str(o.get("session", "")).upper()
        if sess and sess not in VALID_SESSIONS:
            errors.append(f"{path}: invalid session {sess!r}")

        legs = o.get("orderLegCollection", []) or []
        children = o.get("childOrderStrategies", []) or []

        # An OCO node coordinates children and carries no legs of its own.
        if strat == "OCO":
            if not children:
                errors.append(f"{path}: OCO requires childOrderStrategies")
        else:
            # A non-OCO node must have legs OR children (never an empty order).
            if not legs and not children:
                errors.append(f"{path}: order has no orderLegCollection and no "
                              f"childOrderStrategies (empty order)")

        for i, leg in enumerate(legs):
            lpath = f"{path}.leg[{i}]"
            if not isinstance(leg, dict):
                errors.append(f"{lpath}: not an object"); continue
            inst = str(leg.get("instruction", "")).upper()
            if not inst:
                errors.append(f"{lpath}: missing instruction")
            instrument = leg.get("instrument") or {}
            atype = str(instrument.get("assetType", "")).upper()
            symbol = instrument.get("symbol")
            if not symbol:
                errors.append(f"{lpath}: missing instrument.symbol")
            if not atype:
                errors.append(f"{lpath}: missing instrument.assetType")
            elif atype not in VALID_ORDER_ASSET_TYPES:
                errors.append(f"{lpath}: assetType {atype!r} not valid for order "
                              f"entry (allowed {sorted(VALID_ORDER_ASSET_TYPES)})")
            qty = leg.get("quantity")
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                errors.append(f"{lpath}: quantity must be a positive integer (got {qty!r})")
            # instruction×assetType matrix (only when both are present/valid)
            if inst and atype in VALID_ORDER_ASSET_TYPES:
                try:
                    _validate_leg(inst, atype)
                except ValueError as e:
                    errors.append(f"{lpath}: {e}")

        for j, child in enumerate(children):
            _check_node(child, f"{path}.child[{j}]")

    _check_node(order)
    return {"valid": not errors, "errors": errors}


# --------------------------------------------------------------------------- #
# Order mutation endpoints — POST-APPROVAL ONLY
# --------------------------------------------------------------------------- #
def preview_order(account_hash: str, order: Dict[str, Any]) -> Dict[str, Any]:
    """POST /accounts/{n}/previewOrder — Schwab's pre-trade dry-run.

    Places NO order. Returns Schwab's own validation, estimated commissions/
    fees, and any warnings/rejects for the given payload. Industry-standard
    pre-trade check: call this before place_order so the human approval preview
    reflects Schwab's actual assessment (buying power, fees, order-status
    rejects), not just our local validator. We still validate locally first so a
    structurally-broken order never leaves the process.
    """
    v = validate_order(order)
    if not v["valid"]:
        raise ValueError(f"Refusing to preview invalid order: {v['errors']}")
    r = httpx.post(f"{TRADER_BASE}/accounts/{account_hash}/previewOrder",
                   headers=_headers(write=True), json=order, timeout=30)
    r.raise_for_status()
    return r.json()


def place_order(account_hash: str, order: Dict[str, Any]) -> Dict[str, Any]:
    """POST an order. CALLER MUST HAVE A RECORDED HUMAN APPROVAL.

    Returns {"order_id": <from Location header>, "status_code": ...}.
    """
    v = validate_order(order)
    if not v["valid"]:
        raise ValueError(f"Refusing to place invalid order: {v['errors']}")
    r = httpx.post(f"{TRADER_BASE}/accounts/{account_hash}/orders",
                   headers=_headers(write=True), json=order, timeout=30)
    r.raise_for_status()
    # Schwab returns the new order id in the Location header.
    location = r.headers.get("Location", "")
    order_id = location.rstrip("/").split("/")[-1] if location else None
    return {"order_id": order_id, "status_code": r.status_code, "location": location}


def replace_order(account_hash: str, order_id: str, order: Dict[str, Any]) -> Dict[str, Any]:
    v = validate_order(order)
    if not v["valid"]:
        raise ValueError(f"Refusing to replace with invalid order: {v['errors']}")
    r = httpx.put(f"{TRADER_BASE}/accounts/{account_hash}/orders/{order_id}",
                  headers=_headers(write=True), json=order, timeout=30)
    r.raise_for_status()
    return {"status_code": r.status_code}


def cancel_order(account_hash: str, order_id: str) -> Dict[str, Any]:
    r = httpx.delete(f"{TRADER_BASE}/accounts/{account_hash}/orders/{order_id}",
                     headers=_headers(), timeout=30)
    r.raise_for_status()
    return {"status_code": r.status_code}
