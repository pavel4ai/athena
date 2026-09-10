"""Behavior contracts for cron HOME repair."""

from unittest.mock import MagicMock

import pytest

import athena_constants
import athena_state
import cron.scheduler as scheduler
import gateway.session_context as session_context


class _ReachedPostRepairBoundary(RuntimeError):
    """Stop ``run_job`` immediately after the HOME repair block."""


def _run_to_post_repair_boundary(monkeypatch) -> None:
    monkeypatch.setattr(
        scheduler,
        "_build_job_prompt",
        lambda job, prerun_script=None: "test prompt",
    )
    monkeypatch.setattr(scheduler, "_resolve_origin", lambda job: {})
    monkeypatch.setattr(athena_state, "SessionDB", lambda: None)
    monkeypatch.setattr(
        session_context,
        "set_session_vars",
        MagicMock(side_effect=_ReachedPostRepairBoundary),
    )

    with pytest.raises(_ReachedPostRepairBoundary):
        scheduler.run_job({"id": "home-repair", "prompt": "test prompt"})


def test_missing_home_is_repaired_from_real_home(monkeypatch, tmp_path):
    repaired_home = tmp_path / "real-home"
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("ATHENA_REAL_HOME", raising=False)
    monkeypatch.setattr(
        athena_constants,
        "get_real_home",
        MagicMock(return_value=repaired_home),
    )

    _run_to_post_repair_boundary(monkeypatch)

    assert scheduler.os.environ["HOME"] == str(repaired_home)
    assert scheduler.os.environ["ATHENA_REAL_HOME"] == str(repaired_home)


def test_existing_home_is_preserved(monkeypatch, tmp_path):
    configured_home = str(tmp_path / "configured-home")
    existing_real_home = str(tmp_path / "existing-real-home")
    get_real_home = MagicMock(side_effect=AssertionError("must not be called"))
    monkeypatch.setenv("HOME", configured_home)
    monkeypatch.setenv("ATHENA_REAL_HOME", existing_real_home)
    monkeypatch.setattr(athena_constants, "get_real_home", get_real_home)

    _run_to_post_repair_boundary(monkeypatch)

    assert scheduler.os.environ["HOME"] == configured_home
    assert scheduler.os.environ["ATHENA_REAL_HOME"] == existing_real_home
    get_real_home.assert_not_called()


def test_real_home_failure_leaves_home_unset(monkeypatch):
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("ATHENA_REAL_HOME", raising=False)
    monkeypatch.setattr(
        athena_constants,
        "get_real_home",
        MagicMock(side_effect=OSError("home lookup failed")),
    )

    _run_to_post_repair_boundary(monkeypatch)

    assert "HOME" not in scheduler.os.environ
    assert "ATHENA_REAL_HOME" not in scheduler.os.environ
