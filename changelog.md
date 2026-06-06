# Changelog

All notable changes to this project will be documented in this file.

Entries are generated automatically by [Release Please](https://github.com/googleapis/release-please) from [conventional commit](https://www.conventionalcommits.org/) messages.

## [0.1.0] - 2026-06-06

### Features

- Add/remove/switch/list Git accounts with automatic SSH key generation
- Optional SSH key passphrase support (passphrase never exposed in process list)
- `gitacc list` marks the currently active account
- `gitacc update` — update Git name and/or email for an existing account
- `gitacc init` — bind a repository to an account and install a pre-commit hook
- `gitacc verify` — check current account against the repository expectation
- `gitacc logout` — clear the SSH agent and unset global Git config
- Shell autocomplete for bash and zsh (`gitacc autocomplete install`)
- `--version` flag
