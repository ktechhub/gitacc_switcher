"""Main CLI entry point with argparse commands."""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import argcomplete
except ImportError:
    argcomplete = None

from . import __version__
from .account_manager import AccountManager
from .completion import get_account_names
from .shell_hook import get_hook_script, get_supported_shells
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
        parser.add_argument(
            "--version", action="version", version=f"%(prog)s {__version__}"
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
        self._add_status_command(subparsers)
        self._add_doctor_command(subparsers)
        self._add_init_command(subparsers)
        self._add_verify_command(subparsers)
        self._add_update_command(subparsers)
        self._add_autocomplete_command(subparsers)
        self._add_rule_command(subparsers)

        # Include account names in top-level completion so `gitacc <TAB>` works for
        # the `gitacc <account>` shorthand, not just for subcommand names.
        if argcomplete:
            subparsers.completer = lambda prefix, **kwargs: (
                list(subparsers.choices.keys()) + get_account_names()
            )

        return parser

    def _get_examples(self) -> str:
        """Get usage examples string."""
        key_types = ", ".join(get_ssh_key_types())
        return f"""
Examples:
  gitacc add                    Add a new Git account
  gitacc add --type ed25519     Add account with specific SSH key type
                                Available types: {key_types}
  gitacc add --sign             Add account with SSH commit signing enabled
  gitacc switch myaccount       Switch to an account
  gitacc switch myaccount -l    Switch to an account for this repo only
  gitacc myaccount              Switch to an account (short form)
  gitacc remove myaccount       Remove an account
  gitacc list                   List all registered accounts
  gitacc logout                 Logout current account
  gitacc status                 Show the currently active account
  gitacc doctor                 Run health checks on the SSH agent and keys
  gitacc init myaccount         Initialize repo with account validation
  gitacc verify                 Verify current account matches repo
  gitacc update myaccount       Update Git name for an account
  gitacc rule add work ~/work   Auto-switch to "work" inside that directory
  gitacc rule hook bash         Print the shell hook (add to ~/.bashrc)
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
        parser.add_argument(
            "--sign",
            dest="sign",
            action="store_true",
            help="Sign commits with this account's SSH key when switched to "
            "(sets user.signingkey, gpg.format=ssh, commit.gpgsign=true)",
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
        parser.add_argument(
            "-l",
            "--local",
            action="store_true",
            help="Set the identity for this repository only, instead of globally",
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

    def _add_status_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'status' command parser."""
        parser = subparsers.add_parser(
            "status",
            help="Show the currently active account",
            description="Show the current Git identity and SSH agent key, "
            "and which managed account (if any) matches",
        )
        parser.set_defaults(func=self._handle_status)

    def _add_doctor_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'doctor' command parser."""
        parser = subparsers.add_parser(
            "doctor",
            help="Run health checks on the SSH agent and managed keys",
            description="Check that the SSH agent is running and reachable, "
            "and that each registered account's key file exists and has "
            "safe permissions. Read-only.",
        )
        parser.set_defaults(func=self._handle_doctor)

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
            help="Update Git name and/or email for an account",
            description="Update the Git name and/or email for an existing account",
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
        parser.add_argument(
            "--email",
            dest="new_email",
            help="New email address (will prompt if not provided)",
        )
        sign_group = parser.add_mutually_exclusive_group()
        sign_group.add_argument(
            "--sign",
            dest="sign",
            action="store_const",
            const=True,
            default=None,
            help="Enable SSH commit signing for this account",
        )
        sign_group.add_argument(
            "--no-sign",
            dest="sign",
            action="store_const",
            const=False,
            help="Disable SSH commit signing for this account",
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

    def _add_rule_command(self, subparsers: argparse._SubParsersAction) -> None:
        """Add the 'rule' command parser for directory-based auto-switching."""
        parser = subparsers.add_parser(
            "rule",
            help="Manage directory-based account auto-switch rules",
            description="Add, remove, and list rules that auto-switch accounts by directory",
        )
        rule_subparsers = parser.add_subparsers(
            dest="rule_command",
            help="Rule commands",
        )

        add_parser = rule_subparsers.add_parser(
            "add",
            help="Add or update a directory rule",
            description="Auto-switch to an account whenever inside the given "
            "directory (or a subdirectory of it)",
        )
        account_arg = add_parser.add_argument(
            "account_name",
            help="Account to switch to",
        )
        add_parser.add_argument(
            "directory",
            nargs="?",
            default=None,
            help="Directory the rule applies to (default: current directory)",
        )
        if argcomplete:
            account_arg.completer = lambda **kwargs: get_account_names()
        add_parser.set_defaults(func=self._handle_rule_add)

        remove_parser = rule_subparsers.add_parser(
            "remove",
            help="Remove a directory rule",
        )
        remove_parser.add_argument(
            "directory",
            nargs="?",
            default=None,
            help="Directory whose rule should be removed (default: current directory)",
        )
        remove_parser.set_defaults(func=self._handle_rule_remove)

        list_parser = rule_subparsers.add_parser(
            "list",
            help="List all directory rules",
        )
        list_parser.set_defaults(func=self._handle_rule_list)

        hook_parser = rule_subparsers.add_parser(
            "hook",
            help="Print a shell hook that auto-switches on directory change",
            description="Print a snippet for your shell profile that calls "
            "'gitacc rule check' so rules apply automatically as you move "
            "between directories",
        )
        hook_parser.add_argument(
            "shell",
            choices=get_supported_shells(),
            help="Shell to generate the hook for",
        )
        hook_parser.set_defaults(func=self._handle_rule_hook)

        check_parser = rule_subparsers.add_parser(
            "check",
            help="Match the current directory against rules (used by the shell hook)",
            description="Intended to be called by the shell hook on every "
            "prompt render, not run directly; silently does nothing unless "
            "the current directory matches a rule for a different account "
            "than the one currently active",
        )
        check_parser.set_defaults(func=self._handle_rule_check)

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
        success = self.account_manager.add_account(
            key_type=args.key_type, sign=getattr(args, "sign", False)
        )
        return 0 if success else 1

    def _handle_remove(self, args: argparse.Namespace) -> int:
        """Handle the 'remove' command."""
        success = self.account_manager.remove_account(account_name=args.account_name)
        return 0 if success else 1

    def _handle_switch(self, args: argparse.Namespace) -> int:
        """Handle the 'switch' command."""
        success = self.account_manager.switch_account(
            args.account_name, local=getattr(args, "local", False)
        )
        return 0 if success else 1

    def _handle_list(self, args: argparse.Namespace) -> int:
        """Handle the 'list' command."""
        accounts = self.account_manager.list_accounts_detailed()
        if not accounts:
            echo_color("y", "No accounts registered yet.")
            return 0

        current_config = self.account_manager.config_manager.get_current_git_config()
        current_name = current_config.get("name")
        current_email = current_config.get("email")

        echo_color("g", "Registered accounts:")
        for account_name, account_info in accounts.items():
            git_name = account_info.get("name", account_name)
            email = account_info.get("email", "N/A")
            is_active = bool(
                current_name
                and current_email
                and git_name == current_name
                and email == current_email
            )
            marker = "*" if is_active else "-"
            label = (
                f"{account_name} → Git name: {git_name}"
                if git_name != account_name
                else account_name
            )
            suffix = " (active)" if is_active else ""
            print(f"  {marker} {label} ({email}){suffix}")

        return 0

    def _handle_logout(self, args: argparse.Namespace) -> int:
        """Handle the 'logout' command."""
        success = self.account_manager.logout()
        return 0 if success else 1

    def _handle_status(self, args: argparse.Namespace) -> int:
        """Handle the 'status' command."""
        status = self.account_manager.get_status()
        name = status.get("name")
        email = status.get("email")

        echo_color("g", "Current Git identity:")
        echo_color("g", f"  Name:  {name or '(not set)'}")
        echo_color("g", f"  Email: {email or '(not set)'}")

        matched_account = status.get("matched_account")
        if matched_account:
            echo_color("g", f'Matched account: "{matched_account}"')
        else:
            echo_color("y", "No managed account matches the current Git identity.")

        if status.get("agent_running"):
            matched_key_account = status.get("matched_key_account")
            if matched_key_account:
                echo_color(
                    "g", f'SSH agent key matches account: "{matched_key_account}"'
                )
            else:
                echo_color("y", "SSH agent key does not match any managed account.")
        else:
            echo_color("y", "SSH agent is not running.")

        return 0

    def _handle_doctor(self, args: argparse.Namespace) -> int:
        """Handle the 'doctor' command."""
        report = self.account_manager.run_doctor()
        all_ok = True

        if report.get("agent_running"):
            echo_color("g", "✓ SSH agent is running and reachable")
        else:
            echo_color("r", "✗ SSH agent is not running or not reachable")
            all_ok = False

        accounts = report.get("accounts", {})
        if not accounts:
            echo_color("y", "No accounts registered yet.")

        for account_name, check in accounts.items():
            if not check.get("exists"):
                echo_color("r", f'✗ Account "{account_name}": key file is missing')
                all_ok = False
            elif not check.get("readable"):
                echo_color("r", f'✗ Account "{account_name}": key file is unreadable')
                all_ok = False
            elif not check.get("permissions_ok"):
                echo_color(
                    "r",
                    f'✗ Account "{account_name}": key file permissions are too '
                    "permissive (should be readable by owner only)",
                )
                all_ok = False
            else:
                echo_color("g", f'✓ Account "{account_name}": key file OK')

        return 0 if all_ok else 1

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
        success = self.account_manager.update_account(
            args.account_name,
            args.new_git_name,
            args.new_email,
            new_sign=getattr(args, "sign", None),
        )
        return 0 if success else 1

    def _handle_rule_add(self, args: argparse.Namespace) -> int:
        """Handle the 'rule add' command."""
        if not self.account_manager.account_exists(args.account_name):
            echo_color("r", f'Account "{args.account_name}" not found!')
            return 1

        directory = Path(args.directory) if args.directory else Path.cwd()
        success = self.account_manager.rules_manager.add_rule(
            directory, args.account_name
        )
        if success:
            resolved = Path(directory).expanduser().resolve()
            echo_color("g", f'Rule added: "{resolved}" → "{args.account_name}"')
        else:
            echo_color("r", "Failed to add rule!")
        return 0 if success else 1

    def _handle_rule_remove(self, args: argparse.Namespace) -> int:
        """Handle the 'rule remove' command."""
        directory = Path(args.directory) if args.directory else Path.cwd()
        success = self.account_manager.rules_manager.remove_rule(directory)
        resolved = Path(directory).expanduser().resolve()
        if success:
            echo_color("g", f'Rule removed for "{resolved}"')
        else:
            echo_color("y", f'No rule was set for "{resolved}"')
        return 0 if success else 1

    def _handle_rule_list(self, args: argparse.Namespace) -> int:
        """Handle the 'rule list' command."""
        rules = self.account_manager.rules_manager.list_rules()
        if not rules:
            echo_color("y", "No directory rules registered yet.")
            return 0

        echo_color("g", "Directory auto-switch rules:")
        for directory, account_name in rules.items():
            print(f"  {directory} → {account_name}")
        return 0

    def _handle_rule_hook(self, args: argparse.Namespace) -> int:
        """Handle the 'rule hook' command."""
        script = get_hook_script(args.shell)
        if not script:
            echo_color("r", f'Unsupported shell: "{args.shell}"')
            return 1
        print(script)
        return 0

    def _handle_rule_check(self, args: argparse.Namespace) -> int:
        """Handle the 'rule check' command.

        Called by the installed shell hook on every prompt render, so it
        must stay quiet unless there is actually something to do: no match,
        an already-correct identity, and a down SSH agent (which
        `switch_account` would otherwise report loudly on every prompt) are
        all silent no-ops.
        """
        account_name = self.account_manager.rules_manager.find_matching_account(
            Path.cwd()
        )
        if not account_name or not self.account_manager.account_exists(account_name):
            return 0

        status = self.account_manager.get_status()
        if status.get("matched_account") == account_name:
            return 0

        if not self.account_manager.ssh_manager.is_ssh_agent_running():
            return 0

        success = self.account_manager.switch_account(account_name)
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
                if not self.account_manager.account_exists(account_name):
                    echo_color("r", f'Unknown command or account: "{account_name}"')
                    self.parser.print_help()
                    return 1
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
