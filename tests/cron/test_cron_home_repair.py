"""Behavior contracts for cron child-process HOME repair."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import athena_constants
from tools.environments.local import build_subprocess_env


def test_missing_home_is_repaired_in_child_environment(
    monkeypatch,
    tmp_path,
):
    repaired_home = str(tmp_path / "real-home")
    monkeypatch.setattr(
        athena_constants,
        "get_real_home",
        MagicMock(return_value=repaired_home),
    )
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("ATHENA_REAL_HOME", raising=False)
    parent_home = os.environ.get("HOME")

    child = build_subprocess_env(
        base={"PATH": "/usr/bin"},
        scrub_secrets=False,
    )

    assert child["HOME"] == repaired_home
    assert child["ATHENA_REAL_HOME"] == repaired_home
    assert os.environ.get("HOME") == parent_home


def test_existing_home_is_preserved(monkeypatch, tmp_path):
    configured_home = str(tmp_path / "configured-home")
    monkeypatch.setattr(
        athena_constants,
        "get_real_home",
        MagicMock(return_value=configured_home),
    )

    child = build_subprocess_env(
        base={"PATH": "/usr/bin", "HOME": configured_home},
        scrub_secrets=False,
    )

    assert child["HOME"] == configured_home
    assert child["ATHENA_REAL_HOME"] == configured_home


def test_real_home_lookup_failure_is_nonfatal(monkeypatch):
    monkeypatch.setattr(
        athena_constants,
        "get_real_home",
        MagicMock(side_effect=OSError("home lookup failed")),
    )

    child = build_subprocess_env(
        base={"PATH": "/usr/bin"},
        scrub_secrets=False,
    )

    assert child["PATH"] == "/usr/bin"
    assert "HOME" not in child
    assert "ATHENA_REAL_HOME" not in child
