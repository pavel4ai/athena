"""Hermetic safeguards for the portable investment plugin tests."""

from __future__ import annotations

import os
import socket

import pytest


def _schwab_environment_names() -> tuple[str, ...]:
    return tuple(name for name in os.environ if name.startswith("SCHWAB_"))


# Test modules can import plugin packages during collection, before fixtures run.
# Remove production brokerage settings at conftest import time as well.
for _name in _schwab_environment_names():
    os.environ.pop(_name, None)


@pytest.fixture(autouse=True)
def _isolated_schwab_test_environment(tmp_path, monkeypatch):
    for name in _schwab_environment_names():
        monkeypatch.delenv(name, raising=False)

    athena_home = tmp_path / "athena-home"
    athena_home.mkdir()
    monkeypatch.setenv("ATHENA_HOME", str(athena_home))

    real_socket = socket.socket

    def blocked_network_socket(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError("network disabled in Schwab plugin tests")
        return real_socket(family, *args, **kwargs)

    monkeypatch.setattr(socket, "socket", blocked_network_socket)
