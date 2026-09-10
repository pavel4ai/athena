"""Safety requirement for the isolated Schwab execution upgrade."""

from __future__ import annotations

import importlib
import importlib.util
import os
import socket
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

PLUGIN_ROOT = (
    Path(__file__).parents[2]
    / "athena_invest_export"
    / "plugins"
    / "schwab_marketdata"
)

ORDER = {
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


@pytest.fixture
def isolated_executor(tmp_path, monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("SCHWAB_"):
            monkeypatch.delenv(name, raising=False)

    athena_home = tmp_path / "athena-home"
    monkeypatch.setenv("ATHENA_HOME", str(athena_home))

    real_socket = socket.socket

    def blocked_network_socket(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError("network disabled in Schwab approval requirement")
        return real_socket(family, *args, **kwargs)

    monkeypatch.setattr(socket, "socket", blocked_network_socket)

    package_name = "_approval_requirement_schwab"
    for name in tuple(sys.modules):
        if name == package_name or name.startswith(f"{package_name}."):
            sys.modules.pop(name)
    spec = importlib.util.spec_from_file_location(
        package_name,
        PLUGIN_ROOT / "__init__.py",
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    assert spec and spec.loader
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)

    executor = importlib.import_module(f"{package_name}.live_executor")
    mode = importlib.import_module(f"{package_name}.mode")
    executor._config_path().write_text(
        """```
mode: live
kill_switch: off
require_preview: on
```
```
allow: 568
```
"""
    )
    mode.set_mode("live")
    return executor


@pytest.mark.integration
def test_live_order_without_matching_sha_bound_approval_never_reaches_broker(
    isolated_executor,
    monkeypatch,
):
    executor = isolated_executor
    previews = Path(os.environ["ATHENA_HOME"]) / "athena_invest" / "schwab" / "previews"
    previews.mkdir(parents=True)
    assert list(previews.iterdir()) == []

    validate_order = Mock(return_value={"valid": True, "errors": []})
    account_numbers = Mock(return_value=[
        {"accountNumber": "11111568", "hashValue": "HASH-568"},
    ])
    preview_order = Mock(return_value={"orderValidationResult": {"accepts": []}})
    place_order = Mock(return_value={"order_id": "MUST-NOT-PLACE", "status_code": 201})
    get_order = Mock(return_value={"orderId": "MUST-NOT-PLACE", "status": "WORKING"})
    monkeypatch.setattr(executor.trader, "validate_order", validate_order)
    monkeypatch.setattr(executor.trader, "get_account_numbers", account_numbers)
    monkeypatch.setattr(executor.trader, "preview_order", preview_order)
    monkeypatch.setattr(executor.trader, "place_order", place_order)
    monkeypatch.setattr(executor.trader, "get_order", get_order)

    result = executor.place_live_order(
        ORDER,
        {"account_suffix": "568", "idempotency_key": "NO-APPROVAL"},
    )

    place_order.assert_not_called()
    assert result["success"] is False
