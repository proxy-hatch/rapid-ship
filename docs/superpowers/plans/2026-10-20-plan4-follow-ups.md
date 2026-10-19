# Plan 4 follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change plan 4's built code to the owner's decisions of 2026-10-19 before PRs #31 to #33 merge: organisation-owned repositories, Keychain items named by App ID, `rapid-ship app --import-key`, and `[github] code_owner`.

**Architecture:** Each change lands on the PR that holds its file and is merged up the stack with `git merge --no-ff`: #31 (`plan4-settings-tokens`) owns the settings and devctl's token code, #32 (`plan4-doctor`) owns doctor, #33 (`doctor-agent-identity`) owns `rapid-ship app`. devctl is edited only under `rapid_ship/templates/common/tools/devctl/devctl/`, then `uv run rapid-ship sync --in-place` regenerates the vendored copy and the lock.

**Tech Stack:** Python 3.12, PyJWT with cryptography, macOS `security`, GitHub REST through `gh` (owner reads) and App JWTs.

**Spec:** [Spec 1](../specs/2026-10-14-kit-and-setup-design.md), sections 3 (`rapid-ship app`), 4 (settings files), 6 (doctor, Agent identity) and 11 (answered on 2026-10-19). The [plan index](2026-10-14-kit-and-setup.md) lists these follow-ups under "Plan 4 follow-ups, before #31 to #33 merge".

## Global Constraints

- No private key or token is written to disk, put on a command line or printed. A key reaches `security` only on stdin.
- Keychain item name: `rapid-ship/<role>-app/<App ID>`, such as `rapid-ship/worker-app/5376519`; the item's account holds the App ID and its comment the slug. The old name is `rapid-ship/<role>-app`.
- An existing Keychain item is left in place: rapid-ship never replaces or deletes one.
- `code_owner` is written as CODEOWNERS writes it: `"@<login>"` or `"@<organisation>/<team>"`. devctl rejects any other value, naming the file, the key and what it accepts.
- The organisation manifest flow posts to `https://github.com/organizations/<organisation>/settings/apps/new`.
- Each source file stays under the `filesize` step's limit; `rapid_ship/github_app.py` has 499 lines today, so Task 4 splits it.
- Tests are offline: fake `security`, fake GitHub. No test touches the real Keychain or network.

## Review Focus

1. The owner's two existing items, `rapid-ship/worker-app` and `rapid-ship/reviewer-app`: after this plan, `rapid-ship app` must re-store each under its new name from the item's account, and leave the old item in place.
2. A second repository of the same owner, with no `[github]` IDs yet: `rapid-ship app` must reuse the owner's existing Apps found in the Keychain, not create a second pair.
3. An organisation developer whose repository records the Apps but whose machine has no key: `rapid-ship app` must not open the browser or create an App; it says to run `--import-key`.
4. `--import-key` with a key for a different App, or a public key, or an empty stdin: nothing is stored, exit 1, and the message names the problem without echoing input.
5. `init` without `--owner`: the seeded `code_owner` must be `""`, never a placeholder that devctl would reject on every later command.

---

## PR #31 (`plan4-settings-tokens`)

### Task 1: `[github] code_owner` and the stale settings text

**Files:**
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/settings.py`
- Modify: `rapid_ship/templates/python/.rapid-ship/project.toml`, `rapid_ship/templates/agnostic/.rapid-ship/project.toml`, `rapid_ship/kit/init.py` (seed value), `.rapid-ship/project.toml` (this repository: `code_owner = "@proxy-hatch"`, the owner of every line in `.github/CODEOWNERS`)
- Test: `tests/devctl/test_devctl_settings*.py`, `tests/test_kit_contents.py` or the init tests that check seeded values

**Interfaces:**
- Produces: `ProjectSettings.code_owner: str | None` (None when the key is `""` or absent), used by Task 3.

- [ ] Write failing tests: `"@octocat"`, `"@my-org/platform-team"` load; `"octocat"`, `"@"`, `"@org/"`, `"@-bad"`, `"@a/b/c"` and a number raise `SettingsError` naming `.rapid-ship/project.toml`, `code_owner` and `"@login" or "@organisation/team"`; `""` and an absent key give `None`. Init with `--owner octocat` seeds `code_owner = "@octocat"`; init without it seeds `code_owner = ""`, and the seeded file loads.
- [ ] Implement: add `code_owner` to `_GITHUB_KEYS`, validate it with `@[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)?`, and seed it in both templates under `repository` with Spec 1 section 4's comment: `# The code owner that CODEOWNERS names, written as CODEOWNERS writes it: "@login" or "@organisation/team".` Init fills it the way it fills CODEOWNERS's owner.
- [ ] Fix the text the owner's review made wrong: the `[dispatch]` entry of `REMOVED_TABLES` drops "the Lead brief's Focus caps parallel Workers" (rapid-ship takes no notice of how many Sessions run), and the `Harness` comment drops `# Proposal: Spec 1 section 11, Roster Harnesses` (any Harness is decided; plan 5 builds the Roster `command`).
- [ ] Update every document on this branch that lists the `[github]` keys, such as `ARCHITECTURE.md` and `tools/AGENTS.md`.
- [ ] `uv run rapid-ship sync --in-place`, `uv run pytest -q`, `./devctl check --tier fast`, `uv run rapid-ship status --strict`; commit `feat: record the code owner under [github]`.

### Task 2: devctl reads Keychain items named by App ID

**Files:**
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/github/app.py`
- Test: `tests/devctl/test_devctl_github_app.py`, `tests/devctl/test_devctl_github_app_limits.py`, `tests/devctl/github_fakes.py`

**Interfaces:**
- Produces: `keychain_service(role: Role, app_id: int) -> str` returning `f"rapid-ship/{role}-app/{app_id}"`; `keychain_private_key(role: Role, app_id: int, keychain: Keychain | None = None) -> bytes`. `KEYCHAIN_SERVICE` is removed. Task 4's parity test compares `keychain_service` with rapid-ship's.

- [ ] Write failing tests: the read asks `security` for `rapid-ship/worker-app/5376519` when `[github]` records 5376519; a missing item raises `KeychainMissing` whose message names that item and says: run `rapid-ship app`, which re-stores a key kept under `rapid-ship/worker-app`, or `rapid-ship app --import-key worker`.
- [ ] Implement, passing the App ID from `_app_client` and every other caller; `guarded_message` keeps its doctor hint.
- [ ] Sync, run the four checks above; commit `feat: name each App's Keychain item by its App ID`.

## PR #32 (`plan4-doctor`)

Merge `plan4-settings-tokens` first; fix doctor's callers of `keychain_private_key` in the merge commit if the build needs it.

### Task 3: doctor's CODEOWNERS item reads `[github] code_owner`

**Files:**
- Modify: `rapid_ship/templates/common/tools/devctl/devctl/doctor_github.py:121-137`, `doctor_rules.py` (`codeowners_problems`, `_walk_problems`, `_protected_set_problems`), `doctor_skills.py:168`
- Test: `tests/devctl/test_devctl_doctor*.py`

**Interfaces:**
- Consumes: `ProjectSettings.code_owner` (Task 1).
- Produces: `codeowners_problems(text: str, every_pr: bool, code_owner: str, stack: Stack) -> list[str]`, where `code_owner` includes the `@`.

- [ ] Write failing tests: with `code_owner = "@my-org/platform-team"`, Walk passes with `* @my-org/platform-team` and fails with `* @my-org`; matching ignores case; Flight checks every Protected path against the code owner; with `code_owner` unset the item is missing and its detail says `set [github] code_owner in .rapid-ship/project.toml`, without reading CODEOWNERS.
- [ ] Implement: doctor takes the code owner from the settings, never from the repository's owner.
- [ ] Drop `(Spec 1 section 6, a Proposal)` from `probed_harnesses`'s docstring: the owner accepted it.
- [ ] Sync, run the four checks; commit `feat: check CODEOWNERS against the recorded code owner`.

## PR #33 (`doctor-agent-identity`)

Merge `plan4-doctor` first. Task 4's parity test fails until Task 4 lands; that is expected inside this PR.

### Task 4: rapid-ship's Keychain names, finding existing Apps, and re-storing old items

**Files:**
- Split `rapid_ship/github_app.py` by responsibility, each part under the size limit: Keychain store and names (`rapid_ship/app_keychain.py`), the manifest flow (`rapid_ship/app_flow.py`), and the command (`rapid_ship/github_app.py`). Update `rapid_ship/AGENTS.md` and any import-linter contract.
- Test: `tests/test_kit_app.py`, `tests/test_kit_app_limits.py`, `tests/devctl/test_devctl_github_app.py` (parity)

**Interfaces:**
- Produces: `keychain_service(role: str, app_id: int) -> str`; `LEGACY_SERVICE = {"worker": "rapid-ship/worker-app", "reviewer": "rapid-ship/reviewer-app"}`; `KeychainStore` gains `read_key(service: str) -> bytes` and `listed(role: str) -> list[StoredApp]` (the role's items named `rapid-ship/<role>-app/<id>`, read from `security dump-keychain` without `-d`, attributes only); `recorded_apps(root: Path, repository: str) -> dict[str, StoredApp]`, the Apps `.rapid-ship/project.toml` records when its `repository` is the target.

`run_app` decides per role, in this order (ruling: Spec 1 section 3 says `app` creates only Apps that do not exist yet; with names that carry the ID, finding them needs the Keychain listing or the recorded IDs):
1. `[github]` records the role's App: use `rapid-ship/<role>-app/<id>` if present; else re-store the old item if its account is that ID; else exit 1 and say how to `--import-key`. Never create.
2. Nothing recorded: among `listed(role)` plus the old item, use the one whose App the repository's owner owns (`GET /apps/<slug>` with the owner's `gh`; a 404 skips the item); re-store it first if it is the old item.
3. Otherwise create the App (Task 5 for an organisation).

Re-storing reads the key with `security find-generic-password -s <old> -w`, adds it under the new name as `add` does, verifies it, and prints that the old item can be deleted with `security delete-generic-password -s rapid-ship/<role>-app` once `./devctl doctor` passes; rapid-ship deletes nothing.

- [ ] Write failing tests for each branch of the order above (fake store, fake `owner_get`, no browser opened where none should be), the dump parsing (a fixture with an unrelated item, a `rapid-ship/worker-app/12` item and an old item), and the parity test `github_app.keychain_service(r, 7) == devctl app.keychain_service(r, 7)` for both roles.
- [ ] Implement, split the module, run the four checks; commit `feat: find Apps by their Keychain items and re-store old item names`.

### Task 5: the organisation manifest flow

**Files:** `rapid_ship/github_app.py`, `rapid_ship/app_flow.py`; tests in `tests/test_kit_app*.py`.

- [ ] Write failing tests: an organisation-owned repository is no longer refused; when an App must be created, `GET /user/memberships/orgs/<org>` must show an active `admin`, otherwise exit 1 with "an organisation admin creates its Apps once; ask one to run rapid-ship app, or, if the Apps exist, record their IDs and run rapid-ship app --import-key <role>", and no browser opens; an admin's start page posts to `https://github.com/organizations/<org>/settings/apps/new?state=...`; the App settings and orphaned-App URLs use `https://github.com/organizations/<org>/settings/apps/<slug>`. A personal repository keeps today's checks and URLs.
- [ ] Implement with a target that knows its kind (user or organisation); run the four checks; commit `feat: create an organisation's Apps through its manifest flow`.

### Task 6: `rapid-ship app --import-key {worker,reviewer}`

**Files:** `rapid_ship/cli.py`, `rapid_ship/github_app.py` (or `rapid_ship/app_import.py`), `pyproject.toml` and `uv.lock` (add `pyjwt[crypto]>=2.10,<3` to `[project] dependencies`, the range devctl uses: ruling, because Spec 1 section 3 requires the check that the key signs a token GitHub accepts); tests in `tests/test_kit_app*.py`.

- [ ] Write failing tests: with `[github]` recording the role's App, a valid key on stdin is checked with `GET /app` under an App JWT (its `id` and `slug` must equal the recorded ones), then stored under `rapid-ship/<role>-app/<id>`; output says to delete the downloaded key file. Exit 1 and nothing stored when: `[github]` records no App for the role; stdin is empty or over 64 KiB; the key is not an unencrypted RSA PEM private key; GitHub answers 401 or another App's ID; the item already exists (left in place). No test output or fake `security` argv contains the PEM.
- [ ] Implement; the distribution smoke must still pass with the new dependency; run the four checks and `./devctl check --tier full --base plan4-doctor` with a PR body; commit `feat: import a developer's App key with rapid-ship app --import-key`.

### Task 7: documents

- [ ] Spec 1 sections 3 and 6 state the built behaviour, without "plan 4 as built ... its follow-ups"; the plan index marks follow-ups 1 to 4 built in #31 to #33; `README.md`, `ARCHITECTURE.md` and `rapid_ship/AGENTS.md` describe organisation repositories, the item names and `--import-key`; this plan's status line says built. Commit `docs: record plan 4's follow-ups as built`.

## Owner steps after the merge-up

- Run `uv run rapid-ship app` once in #33's worktree: it re-stores the two keys under `rapid-ship/worker-app/5376519` and `rapid-ship/reviewer-app/5376520`, then `./devctl doctor` passes the key items. Until then `./devctl as` reports the item missing.
- The organisation trial (plan index, follow-up 5).
