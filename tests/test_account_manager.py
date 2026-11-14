"""Tests for AccountManager — orchestration of account operations."""

import json
import pytest
from unittest.mock import patch, MagicMock
from gitacc_switcher.account_manager import AccountManager
from gitacc_switcher.config_manager import ConfigManager
from gitacc_switcher.ssh_manager import SSHManager


@pytest.fixture
def manager():
    with patch("gitacc_switcher.account_manager.ConfigManager"), patch(
        "gitacc_switcher.account_manager.SSHManager"
    ), patch("gitacc_switcher.account_manager.HookManager"):
        m = AccountManager()
    return m


WORK_ACCOUNT = {
    "name": "Work User",
    "email": "work@company.com",
    "private_key": "/home/user/.ssh/id_rsa_work",
    "public_key": "/home/user/.ssh/id_rsa_work.pub",
}


class TestAccountExists:
    def test_returns_true_for_existing(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        assert manager.account_exists("work") is True

    def test_returns_false_for_missing(self, manager):
        manager.config_manager.get_account.return_value = None
        assert manager.account_exists("nobody") is False


class TestListAccounts:
    def test_list_names(self, manager):
        manager.config_manager.list_account_names.return_value = ["work", "personal"]
        assert manager.list_accounts() == ["work", "personal"]

    def test_list_detailed(self, manager):
        data = {"work": WORK_ACCOUNT}
        manager.config_manager.read_accounts.return_value = data
        assert manager.list_accounts_detailed() == data

    def test_list_empty(self, manager):
        manager.config_manager.list_account_names.return_value = []
        assert manager.list_accounts() == []


class TestSwitchAccount:
    def test_fails_when_account_not_found(self, manager):
        manager.config_manager.get_account.return_value = None
        assert manager.switch_account("nobody") is False

    def test_fails_when_no_ssh_agent(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.ssh_manager.is_ssh_agent_running.return_value = False
        assert manager.switch_account("work") is False

    def test_fails_when_key_file_missing(self, manager, tmp_path):
        account = {**WORK_ACCOUNT, "private_key": str(tmp_path / "nonexistent")}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        assert manager.switch_account("work") is False

    def test_fails_when_add_key_fails(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key)}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (False, "bad key")
        assert manager.switch_account("work") is False

    def test_success(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key)}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 key\n")
            result = manager.switch_account("work")
        assert result is True
        manager.config_manager.set_git_config.assert_called_once_with(
            "Work User", "work@company.com"
        )

    def test_unsigned_account_unsets_signing_config(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key), "sign": "false"}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 key\n")
            result = manager.switch_account("work")
        assert result is True
        manager.config_manager.unset_git_signing_config.assert_called_once()
        manager.config_manager.set_git_signing_config.assert_not_called()

    def test_signed_account_sets_signing_config(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key), "sign": "true"}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 key\n")
            result = manager.switch_account("work")
        assert result is True
        manager.config_manager.set_git_signing_config.assert_called_once_with(
            "/home/user/.ssh/id_rsa_work.pub"
        )
        manager.config_manager.unset_git_signing_config.assert_not_called()

    def test_signed_account_local_sets_local_signing_config(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key), "sign": "true"}
        manager.config_manager.get_account.return_value = account
        manager.config_manager.is_git_repo.return_value = True
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config_local.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 key\n")
            result = manager.switch_account("work", local=True)
        assert result is True
        manager.config_manager.set_git_signing_config_local.assert_called_once_with(
            "/home/user/.ssh/id_rsa_work.pub"
        )
        manager.config_manager.set_git_signing_config.assert_not_called()

    def test_clears_all_keys_before_adding(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key)}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            manager.switch_account("work")
        manager.ssh_manager.clear_all_keys.assert_called_once()

    def test_local_fails_when_not_a_git_repo(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.config_manager.is_git_repo.return_value = False
        assert manager.switch_account("work", local=True) is False
        manager.config_manager.set_git_config_local.assert_not_called()

    def test_local_sets_local_git_config(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key)}
        manager.config_manager.get_account.return_value = account
        manager.config_manager.is_git_repo.return_value = True
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config_local.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 key\n")
            result = manager.switch_account("work", local=True)
        assert result is True
        manager.config_manager.set_git_config_local.assert_called_once_with(
            "Work User", "work@company.com"
        )
        manager.config_manager.set_git_config.assert_not_called()

    def test_global_switch_does_not_check_git_repo(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("key")
        account = {**WORK_ACCOUNT, "private_key": str(key)}
        manager.config_manager.get_account.return_value = account
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.clear_all_keys.return_value = True
        manager.ssh_manager.add_key_to_agent.return_value = (True, None)
        manager.config_manager.set_git_config.return_value = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1 key\n")
            manager.switch_account("work")
        manager.config_manager.is_git_repo.assert_not_called()


class TestLogout:
    def test_kills_agent_when_running(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        assert manager.logout() is True
        manager.ssh_manager.kill_ssh_agent.assert_called_once()

    def test_skips_kill_when_no_agent(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = False
        assert manager.logout() is True
        manager.ssh_manager.kill_ssh_agent.assert_not_called()

    def test_unsets_git_config(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = False
        manager.logout()
        manager.config_manager.unset_git_config.assert_called_once()

    def test_unsets_signing_config(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = False
        manager.logout()
        manager.config_manager.unset_git_signing_config.assert_called_once()


class TestUpdateAccount:
    def test_update_name(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Old Name",
            "email": "work@co.com",
        }
        manager.config_manager.update_account_field.return_value = True
        assert (
            manager.update_account(
                "work", new_git_name="New Name", new_email="work@co.com"
            )
            is True
        )
        manager.config_manager.update_account_field.assert_called_once_with(
            "work", "name", "New Name"
        )

    def test_update_email(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Work User",
            "email": "old@co.com",
        }
        manager.config_manager.update_account_field.return_value = True
        assert (
            manager.update_account(
                "work", new_git_name="Work User", new_email="new@co.com"
            )
            is True
        )
        manager.config_manager.update_account_field.assert_called_once_with(
            "work", "email", "new@co.com"
        )

    def test_update_both_fields(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Old Name",
            "email": "old@co.com",
        }
        manager.config_manager.update_account_field.return_value = True
        manager.update_account("work", new_git_name="New Name", new_email="new@co.com")
        assert manager.config_manager.update_account_field.call_count == 2

    def test_no_changes_does_not_write(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Work User",
            "email": "work@co.com",
        }
        manager.update_account(
            "work", new_git_name="Work User", new_email="work@co.com"
        )
        manager.config_manager.update_account_field.assert_not_called()

    def test_returns_false_for_missing_account(self, manager):
        manager.config_manager.get_account.return_value = None
        assert manager.update_account("nobody", "name", "email") is False

    def test_enables_signing(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Work User",
            "email": "work@co.com",
            "sign": "false",
        }
        manager.config_manager.update_account_field.return_value = True
        result = manager.update_account(
            "work", new_git_name="Work User", new_email="work@co.com", new_sign=True
        )
        assert result is True
        manager.config_manager.update_account_field.assert_called_once_with(
            "work", "sign", "true"
        )

    def test_disables_signing(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Work User",
            "email": "work@co.com",
            "sign": "true",
        }
        manager.config_manager.update_account_field.return_value = True
        result = manager.update_account(
            "work", new_git_name="Work User", new_email="work@co.com", new_sign=False
        )
        assert result is True
        manager.config_manager.update_account_field.assert_called_once_with(
            "work", "sign", "false"
        )

    def test_no_sign_change_does_not_write(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Work User",
            "email": "work@co.com",
            "sign": "true",
        }
        manager.update_account(
            "work", new_git_name="Work User", new_email="work@co.com", new_sign=True
        )
        manager.config_manager.update_account_field.assert_not_called()

    def test_sign_none_leaves_setting_unchanged(self, manager):
        manager.config_manager.get_account.return_value = {
            "name": "Work User",
            "email": "work@co.com",
            "sign": "true",
        }
        manager.update_account(
            "work", new_git_name="Work User", new_email="work@co.com", new_sign=None
        )
        manager.config_manager.update_account_field.assert_not_called()


class TestRemoveAccount:
    def test_returns_false_for_missing_account(self, manager):
        manager.config_manager.get_account.return_value = None
        assert manager.remove_account("nobody") is False

    def test_cancellation_prevents_removal(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        with patch("builtins.input", return_value="n"):
            assert manager.remove_account("work") is False
        manager.config_manager.remove_account.assert_not_called()

    def test_confirmation_removes_account(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.config_manager.remove_account.return_value = True
        with patch("builtins.input", return_value="y"):
            assert manager.remove_account("work") is True
        manager.config_manager.remove_account.assert_called_once_with("work")

    def test_deletes_ssh_keys_on_removal(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.config_manager.remove_account.return_value = True
        with patch("builtins.input", return_value="y"):
            manager.remove_account("work")
        manager.ssh_manager.delete_ssh_key.assert_called_once_with(
            "/home/user/.ssh/id_rsa_work",
            "/home/user/.ssh/id_rsa_work.pub",
        )


class TestAddAccount:
    def _setup_add(self, manager, tmp_path):
        """Configure mocks for a successful add_account call."""
        key = tmp_path / "id_rsa_test"
        key_pub = tmp_path / "id_rsa_test.pub"
        key.write_text("private")
        key_pub.write_text("ssh-rsa AAAA test@test.com")
        manager.config_manager.get_account.return_value = None
        manager.ssh_manager.generate_ssh_key.return_value = (str(key), str(key_pub))
        manager.ssh_manager.get_public_key_content.return_value = (
            "ssh-rsa AAAA test@test.com"
        )
        manager.config_manager.add_account.return_value = True

    def test_happy_path(self, manager, tmp_path):
        self._setup_add(manager, tmp_path)
        inputs = ["mywork", "My Work", "work@co.com"]
        with patch("builtins.input", side_effect=inputs), patch(
            "gitacc_switcher.account_manager.ask_yes_no", return_value=False
        ):
            result = manager.add_account()
        assert result is True
        manager.config_manager.add_account.assert_called_once()

    def test_empty_account_name_fails(self, manager):
        with patch("builtins.input", return_value=""):
            assert manager.add_account() is False

    def test_empty_email_fails(self, manager):
        with patch("builtins.input", side_effect=["mywork", "My Work", ""]):
            assert manager.add_account() is False

    def test_ssh_key_failure_fails(self, manager, tmp_path):
        manager.config_manager.get_account.return_value = None
        manager.ssh_manager.generate_ssh_key.return_value = (None, None)
        inputs = ["mywork", "My Work", "work@co.com"]
        with patch("builtins.input", side_effect=inputs), patch(
            "gitacc_switcher.account_manager.ask_yes_no", return_value=False
        ):
            assert manager.add_account() is False

    def test_passphrase_mismatch_fails(self, manager, tmp_path):
        manager.config_manager.get_account.return_value = None
        inputs = ["mywork", "", "work@co.com"]
        with patch("builtins.input", side_effect=inputs), patch(
            "gitacc_switcher.account_manager.ask_yes_no", return_value=True
        ), patch("getpass.getpass", side_effect=["pass1", "pass2"]):
            assert manager.add_account() is False

    def test_sign_flag_passed_to_config_manager(self, manager, tmp_path):
        self._setup_add(manager, tmp_path)
        inputs = ["mywork", "My Work", "work@co.com"]
        with patch("builtins.input", side_effect=inputs), patch(
            "gitacc_switcher.account_manager.ask_yes_no", return_value=False
        ):
            result = manager.add_account(sign=True)
        assert result is True
        _, kwargs = manager.config_manager.add_account.call_args
        assert kwargs["sign"] is True

    def test_sign_defaults_to_false(self, manager, tmp_path):
        self._setup_add(manager, tmp_path)
        inputs = ["mywork", "My Work", "work@co.com"]
        with patch("builtins.input", side_effect=inputs), patch(
            "gitacc_switcher.account_manager.ask_yes_no", return_value=False
        ):
            result = manager.add_account()
        assert result is True
        _, kwargs = manager.config_manager.add_account.call_args
        assert kwargs["sign"] is False


class TestGetStatus:
    def test_matches_account_by_identity(self, manager):
        manager.config_manager.is_git_repo.return_value = False
        manager.config_manager.get_current_git_config.return_value = {
            "name": "Work User",
            "email": "work@company.com",
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = False

        status = manager.get_status()

        assert status["name"] == "Work User"
        assert status["email"] == "work@company.com"
        assert status["matched_account"] == "work"
        assert status["agent_running"] is False
        assert status["matched_key_account"] is None

    def test_no_match_when_identity_unknown(self, manager):
        manager.config_manager.is_git_repo.return_value = False
        manager.config_manager.get_current_git_config.return_value = {
            "name": "Someone Else",
            "email": "someone@else.com",
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = False

        status = manager.get_status()

        assert status["matched_account"] is None

    def test_no_match_when_identity_unset(self, manager):
        manager.config_manager.is_git_repo.return_value = False
        manager.config_manager.get_current_git_config.return_value = {
            "name": None,
            "email": None,
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = False

        status = manager.get_status()

        assert status["matched_account"] is None

    def test_uses_local_git_config_inside_repo(self, manager):
        manager.config_manager.is_git_repo.return_value = True
        manager.config_manager.get_current_git_config_local.return_value = {
            "name": "Work User",
            "email": "work@company.com",
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = False

        status = manager.get_status()

        manager.config_manager.get_current_git_config_local.assert_called_once()
        manager.config_manager.get_current_git_config.assert_not_called()
        assert status["matched_account"] == "work"

    def test_matches_account_by_agent_key_fingerprint(self, manager):
        manager.config_manager.is_git_repo.return_value = False
        manager.config_manager.get_current_git_config.return_value = {
            "name": None,
            "email": None,
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.get_agent_fingerprints.return_value = ["SHA256:abc123"]
        manager.ssh_manager.get_key_fingerprint.return_value = "SHA256:abc123"

        status = manager.get_status()

        assert status["agent_running"] is True
        assert status["matched_key_account"] == "work"

    def test_no_key_match_when_fingerprints_differ(self, manager):
        manager.config_manager.is_git_repo.return_value = False
        manager.config_manager.get_current_git_config.return_value = {
            "name": None,
            "email": None,
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.ssh_manager.get_agent_fingerprints.return_value = ["SHA256:other"]
        manager.ssh_manager.get_key_fingerprint.return_value = "SHA256:abc123"

        status = manager.get_status()

        assert status["matched_key_account"] is None

    def test_no_key_lookup_when_agent_not_running(self, manager):
        manager.config_manager.is_git_repo.return_value = False
        manager.config_manager.get_current_git_config.return_value = {
            "name": None,
            "email": None,
        }
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.is_ssh_agent_running.return_value = False

        status = manager.get_status()

        manager.ssh_manager.get_agent_fingerprints.assert_not_called()
        assert status["matched_key_account"] is None


class TestRunDoctor:
    def test_agent_running_and_all_keys_ok(self, manager, tmp_path):
        key = tmp_path / "id_rsa_work"
        key.write_text("private")
        key.chmod(0o600)
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.config_manager.read_accounts.return_value = {
            "work": {**WORK_ACCOUNT, "private_key": str(key)}
        }
        manager.ssh_manager.check_key_file.return_value = {
            "exists": True,
            "readable": True,
            "permissions_ok": True,
        }

        report = manager.run_doctor()

        assert report["agent_running"] is True
        assert report["accounts"] == {
            "work": {"exists": True, "readable": True, "permissions_ok": True}
        }
        manager.ssh_manager.check_key_file.assert_called_once_with(str(key))

    def test_agent_not_running(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = False
        manager.config_manager.read_accounts.return_value = {}

        report = manager.run_doctor()

        assert report["agent_running"] is False
        assert report["accounts"] == {}

    def test_flags_account_with_no_private_key_recorded(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.config_manager.read_accounts.return_value = {
            "broken": {"name": "Broken", "email": "b@co.com"}
        }

        report = manager.run_doctor()

        assert report["accounts"] == {
            "broken": {"exists": False, "readable": False, "permissions_ok": False}
        }
        manager.ssh_manager.check_key_file.assert_not_called()

    def test_flags_missing_key_file(self, manager):
        manager.ssh_manager.is_ssh_agent_running.return_value = True
        manager.config_manager.read_accounts.return_value = {
            "work": {**WORK_ACCOUNT, "private_key": "/nonexistent/id_rsa_work"}
        }
        manager.ssh_manager.check_key_file.return_value = {
            "exists": False,
            "readable": False,
            "permissions_ok": False,
        }

        report = manager.run_doctor()

        assert report["accounts"]["work"]["exists"] is False


class TestAddHostAlias:
    def test_fails_when_account_not_found(self, manager):
        manager.config_manager.get_account.return_value = None
        assert manager.add_host_alias("nobody", "github-work") is False
        manager.ssh_manager.add_host_alias.assert_not_called()

    def test_fails_when_account_has_no_private_key(self, manager):
        manager.config_manager.get_account.return_value = {"email": "w@co.com"}
        assert manager.add_host_alias("work", "github-work") is False
        manager.ssh_manager.add_host_alias.assert_not_called()

    def test_success_uses_defaults(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.ssh_manager.add_host_alias.return_value = True

        assert manager.add_host_alias("work", "github-work") is True

        manager.ssh_manager.add_host_alias.assert_called_once_with(
            "github-work", "github.com", WORK_ACCOUNT["private_key"], "git"
        )

    def test_success_with_custom_hostname_and_user(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.ssh_manager.add_host_alias.return_value = True

        result = manager.add_host_alias(
            "work", "gitlab-work", hostname="gitlab.com", ssh_user="deploy"
        )

        assert result is True
        manager.ssh_manager.add_host_alias.assert_called_once_with(
            "gitlab-work", "gitlab.com", WORK_ACCOUNT["private_key"], "deploy"
        )

    def test_returns_false_when_ssh_manager_fails(self, manager):
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.ssh_manager.add_host_alias.return_value = False
        assert manager.add_host_alias("work", "github-work") is False


class TestRemoveHostAlias:
    def test_success(self, manager):
        manager.ssh_manager.remove_host_alias.return_value = True
        assert manager.remove_host_alias("github-work") is True

    def test_not_found(self, manager):
        manager.ssh_manager.remove_host_alias.return_value = False
        assert manager.remove_host_alias("nonexistent") is False


class TestListHostAliases:
    def test_delegates_to_ssh_manager(self, manager):
        data = {"github-work": {"hostname": "github.com"}}
        manager.ssh_manager.list_host_aliases.return_value = data
        assert manager.list_host_aliases() == data

    def test_empty(self, manager):
        manager.ssh_manager.list_host_aliases.return_value = {}
        assert manager.list_host_aliases() == {}


class TestExportAccounts:
    def test_fails_when_no_accounts(self, manager, tmp_path):
        manager.config_manager.read_accounts.return_value = {}
        assert manager.export_accounts(tmp_path / "out.json") is False

    def test_writes_metadata_only_by_default(self, manager, tmp_path):
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.list_host_aliases.return_value = {}
        output = tmp_path / "out.json"

        assert manager.export_accounts(output) is True

        data = json.loads(output.read_text())
        assert data["include_keys"] is False
        work = data["accounts"]["work"]
        assert work["name"] == "Work User"
        assert work["email"] == "work@company.com"
        assert work["private_key"] == WORK_ACCOUNT["private_key"]
        assert "private_key_content" not in work
        assert "public_key_content" not in work
        manager.ssh_manager.get_private_key_content.assert_not_called()

    def test_includes_key_content_when_opted_in(self, manager, tmp_path):
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.list_host_aliases.return_value = {}
        manager.ssh_manager.get_public_key_content.return_value = "ssh-rsa AAAA"
        manager.ssh_manager.get_private_key_content.return_value = "PRIVATE-DATA"
        output = tmp_path / "out.json"

        assert manager.export_accounts(output, include_keys=True) is True

        data = json.loads(output.read_text())
        work = data["accounts"]["work"]
        assert work["private_key_content"] == "PRIVATE-DATA"
        assert work["public_key_content"] == "ssh-rsa AAAA"
        assert (output.stat().st_mode & 0o777) == 0o600

    def test_includes_host_aliases_bound_to_account_key(self, manager, tmp_path):
        manager.config_manager.read_accounts.return_value = {"work": WORK_ACCOUNT}
        manager.ssh_manager.list_host_aliases.return_value = {
            "github-work": {
                "hostname": "github.com",
                "user": "git",
                "identity_file": WORK_ACCOUNT["private_key"],
            },
            "other-alias": {
                "hostname": "gitlab.com",
                "user": "git",
                "identity_file": "/home/user/.ssh/id_rsa_other",
            },
        }
        output = tmp_path / "out.json"

        assert manager.export_accounts(output) is True

        work = json.loads(output.read_text())["accounts"]["work"]
        assert work["host_aliases"] == {
            "github-work": {"hostname": "github.com", "user": "git"}
        }


class TestImportAccounts:
    def _write_export(self, tmp_path, accounts, include_keys=False):
        export_file = tmp_path / "export.json"
        export_file.write_text(
            json.dumps(
                {"version": 1, "include_keys": include_keys, "accounts": accounts}
            )
        )
        return export_file

    def test_fails_when_file_missing(self, manager, tmp_path):
        assert manager.import_accounts(tmp_path / "nope.json") is False

    def test_fails_when_no_accounts_in_file(self, manager, tmp_path):
        export_file = self._write_export(tmp_path, {})
        assert manager.import_accounts(export_file) is False

    def test_imports_new_account(self, manager, tmp_path):
        export_file = self._write_export(
            tmp_path,
            {
                "work": {
                    "name": "Work User",
                    "email": "work@company.com",
                    "sign": "false",
                    "private_key": "/home/user/.ssh/id_rsa_work",
                    "public_key": "/home/user/.ssh/id_rsa_work.pub",
                }
            },
        )
        manager.config_manager.get_account.return_value = None
        manager.config_manager.add_account.return_value = True

        assert manager.import_accounts(export_file) is True

        manager.config_manager.add_account.assert_called_once_with(
            "work",
            "Work User",
            "work@company.com",
            "/home/user/.ssh/id_rsa_work",
            "/home/user/.ssh/id_rsa_work.pub",
            sign=False,
        )
        manager.config_manager.remove_account.assert_not_called()

    def test_skips_existing_account_without_force(self, manager, tmp_path):
        export_file = self._write_export(
            tmp_path,
            {
                "work": {
                    "name": "Work User",
                    "email": "work@company.com",
                    "private_key": "/home/user/.ssh/id_rsa_work",
                    "public_key": "/home/user/.ssh/id_rsa_work.pub",
                }
            },
        )
        manager.config_manager.get_account.return_value = WORK_ACCOUNT

        assert manager.import_accounts(export_file) is True

        manager.config_manager.add_account.assert_not_called()

    def test_force_overwrites_existing_account(self, manager, tmp_path):
        export_file = self._write_export(
            tmp_path,
            {
                "work": {
                    "name": "New Name",
                    "email": "work@company.com",
                    "private_key": "/home/user/.ssh/id_rsa_work",
                    "public_key": "/home/user/.ssh/id_rsa_work.pub",
                }
            },
        )
        manager.config_manager.get_account.return_value = WORK_ACCOUNT
        manager.config_manager.add_account.return_value = True

        assert manager.import_accounts(export_file, force=True) is True

        manager.config_manager.remove_account.assert_called_once_with("work")
        manager.config_manager.add_account.assert_called_once()

    def test_writes_key_material_when_present(self, manager, tmp_path):
        private_key = tmp_path / "id_rsa_work"
        public_key = tmp_path / "id_rsa_work.pub"
        export_file = self._write_export(
            tmp_path,
            {
                "work": {
                    "name": "Work User",
                    "email": "work@company.com",
                    "private_key": str(private_key),
                    "public_key": str(public_key),
                    "private_key_content": "PRIVATE-DATA",
                    "public_key_content": "ssh-rsa AAAA",
                }
            },
            include_keys=True,
        )
        manager.config_manager.get_account.return_value = None
        manager.config_manager.add_account.return_value = True

        assert manager.import_accounts(export_file) is True

        assert private_key.read_text() == "PRIVATE-DATA"
        assert public_key.read_text() == "ssh-rsa AAAA"
        assert (private_key.stat().st_mode & 0o777) == 0o600

    def test_does_not_overwrite_existing_key_file_without_force(
        self, manager, tmp_path
    ):
        private_key = tmp_path / "id_rsa_work"
        private_key.write_text("ORIGINAL")
        export_file = self._write_export(
            tmp_path,
            {
                "work": {
                    "name": "Work User",
                    "email": "work@company.com",
                    "private_key": str(private_key),
                    "public_key": str(tmp_path / "id_rsa_work.pub"),
                    "private_key_content": "IMPORTED-DATA",
                }
            },
            include_keys=True,
        )
        manager.config_manager.get_account.return_value = None
        manager.config_manager.add_account.return_value = True

        manager.import_accounts(export_file)

        assert private_key.read_text() == "ORIGINAL"

    def test_imports_host_aliases(self, manager, tmp_path):
        export_file = self._write_export(
            tmp_path,
            {
                "work": {
                    "name": "Work User",
                    "email": "work@company.com",
                    "private_key": "/home/user/.ssh/id_rsa_work",
                    "public_key": "/home/user/.ssh/id_rsa_work.pub",
                    "host_aliases": {
                        "github-work": {"hostname": "github.com", "user": "git"}
                    },
                }
            },
        )
        manager.config_manager.get_account.return_value = None
        manager.config_manager.add_account.return_value = True
        manager.ssh_manager.has_host_alias.return_value = False

        manager.import_accounts(export_file)

        manager.ssh_manager.add_host_alias.assert_called_once_with(
            "github-work",
            "github.com",
            "/home/user/.ssh/id_rsa_work",
            "git",
        )


class TestExportImportRoundTrip:
    """Round-trips a real (unmocked) config through export then import."""

    def _real_manager(self, tmp_path, label):
        config = ConfigManager.__new__(ConfigManager)
        config.gitacc_file = tmp_path / f"{label}.gitacc"
        config._ensure_gitacc_file()

        ssh = SSHManager.__new__(SSHManager)
        ssh.ssh_dir = tmp_path / f"{label}-ssh"
        ssh.ssh_dir.mkdir(mode=0o700)

        mgr = AccountManager.__new__(AccountManager)
        mgr.config_manager = config
        mgr.ssh_manager = ssh
        return mgr

    def test_round_trip_metadata_only(self, tmp_path):
        source = self._real_manager(tmp_path, "source")
        key = source.ssh_manager.ssh_dir / "id_rsa_work"
        key.write_text("PRIVATE")
        pub = source.ssh_manager.ssh_dir / "id_rsa_work.pub"
        pub.write_text("PUBLIC")
        assert source.config_manager.add_account(
            "work", "Work User", "work@company.com", str(key), str(pub), sign=False
        )

        export_file = tmp_path / "export.json"
        assert source.export_accounts(export_file) is True

        target = self._real_manager(tmp_path, "target")
        assert target.import_accounts(export_file) is True

        imported = target.config_manager.read_accounts()
        assert imported["work"]["name"] == "Work User"
        assert imported["work"]["email"] == "work@company.com"
        assert imported["work"]["private_key"] == str(key)
        # Metadata-only: no key material was embedded, so nothing is written
        # to disk at the target other than the .gitacc entry itself.
        assert not (target.ssh_manager.ssh_dir / "id_rsa_work").exists()

    def test_round_trip_with_keys_restores_key_files(self, tmp_path):
        source = self._real_manager(tmp_path, "shared")
        key = source.ssh_manager.ssh_dir / "id_rsa_work"
        key.write_text("PRIVATE-CONTENT")
        pub = source.ssh_manager.ssh_dir / "id_rsa_work.pub"
        pub.write_text("PUBLIC-CONTENT")
        assert source.config_manager.add_account(
            "work", "Work User", "work@company.com", str(key), str(pub), sign=False
        )

        export_file = tmp_path / "export.json"
        assert source.export_accounts(export_file, include_keys=True) is True

        # Simulate a fresh machine: a separate .gitacc, and the key files
        # for this account are gone (never existed there).
        key.unlink()
        pub.unlink()
        target = AccountManager.__new__(AccountManager)
        target_config = ConfigManager.__new__(ConfigManager)
        target_config.gitacc_file = tmp_path / "fresh.gitacc"
        target_config._ensure_gitacc_file()
        target.config_manager = target_config
        target.ssh_manager = source.ssh_manager  # same ~/.ssh path on "this machine"

        assert target.import_accounts(export_file) is True

        assert key.read_text() == "PRIVATE-CONTENT"
        assert pub.read_text() == "PUBLIC-CONTENT"
        assert (key.stat().st_mode & 0o777) == 0o600
        imported = target_config.read_accounts()
        assert imported["work"]["private_key"] == str(key)
