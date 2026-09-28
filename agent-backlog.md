# Agent backlog

This is the source of work for the weekly automated maintenance routine on this repo. The routine
picks **one open item per run**, implements it, opens a PR, and marks the item `Claimed` with a
link to the PR. It never invents work outside this list — if every item is `Claimed`/`Done`, or the
next unclaimed item genuinely isn't actionable yet, the routine does nothing that week rather than
freelancing. Humans (mainly the repo owner) add new items here as ideas come up; the routine only
consumes, it doesn't add.

## Rules for the routine (read before picking an item)

- Pick the **first `Open` item**, top to bottom. Don't skip around for an "easier" one.
- Update this file's line for that item to `Status: Claimed (PR: <link>)` in the same PR that does
  the work, so the next run doesn't duplicate it.
- Every change needs tests. For a bug fix, write a failing test first, then the fix — never claim a
  bug exists without a reproducing test.
- **Never autonomously edit `gitacc_switcher/ssh_manager.py`, `config_manager.py`, or
  `hook_manager.py`** beyond what an item below explicitly describes for that file. These handle SSH
  keys, passphrases, and hook installation — if an item touches them, keep the diff narrowly scoped
  to exactly what the item says, and call that out explicitly in the PR description for extra
  reviewer attention.
- Stay inside the scope written for the item. If something seems like a good idea but isn't written
  here, don't do it — add it as a new `Open` item instead and let a human decide whether to prioritize it.
- Match existing conventions: Black formatting, one test file per module (see `tests/`), Conventional
  Commit PR titles (enforced by CI), update `CHANGELOG.md` only if release-please doesn't do it
  automatically (check `.github/workflows/release-please.yaml` if unsure).
- **PR title and branch name**: title must be `type: description` (types: `feat`, `fix`, `docs`,
  `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`; add `!` after the type for a
  breaking change, e.g. `feat!:`) — this title is what actually drives the version bump, since
  release-please reads the squash-merge commit message, not the branch name. Still name the branch
  to match, `<type>/<slug>`, for consistency (e.g. `feat/local-config-override`). Almost everything
  in this backlog is a `feat:`; only use `!` if the item explicitly describes a breaking change.

---

## 1. Per-repo (local) config override

**Status:** Claimed (PR: https://github.com/ktechhub/gitacc_switcher/pull/23)

**What:** Add a way to set the git identity for just the current repo (`git config` local scope)
instead of always writing to global scope. Something like `gitacc switch <account> --local`, or a
new `gitacc use <account>` that defaults to local scope while `switch` keeps today's global
behavior — pick whichever fits the existing command naming better after reading `cli.py`.

**Why:** Today, switching accounts changes `user.name`/`user.email` globally, which affects every
other repo on the machine until you switch again. A local-scope option lets someone pin an identity
to one repo without disturbing their global default.

**Files likely involved:** `cli.py` (new flag/subcommand), `config_manager.py` (the function that
currently calls `git config --global` needs a local-scope variant).

**Done looks like:** new flag/command documented in README, unit tests in
`tests/test_config_manager.py` and `tests/test_cli.py` covering both local and global paths.

---

## 2. SSH commit-signing setup

**Status:** Open

**What:** Let an account's config optionally set `user.signingkey` and `gpg.format=ssh` (plus
`commit.gpgsign=true`) using that account's SSH key, since GitHub and GitLab both support SSH-signed
commits now.

**Why:** Users managing multiple identities often want commits signed per-identity too — this is a
natural extension of what the tool already manages (the key), not a new credential type.

**Files likely involved:** `config_manager.py` (git config writes), possibly `account_manager.py`
(whether signing is enabled per account, stored in `~/.gitacc`).

**Done looks like:** an opt-in flag (e.g. `--sign`) on account add/update, config_manager tests
covering the new git config keys, README section explaining it.

---

## 3. `gitacc status` — show the currently active account

**Status:** Open

**What:** A new read-only command that inspects the current global (or local, if #1 lands first)
git config and the currently-loaded SSH agent key, and reports which managed account (if any)
currently matches.

**Why:** It's easy to forget which identity is currently active, especially with multiple accounts.
This is diagnostic only — no writes.

**Files likely involved:** new logic probably in `cli.py` + `config_manager.py`/`ssh_manager.py` for
the read side; no changes needed to how accounts are stored.

**Done looks like:** `gitacc status` prints the active name/email and which account it matches (or
"no managed account matches"), with tests mocking the git config / ssh-agent read.

---

## 4. Directory-based auto-switch

**Status:** Open

**What:** A per-directory rule (e.g. a `.gitaccrc` file, or entries in `~/.gitacc` mapping a path
prefix to an account) that a shell hook can read to auto-switch identity when entering a directory —
similar in spirit to how `direnv` works, but scoped to just the account-switching piece this tool
already does.

**Why:** Manually running `gitacc switch` every time you move between a work and personal project is
the main daily friction this tool doesn't yet solve.

**Files likely involved:** new module for rule storage/lookup, `completion.py` or a new shell-hook
script for the actual `cd` integration (this is the most shell-integration-heavy item on this list —
read how `completion.py` currently generates shell scripts before starting).

**Done looks like:** a documented opt-in shell hook, rule file format, tests for the rule-matching
logic (the shell-hook wiring itself is hard to unit test — cover what's testable in pure Python and
note in the PR what had to be manually verified instead).

---

## 5. `gitacc doctor` — health check

**What:** A diagnostic command checking: SSH agent is running and reachable, each managed key file
exists with correct permissions (matches what `ssh_manager.py` sets on creation), and flags any
account whose key file is missing/unreadable.

**Status:** Open

**Why:** Gives users one command to sanity-check their setup instead of debugging failures manually.

**Files likely involved:** new function(s) in or alongside `ssh_manager.py` for the checks, `cli.py`
for the new subcommand. Read-only — should never modify anything it checks.

**Done looks like:** `gitacc doctor` prints a pass/fail line per check, non-zero exit code if any
check fails, tests covering each check condition (agent down, key missing, bad permissions).

---

## 6. Per-account host aliasing

**Status:** Open

**What:** Let an account optionally manage an SSH config `Host` alias block (e.g. `github-work`)
pointing at the account's key, so the user can clone/push via `git@github-work:org/repo` without
hand-editing `~/.ssh/config`.

**Why:** This is the standard way to support multiple GitHub/GitLab identities over SSH, and it's
adjacent to what `ssh_manager.py` already manages (the key) — right now the user has to wire this up
by hand even though the tool generates the key.

**Files likely involved:** `ssh_manager.py` (writing/removing a managed block in `~/.ssh/config`,
clearly delimited so it never touches unrelated entries the user already has there).

**Done looks like:** managed block uses clear begin/end markers so it's safely add/removable, tests
covering add/update/remove without disturbing surrounding file content, README example of the
resulting alias usage.

---

## 7. `gitacc export` / `gitacc import`

**Status:** Open

**What:** Export account *metadata* (names, emails, key paths, host aliases if #6 lands) to a
portable file, and import it on another machine. Private key material should NOT be included by
default — export should be metadata-only unless the user explicitly opts into including keys, and
if they do, the PR must explain the security tradeoff clearly in its description for reviewer
attention.

**Why:** Setting up multiple accounts again from scratch on a new machine is repetitive.

**Files likely involved:** `account_manager.py`, `config_manager.py` (reading/writing `~/.gitacc`
in a portable format — it may already be close to portable as INI).

**Done looks like:** `gitacc export`/`gitacc import` commands, metadata-only by default, tests for
round-tripping a config through export then import.

---

## 8. Use `core.hooksPath` instead of writing directly into `.git/hooks/`

**Status:** Open

**What:** Change how `gitacc init`'s identity-enforcement hook is installed: instead of writing
directly into `.git/hooks/pre-commit` (which silently overwrites anything already there from
pre-commit-framework, husky, lefthook, etc.), set `core.hooksPath` to a gitacc-managed directory, or
detect an existing hook and chain to it instead of clobbering it.

**Why:** The current approach is a real interoperability problem flagged during a repo review —
it can silently destroy another tool's hook setup with no warning.

**Files likely involved:** `hook_manager.py` — this is the most security/behavior-sensitive item on
this list per the "never autonomously edit" rule above. Keep the diff to exactly this
interoperability fix; don't restructure anything else in this file while in there.

**Done looks like:** `gitacc init` detects an existing hook/hooksPath setup and either chains to it
or clearly warns instead of overwriting silently, tests covering both the empty-hooks-dir case and
the existing-hook case.

---

## 9. Extend `gitacc verify` with a hook-integrity check

**Status:** Open

**Note:** `gitacc verify` **already exists** — today it only checks whether the current git identity
matches the account expected for this repo. This item is about *adding a second, related check* to
that same command, not creating a new one. Read the existing `gitacc verify` implementation in
`cli.py`/`hook_manager.py` first so the addition fits its current output format rather than
duplicating or conflicting with it.

**What:** Add a check to `gitacc verify` for whether the pre-commit hook `gitacc init` installed is
still present and unmodified, warning if something else (another tool, a manual edit) has since
removed or replaced it.

**Why:** Nothing today tells a user their enforcement hook silently stopped working (e.g. because
another tool overwrote it — see item #8, which is a related but separate change to *how* the hook
is installed).

**Files likely involved:** `hook_manager.py` (read-only check logic), `cli.py` (extend the existing
`verify` subcommand's output, don't add a new one).

**Done looks like:** `gitacc verify`'s existing output gains a hook-status line (present/missing/
modified) alongside its current identity check, tests for each state.

---

## 10. Key-age tracking and rotation reminder

**Status:** Open

**What:** Record each key's creation date in `~/.gitacc` when generated, and add a check (in
`gitacc status`/`doctor`, or its own command) that flags keys older than a configurable threshold
(default something reasonable like 12 months). A `gitacc rotate <account>` command regenerates the
key for an account.

**Why:** Basic key-hygiene nudge; the tool already knows when it created each key.

**Files likely involved:** `account_manager.py`/`config_manager.py` (store creation date),
`ssh_manager.py` (rotation = regenerate, reusing existing keygen logic).

**Done looks like:** creation date stored on new key generation (existing accounts without one just
skip the age check rather than erroring), `gitacc rotate` covered by tests reusing the existing
keygen test patterns.

---

## 11. Shell prompt integration

**Status:** Open

**What:** Expose the currently active account (same data `gitacc status`, item #3, computes) in a
form easy to drop into a shell prompt (e.g. a `gitacc prompt` command that just prints the account
name, fast enough to call on every prompt render).

**Why:** Visibility into which identity is active without having to run a full command and read a
sentence of output.

**Files likely involved:** depends on #3 landing first — reuses its detection logic, just adds a
minimal-output mode. `cli.py`.

**Done looks like:** `gitacc prompt` prints just the account name (or nothing if unmatched) with
minimal startup overhead, a README snippet for wiring it into bash/zsh/starship prompts.

---

## 12. `gitacc list --verbose`

**Status:** Open

**What:** Extend the existing list command with a verbose mode showing key fingerprint, last-used
date (if #10's tracking exists, extend it to also track last-used), and any bound hosts (#6).

**Why:** The plain list today probably only shows account names/emails — verbose mode surfaces the
detail useful for auditing your own setup.

**Files likely involved:** `cli.py`, `account_manager.py`.

**Done looks like:** `--verbose` flag on the existing list command, tests for the extra fields
(degrading gracefully for accounts missing optional data like fingerprints/last-used if this is
implemented before #10).

---

## 13. Config self-check for orphaned entries

**Status:** Open

**What:** Detect accounts in `~/.gitacc` whose referenced key file no longer exists on disk (moved,
deleted, or machine changed), and report or offer to clean them up.

**Why:** Prevents `~/.gitacc` from silently accumulating references to keys that no longer work.

**Files likely involved:** `config_manager.py`/`account_manager.py`. Could be folded into `doctor`
(#5) as one more check rather than a fully separate command — read `doctor`'s implementation first
if it's landed by the time this is picked up, and prefer extending it over duplicating logic.

**Done looks like:** orphaned entries are detected and reported (deletion should require explicit
confirmation/flag, never automatic), tests covering the missing-key-file case.

---

## 14. `gitacc init --template`

**Status:** Open

**What:** Let a team define a shareable config template (key algorithm, host alias pattern) that
`gitacc init --template <file>` applies when setting up a new account, so onboarding a new developer
onto a consistent setup doesn't require verbally explaining the conventions.

**Why:** Useful for onboarding at KTechHub specifically — a documented, repeatable setup path.

**Files likely involved:** `account_manager.py` (template application), new template file format
(keep it simple — reuse the existing `~/.gitacc` INI shape rather than inventing a new format).

**Done looks like:** a template file example in the repo (e.g. `examples/team-template.ini`),
`--template` flag, tests for template application.
