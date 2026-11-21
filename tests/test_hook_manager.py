"""Tests for HookManager — git pre-commit hook install/uninstall."""

import pytest
from unittest.mock import patch, MagicMock
from gitacc_switcher.hook_manager import HookManager


@pytest.fixture
def git_repo(tmp_path):
    """Minimal fake git repository with a hooks directory."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "hooks").mkdir()
    return tmp_path


@pytest.fixture
def hook_manager():
    return HookManager()


def _git_subprocess(configured_hooks_path=None):
    """Fake `subprocess.run` that answers `git rev-parse --git-dir` and
    `git config --get core.hooksPath`, mirroring real git's behavior of a
    non-zero exit with empty output when core.hooksPath isn't set."""

    def _run(cmd, **kwargs):
        if cmd[:2] == ["git", "rev-parse"]:
            return MagicMock(returncode=0, stdout=".git\n")
        if cmd[:2] == ["git", "config"]:
            if configured_hooks_path is not None:
                return MagicMock(returncode=0, stdout=f"{configured_hooks_path}\n")
            return MagicMock(returncode=1, stdout="")
        raise AssertionError(f"unexpected subprocess.run call: {cmd}")

    return _run


def _mock_git_dir(repo_path, configured_hooks_path=None):
    """Return a patch context that makes get_hooks_dir resolve correctly."""
    return patch("subprocess.run", side_effect=_git_subprocess(configured_hooks_path))


class TestGetHooksDir:
    def test_returns_hooks_path(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            result = hook_manager.get_hooks_dir(git_repo)
        assert result is not None
        assert result.name == "hooks"

    def test_returns_none_on_subprocess_error(self, hook_manager, tmp_path):
        import subprocess

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(128, "git")
        ):
            assert hook_manager.get_hooks_dir(tmp_path) is None

    def test_honors_configured_core_hooks_path(self, hook_manager, git_repo):
        (git_repo / "custom-hooks").mkdir()
        with _mock_git_dir(git_repo, configured_hooks_path="custom-hooks"):
            result = hook_manager.get_hooks_dir(git_repo)
        assert result == git_repo / "custom-hooks"

    def test_falls_back_to_git_hooks_when_hooks_path_unset(
        self, hook_manager, git_repo
    ):
        with _mock_git_dir(git_repo, configured_hooks_path=None):
            result = hook_manager.get_hooks_dir(git_repo)
        assert result == git_repo / ".git" / "hooks"


class TestInstallPreCommitHook:
    def test_creates_hook_file(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            assert hook_manager.install_pre_commit_hook(git_repo) is True
        assert (git_repo / ".git" / "hooks" / "pre-commit").exists()

    def test_hook_is_executable(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            hook_manager.install_pre_commit_hook(git_repo)
        hook = git_repo / ".git" / "hooks" / "pre-commit"
        assert hook.stat().st_mode & 0o111

    def test_hook_contains_gitacc_marker(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            hook_manager.install_pre_commit_hook(git_repo)
        content = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
        assert "Git Account Switcher" in content

    def test_hook_contains_expected_account_check(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            hook_manager.install_pre_commit_hook(git_repo)
        content = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
        assert "gitacc.expected-account" in content

    def test_refuses_to_overwrite_foreign_hook(self, hook_manager, git_repo, capsys):
        hook = git_repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'other tool'\n")
        hook.chmod(0o755)
        with _mock_git_dir(git_repo):
            result = hook_manager.install_pre_commit_hook(git_repo)
        assert result is False
        assert "other tool" in hook.read_text()  # original preserved

    def test_overwrites_own_existing_hook(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            hook_manager.install_pre_commit_hook(git_repo)
            result = hook_manager.install_pre_commit_hook(git_repo)
        assert result is True

    def test_installs_into_configured_hooks_path(self, hook_manager, git_repo):
        """When core.hooksPath already points elsewhere (e.g. husky, lefthook),
        gitacc must install there instead of .git/hooks, where git would
        otherwise silently never run it."""
        with _mock_git_dir(git_repo, configured_hooks_path="custom-hooks"):
            assert hook_manager.install_pre_commit_hook(git_repo) is True
        assert (git_repo / "custom-hooks" / "pre-commit").exists()
        assert not (git_repo / ".git" / "hooks" / "pre-commit").exists()

    def test_refuses_to_overwrite_foreign_hook_in_configured_hooks_path(
        self, hook_manager, git_repo
    ):
        custom_hooks = git_repo / "custom-hooks"
        custom_hooks.mkdir()
        hook = custom_hooks / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'husky'\n")
        hook.chmod(0o755)
        with _mock_git_dir(git_repo, configured_hooks_path="custom-hooks"):
            result = hook_manager.install_pre_commit_hook(git_repo)
        assert result is False
        assert "husky" in hook.read_text()  # original preserved


class TestUninstallPreCommitHook:
    def test_removes_own_hook(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            hook_manager.install_pre_commit_hook(git_repo)
            result = hook_manager.uninstall_pre_commit_hook(git_repo)
        assert result is True
        assert not (git_repo / ".git" / "hooks" / "pre-commit").exists()

    def test_does_not_remove_foreign_hook(self, hook_manager, git_repo):
        hook = git_repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\n# foreign tool\n")
        with _mock_git_dir(git_repo):
            result = hook_manager.uninstall_pre_commit_hook(git_repo)
        assert result is False
        assert hook.exists()

    def test_succeeds_when_no_hook_present(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            result = hook_manager.uninstall_pre_commit_hook(git_repo)
        assert result is True


class TestIsHookInstalled:
    def test_detects_own_hook(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            hook_manager.install_pre_commit_hook(git_repo)
            assert hook_manager.is_hook_installed(git_repo) is True

    def test_returns_false_when_no_hook(self, hook_manager, git_repo):
        with _mock_git_dir(git_repo):
            assert hook_manager.is_hook_installed(git_repo) is False

    def test_returns_false_for_foreign_hook(self, hook_manager, git_repo):
        hook = git_repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho foreign\n")
        with _mock_git_dir(git_repo):
            assert hook_manager.is_hook_installed(git_repo) is False
