"""Cross-surface contracts for hidden subscription provider choices."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


_HIDDEN_TOOL_CHOICE = "Nous Subscription"


def _assert_no_subscription_choice(rows: list[dict], *, surface: str) -> None:
    offenders = [
        row.get("name", "")
        for row in rows
        if str(row.get("name", "")).startswith(_HIDDEN_TOOL_CHOICE)
        or row.get("managed_nous_feature")
    ]
    assert offenders == [], f"{surface} exposed managed subscription rows: {offenders}"


def _stub_subscription_state(monkeypatch, tools_config) -> None:
    state = SimpleNamespace(
        nous_auth_present=False,
        account_info=None,
        features={},
    )
    monkeypatch.setattr(
        tools_config,
        "get_nous_subscription_features",
        lambda *_args, **_kwargs: state,
    )


def test_setup_and_model_share_the_same_hidden_provider_menu(monkeypatch):
    from athena_cli import auth, main, setup
    from athena_cli.config import load_config

    captured: list[tuple[str, ...]] = []

    def capture_and_cancel(choices, default=0, title=None):
        del default, title
        captured.append(tuple(choices))
        return next(
            index
            for index, label in enumerate(choices)
            if label == "Leave unchanged"
        )

    monkeypatch.setattr(auth, "resolve_provider", lambda _provider: None)
    monkeypatch.setattr(main, "_prompt_provider_choice", capture_and_cancel)

    main.select_provider_and_model()
    setup.setup_model_provider(load_config(), quick=True)

    assert len(captured) == 2
    assert captured[0] == captured[1]
    for labels in captured:
        assert not any("Nous Portal" in label for label in labels)
        assert not any(
            label.startswith(_HIDDEN_TOOL_CHOICE) for label in labels
        )


def test_cli_tool_provider_matrix_has_no_subscription_choices(monkeypatch):
    from athena_cli import tools_config

    _stub_subscription_state(monkeypatch, tools_config)

    checked = 0
    for key, category in tools_config.TOOL_CATEGORIES.items():
        rows = tools_config._visible_providers(category, {})
        _assert_no_subscription_choice(rows, surface=f"athena tools:{key}")
        checked += 1

    assert checked > 0


@pytest.mark.asyncio
async def test_dashboard_tool_payload_matches_hidden_cli_policy(monkeypatch):
    from athena_cli import tools_config
    from athena_cli.web_routers.tools import get_toolset_config

    _stub_subscription_state(monkeypatch, tools_config)
    configurable = {
        key
        for key, _label, _description
        in tools_config._get_effective_configurable_toolsets()
    }
    keys = sorted(configurable & tools_config.TOOL_CATEGORIES.keys())
    assert keys

    for key in keys:
        cli_rows = tools_config._visible_providers(
            tools_config.TOOL_CATEGORIES[key],
            {},
            force_fresh=True,
        )
        payload = await get_toolset_config(key)
        dashboard_rows = payload["providers"]

        _assert_no_subscription_choice(
            cli_rows,
            surface=f"athena tools:{key}",
        )
        _assert_no_subscription_choice(
            dashboard_rows,
            surface=f"dashboard:{key}",
        )
        assert [row["name"] for row in dashboard_rows] == [
            row["name"] for row in cli_rows
        ]
