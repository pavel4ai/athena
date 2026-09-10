"""Behavior contracts for task-specific auxiliary request bodies."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent import auxiliary_client


def _response(content: str):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _client_returning(content: str):
    client = MagicMock()
    client.chat.completions.create.return_value = _response(content)
    return client


@pytest.fixture(autouse=True)
def _task_specific_bodies(monkeypatch):
    monkeypatch.setattr(auxiliary_client, "auxiliary_is_nous", False)
    monkeypatch.setattr(
        auxiliary_client,
        "_get_task_extra_body",
        lambda task: {"task_route": task},
    )


def test_goal_judge_routes_goal_judge_extra_body(monkeypatch):
    from athena_cli import goals

    client = _client_returning('{"done": true, "reason": "complete"}')
    monkeypatch.setattr(
        auxiliary_client,
        "get_text_auxiliary_client",
        lambda task: (client, "judge-model"),
    )

    verdict, _, _, _ = goals.judge_goal("ship", "shipped")

    assert verdict == "done"
    assert client.chat.completions.create.call_args.kwargs["extra_body"] == {
        "task_route": "goal_judge"
    }


def test_goal_contract_draft_routes_goal_judge_extra_body(monkeypatch):
    from athena_cli import goals

    client = _client_returning(
        '{"outcome": "feature works", "verification": "targeted tests pass"}'
    )
    monkeypatch.setattr(
        auxiliary_client,
        "get_text_auxiliary_client",
        lambda task: (client, "judge-model"),
    )

    contract = goals.draft_contract("ship the feature")

    assert contract is not None
    assert client.chat.completions.create.call_args.kwargs["extra_body"] == {
        "task_route": "goal_judge"
    }


def test_kanban_decompose_routes_decomposer_extra_body(monkeypatch):
    from athena_cli import kanban_decompose

    task = SimpleNamespace(
        id="task-1",
        status="triage",
        title="Investigate",
        body="Find the cause",
        assignee=None,
    )
    client = _client_returning("not json")
    monkeypatch.setattr(
        kanban_decompose.kb,
        "connect_closing",
        lambda: nullcontext(object()),
    )
    monkeypatch.setattr(
        kanban_decompose.kb,
        "get_task",
        lambda connection, task_id: task,
    )
    monkeypatch.setattr(kanban_decompose, "_load_config", lambda: {})
    monkeypatch.setattr(
        kanban_decompose,
        "_resolve_orchestrator_profile",
        lambda config: "orchestrator",
    )
    monkeypatch.setattr(
        kanban_decompose,
        "_resolve_default_assignee",
        lambda config: "orchestrator",
    )
    monkeypatch.setattr(
        kanban_decompose,
        "_build_roster",
        lambda: (
            [
                {
                    "name": "orchestrator",
                    "description": "Coordinates work",
                    "has_description": True,
                }
            ],
            {"orchestrator"},
        ),
    )
    monkeypatch.setattr(
        auxiliary_client,
        "get_text_auxiliary_client",
        lambda task_name: (client, "decomposer-model"),
    )

    outcome = kanban_decompose.decompose_task("task-1")

    assert outcome.ok is False
    assert client.chat.completions.create.call_args.kwargs["extra_body"] == {
        "task_route": "kanban_decomposer"
    }


def test_kanban_specify_routes_specifier_extra_body(monkeypatch):
    from athena_cli import kanban_specify

    task = SimpleNamespace(
        id="task-2",
        status="triage",
        title="Draft",
        body="Add details",
    )
    client = _client_returning("")
    monkeypatch.setattr(
        kanban_specify.kb,
        "connect_closing",
        lambda: nullcontext(object()),
    )
    monkeypatch.setattr(
        kanban_specify.kb,
        "get_task",
        lambda connection, task_id: task,
    )
    monkeypatch.setattr(
        auxiliary_client,
        "get_text_auxiliary_client",
        lambda task_name: (client, "specifier-model"),
    )

    outcome = kanban_specify.specify_task("task-2")

    assert outcome.ok is False
    assert client.chat.completions.create.call_args.kwargs["extra_body"] == {
        "task_route": "triage_specifier"
    }


def test_profile_describer_routes_profile_extra_body(monkeypatch, tmp_path):
    from athena_cli import profile_describer

    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    client = _client_returning("")
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
    monkeypatch.setattr(profile_describer, "_collect_skills", lambda path: [])
    monkeypatch.setattr(
        auxiliary_client,
        "get_text_auxiliary_client",
        lambda task_name: (client, "describer-model"),
    )

    outcome = profile_describer.describe_profile("profile")

    assert outcome.ok is False
    assert client.chat.completions.create.call_args.kwargs["extra_body"] == {
        "task_route": "profile_describer"
    }


def test_web_extract_routes_web_extract_extra_body(monkeypatch):
    from tools import web_tools

    client = SimpleNamespace(
        base_url="https://inference-api.nousresearch.com/v1"
    )
    monkeypatch.delenv("AUXILIARY_WEB_EXTRACT_MODEL", raising=False)
    monkeypatch.setattr(
        web_tools,
        "get_async_text_auxiliary_client",
        lambda task_name: (client, "extract-model"),
    )

    resolved_client, model, extra_body = (
        web_tools._resolve_web_extract_auxiliary()
    )

    assert resolved_client is client
    assert model == "extract-model"
    assert extra_body == {"task_route": "web_extract"}
