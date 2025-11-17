"""Account management operations."""

import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from .config_manager import ConfigManager
from .ssh_manager import SSHManager
from .hook_manager import HookManager
from .utils import echo_color, ask_yes_no, validate_ssh_key_type


class AccountManager:
    """Manages Git account operations."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.ssh_manager = SSHManager()
        self.hook_manager = HookManager()

    def add_account(self, key_type: str = "rsa") -> bool:
        """Add a new Git account.

        Args:
            key_type: SSH key type (default: rsa)

        Returns:
            True if successful, False otherwise
        """
        # Validate key type
        if not validate_ssh_key_type(key_type):
            echo_color("r", f"Invalid SSH key type: {key_type}")
            return False

        # Get account info from user
        account_name = input("Enter your git user name: ").strip()
        if not account_name:
            echo_color("r", "Account name cannot be empty!")
            return False

        email = input("Enter your git user mail: ").strip()
        if not email:
            echo_color("r", "Email cannot be empty!")
            return False

        # Check if account already exists
        existing_account = self.config_manager.get_account(account_name)
        overwrite = False

        if existing_account:
            echo_color("r", "Warning: Already have same account name.")
            if ask_yes_no("Do you want to overwrite?"):
                overwrite = True
            else:
                echo_color("y", "Please use another account name.")
                return False

        # Generate SSH keys
        if overwrite:
            # Remove old account entry first
            self.config_manager.remove_account(account_name)
            private_key, public_key = self.ssh_manager.overwrite_ssh_key(
                key_type, account_name, email
            )
        else:
            private_key, public_key = self.ssh_manager.generate_ssh_key(
                key_type, account_name, email
            )

        if not private_key or not public_key:
            echo_color("r", "Failed to generate SSH keys!")
            return False

        # Add to .gitacc file
        success = self.config_manager.add_account(
            account_name, account_name, email, private_key, public_key
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

    def switch_account(self, account_name: str) -> bool:
        """Switch to a Git account.

        Args:
            account_name: Account name to switch to

        Returns:
            True if successful, False otherwise
        """
        # Get account info
        account_info = self.config_manager.get_account(account_name)
        if not account_info:
            echo_color("r", "Wrong: account name!!")
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
        if not self.config_manager.set_git_config(name, email):
            echo_color("r", "Failed to set Git config!")
            return False

        echo_color("g", f'Switched to account "{account_name}" successfully!')
        return True

    def logout(self) -> bool:
        """Logout current Git account.

        Returns:
            True if successful, False otherwise
        """
        if self.ssh_manager.is_ssh_agent_running():
            self.ssh_manager.kill_ssh_agent()

        self.config_manager.unset_git_config()
        echo_color("g", "Logged out successfully!")
        return True

    def list_accounts(self) -> List[str]:
        """List all registered accounts.

        Returns:
            List of account names
        """
        return self.config_manager.list_account_names()

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
