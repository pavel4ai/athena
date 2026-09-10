"""Behavior contracts for supplemental CLI status-line providers."""

from __future__ import annotations

import pytest

from athena_cli import status_lines


@pytest.fixture(autouse=True)
def _isolated_provider_registry():
    original = list(status_lines._PROVIDERS)
    status_lines._PROVIDERS.clear()
    yield
    status_lines._PROVIDERS[:] = original


def test_registration_is_idempotent_and_preserves_order():
    first = lambda: [("", "first")]
    second = lambda: [("", "second")]

    status_lines.register_supplemental_status_line(first)
    status_lines.register_supplemental_status_line(first)
    status_lines.register_supplemental_status_line(second)

    assert status_lines.get_supplemental_status_providers() == [first, second]


def test_provider_snapshot_cannot_mutate_registry():
    provider = lambda: [("", "value")]
    status_lines.register_supplemental_status_line(provider)

    snapshot = status_lines.get_supplemental_status_providers()
    snapshot.clear()

    assert status_lines.get_supplemental_status_providers() == [provider]


def test_fragments_merge_nonempty_providers_with_separator():
    status_lines.register_supplemental_status_line(
        lambda: [("class:market", "MKT 10s")]
    )
    status_lines.register_supplemental_status_line(lambda: [])
    status_lines.register_supplemental_status_line(
        lambda: [("class:news", "NEWS 20s")]
    )

    assert status_lines.merged_supplemental_fragments() == [
        ("class:market", "MKT 10s"),
        ("", "  "),
        ("class:news", "NEWS 20s"),
    ]


def test_failing_provider_does_not_hide_later_provider():
    def fail():
        raise RuntimeError("provider failed")

    status_lines.register_supplemental_status_line(fail)
    status_lines.register_supplemental_status_line(
        lambda: [("class:healthy", "healthy")]
    )

    assert status_lines.merged_supplemental_fragments() == [
        ("class:healthy", "healthy")
    ]


def test_provider_added_during_render_is_deferred_until_next_render():
    late = lambda: [("", "late")]

    def first():
        status_lines.register_supplemental_status_line(late)
        return [("", "first")]

    status_lines.register_supplemental_status_line(first)

    assert status_lines.merged_supplemental_fragments() == [("", "first")]
    assert status_lines.merged_supplemental_fragments() == [
        ("", "first"),
        ("", "  "),
        ("", "late"),
    ]
