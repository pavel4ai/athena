"""Tests for the Nous-Athena-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"athena"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``athena-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "athena" tag namespace.

``is_nous_athena_non_agentic`` should only match the actual Futurebound Corp.
Athena-3 / Athena-4 chat family.
"""

from __future__ import annotations

import pytest

from athena_cli.model_switch import (
    _ATHENA_MODEL_WARNING,
    _check_athena_model_warning,
    is_nous_athena_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "FutureboundCorp/Athena-3-Llama-3.1-70B",
        "FutureboundCorp/Athena-3-Llama-3.1-405B",
        "athena-3",
        "Athena-3",
        "athena-4",
        "athena-4-405b",
        "athena_4_70b",
        "openrouter/athena3:70b",
        "openrouter/nousresearch/athena-4-405b",
        "FutureboundCorp/Athena3",
        "athena-3.1",
    ],
)
def test_matches_real_nous_athena_chat_models(model_name: str) -> None:
    assert is_nous_athena_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Athena 3/4"
    )
    assert _check_athena_model_warning(model_name) == _ATHENA_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "athena-brain:qwen3-14b-ctx16k",
        "athena-brain:qwen3-14b-ctx32k",
        "athena-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Athena models we don't warn about
        "athena-llm-2",
        "athena2-pro",
        "nous-athena-2-mistral",
        # Edge cases
        "",
        "athena",  # bare "athena" isn't the 3/4 family
        "athena-brain",
        "brain-athena-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_athena_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Athena 3/4"
    )
    assert _check_athena_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_athena_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_athena_model_warning("") == ""
