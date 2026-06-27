"""Schwab Market Data Production REST client (/marketdata/v1).

This is the REST quote path, entitled to apps subscribed to "Market Data
Production". Unlike the Streamer (WebSocket), it does NOT require GET User
Preference (a Trader-API endpoint), so it works for data-only apps.

Endpoints used:
  GET /marketdata/v1/quotes            — quotes for a list of symbols
  GET /marketdata/v1/{symbol}/quotes   — single-symbol quote
  GET /marketdata/v1/pricehistory      — candles
  GET /marketdata/v1/chains            — option chains
  GET /marketdata/v1/markets           — market hours
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from .oauth import get_valid_access_token

logger = logging.getLogger(__name__)

MARKETDATA_BASE = "https://api.schwabapi.com/marketdata/v1"


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {get_valid_access_token()}"}


def get_quotes(symbols: List[str], fields: Optional[str] = None) -> Dict[str, Any]:
    """Quotes for one or more symbols. Returns {symbol: {...}} keyed by symbol."""
    params: Dict[str, Any] = {"symbols": ",".join(s.upper() for s in symbols)}
    if fields:
        params["fields"] = fields
    r = httpx.get(f"{MARKETDATA_BASE}/quotes", headers=_headers(),
                  params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_price_history(symbol: str, period_type: str = "month", period: int = 1,
                      frequency_type: str = "daily", frequency: int = 1,
                      start_ms: Optional[int] = None, end_ms: Optional[int] = None,
                      need_extended: bool = False) -> Dict[str, Any]:
    """Historical candles for a symbol."""
    params: Dict[str, Any] = {
        "symbol": symbol.upper(), "periodType": period_type, "period": period,
        "frequencyType": frequency_type, "frequency": frequency,
        "needExtendedHoursData": str(need_extended).lower(),
    }
    if start_ms is not None:
        params["startDate"] = start_ms
    if end_ms is not None:
        params["endDate"] = end_ms
    r = httpx.get(f"{MARKETDATA_BASE}/pricehistory", headers=_headers(),
                  params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_option_chain(symbol: str, contract_type: str = "ALL",
                     strike_count: Optional[int] = None,
                     from_date: Optional[str] = None,
                     to_date: Optional[str] = None) -> Dict[str, Any]:
    """Option chain for an underlying."""
    params: Dict[str, Any] = {"symbol": symbol.upper(), "contractType": contract_type}
    if strike_count is not None:
        params["strikeCount"] = strike_count
    if from_date:
        params["fromDate"] = from_date
    if to_date:
        params["toDate"] = to_date
    r = httpx.get(f"{MARKETDATA_BASE}/chains", headers=_headers(),
                  params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def simplify_quotes(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Flatten the verbose quotes response to the fields Athena agents need."""
    out: Dict[str, Dict[str, Any]] = {}
    for sym, payload in raw.items():
        q = payload.get("quote", {}) or {}
        ref = payload.get("reference", {}) or {}
        out[sym] = {
            "symbol": sym,
            "asset_type": payload.get("assetMainType"),
            "last_price": q.get("lastPrice"),
            "bid_price": q.get("bidPrice"),
            "ask_price": q.get("askPrice"),
            "bid_size": q.get("bidSize"),
            "ask_size": q.get("askSize"),
            "total_volume": q.get("totalVolume"),
            "open_price": q.get("openPrice"),
            "high_price": q.get("highPrice"),
            "low_price": q.get("lowPrice"),
            "close_price": q.get("closePrice"),
            "net_change": q.get("netChange"),
            "net_percent_change": q.get("netPercentChange"),
            "week52_high": q.get("52WeekHigh"),
            "week52_low": q.get("52WeekLow"),
            "pe_ratio": q.get("peRatio"),
            "mark": q.get("mark"),
            "quote_time": q.get("quoteTime"),
            "security_status": payload.get("ssid") and q.get("securityStatus"),
            "description": ref.get("description"),
            "exchange": ref.get("exchangeName"),
            "delayed": payload.get("realtime") is False,
        }
    return out
