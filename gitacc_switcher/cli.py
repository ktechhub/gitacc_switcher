"""Main CLI entry point with argparse commands."""

import argparse
import sys
from typing import Optional

try:
    import argcomplete
except ImportError:
    argcomplete = None

from .account_manager import AccountManager
from .completion import get_account_names
from .utils import echo_color, get_ssh_key_types


class CLI:
    """Command-line interface for Git Account Switcher."""

    def __init__(self):
        self.account_manager = AccountManager()
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            prog="gitacc",
            description="Git Account Switcher - Manage multiple Git SSH accounts easily",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_examples(),
        )

        subparsers = parser.add_subparsers(
            dest="command",
            help="Available commands",
            metavar="COMMAND",
        )

        self._add_add_command(subparsers)
        self._add_remove_command(subparsers)
        self._add_switch_command(subparsers)
        self._add_list_command(subparsers)
        self._add_logout_command(subparsers)
        self._add_init_command(subparsers)
        self._add_verify_command(subparsers)
        self._add_update_command(subparsers)
        self._add_autocomplete_command(subparsers)

        return parser

    def _get_examples(self) -> str:
        """Get usage examples string."""
        key_types = ", ".join(get_ssh_key_types())
        return f"""
Examples:
  gitacc add                    Add a new Git account
  gitacc add --type ed25519     Add account with specific SSH key type
                                Available types: {key_types}
  gitacc switch myaccount       Switch to an account
  gitacc myaccount              Switch to an account (short form)
  gitacc remove myaccount       Remove an account
  gitacc list                   List all registered accounts
  gitacc logout                 Logout current account
  gitacc init myaccount         Initialize repo with account validation
  gitacc verify                 Verify current account matches repo
  gitacc update myaccount       Update Git name for an account
        """

    def _add_add_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'add' command parser."""
        parser = subparsers.add_parser(
            "add",
            help="Add a new Git account",
            description="Add a new Git account with SSH key generation",
        )
        parser.add_argument(
            "-t",
            "--type",
            dest="key_type",
            default="rsa",
            choices=get_ssh_key_types(),
            help="SSH key type (default: rsa). Available: dsa, ecdsa, ecdsa-sk, ed25519, ed25519-sk, rsa",
        )
        parser.set_defaults(func=self._handle_add)

    def _add_remove_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'remove' command parser."""
        parser = subparsers.add_parser(
            "remove",
            help="Remove a Git account",
            description="Remove a Git account and its SSH keys",
        )
        account_arg = parser.add_argument(
            "account_name",
            nargs="?",
            help="Account name to remove (will prompt if not provided)",
        )
        if argcomplete:
            account_arg.completer = lambda **kwargs: get_account_names()
        parser.set_defaults(func=self._handle_remove)

    def _add_switch_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'switch' command parser."""
        parser = subparsers.add_parser(
            "switch",
            help="Switch to a Git account",
            description="Switch to a registered Git account",
        )
        account_arg = parser.add_argument(
            "account_name",
            help="Account name to switch to",
        )
        if argcomplete:
            account_arg.completer = lambda **kwargs: get_account_names()
        parser.set_defaults(func=self._handle_switch)

    def _add_list_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'list' command parser."""
        parser = subparsers.add_parser(
            "list",
            help="List all registered accounts",
            description="Display all registered Git accounts",
        )
        parser.set_defaults(func=self._handle_list)

    def _add_logout_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'logout' command parser."""
        parser = subparsers.add_parser(
            "logout",
            help="Logout current Git account",
            description="Logout from the current Git account",
        )
        parser.set_defaults(func=self._handle_logout)

    def _add_init_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'init' command parser."""
        parser = subparsers.add_parser(
            "init",
            help="Initialize repository with account validation",
            description="Set expected account for repository and install pre-commit hook",
        )
        account_arg = parser.add_argument(
            "account_name",
            help="Account name to set as expected for this repository",
        )
        if argcomplete:
            account_arg.completer = lambda **kwargs: get_account_names()
        parser.set_defaults(func=self._handle_init)

    def _add_verify_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'verify' command parser."""
        parser = subparsers.add_parser(
            "verify",
            help="Verify current account matches repository",
            description="Check if current Git account matches the expected account for the repository",
        )
        parser.set_defaults(func=self._handle_verify)

    def _add_update_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'update' command parser."""
        parser = subparsers.add_parser(
            "update",
            help="Update Git name for an account",
            description="Update the Git name (commit author name) for an existing account",
        )
        account_arg = parser.add_argument(
            "account_name",
            help="Account identifier to update",
        )
        parser.add_argument(
            "--name",
            dest="new_git_name",
            help="New Git name (will prompt if not provided)",
        )
        if argcomplete:
            account_arg.completer = lambda **kwargs: get_account_names()
        parser.set_defaults(func=self._handle_update)

    def _add_autocomplete_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'autocomplete' command parser."""
        parser = subparsers.add_parser(
            "autocomplete",
            help="Install shell autocomplete",
            description="Install shell autocomplete for gitacc command",
        )
        subparsers_autocomplete = parser.add_subparsers(
            dest="autocomplete_command",
            help="Autocomplete commands",
        )

        install_parser = subparsers_autocomplete.add_parser(
            "install",
            help="Install autocomplete for your shell",
            description="Install autocomplete for bash/zsh",
        )
        install_parser.set_defaults(func=self._handle_autocomplete_install)

    def _handle_autocomplete_install(self, args: argparse.Namespace) -> int:
        """Handle the 'autocomplete install' command."""
        if not argcomplete:
            echo_color("r", "argcomplete is not installed!")
            echo_color(
                "y",
                "This should have been installed automatically with gitacc-switcher.",
            )
            echo_color("y", "Please reinstall the package:")
            echo_color("b", "  pip install --upgrade gitacc-switcher")
            echo_color("y", "Or if developing locally:")
            echo_color("b", "  pip install -e .")
            return 1

        import os
        import shutil

        shell = os.environ.get("SHELL", "")
        shell_name = os.path.basename(shell) if shell else ""

        if shell_name in ["bash", "zsh"]:
            try:
                # Get the completion script
                completion_script = argcomplete.shellcode(["gitacc"], shell=shell_name)

                # Determine shell config file
                if shell_name == "bash":
                    config_file = os.path.expanduser("~/.bashrc")
                    # Check for .bash_profile on macOS
                    if sys.platform == "darwin" and os.path.exists(
                        os.path.expanduser("~/.bash_profile")
                    ):
                        config_file = os.path.expanduser("~/.bash_profile")
                else:  # zsh
                    config_file = os.path.expanduser("~/.zshrc")

                # Check if already installed
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        if "register-python-argcomplete gitacc" in f.read():
                            echo_color(
                                "y", f"Autocomplete already installed in {config_file}"
                            )
                            echo_color(
                                "y",
                                f"To activate in this session: source {config_file}",
                            )
                            return 0

                # Add to config file
                with open(config_file, "a") as f:
                    f.write("\n# Git Account Switcher autocomplete\n")
                    f.write(completion_script)
                    f.write("\n")

                echo_color("g", f"Autocomplete installed successfully!")
                echo_color("g", f"Added to {config_file}")

                # Try to source it automatically for current shell
                # Note: We can't modify the parent shell, but we can validate and provide instructions
                try:
                    import subprocess

                    # Validate the installation works
                    result = subprocess.run(
                        [shell, "-c", f"source {config_file} && echo 'OK'"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if result.returncode == 0:
                        echo_color("g", "✓ Installation validated!")
                        echo_color(
                            "y",
                            "Autocomplete will work automatically in new shell sessions.",
                        )
                        echo_color(
                            "y", f"To activate in this session: source {config_file}"
                        )
                    else:
                        echo_color("y", f"To activate: source {config_file}")
                except Exception:
                    echo_color("y", f"To activate: source {config_file}")

                return 0

            except Exception as e:
                echo_color("r", f"Failed to install autocomplete: {e}")
                echo_color("y", "You can manually install by running:")
                echo_color("b", f'  eval "$(register-python-argcomplete gitacc)"')
                return 1
        else:
            echo_color("y", f"Shell '{shell_name}' detected.")
            echo_color("y", "Automatic installation is supported for bash and zsh.")
            echo_color("y", "For other shells, run manually:")
            echo_color("b", '  eval "$(register-python-argcomplete gitacc)"')
            return 0

    def _handle_add(self, args: argparse.Namespace) -> int:
        """Handle the 'add' command."""
        success = self.account_manager.add_account(key_type=args.key_type)
        return 0 if success else 1

    def _handle_remove(self, args: argparse.Namespace) -> int:
        """Handle the 'remove' command."""
        success = self.account_manager.remove_account(account_name=args.account_name)
        return 0 if success else 1

    def _handle_switch(self, args: argparse.Namespace) -> int:
        """Handle the 'switch' command."""
        success = self.account_manager.switch_account(args.account_name)
        return 0 if success else 1

    def _handle_list(self, args: argparse.Namespace) -> int:
        """Handle the 'list' command."""
        accounts = self.account_manager.list_accounts_detailed()
        if accounts:
            echo_color("g", "Registered accounts:")
            for account_name, account_info in accounts.items():
                git_name = account_info.get("name", account_name)
                email = account_info.get("email", "N/A")
                if git_name == account_name:
                    print(f"  - {account_name} ({email})")
                else:
                    print(f"  - {account_name} → Git name: {git_name} ({email})")
        else:
            echo_color("y", "No accounts registered yet.")
        return 0

    def _handle_logout(self, args: argparse.Namespace) -> int:
        """Handle the 'logout' command."""
        success = self.account_manager.logout()
        return 0 if success else 1

    def _handle_init(self, args: argparse.Namespace) -> int:
        """Handle the 'init' command."""
        success = self.account_manager.init_repo(args.account_name)
        return 0 if success else 1

    def _handle_verify(self, args: argparse.Namespace) -> int:
        """Handle the 'verify' command."""
        success = self.account_manager.verify_account()
        return 0 if success else 1

    def _handle_update(self, args: argparse.Namespace) -> int:
        """Handle the 'update' command."""
        success = self.account_manager.update_account_git_name(
            args.account_name, args.new_git_name
        )
        return 0 if success else 1

    def _handle_account_name_shortcut(self, account_name: str) -> int:
        """Handle account name as shortcut for switch command."""
        success = self.account_manager.switch_account(account_name)
        return 0 if success else 1

    def run(self) -> int:
        """Run the CLI application.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        args = self.parser.parse_args()

        # Handle account name shortcut (gitacc <account_name>)
        if not args.command and len(sys.argv) > 1:
            account_name = sys.argv[1]
            if account_name not in ["-h", "--help", "--version"]:
                return self._handle_account_name_shortcut(account_name)

        # Handle commands
        if hasattr(args, "func"):
            return args.func(args)

        # No command provided, show help
        self.parser.print_help()
        return 0


def main() -> None:
    """Main entry point for the CLI."""
    cli = CLI()

    # Enable argcomplete if available
    if argcomplete:
        argcomplete.autocomplete(cli.parser)

    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
