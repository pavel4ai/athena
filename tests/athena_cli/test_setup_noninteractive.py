"""Tests for non-interactive setup and first-run headless behavior."""

from argparse import Namespace
from unittest.mock import patch

import pytest
from athena_cli.config import DEFAULT_CONFIG, load_config, save_config


def _make_setup_args(**overrides):
    return Namespace(
        non_interactive=overrides.get("non_interactive", False),
        section=overrides.get("section", None),
        reset=overrides.get("reset", False),
    )


def _make_chat_args(**overrides):
    return Namespace(
        continue_last=overrides.get("continue_last", None),
        resume=overrides.get("resume", None),
        model=overrides.get("model", None),
        provider=overrides.get("provider", None),
        toolsets=overrides.get("toolsets", None),
        verbose=overrides.get("verbose", False),
        query=overrides.get("query", None),
        worktree=overrides.get("worktree", False),
        yolo=overrides.get("yolo", False),
        pass_session_id=overrides.get("pass_session_id", False),
        quiet=overrides.get("quiet", False),
        checkpoints=overrides.get("checkpoints", False),
    )


class TestNonInteractiveSetup:
    """Verify setup paths exit cleanly in headless/non-interactive environments."""

    def test_cmd_setup_allows_noninteractive_flag_without_tty(self):
        """The CLI entrypoint should not block --non-interactive before setup.py handles it."""
        from athena_cli.main import cmd_setup

        args = _make_setup_args(non_interactive=True)

        with (
            patch("athena_cli.setup.run_setup_wizard") as mock_run_setup,
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            cmd_setup(args)

        mock_run_setup.assert_called_once_with(args)

    def test_cmd_setup_defers_no_tty_handling_to_setup_wizard(self):
        """Bare `athena setup` should reach setup.py, which prints headless guidance."""
        from athena_cli.main import cmd_setup

        args = _make_setup_args(non_interactive=False)

        with (
            patch("athena_cli.setup.run_setup_wizard") as mock_run_setup,
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            cmd_setup(args)

        mock_run_setup.assert_called_once_with(args)

    def test_non_interactive_flag_skips_wizard(self, capsys):
        """--non-interactive should print guidance and not enter the wizard."""
        from athena_cli.setup import run_setup_wizard

        args = _make_setup_args(non_interactive=True)

        with (
            patch("athena_cli.setup.ensure_athena_home"),
            patch("athena_cli.setup.load_config", return_value={}),
            patch("athena_cli.setup.get_athena_home", return_value="/tmp/.athena"),
            patch("athena_cli.auth.get_active_provider", side_effect=AssertionError("wizard continued")),
            patch("builtins.input", side_effect=AssertionError("input should not be called")),
        ):
            run_setup_wizard(args)

        out = capsys.readouterr().out
        assert "athena config set model.provider custom" in out

    def test_no_tty_skips_wizard(self, capsys):
        """When stdin has no TTY, the setup wizard should print guidance and return."""
        from athena_cli.setup import run_setup_wizard

        args = _make_setup_args(non_interactive=False)

        with (
            patch("athena_cli.setup.ensure_athena_home"),
            patch("athena_cli.setup.load_config", return_value={}),
            patch("athena_cli.setup.get_athena_home", return_value="/tmp/.athena"),
            patch("athena_cli.auth.get_active_provider", side_effect=AssertionError("wizard continued")),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", side_effect=AssertionError("input should not be called")),
        ):
            mock_stdin.isatty.return_value = False
            run_setup_wizard(args)

        out = capsys.readouterr().out
        assert "athena config set model.provider custom" in out

    def test_reset_flag_rewrites_config_before_noninteractive_exit(self, tmp_path, monkeypatch, capsys):
        """--reset should rewrite config.yaml even when the wizard cannot run interactively."""
        from athena_cli.setup import run_setup_wizard

        monkeypatch.setenv("ATHENA_HOME", str(tmp_path))
        cfg = load_config()
        cfg["model"] = {"provider": "custom", "base_url": "http://localhost:8080/v1", "default": "llama3"}
        cfg["agent"]["max_turns"] = 12
        save_config(cfg)

        args = _make_setup_args(non_interactive=True, reset=True)

        run_setup_wizard(args)

        reloaded = load_config()
        assert reloaded["model"] == DEFAULT_CONFIG["model"]
        assert reloaded["agent"]["max_turns"] == DEFAULT_CONFIG["agent"]["max_turns"]
        out = capsys.readouterr().out
        assert "Configuration reset to defaults." in out

    def test_chat_first_run_headless_skips_setup_prompt(self, capsys):
        """Bare `athena` should not prompt for input when no provider exists and stdin is headless."""
        from athena_cli.main import cmd_chat

        args = _make_chat_args()

        with (
            patch("athena_cli.main._has_any_provider_configured", return_value=False),
            patch("athena_cli.main.cmd_setup") as mock_setup,
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", side_effect=AssertionError("input should not be called")),
        ):
            mock_stdin.isatty.return_value = False
            with pytest.raises(SystemExit) as exc:
                cmd_chat(args)

        assert exc.value.code == 1
        mock_setup.assert_not_called()
        out = capsys.readouterr().out
        assert "athena config set model.provider custom" in out

    def test_chat_missing_config_runs_setup_even_with_provider_env(self):
        """Fresh ATHENA_HOME must run setup even if ambient credentials exist."""
        from athena_cli.main import cmd_chat

        args = _make_chat_args()

        with (
            patch("athena_cli.main._is_first_run_config_missing", return_value=True),
            patch("athena_cli.main._has_any_provider_configured", return_value=True) as mock_has_provider,
            patch("athena_cli.main.cmd_setup") as mock_setup,
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = True
            cmd_chat(args)

        mock_has_provider.assert_not_called()
        mock_setup.assert_called_once_with(args)

    def test_chat_missing_config_headless_prints_guidance(self, capsys):
        """Fresh ATHENA_HOME without a TTY should print setup guidance and exit."""
        from athena_cli.main import cmd_chat

        args = _make_chat_args()

        with (
            patch("athena_cli.main._is_first_run_config_missing", return_value=True),
            patch("athena_cli.main.cmd_setup") as mock_setup,
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            with pytest.raises(SystemExit) as exc:
                cmd_chat(args)

        assert exc.value.code == 1
        mock_setup.assert_not_called()
        out = capsys.readouterr().out
        assert "this Athena profile has not been set up yet" in out
        assert "athena config set model.provider custom" in out

    def test_main_accepts_tts_setup_section(self, monkeypatch):
        """`athena setup tts` should parse and dispatch like other setup sections."""
        from athena_cli import main as main_mod

        received = {}

        def fake_cmd_setup(args):
            received["section"] = args.section

        monkeypatch.setattr(main_mod, "cmd_setup", fake_cmd_setup)
        monkeypatch.setattr("sys.argv", ["athena", "setup", "tts"])

        main_mod.main()

        assert received["section"] == "tts"

    def test_main_accepts_x_twitter_setup_section(self, monkeypatch):
        """`athena setup x-twitter` should parse and dispatch."""
        from athena_cli import main as main_mod

        received = {}

        def fake_cmd_setup(args):
            received["section"] = args.section

        monkeypatch.setattr(main_mod, "cmd_setup", fake_cmd_setup)
        monkeypatch.setattr("sys.argv", ["athena", "setup", "x-twitter"])

        main_mod.main()

        assert received["section"] == "x-twitter"
