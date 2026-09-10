"""Provider-identity contracts for OpenAI model metadata."""

from unittest.mock import patch

from agent import model_metadata, models_dev


def test_openai_api_maps_to_openai_models_dev_provider():
    assert models_dev.PROVIDER_TO_MODELS_DEV["openai-api"] == "openai"


def test_direct_api_context_does_not_inherit_codex_oauth_cap():
    registry = {
        "openai": {
            "models": {
                "gpt-5.6-sol": {
                    "limit": {
                        "context": 1_050_000,
                        "output": 128_000,
                    }
                }
            }
        }
    }

    with (
        patch(
            "agent.model_metadata.get_cached_context_length",
            return_value=None,
        ),
        patch(
            "agent.model_metadata._query_ollama_api_show",
            return_value=None,
        ),
        patch("agent.models_dev.fetch_models_dev", return_value=registry),
        patch(
            "agent.model_metadata._resolve_codex_oauth_context_length",
            return_value=272_000,
        ) as codex_context,
        patch("agent.model_metadata.save_context_length"),
    ):
        direct_context = model_metadata.get_model_context_length(
            "gpt-5.6-sol",
            provider="openai-api",
            base_url="https://api.openai.com/v1",
        )
        codex_context.assert_not_called()

        oauth_context = model_metadata.get_model_context_length(
            "gpt-5.6-sol",
            provider="openai-codex",
            base_url="https://chatgpt.com/backend-api/codex",
        )

    assert direct_context == 1_050_000
    assert oauth_context == 272_000
    codex_context.assert_called_once_with(
        "gpt-5.6-sol",
        access_token="",
    )
