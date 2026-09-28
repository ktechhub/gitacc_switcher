# gitacc-switcher — AI assistant context

A Python CLI (`gitacc`) for managing multiple Git/SSH identities on one machine: generates
per-account SSH keypairs, switches the active SSH-agent key + git config `user.name`/`user.email`,
and can bind a repo to an expected account with a pre-commit hook that blocks commits made under the
wrong identity. Published to PyPI as `gitacc-switcher`.

## Layout

- `gitacc_switcher/cli.py` — argparse entry point / command dispatch
- `gitacc_switcher/account_manager.py` — orchestrates add/update/remove/list of accounts
- `gitacc_switcher/ssh_manager.py` — SSH keygen, ssh-agent interaction
- `gitacc_switcher/config_manager.py` — git config writes + `~/.gitacc` INI store
- `gitacc_switcher/hook_manager.py` — pre-commit hook install/verify
- `gitacc_switcher/completion.py` — bash/zsh completion generation
- `tests/` — one test file per module above

## Commands

```bash
pip install -e .
pip install -r requirements-dev.txt

pytest tests/                        # run tests
pytest --cov=gitacc_switcher tests/  # with coverage
black gitacc_switcher/ tests/        # format (CI checks this — run before opening a PR)
```

## Conventions

- **Formatting**: Black only — no ruff/mypy configured yet.
- **Commit types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
  `chore`, `revert` (enforced on PR titles by `pr-title-check.yaml`).
- **Breaking changes**: add `!` right after the type, before the colon — e.g. `feat!:`, `fix!:`.
  Triggers a major version bump instead of minor/patch.
- **Branch naming**: prefix branches to match their eventual PR type — `feat/<slug>`, `fix/<slug>`,
  `docs/<slug>`, `chore/<slug>`, etc. This is a readability convention only; **the version bump is
  driven entirely by the PR title / squash-merge commit message on `main`, not the branch name** —
  neither `release-please` nor `pr-title-check.yaml` reads branch names.
- **Releases**: automated via `release-please`, triggered by conventional-commit messages landing on
  `main` — don't hand-edit `CHANGELOG.md` version headers; let the release PR do it.
- **Dependencies**: Dependabot already handles version bumps for `pip` and `github-actions` weekly
  (`.github/dependabot.yml`) — don't open PRs that just bump a dependency, that's redundant.
- **Tests required**: every change needs a test. For a bug fix, the test must fail before the fix
  and pass after — never claim a bug exists without a reproducing test.

## Security-sensitive files — extra care required

`ssh_manager.py`, `config_manager.py`, and `hook_manager.py` handle SSH keys, passphrases, and
hook installation into the user's repos. Passphrases are deliberately never passed as CLI args (they
go through a generated, `0o700`-permissioned `SSH_ASKPASS` script with `shlex.quote`) — this is an
intentional mitigation against leaking via the process list; don't "simplify" it. Any change to
these three files should be narrowly scoped to exactly what's being asked, called out explicitly in
the PR description, and treated as needing closer human review than the rest of the codebase.

## Automated weekly maintenance routine

This repo has a scheduled Claude routine that opens one PR per week, sourced from `agent-backlog.md`
in this repo's root — it picks the next `Open` item, implements it, opens a PR, and marks the item
`Claimed` with the PR link. It never invents work outside that file. If you're extending or
debugging that routine, `agent-backlog.md`'s own header documents its exact operating rules (pick
top-down, tests required, never freelance beyond the item's written scope, never autonomously
restructure the three security-sensitive files beyond what an item explicitly describes).

Humans add new ideas to `agent-backlog.md`; the routine only consumes it, never adds to it.
