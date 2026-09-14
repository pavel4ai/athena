"""Behavior contracts for an explicit Gemini fallback."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from run_agent import AIAgent


class _RateLimitError(RuntimeError):
    status_code = 429


def _response(content: str):
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="gemini-2.5-flash", usage=None)


def _client(base_url: str, api_key: str):
    client = MagicMock()
    client.base_url = base_url
    client.api_key = api_key
    client._custom_headers = None
    client.default_headers = None
    return client


def _make_agent(primary_client):
    fallback = {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
    }
    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("athena_cli.config.load_config", return_value={}),
        patch("athena_logging.setup_logging"),
        patch(
            "agent.model_metadata.get_model_context_length",
            return_value=200_000,
        ),
        patch("agent.process_bootstrap.OpenAI", return_value=primary_client),
    ):
        agent = AIAgent(
            provider="openrouter",
            model="primary/model",
            api_key="primary-key",
            base_url="https://openrouter.ai/api/v1",
            fallback_model=[fallback],
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )

    agent.client = primary_client
    agent._cached_system_prompt = (
        "You are helpful.\nModel: primary/model\nProvider: openrouter"
    )
    agent._disable_streaming = True
    agent._use_prompt_caching = False
    agent._api_max_retries = 1
    agent.compression_enabled = False
    agent.save_trajectories = False
    return agent


def _run_with_mocked_runtime(agent, fallback_client):
    with (
        patch(
            "agent.auxiliary_client.resolve_provider_client",
            return_value=(fallback_client, "gemini-2.5-flash"),
        ) as resolve_provider,
        patch(
            "athena_cli.model_normalize.normalize_model_for_provider",
            side_effect=lambda model, provider: model,
        ),
        patch(
            "agent.model_metadata.get_model_context_length",
            return_value=1_000_000,
        ),
        patch.object(agent, "_try_recover_primary_transport", return_value=False),
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("Answer the request")

    return result, resolve_provider


def test_rate_limit_activates_explicit_gemini_fallback():
    primary_client = _client(
        "https://openrouter.ai/api/v1",
        "primary-key",
    )
    fallback_client = _client(
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-key",
    )
    primary_client.chat.completions.create.side_effect = _RateLimitError(
        "rate limit exceeded"
    )
    fallback_client.chat.completions.create.return_value = _response(
        "Recovered through Gemini."
    )
    agent = _make_agent(primary_client)

    result, resolve_provider = _run_with_mocked_runtime(
        agent,
        fallback_client,
    )

    assert result["final_response"] == "Recovered through Gemini."
    assert agent.provider == "gemini"
    assert agent.model == "gemini-2.5-flash"
    assert agent.api_mode == "chat_completions"
    resolve_provider.assert_called_once()
    assert resolve_provider.call_args.args == ("gemini",)
    assert resolve_provider.call_args.kwargs["model"] == "gemini-2.5-flash"


def test_exhausted_gemini_fallback_flushes_attempt_trace():
    primary_client = _client(
        "https://openrouter.ai/api/v1",
        "primary-key",
    )
    fallback_client = _client(
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-key",
    )
    primary_client.chat.completions.create.side_effect = _RateLimitError(
        "primary quota exhausted"
    )
    fallback_client.chat.completions.create.side_effect = _RateLimitError(
        "gemini quota exhausted"
    )
    agent = _make_agent(primary_client)
    emitted_status = []
    agent._emit_status = emitted_status.append

    result, _ = _run_with_mocked_runtime(agent, fallback_client)

    status_text = "\n".join(emitted_status)
    assert result["failed"] is True
    assert "Model fallback:" in status_text
    assert "gemini-2.5-flash via gemini" in status_text
    assert "gemini quota exhausted" in status_text
    assert agent._retry_status_buffer == []
