"""Tests for ConfigManager — .gitacc file parsing and git config operations."""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from gitacc_switcher.config_manager import ConfigManager

SAMPLE_GITACC = (
    "[work]\n"
    "\tname = Work User\n"
    "\temail = work@company.com\n"
    "\tprivate_key = /home/user/.ssh/id_rsa_work\n"
    "\tpublic_key = /home/user/.ssh/id_rsa_work.pub\n"
    "[personal]\n"
    "\tname = Personal User\n"
    "\temail = personal@gmail.com\n"
    "\tprivate_key = /home/user/.ssh/id_ed25519_personal\n"
    "\tpublic_key = /home/user/.ssh/id_ed25519_personal.pub\n"
)


@pytest.fixture
def config(tmp_path):
    obj = ConfigManager.__new__(ConfigManager)
    obj.gitacc_file = tmp_path / ".gitacc"
    obj._ensure_gitacc_file()
    return obj


@pytest.fixture
def config_with_accounts(config):
    config.gitacc_file.write_text(SAMPLE_GITACC)
    return config


class TestEnsureGitaccFile:
    def test_creates_file_if_missing(self, tmp_path):
        obj = ConfigManager.__new__(ConfigManager)
        obj.gitacc_file = tmp_path / ".gitacc"
        assert not obj.gitacc_file.exists()
        obj._ensure_gitacc_file()
        assert obj.gitacc_file.exists()

    def test_does_not_overwrite_existing(self, config):
        config.gitacc_file.write_text("[existing]\n")
        config._ensure_gitacc_file()
        assert "[existing]" in config.gitacc_file.read_text()


class TestReadAccounts:
    def test_empty_file(self, config):
        assert config.read_accounts() == {}

    def test_parses_single_account(self, config):
        config.gitacc_file.write_text(
            "[work]\n\tname = Work User\n\temail = work@co.com\n"
            "\tprivate_key = /k\n\tpublic_key = /k.pub\n"
        )
        accounts = config.read_accounts()
        assert "work" in accounts
        assert accounts["work"]["name"] == "Work User"
        assert accounts["work"]["email"] == "work@co.com"

    def test_parses_multiple_accounts(self, config_with_accounts):
        accounts = config_with_accounts.read_accounts()
        assert len(accounts) == 2
        assert "work" in accounts
        assert "personal" in accounts

    def test_accounts_not_cross_contaminated(self, config_with_accounts):
        accounts = config_with_accounts.read_accounts()
        assert accounts["work"]["email"] == "work@company.com"
        assert accounts["personal"]["email"] == "personal@gmail.com"

    def test_parses_all_fields(self, config_with_accounts):
        account = config_with_accounts.read_accounts()["work"]
        assert account["private_key"] == "/home/user/.ssh/id_rsa_work"
        assert account["public_key"] == "/home/user/.ssh/id_rsa_work.pub"


class TestGetAccount:
    def test_returns_existing_account(self, config_with_accounts):
        account = config_with_accounts.get_account("work")
        assert account is not None
        assert account["email"] == "work@company.com"

    def test_returns_none_for_missing(self, config_with_accounts):
        assert config_with_accounts.get_account("nobody") is None


class TestAddAccount:
    def test_adds_account(self, config):
        result = config.add_account("test", "Test User", "t@t.com", "/k", "/k.pub")
        assert result is True
        assert config.get_account("test") is not None

    def test_persists_all_fields(self, config):
        config.add_account(
            "work", "Work User", "work@co.com", "/path/key", "/path/key.pub"
        )
        account = config.get_account("work")
        assert account["name"] == "Work User"
        assert account["email"] == "work@co.com"
        assert account["private_key"] == "/path/key"
        assert account["public_key"] == "/path/key.pub"

    def test_multiple_accounts_coexist(self, config):
        config.add_account("work", "Work", "w@co.com", "/k1", "/k1.pub")
        config.add_account("personal", "Personal", "p@p.com", "/k2", "/k2.pub")
        assert len(config.read_accounts()) == 2

    def test_defaults_sign_to_false(self, config):
        config.add_account("test", "Test User", "t@t.com", "/k", "/k.pub")
        assert config.get_account("test")["sign"] == "false"

    def test_persists_sign_true_when_enabled(self, config):
        config.add_account("test", "Test User", "t@t.com", "/k", "/k.pub", sign=True)
        assert config.get_account("test")["sign"] == "true"


class TestRemoveAccount:
    def test_removes_account(self, config_with_accounts):
        assert config_with_accounts.remove_account("work") is True
        assert config_with_accounts.get_account("work") is None

    def test_preserves_other_accounts(self, config_with_accounts):
        config_with_accounts.remove_account("work")
        assert config_with_accounts.get_account("personal") is not None

    def test_returns_false_for_missing(self, config_with_accounts):
        assert config_with_accounts.remove_account("nobody") is False

    def test_removes_last_account(self, config_with_accounts):
        config_with_accounts.remove_account("work")
        config_with_accounts.remove_account("personal")
        assert config_with_accounts.read_accounts() == {}


class TestUpdateAccountField:
    def test_updates_name(self, config_with_accounts):
        assert (
            config_with_accounts.update_account_field("work", "name", "New Name")
            is True
        )
        assert config_with_accounts.get_account("work")["name"] == "New Name"

    def test_updates_email(self, config_with_accounts):
        assert (
            config_with_accounts.update_account_field("work", "email", "new@co.com")
            is True
        )
        assert config_with_accounts.get_account("work")["email"] == "new@co.com"

    def test_other_fields_unchanged_after_update(self, config_with_accounts):
        config_with_accounts.update_account_field("work", "name", "New Name")
        account = config_with_accounts.get_account("work")
        assert account["email"] == "work@company.com"
        assert account["private_key"] == "/home/user/.ssh/id_rsa_work"

    def test_other_account_unchanged(self, config_with_accounts):
        config_with_accounts.update_account_field("work", "name", "New Name")
        assert config_with_accounts.get_account("personal")["name"] == "Personal User"

    def test_returns_false_for_missing_account(self, config_with_accounts):
        assert config_with_accounts.update_account_field("nobody", "name", "X") is False

    def test_appends_field_missing_from_section(self, config_with_accounts):
        # SAMPLE_GITACC accounts have no "sign" field — this reproduces a pre-1.2.0
        # account whose section was written before that field existed.
        assert "sign" not in config_with_accounts.get_account("work")
        assert config_with_accounts.update_account_field("work", "sign", "true") is True
        assert config_with_accounts.get_account("work")["sign"] == "true"

    def test_appending_missing_field_preserves_other_fields(self, config_with_accounts):
        config_with_accounts.update_account_field("work", "sign", "true")
        account = config_with_accounts.get_account("work")
        assert account["name"] == "Work User"
        assert account["email"] == "work@company.com"
        assert account["private_key"] == "/home/user/.ssh/id_rsa_work"
        assert account["public_key"] == "/home/user/.ssh/id_rsa_work.pub"

    def test_appending_missing_field_does_not_affect_other_account(
        self, config_with_accounts
    ):
        config_with_accounts.update_account_field("work", "sign", "true")
        assert "sign" not in config_with_accounts.get_account("personal")


class TestListAccountNames:
    def test_empty(self, config):
        assert config.list_account_names() == []

    def test_returns_all_names(self, config_with_accounts):
        names = config_with_accounts.list_account_names()
        assert set(names) == {"work", "personal"}


class TestSetGitConfig:
    def test_calls_git_config(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = config.set_git_config("Test User", "test@test.com")
        assert result is True
        assert mock_run.call_count == 2

    def test_returns_false_on_error(self, config):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            assert config.set_git_config("Test", "test@test.com") is False


class TestSetGitConfigLocal:
    def test_calls_git_config_without_global_flag(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = config.set_git_config_local("Test User", "test@test.com")
        assert result is True
        assert mock_run.call_count == 2
        for call in mock_run.call_args_list:
            assert "--global" not in call.args[0]

    def test_passes_repo_path_as_cwd(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            config.set_git_config_local("Test User", "test@test.com", tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs["cwd"] == tmp_path

    def test_returns_false_on_error(self, config):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            assert config.set_git_config_local("Test", "test@test.com") is False


class TestSetGitSigningConfig:
    def test_sets_signingkey_format_and_gpgsign(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = config.set_git_signing_config("/home/user/.ssh/id_rsa.pub")
        assert result is True
        assert mock_run.call_count == 3
        calls = [call.args[0] for call in mock_run.call_args_list]
        assert [
            "git",
            "config",
            "--global",
            "user.signingkey",
            "/home/user/.ssh/id_rsa.pub",
        ] in calls
        assert ["git", "config", "--global", "gpg.format", "ssh"] in calls
        assert ["git", "config", "--global", "commit.gpgsign", "true"] in calls

    def test_returns_false_on_error(self, config):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            assert config.set_git_signing_config("/k.pub") is False


class TestUnsetGitSigningConfig:
    def test_unsets_all_signing_keys(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = config.unset_git_signing_config()
        assert result is True
        assert mock_run.call_count == 3
        calls = [call.args[0] for call in mock_run.call_args_list]
        assert ["git", "config", "--global", "--unset", "user.signingkey"] in calls
        assert ["git", "config", "--global", "--unset", "gpg.format"] in calls
        assert ["git", "config", "--global", "--unset", "commit.gpgsign"] in calls

    def test_succeeds_even_when_key_was_unset(self, config):
        # git config --unset on a missing key returns non-zero, but we don't
        # pass check=True for unset, so this should not raise/fail.
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=5)
            assert config.unset_git_signing_config() is True


class TestSetGitSigningConfigLocal:
    def test_calls_git_config_without_global_flag(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = config.set_git_signing_config_local("/k.pub")
        assert result is True
        for call in mock_run.call_args_list:
            assert "--global" not in call.args[0]

    def test_passes_repo_path_as_cwd(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            config.set_git_signing_config_local("/k.pub", tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs["cwd"] == tmp_path

    def test_returns_false_on_error(self, config):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            assert config.set_git_signing_config_local("/k.pub") is False


class TestUnsetGitSigningConfigLocal:
    def test_calls_git_config_without_global_flag(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = config.unset_git_signing_config_local()
        assert result is True
        for call in mock_run.call_args_list:
            assert "--global" not in call.args[0]

    def test_passes_repo_path_as_cwd(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            config.unset_git_signing_config_local(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs["cwd"] == tmp_path


class TestGetCurrentGitConfig:
    def test_returns_name_and_email_keys(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Test User\n")
            result = config.get_current_git_config()
        assert "name" in result
        assert "email" in result

    def test_returns_none_when_not_set(self, config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = config.get_current_git_config()
        assert result["name"] is None
        assert result["email"] is None


class TestIsGitRepo:
    def test_returns_true_for_git_repo(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert config.is_git_repo(tmp_path) is True

    def test_returns_false_for_non_repo(self, config, tmp_path):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(128, "git")
        ):
            assert config.is_git_repo(tmp_path) is False


class TestRepoExpectedAccount:
    def test_set_and_get_expected_account(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="work\n")
            result = config.get_repo_expected_account(tmp_path)
        assert result == "work"

    def test_returns_none_when_not_set(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = config.get_repo_expected_account(tmp_path)
        assert result is None

    def test_set_expected_account(self, config, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # First call for is_git_repo check, second for set
            result = config.set_repo_expected_account("work", tmp_path)
        assert result is True
