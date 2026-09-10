"""Contracts that keep tests away from production credentials and state."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


SCHWAB_TEST_ENV_VARS = (
    "SCHWAB_APP_KEY",
    "SCHWAB_APP_SECRET",
    "SCHWAB_TRADER_APP_KEY",
    "SCHWAB_TRADER_APP_SECRET",
    "SCHWAB_CALLBACK_URL",
)


@pytest.mark.parametrize("name", SCHWAB_TEST_ENV_VARS)
def test_schwab_environment_is_removed_before_test(name):
    assert name not in os.environ


def test_tests_never_use_default_production_athena_home():
    test_home = Path(os.environ["ATHENA_HOME"]).resolve()
    production_home = (Path.home() / ".athena").resolve()

    assert test_home != production_home
