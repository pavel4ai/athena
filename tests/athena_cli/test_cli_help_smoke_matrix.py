"""Smoke contracts for top-level built-in command help."""

from __future__ import annotations

import sys

import pytest


def test_every_safe_builtin_subcommand_help_exits_before_dispatch(
    monkeypatch,
    capsys,
):
    from athena_cli import config as config_mod
    from athena_cli import main as cli_main

    dispatched: list[str] = []

    def reject_dispatch(*_args, **_kwargs):
        dispatched.append(sys.argv[1])
        raise AssertionError(f"{sys.argv[1]} --help reached command dispatch")

    monkeypatch.setattr(cli_main, "_set_process_title", lambda: None)
    monkeypatch.setattr(cli_main, "_cleanup_quarantined_exes", lambda: None)
    monkeypatch.setattr(cli_main, "_recover_from_interrupted_install", lambda: None)
    monkeypatch.setattr(cli_main, "_try_termux_fast_tui_launch", lambda: False)
    monkeypatch.setattr(cli_main, "_try_termux_fast_cli_launch", lambda: False)
    monkeypatch.setattr(cli_main, "_prepare_agent_startup", reject_dispatch)
    monkeypatch.setattr(cli_main, "_exec_in_container", reject_dispatch)
    monkeypatch.setattr(config_mod, "get_container_exec_info", lambda: None)

    for name in tuple(vars(cli_main)):
        if name.startswith("cmd_"):
            monkeypatch.setattr(cli_main, name, reject_dispatch)

    commands = sorted(cli_main._BUILTIN_SUBCOMMANDS - {"help"})
    assert commands

    for command in commands:
        monkeypatch.setattr(sys, "argv", ["athena", command, "--help"])

        with pytest.raises(SystemExit) as exc_info:
            cli_main.main()

        captured = capsys.readouterr()
        assert exc_info.value.code == 0, (
            f"{command} --help exited with {exc_info.value.code}: "
            f"{captured.err or captured.out}"
        )
        assert "usage: athena" in captured.out.lower(), (
            f"{command} --help did not print argparse help"
        )

    assert dispatched == []
