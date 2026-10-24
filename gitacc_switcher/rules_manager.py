"""Directory-based auto-switch rule storage and lookup.

Rules map a directory (and everything beneath it) to the account that should
become active whenever the shell's current working directory is there. This
is the pure-Python half of the opt-in auto-switch feature; the actual
"notice I changed directories" trigger comes from a shell hook (see
`shell_hook.py`) that calls `gitacc rule check` on every prompt render.
"""

import re
from pathlib import Path
from typing import Dict, Optional


class RulesManager:
    """Manages directory-to-account auto-switch rules."""

    def __init__(self, rules_file: Optional[Path] = None):
        self.rules_file = rules_file or (Path.home() / ".gitaccrules")

    def _normalize_path(self, directory: Path) -> str:
        """Resolve a directory to its canonical absolute form."""
        return str(Path(directory).expanduser().resolve())

    def list_rules(self) -> Dict[str, str]:
        """Read all rules from the rules file.

        Returns:
            Dictionary mapping normalized directory path to account name, in
            file order. Blank lines and lines starting with '#' are ignored.
        """
        rules: Dict[str, str] = {}
        if not self.rules_file.exists():
            return rules

        with open(self.rules_file, "r") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^(.+?)\s*=\s*(.+)$", line)
                if not match:
                    continue
                directory = match.group(1).strip()
                account_name = match.group(2).strip()
                if directory and account_name:
                    rules[directory] = account_name

        return rules

    def _write_rules(self, rules: Dict[str, str]) -> None:
        with open(self.rules_file, "w") as f:
            for directory, account_name in rules.items():
                f.write(f"{directory} = {account_name}\n")

    def add_rule(self, directory: Path, account_name: str) -> bool:
        """Add or update the rule for a directory.

        Args:
            directory: Directory the rule applies to (and its subdirectories)
            account_name: Account to switch to while inside that directory

        Returns:
            True if successful, False otherwise
        """
        try:
            normalized = self._normalize_path(directory)
            rules = self.list_rules()
            rules[normalized] = account_name
            self._write_rules(rules)
            return True
        except OSError:
            return False

    def remove_rule(self, directory: Path) -> bool:
        """Remove the rule for a directory, if one exists.

        Args:
            directory: Directory whose rule should be removed

        Returns:
            True if a rule was removed, False if none existed or on error
        """
        try:
            normalized = self._normalize_path(directory)
            rules = self.list_rules()
            if normalized not in rules:
                return False
            del rules[normalized]
            self._write_rules(rules)
            return True
        except OSError:
            return False

    def find_matching_account(self, cwd: Path) -> Optional[str]:
        """Find the account whose rule most specifically matches a directory.

        Walks from the given directory up through its parents, direnv-style,
        and returns the account for the first (deepest, most specific) rule
        directory that is the given directory or an ancestor of it.

        Args:
            cwd: Directory to match against registered rules

        Returns:
            Matching account name, or None if no rule applies
        """
        rules = self.list_rules()
        if not rules:
            return None

        current = Path(cwd).expanduser().resolve()
        for directory in [current, *current.parents]:
            account_name = rules.get(str(directory))
            if account_name:
                return account_name

        return None
