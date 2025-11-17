"""Main CLI entry point with argparse commands."""

import argparse
import sys
from typing import Optional

from .account_manager import AccountManager
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

        return parser

    def _get_examples(self) -> str:
        """Get usage examples string."""
        return """
Examples:
  gitacc add                    Add a new Git account
  gitacc add --type ed25519     Add account with specific SSH key type
  gitacc switch myaccount       Switch to an account
  gitacc myaccount              Switch to an account (short form)
  gitacc remove myaccount       Remove an account
  gitacc list                   List all registered accounts
  gitacc logout                 Logout current account
  gitacc init myaccount         Initialize repo with account validation
  gitacc verify                 Verify current account matches repo
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
        parser.add_argument(
            "account_name",
            nargs="?",
            help="Account name to remove (will prompt if not provided)",
        )
        parser.set_defaults(func=self._handle_remove)

    def _add_switch_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'switch' command parser."""
        parser = subparsers.add_parser(
            "switch",
            help="Switch to a Git account",
            description="Switch to a registered Git account",
        )
        parser.add_argument(
            "account_name",
            help="Account name to switch to",
        )
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
        parser.add_argument(
            "account_name",
            help="Account name to set as expected for this repository",
        )
        parser.set_defaults(func=self._handle_init)

    def _add_verify_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'verify' command parser."""
        parser = subparsers.add_parser(
            "verify",
            help="Verify current account matches repository",
            description="Check if current Git account matches the expected account for the repository",
        )
        parser.set_defaults(func=self._handle_verify)

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
        accounts = self.account_manager.list_accounts()
        if accounts:
            echo_color("g", "Registered accounts:")
            for account in accounts:
                print(f"  - {account}")
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
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
