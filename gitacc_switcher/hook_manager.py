"""Manage Git hooks for account validation."""

import subprocess
from pathlib import Path
from typing import Optional


class HookManager:
    """Manages Git hooks for account validation."""

    PRE_COMMIT_HOOK_TEMPLATE = """#!/bin/sh
# Git Account Switcher - Pre-commit hook
# This hook prevents commits with the wrong Git account

# Get expected account from git config
EXPECTED_ACCOUNT=$(git config gitacc.expected-account)

if [ -z "$EXPECTED_ACCOUNT" ]; then
    # No expected account set, allow commit
    exit 0
fi

# Get current git config
CURRENT_NAME=$(git config user.name)
CURRENT_EMAIL=$(git config user.email)

# Get expected account info from ~/.gitacc
GITACC_FILE="$HOME/.gitacc"
if [ ! -f "$GITACC_FILE" ]; then
    echo "Error: ~/.gitacc file not found"
    exit 1
fi

# Extract expected name and email from .gitacc
# Use awk for more reliable parsing
EXPECTED_NAME=$(awk -v account="$EXPECTED_ACCOUNT" '
    /^\[/ { 
        # Reset in_section for each new section
        in_section = 0
        # Check if this is the section we want (exact match)
        if ($0 == "[" account "]") {
            in_section = 1
        }
        next
    }
    in_section && /^[[:space:]]*name[[:space:]]*=/ { 
        gsub(/^[^=]*=[[:space:]]*/, "")
        gsub(/[[:space:]]*$/, "")
        print
        exit
    }
' "$GITACC_FILE")

EXPECTED_EMAIL=$(awk -v account="$EXPECTED_ACCOUNT" '
    /^\[/ { 
        # Reset in_section for each new section
        in_section = 0
        # Check if this is the section we want (exact match)
        if ($0 == "[" account "]") {
            in_section = 1
        }
        next
    }
    in_section && /^[[:space:]]*email[[:space:]]*=/ { 
        gsub(/^[^=]*=[[:space:]]*/, "")
        gsub(/[[:space:]]*$/, "")
        print
        exit
    }
' "$GITACC_FILE")

if [ -z "$EXPECTED_NAME" ] || [ -z "$EXPECTED_EMAIL" ]; then
    echo "Error: Account '$EXPECTED_ACCOUNT' not found in ~/.gitacc"
    exit 1
fi

# Check if current config matches expected
if [ "$CURRENT_NAME" != "$EXPECTED_NAME" ] || [ "$CURRENT_EMAIL" != "$EXPECTED_EMAIL" ]; then
    echo ""
    echo "❌ Git Account Mismatch!"
    echo ""
    echo "Expected account: $EXPECTED_ACCOUNT"
    echo "  Name:  $EXPECTED_NAME"
    echo "  Email: $EXPECTED_EMAIL"
    echo ""
    echo "Current Git config:"
    echo "  Name:  $CURRENT_NAME"
    echo "  Email: $CURRENT_EMAIL"
    echo ""
    echo "Please switch to the correct account:"
    echo "  gitacc switch $EXPECTED_ACCOUNT"
    echo ""
    exit 1
fi

exit 0
"""

    def __init__(self):
        pass

    def get_hooks_dir(self, repo_path: Optional[Path] = None) -> Optional[Path]:
        """Get the Git hooks directory for a repository.

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            Path to hooks directory or None if not a Git repo
        """
        if repo_path is None:
            repo_path = Path.cwd()

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            git_dir = Path(result.stdout.strip())
            if not git_dir.is_absolute():
                git_dir = repo_path / git_dir

            hooks_dir = git_dir / "hooks"
            return hooks_dir
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def install_pre_commit_hook(self, repo_path: Optional[Path] = None) -> bool:
        """Install the pre-commit hook for account validation.

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            True if successful, False otherwise
        """
        hooks_dir = self.get_hooks_dir(repo_path)
        if not hooks_dir:
            return False

        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_file = hooks_dir / "pre-commit"

        try:
            with open(hook_file, "w") as f:
                f.write(self.PRE_COMMIT_HOOK_TEMPLATE)

            # Make it executable
            hook_file.chmod(0o755)
            return True
        except Exception:
            return False

    def uninstall_pre_commit_hook(self, repo_path: Optional[Path] = None) -> bool:
        """Uninstall the pre-commit hook.

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            True if successful, False otherwise
        """
        hooks_dir = self.get_hooks_dir(repo_path)
        if not hooks_dir:
            return False

        hook_file = hooks_dir / "pre-commit"

        if not hook_file.exists():
            return True

        try:
            # Check if it's our hook before removing
            with open(hook_file, "r") as f:
                content = f.read()
                if "Git Account Switcher" in content:
                    hook_file.unlink()
                    return True
        except Exception:
            pass

        return False

    def is_hook_installed(self, repo_path: Optional[Path] = None) -> bool:
        """Check if the pre-commit hook is installed.

        Args:
            repo_path: Path to repository (default: current directory)

        Returns:
            True if hook is installed, False otherwise
        """
        hooks_dir = self.get_hooks_dir(repo_path)
        if not hooks_dir:
            return False

        hook_file = hooks_dir / "pre-commit"
        if not hook_file.exists():
            return False

        try:
            with open(hook_file, "r") as f:
                content = f.read()
                return "Git Account Switcher" in content
        except Exception:
            return False
