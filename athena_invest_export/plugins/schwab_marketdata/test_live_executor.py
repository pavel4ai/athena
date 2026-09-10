"""Tests for the money-safe live executor. No live network; trader is mocked.

Verifies the fail-closed safety gates from PRE_LIVE_MONEY_SAFETY.md:
  - config fails closed (missing / kill_switch / mode)
  - allow-list / deny-list enforcement
  - idempotency replay (no double-fill) + collision detection
  - daily order-limit
  - account-hash resolution fails closed on a flapping/empty accounts API
  - integer-cents money helpers
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest import mock

import pytest


CONFIG_LIVE = """# cfg
```
mode: live
kill_switch: off
order_limit_per_day: 10
```
```
allow: 568
deny: 892
deny: 726
deny: 331
```
"""

CONFIG_MOCK = CONFIG_LIVE.replace("mode: live", "mode: mock")
CONFIG_KILL = CONFIG_LIVE.replace("kill_switch: off", "kill_switch: on")

ORDER = {
    "orderType": "MARKET", "session": "NORMAL", "duration": "DAY",
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [{
        "instruction": "BUY", "quantity": 1,
        "instrument": {"symbol": "SPY", "assetType": "EQUITY"}}],
}

ACCT_NUMS = [
    {"accountNumber": "11111568", "hashValue": "HASH_568"},
    {"accountNumber": "22222892", "hashValue": "HASH_892"},
]


@pytest.fixture
def le(tmp_path, monkeypatch):
    """Fresh live_executor bound to a temp ATHENA_HOME, with a live config."""
    home = tmp_path / ".athena"
    (home / "athena_invest" / "schwab").mkdir(parents=True)
    monkeypatch.setenv("ATHENA_HOME", str(home))
    import schwab_marketdata.live_executor as m
    importlib.reload(m)
    # default config = live, kill off
    m._config_path().write_text(CONFIG_LIVE)
    # mode.json must also say live for the stricter-of-two gate
    from schwab_marketdata import mode as mode_mod
    importlib.reload(mode_mod)
    mode_mod.set_mode("live")
    return m


def _mock_trader(le, place_ok=True):
    """Patch trader used by the executor with a fake that never hits network."""
    t = mock.MagicMock()
    t.validate_order.return_value = {"valid": True, "errors": []}
    t.get_account_numbers.return_value = ACCT_NUMS
    t.preview_order.return_value = {"orderValidationResult": {}}  # clean preview
    t.place_order.return_value = {"order_id": "OID1", "status_code": 201}
    t.get_order.return_value = {"orderId": "OID1", "status": "WORKING"}
    return mock.patch.object(le, "trader", t), t


# --- money helpers ---------------------------------------------------------
def test_integer_cents_no_float_drift(le):
    assert le.to_cents("10.10") == 1010
    assert le.to_cents(0.1) + le.to_cents(0.2) == 30  # 0.1+0.2 float trap
    assert le.cents_to_str(1010) == "10.10"
    assert le.cents_to_str(-5) == "-0.05"


# --- config fail-closed ----------------------------------------------------
def test_config_missing_fails_closed(le):
    le._config_path().unlink()
    cfg = le.load_config()
    assert not cfg.raw_ok and cfg.kill_switch is True  # HALT default


def test_kill_switch_default_true_when_unparsed(le):
    le._config_path().write_text("no fenced blocks here")
    cfg = le.load_config()
    assert cfg.kill_switch is True and not cfg.raw_ok


# --- gates -----------------------------------------------------------------
def test_kill_switch_on_rejects(le):
    le._config_path().write_text(CONFIG_KILL)
    p, t = _mock_trader(le)
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568"})
    assert not r["success"] and "kill_switch" in r["reason"]
    t.place_order.assert_not_called()


def test_mock_mode_rejects_live_order(le):
    le._config_path().write_text(CONFIG_MOCK)
    p, t = _mock_trader(le)
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568"})
    assert not r["success"] and "live mode" in r["reason"]
    t.place_order.assert_not_called()


def test_denied_account_rejected_before_schwab(le):
    p, t = _mock_trader(le)
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "892"})
    assert not r["success"] and "not cleared" in r["reason"]
    t.place_order.assert_not_called()


def test_unknown_account_rejected(le):
    p, t = _mock_trader(le)
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "999"})
    assert not r["success"]
    t.place_order.assert_not_called()


def test_missing_account_suffix_rejected(le):
    p, t = _mock_trader(le)
    with p:
        r = le.place_live_order(ORDER, {})
    assert not r["success"] and "account_suffix" in r["reason"]
    t.place_order.assert_not_called()


def test_allowed_account_places_and_verifies(le):
    p, t = _mock_trader(le)
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568"})
    assert r["success"] and r["status"] == "PLACED" and r["order_id"] == "OID1"
    # placed against the resolved hash for 568, never the denied one
    t.place_order.assert_called_once()
    assert t.place_order.call_args[0][0] == "HASH_568"
    # preview was consulted before placing
    t.preview_order.assert_called_once()


def test_preview_reject_blocks_placement(le):
    p, t = _mock_trader(le)
    t.preview_order.return_value = {"orderValidationResult": {
        "rejects": [{"validationRuleType": "REJECT", "message": "insufficient buying power"}]}}
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568"})
    assert not r["success"] and "preview rejected" in r["reason"]
    t.place_order.assert_not_called()


def test_preview_error_fails_closed(le):
    p, t = _mock_trader(le)
    t.preview_order.side_effect = RuntimeError("preview 500")
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568"})
    assert not r["success"] and "preview failed" in r["reason"]
    t.place_order.assert_not_called()


# --- idempotency -----------------------------------------------------------
def test_idempotent_replay_no_double_fill(le):
    p, t = _mock_trader(le)
    with p:
        r1 = le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "K1"})
        r2 = le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "K1"})
    assert r1["success"] and r2["success"]
    assert r2.get("idempotent_replay") is True
    assert t.place_order.call_count == 1  # placed exactly once


def test_idempotency_collision_rejected(le):
    p, t = _mock_trader(le)
    other = {**ORDER, "orderLegCollection": [{
        "instruction": "BUY", "quantity": 999,
        "instrument": {"symbol": "SPY", "assetType": "EQUITY"}}]}
    with p:
        le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "K1"})
        r = le.place_live_order(other, {"account_suffix": "568", "idempotency_key": "K1"})
    assert not r["success"] and "collision" in r["reason"]
    assert t.place_order.call_count == 1  # the different order was NOT placed


# --- no global daily order counter -----------------------------------------
def test_legacy_daily_limit_config_does_not_block_approved_orders(le):
    """Human-approved, idempotent orders are not capped by a global UTC-day count."""
    cfg = CONFIG_LIVE.replace("order_limit_per_day: 10", "order_limit_per_day: 2")
    le._config_path().write_text(cfg)
    p, t = _mock_trader(le)
    with p:
        a = le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "A"})
        b = le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "B"})
        c = le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "C"})
    assert a["success"] and b["success"] and c["success"]
    assert t.place_order.call_count == 3


# --- hash resolution fails closed on flapping API --------------------------
def test_hash_resolution_fails_closed_on_api_error(le):
    p, t = _mock_trader(le)
    t.get_account_numbers.side_effect = RuntimeError("500 flap")
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568"})
    assert not r["success"] and "cannot confirm account hash" in r["reason"]
    t.place_order.assert_not_called()


# --- event log is append-only + replayable ---------------------------------
def test_ledger_records_events(le):
    p, t = _mock_trader(le)
    with p:
        le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "K1"})
    events = le.replay_events()
    types = [e["type"] for e in events]
    assert "ORDER_INTENT" in types and "ORDER_PLACED" in types
    # every event carries a timestamp
    assert all("ts_ms" in e for e in events)


# --- schema-driven parsers (previewOrder / status / balances) --------------
def test_preview_severity_model(le):
    # REJECT severity in any bucket blocks; overrideSeverity beats original.
    reject = {"orderValidationResult": {"reviews": [
        {"message": "needs review", "originalSeverity": "REVIEW"}]}}
    assert le._preview_rejects(reject)  # REVIEW is blocking for autonomous trading
    override = {"orderValidationResult": {"alerts": [
        {"message": "escalated", "originalSeverity": "ALERT", "overrideSeverity": "REJECT"}]}}
    assert le._preview_rejects(override)  # override REJECT blocks
    clean = {"orderValidationResult": {"accepts": [
        {"message": "ok", "originalSeverity": "ACCEPT"}], "warns": [
        {"message": "fyi", "originalSeverity": "ALERT"}]}}
    assert le._preview_rejects(clean) == []  # accept + alert are non-blocking


def test_preview_cost_estimate_cents(le):
    preview = {"commissionAndFee": {
        "commission": {"commissionLegs": [{"commissionValues": [
            {"value": 0.65, "type": "COMMISSION"}]}]},
        "fee": {"feeLegs": [{"feeValues": [
            {"value": 0.01, "type": "SEC_FEE"}, {"value": 0.02, "type": "TAF_FEE"}]}]}}}
    assert le.preview_cost_estimate(preview) == 68  # 0.65 + 0.01 + 0.02 = 0.68


def test_status_classifier(le):
    assert le.classify_order_status("FILLED") == "filled"
    assert le.classify_order_status("REJECTED") == "bad"
    assert le.classify_order_status("CANCELED") == "bad"
    assert le.classify_order_status("EXPIRED") == "bad"
    assert le.classify_order_status("WORKING") == "live"
    assert le.classify_order_status("QUEUED") == "live"
    assert le.classify_order_status("SOMETHING_NEW") == "unknown"


def test_reconcile_cash_account_reads_initial_balances(le):
    # A CASH account keeps cashBalance/liquidationValue on initialBalances.
    p, t = _mock_trader(le)
    t.get_account.return_value = {"securitiesAccount": {
        "type": "CASH", "accountNumber": "11111568",
        "currentBalances": {"cashAvailableForTrading": 9000.0, "totalCash": 10000.0},
        "initialBalances": {"cashBalance": 10000.0, "liquidationValue": 10000.0},
        "positions": [{"instrument": {"symbol": "SPY"}, "longQuantity": 3, "shortQuantity": 0}]}}
    with p:
        rec = le.reconcile("568")
    assert rec["ok"] and rec["account_type"] == "CASH"
    assert rec["schwab_cash"] == 10000.0        # from initialBalances, not None
    assert rec["schwab_nav"] == 10000.0          # from initialBalances
    assert rec["schwab_positions"]["SPY"] == 3   # net long-short


def test_read_back_terminal_bad_status_not_verified(le):
    p, t = _mock_trader(le)
    t.get_order.return_value = {"orderId": "OID1", "status": "REJECTED"}
    with p:
        r = le.place_live_order(ORDER, {"account_suffix": "568", "idempotency_key": "RB1"})
    # order was placed (HTTP ok) but read-back shows REJECTED -> verified False
    assert r["success"] is True and r["verified"] is False
    assert r["status_class"] == "bad"
