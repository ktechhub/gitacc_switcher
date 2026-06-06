"""Tests for SSHManager — SSH key generation and agent operations."""

import os
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from gitacc_switcher.ssh_manager import SSHManager


@pytest.fixture
def ssh(tmp_path):
    obj = SSHManager.__new__(SSHManager)
    obj.ssh_dir = tmp_path / ".ssh"
    obj.ssh_dir.mkdir(mode=0o700)
    return obj


class TestIsSSHAgentRunning:
    def test_no_socket_env_var(self, ssh):
        with patch.dict(os.environ, {}, clear=True):
            assert ssh.is_ssh_agent_running() is False

    def test_socket_set_but_agent_dead(self, ssh):
        with patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/fake.sock"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=2)
                assert ssh.is_ssh_agent_running() is False

    def test_agent_running_with_keys(self, ssh):
        with patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh.sock"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                assert ssh.is_ssh_agent_running() is True

    def test_agent_running_no_keys_loaded(self, ssh):
        # returncode=1 means agent is up but has no keys
        with patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh.sock"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                assert ssh.is_ssh_agent_running() is True


class TestGenerateSSHKey:
    def test_returns_key_paths(self, ssh):
        with patch("subprocess.run"):
            private, public = ssh.generate_ssh_key("rsa", "test", "t@t.com")
        assert private is not None
        assert public is not None
        assert "test" in private
        assert public.endswith(".pub")

    def test_returns_none_if_private_key_exists(self, ssh):
        (ssh.ssh_dir / "id_rsa_test").write_text("exists")
        private, public = ssh.generate_ssh_key("rsa", "test", "t@t.com")
        assert private is None
        assert public is None

    def test_returns_none_if_public_key_exists(self, ssh):
        (ssh.ssh_dir / "id_rsa_test.pub").write_text("exists")
        private, public = ssh.generate_ssh_key("rsa", "test", "t@t.com")
        assert private is None
        assert public is None

    def test_generates_with_passphrase(self, ssh):
        with patch("subprocess.run"):
            private, public = ssh.generate_ssh_key(
                "rsa", "testpass", "t@t.com", "secret"
            )
        assert private is not None
        assert "testpass" in private

    def test_returns_none_on_subprocess_error(self, ssh):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "ssh-keygen")
        ):
            private, public = ssh.generate_ssh_key("rsa", "test", "t@t.com")
        assert private is None
        assert public is None

    def test_key_paths_use_correct_type(self, ssh):
        with patch("subprocess.run"):
            private, public = ssh.generate_ssh_key("ed25519", "myacc", "t@t.com")
        assert "ed25519" in private
        assert "myacc" in private


class TestOverwriteSSHKey:
    def test_overwrites_existing_keys(self, ssh):
        private_path = ssh.ssh_dir / "id_rsa_test"
        public_path = ssh.ssh_dir / "id_rsa_test.pub"
        private_path.write_text("old private")
        public_path.write_text("old public")

        with patch("subprocess.run"):
            private, public = ssh.overwrite_ssh_key("rsa", "test", "t@t.com")
        # old files were deleted before generate_ssh_key was called
        assert private is not None
        assert not private_path.exists() or private_path.read_text() != "old private"

    def test_works_when_no_existing_keys(self, ssh):
        with patch("subprocess.run"):
            private, public = ssh.overwrite_ssh_key("rsa", "newkey", "t@t.com")
        assert private is not None


class TestDeleteSSHKey:
    def test_deletes_both_files(self, ssh, tmp_path):
        private = tmp_path / "id_rsa_test"
        public = tmp_path / "id_rsa_test.pub"
        private.write_text("private")
        public.write_text("public")

        assert ssh.delete_ssh_key(str(private), str(public)) is True
        assert not private.exists()
        assert not public.exists()

    def test_succeeds_when_files_missing(self, ssh, tmp_path):
        assert (
            ssh.delete_ssh_key(
                str(tmp_path / "nonexistent"),
                str(tmp_path / "nonexistent.pub"),
            )
            is True
        )


class TestClearAllKeys:
    def test_clears_keys_successfully(self, ssh):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert ssh.clear_all_keys() is True

    def test_succeeds_when_no_keys_loaded(self, ssh):
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "ssh-add")
        ):
            assert ssh.clear_all_keys() is True

    def test_returns_false_when_ssh_add_missing(self, ssh):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert ssh.clear_all_keys() is False


class TestAddKeyToAgent:
    def test_success(self, ssh, tmp_path):
        key = tmp_path / "id_rsa_test"
        key.write_text("key content")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            success, error = ssh.add_key_to_agent(str(key))
        assert success is True
        assert error is None

    def test_failure_with_error_message(self, ssh, tmp_path):
        key = tmp_path / "id_rsa_test"
        key.write_text("bad key")
        exc = subprocess.CalledProcessError(1, "ssh-add")
        exc.stderr = "Error loading key"
        with patch("subprocess.run", side_effect=exc):
            success, error = ssh.add_key_to_agent(str(key))
        assert success is False
        assert "Error loading key" in error

    def test_failure_when_ssh_add_missing(self, ssh, tmp_path):
        key = tmp_path / "id_rsa_test"
        key.write_text("key")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            success, error = ssh.add_key_to_agent(str(key))
        assert success is False
        assert error is not None


class TestGetPublicKeyContent:
    def test_reads_content(self, ssh, tmp_path):
        pub_key = tmp_path / "id_rsa_test.pub"
        pub_key.write_text("ssh-rsa AAAA test@test.com")
        assert ssh.get_public_key_content(str(pub_key)) == "ssh-rsa AAAA test@test.com"

    def test_strips_whitespace(self, ssh, tmp_path):
        pub_key = tmp_path / "id_rsa_test.pub"
        pub_key.write_text("  ssh-rsa AAAA  \n")
        assert ssh.get_public_key_content(str(pub_key)) == "ssh-rsa AAAA"

    def test_returns_none_for_missing_file(self, ssh, tmp_path):
        assert ssh.get_public_key_content(str(tmp_path / "nonexistent.pub")) is None
