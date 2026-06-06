"""Manage SSH keys and SSH agent."""

import os
import shlex
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Optional, Tuple


class SSHManager:
    """Manages SSH key generation and SSH agent operations."""

    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"
        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)

    def generate_ssh_key(
        self,
        key_type: str,
        account_name: str,
        email: str,
        passphrase: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate SSH key pair for an account.

        Args:
            key_type: SSH key type (rsa, ed25519, etc.)
            account_name: Account name (used in key filename)
            email: Email for key comment
            passphrase: Optional passphrase for the key (None for no passphrase)

        Returns:
            Tuple of (private_key_path, public_key_path) or (None, None) on error
        """
        private_key_path = self.ssh_dir / f"id_{key_type}_{account_name}"
        public_key_path = self.ssh_dir / f"id_{key_type}_{account_name}.pub"

        # Check if key already exists
        if private_key_path.exists() or public_key_path.exists():
            return None, None

        try:
            if passphrase:
                # Use SSH_ASKPASS so the passphrase is never exposed in the process list
                fd, askpass_path = tempfile.mkstemp(suffix=".sh")
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(f"#!/bin/sh\nprintf '%s' {shlex.quote(passphrase)}\n")
                    os.chmod(askpass_path, 0o700)
                    env = os.environ.copy()
                    env["SSH_ASKPASS"] = askpass_path
                    env["SSH_ASKPASS_REQUIRE"] = "force"  # OpenSSH 8.4+
                    subprocess.run(
                        ["ssh-keygen", "-t", key_type, "-C", email, "-f", str(private_key_path)],
                        check=True,
                        capture_output=True,
                        env=env,
                        stdin=subprocess.DEVNULL,
                    )
                finally:
                    os.unlink(askpass_path)
            else:
                subprocess.run(
                    [
                        "ssh-keygen", "-t", key_type, "-C", email,
                        "-f", str(private_key_path), "-N", "",
                    ],
                    check=True,
                    capture_output=True,
                )

            return str(private_key_path), str(public_key_path)
        except subprocess.CalledProcessError:
            return None, None

    def overwrite_ssh_key(
        self,
        key_type: str,
        account_name: str,
        email: str,
        passphrase: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Overwrite existing SSH key pair.

        Args:
            key_type: SSH key type
            account_name: Account name
            email: Email for key comment
            passphrase: Optional passphrase for the key (None for no passphrase)

        Returns:
            Tuple of (private_key_path, public_key_path) or (None, None) on error
        """
        private_key_path = self.ssh_dir / f"id_{key_type}_{account_name}"
        public_key_path = self.ssh_dir / f"id_{key_type}_{account_name}.pub"

        # Remove existing keys if they exist
        if private_key_path.exists():
            private_key_path.unlink()
        if public_key_path.exists():
            public_key_path.unlink()

        return self.generate_ssh_key(key_type, account_name, email, passphrase)

    def delete_ssh_key(self, private_key_path: str, public_key_path: str) -> bool:
        """Delete SSH key pair.

        Args:
            private_key_path: Path to private key
            public_key_path: Path to public key

        Returns:
            True if successful, False otherwise
        """
        try:
            private_path = Path(private_key_path)
            public_path = Path(public_key_path)

            if private_path.exists():
                private_path.unlink()
            if public_path.exists():
                public_path.unlink()

            return True
        except Exception:
            return False

    def is_ssh_agent_running(self) -> bool:
        """Check if SSH agent is running.

        Returns:
            True if SSH agent is active, False otherwise
        """
        ssh_auth_sock = os.environ.get("SSH_AUTH_SOCK")
        if not ssh_auth_sock:
            return False

        # Check if the agent is actually responding
        try:
            result = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
            return (
                result.returncode == 0 or result.returncode == 1
            )  # 1 means no keys, but agent is running
        except FileNotFoundError:
            return False

    def kill_ssh_agent(self) -> bool:
        """Kill SSH agent.

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(["ssh-agent", "-k"], capture_output=True)
            if "SSH_AUTH_SOCK" in os.environ:
                del os.environ["SSH_AUTH_SOCK"]
            if "SSH_AGENT_PID" in os.environ:
                del os.environ["SSH_AGENT_PID"]
            return True
        except subprocess.CalledProcessError:
            return False

    def clear_all_keys(self) -> bool:
        """Clear all keys from SSH agent.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove all keys from agent
            subprocess.run(["ssh-add", "-D"], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            # If no keys to remove, that's fine
            return True
        except FileNotFoundError:
            return False

    def add_key_to_agent(self, private_key_path: str) -> Tuple[bool, Optional[str]]:
        """Add SSH key to agent.

        Args:
            private_key_path: Path to private key

        Returns:
            Tuple of (success, error_message). Returns (True, None) on success.
        """
        try:
            result = subprocess.run(
                ["ssh-add", private_key_path],
                capture_output=True,
                text=True,
                check=True,
            )
            return True, None
        except subprocess.CalledProcessError as e:
            error_msg = (
                e.stderr.strip() if e.stderr else "Failed to add key to SSH agent"
            )
            return False, error_msg
        except FileNotFoundError:
            return (
                False,
                "ssh-add command not found. Please ensure SSH tools are installed.",
            )

    def get_public_key_content(self, public_key_path: str) -> Optional[str]:
        """Read public key content.

        Args:
            public_key_path: Path to public key file

        Returns:
            Public key content or None on error
        """
        try:
            with open(public_key_path, "r") as f:
                return f.read().strip()
        except Exception:
            return None
