"""Tests for shell autocomplete helpers."""

from unittest.mock import patch
from gitacc_switcher.completion import get_account_names


def test_returns_account_names():
    with patch("gitacc_switcher.completion.ConfigManager") as MockCM:
        MockCM.return_value.list_account_names.return_value = ["work", "personal"]
        assert get_account_names() == ["work", "personal"]


def test_returns_empty_list_on_error():
    with patch(
        "gitacc_switcher.completion.ConfigManager", side_effect=Exception("fail")
    ):
        assert get_account_names() == []


def test_returns_empty_when_no_accounts():
    with patch("gitacc_switcher.completion.ConfigManager") as MockCM:
        MockCM.return_value.list_account_names.return_value = []
        assert get_account_names() == []


def test_returns_list_type():
    with patch("gitacc_switcher.completion.ConfigManager") as MockCM:
        MockCM.return_value.list_account_names.return_value = ["work"]
        result = get_account_names()
        assert isinstance(result, list)
