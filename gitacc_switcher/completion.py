"""Completion functions for shell autocomplete."""

from typing import List
from .config_manager import ConfigManager


def get_account_names() -> List[str]:
    """Get list of account names for completion.

    Returns:
        List of account names
    """
    try:
        config_manager = ConfigManager()
        return config_manager.list_account_names()
    except Exception:
        return []
