"""Tests for shell hook snippet generation."""

from gitacc_switcher.shell_hook import get_hook_script, get_supported_shells


class TestGetHookScript:
    def test_bash_hook_calls_rule_check(self):
        script = get_hook_script("bash")
        assert script is not None
        assert "gitacc rule check" in script
        assert "PROMPT_COMMAND" in script

    def test_zsh_hook_calls_rule_check(self):
        script = get_hook_script("zsh")
        assert script is not None
        assert "gitacc rule check" in script
        assert "chpwd_functions" in script

    def test_is_case_insensitive(self):
        assert get_hook_script("Bash") == get_hook_script("bash")

    def test_unsupported_shell_returns_none(self):
        assert get_hook_script("fish") is None


class TestGetSupportedShells:
    def test_includes_bash_and_zsh(self):
        shells = get_supported_shells()
        assert "bash" in shells
        assert "zsh" in shells

    def test_every_supported_shell_has_a_script(self):
        for shell in get_supported_shells():
            assert get_hook_script(shell)
