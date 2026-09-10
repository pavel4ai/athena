"""End-to-end contract for clean inbound tool provenance."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from run_agent import AIAgent


def _tool_definitions():
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            },
        }
    ]


def _response(content: str, finish_reason: str, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], model="test/model", usage=None)


def _make_agent():
    with (
        patch("run_agent.get_tool_definitions", return_value=_tool_definitions()),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("athena_cli.config.load_config", return_value={}),
        patch("athena_logging.setup_logging"),
        patch(
            "agent.model_metadata.get_model_context_length",
            return_value=200_000,
        ),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            provider="openrouter",
            model="test/model",
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )

    agent.client = MagicMock()
    agent._cached_system_prompt = "You are helpful."
    agent._disable_streaming = True
    agent._use_prompt_caching = False
    agent.compression_enabled = False
    agent.save_trajectories = False
    agent.tool_delay = 0
    return agent


def test_clean_inbound_task_reaches_registry_dispatch():
    agent = _make_agent()
    tool_call = SimpleNamespace(
        id="call-1",
        type="function",
        function=SimpleNamespace(
            name="web_search",
            arguments=json.dumps({"query": "release status"}),
        ),
    )
    agent.client.chat.completions.create.side_effect = [
        _response("", "tool_calls", [tool_call]),
        _response("Done.", "stop"),
    ]
    api_facing_message = (
        "[Observed gateway context: room=ops]\n"
        "APPROVE B892-20260901-01"
    )
    clean_inbound_task = "APPROVE B892-20260901-01"

    with (
        patch(
            "run_agent.handle_function_call",
            return_value='{"success": true}',
        ) as dispatch,
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation(
            api_facing_message,
            persist_user_message=clean_inbound_task,
        )

    assert result["final_response"] == "Done."
    assert agent._current_user_task == clean_inbound_task
    assert dispatch.call_count == 1
    assert dispatch.call_args.kwargs["user_task"] == clean_inbound_task
    assert dispatch.call_args.kwargs["user_task"] != api_facing_message
