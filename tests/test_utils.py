"""Tests for utility functions."""

import pytest
from unittest.mock import patch
from gitacc_switcher.utils import echo_color, ask_yes_no, validate_ssh_key_type, get_ssh_key_types


class TestValidateSSHKeyType:
    def test_valid_types(self):
        for key_type in ["dsa", "ecdsa", "ecdsa-sk", "ed25519", "ed25519-sk", "rsa"]:
            assert validate_ssh_key_type(key_type) is True

    def test_case_insensitive(self):
        assert validate_ssh_key_type("RSA") is True
        assert validate_ssh_key_type("Ed25519") is True

    def test_invalid_types(self):
        assert validate_ssh_key_type("invalid") is False
        assert validate_ssh_key_type("ssh-rsa") is False
        assert validate_ssh_key_type("") is False
        assert validate_ssh_key_type("rsa2") is False


class TestGetSSHKeyTypes:
    def test_returns_list(self):
        assert isinstance(get_ssh_key_types(), list)

    def test_contains_common_types(self):
        types = get_ssh_key_types()
        assert "rsa" in types
        assert "ed25519" in types
        assert "ecdsa" in types

    def test_length(self):
        assert len(get_ssh_key_types()) == 6


class TestEchoColor:
    def test_green_output(self, capsys):
        echo_color("g", "hello")
        assert "hello" in capsys.readouterr().out

    def test_red_output(self, capsys):
        echo_color("r", "error")
        assert "error" in capsys.readouterr().out

    def test_yellow_output(self, capsys):
        echo_color("y", "warning")
        assert "warning" in capsys.readouterr().out

    def test_blue_output(self, capsys):
        echo_color("b", "info")
        assert "info" in capsys.readouterr().out

    def test_full_color_name(self, capsys):
        echo_color("green", "hello")
        assert "hello" in capsys.readouterr().out

    def test_unknown_color_warns(self, capsys):
        echo_color("z", "test")
        assert "Wrong COLOR keyword!" in capsys.readouterr().out

    def test_ansi_codes_present(self, capsys):
        echo_color("g", "msg")
        out = capsys.readouterr().out
        assert "\033[" in out  # ANSI escape present


class TestAskYesNo:
    def test_y_returns_true(self):
        with patch("builtins.input", return_value="y"):
            assert ask_yes_no("Continue?") is True

    def test_n_returns_false(self):
        with patch("builtins.input", return_value="n"):
            assert ask_yes_no("Continue?") is False

    def test_yes_returns_true(self):
        with patch("builtins.input", return_value="yes"):
            assert ask_yes_no("Continue?") is True

    def test_no_returns_false(self):
        with patch("builtins.input", return_value="no"):
            assert ask_yes_no("Continue?") is False

    def test_invalid_then_valid(self, capsys):
        with patch("builtins.input", side_effect=["maybe", "y"]):
            result = ask_yes_no("Continue?")
        assert result is True
        assert "Wrong command!!" in capsys.readouterr().out

    def test_uppercase_accepted(self):
        with patch("builtins.input", return_value="Y"):
            assert ask_yes_no("Continue?") is True
