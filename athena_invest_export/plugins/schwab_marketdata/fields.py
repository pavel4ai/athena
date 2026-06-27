"""Schwab Streamer field maps and decoders.

The Schwab Streamer (WebSocket) market-data API delivers Level 1 data with
*integer* field keys (e.g. {"1": 76.08, "2": 76.49, ...}). These maps turn the
raw numeric payloads into named dicts so the rest of Athena never deals with
magic field numbers.

Source: Schwab Streamer API spec (Market Data Production), LEVELONE_* services.
Field numbers are part of the wire contract; they are deliberately frozen here.
Do NOT renumber — they mirror Schwab's documented field tables exactly.
"""

from __future__ import annotations

from typing import Any, Dict

# ---------------------------------------------------------------------------
# LEVELONE_EQUITIES — field number -> name (Schwab spec section 3.1)
# ---------------------------------------------------------------------------
LEVELONE_EQUITIES_FIELDS: Dict[str, str] = {
    "0": "symbol", "1": "bid_price", "2": "ask_price", "3": "last_price",
    "4": "bid_size", "5": "ask_size", "6": "ask_id", "7": "bid_id",
    "8": "total_volume", "9": "last_size", "10": "high_price", "11": "low_price",
    "12": "close_price", "13": "exchange_id", "14": "marginable",
    "15": "description", "16": "last_id", "17": "open_price", "18": "net_change",
    "19": "week52_high", "20": "week52_low", "21": "pe_ratio",
    "22": "annual_dividend_amount", "23": "dividend_yield", "24": "nav",
    "25": "exchange_name", "26": "dividend_date", "27": "regular_market_quote",
    "28": "regular_market_trade", "29": "regular_market_last_price",
    "30": "regular_market_last_size", "31": "regular_market_net_change",
    "32": "security_status", "33": "mark_price", "34": "quote_time",
    "35": "trade_time", "36": "regular_market_trade_time", "37": "bid_time",
    "38": "ask_time", "39": "ask_mic_id", "40": "bid_mic_id", "41": "last_mic_id",
    "42": "net_percent_change", "43": "regular_market_percent_change",
    "44": "mark_price_net_change", "45": "mark_price_percent_change",
    "46": "hard_to_borrow_quantity", "47": "hard_to_borrow_rate",
    "48": "hard_to_borrow", "49": "shortable", "50": "post_market_net_change",
    "51": "post_market_percent_change",
}

# ---------------------------------------------------------------------------
# LEVELONE_OPTIONS — field number -> name (Schwab spec section 3.2)
# ---------------------------------------------------------------------------
LEVELONE_OPTIONS_FIELDS: Dict[str, str] = {
    "0": "symbol", "1": "description", "2": "bid_price", "3": "ask_price",
    "4": "last_price", "5": "high_price", "6": "low_price", "7": "close_price",
    "8": "total_volume", "9": "open_interest", "10": "volatility",
    "11": "money_intrinsic_value", "12": "expiration_year", "13": "multiplier",
    "14": "digits", "15": "open_price", "16": "bid_size", "17": "ask_size",
    "18": "last_size", "19": "net_change", "20": "strike_price",
    "21": "contract_type", "22": "underlying", "23": "expiration_month",
    "24": "deliverables", "25": "time_value", "26": "expiration_day",
    "27": "days_to_expiration", "28": "delta", "29": "gamma", "30": "theta",
    "31": "vega", "32": "rho", "33": "security_status",
    "34": "theoretical_option_value", "35": "underlying_price",
    "36": "uv_expiration_type", "37": "mark_price", "38": "quote_time",
    "39": "trade_time", "40": "exchange", "41": "exchange_name",
    "42": "last_trading_day", "43": "settlement_type", "44": "net_percent_change",
    "45": "mark_price_net_change", "46": "mark_price_percent_change",
    "47": "implied_yield", "48": "is_penny_pilot", "49": "option_root",
    "50": "week52_high", "51": "week52_low", "52": "indicative_ask_price",
    "53": "indicative_bid_price", "54": "indicative_quote_time",
    "55": "exercise_type",
}

# ---------------------------------------------------------------------------
# LEVELONE_FUTURES — field number -> name (Schwab spec section 3.3)
# ---------------------------------------------------------------------------
LEVELONE_FUTURES_FIELDS: Dict[str, str] = {
    "0": "symbol", "1": "bid_price", "2": "ask_price", "3": "last_price",
    "4": "bid_size", "5": "ask_size", "6": "bid_id", "7": "ask_id",
    "8": "total_volume", "9": "last_size", "10": "quote_time", "11": "trade_time",
    "12": "high_price", "13": "low_price", "14": "close_price",
    "15": "exchange_id", "16": "description", "17": "last_id", "18": "open_price",
    "19": "net_change", "20": "future_percent_change", "21": "exchange_name",
    "22": "security_status", "23": "open_interest", "24": "mark", "25": "tick",
    "26": "tick_amount", "27": "product", "28": "future_price_format",
    "29": "future_trading_hours", "30": "future_is_tradable",
    "31": "future_multiplier", "32": "future_is_active",
    "33": "future_settlement_price", "34": "future_active_symbol",
    "35": "future_expiration_date", "36": "expiration_style", "37": "ask_time",
    "38": "bid_time", "39": "quoted_in_session", "40": "settlement_date",
}

# ---------------------------------------------------------------------------
# LEVELONE_FUTURES_OPTIONS — field number -> name (Schwab spec section 3.4)
# ---------------------------------------------------------------------------
LEVELONE_FUTURES_OPTIONS_FIELDS: Dict[str, str] = {
    "0": "symbol", "1": "bid_price", "2": "ask_price", "3": "last_price",
    "4": "bid_size", "5": "ask_size", "6": "bid_id", "7": "ask_id",
    "8": "total_volume", "9": "last_size", "10": "quote_time", "11": "trade_time",
    "12": "high_price", "13": "low_price", "14": "close_price", "15": "last_id",
    "16": "description", "17": "open_price", "18": "open_interest", "19": "mark",
    "20": "tick", "21": "tick_amount", "22": "future_multiplier",
    "23": "future_settlement_price", "24": "underlying_symbol",
    "25": "strike_price", "26": "future_expiration_date", "27": "expiration_style",
    "28": "contract_type", "29": "security_status", "30": "exchange",
    "31": "exchange_name",
}

# ---------------------------------------------------------------------------
# LEVELONE_FOREX — field number -> name (Schwab spec section 3.5)
# ---------------------------------------------------------------------------
LEVELONE_FOREX_FIELDS: Dict[str, str] = {
    "0": "symbol", "1": "bid_price", "2": "ask_price", "3": "last_price",
    "4": "bid_size", "5": "ask_size", "6": "total_volume", "7": "last_size",
    "8": "quote_time", "9": "trade_time", "10": "high_price", "11": "low_price",
    "12": "close_price", "13": "exchange", "14": "description", "15": "open_price",
    "16": "net_change", "17": "percent_change", "18": "exchange_name",
    "19": "digits", "20": "security_status", "21": "tick", "22": "tick_amount",
    "23": "product", "24": "trading_hours", "25": "is_tradable",
    "26": "market_maker", "27": "week52_high", "28": "week52_low", "29": "mark",
}

# ---------------------------------------------------------------------------
# CHART_EQUITY — field number -> name (Schwab spec section 5.1)
# ---------------------------------------------------------------------------
CHART_EQUITY_FIELDS: Dict[str, str] = {
    "0": "key", "1": "open_price", "2": "high_price", "3": "low_price",
    "4": "close_price", "5": "volume", "6": "sequence", "7": "chart_time",
    "8": "chart_day",
}

# ---------------------------------------------------------------------------
# CHART_FUTURES — field number -> name (Schwab spec section 5.2)
# ---------------------------------------------------------------------------
CHART_FUTURES_FIELDS: Dict[str, str] = {
    "0": "key", "1": "chart_time", "2": "open_price", "3": "high_price",
    "4": "low_price", "5": "close_price", "6": "volume",
}

# Service name -> field map
SERVICE_FIELD_MAPS: Dict[str, Dict[str, str]] = {
    "LEVELONE_EQUITIES": LEVELONE_EQUITIES_FIELDS,
    "LEVELONE_OPTIONS": LEVELONE_OPTIONS_FIELDS,
    "LEVELONE_FUTURES": LEVELONE_FUTURES_FIELDS,
    "LEVELONE_FUTURES_OPTIONS": LEVELONE_FUTURES_OPTIONS_FIELDS,
    "LEVELONE_FOREX": LEVELONE_FOREX_FIELDS,
    "CHART_EQUITY": CHART_EQUITY_FIELDS,
    "CHART_FUTURES": CHART_FUTURES_FIELDS,
}

# Full field id lists (for "give me everything" subscriptions), per service.
SERVICE_ALL_FIELDS: Dict[str, str] = {
    svc: ",".join(str(i) for i in range(len(fmap)))
    for svc, fmap in SERVICE_FIELD_MAPS.items()
}

# Streamer response codes (spec section 1.4). code -> (name, severs_connection)
RESPONSE_CODES: Dict[int, tuple] = {
    0: ("SUCCESS", False),
    3: ("LOGIN_DENIED", True),
    9: ("UNKNOWN_FAILURE", None),
    11: ("SERVICE_NOT_AVAILABLE", False),
    12: ("CLOSE_CONNECTION", True),       # max 1 connection per user
    19: ("REACHED_SYMBOL_LIMIT", False),
    20: ("STREAM_CONN_NOT_FOUND", None),
    21: ("BAD_COMMAND_FORMAT", False),
    22: ("FAILED_COMMAND_SUBS", False),
    23: ("FAILED_COMMAND_UNSUBS", False),
    24: ("FAILED_COMMAND_ADD", False),
    25: ("FAILED_COMMAND_VIEW", False),
    26: ("SUCCEEDED_COMMAND_SUBS", False),
    27: ("SUCCEEDED_COMMAND_UNSUBS", False),
    28: ("SUCCEEDED_COMMAND_ADD", False),
    29: ("SUCCEEDED_COMMAND_VIEW", False),
    30: ("STOP_STREAMING", True),
}

# Metadata keys that ride alongside numbered fields in a data row.
_PASSTHROUGH_KEYS = {
    "key", "delayed", "assetMainType", "assetSubType", "cusip", "seq",
}


def decode_row(service: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """Decode one streamer data row from numbered fields to named fields.

    Unknown numeric keys are preserved under "field_<n>" so nothing is silently
    dropped if Schwab adds a field before this map is updated. Passthrough
    metadata keys (key, delayed, cusip, ...) are kept as-is.
    """
    fmap = SERVICE_FIELD_MAPS.get(service, {})
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if k in _PASSTHROUGH_KEYS:
            out[k] = v
        elif k in fmap:
            out[fmap[k]] = v
        elif k.isdigit():
            out[f"field_{k}"] = v
        else:
            out[k] = v
    return out


def decode_data_message(msg: Dict[str, Any]) -> list:
    """Decode a full {"data": [...]} streamer message into named rows.

    Returns a list of {"service", "timestamp", "command", "rows": [...]} dicts.
    """
    result = []
    for block in msg.get("data", []):
        service = block.get("service", "")
        result.append({
            "service": service,
            "timestamp": block.get("timestamp"),
            "command": block.get("command"),
            "rows": [decode_row(service, r) for r in block.get("content", [])],
        })
    return result
