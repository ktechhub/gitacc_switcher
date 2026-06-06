"""Tests for CLI argument parsing and command dispatch."""

import sys
import argparse
import pytest
from unittest.mock import patch, MagicMock
from gitacc_switcher.cli import CLI


@pytest.fixture
def cli():
    with patch("gitacc_switcher.cli.AccountManager"):
        c = CLI()
    return c


# ---------------------------------------------------------------------------
# Parser configuration
# ---------------------------------------------------------------------------


class TestParserCommands:
    def test_add_default_key_type(self, cli):
        args = cli.parser.parse_args(["add"])
        assert args.command == "add"
        assert args.key_type == "rsa"

    def test_add_custom_key_type(self, cli):
        args = cli.parser.parse_args(["add", "--type", "ed25519"])
        assert args.key_type == "ed25519"

    def test_add_invalid_key_type_exits(self, cli):
        with pytest.raises(SystemExit):
            cli.parser.parse_args(["add", "--type", "invalid"])

    def test_switch_parses_account(self, cli):
        args = cli.parser.parse_args(["switch", "mywork"])
        assert args.command == "switch"
        assert args.account_name == "mywork"

    def test_remove_with_account(self, cli):
        args = cli.parser.parse_args(["remove", "mywork"])
        assert args.account_name == "mywork"

    def test_remove_without_account(self, cli):
        args = cli.parser.parse_args(["remove"])
        assert args.account_name is None

    def test_list_command(self, cli):
        assert cli.parser.parse_args(["list"]).command == "list"

    def test_logout_command(self, cli):
        assert cli.parser.parse_args(["logout"]).command == "logout"

    def test_init_parses_account(self, cli):
        args = cli.parser.parse_args(["init", "mywork"])
        assert args.account_name == "mywork"

    def test_verify_command(self, cli):
        assert cli.parser.parse_args(["verify"]).command == "verify"

    def test_update_no_flags(self, cli):
        args = cli.parser.parse_args(["update", "mywork"])
        assert args.account_name == "mywork"
        assert args.new_git_name is None
        assert args.new_email is None

    def test_update_with_name_flag(self, cli):
        args = cli.parser.parse_args(["update", "mywork", "--name", "New Name"])
        assert args.new_git_name == "New Name"

    def test_update_with_email_flag(self, cli):
        args = cli.parser.parse_args(["update", "mywork", "--email", "new@co.com"])
        assert args.new_email == "new@co.com"

    def test_update_with_both_flags(self, cli):
        args = cli.parser.parse_args(
            ["update", "mywork", "--name", "N", "--email", "e@e.com"]
        )
        assert args.new_git_name == "N"
        assert args.new_email == "e@e.com"

    def test_version_exits_cleanly(self, cli, capsys):
        with pytest.raises(SystemExit) as exc:
            cli.parser.parse_args(["--version"])
        assert exc.value.code == 0
        assert "gitacc" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Handler exit codes
# ---------------------------------------------------------------------------


class TestHandlers:
    def test_handle_add_success(self, cli):
        cli.account_manager.add_account.return_value = True
        assert cli._handle_add(argparse.Namespace(key_type="rsa")) == 0

    def test_handle_add_failure(self, cli):
        cli.account_manager.add_account.return_value = False
        assert cli._handle_add(argparse.Namespace(key_type="rsa")) == 1

    def test_handle_switch_success(self, cli):
        cli.account_manager.switch_account.return_value = True
        assert cli._handle_switch(argparse.Namespace(account_name="work")) == 0

    def test_handle_switch_failure(self, cli):
        cli.account_manager.switch_account.return_value = False
        assert cli._handle_switch(argparse.Namespace(account_name="work")) == 1

    def test_handle_remove_success(self, cli):
        cli.account_manager.remove_account.return_value = True
        assert cli._handle_remove(argparse.Namespace(account_name="work")) == 0

    def test_handle_logout_success(self, cli):
        cli.account_manager.logout.return_value = True
        assert cli._handle_logout(argparse.Namespace()) == 0

    def test_handle_verify_success(self, cli):
        cli.account_manager.verify_account.return_value = True
        assert cli._handle_verify(argparse.Namespace()) == 0

    def test_handle_verify_failure(self, cli):
        cli.account_manager.verify_account.return_value = False
        assert cli._handle_verify(argparse.Namespace()) == 1

    def test_handle_init_success(self, cli):
        cli.account_manager.init_repo.return_value = True
        assert cli._handle_init(argparse.Namespace(account_name="work")) == 0

    def test_handle_update_success(self, cli):
        cli.account_manager.update_account.return_value = True
        args = argparse.Namespace(
            account_name="work", new_git_name=None, new_email=None
        )
        assert cli._handle_update(args) == 0

    def test_handle_update_failure(self, cli):
        cli.account_manager.update_account.return_value = False
        args = argparse.Namespace(
            account_name="work", new_git_name=None, new_email=None
        )
        assert cli._handle_update(args) == 1


# ---------------------------------------------------------------------------
# List shows active account marker
# ---------------------------------------------------------------------------


class TestHandleList:
    def test_empty_accounts(self, cli, capsys):
        cli.account_manager.list_accounts_detailed.return_value = {}
        result = cli._handle_list(argparse.Namespace())
        assert result == 0
        assert "No accounts" in capsys.readouterr().out

    def test_active_account_marked(self, cli, capsys):
        cli.account_manager.list_accounts_detailed.return_value = {
            "work": {"name": "Work User", "email": "work@co.com"}
        }
        cli.account_manager.config_manager.get_current_git_config.return_value = {
            "name": "Work User",
            "email": "work@co.com",
        }
        cli._handle_list(argparse.Namespace())
        assert "* " in capsys.readouterr().out

    def test_inactive_account_uses_dash(self, cli, capsys):
        cli.account_manager.list_accounts_detailed.return_value = {
            "work": {"name": "Work User", "email": "work@co.com"}
        }
        cli.account_manager.config_manager.get_current_git_config.return_value = {
            "name": None,
            "email": None,
        }
        cli._handle_list(argparse.Namespace())
        assert "- work" in capsys.readouterr().out

    def test_git_name_different_from_identifier_shown(self, cli, capsys):
        cli.account_manager.list_accounts_detailed.return_value = {
            "work": {"name": "Jane Doe", "email": "jane@co.com"}
        }
        cli.account_manager.config_manager.get_current_git_config.return_value = {
            "name": None,
            "email": None,
        }
        cli._handle_list(argparse.Namespace())
        out = capsys.readouterr().out
        assert "Jane Doe" in out
        assert "work" in out


# ---------------------------------------------------------------------------
# run() — shorthand and dispatch
# ---------------------------------------------------------------------------


class TestRun:
    def test_no_args_shows_help(self, cli, capsys):
        with patch.object(sys, "argv", ["gitacc"]):
            result = cli.run()
        assert result == 0

    def test_shorthand_unknown_account_returns_error(self, cli):
        cli.account_manager.account_exists.return_value = False
        mock_args = argparse.Namespace(command=None)
        with patch.object(
            cli.parser, "parse_args", return_value=mock_args
        ), patch.object(sys, "argv", ["gitacc", "unknown"]):
            result = cli.run()
        assert result == 1

    def test_shorthand_known_account_switches(self, cli):
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.switch_account.return_value = True
        mock_args = argparse.Namespace(command=None)
        with patch.object(
            cli.parser, "parse_args", return_value=mock_args
        ), patch.object(sys, "argv", ["gitacc", "mywork"]):
            result = cli.run()
        assert result == 0
        cli.account_manager.switch_account.assert_called_once_with("mywork")

    def test_explicit_switch_command(self, cli):
        cli.account_manager.switch_account.return_value = True
        with patch.object(sys, "argv", ["gitacc", "switch", "mywork"]):
            result = cli.run()
        assert result == 0

    def test_list_command_runs(self, cli):
        cli.account_manager.list_accounts_detailed.return_value = {}
        with patch.object(sys, "argv", ["gitacc", "list"]):
            result = cli.run()
        assert result == 0

    def test_logout_command_runs(self, cli):
        cli.account_manager.logout.return_value = True
        with patch.object(sys, "argv", ["gitacc", "logout"]):
            result = cli.run()
        assert result == 0
