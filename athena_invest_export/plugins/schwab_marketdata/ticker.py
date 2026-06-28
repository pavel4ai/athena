"""Bloomberg-style live ticker bar for the Athena CLI.

Renders a single fitted status line of prominent mega-cap securities with live
near-real-time prices and % change, sourced from the Schwab Market Data REST
API. Registers itself into Athena's generic supplemental-status-line hook
(cli.AthenaCLI.register_supplemental_status_line).

Safety / gating:
  - Only activates if Schwab credentials are present AND a live quote actually
    comes back. If the API is down or unconfigured, the bar simply never renders
    (the provider returns []), so it can never break the prompt.
  - A background daemon thread refreshes a price cache every REFRESH_SECONDS.
    The render path only reads the cache — it never makes a network call, so it
    can't block or slow the TUI.
  - All exceptions are swallowed; a failure just yields an empty (hidden) bar.

Enable by importing and calling start_ticker() (done from the plugin register()
when running in the CLI). Mega-cap symbol list is static + override-able.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Prominent large-cap names (by market cap, broad + recognizable). Kept short so
# the line fits a normal terminal; trimmed further to terminal width at render.
DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "SPY", "QQQ"]

REFRESH_SECONDS = 15          # how often the poller refreshes quotes
STALE_AFTER_SECONDS = 120     # hide the bar if data is older than this

_state = {
    "quotes": {},             # symbol -> {"last": float, "pct": float}
    "updated_at": 0.0,
    "next_refresh_at": 0.0,
    "thread": None,
    "running": False,
    "symbols": list(DEFAULT_SYMBOLS),
}


def _poll_once() -> None:
    """Fetch quotes for the symbol set and update the cache. Never raises."""
    try:
        from . import rest_marketdata as rmd
        raw = rmd.get_quotes(_state["symbols"])
        simple = rmd.simplify_quotes(raw)
        q = {}
        for sym, data in simple.items():
            last = data.get("last_price")
            pct = data.get("net_percent_change")
            if last is not None:
                q[sym] = {"last": last, "pct": pct if pct is not None else 0.0}
        if q:
            _state["quotes"] = q
            now = time.time()
            _state["updated_at"] = now
            _state["next_refresh_at"] = now + REFRESH_SECONDS
    except Exception as exc:
        logger.debug("ticker poll failed: %s", exc)


def _poller_loop() -> None:
    # Prime once immediately, then on cadence.
    _poll_once()
    while _state["running"]:
        time.sleep(REFRESH_SECONDS)
        if not _state["running"]:
            break
        _poll_once()


def start_ticker(symbols: Optional[List[str]] = None) -> bool:
    """Start the background poller. Returns True if it started (creds present)."""
    if not (os.getenv("SCHWAB_APP_KEY") and os.getenv("SCHWAB_APP_SECRET")):
        return False
    if _state["running"]:
        return True
    if symbols:
        _state["symbols"] = list(symbols)
    _state["running"] = True
    t = threading.Thread(target=_poller_loop, name="schwab-ticker", daemon=True)
    _state["thread"] = t
    t.start()
    return True


def stop_ticker() -> None:
    _state["running"] = False


def _fmt_symbol(sym: str, last: float, pct: float) -> Tuple[str, str]:
    """Return (style_class, text) for one symbol cell."""
    arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "·")
    if pct > 0:
        style = "class:ticker-up"
    elif pct < 0:
        style = "class:ticker-down"
    else:
        style = "class:ticker-flat"
    # compact: AAPL 282.65 ▲0.42%
    txt = f"{sym} {last:,.2f} {arrow}{abs(pct):.2f}%"
    return style, txt


def _refresh_countdown(now: Optional[float] = None) -> str:
    """Return compact countdown until the next scheduled quote refresh."""
    target = float(_state.get("next_refresh_at") or 0.0)
    if target <= 0:
        return ""
    remaining = max(0, int(round(target - (time.time() if now is None else now))))
    if remaining >= 60:
        return f"{remaining // 60}m{remaining % 60:02d}s"
    return f"{remaining}s"


def get_ticker_fragments() -> list:
    """Fragment-provider for the supplemental status line. Reads cache only.

    Returns [] (hidden bar) when no fresh data — so the bar is invisible unless
    live Schwab data is flowing. Lazily starts the background poller on first
    call so the ticker works regardless of plugin-load ordering.
    """
    if not _state["running"]:
        start_ticker()

    updated = _state["updated_at"]
    if not updated or (time.time() - updated) > STALE_AFTER_SECONDS:
        return []
    quotes = _state["quotes"]
    if not quotes:
        return []

    # terminal width (best effort)
    try:
        import shutil
        width = shutil.get_terminal_size().columns
    except Exception:
        width = 100

    sep = ("class:ticker-sep", "  │  ")
    countdown = _refresh_countdown()
    label_text = f" MKT ⏱{countdown} " if countdown else " MKT "
    label = ("class:ticker-label", label_text)
    frags = [label]
    used = len(label_text)
    for sym in _state["symbols"]:
        q = quotes.get(sym)
        if not q:
            continue
        style, txt = _fmt_symbol(sym, q["last"], q["pct"])
        cell_len = len(txt) + len("  │  ")
        if used + cell_len > width - 2:
            break
        if len(frags) > 1:
            frags.append(sep)
            used += len("  │  ")
        frags.append((style, txt))
        used += len(txt)
    if len(frags) <= 1:
        return []
    return frags


# Style classes the ticker uses (green up / red down / dim flat). Athena's TUI
# style dict won't define these, but prompt_toolkit tolerates unknown classes by
# rendering plain; for color we provide inline fallbacks via fragment styles.
TICKER_STYLE = {
    "ticker-up": "#3ddc84",
    "ticker-down": "#ff5c5c",
    "ticker-flat": "#888888",
    "ticker-sep": "#555555",
    "ticker-label": "bold #FFD700",
}


def register_with_cli() -> bool:
    """Register the ticker fragment-provider into the Athena CLI hook.

    Returns True if registration succeeded. Safe no-op if the CLI class or hook
    is unavailable (e.g. running in the gateway, not the CLI).
    """
    try:
        import cli  # Athena core CLI module
        if not hasattr(cli.AthenaCLI, "register_supplemental_status_line"):
            logger.info("ticker: CLI lacks supplemental-status hook; skipping.")
            return False
        # Use a style-injecting wrapper: prepend inline color so it renders even
        # if the TUI style dict doesn't know our classes.
        cli.AthenaCLI.register_supplemental_status_line(_styled_fragments)
        return True
    except Exception as exc:
        logger.debug("ticker register_with_cli failed: %s", exc)
        return False


def _styled_fragments() -> list:
    """Map our class-based fragments to inline-styled fragments for portability."""
    out = []
    for style, text in get_ticker_fragments():
        cls = style.split(":", 1)[-1]
        color = TICKER_STYLE.get(cls, "")
        out.append((color, text) if color else (style, text))
    return out
