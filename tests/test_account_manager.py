"""Tests for AccountManager — orchestration of account operations."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from gitacc_switcher.account_manager import AccountManager


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
