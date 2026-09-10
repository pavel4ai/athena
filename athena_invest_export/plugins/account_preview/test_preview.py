from __future__ import annotations

import importlib.util
import json
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

PLUGIN_PATH = Path(__file__).with_name("__init__.py")


def _load_plugin():
    spec = importlib.util.spec_from_file_location("account_preview_test_subject", PLUGIN_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path))
    source = PLUGIN_PATH.parent.parent / "schwab_marketdata"
    target = tmp_path / "plugins" / "schwab_marketdata"
    shutil.copytree(source, target)
    module = _load_plugin()
    monkeypatch.setattr(module, "_now_utc", lambda: datetime(2026, 9, 2, 14, 15, tzinfo=timezone.utc))
    cfg = SimpleNamespace(raw_ok=True, error=None, kill_switch=False, mode="live",
                          tradeable=lambda suffix: suffix in {"331", "568", "726"})
    monkeypatch.setattr(module._live_executor, "load_config", lambda: cfg)
    monkeypatch.setattr(module._mode, "get_mode", lambda: "live")
    monkeypatch.setattr(module._live_executor, "resolve_allowed_hash",
                        lambda suffix, _cfg: (f"hash-{suffix}", None) if suffix in module._SCOPES else (None, "denied"))
    monkeypatch.setattr(module._trader, "get_account", lambda *a, **k: {
        "securitiesAccount": {"type": "CASH", "currentBalances": {
            "liquidationValue": 10000.0, "cashAvailableForTrading": 10000.0,
            "availableFunds": 10000.0}, "positions": []}})
    monkeypatch.setattr(module._trader, "get_orders", lambda *a, **k: [])
    monkeypatch.setattr(module._trader, "validate_order", lambda order: {"valid": True, "errors": []})
    monkeypatch.setattr(module._trader, "preview_order",
                        lambda account_hash, order: {"orderValidationResult": {"accepts": []}})
    return module


def _args(suffix="331"):
    cohorts = {"331": "sep_1_2026", "568": "july1_568", "726": "aug_1_2026"}
    return {"account_suffix": suffix, "cohort": cohorts[suffix], "proposal_id": f"P{suffix}-TEST-01",
            "summary": "Fresh post-open reconciliation supports this whole-share deployment.",
            "source_artifacts": {"sentinel": "2026-09-02T14:10:00Z"},
            "release_conditions": ["Account, order ledger, quotes, and thesis still pass at release."],
            "items": [{"order": {"orderType": "MARKET", "session": "NORMAL", "duration": "DAY",
                        "orderStrategyType": "SINGLE", "orderLegCollection": [{"instruction": "BUY",
                        "quantity": 1, "instrument": {"symbol": "RSP", "assetType": "EQUITY"}}]},
                       "quote": {"bid": 220.0, "ask": 220.05, "status": "Normal"},
                       "thesis": "Mandate-aligned equal-weight exposure."}]}


@pytest.mark.parametrize("suffix", ["331", "568", "726"])
def test_each_scope_creates_sha_bound_pending_preview_without_placement(plugin, monkeypatch, suffix):
    monkeypatch.setattr(plugin._trader, "place_order",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must never place")))
    result = json.loads(plugin._prepare_preview(suffix, _args(suffix)))
    assert result["success"] is True and result["status"] == "PENDING_APPROVAL"
    assert result["orders_placed"] is False
    preview = Path(result["preview_path"])
    state = json.loads(
        Path(result["state_path"]).read_text(encoding="utf-8")
    )
    assert state["account_suffix"] == suffix
    assert state["preview_sha256"] == result["preview_sha256"]
    preview_text = preview.read_text(encoding="utf-8")
    assert f'"account_suffix":"{suffix}"' in preview_text
    assert "APPROVE RH-" in preview_text


def test_foreign_scope_rejected_before_broker(plugin, monkeypatch):
    called = False
    def preview(*a, **k):
        nonlocal called
        called = True
    monkeypatch.setattr(plugin._trader, "preview_order", preview)
    args = _args("331")
    args["account_suffix"] = "892"
    result = json.loads(plugin._prepare_preview("331", args))
    assert result["success"] is False and called is False


def test_cross_account_pending_does_not_block(plugin):
    first = json.loads(plugin._prepare_preview("568", _args("568")))
    second = json.loads(plugin._prepare_preview("331", _args("331")))
    assert first["success"] is True and second["success"] is True


def test_same_account_pending_is_idempotent(plugin):
    first = json.loads(plugin._prepare_preview("331", _args("331")))
    second = json.loads(plugin._prepare_preview("331", _args("331")))
    assert second["success"] is True and second["status"] == "EXISTING_PENDING"
    assert second["preview_id"] == first["preview_id"]


def test_different_same_account_proposal_conflicts(plugin):
    json.loads(plugin._prepare_preview("331", _args("331")))
    other = _args("331")
    other["proposal_id"] = "P331-TEST-02"
    result = json.loads(plugin._prepare_preview("331", other))
    assert result["success"] is False and result["status"] == "CONFLICTING_PENDING"


def test_fractional_share_rejected_without_broker_preview(plugin, monkeypatch):
    called = False
    def preview(*a, **k):
        nonlocal called
        called = True
    monkeypatch.setattr(plugin._trader, "preview_order", preview)
    args = _args("331")
    args["items"][0]["order"]["orderLegCollection"][0]["quantity"] = 0.5
    result = json.loads(plugin._prepare_preview("331", args))
    assert result["success"] is False and "whole number" in result["error"] and called is False


def test_current_day_order_blocks_preview(plugin, monkeypatch):
    monkeypatch.setattr(plugin._trader, "get_orders", lambda *a, **k: [{"status": "FILLED"}])
    result = json.loads(plugin._prepare_preview("331", _args("331")))
    assert result["success"] is False and "Current-day" in result["error"]


def test_old_working_order_blocks_preview(plugin, monkeypatch):
    monkeypatch.setattr(plugin._trader, "get_orders", lambda *a, **k: [
        {"status": "WORKING", "enteredTime": "2026-08-31T14:00:00Z"}])
    result = json.loads(plugin._prepare_preview("331", _args("331")))
    assert result["success"] is False and "older open" in result["error"]


def test_review_and_malformed_broker_previews_fail_closed(plugin, monkeypatch):
    monkeypatch.setattr(plugin._trader, "preview_order", lambda *a, **k: {
        "orderValidationResult": {"reviews": [{"originalSeverity": "REVIEW", "message": "review"}]}})
    assert "rejected/reviewed" in json.loads(plugin._prepare_preview("331", _args("331")))["error"]
    monkeypatch.setattr(plugin._trader, "preview_order", lambda *a, **k: {})
    assert "rejected/reviewed" in json.loads(plugin._prepare_preview("331", _args("331")))["error"]


def test_outside_window_stops_before_broker(plugin, monkeypatch):
    monkeypatch.setattr(plugin, "_now_utc", lambda: datetime(2026, 9, 2, 20, 15, tzinfo=timezone.utc))
    monkeypatch.setattr(plugin._trader, "get_account",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("broker must not be called")))
    result = json.loads(plugin._prepare_preview("331", _args("331")))
    assert result["status"] == "OUTSIDE_ACTIVATION_WINDOW" and result["orders_placed"] is False


def test_creation_lock_serializes_accounts(plugin, monkeypatch):
    guard = threading.Lock()
    active = 0
    maximum = 0
    def inner(suffix, args):
        nonlocal active, maximum
        with guard:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.03)
        with guard:
            active -= 1
        return json.dumps({"success": True})
    monkeypatch.setattr(plugin, "_prepare_preview_locked", inner)
    threads = [threading.Thread(target=plugin._prepare_preview, args=(suffix, _args(suffix)))
               for suffix in ("331", "568")]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert maximum == 1


def test_registration_exposes_isolated_surfaces_and_no_placement(plugin):
    registrations = []
    class Ctx:
        def register_tool(self, **kwargs): registrations.append(kwargs)
    plugin.register(Ctx())
    names = {entry["name"] for entry in registrations}
    toolsets = {entry["toolset"] for entry in registrations}
    assert len(registrations) == 27
    assert {f"account{s}_readonly" for s in ("331", "568", "726")} <= toolsets
    assert {f"account{s}_preview" for s in ("331", "568", "726")} <= toolsets
    assert {f"account{s}_prepare_preview" for s in ("331", "568", "726")} <= names
    assert all("place" not in name and "resolve" not in name for name in names)
    for entry in registrations:
        properties = entry["schema"]["parameters"].get("properties", {})
        assert "account_hash" not in properties
        assert "order" not in properties


def test_read_surfaces_redact_full_account_number(plugin, monkeypatch):
    monkeypatch.setattr(plugin._trader, "get_account", lambda *a, **k: {
        "securitiesAccount": {"accountNumber": "1234567331", "type": "CASH",
                              "initialBalances": {"cashBalance": 10000, "liquidationValue": 10000},
                              "positions": []}})
    result = json.loads(plugin._read_account("331", {}))
    assert result["success"] is True and "1234567331" not in json.dumps(result)


def test_token_health_allowlists_fields(plugin, monkeypatch):
    token_health = Mock(return_value={"app": "trader", "probe_ok": True, "access_token": "secret"})
    monkeypatch.setattr(plugin._oauth, "token_health", token_health)
    result = json.loads(plugin._token_health({"probe": True}))
    assert result["probe_ok"] is True and "access_token" not in result
    token_health.assert_called_once_with(probe=True, app=plugin._oauth.TRADER_APP)


def test_kill_switch_blocks_preview_before_broker(plugin, monkeypatch):
    cfg = plugin._live_executor.load_config()
    cfg.kill_switch = True
    broker = Mock(side_effect=AssertionError("broker must not be called"))
    monkeypatch.setattr(plugin._trader, "get_account", broker)

    result = json.loads(plugin._prepare_preview("331", _args("331")))

    assert result["success"] is False
    assert "kill_switch" in result["error"]
    broker.assert_not_called()


def test_non_live_mode_blocks_preview_before_broker(plugin, monkeypatch):
    broker = Mock(side_effect=AssertionError("broker must not be called"))
    monkeypatch.setattr(plugin._trader, "get_account", broker)
    monkeypatch.setattr(plugin._mode, "get_mode", lambda: "mock")

    result = json.loads(plugin._prepare_preview("331", _args("331")))

    assert result["success"] is False
    assert "LIVE mode" in result["error"]
    broker.assert_not_called()


def test_successful_preview_appends_scoped_journal_record(plugin):
    result = json.loads(plugin._prepare_preview("331", _args("331")))

    records = [
        json.loads(line)
        for line in plugin._journal_path("331").read_text().splitlines()
    ]
    assert len(records) == 1
    assert records[0]["event"] == "PREVIEW_CREATED"
    assert records[0]["account_suffix"] == "331"
    assert records[0]["preview_sha256"] == result["preview_sha256"]
    assert records[0]["orders_placed"] is False


def test_max_orders_rejected_before_broker(plugin, monkeypatch):
    broker = Mock(side_effect=AssertionError("broker must not be called"))
    monkeypatch.setattr(plugin._trader, "get_account", broker)
    args = _args("331")
    args["items"] = args["items"] * (plugin._MAX_ORDERS + 1)

    result = json.loads(plugin._prepare_preview("331", args))

    assert result["success"] is False
    assert f"1-{plugin._MAX_ORDERS}" in result["error"]
    broker.assert_not_called()


def test_invalid_symbol_rejected_before_marketdata(plugin, monkeypatch):
    get_quotes = Mock(side_effect=AssertionError("market data must not be called"))
    monkeypatch.setattr(plugin._marketdata, "get_quotes", get_quotes)

    result = json.loads(plugin._quotes({"symbols": ["AAPL;DROP"]}))

    assert result["success"] is False
    assert "Invalid symbol" in result["error"]
    get_quotes.assert_not_called()
