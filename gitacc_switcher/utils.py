"""Utility functions for colored output, prompts, and validation."""

import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    RESET = "\033[0m"


def echo_color(color: str, message: str) -> None:
    """Print colored message to terminal.

    Args:
        color: Color keyword (r/red, g/green, y/yellow, b/blue)
        message: Message to print
    """
    color_code = Colors.RESET
    color_lower = color.lower()

    if color_lower.startswith("r"):
        color_code = Colors.RED
    elif color_lower.startswith("g"):
        color_code = Colors.GREEN
    elif color_lower.startswith("y"):
        color_code = Colors.YELLOW
    elif color_lower.startswith("b"):
        color_code = Colors.BLUE
    else:
        print(f"{Colors.RED}Wrong COLOR keyword!{Colors.RESET}")
        return

    print(f"{color_code}{message}{Colors.RESET}")


def ask_yes_no(prompt: str) -> bool:
    """Ask user a yes/no question.

    Args:
        prompt: Question to ask

    Returns:
        True if yes, False if no
    """
    while True:
        response = (
            input(f"{Colors.YELLOW}{prompt} [y/n] {Colors.RESET}").strip().lower()
        )
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            echo_color("r", "Wrong command!!")


def validate_ssh_key_type(key_type: str) -> bool:
    """Validate SSH key type.

    Args:
        key_type: SSH key type to validate

    Returns:
        True if valid, False otherwise
    """
    valid_types = ["dsa", "ecdsa", "ecdsa-sk", "ed25519", "ed25519-sk", "rsa"]
    return key_type.lower() in valid_types


def get_ssh_key_types() -> list:
    """Get list of valid SSH key types.

    Returns:
        List of valid SSH key types
    """
    return ["dsa", "ecdsa", "ecdsa-sk", "ed25519", "ed25519-sk", "rsa"]
