"""Portable plugin contracts. All broker and network surfaces are mocked."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import os
import shutil
import socket
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from athena_cli.plugins import PluginContext
from athena_cli.plugins_manifest import parse_manifest_file

EXPORT_ROOT = Path(__file__).parents[1]
PLUGINS_ROOT = EXPORT_ROOT / "plugins"
SCHWAB_ROOT = PLUGINS_ROOT / "schwab_marketdata"
ACCOUNT_PREVIEW_ROOT = PLUGINS_ROOT / "account_preview"


class RecordingContext:
    def __init__(self):
        self.registrations = []

    def register_tool(self, **kwargs):
        self.registrations.append(kwargs)


def _load_schwab(monkeypatch):
    monkeypatch.syspath_prepend(str(PLUGINS_ROOT))
    return importlib.import_module("schwab_marketdata")


def _load_account_preview(monkeypatch):
    home = Path(os.environ["ATHENA_HOME"])
    staged = home / "plugins" / "schwab_marketdata"
    shutil.copytree(
        SCHWAB_ROOT,
        staged,
        ignore=shutil.ignore_patterns("test_*.py", "__pycache__", "README.md"),
    )
    for name in tuple(sys.modules):
        if name == "_default_preview_schwab" or name.startswith("_default_preview_schwab."):
            sys.modules.pop(name)
    spec = importlib.util.spec_from_file_location(
        "account_preview_contract_subject",
        ACCOUNT_PREVIEW_ROOT / "__init__.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest(path):
    return yaml.safe_load(path.read_text())


def _assert_registration_contract(manifest, registrations):
    assert registrations
    assert len({entry["name"] for entry in registrations}) == len(registrations)

    registered = {}
    context_parameters = inspect.signature(PluginContext.register_tool).parameters
    required_context_fields = {
        name
        for name, parameter in context_parameters.items()
        if name != "self" and parameter.default is inspect.Parameter.empty
    }

    for entry in registrations:
        assert required_context_fields <= set(entry)
        assert set(entry) <= set(context_parameters)
        assert callable(entry["handler"])
        assert callable(entry["check_fn"])
        assert entry["requires_env"] == ["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"]
        assert entry["description"]
        assert entry["emoji"]

        schema = entry["schema"]
        assert schema["name"] == entry["name"]
        assert schema["description"]
        parameters = schema["parameters"]
        assert parameters["type"] == "object"
        assert isinstance(parameters.get("properties", {}), dict)
        assert set(parameters.get("required", ())) <= set(parameters.get("properties", {}))
        registered.setdefault(entry["toolset"], set()).add(entry["name"])

    declared = {
        toolset: set(details["tools"])
        for toolset, details in manifest["toolsets"].items()
    }
    assert registered == declared


def test_hermetic_fixture_clears_credentials_and_blocks_ip_network():
    assert not any(name.startswith("SCHWAB_") for name in os.environ)
    assert Path(os.environ["ATHENA_HOME"]).is_dir()
    with pytest.raises(RuntimeError, match="network disabled"):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError, match="network disabled"):
        socket.socket(socket.AF_INET6, socket.SOCK_STREAM)


def test_schwab_manifest_registration_and_schema_contract(monkeypatch):
    schwab = _load_schwab(monkeypatch)
    context = RecordingContext()

    schwab.register(context)

    _assert_registration_contract(
        _manifest(SCHWAB_ROOT / "plugin.yaml"),
        context.registrations,
    )


def test_account_preview_manifest_registration_and_schema_contract(monkeypatch):
    account_preview = _load_account_preview(monkeypatch)
    context = RecordingContext()

    account_preview.register(context)

    _assert_registration_contract(
        _manifest(ACCOUNT_PREVIEW_ROOT / "plugin.yaml"),
        context.registrations,
    )


@pytest.mark.parametrize(
    ("plugin_root", "expected_name"),
    (
        (SCHWAB_ROOT, "schwab_marketdata"),
        (ACCOUNT_PREVIEW_ROOT, "account-preview"),
    ),
)
def test_manifests_are_compatible_with_plugin_manager(plugin_root, expected_name):
    manifest = parse_manifest_file(
        plugin_root / "plugin.yaml",
        plugin_root,
        source="user",
        prefix="",
    )

    assert manifest is not None
    assert manifest.name == expected_name
    assert manifest.kind == "standalone"


def test_mock_and_live_routing_never_bypass_broker_adapters(monkeypatch):
    schwab = _load_schwab(monkeypatch)
    trader = importlib.import_module("schwab_marketdata.trader")
    mode = importlib.import_module("schwab_marketdata.mode")
    mock_broker = importlib.import_module("schwab_marketdata.mock_broker")
    live_executor = importlib.import_module("schwab_marketdata.live_executor")
    order = {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [{
            "instruction": "BUY",
            "quantity": 1,
            "instrument": {"symbol": "SPY", "assetType": "EQUITY"},
        }],
    }

    monkeypatch.setattr(schwab, "_credentials_present", lambda: True)
    validate_order = Mock(return_value={"valid": True, "errors": []})
    direct_place = Mock(side_effect=AssertionError("direct place_order is forbidden"))
    monkeypatch.setattr(trader, "validate_order", validate_order)
    monkeypatch.setattr(trader, "place_order", direct_place)

    paper = Mock()
    paper.place_order.return_value = {
        "order_id": "MOCK-1",
        "status": "FILLED",
        "fills": [],
        "mock": True,
    }
    paper_factory = Mock(return_value=paper)
    live_place = Mock(return_value={"success": True, "status": "PLACED", "mode": "live"})
    monkeypatch.setattr(mock_broker, "MockBroker", paper_factory)
    monkeypatch.setattr(live_executor, "place_live_order", live_place)

    monkeypatch.setattr(mode, "is_mock", lambda: True)
    mock_result = json.loads(schwab.schwab_place_order({
        "cohort": "safe-test",
        "account_hash": "IGNORED",
        "order": order,
        "idempotency_key": "MOCK-IDEM",
    }))
    assert mock_result["success"] is True
    paper_factory.assert_called_once_with("safe-test")
    paper.place_order.assert_called_once_with(
        "IGNORED",
        order,
        idempotency_key="MOCK-IDEM",
    )
    live_place.assert_not_called()
    direct_place.assert_not_called()

    monkeypatch.setattr(mode, "is_mock", lambda: False)
    live_result = json.loads(schwab.schwab_place_order({
        "cohort": "safe-test",
        "account_hash": "UNTRUSTED-CALLER-HASH",
        "account_suffix": "568",
        "order": order,
        "idempotency_key": "LIVE-IDEM",
        "preview_id": "P-LIVE",
    }, user_task="APPROVE P-LIVE"))
    assert live_result["success"] is True
    live_place.assert_called_once_with(
        order,
        {
            "account_suffix": "568",
            "idempotency_key": "LIVE-IDEM",
            "preview_id": "P-LIVE",
            "user_task": "APPROVE P-LIVE",
        },
    )
    direct_place.assert_not_called()


def test_schwab_token_health_forwards_probe(monkeypatch):
    schwab = _load_schwab(monkeypatch)
    oauth = importlib.import_module("schwab_marketdata.oauth")
    token_health = Mock(return_value={"configured": False, "probed": True})
    monkeypatch.setattr(oauth, "token_health", token_health)

    result = json.loads(schwab.schwab_token_health({"probe": True}))

    assert result["success"] is True
    assert result["probed"] is True
    token_health.assert_called_once_with(probe=True)
