"""Black-box CLI contracts against a fresh isolated Athena home."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "ATHENA_HOME": str(home),
            "CI": "1",
            "NO_COLOR": "1",
            "TERM": "dumb",
        }
    )
    for name in tuple(env):
        if name.startswith("SCHWAB_"):
            env.pop(name, None)

    return subprocess.run(
        [sys.executable, "-m", "athena_cli.main", *args],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_version_uses_athena_identity_with_fresh_home(tmp_path):
    home = tmp_path / "fresh-home"

    result = _run_cli(home, "--version")

    assert result.returncode == 0
    assert "Athena Agent" in result.stdout
    assert "Traceback" not in result.stderr


def test_noninteractive_first_run_fails_with_setup_guidance(tmp_path):
    home = tmp_path / "fresh-home"

    result = _run_cli(home)
    output = result.stdout + result.stderr

    assert result.returncode == 1
    assert "athena setup" in output.lower()
    assert "no interactive tty" in output.lower()
    assert "Traceback" not in output
    assert not (home / "config.yaml").exists()
