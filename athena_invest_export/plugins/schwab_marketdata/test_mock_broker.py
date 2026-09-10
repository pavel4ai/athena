"""Tests for the mock broker — paper fills on stubbed quotes (no network)."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schwab_marketdata import mock_broker as MB  # noqa: E402
from schwab_marketdata import mode as MODE  # noqa: E402


@pytest.fixture
def broker(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path))
    # stub live quotes
    quotes = {"AAPL": {"last_price": 100.0, "bid_price": 99.9, "ask_price": 100.1},
              "SPY": {"last_price": 500.0, "bid_price": 499.5, "ask_price": 500.5}}
    monkeypatch.setattr(MB, "_live_quote", lambda s: quotes[s.upper()])
    b = MB.MockBroker("test", slippage_bps=0, commission=0)
    b.fund(100000.0)
    return b


def _mkt(symbol, instr, qty):
    return {"orderType": "MARKET", "orderLegCollection": [
        {"instruction": instr, "quantity": qty,
         "instrument": {"symbol": symbol, "assetType": "EQUITY"}}]}


def _lim(symbol, instr, qty, price):
    return {"orderType": "LIMIT", "price": str(price), "orderLegCollection": [
        {"instruction": instr, "quantity": qty,
         "instrument": {"symbol": symbol, "assetType": "EQUITY"}}]}


def test_market_buy_fills_at_ask(broker):
    r = broker.place_order("MOCK", _mkt("AAPL", "BUY", 10))
    assert r["status"] == "FILLED"
    assert r["fills"][0]["price"] == 100.1  # ask
    assert broker.state["positions"]["AAPL"]["qty"] == 10
    assert broker.state["cash"] == 100000.0 - 100.1 * 10


def test_market_sell_fills_at_bid(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 10))
    cash_after_buy = broker.state["cash"]
    r = broker.place_order("MOCK", _mkt("AAPL", "SELL", 10))
    assert r["fills"][0]["price"] == 99.9  # bid
    assert "AAPL" not in broker.state["positions"]
    assert broker.state["cash"] == cash_after_buy + 99.9 * 10


def test_limit_buy_stays_working_when_above_market(broker):
    # want to buy at 95 but ask is 100.1 -> not crossable
    r = broker.place_order("MOCK", _lim("AAPL", "BUY", 5, 95.0))
    assert r["status"] == "WORKING"
    assert "AAPL" not in broker.state["positions"]


def test_limit_buy_fills_when_crossable(broker):
    r = broker.place_order("MOCK", _lim("AAPL", "BUY", 5, 101.0))  # ask 100.1 <= 101
    assert r["status"] == "FILLED"
    assert r["fills"][0]["price"] == 101.0


def test_working_order_fills_after_price_moves(broker, monkeypatch):
    r = broker.place_order("MOCK", _lim("AAPL", "BUY", 5, 95.0))
    assert r["status"] == "WORKING"
    # price drops: ask now 94 -> crossable
    monkeypatch.setattr(MB, "_live_quote",
                        lambda s: {"last_price": 94.0, "bid_price": 93.9, "ask_price": 94.0})
    filled = broker.process_working_orders()
    assert len(filled) == 1
    assert broker.state["positions"]["AAPL"]["qty"] == 5


def test_avg_price_on_add(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 10))   # @100.1
    # bump ask to 110 for the second buy
    import types
    broker.place_order("MOCK", _lim("AAPL", "BUY", 10, 120.0))  # fills @120
    pos = broker.state["positions"]["AAPL"]
    assert pos["qty"] == 20
    assert abs(pos["avg_price"] - (100.1 + 120.0) / 2) < 1e-6


def test_nav_reflects_positions(broker):
    broker.place_order("MOCK", _mkt("SPY", "BUY", 10))   # @500.5
    acct = broker.get_account()
    bal = acct["securitiesAccount"]["currentBalances"]
    # NAV = cash + market value (10 * last 500)
    assert bal["liquidationValue"] == round(broker.state["cash"] + 500.0 * 10, 2)


def test_transactions_recorded(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 3))
    txns = broker.get_transactions()
    assert len(txns) == 1
    assert txns[0]["symbol"] == "AAPL" and txns[0]["qty"] == 3


def test_state_persists(broker, tmp_path, monkeypatch):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 7))
    # reload a fresh broker from disk
    b2 = MB.MockBroker("test")
    assert b2.state["positions"]["AAPL"]["qty"] == 7


# -- mode switch -----------------------------------------------------------
def test_mode_defaults_to_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path))
    assert MODE.get_mode() == "mock"
    assert MODE.is_mock() is True


def test_mode_set_and_get(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path))
    MODE.set_mode("live")
    assert MODE.get_mode() == "live"
    assert MODE.is_mock() is False
    MODE.set_mode("mock")
    assert MODE.is_mock() is True


def test_mode_rejects_bad_value(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path))
    with pytest.raises(ValueError):
        MODE.set_mode("paper")


# -- money-safety fixes (expert review, 2026-06-27) ------------------------
def test_oversell_is_rejected(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 10))
    r = broker.place_order("MOCK", _mkt("AAPL", "SELL", 25))  # only 10 held
    assert r["status"] == "REJECTED"
    assert "oversell" in r["reason"]
    # state unchanged: still hold exactly 10, no phantom cash credited
    assert broker.state["positions"]["AAPL"]["qty"] == 10


def test_sell_with_no_position_rejected(broker):
    r = broker.place_order("MOCK", _mkt("SPY", "SELL", 1))
    assert r["status"] == "REJECTED" and "oversell" in r["reason"]
    assert "SPY" not in broker.state["positions"]


def test_short_sell_rejected(broker):
    order = {"orderType": "MARKET", "orderLegCollection": [
        {"instruction": "SELL_SHORT", "quantity": 5,
         "instrument": {"symbol": "AAPL", "assetType": "EQUITY"}}]}
    r = broker.place_order("MOCK", order)
    assert r["status"] == "REJECTED" and "short" in r["reason"].lower()


def test_idempotency_key_prevents_double_fill(broker):
    k = "preview-RH-1-leg-AAPL"
    r1 = broker.place_order("MOCK", _mkt("AAPL", "BUY", 10), idempotency_key=k)
    cash_after = broker.state["cash"]
    r2 = broker.place_order("MOCK", _mkt("AAPL", "BUY", 10), idempotency_key=k)  # retry
    assert r1["order_id"] == r2["order_id"]
    assert r2.get("idempotent_replay") is True
    # only filled once: still 10 shares, cash unchanged by the retry
    assert broker.state["positions"]["AAPL"]["qty"] == 10
    assert broker.state["cash"] == cash_after


def test_fund_refused_after_trades(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 1))
    with pytest.raises(ValueError, match="fund\\(\\) refused"):
        broker.fund(999999.0)


def test_deposit_is_additive_and_tracked(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 1))
    cash = broker.state["cash"]
    broker.deposit(5000.0)
    assert broker.state["cash"] == cash + 5000.0
    assert any(t.get("type") == "deposit" for t in broker.state["transactions"])


def test_atomic_save_leaves_no_tmp(broker):
    broker.place_order("MOCK", _mkt("AAPL", "BUY", 1))
    leftovers = list(broker.path.parent.glob("*.tmp*"))
    assert leftovers == []  # temp file renamed away, none left behind
    # and the saved file is valid JSON
    import json as _j
    _j.loads(broker.path.read_text())
