"""Contracts for task-specific auxiliary configuration on the modular runtime."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent import auxiliary_client


def _response(content: str = "ok"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


def test_task_extra_body_merges_reasoning_effort(monkeypatch):
    monkeypatch.setattr(
        auxiliary_client,
        "_get_auxiliary_task_config",
        lambda task: {
            "extra_body": {"task_route": task},
            "reasoning_effort": "high",
        },
    )

    assert auxiliary_client._get_task_extra_body("goal_judge") == {
        "task_route": "goal_judge",
        "reasoning": {"enabled": True, "effort": "high"},
    }


def test_goal_judge_helper_routes_goal_task():
    from athena_cli import goals

    call_llm = MagicMock(return_value=_response('{"verdict":"continue"}'))

    goals._call_goal_judge_llm(
        call_llm,
        "system",
        "user",
        timeout=15,
    )

    assert call_llm.call_args.kwargs["task"] == "goal_judge"


@pytest.mark.parametrize(
    "aux_task",
    ("kanban_decomposer", "triage_specifier"),
)
def test_kanban_auxiliary_calls_preserve_task_route(monkeypatch, aux_task):
    from athena_cli import kanban_specify

    call_llm = MagicMock(return_value=_response("{}"))
    monkeypatch.setattr(auxiliary_client, "call_llm", call_llm)

    reply, reason = kanban_specify._call_aux(
        "specify",
        "task-1",
        aux_task=aux_task,
        system="system",
        user="user",
        max_tokens=100,
        timeout=10,
    )

    assert reply == "{}"
    assert reason == ""
    assert call_llm.call_args.kwargs["task"] == aux_task


def test_profile_describer_routes_profile_task(monkeypatch, tmp_path):
    from athena_cli import profile_describer

    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    call_llm = MagicMock(
        return_value=_response(
            json.dumps({"description": "Investment research profile"})
        )
    )
    monkeypatch.setattr(auxiliary_client, "call_llm", call_llm)
    monkeypatch.setattr(
        profile_describer.profiles_mod,
        "normalize_profile_name",
        lambda name: name,
    )
    monkeypatch.setattr(
        profile_describer.profiles_mod,
        "profile_exists",
        lambda name: True,
    )
    monkeypatch.setattr(
        profile_describer.profiles_mod,
        "get_profile_dir",
        lambda name: profile_dir,
    )
    monkeypatch.setattr(
        profile_describer.profiles_mod,
        "read_profile_meta",
        lambda path: {},
    )
    monkeypatch.setattr(
        profile_describer.profiles_mod,
        "_read_config_model",
        lambda path: ("main-model", "main-provider"),
    )
    monkeypatch.setattr(
        profile_describer,
        "_collect_skills",
        lambda path: [],
    )

    outcome = profile_describer.describe_profile("profile")

    assert outcome.ok is True
    assert call_llm.call_args.kwargs["task"] == "profile_describer"
