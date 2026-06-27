"""Tests for the Schwab OAuth token logic and Trader order builder/validator.

No network: httpx calls are not exercised here; we test pure logic (token
validity math, order payload construction, instruction validation).
"""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schwab_marketdata import trader as T  # noqa: E402
from schwab_marketdata.oauth import TokenSet  # noqa: E402


# --------------------------------------------------------------------------- #
# Token validity math
# --------------------------------------------------------------------------- #
def _ts(access_in=1800, refresh_in_days=7):
    now = time.time()
    return TokenSet(access_token="A", refresh_token="R",
                    access_expires_at=now + access_in,
                    refresh_expires_at=now + refresh_in_days * 86400)


def test_access_valid_when_fresh():
    assert _ts().access_valid() is True


def test_access_invalid_within_skew():
    # Inside the 300s refresh skew -> treated as needing refresh.
    assert _ts(access_in=120).access_valid() is False


def test_access_invalid_when_expired():
    assert _ts(access_in=-10).access_valid() is False


def test_refresh_valid_and_expired():
    assert _ts(refresh_in_days=1).refresh_valid() is True
    assert _ts(refresh_in_days=-1).refresh_valid() is False


def test_from_token_response_sets_expiries():
    body = {"access_token": "AA", "refresh_token": "RR", "expires_in": 1800,
            "scope": "api", "id_token": "JWT"}
    ts = TokenSet.from_token_response(body)
    assert ts.access_token == "AA"
    assert ts.refresh_token == "RR"
    assert ts.id_token == "JWT"
    assert ts.access_valid() is True
    assert ts.refresh_valid() is True


# --------------------------------------------------------------------------- #
# Order builder + instruction validation
# --------------------------------------------------------------------------- #
def test_build_equity_market_order():
    o = T.build_single_order("XYZ", "EQUITY", "BUY", 15, order_type="MARKET")
    assert o["orderType"] == "MARKET"
    assert o["orderStrategyType"] == "SINGLE"
    leg = o["orderLegCollection"][0]
    assert leg["instruction"] == "BUY"
    assert leg["quantity"] == 15
    assert leg["instrument"] == {"symbol": "XYZ", "assetType": "EQUITY"}
    assert "price" not in o


def test_build_option_limit_order():
    o = T.build_single_order("XYZ   240315C00500000", "OPTION", "BUY_TO_OPEN",
                             10, order_type="LIMIT", price=6.45)
    assert o["price"] == "6.45"
    assert o["orderLegCollection"][0]["instruction"] == "BUY_TO_OPEN"
    assert o["orderLegCollection"][0]["instrument"]["assetType"] == "OPTION"


def test_equity_rejects_option_instruction():
    with pytest.raises(ValueError, match="invalid for EQUITY"):
        T.build_single_order("XYZ", "EQUITY", "BUY_TO_OPEN", 1)


def test_option_rejects_equity_instruction():
    with pytest.raises(ValueError, match="invalid for OPTION"):
        T.build_single_order("XYZ   240315C00500000", "OPTION", "BUY", 1)


def test_futures_order_entry_rejected():
    with pytest.raises(ValueError, match="does not support futures"):
        T.build_single_order("/ESZ25", "FUTURE", "BUY", 1)


def test_limit_requires_price():
    with pytest.raises(ValueError, match="requires a price"):
        T.build_single_order("XYZ", "EQUITY", "BUY", 1, order_type="LIMIT")


def test_stop_limit_requires_stop_price():
    with pytest.raises(ValueError, match="requires a stopPrice"):
        T.build_single_order("XYZ", "EQUITY", "SELL", 1, order_type="STOP_LIMIT", price=10)


def test_quantity_must_be_positive():
    with pytest.raises(ValueError, match="quantity must be positive"):
        T.build_single_order("XYZ", "EQUITY", "BUY", 0)


def test_validate_order_catches_bad_nested_leg():
    # OCO with one valid + one invalid (option instruction on equity)
    order = {"orderStrategyType": "OCO", "childOrderStrategies": [
        {"orderType": "LIMIT", "orderLegCollection": [
            {"instruction": "SELL", "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]},
        {"orderType": "STOP", "orderLegCollection": [
            {"instruction": "BUY_TO_OPEN", "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]},
    ]}
    result = T.validate_order(order)
    assert result["valid"] is False
    assert any("invalid for EQUITY" in e for e in result["errors"])


def test_validate_good_vertical_spread():
    order = {"orderType": "NET_DEBIT", "price": "0.10", "orderStrategyType": "SINGLE",
             "orderLegCollection": [
                 {"instruction": "BUY_TO_OPEN", "quantity": 2,
                  "instrument": {"symbol": "XYZ   240315P00045000", "assetType": "OPTION"}},
                 {"instruction": "SELL_TO_OPEN", "quantity": 2,
                  "instrument": {"symbol": "XYZ   240315P00043000", "assetType": "OPTION"}}]}
    assert T.validate_order(order)["valid"] is True
