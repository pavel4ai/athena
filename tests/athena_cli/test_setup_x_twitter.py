"""Athena-specific setup policy for X/Twitter news and first-run modes."""

from __future__ import annotations

import shutil

from athena_cli import setup


def test_x_twitter_section_is_available_without_portal_quick_mode():
    section_keys = [key for key, _label, _func in setup.SETUP_SECTIONS]
    first_time_labels = [label for label, _runner in setup._FIRST_TIME_MODES]

    assert "x-twitter" in section_keys
    assert all("Nous Portal" not in label for label in first_time_labels)
    assert len(first_time_labels) == 2


def test_x_twitter_setup_can_skip_without_changing_config(monkeypatch):
    config = {}
    monkeypatch.setattr(setup, "prompt_yes_no", lambda *args, **kwargs: False)

    setup.setup_x_twitter_news(config)

    assert config == {}


def test_x_twitter_setup_stores_only_non_secret_metadata(monkeypatch):
    config = {}
    answers = iter(("AthenaNews", "@athena_invest"))
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/xurl")
    monkeypatch.setattr(setup, "prompt_yes_no", lambda *args, **kwargs: True)
    monkeypatch.setattr(setup, "prompt", lambda *args, **kwargs: next(answers))

    setup.setup_x_twitter_news(config)

    assert config["social"]["xurl"] == {
        "app_name": "AthenaNews",
        "username": "athena_invest",
    }
    serialized = repr(config).lower()
    assert "token" not in serialized
    assert "secret" not in serialized
