# Git Account Switcher

A Python CLI tool to easily switch between multiple Git SSH accounts. Manage multiple Git accounts with separate SSH keys and switch between them seamlessly.

## Features

- 🔐 Manage multiple Git accounts with separate SSH keys
- 🔄 Switch between accounts easily
- 🔑 Generate SSH keys automatically
- 📝 Store account information securely
- 🎨 Colored terminal output
- 🚀 Cross-platform support (works on Unix/Linux/macOS)
- ✅ **Commit validation** - Prevent commits with the wrong account using pre-commit hooks
- ⌨️ **Shell autocomplete** - Tab completion for commands and account names (bash/zsh)

## Installation

### From PyPI (when published)

```bash
pip install gitacc-switcher
```

### From source

```bash
git clone https://github.com/ktechhub/gitacc_switcher.git
cd gitacc_switcher
pip install .
```

## Usage

### Add a new account

```bash
gitacc add
```

This will prompt you for:
- Git user name (account identifier)
- Git user email

The tool will generate SSH keys automatically and save them to `~/.ssh/`.

**Specify SSH key type:**

```bash
gitacc add --type ed25519
```

Available key types: `dsa`, `ecdsa`, `ecdsa-sk`, `ed25519`, `ed25519-sk`, `rsa` (default)

### Switch to an account

```bash
gitacc switch myaccount
```

Or use the short form:

```bash
gitacc myaccount
```

This will:
- Start SSH agent (if not running)
- Add the account's SSH key to the agent
- Set Git global user.name and user.email

### List all accounts

```bash
gitacc list
```

### Remove an account

```bash
gitacc remove myaccount
```

Or without specifying the account name (will prompt):

```bash
gitacc remove
```

### Logout current account

```bash
gitacc logout
```

This will:
- Kill the SSH agent
- Unset Git global user.name and user.email

### Initialize repository with account validation

```bash
gitacc init myaccount
```

This will:
- Set the expected account for the current repository
- Install a pre-commit hook that prevents commits with the wrong account

**How it works:**
1. Run `gitacc init <account_name>` in your repository
2. The tool sets the expected account and installs a pre-commit hook
3. When you try to commit, the hook checks if your current Git account matches the expected account
4. If it doesn't match, the commit is blocked with a helpful error message

### Verify current account

```bash
gitacc verify
```

Check if your current Git account matches the expected account for the repository. This is useful to verify before committing.

### Shell Autocomplete

Install shell autocomplete for easier command usage:

```bash
gitacc autocomplete install
```

This will automatically detect your shell (bash/zsh) and install autocomplete. After installation, restart your shell or run:

```bash
source ~/.zshrc  # for zsh
# or
source ~/.bashrc  # for bash
```

**What gets completed:**
- Commands: `add`, `remove`, `switch`, `list`, `logout`, `init`, `verify`, `autocomplete`
- Account names: When using `switch`, `remove`, `init`, or the shortcut `gitacc <account>`
- Options: `--type` for `add` command (SSH key types)

**Example:**
```bash
gitacc <TAB>           # Shows all commands and account names
gitacc switch <TAB>    # Shows all registered account names
gitacc remove <TAB>    # Shows all registered account names
gitacc init <TAB>      # Shows all registered account names
```

## File Structure

The tool stores account information in `~/.gitacc` in an INI-like format:

```
[account_name]
    name = account_name
    email = user@example.com
    private_key = /home/user/.ssh/id_rsa_account_name
    public_key = /home/user/.ssh/id_rsa_account_name.pub
```

SSH keys are stored in `~/.ssh/` with the naming pattern:
- Private key: `id_{key_type}_{account_name}`
- Public key: `id_{key_type}_{account_name}.pub`

## Examples

```bash
# Add a new account
gitacc add
# Enter: mywork
# Enter: work@company.com

# Add account with ed25519 key
gitacc add --type ed25519

# Switch to account
gitacc switch mywork
# or
gitacc mywork

# List all accounts
gitacc list

# Remove an account
gitacc remove mywork

# Initialize repository with account validation
gitacc init mywork

# Verify current account matches repository
gitacc verify

# Logout
gitacc logout
```

## Requirements

- Python 3.7+
- Git installed
- SSH tools (ssh-keygen, ssh-agent, ssh-add) available in PATH

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

