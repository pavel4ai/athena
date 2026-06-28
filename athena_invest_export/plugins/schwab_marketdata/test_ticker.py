"""Tests for the Schwab CLI ticker status-line fragments."""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schwab_marketdata import ticker  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_ticker_state():
    original = {
        "quotes": dict(ticker._state["quotes"]),
        "updated_at": ticker._state["updated_at"],
        "next_refresh_at": ticker._state.get("next_refresh_at", 0.0),
        "symbols": list(ticker._state["symbols"]),
        "running": ticker._state["running"],
        "thread": ticker._state["thread"],
    }
    yield
    ticker._state.update(original)


def test_ticker_fragments_include_refresh_countdown(monkeypatch):
    now = time.time()
    ticker._state["symbols"] = ["AAPL"]
    ticker._state["quotes"] = {"AAPL": {"last": 123.45, "pct": 1.23}}
    ticker._state["updated_at"] = now
    ticker._state["next_refresh_at"] = now + 12

    monkeypatch.setattr(ticker.time, "time", lambda: now)

    frags = ticker.get_ticker_fragments()
    rendered = "".join(text for _style, text in frags)

    assert "MKT ⏱12s" in rendered
    assert "AAPL 123.45 ▲1.23%" in rendered


def test_refresh_countdown_clamps_at_zero(monkeypatch):
    now = time.time()
    ticker._state["next_refresh_at"] = now - 5
    monkeypatch.setattr(ticker.time, "time", lambda: now)

    assert ticker._refresh_countdown() == "0s"
