"""Account management operations."""

import getpass
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from .config_manager import ConfigManager
from .ssh_manager import SSHManager
from .hook_manager import HookManager
from .rules_manager import RulesManager
from .utils import echo_color, ask_yes_no, validate_ssh_key_type


class AccountManager:
    """Manages Git account operations."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.ssh_manager = SSHManager()
        self.hook_manager = HookManager()
        self.rules_manager = RulesManager()

    def add_account(self, key_type: str = "rsa", sign: bool = False) -> bool:
        """Add a new Git account.

        Args:
            key_type: SSH key type (default: rsa)
            sign: Opt-in to SSH commit signing with this account's key when
                switched to (sets user.signingkey, gpg.format=ssh,
                commit.gpgsign=true)

        Returns:
            True if successful, False otherwise
        """
        # Validate key type
        if not validate_ssh_key_type(key_type):
            echo_color("r", f"Invalid SSH key type: {key_type}")
            return False

        # Get account info from user
        account_name = input("Enter account name (identifier): ").strip()
        if not account_name:
            echo_color("r", "Account name cannot be empty!")
            return False

        # Get Git name (defaults to account name)
        git_name_prompt = (
            f"Enter Git name (default: {account_name}, press Enter to use same): "
        )
        git_name = input(git_name_prompt).strip()
        if not git_name:
            git_name = account_name  # Use account name as default

        email = input("Enter your git user email: ").strip()
        if not email:
            echo_color("r", "Email cannot be empty!")
            return False

        # Check if account already exists before prompting for passphrase
        existing_account = self.config_manager.get_account(account_name)
        overwrite = False

        if existing_account:
            echo_color("r", "Warning: Already have same account name.")
            if ask_yes_no("Do you want to overwrite?"):
                overwrite = True
            else:
                echo_color("y", "Please use another account name.")
                return False

        # Ask if user wants to add a passphrase to the SSH key
        passphrase = None
        if ask_yes_no("Do you want to add a passphrase to the SSH key?"):
            passphrase = getpass.getpass("Enter passphrase (will be hidden): ")
            if passphrase:
                passphrase_confirm = getpass.getpass("Confirm passphrase: ")
                if passphrase != passphrase_confirm:
                    echo_color("r", "Passphrases do not match!")
                    return False
            else:
                echo_color("y", "No passphrase set (empty passphrase).")

        # Generate SSH keys
        if overwrite:
            # Remove old account entry first
            self.config_manager.remove_account(account_name)
            private_key, public_key = self.ssh_manager.overwrite_ssh_key(
                key_type, account_name, email, passphrase
            )
        else:
            private_key, public_key = self.ssh_manager.generate_ssh_key(
                key_type, account_name, email, passphrase
            )

        if not private_key or not public_key:
            echo_color("r", "Failed to generate SSH keys!")
            return False

        # Add to .gitacc file
        success = self.config_manager.add_account(
            account_name, git_name, email, private_key, public_key, sign=sign
        )
        if not success:
            echo_color("r", "Failed to save account info!")
            return False

        # Show public key
        public_key_content = self.ssh_manager.get_public_key_content(public_key)
        if public_key_content:
            echo_color("g", "Your SSH publish key is :")
            print(public_key_content)
            echo_color("g", "Paste it to your SSH keys in github or server.")

        return True

    def remove_account(self, account_name: Optional[str] = None) -> bool:
        """Remove a Git account.

        Args:
            account_name: Account name to remove (if None, prompt user)

        Returns:
            True if successful, False otherwise
        """
        if not account_name:
            account_name = input("Enter the git user name you want to remove: ").strip()
            if not account_name:
                echo_color("r", "Account name cannot be empty!")
                return False

        # Get account info
        account_info = self.config_manager.get_account(account_name)
        if not account_info:
            echo_color("r", "Wrong: account name!!")
            return False

        # Show account details and ask for confirmation
        git_name = account_info.get("name", account_name)
        email = account_info.get("email", "N/A")
        echo_color("y", f"Account to remove: {account_name}")
        echo_color("y", f"  Git name: {git_name}")
        echo_color("y", f"  Email: {email}")

        if not ask_yes_no(f"Are you sure you want to remove account '{account_name}'?"):
            echo_color("y", "Removal cancelled.")
            return False

        # Remove SSH keys
        private_key = account_info.get("private_key")
        public_key = account_info.get("public_key")

        if private_key and public_key:
            self.ssh_manager.delete_ssh_key(private_key, public_key)

        # Remove from .gitacc file
        success = self.config_manager.remove_account(account_name)
        if not success:
            echo_color("r", "Failed to remove account from config!")
            return False

        echo_color("g", f'Account "{account_name}" removed successfully!')
        return True

    def switch_account(self, account_name: str, local: bool = False) -> bool:
        """Switch to a Git account.

        Args:
            account_name: Account name to switch to
            local: If True, set the identity for the current repository only
                (git config local scope) instead of globally

        Returns:
            True if successful, False otherwise
        """
        # Get account info
        account_info = self.config_manager.get_account(account_name)
        if not account_info:
            echo_color("r", "Wrong: account name!!")
            return False

        if local and not self.config_manager.is_git_repo():
            echo_color("r", "Not a Git repository!")
            echo_color("y", "--local requires running inside a Git repository.")
            return False

        # Check if SSH agent is already running
        agent_running = self.ssh_manager.is_ssh_agent_running()

        if not agent_running:
            # Agent not running, need to start it
            echo_color("y", "SSH agent is not running in your shell.")
            echo_color("y", "Please run the following command in your shell:")
            echo_color("b", "  eval $(ssh-agent)")
            echo_color("y", "Then run this command again:")
            echo_color("b", f"  gitacc switch {account_name}")
            return False

        # Clear all existing keys from agent first
        self.ssh_manager.clear_all_keys()

        # Agent is running, add only the new account's key
        private_key = account_info.get("private_key")
        if not private_key or not Path(private_key).exists():
            echo_color("r", f"SSH key not found: {private_key}")
            return False

        success, error_msg = self.ssh_manager.add_key_to_agent(private_key)
        if not success:
            echo_color("r", f"Failed to add SSH key to agent: {error_msg}")
            echo_color("y", "Make sure the SSH agent is running in your shell.")
            echo_color("y", "You may need to run: eval $(ssh-agent)")
            return False

        # Verify key was added and is the only one
        try:
            result = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
            if result.returncode == 0:
                key_count = len(
                    [line for line in result.stdout.strip().split("\n") if line.strip()]
                )
                echo_color(
                    "g",
                    f"SSH key added to agent successfully ({key_count} key(s) in agent)",
                )
            else:
                echo_color("y", "Warning: Could not verify key was added to agent")
        except Exception:
            pass

        # Set Git config
        name = account_info.get("name")
        email = account_info.get("email")
        if local:
            config_success = self.config_manager.set_git_config_local(name, email)
        else:
            config_success = self.config_manager.set_git_config(name, email)
        if not config_success:
            echo_color("r", "Failed to set Git config!")
            return False

        # Apply (or clear) this account's SSH commit-signing preference
        sign_enabled = str(account_info.get("sign", "false")).lower() == "true"
        public_key = account_info.get("public_key")
        if local:
            if sign_enabled and public_key:
                signing_success = self.config_manager.set_git_signing_config_local(
                    public_key
                )
            else:
                signing_success = self.config_manager.unset_git_signing_config_local()
        else:
            if sign_enabled and public_key:
                signing_success = self.config_manager.set_git_signing_config(public_key)
            else:
                signing_success = self.config_manager.unset_git_signing_config()
        if not signing_success:
            echo_color("y", "Warning: Could not update commit-signing config.")

        scope = "this repository only" if local else "globally"
        echo_color(
            "g",
            f'Switched to account "{account_name}" successfully! ({scope})',
        )
        return True

    def logout(self) -> bool:
        """Logout current Git account.

        Returns:
            True if successful, False otherwise
        """
        if self.ssh_manager.is_ssh_agent_running():
            self.ssh_manager.kill_ssh_agent()

        self.config_manager.unset_git_config()
        self.config_manager.unset_git_signing_config()
        echo_color("g", "Logged out successfully!")
        return True

    def list_accounts(self) -> List[str]:
        """List all registered accounts.

        Returns:
            List of account names
        """
        return self.config_manager.list_account_names()

    def list_accounts_detailed(self) -> Dict[str, Dict[str, str]]:
        """List all registered accounts with details.

        Returns:
            Dictionary mapping account names to their info
        """
        return self.config_manager.read_accounts()

    def account_exists(self, account_name: str) -> bool:
        """Check if an account exists.

        Args:
            account_name: Account name to check

        Returns:
            True if account exists, False otherwise
        """
        return self.config_manager.get_account(account_name) is not None

    def update_account(
        self,
        account_name: str,
        new_git_name: Optional[str] = None,
        new_email: Optional[str] = None,
        new_sign: Optional[bool] = None,
    ) -> bool:
        """Update the Git name, email, and/or commit-signing preference for an
        existing account.

        Args:
            account_name: Account identifier to update
            new_git_name: New Git name (if None, will prompt)
            new_email: New email (if None, will prompt)
            new_sign: New commit-signing preference (if None, leave unchanged)

        Returns:
            True if successful, False otherwise
        """
        account_info = self.config_manager.get_account(account_name)
        if not account_info:
            echo_color("r", f'Account "{account_name}" not found!')
            return False

        current_git_name = account_info.get("name", account_name)
        current_email = account_info.get("email", "")

        if new_git_name is None:
            prompt = f"Enter new Git name (current: {current_git_name}, press Enter to keep): "
            new_git_name = input(prompt).strip() or current_git_name

        if new_email is None:
            prompt = (
                f"Enter new email (current: {current_email}, press Enter to keep): "
            )
            new_email = input(prompt).strip() or current_email

        changed = False

        if new_git_name != current_git_name:
            if not self.config_manager.update_account_field(
                account_name, "name", new_git_name
            ):
                echo_color("r", "Failed to update Git name!")
                return False
            echo_color(
                "g",
                f'Updated Git name for "{account_name}": {current_git_name} → {new_git_name}',
            )
            changed = True

        if new_email != current_email:
            if not self.config_manager.update_account_field(
                account_name, "email", new_email
            ):
                echo_color("r", "Failed to update email!")
                return False
            echo_color(
                "g",
                f'Updated email for "{account_name}": {current_email} → {new_email}',
            )
            changed = True

        if new_sign is not None:
            current_sign = str(account_info.get("sign", "false")).lower() == "true"
            if new_sign != current_sign:
                if not self.config_manager.update_account_field(
                    account_name, "sign", "true" if new_sign else "false"
                ):
                    echo_color("r", "Failed to update commit-signing setting!")
                    return False
                state = "enabled" if new_sign else "disabled"
                echo_color("g", f'Commit signing {state} for "{account_name}"')
                changed = True

        if not changed:
            echo_color("y", "No changes made.")

        return True

    def add_host_alias(
        self,
        account_name: str,
        host_alias: str,
        hostname: str = "github.com",
        ssh_user: str = "git",
    ) -> bool:
        """Bind an SSH config `Host` alias to an account's key.

        Args:
            account_name: Account whose key the alias should use
            host_alias: The `Host` alias to create/update (e.g. "github-work")
            hostname: Real host to connect to (default: "github.com")
            ssh_user: SSH user for the connection (default: "git")

        Returns:
            True if successful, False otherwise
        """
        account_info = self.config_manager.get_account(account_name)
        if not account_info:
            echo_color("r", f'Account "{account_name}" not found!')
            return False

        private_key = account_info.get("private_key")
        if not private_key:
            echo_color("r", f'Account "{account_name}" has no private key on record!')
            return False

        success = self.ssh_manager.add_host_alias(
            host_alias, hostname, private_key, ssh_user
        )
        if success:
            echo_color(
                "g",
                f'Host alias "{host_alias}" → account "{account_name}" '
                f"({ssh_user}@{hostname})",
            )
        else:
            echo_color("r", f'Failed to write host alias "{host_alias}"!')
        return success

    def remove_host_alias(self, host_alias: str) -> bool:
        """Remove a managed SSH config host alias.

        Args:
            host_alias: The `Host` alias to remove

        Returns:
            True if a block was found and removed, False otherwise
        """
        success = self.ssh_manager.remove_host_alias(host_alias)
        if success:
            echo_color("g", f'Host alias "{host_alias}" removed.')
        else:
            echo_color("y", f'No managed host alias "{host_alias}" was found.')
        return success

    def list_host_aliases(self) -> Dict[str, Dict[str, str]]:
        """List all gitacc-managed SSH config host aliases.

        Returns:
            Dictionary mapping host alias to its hostname, ssh user, and
            identity file path.
        """
        return self.ssh_manager.list_host_aliases()

    def run_doctor(self) -> Dict[str, object]:
        """Run read-only health checks on the SSH agent and managed key files.

        Checks whether the SSH agent is running and reachable, and whether
        each registered account's private key file exists, is readable, and
        has safe permissions. Makes no changes.

        Returns:
            Dictionary with 'agent_running' (bool) and 'accounts' (dict
            mapping account name to its key-file check result — see
            SSHManager.check_key_file).
        """
        agent_running = self.ssh_manager.is_ssh_agent_running()

        accounts = self.config_manager.read_accounts()
        account_checks = {}
        for account_name, account_info in accounts.items():
            private_key = account_info.get("private_key")
            if not private_key:
                account_checks[account_name] = {
                    "exists": False,
                    "readable": False,
                    "permissions_ok": False,
                }
                continue
            account_checks[account_name] = self.ssh_manager.check_key_file(private_key)

        return {"agent_running": agent_running, "accounts": account_checks}

    def get_status(self, repo_path: Optional[Path] = None) -> Dict[str, object]:
        """Report the currently active Git identity and SSH agent key, and
        which registered account (if any) they match.

        Read-only: makes no changes to Git config, the SSH agent, or any
        managed files.

        Args:
            repo_path: Path to repository (default: current directory). Used
                to resolve local Git config when run inside a repo.

        Returns:
            Dictionary with the current name/email, the matched account name
            (or None), whether the SSH agent is running, and which account
            (if any) the currently loaded agent key belongs to.
        """
        if self.config_manager.is_git_repo(repo_path):
            current_config = self.config_manager.get_current_git_config_local(repo_path)
        else:
            current_config = self.config_manager.get_current_git_config()

        current_name = current_config.get("name")
        current_email = current_config.get("email")

        accounts = self.config_manager.read_accounts()

        matched_account = None
        for account_name, account_info in accounts.items():
            if (
                current_name
                and current_email
                and account_info.get("name") == current_name
                and account_info.get("email") == current_email
            ):
                matched_account = account_name
                break

        agent_running = self.ssh_manager.is_ssh_agent_running()
        agent_fingerprints = (
            self.ssh_manager.get_agent_fingerprints() if agent_running else []
        )

        matched_key_account = None
        if agent_fingerprints:
            for account_name, account_info in accounts.items():
                public_key = account_info.get("public_key")
                if not public_key:
                    continue
                fingerprint = self.ssh_manager.get_key_fingerprint(public_key)
                if fingerprint and fingerprint in agent_fingerprints:
                    matched_key_account = account_name
                    break

        return {
            "name": current_name,
            "email": current_email,
            "matched_account": matched_account,
            "agent_running": agent_running,
            "matched_key_account": matched_key_account,
        }

    def init_repo(self, account_name: str, repo_path: Optional[Path] = None) -> bool:
        """Initialize repository with expected account and install pre-commit hook.

        Args:
            account_name: Account name to set as expected for this repo
            repo_path: Path to repository (default: current directory)

        Returns:
            True if successful, False otherwise
        """
        if not self.config_manager.is_git_repo(repo_path):
            echo_color("r", "Not a Git repository!")
            return False

        # Verify account exists
        account_info = self.config_manager.get_account(account_name)
        if not account_info:
            echo_color("r", f'Account "{account_name}" not found!')
            return False

        # Set expected account
        if not self.config_manager.set_repo_expected_account(account_name, repo_path):
            echo_color("r", "Failed to set expected account!")
            return False

        # Install pre-commit hook
        if not self.hook_manager.install_pre_commit_hook(repo_path):
            echo_color("r", "Failed to install pre-commit hook!")
            return False

        echo_color("g", f'Repository initialized with account "{account_name}"')
        echo_color("g", "Pre-commit hook installed. Commits will be validated.")
        return True

    def verify_account(self, repo_path: Optional[Path] = None) -> bool:
        """Verify that the current Git account matches the expected account for the repository.

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            True if account matches, False otherwise
        """
        if not self.config_manager.is_git_repo(repo_path):
            echo_color("r", "Not a Git repository!")
            return False

        expected_account = self.config_manager.get_repo_expected_account(repo_path)
        if not expected_account:
            echo_color("y", "No expected account set for this repository.")
            echo_color("y", 'Use "gitacc init <account>" to set one.')
            return True  # Not an error, just not configured

        # Get expected account info
        account_info = self.config_manager.get_account(expected_account)
        if not account_info:
            echo_color(
                "r",
                f'Expected account "{expected_account}" not found in registered accounts!',
            )
            return False

        # Get current config
        current_config = self.config_manager.get_current_git_config_local(repo_path)
        expected_name = account_info.get("name")
        expected_email = account_info.get("email")
        current_name = current_config.get("name")
        current_email = current_config.get("email")

        # Check if they match
        if current_name == expected_name and current_email == expected_email:
            echo_color("g", f'✓ Account verified: "{expected_account}"')
            echo_color("g", f"  Name:  {current_name}")
            echo_color("g", f"  Email: {current_email}")
            return True
        else:
            echo_color("r", f"✗ Account mismatch!")
            echo_color("r", "")
            echo_color("r", f'Expected account: "{expected_account}"')
            echo_color("r", f"  Name:  {expected_name}")
            echo_color("r", f"  Email: {expected_email}")
            echo_color("r", "")
            echo_color("r", "Current Git config:")
            echo_color("r", f"  Name:  {current_name}")
            echo_color("r", f"  Email: {current_email}")
            echo_color("r", "")
            echo_color("y", f"Please switch to the correct account:")
            echo_color("y", f"  gitacc switch {expected_account}")
            return False

    def export_accounts(self, output_path: Path, include_keys: bool = False) -> bool:
        """Export registered accounts' metadata to a portable JSON file.

        Metadata-only by default (name, email, sign preference, key *paths*,
        and any host aliases bound to each account's key) — no key material
        is read or written unless `include_keys` is explicitly set.

        Args:
            output_path: File to write the export to
            include_keys: If True, also embed each account's private/public
                SSH key file contents in the export. The resulting file will
                contain private key material in plain text; it is written
                with 0600 permissions, but the caller is responsible for
                keeping it secure afterwards.

        Returns:
            True if successful, False otherwise
        """
        accounts = self.config_manager.read_accounts()
        if not accounts:
            echo_color("y", "No accounts registered yet. Nothing to export.")
            return False

        host_aliases = self.ssh_manager.list_host_aliases()

        exported_accounts = {}
        for account_name, info in accounts.items():
            private_key = info.get("private_key", "")
            public_key = info.get("public_key", "")

            entry = {
                "name": info.get("name", account_name),
                "email": info.get("email", ""),
                "sign": info.get("sign", "false"),
                "private_key": private_key,
                "public_key": public_key,
            }

            matching_aliases = {
                alias: {"hostname": alias_info["hostname"], "user": alias_info["user"]}
                for alias, alias_info in host_aliases.items()
                if private_key and alias_info.get("identity_file") == private_key
            }
            if matching_aliases:
                entry["host_aliases"] = matching_aliases

            if include_keys:
                if public_key:
                    public_key_content = self.ssh_manager.get_public_key_content(
                        public_key
                    )
                    if public_key_content:
                        entry["public_key_content"] = public_key_content
                if private_key:
                    private_key_content = self.ssh_manager.get_private_key_content(
                        private_key
                    )
                    if private_key_content:
                        entry["private_key_content"] = private_key_content

            exported_accounts[account_name] = entry

        export_data = {
            "version": 1,
            "include_keys": include_keys,
            "accounts": exported_accounts,
        }

        output_path = Path(output_path)
        try:
            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2)
                f.write("\n")
            if include_keys:
                output_path.chmod(0o600)
        except OSError as e:
            echo_color("r", f"Failed to write export file: {e}")
            return False

        echo_color(
            "g",
            f'Exported {len(exported_accounts)} account(s) to "{output_path}"',
        )
        if include_keys:
            echo_color(
                "y",
                "This file contains private key material in plain text — "
                "keep it secure (e.g. encrypt it or delete it once transferred).",
            )
        else:
            echo_color(
                "y",
                "Metadata only: key files themselves were not copied. Pass "
                "--include-keys to also embed key material.",
            )
        return True

    def _write_imported_key_file(
        self, path_str: str, content: str, mode: int, force: bool
    ) -> bool:
        """Write key material from an import file to disk, if safe to do so.

        Args:
            path_str: Destination path for the key file
            content: Key file content to write
            mode: File permission mode to set (e.g. 0o600 for a private key)
            force: If True, overwrite an existing file at that path

        Returns:
            True if the file was written, False if skipped or on error
        """
        if not path_str:
            return False
        path = Path(path_str)
        if path.exists() and not force:
            return False
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_text(content)
            path.chmod(mode)
            return True
        except OSError:
            return False

    def import_accounts(self, input_path: Path, force: bool = False) -> bool:
        """Import accounts previously written by `export_accounts`.

        Args:
            input_path: File previously created with `gitacc export`
            force: If True, overwrite existing accounts, host aliases, and
                key files with the same name/path. Without it, anything
                that already exists is left untouched and skipped.

        Returns:
            True if the file was read and processed, False if the file
            could not be read or contained no accounts
        """
        input_path = Path(input_path)
        if not input_path.exists():
            echo_color("r", f'Import file not found: "{input_path}"')
            return False

        try:
            with open(input_path, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            echo_color("r", f"Failed to read import file: {e}")
            return False

        accounts = data.get("accounts", {})
        if not accounts:
            echo_color("y", "No accounts found in import file.")
            return False

        imported = 0
        skipped = 0

        for account_name, entry in accounts.items():
            if self.account_exists(account_name) and not force:
                echo_color(
                    "y",
                    f'Skipping "{account_name}": account already exists '
                    "(use --force to overwrite).",
                )
                skipped += 1
                continue

            private_key = entry.get("private_key", "")
            public_key = entry.get("public_key", "")

            private_key_content = entry.get("private_key_content")
            if private_key_content:
                self._write_imported_key_file(
                    private_key, private_key_content, 0o600, force
                )
            public_key_content = entry.get("public_key_content")
            if public_key_content:
                self._write_imported_key_file(
                    public_key, public_key_content, 0o644, force
                )

            if self.account_exists(account_name):
                self.config_manager.remove_account(account_name)

            success = self.config_manager.add_account(
                account_name,
                entry.get("name", account_name),
                entry.get("email", ""),
                private_key,
                public_key,
                sign=str(entry.get("sign", "false")).lower() == "true",
            )
            if not success:
                echo_color("r", f'Failed to import account "{account_name}".')
                continue

            for alias, alias_info in entry.get("host_aliases", {}).items():
                if self.ssh_manager.has_host_alias(alias) and not force:
                    continue
                self.ssh_manager.add_host_alias(
                    alias,
                    alias_info.get("hostname", "github.com"),
                    private_key,
                    alias_info.get("user", "git"),
                )

            imported += 1
            echo_color("g", f'Imported account "{account_name}"')

        echo_color("g", f"Import complete: {imported} imported, {skipped} skipped.")
        return True
