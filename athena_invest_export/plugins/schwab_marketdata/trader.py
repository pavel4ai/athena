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

from .oauth import TRADER_BASE, get_valid_access_token

logger = logging.getLogger(__name__)

# Instruction validity matrix (Schwab spec).
EQUITY_INSTRUCTIONS = {"BUY", "SELL", "BUY_TO_COVER", "SELL_SHORT"}
OPTION_INSTRUCTIONS = {"BUY_TO_OPEN", "BUY_TO_CLOSE", "SELL_TO_OPEN", "SELL_TO_CLOSE"}

VALID_ORDER_TYPES = {
    "MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP",
    "NET_DEBIT", "NET_CREDIT", "NET_ZERO",
}
VALID_DURATIONS = {"DAY", "GOOD_TILL_CANCEL", "FILL_OR_KILL"}
VALID_SESSIONS = {"NORMAL", "AM", "PM", "SEAMLESS"}


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {get_valid_access_token()}",
            "Content-Type": "application/json"}


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


def get_transactions(account_hash: str, start: str, end: str,
                     types: str = "TRADE") -> List[Dict[str, Any]]:
    r = httpx.get(f"{TRADER_BASE}/accounts/{account_hash}/transactions",
                  headers=_headers(),
                  params={"startDate": start, "endDate": end, "types": types},
                  timeout=30)
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

    Returns {"valid": bool, "errors": [...]} without raising, so callers can
    surface problems in a preview.
    """
    errors: List[str] = []

    def _check_legs(o: Dict[str, Any]):
        for leg in o.get("orderLegCollection", []):
            inst = leg.get("instruction", "")
            atype = leg.get("instrument", {}).get("assetType", "")
            try:
                _validate_leg(inst, atype)
            except ValueError as e:
                errors.append(str(e))
        for child in o.get("childOrderStrategies", []):
            _check_legs(child)

    _check_legs(order)
    return {"valid": not errors, "errors": errors}


# --------------------------------------------------------------------------- #
# Order mutation endpoints — POST-APPROVAL ONLY
# --------------------------------------------------------------------------- #
def place_order(account_hash: str, order: Dict[str, Any]) -> Dict[str, Any]:
    """POST an order. CALLER MUST HAVE A RECORDED HUMAN APPROVAL.

    Returns {"order_id": <from Location header>, "status_code": ...}.
    """
    v = validate_order(order)
    if not v["valid"]:
        raise ValueError(f"Refusing to place invalid order: {v['errors']}")
    r = httpx.post(f"{TRADER_BASE}/accounts/{account_hash}/orders",
                   headers=_headers(), json=order, timeout=30)
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
                  headers=_headers(), json=order, timeout=30)
    r.raise_for_status()
    return {"status_code": r.status_code}


def cancel_order(account_hash: str, order_id: str) -> Dict[str, Any]:
    r = httpx.delete(f"{TRADER_BASE}/accounts/{account_hash}/orders/{order_id}",
                     headers=_headers(), timeout=30)
    r.raise_for_status()
    return {"status_code": r.status_code}
