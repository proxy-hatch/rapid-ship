# Doctor and Agent identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** built and merged in PRs #31 to #33. The [plan 4 follow-ups](2026-10-20-plan4-follow-ups.md), built in the same PRs, changed what this plan built: devctl has no `[roster]` table and doctor no Harness sign-in items, `[github] code_owner` names the code owner, each Keychain item's name carries its App's ID, and `rapid-ship app` supports repositories that an organisation owns, with `--import-key` for a developer's own key. The tasks below keep the plan as it was written, apart from the lines that the Follow-ups note below describes; [ARCHITECTURE.md](../../../ARCHITECTURE.md) describes what exists.

**Goal:** Give devctl `doctor`, with `--skills`, and give the owner optional Agent identity: `rapid-ship app`, the App token code and `devctl as`. Move the settings to the re-scope: the escalation list and each App's ID and slug, with `[agents]`, `[linear]`, `[dispatch]` and `[release]` removed and `gate.toml` no longer read.

**Architecture:** A fresh branch from the head of PR #30 (`codex/devctl-check`) brings over only the surviving code of `codex/github-commands` at `901bd43`, copied file by file with `git show 901bd43:<path>`, then reshaped to Spec 1 and the plan index. devctl's source changes only in its template under `rapid_ship/templates/common/tools/devctl/`, and `uv run rapid-ship sync --in-place` vendors it into `tools/devctl/` with `.rapid-ship/kit.lock`. doctor reads this machine, the repository and GitHub (always `GET` with the owner's `gh` sign-in) and changes nothing in the repository; only while Agent identity is on does it read the two Apps, as the Apps. `devctl as` mints one installation token per run from a Keychain key, holds it in memory and hands it to one `gh` or `git push` child only.

**Tech Stack:** Python 3.12+ standard library (`argparse`, `http.client`, `http.server`, `tomllib`, `contextlib`), PyJWT 2.x with its `crypto` extra (devctl only), PyYAML (devctl), `tomli-w` (rapid-ship), git 2.31+, gh, the macOS `security` tool, uv, pytest, Ruff, mypy, import-linter; Docusaurus for the docs site.

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), sections 3 (`rapid-ship app`), 4 (settings files), 6 (`devctl doctor`, Agent identity and `devctl as`), 10 (testing) and 11 (questions). Plan 4 of 6 in the [plan index](2026-10-14-kit-and-setup.md), whose Conventions, Layout, Built interfaces, Shared interfaces and "Plan 4: Doctor and Agent identity" section bind this plan.

**Owner steps:** a step labelled "Owner step" uses the owner's accounts or changes state outside this worktree. The controller never dispatches an Owner step to an implementer subagent, and no agent runs one. Task 10 Steps 1 to 14 (with Step 11a) and the pushes in Task 11 Steps 3 and 5 run only in the owner's own terminal. The implementer works from the owner's recorded output.

**Follow-ups:** the owner descoped running agents across several Providers on 2026-10-20. The [plan 4 follow-ups](2026-10-20-plan4-follow-ups.md) then removed the `[roster]` table, doctor's Harness sign-in items and the branch of `--skills` that probed the Harnesses `[roster]` named. Where this plan built them, one line now says so. After the owner's review of PR #27 on 2026-10-20, `--skills` probes Claude Code alone until another Harness's integration lands, after the PRO-139 spike (the plan index's follow-up 9). #31 dropped the `Harness` alias from `settings.py`. On #32 the codex and agy probes went with their tests (c05e443); Tasks 4 and 6 below still show the probe of all three Harnesses that #32 built first. On #33 the `--skills` sign-in tests keep the claude case alone (2172517), and `SIGN_IN_VARIABLES` names gh and claude alone (3e7ad36).

## Global Constraints

Copied from the plan index and Spec 1; every task's requirements include them.

- Every command in both CLIs is one word followed by arguments (index, Conventions):
  - `rapid-ship init [--stack {python,agnostic}] [--owner LOGIN] [--repository OWNER/NAME] [--name NAME] [--package NAME]`
  - `rapid-ship status [--strict] [--json]`, `rapid-ship sync [--in-place] [--revert PATH]...`
  - `rapid-ship app [--repository OWNER/NAME]` (plan 4)
  - `devctl check [--tier {fast,full}] [--json] [--base REV] [--pr-body PATH]`
  - `devctl doctor [--skills]`, `devctl as {worker,reviewer} push`, `devctl as {worker,reviewer} gh ARGS...` (plan 4)
  - `devctl hook claude pre-tool` (plan 5); each later wiring adds its Harness
- Exit codes in both CLIs: 0 success; 1 a check failed, something is missing, or a request was refused; 2 the command could not run. When both 1 and 2 apply, 2 wins. `KitRefusal` exits 1; `KitError`, `SettingsError`, `RepoError` and `DevctlError` exit 2. Two commands differ, as Spec 1 section 6 says: after it runs `gh` or `git`, `devctl as` returns that tool's exit code; `devctl hook` follows each Harness's hook protocol and exits 1 on an internal error, never 2 (index).
- doctor "exits 0 when everything is ok, 1 when something is missing and 2 when an item could not be checked" (Spec 1 section 6).
- Write tests first. Label offline and simulated tests as such. A blocked or skipped step never counts as passed (index).
- Python 3.12 or later; `uv` runs everything. Settings are TOML, read with `tomllib` (index).
- devctl source is edited only under `rapid_ship/templates/common/tools/devctl/`. Then run `uv run rapid-ship sync --in-place`, which accepts a dirty work tree. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit the vendored copy: `sync` would make it this repository's own, and `tests/test_kit_dogfood.py` fails (index).
- Never cherry-pick a `kit.lock` hunk (index, plan 4 task 1). This plan copies no `.rapid-ship/kit.lock` and no file under `tools/devctl/` from `901bd43`; `sync` writes both.
- devctl starts processes only through `process.run_process`, called through the module (`from devctl import process`). The one other caller is `repo._git` (EX-3). `rapid_ship` never imports devctl, which an import-linter `forbidden` contract enforces (index).
- The Python guardrail settings cover `rapid_ship`, devctl and `tests/`: no `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression carries an `rs-exception` marker and an entry (index).
- `uv run pytest` and `./devctl check --tier full` need network access and gitleaks 8.30.1 on `PATH` (index).
- The Kit version is the rapid-ship package version. Each Kit release is a tag `v<version>` on `main`, created by the owner. Run `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<version> rapid-ship <command>`, or `--from <local checkout>` before the first tag. PyPI publishing is a later, separate change (index).
- devctl depends only on PyYAML (`pyyaml>=6.0.3,<7`, plan 3) and `PyJWT[crypto]>=2.10,<3` (plan 4). The root dev group adds the same two, plus `types-pyyaml`, so `tests/devctl` can import devctl. The rapid-ship CLI depends only on `tomli-w` (index, Layout).
- Never write a GitHub App private key or token to disk, a command line or output (AGENTS.md, Safety). "No key or token is written to disk, put on a command line or printed" (Spec 1 section 6).
- A token lives in memory only, one per command. `gh` receives it only as `GH_TOKEN` in its own environment, with `GH_REPO`; git receives it only through `devctl/github/askpass.py`, which reads `RAPID_SHIP_GIT_TOKEN` (index, Agent identity).
- `rapid_ship/github_app.py` keeps its own `KEYCHAIN_SERVICE` and `APP_PERMISSIONS`, because `rapid_ship` cannot import devctl. A parity test keeps them equal to devctl's (index).
- "doctor changes nothing in the repository." "It reads GitHub with the owner's `gh` sign-in, always as `GET`." (Spec 1 section 6.) The follow-ups removed the Harness sign-in items after the owner descoped several Providers.
- "devctl never starts an agent to do work, never tracks or resumes one, and never talks to the issue tracker. Only `doctor --skills` starts a short headless Session, to check which skills a Harness loads." (Spec 1 section 6.)
- Settings files: "None of these holds a secret. All are in the Protected set. devctl rejects an unknown key, so a typo cannot silently keep a default." (Spec 1 section 4.)
- Plan 4 removes `GateSettings`, `load_gate`, `Mode`, `CheckContext.gate` and `release_method`. `[agents]`, `[linear]`, `[dispatch]` and `[release]` become unknown keys, which are errors; the message names what replaced each (index).
- "GitHub is the only supported remote." "The owner's machine must run macOS for now: Agent identity keeps its App keys in the macOS Keychain." (Spec 1 section 1.)
- A live trial is an Owner step: the plan names what to run and what to record under `docs/trials/`, and the owner runs or approves each external write (index). In this plan the owner runs each one (Owner steps, above). Record an external operation before sending it. Resolve an uncertain result before retrying (AGENTS.md, Safety).
- Each plan's last task runs `./devctl check`, builds the docs site with `npm --prefix website run build`, and records the actual results in the plan (index).
- A review applies to one head commit. A Worker's own report is not independent verification (AGENTS.md, Safety). This plan is one worktree, one branch and one PR, reviewed and fixed before it merges.
- Ruff skips `rapid_ship/templates/` unless a path is named. After editing a devctl template, run `uv run ruff format <template files>` and `uv run ruff check <template files>` on the files you changed, then sync; the vendored copy is linted, formatted and type-checked by `./devctl check`.
- Commit trailer: each commit command below ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, the trailer of the model that wrote this plan. An implementer of another model writes its own model's trailer line in its place, in the form `Co-Authored-By: <the model that writes the commit>`.

## Review Focus

The five failure modes most likely to bite a person using this software that Spec 1 implies but does not spell out, most likely first. Each line names the test that pins it.

1. **A token or key leaks.** Paths: gh's argv or output, a git argv, a file, exception text, the caller's `GIT_TRACE*`, a repository hook, an HTTP redirect, or a gh command that prints or reuses its token (`gh auth`, `gh alias`, `gh extension`). Expected: none sees the token, and a refused gh command mints none. Pinned by Task 3's copied `test_redirects_are_not_followed`, `test_repository_hooks_do_not_run_with_the_token`, `test_git_tracing_from_the_callers_environment_is_dropped` and `test_token_is_never_an_argument`, and by Task 8's `test_gh_runs_as_the_worker_app_with_the_token_only_in_its_environment`, `test_the_push_token_is_never_an_argument_or_in_a_file`, `test_a_token_the_tool_prints_is_hidden` and `test_gh_refusals_mint_no_token_and_start_no_gh`.
2. **`devctl as worker push` lands somewhere it should not, or overwrites.** Inputs: a diverged remote branch, the default branch, a detached `HEAD`, extra arguments such as `--force` or `+branch`, the Reviewer role, and an `insteadOf` or `pushInsteadOf` rule that rewrites the remote. Expected: a non-fast-forward push fails with git's own exit code and changes nothing; every other case is refused before git runs. Pinned by Task 8's `test_push_never_forces`, `test_push_refuses_the_default_branch`, `test_push_refusals_mint_no_token` and `test_a_detached_head_is_refused_before_a_token_is_minted`, and Task 3's copied `test_rewritten_remote_url_is_refused`.
3. **Settings that look valid but are not.** Inputs: one App recorded without the other, an ID without its slug, Apps without `repository`, an old `[agents]`, `[linear]`, `[dispatch]` or `[release]` table, and a recorded slug that is not the installed App's. Expected: `load_project` refuses each with a message that names the fix, and doctor reports a slug mismatch as missing, because Spec 3 finds agent pull requests by that slug. Pinned by Task 2's `test_invalid_settings_raise_settings_error` and `test_a_removed_table_names_what_replaced_it`, and Task 5's `test_an_installed_app_whose_slug_differs_from_the_record_is_missing`.
4. **doctor reports more than it proved, or leaves something behind.** Inputs: a Session that fails, hangs, writes files or locks its worktree, a ruleset that fits one Mode but not the current one, and Agent identity turned off. Expected: a Session that fails or never finishes is unknown; the `--skills` worktree is removed in every case; the relaxed ruleset is ok only for Flight without Agent identity; no App is read while Agent identity is off. Pinned by Task 5's `test_doctor_calls_the_relaxed_ruleset_ok_only_in_flight_without_agent_identity` and `test_agent_identity_off_has_no_app_items_and_asks_github_nothing`, and Task 6's `test_the_worktree_is_removed_when_a_session_fails`, `test_a_session_that_writes_files_and_locks_its_worktree_still_has_it_removed` and `test_a_session_that_never_finishes_is_unknown_and_its_worktree_is_removed`.
5. **`devctl as` reports success it cannot vouch for.** Inputs: gh output over the 1 MiB capture cap, a gh that never finishes, a gh that is not installed, a missing Keychain item, and a GitHub answer with no default branch. Expected: exit 2 with a message that says what happened, never a silent 0; a cut output still names gh's own exit code. Pinned by Task 8's `test_gh_output_that_was_cut_exits_2_and_says_so`, `test_a_gh_that_never_finishes_exits_2`, `test_a_gh_that_cannot_start_exits_2`, `test_a_missing_key_exits_2_before_any_tool_runs` and `test_a_default_branch_github_cannot_name_exits_2_without_a_push`.

---

## File Structure

Paths under `devctl/` mean the template `rapid_ship/templates/common/tools/devctl/devctl/`; `sync` writes each one's vendored copy under `tools/devctl/devctl/`.

| File | Change | Responsibility |
| --- | --- | --- |
| `devctl/process.py` | Modify (Task 1) | `first_line`, and `_kill_group` probing after a refused SIGTERM |
| `devctl/settings.py` | Rewrite (Task 2) | `Role`, `ROLES`, `App`, `Escalation`, `ProjectSettings` with `agent_identity`, `REMOVED_TABLES`, `load_project`, `load_exceptions` |
| `devctl/check/steps.py`, `devctl/check/diff.py`, `devctl/cli.py` | Modify (Task 2) | `CheckContext` loses `gate`; the `diff` step loses its Flight note |
| `rapid_ship/templates/{python,agnostic}/.rapid-ship/project.toml`, `.rapid-ship/project.toml` | Rewrite (Task 2) | `[github]` App IDs and slugs, `[escalation]` |
| `rapid_ship/templates/common/.rapid-ship/gate.toml`, `.rapid-ship/gate.toml` | Delete (Task 2) | Nothing reads `gate.toml` any more |
| `rapid_ship/templates/kit.toml` | Modify (Tasks 2, 3) | Drop the `gate.toml` seed; make `askpass.py` executable |
| `devctl/github/__init__.py`, `api.py`, `askpass.py` | Copy, trimming `api.py` (Task 3) | The redirect-free REST client, without pagination, and the `GIT_ASKPASS` helper |
| `devctl/github/app.py` | Copy and trim (Task 3) | Keychain keys, App JWTs, installation tokens, `GitHubAccess`, `run_guarded`, token-bearing `run_git` |
| `devctl/check/kit.py` | Copy (Tasks 3, 4) | `rapid_ship_command`, then `kit_summary` for doctor |
| `devctl/check/stacks/python.py` | Copy (Task 4) | `guardrail_gaps`, the Python floor that doctor checks |
| `devctl/harness.py` | Copy and edit (Task 4) | Probe models, each Harness's skills prompt and parser; follow-up 9 kept Claude Code's alone |
| `devctl/doctor_items.py` | Write (Task 4) | Item types, `DoctorContext`, `gh_get`. The follow-ups removed `doctor_signin.py`, the Harness sign-in items, after the owner descoped several Providers |
| `devctl/doctor_local.py` | Copy and edit (Task 4) | Toolchain, guardrails and Kit items, without the Linear item |
| `devctl/doctor.py` | Write (Task 4), modify (Tasks 5, 6) | Runs the items, prints them, exits with the worst answer; `register` |
| `devctl/doctor_rules.py`, `doctor_github.py` | Write (Task 5) | The ruleset and CODEOWNERS for the Mode and Agent identity; App items only while it is on |
| `devctl/doctor_skills.py` | Write (Task 6) | `probe_worktree` at `HEAD` in a temporary directory, and the `--skills` items |
| `rapid_ship/github_app.py`, `rapid_ship/cli.py` | Copy and edit (Task 7) | `rapid-ship app`, printing each App's ID and slug as `[github]` lines |
| `devctl/identity.py` | Write (Task 8) | `devctl as`: `push` and `gh` as an App, every refusal |
| `tools/devctl/pyproject.toml`, `uv.lock` (template), root `pyproject.toml`, `uv.lock` | Modify (Task 3) | PyJWT |
| `tests/devctl/github_fakes.py`, `github_fixtures.py`, `tests/conftest.py` | Write (Task 3), extend (Tasks 4, 5) | Simulated GitHub, Keychain, bare remote, fake Harnesses and doctor contexts |
| `tests/devctl/test_devctl_*.py`, `tests/devctl/fixtures/github/`, `tests/test_kit_app*.py` | Write or copy (Tasks 1 to 8) | One file per area, as each task lists |
| Root `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `rapid_ship/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `docs/trials/` | Modify (Tasks 2, 9, 10) | Guides, the architecture page, the front page and the trial record |
| Spec 1, the plan index and the rapid-ship design | Modify (Tasks 9, 10, 11) | Status lines that say which plans are built; the approval count; plan 4's row |

Not brought over from `901bd43`: `dispatch.py`, `claims.py`, `claim_status.py`, `release.py`, `records.py`, `pr.py`, `review.py`, `merge.py`, `worktrees.py` (only its `probe_worktree` survives, rewritten in `doctor_skills.py`), app.py's Claim-only git helpers (`PushOutcome` to `default_head`), `GitHubApi.paginate`, `app_slug` and `GitHubAccess.slug`, which only those commands called, and their tests.

## Rulings

Where the old code, Spec 1 and the index differ, this plan follows the index and Spec 1:

1. **Roles.** The old `AppRole` becomes the index's `Role` from `devctl.settings`; the old `Agent` pair `worker`/`reviewer` goes. The follow-ups removed the `[roster]` table that first replaced it, after the owner descoped several Providers.
2. **Sign-ins.** The follow-ups removed doctor's Harness sign-in items after the owner descoped several Providers.
3. **`doctor --skills`.** The old code fetched the default branch as the Worker App into a worktree under `worktree_root`. Spec 1 section 6 and the index want a detached worktree at `HEAD` in a temporary directory with the owner's git and no App fetch, so `probe_worktree(repo)` takes no setting and no start. Removal is forced twice, so a Session's lock cannot keep the worktree.
4. **App items.** They move to the index's area `agent identity` and appear only while Agent identity is on. Each installation item also compares GitHub's `app_slug` with the recorded slug, because Spec 3 relies on it; Task 10 confirms the field live.
5. **Ruleset.** `ruleset_problems` takes `every_pr` and `agent_identity`. Walk and Flight with Agent identity need the whole ruleset with an approval count of at least 1 until Task 10 settles it. Flight without Agent identity also accepts the ruleset without its review requirement: no approval, no code-owner review and no last-push approval (index, Ruleset).
6. **`rapid-ship app`.** It prints `worker_app_id`, `worker_app_slug`, `reviewer_app_id` and `reviewer_app_slug` lines under each App, so `rs-setup` records them verbatim, and stays within the 500-line source cap.
7. **`devctl as`.** Its token is minted only after every refusal that needs no GitHub. `push` reads the default branch with the Worker App's token, because the refusal needs it. gh's and git's output is relayed with the token hidden; a timeout or cut output exits 2.

## Checked facts

Rows marked "old plan" were checked on 2026-10-14 and are recorded in the [GitHub commands plan](https://github.com/proxy-hatch/rapid-ship/blob/928fbe493977ae41d2012e19baff3e861fd5b0e8/docs/superpowers/plans/2026-10-14-github-commands.md#checked-facts), the old plan 4, since deleted; Task 10 rechecks the live ones.

| Fact | Source |
| --- | --- |
| `GET /repos/{o}/{r}/installation` and `POST /app/installations/{id}/access_tokens` need an App JWT: RS256, `iat` 60 s in the past, `exp` at most 10 minutes ahead, `iss` the App ID. The token request takes `repositories` and `permissions`. Tokens last one hour. PyJWT needs `iss` as a string. | Old plan |
| The installation object that `GET /repos/{o}/{r}/installation` returns carries `id`, `app_id`, `app_slug` and `permissions`. | GitHub REST "Get a repository installation for the authenticated app"; not observed here, so Task 10 Step 5 records it |
| `security find-generic-password -w` prints a PEM as lowercase hex; a missing item exits 44; `security -i` reads 4096-byte lines from stdin. An item `security` wrote trusts `security`, so reads show no dialog. | Old plan |
| `-c credential.helper=` clears every configured helper; `-c http.<exact url>.extraHeader=` clears generic and URL-scoped headers; `git push <url>` applies `pushInsteadOf`, which `--get-url` does not show. | Old plan, observed with git 2.39.5 |
| `git symbolic-ref --quiet --short HEAD` exits 1 on a detached `HEAD`. `git worktree remove --force` refuses a locked worktree and `--force --force` removes it. `git worktree add --detach <path> HEAD` in a repository with no commit fails with `invalid reference: HEAD`. | Observed with git 2.39.5 on 2026-10-16 |
| An argparse positional with `nargs=argparse.REMAINDER` after two `choices` positionals collects every later argument, `-h`, `--help`, `--force` and `--` included. | Observed on Python 3.12.10, 3.13.12 and 3.14.3 on 2026-10-16 |
| gh uses `GH_TOKEN` for github.com ahead of its stored sign-in, and `GH_REPO` names the repository for commands run outside a clone; `GH_PROMPT_DISABLED` stops prompts. | `gh help environment`; Task 10 Step 10 records the author of a PR opened through `devctl as` |
| GitHub rejects an App-token push that creates or updates a file under `.github/workflows/` without the Workflows permission, with `refusing to allow a GitHub App to create or update workflow`. | Old plan; Task 10 Step 12 records the live message |
| On a GitHub Free private repository, `GET …/rulesets` returns 403 "Upgrade to GitHub Pro or make this repository public to enable this feature." | Old plan, observed on 18 private repositories |
| `PROBE_MODELS`, the cheapest model for each Harness's probe: `haiku` for Claude Code, which ran as `claude-haiku-4-5-20251001` (Claude Code 2.1.287); `gpt-6-luna` for Codex, which `codex debug models --bundled` describes as its fast and affordable model, with `low` its lowest reasoning level (codex-cli 0.162.0); and `gemini-3.8-flash-low` for agy, the Flash model at the lowest effort that `agy models` lists (agy 1.3.4). No Harness lists prices. Follow-up 9 kept Claude Code's alone, as `PROBE_MODEL`. | Old plan; Task 10 Step 13 confirms or corrects `PROBE_MODEL` |
| Ruff formats and checks a file under `rapid_ship/templates/` when the path is named, although `extend-exclude` skips the directory otherwise. | Observed with this repository's Ruff on 2026-10-16 |
| Ruff 0.17.0, on #30's lock, formats code blocks fenced as `python` inside Markdown files, so `ruff format --check .` fails on a document whose fragments or one-line stubs are not in Ruff's layout. `<!-- fmt:off -->` on the line before such a block and `<!-- fmt:on -->` on the line after it leave the block as written, and the docs site, which reads Markdown as CommonMark, still builds. | Observed on a scratch copy of #30's head on 2026-10-16 |
| Tasks 1 to 8, applied from this plan's text to a scratch copy of `98f0be1`, pass every `./devctl check --tier full` step once the PR body declares the three tests the re-scope removed (Task 11). | Dry run on 2026-10-16, offline except for the package index and gitleaks; no GitHub, Keychain or Harness was used. This document was not in that copy; Task 1 Step 6 checks its format |

### Task 1: The branch and the two `process.py` fixes

`98082fb` adds `process.first_line`, and `de800ae` lets `run_process` finish when macOS refuses SIGTERM to a group whose members exited. Neither cherry-picks onto #30: both carry `kit.lock` hunks for other hashes, and `98082fb` also edits `github/app.py` and `worktrees.py`. At `901bd43`, `process.py` and `tests/devctl/test_devctl_process.py` differ from #30 only by these two commits, so this task copies both files whole.

**Files:**
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/process.py` (vendored by `sync`)
- Test: `tests/devctl/test_devctl_process.py`

**Interfaces:**
- Consumes: `process.run_process`, `ProcessResult`, `MAX_OUTPUT_BYTES` (index, Built interfaces).
- Produces: `process.first_line(text: str) -> str`, the first line of the stripped text cut to 300 characters, which every later task uses to quote a tool's stderr.

- [ ] **Step 1: Make the worktree and check the baseline**

Run from the main checkout of `proxy-hatch/rapid-ship`. The three `git cat-file` commands stop the task if #30's head does not yet hold the re-scope, or if `901bd43` is not in this clone. `codex/github-commands` was never pushed, so no fetch can bring `901bd43`: it exists only in the main checkout, whose worktrees share its objects.

```sh
git fetch origin
git cat-file -e origin/codex/devctl-check:docs/adr/0004-team-management-boundary.md
! git cat-file -e origin/codex/devctl-check:docs/superpowers/specs/2026-10-15-walk-flow-design.md
git cat-file -e '901bd43^{commit}'
git worktree add .worktrees/doctor-agent-identity -b doctor-agent-identity origin/codex/devctl-check
cd .worktrees/doctor-agent-identity
uv sync --locked
git config core.hooksPath .githooks
gitleaks version
./devctl check --base origin/codex/devctl-check
uv run rapid-ship status --strict
```

This branch stacks on #30, so every full-tier run names #30's head as its base; without `--base`, the `diff` step compares with `origin/main` and reports the tests that plans 1 to 3 removed, as plan 3's record shows.

Expected: every `git cat-file` exits 0, `gitleaks version` prints `8.30.1`, and both checks exit 0. Every later command runs from this worktree. If a check fails, stop: this plan cannot show its own changes are safe against a red baseline.

This plan lives at `docs/superpowers/plans/2026-10-16-doctor-and-agent-identity.md`, where Task 11 records its results. If #30's head lacks it, copy this document there now; Step 6 commits it. Ruff formats the `python` code blocks of a Markdown file (Checked facts), so each fragment or stub block that is not in Ruff's layout sits between `<!-- fmt:off -->` and `<!-- fmt:on -->` lines. Keep those lines when you edit the plan, and add them around any such block you add.

- [ ] **Step 2: Copy the tests**

```sh
git show 901bd43:tests/devctl/test_devctl_process.py > tests/devctl/test_devctl_process.py
```

The copy imports `first_line` and adds `test_term_denial_is_ignored_only_after_group_disappears`, a `sig` parameter on `test_kill_denial_for_existing_group_remains_an_error` so it runs for SIGTERM and SIGKILL, and `test_first_line_is_the_first_line_of_the_stripped_text`, `test_first_line_of_nothing_is_empty` and `test_first_line_is_cut_to_300_characters`.

- [ ] **Step 3: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_process.py -q`
Expected: collection fails with `ImportError: cannot import name 'first_line' from 'devctl.process'`.

- [ ] **Step 4: Copy the fixed runner and vendor it**

```sh
git show 901bd43:rapid_ship/templates/common/tools/devctl/devctl/process.py > rapid_ship/templates/common/tools/devctl/devctl/process.py
uv run rapid-ship sync --in-place
```

The copy adds this function after `safe_environment`:

```python
def first_line(text: str) -> str:
    """The first line of text, cut to 300 characters: what a message quotes of a tool's stderr."""
    lines = text.strip().splitlines()
    return lines[0][:300] if lines else ""
```

and makes `_kill_group` probe for the group after any refused signal, not only SIGKILL:

```python
def _kill_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError as denied:
        # Darwin reports EPERM for a group whose members have exited but are not yet reaped:
        # a TERM-killed group, or a child that outlived its leader, as git upload-pack outlives
        # a failed fetch from a local repository. Probe existence only; never repeat the
        # signal or accept a persistent denial.
        deadline = time.monotonic() + 0.05
        while True:
            try:
                os.killpg(pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise denied from None
                time.sleep(0.001)
            else:
                raise denied from None
```

Expected: `sync` reports `tools/devctl/devctl/process.py` replaced.

- [ ] **Step 5: Run the tests and see them pass**

Run: `uv run pytest tests/devctl/test_devctl_process.py -q && uv run rapid-ship status --strict`
Expected: 23 passed; status exits 0 with every managed file unchanged.

- [ ] **Step 6: Commit**

```sh
uv run ruff format --check docs/superpowers/plans/2026-10-16-doctor-and-agent-identity.md
git add rapid_ship/templates/common/tools/devctl/devctl/process.py tools/devctl/devctl/process.py .rapid-ship/kit.lock tests/devctl/test_devctl_process.py docs/superpowers/plans/2026-10-16-doctor-and-agent-identity.md
git commit -m "fix: let run_process finish when macOS refuses SIGTERM, and share first_line" -m "Brings over 98082fb and de800ae from codex/github-commands by hand: both commits carry kit.lock hunks for other hashes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: Ruff reports the plan `already formatted`, and the pre-commit hook's fast tier passes, `format` included. If Ruff would reformat the plan, a `python` block lost its `<!-- fmt:off -->` lines: restore them, never run `ruff format` on the plan, which rewrites the fragments so they no longer match the text they replace.

### Task 2: Settings for the escalation list and the Apps

`project.toml` gains each App's slug and `[escalation]`, and loses `[agents]`, `[linear]`, `[dispatch]` and `[release]`. The follow-ups removed the optional `[roster]` table that this task also added, after the owner descoped several Providers. `gate.toml` is no longer seeded or read, so `CheckContext` loses `gate` and the `diff` step loses its Flight note: whether a declared removal goes to the owner is the escalation list's business (Spec 1 section 5).

**Files:**
- Rewrite: `rapid_ship/templates/common/tools/devctl/devctl/settings.py`
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/check/steps.py`, `check/diff.py`, `cli.py`; `rapid_ship/templates/kit.toml`
- Rewrite: `rapid_ship/templates/python/.rapid-ship/project.toml`, `rapid_ship/templates/agnostic/.rapid-ship/project.toml`, `.rapid-ship/project.toml` (this repository's, seeded, so edited in place)
- Delete: `rapid_ship/templates/common/.rapid-ship/gate.toml`, `.rapid-ship/gate.toml`
- Modify: root `AGENTS.md` (its link to `gate.toml`)
- Test: `tests/devctl/test_devctl_settings.py` (rewrite), `tests/devctl/check_workspace.py`, `tests/devctl/test_devctl_diff_removed_tests.py`, `tests/devctl/test_devctl_check_cli.py`, `tests/devctl/test_devctl_cli.py`, `tests/test_kit_contents.py`

**Interfaces:**
- Consumes: `_Table`, `_read`, `_inside_repository`, `_exclude_paths` and `load_exceptions`, unchanged from plan 3.
- Produces (the index's Settings section, exactly):

```python
Role = Literal["worker", "reviewer"]
ROLES: tuple[Role, ...] = ("worker", "reviewer")
REMOVED_TABLES: dict[str, str]  # "agents", "dispatch", "linear", "release" -> what replaced each


@dataclass(frozen=True)
class App:
    id: int
    slug: str


@dataclass(frozen=True)
class Escalation:
    every_pr: bool  # default True
    kinds: tuple[str, ...]  # default ()
    revision_rounds: int  # default 3, at least 1


@dataclass(frozen=True)
class ProjectSettings:
    stack: Stack
    repository: str | None
    worker_app: App | None
    reviewer_app: App | None
    escalation: Escalation
    optional_skills: tuple[str, ...]
    excluded: tuple[str, ...]
    source_roots: tuple[str, ...]
    unguided: tuple[str, ...]
    map_exclude: tuple[str, ...]
    unit_tests: tuple[str, ...]

    @property
    def agent_identity(self) -> bool: ...


def load_project(root: Path) -> ProjectSettings: ...
def load_exceptions(root: Path) -> list[ExceptionEntry]: ...
```

`CheckContext(repo, project, base, pr_body)`, without `gate`. `check_workspace.project_settings(**changes)` builds the test defaults above with Walk; `gate_settings` is gone.

- [ ] **Step 1: Write the failing tests**

Replace `tests/devctl/test_devctl_settings.py` with:

```python
"""devctl settings loading, defaults and errors (offline)."""

import json
import re
from pathlib import Path

import pytest

from devctl.settings import (
    EXCEPTIONS,
    PROJECT,
    REMOVED_TABLES,
    App,
    Escalation,
    ProjectSettings,
    SettingsError,
    load_exceptions,
    load_project,
)
from rapid_ship.kit.init import resolve_variables
from rapid_ship.kit.templates import KitError, render_files

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = {"project_name": "demo-app", "package": "demo_app", "owner": "", "repository": ""}
LOADERS = {PROJECT: load_project, EXCEPTIONS: load_exceptions}
SEEDED_KIND = "a pull request that removes a behavioural test"
APPS = (
    '[github]\nrepository = "o/r"\n'
    'worker_app_id = 101\nworker_app_slug = "o-rs-worker"\n'
    'reviewer_app_id = 202\nreviewer_app_slug = "o-rs-reviewer"\n'
)


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_the_seeded_settings_load_with_the_spec_defaults(tmp_path: Path) -> None:
    for template in render_files("python", VARIABLES, ()):
        if template.path.startswith(".rapid-ship/"):
            assert template.content is not None
            write(tmp_path, template.path, template.content.decode())

    project = load_project(tmp_path)

    assert project == ProjectSettings(
        stack="python",
        repository=None,
        worker_app=None,
        reviewer_app=None,
        escalation=Escalation(every_pr=True, kinds=(SEEDED_KIND,), revision_rounds=3),
        optional_skills=(),
        excluded=(),
        source_roots=("src/demo_app",),
        unguided=(),
        map_exclude=(),
        unit_tests=("tests/unit/**",),
    )
    assert not project.agent_identity
    assert load_exceptions(tmp_path) == []
    assert not (tmp_path / ".rapid-ship/gate.toml").exists()


def test_absent_keys_take_their_defaults(tmp_path: Path) -> None:
    write(tmp_path, PROJECT, 'stack = "agnostic"\n')

    project = load_project(tmp_path)

    assert project.escalation == Escalation(every_pr=True, kinds=(), revision_rounds=3)
    assert project.unit_tests == ("tests/unit/**",)
    assert (project.worker_app, project.reviewer_app, project.agent_identity) == (
        None,
        None,
        False,
    )


def test_both_apps_turn_agent_identity_on(tmp_path: Path) -> None:
    write(tmp_path, PROJECT, 'stack = "python"\n' + APPS)

    project = load_project(tmp_path)

    assert (project.worker_app, project.reviewer_app) == (
        App(101, "o-rs-worker"),
        App(202, "o-rs-reviewer"),
    )
    assert project.agent_identity


def test_an_escalation_list_for_flight_loads(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n[escalation]\nevery_pr = false\n'
        'kinds = ["a database migration", "a public API change"]\nrevision_rounds = 2\n',
    )

    assert load_project(tmp_path).escalation == Escalation(
        every_pr=False, kinds=("a database migration", "a public API change"), revision_rounds=2
    )


# What replaced each removed table (Spec 1 section 4), written out so the test does not compare
# the code with itself.
REPLACED_BY = {
    "agents": "does not run agents across several Providers",
    "dispatch": "no longer starts Workers",
    "linear": "never talks to the issue tracker",
    "release": "Spec 3",
}


def test_every_removed_table_is_tested() -> None:
    assert sorted(REMOVED_TABLES) == sorted(REPLACED_BY)


@pytest.mark.parametrize(("table", "replacement"), sorted(REPLACED_BY.items()))
def test_a_removed_table_names_what_replaced_it(
    tmp_path: Path, table: str, replacement: str
) -> None:
    write(tmp_path, PROJECT, f'stack = "python"\n[{table}]\n')

    with pytest.raises(SettingsError) as raised:
        load_project(tmp_path)

    message = str(raised.value)
    assert message.startswith(f"{PROJECT}: [{table}] was removed: ")
    assert replacement in message


def test_kit_exclude_is_loaded_and_normalised(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n[kit]\n'
        'exclude = ["devctl", "tools/devctl/", "./.agents/skills/rs-tdd"]\n',
    )

    assert load_project(tmp_path).excluded == ("devctl", "tools/devctl", ".agents/skills/rs-tdd")


def test_map_exclude_is_loaded_and_normalised(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n[map]\nexclude = ["pkg/templates/", "./other/dir"]\n',
    )

    assert load_project(tmp_path).map_exclude == ("pkg/templates", "other/dir")


def test_this_repository_settings_load() -> None:
    project = load_project(ROOT)
    assert (project.repository, project.source_roots) == ("proxy-hatch/rapid-ship", ("rapid_ship",))
    # Nothing is excluded here, so status --strict holds every Kit file to its template.
    assert project.excluded == ()
    assert project.escalation.every_pr  # Walk
    assert not (ROOT / ".rapid-ship/gate.toml").exists()


def test_a_missing_file_is_a_settings_error(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match=re.escape(".rapid-ship/project.toml: missing")):
        load_project(tmp_path)


EXCEPTION = (
    '[[exception]]\nid = "EX-1"\npath = "a.py"\nrule = "S603"\nreason = "r"\nremove_when = "w"\n'
)
NO_REVIEWER_APP = APPS.replace("reviewer_app_id = 202", "reviewer_app_id = 0").replace(
    'reviewer_app_slug = "o-rs-reviewer"', 'reviewer_app_slug = ""'
)


@pytest.mark.parametrize(
    ("relative", "text", "message"),
    [
        (PROJECT, "", "stack: required"),
        (PROJECT, "stack = \n", "project.toml: Invalid value"),
        (PROJECT, 'stack = "rust"\n', "stack: expected python or agnostic"),
        (PROJECT, 'stack = "python"\n[test]\nunit = []\n', "unknown key 'test'"),
        (
            PROJECT,
            'stack = "python"\n[github]\nworker_app_id = true\n',
            "worker_app_id: expected an integer of at least 0",
        ),
        (
            PROJECT,
            'stack = "python"\n[github]\nrepository = "o/r"\nworker_app_id = 101\n',
            "worker_app_id and worker_app_slug go together",
        ),
        (
            PROJECT,
            'stack = "python"\n' + NO_REVIEWER_APP,
            "Agent identity needs both the Worker App and the Reviewer App",
        ),
        (
            PROJECT,
            'stack = "python"\n' + APPS.replace('repository = "o/r"\n', ""),
            "Apps are recorded but repository is not",
        ),
        (
            PROJECT,
            'stack = "python"\n' + APPS.replace('"o-rs-worker"', '"O RS Worker"'),
            "worker_app_slug: expected an App slug",
        ),
        (
            PROJECT,
            'stack = "python"\n[escalation]\nevery_pr = "no"\n',
            "every_pr: expected true or false",
        ),
        (
            PROJECT,
            'stack = "python"\n[escalation]\nrevision_rounds = 0\n',
            "revision_rounds: expected an integer of at least 1",
        ),
        (
            PROJECT,
            'stack = "python"\n[escalation]\nkinds = ["", "x"]\n',
            "kinds: expected a list of non-empty strings",
        ),
        (PROJECT, 'stack = "python"\n[escalation]\nmode = "flight"\n', "unknown key 'mode'"),
        (
            PROJECT,
            'stack = "python"\n[github]\nrepository = "not a repo"\n',
            "repository: expected owner/name",
        ),
        (
            PROJECT,
            'stack = "python"\n[github]\nrepository = "owner/.."\n',
            "repository: expected owner/name",
        ),
        (
            PROJECT,
            'stack = "python"\n[tests]\nunit = "tests/unit/**"\n',
            "unit: expected a list of non-empty strings",
        ),
        (
            PROJECT,
            'stack = "python"\n[kit]\nexclude = "devctl"\n',
            "exclude: expected a list of non-empty strings",
        ),
        (
            PROJECT,
            'stack = "python"\n[kit]\nexclude = ["../outside"]\n',
            "exclude: expected paths inside the repository",
        ),
        (
            PROJECT,
            'stack = "python"\n[kit]\nexclude = ["/etc"]\n',
            "exclude: expected paths inside the repository",
        ),
        (
            PROJECT,
            'stack = "python"\n[map]\nexclude = ["../x"]\n',
            "exclude: expected paths inside the repository",
        ),
        (EXCEPTIONS, EXCEPTION.replace('remove_when = "w"\n', ""), "remove_when: required"),
        (EXCEPTIONS, EXCEPTION + EXCEPTION, "EX-1 is listed twice"),
        (EXCEPTIONS, EXCEPTION.replace("EX-1", "EX-01"), "id: expected EX-<n>"),
        (
            EXCEPTIONS,
            EXCEPTION.replace('"a.py"', '"../a.py"'),
            "path: expected a path inside the repository",
        ),
    ],
)
def test_invalid_settings_raise_settings_error(
    tmp_path: Path, relative: str, text: str, message: str
) -> None:
    write(tmp_path, relative, text)

    with pytest.raises(SettingsError, match=re.escape(message)):
        LOADERS[relative](tmp_path)


@pytest.mark.parametrize(
    ("repository", "valid"),
    [
        ("octo/demo", True),
        ("octo-cat/my.app", True),
        ("octo/.github", True),
        ("octo/a..b", True),
        ("octo", False),
        ("octo/", False),
        ("octo/.", False),
        ("octo/..", False),
        ("-octo/demo", False),
        ("octo/de mo", False),
        ("octo/demo\n", False),
    ],
)
def test_devctl_and_init_accept_the_same_repositories(
    tmp_path: Path, repository: str, valid: bool
) -> None:
    # devctl is vendored into projects without rapid-ship, so it keeps its own copy of the pattern.
    write(tmp_path, PROJECT, f'stack = "python"\n[github]\nrepository = {json.dumps(repository)}\n')

    try:
        load_project(tmp_path)
        devctl_accepts = True
    except SettingsError:
        devctl_accepts = False
    try:
        # --name keeps the repository's own name, such as .github, out of the project-name check.
        resolve_variables(tmp_path, name="demo-app", repository=repository)
        init_accepts = True
    except KitError:
        init_accepts = False

    assert (devctl_accepts, init_accepts) == (valid, valid)
```

Then make these edits to the tests that used `gate.toml` and the old fields:

In `tests/devctl/check_workspace.py`, replace:

```python
from devctl.settings import GateSettings, ProjectSettings
```

with:

```python
from devctl.settings import Escalation, ProjectSettings
```

In `tests/devctl/check_workspace.py`, replace:

```python
    base = ProjectSettings(
        stack="python",
        worker=None,
        reviewer=None,
        repository=None,
        worker_app_id=None,
        reviewer_app_id=None,
        linear_team_id=None,
        linear_project_id=None,
        optional_skills=(),
        excluded=(),
        max_workers=5,
        attempt_limit=3,
        worktree_root="../app.worktrees",
        source_roots=("src/app",),
        unguided=(),
        map_exclude=(),
        unit_tests=("tests/unit/**",),
        release_method="none",
    )
    return dataclasses.replace(base, **cast("dict[str, Any]", changes))


def gate_settings(**changes: object) -> GateSettings:
    base = GateSettings(
        mode="walk", flight_lease_until=None, owner_approves_behavioural_test_removal=True
    )
    return dataclasses.replace(base, **cast("dict[str, Any]", changes))
```

with:

```python
    base = ProjectSettings(
        stack="python",
        repository=None,
        worker_app=None,
        reviewer_app=None,
        escalation=Escalation(every_pr=True, kinds=(), revision_rounds=3),
        optional_skills=(),
        excluded=(),
        source_roots=("src/app",),
        unguided=(),
        map_exclude=(),
        unit_tests=("tests/unit/**",),
    )
    return dataclasses.replace(base, **cast("dict[str, Any]", changes))
```

In `tests/devctl/check_workspace.py`, replace:

```python
        pr_body: str | None = None,
        gate: GateSettings | None = None,
        **project: object,
    ) -> CheckContext:
        return CheckContext(
            Repo.discover(self.root),
            project_settings(**project),
            gate or gate_settings(),
            base,
            pr_body,
        )
```

with:

```python
        pr_body: str | None = None,
        **project: object,
    ) -> CheckContext:
        return CheckContext(Repo.discover(self.root), project_settings(**project), base, pr_body)
```

In `tests/devctl/test_devctl_diff_removed_tests.py`, replace:

```python
from check_workspace import Workspace, gate_settings
```

with:

```python
from check_workspace import Workspace
```

In `tests/devctl/test_devctl_diff_removed_tests.py`, replace:

```python
def run(workspace: Workspace, base: str, body: str | None = None, **gate: object) -> StepResult:
    return DiffStep().run(workspace.context(base=base, pr_body=body, gate=gate_settings(**gate)))
```

with:

```python
def run(workspace: Workspace, base: str, body: str | None = None) -> StepResult:
    return DiffStep().run(workspace.context(base=base, pr_body=body))
```

In `tests/devctl/test_devctl_diff_removed_tests.py`, replace:

```python
def test_declared_removal_passes_and_flight_waits_for_the_owner(workspace: Workspace) -> None:
    workspace.write("tests/test_api.py", "class TestApi:\n    def test_delete(self): pass\n")
    base = workspace.commit()
    workspace.write("tests/test_api.py", "class TestApi:\n    pass\n")
    body = (
        EVIDENCE + "Removed tests:\n- tests/test_api.py::TestApi::test_delete: endpoint removed\n"
    )

    walk = run(workspace, base, body)
    flight = run(workspace, base, body, mode="flight")
    flight_off = run(
        workspace, base, body, mode="flight", owner_approves_behavioural_test_removal=False
    )

    assert walk.status == flight.status == flight_off.status == "passed"
    assert walk.details[0] == (
        "removed behavioural test tests/test_api.py::TestApi::test_delete: "
        "declared (endpoint removed)"
    )
    assert flight.details[0].endswith("; in Flight this waits for the owner's approval")
    assert flight_off.details[0] == walk.details[0]
```

with:

```python
def test_declared_removal_passes_with_its_reason_and_no_mode(workspace: Workspace) -> None:
    workspace.write("tests/test_api.py", "class TestApi:\n    def test_delete(self): pass\n")
    base = workspace.commit()
    workspace.write("tests/test_api.py", "class TestApi:\n    pass\n")
    body = (
        EVIDENCE + "Removed tests:\n- tests/test_api.py::TestApi::test_delete: endpoint removed\n"
    )

    result = run(workspace, base, body)

    assert result.status == "passed"
    # The escalation list, not the step, decides whether the owner sees a declared removal.
    assert result.details[0] == (
        "removed behavioural test tests/test_api.py::TestApi::test_delete: "
        "declared (endpoint removed)"
    )
```

In `tests/devctl/test_devctl_check_cli.py`, replace:

```python
from check_workspace import FakeStep, Workspace, gate_settings, project_settings
```

with:

```python
from check_workspace import FakeStep, Workspace, project_settings
```

In `tests/devctl/test_devctl_check_cli.py`, delete:

```python
    monkeypatch.setattr(cli, "load_gate", lambda root: gate_settings())
```

In `tests/test_kit_contents.py`, replace:

<!-- fmt:off -->
```python
    ".rapid-ship/exceptions.toml",
    ".rapid-ship/gate.toml",
    ".rapid-ship/project.toml",
```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
    ".rapid-ship/exceptions.toml",
    ".rapid-ship/project.toml",
```
<!-- fmt:on -->

In `tests/test_kit_contents.py`, replace:

```python
    settings = tomllib.loads(text(stack, ".rapid-ship/project.toml"))
    assert settings == {
        "stack": stack,
        "github": {"repository": "octo/demo-app", "worker_app_id": 0, "reviewer_app_id": 0},
        "kit": {"optional": [], "exclude": []},
        "linear": {"team_id": "", "project_id": ""},
        "dispatch": {
            "max_workers": 5,
            "attempt_limit": 3,
            "worktree_root": "../demo-app.worktrees",
        },
        "map": {"source_roots": roots, "unguided": [], "exclude": []},
        "tests": {"unit": ["tests/unit/**"]},
        "release": {"method": "none"},
    }
```

with:

```python
    settings = tomllib.loads(text(stack, ".rapid-ship/project.toml"))
    assert settings == {
        "stack": stack,
        "github": {
            "repository": "octo/demo-app",
            "worker_app_id": 0,
            "worker_app_slug": "",
            "reviewer_app_id": 0,
            "reviewer_app_slug": "",
        },
        "escalation": {
            "every_pr": True,
            "kinds": ["a pull request that removes a behavioural test"],
            "revision_rounds": 3,
        },
        "kit": {"optional": [], "exclude": []},
        "map": {"source_roots": roots, "unguided": [], "exclude": []},
        "tests": {"unit": ["tests/unit/**"]},
    }
```

In `tests/test_kit_contents.py`, replace:

```python
def test_gate_seed_has_the_spec_defaults() -> None:
    gate = tomllib.loads(text("agnostic", ".rapid-ship/gate.toml"))
    assert gate["mode"] == "walk"
    assert gate["flight_lease_until"] == ""
    assert gate["owner_approves_behavioural_test_removal"] is True
    limits = {"max_revisions_per_pr": 1.0, "max_rollbacks": 1, "max_open_alarms": 0}
    assert gate["thresholds"] == {
        "promotion": {"window": 30, **limits},
        "demotion": {"window": 20, **limits},
    }
```

with:

```python
def test_the_kit_no_longer_seeds_gate_toml() -> None:
    assert ".rapid-ship/gate.toml" not in rendered("python")
    assert ".rapid-ship/gate.toml" not in load_manifest().seeded
```

In `tests/devctl/test_devctl_cli.py`, replace both occurrences of `.rapid-ship/gate.toml mode: expected walk or flight` with `.rapid-ship/project.toml stack: required`. That test only needs some `SettingsError` text, and the old text names a file that no longer exists.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_settings.py -q`
Expected: pytest stops while loading `tests/conftest.py`, with `ImportError: cannot import name 'Escalation' from 'devctl.settings'`.

- [ ] **Step 3: Write the settings, the seeds and this repository's settings**

Replace `rapid_ship/templates/common/tools/devctl/devctl/settings.py` with:

```python
"""devctl's typed view of .rapid-ship settings.

Unknown keys are errors, so a typo cannot silently keep a default. Every loader reads
one file and raises SettingsError, which devctl reports with exit 2.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, cast, get_args

PROJECT = ".rapid-ship/project.toml"
EXCEPTIONS = ".rapid-ship/exceptions.toml"

Role = Literal["worker", "reviewer"]
Stack = Literal["python", "agnostic"]
ROLES: tuple[Role, ...] = ("worker", "reviewer")
# Tables the re-scope of 2026-10-16 removed, and what replaced each (Spec 1 section 4).
REMOVED_TABLES = {
    "agents": "rapid-ship does not run agents across several Providers; delete the table",
    "dispatch": "rapid-ship no longer starts Workers, and the Lead brief's Focus caps parallel "
    "Workers; delete the table",
    "linear": "devctl never talks to the issue tracker; delete the table",
    "release": "a project defines its own deploy metrics (Spec 3); delete the table",
}

_TABLES = {"stack", "github", "escalation", "kit", "map", "tests"}
_GITHUB_KEYS = {
    "repository",
    "worker_app_id",
    "worker_app_slug",
    "reviewer_app_id",
    "reviewer_app_slug",
}
_REPOSITORY = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*/(?!\.{1,2}$)[A-Za-z0-9._-]+")
_APP_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")  # the slugs GitHub gives Apps
_EXCEPTION_ID = re.compile(r"EX-[1-9][0-9]*")
_EXCEPTION_KEYS = ("id", "path", "rule", "reason", "remove_when")


class SettingsError(Exception):
    """A settings file is missing or invalid. devctl exits 2."""


@dataclass(frozen=True)
class App:
    id: int  # [github] <role>_app_id; 0 in the file means unset
    slug: str  # [github] <role>_app_slug; Spec 3 matches agent PR authors against it


@dataclass(frozen=True)
class Escalation:
    every_pr: bool  # default True: Walk
    kinds: tuple[str, ...]  # plain text for the Lead
    revision_rounds: int  # default 3, at least 1


@dataclass(frozen=True)
class ProjectSettings:
    stack: Stack
    repository: str | None  # "owner/name"
    worker_app: App | None  # both Apps recorded, or neither; recorded Apps need repository
    reviewer_app: App | None
    escalation: Escalation
    optional_skills: tuple[str, ...]  # [kit] optional
    # [kit] exclude: Kit paths the project owns; a skill directory also covers its link.
    excluded: tuple[str, ...]
    source_roots: tuple[str, ...]  # [map] source_roots
    unguided: tuple[str, ...]  # [map] unguided
    # [map] exclude: directories whose AGENTS.md files are template content, not guides.
    map_exclude: tuple[str, ...]
    unit_tests: tuple[str, ...]  # [tests] unit; default ("tests/unit/**",)

    @property
    def agent_identity(self) -> bool:
        """On when both Apps are recorded; load_project accepts both or neither."""
        return self.worker_app is not None and self.reviewer_app is not None


@dataclass(frozen=True)
class ExceptionEntry:
    id: str  # "EX-<n>", n >= 1, unique
    path: str
    rule: str
    reason: str
    remove_when: str


class _Table:
    """One TOML table with known keys. Each accessor checks the value's type."""

    def __init__(self, value: object, where: str, keys: set[str]) -> None:
        if not isinstance(value, dict):
            raise SettingsError(f"{where}: expected a table")
        unknown = sorted(set(value) - keys)
        if unknown:
            raise SettingsError(f"{where}: unknown key {unknown[0]!r}")
        self.values: dict[str, object] = value
        self.where = where

    def table(self, key: str, keys: set[str]) -> _Table:
        return _Table(self.values.get(key, {}), f"{self.where} [{key}]", keys)

    def _error(self, key: str, expected: str) -> SettingsError:
        return SettingsError(f"{self.where} {key}: expected {expected}")

    def text(self, key: str, default: str = "") -> str:
        value = self.values.get(key, default)
        if not isinstance(value, str):
            raise self._error(key, "a string")
        return value

    def choice(self, key: str, options: tuple[str, ...], default: str | None = None) -> str:
        if key not in self.values and default is None:
            raise SettingsError(f"{self.where} {key}: required")
        value = self.values.get(key, default)
        if value not in options:
            raise self._error(key, " or ".join(options))
        return value

    def integer(self, key: str, default: int, minimum: int) -> int:
        value = self.values.get(key, default)
        # TOML true is a Python bool, which is also an int.
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise self._error(key, f"an integer of at least {minimum}")
        return value

    def boolean(self, key: str, default: bool) -> bool:
        value = self.values.get(key, default)
        if not isinstance(value, bool):
            raise self._error(key, "true or false")
        return value

    def texts(self, key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
        value = self.values.get(key, list(default))
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise self._error(key, "a list of non-empty strings")
        return tuple(value)


def _read(root: Path, relative: str) -> dict[str, object]:
    try:
        return tomllib.loads((root / relative).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"{relative}: missing; rapid-ship init seeds it") from None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SettingsError(f"{relative}: {error}") from error


def _inside_repository(entry: str) -> str | None:
    """The repository-relative POSIX path without "./" or a trailing "/", or None if it leaves."""
    path = PurePosixPath(entry)
    if not path.parts or path.is_absolute() or ".." in path.parts or "\\" in entry:
        return None
    return "/".join(path.parts)


def _app(github: _Table, role: Role) -> App | None:
    """The role's App, or None when its ID is 0 and its slug empty."""
    app_id = github.integer(f"{role}_app_id", 0, minimum=0)
    slug = github.text(f"{role}_app_slug")
    if not app_id and not slug:
        return None
    if not app_id or not slug:
        raise SettingsError(
            f"{github.where}: {role}_app_id and {role}_app_slug go together; record both, "
            "as rapid-ship app prints them, or neither"
        )
    if not _APP_SLUG.fullmatch(slug):
        raise github._error(f"{role}_app_slug", "an App slug: lowercase letters, digits and -")
    return App(app_id, slug)


def _apps(github: _Table, repository: str | None) -> tuple[App | None, App | None]:
    """Both Apps, or neither: Agent identity is on or off, never half on."""
    worker, reviewer = _app(github, "worker"), _app(github, "reviewer")
    if (worker is None) != (reviewer is None):
        raise SettingsError(
            f"{github.where}: Agent identity needs both the Worker App and the Reviewer App; "
            "record both or neither"
        )
    if worker is not None and repository is None:
        raise SettingsError(
            f"{github.where}: Apps are recorded but repository is not; "
            'set repository = "owner/name"'
        )
    return worker, reviewer


def _escalation(top: _Table) -> Escalation:
    table = top.table("escalation", {"every_pr", "kinds", "revision_rounds"})
    return Escalation(
        every_pr=table.boolean("every_pr", True),
        kinds=table.texts("kinds"),
        revision_rounds=table.integer("revision_rounds", 3, minimum=1),
    )


def _exclude_paths(table: _Table) -> tuple[str, ...]:
    """A table's `exclude` list, normalised as rapid-ship's read_excluded does."""
    paths = [_inside_repository(entry) for entry in table.texts("exclude")]
    if None in paths:
        raise table._error("exclude", "paths inside the repository")
    return tuple(path for path in paths if path is not None)


def _refuse_removed(data: dict[str, object]) -> None:
    for name, replacement in REMOVED_TABLES.items():
        if name in data:
            raise SettingsError(f"{PROJECT}: [{name}] was removed: {replacement}")


def load_project(root: Path) -> ProjectSettings:
    data = _read(root, PROJECT)
    _refuse_removed(data)
    top = _Table(data, PROJECT, _TABLES)
    stack = cast(Stack, top.choice("stack", get_args(Stack)))
    github = top.table("github", _GITHUB_KEYS)
    kit = top.table("kit", {"optional", "exclude"})
    source_map = top.table("map", {"source_roots", "unguided", "exclude"})
    tests = top.table("tests", {"unit"})

    repository = github.text("repository") or None
    if repository is not None and not _REPOSITORY.fullmatch(repository):
        raise github._error("repository", "owner/name")
    worker_app, reviewer_app = _apps(github, repository)
    return ProjectSettings(
        stack=stack,
        repository=repository,
        worker_app=worker_app,
        reviewer_app=reviewer_app,
        escalation=_escalation(top),
        optional_skills=kit.texts("optional"),
        excluded=_exclude_paths(kit),
        source_roots=source_map.texts("source_roots"),
        unguided=source_map.texts("unguided"),
        map_exclude=_exclude_paths(source_map),
        unit_tests=tests.texts("unit", ("tests/unit/**",)),
    )


def load_exceptions(root: Path) -> list[ExceptionEntry]:
    top = _Table(_read(root, EXCEPTIONS), EXCEPTIONS, {"exception"})
    items = top.values.get("exception", [])
    if not isinstance(items, list):
        raise top._error("exception", "a list of tables")
    entries: list[ExceptionEntry] = []
    for number, item in enumerate(items, start=1):
        row = _Table(item, f"{EXCEPTIONS} [[exception]] #{number}", set(_EXCEPTION_KEYS))
        fields = {key: row.text(key) for key in _EXCEPTION_KEYS}
        for key, value in fields.items():
            if not value.strip():
                raise SettingsError(f"{row.where} {key}: required")
        if not _EXCEPTION_ID.fullmatch(fields["id"]):
            raise row._error("id", "EX-<n>")
        if any(entry.id == fields["id"] for entry in entries):
            raise SettingsError(f"{row.where}: {fields['id']} is listed twice")
        if _inside_repository(fields["path"]) is None:
            raise row._error("path", "a path inside the repository")
        entries.append(ExceptionEntry(**fields))
    return entries
```

Make these edits to the other devctl templates and to the Kit manifest:

In `rapid_ship/templates/common/tools/devctl/devctl/check/steps.py`, replace:

```python
from devctl.settings import GateSettings, ProjectSettings
```

with:

```python
from devctl.settings import ProjectSettings
```

In `rapid_ship/templates/common/tools/devctl/devctl/check/steps.py`, replace:

```python
    project: ProjectSettings
    gate: GateSettings
```

with:

```python
    project: ProjectSettings
```

In `rapid_ship/templates/common/tools/devctl/devctl/check/diff.py`, delete:

```python
_OWNER_WAITS = "; in Flight this waits for the owner's approval"
```

In `rapid_ship/templates/common/tools/devctl/devctl/check/diff.py`, replace:

<!-- fmt:off -->
```python
    """A problem for each undeclared removal and a note for each declared one, in removed order."""
    body = context.pr_body
    declared = {} if body is None else removed_test_declarations(body)[0]
    gate = context.gate
    owner_waits = gate.mode == "flight" and gate.owner_approves_behavioural_test_removal
    problems: list[str] = []
```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
    """A problem for each undeclared removal and a note for each declared one, in removed order.

    Whether a declared removal goes to the owner is the escalation list's business, not this
    step's (Spec 1 section 5).
    """
    body = context.pr_body
    declared = {} if body is None else removed_test_declarations(body)[0]
    problems: list[str] = []
```
<!-- fmt:on -->

In `rapid_ship/templates/common/tools/devctl/devctl/check/diff.py`, replace:

```python
        else:
            waits = owner_waits and not unit
            notes.append(f"{removal}: declared ({declared[test]}){_OWNER_WAITS if waits else ''}")
```

with:

```python
        else:
            notes.append(f"{removal}: declared ({declared[test]})")
```

In `rapid_ship/templates/common/tools/devctl/devctl/cli.py`, replace:

```python
from devctl.settings import SettingsError, load_gate, load_project
```

with:

```python
from devctl.settings import SettingsError, load_project
```

In `rapid_ship/templates/common/tools/devctl/devctl/cli.py`, replace:

```python
        context = CheckContext(repo, load_project(repo.root), load_gate(repo.root), base, pr_body)
```

with:

```python
        context = CheckContext(repo, load_project(repo.root), base, pr_body)
```

In `rapid_ship/templates/kit.toml`, replace:

```toml
    ".rapid-ship/exceptions.toml",
    ".rapid-ship/gate.toml",
```

with:

```toml
    ".rapid-ship/exceptions.toml",
```

Replace `rapid_ship/templates/python/.rapid-ship/project.toml` with:

```toml
# rapid-ship project settings. No secrets. Changes need the owner (Protected set).
stack = "python"

[github]
repository = "{{repository}}"
# Agent identity: each App's ID and slug, as rapid-ship app prints them. 0 and "" mean off.
worker_app_id = 0
worker_app_slug = ""
reviewer_app_id = 0
reviewer_app_slug = ""

[escalation]
# The kinds of pull request the Lead brings to the owner instead of merging it itself.
# true is Walk. false leaves the Protected set and the kinds below: Flight, or anything between.
every_pr = true
kinds = [
  "a pull request that removes a behavioural test",
]
revision_rounds = 3    # a PR that reached this many Revisions also goes to the owner

[kit]
optional = []        # opt-in Kit skills, such as "rs-contribute"
# Kit files or directories the project owns instead. rapid-ship sync never
# creates, replaces, deletes or reports them. A skill directory covers its
# .claude/skills link.
exclude = []

[map]
source_roots = ["src/{{package}}"]
unguided = []
# Directories whose AGENTS.md files are template content, not guides. The map
# check ignores those files: it requires none and checks no links in them.
exclude = []

[tests]
unit = ["tests/unit/**"]   # every other test counts as behavioural
```

Replace `rapid_ship/templates/agnostic/.rapid-ship/project.toml` with the same text, except that its second line is `stack = "agnostic"` and its `[map]` line `source_roots = ["src/{{package}}"]` is `source_roots = []`.

Replace this repository's `.rapid-ship/project.toml` with:

```toml
# rapid-ship project settings. No secrets. Changes need the owner (Protected set).
stack = "python"

[github]
repository = "proxy-hatch/rapid-ship"
# Agent identity: each App's ID and slug, as rapid-ship app prints them. 0 and "" mean off.
worker_app_id = 0
worker_app_slug = ""
reviewer_app_id = 0
reviewer_app_slug = ""

[escalation]
# The kinds of pull request the Lead brings to the owner instead of merging it itself.
# true is Walk. false leaves the Protected set and the kinds below: Flight, or anything between.
every_pr = true
kinds = [
  "a pull request that removes a behavioural test",
]
revision_rounds = 3    # a PR that reached this many Revisions also goes to the owner

[kit]
optional = []        # opt-in Kit skills, such as "rs-contribute"
# Kit files or directories the project owns instead. rapid-ship sync never
# creates, replaces, deletes or reports them. A skill directory covers its
# .claude/skills link.
exclude = []

[map]
source_roots = ["rapid_ship"]
unguided = []
# Template trees hold the AGENTS.md files of future projects, not guides of this one.
exclude = ["rapid_ship/templates/common", "rapid_ship/templates/python", "rapid_ship/templates/agnostic"]

[tests]
unit = ["tests/unit/**"]   # every other test counts as behavioural
```

Delete both `gate.toml` files, drop the root guide's link to this repository's copy, format and vendor:

```sh
git rm -q rapid_ship/templates/common/.rapid-ship/gate.toml .rapid-ship/gate.toml
perl -pi -e 's/\[gate\.toml\]\(\.rapid-ship\/gate\.toml\), //' AGENTS.md
! grep -n 'gate\.toml' AGENTS.md
T=rapid_ship/templates/common/tools/devctl/devctl
uv run ruff format $T/settings.py $T/check/steps.py $T/check/diff.py $T/cli.py
uv run ruff check $T/settings.py $T/check/steps.py $T/check/diff.py $T/cli.py
uv run rapid-ship sync --in-place
```

Expected: `grep` finds nothing; `sync` replaces `tools/devctl/devctl/settings.py`, `check/diff.py`, `check/steps.py` and `cli.py`, and lists `.rapid-ship/project.toml` as a seeded file whose template changed. The lock keeps a seeded entry for `.rapid-ship/gate.toml`: `sync` never deletes a seeded file or its entry, nothing reads it, and the lock is never edited by hand.

- [ ] **Step 4: Run the tests and see them pass**

```sh
uv run pytest tests/devctl tests/test_kit_contents.py tests/test_kit_dogfood.py -q
uv run rapid-ship status --strict
./devctl check --tier fast
uv run mypy
```

Expected: every test passes; status exits 0; the fast tier passes every step, and `map` finds no broken link in the root guide; mypy reports no issues.

- [ ] **Step 5: Commit**

```sh
git add -A rapid_ship/templates tools/devctl .rapid-ship AGENTS.md tests
git commit -m "feat: read the escalation list and both Apps from project.toml" -m "The re-scope removes [agents], [linear], [dispatch], [release] and gate.toml; each removed table is refused with what replaced it, and the diff step no longer reads a Mode." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: The REST client, App tokens and the askpass helper

The token code comes over from `1eb138d`, `620e5ff` and `f5177ba` with `ebe3bd2`'s additions (`installation`, `AppNotInstalled`, `guarded_message`), without `d44b673`'s Claim-only git helpers, and without `paginate`, `app_slug` and `GitHubAccess.slug`, which only the cut commands called. Its tests run against a fake HTTP server on 127.0.0.1, a fake Keychain and local bare repositories, and say so.

**Files:**
- Create (copied): `rapid_ship/templates/common/tools/devctl/devctl/github/__init__.py`, `github/askpass.py`
- Create (copied, then trimmed): `rapid_ship/templates/common/tools/devctl/devctl/github/app.py`, `github/api.py`
- Modify (copied from `620e5ff`): `rapid_ship/templates/common/tools/devctl/devctl/check/kit.py`
- Modify: `rapid_ship/templates/common/tools/devctl/pyproject.toml` and `uv.lock`, root `pyproject.toml` and `uv.lock`, `rapid_ship/templates/kit.toml`, `tests/conftest.py`
- Create: `tests/devctl/github_fakes.py`, `tests/devctl/github_fixtures.py`
- Test (copied): `tests/devctl/test_devctl_github_api.py`, `test_devctl_github_api_limits.py`, `test_devctl_github_app.py`, `test_devctl_github_app_limits.py`, `test_devctl_askpass.py`, `test_devctl_askpass_limits.py`, `test_devctl_kit_step.py`; modify `tests/test_kit_contents.py`

**Interfaces:**
- Consumes: `Role`, `ProjectSettings`, `SettingsError` (Task 2); `process.run_process`, `process.first_line` (Task 1); `KitLockError` (plan 3).
- Produces (the index's Agent identity section, plus what doctor and `devctl as` call):

<!-- fmt:off -->
```python
# devctl/github/api.py
API_URL = "https://api.github.com"
class GitHubError(Exception):  # .status: int | None
    def __init__(self, status: int | None, message: str) -> None: ...
def json_object(value: object, what: str) -> dict[str, object]: ...
def json_list(value: object, what: str) -> list[object]: ...
class GitHubApi:
    def __init__(self, token: str, *, base_url: str = API_URL) -> None: ...
    def request(self, method: str, path: str, body: object | None = None) -> object: ...

# devctl/github/askpass.py
ASKPASS_VARIABLE = "RAPID_SHIP_GIT_TOKEN"
ASKPASS_PATH: Path
GIT_TOKEN_OPTIONS = ("-c", "credential.helper=", "-c", "core.hooksPath=/dev/null")

# devctl/github/app.py
KEYCHAIN_SERVICE: dict[Role, str]  # "rapid-ship/worker-app", "rapid-ship/reviewer-app"
APP_PERMISSIONS: dict[Role, dict[str, str]]  # Spec 1 section 3
class DevctlError(Exception): ...  # exit 2
class AppError(DevctlError): ...
class KeychainMissing(AppError): ...
class AppNotInstalled(AppError): ...
class GitError(DevctlError): ...
class Keychain(Protocol):
    def read(self, service: str) -> bytes: ...
class MacKeychain: ...
def app_jwt(private_key: bytes, app_id: int, now: float | None = None) -> str: ...
def installation(role: Role, repository: str, app_id: int, *, keychain: Keychain | None = None, api_url: str = API_URL) -> dict[str, object]: ...
def installation_token(role: Role, repository: str, app_id: int, *, keychain: Keychain | None = None, api_url: str = API_URL) -> str: ...
@dataclass(frozen=True)
class GitHubAccess:
    repository: str
    api_url: str = API_URL
    remote_url: str | None = None
    keychain: Keychain | None = None
    @property
    def remote(self) -> str: ...  # https://github.com/<repository>.git unless remote_url
    def token(self, role: Role, app_id: int) -> str: ...  # one mint per call
    def api(self, token: str) -> GitHubApi: ...
def project_access(project: ProjectSettings) -> GitHubAccess: ...  # AppError without a repository
def guarded_message(error: Exception, root: Path | None) -> str: ...
def run_guarded(action: Callable[[], int], *, root: Path | None = None) -> int: ...  # exit 2 on known errors
def git_environment(token: str) -> dict[str, str]: ...
def require_exact_remote(cwd: Path, url: str) -> None: ...
def run_git(cwd: Path, args: Sequence[str], token: str, *, url: str, timeout_seconds: float = 120.0) -> ProcessResult: ...

# devctl/check/kit.py
RAPID_SHIP_SOURCE = "git+https://github.com/proxy-hatch/rapid-ship"
def rapid_ship_command(root: Path, command: str) -> str: ...  # KitLockError when the lock is unreadable
```
<!-- fmt:on -->

Test helpers that later tasks extend: `github_fakes.py` holds `WORKER_ID = 101`, `REVIEWER_ID = 202`, `WORKER_INSTALLATION = 1001`, `REVIEWER_INSTALLATION = 2002`, `WORKER_PERMISSIONS`, `REVIEWER_PERMISSIONS`, `Call`, `Reply`, `FakeGitHub`, `FakeKeychain`, `git`, `files_containing` and `Remote`; `github_fixtures.py` holds the `app_keys`, `keychain`, `keychain_without_reviewer`, `github`, `isolated_home`, `remote`, `access` and `recorded_argv` fixtures. The `github` fixture registers the Apps with the slugs `rs-worker` and `rs-reviewer`.

- [ ] **Step 1: Add PyJWT to devctl and the dev group**

`--no-sync` keeps uv from creating a virtual environment inside the template directory.

```sh
uv add --no-sync --project rapid_ship/templates/common/tools/devctl "PyJWT[crypto]>=2.10,<3"
uv add --dev "PyJWT[crypto]>=2.10,<3"
uv lock --check --project rapid_ship/templates/common/tools/devctl
uv run rapid-ship sync --in-place
uv run pytest tests/test_kit_contents.py -q
```

Expected: both `pyproject.toml` files list `"pyjwt[crypto]>=2.10,<3"`; the template's `uv.lock` and the root `uv.lock` resolve PyJWT and cryptography; `sync` replaces `tools/devctl/pyproject.toml` and `tools/devctl/uv.lock`; the tests pass.

- [ ] **Step 2: Write the test helpers and copy the tests**

Create `tests/devctl/github_fakes.py`. Its routes, keys and git helpers are `901bd43`'s, without the pull-request routes, `Pulls`, the Claim helpers of `Remote` and the `GET /app` route that only `app_slug` used, and its installation reply now carries `app_slug`:

```python
"""Simulated GitHub, Keychain and repositories for offline devctl tests.

Nothing here contacts GitHub: a remote is a local bare repository.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import jwt

from devctl.github.app import KeychainMissing

# run_process is imported directly, so recorded_argv and fake_run never see test setup.
from devctl.process import run_process

WORKER_ID = 101
REVIEWER_ID = 202
WORKER_INSTALLATION = 1001
REVIEWER_INSTALLATION = 2002
# Spec 1 section 3's permission table, written out so tests do not compare the code with itself.
WORKER_PERMISSIONS = {
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "metadata": "read",
}
REVIEWER_PERMISSIONS = {"pull_requests": "write", "contents": "read", "metadata": "read"}
MAX_JWT_SECONDS = 600  # GitHub refuses an App JWT that lives longer than 10 minutes
_UNAUTHORIZED = (401, {"message": "A JSON web token could not be decoded"})
_NOT_FOUND = (404, {"message": "Not Found"})


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: Any


Reply = tuple[Any, ...]  # (status, body) or (status, body, headers)
Handler = Callable[[Call, re.Match[str]], Reply]


@dataclass(frozen=True)
class FakeApp:
    slug: str
    public_key_pem: bytes


@dataclass(frozen=True)
class FakeInstallation:
    installation_id: int
    permissions: dict[str, str]


class FakeGitHub:
    """GitHub's REST API, simulated on 127.0.0.1.

    Routes match the path with re.fullmatch; the most recently added route wins. Two generic
    routes answer for the Apps that add_app registers and install installs: a repository's
    installation, and installation token mints. Each needs a valid App JWT. A test adds any other
    route it needs with route().
    """

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.routes: list[tuple[str, re.Pattern[str], Handler]] = []
        self.apps: dict[int, FakeApp] = {}
        self.installations: dict[tuple[int, str], FakeInstallation] = {}
        self.issued_tokens: list[str] = []
        fake = self

        class _Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                call = Call(
                    self.command,
                    parts.path,
                    parse_qs(parts.query),
                    dict(self.headers.items()),
                    json.loads(raw) if raw else None,
                )
                fake.calls.append(call)
                status, body, headers = fake.reply(call)
                data = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = _serve

            def log_message(self, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        # A short poll interval makes close() return at once; the default 0.5 s costs every test.
        serve = self.server.serve_forever
        threading.Thread(target=serve, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.route("GET", r"/repos/([^/]+/[^/]+)/installation", self._installation)
        self.route("POST", r"/app/installations/(\d+)/access_tokens", self._access_token)

    def add_app(self, app_id: int, slug: str, public_key_pem: bytes) -> None:
        self.apps[app_id] = FakeApp(slug, public_key_pem)

    def install(
        self, app_id: int, repository: str, permissions: dict[str, str], installation_id: int
    ) -> None:
        self.installations[(app_id, repository)] = FakeInstallation(
            installation_id, dict(permissions)
        )

    def uninstall(self, app_id: int, repository: str) -> None:
        """Remove the App's installation on repository, as the owner's uninstall does."""
        del self.installations[(app_id, repository)]

    def jwt_app_id(self, call: Call) -> int | None:
        """The App whose JWT authorises call, or None when the JWT is missing or invalid.

        The issuer is read unverified only to pick the App's public key; the signature, iat, exp
        and iss are then verified with it, and the JWT may live at most 10 minutes.
        """
        scheme, _, token = call.headers.get("Authorization", "").partition(" ")
        if scheme != "Bearer" or not token:
            return None
        try:
            app_id = int(jwt.decode(token, options={"verify_signature": False})["iss"])
            claims = jwt.decode(
                token,
                self.apps[app_id].public_key_pem,
                algorithms=["RS256"],
                options={"require": ["iat", "exp", "iss"]},
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            return None
        return app_id if claims["exp"] - claims["iat"] <= MAX_JWT_SECONDS else None

    def _installation(self, call: Call, match: re.Match[str]) -> Reply:
        app_id = self.jwt_app_id(call)
        if app_id is None:
            return _UNAUTHORIZED
        found = self.installations.get((app_id, match[1]))
        if found is None:
            return _NOT_FOUND
        return 200, {
            "id": found.installation_id,
            "app_id": app_id,
            "app_slug": self.apps[app_id].slug,
            "permissions": found.permissions,
            "repository_selection": "selected",
        }

    def _access_token(self, call: Call, match: re.Match[str]) -> Reply:
        app_id = self.jwt_app_id(call)
        if app_id is None:
            return _UNAUTHORIZED
        owned = {
            found.installation_id
            for (owner, _), found in self.installations.items()
            if owner == app_id
        }
        if int(match[1]) not in owned:
            return _NOT_FOUND
        # Longer than 40 characters, like GitHub's stateless token format.
        token = "ghs_" + secrets.token_urlsafe(64)
        self.issued_tokens.append(token)
        expires = datetime.now(UTC) + timedelta(hours=1)
        return 201, {
            "token": token,
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "permissions": (call.body or {}).get("permissions"),
        }

    def route(self, method: str, pattern: str, handler: Handler) -> None:
        self.routes.append((method, re.compile(pattern), handler))

    def reply(self, call: Call) -> tuple[int, Any, dict[str, str]]:
        for method, pattern, handler in reversed(self.routes):
            match = pattern.fullmatch(call.path)
            if method == call.method and match:
                answer = handler(call, match)
                headers: dict[str, str] = answer[2] if len(answer) > 2 else {}
                return answer[0], answer[1], headers
        return 404, {"message": "Not Found"}, {}

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class FakeKeychain:
    """The macOS Keychain, simulated: generic-password items by service name."""

    def __init__(self, items: dict[str, bytes]) -> None:
        self.items = dict(items)

    def read(self, service: str) -> bytes:
        try:
            return self.items[service]
        except KeyError:
            raise KeychainMissing(f"Keychain item {service} not found") from None


GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def git(cwd: Path, *args: str) -> str:
    """Run git for test setup with a fixed identity; assert it succeeds and return its output."""
    result = run_process(["git", *args], cwd, 60, env=GIT_IDENTITY)
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}"
    return result.stdout.strip()


def files_containing(root: Path, needle: str) -> list[Path]:
    """Every regular, non-symlink file under root whose bytes contain needle, sorted.

    Used to prove a secret reached no file: root is a test's tmp_path, which holds the isolated
    HOME, the bare repository, the clone and every .git directory.
    """
    data = needle.encode()
    found: list[Path] = []
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory, name)
            if path.is_symlink() or not path.is_file():
                continue
            if data in path.read_bytes():
                found.append(path)
    return sorted(found)


@dataclass(frozen=True)
class Remote:
    """A local bare repository in GitHub's place, and a clone of it with main pushed.

    Each method runs git outside the clone, so rules a test writes into the clone's git config,
    such as insteadOf, never apply to it.
    """

    bare: Path
    clone: Path
    git_common_dir: Path  # the clone's resolved .git, as Repo.discover(clone) reports it

    def branch(self, name: str) -> str | None:
        """The branch's head on the bare repository, or None when it has no such branch."""
        listed = git(self.bare, "ls-remote", "--heads", str(self.bare))
        for line in listed.splitlines():
            sha, _, ref = line.partition("\t")
            if ref == f"refs/heads/{name}":
                return sha
        return None

    def commit_on(self, branch: str, message: str) -> str:
        """Commit a new file on the bare repository's branch from a temporary clone; return it."""
        with tempfile.TemporaryDirectory(dir=self.bare.parent) as scratch:
            work = Path(scratch) / "c"
            git(self.bare.parent, "clone", "-q", "--branch", branch, str(self.bare), str(work))
            # A new file makes each commit distinct, even with its parent, message and second
            # shared with another.
            (work / f"{secrets.token_hex(4)}.txt").write_text(message + "\n")
            git(work, "add", "--all")
            git(work, "commit", "-q", "-m", message)
            git(work, "push", "-q", "origin", f"HEAD:refs/heads/{branch}")
            return git(work, "rev-parse", "HEAD")

    def commit_in(self, worktree: Path, message: str) -> str:
        """Commit a new file in the worktree and return the new HEAD."""
        (worktree / f"{secrets.token_hex(4)}.txt").write_text(message)
        git(worktree, "add", "--all")
        git(worktree, "commit", "-q", "-m", message)
        return git(worktree, "rev-parse", "HEAD")
```

Create `tests/devctl/github_fixtures.py`:

```python
"""Fixtures for the offline GitHub, doctor and devctl as tests. Loaded by tests/conftest.py."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from devctl import process
from devctl.github.app import GitHubAccess
from devctl.process import ProcessResult
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_INSTALLATION,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeKeychain,
    Remote,
    git,
)


@pytest.fixture(scope="session")
def app_keys() -> dict[str, tuple[bytes, bytes]]:
    """Throwaway RSA test keys, made in memory for this test session: {role: (private, public)}.

    No real App uses them, and nothing writes them to disk.
    """
    keys: dict[str, tuple[bytes, bytes]] = {}
    for role in ("worker", "reviewer"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        keys[role] = (private, public)
    return keys


@pytest.fixture
def keychain(app_keys: dict[str, tuple[bytes, bytes]]) -> FakeKeychain:
    """Both test keys under the Keychain services that rapid-ship app writes."""
    return FakeKeychain(
        {
            "rapid-ship/worker-app": app_keys["worker"][0],
            "rapid-ship/reviewer-app": app_keys["reviewer"][0],
        }
    )


@pytest.fixture
def keychain_without_reviewer(app_keys: dict[str, tuple[bytes, bytes]]) -> FakeKeychain:
    """A Keychain that holds only the Worker App's key."""
    return FakeKeychain({"rapid-ship/worker-app": app_keys["worker"][0]})


@pytest.fixture
def github(app_keys: dict[str, tuple[bytes, bytes]]) -> Iterator[FakeGitHub]:
    """Simulated GitHub with the Worker App and the Reviewer App, both installed on o/r."""
    fake = FakeGitHub()
    fake.add_app(WORKER_ID, "rs-worker", app_keys["worker"][1])
    fake.add_app(REVIEWER_ID, "rs-reviewer", app_keys["reviewer"][1])
    fake.install(WORKER_ID, "o/r", WORKER_PERMISSIONS, WORKER_INSTALLATION)
    fake.install(REVIEWER_ID, "o/r", REVIEWER_PERMISSIONS, REVIEWER_INSTALLATION)
    yield fake
    fake.close()


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HOME in tmp_path, so git never reads the owner's ~/.gitconfig.

    Not autouse: integration tests that run uv need the real HOME for its cache.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def remote(tmp_path: Path, isolated_home: Path) -> Remote:
    """A bare repository at tmp_path/remote.git and its clone at tmp_path/work/r.

    The clone has one commit on main, pushed.
    """
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "--initial-branch=main", str(bare))
    clone = tmp_path / "work" / "r"
    clone.parent.mkdir()
    git(clone.parent, "clone", "-q", str(bare), str(clone))
    git(clone, "symbolic-ref", "HEAD", "refs/heads/main")
    git(clone, "commit", "-q", "--allow-empty", "-m", "Initial commit")
    git(clone, "push", "-q", "-u", "origin", "main")
    return Remote(bare, clone, (clone / ".git").resolve())


@pytest.fixture
def access(github: FakeGitHub, remote: Remote, keychain: FakeKeychain) -> GitHubAccess:
    """o/r on the simulated GitHub, its git remote the bare repository, its keys the test keys."""
    return GitHubAccess("o/r", api_url=github.url, remote_url=str(remote.bare), keychain=keychain)


@pytest.fixture
def recorded_argv(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Every argv passed to devctl.process.run_process, in order. Each process still runs."""
    seen: list[list[str]] = []
    real = process.run_process

    def record(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        seen.append(list(argv))
        return real(argv, cwd, timeout_seconds, env=env, input_text=input_text)

    monkeypatch.setattr(process, "run_process", record)
    return seen
```

Load the fixtures from the only conftest. In `tests/conftest.py`, replace:

<!-- fmt:off -->
```python
from devctl.process import run_process

```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
from devctl.process import run_process

pytest_plugins = ["github_fixtures"]

```
<!-- fmt:on -->

Copy the tests. Drop the parity test, which needs `rapid-ship app` and returns in Task 7, and the tests of `GitHubApi.paginate`, `app_slug` and `GitHubAccess.slug`, which only the commands this plan leaves behind called (Step 4 deletes them):

```sh
for name in test_devctl_github_api test_devctl_github_api_limits test_devctl_github_app test_devctl_github_app_limits test_devctl_askpass test_devctl_askpass_limits test_devctl_kit_step; do
  git show "901bd43:tests/devctl/$name.py" > "tests/devctl/$name.py"
done
perl -0pi -e 's/\n\n\ndef test_rapid_ship_and_devctl_agree_on_services_and_permissions\(\).*\z/\n/s' tests/devctl/test_devctl_github_app.py
perl -0pi -e 's/\n    app_slug,\n/\n/; s/\n\n\ndef test_app_slug_comes_from_the_app_itself\(.*?(?=\n\n\ndef )//s' tests/devctl/test_devctl_github_app.py
perl -0pi -e 's/\n\n\ndef test_paginate_follows_next_links_on_the_same_host_only\(.*?(?=\n\n\ndef )//s' tests/devctl/test_devctl_github_api.py
perl -0pi -e 's/\n\n\ndef test_a_list_with_more_pages_than_the_cap_is_an_error_not_a_short_list\(.*?(?=\n\n\ndef )//s; s/\n\n\ndef test_a_next_link_with_a_bad_port_leaves_the_host_instead_of_raising_value_error\(.*?(?=\n\n\ndef )//s' tests/devctl/test_devctl_github_api_limits.py
perl -0pi -e 's/\n    assert access\.slug\("worker", WORKER_ID\) == "rs-worker"\n/\n/' tests/devctl/test_devctl_github_app_limits.py
! grep -nE "from rapid_ship|import rapid_ship|test_rapid_ship_and_devctl_agree" tests/devctl/test_devctl_github_app.py
! grep -nE "paginate|app_slug|\.slug\(" tests/devctl/test_devctl_github_*.py
```

Expected: both `grep` commands find nothing. `test_missing_key_message_names_the_tagged_rapid_ship_command` stays: it names the command, not the package.

`test_devctl_kit_step.py` now expects the kit step's hint to name the full tagged command, `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.2.0 rapid-ship sync`.

Append to `tests/test_kit_contents.py`:

<!-- fmt:off -->
```python


def test_askpass_is_written_executable() -> None:
    # init and sync set the executable bit only for paths kit.toml lists (plan 2).
    assert "tools/devctl/devctl/github/askpass.py" in load_manifest().executable
```
<!-- fmt:on -->

- [ ] **Step 3: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_github_api.py -q`
Expected: pytest stops while loading its plugins, with `Error importing plugin "github_fixtures": No module named 'devctl.github'`.

- [ ] **Step 4: Copy the client, the token code and the helper, then trim**

```sh
T=rapid_ship/templates/common/tools/devctl/devctl
mkdir -p $T/github
for name in __init__.py api.py askpass.py app.py; do
  git show "901bd43:$T/github/$name" > "$T/github/$name"
done
git show "620e5ff:$T/check/kit.py" > "$T/check/kit.py"
```

`check/kit.py` at `620e5ff` adds `RAPID_SHIP_SOURCE`, `_Lock`, `_lock` and `rapid_ship_command`, and makes a missing managed file's message name both full `sync` commands.

In `$T/github/app.py`, replace everything above `class DevctlError(Exception):` with:

```python
"""GitHub App keys, App JWTs, installation tokens and token-bearing git.

Each App's private key lives in the macOS Keychain. A command reads it, signs a short-lived JWT
and mints one installation token, restricted to one repository and the App's permissions. Keys
and tokens stay in memory: nothing here writes one to disk, puts one in argv or prints one.
git receives a token only from askpass.py, through the environment of that one git command.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import jwt
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from devctl import process
from devctl.check.kit import KitLockError, rapid_ship_command
from devctl.github import askpass
from devctl.github.api import API_URL, GitHubApi, GitHubError, json_object
from devctl.process import ProcessResult
from devctl.settings import ProjectSettings, Role, SettingsError

KEYCHAIN_SERVICE: dict[Role, str] = {
    "worker": "rapid-ship/worker-app",
    "reviewer": "rapid-ship/reviewer-app",
}
# Spec 1 section 3. Every token asks for exactly these, never the installation's whole grant.
APP_PERMISSIONS: dict[Role, dict[str, str]] = {
    "worker": {
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "metadata": "read",
    },
    "reviewer": {"pull_requests": "write", "contents": "read", "metadata": "read"},
}
_KEYCHAIN_TIMEOUT_SECONDS = 120.0
_ITEM_NOT_FOUND = 44  # the exit code of `security find-generic-password` for a missing item
_REWRITE_RULES = r"^url\..*\.(push)?insteadof$"  # git lowercases section and key names
```

Then delete the Claim-only git helpers at the end of the file, from `@dataclass(frozen=True)` above `class PushOutcome:` to the last line, and use the index's `Role`. Delete `app_slug` and `GitHubAccess.slug`, which only `review.py` called, and from `api.py` delete `GitHubApi.paginate` with `_same_host`, `MAX_PAGES`, `_NEXT`, `import re` and `_Response.link`, which only `claims.py` and `review.py` used: a token-bearing helper that follows `next` links has no caller here. Then check what is left:

```sh
perl -0pi -e 's/\n\n\n\@dataclass\(frozen=True\)\nclass PushOutcome:.*\z/\n/s' $T/github/app.py
perl -pi -e 's/\bAppRole\b/Role/g' $T/github/app.py
perl -0pi -e 's/\n\n\ndef app_slug\(.*?(?=\n\n\n\@dataclass)//s; s/\n\n    def slug\(self, role: Role, app_id: int\) -> str:\n[^\n]*\n/\n/' $T/github/app.py
perl -0pi -e 's/\nimport re\n/\n/; s/\nMAX_PAGES = [^\n]*\n/\n/; s/\n_NEXT = [^\n]*\n/\n/; s/\n    link: str \| None\n/\n/; s/, reply\.getheader\("Link"\), data\)/, data)/; s/\n    def paginate\(.*?(?=\n    def _send\()//s' $T/github/api.py
! grep -nE "AppRole|PushOutcome|push_ref|fetch_ref|default_head|ls_remote_heads|remote_default_branch|Literal|app_slug|def slug" $T/github/app.py
! grep -nE "paginate|_same_host|MAX_PAGES|_NEXT|getheader|^import re" $T/github/api.py
tail -4 $T/github/app.py
```

Expected: both `grep` commands find nothing, and `app.py` ends with `run_git`'s `return process.run_process(...)`.

In `rapid_ship/templates/kit.toml`, replace:

```toml
executable = ["devctl", ".githooks/pre-commit"]
```

with:

```toml
executable = ["devctl", ".githooks/pre-commit", "tools/devctl/devctl/github/askpass.py"]
```

Format, check and vendor:

```sh
uv run ruff format $T/github $T/check/kit.py
uv run ruff check $T/github $T/check/kit.py
uv run rapid-ship sync --in-place
ls -l tools/devctl/devctl/github/askpass.py
```

Expected: `sync` adds the four `github/` files and replaces `check/kit.py`; `askpass.py` is executable (`-rwxr-xr-x`).

- [ ] **Step 5: Run the tests and see them pass**

```sh
uv run pytest tests/devctl/test_devctl_github_api.py tests/devctl/test_devctl_github_api_limits.py tests/devctl/test_devctl_github_app.py tests/devctl/test_devctl_github_app_limits.py tests/devctl/test_devctl_askpass.py tests/devctl/test_devctl_askpass_limits.py tests/devctl/test_devctl_kit_step.py tests/test_kit_contents.py -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run rapid-ship status --strict
```

Expected: every test passes; Ruff and mypy report nothing; status exits 0.

- [ ] **Step 6: Commit**

```sh
git add -A rapid_ship/templates tools/devctl .rapid-ship/kit.lock pyproject.toml uv.lock tests
git commit -m "feat: mint App installation tokens and pass them to git through askpass" -m "Copied from codex/github-commands (1eb138d, 620e5ff, f5177ba, ebe3bd2) without the Claim-only git helpers; tests use a fake GitHub on 127.0.0.1, a fake Keychain and local bare repositories." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: doctor's core and local items

doctor's toolchain, guardrails and Kit items come over from `0c2b27f` and `51c9300` without the Linear item. The follow-ups removed doctor's Harness sign-in items after the owner descoped several Providers. `harness.py` comes over whole, with the skills parsers Task 6 uses, and its tests. On #32, follow-up 9 keeps Claude Code's probe alone and drops `harness.py`'s import of `Harness`, which #31 deleted.

**Files:**
- Create: `rapid_ship/templates/common/tools/devctl/devctl/doctor.py`, `doctor_items.py`
- Create (copied, then edited): `rapid_ship/templates/common/tools/devctl/devctl/doctor_local.py`, `harness.py`
- Modify (copied): `rapid_ship/templates/common/tools/devctl/devctl/check/kit.py`, `check/stacks/python.py`
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/cli.py`
- Modify: `tests/devctl/github_fakes.py`, `tests/devctl/github_fixtures.py`
- Test (copied, then edited): `tests/devctl/test_devctl_doctor_local.py`, `test_devctl_doctor_local_limits.py`; (copied) `test_devctl_kit_summary.py`, `test_devctl_python_guardrails.py`, `test_devctl_python_guardrails_limits.py`, and `test_devctl_harness.py`, the index's name for `901bd43`'s `test_devctl_harness_skills.py`

**Interfaces:**
- Consumes: `ProjectSettings`, `Harness` (Task 2); `GitHubAccess`, `project_access`, `rapid_ship_command`, `KitLockError` (Task 3); `process.first_line` (Task 1).
- Produces (the index's doctor section):

<!-- fmt:off -->
```python
# devctl/doctor_items.py
Status = Literal["ok", "missing", "unknown"]
@dataclass(frozen=True)
class Item:
    area: str  # toolchain, guardrails, kit, github, agent identity, skills
    name: str
    status: Status
    detail: str
OwnerGet = Callable[[str], object]  # GET with the owner's gh sign-in; raises OwnerReadError
class OwnerReadError(Exception):  # .status: int | None, .message: str
    def __init__(self, status: int | None, message: str) -> None: ...
@dataclass(frozen=True)
class DoctorContext:
    root: Path
    project: ProjectSettings
    owner_get: OwnerGet
    access: GitHubAccess | None  # None while Agent identity is off
def gh_get(path: str) -> object: ...
def run_installed(tool: str, *args: str, cwd: Path | None = None, timeout: float = 30.0) -> ProcessResult | None: ...
def finished(result: ProcessResult) -> bool: ...

# devctl/doctor_local.py
CI_JOB_NAME = "devctl check"
def git_item() -> Item: ...
def local_items(ctx: DoctorContext) -> list[Item]: ...
def devctl_exclusion_gaps(pyproject: Mapping[str, object], *, python: bool) -> list[str]: ...

# devctl/harness.py
HarnessName = Harness
PROBE_MODELS: dict[HarnessName, str]
PROBE_TIMEOUT_SECONDS = 120.0
def skills_args(harness: HarnessName) -> list[str]: ...
def parse_skills(harness: HarnessName, result: ProcessResult) -> SkillReport: ...  # .names, .error

# devctl/check/kit.py
def kit_summary(root: Path, excluded: Sequence[str]) -> KitSummary: ...

# devctl/doctor.py
def doctor_exit_code(items: Sequence[Item]) -> int: ...
def run_doctor(ctx: DoctorContext) -> int: ...
def doctor_command(args: argparse.Namespace) -> int: ...
def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None: ...
```
<!-- fmt:on -->

Test helpers added: `github_fakes.py` gains `MakeContext`, `RecordedOwner`, `FakeRun`, `FakeHarness` and `RepoFiles`; `github_fixtures.py` gains `project` (o/r and both Apps, so Agent identity is on), `fake_run`, `fake_harness`, `no_owner_reads`, `ctx` and `repo_files`.

- [ ] **Step 1: Write the failing tests**

Extend the test helpers. Make these edits:

In `tests/devctl/github_fakes.py`, replace:

```python
import json
import os
import re
import secrets
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
```

with:

```python
import hashlib
import json
import os
import re
import secrets
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
```

In `tests/devctl/github_fakes.py`, replace:

```python
from devctl.github.app import KeychainMissing

# run_process is imported directly, so recorded_argv and fake_run never see test setup.
from devctl.process import run_process
```

with:

```python
from devctl.doctor_items import DoctorContext, OwnerReadError
from devctl.github.app import KeychainMissing

# run_process is imported directly, so recorded_argv and fake_run never see test setup.
from devctl.process import ProcessResult, run_process
```

In `tests/devctl/github_fakes.py`, replace:

```python
Reply = tuple[Any, ...]  # (status, body) or (status, body, headers)
Handler = Callable[[Call, re.Match[str]], Reply]
```

with:

```python
Reply = tuple[Any, ...]  # (status, body) or (status, body, headers)
Handler = Callable[[Call, re.Match[str]], Reply]
MakeContext = Callable[..., DoctorContext]
```

In `tests/devctl/github_fixtures.py`, replace:

```python
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
```

with:

```python
from __future__ import annotations

import dataclasses
import os
import shutil
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
```

In `tests/devctl/github_fixtures.py`, replace:

```python
from devctl import process
from devctl.github.app import GitHubAccess
from devctl.process import ProcessResult
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_INSTALLATION,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeKeychain,
    Remote,
    git,
)
```

with:

```python
from check_workspace import project_settings
from devctl import process
from devctl.doctor_items import DoctorContext, OwnerReadError
from devctl.github.app import GitHubAccess
from devctl.process import ProcessResult
from devctl.settings import App, ProjectSettings
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_INSTALLATION,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeHarness,
    FakeKeychain,
    FakeRun,
    MakeContext,
    Remote,
    RepoFiles,
    git,
)
```

Append `RecordedOwner` and the doctor fakes to `github_fakes.py`, unchanged from `901bd43`, and format:

```sh
F=tests/devctl/github_fakes.py
{ printf '\n\n'; git show 901bd43:$F | sed -n '392,415p'; printf '\n\n'; git show 901bd43:$F | sed -n '595,723p'; } >> $F
grep -nE "^class (RecordedOwner|FakeRun|FakeHarness|RepoFiles)" $F
```

Expected: the four classes, each once. Lines 392 to 415 hold `RecordedOwner`; lines 595 to 723 hold `FakeRun`, `FakeHarness` and `RepoFiles`.

Append to `tests/devctl/github_fixtures.py`:

```python
@pytest.fixture
def project() -> ProjectSettings:
    """o/r with both Apps recorded, so Agent identity is on."""
    return project_settings(
        repository="o/r",
        worker_app=App(WORKER_ID, "rs-worker"),
        reviewer_app=App(REVIEWER_ID, "rs-reviewer"),
    )


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    """Patch process.run_process and shutil.which. Nothing a test starts through devctl runs."""
    fake = FakeRun()
    monkeypatch.setattr(process, "run_process", fake.run_process)
    monkeypatch.setattr(shutil, "which", fake.which)
    return fake


@pytest.fixture
def fake_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeHarness:
    """PATH holds only a directory of fake executables, /usr/bin and /bin, so no real Harness or
    gh is found."""
    directory = tmp_path / "harness-bin"
    directory.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join([str(directory), "/usr/bin", "/bin"]))
    return FakeHarness(directory)


def no_owner_reads(path: str) -> object:
    raise OwnerReadError(None, "no owner reads in this test")


@pytest.fixture
def ctx(tmp_path: Path, isolated_home: Path, project: ProjectSettings) -> MakeContext:
    """Make DoctorContexts for a temporary repository on main, with no access and no owner reads.

    excluded replaces project.excluded, as load_project would from [kit] exclude.
    """
    root = tmp_path / "doctor-repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")

    def make(*, excluded: Sequence[str] = ()) -> DoctorContext:
        settings = dataclasses.replace(project, excluded=tuple(excluded))
        return DoctorContext(root, settings, no_owner_reads, None)

    return make


@pytest.fixture
def repo_files(ctx: MakeContext) -> RepoFiles:
    """Writes into ctx's repository, and git adds what it writes."""
    context = ctx()
    return RepoFiles(context.root, context.project.stack)
```

Copy the tests:

```sh
for name in test_devctl_doctor_local test_devctl_doctor_local_limits test_devctl_kit_summary test_devctl_python_guardrails test_devctl_python_guardrails_limits; do
  git show "901bd43:tests/devctl/$name.py" > "tests/devctl/$name.py"
done
git show 901bd43:tests/devctl/test_devctl_harness_skills.py > tests/devctl/test_devctl_harness.py
```

Reshape the two doctor test files to no Linear item. The follow-ups removed the claude, codex and agy sign-in tests, with the edits this step made to them, after the owner descoped several Providers; they moved `test_agy_is_probed_inside_another_coding_session` to the `--skills` tests, and follow-up 9 removed it with the agy probe on #32 (c05e443).

In `tests/devctl/test_devctl_doctor_local.py`, replace:

```python
import argparse
from pathlib import Path

import pytest

from devctl.check.stacks.agnostic import GITLEAKS_VERSION
from devctl.doctor import (
    AGY_PROBE_ARGS,
    Item,
```

with:

```python
import argparse
import dataclasses
from pathlib import Path

import pytest

from devctl import doctor
from devctl.check.stacks.agnostic import GITLEAKS_VERSION
from devctl.doctor import (
    DoctorContext,
    Item,
```

In `tests/devctl/test_devctl_doctor_local.py`, replace:

```python
def test_hooks_ci_workflow_kit_and_issue_tracking(
```

with:

```python
def test_hooks_ci_workflow_and_kit(
```

In `tests/devctl/test_devctl_doctor_local.py`, replace:

```python
    linear = items["Linear team and project IDs"]
    assert (linear.area, linear.status) == ("issue tracking", "ok")
    assert "doctor cannot verify Linear" in linear.detail
```

with:

```python
    assert "Linear team and project IDs" not in items  # devctl never talks to the tracker
```

In `tests/devctl/test_devctl_doctor_local_limits.py`, replace:

```python
            ("kit", "Kit files"),
            ("issue tracking", "Linear team and project IDs"),
        ]
```

with:

```python
            ("kit", "Kit files"),
        ]
```

In `tests/devctl/test_devctl_doctor_local_limits.py`, delete:

```python
    @pytest.mark.parametrize(("team_id", "project_id"), [("", "p"), ("t", ""), (None, None)])
    def test_both_linear_ids_are_needed(
        self, ctx: MakeContext, fake_run: FakeRun, team_id: str | None, project_id: str | None
    ) -> None:
        context = adjusted(ctx(), linear_team_id=team_id, linear_project_id=project_id)
        item = by_name(local_items(context))["Linear team and project IDs"]
        assert (item.area, item.status) == ("issue tracking", "missing")
        assert "[linear] team_id and project_id in .rapid-ship/project.toml" in item.detail
```

In `tests/devctl/test_devctl_doctor_local_limits.py`, replace:

<!-- fmt:off -->
```python
        # Unanswered commands exit 1 with no output: gh sign-in, hooks, CI and Kit files are
        # missing, and gitleaks (no version printed) is unknown. With no repository, the GitHub
        # part is one missing item, printed after the local ones.
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        context = adjusted(ctx(), stack="agnostic", worker=None, reviewer=None, repository=None)
        assert run_doctor(context) == 2
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "ok  toolchain  git: 2.39.5"
        assert "missing  toolchain  gh sign-in: not signed in; run gh auth login" in lines
        assert "unknown  toolchain  gitleaks: gitleaks version gave no readable version" in lines
        assert (
            lines[-2]
            == "missing  github  repository: repository is not set in .rapid-ship/project.toml"
        )
        assert lines[-1] == "doctor: 5 ok, 5 missing, 1 unknown"
        assert len(lines) == 12
```
<!-- fmt:on -->

with:

```python
        # Unanswered commands exit 1 with no output: gh sign-in, hooks, CI and Kit files are
        # missing, and gitleaks (no version printed) is unknown.
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        context = adjusted(ctx(), stack="agnostic")
        assert run_doctor(context) == 2
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "ok  toolchain  git: 2.39.5"
        assert "missing  toolchain  gh sign-in: not signed in; run gh auth login" in lines
        assert "unknown  toolchain  gitleaks: gitleaks version gave no readable version" in lines
        assert lines[-1] == "doctor: 4 ok, 4 missing, 1 unknown"
        assert len(lines) == 10
```

In `tests/devctl/test_devctl_doctor_local_limits.py`, replace:

```python
        repo_files.write(
            ".rapid-ship/project.toml",
            'stack = "agnostic"\n\n[linear]\nteam_id = "t"\nproject_id = "p"\n',
        )
        repo_files.write(".rapid-ship/gate.toml", 'mode = "walk"\n')
```

with:

```python
        repo_files.write(".rapid-ship/project.toml", 'stack = "agnostic"\n')
```

In `tests/devctl/test_devctl_doctor_local_limits.py`, replace:

```python
        # The project names no repository, so GitHub's part is one missing item and the exit is 1.
        assert doctor_command(argparse.Namespace(skills=False)) == 1
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == "doctor: 10 ok, 1 missing, 0 unknown"
        assert lines[-2].startswith("missing  github  repository: ")
        assert all(line.startswith("ok  ") for line in lines[:-2])
```

with:

```python
        assert doctor_command(argparse.Namespace(skills=False)) == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == "doctor: 9 ok, 0 missing, 0 unknown"
        assert all(line.startswith("ok  ") for line in lines[:-1])
```

Append to `tests/devctl/test_devctl_doctor_local.py`:

```python
def test_doctor_reads_the_apps_only_with_agent_identity_on(
    ctx: MakeContext, fake_run: FakeRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    contexts: list[DoctorContext] = []

    def record(context: DoctorContext, *, skills: bool = False) -> int:
        contexts.append(context)
        return 0

    on = ctx().project
    off = dataclasses.replace(on, worker_app=None, reviewer_app=None)
    fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
    monkeypatch.chdir(ctx().root)
    monkeypatch.setattr(doctor, "run_doctor", record)
    for settings in (on, off):
        monkeypatch.setattr(doctor, "load_project", lambda root, found=settings: found)
        assert doctor.doctor_command(argparse.Namespace(skills=False)) == 0
    [with_apps, without_apps] = contexts
    assert with_apps.access is not None
    assert with_apps.access.repository == "o/r"
    assert without_apps.access is None
```

Format the edited helpers and tests:

```sh
uv run ruff format tests/devctl/github_fakes.py tests/devctl/github_fixtures.py tests/devctl/test_devctl_doctor_local.py tests/devctl/test_devctl_doctor_local_limits.py
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_doctor_local.py -q`
Expected: pytest stops while loading its plugins, with `No module named 'devctl.doctor_items'`.

- [ ] **Step 3: Write doctor's core and local items**

Copy the Kit summary, the Python floor, the Harness probes and the local items:

```sh
T=rapid_ship/templates/common/tools/devctl/devctl
for name in check/kit.py check/stacks/python.py harness.py doctor_local.py; do
  git show "901bd43:$T/$name" > "$T/$name"
done
```

`check/kit.py` at `901bd43` adds `KitSummary` and `kit_summary` to Task 3's version; `check/stacks/python.py` adds `guardrail_gaps`, `toml_table`, `toml_strings` and `pytest_addopts`. Then make these edits, which drop the Linear item, describe any Provider's quota, point the probe models at this plan's live trial and register the command:

In `rapid_ship/templates/common/tools/devctl/devctl/doctor_local.py`, replace:

```python
"""doctor's local items: the toolchain, Harness sign-ins, guardrails, Kit files and issue tracking.
```

with:

```python
"""doctor's local items: the toolchain, guardrails and Kit files.
```

In `rapid_ship/templates/common/tools/devctl/devctl/doctor_local.py`, delete:

```python
from devctl.settings import ProjectSettings
```

In `rapid_ship/templates/common/tools/devctl/devctl/doctor_local.py`, delete:

```python
def _linear_item(project: ProjectSettings) -> Item:
    name = "Linear team and project IDs"
    if project.linear_team_id and project.linear_project_id:
        detail = (
            "Linear team and project IDs are set; doctor cannot verify Linear, "
            "rs-setup verifies it through Linear's MCP"
        )
        return Item("issue tracking", name, "ok", detail)
    detail = (
        "set [linear] team_id and project_id in .rapid-ship/project.toml; rs-setup records them"
    )
    return Item("issue tracking", name, "missing", detail)
```

In `rapid_ship/templates/common/tools/devctl/devctl/doctor_local.py`, replace:

```python
    """Every item that needs no GitHub: toolchain, guardrails, Kit and issue tracking."""
```

with:

```python
    """Every item that needs no GitHub: the toolchain, guardrails and Kit files."""
```

In `rapid_ship/templates/common/tools/devctl/devctl/doctor_local.py`, replace:

<!-- fmt:off -->
```python
        _kit_item(ctx),
        _linear_item(ctx.project),
```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
        _kit_item(ctx),
```
<!-- fmt:on -->

In `rapid_ship/templates/common/tools/devctl/devctl/harness.py`, replace:

```python
doctor spends a little of the owner's subscription quota to prove a sign-in, and with --skills to
ask which skills a Harness loads. Each Harness runs its cheapest model.
```

with:

```python
doctor spends a little of the owner's quota, whatever the Provider, with --skills to ask which
skills a Harness loads. Each Harness runs its cheapest model.
```

In `rapid_ship/templates/common/tools/devctl/devctl/harness.py`, replace:

```python
# The cheapest model per Harness in plan 4's Checked facts. The owner confirms each one live in
# Task 13 Step 1 and Task 15 Step 1.
```

with:

```python
# The cheapest model per Harness, as the Checked facts of plan 4 (Doctor and Agent identity)
# record it. That plan's live trial confirms each one.
```

In `rapid_ship/templates/common/tools/devctl/devctl/cli.py`, replace:

```python
from devctl import __version__
```

with:

```python
from devctl import __version__, doctor
```

In `rapid_ship/templates/common/tools/devctl/devctl/cli.py`, replace:

```python
    check.set_defaults(handler=check_command)
    devctl_project.register(commands)
```

with:

```python
    check.set_defaults(handler=check_command)
    doctor.register(commands)
    devctl_project.register(commands)
```

Create `$T/doctor_items.py`:

```python
"""What every doctor item shares: its type, its context, and the owner's one way to read GitHub.

doctor reads GitHub with the owner's gh sign-in, always as GET (gh api defaults to POST once it
is given a field).
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from devctl import process
from devctl.github.app import GitHubAccess
from devctl.process import ProcessResult
from devctl.settings import ProjectSettings

Status = Literal["ok", "missing", "unknown"]
TOOL_TIMEOUT_SECONDS = 30.0
_GH_TIMEOUT_SECONDS = 60.0
_HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")


@dataclass(frozen=True)
class Item:
    area: str  # toolchain, guardrails, kit, github, agent identity, skills
    name: str
    status: Status
    detail: str


OwnerGet = Callable[[str], object]  # GET with the owner's gh sign-in; raises OwnerReadError


class OwnerReadError(Exception):
    """gh could not read a path: its HTTP status when it printed one, and what it said."""

    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class DoctorContext:
    root: Path
    project: ProjectSettings
    owner_get: OwnerGet
    access: GitHubAccess | None  # None while Agent identity is off


def _json_message(stdout: str) -> str:
    """The `message` of the JSON body that gh api printed for a failed request, or ""."""
    try:
        body = json.loads(stdout)
    except ValueError:
        return ""
    message = body.get("message") if isinstance(body, dict) else None
    return process.first_line(message) if isinstance(message, str) else ""


def gh_get(path: str) -> object:
    """GET path with the owner's gh sign-in and return the parsed JSON. Raises OwnerReadError."""
    try:
        result = process.run_process(
            ["gh", "api", "--method", "GET", path], Path(tempfile.gettempdir()), _GH_TIMEOUT_SECONDS
        )
    except OSError:  # gh is not installed, or cannot start
        raise OwnerReadError(None, "gh could not start") from None
    if result.timed_out:
        raise OwnerReadError(None, "gh api timed out")
    if result.stdout_truncated:
        raise OwnerReadError(None, f"gh api output exceeded {process.MAX_OUTPUT_BYTES} bytes")
    if result.returncode != 0:
        status = _HTTP_STATUS.search(result.stderr)
        message = _json_message(result.stdout) or process.first_line(result.stderr)
        raise OwnerReadError(
            int(status[1]) if status else None, message or f"gh api exited {result.returncode}"
        )
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise OwnerReadError(None, "gh api printed no JSON") from None


def run_installed(
    tool: str, *args: str, cwd: Path | None = None, timeout: float = TOOL_TIMEOUT_SECONDS
) -> ProcessResult | None:
    """Run an installed tool; None when it is not on PATH.

    A tool that cannot start gets exit 126, as a shell reports one.
    """
    path = shutil.which(tool)
    if path is None:
        return None
    argv = [path, *args]
    try:
        return process.run_process(argv, cwd or Path(tempfile.gettempdir()), timeout)
    except OSError:
        return ProcessResult(argv, 126, "", "", 0.0)


def finished(result: ProcessResult) -> bool:
    """False for a command that timed out or whose output was cut: it proves nothing."""
    return not (result.timed_out or result.stdout_truncated or result.stderr_truncated)
```

The follow-ups removed `doctor_signin.py`, which this step created for the Harness sign-in items, with the agy sign-in probe's `AGY_PROBE_ARGS` and `SERVICE_ERROR` in `harness.py`, after the owner descoped several Providers.

Create `$T/doctor.py`:

```python
"""devctl doctor: report each item as ok, missing or unknown.

doctor_local.py builds the items for this machine and repository; doctor_items.py holds the
types they share and the owner's one way to read GitHub. This module runs them, prints them and
exits with the worst answer. It re-exports the names that tests import from devctl.doctor.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from devctl.doctor_items import DoctorContext as DoctorContext
from devctl.doctor_items import Item as Item
from devctl.doctor_items import OwnerGet as OwnerGet
from devctl.doctor_items import OwnerReadError as OwnerReadError
from devctl.doctor_items import Status as Status
from devctl.doctor_items import gh_get as gh_get
from devctl.doctor_local import DEVCTL_DIRECTORY as DEVCTL_DIRECTORY
from devctl.doctor_local import KIT_SOURCE as KIT_SOURCE
from devctl.doctor_local import devctl_exclusion_gaps as devctl_exclusion_gaps
from devctl.doctor_local import git_item as git_item
from devctl.doctor_local import local_items as local_items
from devctl.github.app import project_access
from devctl.repo import Repo
from devctl.settings import load_project

STATUSES: tuple[Status, ...] = ("ok", "missing", "unknown")


def doctor_exit_code(items: Sequence[Item]) -> int:
    """2 when any item is unknown, else 1 when any is missing, else 0."""
    statuses = {item.status for item in items}
    if "unknown" in statuses:
        return 2
    return 1 if "missing" in statuses else 0


def _report(items: Sequence[Item]) -> int:
    for item in items:
        sys.stdout.write(f"{item.status}  {item.area}  {item.name}: {item.detail}\n")
    ok, missing, unknown = (sum(i.status == status for i in items) for status in STATUSES)
    sys.stdout.write(f"doctor: {ok} ok, {missing} missing, {unknown} unknown\n")
    return doctor_exit_code(items)


def run_doctor(ctx: DoctorContext) -> int:
    """Print every item for ctx, then a summary line, and return the exit code."""
    return _report(local_items(ctx))


def doctor_command(args: argparse.Namespace) -> int:
    item = git_item()
    if item.status != "ok":
        # Every later item needs git rev-parse --path-format=absolute.
        return _report([item])
    repo = Repo.discover(Path.cwd())  # cli.main maps RepoError and SettingsError to exit 2
    project = load_project(repo.root)
    # doctor reads the Apps only while Agent identity is on (Spec 1 section 6).
    access = project_access(project) if project.agent_identity else None
    return run_doctor(DoctorContext(repo.root, project, gh_get, access))


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "doctor",
        help="Report what this machine and repository lack",
        description="Report each item as ok, missing or unknown. Exit 0 when every item is ok, "
        "1 when one is missing, 2 when one is unknown.",
    )
    parser.set_defaults(handler=doctor_command)
```

Format, check and vendor:

```sh
uv run ruff format $T/doctor.py $T/doctor_items.py $T/doctor_local.py $T/harness.py $T/cli.py $T/check
uv run ruff check $T/doctor.py $T/doctor_items.py $T/doctor_local.py $T/harness.py $T/cli.py $T/check
! grep -nE "Linear|linear|ADR 0001|subscription quota" $T/doctor*.py $T/harness.py
uv run rapid-ship sync --in-place
```

- [ ] **Step 4: Run the tests and see them pass**

```sh
uv run pytest tests/devctl/test_devctl_doctor_local.py tests/devctl/test_devctl_doctor_local_limits.py tests/devctl/test_devctl_kit_summary.py tests/devctl/test_devctl_python_guardrails.py tests/devctl/test_devctl_python_guardrails_limits.py tests/devctl/test_devctl_harness.py tests/devctl/test_devctl_kit_step.py -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run rapid-ship status --strict
./devctl doctor --help
```

Expected: every test passes; Ruff and mypy report nothing; status exits 0; doctor's help exits 0.

- [ ] **Step 5: Commit**

```sh
git add -A rapid_ship/templates tools/devctl .rapid-ship/kit.lock tests
git commit -m "feat: report the toolchain, guardrails and Kit files in devctl doctor" -m "Copied from codex/github-commands (0c2b27f, 51c9300) without the Linear item." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: doctor's GitHub items

The ruleset, CODEOWNERS, branch deletion and fork-approval items come over from `ebe3bd2`, reshaped to the Mode: the ruleset for Walk, for Flight with Agent identity and for Flight without it, and CODEOWNERS against `every_pr`. The App items appear only while Agent identity is on, in the area `agent identity`, and the installation item also checks the recorded slug.

**Files:**
- Create: `rapid_ship/templates/common/tools/devctl/devctl/doctor_rules.py`, `doctor_github.py`
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/doctor.py`
- Create (copied): `tests/devctl/fixtures/github/codeowners.json`, `fork-approval.json`, `repository.json`, `ruleset-list.json`, `ruleset.json`
- Modify: `tests/devctl/github_fixtures.py`, `tests/devctl/test_devctl_doctor_local_limits.py`
- Test (copied, then edited): `tests/devctl/test_devctl_doctor_github.py`, `test_devctl_doctor_github_limits.py`

**Interfaces:**
- Consumes: `DoctorContext`, `Item`, `OwnerReadError`, `CI_JOB_NAME` (Task 4); `installation`, `GitHubAccess`, `APP_PERMISSIONS`, `guarded_message`, `AppError`, `AppNotInstalled`, `KeychainMissing` (Task 3); `App`, `Role`, `Stack`, `PROJECT` (Task 2).
- Produces (the index's doctor section):

<!-- fmt:off -->
```python
# devctl/doctor_rules.py
ADMIN_ROLE_ID = 5
GITHUB_ACTIONS_APP_ID = 15368
# Codex's wiring adds .codex/, and agy's widens .agents/skills/ to .agents/
PROTECTED_PATHS: tuple[str, ...]
PYTHON_PROTECTED_PATHS: tuple[str, ...]
NO_APPROVAL = "no pull_request rule requires an approval"
def ruleset_problems(
    rulesets: Sequence[Mapping[str, object]],
    default_branch: str,
    *,
    every_pr: bool,
    agent_identity: bool,
) -> list[str]: ...  # plan 6's test checks rs-setup's ruleset.json with it
def codeowners_problems(text: str, every_pr: bool, owner: str, stack: Stack) -> list[str]: ...
def installation_problems(found: Mapping[str, object], role: Role) -> list[str]: ...

# devctl/doctor_github.py
def github_items(ctx: DoctorContext) -> list[Item]: ...

# devctl/doctor.py
def run_doctor(ctx: DoctorContext) -> int: ...  # local items, then GitHub items
```
<!-- fmt:on -->

`devctl.doctor` re-exports `github_items` and everything in `doctor_rules` above, as plan 6's ruleset test imports them from there. Test helpers added: the `recorded` fixture (the owner's recorded reads of o/r) and `ctx_github` (Walk, Agent identity on, o/r on the simulated GitHub).

- [ ] **Step 1: Write the failing tests**

Copy the recorded GitHub answers and the tests:

```sh
mkdir -p tests/devctl/fixtures/github
for name in codeowners fork-approval repository ruleset-list ruleset; do
  git show "901bd43:tests/devctl/fixtures/github/$name.json" > "tests/devctl/fixtures/github/$name.json"
done
for name in test_devctl_doctor_github test_devctl_doctor_github_limits; do
  git show "901bd43:tests/devctl/$name.py" > "tests/devctl/$name.py"
done
```

`ruleset.json` is the ruleset `rs-setup` applies (index, Ruleset): one active ruleset on `~DEFAULT_BRANCH`, approval count 1, code-owner review, stale approvals dismissed, last-push approval, review threads resolved, squash only, the `devctl check` status check from GitHub Actions, force pushes and deletion blocked, and only the admin role bypassing in pull-request mode.

Give every ruleset call the Mode and Agent identity of Walk, and turn the old Mode strings into `every_pr`:

```sh
perl -pi -e 's/ruleset_problems\((\[[^\]]*\]), "(\w+)"\)/ruleset_problems($1, "$2", every_pr=True, agent_identity=True)/g; s/"walk"/True/g; s/"flight"/False/g' tests/devctl/test_devctl_doctor_github.py tests/devctl/test_devctl_doctor_github_limits.py
! grep -nE '"walk"|"flight"|ruleset_problems\(\[[^]]*\], "[a-z]+"\)' tests/devctl/test_devctl_doctor_github.py tests/devctl/test_devctl_doctor_github_limits.py
```

Then make these edits, which also bring the two output tests of Task 4 to their final form, with the GitHub part printed after the local items:

In `tests/devctl/github_fixtures.py`, replace:

```python
import dataclasses
import os
```

with:

```python
import dataclasses
import json
import os
```

In `tests/devctl/github_fixtures.py`, replace:

<!-- fmt:off -->
```python
    MakeContext,
    Remote,
```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
    MakeContext,
    RecordedOwner,
    Remote,
```
<!-- fmt:on -->

In `tests/devctl/test_devctl_doctor_github.py`, replace:

```python
import copy
import json
```

with:

```python
import copy
import dataclasses
import json
```

In `tests/devctl/test_devctl_doctor_github.py`, replace:

```python
from devctl.process import ProcessResult
from devctl.records import gate_log_path
from devctl.repo import Repo
from github_fakes import FakeGitHub, FakeKeychain, FakeRun, MakeContext, RecordedOwner
```

with:

```python
from devctl.doctor_rules import NO_APPROVAL
from devctl.process import ProcessResult
from devctl.settings import App
from github_fakes import (
    REVIEWER_ID,
    FakeGitHub,
    FakeKeychain,
    FakeRun,
    MakeContext,
    RecordedOwner,
)
```

In `tests/devctl/test_devctl_doctor_github.py`, delete:

```python
    assert not gate_log_path(Repo.discover(ctx.root).git_common_dir).exists()
```

In `tests/devctl/test_devctl_doctor_github_limits.py`, replace:

<!-- fmt:off -->
```python
    PROTECTED_PATHS,
    DoctorContext,
    Item,
```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
    PROTECTED_PATHS,
    Item,
```
<!-- fmt:on -->

In `tests/devctl/test_devctl_doctor_github_limits.py`, replace:

<!-- fmt:off -->
```python
        (contents("* @O  # the owner\n"), "ok", "matches walk"),
```
<!-- fmt:on -->

with:

<!-- fmt:off -->
```python
        (contents("* @O  # the owner\n"), "ok", "matches Walk"),
```
<!-- fmt:on -->

In `tests/devctl/test_devctl_doctor_github_limits.py`, delete:

```python
def without_app_ids(context: DoctorContext) -> DoctorContext:
    project = dataclasses.replace(context.project, worker_app_id=None, reviewer_app_id=None)
    return dataclasses.replace(context, project=project)
```

In `tests/devctl/test_devctl_doctor_github_limits.py`, delete:

```python
def test_an_unset_app_id_is_missing_without_asking_github(
    ctx_github: MakeContext, github: FakeGitHub
) -> None:
    context = without_app_ids(ctx_github())
    items = by_name(github_items(context))
    for name in APP_ITEMS:
        assert items[name].status == "missing"
        assert "app_id" in items[name].detail
        assert "rs-setup" in items[name].detail
    assert github.calls == []
```

In `tests/devctl/test_devctl_doctor_local_limits.py`, replace:

```python
        # Unanswered commands exit 1 with no output: gh sign-in, hooks, CI and Kit files are
        # missing, and gitleaks (no version printed) is unknown.
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        context = adjusted(ctx(), stack="agnostic")
        assert run_doctor(context) == 2
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "ok  toolchain  git: 2.39.5"
        assert "missing  toolchain  gh sign-in: not signed in; run gh auth login" in lines
        assert "unknown  toolchain  gitleaks: gitleaks version gave no readable version" in lines
        assert lines[-1] == "doctor: 4 ok, 4 missing, 1 unknown"
        assert len(lines) == 10
```

with:

<!-- fmt:off -->
```python
        # Unanswered commands exit 1 with no output: gh sign-in, hooks, CI and Kit files are
        # missing, and gitleaks (no version printed) is unknown. With no repository, the GitHub
        # part is one missing item, printed after the local ones.
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        context = adjusted(
            ctx(), stack="agnostic", repository=None, worker_app=None, reviewer_app=None
        )
        assert run_doctor(context) == 2
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "ok  toolchain  git: 2.39.5"
        assert "missing  toolchain  gh sign-in: not signed in; run gh auth login" in lines
        assert "unknown  toolchain  gitleaks: gitleaks version gave no readable version" in lines
        assert (
            lines[-2]
            == "missing  github  repository: repository is not set in .rapid-ship/project.toml"
        )
        assert lines[-1] == "doctor: 4 ok, 5 missing, 1 unknown"
        assert len(lines) == 11
```
<!-- fmt:on -->

In `tests/devctl/test_devctl_doctor_local_limits.py`, replace:

```python
        assert doctor_command(argparse.Namespace(skills=False)) == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == "doctor: 9 ok, 0 missing, 0 unknown"
        assert all(line.startswith("ok  ") for line in lines[:-1])
```

with:

```python
        # The project names no repository, so GitHub's part is one missing item and the exit is 1.
        assert doctor_command(argparse.Namespace(skills=False)) == 1
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == "doctor: 9 ok, 1 missing, 0 unknown"
        assert lines[-2].startswith("missing  github  repository: ")
        assert all(line.startswith("ok  ") for line in lines[:-2])
```

Append to `tests/devctl/github_fixtures.py`:

```python
FIXTURES = Path(__file__).parent / "fixtures" / "github"


@pytest.fixture
def recorded() -> RecordedOwner:
    """The owner's gh reads of o/r, as GitHub answered on 2026-10-14. Other paths are a 404."""

    def fixture(name: str) -> object:
        return json.loads((FIXTURES / name).read_text())

    return RecordedOwner(
        {
            "repos/o/r": fixture("repository.json"),
            "repos/o/r/rulesets?targets=branch": fixture("ruleset-list.json"),
            "repos/o/r/rulesets/9": fixture("ruleset.json"),
            "repos/o/r/actions/permissions/fork-pr-contributor-approval": fixture(
                "fork-approval.json"
            ),
            "repos/o/r/contents/.github/CODEOWNERS?ref=main": fixture("codeowners.json"),
        }
    )


@pytest.fixture
def ctx_github(
    isolated_home: Path,
    project: ProjectSettings,
    github: FakeGitHub,
    keychain: FakeKeychain,
    recorded: RecordedOwner,
    repo_files: RepoFiles,
) -> MakeContext:
    """Make DoctorContexts for the temporary repository in Walk with Agent identity on, and o/r on
    the simulated GitHub. The owner reads are the recorded ones. keychain replaces the Keychain
    that holds both keys."""
    repo_files.lock(unchanged=[], missing=[])  # so a missing key can name rapid-ship app

    def make(*, keychain: FakeKeychain = keychain) -> DoctorContext:
        access = GitHubAccess("o/r", api_url=github.url, keychain=keychain)
        return DoctorContext(repo_files.root, project, recorded, access)

    return make
```

Append to `tests/devctl/test_devctl_doctor_github.py`:

```python
def relaxed_ruleset() -> dict[str, Any]:
    """rs-setup's ruleset without the review requirement, which Flight without Agent identity
    drops."""
    ruleset = copy.deepcopy(RULESET)
    rule(ruleset, "pull_request")["parameters"].update(
        required_approving_review_count=0,
        require_code_owner_review=False,
        require_last_push_approval=False,
    )
    return ruleset


def test_only_flight_without_agent_identity_accepts_no_review_requirement() -> None:
    relaxed = relaxed_ruleset()
    assert ruleset_problems([relaxed], "main", every_pr=False, agent_identity=False) == []
    assert ruleset_problems([RULESET], "main", every_pr=False, agent_identity=False) == []
    # The whole ruleset passes in Walk without Agent identity and in Flight with it too.
    for every_pr, agent_identity in ((True, False), (False, True)):
        full = ruleset_problems([RULESET], "main", every_pr=every_pr, agent_identity=agent_identity)
        assert full == []
    for every_pr, agent_identity in ((True, False), (True, True), (False, True)):
        problems = ruleset_problems(
            [relaxed], "main", every_pr=every_pr, agent_identity=agent_identity
        )
        assert NO_APPROVAL in problems
        assert any("code-owner review" in p for p in problems)


def test_the_relaxed_ruleset_still_needs_everything_else() -> None:
    relaxed = relaxed_ruleset()
    rule(relaxed, "pull_request")["parameters"].update(allowed_merge_methods=["merge"])
    assert ruleset_problems([relaxed], "main", every_pr=False, agent_identity=False) == [
        "the pull_request rule must allow squash merges only"
    ]
    relaxed["rules"] = [r for r in relaxed["rules"] if r["type"] != "pull_request"]
    assert ruleset_problems([relaxed], "main", every_pr=False, agent_identity=False) == [
        "the ruleset has no pull_request rule"
    ]


def test_doctor_calls_the_relaxed_ruleset_ok_only_in_flight_without_agent_identity(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve("repos/o/r/rulesets/9", relaxed_ruleset())
    context = ctx_github()
    walk = {i.name: i for i in github_items(context)}["ruleset"]
    escalation = dataclasses.replace(context.project.escalation, every_pr=False)
    on = dataclasses.replace(context.project, escalation=escalation)
    off = dataclasses.replace(on, worker_app=None, reviewer_app=None)
    with_identity = {i.name: i for i in github_items(dataclasses.replace(context, project=on))}
    flight = {i.name: i for i in github_items(dataclasses.replace(context, project=off))}
    assert walk.status == "missing"
    assert with_identity["ruleset"].status == "missing"
    assert flight["ruleset"].status == "ok"
    assert "without the review requirement" in flight["ruleset"].detail
    # Flight with Agent identity, the Mode Task 10's trial reaches, accepts the whole ruleset.
    recorded.serve("repos/o/r/rulesets/9", RULESET)
    with_identity = {i.name: i for i in github_items(dataclasses.replace(context, project=on))}
    assert with_identity["ruleset"].status == "ok"


def test_agent_identity_off_has_no_app_items_and_asks_github_nothing(
    ctx_github: MakeContext, github: FakeGitHub
) -> None:
    context = ctx_github()
    off = dataclasses.replace(context.project, worker_app=None, reviewer_app=None)
    items = github_items(dataclasses.replace(context, project=off, access=None))
    assert [i.name for i in items] == [
        "ruleset",
        "CODEOWNERS",
        "delete branch on merge",
        "fork PR workflow approval",
    ]
    assert {i.area for i in items} == {"github"}
    assert github.calls == []


def test_app_items_are_in_the_agent_identity_area(ctx_github: MakeContext) -> None:
    areas = {i.name: i.area for i in github_items(ctx_github())}
    assert areas["Worker App installation"] == areas["Reviewer App key"] == "agent identity"


def test_an_installed_app_whose_slug_differs_from_the_record_is_missing(
    ctx_github: MakeContext,
) -> None:
    context = ctx_github()
    project = dataclasses.replace(context.project, reviewer_app=App(REVIEWER_ID, "o-rs-reviewer"))
    items = {i.name: i for i in github_items(dataclasses.replace(context, project=project))}
    reviewer = items["Reviewer App installation"]
    assert reviewer.status == "missing"
    assert reviewer.detail == (
        "the installed App's slug is rs-reviewer, but .rapid-ship/project.toml records "
        "o-rs-reviewer"
    )
    assert items["Worker App installation"].status == "ok"
```

Format: `uv run ruff format tests/devctl`

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_doctor_github.py -q`
Expected: collection fails with `ImportError: cannot import name 'PROTECTED_PATHS' from 'devctl.doctor'`.

- [ ] **Step 3: Write the rules and the GitHub items**

Create `rapid_ship/templates/common/tools/devctl/devctl/doctor_rules.py`:

```python
"""What doctor expects of a ruleset, CODEOWNERS and an App installation.

These checks are pure: they take what GitHub returned and name each way it differs from Spec 1
section 3 (the Apps' permissions) and section 8 (the ruleset and CODEOWNERS). doctor_github.py
reads GitHub and builds the items; plan 6's test checks rs-setup's ruleset.json with
ruleset_problems.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from devctl.doctor_local import CI_JOB_NAME
from devctl.github.app import APP_PERMISSIONS
from devctl.settings import Role, Stack

ADMIN_ROLE_ID = 5  # the repository admin role; plan 4's live trial reads it back
GITHUB_ACTIONS_APP_ID = 15368  # gh api /apps/github-actions
# The Protected set of the seeded CODEOWNERS (Spec 1 section 4), in its order, with the devctl
# shim. Codex's wiring adds .codex/, and agy's widens .agents/skills/ to .agents/.
PROTECTED_PATHS = (
    ".github/",
    ".githooks/",
    "devctl",
    "tools/devctl/",
    ".agents/skills/",
    ".claude/",
    "**/AGENTS.md",
    "**/CLAUDE.md",
    ".rapid-ship/",
    ".gitleaks.toml",
    ".gitleaksignore",
    "zizmor.yml",
    "zizmor.yaml",
)
# The Python guardrail settings: every file Ruff, mypy, pytest and import-linter read settings
# from, in the template's last lines. Ruff reads the nearest ruff.toml, so those match at any depth.
PYTHON_PROTECTED_PATHS = (
    "pyproject.toml",
    "**/ruff.toml",
    "**/.ruff.toml",
    "mypy.ini",
    ".mypy.ini",
    "pytest.ini",
    ".pytest.ini",
    "pytest.toml",
    ".pytest.toml",
    "setup.cfg",
    "tox.ini",
    ".importlinter",
)
NO_APPROVAL = "no pull_request rule requires an approval"
NO_PULL_REQUEST_RULE = "the ruleset has no pull_request rule"
NO_RULESET = "no ruleset targets the default branch"
_COMMENT = re.compile(r"\s+#.*$")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: object) -> set[str]:
    return {s for s in value if isinstance(s, str)} if isinstance(value, list) else set()


def _target_problems(ruleset: Mapping[str, object], default_branch: str) -> list[str]:
    ref_name = _mapping(_mapping(ruleset.get("conditions")).get("ref_name"))
    names = {"~DEFAULT_BRANCH", "~ALL", f"refs/heads/{default_branch}"}
    if names & _strings(ref_name.get("include")) and not names & _strings(ref_name.get("exclude")):
        return []
    return ["the ruleset does not target the default branch"]


def _approves(count: object) -> bool:
    return isinstance(count, int) and not isinstance(count, bool) and count >= 1


def _pull_request_problems(params: Mapping[str, object], *, review: bool) -> list[str]:
    """The pull_request rule's problems. review=False leaves out the review requirement, which
    Flight without Agent identity drops: an approval, code-owner review and approval of the most
    recent push (Spec 1 section 8, step 8)."""
    holds = [
        (not review or _approves(params.get("required_approving_review_count")), NO_APPROVAL),
        (
            not review or params.get("require_code_owner_review") is True,
            "the pull_request rule does not require code-owner review",
        ),
        (
            params.get("dismiss_stale_reviews_on_push") is True,
            "the pull_request rule does not dismiss stale approvals on push",
        ),
        (
            not review or params.get("require_last_push_approval") is True,
            "the pull_request rule does not require approval of the most recent push",
        ),
        (
            params.get("allowed_merge_methods") == ["squash"],
            "the pull_request rule must allow squash merges only",
        ),
        (
            params.get("required_review_thread_resolution") is True,
            "the pull_request rule does not require review threads to be resolved",
        ),
    ]
    return [problem for ok, problem in holds if not ok]


def _status_check_problems(params: Mapping[str, object]) -> list[str]:
    checks = params.get("required_status_checks")
    bound = isinstance(checks, list) and any(
        isinstance(check, Mapping)
        and check.get("context") == CI_JOB_NAME
        and check.get("integration_id") == GITHUB_ACTIONS_APP_ID
        for check in checks
    )
    if bound:
        return []
    return [
        f"the {CI_JOB_NAME} status check is not bound to GitHub Actions "
        f"(integration {GITHUB_ACTIONS_APP_ID})"
    ]


def _bypass_problems(actors: object) -> list[str]:
    found = (
        [
            (a.get("actor_id"), a.get("actor_type"), a.get("bypass_mode"))
            if isinstance(a, Mapping)
            else None
            for a in actors
        ]
        if isinstance(actors, list)
        else None
    )
    if found == [(ADMIN_ROLE_ID, "RepositoryRole", "pull_request")]:
        return []
    return ["the bypass list must hold only the admin role in pull_request mode"]


def _rules(ruleset: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    """The ruleset's rules: type -> parameters, empty for a rule such as deletion that has none."""
    rules = ruleset.get("rules")
    found: dict[str, Mapping[str, object]] = {}
    for entry in rules if isinstance(rules, list) else []:
        kind = _mapping(entry).get("type")
        if isinstance(kind, str):
            found[kind] = _mapping(_mapping(entry).get("parameters"))
    return found


def _one_ruleset_problems(
    ruleset: Mapping[str, object], default_branch: str, *, review: bool
) -> list[str]:
    rules = _rules(ruleset)
    pull_request = rules.get("pull_request")
    # Without the rule, its other settings have nothing to describe.
    missing_rule = NO_APPROVAL if review else NO_PULL_REQUEST_RULE
    return [
        *_target_problems(ruleset, default_branch),
        *([] if ruleset.get("enforcement") == "active" else ["the ruleset is not active"]),
        *(
            [missing_rule]
            if pull_request is None
            else _pull_request_problems(pull_request, review=review)
        ),
        *_status_check_problems(rules.get("required_status_checks", {})),
        *([] if "non_fast_forward" in rules else ["force pushes are not blocked"]),
        *([] if "deletion" in rules else ["deletion is not blocked"]),
        *_bypass_problems(ruleset.get("bypass_actors")),
    ]


def _closest(
    rulesets: Sequence[Mapping[str, object]], default_branch: str, *, review: bool
) -> list[str]:
    """No problem when one ruleset has none, because GitHub applies every ruleset that matches.
    Otherwise the problems of the ruleset with the fewest."""
    found = [_one_ruleset_problems(r, default_branch, review=review) for r in rulesets]
    return [] if any(not problems for problems in found) else min(found, key=len)


def ruleset_problems(
    rulesets: Sequence[Mapping[str, object]],
    default_branch: str,
    *,
    every_pr: bool,
    agent_identity: bool,
) -> list[str]:
    """What keeps the default branch from matching Spec 1 section 8's ruleset for the Mode.

    rulesets are in the shape GET /repos/{o}/{r}/rulesets/{id} returns. Walk, and Flight with
    Agent identity, need the whole ruleset. Flight without Agent identity also accepts it without
    the review requirement, because the owner cannot approve a pull request from their own
    account (Spec 1 section 8, step 8).
    """
    if not rulesets:
        return [NO_RULESET]
    strict = _closest(rulesets, default_branch, review=True)
    if not strict or every_pr or agent_identity:
        return strict
    return _closest(rulesets, default_branch, review=False)


def _active_lines(text: str) -> list[tuple[str, tuple[str, ...]]]:
    """Each active CODEOWNERS line as (pattern, owners), the owners in lower case.

    GitHub compares logins without regard to case. Blank lines and comments, whole-line or after
    the owners, are not active.
    """
    lines: list[tuple[str, tuple[str, ...]]] = []
    for raw in text.splitlines():
        line = _COMMENT.sub("", raw.strip())
        if line and not line.startswith("#"):
            pattern, *owners = line.split()
            lines.append((pattern, tuple(owner.lower() for owner in owners)))
    return lines


def _walk_problems(lines: Sequence[tuple[str, tuple[str, ...]]], owner: str) -> list[str]:
    wanted = f"* @{owner}"
    if len(lines) != 1:
        return [f"Walk needs exactly one active CODEOWNERS line, {wanted}; found {len(lines)}"]
    if lines[0] != ("*", (f"@{owner.lower()}",)):
        return [f"the one active CODEOWNERS line is not {wanted}"]
    return []


def _protected_set_problems(
    lines: Sequence[tuple[str, tuple[str, ...]]], owner: str, stack: Stack
) -> list[str]:
    problems: list[str] = []
    if any(pattern == "*" for pattern, _ in lines):
        problems.append(
            "with every_pr = false, CODEOWNERS must have no * line; only the Protected set is owned"
        )
    # The last line for a pattern is the one GitHub applies.
    owned = {pattern.removeprefix("/"): owners for pattern, owners in lines}
    required = (*PROTECTED_PATHS, *(PYTHON_PROTECTED_PATHS if stack == "python" else ()))
    unowned = [path for path in required if owned.get(path) != (f"@{owner.lower()}",)]
    if unowned:
        problems.append(f"CODEOWNERS must name only @{owner} for: {', '.join(unowned)}")
    return problems


def codeowners_problems(text: str, every_pr: bool, owner: str, stack: Stack) -> list[str]:
    """What keeps CODEOWNERS from matching the Mode (Spec 1 section 6): the * line when every_pr
    is true, the Protected set otherwise."""
    lines = _active_lines(text)
    if every_pr:
        return _walk_problems(lines, owner)
    return _protected_set_problems(lines, owner, stack)


def installation_problems(found: Mapping[str, object], role: Role) -> list[str]:
    """How an installation's permissions differ from the role's, which must match exactly."""
    granted = found.get("permissions")
    if not isinstance(granted, Mapping):
        return ["the installation lists no permissions"]
    wanted = APP_PERMISSIONS[role]
    problems: list[str] = []
    for name, level in sorted(wanted.items()):
        has = granted.get(name)
        if has is None:
            problems.append(f"{name}: {level} is not granted")
        elif has != level:
            problems.append(f"{name} is {has}, not {level}")
    problems.extend(
        f"{name}: {has} must not be granted"
        for name, has in sorted(granted.items(), key=lambda entry: str(entry[0]))
        if name not in wanted
    )
    return problems
```

Create `rapid_ship/templates/common/tools/devctl/devctl/doctor_github.py`:

```python
"""doctor's GitHub items: the ruleset, CODEOWNERS, repository settings and, while Agent identity is
on, both Apps.

Repository settings are read with the owner's gh sign-in (OwnerGet, always GET). Each App is read
as the App itself: its installation, and one installation token that proves its Keychain key can
mint. Those POSTs are the only writes, they change nothing in the repository, and each token is
discarded unprinted. doctor_rules.py holds the checks that compare what GitHub returned.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from urllib.parse import quote

from devctl.doctor_items import DoctorContext, Item, OwnerReadError, Status
from devctl.doctor_rules import codeowners_problems, installation_problems, ruleset_problems
from devctl.github.api import GitHubError, json_list, json_object
from devctl.github.app import (
    AppError,
    AppNotInstalled,
    GitHubAccess,
    KeychainMissing,
    guarded_message,
    installation,
)
from devctl.settings import PROJECT, App, Role

PLAN_LIMIT = "Upgrade to GitHub Pro"  # GitHub's 403 for rulesets on a private repository
REPOSITORY_ITEMS = ("ruleset", "CODEOWNERS", "delete branch on merge", "fork PR workflow approval")
IDENTITY = "agent identity"  # the area of the App items
_LABELS: dict[Role, str] = {"worker": "Worker", "reviewer": "Reviewer"}


def _github(name: str, status: Status, detail: str) -> Item:
    return Item("github", name, status, detail)


def _identity(name: str, status: Status, detail: str) -> Item:
    return Item(IDENTITY, name, status, detail)


def _unreadable(name: str, what: str, error: OwnerReadError) -> Item:
    http = f" (HTTP {error.status})" if error.status else ""
    return _github(name, "unknown", f"cannot read {what}: {error.message}{http}")


def _guarded(name: str, build: Callable[[], Item]) -> Item:
    """build() with a response that is not the shape GitHub documents made unknown."""
    try:
        return build()
    except GitHubError as error:
        return _github(name, "unknown", str(error))


def _field(repo: Mapping[str, object], key: str) -> str:
    value = repo.get(key)
    if isinstance(value, str) and value:
        return value
    raise GitHubError(None, f"the repository has no {key}")


def _mode(every_pr: bool) -> str:
    return "Walk" if every_pr else "the Protected set (every_pr = false)"


def _repository_rulesets(ctx: DoctorContext, repository: str) -> list[Mapping[str, object]]:
    """The repository's own rulesets on branches, each read by ID; inherited ones are left out."""
    listed = json_list(
        ctx.owner_get(f"repos/{repository}/rulesets?targets=branch"), "the ruleset list"
    )
    found: list[Mapping[str, object]] = []
    for entry in listed:
        summary = json_object(entry, "a listed ruleset")
        if summary.get("source_type") != "Repository":
            continue
        ruleset_id = summary.get("id")
        if isinstance(ruleset_id, bool) or not isinstance(ruleset_id, int):
            raise GitHubError(None, "a listed ruleset has no numeric id")
        found.append(
            json_object(ctx.owner_get(f"repos/{repository}/rulesets/{ruleset_id}"), "the ruleset")
        )
    return found


def _ruleset_item(ctx: DoctorContext, repository: str, repo: Mapping[str, object]) -> Item:
    name = "ruleset"
    default = _field(repo, "default_branch")
    try:
        rulesets = _repository_rulesets(ctx, repository)
    except OwnerReadError as error:
        if error.status == 403 and PLAN_LIMIT in error.message:
            detail = "rulesets need a public repository or a paid GitHub plan (GitHub returned 403)"
            return _github(name, "missing", detail)
        return _unreadable(name, "the rulesets", error)
    if any("bypass_actors" not in ruleset for ruleset in rulesets):
        detail = "the bypass list is visible only to users who can edit the ruleset"
        return _github(name, "unknown", detail)
    every_pr, identity = ctx.project.escalation.every_pr, ctx.project.agent_identity
    problems = ruleset_problems(rulesets, default, every_pr=every_pr, agent_identity=identity)
    if problems:
        return _github(name, "missing", "; ".join(problems))
    if ruleset_problems(rulesets, default, every_pr=True, agent_identity=True):
        detail = (
            f"an active ruleset on {default} has rs-setup's settings without the review "
            "requirement, as Flight without Agent identity needs; the Protected set is advice"
        )
        return _github(name, "ok", detail)
    return _github(name, "ok", f"an active ruleset on {default} has every setting rs-setup applies")


def _decoded(contents: Mapping[str, object]) -> str:
    content = contents.get("content")
    if contents.get("encoding") != "base64" or not isinstance(content, str):
        raise GitHubError(None, "the CODEOWNERS contents are not base64 text")
    try:
        # GitHub wraps the base64 at 60 characters.
        return base64.b64decode(content.replace("\n", ""), validate=True).decode()
    except ValueError:  # binascii.Error and UnicodeDecodeError
        raise GitHubError(None, "the CODEOWNERS contents are not UTF-8 text") from None


def _codeowners_item(ctx: DoctorContext, repository: str, repo: Mapping[str, object]) -> Item:
    name = "CODEOWNERS"
    default = _field(repo, "default_branch")
    # GitHub reads CODEOWNERS from the base branch, so that is the file doctor reads.
    path = f"repos/{repository}/contents/.github/CODEOWNERS?ref={quote(default, safe='/')}"
    try:
        text = _decoded(json_object(ctx.owner_get(path), "the CODEOWNERS contents"))
    except OwnerReadError as error:
        if error.status == 404:
            return _github(name, "missing", f".github/CODEOWNERS is not on {default}")
        return _unreadable(name, ".github/CODEOWNERS", error)
    owner = repository.split("/", 1)[0]
    every_pr = ctx.project.escalation.every_pr
    problems = codeowners_problems(text, every_pr, owner, ctx.project.stack)
    if problems:
        return _github(name, "missing", "; ".join(problems))
    return _github(name, "ok", f".github/CODEOWNERS on {default} matches {_mode(every_pr)}")


def _delete_branch_item(repo: Mapping[str, object]) -> Item:
    name = "delete branch on merge"
    setting = repo.get("delete_branch_on_merge")
    if setting is True:
        return _github(name, "ok", "head branches are deleted after merge")
    if setting is False:
        detail = "turn on Automatically delete head branches in the repository settings"
        return _github(name, "missing", detail)
    return _github(name, "unknown", "GitHub did not report delete_branch_on_merge")


def _fork_item(ctx: DoctorContext, repository: str, repo: Mapping[str, object]) -> Item:
    name = "fork PR workflow approval"
    visibility = _field(repo, "visibility")
    if visibility != "public":
        return _github(name, "ok", f"not applicable: {visibility} repository")
    path = f"repos/{repository}/actions/permissions/fork-pr-contributor-approval"
    try:
        setting = json_object(ctx.owner_get(path), "the fork approval setting")
    except OwnerReadError as error:
        return _unreadable(name, "the fork pull request approval setting", error)
    policy = setting.get("approval_policy")
    if policy == "all_external_contributors":
        return _github(name, "ok", "workflows from all outside contributors need approval")
    found = policy if isinstance(policy, str) else "unreadable"
    detail = (
        f"approval_policy is {found}; require approval for all outside contributors "
        "under Settings, Actions, General"
    )
    return _github(name, "missing", detail)


def _repository_items(ctx: DoctorContext, repository: str) -> list[Item]:
    try:
        repo = json_object(ctx.owner_get(f"repos/{repository}"), "the repository")
    except OwnerReadError as error:
        return [_unreadable(name, f"repos/{repository}", error) for name in REPOSITORY_ITEMS]
    except GitHubError as error:
        return [_github(name, "unknown", str(error)) for name in REPOSITORY_ITEMS]
    return [
        _guarded("ruleset", lambda: _ruleset_item(ctx, repository, repo)),
        _guarded("CODEOWNERS", lambda: _codeowners_item(ctx, repository, repo)),
        _guarded("delete branch on merge", lambda: _delete_branch_item(repo)),
        _guarded("fork PR workflow approval", lambda: _fork_item(ctx, repository, repo)),
    ]


def _installation_item(
    ctx: DoctorContext, access: GitHubAccess, repository: str, role: Role, app: App
) -> Item:
    name = f"{_LABELS[role]} App installation"
    try:
        found = installation(
            role, repository, app.id, keychain=access.keychain, api_url=access.api_url
        )
    except AppError as error:
        return _identity(name, "missing", guarded_message(error, ctx.root))
    except GitHubError as error:
        return _identity(name, "unknown", str(error))
    problems: list[str] = []
    granted = installation_problems(found, role)
    if granted:
        problems.append(f"permissions differ from Spec 1 section 3: {'; '.join(granted)}")
    slug = found.get("app_slug")
    if slug != app.slug:
        # Spec 3 finds agent pull requests by this slug, so a wrong one hides them all.
        shown = slug if isinstance(slug, str) else "unreadable"
        problems.append(f"the installed App's slug is {shown}, but {PROJECT} records {app.slug}")
    if problems:
        return _identity(name, "missing", "; ".join(problems))
    detail = f"{app.slug} is installed on {repository} with exactly the {role} App's permissions"
    return _identity(name, "ok", detail)


def _key_item(ctx: DoctorContext, access: GitHubAccess, role: Role, app: App) -> Item:
    name = f"{_LABELS[role]} App key"
    try:
        access.token(role, app.id)  # proves the key; the token is dropped unprinted
    except KeychainMissing as error:
        return _identity(name, "missing", guarded_message(error, ctx.root))
    except AppNotInstalled:
        return _identity(name, "unknown", "key found; minting needs the App installed")
    except AppError as error:
        return _identity(name, "unknown", f"cannot mint a token: {error}")
    except GitHubError as error:
        return _identity(name, "unknown", str(error))
    detail = "Keychain item found; token minted (changes nothing in the repository)"
    return _identity(name, "ok", detail)


def _app_items(ctx: DoctorContext, repository: str) -> list[Item]:
    """Both Apps' installation and key items; none while Agent identity is off."""
    worker, reviewer = ctx.project.worker_app, ctx.project.reviewer_app
    if worker is None or reviewer is None:
        return []
    apps: tuple[tuple[Role, App], ...] = (("worker", worker), ("reviewer", reviewer))
    access = ctx.access
    if access is None:
        detail = "no GitHub access is set up for this run, so the Apps cannot be checked"
        return [
            *(_identity(f"{_LABELS[r]} App installation", "unknown", detail) for r, _ in apps),
            *(_identity(f"{_LABELS[r]} App key", "unknown", detail) for r, _ in apps),
        ]
    return [
        *(_installation_item(ctx, access, repository, role, app) for role, app in apps),
        *(_key_item(ctx, access, role, app) for role, app in apps),
    ]


def github_items(ctx: DoctorContext) -> list[Item]:
    """The repository's settings, and both Apps while Agent identity is on. Nothing in the
    repository changes."""
    repository = ctx.project.repository
    if repository is None:
        return [_github("repository", "missing", f"repository is not set in {PROJECT}")]
    return [*_repository_items(ctx, repository), *_app_items(ctx, repository)]
```

In `rapid_ship/templates/common/tools/devctl/devctl/doctor.py`, replace the module docstring and the imports, everything above `STATUSES: tuple[Status, ...] = ("ok", "missing", "unknown")`, with:

```python
"""devctl doctor: report each item as ok, missing or unknown.

doctor_local.py builds the items for this machine and repository, and doctor_github.py the GitHub
items, which compare what they read with the settings in doctor_rules.py. doctor_items.py holds
the types they share and the owner's one way to read GitHub. This module runs them, prints them
and exits with the worst answer. It re-exports the names that tests, and plan 6's test of
rs-setup's ruleset, import from devctl.doctor.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from devctl.doctor_github import github_items as github_items
from devctl.doctor_items import DoctorContext as DoctorContext
from devctl.doctor_items import Item as Item
from devctl.doctor_items import OwnerGet as OwnerGet
from devctl.doctor_items import OwnerReadError as OwnerReadError
from devctl.doctor_items import Status as Status
from devctl.doctor_items import gh_get as gh_get
from devctl.doctor_local import DEVCTL_DIRECTORY as DEVCTL_DIRECTORY
from devctl.doctor_local import KIT_SOURCE as KIT_SOURCE
from devctl.doctor_local import devctl_exclusion_gaps as devctl_exclusion_gaps
from devctl.doctor_local import git_item as git_item
from devctl.doctor_local import local_items as local_items
from devctl.doctor_rules import ADMIN_ROLE_ID as ADMIN_ROLE_ID
from devctl.doctor_rules import GITHUB_ACTIONS_APP_ID as GITHUB_ACTIONS_APP_ID
from devctl.doctor_rules import PROTECTED_PATHS as PROTECTED_PATHS
from devctl.doctor_rules import PYTHON_PROTECTED_PATHS as PYTHON_PROTECTED_PATHS
from devctl.doctor_rules import codeowners_problems as codeowners_problems
from devctl.doctor_rules import installation_problems as installation_problems
from devctl.doctor_rules import ruleset_problems as ruleset_problems
from devctl.github.app import project_access
from devctl.repo import Repo
from devctl.settings import load_project
```

and replace `run_doctor` with:

```python
def run_doctor(ctx: DoctorContext) -> int:
    """Print every item for ctx, the local ones first, then a summary line; return the exit code."""
    return _report([*local_items(ctx), *github_items(ctx)])
```

Format, check and vendor:

```sh
T=rapid_ship/templates/common/tools/devctl/devctl
uv run ruff format $T/doctor.py $T/doctor_rules.py $T/doctor_github.py
uv run ruff check $T/doctor.py $T/doctor_rules.py $T/doctor_github.py
uv run rapid-ship sync --in-place
```

- [ ] **Step 4: Run the tests and see them pass**

```sh
uv run pytest tests/devctl -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run rapid-ship status --strict
```

Expected: every devctl test passes, including Task 4's two output tests in their final form; Ruff and mypy report nothing; status exits 0.

- [ ] **Step 5: Commit**

```sh
git add -A rapid_ship/templates tools/devctl .rapid-ship/kit.lock tests
git commit -m "feat: check the ruleset, CODEOWNERS and, with Agent identity on, both Apps in devctl doctor" -m "Copied from codex/github-commands (ebe3bd2), reshaped to every_pr and Agent identity: Flight without Agent identity also accepts the ruleset without its review requirement, and each installation's slug must match project.toml." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: `doctor --skills`

For each of `claude`, `codex` and `agy` on `PATH`, `--skills` adds a detached worktree at `HEAD` in a temporary directory with the owner's own git, starts one headless Session there on the cheapest model, and compares the skills it lists with the ones committed at `HEAD`. It mints no App token and fetches nothing. `013cdac`'s comparison and `f9c3872`'s `probe_worktree` come over, reshaped to that. The follow-ups removed the branch that probed the Harnesses `[roster]` named, after the owner descoped several Providers. Follow-up 9 narrowed `--skills` to `claude` on #32 (c05e443), until another Harness's integration lands; the code and tests below still probe all three Harnesses.

**Files:**
- Create: `rapid_ship/templates/common/tools/devctl/devctl/doctor_skills.py`
- Rewrite: `rapid_ship/templates/common/tools/devctl/devctl/doctor.py`
- Test: `tests/devctl/test_devctl_probe_worktree.py`, `tests/devctl/test_devctl_doctor_skills.py`, `tests/devctl/test_devctl_doctor_skills_limits.py`

**Interfaces:**
- Consumes: `DoctorContext`, `Item`, `run_installed` (Task 4); `PROBE_TIMEOUT_SECONDS`, `skills_args`, `parse_skills`, `HarnessName` (Task 4's `harness.py`); `front_matter` (plan 3's `check/markdown.py`); `Repo` (plan 2).
- Produces:

<!-- fmt:off -->
```python
# devctl/doctor_skills.py
SUPPORTED: tuple[HarnessName, ...] = ("claude", "codex", "agy")
class ProbeError(Exception): ...  # the probe worktree could not be added or removed
@contextmanager
def probe_worktree(repo: Repo) -> Iterator[Path]: ...  # detached at HEAD, in tempfile.mkdtemp()
def repository_skills(tree: Path) -> tuple[frozenset[str], frozenset[str]]: ...  # (checked, user-invoked)
def probed_harnesses(project: ProjectSettings) -> dict[HarnessName, str]: ...  # Harness -> item name
def skills_items(ctx: DoctorContext) -> list[Item]: ...

# devctl/doctor.py
def run_doctor(ctx: DoctorContext, *, skills: bool = False) -> int: ...
```
<!-- fmt:on -->

- [ ] **Step 1: Write the failing tests**

Create `tests/devctl/test_devctl_probe_worktree.py`:

```python
"""Offline: the temporary worktree that doctor --skills starts a Session in. Real git runs in a
scratch clone; one test simulates a failed removal. No network, no Harness."""

import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from devctl import process
from devctl.doctor_skills import ProbeError, probe_worktree
from devctl.process import ProcessResult
from devctl.repo import Repo
from github_fakes import Remote, git

pytestmark = pytest.mark.usefixtures("isolated_home")


class Boom(Exception):
    """What a failing body raises."""


def worktree_paths(clone: Path) -> list[str]:
    listing = git(clone, "worktree", "list", "--porcelain")
    return [line for line in listing.splitlines() if line.startswith("worktree ")]


@pytest.fixture
def scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The directory tempfile.mkdtemp uses for this test, so a test can see what is left."""
    directory = tmp_path / "tmp"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


def test_it_yields_a_detached_worktree_at_head_and_removes_it(
    remote: Remote, scratch: Path
) -> None:
    head = git(remote.clone, "rev-parse", "HEAD")
    with probe_worktree(Repo.discover(remote.clone)) as path:
        assert path.is_relative_to(scratch.resolve())
        assert git(path, "rev-parse", "HEAD") == head
        assert git(path, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"  # detached
        assert len(worktree_paths(remote.clone)) == 2
    assert list(scratch.iterdir()) == []
    assert len(worktree_paths(remote.clone)) == 1
    assert git(remote.clone, "branch", "--list") == "* main"


def test_head_is_the_current_commit_not_the_default_branch(remote: Remote) -> None:
    git(remote.clone, "switch", "-q", "-c", "feature")
    head = remote.commit_in(remote.clone, "a commit only on feature")
    with probe_worktree(Repo.discover(remote.clone)) as path:
        assert git(path, "rev-parse", "HEAD") == head


def test_it_removes_files_and_a_lock_a_session_left(remote: Remote, scratch: Path) -> None:
    with probe_worktree(Repo.discover(remote.clone)) as path:
        (path / "scratch.txt").write_text("a Session wrote this\n")
        (path / "nested").mkdir()
        (path / "nested" / "more.txt").write_text("and this\n")
        git(path, "worktree", "lock", str(path))  # one --force alone cannot remove a lock
    assert list(scratch.iterdir()) == []
    assert len(worktree_paths(remote.clone)) == 1


def test_it_removes_the_worktree_when_the_body_raises(remote: Remote, scratch: Path) -> None:
    repo = Repo.discover(remote.clone)

    def body() -> None:
        with probe_worktree(repo):
            raise Boom

    with pytest.raises(Boom):
        body()
    assert list(scratch.iterdir()) == []
    assert len(worktree_paths(remote.clone)) == 1


def test_two_open_probes_do_not_share_a_path(remote: Remote) -> None:
    repo = Repo.discover(remote.clone)
    with probe_worktree(repo) as first, probe_worktree(repo) as second:
        assert first != second
        assert first.exists()
        assert second.exists()
    assert len(worktree_paths(remote.clone)) == 1


def test_a_repository_without_a_commit_leaves_nothing(tmp_path: Path, scratch: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    git(empty, "init", "-q", "-b", "main")
    with pytest.raises(ProbeError) as raised, probe_worktree(Repo.discover(empty)):
        pytest.fail("the body must not run")
    assert str(raised.value).startswith("could not add the probe worktree ")
    assert list(scratch.iterdir()) == []


def test_a_failed_removal_says_how_to_remove_it_by_hand(
    remote: Remote, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulated: git refuses the removal.
    real = process.run_process

    def refuse_removal(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        if list(argv[1:3]) == ["worktree", "remove"]:
            return ProcessResult(list(argv), 128, "", "fatal: simulated refusal\n", 0.0)
        return real(argv, cwd, timeout_seconds, env=env, input_text=input_text)

    monkeypatch.setattr(process, "run_process", refuse_removal)
    with pytest.raises(ProbeError) as raised, probe_worktree(Repo.discover(remote.clone)) as path:
        pass
    assert str(raised.value) == (
        f"could not remove the probe worktree {path}: fatal: simulated refusal; "
        f"remove it with git worktree remove --force --force {path}"
    )
    assert path.exists()
    git(remote.clone, "worktree", "remove", "--force", str(path))


def test_git_runs_in_the_repository_root(remote: Remote, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, Path]] = []
    real = process.run_process

    def record(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        seen.append((" ".join(argv[1:3]), cwd))
        return real(argv, cwd, timeout_seconds, env=env, input_text=input_text)

    monkeypatch.setattr(process, "run_process", record)
    nested = remote.clone / "nested"
    nested.mkdir()
    with probe_worktree(Repo.discover(nested)):
        pass
    root = remote.clone.resolve()
    assert seen == [("worktree add", root), ("worktree remove", root)]
```

Create `tests/devctl/test_devctl_doctor_skills.py`:

```python
"""Offline: doctor --skills with fake Harness executables on PATH and a scratch clone. No real
Harness runs, and no App token is minted."""

import json
from pathlib import Path

import pytest

from devctl.doctor import DoctorContext, Item, OwnerReadError, skills_items
from devctl.github.app import GitHubAccess
from devctl.harness import PROBE_MODELS
from devctl.settings import ProjectSettings
from github_fakes import FakeGitHub, FakeHarness, Remote, files_containing, git


def no_owner_reads(path: str) -> object:
    raise OwnerReadError(None, "no owner reads in this test")


@pytest.fixture
def doctor_ctx(remote: Remote, project: ProjectSettings, access: GitHubAccess) -> DoctorContext:
    """The clone with Agent identity on, so a test can show --skills mints no token anyway."""
    return DoctorContext(remote.clone, project, no_owner_reads, access)


def commit_skills(clone: Path, *names: str, user_invoked: tuple[str, ...] = ()) -> None:
    for name in (*names, *user_invoked):
        flag = "disable-model-invocation: true\n" if name in user_invoked else ""
        skill = clone / ".agents" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: The {name} skill.\n{flag}---\n"
        )
    git(clone, "add", ".agents")
    git(clone, "commit", "-q", "-m", "add skills")


def claude_stream(skills: list[str]) -> str:
    init = {"type": "system", "subtype": "init", "session_id": "s-1", "skills": skills}
    done = {"type": "result", "subtype": "success", "is_error": False, "result": "\n".join(skills)}
    return f"{json.dumps(init)}\n{json.dumps(done)}\n"


def agy_skills(names: list[str]) -> str:
    return json.dumps([{"name": name, "builtin": False} for name in names])


def install_script(harness: FakeHarness, name: str, body: str) -> None:
    """A Harness executable of its own: body runs in the Session's working directory."""
    script = harness.directory / name
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(0o755)


def worktrees(remote: Remote) -> list[str]:
    listing = git(remote.clone, "worktree", "list", "--porcelain")
    return [line for line in listing.splitlines() if line.startswith("worktree ")]


def by_name(items: list[Item]) -> dict[str, Item]:
    return {item.name: item for item in items}


def test_each_harness_on_path_sees_the_skills_at_head(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", "billing-rules")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd", "billing-rules"]))
    fake_harness.install(
        "claude", stdout=claude_stream(["rs-tdd", "billing-rules", "my-notes", "tools:lint"])
    )
    items = by_name(skills_items(doctor_ctx))
    assert items["skills (agy)"].status == "ok"
    claude = items["skills (claude)"]
    assert claude.status == "ok"
    assert "outside the repository: my-notes, tools:lint" in claude.detail
    [args] = fake_harness.calls("claude")
    assert args[args.index("--model") + 1] == PROBE_MODELS["claude"]
    [cwd] = fake_harness.cwds("claude")
    assert not cwd.is_relative_to(remote.clone.resolve())
    assert not cwd.exists()
    assert len(worktrees(remote)) == 1


def test_an_uncommitted_skill_is_not_compared(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    draft = remote.clone / ".agents" / "skills" / "draft"
    draft.mkdir()
    (draft / "SKILL.md").write_text("---\nname: draft\ndescription: Not committed.\n---\n")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd"]))
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    for item in skills_items(doctor_ctx):
        assert (item.status, item.detail) == ("ok", "1 repository skills seen")


def test_a_skill_the_session_cannot_see_is_missing(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", "billing-rules")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd", "billing-rules"]))
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    claude = by_name(skills_items(doctor_ctx))["skills (claude)"]
    assert (claude.status, claude.detail) == ("missing", "missing: billing-rules")


def test_codex_lists_skills_one_name_per_line(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    events = [
        {"type": "thread.started", "thread_id": "t-1"},
        {
            "type": "item.completed",
            "item": {"id": "item_0", "type": "agent_message", "text": "- rs-tdd\nreview-notes\n"},
        },
        {"type": "turn.completed", "usage": {}},
    ]
    fake_harness.install("codex", stdout="".join(f"{json.dumps(event)}\n" for event in events))
    [item] = skills_items(doctor_ctx)
    assert (item.name, item.status) == ("skills (codex)", "ok")
    assert "outside the repository: review-notes" in item.detail
    [args] = fake_harness.calls("codex")
    assert args[:2] == ["exec", "--json"]
    assert args[args.index("--model") + 1] == PROBE_MODELS["codex"]
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in args


def test_user_invoked_skills_are_not_checked(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", user_invoked=("rs-setup",))
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd"]))
    # A Harness may list a user-invoked skill anyway; it is still a repository skill.
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd", "rs-setup"]))
    for item in skills_items(doctor_ctx):
        assert item.status == "ok"
        assert "not checked, user-invoked: rs-setup" in item.detail
        assert "outside the repository" not in item.detail


def test_each_supported_harness_on_path_is_probed_in_order(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd"]))
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    items = skills_items(doctor_ctx)
    assert [(i.name, i.status) for i in items] == [
        ("skills (claude)", "ok"),
        ("skills (agy)", "ok"),
    ]
    assert fake_harness.calls("codex") == []


def test_with_no_harness_on_path_one_item_is_missing(
    doctor_ctx: DoctorContext, fake_harness: FakeHarness
) -> None:
    assert skills_items(doctor_ctx) == [
        Item("skills", "skills", "missing", "none of claude, codex or agy is on PATH")
    ]


def test_the_worktree_is_removed_when_a_session_fails(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    fake_harness.install(
        "agy",
        code=1,
        stderr="error: Eligibility check failed: UNAVAILABLE (code 503): "
        "The service is currently unavailable.\n",
    )
    fake_harness.install("claude", code=1)
    items = by_name(skills_items(doctor_ctx))
    assert items["skills (agy)"].status == "unknown"
    assert "code 503" in items["skills (agy)"].detail
    assert items["skills (claude)"].status == "unknown"
    assert len(worktrees(remote)) == 1


def test_a_session_that_writes_files_and_locks_its_worktree_still_has_it_removed(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    reply = agy_skills(["rs-tdd"])
    install_script(
        fake_harness,
        "agy",
        f"echo scratch > scratch.txt\ngit worktree lock \"$(pwd)\"\necho '{reply}'",
    )
    [item] = skills_items(doctor_ctx)
    assert item.status == "ok"
    assert len(worktrees(remote)) == 1


def test_a_session_that_never_finishes_is_unknown_and_its_worktree_is_removed(
    doctor_ctx: DoctorContext,
    remote: Remote,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("devctl.doctor_skills.PROBE_TIMEOUT_SECONDS", 0.3)
    install_script(fake_harness, "agy", "sleep 30")
    [item] = skills_items(doctor_ctx)
    assert item.status == "unknown"
    assert "did not finish" in item.detail
    assert len(worktrees(remote)) == 1


def test_no_token_is_minted_and_the_session_sees_none(
    doctor_ctx: DoctorContext,
    github: FakeGitHub,
    remote: Remote,
    fake_harness: FakeHarness,
    tmp_path: Path,
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    record = fake_harness.directory / "agy.env"
    install_script(fake_harness, "agy", f"env > \"{record}\"\necho '{agy_skills(['rs-tdd'])}'")
    [item] = skills_items(doctor_ctx)
    assert item.status == "ok"
    assert github.calls == []
    environment = record.read_text()
    assert "GIT_ASKPASS" not in environment
    assert "RAPID_SHIP_GIT_TOKEN" not in environment
    assert files_containing(tmp_path, "ghs_") == []
```

Create `tests/devctl/test_devctl_doctor_skills_limits.py`. Its `TestRepositorySkills` cases are `901bd43`'s:

```python
"""Offline: the edges of doctor --skills: how a repository's skills are read, how the items are
worded, and how the flag reaches run_doctor. Fake Harness executables and stubbed items only; no
real Harness runs."""

import argparse
import json
from pathlib import Path

import pytest

from devctl import cli, doctor
from devctl.doctor import (
    DoctorContext,
    Item,
    OwnerReadError,
    probed_harnesses,
    repository_skills,
    run_doctor,
    skills_items,
)
from devctl.settings import ProjectSettings
from github_fakes import FakeHarness, Remote, git


def no_owner_reads(path: str) -> object:
    raise OwnerReadError(None, "no owner reads in this test")


@pytest.fixture
def doctor_ctx(remote: Remote, project: ProjectSettings) -> DoctorContext:
    return DoctorContext(remote.clone, project, no_owner_reads, None)


def write_skill(tree: Path, name: str, text: str | bytes | None) -> None:
    """A skill directory under tree; text None leaves it without a SKILL.md."""
    skill = tree / ".agents" / "skills" / name
    skill.mkdir(parents=True)
    if isinstance(text, str):
        (skill / "SKILL.md").write_text(text)
    elif text is not None:
        (skill / "SKILL.md").write_bytes(text)


class TestRepositorySkills:
    def test_a_tree_without_skills_has_none(self, tmp_path: Path) -> None:
        assert repository_skills(tmp_path) == (frozenset(), frozenset())

    def test_only_directories_with_a_skill_manifest_count(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "rs-tdd", "---\nname: rs-tdd\n---\n")
        write_skill(tmp_path, "no-manifest", None)
        (tmp_path / ".agents" / "skills" / "README.md").write_text("not a skill\n")
        assert repository_skills(tmp_path) == (frozenset({"rs-tdd"}), frozenset())

    def test_the_directory_name_is_the_skill_name(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "dir-name", "---\nname: another-name\n---\n")
        assert repository_skills(tmp_path) == (frozenset({"dir-name"}), frozenset())

    def test_a_skill_that_only_the_owner_invokes_is_not_checked(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "rs-tdd", "---\nname: rs-tdd\n---\n")
        write_skill(
            tmp_path, "rs-setup", "---\nname: rs-setup\ndisable-model-invocation: true\n---\n"
        )
        assert repository_skills(tmp_path) == (frozenset({"rs-tdd"}), frozenset({"rs-setup"}))

    @pytest.mark.parametrize(
        "text",
        [
            "---\nname: x\ndisable-model-invocation: false\n---\n",
            '---\nname: x\ndisable-model-invocation: "true"\n---\n',
            "---\nname: x\n---\n",
            "no front matter\n",
            "---\nname: x\n",  # never closed
            "---\n: : :\n  - [\n---\n",  # not YAML
            "---\n- a\n- b\n---\n",  # not a mapping
            b"---\nname: \xff\xfe\n---\n",  # not UTF-8
        ],
    )
    def test_front_matter_that_does_not_say_true_leaves_the_skill_checked(
        self, tmp_path: Path, text: str | bytes
    ) -> None:
        write_skill(tmp_path, "x", text)
        assert repository_skills(tmp_path) == (frozenset({"x"}), frozenset())


class TestNames:
    def test_only_supported_harnesses_on_path_are_named(
        self, project: ProjectSettings, fake_harness: FakeHarness
    ) -> None:
        fake_harness.install("codex")
        fake_harness.install("pi")
        assert probed_harnesses(project) == {"codex": "skills (codex)"}

    def test_the_item_lists_missing_outside_and_user_invoked_skills(
        self, doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
    ) -> None:
        for name in ("b-skill", "a-skill", "c-skill"):
            write_skill(remote.clone, name, f"---\nname: {name}\ndescription: d\n---\n")
        write_skill(
            remote.clone,
            "u-skill",
            "---\nname: u-skill\ndescription: d\ndisable-model-invocation: true\n---\n",
        )
        git(remote.clone, "add", ".agents")
        git(remote.clone, "commit", "-q", "-m", "skills")
        listed = [{"name": n} for n in ("c-skill", "z-out", "m-out", "u-skill")]
        fake_harness.install("agy", stdout=json.dumps(listed))
        assert skills_items(doctor_ctx) == [
            Item(
                "skills",
                "skills (agy)",
                "missing",
                "missing: a-skill, b-skill; outside the repository: m-out, z-out; "
                "not checked, user-invoked: u-skill",
            )
        ]


class TestRunDoctor:
    @pytest.fixture
    def stubbed(self, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        """The other items stubbed out; the list records each skills_items call."""
        calls: list[str] = []

        def skills(ctx: DoctorContext) -> list[Item]:
            calls.append("skills")
            return [Item("skills", "skills (agy)", "missing", "missing: rs-tdd")]

        monkeypatch.setattr(
            doctor, "local_items", lambda ctx: [Item("toolchain", "git", "ok", "2")]
        )
        monkeypatch.setattr(
            doctor, "github_items", lambda ctx: [Item("github", "ruleset", "ok", "")]
        )
        monkeypatch.setattr(doctor, "skills_items", skills)
        return calls

    def test_without_the_flag_no_skills_item_is_built(
        self,
        doctor_ctx: DoctorContext,
        stubbed: list[str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert run_doctor(doctor_ctx) == 0
        assert stubbed == []
        assert capsys.readouterr().out.splitlines()[-1] == "doctor: 2 ok, 0 missing, 0 unknown"

    def test_with_the_flag_the_skills_items_follow_the_others(
        self,
        doctor_ctx: DoctorContext,
        stubbed: list[str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert run_doctor(doctor_ctx, skills=True) == 1
        assert stubbed == ["skills"]
        assert capsys.readouterr().out.splitlines() == [
            "ok  toolchain  git: 2",
            "ok  github  ruleset: ",
            "missing  skills  skills (agy): missing: rs-tdd",
            "doctor: 2 ok, 1 missing, 0 unknown",
        ]


class TestCommand:
    def test_the_flag_defaults_to_off_and_reaches_run_doctor(
        self, remote: Remote, project: ProjectSettings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        passed: list[bool] = []

        def record(ctx: DoctorContext, *, skills: bool = False) -> int:
            passed.append(skills)
            return 0

        monkeypatch.chdir(remote.clone)
        monkeypatch.setattr(doctor, "git_item", lambda: Item("toolchain", "git", "ok", "2.39"))
        monkeypatch.setattr(doctor, "load_project", lambda root: project)
        monkeypatch.setattr(doctor, "run_doctor", record)
        parser = cli.build_parser()
        for argv in (["doctor"], ["doctor", "--skills"]):
            args = parser.parse_args(argv)
            assert args.handler(args) == 0
        assert passed == [False, True]

    def test_help_lists_the_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as raised:
            cli.main(["doctor", "--help"])
        assert raised.value.code == 0
        out = " ".join(capsys.readouterr().out.split())
        assert "--skills" in out
        assert "spends a little quota" in out

    def test_a_namespace_from_the_parser_has_the_flag(self) -> None:
        args = cli.build_parser().parse_args(["doctor", "--skills"])
        assert isinstance(args, argparse.Namespace)
        assert args.skills is True
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_probe_worktree.py -q`
Expected: collection fails with `ModuleNotFoundError: No module named 'devctl.doctor_skills'`.

- [ ] **Step 3: Write the skills items and add the flag**

Create `rapid_ship/templates/common/tools/devctl/devctl/doctor_skills.py`:

```python
"""doctor --skills: the skills each Harness's Session loads from a worktree at HEAD.

For each of claude, codex and agy found on PATH, doctor adds a detached worktree at HEAD in a new
temporary directory, starts one new headless Session there and compares the skills it lists with
the ones committed at HEAD. git runs with the owner's own setup; no App token is minted. The
worktree is doctor's only local write, and it is removed again whatever the Session did. Each
Session spends a little of the owner's quota.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

from devctl import process
from devctl.check.markdown import front_matter
from devctl.doctor_items import DoctorContext, Item, Status, run_installed
from devctl.harness import PROBE_TIMEOUT_SECONDS, HarnessName, parse_skills, skills_args
from devctl.process import ProcessResult
from devctl.repo import Repo
from devctl.settings import ProjectSettings

SUPPORTED: tuple[HarnessName, ...] = ("claude", "codex", "agy")
_GIT_TIMEOUT_SECONDS = 120.0
_NONE_ON_PATH = "none of claude, codex or agy is on PATH"


class ProbeError(Exception):
    """The probe worktree could not be added or removed."""


def _git_problem(result: ProcessResult) -> str | None:
    """Why git's answer cannot be used, or None. A timeout or cut output is never an answer."""
    if result.timed_out:
        return f"timed out after {_GIT_TIMEOUT_SECONDS:g} seconds"
    if result.stdout_truncated or result.stderr_truncated:
        return "its output was too long"
    if result.returncode != 0:
        return process.first_line(result.stderr) or f"exit code {result.returncode}"
    return None


def _git(cwd: Path, *args: str, failure: str) -> None:
    problem = _git_problem(process.run_process(["git", *args], cwd, _GIT_TIMEOUT_SECONDS))
    if problem is not None:
        raise ProbeError(f"{failure}: {problem}")


@contextmanager
def probe_worktree(repo: Repo) -> Iterator[Path]:
    """A detached worktree at HEAD in a new temporary directory, removed whatever the body did.

    The removal is forced twice, so files a Session wrote, or a lock it took, cannot keep the
    worktree. When the removal fails anyway, the worktree stays and ProbeError says how to remove
    it by hand.
    """
    scratch = Path(tempfile.mkdtemp(prefix="devctl-skills-")).resolve()
    path = scratch / "tree"
    try:
        _git(
            repo.root,
            "worktree",
            "add",
            "--detach",
            str(path),
            "HEAD",
            failure=f"could not add the probe worktree {path}",
        )
    except ProbeError:
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    try:
        yield path
    finally:
        command = f"git worktree remove --force --force {path}"
        try:
            _git(
                repo.root,
                "worktree",
                "remove",
                "--force",
                "--force",
                str(path),
                failure=f"could not remove the probe worktree {path}",
            )
        except ProbeError as error:
            raise ProbeError(f"{error}; remove it with {command}") from None
        scratch.rmdir()


def _item(name: str, status: Status, detail: str) -> Item:
    return Item("skills", name, status, detail)


def _user_invoked(manifest: Path) -> bool:
    """True when the skill's front matter sets disable-model-invocation: true.

    Front matter that cannot be read leaves the skill checked; map rule 7 reports it.
    """
    try:
        data = front_matter(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return False
    return isinstance(data, dict) and data.get("disable-model-invocation") is True


def repository_skills(tree: Path) -> tuple[frozenset[str], frozenset[str]]:
    """The skills under tree/.agents/skills, by directory name: (checked, user-invoked).

    A user-invoked skill is one that a Session may leave out of its list, so it is not checked.
    """
    checked: set[str] = set()
    user_invoked: set[str] = set()
    root = tree / ".agents" / "skills"
    for entry in root.iterdir() if root.is_dir() else ():
        manifest = entry / "SKILL.md"
        if manifest.is_file():
            (user_invoked if _user_invoked(manifest) else checked).add(entry.name)
    return frozenset(checked), frozenset(user_invoked)


def _compare(name: str, listed: frozenset[str], tree: Path) -> Item:
    """Missing when the Session did not list a checked skill; outside skills are only named."""
    checked, user_invoked = repository_skills(tree)
    missing = sorted(checked - listed)
    outside = sorted(listed - checked - user_invoked)
    parts = [
        f"missing: {', '.join(missing)}" if missing else f"{len(checked)} repository skills seen"
    ]
    if outside:
        parts.append(f"outside the repository: {', '.join(outside)}")
    if user_invoked:
        parts.append(f"not checked, user-invoked: {', '.join(sorted(user_invoked))}")
    return _item(name, "missing" if missing else "ok", "; ".join(parts))


def _session(name: str, harness: HarnessName, tree: Path) -> Item:
    """Start one headless Session of harness in tree; compare what it lists with tree's skills."""
    result = run_installed(harness, *skills_args(harness), cwd=tree, timeout=PROBE_TIMEOUT_SECONDS)
    if result is None:
        return _item(name, "missing", f"{harness} is not on PATH")
    report = parse_skills(harness, result)
    if report.names is None:
        return _item(name, "unknown", report.error or f"{harness} gave no skill list")
    return _compare(name, report.names, tree)


def _harness_item(repo: Repo, harness: HarnessName, name: str) -> Item:
    """One Harness in a worktree of its own, so one Session cannot change what the next sees."""
    if shutil.which(harness) is None:
        return _item(name, "missing", f"{harness} is not on PATH")
    try:
        with probe_worktree(repo) as tree:
            return _session(name, harness, tree)
    except (ProbeError, OSError) as error:  # adding or removing the worktree
        return _item(name, "unknown", str(error))


def probed_harnesses(project: ProjectSettings) -> dict[HarnessName, str]:
    """Each of claude, codex and agy on PATH, with its item's name (Spec 1 section 6)."""
    return {h: f"skills ({h})" for h in SUPPORTED if shutil.which(h) is not None}


def skills_items(ctx: DoctorContext) -> list[Item]:
    """One item per probed Harness, or one missing item when there is none to probe."""
    names = probed_harnesses(ctx.project)
    if not names:
        return [_item("skills", "missing", _NONE_ON_PATH)]
    repo = Repo.discover(ctx.root)
    return [_harness_item(repo, harness, name) for harness, name in names.items()]
```

Replace `rapid_ship/templates/common/tools/devctl/devctl/doctor.py` with its final form, which adds the `doctor_skills` re-exports, `run_doctor`'s `skills` flag and the `--skills` option:

```python
"""devctl doctor: report each item as ok, missing or unknown.

doctor_local.py builds the items for this machine and repository, and doctor_github.py the GitHub
items, which compare what they read with the settings in doctor_rules.py; doctor_skills.py adds
the --skills items. doctor_items.py holds the types they share and the owner's one way to read
GitHub. This module runs them, prints them and exits with the worst answer. It re-exports the
names that tests, and plan 6's test of rs-setup's ruleset, import from devctl.doctor.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from devctl.doctor_github import github_items as github_items
from devctl.doctor_items import DoctorContext as DoctorContext
from devctl.doctor_items import Item as Item
from devctl.doctor_items import OwnerGet as OwnerGet
from devctl.doctor_items import OwnerReadError as OwnerReadError
from devctl.doctor_items import Status as Status
from devctl.doctor_items import gh_get as gh_get
from devctl.doctor_local import DEVCTL_DIRECTORY as DEVCTL_DIRECTORY
from devctl.doctor_local import KIT_SOURCE as KIT_SOURCE
from devctl.doctor_local import devctl_exclusion_gaps as devctl_exclusion_gaps
from devctl.doctor_local import git_item as git_item
from devctl.doctor_local import local_items as local_items
from devctl.doctor_rules import ADMIN_ROLE_ID as ADMIN_ROLE_ID
from devctl.doctor_rules import GITHUB_ACTIONS_APP_ID as GITHUB_ACTIONS_APP_ID
from devctl.doctor_rules import PROTECTED_PATHS as PROTECTED_PATHS
from devctl.doctor_rules import PYTHON_PROTECTED_PATHS as PYTHON_PROTECTED_PATHS
from devctl.doctor_rules import codeowners_problems as codeowners_problems
from devctl.doctor_rules import installation_problems as installation_problems
from devctl.doctor_rules import ruleset_problems as ruleset_problems
from devctl.doctor_skills import probe_worktree as probe_worktree
from devctl.doctor_skills import probed_harnesses as probed_harnesses
from devctl.doctor_skills import repository_skills as repository_skills
from devctl.doctor_skills import skills_items as skills_items
from devctl.github.app import project_access
from devctl.repo import Repo
from devctl.settings import load_project

STATUSES: tuple[Status, ...] = ("ok", "missing", "unknown")


def doctor_exit_code(items: Sequence[Item]) -> int:
    """2 when any item is unknown, else 1 when any is missing, else 0."""
    statuses = {item.status for item in items}
    if "unknown" in statuses:
        return 2
    return 1 if "missing" in statuses else 0


def _report(items: Sequence[Item]) -> int:
    for item in items:
        sys.stdout.write(f"{item.status}  {item.area}  {item.name}: {item.detail}\n")
    ok, missing, unknown = (sum(i.status == status for i in items) for status in STATUSES)
    sys.stdout.write(f"doctor: {ok} ok, {missing} missing, {unknown} unknown\n")
    return doctor_exit_code(items)


def run_doctor(ctx: DoctorContext, *, skills: bool = False) -> int:
    """Print every item for ctx, the local ones first, then a summary line; return the exit code.

    Only skills=True starts a Harness Session, each in a temporary worktree of its own.
    """
    items = [*local_items(ctx), *github_items(ctx)]
    if skills:
        items.extend(skills_items(ctx))
    return _report(items)


def doctor_command(args: argparse.Namespace) -> int:
    item = git_item()
    if item.status != "ok":
        # Every later item needs git rev-parse --path-format=absolute.
        return _report([item])
    repo = Repo.discover(Path.cwd())  # cli.main maps RepoError and SettingsError to exit 2
    project = load_project(repo.root)
    # doctor reads the Apps only while Agent identity is on (Spec 1 section 6).
    access = project_access(project) if project.agent_identity else None
    return run_doctor(DoctorContext(repo.root, project, gh_get, access), skills=args.skills)


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "doctor",
        help="Report what this machine and repository lack",
        description="Report each item as ok, missing or unknown. Exit 0 when every item is ok, "
        "1 when one is missing, 2 when one is unknown.",
    )
    parser.add_argument(
        "--skills",
        action="store_true",
        help="also start one headless Session per Harness in a temporary worktree at HEAD and "
        "compare the skills it loads; spends a little quota",
    )
    parser.set_defaults(handler=doctor_command)
```

Format, check and vendor:

```sh
T=rapid_ship/templates/common/tools/devctl/devctl
uv run ruff format $T/doctor.py $T/doctor_skills.py
uv run ruff check $T/doctor.py $T/doctor_skills.py
uv run rapid-ship sync --in-place
```

- [ ] **Step 4: Run the tests and see them pass**

```sh
uv run pytest tests/devctl/test_devctl_probe_worktree.py tests/devctl/test_devctl_doctor_skills.py tests/devctl/test_devctl_doctor_skills_limits.py tests/devctl/test_devctl_doctor_local.py tests/devctl/test_devctl_doctor_local_limits.py -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run rapid-ship status --strict
```

Expected: every test passes, none skipped; Ruff and mypy report nothing; status exits 0.

- [ ] **Step 5: Commit**

```sh
git add -A rapid_ship/templates tools/devctl .rapid-ship/kit.lock tests
git commit -m "feat: compare the skills each Harness loads at HEAD with devctl doctor --skills" -m "Each probe runs in a detached worktree at HEAD in a temporary directory, with the owner's git and no App token, and the worktree is removed whatever the Session did." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 7: `rapid-ship app`

`rapid-ship app` comes over from `3eec7a1` and `901bd43`: GitHub's manifest flow creates each missing App on the owner's personal account, the key goes to the Keychain on `security`'s stdin, and the command prints each App's ID, slug and install URL. It now prints each App's `[github]` lines, so `rs-setup` records the ID and the slug as printed. Its tests simulate the browser, GitHub's conversion endpoint, gh and `security`.

**Files:**
- Create (copied, then edited): `rapid_ship/github_app.py`
- Modify (copied): `rapid_ship/cli.py`
- Modify: `.rapid-ship/exceptions.toml` (EX-11)
- Test (copied, then edited): `tests/test_kit_app.py`, `tests/test_kit_app_limits.py`; modify `tests/devctl/test_devctl_github_app.py` (the parity test)

**Interfaces:**
- Consumes: nothing from devctl; `rapid_ship` may not import it.
- Produces:

<!-- fmt:off -->
```python
# rapid_ship/github_app.py
KEYCHAIN_SERVICE = {"worker": "rapid-ship/worker-app", "reviewer": "rapid-ship/reviewer-app"}
APP_PERMISSIONS: dict[str, dict[str, str]]  # equal to devctl's, held by a parity test
class AppSetupError(Exception): ...  # exit 2
@dataclass(frozen=True)
class StoredApp:
    app_id: int
    slug: str
class MacKeychainStore: ...  # find(service) -> StoredApp | None; add(service, app, private_key)
def gh_owner_get(path: str) -> object: ...
def current_repository() -> str: ...
def run_app(repository: str, *, store: KeychainStore, owner_get: OwnerGet, open_browser: Callable[[str], object], api_url: str = API_URL, timeout_seconds: float = 900.0) -> int: ...
# rapid_ship/cli.py: the app subcommand, `rapid-ship app [--repository OWNER/NAME]`, which needs no work tree
```
<!-- fmt:on -->

For each App, `run_app` prints `<Role> App: ID <id> (<slug>)`, then `  <role>_app_id = <id>` and `  <role>_app_slug = "<slug>"`, then the install URL.

- [ ] **Step 1: Write the failing tests**

```sh
git show 901bd43:tests/test_kit_app.py > tests/test_kit_app.py
git show 901bd43:tests/test_kit_app_limits.py > tests/test_kit_app_limits.py
```

Then make these edits:

In `tests/test_kit_app_limits.py`, replace:

```python
    assert "Record both IDs in .rapid-ship/project.toml under [github]." in out
```

with:

```python
    assert "Record each App's ID and slug, as printed above, in .rapid-ship/project.toml" in out
    assert 'worker_app_slug = "o-old-worker"' in out
```

In `tests/test_kit_app.py`, replace:

```python
import threading
import webbrowser
```

with:

```python
import threading
import tomllib
import webbrowser
```

Append to `tests/test_kit_app.py`:

```python
def test_the_printed_settings_lines_are_the_github_table(
    store: FakeStore, owner_get: OwnerGet, capsys: pytest.CaptureFixture[str]
) -> None:
    store.apps = {
        "rapid-ship/worker-app": StoredApp(11, "o-rs-worker"),
        "rapid-ship/reviewer-app": StoredApp(12, "o-rs-reviewer"),
    }
    assert run_app("o/r", store=store, owner_get=owner_get, open_browser=lambda url: None) == 0
    lines = [line.strip() for line in capsys.readouterr().out.splitlines() if "_app_" in line]
    assert tomllib.loads("\n".join(lines)) == {
        "worker_app_id": 11,
        "worker_app_slug": "o-rs-worker",
        "reviewer_app_id": 12,
        "reviewer_app_slug": "o-rs-reviewer",
    }
```

Append the parity test that Task 3 left out to `tests/devctl/test_devctl_github_app.py`:

```python
def test_rapid_ship_and_devctl_agree_on_services_and_permissions() -> None:
    from devctl.github import app
    from rapid_ship import github_app

    assert github_app.KEYCHAIN_SERVICE == app.KEYCHAIN_SERVICE
    assert github_app.APP_PERMISSIONS == app.APP_PERMISSIONS
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run pytest tests/test_kit_app.py -q`
Expected: collection fails with `ModuleNotFoundError: No module named 'rapid_ship.github_app'`.

- [ ] **Step 3: Copy the command and print the `[github]` lines**

```sh
git show 901bd43:rapid_ship/github_app.py > rapid_ship/github_app.py
git show 901bd43:rapid_ship/cli.py > rapid_ship/cli.py
```

At `901bd43`, `rapid_ship/cli.py` differs from #30 only by the `app` subcommand: its import of `github_app`, the `app` parser with `--repository`, the early `if args.command == "app"` in `main` (app reads no Kit file, so it runs outside a work tree) and `_app`. Then make these edits to `rapid_ship/github_app.py`:

In `rapid_ship/github_app.py`, replace:

```python
    sys.stdout.write(
        f"{_TITLES[role]}: ID {app.app_id} ({app.slug})\n"
        f"  Install on {repository}: "
```

with:

```python
    sys.stdout.write(
        f"{_TITLES[role]}: ID {app.app_id} ({app.slug})\n"
        f"  {role}_app_id = {app.app_id}\n"
        f'  {role}_app_slug = "{app.slug}"\n'
        f"  Install on {repository}: "
```

In `rapid_ship/github_app.py`, replace:

```python
    sys.stdout.write(
        "Record both IDs in .rapid-ship/project.toml under [github]. "
        "./devctl doctor confirms each installation.\n"
    )
```

with:

```python
    sys.stdout.write(
        "Record each App's ID and slug, as printed above, in .rapid-ship/project.toml under "
        "[github]; rs-setup does this. ./devctl doctor then confirms each installation.\n"
    )
```

`run_command` starts `security` and `gh` itself, because `rapid_ship` may not import devctl's runner, so its `# noqa: S603` needs an entry. Append to `.rapid-ship/exceptions.toml`:

```toml

[[exception]]
id = "EX-11"
path = "rapid_ship/github_app.py"
rule = "S603"
reason = "rapid-ship app runs security and gh with fixed arguments and no shell; rapid_ship may not import devctl's runner"
remove_when = "Ruff stops reporting S603 for list arguments without a shell"
```

Run: `wc -l rapid_ship/github_app.py`
Expected: 499 lines, within the 500-line `file-size` cap.

- [ ] **Step 4: Run the tests and see them pass**

```sh
uv run pytest tests/test_kit_app.py tests/test_kit_app_limits.py tests/devctl/test_devctl_github_app.py -q
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
./devctl check --tier fast
uv run rapid-ship app --help
```

Expected: every test passes; Ruff, mypy and import-linter report nothing (`rapid_ship` still imports no devctl); the fast tier passes `exceptions` with EX-11 and `file-size`; the help names `--repository OWNER/NAME`.

- [ ] **Step 5: Commit**

```sh
git add rapid_ship/github_app.py rapid_ship/cli.py .rapid-ship/exceptions.toml tests/test_kit_app.py tests/test_kit_app_limits.py tests/devctl/test_devctl_github_app.py
git commit -m "feat: create and install the Worker and Reviewer Apps with rapid-ship app" -m "Copied from codex/github-commands (3eec7a1, 901bd43); it now prints each App's [github] lines, so rs-setup records the ID and the slug as printed." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 8: `devctl as`

`devctl as` is Agent identity's one thin command (Spec 1 section 6): `push` pushes the current branch as the Worker App, and `gh` runs `gh pr`, `gh issue` or `gh api` as the role's App. It refuses what it can before it mints a token, hands the token to one child only, relays the child's output with the token hidden, and returns the child's exit code. Its tests use a local bare repository in GitHub's place, the simulated GitHub and Keychain, and a fake `gh` that reports a hash of the token it received, never the token.

**Files:**
- Create: `rapid_ship/templates/common/tools/devctl/devctl/identity.py`
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/cli.py`
- Test: `tests/devctl/test_devctl_identity.py`, `tests/devctl/test_devctl_identity_limits.py`

**Interfaces:**
- Consumes: `GitHubAccess`, `project_access`, `run_git`, `run_guarded`, `DevctlError`, `json_object` (Task 3); `App`, `ProjectSettings`, `Role`, `ROLES`, `load_project` (Task 2); `process.run_process`, `process.first_line`, `process.MAX_OUTPUT_BYTES` (Task 1).
- Produces (the index's `devctl as` interface):

<!-- fmt:off -->
```python
# devctl/identity.py
ACTIONS = ("push", "gh")
GH_COMMANDS = frozenset({"pr", "issue", "api"})
GH_TIMEOUT_SECONDS = 600.0
PUSH_TIMEOUT_SECONDS = 300.0
class Refusal(Exception): ...  # exit 1
def gh_refusal(arguments: Sequence[str]) -> str | None: ...
def push_hint(stderr: str) -> str | None: ...
def run_as(repo: Repo, project: ProjectSettings, role: Role, action: str, arguments: Sequence[str]) -> int: ...
def as_command(args: argparse.Namespace) -> int: ...
def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None: ...
```
<!-- fmt:on -->

The command line is `devctl as {worker,reviewer} {push,gh} [ARGS...]`; everything after the action reaches `devctl as` unparsed (Checked facts). Exit codes: 2 while Agent identity is off, when no token can be minted, when the tool cannot start, or when it timed out or its output was cut; 1 when devctl refuses; otherwise the exit code of `gh` or `git`.

- [ ] **Step 1: Write the failing tests**

Create `tests/devctl/test_devctl_identity.py`:

```python
"""Offline: devctl as, with simulated GitHub (FakeGitHub), the test Keychain, a local bare
repository in GitHub's place and a fake gh on PATH. No live GitHub, gh sign-in or Keychain."""

import hashlib
import json
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from devctl import identity
from devctl.github.app import GitHubAccess
from devctl.repo import Repo
from devctl.settings import ProjectSettings, Role
from github_fakes import (
    REVIEWER_INSTALLATION,
    WORKER_INSTALLATION,
    FakeGitHub,
    FakeHarness,
    Remote,
    files_containing,
    git,
)

RunAs = Callable[..., int]


def install_gh(fakes: FakeHarness, *, code: int = 0, extra: str = "") -> None:
    """A gh that prints its arguments, GH_REPO, whether prompts are off, the sha256 of GH_TOKEN
    and whether the git askpass variable reached it, as one JSON line; then runs extra."""
    gh = fakes.directory / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import hashlib, json, os, sys\n"
        "token = os.environ.get('GH_TOKEN', '')\n"
        "print(json.dumps({'argv': sys.argv[1:], 'repo': os.environ.get('GH_REPO'),"
        " 'prompt': os.environ.get('GH_PROMPT_DISABLED'),"
        " 'token_sha256': hashlib.sha256(token.encode()).hexdigest(),"
        " 'askpass': 'RAPID_SHIP_GIT_TOKEN' in os.environ}))\n"
        f"{extra}\n"
        f"sys.exit({code})\n"
    )
    gh.chmod(0o755)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def feature(remote: Remote, monkeypatch: pytest.MonkeyPatch) -> str:
    """The clone on branch feature with one new commit, as the working directory; its head."""
    git(remote.clone, "switch", "-q", "-c", "feature")
    head = remote.commit_in(remote.clone, "feature work")
    monkeypatch.chdir(remote.clone)
    return head


@pytest.fixture
def default_branch(github: FakeGitHub) -> None:
    """GitHub names main as o/r's default branch, to a token of either App."""
    github.route("GET", "/repos/o/r", lambda call, match: (200, {"default_branch": "main"}))


@pytest.fixture
def run_as(
    access: GitHubAccess, project: ProjectSettings, monkeypatch: pytest.MonkeyPatch
) -> RunAs:
    """devctl as in the working directory, with o/r on the simulated GitHub and the test keys."""
    monkeypatch.setattr(identity, "project_access", lambda settings: access)

    def run(role: Role, action: str, *arguments: str, settings: ProjectSettings = project) -> int:
        return identity.run_as(Repo.discover(Path.cwd()), settings, role, action, list(arguments))

    return run


@pytest.mark.usefixtures("default_branch")
def test_push_sends_the_branch_to_the_branch_of_the_same_name(
    run_as: RunAs,
    feature: str,
    remote: Remote,
    github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_as("worker", "push") == 0
    assert remote.branch("feature") == feature
    assert remote.branch("main") != feature
    mints = [call.path for call in github.calls if call.method == "POST"]
    assert mints == [f"/app/installations/{WORKER_INSTALLATION}/access_tokens"]
    assert "feature -> feature" in capsys.readouterr().err


@pytest.mark.usefixtures("default_branch")
def test_push_never_forces(
    run_as: RunAs, feature: str, remote: Remote, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_as("worker", "push") == 0
    elsewhere = remote.commit_on("feature", "pushed from another clone")
    remote.commit_in(remote.clone, "local work on the old head")
    assert run_as("worker", "push") == 1  # git's own exit code
    assert remote.branch("feature") == elsewhere
    assert "rejected" in capsys.readouterr().err


@pytest.mark.usefixtures("default_branch")
def test_push_refuses_the_default_branch(
    run_as: RunAs,
    remote: Remote,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = remote.branch("main")
    remote.commit_in(remote.clone, "a commit on main")
    monkeypatch.chdir(remote.clone)
    assert run_as("worker", "push") == 1
    assert "main is the default branch" in capsys.readouterr().err
    assert remote.branch("main") == before


@pytest.mark.parametrize(
    ("role", "arguments", "reason"),
    [
        ("reviewer", (), "only the Worker App pushes"),
        ("worker", ("--force",), "push takes no arguments and never forces"),
        ("worker", ("origin", "+feature"), "push takes no arguments and never forces"),
    ],
)
def test_push_refusals_mint_no_token(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
    role: Role,
    arguments: tuple[str, ...],
    reason: str,
) -> None:
    assert run_as(role, "push", *arguments) == 1
    assert f"devctl as: refused: {reason}" in capsys.readouterr().err
    assert github.issued_tokens == []


def test_a_detached_head_is_refused_before_a_token_is_minted(
    run_as: RunAs, feature: str, remote: Remote, github: FakeGitHub
) -> None:
    git(remote.clone, "switch", "-q", "--detach")
    assert run_as("worker", "push") == 1
    assert github.issued_tokens == []


@pytest.mark.usefixtures("default_branch")
def test_the_push_token_is_never_an_argument_or_in_a_file(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    recorded_argv: list[list[str]],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert run_as("worker", "push") == 0
    out, err = capsys.readouterr()
    [token] = github.issued_tokens
    [push] = [argv for argv in recorded_argv if "push" in argv]
    assert push[:5] == ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]
    assert all(token not in arg for argv in recorded_argv for arg in argv)
    assert token not in out + err
    assert files_containing(tmp_path, token) == []


def test_gh_runs_as_the_worker_app_with_the_token_only_in_its_environment(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    recorded_argv: list[list[str]],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    install_gh(fake_harness)
    assert run_as("worker", "gh", "pr", "create", "--title", "Add the feature") == 0
    out, err = capsys.readouterr()
    [token] = github.issued_tokens
    assert json.loads(out) == {
        "argv": ["pr", "create", "--title", "Add the feature"],
        "repo": "o/r",
        "prompt": "1",
        "token_sha256": sha256(token),
        "askpass": False,
    }
    assert token not in out + err
    assert all(token not in arg for argv in recorded_argv for arg in argv)
    assert files_containing(tmp_path, token) == []
    mints = [call.path for call in github.calls if call.method == "POST"]
    assert mints == [f"/app/installations/{WORKER_INSTALLATION}/access_tokens"]


def test_gh_as_the_reviewer_uses_the_reviewer_app(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_gh(fake_harness)
    assert run_as("reviewer", "gh", "pr", "review", "7", "--approve") == 0
    mints = [call.path for call in github.calls if call.method == "POST"]
    assert mints == [f"/app/installations/{REVIEWER_INSTALLATION}/access_tokens"]
    assert json.loads(capsys.readouterr().out)["argv"] == ["pr", "review", "7", "--approve"]


def test_a_token_the_tool_prints_is_hidden(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # gh and git push share one relay, so a gh that prints its token proves the relay hides it.
    install_gh(fake_harness, extra="print(token)\nprint(token, file=sys.stderr)")
    assert run_as("worker", "gh", "api", "user") == 0
    out, err = capsys.readouterr()
    [token] = github.issued_tokens
    assert token not in out + err
    assert out.splitlines()[-1] == "[token]"
    assert err.splitlines()[-1] == "[token]"


def test_gh_exit_code_is_passed_through(
    run_as: RunAs, feature: str, fake_harness: FakeHarness
) -> None:
    install_gh(fake_harness, code=3)
    assert run_as("worker", "gh", "issue", "list") == 3


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("auth", "token"),
        ("alias", "set", "x", "y"),
        ("extension", "install", "x"),
        ("repo", "delete", "o/r"),
        ("-R", "o/r", "pr", "list"),
        ("pr", "merge", "7", "--admin"),
        ("pr", "merge", "--admin=true", "7"),
    ],
)
def test_gh_refusals_mint_no_token_and_start_no_gh(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    install_gh(fake_harness)
    assert run_as("worker", "gh", *arguments) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "devctl as: refused: " in err
    assert github.issued_tokens == []


def test_agent_identity_off_exits_2_and_says_how_to_turn_it_on(
    run_as: RunAs,
    feature: str,
    project: ProjectSettings,
    github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
) -> None:
    off = replace(project, worker_app=None, reviewer_app=None)
    assert run_as("worker", "push", settings=off) == 2
    assert run_as("worker", "gh", "pr", "list", settings=off) == 2
    err = capsys.readouterr().err
    assert err.count("devctl: Agent identity is off") == 2
    assert "rapid-ship app" in err
    assert github.calls == []
```

Create `tests/devctl/test_devctl_identity_limits.py`:

```python
"""Offline: the edges of devctl as: cut or endless gh output, a gh that cannot start, a missing
key, GitHub's answers it cannot use, the workflow hint and the command line. GitHub, the Keychain
and gh are simulated; git runs against a local bare repository."""

import argparse
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from devctl import cli, identity, process
from devctl.github.app import GitHubAccess
from devctl.repo import Repo
from devctl.settings import ProjectSettings, Role
from github_fakes import FakeGitHub, FakeHarness, FakeKeychain, Remote, git

RunAs = Callable[..., int]


def install_gh(fakes: FakeHarness, body: str) -> None:
    gh = fakes.directory / "gh"
    gh.write_text(f"#!{sys.executable}\nimport sys, time\n{body}\n")
    gh.chmod(0o755)


@pytest.fixture
def worktree(remote: Remote, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(remote.clone, "switch", "-q", "-c", "feature")
    remote.commit_in(remote.clone, "feature work")
    monkeypatch.chdir(remote.clone)
    return remote.clone


@pytest.fixture
def run_as(
    access: GitHubAccess, project: ProjectSettings, monkeypatch: pytest.MonkeyPatch
) -> RunAs:
    monkeypatch.setattr(identity, "project_access", lambda settings: access)

    def run(role: Role, action: str, *arguments: str) -> int:
        return identity.run_as(Repo.discover(Path.cwd()), project, role, action, list(arguments))

    return run


@pytest.mark.usefixtures("worktree")
def test_gh_output_that_was_cut_exits_2_and_says_so(
    run_as: RunAs,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(process, "MAX_OUTPUT_BYTES", 16)
    install_gh(fake_harness, "print('x' * 100)")
    assert run_as("worker", "gh", "api", "repos/{owner}/{repo}") == 2
    assert "gh printed more than 16 bytes, so its output was cut; it exited 0" in (
        capsys.readouterr().err
    )


@pytest.mark.usefixtures("worktree")
def test_a_gh_that_never_finishes_exits_2(
    run_as: RunAs,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(identity, "GH_TIMEOUT_SECONDS", 0.3)
    install_gh(fake_harness, "time.sleep(30)")
    assert run_as("worker", "gh", "pr", "checks", "7") == 2
    assert "devctl: gh did not finish within 0.3 seconds" in capsys.readouterr().err


@pytest.mark.usefixtures("worktree")
def test_a_gh_that_cannot_start_exits_2(
    access: GitHubAccess,
    project: ProjectSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = Repo.discover(Path.cwd())
    # CI runners install a real gh in /usr/bin, so PATH holds an empty directory only.
    empty = tmp_path / "no-gh"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setattr(identity, "project_access", lambda settings: access)
    assert identity.run_as(repo, project, "worker", "gh", ["pr", "list"]) == 2
    assert capsys.readouterr().err == "devctl: gh could not start; install gh\n"


@pytest.mark.usefixtures("worktree")
def test_a_missing_key_exits_2_before_any_tool_runs(
    access: GitHubAccess,
    project: ProjectSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    no_keys = replace(access, keychain=FakeKeychain({}))
    monkeypatch.setattr(identity, "project_access", lambda settings: no_keys)
    assert identity.run_as(Repo.discover(Path.cwd()), project, "worker", "push", []) == 2
    assert "devctl: Keychain item rapid-ship/worker-app not found" in capsys.readouterr().err


@pytest.mark.usefixtures("worktree")
@pytest.mark.parametrize(
    "answer", [(404, {"message": "Not Found"}), (200, {}), (200, {"default_branch": ""})]
)
def test_a_default_branch_github_cannot_name_exits_2_without_a_push(
    run_as: RunAs,
    github: FakeGitHub,
    remote: Remote,
    capsys: pytest.CaptureFixture[str],
    answer: tuple[int, dict[str, str]],
) -> None:
    github.route("GET", "/repos/o/r", lambda call, match: answer)
    assert run_as("worker", "push") == 2
    assert capsys.readouterr().err.startswith("devctl: ")
    assert remote.branch("feature") is None


def test_the_workflow_refusal_gets_a_hint_and_nothing_else_does() -> None:
    refusal = (
        "remote: refusing to allow a GitHub App to create or update workflow "
        "`.github/workflows/devctl-check.yml` without `workflows` permission"
    )
    hint = identity.push_hint(refusal)
    assert hint is not None
    assert "the owner pushes it" in hint
    assert identity.push_hint("! [rejected] feature -> feature (non-fast-forward)") is None


@pytest.mark.parametrize(
    ("argv", "arguments"),
    [
        (["as", "worker", "gh", "pr", "create", "--body", "-x"], ["pr", "create", "--body", "-x"]),
        (["as", "worker", "gh", "pr", "--help"], ["pr", "--help"]),
        (["as", "worker", "gh", "-h"], ["-h"]),
        (["as", "worker", "push", "--force"], ["--force"]),
        (["as", "reviewer", "push"], []),
    ],
)
def test_everything_after_the_action_reaches_devctl_as(
    argv: list[str], arguments: list[str]
) -> None:
    args = cli.build_parser().parse_args(argv)
    assert isinstance(args, argparse.Namespace)
    assert args.handler is identity.as_command
    assert args.arguments == arguments


def test_an_unknown_role_or_action_is_a_usage_error() -> None:
    for argv in (["as", "lead", "push"], ["as", "worker", "merge"]):
        with pytest.raises(SystemExit) as raised:
            cli.build_parser().parse_args(argv)
        assert raised.value.code == 2


def test_the_command_reads_this_repositorys_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship/project.toml").write_text('stack = "agnostic"\n')
    monkeypatch.chdir(tmp_path)
    assert cli.main(["as", "worker", "push"]) == 2
    assert "Agent identity is off" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run pytest tests/devctl/test_devctl_identity.py -q`
Expected: collection fails with `ImportError: cannot import name 'identity' from 'devctl'`.

- [ ] **Step 3: Write `devctl as` and register it**

Create `rapid_ship/templates/common/tools/devctl/devctl/identity.py`:

```python
"""devctl as: an agent's GitHub writes, made as the Worker App or the Reviewer App.

Agent identity is on when .rapid-ship/project.toml records both Apps (Spec 1 section 6). Each run
mints one installation token, keeps it in memory and gives it to one child only: gh through
GH_TOKEN, or git push through askpass.py. Nothing here writes the token to disk, puts it in argv
or prints it. devctl refuses (exit 1) before it mints a token wherever it can.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from functools import partial
from pathlib import Path

from devctl import process
from devctl.github.api import json_object
from devctl.github.app import DevctlError, GitHubAccess, project_access, run_git, run_guarded
from devctl.process import ProcessResult
from devctl.repo import Repo
from devctl.settings import ROLES, App, ProjectSettings, Role, load_project

ACTIONS = ("push", "gh")
GH_COMMANDS = frozenset({"pr", "issue", "api"})
GH_TIMEOUT_SECONDS = 600.0
PUSH_TIMEOUT_SECONDS = 300.0
OFF = (
    "Agent identity is off: .rapid-ship/project.toml records no Apps. Push and open pull "
    "requests under your own sign-in, or turn Agent identity on with rs-setup: run rapid-ship "
    "app, install both Apps, and record each App's ID and slug under [github]"
)
# GitHub's reason when an App without the Workflows permission pushes a workflow change.
_WORKFLOW_REFUSAL = "refusing to allow a GitHub App to create or update workflow"


class Refusal(Exception):
    """devctl refuses the request; the command exits 1."""


def gh_refusal(arguments: Sequence[str]) -> str | None:
    """Why devctl will not run gh with these arguments, or None.

    gh auth can print the token, and gh alias and gh extension can run other code with it, so
    only gh pr, gh issue and gh api run (Spec 1 section 6).
    """
    if not arguments or arguments[0] not in GH_COMMANDS:
        named = f"gh {arguments[0]}" if arguments else "gh with no command"
        return f"{named} is not allowed; devctl as runs only gh pr, gh issue and gh api"
    admin = any(a == "--admin" or a.startswith("--admin=") for a in arguments)
    if arguments[0] == "pr" and "merge" in arguments[1:] and admin:
        return "gh pr merge --admin is not allowed; merge through the ruleset"
    return None


def push_hint(stderr: str) -> str | None:
    """What to do when GitHub refused an App's push of a workflow change, else None."""
    if _WORKFLOW_REFUSAL not in stderr:
        return None
    return (
        "neither App may push a change under .github/workflows/; that change is in the "
        "Protected set, so the owner pushes it under their own sign-in"
    )


def _hide(text: str, token: str) -> str:
    return text.replace(token, "[token]") if token else text


def _relay(tool: str, result: ProcessResult, token: str, timeout_seconds: float) -> int:
    """Write the tool's output with the token hidden, and return its exit code.

    A timeout or cut output is 2: devctl cannot show the tool's whole answer.
    """
    sys.stdout.write(_hide(result.stdout, token))
    sys.stderr.write(_hide(result.stderr, token))
    if result.timed_out:
        sys.stderr.write(f"devctl: {tool} did not finish within {timeout_seconds:g} seconds\n")
        return 2
    if result.stdout_truncated or result.stderr_truncated:
        sys.stderr.write(
            f"devctl: {tool} printed more than {process.MAX_OUTPUT_BYTES} bytes, so its output "
            f"was cut; it exited {result.returncode}\n"
        )
        return 2
    return result.returncode


def _current_branch(root: Path) -> str:
    """The branch HEAD names; a Refusal when HEAD is detached."""
    result = process.run_process(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], root, 30)
    if result.timed_out or result.stdout_truncated or result.stderr_truncated:
        raise DevctlError("git symbolic-ref did not finish")
    if result.returncode == 1:
        raise Refusal("HEAD is detached; switch to the branch to push")
    if result.returncode != 0:
        raise DevctlError(f"git symbolic-ref failed: {process.first_line(result.stderr)}")
    return result.stdout.strip()


def _default_branch(access: GitHubAccess, token: str) -> str:
    found = json_object(
        access.api(token).request("GET", f"/repos/{access.repository}"), "the repository"
    )
    name = found.get("default_branch")
    if not isinstance(name, str) or not name:
        raise DevctlError(f"GitHub did not name the default branch of {access.repository}")
    return name


def _push(repo: Repo, role: Role, arguments: Sequence[str], access: GitHubAccess, app: App) -> int:
    if role != "worker":
        raise Refusal("only the Worker App pushes; run ./devctl as worker push")
    if arguments:
        raise Refusal(f"push takes no arguments and never forces; got {' '.join(arguments)}")
    branch = _current_branch(repo.root)
    token = access.token(role, app.id)
    if branch == _default_branch(access, token):
        raise Refusal(f"{branch} is the default branch; push a task branch and open a pull request")
    url = access.remote
    result = run_git(
        repo.root,
        ["push", url, f"refs/heads/{branch}:refs/heads/{branch}"],
        token,
        url=url,
        timeout_seconds=PUSH_TIMEOUT_SECONDS,
    )
    code = _relay("git push", result, token, PUSH_TIMEOUT_SECONDS)
    hint = push_hint(result.stderr)
    if hint is not None:
        sys.stderr.write(f"devctl: {hint}\n")
    return code


def _gh(role: Role, arguments: Sequence[str], access: GitHubAccess, app: App) -> int:
    refusal = gh_refusal(arguments)
    if refusal is not None:
        raise Refusal(refusal)
    token = access.token(role, app.id)
    env = {"GH_TOKEN": token, "GH_REPO": access.repository, "GH_PROMPT_DISABLED": "1"}
    try:
        result = process.run_process(["gh", *arguments], Path.cwd(), GH_TIMEOUT_SECONDS, env=env)
    except OSError:  # gh is not installed, or cannot start
        raise DevctlError("gh could not start; install gh") from None
    return _relay("gh", result, token, GH_TIMEOUT_SECONDS)


def _act(
    repo: Repo,
    project: ProjectSettings,
    role: Role,
    action: str,
    arguments: Sequence[str],
    app: App,
) -> int:
    access = project_access(project)
    try:
        if action == "push":
            return _push(repo, role, arguments, access, app)
        return _gh(role, arguments, access, app)
    except Refusal as refusal:
        sys.stderr.write(f"devctl as: refused: {refusal}\n")
        return 1


def run_as(
    repo: Repo, project: ProjectSettings, role: Role, action: str, arguments: Sequence[str]
) -> int:
    """Run one devctl as request and return its exit code (Spec 1 section 6).

    2 while Agent identity is off, or when no token can be minted or the tool cannot start; 1
    when devctl refuses; otherwise the exit code of gh or git.
    """
    app = project.worker_app if role == "worker" else project.reviewer_app
    if app is None or not project.agent_identity:
        sys.stderr.write(f"devctl: {OFF}\n")
        return 2
    return run_guarded(partial(_act, repo, project, role, action, arguments, app), root=repo.root)


def as_command(args: argparse.Namespace) -> int:
    repo = Repo.discover(Path.cwd())  # cli.main maps RepoError and SettingsError to exit 2
    return run_as(repo, load_project(repo.root), args.role, args.action, args.arguments)


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "as",
        help="Run git push or gh as the Worker App or the Reviewer App (Agent identity)",
        description="push: push the current branch to the branch of the same name on GitHub, "
        "as the Worker App; it never forces. gh: run gh pr, gh issue or gh api as the role's "
        "App. Exit 1 when devctl refuses, 2 when it cannot mint a token or start the tool, "
        "otherwise the tool's exit code.",
    )
    parser.add_argument("role", choices=ROLES)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument(
        "arguments", nargs=argparse.REMAINDER, help="gh's arguments; push takes none"
    )
    parser.set_defaults(handler=as_command)
```

In `rapid_ship/templates/common/tools/devctl/devctl/cli.py`, replace:

```python
from devctl import __version__, doctor
```

with:

```python
from devctl import __version__, doctor, identity
```

and replace:

```python
    doctor.register(commands)
```

with:

```python
    doctor.register(commands)
    identity.register(commands)
```

Format, check and vendor:

```sh
T=rapid_ship/templates/common/tools/devctl/devctl
uv run ruff format $T/identity.py $T/cli.py
uv run ruff check $T/identity.py $T/cli.py
uv run rapid-ship sync --in-place
```

- [ ] **Step 4: Run the tests and see them pass**

```sh
uv run pytest tests/devctl/test_devctl_identity.py tests/devctl/test_devctl_identity_limits.py tests/devctl/test_devctl_cli.py -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run rapid-ship status --strict
./devctl as --help
./devctl as worker push; echo "exit $?"
```

Expected: every test passes; Ruff and mypy report nothing; status exits 0. This repository records no Apps, so the last command prints `devctl: Agent identity is off: ...` and exits 2.

- [ ] **Step 5: Commit**

```sh
git add -A rapid_ship/templates tools/devctl .rapid-ship/kit.lock tests
git commit -m "feat: push and run gh as the Worker or Reviewer App with devctl as" -m "One token per run, held in memory and given only to the gh or git child; refusals come before minting, and gh's or git's exit code is returned." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 9: Guides, ARCHITECTURE.md and the status lines

The guides, the architecture page, README.md and the status lines of Spec 1, the plan index and the rapid-ship design describe what plan 4 built. The text to replace is #30's on 2026-10-16, after the re-scope merge; each replacement below occurs once there.

**Files:**
- Modify: root `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `rapid_ship/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`
- Modify: `docs/superpowers/specs/2026-10-14-kit-and-setup-design.md` (its Status line), `docs/superpowers/plans/2026-10-14-kit-and-setup.md` (its opening paragraph and plan 4's Docs list), `docs/superpowers/specs/2026-10-14-rapid-ship-design.md` (its Delivery list)

**Interfaces:**
- Consumes: the commands, modules and tests of Tasks 1 to 8.
- Produces: no code. The `map` step checks that every new link in a guide resolves and every guide stays reachable.

- [ ] **Step 1: Check the anchors**

Run: `grep -c "Plans 1 to 3 are built" AGENTS.md ARCHITECTURE.md docs/superpowers/specs/2026-10-14-kit-and-setup-design.md docs/superpowers/plans/2026-10-14-kit-and-setup.md && grep -c "plans 1 to 3 work today" README.md`
Expected: `1` for each file. If any is 0, the re-scope text changed after this plan was written: make the edits below by meaning, keep every sentence you replace accurate, and note the difference in the PR body.

- [ ] **Step 2: Edit the guides, the architecture page and the status lines**

The follow-ups removed the text below that described the `[roster]` table, the Harness sign-in items and the `--skills` branch for `[roster]`, after the owner descoped several Providers. Follow-up 9 narrowed its `--skills` text to Claude Code.

In `AGENTS.md`, replace:

```markdown
Plans 1 to 3 are built: `rapid-ship init`, `status` and `sync`, and `devctl check`.
```

with:

```markdown
Plans 1 to 4 are built: `rapid-ship init`, `status`, `sync` and `app`, and `devctl check`, `doctor` and `as`.
```

In `AGENTS.md`, replace:

```markdown
Not built yet: plans 4 to 6 (doctor and Agent identity; Kit standards and Harness guardrails; `rs-setup` and `rs-health`)
```

with:

```markdown
Not built yet: plans 5 and 6 (Kit standards and Harness guardrails; `rs-setup` and `rs-health`)
```

In `AGENTS.md`, replace:

```markdown
- Fast check, which the pre-commit hook runs: `./devctl check --tier fast`.
```

with:

```markdown
- Fast check, which the pre-commit hook runs: `./devctl check --tier fast`.
- Doctor: `./devctl doctor` reports what this machine, this repository and its GitHub settings lack; `--skills` also starts one headless Claude Code Session.
```

In `ARCHITECTURE.md`, replace:

```markdown
listed in its [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md). Plans 1 to 3 are built.
```

with:

```markdown
listed in its [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md). Plans 1 to 4 are built.
```

In `ARCHITECTURE.md`, replace:

```markdown
| `rapid-ship` CLI | `rapid_ship/cli.py`, `rapid_ship/kit/` | `init`, `status` and `sync`: writes the Kit into a repository and keeps it current |
```

with:

```markdown
| `rapid-ship` CLI | `rapid_ship/cli.py`, `rapid_ship/kit/`, `rapid_ship/github_app.py` | `init`, `status` and `sync`: writes the Kit into a repository and keeps it current. `app`: creates the owner's Worker and Reviewer Apps for Agent identity |
```

In `ARCHITECTURE.md`, replace:

```markdown
| devctl | `tools/devctl/`, run through the `devctl` shim | `devctl check`, the one entry point for every check, in the pre-commit hook and in CI |
```

with:

```markdown
| devctl | `tools/devctl/`, run through the `devctl` shim | `devctl check`, the one entry point for every check, in the pre-commit hook and in CI; `devctl doctor`, which reports what this machine and repository lack; `devctl as`, Agent identity's command for `gh` and `git push` |
```

In `ARCHITECTURE.md`, replace:

```markdown
| Seeded files | `.rapid-ship/project.toml`, `gate.toml` and `exceptions.toml`,
```

with:

```markdown
| Seeded files | `.rapid-ship/project.toml` and `exceptions.toml`,
```

In `ARCHITECTURE.md`, replace:

```markdown
Nothing here runs as a service. Plans 4 to 6 of Spec 1, Spec 2 and Spec 3 are designed but not built
```

with:

```markdown
Nothing here runs as a service. Plans 5 and 6 of Spec 1, Spec 2 and Spec 3 are designed but not built
```

In `ARCHITECTURE.md`, replace:

```markdown
It depends only on PyYAML. Today devctl has `--version` and `check`, plus any verbs the project registers
```

with:

```markdown
It depends only on PyYAML and PyJWT with its crypto extra. devctl has `--version`, `check`, `doctor` and `as`, plus any verbs the project registers
```

In `ARCHITECTURE.md`, replace:

```markdown
## Dog-fooding
```

with:

```markdown
## `devctl doctor` and Agent identity

`./devctl doctor [--skills]` reports each item as ok, missing or unknown, then a summary line, and exits 0 when every item is ok, 1 when one is missing and 2 when one could not be checked. It changes nothing in the repository and never reads a token file. The modules are `doctor.py`, which runs and prints the items, `doctor_local.py` for this machine and the repository, `doctor_github.py` with the rules in `doctor_rules.py` for GitHub, `doctor_skills.py` for `--skills`, and `harness.py` for the headless probes.

- **Local items:** git 2.31 or later, uv, gh and its sign-in, gitleaks 8.30.1, `core.hooksPath`, the CI job named `devctl check`, the Python guardrail settings, `tools/devctl` left out of the project's own tools, and the Kit files against the lock.
- **GitHub items:** read with the owner's `gh` sign-in, always as `GET`: the ruleset for the current Mode, CODEOWNERS against `every_pr`, branch deletion after merge and fork-PR workflow approval. A GitHub Free private repository has no rulesets, and the item says so.
- **Agent identity items:** only while `[github]` records both Apps: each App's installation, its exact permissions and its slug, read as the App, and each Keychain key, proved by minting a token that is dropped unprinted.
- **`--skills`:** when `claude` is on `PATH`, a detached worktree at `HEAD` in a temporary directory, one headless Claude Code Session on its cheapest model, and a comparison of the skills it lists with the ones committed at `HEAD`. The worktree is removed whatever the Session did.

Agent identity is optional ([ADR 0002](docs/adr/0002-github-gates-merges-reviews-run-locally.md)). `rapid-ship app` creates the owner's Worker App and Reviewer App through GitHub's manifest flow, stores each private key in the macOS Keychain from `security`'s stdin, and prints each App's `[github]` lines and install URL. `./devctl as worker push` pushes the current branch, never forcing, and `./devctl as {worker,reviewer} gh` runs `gh pr`, `gh issue` or `gh api` as that App. Each run mints one installation token in `devctl/github/app.py`, holds it in memory and gives it only to that `gh`, as `GH_TOKEN`, or to that `git push`, through `devctl/github/askpass.py` with every credential helper and repository hook switched off. No key or token is written to disk, put on a command line or printed.

## Dog-fooding
```

In `ARCHITECTURE.md`, replace:

```markdown
Spec 1's [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md) defines three more plans:

- **[Plan 4, doctor and Agent identity](docs/superpowers/plans/2026-10-14-kit-and-setup.md#plan-4-doctor-and-agent-identity):** `devctl doctor` and `doctor --skills`; optional Agent identity through `rapid-ship app`, the App token code and `devctl as`, the thin command for `gh` and `git push`; and the settings for the escalation list, after which the Kit no longer seeds or reads `gate.toml`. It brings over the surviving code of `codex/github-commands`, the old plan 4's branch, which was never merged and is kept as history.
```

with:

```markdown
Spec 1's [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md) defines two more plans:
```

In `rapid_ship/AGENTS.md`, replace:

```markdown
- [cli.py](cli.py) parses arguments and runs `init`, `status` and `sync`. It exits 1 on a `KitRefusal` and 2 on a `KitError`; `app` comes with plan 4. [__main__.py](__main__.py) and the entry point call the same `main`.
```

with:

```markdown
- [cli.py](cli.py) parses arguments and runs `init`, `status`, `sync` and `app`. It exits 1 on a `KitRefusal` and 2 on a `KitError`. `app` reads no Kit file, so it runs outside a work tree. [__main__.py](__main__.py) and the entry point call the same `main`.
- [github_app.py](github_app.py) runs `rapid-ship app`. GitHub's manifest flow, through a server on `127.0.0.1`, creates the Worker App and the Reviewer App on the owner's account. `security` stores each key in the macOS Keychain from stdin, and the command prints each App's ID, slug and install URL. `rapid_ship` cannot import devctl, so this module has its own process runner (EX-11) and repeats devctl's Keychain services and App permissions; a test in `tests/devctl/test_devctl_github_app.py` keeps them equal.
```

In `rapid_ship/templates/AGENTS.md`, replace:

```markdown
- [common/.github/workflows/devctl-check.yml]
```

with:

```markdown
- `tools/devctl/devctl/github/askpass.py` is listed under `executable` in `kit.toml`, because git runs it as `GIT_ASKPASS`; a template's own file mode does not reach the rendered file.
- [common/.github/workflows/devctl-check.yml]
```

In `tools/AGENTS.md`, replace:

```markdown
and `tests/devctl/test_devctl_project_dogfood.py` checks that they still run after a sync.
```

with:

```markdown
and `tests/devctl/test_devctl_project_dogfood.py` checks that they still run after a sync.

`devctl doctor` lives in `devctl/devctl/doctor*.py` and `harness.py`; Agent identity's token code is in `devctl/devctl/github/`, and `devctl as` in `identity.py`. Read `github/app.py` before any change that touches a token: a token reaches only one gh or git child and never a file, an argument or output.
```

In `tests/AGENTS.md`, replace:

```markdown
| Bounded process runner | [devctl/test_devctl_process.py](devctl/test_devctl_process.py) |
```

with:

```markdown
| Bounded process runner | [devctl/test_devctl_process.py](devctl/test_devctl_process.py) |
| `devctl doctor`: local items, GitHub items and `--skills` | `devctl/test_devctl_doctor_*.py`, `devctl/test_devctl_probe_worktree.py`, `devctl/test_devctl_harness.py`, with the owner's recorded GitHub answers in `devctl/fixtures/github/` |
| Agent identity: the REST client, App tokens, askpass, `devctl as` and `rapid-ship app` | `devctl/test_devctl_github_*.py`, `devctl/test_devctl_askpass*.py`, `devctl/test_devctl_identity*.py`, [test_kit_app.py](test_kit_app.py) and [test_kit_app_limits.py](test_kit_app_limits.py). [devctl/github_fakes.py](devctl/github_fakes.py) simulates GitHub, the Keychain, a bare remote and the Harnesses; [devctl/github_fixtures.py](devctl/github_fixtures.py) holds their fixtures, which `conftest.py` loads. No test contacts GitHub or reads the Keychain |
```

In `README.md`, the GitHub front page that the docs site also publishes, replace:

```markdown
and plans 1 to 3 work today: `rapid-ship init` vendors the Kit into a repository, `status` compares the repository with the Kit, `sync` proposes Kit updates as a PR, and `./devctl check` runs the checks in the pre-commit hook and in CI.
```

with:

```markdown
and plans 1 to 4 work today: `rapid-ship init` vendors the Kit into a repository, `status` compares the repository with the Kit, `sync` proposes Kit updates as a PR, `./devctl check` runs the checks in the pre-commit hook and in CI, and `./devctl doctor` reports what this machine and repository lack. Optional Agent identity gives agents their own GitHub Apps: `rapid-ship app` creates them, and `./devctl as` runs `gh` and `git push` as one of them.
```

In `README.md`, replace:

```markdown
Plans 4 to 6 add `devctl doctor`, the optional Agent identity, Kit standards, the Harness guardrails and the setup skills.
```

with:

```markdown
Plans 5 and 6 add Kit standards, the Harness guardrails and the setup skills.
```

In `docs/superpowers/specs/2026-10-14-kit-and-setup-design.md`, replace:

```markdown
Plans 1 to 3 are built. Plans 4 to 6 are proposed in the [plan index](../plans/2026-10-14-kit-and-setup.md).
```

with:

```markdown
Plans 1 to 4 are built. Plans 5 and 6 are proposed in the [plan index](../plans/2026-10-14-kit-and-setup.md).
```

In `docs/superpowers/plans/2026-10-14-kit-and-setup.md`, replace:

```markdown
Each one ends with a working, tested repository and its own PR. Plans 1 to 3 are built.
```

with:

```markdown
Each one ends with a working, tested repository and its own PR. Plans 1 to 4 are built.
```

In `docs/superpowers/plans/2026-10-14-kit-and-setup.md`, replace:

```markdown
- Docs: `ARCHITECTURE.md`, the root `AGENTS.md` (its link to `gate.toml`), `rapid_ship/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, and the trial record under `docs/trials/`.
```

with:

```markdown
- Docs: `README.md`, `ARCHITECTURE.md`, the root `AGENTS.md` (its link to `gate.toml`), `rapid_ship/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, the status lines of Spec 1, this index and the rapid-ship design, and the trial record under `docs/trials/`.
```

In `docs/superpowers/specs/2026-10-14-rapid-ship-design.md`, replace:

```markdown
Plans 1 to 3 built `init`, `status`, `sync` and `devctl check`. The [plan index](../plans/2026-10-14-kit-and-setup.md) lists the rest: plan 4, doctor and Agent identity; plan 5, Kit standards and Harness guardrails; plan 6, `rs-setup` and `rs-health`.
```

with:

```markdown
Plans 1 to 4 built `init`, `status`, `sync` and `app`, and `devctl check`, `doctor` and `as`. The [plan index](../plans/2026-10-14-kit-and-setup.md) lists the rest: plan 5, Kit standards and Harness guardrails; plan 6, `rs-setup` and `rs-health`.
```

- [ ] **Step 3: Run the checks the guides answer to**

```sh
./devctl check --tier fast
uv run rapid-ship status --strict
npm --prefix website ci --no-audit --no-fund
npm --prefix website run build
! grep -n "gate\.toml" AGENTS.md ARCHITECTURE.md rapid_ship/AGENTS.md tools/AGENTS.md tests/AGENTS.md
! grep -n "Plans 1 to 3 are built\|plans 1 to 3 work today\|Plans 1 to 3 built" AGENTS.md ARCHITECTURE.md README.md docs/superpowers/specs/2026-10-14-kit-and-setup-design.md docs/superpowers/plans/2026-10-14-kit-and-setup.md docs/superpowers/specs/2026-10-14-rapid-ship-design.md
```

Expected: the fast tier passes, `map` included; status exits 0; the site builds with no broken link; neither `grep` finds anything.

- [ ] **Step 4: Commit**

```sh
git add AGENTS.md ARCHITECTURE.md README.md rapid_ship/AGENTS.md rapid_ship/templates/AGENTS.md tools/AGENTS.md tests/AGENTS.md docs/superpowers/specs/2026-10-14-kit-and-setup-design.md docs/superpowers/plans/2026-10-14-kit-and-setup.md docs/superpowers/specs/2026-10-14-rapid-ship-design.md
git commit -m "docs: describe devctl doctor, Agent identity and devctl as in the guides and status lines" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 10: Live trials (Owner steps)

Steps 1 to 14, with Step 11a, use the owner's accounts or change outside state, so each is an Owner step: the owner runs it in their own terminal, and no agent runs it (Owner steps, in the header). Run Steps 2 to 14 in one terminal session, because later steps use the shell variables earlier ones set. The owner keeps each command with its exit code and output, and leaves the ruleset read-back of Steps 9 and 11a in this plan's worktree.

Steps 15 to 17 are implementer steps, done from the owner's record. When a result calls for a code fix (Steps 3, 9 and 13), the implementer makes it with its test after the owner's session, and the report says whether the owner reran the step with the fix.

Record the results in `docs/trials/<trial date>-agent-identity.md`, the date in `YYYY-MM-DD` form, with the versions, every command, its exit code and output, deviations from Checked facts, and limits. Mark each result live or offline. The website publishes trial reports: never record a token, a private key, a client secret or an email address. A token's length may be recorded.

**Files:**
- Create: `docs/trials/<trial date>-agent-identity.md`
- Modify: `docs/trials/AGENTS.md` (link the report), `tests/devctl/fixtures/github/ruleset.json` (the read-back of Step 9, or of Step 11a when it runs)
- Modify, only as Step 17 says: `rapid_ship/templates/common/tools/devctl/devctl/doctor_rules.py`, `tests/devctl/test_devctl_doctor_github.py`, `docs/superpowers/plans/2026-10-14-kit-and-setup.md`, `docs/superpowers/specs/2026-10-14-kit-and-setup-design.md`

**Interfaces:**
- Consumes: `rapid-ship app` (Task 7), `devctl doctor` (Tasks 4 to 6), `devctl as` (Task 8), `installation` and `installation_token` (Task 3).
- Produces: the trial report, a live ruleset fixture, and the answer to Spec 1 section 11's open question on the approval count.

- [ ] **Step 1: Owner step: accept the outside changes**

The owner reads this list and starts Step 2 only if they accept every change on it: creating two private GitHub Apps on their personal account, which become their real Worker and Reviewer Apps; creating the public repository `<login>/rs-trial` and the private repository `<login>/rs-trial-private`; installing both Apps on both; applying a ruleset, branch deletion after merge and the fork approval policy to `rs-trial`, and, if Step 11 calls for it, setting that ruleset's approval count to 0; opening, reviewing and merging pull requests there as the Apps and as the owner; merging the owner's own setup pull requests there with the admin bypass; and spending a little Claude Code quota on `doctor --skills`.

- [ ] **Step 2: Owner step: record the versions and prepare `rs-trial`**

Run from this plan's worktree:

```sh
PLAN4=$(pwd)
TRIALS=$(mktemp -d)
OWNER=$(gh api user --jq .login)
sw_vers -productVersion; git --version; gh --version | head -1; uv --version
git -C "$PLAN4" rev-parse HEAD
gh api user --jq .plan.name
claude --version
cd "$TRIALS"
gh repo create "$OWNER/rs-trial" --public --add-readme --clone
cd rs-trial
uvx --from "$PLAN4" rapid-ship init --stack agnostic --owner "$OWNER" --repository "$OWNER/rs-trial"
mkdir -p .agents/skills/trial-notes .agents/skills/trial-release .claude/skills
printf -- '---\nname: trial-notes\ndescription: Notes on the rs-trial repository. Use before editing README.md.\n---\n\nKeep README.md to one paragraph.\n' > .agents/skills/trial-notes/SKILL.md
printf -- '---\nname: trial-release\ndescription: Release steps for the rs-trial repository.\ndisable-model-invocation: true\n---\n\nRun only when the owner asks.\n' > .agents/skills/trial-release/SKILL.md
ln -s ../../.agents/skills/trial-notes .claude/skills/trial-notes
ln -s ../../.agents/skills/trial-release .claude/skills/trial-release
./devctl check --tier fast; echo "exit $?"
git add .agents .claude && git commit -m "Add two trial skills"
git switch main && git merge --ff-only rapid-ship/init && git push origin main
```

Record every version, the owner's GitHub plan, and the fast check's exit code. Expected: the fast check exits 0 (map rule 7 accepts both skills and links), and `main` holds the Kit, the two skills and CODEOWNERS with `* @<login>` active. No ruleset exists yet, so the push to `main` goes through.

- [ ] **Step 3: Owner step: create the Apps**

```sh
uvx --from "$PLAN4" rapid-ship app; echo "exit $?"
security find-generic-password -s rapid-ship/worker-app >/dev/null && echo "worker item stored"
security find-generic-password -s rapid-ship/reviewer-app >/dev/null && echo "reviewer item stored"
```

Complete both browser pages. Record: the printed lines (IDs, slugs, `[github]` lines and install URLs), the exit code, whether GitHub accepted the manifest without `hook_attributes`, whether the App's settings page shows no webhook, whether `security` showed a dialog while storing each key, and both "stored" lines. Expected: exit 0. If GitHub rejects the manifest, stop and record the error; the fix is a change to `app_manifest` with a test, in this plan's PR.

- [ ] **Step 4: Owner step: install the Apps and record them**

Open both printed install URLs and install each App on `rs-trial` only. In `.rapid-ship/project.toml`, set `worker_app_id`, `worker_app_slug`, `reviewer_app_id` and `reviewer_app_slug` under `[github]` to the four printed lines, then:

```sh
WORKER_ID=$(python3 -c 'import tomllib; print(tomllib.load(open(".rapid-ship/project.toml", "rb"))["github"]["worker_app_id"])')
REVIEWER_ID=$(python3 -c 'import tomllib; print(tomllib.load(open(".rapid-ship/project.toml", "rb"))["github"]["reviewer_app_id"])')
git commit -am "Record the Worker and Reviewer Apps" && git push origin main
```

- [ ] **Step 5: Owner step: doctor reads both Apps**

```sh
./devctl doctor; echo "exit $?"
uv run --project tools/devctl --frozen python -c 'import sys; from devctl.github.app import installation; print(sorted(installation("worker", sys.argv[1], int(sys.argv[2]))))' "$OWNER/rs-trial" "$WORKER_ID"
security find-generic-password -s rapid-ship/worker-app -w >/dev/null; echo "read exit $?"
```

Record every doctor line and the exit code, the installation's keys, and whether a macOS dialog appeared. Expected: the four `agent identity` items are ok; the keys include `app_slug` (Checked facts); the key read exits 0 with no dialog, which confirms that any process the owner runs can read the keys (Spec 1 section 6). Record that under the report's limits. The ruleset, delete-branch and fork-approval items are missing until Steps 7 and 8.

- [ ] **Step 6: Owner step: a second, private repository on the owner's plan**

```sh
cd "$TRIALS"
gh repo create "$OWNER/rs-trial-private" --private --add-readme --clone
cd rs-trial-private
uvx --from "$PLAN4" rapid-ship app --repository "$OWNER/rs-trial-private"; echo "exit $?"
uvx --from "$PLAN4" rapid-ship init --stack agnostic --owner "$OWNER" --repository "$OWNER/rs-trial-private"
git switch main && git merge --ff-only rapid-ship/init && git push origin main
./devctl doctor; echo "exit $?"
cd "$TRIALS/rs-trial"
```

Expected: `rapid-ship app` opens no browser and prints both Apps' lines and install URLs for this repository. Install both Apps there with the printed URLs, then prove a token mints without printing it:

```sh
uv run --project tools/devctl --frozen python -c 'import sys; from devctl.github.app import installation_token as t; t("worker", sys.argv[1], int(sys.argv[2])); print("minted")' "$OWNER/rs-trial-private" "$WORKER_ID"
```

Record whether the install URL added the repository to the existing installation, the `minted` line, and doctor's `ruleset` line. On a GitHub Free account, expected: `missing  github  ruleset: rulesets need a public repository or a paid GitHub plan (GitHub returned 403)`. On a paid plan, record the plan and what doctor reports instead.

- [ ] **Step 7: Owner step: apply the repository settings to `rs-trial`**

```sh
gh api --method PATCH "repos/$OWNER/rs-trial" -F delete_branch_on_merge=true
gh api --method PUT "repos/$OWNER/rs-trial/actions/permissions/fork-pr-contributor-approval" -f approval_policy=all_external_contributors
```

- [ ] **Step 8: Owner step: apply the ruleset**

Write the ruleset the index specifies, the one plan 6 ships as `rs-setup/ruleset.json`, outside the repository and apply it:

```sh
cat > "$TRIALS/ruleset.json" <<'EOF'
{
  "name": "rapid-ship",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [{"context": "devctl check", "integration_id": 15368}]
      }
    }
  ]
}
EOF
RULESET_ID=$(gh api --method POST "repos/$OWNER/rs-trial/rulesets" --input "$TRIALS/ruleset.json" --jq .id)
echo "$RULESET_ID"
```

- [ ] **Step 9: Owner step: read the ruleset back and keep it as the fixture**

```sh
./devctl doctor; echo "exit $?"
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq 'del(.node_id, ._links, .created_at, .updated_at, .current_user_can_bypass) | .id = 9 | .source = "o/r"' > "$PLAN4/tests/devctl/fixtures/github/ruleset.json"
(cd "$PLAN4" && uv run pytest tests/devctl/test_devctl_doctor_github.py tests/devctl/test_devctl_doctor_github_limits.py -q)
```

Record every doctor line, whether the GitHub UI names `actor_id` 5 as the admin role, and the test result. Expected: `ruleset`, `CODEOWNERS`, `delete branch on merge` and `fork PR workflow approval` are ok, and every test passes with the read-back as the fixture. If a test fails, the read-back differs from what doctor expects: record the difference, then fix doctor or `ruleset.json` with a test in this plan's PR.

- [ ] **Step 10: Owner step: Walk with Agent identity**

```sh
git switch -c trial-walk
printf '\nA trial line.\n' >> README.md
git commit -am "Trial change"
./devctl as worker push; echo "push exit $?"
printf '## Evidence\n\n- `./devctl check --tier fast`: exit 0\n\nNot covered: everything; this pull request is a trial.\n' > "$TRIALS/pr-body.md"
./devctl as worker gh pr create --base main --head trial-walk --title "Trial change" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR=$(gh pr view trial-walk --json number --jq .number)
gh pr view "$PR" --json author --jq .author.login
./devctl as reviewer gh pr review "$PR" --approve --body "Trial approval by the Reviewer App"; echo "review exit $?"
gh pr view "$PR" --json reviews,reviewDecision,mergeStateStatus
./devctl as worker gh pr merge "$PR" --squash --admin; echo "admin exit $?"
./devctl as worker gh pr merge "$PR" --squash; echo "merge exit $?"
```

Record each exit code and output. Expected: the push and the pull request succeed, and the author is the Worker App (`<worker slug>[bot]`); the review is the Reviewer App's, yet `reviewDecision` stays `REVIEW_REQUIRED`, because CODEOWNERS `*` needs the owner; `--admin` is refused by devctl with exit 1 before anything runs; the plain merge is refused by GitHub, and devctl returns gh's nonzero exit code.

Then, in the browser, the owner adds one review comment on the pull request's diff, which opens a thread, and approves the pull request. Run:

```sh
gh pr checks "$PR" --watch
./devctl as worker gh pr merge "$PR" --squash; echo "merge exit $?"
```

Expected: refused, because a review thread is unresolved. The owner resolves the thread in the browser, then:

```sh
./devctl as worker gh pr merge "$PR" --squash; echo "merge exit $?"
gh pr view "$PR" --json state,mergedBy
```

Expected: merged by the Worker App, and the head branch deleted. Record each step's result.

- [ ] **Step 11: Owner step: Flight with Agent identity, and whether GitHub counts the Reviewer App's approval**

The owner moves `rs-trial` to Flight through their own pull request: CODEOWNERS loses its `*` line and owns only the Protected set, and `[escalation]` sets `every_pr = false`.

```sh
git switch main && git pull --ff-only
git switch -c trial-flight
perl -ni -e 'next if /^\* @/; s{^# (/\S+ @\S+)$}{$1}; print' .github/CODEOWNERS
perl -pi -e 's/^every_pr = true/every_pr = false/' .rapid-ship/project.toml
grep -v '^#' .github/CODEOWNERS | grep -c '^/'
git commit -am "Move rs-trial to Flight"
git push -u origin trial-flight
gh pr create --base main --head trial-flight --title "Move rs-trial to Flight" --body-file "$TRIALS/pr-body.md"
gh pr merge trial-flight --squash --admin --delete-branch
git switch main && git pull --ff-only
./devctl doctor; echo "exit $?"
git switch -c trial-agent
printf '\nA Flight trial line.\n' >> README.md
git commit -am "Flight trial change"
./devctl as worker push; echo "push exit $?"
./devctl as worker gh pr create --base main --head trial-agent --title "Flight trial change" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR2=$(gh pr view trial-agent --json number --jq .number)
./devctl as reviewer gh pr review "$PR2" --approve --body "Trial approval by the Reviewer App"; echo "review exit $?"
gh pr view "$PR2" --json reviewDecision,mergeStateStatus,statusCheckRollup
./devctl as worker gh pr merge "$PR2" --squash; echo "pending merge exit $?"
gh pr checks "$PR2" --watch
gh pr view "$PR2" --json reviewDecision,mergeStateStatus
./devctl as worker gh pr merge "$PR2" --squash; echo "merge exit $?"
```

The `grep -c` prints 13, the agnostic stack's Protected set. Record every result. doctor's `ruleset` and `CODEOWNERS` items are expected ok for `every_pr = false` with Agent identity on.

README.md is outside the Protected set, so this pull request has no code owner, and the Reviewer App's approval is the only review it can get. The first merge attempt runs while the `devctl check` run is still queued or in progress, which `statusCheckRollup` shows. Expected: gh refuses it, exit nonzero. Record gh's message and the state just before it. When `reviewDecision` is `APPROVED`, the pending required check is the only gate left, so this refusal is GitHub enforcing `devctl check` (Spec 1 section 10). If the run had already finished, the attempt shows nothing about the check: record that, and Task 11's PR body names the gap under `Not covered:`.

The answer this step exists for: whether the last merge, after the check passed, succeeded with only the Reviewer App's approval. If it did, GitHub counts that approval, and the approval count stays 1; skip Step 11a. If GitHub refused the merge for want of an approval (`reviewDecision` stays `REVIEW_REQUIRED`), it does not count it: run Step 11a, and Step 17 applies.

- [ ] **Step 11a: Owner step, only when GitHub did not count the approval: set the trial ruleset's count to 0 and read it back**

```sh
perl -pi -e 's/"required_approving_review_count": 1/"required_approving_review_count": 0/' "$TRIALS/ruleset.json"
gh api --method PUT "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --input "$TRIALS/ruleset.json"
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq '.rules[] | select(.type == "pull_request") | .parameters.required_approving_review_count'
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq 'del(.node_id, ._links, .created_at, .updated_at, .current_user_can_bypass) | .id = 9 | .source = "o/r"' > "$PLAN4/tests/devctl/fixtures/github/ruleset.json"
./devctl as worker gh pr merge "$PR2" --squash; echo "merge exit $?"
```

Expected: the first read-back prints `0`, and `tests/devctl/fixtures/github/ruleset.json` in this plan's worktree now holds the count of 0; doctor still requires an approval, so Task 5's tests fail on that fixture until Step 17 changes doctor. `$PR2`, approved by the Reviewer App and with its check passed, now merges. If it is still refused, record GitHub's state and stop the trial here: a count of 0 is not enough for Flight with Agent identity, and the owner decides the ruleset before Step 17 runs. Otherwise:

```sh
git switch main && git pull --ff-only
git switch -c trial-agent-zero
printf '\nA Flight trial line under an approval count of 0.\n' >> README.md
git commit -am "Flight trial change under an approval count of 0"
./devctl as worker push; echo "push exit $?"
./devctl as worker gh pr create --base main --head trial-agent-zero --title "Flight trial change under an approval count of 0" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR4=$(gh pr view trial-agent-zero --json number --jq .number)
./devctl as reviewer gh pr review "$PR4" --approve --body "Trial approval by the Reviewer App"; echo "review exit $?"
gh pr view "$PR4" --json reviewDecision,mergeStateStatus,statusCheckRollup
./devctl as worker gh pr merge "$PR4" --squash; echo "pending merge exit $?"
gh pr checks "$PR4" --watch
./devctl as worker gh pr merge "$PR4" --squash; echo "merge exit $?"
```

Record every result. Expected: on `$PR4`, the merge attempt while its run is queued or in progress is refused, and the merge after the check passed succeeds. `$PR4` then differs from `$PR2`'s successful merge only by the pending check, so this pair shows GitHub enforcing `devctl check`. If the run had already finished at the first attempt, record that, as in Step 11.

- [ ] **Step 12: Owner step: a Reviewer App change request, and a workflow change**

```sh
git switch main && git pull --ff-only
git switch -c trial-agent-2
printf '\nAnother Flight trial line.\n' >> README.md
git commit -am "Second Flight trial change"
./devctl as worker push; echo "push exit $?"
./devctl as worker gh pr create --base main --head trial-agent-2 --title "Second Flight trial change" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR3=$(gh pr view trial-agent-2 --json number --jq .number)
./devctl as reviewer gh pr review "$PR3" --request-changes --body "Trial change request by the Reviewer App"; echo "review exit $?"
gh pr checks "$PR3" --watch
gh pr view "$PR3" --json reviewDecision,mergeStateStatus
```

Expected: `CHANGES_REQUESTED`, and, with the count at 1, a blocked merge, read after the check passed. Record what GitHub reports: it tells Spec 3 whether the Reviewer App's change requests count as Revisions. After Step 11a the count is 0: record whether the change request alone still blocks the merge.

Next, the owner changes `.github/workflows/devctl-check.yml` on `main` through their own pull request, merged with the admin bypass, and the agent branch takes that change in:

```sh
git switch main
git switch -c trial-workflow
printf '# A trial comment.\n' >> .github/workflows/devctl-check.yml
git commit -am "Trial workflow comment"
git push -u origin trial-workflow
gh pr create --base main --head trial-workflow --title "Trial workflow comment" --body-file "$TRIALS/pr-body.md"
gh pr merge trial-workflow --squash --admin --delete-branch
git switch trial-agent-2
git fetch origin main && git merge --no-edit origin/main
./devctl as worker push; echo "push exit $?"
```

Record GitHub's message, devctl's `devctl: neither App may push a change under .github/workflows/; ...` line and the exit code. Expected: GitHub refuses the Worker App's push, because the merge brings in a workflow change (Checked facts), and devctl returns git's nonzero exit code with the hint. If GitHub accepts the push, record that; the hint still serves a direct workflow edit.

- [ ] **Step 13: Owner step: `doctor --skills` live**

The follow-ups removed this step's run with a `[roster]` table, and its sign-in items, after the owner descoped several Providers, and follow-up 9 narrowed it to Claude Code. Run the probe:

```sh
./devctl doctor --skills; echo "exit $?"
git worktree list
```

Record every skills line and the exit code. Expected: one `skills (claude)` item when `claude` is on `PATH`, ok with `1 repository skills seen` and `not checked, user-invoked: trial-release`, never listing `trial-release` as outside the repository; outside skills are listed for information. `git worktree list` shows only the clone. Record whether Claude Code listed `trial-release` anyway, and confirm or correct `PROBE_MODEL`; a wrong model is fixed in `harness.py`, with its test, in this plan's PR.

- [ ] **Step 14: Owner step: clean up**

Close any open trial pull request. The owner decides whether to delete `rs-trial` and `rs-trial-private`; the Apps stay, as the owner's real Apps.

- [ ] **Step 15: Write the report (implementer, from the owner's record)**

Write `docs/trials/<trial date>-agent-identity.md` from the owner's record of Steps 2 to 14: a summary, the versions, then one section per step with its commands, exit codes, output and result, and the deviations from Checked facts. Its limits section names at least: any process the owner runs can read both keys (Step 5); the Reviewer App's approval does or does not count (Step 11); whether GitHub refused a merge while `devctl check` was pending (Step 11 or 11a), or that the run had finished before the attempt; and whether a merge that brings in a workflow change is refused (Step 12). Link it from `docs/trials/AGENTS.md` with one line naming what it records.

- [ ] **Step 16: Commit the report, and the fixture when the count stays 1 (implementer)**

From this plan's worktree, when Step 11a did not run:

```sh
./devctl check --tier fast
git add docs/trials tests/devctl/fixtures/github/ruleset.json
git commit -m "docs: record the Agent identity, ruleset and doctor trial" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

When Step 11a ran, the fixture holds a count of 0 that doctor does not yet accept, so leave it out of this commit: run the same commands with `git add docs/trials` only. Step 17 commits the fixture with the change that accepts it.

- [ ] **Step 17: Settle the approval count in the index and Spec 1 (implementer)**

Step 11 answered Spec 1 section 11's open question. Make the edits for its answer, then commit.

**If GitHub counts the Reviewer App's approval**, change no code. In `docs/superpowers/plans/2026-10-14-kit-and-setup.md`, replace:

```markdown
- Plan 4's live trial settles the approval count with Agent identity in Flight (Spec 1 section 8, step 7). If GitHub does not count the Reviewer App's approval, the count becomes 0, and both plans change this paragraph.
```

with:

```markdown
- Plan 4's live trial found that GitHub counts the Reviewer App's approval toward this count, so it stays 1 with Agent identity in Flight (Spec 1 section 8, step 7).
```

In `docs/superpowers/specs/2026-10-14-kit-and-setup-design.md`, replace section 8, step 7.3:

```markdown
   3. The required approval count is `1` until the live trial (section 10) settles it. With Agent identity in Flight, a PR outside the Protected set has no code owner, so unless the owner reviews it, its approval must come from the Reviewer App. If GitHub does not count that approval, the count becomes `0` and code-owner review stays required, so CODEOWNERS alone decides who must approve: the owner for every path in Walk, and for the Protected set in Flight.
```

with:

```markdown
   3. The required approval count is `1`. With Agent identity in Flight, a PR outside the Protected set has no code owner, so unless the owner reviews it, its approval comes from the Reviewer App, which plan 4's live trial found GitHub counts.
```

**If GitHub does not count it**, the count becomes 0 and code-owner review alone decides who must approve, so doctor stops requiring an approval count. Step 11a already set the trial ruleset's count to 0 and wrote its read-back to `tests/devctl/fixtures/github/ruleset.json`, so the fixture holds 0; check with `grep -n '"required_approving_review_count"' tests/devctl/fixtures/github/ruleset.json`. Write the failing test first: append to `tests/devctl/test_devctl_doctor_github.py`:

<!-- fmt:off -->
```python


def test_an_approval_count_of_zero_passes_while_code_owner_review_is_required() -> None:
    ruleset = copy.deepcopy(RULESET)
    rule(ruleset, "pull_request")["parameters"].update(required_approving_review_count=0)
    assert ruleset_problems([ruleset], "main", every_pr=True, agent_identity=True) == []
```
<!-- fmt:on -->

and in `test_only_flight_without_agent_identity_accepts_no_review_requirement`, replace `        assert NO_APPROVAL in problems` with `        assert NO_APPROVAL not in problems`. Run `uv run pytest tests/devctl/test_devctl_doctor_github.py -q` and see both tests fail, with every test that checks the fixture as the whole ruleset, such as `test_the_rs_setup_ruleset_passes`, because the fixture now holds Step 11a's count of 0. Then, in `rapid_ship/templates/common/tools/devctl/devctl/doctor_rules.py`, delete the function `_approves` and, in `_pull_request_problems`, delete this line:

<!-- fmt:off -->
```python
        (not review or _approves(params.get("required_approving_review_count")), NO_APPROVAL),
```
<!-- fmt:on -->

Run `uv run ruff format` and `uv run ruff check` on `doctor_rules.py`, then `uv run rapid-ship sync --in-place`, and see `uv run pytest tests/devctl -q` pass with the fixture's count of 0.

In the index, replace `` A `pull_request` rule with `required_approving_review_count` 1, `` with `` A `pull_request` rule with `required_approving_review_count` 0, ``, and replace the bullet quoted above with:

```markdown
- Plan 4's live trial found that GitHub does not count the Reviewer App's approval, so the count is 0 and code-owner review decides who must approve (Spec 1 section 8, step 7).
```

In Spec 1, replace section 8, step 7.3, quoted above, with:

```markdown
   3. The required approval count is `0`, and code-owner review stays required, so CODEOWNERS alone decides who must approve: the owner for every path in Walk, and for the Protected set in Flight. Plan 4's live trial found that GitHub does not count the Reviewer App's approval.
```

**Either way**, in Spec 1 section 11, delete the open item that starts `- **The ruleset's approval count with Agent identity in Flight:**`, and add this line to the end of the "Answered" list when GitHub counts the approval:

```markdown
- **The ruleset's approval count** is `1`: plan 4's live trial found that GitHub counts the Reviewer App's approval (section 8, step 7).
```

or this line when it does not:

```markdown
- **The ruleset's approval count** is `0`, with code-owner review required: plan 4's live trial found that GitHub does not count the Reviewer App's approval (section 8, step 7).
```

Then commit:

```sh
./devctl check --tier fast
npm --prefix website run build
git add -A docs tests rapid_ship/templates tools/devctl .rapid-ship/kit.lock
git commit -m "docs: settle the ruleset's approval count from plan 4's trial" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 11: Verification and record

The last task runs every check, opens the PR with its Evidence, and records actual results in this plan's Verification record. A skipped, blocked or simulated result is recorded as such and never as a pass.

**Files:**
- Modify: this plan, `docs/superpowers/plans/2026-10-16-doctor-and-agent-identity.md` (the Verification record)
- Modify: `docs/superpowers/plans/2026-10-14-kit-and-setup.md` (plan 4's row)

**Interfaces:**
- Consumes: everything Tasks 1 to 10 built and recorded.
- Produces: the PR, and the record that its review reads.

- [ ] **Step 1: Run the full verification**

The PR stacks on #30 while #30 is open, and the full tier names that base:

```sh
if [ "$(gh pr view 30 --json state --jq .state)" = MERGED ]; then BASE=main; else BASE=codex/devctl-check; fi
git fetch origin "$BASE"
./devctl check --tier full --base "origin/$BASE"; echo "check exit $?"
uv run rapid-ship status --strict
uv run pytest -q
./devctl doctor; echo "doctor exit $?"
./devctl doctor --help && ./devctl as --help && uv run rapid-ship app --help
npm --prefix website ci --no-audit --no-fund
npm --prefix website run build
```

Expected:
- `./devctl check` exits 1, and only `diff` fails: it names the three tests the re-scope removed, each ending `(pass --pr-body <file> to check a body locally)`, and lists the Protected paths the change touches. `evidence` is not applicable. Every other step passes: `exceptions` with EX-11 as the only new entry, and `file-size` with `rapid_ship/github_app.py` at 499 lines.
- `status --strict` exits 0, and pytest passes with none skipped.
- `./devctl doctor` on this repository: record every line and the exit code. This repository records no Apps, so no `agent identity` item appears. Expect missing items for the ruleset, `delete branch on merge` and `fork PR workflow approval` until plan 6 applies `rs-setup`'s GitHub settings here (an Owner step); those are this repository's settings, not failures of this plan. `tools/devctl exclusions` is expected ok, with the note that this repository holds the Kit templates.
- Each `--help` exits 0; doctor's lists `--skills`, and `as` lists `{worker,reviewer}` and `{push,gh}`.
- The site build exits 0 with no broken link.

- [ ] **Step 2: Write the PR body and check it**

Write the PR description to a file outside the repository, `BODY=$(mktemp)`. It states the problem and the resulting behaviour. Its `## Evidence` section lists each Step 1 command with its actual result and the Task 10 trial report, names EX-11 and why it exists, and declares the three tests the re-scope removed:

```markdown
Removed tests:
- `tests/devctl/test_devctl_settings.py::test_agents_keep_the_exact_model`: [agents] is removed; test_a_removed_table_names_what_replaced_it covers its refusal
- `tests/devctl/test_devctl_diff_removed_tests.py::test_declared_removal_passes_and_flight_waits_for_the_owner`: gate.toml and the step's Flight note are removed; test_declared_removal_passes_with_its_reason_and_no_mode covers the step
- `tests/test_kit_contents.py::test_gate_seed_has_the_spec_defaults`: the Kit no longer seeds gate.toml; test_the_kit_no_longer_seeds_gate_toml covers it
```

The section ends with a line starting `Not covered:` that names what stayed offline or unproven: organisation-owned repositories, Linux and Windows for Agent identity, Harness output beyond the versions Task 10 recorded, this repository's own ruleset and GitHub settings, which plan 6 applies, and, when Task 10 never caught a `devctl check` run before it finished, GitHub refusing a merge while the check is pending. Then:

```sh
./devctl check --tier full --base "origin/$BASE" --pr-body "$BODY"; echo "check exit $?"
```

Expected: exit 0. `diff` passes with a `declared (...)` note for each of the three tests, and `evidence` passes.

- [ ] **Step 3: Owner step: push and open the PR**

The implementer gives the owner the path of `$BODY`. The owner runs, from this plan's worktree in their own terminal, with that path in place of `<body path>`:

```sh
if [ "$(gh pr view 30 --json state --jq .state)" = MERGED ]; then BASE=main; else BASE=codex/devctl-check; fi
BODY=<body path>
git push -u origin doctor-agent-identity
gh pr create --base "$BASE" --head doctor-agent-identity --title "feat: add devctl doctor and optional Agent identity (plan 4)" --body-file "$BODY"
gh pr checks --watch
```

Expected: the `devctl check` job passes. The implementer records the PR URL and the run URL from the owner's output.

- [ ] **Step 4: Mark plan 4 built in the index**

```sh
N=$(gh pr view --json number --jq .number)
perl -pi -e "s{\| 4 \| \[Doctor and Agent identity\]\(#plan-4-doctor-and-agent-identity\)}{| 4 | [Doctor and Agent identity](2026-10-16-doctor-and-agent-identity.md)}; s{\| 3, 4, 6, 10 \| 3 \| Proposed \|}{| 3, 4, 6, 10 | 3 | Built: PR #$N, \`doctor-agent-identity\` |}" docs/superpowers/plans/2026-10-14-kit-and-setup.md
grep -n "^| 4 |" docs/superpowers/plans/2026-10-14-kit-and-setup.md
```

Expected: plan 4's row links this plan and reads `Built: PR #<the PR's number>, \`doctor-agent-identity\``.

- [ ] **Step 5: Fill in the Verification record and commit**

Fill in every field of the Verification record below with actual output. Ruff formats this plan's `python` blocks (Checked facts): record output as plain text or in `text` or `sh` blocks, and wrap any `python` block that is not in Ruff's layout in `<!-- fmt:off -->` and `<!-- fmt:on -->` lines. Then:

```sh
uv run ruff format --check docs/superpowers/plans/2026-10-16-doctor-and-agent-identity.md
./devctl check --tier fast
git add docs/superpowers/plans/2026-10-16-doctor-and-agent-identity.md docs/superpowers/plans/2026-10-14-kit-and-setup.md
git commit -m "docs: record plan 4's verification" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Pushing it is an Owner step. The owner runs `git push` from this plan's worktree in their own terminal, and the PR's checks run again on the new head.

## Verification record

Fill in after Task 11. Record actual output, not expectations. Mark live, offline and simulated results separately; a skipped or blocked step is not a pass.

- Baseline on #30's head (Task 1 Step 1): commit, `./devctl check` and `status --strict` exit codes: #30's head is `928fbe4` (PR #30 was open when Step 1 ran). This branch started at `a7177bc`, which adds this plan to it. Task 1's report records, before any change, `./devctl check --base origin/codex/devctl-check` with every step passed and `evidence` not applicable (the report prints no exit code), and `uv run rapid-ship status --strict` exit 0 with "24 managed files unchanged." These are Task 1's reported results; Task 11 did not re-run the baseline.
- Each task's commit and its test command's result (Tasks 1 to 9): These are the implementers' reported results. The plan-4 tests behind them are offline and simulated: a fake GitHub on 127.0.0.1, a fake Keychain, local bare repositories and fake Harness executables. Each task also ran the whole suite once before its commit, and the whole suite is not all offline: two of its files need network access and gitleaks 8.30.1 (see `uv run pytest -q` below). Task 11 re-ran the whole suite on `82d03f0`.
  - Task 1, `24e7a2b` (fix: let run_process finish when macOS refuses SIGTERM, and share first_line): `uv run pytest tests/devctl/test_devctl_process.py -q`, 23 passed; whole suite 764 passed.
  - Task 2, `7e87fe4` (the settings; the follow-ups removed its `[roster]` table after the owner descoped several Providers): `uv run pytest tests/devctl/test_devctl_settings.py -q`, 53 passed; `uv run pytest tests/devctl tests/test_kit_contents.py tests/test_kit_dogfood.py -q`, 477 passed; whole suite 777 passed.
  - Task 3, `9cd2c95` (feat: mint App installation tokens and pass them to git through askpass): the GitHub client, App, askpass, kit-step and kit-contents test files, 109 passed; whole suite 832 passed.
  - Task 4, `ad6243e` (doctor's local items; the follow-ups removed its Harness sign-in items after the owner descoped several Providers): the doctor-local, kit-summary, python-guardrails, harness and kit-step test files, 282 passed; whole suite 1086 passed.
  - Task 5, `b1b925c` (feat: check the ruleset, CODEOWNERS and, with Agent identity on, both Apps in devctl doctor): `uv run pytest tests/devctl -q`, 818 passed; whole suite 1148 passed.
  - Task 6, `0b85534` (feat: compare the skills each Harness loads at HEAD with devctl doctor --skills): the probe-worktree, doctor-skills and doctor-local test files, 176 passed; whole suite 1188 passed.
  - Task 7, `8d68745` (feat: create and install the Worker and Reviewer Apps with rapid-ship app): `uv run pytest tests/test_kit_app.py tests/test_kit_app_limits.py tests/devctl/test_devctl_github_app.py -q`, 51 passed; whole suite 1231 passed.
  - Task 8, `fc93c71` (feat: push and run gh as the Worker or Reviewer App with devctl as): `uv run pytest tests/devctl/test_devctl_identity.py tests/devctl/test_devctl_identity_limits.py tests/devctl/test_devctl_cli.py -q`, 42 passed; whole suite 1267 passed. An earlier full-tier run on the same head exited 1 because `uv` could not fetch hatchling ("Network is unreachable") in `test_own_check_steps_still_run_after_sync`; the rerun with no code change exited 0.
  - Task 9, `c2f0a70` (docs: describe devctl doctor, Agent identity and devctl as in the guides and status lines): Markdown only; `./devctl check --tier fast` exit 0, `npm --prefix website run build` exit 0, `uv run pytest -q -x` 1267 passed.
  - Task 10, `82d03f0` (docs: record plan 4's live trials as pending Owner steps): Markdown only; it ran no trial step. `uv run ruff format --check` on this plan and `./devctl check --tier fast` exit 0.
- `./devctl check --tier full --base origin/<base>` without a body: exit code, and each step that did not pass with its details: exit 1, with `<base>` = `codex/devctl-check` because #30 was open. Only `diff` failed, as expected: it names the three tests the re-scope removed, each ending "(pass --pr-body <file> to check a body locally)", and lists the 33 Protected paths the change touches. `evidence` is not applicable ("not a pull request"). Every other step passed, including `exceptions` with EX-11 as the only new entry and `file-size` with `rapid_ship/github_app.py` at 499 lines. Run live on `82d03f0`: the full tier needs network access and gitleaks 8.30.1. The whole output follows.
  ```text
  passed         format
  passed         lint
  passed         map
  passed         exceptions
  passed         file-size
  passed         kit
  passed         types
  passed         contracts
  passed         tests
  passed         audit
  passed         secrets
  passed         workflows
  failed         diff
      removed behavioural test tests/devctl/test_devctl_settings.py::test_agents_keep_the_exact_model: declare it under 'Removed tests:' in the PR's Evidence section (pass --pr-body <file> to check a body locally)
      removed behavioural test tests/devctl/test_devctl_diff_removed_tests.py::test_declared_removal_passes_and_flight_waits_for_the_owner: declare it under 'Removed tests:' in the PR's Evidence section (pass --pr-body <file> to check a body locally)
      removed behavioural test tests/test_kit_contents.py::test_gate_seed_has_the_spec_defaults: declare it under 'Removed tests:' in the PR's Evidence section (pass --pr-body <file> to check a body locally)
      protected: .rapid-ship/exceptions.toml
      protected: .rapid-ship/gate.toml
      protected: .rapid-ship/kit.lock
      protected: .rapid-ship/project.toml
      protected: AGENTS.md
      protected: docs/superpowers/AGENTS.md
      protected: pyproject.toml
      protected: rapid_ship/AGENTS.md
      protected: rapid_ship/templates/AGENTS.md
      protected: tests/AGENTS.md
      protected: tools/AGENTS.md
      protected: tools/devctl/devctl/check/diff.py
      protected: tools/devctl/devctl/check/kit.py
      protected: tools/devctl/devctl/check/stacks/python.py
      protected: tools/devctl/devctl/check/steps.py
      protected: tools/devctl/devctl/cli.py
      protected: tools/devctl/devctl/doctor.py
      protected: tools/devctl/devctl/doctor_github.py
      protected: tools/devctl/devctl/doctor_items.py
      protected: tools/devctl/devctl/doctor_local.py
      protected: tools/devctl/devctl/doctor_rules.py
      protected: tools/devctl/devctl/doctor_signin.py
      protected: tools/devctl/devctl/doctor_skills.py
      protected: tools/devctl/devctl/github/__init__.py
      protected: tools/devctl/devctl/github/api.py
      protected: tools/devctl/devctl/github/app.py
      protected: tools/devctl/devctl/github/askpass.py
      protected: tools/devctl/devctl/harness.py
      protected: tools/devctl/devctl/identity.py
      protected: tools/devctl/devctl/process.py
      protected: tools/devctl/devctl/settings.py
      protected: tools/devctl/pyproject.toml
      protected: tools/devctl/uv.lock
  not applicable evidence
      not a pull request
  passed         vendored
  passed         distribution
  passed         python-3.12
  check exit 1
  ```
- The same run with `--pr-body`: exit code, the `diff` notes and the `evidence` status: exit 0, run on `82d03f0` with the PR body written for Step 2 (kept outside Git at `/Users/shawn/workspace/rapid-ship/.worktrees/doctor-agent-identity/.superpowers/sdd/2026-10-16-doctor-and-agent-identity/task-11-pr-body.md`). `diff` passed with a `declared (...)` note for each of the three removed tests, and `evidence` passed. Every other step passed. The output follows, without its 33 `protected:` lines, which are the same as above, and without the reason declared for `test_agents_keep_the_exact_model`, which named a `[roster]` test that the follow-ups removed after the owner descoped several Providers.
  ```text
  passed         format
  passed         lint
  passed         map
  passed         exceptions
  passed         file-size
  passed         kit
  passed         types
  passed         contracts
  passed         tests
  passed         audit
  passed         secrets
  passed         workflows
  passed         diff
      removed behavioural test tests/devctl/test_devctl_settings.py::test_agents_keep_the_exact_model: declared (...)
      removed behavioural test tests/devctl/test_devctl_diff_removed_tests.py::test_declared_removal_passes_and_flight_waits_for_the_owner: declared (gate.toml and the step's Flight note are removed; test_declared_removal_passes_with_its_reason_and_no_mode covers the step)
      removed behavioural test tests/test_kit_contents.py::test_gate_seed_has_the_spec_defaults: declared (the Kit no longer seeds gate.toml; test_the_kit_no_longer_seeds_gate_toml covers it)
  passed         evidence
  passed         vendored
  passed         distribution
  passed         python-3.12
  check exit 0
  ```
- `uv run rapid-ship status --strict`: exit 0.
  ```text
  Kit 0.1.0 (installed rapid-ship 0.1.0), stack python
  37 managed files unchanged.
  status exit 0
  ```
- `uv run pytest -q`: passed, failed and skipped counts: 1267 passed, 0 failed, 0 skipped, in 178.07 s, exit 0, on `82d03f0`. The results are of two kinds. The plan-4 tests (doctor, the token code, `rapid-ship app` and `devctl as`) are offline and simulated: a fake GitHub on 127.0.0.1, a fake Keychain, local bare repositories and fake Harness executables. `tests/devctl/test_devctl_check_integration.py` and `tests/devctl/test_devctl_project_dogfood.py` ran live, as `tests/AGENTS.md` says they need: with network access (PyPI, pip-audit's lookups, and `uv run --locked rapid-ship sync --in-place` in a copy of the work tree) and gitleaks 8.30.1 on `PATH`. `tests/test_gitleaks_settings.py` ran real gitleaks offline. The summary line names no failed, skipped, xfailed or errored test.
  ```text
  1267 passed in 178.07s (0:02:58)
  pytest exit 0
  ```
- `./devctl doctor` on this repository: every line and the exit code: exit 1, live (it read this machine, this repository and GitHub with the owner's `gh` sign-in, as `GET`). No `agent identity` item appears, because this repository records no Apps (`worker_app_id = 0`, empty slugs). `tools/devctl exclusions` is ok, with the note that this repository holds the Kit templates. Five items are missing; none is a failure of this plan:
  - `core.hooksPath`: unset in this linked worktree (the pre-commit hook does not run here, so each commit ran `./devctl check --tier fast` by hand).
  - `CODEOWNERS`: `.github/CODEOWNERS` is in this branch but not on `main`, because `main` (`f7b877b`) does not hold #28 to #30 yet.
  - `ruleset`, `delete branch on merge` and `fork PR workflow approval`: this repository's own GitHub settings, which plan 6's `rs-setup` applies (an Owner step).
  ```text
  ok  toolchain  git: 2.39.5
  ok  toolchain  uv: /opt/homebrew/bin/uv
  ok  toolchain  gh: /opt/homebrew/bin/gh
  ok  toolchain  gh sign-in: gh auth status exited 0
  ok  toolchain  gitleaks: 8.30.1
  missing  guardrails  core.hooksPath: core.hooksPath is not set; run git config core.hooksPath .githooks; the pre-commit hook runs devctl check --tier fast
  ok  guardrails  CI workflow: .github/workflows/devctl-check.yml has a job named devctl check
  ok  guardrails  Python guardrail settings: meets the Python floor of spec section 4
  ok  guardrails  tools/devctl exclusions: ruff, mypy and pytest not checked: this repository holds the Kit templates
  ok  kit  Kit files: Kit 0.1.0: 37 unchanged, 0 modified, 0 excluded; run uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.1.0 rapid-ship status to see template updates
  missing  github  ruleset: no ruleset targets the default branch
  missing  github  CODEOWNERS: .github/CODEOWNERS is not on main
  missing  github  delete branch on merge: turn on Automatically delete head branches in the repository settings
  missing  github  fork PR workflow approval: approval_policy is first_time_contributors; require approval for all outside contributors under Settings, Actions, General
  doctor: 9 ok, 5 missing, 0 unknown
  doctor exit 1
  ```
- `--help` of `devctl doctor`, `devctl as` and `rapid-ship app`: each exit 0. doctor's lists `--skills`, `as` lists `{worker,reviewer}` and `{push,gh}`, and `app` lists `--repository OWNER/NAME`.
  ```text
  usage: devctl doctor [-h] [--skills]

  Report each item as ok, missing or unknown. Exit 0 when every item is ok, 1
  when one is missing, 2 when one is unknown.

  options:
    -h, --help  show this help message and exit
    --skills    also start one headless Session per Harness in a temporary
                worktree at HEAD and compare the skills it loads; spends a
                little quota
  doctor --help exit 0
  usage: devctl as [-h] {worker,reviewer} {push,gh} ...

  push: push the current branch to the branch of the same name on GitHub, as the
  Worker App; it never forces. gh: run gh pr, gh issue or gh api as the role's
  App. Exit 1 when devctl refuses, 2 when it cannot mint a token or start the
  tool, otherwise the tool's exit code.

  positional arguments:
    {worker,reviewer}
    {push,gh}
    arguments          gh's arguments; push takes none

  options:
    -h, --help         show this help message and exit
  as --help exit 0
  usage: rapid-ship app [-h] [--repository OWNER/NAME]

  options:
    -h, --help            show this help message and exit
    --repository OWNER/NAME
                          the GitHub repository to install the Apps on; default:
                          the one gh finds here
  app --help exit 0
  ```
- Docs site build: `npm --prefix website ci --no-audit --no-fund` exit 0 (only npm's allow-scripts notice for `core-js` and `fsevents`), then `npm --prefix website run build` exit 0 with `[SUCCESS] Generated static files in "build".` and no broken-link warning or error. That build ran on `82d03f0`, before this record was filled in.
  ```text

  > rapid-ship-docs@0.1.0 build
  > docusaurus build

  [INFO] [en] Creating an optimized production build...
  [webpackbar] ℹ Compiling Client
  [webpackbar] ℹ Compiling Server
  [webpackbar] ✔ Server: Compiled successfully in 7.39s
  [webpackbar] ✔ Client: Compiled successfully in 11.96s
  [SUCCESS] Generated static files in "build".
  [INFO] Use `npm run serve` command to test your build locally.
  build exit 0
  ```
  Rebuilt after this record was filled in, from the same work tree: `npm --prefix website run build` exit 0 with `[SUCCESS] Generated static files in "build".` and no broken-link warning or error. The built page for this plan holds the "Task 11: pending Owner steps" subsection.
- Live trial report and its deviations from Checked facts (Task 10), with the approval-count answer and the Step 17 edits it led to: Pending owner step. No agent ran Task 10 Steps 1 to 14. Outside the trial, the equivalents of Steps 3 to 5 ran on this repository on 2026-10-19, and no output was kept; "Task 10: pending Owner steps" below records what is known. There is no report under `docs/trials/`, no live ruleset fixture and no approval-count answer, and Step 17 has not run. Each step's command and what it must observe are under "Task 10: pending Owner steps" below.
- GitHub refusing a merge while `devctl check` was pending (Task 10 Step 11, or Step 11a), with `reviewDecision` and the run's state at the attempt, or that the run had finished first: Pending owner step. Nothing was observed: no `reviewDecision` and no run state were read. The commands are under "Task 10: pending Owner steps" below, and the PR body's `Not covered:` line names this gap until the owner's record fills it.
- `PROBE_MODEL` as confirmed or corrected in Task 10 Step 13: Pending owner step. Unconfirmed: `harness.py` holds `haiku`, the value of the Checked facts. Follow-up 9 removed the codex and agy models, `gpt-6-luna` and `gemini-3.8-flash-low`, with their probes.
- PR URL, base, and the `devctl check` run: Pending owner step. No PR exists, so there is no PR URL and no `devctl check` run on GitHub. The base is `codex/devctl-check` while #30 is open, and `main` once it is merged. The PR body is written and passes `./devctl check --tier full --base origin/codex/devctl-check --pr-body <body>` with exit 0 (above). The commands are under "Task 11: pending Owner steps" below.
- Final whole-branch review: two Important findings, handled after this record was first filled in.
  - R1, fixed in `ab473c6` (fix: pass doctor's tools the owner's sign-in and proxy variables). doctor's tools ran with only `PATH`, `HOME` and the locale, so a sign-in held only in the environment, such as `GH_TOKEN`, an API key, a gateway, Bedrock, Vertex, `CLAUDE_CONFIG_DIR` or `CODEX_HOME`, read as missing. Each tool doctor runs now gets the owner's proxy and certificate variables, where the owner's files live, and its own sign-in variables (`SIGN_IN_VARIABLES` in `doctor_items.py`). `devctl as` passes `gh` and `git push` the proxy and certificate variables only. The 17 new tests are offline and simulated, with fake tools that answer from their own environment: `tests/devctl/test_devctl_doctor_environment.py`, and one test each in `test_devctl_doctor_skills.py`, `test_devctl_identity.py` and `test_devctl_askpass_limits.py`. Which variables each real Harness reads is unconfirmed.
  - R2, recorded and not fixed, because the fix needs a spec decision: doctor's CODEOWNERS item cannot pass on an organisation-owned repository (Remaining limits, below). Its Linear task is a pending Owner step under "Task 11: pending Owner steps".
  - Re-run on `ab473c6`, live as above: `./devctl check --tier full --base origin/codex/devctl-check` exit 1, with only `diff` failing, on the same three removed tests and 33 Protected paths; the same with the PR body exit 0, every step passed; `uv run rapid-ship status --strict` exit 0, "37 managed files unchanged."; `uv run pytest -q` "1284 passed in 193.93s (0:03:13)", exit 0; `./devctl doctor` exit 1, the same 14 lines as above and "doctor: 9 ok, 5 missing, 0 unknown"; each `--help` exit 0; `npm --prefix website ci --no-audit --no-fund` exit 0 and `npm --prefix website run build` exit 0 with `[SUCCESS] Generated static files in "build".` After this entry was written, the build ran again from the work tree and exited 0 with the same line and no broken-link warning.
- Remaining limits, including at least: Agent identity works only on macOS, where any process the owner runs can read both App keys through `security`; a Worker can therefore act as the Reviewer App, and `rs-work` (Spec 2) is the only barrier; organisation-owned repositories cannot install the owner's private Apps; and this repository's own ruleset and GitHub settings wait for plan 6:
  - Agent identity works only on macOS, where any process the owner runs can read both App keys through `security`. A Worker can therefore act as the Reviewer App, and `rs-work` (Spec 2) is the only barrier.
  - Organisation-owned repositories cannot install the owner's private Apps, and doctor's CODEOWNERS item cannot pass on one. doctor takes the code owner from the repository's owner (`tools/devctl/devctl/doctor_github.py:134`), so it asks for `* @<organisation>`, which is not a valid code owner, and reports the owner's correct `* @<login>` as wrong; doctor never exits 0 there. The fix needs a spec decision, to record the owner's login or to scope Spec 1 to personal repositories, and must land before plan 6's `rs-setup` runs doctor for owners.
  - devctl's own REST client, which mints App tokens and reads the Apps, does not use `HTTPS_PROXY`. Where GitHub is reachable only through a proxy, `devctl as` and doctor's App items cannot mint a token.
  - This repository's own ruleset and GitHub settings (the ruleset, `delete branch on merge`, `fork PR workflow approval`, and CODEOWNERS on `main`) wait for plan 6.
  - Linux and Windows are untested for Agent identity.
  - The live results in this record are `./devctl check`, `./devctl doctor`, the docs site build and, within `uv run pytest -q`, the two network-dependent test files named there (`test_devctl_check_integration.py` and `test_devctl_project_dogfood.py`); the rest of the suite is offline, simulated except for `tests/test_gitleaks_settings.py`, which runs real gitleaks. The live trial (Task 10), the approval count, `app_slug` on the installation object, GitHub refusing a merge while `devctl check` is pending, and the three `PROBE_MODELS` are pending Owner steps. The doctor run on this repository suggests that the installation object carries `app_slug`, but its output was not kept (Task 10 Step 5, below).
  - `devctl as` exits 2 when the tool's output was cut or the tool timed out, even if the tool exited 0 (ruling P5). Spec 1 section 11 still lists the exit-code pass-through as an open Proposal, and this PR does not edit the spec for it.
  - `rapid_ship/github_app.py` is at 499 of the 500 lines that `file-size` allows.

### Task 10: pending Owner steps

Every step of Task 10 is an Owner step, and no agent ran any of them. Outside the trial, on 2026-10-19, the owner created the Worker App and the Reviewer App and installed both on this repository, `proxy-hatch/rapid-ship`; `./devctl doctor` then ran here. Commit `699fe95` records both Apps under `[github]` in this repository's `.rapid-ship/project.toml`, and its message is the only record of these runs: no command output or exit code was kept. Steps 3 to 5 below start with what is known of them. The trial itself has not run: it works in `rs-trial`, and `gh api repos/proxy-hatch/rs-trial` returned 404 on 2026-10-20.

Below, each step has the exact command and what it must observe, copied from Task 10, so the owner's session can be compared with them. Apart from the runs on this repository in Steps 3 to 5, nothing here is a result. Each of Steps 1 to 17 stays "Pending owner step" for the trial, neither a pass nor a skip, until the owner's record of Steps 2 to 14 replaces its entry with the exit code, the output and a live mark.

Where this stood at `c2f0a70`, the base of this record: `docs/trials/` holds no `*-agent-identity.md` report and `docs/trials/AGENTS.md` links none; `tests/devctl/fixtures/github/ruleset.json` is still the offline fixture from Task 5, the ruleset the index specifies with `id` 9, `source` `o/r` and `required_approving_review_count` 1; `doctor_rules.py` still requires an approval; the index's approval-count paragraph, Spec 1 section 8, step 7.3 and Spec 1 section 11's open item read as drafted; and `PROBE_MODELS` in `harness.py` holds `haiku`, `gpt-6-luna` and `gemini-3.8-flash-low`, the values of the Checked facts.

The owner runs Steps 2 to 14 in one terminal session, from this plan's worktree, because later steps use the shell variables earlier ones set. The owner keeps each command with its exit code and output. A trial report never records a token, a private key, a client secret or an email address; a token's length may be recorded.

#### Step 1: accept the outside changes

Pending owner step. Command: none. The owner reads the list of outside changes in Task 10 Step 1 and starts Step 2 only if they accept every change on it.

Must observe: the owner's own acceptance of every change on that list. Until then none of Steps 2 to 14 starts.

#### Step 2: record the versions and prepare `rs-trial`

Pending owner step. Run from this plan's worktree:

```sh
PLAN4=$(pwd)
TRIALS=$(mktemp -d)
OWNER=$(gh api user --jq .login)
sw_vers -productVersion; git --version; gh --version | head -1; uv --version
git -C "$PLAN4" rev-parse HEAD
gh api user --jq .plan.name
claude --version
cd "$TRIALS"
gh repo create "$OWNER/rs-trial" --public --add-readme --clone
cd rs-trial
uvx --from "$PLAN4" rapid-ship init --stack agnostic --owner "$OWNER" --repository "$OWNER/rs-trial"
mkdir -p .agents/skills/trial-notes .agents/skills/trial-release .claude/skills
printf -- '---\nname: trial-notes\ndescription: Notes on the rs-trial repository. Use before editing README.md.\n---\n\nKeep README.md to one paragraph.\n' > .agents/skills/trial-notes/SKILL.md
printf -- '---\nname: trial-release\ndescription: Release steps for the rs-trial repository.\ndisable-model-invocation: true\n---\n\nRun only when the owner asks.\n' > .agents/skills/trial-release/SKILL.md
ln -s ../../.agents/skills/trial-notes .claude/skills/trial-notes
ln -s ../../.agents/skills/trial-release .claude/skills/trial-release
./devctl check --tier fast; echo "exit $?"
git add .agents .claude && git commit -m "Add two trial skills"
git switch main && git merge --ff-only rapid-ship/init && git push origin main
```

Must observe: the fast check exits 0 (map rule 7 accepts both skills and links), and `main` holds the Kit, the two skills and CODEOWNERS with `* @<login>` active. No ruleset exists yet, so the push to `main` goes through.

Record: every version, the owner's GitHub plan, and the fast check's exit code.

#### Step 3: create the Apps

Run outside the trial: on 2026-10-19 the owner ran `rapid-ship app`, which created the Worker App, ID 5376519 (`proxy-hatch-rs-worker`), and the Reviewer App, ID 5376520 (`proxy-hatch-rs-reviewer`). `699fe95` records the four `[github]` lines. Not kept: the exit code, the install URLs, whether GitHub accepted the manifest without `hook_attributes`, whether each App's settings page shows no webhook, whether `security` showed a dialog while storing each key, and the two "stored" lines.

Pending owner step on `rs-trial`. The owner completes both browser pages that `rapid-ship app` opens.

```sh
uvx --from "$PLAN4" rapid-ship app; echo "exit $?"
security find-generic-password -s rapid-ship/worker-app >/dev/null && echo "worker item stored"
security find-generic-password -s rapid-ship/reviewer-app >/dev/null && echo "reviewer item stored"
```

Must observe: exit 0. If GitHub rejects the manifest, stop and record the error; the fix is a change to `app_manifest` with a test, in this plan's PR.

Record: the printed lines (IDs, slugs, `[github]` lines and install URLs), the exit code, whether GitHub accepted the manifest without `hook_attributes`, whether the App's settings page shows no webhook, whether `security` showed a dialog while storing each key, and both "stored" lines.

#### Step 4: install the Apps and record them

Run outside the trial: the owner installed both Apps on `proxy-hatch/rapid-ship`, not on `rs-trial`. `699fe95` (2026-10-19) sets this repository's `[github]` values to `worker_app_id = 5376519`, `worker_app_slug = "proxy-hatch-rs-worker"`, `reviewer_app_id = 5376520` and `reviewer_app_slug = "proxy-hatch-rs-reviewer"`. The step's push to `rs-trial` did not run. The installation date was not recorded.

Pending owner step on `rs-trial`. The owner opens both printed install URLs and installs each App on `rs-trial` only. In `.rapid-ship/project.toml` they set `worker_app_id`, `worker_app_slug`, `reviewer_app_id` and `reviewer_app_slug` under `[github]` to the four printed lines, then run:

```sh
WORKER_ID=$(python3 -c 'import tomllib; print(tomllib.load(open(".rapid-ship/project.toml", "rb"))["github"]["worker_app_id"])')
REVIEWER_ID=$(python3 -c 'import tomllib; print(tomllib.load(open(".rapid-ship/project.toml", "rb"))["github"]["reviewer_app_id"])')
git commit -am "Record the Worker and Reviewer Apps" && git push origin main
```

The plan names no expected output for this step. The commands must set `WORKER_ID` and `REVIEWER_ID` from `project.toml`, and the commit and push of the four lines must succeed.

Record: the four recorded values and the push's result.

#### Step 5: doctor reads both Apps

Run outside the trial: before `699fe95` (2026-10-19), `./devctl doctor` ran in this repository; who ran it is not recorded. That commit's message says that doctor reports all four `agent identity` items ok: the Worker App installation, the Reviewer App installation, the Worker App key and the Reviewer App key. The doctor output and its exit code were not kept, so the state of doctor's other items is unknown. An ok installation item would mean that the installation object carries `app_slug`, because that item compares it with the recorded slug (`_installation_item` in `doctor_github.py`); this is an inference, not an observation. Nothing records a run of the `installation` command that prints the installation object's keys, or of the `security ... -w` read, so whether a macOS dialog appears is unknown.

Pending owner step on `rs-trial`.

```sh
./devctl doctor; echo "exit $?"
uv run --project tools/devctl --frozen python -c 'import sys; from devctl.github.app import installation; print(sorted(installation("worker", sys.argv[1], int(sys.argv[2]))))' "$OWNER/rs-trial" "$WORKER_ID"
security find-generic-password -s rapid-ship/worker-app -w >/dev/null; echo "read exit $?"
```

Must observe: the four `agent identity` items are ok; the installation's keys include `app_slug` (Checked facts); the key read exits 0 with no dialog, which confirms that any process the owner runs can read the keys (Spec 1 section 6). The ruleset, delete-branch and fork-approval items are missing until Steps 7 and 8.

Record: every doctor line and the exit code, the installation's keys, and whether a macOS dialog appeared. Record that any process can read the keys under the report's limits.

#### Step 6: a second, private repository on the owner's plan

Pending owner step. First:

```sh
cd "$TRIALS"
gh repo create "$OWNER/rs-trial-private" --private --add-readme --clone
cd rs-trial-private
uvx --from "$PLAN4" rapid-ship app --repository "$OWNER/rs-trial-private"; echo "exit $?"
uvx --from "$PLAN4" rapid-ship init --stack agnostic --owner "$OWNER" --repository "$OWNER/rs-trial-private"
git switch main && git merge --ff-only rapid-ship/init && git push origin main
./devctl doctor; echo "exit $?"
cd "$TRIALS/rs-trial"
```

Must observe: `rapid-ship app` opens no browser and prints both Apps' lines and install URLs for this repository. The owner then installs both Apps there with the printed URLs and proves a token mints without printing it:

```sh
uv run --project tools/devctl --frozen python -c 'import sys; from devctl.github.app import installation_token as t; t("worker", sys.argv[1], int(sys.argv[2])); print("minted")' "$OWNER/rs-trial-private" "$WORKER_ID"
```

Must observe, on a GitHub Free account: `missing  github  ruleset: rulesets need a public repository or a paid GitHub plan (GitHub returned 403)`. On a paid plan, record the plan and what doctor reports instead.

Record: whether the install URL added the repository to the existing installation, the `minted` line, and doctor's `ruleset` line.

#### Step 7: apply the repository settings to `rs-trial`

Pending owner step.

```sh
gh api --method PATCH "repos/$OWNER/rs-trial" -F delete_branch_on_merge=true
gh api --method PUT "repos/$OWNER/rs-trial/actions/permissions/fork-pr-contributor-approval" -f approval_policy=all_external_contributors
```

The plan names no expected output for this step beyond success; Step 9's doctor expects the `delete branch on merge` and `fork PR workflow approval` items ok.

Record: each call's exit code and output.

#### Step 8: apply the ruleset

Pending owner step. The commands write the ruleset the index specifies, the one plan 6 ships as `rs-setup/ruleset.json`, outside the repository and apply it:

```sh
cat > "$TRIALS/ruleset.json" <<'EOF'
{
  "name": "rapid-ship",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [{"context": "devctl check", "integration_id": 15368}]
      }
    }
  ]
}
EOF
RULESET_ID=$(gh api --method POST "repos/$OWNER/rs-trial/rulesets" --input "$TRIALS/ruleset.json" --jq .id)
echo "$RULESET_ID"
```

The plan names no expected output for this step beyond the ruleset's ID, which Steps 9 and 11a read back.

Record: `$RULESET_ID` and the exit code.

#### Step 9: read the ruleset back and keep it as the fixture

Pending owner step.

```sh
./devctl doctor; echo "exit $?"
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq 'del(.node_id, ._links, .created_at, .updated_at, .current_user_can_bypass) | .id = 9 | .source = "o/r"' > "$PLAN4/tests/devctl/fixtures/github/ruleset.json"
(cd "$PLAN4" && uv run pytest tests/devctl/test_devctl_doctor_github.py tests/devctl/test_devctl_doctor_github_limits.py -q)
```

Must observe: the `ruleset`, `CODEOWNERS`, `delete branch on merge` and `fork PR workflow approval` items are ok, and every test passes with the read-back as the fixture. If a test fails, the read-back differs from what doctor expects: record the difference, then fix doctor or `ruleset.json` with a test in this plan's PR.

Record: every doctor line, whether the GitHub UI names `actor_id` 5 as the admin role, and the test result.

#### Step 10: Walk with Agent identity

Pending owner step.

```sh
git switch -c trial-walk
printf '\nA trial line.\n' >> README.md
git commit -am "Trial change"
./devctl as worker push; echo "push exit $?"
printf '## Evidence\n\n- `./devctl check --tier fast`: exit 0\n\nNot covered: everything; this pull request is a trial.\n' > "$TRIALS/pr-body.md"
./devctl as worker gh pr create --base main --head trial-walk --title "Trial change" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR=$(gh pr view trial-walk --json number --jq .number)
gh pr view "$PR" --json author --jq .author.login
./devctl as reviewer gh pr review "$PR" --approve --body "Trial approval by the Reviewer App"; echo "review exit $?"
gh pr view "$PR" --json reviews,reviewDecision,mergeStateStatus
./devctl as worker gh pr merge "$PR" --squash --admin; echo "admin exit $?"
./devctl as worker gh pr merge "$PR" --squash; echo "merge exit $?"
```

Must observe: the push and the pull request succeed, and the author is the Worker App (`<worker slug>[bot]`); the review is the Reviewer App's, yet `reviewDecision` stays `REVIEW_REQUIRED`, because CODEOWNERS `*` needs the owner; `--admin` is refused by devctl with exit 1 before anything runs; the plain merge is refused by GitHub, and devctl returns gh's nonzero exit code.

Then, in the browser, the owner adds one review comment on the pull request's diff, which opens a thread, and approves the pull request. Run:

```sh
gh pr checks "$PR" --watch
./devctl as worker gh pr merge "$PR" --squash; echo "merge exit $?"
```

Must observe: refused, because a review thread is unresolved. The owner then resolves the thread in the browser and runs:

```sh
./devctl as worker gh pr merge "$PR" --squash; echo "merge exit $?"
gh pr view "$PR" --json state,mergedBy
```

Must observe: merged by the Worker App, and the head branch deleted.

Record: each step's exit code, output and result.

#### Step 11: Flight with Agent identity, and whether GitHub counts the Reviewer App's approval

Pending owner step. The owner moves `rs-trial` to Flight through their own pull request: CODEOWNERS loses its `*` line and owns only the Protected set, and `[escalation]` sets `every_pr = false`.

```sh
git switch main && git pull --ff-only
git switch -c trial-flight
perl -ni -e 'next if /^\* @/; s{^# (/\S+ @\S+)$}{$1}; print' .github/CODEOWNERS
perl -pi -e 's/^every_pr = true/every_pr = false/' .rapid-ship/project.toml
grep -v '^#' .github/CODEOWNERS | grep -c '^/'
git commit -am "Move rs-trial to Flight"
git push -u origin trial-flight
gh pr create --base main --head trial-flight --title "Move rs-trial to Flight" --body-file "$TRIALS/pr-body.md"
gh pr merge trial-flight --squash --admin --delete-branch
git switch main && git pull --ff-only
./devctl doctor; echo "exit $?"
git switch -c trial-agent
printf '\nA Flight trial line.\n' >> README.md
git commit -am "Flight trial change"
./devctl as worker push; echo "push exit $?"
./devctl as worker gh pr create --base main --head trial-agent --title "Flight trial change" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR2=$(gh pr view trial-agent --json number --jq .number)
./devctl as reviewer gh pr review "$PR2" --approve --body "Trial approval by the Reviewer App"; echo "review exit $?"
gh pr view "$PR2" --json reviewDecision,mergeStateStatus,statusCheckRollup
./devctl as worker gh pr merge "$PR2" --squash; echo "pending merge exit $?"
gh pr checks "$PR2" --watch
gh pr view "$PR2" --json reviewDecision,mergeStateStatus
./devctl as worker gh pr merge "$PR2" --squash; echo "merge exit $?"
```

Must observe: the `grep -c` prints 13, the agnostic stack's Protected set; doctor's `ruleset` and `CODEOWNERS` items are ok for `every_pr = false` with Agent identity on. README.md is outside the Protected set, so the pull request has no code owner, and the Reviewer App's approval is the only review it can get. The first merge attempt runs while the `devctl check` run is still queued or in progress, which `statusCheckRollup` shows; gh refuses it, exit nonzero. When `reviewDecision` is `APPROVED`, the pending required check is the only gate left, so this refusal is GitHub enforcing `devctl check` (Spec 1 section 10). If the run had already finished, the attempt shows nothing about the check.

The answer this step exists for: whether the last merge, after the check passed, succeeded with only the Reviewer App's approval. If it did, GitHub counts that approval, the approval count stays 1, and Step 11a is skipped. If GitHub refused the merge for want of an approval (`reviewDecision` stays `REVIEW_REQUIRED`), it does not count it: Step 11a runs, and Step 17 applies.

Record: every result, gh's message and the state just before the first merge attempt. If the run had finished, record that, and the PR body names the gap under `Not covered:`.

#### Step 11a: only when GitHub did not count the approval: set the trial ruleset's count to 0 and read it back

Pending owner step. Runs only if Step 11 found that GitHub did not count the Reviewer App's approval.

```sh
perl -pi -e 's/"required_approving_review_count": 1/"required_approving_review_count": 0/' "$TRIALS/ruleset.json"
gh api --method PUT "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --input "$TRIALS/ruleset.json"
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq '.rules[] | select(.type == "pull_request") | .parameters.required_approving_review_count'
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq 'del(.node_id, ._links, .created_at, .updated_at, .current_user_can_bypass) | .id = 9 | .source = "o/r"' > "$PLAN4/tests/devctl/fixtures/github/ruleset.json"
./devctl as worker gh pr merge "$PR2" --squash; echo "merge exit $?"
```

Must observe: the first read-back prints `0`, and `tests/devctl/fixtures/github/ruleset.json` in this plan's worktree now holds the count of 0; doctor still requires an approval, so Task 5's tests fail on that fixture until Step 17 changes doctor. `$PR2`, approved by the Reviewer App and with its check passed, now merges. If it is still refused, record GitHub's state and stop the trial here: a count of 0 is not enough for Flight with Agent identity, and the owner decides the ruleset before Step 17 runs. Otherwise the owner runs:

```sh
git switch main && git pull --ff-only
git switch -c trial-agent-zero
printf '\nA Flight trial line under an approval count of 0.\n' >> README.md
git commit -am "Flight trial change under an approval count of 0"
./devctl as worker push; echo "push exit $?"
./devctl as worker gh pr create --base main --head trial-agent-zero --title "Flight trial change under an approval count of 0" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR4=$(gh pr view trial-agent-zero --json number --jq .number)
./devctl as reviewer gh pr review "$PR4" --approve --body "Trial approval by the Reviewer App"; echo "review exit $?"
gh pr view "$PR4" --json reviewDecision,mergeStateStatus,statusCheckRollup
./devctl as worker gh pr merge "$PR4" --squash; echo "pending merge exit $?"
gh pr checks "$PR4" --watch
./devctl as worker gh pr merge "$PR4" --squash; echo "merge exit $?"
```

Must observe: on `$PR4`, the merge attempt while its run is queued or in progress is refused, and the merge after the check passed succeeds. `$PR4` then differs from `$PR2`'s successful merge only by the pending check, so this pair shows GitHub enforcing `devctl check`. If the run had already finished at the first attempt, record that, as in Step 11.

Record: every result.

#### Step 12: a Reviewer App change request, and a workflow change

Pending owner step.

```sh
git switch main && git pull --ff-only
git switch -c trial-agent-2
printf '\nAnother Flight trial line.\n' >> README.md
git commit -am "Second Flight trial change"
./devctl as worker push; echo "push exit $?"
./devctl as worker gh pr create --base main --head trial-agent-2 --title "Second Flight trial change" --body-file "$TRIALS/pr-body.md"; echo "create exit $?"
PR3=$(gh pr view trial-agent-2 --json number --jq .number)
./devctl as reviewer gh pr review "$PR3" --request-changes --body "Trial change request by the Reviewer App"; echo "review exit $?"
gh pr checks "$PR3" --watch
gh pr view "$PR3" --json reviewDecision,mergeStateStatus
```

Must observe: `reviewDecision` is `CHANGES_REQUESTED`, and, with the count at 1, the merge is blocked, read after the check passed. After Step 11a the count is 0: record whether the change request alone still blocks the merge. Record what GitHub reports: it tells Spec 3 whether the Reviewer App's change requests count as Revisions.

Next, the owner changes `.github/workflows/devctl-check.yml` on `main` through their own pull request, merged with the admin bypass, and the agent branch takes that change in:

```sh
git switch main
git switch -c trial-workflow
printf '# A trial comment.\n' >> .github/workflows/devctl-check.yml
git commit -am "Trial workflow comment"
git push -u origin trial-workflow
gh pr create --base main --head trial-workflow --title "Trial workflow comment" --body-file "$TRIALS/pr-body.md"
gh pr merge trial-workflow --squash --admin --delete-branch
git switch trial-agent-2
git fetch origin main && git merge --no-edit origin/main
./devctl as worker push; echo "push exit $?"
```

Must observe: GitHub refuses the Worker App's push, because the merge brings in a workflow change (Checked facts), and devctl returns git's nonzero exit code with its `devctl: neither App may push a change under .github/workflows/; ...` hint. If GitHub accepts the push, record that; the hint still serves a direct workflow edit.

Record: GitHub's message, devctl's hint line and the exit code.

#### Step 13: `doctor --skills` live

Pending owner step. The follow-ups removed this step's run with a `[roster]` table, and its sign-in items, after the owner descoped several Providers, and follow-up 9 narrowed it to Claude Code. The owner runs the probe.

```sh
./devctl doctor --skills; echo "exit $?"
git worktree list
```

Must observe: one `skills (claude)` item when `claude` is on `PATH`, ok with `1 repository skills seen` and `not checked, user-invoked: trial-release`, never listing `trial-release` as outside the repository; outside skills are listed for information. `git worktree list` shows only the clone.

Record: every skills line and the exit code, whether Claude Code listed `trial-release` anyway, and `PROBE_MODEL` confirmed or corrected. A wrong model is fixed in `harness.py`, with its test, in this plan's PR.

#### Step 14: clean up

Pending owner step. Command: none. The owner closes any open trial pull request and decides whether to delete `rs-trial` and `rs-trial-private`; the Apps stay, as the owner's real Apps.

Must observe: no trial pull request stays open.

#### Step 15: write the report (implementer, from the owner's record)

Pending owner step: an implementer step that waits for the owner's record of Steps 2 to 14. Command: none.

Must observe: `docs/trials/<trial date>-agent-identity.md` holds a summary, the versions, one section per step with its commands, exit codes, output and result, and the deviations from Checked facts, with each result marked live or offline and no token, private key, client secret or email address. Its limits section names at least: any process the owner runs can read both keys (Step 5); the Reviewer App's approval does or does not count (Step 11); whether GitHub refused a merge while `devctl check` was pending (Step 11 or 11a), or that the run had finished before the attempt; and whether a merge that brings in a workflow change is refused (Step 12). `docs/trials/AGENTS.md` links the report with one line naming what it records.

#### Step 16: commit the report, and the fixture when the count stays 1 (implementer)

Pending owner step: an implementer step that waits for Step 15. From this plan's worktree, when Step 11a did not run:

```sh
./devctl check --tier fast
git add docs/trials tests/devctl/fixtures/github/ruleset.json
git commit -m "docs: record the Agent identity, ruleset and doctor trial" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

When Step 11a ran, the fixture holds a count of 0 that doctor does not yet accept, so the commit leaves it out and adds `docs/trials` only; Step 17 commits the fixture with the change that accepts it. The implementer who runs the commit writes the trailer of its own model in place of the plan's.

Must observe: the fast check exits 0, and the commit holds the report and the guide line (and the fixture when the count stays 1).

#### Step 17: settle the approval count in the index and Spec 1 (implementer)

Pending owner step: an implementer step that waits for Step 11's answer. If GitHub counts the Reviewer App's approval, no code changes; the index and Spec 1 section 8, step 7.3 take the replacement text in Task 10 Step 17. If it does not, the count becomes 0. The commands for that case, in the order Task 10 Step 17 gives them: the first checks the fixture. Before the second, the implementer appends the new test and changes the assertion, as Task 10 Step 17 says; the second must then fail.

```sh
grep -n '"required_approving_review_count"' tests/devctl/fixtures/github/ruleset.json
uv run pytest tests/devctl/test_devctl_doctor_github.py -q
uv run ruff format rapid_ship/templates/common/tools/devctl/devctl/doctor_rules.py
uv run ruff check rapid_ship/templates/common/tools/devctl/devctl/doctor_rules.py
uv run rapid-ship sync --in-place
uv run pytest tests/devctl -q
```

Between the second and third command the implementer deletes `_approves` and, in `_pull_request_problems`, the line that calls it with `NO_APPROVAL`, as Task 10 Step 17 says. Then, either way (the implementer writes the trailer of its own model in place of the plan's):

```sh
./devctl check --tier fast
npm --prefix website run build
git add -A docs tests rapid_ship/templates tools/devctl .rapid-ship/kit.lock
git commit -m "docs: settle the ruleset's approval count from plan 4's trial" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Must observe: with a count of 0, the grep shows `0` in the fixture, and the second command fails for the new test, for `test_only_flight_without_agent_identity_accepts_no_review_requirement` with `assert NO_APPROVAL not in problems`, and for every test that checks the fixture as the whole ruleset, such as `test_the_rs_setup_ruleset_passes`; after the deletion `uv run pytest tests/devctl -q` passes with the fixture's count of 0. Either way the open item that starts `- **The ruleset's approval count with Agent identity in Flight:**` leaves Spec 1 section 11, the matching line joins the "Answered" list, the fast check and the docs site build pass, and the commit holds the docs, tests, templates, `tools/devctl` and `.rapid-ship/kit.lock`.

### Task 11: pending Owner steps

Steps 1, 2 and 5 of Task 11 ran: Step 1's commands and Step 2's body check are recorded above, and this record is Step 5. Steps 3 and 4 are Owner steps. No agent pushed, opened a pull request or edited one. Neither step is a pass or a skip until the owner's output replaces its entry. The PR body is a file outside Git, `/Users/shawn/workspace/rapid-ship/.worktrees/doctor-agent-identity/.superpowers/sdd/2026-10-16-doctor-and-agent-identity/task-11-pr-body.md`.

#### Step 3: push and open the PR

Pending owner step. The record's commit is already on the branch, so this push carries it. If the owner pushed earlier, `git push` sends it and the PR's checks run again on the new head. The owner runs this from this plan's worktree in their own terminal:

```sh
if [ "$(gh pr view 30 --json state --jq .state)" = MERGED ]; then BASE=main; else BASE=codex/devctl-check; fi
BODY=/Users/shawn/workspace/rapid-ship/.worktrees/doctor-agent-identity/.superpowers/sdd/2026-10-16-doctor-and-agent-identity/task-11-pr-body.md
git push -u origin doctor-agent-identity
gh pr create --base "$BASE" --head doctor-agent-identity --title "feat: add devctl doctor and optional Agent identity (plan 4)" --body-file "$BODY"
gh pr checks --watch
```

Must observe: the `devctl check` job passes. Record the PR URL and the run URL from this output in the field "PR URL, base, and the `devctl check` run" above.

#### Step 4: mark plan 4 built in the index

Pending owner step, which needs the PR's number from Step 3. Task 11's own command expects the index row to read `Proposed` and to link `#plan-4-doctor-and-agent-identity`. At this head the row already links this plan and reads "In progress: branch `doctor-agent-identity`", so that command would match nothing (controller ruling P4). This command matches the row as it is. A dry run on a copy of the index changed only plan 4's row.

```sh
N=$(gh pr view --json number --jq .number)
perl -pi -e "s{\| 3, 4, 6, 10 \| 3 \| In progress: branch \`doctor-agent-identity\` \|}{| 3, 4, 6, 10 | 3 | Built: PR #$N, \`doctor-agent-identity\` |}" docs/superpowers/plans/2026-10-14-kit-and-setup.md
grep -n "^| 4 |" docs/superpowers/plans/2026-10-14-kit-and-setup.md
```

Must observe: plan 4's row links this plan and reads `Built: PR #<the PR's number>, `doctor-agent-identity``. Then the implementer commits the row on its own, because the record's commit is already made, and the owner pushes it:

```sh
./devctl check --tier fast
git add docs/superpowers/plans/2026-10-14-kit-and-setup.md
git commit -m "docs: mark plan 4 built in the plan index" -m "Co-Authored-By: <the model that writes the commit>"
git push
```

#### Before merge: record the organisation-repository limit in Linear

Pending owner step. The final whole-branch review (R2) asks for a Linear task before merge, and no agent changes Linear (controller ruling 3). The owner creates it in this repository's Linear team, through Linear's official MCP or its web app, with this title and description:

```text
Title: doctor: the CODEOWNERS item cannot pass on an organisation-owned repository

doctor takes the code owner from the repository's owner: tools/devctl/devctl/doctor_github.py:134 sets owner = repository.split("/", 1)[0], and codeowners_problems in doctor_rules.py then requires `* @<owner>` in Walk, and owner lines on the Protected set in Flight. On an organisation-owned repository that asks for `* @<organisation>`. An organisation login is neither a user nor a team, so it is not a valid code owner, and the owner's correct `* @<login>` is reported wrong. doctor therefore never exits 0 for such a repository.

`rapid-ship app` already refuses organisation repositories (rapid_ship/github_app.py:413-417), but nothing scopes Walk or doctor to personal accounts, and Spec 1 is silent.

Decide in Spec 1: record the owner's login, which `rapid-ship init --owner LOGIN` already takes but .rapid-ship/project.toml does not keep, or scope Spec 1 to personal repositories. Then fix doctor before plan 6's rs-setup runs it for owners.

Found by plan 4's final whole-branch review (R2). Recorded as a limit in the plan 4 PR body and in the plan's Verification record.
```

Must observe: the task exists in Linear. Record its ID beside the organisation-repository limit in "Remaining limits" above and in the PR body.
