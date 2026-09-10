"""Integration contracts for supplemental classic-CLI status bars."""

from __future__ import annotations

import pytest

from athena_cli import status_lines


@pytest.fixture(autouse=True)
def _isolated_provider_registry():
    original = list(status_lines._PROVIDERS)
    status_lines._PROVIDERS.clear()
    yield
    status_lines._PROVIDERS[:] = original


def test_athena_cli_registration_delegates_to_shared_registry(monkeypatch):
    from cli import AthenaCLI

    provider = lambda: [("", "delegated")]
    registered = []
    monkeypatch.setattr(
        status_lines,
        "register_supplemental_status_line",
        registered.append,
    )

    AthenaCLI.register_supplemental_status_line(provider)

    assert registered == [provider]


def test_registered_fragments_render_between_extension_and_primary_status():
    from prompt_toolkit.layout import ConditionalContainer, Window

    from cli import AthenaCLI

    calls: list[str] = []

    def failing_provider():
        calls.append("failing")
        raise RuntimeError("provider unavailable")

    def healthy_provider():
        calls.append("healthy")
        return [("class:healthy", "healthy")]

    AthenaCLI.register_supplemental_status_line(failing_provider)
    AthenaCLI.register_supplemental_status_line(healthy_provider)

    cli = AthenaCLI.__new__(AthenaCLI)
    cli._get_extra_tui_widgets = lambda: ["extension"]
    children = cli._build_tui_layout_children(
        sudo_widget="sudo",
        secret_widget="secret",
        approval_widget="approval",
        slash_confirm_widget="slash-confirm",
        clarify_widget="clarify",
        model_picker_widget="model-picker",
        spinner_widget="spinner",
        spacer="spacer",
        status_bar="primary-status",
        input_rule_top="top-rule",
        image_bar="image-bar",
        input_area="input-area",
        input_rule_bot="bottom-rule",
        voice_status_bar="voice-status",
        completions_menu="completions-menu",
    )

    primary_index = children.index("primary-status")
    supplemental = children[primary_index - 1]

    assert children[primary_index - 2] == "extension"
    assert isinstance(supplemental, ConditionalContainer)
    assert isinstance(supplemental.content, Window)
    assert supplemental.content.height == 1
    assert supplemental.content.wrap_lines() is False
    assert supplemental.filter() is True
    assert supplemental.content.content.text() == [
        ("class:healthy", "healthy")
    ]
    assert "failing" in calls
    assert "healthy" in calls

    AthenaCLI.register_supplemental_status_line(
        lambda: [("class:late", "late")]
    )
    assert supplemental.content.content.text() == [
        ("class:healthy", "healthy"),
        ("", "  "),
        ("class:late", "late"),
    ]
