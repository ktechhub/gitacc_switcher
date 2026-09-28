# Contributing

Contributions are welcome! This document covers how to set up your environment, the conventions we follow, and the PR process.

## Development setup

```bash
git clone https://github.com/ktechhub/gitacc_switcher.git
cd gitacc-switcher
python -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

## Running tests

```bash
pytest tests/
```

With coverage:

```bash
pytest --cov=gitacc_switcher tests/
```

## Code style

We use [Black](https://black.readthedocs.io/) for formatting. Before opening a PR:

```bash
black .
```

CI will fail if the code is not formatted.

## Commit message convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit (and PR title, if you squash-merge) must follow this format:

```
type(optional-scope): short description
```

**Allowed types:**

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting only, no code meaning change |
| `refactor` | Code change without feature/fix |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration |
| `chore` | Maintenance (cleanup, config, etc.) |
| `revert` | Revert a previous commit |

**Examples:**

```
feat: add --email flag to update command
fix: passphrase no longer exposed in process list
docs: update README with --version flag
chore: upgrade actions to v4
feat!: remove deprecated --legacy-mode flag
```

**Breaking changes → major bump:** add `!` right after the type (before the colon), e.g. `feat!:`
or `fix!:`. This is equivalent to a `BREAKING CHANGE:` footer in the commit body — either works,
but `!` in the title is the simplest way to do it since the PR title alone drives the version bump
here (see below).

> **Why this matters:** PR titles become commit messages on squash-merge, and [Release Please](https://github.com/googleapis/release-please) reads those commits to auto-generate `CHANGELOG.md` and bump the version. A `feat:` bumps the minor version; a `fix:` (or any other type) bumps the patch; a `!` after the type (or a `BREAKING CHANGE:` footer) bumps the major. **The version bump is determined entirely by the PR title / squash-merge commit message — Release Please and the PR-title-check CI job do not read branch names at all.**

## Branch naming

Prefix your branch with the same type you'll use in the PR title — `feat/<slug>`, `fix/<slug>`,
`docs/<slug>`, `chore/<slug>`, etc. This is a convention for readability and isn't read by any
automation here (the PR title is what actually drives the version bump, per above) — but keeping
branch and PR-title types matching avoids the confusing case of a `fix/` branch landing as a `feat:`
PR or vice versa.

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make your changes and write tests if applicable
3. Run `black .` and `pytest tests/`
4. Open a PR — the title **must** follow the conventional commit format above
5. Fill in the PR template

The PR title is validated automatically by CI. A merge will be blocked if the title is invalid.

## Reporting bugs

Open an issue at [github.com/ktechhub/gitacc_switcher/issues](https://github.com/ktechhub/gitacc_switcher/issues) and include:
- Your OS and Python version
- Steps to reproduce
- Expected vs. actual behaviour
