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


# --------------------------------------------------------------------------- #
# Spec conformance — the Schwab "Place Order Samples" MUST all validate, and the
# instruction×assetType matrix + structural rules MUST reject bad orders locally
# (fail-loud, don't rely on a server 400). These are golden fixtures copied from
# the Accounts and Trading Production spec.
# --------------------------------------------------------------------------- #
SPEC_VALID_ORDERS = {
    "buy_market_stock": {"orderType": "MARKET", "session": "NORMAL", "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "BUY", "quantity": 15, "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]},
    "buy_limit_option": {"complexOrderStrategyType": "NONE", "orderType": "LIMIT", "session": "NORMAL", "price": "6.45", "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "BUY_TO_OPEN", "quantity": 10, "instrument": {"symbol": "XYZ   240315C00500000", "assetType": "OPTION"}}]},
    "vertical_call_spread": {"orderType": "NET_DEBIT", "session": "NORMAL", "price": "0.10", "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "BUY_TO_OPEN", "quantity": 2, "instrument": {"symbol": "XYZ   240315P00045000", "assetType": "OPTION"}}, {"instruction": "SELL_TO_OPEN", "quantity": 2, "instrument": {"symbol": "XYZ   240315P00043000", "assetType": "OPTION"}}]},
    "oto_trigger": {"orderType": "LIMIT", "session": "NORMAL", "price": "34.97", "duration": "DAY", "orderStrategyType": "TRIGGER", "orderLegCollection": [{"instruction": "BUY", "quantity": 10, "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}], "childOrderStrategies": [{"orderType": "LIMIT", "session": "NORMAL", "price": "42.03", "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "SELL", "quantity": 10, "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]}]},
    "oco": {"orderStrategyType": "OCO", "childOrderStrategies": [{"orderType": "LIMIT", "session": "NORMAL", "price": "45.97", "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "SELL", "quantity": 2, "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]}, {"orderType": "STOP_LIMIT", "session": "NORMAL", "price": "37.00", "stopPrice": "37.03", "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "SELL", "quantity": 2, "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]}]},
    "trigger_oco": {"orderStrategyType": "TRIGGER", "session": "NORMAL", "duration": "DAY", "orderType": "LIMIT", "price": 14.97, "orderLegCollection": [{"instruction": "BUY", "quantity": 5, "instrument": {"assetType": "EQUITY", "symbol": "XYZ"}}], "childOrderStrategies": [{"orderStrategyType": "OCO", "childOrderStrategies": [{"orderStrategyType": "SINGLE", "session": "NORMAL", "duration": "GOOD_TILL_CANCEL", "orderType": "LIMIT", "price": 15.27, "orderLegCollection": [{"instruction": "SELL", "quantity": 5, "instrument": {"assetType": "EQUITY", "symbol": "XYZ"}}]}, {"orderStrategyType": "SINGLE", "session": "NORMAL", "duration": "GOOD_TILL_CANCEL", "orderType": "STOP", "stopPrice": 11.27, "orderLegCollection": [{"instruction": "SELL", "quantity": 5, "instrument": {"assetType": "EQUITY", "symbol": "XYZ"}}]}]}]},
    "trailing_stop": {"complexOrderStrategyType": "NONE", "orderType": "TRAILING_STOP", "session": "NORMAL", "stopPriceLinkBasis": "BID", "stopPriceLinkType": "VALUE", "stopPriceOffset": 10, "duration": "DAY", "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "SELL", "quantity": 10, "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]},
}


@pytest.mark.parametrize("name", list(SPEC_VALID_ORDERS))
def test_spec_sample_orders_all_validate(name):
    assert T.validate_order(SPEC_VALID_ORDERS[name])["valid"] is True, name


@pytest.mark.parametrize("instruction,asset,ok", [
    ("BUY", "EQUITY", True), ("SELL", "EQUITY", True),
    ("BUY_TO_COVER", "EQUITY", True), ("SELL_SHORT", "EQUITY", True),
    ("BUY_TO_OPEN", "OPTION", True), ("BUY_TO_CLOSE", "OPTION", True),
    ("SELL_TO_OPEN", "OPTION", True), ("SELL_TO_CLOSE", "OPTION", True),
    ("BUY", "OPTION", False), ("SELL", "OPTION", False),
    ("BUY_TO_OPEN", "EQUITY", False), ("BUY_TO_CLOSE", "EQUITY", False),
    ("SELL_TO_OPEN", "EQUITY", False), ("SELL_TO_CLOSE", "EQUITY", False),
    ("SELL_SHORT", "OPTION", False), ("BUY_TO_COVER", "OPTION", False),
])
def test_instruction_asset_matrix(instruction, asset, ok):
    order = {"orderType": "MARKET", "orderStrategyType": "SINGLE",
             "orderLegCollection": [{"instruction": instruction, "quantity": 1,
                                     "instrument": {"symbol": "XYZ", "assetType": asset}}]}
    assert T.validate_order(order)["valid"] is ok


def test_validate_rejects_garbage_strategy_type():
    order = {"orderStrategyType": "BOGUS", "orderType": "LIMIT", "price": "1",
             "orderLegCollection": [{"instruction": "BUY", "quantity": 1,
                                     "instrument": {"symbol": "XYZ", "assetType": "EQUITY"}}]}
    assert T.validate_order(order)["valid"] is False


def test_validate_rejects_empty_order():
    assert T.validate_order({"orderStrategyType": "SINGLE", "orderType": "MARKET"})["valid"] is False


def test_validate_rejects_missing_symbol():
    order = {"orderType": "MARKET", "orderStrategyType": "SINGLE",
             "orderLegCollection": [{"instruction": "BUY", "quantity": 1,
                                     "instrument": {"assetType": "EQUITY"}}]}
    assert T.validate_order(order)["valid"] is False


def test_validate_rejects_zero_and_noninteger_quantity():
    for bad in (0, -1, 1.5, "1", True):
        order = {"orderType": "MARKET", "orderStrategyType": "SINGLE",
                 "orderLegCollection": [{"instruction": "BUY", "quantity": bad,
                                         "instrument": {"symbol": "X", "assetType": "EQUITY"}}]}
        assert T.validate_order(order)["valid"] is False, bad


def test_validate_rejects_futures_asset_for_order_entry():
    order = {"orderType": "MARKET", "orderStrategyType": "SINGLE",
             "orderLegCollection": [{"instruction": "BUY", "quantity": 1,
                                     "instrument": {"symbol": "/ES", "assetType": "FUTURE"}}]}
    assert T.validate_order(order)["valid"] is False


def test_validate_rejects_oco_without_children():
    assert T.validate_order({"orderStrategyType": "OCO"})["valid"] is False


# --------------------------------------------------------------------------- #
# Header contract: Content-Type only on JSON-body writes (GET/DELETE bodyless).
# Regression for the 2026-07-08 bug where `Content-Type: application/json` on a
# bodyless GET made Schwab's gateway 400 (body reading "500 Internal Server
# Error"), which masqueraded as intermittent accounts-API flapping.
# --------------------------------------------------------------------------- #
def test_read_headers_omit_content_type(monkeypatch):
    monkeypatch.setattr(T, "get_valid_access_token", lambda app: "tok")
    h = T._headers()  # default = read
    assert h.get("Accept") == "application/json"
    assert "Content-Type" not in h


def test_write_headers_include_content_type(monkeypatch):
    monkeypatch.setattr(T, "get_valid_access_token", lambda app: "tok")
    h = T._headers(write=True)
    assert h.get("Content-Type") == "application/json"
    assert h.get("Accept") == "application/json"


# --------------------------------------------------------------------------- #
# OAuth state (CSRF/replay) + invalid_grant re-consent signal
# --------------------------------------------------------------------------- #
def test_state_generated_and_verified(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path / ".athena"))
    from schwab_marketdata import oauth as O
    importlib.reload(O)
    monkeypatch.setenv("SCHWAB_APP_KEY", "k"); monkeypatch.setenv("SCHWAB_APP_SECRET", "s")
    url = O.build_authorization_url(O.MARKETDATA_APP, use_state=True)
    assert "response_type=code" in url and "state=" in url
    import urllib.parse as up
    q = up.parse_qs(up.urlparse(url).query)
    issued = q["state"][0]
    # correct state verifies (and is consumed = single-use)
    assert O.verify_state(issued, O.MARKETDATA_APP) is True
    assert O.verify_state(issued, O.MARKETDATA_APP) is True  # consumed -> no stored state -> ok/no-op
    # a fresh issue + wrong state fails
    O.build_authorization_url(O.MARKETDATA_APP, use_state=True)
    assert O.verify_state("WRONG", O.MARKETDATA_APP) is False


def test_exchange_requires_state_when_asked(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path / ".athena"))
    from schwab_marketdata import oauth as O
    importlib.reload(O)
    monkeypatch.setenv("SCHWAB_APP_KEY", "k"); monkeypatch.setenv("SCHWAB_APP_SECRET", "s")
    O.build_authorization_url(O.MARKETDATA_APP, use_state=True)
    with pytest.raises(RuntimeError, match="state mismatch"):
        O.exchange_code_for_tokens("code123", O.MARKETDATA_APP,
                                   returned_state="bad", require_state=True)


def test_refresh_invalid_grant_raises_reconsent(tmp_path, monkeypatch):
    import importlib
    from unittest import mock
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path / ".athena"))
    from schwab_marketdata import oauth as O
    importlib.reload(O)
    monkeypatch.setenv("SCHWAB_APP_KEY", "k"); monkeypatch.setenv("SCHWAB_APP_SECRET", "s")
    ts = _ts()  # valid clock
    resp = mock.MagicMock(status_code=400)
    resp.text = '{"error":"invalid_grant","error_description":"revoked"}'
    with mock.patch.object(O.httpx, "post", return_value=resp):
        with pytest.raises(O.RefreshTokenInvalid, match="invalid_grant"):
            O.refresh_access_token(ts, O.MARKETDATA_APP)
