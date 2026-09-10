"""Portable restore contracts for production investment extensions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


EXPORT_ROOT = Path(__file__).parents[1]


@pytest.fixture
def restore_module():
    spec = importlib.util.spec_from_file_location(
        "athena_invest_restore_test_subject",
        EXPORT_ROOT / "restore.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_restore_component_list_includes_both_production_plugins(restore_module):
    assert ("plugins/schwab_marketdata", "plugins/schwab_marketdata") in (
        restore_module.COMPONENTS
    )
    assert ("plugins/account_preview", "plugins/account_preview") in (
        restore_module.COMPONENTS
    )


def test_restore_dry_run_does_not_write_files(
    restore_module,
    monkeypatch,
    tmp_path,
):
    home = tmp_path / "target-home"
    monkeypatch.setenv("ATHENA_HOME", str(home))
    monkeypatch.setattr(
        restore_module,
        "COMPONENTS",
        [("plugins/account_preview", "plugins/account_preview")],
    )

    assert restore_module.restore(force=False, dry_run=True) == 0
    assert not home.exists()


def test_restore_refuses_overwrite_without_force_and_replaces_with_force(
    restore_module,
    monkeypatch,
    tmp_path,
):
    home = tmp_path / "target-home"
    monkeypatch.setenv("ATHENA_HOME", str(home))
    monkeypatch.setattr(
        restore_module,
        "COMPONENTS",
        [("plugins/account_preview", "plugins/account_preview")],
    )

    assert restore_module.restore(force=False, dry_run=False) == 0
    target = home / "plugins" / "account_preview" / "plugin.yaml"
    original = target.read_text(encoding="utf-8")
    target.write_text("local override\n", encoding="utf-8")

    assert restore_module.restore(force=False, dry_run=False) == 0
    assert target.read_text(encoding="utf-8") == "local override\n"

    assert restore_module.restore(force=True, dry_run=False) == 0
    assert target.read_text(encoding="utf-8") == original


def test_manifest_lists_separate_marketdata_and_trader_credentials():
    manifest = json.loads(
        (EXPORT_ROOT / "MANIFEST.json").read_text(encoding="utf-8")
    )
    keys = set(manifest["secrets_required_after_restore"]["keys"])

    assert {
        "SCHWAB_APP_KEY",
        "SCHWAB_APP_SECRET",
        "SCHWAB_TRADER_APP_KEY",
        "SCHWAB_TRADER_APP_SECRET",
        "SCHWAB_CALLBACK_URL",
    } <= keys
