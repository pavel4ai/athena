"""Regression tests for _apply_profile_override ATHENA_HOME guard (issue #22502).

When ATHENA_HOME is set to the athena root (e.g. systemd hardcodes
ATHENA_HOME=/root/.athena), _apply_profile_override must still read
active_profile and update ATHENA_HOME to the profile directory.

When ATHENA_HOME is already a profile directory (.../profiles/<name>),
_apply_profile_override must trust it and return without re-reading
active_profile (child-process inheritance contract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace


def _run_apply_profile_override(
    tmp_path, monkeypatch, *, athena_home: str | None, active_profile: str | None,
    argv: list[str] | None = None, extra_env: dict[str, str] | None = None,
):
    """Run _apply_profile_override in isolation.

    Returns the value of os.environ["ATHENA_HOME"] after the call,
    or None if unset.
    """
    athena_root = tmp_path / ".athena"
    athena_root.mkdir(parents=True, exist_ok=True)

    if active_profile is not None:
        (athena_root / "active_profile").write_text(active_profile)

    if active_profile and active_profile != "default":
        (athena_root / "profiles" / active_profile).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    if athena_home is not None:
        monkeypatch.setenv("ATHENA_HOME", athena_home)
    else:
        monkeypatch.delenv("ATHENA_HOME", raising=False)

    monkeypatch.setattr(sys, "argv", argv or ["athena", "gateway", "start"])

    # Scrub supervisor markers the host environment may carry (systemd-run
    # CI runners export INVOCATION_ID) so each test controls them explicitly.
    for var in (
        "ATHENA_SUPERVISED_CHILD",
        "ATHENA_S6_SUPERVISED_CHILD",
        "INVOCATION_ID",
        "ATHENA_GATEWAY_EXTERNAL_SUPERVISOR",
    ):
        monkeypatch.delenv(var, raising=False)

    for key, value in (extra_env or {}).items():
        monkeypatch.setenv(key, value)

    from athena_cli.main import _apply_profile_override
    _apply_profile_override()

    return os.environ.get("ATHENA_HOME")


class TestApplyProfileOverrideAthenaHomeGuard:
    """Regression guard for issue #22502.

    Verifies that ATHENA_HOME pointing to the athena root does NOT suppress
    the active_profile check, while ATHENA_HOME already pointing to a
    profile directory IS trusted as-is.
    """

    def test_athena_home_at_root_with_active_profile_is_redirected(
        self, tmp_path, monkeypatch
    ):
        """ATHENA_HOME=/root/.athena + active_profile=coder must redirect
        ATHENA_HOME to .../profiles/coder.

        Bug scenario from #22502: systemd sets ATHENA_HOME to the athena root
        and the user switches to a profile via `athena profile use`.
        Before the fix, the guard returned early and active_profile was ignored.
        """
        athena_root = tmp_path / ".athena"
        athena_root.mkdir(parents=True, exist_ok=True)

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=str(athena_root),
            active_profile="coder",
        )

        assert result is not None, "ATHENA_HOME must be set after profile redirect"
        assert "profiles" in result, (
            f"Expected ATHENA_HOME to point into profiles/ dir, got: {result!r}"
        )
        assert result.endswith("coder"), (
            f"Expected ATHENA_HOME to end with 'coder', got: {result!r}"
        )


    def test_sudo_explicit_profile_resolves_invoking_users_profile(self, tmp_path, monkeypatch):
        """sudo elias ... should resolve `-p elias` under SUDO_USER, not root."""
        root_home = tmp_path / "root"
        user_home = tmp_path / "home" / "athena"
        profile_dir = user_home / ".athena" / "profiles" / "elias"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (root_home / ".athena").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: root_home)
        monkeypatch.setenv("SUDO_USER", "athena")
        monkeypatch.delenv("ATHENA_HOME", raising=False)
        monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
        monkeypatch.setattr(sys, "argv", ["athena", "-p", "elias", "gateway", "install", "--system"])

        import pwd

        monkeypatch.setattr(pwd, "getpwnam", lambda name: SimpleNamespace(pw_dir=str(user_home)))

        from athena_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("ATHENA_HOME") == str(profile_dir)
        assert sys.argv == ["athena", "gateway", "install", "--system"]




class TestSupervisedChildIgnoresStickyProfile:
    """The reserved default gateway s6 slot must not follow active_profile.

    Inside the Docker s6 image the ``gateway-default`` service slot runs a
    bare ``athena gateway run`` (no ``-p``) to mean "the root ATHENA_HOME
    profile". The run-script exports ``ATHENA_S6_SUPERVISED_CHILD=1``.
    Without a guard, ``_apply_profile_override`` would read the sticky
    ``active_profile`` file (set by e.g. the dashboard profile switcher) and
    redirect the reserved default gateway into that profile — producing a
    duplicate gateway for the active profile and no real default gateway.
    """


    def test_non_supervised_run_still_follows_active_profile(
        self, tmp_path, monkeypatch
    ):
        """Without the sentinel, a normal `athena gateway run` still honors
        active_profile — the guard is scoped strictly to supervised children."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=None,
            active_profile="briefer",
            argv=["athena", "gateway", "run"],
        )

        assert result is not None
        assert result.endswith("briefer")

    def test_supervised_named_profile_flag_still_wins(self, tmp_path, monkeypatch):
        """A supervised named-profile slot passes ``-p <name>`` explicitly;
        that must still resolve (the sentinel guard only skips the sticky
        active_profile fallback, never an explicit flag)."""
        athena_root = tmp_path / ".athena"
        athena_root.mkdir(parents=True, exist_ok=True)
        (athena_root / "active_profile").write_text("briefer")
        (athena_root / "profiles" / "briefer").mkdir(parents=True, exist_ok=True)
        (athena_root / "profiles" / "coder").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("ATHENA_HOME", raising=False)
        monkeypatch.setenv("ATHENA_S6_SUPERVISED_CHILD", "1")
        monkeypatch.setattr(sys, "argv", ["athena", "-p", "coder", "gateway", "run"])

        from athena_cli.main import _apply_profile_override
        _apply_profile_override()

        result = os.environ.get("ATHENA_HOME")
        assert result is not None
        assert result.endswith("coder")



class TestGeneralizedSupervisorMarkers:
    """Regression tests for issue #74872.

    A systemd/launchd/Scheduled-Task supervised gateway launch pins its
    profile identity via the unit's ATHENA_HOME (root home for the default
    profile). It must NEVER follow the sticky ``active_profile`` file —
    otherwise the default-profile gateway silently assumes another profile's
    identity (logs + Telegram bot token) and double-polls that profile's
    token. Markers: ATHENA_SUPERVISED_CHILD (generalized, exported by
    generated units), INVOCATION_ID (systemd, gateway commands only), and
    ATHENA_GATEWAY_EXTERNAL_SUPERVISOR (explicit opt-in).
    """

    def _root_home(self, tmp_path):
        athena_root = tmp_path / ".athena"
        athena_root.mkdir(parents=True, exist_ok=True)
        return athena_root

    def test_supervised_child_marker_skips_active_profile(
        self, tmp_path, monkeypatch
    ):
        """ATHENA_SUPERVISED_CHILD=1 + root ATHENA_HOME must keep the
        default profile's home even when active_profile names another
        profile (the #74872 identity-assumption vector)."""
        athena_root = self._root_home(tmp_path)
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=str(athena_root),
            active_profile="telegram_nick",
            argv=["athena", "gateway", "run"],
            extra_env={"ATHENA_SUPERVISED_CHILD": "1"},
        )
        assert result == str(athena_root), (
            f"supervised default gateway was redirected to {result!r}"
        )

    def test_systemd_invocation_id_skips_active_profile_for_gateway(
        self, tmp_path, monkeypatch
    ):
        """INVOCATION_ID (systemd service child) must suppress the sticky
        redirect for gateway commands — covers units installed before the
        ATHENA_SUPERVISED_CHILD marker existed."""
        athena_root = self._root_home(tmp_path)
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=str(athena_root),
            active_profile="telegram_nick",
            argv=["athena", "gateway", "run"],
            extra_env={"INVOCATION_ID": "deadbeef" * 4},
        )
        assert result == str(athena_root)

    def test_invocation_id_does_not_affect_non_gateway_commands(
        self, tmp_path, monkeypatch
    ):
        """INVOCATION_ID leaks into every descendant of a systemd-launched
        process (CI runners, user services). Non-gateway commands must keep
        honoring the sticky active_profile."""
        athena_root = self._root_home(tmp_path)
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=str(athena_root),
            active_profile="coder",
            argv=["athena", "chat"],
            extra_env={"INVOCATION_ID": "deadbeef" * 4},
        )
        assert result is not None
        assert result.endswith("coder")

    def test_external_supervisor_marker_skips_active_profile(
        self, tmp_path, monkeypatch
    ):
        athena_root = self._root_home(tmp_path)
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=str(athena_root),
            active_profile="telegram_nick",
            argv=["athena", "gateway", "run"],
            extra_env={"ATHENA_GATEWAY_EXTERNAL_SUPERVISOR": "1"},
        )
        assert result == str(athena_root)

    def test_desktop_ssh_serve_child_skips_active_profile(self, tmp_path, monkeypatch):
        """A Desktop-owned `serve --ssh-session-token-file` child names its profile explicitly
        (or none for the root home); the remote host's sticky active_profile must not re-home
        it, or Settings read one profile's config.yaml while the user edits another."""
        athena_root = self._root_home(tmp_path)
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            athena_home=str(athena_root),
            active_profile="telegram_nick",
            argv=["athena", "serve", "--isolated", "--host", "127.0.0.1", "--port", "0",
                  "--ssh-session-token-file", "/tmp/x/y.token"],
        )
        assert result == str(athena_root)

    def test_generated_systemd_unit_exports_supervised_marker(
        self, tmp_path, monkeypatch
    ):
        """The generated systemd unit must carry the marker so fresh installs
        are protected without relying on the INVOCATION_ID heuristic."""
        monkeypatch.setenv("ATHENA_HOME", str(tmp_path / "home"))
        (tmp_path / "home").mkdir()
        from athena_cli.gateway import generate_systemd_unit

        unit = generate_systemd_unit()
        assert 'Environment="ATHENA_SUPERVISED_CHILD=1"' in unit

    def test_generated_launchd_plist_exports_supervised_marker(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("ATHENA_HOME", str(tmp_path / "home"))
        (tmp_path / "home").mkdir()
        from athena_cli.gateway import generate_launchd_plist

        plist = generate_launchd_plist()
        assert "<key>ATHENA_SUPERVISED_CHILD</key>" in plist
