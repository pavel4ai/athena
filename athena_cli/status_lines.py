"""Process-wide registry for supplemental CLI status lines.

Lives in the ``athena_cli`` package so it's a single stable module object no
matter how the main CLI is imported (``__main__`` when run as a script, or
``cli`` when imported by tests/plugins). Plugins register fragment-providers
here; the running CLI reads them at render time to paint extra status bars
(e.g. a live market-data ticker) above the main status bar.

A provider is a zero-arg callable returning a list of prompt_toolkit
``(style, text)`` fragments, or ``[]`` to render nothing this frame.
"""

from __future__ import annotations

from typing import Callable, List

_PROVIDERS: List[Callable[[], list]] = []


def register_supplemental_status_line(provider: Callable[[], list]) -> None:
    """Register a fragment-provider for an extra CLI status line (idempotent)."""
    if provider not in _PROVIDERS:
        _PROVIDERS.append(provider)


def get_supplemental_status_providers() -> List[Callable[[], list]]:
    """Return the registered providers (live list snapshot)."""
    return list(_PROVIDERS)


def merged_supplemental_fragments() -> list:
    """Merge all providers' fragments into one line; [] when all are empty."""
    out: list = []
    for provider in list(_PROVIDERS):
        try:
            frags = provider() or []
        except Exception:
            frags = []
        if frags:
            if out:
                out.append(("", "  "))
            out.extend(frags)
    return out
