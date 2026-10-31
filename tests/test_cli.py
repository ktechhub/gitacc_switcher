"""Tests for CLI argument parsing and command dispatch."""

import sys
import argparse
import pytest
from unittest.mock import patch
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

    def test_add_sign_defaults_to_false(self, cli):
        args = cli.parser.parse_args(["add"])
        assert args.sign is False

    def test_add_sign_flag(self, cli):
        args = cli.parser.parse_args(["add", "--sign"])
        assert args.sign is True

    def test_switch_parses_account(self, cli):
        args = cli.parser.parse_args(["switch", "mywork"])
        assert args.command == "switch"
        assert args.account_name == "mywork"
        assert args.local is False

    def test_switch_local_flag(self, cli):
        args = cli.parser.parse_args(["switch", "mywork", "--local"])
        assert args.local is True

    def test_switch_local_short_flag(self, cli):
        args = cli.parser.parse_args(["switch", "mywork", "-l"])
        assert args.local is True

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

    def test_status_command(self, cli):
        assert cli.parser.parse_args(["status"]).command == "status"

    def test_init_parses_account(self, cli):
        args = cli.parser.parse_args(["init", "mywork"])
        assert args.account_name == "mywork"

    def test_verify_command(self, cli):
        assert cli.parser.parse_args(["verify"]).command == "verify"

    def test_doctor_command(self, cli):
        assert cli.parser.parse_args(["doctor"]).command == "doctor"

    def test_update_no_flags(self, cli):
        args = cli.parser.parse_args(["update", "mywork"])
        assert args.account_name == "mywork"
        assert args.new_git_name is None
        assert args.new_email is None
        assert args.sign is None

    def test_update_sign_flag(self, cli):
        args = cli.parser.parse_args(["update", "mywork", "--sign"])
        assert args.sign is True

    def test_update_no_sign_flag(self, cli):
        args = cli.parser.parse_args(["update", "mywork", "--no-sign"])
        assert args.sign is False

    def test_update_sign_and_no_sign_mutually_exclusive(self, cli):
        with pytest.raises(SystemExit):
            cli.parser.parse_args(["update", "mywork", "--sign", "--no-sign"])

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

    def test_handle_add_passes_sign_flag(self, cli):
        cli.account_manager.add_account.return_value = True
        cli._handle_add(argparse.Namespace(key_type="rsa", sign=True))
        cli.account_manager.add_account.assert_called_once_with(
            key_type="rsa", sign=True
        )

    def test_handle_switch_success(self, cli):
        cli.account_manager.switch_account.return_value = True
        args = argparse.Namespace(account_name="work", local=False)
        assert cli._handle_switch(args) == 0

    def test_handle_switch_failure(self, cli):
        cli.account_manager.switch_account.return_value = False
        args = argparse.Namespace(account_name="work", local=False)
        assert cli._handle_switch(args) == 1

    def test_handle_switch_passes_local_flag(self, cli):
        cli.account_manager.switch_account.return_value = True
        args = argparse.Namespace(account_name="work", local=True)
        cli._handle_switch(args)
        cli.account_manager.switch_account.assert_called_once_with("work", local=True)

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

    def test_handle_status_matched(self, cli, capsys):
        cli.account_manager.get_status.return_value = {
            "name": "Work User",
            "email": "work@co.com",
            "matched_account": "work",
            "agent_running": True,
            "matched_key_account": "work",
        }
        result = cli._handle_status(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 0
        assert "Work User" in out
        assert "work@co.com" in out
        assert 'Matched account: "work"' in out
        assert 'SSH agent key matches account: "work"' in out

    def test_handle_status_no_match(self, cli, capsys):
        cli.account_manager.get_status.return_value = {
            "name": "Someone",
            "email": "someone@else.com",
            "matched_account": None,
            "agent_running": True,
            "matched_key_account": None,
        }
        result = cli._handle_status(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 0
        assert "No managed account matches" in out
        assert "does not match any managed account" in out

    def test_handle_status_no_identity_set(self, cli, capsys):
        cli.account_manager.get_status.return_value = {
            "name": None,
            "email": None,
            "matched_account": None,
            "agent_running": False,
            "matched_key_account": None,
        }
        result = cli._handle_status(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 0
        assert "(not set)" in out
        assert "SSH agent is not running." in out

    def test_handle_doctor_all_ok(self, cli, capsys):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": True,
            "accounts": {
                "work": {"exists": True, "readable": True, "permissions_ok": True}
            },
        }
        result = cli._handle_doctor(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 0
        assert "SSH agent is running and reachable" in out
        assert 'Account "work": key file OK' in out

    def test_handle_doctor_agent_not_running(self, cli, capsys):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": False,
            "accounts": {},
        }
        result = cli._handle_doctor(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 1
        assert "not running or not reachable" in out

    def test_handle_doctor_missing_key(self, cli, capsys):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": True,
            "accounts": {
                "work": {"exists": False, "readable": False, "permissions_ok": False}
            },
        }
        result = cli._handle_doctor(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 1
        assert 'Account "work": key file is missing' in out

    def test_handle_doctor_unreadable_key(self, cli, capsys):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": True,
            "accounts": {
                "work": {"exists": True, "readable": False, "permissions_ok": False}
            },
        }
        result = cli._handle_doctor(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 1
        assert 'Account "work": key file is unreadable' in out

    def test_handle_doctor_bad_permissions(self, cli, capsys):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": True,
            "accounts": {
                "work": {"exists": True, "readable": True, "permissions_ok": False}
            },
        }
        result = cli._handle_doctor(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 1
        assert "permissions are too permissive" in out

    def test_handle_doctor_no_accounts(self, cli, capsys):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": True,
            "accounts": {},
        }
        result = cli._handle_doctor(argparse.Namespace())
        out = capsys.readouterr().out
        assert result == 0
        assert "No accounts registered yet." in out

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

    def test_handle_update_passes_sign_flag(self, cli):
        cli.account_manager.update_account.return_value = True
        args = argparse.Namespace(
            account_name="work", new_git_name=None, new_email=None, sign=True
        )
        cli._handle_update(args)
        cli.account_manager.update_account.assert_called_once_with(
            "work", None, None, new_sign=True
        )


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

    def test_status_command_runs(self, cli):
        cli.account_manager.get_status.return_value = {
            "name": None,
            "email": None,
            "matched_account": None,
            "agent_running": False,
            "matched_key_account": None,
        }
        with patch.object(sys, "argv", ["gitacc", "status"]):
            result = cli.run()
        assert result == 0

    def test_doctor_command_runs(self, cli):
        cli.account_manager.run_doctor.return_value = {
            "agent_running": True,
            "accounts": {},
        }
        with patch.object(sys, "argv", ["gitacc", "doctor"]):
            result = cli.run()
        assert result == 0


# ---------------------------------------------------------------------------
# `rule` command parsing
# ---------------------------------------------------------------------------


class TestRuleParserCommands:
    def test_rule_add_parses_account_and_directory(self, cli):
        args = cli.parser.parse_args(["rule", "add", "work", "/tmp/work"])
        assert args.command == "rule"
        assert args.rule_command == "add"
        assert args.account_name == "work"
        assert args.directory == "/tmp/work"

    def test_rule_add_directory_defaults_to_none(self, cli):
        args = cli.parser.parse_args(["rule", "add", "work"])
        assert args.directory is None

    def test_rule_remove_parses_directory(self, cli):
        args = cli.parser.parse_args(["rule", "remove", "/tmp/work"])
        assert args.directory == "/tmp/work"

    def test_rule_remove_directory_defaults_to_none(self, cli):
        args = cli.parser.parse_args(["rule", "remove"])
        assert args.directory is None

    def test_rule_list_command(self, cli):
        args = cli.parser.parse_args(["rule", "list"])
        assert args.rule_command == "list"

    def test_rule_hook_parses_shell(self, cli):
        args = cli.parser.parse_args(["rule", "hook", "zsh"])
        assert args.shell == "zsh"

    def test_rule_hook_rejects_unsupported_shell(self, cli):
        with pytest.raises(SystemExit):
            cli.parser.parse_args(["rule", "hook", "fish"])

    def test_rule_check_command(self, cli):
        args = cli.parser.parse_args(["rule", "check"])
        assert args.rule_command == "check"


# ---------------------------------------------------------------------------
# `rule` command handlers
# ---------------------------------------------------------------------------


class TestRuleHandlers:
    def test_handle_rule_add_success(self, cli):
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.rules_manager.add_rule.return_value = True
        args = argparse.Namespace(account_name="work", directory="/tmp/work")
        assert cli._handle_rule_add(args) == 0

    def test_handle_rule_add_unknown_account(self, cli):
        cli.account_manager.account_exists.return_value = False
        args = argparse.Namespace(account_name="ghost", directory=None)
        assert cli._handle_rule_add(args) == 1
        cli.account_manager.rules_manager.add_rule.assert_not_called()

    def test_handle_rule_add_failure(self, cli):
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.rules_manager.add_rule.return_value = False
        args = argparse.Namespace(account_name="work", directory="/tmp/work")
        assert cli._handle_rule_add(args) == 1

    def test_handle_rule_remove_success(self, cli):
        cli.account_manager.rules_manager.remove_rule.return_value = True
        args = argparse.Namespace(directory="/tmp/work")
        assert cli._handle_rule_remove(args) == 0

    def test_handle_rule_remove_no_rule(self, cli):
        cli.account_manager.rules_manager.remove_rule.return_value = False
        args = argparse.Namespace(directory="/tmp/work")
        assert cli._handle_rule_remove(args) == 1

    def test_handle_rule_list_empty(self, cli):
        cli.account_manager.rules_manager.list_rules.return_value = {}
        assert cli._handle_rule_list(argparse.Namespace()) == 0

    def test_handle_rule_list_with_rules(self, cli, capsys):
        cli.account_manager.rules_manager.list_rules.return_value = {
            "/home/jane/work": "work"
        }
        result = cli._handle_rule_list(argparse.Namespace())
        assert result == 0
        assert "/home/jane/work" in capsys.readouterr().out

    def test_handle_rule_hook_prints_script(self, cli, capsys):
        result = cli._handle_rule_hook(argparse.Namespace(shell="bash"))
        assert result == 0
        assert "gitacc rule check" in capsys.readouterr().out

    def test_handle_rule_hook_unsupported_shell(self, cli):
        assert cli._handle_rule_hook(argparse.Namespace(shell="fish")) == 1

    def test_handle_rule_check_no_match_is_noop(self, cli):
        cli.account_manager.rules_manager.find_matching_account.return_value = None
        assert cli._handle_rule_check(argparse.Namespace()) == 0
        cli.account_manager.switch_account.assert_not_called()

    def test_handle_rule_check_unknown_account_is_noop(self, cli):
        cli.account_manager.rules_manager.find_matching_account.return_value = "ghost"
        cli.account_manager.account_exists.return_value = False
        assert cli._handle_rule_check(argparse.Namespace()) == 0
        cli.account_manager.switch_account.assert_not_called()

    def test_handle_rule_check_already_matching_is_noop(self, cli):
        cli.account_manager.rules_manager.find_matching_account.return_value = "work"
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.get_status.return_value = {"matched_account": "work"}
        assert cli._handle_rule_check(argparse.Namespace()) == 0
        cli.account_manager.switch_account.assert_not_called()

    def test_handle_rule_check_agent_down_is_noop(self, cli):
        cli.account_manager.rules_manager.find_matching_account.return_value = "work"
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.get_status.return_value = {"matched_account": "personal"}
        cli.account_manager.ssh_manager.is_ssh_agent_running.return_value = False
        assert cli._handle_rule_check(argparse.Namespace()) == 0
        cli.account_manager.switch_account.assert_not_called()

    def test_handle_rule_check_switches_when_mismatched(self, cli):
        cli.account_manager.rules_manager.find_matching_account.return_value = "work"
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.get_status.return_value = {"matched_account": "personal"}
        cli.account_manager.ssh_manager.is_ssh_agent_running.return_value = True
        cli.account_manager.switch_account.return_value = True
        assert cli._handle_rule_check(argparse.Namespace()) == 0
        cli.account_manager.switch_account.assert_called_once_with("work")

    def test_handle_rule_check_switch_failure(self, cli):
        cli.account_manager.rules_manager.find_matching_account.return_value = "work"
        cli.account_manager.account_exists.return_value = True
        cli.account_manager.get_status.return_value = {"matched_account": "personal"}
        cli.account_manager.ssh_manager.is_ssh_agent_running.return_value = True
        cli.account_manager.switch_account.return_value = False
        assert cli._handle_rule_check(argparse.Namespace()) == 1
