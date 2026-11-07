"""Manage SSH keys and SSH agent."""

import os
import shlex
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
                        [
                            "ssh-keygen",
                            "-t",
                            key_type,
                            "-C",
                            email,
                            "-f",
                            str(private_key_path),
                        ],
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
                        "ssh-keygen",
                        "-t",
                        key_type,
                        "-C",
                        email,
                        "-f",
                        str(private_key_path),
                        "-N",
                        "",
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

    def get_agent_fingerprints(self) -> List[str]:
        """Get fingerprints of keys currently loaded in the SSH agent.

        Read-only; does not modify the agent.

        Returns:
            List of fingerprint strings (e.g. "SHA256:abc..."). Empty if the
            agent is not running, has no keys loaded, or can't be reached.
        """
        try:
            result = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
        except FileNotFoundError:
            return []

        if result.returncode != 0:
            return []

        fingerprints = []
        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
                fingerprints.append(parts[1])
        return fingerprints

    def get_key_fingerprint(self, public_key_path: str) -> Optional[str]:
        """Get the fingerprint of a public key file.

        Args:
            public_key_path: Path to the public key file

        Returns:
            Fingerprint string (e.g. "SHA256:abc...") or None on error
        """
        try:
            result = subprocess.run(
                ["ssh-keygen", "-lf", str(public_key_path)],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split()
        return parts[1] if len(parts) >= 2 else None

    def check_key_file(self, private_key_path: str) -> Dict[str, bool]:
        """Check a managed private key file's existence, readability, and permissions.

        Read-only; does not modify anything it checks.

        Args:
            private_key_path: Path to the private key file to check

        Returns:
            Dictionary with 'exists', 'readable', and 'permissions_ok' booleans.
            'permissions_ok' is True when the file is not accessible to
            group/other, matching the 0600 mode ssh-keygen gives private keys
            on creation; it is only meaningful when 'exists' and 'readable'
            are both True.
        """
        path = Path(private_key_path)
        if not path.is_file():
            return {"exists": False, "readable": False, "permissions_ok": False}

        if not os.access(path, os.R_OK):
            return {"exists": True, "readable": False, "permissions_ok": False}

        mode = path.stat().st_mode
        permissions_ok = (mode & 0o077) == 0
        return {"exists": True, "readable": True, "permissions_ok": permissions_ok}

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

    def get_ssh_config_path(self) -> Path:
        """Get the path to the user's SSH config file (~/.ssh/config)."""
        return self.ssh_dir / "config"

    @staticmethod
    def _host_alias_markers(host_alias: str) -> Tuple[str, str]:
        """Begin/end marker lines that delimit a managed host-alias block.

        Keyed by host_alias so each alias's block can be found, replaced, or
        removed independently without touching anything else in the file.
        """
        return (
            f"# >>> gitacc-switcher host-alias: {host_alias} >>>",
            f"# <<< gitacc-switcher host-alias: {host_alias} <<<",
        )

    def _build_host_alias_block(
        self, host_alias: str, hostname: str, private_key_path: str, ssh_user: str
    ) -> str:
        start, end = self._host_alias_markers(host_alias)
        lines = [
            start,
            f"Host {host_alias}",
            f"    HostName {hostname}",
            f"    User {ssh_user}",
            f"    IdentityFile {private_key_path}",
            "    IdentitiesOnly yes",
            end,
        ]
        return "\n".join(lines) + "\n"

    def _read_ssh_config(self) -> str:
        config_path = self.get_ssh_config_path()
        if not config_path.exists():
            return ""
        return config_path.read_text()

    def has_host_alias(self, host_alias: str) -> bool:
        """Check whether a managed host-alias block already exists.

        Args:
            host_alias: The `Host` alias to look for (e.g. "github-work")

        Returns:
            True if a gitacc-managed block for this alias is present
        """
        start, _ = self._host_alias_markers(host_alias)
        return start in self._read_ssh_config()

    def add_host_alias(
        self,
        host_alias: str,
        hostname: str,
        private_key_path: str,
        ssh_user: str = "git",
    ) -> bool:
        """Add or update a managed SSH config `Host` alias block.

        Writes a clearly delimited block to ~/.ssh/config pointing the alias
        at the given key, so the user can clone/push via e.g.
        `git@<host_alias>:org/repo` without hand-editing their SSH config.
        Safe to call again for the same alias: only the block between its
        own markers is replaced, leaving the rest of the file untouched.

        Args:
            host_alias: The `Host` alias to create/update (e.g. "github-work")
            hostname: Real host to connect to (e.g. "github.com")
            private_key_path: Path to the account's private SSH key
            ssh_user: SSH user for the connection (default: "git")

        Returns:
            True if successful, False otherwise
        """
        start, end = self._host_alias_markers(host_alias)
        block = self._build_host_alias_block(
            host_alias, hostname, private_key_path, ssh_user
        )
        existing = self._read_ssh_config()

        pattern = re.compile(
            rf"^{re.escape(start)}\n.*?^{re.escape(end)}\n?",
            re.MULTILINE | re.DOTALL,
        )
        if pattern.search(existing):
            new_content = pattern.sub(block, existing, count=1)
        else:
            new_content = existing
            if new_content and not new_content.endswith("\n"):
                new_content += "\n"
            if new_content and not new_content.endswith("\n\n"):
                new_content += "\n"
            new_content += block

        try:
            config_path = self.get_ssh_config_path()
            is_new_file = not config_path.exists()
            config_path.write_text(new_content)
            if is_new_file:
                config_path.chmod(0o600)
            return True
        except OSError:
            return False

    def remove_host_alias(self, host_alias: str) -> bool:
        """Remove a managed SSH config `Host` alias block, if present.

        Only the block delimited by this alias's own markers is removed;
        everything else in ~/.ssh/config is left exactly as it was.

        Args:
            host_alias: The `Host` alias to remove

        Returns:
            True if a block was found and removed, False if none existed or
            on error
        """
        start, end = self._host_alias_markers(host_alias)
        existing = self._read_ssh_config()

        pattern = re.compile(
            rf"\n?^{re.escape(start)}\n.*?^{re.escape(end)}\n?",
            re.MULTILINE | re.DOTALL,
        )
        new_content, count = pattern.subn("", existing)
        if count == 0:
            return False

        try:
            self.get_ssh_config_path().write_text(new_content)
            return True
        except OSError:
            return False

    def list_host_aliases(self) -> Dict[str, Dict[str, str]]:
        """List all gitacc-managed SSH config host aliases.

        Read-only; does not modify anything.

        Returns:
            Dictionary mapping host alias to its hostname, ssh user, and
            identity file path.
        """
        existing = self._read_ssh_config()
        pattern = re.compile(
            r"^# >>> gitacc-switcher host-alias: (?P<alias>.+?) >>>\n"
            r"Host .+?\n"
            r"\s*HostName (?P<hostname>.+?)\n"
            r"\s*User (?P<user>.+?)\n"
            r"\s*IdentityFile (?P<identity>.+?)\n"
            r"\s*IdentitiesOnly yes\n"
            r"# <<< gitacc-switcher host-alias: (?P=alias) <<<",
            re.MULTILINE,
        )

        aliases = {}
        for match in pattern.finditer(existing):
            aliases[match.group("alias")] = {
                "hostname": match.group("hostname"),
                "user": match.group("user"),
                "identity_file": match.group("identity"),
            }
        return aliases
