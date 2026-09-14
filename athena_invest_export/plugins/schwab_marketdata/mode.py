"""Schwab broker mode: mock (paper) vs live.

A single switch decides whether order/account operations hit the real Trader API
or the MockBroker (paper trading on live quotes). Market-data quotes are ALWAYS
real regardless of mode.

Mode is stored in $ATHENA_HOME/athena_invest/schwab/mode.json:
  {"mode": "mock"}   or   {"mode": "live"}
Default when the file is absent: "mock" (safe — never touches a live account by
accident). Going live is an explicit, logged action.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .oauth import _athena_home


def _mode_path() -> Path:
    p = _athena_home() / "athena_invest" / "schwab" / "mode.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_mode() -> str:
    p = _mode_path()
    if not p.exists():
        return "mock"
    try:
        return json.loads(p.read_text()).get("mode", "mock")
    except (ValueError, OSError):
        return "mock"


def set_mode(mode: str) -> Dict[str, str]:
    mode = mode.lower()
    if mode not in ("mock", "live"):
        raise ValueError("mode must be 'mock' or 'live'")
    _mode_path().write_text(json.dumps({"mode": mode}))
    return {"mode": mode}


def is_mock() -> bool:
    return get_mode() == "mock"
