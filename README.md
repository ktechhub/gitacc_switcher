# Git Account Switcher

[![CI](https://github.com/ktechhub/gitacc_switcher/actions/workflows/pipeline.yaml/badge.svg)](https://github.com/ktechhub/gitacc_switcher/actions/workflows/pipeline.yaml)
[![PyPI](https://img.shields.io/pypi/v/gitacc-switcher)](https://pypi.org/project/gitacc-switcher/)
[![Python Versions](https://img.shields.io/pypi/pyversions/gitacc-switcher)](https://pypi.org/project/gitacc-switcher/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python CLI tool to easily switch between multiple Git SSH accounts. Manage multiple Git accounts with separate SSH keys and switch between them seamlessly.

## Features

- Manage multiple Git accounts with separate SSH keys
- Switch between accounts easily — one command, no fuss
- Generate SSH keys automatically (rsa, ed25519, ecdsa, and more)
- Optional passphrase support for SSH keys
- Colored terminal output with active account indicator
- Pre-commit hook to prevent commits with the wrong account
- Shell autocomplete for bash and zsh
- Cross-platform support (Linux / macOS)

## Installation

```bash
pip install gitacc-switcher
```

### From source

```bash
git clone https://github.com/ktechhub/gitacc_switcher.git
cd gitacc_switcher
pip install .
```

## Quick start

```bash
# 1. Add your accounts
gitacc add                    # prompts for name, email, optional passphrase
gitacc add --type ed25519     # specify key type

# 2. Switch between them
gitacc switch work            # full form
gitacc work                   # shorthand — same thing

# 3. See what's registered (active account is marked with *)
gitacc list

# 4. Prevent wrong-account commits in a repo
gitacc init work              # sets expected account + installs pre-commit hook
gitacc verify                 # manual check
```

## Commands

### `gitacc add [--type TYPE]`

Add a new Git account. Prompts for:
- Account identifier (used in key filename and as a reference)
- Git display name (defaults to account identifier)
- Email
- Optional SSH key passphrase

Available key types: `rsa` (default), `ed25519`, `ecdsa`, `ecdsa-sk`, `ed25519-sk`, `dsa`

```bash
gitacc add
gitacc add --type ed25519
```

### `gitacc switch <account>` / `gitacc <account>`

Switch to a registered account. Clears all keys from the SSH agent, loads only this account's key, and sets `git config --global user.name/email`.

```bash
gitacc switch mywork
gitacc mywork          # shorthand
```

> The SSH agent must already be running (`eval $(ssh-agent)`). If it isn't, gitacc will tell you.

### `gitacc list`

List all registered accounts. The currently active account (matching global git config) is marked with `*`.

```bash
gitacc list
# Registered accounts:
#   * work → Git name: Jane Doe (jane@company.com) (active)
#   - personal (jane@personal.com)
```

### `gitacc remove [account]`

Remove an account and its SSH keys. Prompts for confirmation.

```bash
gitacc remove mywork
gitacc remove          # prompts for account name
```

### `gitacc update <account> [--name NAME] [--email EMAIL]`

Update the Git display name and/or email for an existing account. Prompts for any field not provided as a flag.

```bash
gitacc update mywork --name "Jane Doe"
gitacc update mywork --email "jane@newcompany.com"
gitacc update mywork   # prompts for both
```

### `gitacc init <account>`

Bind the current repository to an account and install a pre-commit hook. Any commit attempt with a mismatched account will be blocked.

```bash
cd ~/projects/work-repo
gitacc init mywork
```

### `gitacc verify`

Check whether the current Git identity matches the account expected by this repository.

```bash
gitacc verify
```

### `gitacc logout`

Kill the SSH agent and unset the global Git user config.

```bash
gitacc logout
```

### `gitacc autocomplete install`

Install tab-completion for your shell (bash or zsh). After running, restart your shell or `source` your profile.

```bash
gitacc autocomplete install
```

Completions cover: all command names, account names (for `switch`, `remove`, `init`, `update`), and key types (for `add --type`).

### `gitacc --version`

```bash
gitacc --version
# gitacc 0.1.0
```

## How pre-commit validation works

1. `gitacc init mywork` stores `gitacc.expected-account = mywork` in the repo's local git config and writes a pre-commit hook.
2. On every `git commit`, the hook reads `~/.gitacc` and compares the expected account's name/email against the current `git config user.*`.
3. If they don't match, the commit is blocked with a helpful message pointing to `gitacc switch`.

## File layout

| Path | Purpose |
|------|---------|
| `~/.gitacc` | Stores all account entries (INI format) |
| `~/.ssh/id_<type>_<account>` | Private SSH key per account |
| `~/.ssh/id_<type>_<account>.pub` | Public SSH key per account |

`~/.gitacc` format:

```ini
[mywork]
    name = Jane Doe
    email = jane@company.com
    private_key = /home/jane/.ssh/id_ed25519_mywork
    public_key = /home/jane/.ssh/id_ed25519_mywork.pub
```

## Requirements

- Python 3.8+
- Git
- SSH tools (`ssh-keygen`, `ssh-agent`, `ssh-add`) in `PATH`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full history of changes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, commit conventions, and the PR process.

## License

MIT — see [LICENSE](LICENSE) for details.
