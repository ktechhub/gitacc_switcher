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
- Opt-in SSH commit signing per account
- Colored terminal output with active account indicator
- Pre-commit hook to prevent commits with the wrong account
- Opt-in directory-based auto-switching (`gitacc rule`) with a bash/zsh shell hook
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
gitacc switch work --local    # only this repo, leave the global identity alone

# 3. See what's registered (active account is marked with *)
gitacc list

# 4. Prevent wrong-account commits in a repo
gitacc init work              # sets expected account + installs pre-commit hook
gitacc verify                 # manual check
```

## Commands

### `gitacc add [--type TYPE] [--sign]`

Add a new Git account. Prompts for:
- Account identifier (used in key filename and as a reference)
- Git display name (defaults to account identifier)
- Email
- Optional SSH key passphrase

Available key types: `rsa` (default), `ed25519`, `ecdsa`, `ecdsa-sk`, `ed25519-sk`, `dsa`

```bash
gitacc add
gitacc add --type ed25519
gitacc add --sign           # opt in to SSH commit signing for this account
```

Pass `--sign` to opt this account into SSH commit signing. When you later `gitacc switch` to it,
`user.signingkey` is set to the account's public key and `gpg.format=ssh` / `commit.gpgsign=true`
are enabled (locally too, with `--local`), so every commit made under this identity is signed.
Switching to an account without `--sign` clears any signing config left by a previous account.
Toggle it later with `gitacc update <account> --sign` / `--no-sign`.

### `gitacc switch <account> [--local]` / `gitacc <account>`

Switch to a registered account. Clears all keys from the SSH agent, loads only this account's key, and sets `git config --global user.name/email`.

```bash
gitacc switch mywork
gitacc mywork          # shorthand
```

Pass `--local`/`-l` to set the identity for the current repository only (`git config` local scope), leaving the global `user.name`/`user.email` untouched. Must be run from inside a Git repository.

```bash
gitacc switch mywork --local
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

### `gitacc update <account> [--name NAME] [--email EMAIL] [--sign | --no-sign]`

Update the Git display name and/or email for an existing account. Prompts for any field not provided as a flag.

```bash
gitacc update mywork --name "Jane Doe"
gitacc update mywork --email "jane@newcompany.com"
gitacc update mywork   # prompts for both
gitacc update mywork --sign      # enable SSH commit signing for this account
gitacc update mywork --no-sign   # disable it
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

### `gitacc rule add <account> [directory]` / `gitacc rule remove [directory]` / `gitacc rule list`

Opt-in, direnv-style directory-based auto-switching: bind an account to a directory (and
everything beneath it) so the right identity is picked automatically as you move around, instead
of running `gitacc switch` by hand. `directory` defaults to the current directory. The most
specific matching directory wins, so a rule on a subdirectory overrides one on its parent.

```bash
gitacc rule add work ~/projects/work      # anything under ~/projects/work uses "work"
gitacc rule add personal ~/projects/side  # anything under ~/projects/side uses "personal"
gitacc rule list
gitacc rule remove ~/projects/side
```

Rules by themselves don't do anything — nothing triggers on `cd` until you install the shell hook
below.

### `gitacc rule hook <bash|zsh>`

Print a shell snippet that calls `gitacc rule check` so rules apply automatically. Add it to your
shell profile and restart your shell (or `source` it):

```bash
# bash
gitacc rule hook bash >> ~/.bashrc

# zsh
gitacc rule hook zsh >> ~/.zshrc
```

The hook is silent unless it actually needs to switch accounts: no matching rule, an SSH agent
that isn't running, or an identity that's already correct all do nothing. This is entirely
opt-in — `gitacc rule add` alone never touches your shell config.

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
| `~/.gitaccrules` | Directory → account rules for `gitacc rule` (opt-in auto-switch) |
| `~/.ssh/id_<type>_<account>` | Private SSH key per account |
| `~/.ssh/id_<type>_<account>.pub` | Public SSH key per account |

`~/.gitacc` format:

```ini
[mywork]
    name = Jane Doe
    email = jane@company.com
    private_key = /home/jane/.ssh/id_ed25519_mywork
    public_key = /home/jane/.ssh/id_ed25519_mywork.pub
    sign = false
```

`~/.gitaccrules` format (one rule per line, most-specific directory wins):

```
/home/jane/projects/work = work
/home/jane/projects/work/client-a = client-a
```

## Requirements

- Python 3.8+
- Git
- SSH tools (`ssh-keygen`, `ssh-agent`, `ssh-add`) in `PATH`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full history of changes.

Versions and the changelog are generated automatically by [Release Please](https://github.com/googleapis/release-please) from Conventional Commit PR titles on `main` — `feat:` bumps minor, everything else bumps patch, and `!` after the type (e.g. `feat!:`) bumps major. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full commit/branch convention.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, commit conventions, and the PR process.

## License

MIT — see [LICENSE](LICENSE) for details.
