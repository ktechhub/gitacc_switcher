"""Manage Git configuration and .gitacc file."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
import re


class ConfigManager:
    """Manages Git global config and .gitacc file."""

    def __init__(self):
        self.gitacc_file = Path.home() / ".gitacc"
        self._ensure_gitacc_file()

    def _ensure_gitacc_file(self) -> None:
        """Ensure .gitacc file exists."""
        if not self.gitacc_file.exists():
            self.gitacc_file.touch()

    def set_git_config(self, name: str, email: str) -> bool:
        """Set Git global user.name and user.email.

        Args:
            name: Git user name
            email: Git user email

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["git", "config", "--global", "user.name", name],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "--global", "user.email", email],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def unset_git_config(self) -> bool:
        """Unset Git global user.name and user.email.

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["git", "config", "--global", "--unset", "user.name"],
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "--global", "--unset", "user.email"],
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_current_git_config(self) -> Dict[str, Optional[str]]:
        """Get current Git global config.

        Returns:
            Dictionary with 'name' and 'email' keys
        """
        name = None
        email = None

        try:
            result = subprocess.run(
                ["git", "config", "--global", "user.name"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                name = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

        try:
            result = subprocess.run(
                ["git", "config", "--global", "user.email"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                email = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

        return {"name": name, "email": email}

    def read_accounts(self) -> Dict[str, Dict[str, str]]:
        """Read all accounts from .gitacc file.

        Returns:
            Dictionary mapping account names to their info
        """
        accounts = {}
        if not self.gitacc_file.exists():
            return accounts

        with open(self.gitacc_file, "r") as f:
            lines = f.readlines()

        # Parse INI-like format: [account_name]\n\tname = ...\n\temail = ...\n\tprivate_key = ...\n\tpublic_key = ...
        current_account = None
        current_info = {}

        for line in lines:
            line = line.rstrip()
            # Check for account section header
            section_match = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
            if section_match:
                # Save previous account if exists
                if current_account and current_info:
                    accounts[current_account] = current_info
                # Start new account
                current_account = section_match.group(1).strip()
                current_info = {}
            # Check for key-value pairs
            elif current_account:
                kv_match = re.match(r"^\s*(\w+)\s*=\s*(.+)$", line)
                if kv_match:
                    key = kv_match.group(1).strip()
                    value = kv_match.group(2).strip()
                    current_info[key] = value

        # Save last account
        if current_account and current_info:
            accounts[current_account] = current_info

        return accounts

    def get_account(self, account_name: str) -> Optional[Dict[str, str]]:
        """Get account info by name.

        Args:
            account_name: Name of the account

        Returns:
            Account info dictionary or None if not found
        """
        accounts = self.read_accounts()
        return accounts.get(account_name)

    def add_account(
        self,
        account_name: str,
        name: str,
        email: str,
        private_key: str,
        public_key: str,
    ) -> bool:
        """Add account to .gitacc file.

        Args:
            account_name: Account identifier
            name: Git user name
            email: Git user email
            private_key: Path to private SSH key
            public_key: Path to public SSH key

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.gitacc_file, "a") as f:
                f.write(f"[{account_name}]\n")
                f.write(f"\tname = {name}\n")
                f.write(f"\temail = {email}\n")
                f.write(f"\tprivate_key = {private_key}\n")
                f.write(f"\tpublic_key = {public_key}\n")
            return True
        except Exception:
            return False

    def update_account_field(
        self, account_name: str, field: str, new_value: str
    ) -> bool:
        """Update a single field for an existing account.

        Args:
            account_name: Account identifier to update
            field: Field name to update (e.g. "name", "email")
            new_value: New value for the field

        Returns:
            True if successful, False otherwise
        """
        accounts = self.read_accounts()
        if account_name not in accounts:
            return False

        with open(self.gitacc_file, "r") as f:
            lines = f.readlines()

        new_lines = []
        in_target_section = False
        i = 0

        while i < len(lines):
            line = lines[i]
            if re.match(rf"^\s*\[{re.escape(account_name)}\]\s*$", line):
                in_target_section = True
                new_lines.append(line)
                i += 1
                while i < len(lines) and in_target_section:
                    if re.match(r"^\s*\[", lines[i]) and not re.match(
                        rf"^\s*\[{re.escape(account_name)}\]\s*$", lines[i]
                    ):
                        in_target_section = False
                        new_lines.append(lines[i])
                        i += 1
                        break
                    elif re.match(rf"^\s*{re.escape(field)}\s*=", lines[i]):
                        new_lines.append(f"\t{field} = {new_value}\n")
                        i += 1
                    else:
                        new_lines.append(lines[i])
                        i += 1
            else:
                new_lines.append(line)
                i += 1

        try:
            with open(self.gitacc_file, "w") as f:
                f.writelines(new_lines)
            return True
        except Exception:
            return False

    def remove_account(self, account_name: str) -> bool:
        """Remove account from .gitacc file.

        Args:
            account_name: Account identifier to remove

        Returns:
            True if successful, False otherwise
        """
        accounts = self.read_accounts()
        if account_name not in accounts:
            return False

        # Read file content
        with open(self.gitacc_file, "r") as f:
            lines = f.readlines()

        # Find and remove account section
        new_lines = []
        skip_section = False
        i = 0

        while i < len(lines):
            line = lines[i]
            # Check if this is the account section header
            if re.match(rf"^\s*\[{re.escape(account_name)}\]\s*$", line):
                skip_section = True
                i += 1
                # Skip until next section or end of file
                while i < len(lines) and skip_section:
                    if re.match(r"^\s*\[", lines[i]) and not re.match(
                        rf"^\s*\[{re.escape(account_name)}\]\s*$", lines[i]
                    ):
                        skip_section = False
                        new_lines.append(lines[i])
                        i += 1
                        break
                    i += 1
            else:
                new_lines.append(line)
                i += 1

        # Write back
        try:
            with open(self.gitacc_file, "w") as f:
                f.writelines(new_lines)
            return True
        except Exception:
            return False

    def list_account_names(self) -> List[str]:
        """Get list of all account names.

        Returns:
            List of account names
        """
        return list(self.read_accounts().keys())

    def is_git_repo(self, path: Optional[Path] = None) -> bool:
        """Check if the current directory is a Git repository.

        Args:
            path: Path to check (default: current directory)

        Returns:
            True if it's a Git repository, False otherwise
        """
        if path is None:
            path = Path.cwd()

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                check=True,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_repo_expected_account(
        self, repo_path: Optional[Path] = None
    ) -> Optional[str]:
        """Get the expected account name for a repository.

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            Expected account name or None if not set
        """
        if not self.is_git_repo(repo_path):
            return None

        try:
            result = subprocess.run(
                ["git", "config", "gitacc.expected-account"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

        return None

    def set_repo_expected_account(
        self, account_name: str, repo_path: Optional[Path] = None
    ) -> bool:
        """Set the expected account name for a repository.

        Args:
            account_name: Account name to set as expected
            repo_path: Path to repository (default: current directory)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_git_repo(repo_path):
            return False

        try:
            subprocess.run(
                ["git", "config", "gitacc.expected-account", account_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_current_git_config_local(
        self, repo_path: Optional[Path] = None
    ) -> Dict[str, Optional[str]]:
        """Get current Git config (local, then global fallback).

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            Dictionary with 'name' and 'email' keys
        """
        name = None
        email = None

        # Try local config first
        try:
            result = subprocess.run(
                ["git", "config", "user.name"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                name = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

        # Fallback to global if local not set
        if not name:
            name = self.get_current_git_config().get("name")

        # Try local config first
        try:
            result = subprocess.run(
                ["git", "config", "user.email"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                email = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

        # Fallback to global if local not set
        if not email:
            email = self.get_current_git_config().get("email")

        return {"name": name, "email": email}
