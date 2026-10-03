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
- **No AI attribution.** Never add a `Co-Authored-By: Claude …` trailer to a commit, never add
  "Generated with Claude Code" (or any mention of Claude/Anthropic/an AI tool) to a commit message
  or PR description, and never include a `claude.ai/code/session_…` link. This applies to every
  commit and PR this repo receives, including from the automated weekly routine below.

## Security-sensitive files — extra care required

`ssh_manager.py`, `config_manager.py`, and `hook_manager.py` handle SSH keys, passphrases, and
hook installation into the user's repos. Passphrases are deliberately never passed as CLI args (they
go through a generated, `0o700`-permissioned `SSH_ASKPASS` script with `shlex.quote`) — this is an
intentional mitigation against leaking via the process list; don't "simplify" it. Any change to
these three files should be narrowly scoped to exactly what's being asked, called out explicitly in
the PR description, and treated as needing closer human review than the rest of the codebase.

## Automated weekly maintenance routine

This repo has a scheduled Claude routine that opens one PR per week. Its work comes from GitHub
issues labelled `agent-backlog` and `status:available`, not from a file in the repo.

**Picking work:** take the oldest open issue with both labels:

```bash
gh issue list --label agent-backlog --label status:available --state open \
  --json number,title,createdAt --jq 'sort_by(.createdAt) | .[0]'
```

**Operating rules:**

- Pick the first (oldest) issue. Don't skip ahead for an easier one.
- When claiming, switch the label from `status:available` to `status:in-progress` and comment with
  the PR link, in the same PR that does the work. When the PR merges, switch to `status:completed`
  and close the issue.
- Stay inside the issue's "Done looks like" scope. If something seems worth doing but isn't written
  there, open a new issue for a human to prioritise instead of doing it.
- Never add or reprioritise backlog issues. Humans add them; the routine only consumes them.
- Every change needs tests. For a bug fix, the test must fail before the fix and pass after.
- Never autonomously restructure `ssh_manager.py`, `config_manager.py`, or `hook_manager.py` beyond
  what an issue explicitly describes. Call that out in the PR description.
- PR title is `type: description` (Conventional Commits). Add `!` for a breaking change.
- Issues with an external prerequisite the routine cannot do itself (for example, a PyPI
  registration) must say so at the top of the PR description, and the PR must not be treated as safe
  to merge until a human confirms it.
