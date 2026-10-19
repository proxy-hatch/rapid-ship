# Spec 1: Kit and Setup

**Status:** revised on 2026-10-16 for the team-management boundary ([ADR 0004](../../adr/0004-team-management-boundary.md)), and on 2026-10-19 for the owner's second review of the design PR. Plans 1 to 3 are built. Plan 4 is built in PRs #31 to #33, which are not merged yet, and its follow-ups for organisation-owned repositories land on them first. Plans 5 to 7 are planned in the [plan index](../plans/2026-10-14-kit-and-setup.md). This is the first of the three specs in the [rapid-ship design](2026-10-14-rapid-ship-design.md), and its terms follow `GLOSSARY.md` at the repository root. [Section 11](#11-questions) lists what is still open.

## 1. Scope and outcome

When this spec is built, an owner has the agent in their Harness Session run `uvx rapid-ship init` in a new or existing repository, then runs the `rs-setup` skill in that Session, and ends with:

- the Kit vendored and recorded in its lock, with one or more stacks, each in its own directory: Python, TypeScript for React, or the stack-agnostic one;
- `devctl check` in the pre-commit hook and in CI as a required status check, and run by each Worker before it reports its task done;
- the Kit's Harness guardrails, with the merge guard, for Claude Code, Codex and agy;
- README.md, ARCHITECTURE.md, the AGENTS.md tree, the feature map and the starter Patterns, each verified by `devctl check`;
- the ruleset and CODEOWNERS applied for Walk, and `devctl doctor` reporting no gap that the owner has not accepted;
- optionally, Agent identity: two GitHub Apps that agents act as through `devctl as`;
- Suggested thresholds recorded and, optionally, the scheduled metrics Action installed, both as [Spec 3](2026-10-16-metrics-and-gardening-design.md) defines them;
- for an existing repository, a separate PR that offers the tool-settings rules the project lacks, and a standards milestone from `rs-health` in the owner's tracker.

This spec covers the `rapid-ship` command (section 3), the Kit's files (section 4), `devctl check` (section 5), devctl's other commands (section 6), the skills the Kit ships (section 7), and the skills `rs-setup` (section 8) and `rs-health` (section 9).

Out of scope:

- [Spec 2: Delivery skills](2026-10-16-delivery-skills-design.md): `rs-design`, `rs-breakdown`, `rs-lead`, `rs-work`, `rs-review` and the tracker mapping notes. Section 4 stores the escalation list and the Roster; Spec 2 says how `rs-lead` builds a Lead brief from them.
- [Spec 3: Metrics and gardening](2026-10-16-metrics-and-gardening-design.md): `devctl metrics`, the scheduled metrics Action, Suggested thresholds and where they are recorded, project-defined metrics, the Corrections ledger, `rs-garden`, and `rs-preflight`, the advisory Pre-flight review before the owner widens the Mode toward Flight. `rs-garden` reruns the audit that section 9 defines.
- Anything that starts an agent Session to do work, watches or resumes one, or pushes, reviews or merges as a step in a flow ([ADR 0004](../../adr/0004-team-management-boundary.md)).

rapid-ship works with GitHub today, through `gh` and GitHub's rulesets. Other Git hosts, such as Bitbucket, may follow if owners ask for them or contribute them. rapid-ship works with any issue tracker that the owner's Harness can reach through an MCP server or a CLI, and devctl never talks to the tracker. The owner's machine must run macOS for now: Agent identity keeps its App keys in the macOS Keychain, and on Windows git can check the skill links out as plain files. `devctl check` also runs on Linux, as CI does.

### Dog-fooding

*This paragraph describes this repository's own configuration, not product behaviour.* rapid-ship vendors its own Kit (section 3) and is validated on itself and on its sample project, hello-rapid-ship. Its tracker is Linear. Its agents sign in with vendor subscriptions only, and the owner accepts the risk of running agy inside another Session, including `devctl doctor`'s agy probe ([ADR 0001](../../adr/0001-subscription-logins-only.md)). agy is never a Reviewer here. This repository records these choices as rules in its root AGENTS.md; no Kit file enforces them. It is also a public repository on GitHub Free with one owner, the setup where Agent identity matters most, so PR #33 turns Agent identity on. The owner created its Worker and Reviewer Apps with `rapid-ship app` on 2026-10-19 and installed both on this repository, and #33 records them in `[github]` ([plan 4](../plans/2026-10-14-kit-and-setup.md#plan-4-doctor-and-agent-identity), follow-up 6). Their keys stay under plan 4's old Keychain names until `rapid-ship app` re-stores them under the new ones (section 3).

## 2. Removing the old controller

Built in plan 1. The last commit that contains the controller is tagged `archive/controller-2026-10` (`f7b877b`).

1. The controller code and its tests were deleted: `rapid_ship/execution/`, `rapid_ship/trust/` and `rapid_ship/project/`; the old `cli.py`, `models.py`, `storage.py`, `logs.py`, `protocol_json.py`, `metrics.py`, `github_metrics.py` and templates; the root controller `devctl` with its build and smoke scripts; the `tests/typecheck_*.py` fixtures; and `examples/`.
2. `rapid_ship/files.py` stayed. `rapid_ship/process.py` moved into devctl in plan 3. The console script is `rapid-ship`.
3. The `rapid-ship` and `rapid-ship-improve` skills were deleted. `rapid-ship-engineering` stays until plan 7's Kit skills replace it; the optional `rs-contribute` replaces `rapid-ship-improve`.
4. The controller-era records and guides left the current documentation. Only `docs/getting-started.md` remains, with a "Historical" line under its title. The tag keeps the deleted records and guides, as the [orchestrator note](../../archive/orchestrator/README.md) says.
5. `README.md`, `ARCHITECTURE.md`, the root `AGENTS.md` and `CLAUDE.md` were rewritten for the Kit.

Later plans reused these parts of the tagged commit:

| Source at the tag | Reused in |
| --- | --- |
| `rapid_ship/files.py`: `atomic_replace`. `rapid_ship/project/configuration.py`: `_safe_path` (lines 33-44), which refuses a path outside the project or through a symlink, and the create-only write in `_copy_skill` (lines 218-222), which never overwrites | The rapid-ship CLI (plan 2), which ported both into `files.py` as `safe_path` and `create_file` |
| `rapid_ship/process.py`, the bounded process runner | devctl (plan 3), with the caller's `PATH` and truncation reported in flags rather than in the output. Plan 4 added two more fixes from its old branch, `codex/github-commands` (`de800ae`, `98082fb`) |
| `scripts/check_repository.py` and `scripts/check.py` | devctl's `map` step and `devctl check` (plan 3), which deleted both scripts |
| `rapid_ship/trust/github.py` `inspect_protection` | Replaced by doctor's ruleset item (plan 4), which reads rulesets rather than branch protection |
| `tests/typecheck_*.py`, `assert_type` fixtures checked by mypy | The `type:` reference kind (section 5) |
| `docs/metrics.md`: definitions and the rule that a missing metric is unknown | Spec 3 |

`codex/github-commands` is not on GitHub, so its commits resolve only in the owner's clone. The [GitHub commands plan at `928fbe4`](https://github.com/proxy-hatch/rapid-ship/blob/928fbe493977ae41d2012e19baff3e861fd5b0e8/docs/superpowers/plans/2026-10-14-github-commands.md) describes its work.

## 3. The rapid-ship CLI

The rapid-ship CLI is a small Python package run with `uvx`; nothing is installed. It holds what runs once or rarely, so devctl keeps only the commands that people, agents and CI use repeatedly. In both CLIs each command is one word followed by arguments.

`uvx` fetches the package from a git tag of this repository: `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<version> rapid-ship <command>`. Each Kit release is a tag `v<version>` on `main`, created by the owner, and the Kit version is the package version. No release tag exists yet; until one does, run `uvx --from <local checkout> rapid-ship <command>`. Publishing to PyPI waits until the Kit settles. This spec writes `uvx rapid-ship` for short.

`rapid-ship` has four commands. `init`, `status` and `sync` are built (plan 2). `app` belongs to Agent identity and is built in plan 4. `rs-setup` marks an existing project's suppressions itself (section 8). Every command exits 0 on success, 1 when a check failed or the repository's state refused the request, and 2 when it could not run.

Both CLIs prefer guided rectifying to a bare exit. Each refusal and error names the problem, what it blocks and the next step, such as the command to run. A command still fails fast and gracefully: it stops at the first error and shows the underlying cause, such as git's own message, and never hides or rewords it.

### `rapid-ship init`

1. **Preconditions:** the current directory is inside a git work tree with a clean status, with no `.rapid-ship/kit.lock` and no branch `rapid-ship/init`. `init` installs at the top of the work tree, even when run from a subdirectory. A stack can live in a subdirectory (step 2).
2. **Stacks:** a stack is `python`, `typescript` or `agnostic`, and it lives in one directory of the repository. As built, a repository with `pyproject.toml` gets the `python` stack; otherwise `init` needs `--stack python` or `--stack agnostic`, and without either it exits 2. A repository has one stack, at its root. Plan 6 adds the TypeScript stack and several stacks: `--stack NAME[=DIRECTORY]`, repeatable, names each stack and its directory, which defaults to the root. `agnostic` cannot sit beside another stack.
   - **Detection (plan 6):** without `--stack`, `init` searches the repository recursively for stack roots, at any depth. It skips vendored and generated directories, such as `node_modules`, `.venv`, `dist` and `build`. A directory with `pyproject.toml` is a `python` root, and one with `package.json` and `tsconfig.json` is a `typescript` root.
   - **Never a silent guess:** `init` proposes what it found and writes nothing. It prints each root and the `--stack` options that name them, such as `--stack python=backend --stack typescript=frontend`, and exits 2. When it finds no root, it asks for `--stack`, which can name `agnostic`.
   - **Confirmation:** the agent that runs `init` in the owner's Session, before the owner runs `rs-setup` there, confirms the stack roots with the owner. When detection is unclear, it asks the owner for them. It then reruns `init` with them as `--stack NAME=DIRECTORY`. `rs-setup` does not exist until `init` writes it, so the proposal that `init` prints carries these instructions. An owner who runs `init` in a terminal follows the same proposal.
3. **Variables:** `--owner`, `--repository`, `--name` and `--package` fill the template variables. The project name defaults to the GitHub repository name, then to the main checkout's directory name. Without `--owner`, CODEOWNERS names `<owner>` with its line commented out, and `rs-setup` writes the code owner (section 8, step 7).
4. **Plan the writes.** Each Kit file is managed (`sync` updates it later) or seeded (written once, then owned by the project). Section 4 lists both kinds.
5. **Conflicts:** if any managed file already exists, `init` writes nothing, lists the conflicts and exits 1. If a seeded file exists, even as a symlink, `init` skips it and lists it for `rs-setup` to merge. For a tool settings file, `rs-setup` also offers the rules it lacks in a separate PR at the end of Setup (section 8, step 15).
6. **List existing checks:** before writing, `init` collects the tool settings, hooks and workflows already in the repository: Ruff, mypy, pytest, flake8, pylint, isort and Black settings, `.pre-commit-config.yaml`, Husky and lefthook files, a configured `core.hooksPath`, executable hooks in git's hooks directory, and workflows in `.github/workflows/`. It reads them without running project code or a hook, and lists an unreadable file as unreadable. Plan 6 adds ESLint, Prettier, Biome, `tsconfig.json`, Vitest and Jest settings.
7. **Write and commit:** it creates the branch `rapid-ship/init` at `HEAD`, writes with the safe-path helpers (never outside the repository, never through a symlink, never over an existing file), and commits exactly the created files and `.rapid-ship/kit.lock`. A repository with no commits gets the Kit as its first commit on the current branch. A failed switch, write or commit removes what `init` created and returns to the starting branch.
8. **Report:** it prints what it created and skipped, the existing checks, and the next step: open a PR from `rapid-ship/init`, which `rs-setup` does.

`init` never edits an existing file, never runs project code and never runs a git hook.

### `rapid-ship status`

Read-only. It compares the repository with the lock and the installed templates.

| Class | Meaning |
| --- | --- |
| unchanged | A managed file matches its locked hash |
| modified | A managed file differs from its locked hash |
| missing | A managed file is absent |
| template updated | A seeded file's template changed since it was seeded. The file itself is never compared |
| excluded | The project listed the path under `[kit] exclude` and owns it |
| outdated | A managed lock entry that the installed template no longer matches, or that the installed Kit dropped |
| not installed | A managed template of the installed Kit that the lock does not list yet, such as a file a newer Kit added |

Files not in the lock are the project's and are not reported. `--strict` exits 1 unless every managed file that is not excluded is unchanged and current. `--json` prints the report as data.

### `rapid-ship sync`

1. **Preconditions:** a clean work tree, unless `--in-place` is given. `sync` compares template hashes, not version numbers; when nothing changed it says so and stops.
2. Without `--in-place`, it creates the branch `rapid-ship/kit-sync-<version>` at `HEAD`. It refuses a detached `HEAD` and an existing branch of that name.
3. It replaces each unchanged managed file with its new template, adds new managed files, including the optional skills listed under `[kit] optional`, and deletes unchanged managed files that the Kit dropped. It never creates, replaces or deletes a path under `[kit] exclude`. A new managed template whose path already holds a different file that the lock does not list is a conflict: `sync` leaves the path alone, lists it and exits 1.
4. A managed file that the project edited to equal the new template stays managed; `sync` only updates the lock. Any other managed file that the project edited or deleted becomes the project's own: `sync` leaves it as it is, records it in the lock as seeded with the current template's hash, and prints how to give it back. `sync --revert <path>` writes the current template over it and records it as managed again.
5. It never changes an existing seeded or project-authored file. It creates a seeded file that a newer Kit adds only where nothing exists at its path, and records the template either way. It lists seeded files whose template changed.
6. It updates the lock. Without `--in-place`, it commits, pushes the branch and opens a PR with `gh` under the owner's sign-in, and the owner merges the PR. With `--in-place` it writes the work tree only. A failed write restores the work tree.

`sync` without `--in-place` is an owner command. Its push runs inside its own process, where the Harness guardrails cannot see it, so skills run `sync` only with `--in-place`.

**Migrations (plan 5).** A Kit version can change what a seeded file must contain, such as a settings table that devctl no longer accepts, or Protected paths that CODEOWNERS must list. The Kit then carries a migration: code in rapid-ship that detects the old content in one seeded file and writes the edit. `sync` never applies a migration silently. Without `--in-place`, when a migration applies, `sync` commits its edits on a second branch, `rapid-ship/kit-migrate-<version>`, based on the sync branch, and opens a second PR whose body explains each edit. The files are Protected, so the owner reviews and merges it. With `--in-place`, `sync` lists each migration that applies, with its edit, and writes none. Where a new rule can accept the old content for one Kit version at little cost, devctl warns for that version before it fails. The first migrations remove the tables that plan 4 dropped and add plan 5's CODEOWNERS lines.

### `rapid-ship app`

Part of Agent identity (section 6); built in plan 4 from its old branch, and extended for organisations by plan 4's follow-ups. Each repository owner, a personal account or an organisation, has two GitHub Apps. They belong to that account, not to one project: `app` creates each App that does not exist yet, then prints how to install both on the current repository. A private App installs only on its owner's repositories, so `app` creates the Apps on the account that owns the repository:

- **A personal account:** GitHub's manifest flow on the owner's own account.
- **An organisation:** GitHub's organisation manifest flow, at `https://github.com/organizations/<organisation>/settings/apps/new`, which an organisation admin runs once. The organisation's repositories then share both Apps, and each developer holds their own key (section 8, step 8). Plan 4 as built refused a repository that an organisation owns; its follow-ups add this flow (backlog item PRO-105).

| App | Permissions | Used by |
| --- | --- | --- |
| Worker App | Contents, Pull requests and Issues: read and write. Metadata: read | `devctl as worker`: pushes, opens and merges PRs, comments |
| Reviewer App | Pull requests: read and write. Contents and Metadata: read | `devctl as reviewer`: posts reviews |

Neither App has the Workflows, Administration or Checks permission, and neither is a code owner, so an App's approval never stands in for the owner's.

1. To create an App, `app` runs GitHub's manifest flow. A local HTTP server on `127.0.0.1` opens the browser at a page that posts the manifest. The App is private and has no webhook. `app` exchanges GitHub's one-time code at `POST /app-manifests/{code}/conversions`.
2. It stores each private key in the macOS Keychain, by passing it to `security` on stdin, under an item whose name carries the role and the App's ID: `rapid-ship/<role>-app/<App ID>`, such as `rapid-ship/worker-app/5376519`. One machine can then hold the keys of several Apps, such as a developer's own and their organisation's. Plan 4 as built names the item `rapid-ship/<role>-app`, without the ID; its follow-ups rename it. `rapid-ship app` re-stores a key it finds under the old name under the new one. A key is never written to disk, put on a command line or printed. An existing Keychain item is left in place.
3. It prints each App's ID and slug, and the URL that installs it on the repository; `--repository OWNER/NAME` names another repository. The owner installs both Apps, and `rs-setup` records the IDs and slugs in `project.toml`.
4. Where the Apps already exist, such as an organisation's, a developer adds their own key. They generate a private key in the App's settings on GitHub and run `rapid-ship app --import-key {worker,reviewer}`. It reads the key on stdin, checks that it signs a token GitHub accepts for the App that `[github]` records, and stores it as step 2 does. GitHub's settings page downloads the key as a file, which rapid-ship never writes; it tells the developer to delete the download. In an organisation the admin makes each developer an App manager of both Apps, so that they can generate a key. Whether an App manager may generate one is unverified (section 11).

### Who owns what

`sync` sorts every path into one of four groups, and respects the project's choices in each.

| Group | Examples | What `sync` does |
| --- | --- | --- |
| Language-agnostic Kit | devctl core, the `rs-` skills, the CI workflow, the pre-commit hook | Replaces unchanged files. A file the project edited or deleted becomes the project's own until `sync --revert` |
| Stack Kit | Each stack's guardrail seeds and check steps, under the stack's directory | The same; where a stack file and a common file share a path, the stack's wins |
| Project extensions | `tools/devctl/devctl_project/`, the project's own skills under `.agents/skills/`, extra workflows | Never touches them. Seeded files are reported when their template changes |
| Project overrides | A Kit path listed under `[kit] exclude` | Never touches it again |

A project that wants its own version of a Kit file, or none, lists it under `[kit] exclude`. Excluding a skill's directory also excludes its `.claude/skills` link. `[kit] exclude` is the only record of an exclusion: `status`, `sync`, `devctl check` and `devctl doctor` all read it there.

### Package layout

```text
rapid_ship/
  cli.py              # init, status, sync; app from plan 4
  files.py            # atomic_replace, safe_path, create_file
  github_app.py       # plan 4: manifest flows, key import, Keychain storage, install URLs
  kit/                # templates, lock, git, init, existing_checks, status, sync, writes, pull_request; migrations (plan 5); stacks (plan 6)
  templates/
    kit.toml          # seeded, new-project, executable and optional lists; template variables
    common/           # every stack: devctl, tools/devctl, skills, settings, CI, hook, guides
    python/           # Python stack: pyproject.toml seed, guardrail settings, skeleton, CODEOWNERS
    typescript/       # plan 6: TypeScript stack: package.json, tsconfig.json, ESLint and Vite seeds, React skeleton
    agnostic/         # stack-agnostic project.toml
```

`rapid_ship` never imports devctl. The upstream lock for forked skills (section 7) lives in this repository only, beside the templates.

### Lock file

`.rapid-ship/kit.lock` is TOML that `rapid-ship` writes; nobody edits it by hand.

```toml
# Written by rapid-ship. To own or drop a Kit file, list it under [kit] exclude in project.toml.
kit_version = "0.1.0"
stack = "python"

[variables]
owner = "octo"
package = "app"
project_name = "app"
repository = "octo/app"

[[file]]
path = "tools/devctl/devctl/check/map.py"
kind = "managed"
sha256 = "…"

[[file]]
path = ".claude/skills/rs-tdd"
kind = "managed"
link = "../../.agents/skills/rs-tdd"

[[file]]
path = "AGENTS.md"
kind = "seeded"
template_sha256 = "…"
```

From plan 6 the lock records each stack and its directory as `[[stack]]` tables, as `project.toml` does, in place of `stack`. `rapid-ship` rewrites an older lock itself, since nobody else writes it.

### This repository's vendored Kit

*This repository's own development, not product behaviour.* This repository ran `init` on itself, so `devctl`, `tools/devctl/`, `.githooks/pre-commit`, `.github/workflows/devctl-check.yml` and `.rapid-ship/` come from its templates. `uv run rapid-ship sync --in-place` refreshes the vendored copy from the working-tree templates, so a template change and its vendored copy land in the same PR. Three project steps in `devctl_project` guard this: `vendored` runs `rapid-ship status --strict`, `distribution` builds the wheel and runs `scripts/smoke_distribution.py`, and `python-3.12` runs the tests on the oldest supported Python.

## 4. Kit contents

| Path | Kind | Purpose |
| --- | --- | --- |
| `devctl` | managed | Shim that runs devctl from `tools/devctl/` with `uv run --frozen` |
| `tools/devctl/` | managed | devctl's source, with its own `pyproject.toml`, `uv.lock` and `.gitignore` |
| `tools/devctl/devctl_project/` | seeded | The project's verbs and extra check steps |
| `.agents/skills/rs-*/` | managed, plan 7 | Kit skills, each one real directory (section 7) |
| `.claude/skills/rs-*` | managed, plan 7 | One relative symlink per skill, to `../../.agents/skills/<name>`. Where a symlink cannot be made, `init` and `sync` exit 2 and leave nothing half-written |
| `.github/workflows/devctl-check.yml` | managed | CI |
| `.githooks/pre-commit` | managed | Runs `./devctl check --tier fast` |
| `.rapid-ship/kit.lock` | written by `rapid-ship` | The lock; not a template |
| `.rapid-ship/project.toml` | seeded | Stacks, repository, Agent identity, escalation list, Roster, Kit, map and test settings |
| `.rapid-ship/exceptions.toml` | seeded | Break-glass exceptions |
| `AGENTS.md`, `docs/AGENTS.md`, `tools/AGENTS.md` | seeded | The root guide and the first directory guides |
| `CLAUDE.md` | seeded | `@AGENTS.md`, so Claude Code reads the same instructions |
| `README.md`, `ARCHITECTURE.md` | seeded, plan 5 | Skeletons that `devctl check` verifies |
| `.claude/settings.json`, `.codex/hooks.json`, `.agents/hooks.json` | seeded, plan 5 | Harness guardrail wiring for Claude Code, Codex and agy |
| `.github/CODEOWNERS` | seeded | The owner for every path in Walk; below it, commented out, the Protected set |
| `docs/features/README.md` | seeded | The feature-file format |
| `docs/patterns/README.md` | seeded | The Pattern-file format |
| `.gitignore`, `pyproject.toml`, `src/AGENTS.md`, `src/<package>/__init__.py`, `tests/AGENTS.md`, `tests/test_import.py` | seeded, Python, only when there is no `pyproject.toml` yet | Guardrail settings, dev dependencies and a skeleton that passes `check` |
| The Python starter Patterns in `docs/patterns/`, with their reference code and tests | seeded, Python, plan 5, with the skeleton above | Error handling, configuration and input validation (Patterns, below) |
| `.gitignore`, `package.json`, `tsconfig.json`, `eslint.config.js`, `vite.config.ts`, `index.html`, `src/AGENTS.md`, `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx` | seeded, TypeScript, plan 6, only when there is no `package.json` yet | Guardrail settings, dev dependencies and a React skeleton that passes `check` |
| The TypeScript starter Patterns in `docs/patterns/`, with their reference code and tests | seeded, TypeScript, plan 6, with the skeleton above | The same three Patterns |

devctl runs through uv for every stack, so a TypeScript project needs uv as well as Node.js and npm. Its own lock keeps its dependencies apart from the project's. Kit-owned code is excluded from the project's lint, type and test settings; this repository checks it upstream.

A stack's files are written under its directory. With the Python stack in `backend/`, for example, the seed is `backend/pyproject.toml` (plan 6). The Kit's common files, such as devctl, the root guides, CI and the hook, stay at the repository root.

The Kit aims to give each area it touches a base template that a new project builds on and owns: the guides, the settings files, the starter Patterns, the CI workflow, the hook and each stack's guardrail settings.

### Settings files

None of these holds a secret. All are in the Protected set. Each is documented where it lives and validated where it is read:

- Every settings file the Kit ships, seeded or managed, documents each key or rule in a short comment wherever its format allows one: what it means, the values or range it accepts, and its default. That covers the TOML files, CODEOWNERS, the CI workflow and, from plan 6, `tsconfig.json`, which TypeScript reads as JSON with comments, `eslint.config.js` and `vite.config.ts`.
- devctl rejects an unknown key, a wrong type, a number outside its range and a value outside its allowed set in the files it reads. The error names the file, the key and what it accepts, so a typo cannot silently keep a default. A tool's own settings file is validated by the tool that reads it, such as Ruff, `tsc` or ESLint.
- Plain JSON seeds, such as the Harness wiring files and `package.json`, cannot hold comments. This section describes them, and doctor checks the wiring files (section 6).
- A test holds each seed to its loader: every key the loader accepts appears in the seed with its comment (plan 5).

`.rapid-ship/project.toml` after plan 6, for a repository with a Python backend and a TypeScript frontend:

```toml
# rapid-ship project settings. No secrets. Changes need the owner (Protected set).

# One table per stack. name: python, typescript or agnostic; agnostic stands alone.
# directory: a path inside the repository, relative to its root; "." is the root.
[[stack]]
name = "python"
directory = "backend"

[[stack]]
name = "typescript"
directory = "frontend"

[github]
repository = "owner/name"
# The code owner that CODEOWNERS names, written as CODEOWNERS writes it: "@login" or "@organisation/team".
code_owner = "@owner"
# Agent identity: each App's ID and slug, as rapid-ship app prints them. 0 and "" mean off.
# Record both Apps or neither. An ID is a whole number; a slug is lowercase letters, digits and -.
worker_app_id = 0
worker_app_slug = ""
reviewer_app_id = 0
reviewer_app_slug = ""

[escalation]
# The kinds of pull request the Lead brings to the owner instead of merging them on its own.
# The Protected set is always on the list. true is Walk: every pull request.
# false leaves the Protected set and the kinds below: Flight, or anything between.
every_pr = true
kinds = [              # plain text for the Lead
  "a pull request that removes a behavioural test",
  "a pull request that declares Over the diff cap:",
]
revision_rounds = 3    # 1 or more: a PR that reached this many Revisions also goes to the owner

# Optional. Only an owner who uses more than one Provider needs a Roster.
# One table per role, worker or reviewer. harness: any name; claude, codex and agy have
# built-in routes. model: the exact model ID, used as written. command: required for any
# other Harness, the headless command that starts it, with {prompt} and {model}.
# [roster.worker]
# harness = "codex"
# model = "<exact model ID>"
#
# [roster.reviewer]
# harness = "pi"
# model = "<exact model ID>"
# command = "<headless command with {prompt} and {model}>"

[kit]
optional = []          # opt-in Kit files and skills, such as "rs-contribute"
exclude = []           # Kit files or directories the project owns instead

[map]
source_roots = ["backend/src/<package>", "frontend/src"]
unguided = []          # maintained directories that need no guide
exclude = []           # directories whose AGENTS.md files are template content

[tests]
unit = ["backend/tests/unit/**"]   # every other test counts as behavioural
```

- **`[[stack]]` (plan 6):** one table per stack. `name` is `python`, `typescript` or `agnostic`, and `agnostic` cannot sit beside another stack. `directory` is a path inside the repository, relative to its root, and not a symlink; `"."` is the root. Two tables cannot name the same stack and directory. Until plan 6 the file holds one top-level key, `stack = "python"`, which TOML cannot hold beside `[[stack]]`. Plan 6's migration (section 3) rewrites it as one table at `"."`, and for one Kit version devctl reads the old key as that table, with a warning.
- **`[github]`:** `repository` is `owner/name`. `code_owner` is the code owner that CODEOWNERS names, written as CODEOWNERS writes it: `@<login>` for a person, or `@<organisation>/<team>` for a team. doctor's CODEOWNERS item checks CODEOWNERS against it, never against the repository's owner, because an organisation itself cannot be a code owner. Agent identity is on when both Apps are recorded, each with its ID and slug. A partial record, or Apps recorded without `repository`, is a settings error. [Spec 3](2026-10-16-metrics-and-gardening-design.md) matches an agent PR's author against the Worker App's slug, so it needs no App key.
- **`[escalation]`:** the escalation list. The Protected set is always on it, whether or not it is written here. `every_pr = true` is Walk. With `every_pr = false`, the list is the Protected set plus `kinds`: that is Flight, and each kind the owner adds moves it toward Walk. The merge guard holds the Protected set in every setup, and GitHub also holds it through CODEOWNERS with Agent identity and a ruleset (section 4). The other kinds are plain text for the Lead, which neither CODEOWNERS nor the merge guard can check. Two kinds are seeded: a PR that removes a behavioural test, which replaces the old test-removal switch, and a PR that declares `Over the diff cap:` (section 5). `revision_rounds`, 1 or more and 3 by default, sends a PR that reached that many Revision rounds to the owner in every Mode; it replaces `review_round_limit`, and [Spec 2](2026-10-16-delivery-skills-design.md) says how the Lead counts a round. `rs-lead` changes this table, and proposes the matching CODEOWNERS change, as a Protected PR.
- **`[roster]`:** one table per role, `worker` and `reviewer`, each naming a Harness and an exact model ID, kept exactly as written. It is optional; without it the Lead's Harness chooses its subagents' models. `harness` is any name. `claude`, `codex` and `agy` have built-in routes ([Spec 2](2026-10-16-delivery-skills-design.md)) and built-in sign-in checks. Any other Harness, such as pi on an API key or a gateway, needs `command`: the headless command that starts it, with `{prompt}` where the spawn prompt goes and `{model}` where the model goes. devctl rejects a `command` without both placeholders, and a Harness without a built-in route that has no `command`. Plan 4 built the table for `claude`, `codex` and `agy` only; plan 5 adds `command`. `devctl doctor` checks each Harness named here (section 6).
- **`[kit]`, `[map]`, `[tests]`:** built in plans 2 and 3. `[map] exclude` lets this repository keep the template guides under `rapid_ship/templates/` out of the map rules. Spec 3's plan lets `[kit] optional` name an optional Kit file, such as the metrics Action, as well as a skill. With several stacks, `source_roots` and `unit` name paths inside each stack's directory.
- **Added by Spec 2's plan:** `[tracker]` and `[design]`, which [Spec 2](2026-10-16-delivery-skills-design.md) defines.
- **Removed by plan 4:** `[agents]`, which the Roster replaces; `[linear]`, because devctl never talks to the tracker; `[dispatch]` (`max_workers`, `attempt_limit`, `worktree_root`), because nothing dispatches and rapid-ship takes no notice of how many Sessions run; and `[release]`, which nothing reads, because a project defines its own deploy metrics (Spec 3).

Plan 4 stopped seeding `.rapid-ship/gate.toml`, and devctl stopped reading it. The Mode lives in `[escalation]`, Flight has no lease, and the test-removal switch became a seeded escalation kind. The file's threshold tables described automatic promotion and demotion, which no longer exist. Spec 3's plan seeds `.rapid-ship/metrics.toml`, which holds the Suggested thresholds ([Spec 3](2026-10-16-metrics-and-gardening-design.md)). `sync` never deletes a seeded file, so an existing project keeps its old `gate.toml` until the owner deletes it; this repository deleted its own in plan 4.

`.rapid-ship/exceptions.toml` holds the break-glass entries. The seed holds comments only:

```toml
[[exception]]
id = "EX-1"
path = "src/app/run.py"
rule = "S603"
reason = "Runs the project's own build tool with fixed arguments"
remove_when = "The build tool has a Python API"
```

### Root AGENTS.md skeleton

The root guide stays short, following upstream `writing-for-agents`:

1. One paragraph naming the project.
2. Commands: `./devctl doctor --settings`, which each Session runs first unless it runs the full `./devctl doctor` (section 6), `./devctl check`, and `./devctl --help` for the project's verbs.
3. A "Find the change" table that points to directory guides, each stack's directory, `docs/features/` and `docs/patterns/`, and from plan 5 to `README.md` and `ARCHITECTURE.md`.
4. **Rules.** Each rule ends with `enforced by: <reference>` or `advisory` (section 5).
5. Pointers to `GLOSSARY.md`, `docs/adr/`, and the `rs-writing` and `rs-ponytail` skills (section 7).

AGENTS.md files are the single instruction source. The seeded `CLAUDE.md` is a real file containing `@AGENTS.md`.

### README.md and ARCHITECTURE.md

Plan 5 seeds both. For a new repository `rs-setup` fills them in with the owner; in an existing one `init` skips them where they exist, and `rs-setup` merges the skeleton's sections into them (section 8).

- **README.md:** what the project does and for whom, how to run it, how to check a change (`./devctl check`), and where the agent instructions start (`AGENTS.md`).
- **ARCHITECTURE.md:** the system's purpose and context, a table of its main parts (part, where, what it does), how data moves between them, links to the ADRs in `docs/adr/`, and how to work on the code. `rs-design` (Spec 2) maintains it.

`devctl check` verifies that both exist and that their links resolve (map rule 8, section 5).

### Patterns

A Pattern is the one supported way to do a recurring task. The Kit ships the file format in the seeded `docs/patterns/README.md`, map rule 5, which verifies it, and a starter set of Patterns for each stack (below). Each Pattern has one file in `docs/patterns/`, whose YAML front matter names three things:

```yaml
---
task: Read configuration
reference: src/app/settings.py
enforced_by:
  - banned:os.environ
  - test:tests/test_settings.py::test_settings_are_the_only_reader
---
```

- `task` is the recurring task in a few words. Plan 5 adds it; `reference` and `enforced_by` are built.
- `reference` is the path of the reference implementation. It must exist.
- `enforced_by` lists at least one reference to the check that enforces the Pattern (section 5). Each must resolve.

The text after the front matter states the rule, when it applies and the bypass it bans. A `## Lessons` section then explains what the reference does right: the choices a reader should copy, such as where it validates input, how it reports an error and why it stops at once. A path alone shows where good code is, not why it is good. Plan 5 adds the section, and map rule 5 requires it to be non-empty.

Agents may add a Pattern; changing an existing one needs the owner, so CODEOWNERS lists each existing Pattern file. That line is itself a Protected change, which the owner makes or approves.

#### Starter Patterns

The Kit seeds three starter Patterns for each stack, so a new project starts from a base it owns and adapts. Each comes with reference code in the stack's skeleton and the checks that enforce it, and its Lessons say what that code does right.

| Pattern | The rule | Enforced by, for example |
| --- | --- | --- |
| Error handling | Fail fast and gracefully: stop at the first error, report it with its cause and what to do next, and never hide, swallow or reword it | Python: `ruff:BLE001`, `ruff:S110`. TypeScript: `eslint:no-empty`, `eslint:@typescript-eslint/no-floating-promises`. A test of the error path |
| Configuration | One typed settings module reads configuration. It validates every value, with numeric ranges and allowed values, and documents each one in a short inline comment | Python: `banned:os.environ`. TypeScript: `eslint:no-restricted-syntax` on `process.env` and `import.meta.env` outside the module. A test that rejects an out-of-range value |
| Input validation | Validate input where it enters the program, into typed values: an enum or a union of literals, never a plain string | Python: a `type:` fixture. TypeScript: `eslint:@typescript-eslint/switch-exhaustiveness-check`. A test that rejects an unknown value |

The starter Patterns are new-project seeds: `init` writes them, with their reference code and tests, only when it starts a project in that stack (plan 5 for Python, plan 6 for TypeScript). Their file names carry the stack, such as `docs/patterns/python-error-handling.md`. In an existing repository their references would not exist, so `rs-setup` offers each one as a task instead, and `rs-health` proposes a reference from the project's own code. The plan that ships each set picks its exact checks. The gardener checks code that departs from them, and failing fast gracefully without obscuring an error is a base rule of the audit it shares with `rs-health` (section 9).

The Python and TypeScript stacks each name a profiler for finding slow code: for Python, a sampling profiler such as py-spy; for the TypeScript stack (React), the browser's performance tools and React's Profiler. `devctl check` never runs a profiler, because timings are not deterministic. Beside the three starter Patterns, each of these stacks has a performance Pattern that documents its profiler, and the plan that ships the stack's starter set writes it. Like any Pattern, it must pass map rule 5:

- `task`: the recurring task, such as `Find slow code`;
- `reference`: a profiling entry point in the stack's skeleton, such as a script that profiles the skeleton's entry point, with comments on how to read the result;
- `enforced_by`: at least one check that resolves, such as a test that runs that entry point on a small input without judging its timing.

That plan picks the exact reference and checks, as it does for the starter Patterns. The performance Pattern is seeded like them, for new projects only, because its reference lives in the skeleton. In an existing repository `rs-setup` offers it as a task.

### Skills layout

Each skill, from the Kit or the project, is one real directory, `.agents/skills/<name>/`, which Codex and agy read. Claude Code is the only major Harness that does not read `.agents/skills`, so it gets one relative directory symlink per skill: `.claude/skills/<name> -> ../../.agents/skills/<name>`. The Kit lock records each link like any other managed file. `SKILL.md` itself is never a symlink, because Codex rejects one by design. opencode and Gemini CLI read both directories and warn about the duplicates; that cost is accepted.

`rs-work` and `rs-review` ship as skills only, with no per-Harness subagent definition files. The Lead tells its Harness's generic subagent to follow the skill, or follows it itself.

### Harness guardrails

The Kit brings the rungs into the agent's loop through the Harness's hooks. One devctl command, `devctl hook` (section 6), holds every rule, and each Harness's seeded settings file only wires that command to the Harness's hook events. A Kit update therefore changes the rules for every project, while each project keeps its own settings files.

rapid-ship works with any Harness, a CLI or a desktop app, on any Provider: a subscription, an API key or a gateway, such as pi on a model through OpenRouter. The Kit ships wiring for three Harnesses: Claude Code, Codex and agy. Any other Harness gets AGENTS.md, `.agents/skills`, the pre-commit hook and CI. Its Sessions run without the Harness guardrails, the merge guard included, until it has wiring, which takes one more wiring file and one more `devctl hook` protocol. The pre-commit hook, CI and any ruleset still hold, so GitHub alone holds the bar at merge: the ruleset's required `devctl check` where a ruleset exists, and the owner's approval of the Protected set only with Agent identity and a ruleset. `rs-lead` and `rs-preflight` say so when the Lead or an Agent runs on such a Harness ([Spec 2](2026-10-16-delivery-skills-design.md), [Spec 3](2026-10-16-metrics-and-gardening-design.md)).

Claude Code documents that its settings hooks also fire inside subagents. Whether Codex's and agy's hooks fire, can ask, fire inside subagents and headless Sessions, and pass the fields the rules need is unconfirmed until a spike, the first task of plan 5 (backlog item PRO-139). Until it reports, Spec 1 claims the guardrails for Claude Code only, and `rs-lead` warns that a Codex or agy Worker may run without them ([Spec 2](2026-10-16-delivery-skills-design.md)).

| Rule | When | Decision |
| --- | --- | --- |
| G1. A git command with `--no-verify`, or `git commit -n` | Before a shell command | Deny |
| G2. `git push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes`, or a refspec that starts with `+` | Before a shell command | Deny |
| G3. Another way to land a change on the default branch: `gh pr merge` with `--admin`, a `git push` to the default branch, or a `gh api` call that merges, writes the default branch's ref or commits a file. Step 1 of the merge guard lists each form the hook recognises | Before a shell command | Deny, with or without Agent identity, and name `gh pr merge <number>` without `--admin` |
| G4. A file-edit tool writing `.rapid-ship/kit.lock` | Before a file edit | Deny: `rapid-ship` writes the lock |
| G5. A file-edit tool writing a path in the Protected set | Before a file edit | Ask the owner |
| G7. With Agent identity on: `git push` in any form | Before a shell command | Deny, and name `./devctl as worker push` |
| G8. With Agent identity on: a `gh` write as the owner, which is any `gh pr` subcommand other than `view`, `list`, `status`, `diff`, `checks` or `checkout`; any `gh issue` subcommand other than `view`, `list` or `status`; or `gh api` with a method other than `GET` or with `-f`, `-F`, `--field`, `--raw-field` or `--input` | Before a shell command | Deny, and name `./devctl as <role> gh` |
| G9, the merge guard. An agent's `gh pr merge`, with or without Agent identity | Before a shell command | Deny while `devctl check` has not passed on the PR's head commit, or when the PR touches the Protected set |

No rule runs when an agent stops, and no rule has the number G6. Running `devctl check` at the end of every turn or subagent costs too much, so rung 2 holds through the pre-commit hook and CI, and `rs-work` has a Worker run `./devctl check` before it reports its task done ([Spec 2](2026-10-16-delivery-skills-design.md)).

- **Commands:** the hook splits the command line with shell rules and checks each simple command joined by `;`, `&&`, `||` or `|`. For G3 and the merge guard, a `gh` command run through `./devctl as <role> gh` counts as the `gh` command it runs. G8 never applies to it, because it runs as an App.
- **The Protected set** for G5 is read from the Protected-set lines of `.github/CODEOWNERS`, commented or not, never the `*` line. These are the lines the `diff` step reads, and both use one matcher.
- **Decisions:** the hook only denies or asks. It never allows or approves anything; with no rule matched it gives no decision, and the Harness's own permission flow continues.
- **Exit codes, a workaround:** devctl's convention, where exit 2 means "could not run", collides with the Harnesses' hook protocols: Claude Code reads a hook's exit 2 as "block". While each Harness defines its own protocol there is no neutral choice. `devctl hook` therefore answers in each Harness's protocol, keeps that mapping in one module, `hook_protocols.py`, and documents it there as a workaround. It never exits 2. An internal error exits 1 with a message, and the call goes through: Claude Code treats exit 1 as a non-blocking error, and the PRO-139 spike confirms how Codex and agy treat it. The merge guard is the exception: once it has recognised a merge, it catches its own errors and denies the merge.
- **When the hook fails before it decides:** the workaround holds only while `devctl hook` runs and has parsed the event. In Claude Code, these are non-blocking errors, so the call goes through, a merge included: `uv` is not on `PATH`, and the `devctl` shim exits 127; Python fails while it loads devctl; the hook cannot parse the event; or Claude Code kills the hook at its hook timeout. When uv itself fails, for example because it finds no Python, it exits 2. Claude Code reads that as block, so every wired call stops until the setup is fixed. The `./devctl doctor` run at the start of a Session is what catches a broken setup: it starts through the same shim, so a uv or Python failure stops it too, and it reports wiring that lacks the Kit's hooks (section 6). It cannot catch a hook timeout, or an event format that a Harness update changed. The PRO-139 spike records how Codex and agy treat these cases.
- **Unreadable settings:** G1 to G4 need no settings and always apply. When the hook cannot read `.rapid-ship/project.toml` or `.github/CODEOWNERS`, G5, G7 and G8 give no decision, and the hook writes the reason to stderr. Checking the settings on every tool call costs too much, so broken settings are caught once, at the start of a Session: `./devctl doctor` exits 2 and names the file and the key (section 6). The merge guard reads what it needs from GitHub and still denies a merge it cannot check.
- **Limits:** the hook reads the command line as the Harness passes it. It does not follow scripts, aliases, `sh -c` strings or shell redirections that write files, and it does not read a request body from a file or stdin. It sees only the tools it is wired to, so a merge through another tool, such as an MCP server's merge tool, is outside it. Other `gh` commands that write, such as `gh release` or `gh workflow run`, are outside G8, and `devctl as` refuses them. These rules stop habits and mistakes. A misbehaving agent can bypass every one of them, the merge guard included, for example through a script, its own HTTP client, a tool the hook does not see or a Harness without the wiring. Where a ruleset exists, GitHub enforces the required `devctl check`, and with Agent identity the owner's approval through CODEOWNERS too.

| Harness | Seeded file | Wiring |
| --- | --- | --- |
| Claude Code | `.claude/settings.json` | `PreToolUse` for `Bash`, `Edit`, `Write`, `MultiEdit` and `NotebookEdit`, running `"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool`. Settings hooks also fire inside subagents |
| Codex | `.codex/hooks.json` | `PreToolUse` for `Bash` and `apply_patch`, running `devctl hook codex pre-tool`. Codex runs project hooks only in a trusted project, after the owner reviews them in `/hooks`; a changed hook needs a new review. The PRO-139 spike confirms whether Codex hooks can ask and fire inside subagents. If they cannot ask, the Codex wiring omits G5 and leaves those edits to CODEOWNERS and the merge guard |
| agy | `.agents/hooks.json` | `PreToolUse`, running `devctl hook agy pre-tool`. The PRO-139 spike confirms whether agy's hooks fire inside subagents |

The files are seeded, not managed, because many repositories already have a `.claude/settings.json`; `init` skips an existing one and `rs-setup` merges the Kit's entries into it. `devctl doctor` reports a wiring file that lacks the Kit's hooks (section 6).

Sandboxing is not part of the Kit. A Harness's subagents inherit the sandbox of the owner's own Session, so a sandbox is the owner's choice for their whole Session. `rs-setup` offers it (section 8).

#### The merge guard

G9, the merge guard, keeps an agent from merging a pull request until `devctl check` has passed on its head commit, and from merging one that touches the Protected set. It is on in every setup and every Mode, with or without Agent identity and with or without a ruleset, in each Harness whose hooks run `devctl hook` (the wiring table above). It has no rule for Walk: in Walk the Lead merges a PR only when the owner says so, which the Lead brief carries as advice ([Spec 2](2026-10-16-delivery-skills-design.md)). With Agent identity and a ruleset, which public repositories and paid plans have, GitHub enforces the same bar too. A GitHub Free private repository has no rulesets, so there the guard is the enforcement: an agent's merge of a PR whose check failed is rejected when the agent tries it. The guard reads GitHub only for `gh pr merge`. G3 denies outright the other ways to land a change on the default branch that the hook recognises, a `git push` to it included, so `gh pr merge` is the only recognised way left (step 1). The owner merges a Protected-set PR in GitHub's web interface. The Protected set therefore needs the owner in every Mode, and Flight without Agent identity keeps that.

1. **Commands.** The guard checks `gh pr merge`, with any arguments, `--auto` included, run directly or through `./devctl as <role> gh`. G3 denies outright each other way to land a change on the default branch that the hook recognises, run directly or, for `gh`, through `./devctl as <role> gh`:
   - `gh pr merge` with `--admin`;
   - `git push` to the default branch: a refspec whose destination is that branch, such as `main`, `HEAD:main`, `HEAD:refs/heads/main` or the deletion `:main`; `--all` or `--mirror`; or `HEAD` or no refspec while the current branch is the default branch. The hook reads the default branch's name locally from `refs/remotes/origin/HEAD`, and treats both `main` and `master` as the default branch when that ref is missing. It reads the refspecs on the command line, not git's push settings;
   - `gh api` with a method other than `GET`, set with `-X` or `--method` or implied by `-f`, `-F`, `--field`, `--raw-field` or `--input`, on one of these paths: `repos/<owner>/<repo>/pulls/<number>/merge`, a PR's merge; `repos/<owner>/<repo>/merges`, the Merges API; `repos/<owner>/<repo>/git/refs/heads/<default branch>`, the default branch's ref; or `repos/<owner>/<repo>/contents/<path>`, the Contents API, which commits a file to a branch. A path matches with or without a leading `/` and as a full API URL, gh's `{owner}` and `{repo}` placeholders included;
   - `gh api graphql` with a query, given inline, that names the `mergePullRequest`, `enablePullRequestAutoMerge`, `enqueuePullRequest`, `mergeBranch`, `updateRef`, `updateRefs` or `createCommitOnBranch` mutation.

   Every other tool call pays only for this match. The guard reads GitHub for `gh pr merge` and for nothing else, and G3 reads git locally only for a `git push` or a ref path.
2. **The pull request.** The number, URL or branch that `gh pr merge` names, or without one the PR of the current branch.
3. **The check.** The guard reads the PR's head commit and that commit's check runs from GitHub, through `gh api` with `GET` under the owner's sign-in. The check has passed when the latest check run named `devctl check` from GitHub Actions, the one the ruleset requires (section 8), has completed on that commit with the conclusion `success`. A pending, failed, cancelled, skipped or missing run has not passed.
4. **The files.** It lists the PR's changed files from GitHub, each with its status and, for a rename, its previous path. It matches both paths of each file against the Protected-set lines of `.github/CODEOWNERS` on the PR's base branch, never its head, the copy GitHub itself reads, so a PR cannot exempt itself. It uses the matcher the `diff` step uses, and it applies the ledger rule (section 5): a Corrections ledger entry that the PR changes, renames or removes is Protected. An entry that the PR adds is not checked, whatever its status.
5. **Decision and message.** While the check has not passed, the guard denies with `merge denied: devctl check on PR #<n> at <commit> is <state>; wait for it to pass or fix what it reports, then merge again`. When the PR touches the Protected set, it denies with `merge denied: PR #<n> touches the Protected set (<paths>); the owner merges it in GitHub's web interface`. When the check has passed and the PR touches no Protected path, the command must also carry `--match-head-commit` set to the head commit the guard checked. When the option is missing or names another commit, the guard denies with `merge denied: PR #<n> merges only at the checked head <commit>; run <the same command> --match-head-commit <commit>`, the exact command to retry. With the option set, GitHub refuses the merge if the head moves after the guard's read. When it cannot read GitHub or identify the PR, it denies with the reason and gh's first error line, so a merge that the running guard cannot check does not pass. When the hook fails before the guard decides, the guardrail bullets above say what happens. Otherwise it gives no decision.
6. **Cost.** Only `gh pr merge` pays: four reads through `gh api`, for the PR, its check runs, its files, paginated, and CODEOWNERS on the base branch.
7. **Limits.** The guard reads GitHub when the command runs. A push that lands between that read and the merge moves the head, so GitHub refuses the merge because of `--match-head-commit` (step 5). It and G3 recognise only the forms of step 1. Like every guardrail, they can be bypassed by a misbehaving agent, for example through a script or a tool the hook does not see.

### The Protected set and CODEOWNERS

The Protected set is the kinds of change that need the owner's approval in every Mode. CODEOWNERS assigns them to the owner, and GitHub reads it from the PR's base branch, so a PR cannot exempt itself. The merge guard holds the Protected set in every setup: it denies an agent's merge of a Protected-set PR, which the owner then merges in GitHub's web interface. With Agent identity and a ruleset that requires code-owner review, GitHub holds it too. The seeded CODEOWNERS has one active line in Walk, `* @<owner>`. Below it, commented out for Flight, is the Protected set:

- `/.github/`, `/.githooks/`, `/devctl`, `/tools/devctl/`;
- the skills and the Harness guardrail wiring: `/.agents/` (widened from `/.agents/skills/` in plan 5, so it covers `.agents/hooks.json`), `/.claude/`, and `/.codex/` (added in plan 5);
- every `AGENTS.md` and `CLAUDE.md` (`/**/AGENTS.md`, `/**/CLAUDE.md`);
- `/.rapid-ship/`, which holds the stacks, the escalation list, the Roster and the exceptions;
- the settings files of the check tools, because a settings file can switch its check off: `/.gitleaks.toml`, `/.gitleaksignore`, `/zizmor.yml` and `/zizmor.yaml`; for the Python stack `/pyproject.toml`, `/**/ruff.toml`, `/**/.ruff.toml`, `/mypy.ini`, `/.mypy.ini`, `/pytest.ini`, `/.pytest.ini`, `/pytest.toml`, `/.pytest.toml`, `/setup.cfg`, `/tox.ini` and `/.importlinter`; and for the TypeScript stack (plan 6), in its directory, `package.json`, `.npmrc`, `tsconfig*.json`, `eslint.config.*`, `.prettierrc*`, `prettier.config.*`, `.prettierignore`, `vite.config.*` and `vitest.config.*`. A stack in a subdirectory gets its lines under that directory, such as `/backend/pyproject.toml` and `/frontend/package.json` (plan 6);
- `/docs/corrections/README.md`, the Corrections ledger's format, which Spec 3's plan seeds with this line;
- one line for each existing Pattern file, and any paths the project adds for access, the data model or the public API.

A change to or removal of an existing Corrections ledger entry is Protected too. CODEOWNERS cannot tell a new file from a changed one, so devctl carries that rule: the `diff` step lists such a change with the Protected paths, and the merge guard treats it as Protected (section 5). Adding an entry is not Protected, and devctl does not read an added entry's status. An agent could therefore add an entry that is already `implemented`, `rejected` or `closed`; the owner accepts that limit.

Plan 5 replaces the seed's placeholder comment about Harness settings with the lines above, and updates doctor's list of Protected paths to match. Flight uncomments the Protected set and removes the `*` line; `rs-lead` proposes that change as a Protected PR. With Agent identity, the `*` line enforces Walk, because an App cannot bypass the ruleset. Without it, under a ruleset, an agent's PR comes from the owner's account and only the owner's bypass can merge it, so Walk rests on the Lead brief and the guardrails ([Spec 2](2026-10-16-delivery-skills-design.md)). Without a ruleset, with or without Agent identity, Walk rests on the Lead brief and the owner's instruction, which are advice. In every setup the merge guard still holds the Protected set and a passing `devctl check`.

### CI workflow

`.github/workflows/devctl-check.yml` (built in plan 3):

- **Triggers:** `pull_request`, including body edits; `push` to `main` or `master`; a nightly `schedule`; and `workflow_dispatch`. A workflow cannot name the default branch, and a push run skipped by a condition would report a passing `devctl check` on the same commit, so the branches are listed. `rs-setup` records a Setup gap when the default branch has another name.
- **Permissions:** `contents: read` only. The job uses no secrets, so fork PRs behave the same.
- **Concurrency:** PR runs share one group per ref and cancel superseded runs. As built in plan 3, push runs share their ref's group too, so GitHub cancels a pending push run when a newer one queues. Plan 5 gives each push run a group of its own commit, so every merge gets its run; [Spec 3](2026-10-16-metrics-and-gardening-design.md) counts red merges from them.
- **Steps:** checkout and `astral-sh/setup-uv`, both pinned by commit SHA, with `persist-credentials: false` and full history for the diff policy. Install gitleaks 8.30.1, verified by its SHA-256. Run `./devctl check --tier full`. Plan 6 adds `actions/setup-node`, pinned by commit SHA, which runs only when the repository holds a `package-lock.json`, and the run becomes `./devctl check --tier full --install`, which installs each TypeScript stack's locked dependencies first. The workflow stays the same file in every project.
- **Job name:** `devctl check`, which the ruleset requires.

The nightly run checks the default branch. Spec 3 counts a red default-branch run after a merge as a metric.

### Python guardrail settings

New projects get these settings in the seeded `pyproject.toml`. An existing project keeps its own settings in the Setup PR, apart from devctl's exclusions. At the end of Setup, `rs-setup` offers the meaningful rules they lack in a separate PR (section 8, step 15), and `devctl doctor` reports what is still missing.

- **Ruff:** E, W, F, I, B, UP, SIM, C4, RUF, PGH, ERA, T20, S, TID, PT, PTH, DTZ, C90, TD, BLE and ANN401. C90's `max-complexity` is 10. Relative imports are banned. A `banned-api` table starts empty, and Patterns fill it. PGH003, PGH004, RUF100 and ERA001 control escape hatches. `rs-setup` adds ASYNC and FAST where it finds asyncio or FastAPI; the seed does not.
- **mypy:** strict over source and tests, with `warn_unreachable` and the error codes `ignore-without-code`, `redundant-expr` and `truthy-bool`.
- **import-linter:** one `layers` contract, whose layers stay optional until the architecture names them, and one `forbidden` contract that keeps pytest out of production code.
- **pytest:** `--strict-markers --strict-config`, `xfail_strict = true`, `filterwarnings = ["error"]`.
- **Dev dependencies:** ruff, mypy, pytest and import-linter in the project's lock.

There is no ratchet. Unsafe patterns are prohibited. A legitimate exception is a listed break-glass entry (section 5).

### TypeScript guardrail settings

Plan 6 adds the TypeScript stack, for React with TypeScript, with npm as the package manager. New projects get these settings in the stack's seeded files; an existing project gets them as a Python project does.

- **TypeScript:** `tsconfig.json` sets `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`, `isolatedModules` and `noEmit`.
- **ESLint:** a flat `eslint.config.js` with ESLint's recommended rules, typescript-eslint's `strictTypeChecked` set and the React Hooks plugin's recommended rules. It adds `complexity` at 10, `no-console`, `@typescript-eslint/switch-exhaustiveness-check`, and `@typescript-eslint/ban-ts-comment`, which bans `@ts-ignore` and `@ts-nocheck` and requires a description on `@ts-expect-error`. An unused disable comment is an error (`reportUnusedDisableDirectives`). A `no-restricted-imports` rule starts empty, and Patterns fill it, as they fill Ruff's `banned-api`. The lint step allows no warnings.
- **Prettier:** its defaults. Line width and other style options are the project's choice.
- **Vitest:** `vitest run`, with `allowOnly: false`. React component tests use jsdom and Testing Library.
- **npm:** `package-lock.json` is committed, and `engines.node` names the supported Node.js major version.
- **Other tools:** Tailwind CSS and tools like it are welcome. The Kit neither seeds nor blocks them, and `rs-setup` adds their ESLint and Prettier plugins where the project uses them.
- **Dev dependencies:** ESLint with its TypeScript and React Hooks plugins, Prettier, TypeScript, Vitest, jsdom and Testing Library, in the stack's `package.json` and lock. Plan 6 pins their versions.

## 5. `devctl check`

`check` is the single entry point for hooks and CI. It covers everything a machine can decide, and it never runs a model. Built in plan 3. Plan 5 adds map rule 8, the Pattern `task` key and Lessons section, the `SKILL.md` rule, the diff cap and the ledger rule. Plan 6 runs each stack's steps in its own directory and adds the TypeScript stack.

### Steps

| Step | Tier | Fails when |
| --- | --- | --- |
| format | fast | Formatting differs (Python: `ruff format --check`; TypeScript: `prettier --check .`) |
| lint | fast | The linter reports a finding (Python: `ruff check`; TypeScript: `eslint --max-warnings 0 .`) |
| map | fast | A map rule below fails |
| exceptions | fast | A suppression lacks a listed exception, or an exception matches nothing |
| file-size | fast | A source file exceeds 500 lines without an exception |
| kit | fast | The lock is unreadable, or a managed file that is not excluded is missing |
| types | full | The type checker fails (Python: mypy; TypeScript: `tsc --noEmit`) |
| contracts | full | An import contract is broken (Python: `lint-imports`; TypeScript has no contracts step yet, which a tool such as dependency-cruiser could fill later) |
| tests | full | The test suite fails (Python: pytest; TypeScript: `vitest run`) |
| audit | full | A locked dependency has a known vulnerability (Python: pip-audit 2.10.1; TypeScript: `npm audit`) |
| secrets | full | gitleaks finds a secret in the change's commits, or in the whole history without a base. gitleaks must be on `PATH` |
| workflows | full | zizmor 1.30.1 reports a finding in a GitHub Actions workflow |
| diff | full | The diff policy below fails |
| evidence | full, PRs only | The PR body lacks its Evidence section |

Each stack supplies its own tools. The agnostic stack has no `format`, `lint`, `types`, `contracts`, `tests` or `audit` step. pip-audit and zizmor run through `uv tool run --from <pin>` and are not dependencies. The TypeScript stack runs each tool from `node_modules/.bin` in its directory and `npm audit` through npm, and it never installs anything: a missing tool blocks its step, and the message names the command that installs it, `npm ci` in that directory. A project adds steps in `devctl_project`.

### Several stacks

Plan 6 runs the common steps once, at the repository root: map, exceptions, file-size, kit, secrets, workflows, diff and evidence. It runs each stack's own steps, format, lint, types, contracts, tests and audit, once per stack, in that stack's directory, with that stack's tools and settings. With one stack at the root, the step names stay as they are. Otherwise each stack's step is named with its directory, such as `lint (frontend)`. The exit code follows the rules below over every step.

A file belongs to the stack whose directory contains it, the innermost one when directories nest. The exceptions step reads each file's suppressions in its stack's forms, and the file-size step counts its stack's source files: `.py` and `.pyi` for Python, `.ts` and `.tsx` for TypeScript. A file outside every stack's directory has only the forms that every stack shares, those of gitleaks and zizmor.

### Output and exit codes

- `./devctl check [--tier fast|full] [--json] [--base REV] [--pr-body PATH] [--install]`. The default tier is `full`. `--install`, from plan 6, first runs `npm ci` in each TypeScript stack's directory; CI uses it.
- One line per step: passed, failed, blocked, or not applicable, with details below a step that did not pass. `--json` prints the same as a list of `{"name", "status", "details"}` objects.
- Exit 0: every applicable step passed. Exit 1: at least one step failed. Exit 2: at least one step could not run, for example a missing tool or an unreadable setting. A blocked step never counts as passed, and 2 outranks 1.
- The `diff` and `evidence` steps need a change. In CI the base is the PR's base and the body comes from the PR event. Locally, `--base` names the base, or devctl uses the merge base with `origin`'s default branch, and `--pr-body` names a file with the body. Without a base `diff` is not applicable; outside a PR, `evidence` is not applicable.

### Map rules

1. Every Markdown link in every AGENTS.md resolves to a tracked or non-ignored file.
2. Every maintained directory has an AGENTS.md. Maintained directories are the top-level tracked directories and the immediate children of each source root, except hidden directories and those listed in `[map] unguided`. AGENTS.md files under a `[map] exclude` directory are template content: the map rules ignore them.
3. Every AGENTS.md is reachable by links from the root AGENTS.md.
4. Every file in `docs/features/` other than its README has front matter with `purpose`, `entry_points`, `data`, `observe` and `reproduce`. Each path it names exists. `entry_points` is not empty. Each `reproduce` command is `./devctl` followed by a registered verb.
5. Every file in `docs/patterns/` other than its README has front matter with a non-empty `task`, a `reference` that exists and a non-empty `enforced_by` list whose references resolve, and the file has a non-empty `## Lessons` section. Plan 5 adds `task` and the Lessons section.
6. Every bullet under a `Rules` heading in any AGENTS.md ends with `enforced by: <reference>` or `advisory`. Each reference resolves.
7. Every skill directory under `.agents/skills/`, from the Kit or the project, has a `SKILL.md` whose front matter `name` equals the directory name and whose `description` is not empty, and a relative symlink at `.claude/skills/<name>` that points to it. No other entry exists under `.claude/skills/`. A skill directory that is itself a symlink must be relative and stay inside the repository. Plan 5 adds: `SKILL.md` is a regular file, not a symlink.
8. Plan 5: `README.md` and `ARCHITECTURE.md` exist at the repository root, every local link in them resolves, and the root AGENTS.md links to both.

Spec 3 adds a rule for the Corrections ledger after these.

### References

A reference names the check that enforces a Rule or Pattern. The stack defines the kinds, and `check` resolves each one.

| Reference | Resolves when |
| --- | --- |
| `check:<step>` | The devctl check step exists |
| `test:<path>::<name>` | The test exists |
| `ruff:<code>` | The rule is selected in the Ruff settings (Python) |
| `banned:<module.member>` | The member is in Ruff's `banned-api` table (Python) |
| `contract:<name>` | An import-linter contract has that name (Python) |
| `type:<path>` | The file exists and the stack's type checker checks it: mypy (Python), or `tsc` through `tsconfig.json` (TypeScript, plan 6) |
| `eslint:<rule>` | The rule is on, as an error, in the configuration that `eslint --print-config` computes for the stack (TypeScript, plan 6) |

These map to the four Pattern enforcement types: import contract, banned-API rule, type fixture and architecture test.

With several stacks, a reference resolves against the stack that holds the Pattern's `reference`, or the AGENTS.md that states the Rule.

### Exceptions

A suppression is a line that switches a check off. For Python these are `# noqa`, `# type: ignore`, the `# mypy:` file comments, `# pragma: no cover`, and pytest's skip, skipif, xfail and importorskip. gitleaks's inline allow comment and `# zizmor: ignore[...]` are suppressions in every stack.

For TypeScript (plan 6) the suppressions are `eslint-disable` comments in each form, `@ts-expect-error`, `prettier-ignore`, the coverage tools' ignore comments, and Vitest's `skip`, `skipIf`, `todo` and `fails`. ESLint bans `@ts-ignore` and `@ts-nocheck`, and Vitest's `allowOnly: false` fails `only`. Plan 6 names each form's rule, as plan 3 did for Python.

1. Each suppression carries `rs-exception: EX-<n>` on the same line. One marker matches one rule, so a line that switches off two rules needs two markers and two entries.
2. `EX-<n>` exists in `.rapid-ship/exceptions.toml` with a matching path and rule, a reason and a removal condition.
3. Each ID is used exactly once. An entry that matches no suppression fails as stale.
4. File-size exceptions are path entries with `rule = "file-size"` and no inline marker. They fail as stale once the file is under the cap.

Kit-managed files that are not excluded are not scanned. An added suppression needs an edit to `exceptions.toml`, which is Protected. Nothing is counted, so removing one suppression cannot pay for adding another. For an existing project, `rs-setup` marks each existing suppression at Setup (section 8).

### Diff policy

The diff policy compares the change with its base. It is adapted from no_human's test-tamper guard (MIT), using each test's identity instead of its net counts.

1. **Removed tests:** a test present at the base and absent everywhere at the head fails, unless the PR body declares it under `Removed tests:` with a reason. A test's identity is its name within its file (`test_x` or `TestA::test_x`), so a test moved to another file is not a removal. The step classes each removed test as unit or behavioural: a test is a unit test only when its path matches `[tests] unit`; every other test, such as an integration or end-to-end test, is behavioural. Whether a declared removal goes to the owner is the escalation list's business: the seeded list names behavioural-test removals.
   For Vitest (plan 6), a test's identity is the chain of its `describe`, `it` and `test` titles in its file. A title that is not a plain string cannot be compared, and the step lists that test as not checked.
2. **Tautologies:** an assertion that the change turns into a tautology, such as `assert True`, `x == x` or Vitest's `expect(x).toBe(x)`, fails.
3. **Faking fixtures:** a new `autouse` fixture in a `conftest.py` fails without an exception. Vitest names its setup files in its configuration, which is Protected.
4. **Protected paths:** the step lists each Protected path the change touches, and each ledger entry that item 6 makes Protected. It does not fail; the merge guard enforces the approval, and so does GitHub through CODEOWNERS with Agent identity and a ruleset.
5. **Diff cap (plan 5):** a change that adds and removes more than 1,500 lines in total fails, unless the PR's Evidence section has a line starting `Over the diff cap:` with a reason. The count leaves out files ending in `.md`, `.txt` or `.log`, binary files, Kit-managed files, `.rapid-ship/kit.lock` and each stack's lock file (`uv.lock`, `package-lock.json`), so documentation, logs and a Kit sync do not count. A declared overage passes with a note. A PR that declares one is a default escalation kind (section 4), so the Lead brings it to the owner in every Mode. `rs-work` declares one only after the owner accepted the overage, before the work ([Spec 2](2026-10-16-delivery-skills-design.md)).
6. **Corrections ledger (plan 5):** a change that modifies, renames or removes an existing entry, a Markdown file under `docs/corrections/` other than `README.md`, is Protected. The step lists each such change with the Protected paths, and the merge guard treats it as Protected. Adding an entry is not Protected, and the step does not read an added entry's status, a limit the owner accepts (section 4). An agent can therefore add a Correction without the owner, while changing or removing one, its status included, needs the owner's review. CODEOWNERS cannot tell a new entry from a changed one, so devctl carries this rule; CODEOWNERS holds only the ledger's `README.md` (section 4). [Spec 3](2026-10-16-metrics-and-gardening-design.md) defines the ledger, whose entries agents report.

Skip markers are suppressions, so the exceptions step handles them.

### Evidence

On a PR, the body must contain an `## Evidence` section with at least one command and its result, and a line starting `Not covered:`. When the change removes tests, the section also lists them under `Removed tests:`. A Worker writes the section by following `rs-work` (Spec 2) and the `rs-pr` engineering skill. CI reruns the check when the PR body is edited.

```markdown
## Evidence

- `./devctl check`: exit 0; every step passed except evidence, not applicable

Removed tests:
- `tests/test_flags.py::test_legacy_flag`: the flag was deleted in this PR

Not covered: behaviour on Windows.
```

### Where `check` runs

1. The pre-commit hook runs the fast tier. `git commit --no-verify` skips it, which the Kit's Harness guardrails deny to agents.
2. `rs-work` has the Worker run it before it reports its task done and before it opens a PR ([Spec 2](2026-10-16-delivery-skills-design.md)). That run is advisory.
3. CI runs the full tier on every PR. A ruleset requires it where GitHub offers one, and in every setup the merge guard denies an agent's merge until it passes; this is the enforcement.
4. The nightly CI run checks the default branch.

## 6. Other devctl commands

devctl keeps only commands used repeatedly. The owner asked to keep this surface small, so a new need becomes an option of an existing command where one fits.

| Command | Built in | What it does |
| --- | --- | --- |
| `check` | plan 3 | Section 5 |
| `doctor [--skills] [--settings]` | plan 4; `--settings` in plan 5 | Reports what this machine and repository lack. `rs-lead` and `rs-preflight` run it first in full; every other Session runs `--settings` first |
| `as {worker,reviewer} ...` | plan 4 | Agent identity's thin command for `gh` and `git push` |
| `hook {claude,codex,agy} pre-tool` | plan 5 | The Harness guardrails, with the merge guard |
| `metrics` | Spec 3 | The metrics report |

A project adds its own verbs in `devctl_project`. devctl never starts an agent to do work, never tracks or resumes one, and never talks to the issue tracker. Only doctor's probes start a short headless Session, to check a Harness's sign-in and the skills it loads.

### `devctl doctor`

doctor changes nothing in the repository. It reports each item as ok, missing or unknown, then a summary line. It exits 0 when everything is ok, 1 when something is missing and 2 when an item could not be checked. Plan 4 built it from the old branch, reshaped as below. It reads GitHub with the owner's `gh` sign-in, always as `GET`.

**At the start of each Session.** While `devctl hook` cannot read the settings, it still applies G1 to G4, and the merge guard still denies a merge it cannot check, but G5, G7 and G8 give no decision: the asks before Protected edits and Agent identity's denies are lost. Checking the settings on every tool call costs too much, so a Session catches broken settings once, at its start. doctor reads `.rapid-ship/project.toml` before its other items, after git, and an unreadable file or an invalid key makes it exit 2 and name the file and the key. doctor starts through the same `devctl` shim as the hook, so a uv or Python failure that breaks the hook stops doctor too (section 4). `rs-lead` and `rs-preflight` run the full `./devctl doctor` first ([Spec 2](2026-10-16-delivery-skills-design.md), [Spec 3](2026-10-16-metrics-and-gardening-design.md)). A full run also starts the Roster's sign-in probes, which spend a little quota and, for agy, start agy inside the Session. The seeded root AGENTS.md therefore asks every other Session, such as a Worker's or a Reviewer's, to run `./devctl doctor --settings` first: it reads and validates only the settings files, spends no quota and starts no probe, agy's included.

| Area | Item | ok when |
| --- | --- | --- |
| toolchain | git | git 2.31 or later |
| toolchain | uv, gh | On `PATH` |
| toolchain | node, npm (plan 6) | On `PATH` when the repository has a TypeScript stack, at the Node.js major version its `package.json` names |
| toolchain | gh sign-in | `gh auth status` succeeds |
| toolchain | gitleaks | Version 8.30.1, which `devctl check` pins |
| toolchain | Each Harness the Roster names | Installed and signed in (below) |
| guardrails | `core.hooksPath` | Set to `.githooks` |
| guardrails | CI | The workflow has a job named `devctl check` |
| guardrails | Python floor | The settings of section 4 are present (Python stack) |
| guardrails | TypeScript floor (plan 6) | The settings of section 4 are present, read from `tsconfig.json` and from `eslint --print-config` (TypeScript stack) |
| guardrails | devctl exclusions | `tools/devctl` is excluded from the project's Ruff, mypy, pytest and uv workspace |
| guardrails | Harness wiring (plan 5) | Each of the three wiring files runs `devctl hook` for its events |
| kit | Kit files | The `rapid-ship status` summary has nothing missing |
| github | ruleset | An active ruleset on the default branch matches section 8 for the current Mode and Agent identity |
| github | CODEOWNERS | Matches the Mode and names `[github] code_owner`: the `*` line when `every_pr = true`, the Protected set otherwise |
| github | delete branch on merge | On |
| github | fork PR workflow approval | A public repository requires approval for workflows from all outside contributors |
| agent identity | Worker App, Reviewer App installation | Only with Agent identity on: installed on this repository with exactly the permissions of section 3 |
| agent identity | Worker App, Reviewer App key | Only with Agent identity on: the Keychain item exists and mints a token. Minting changes nothing in the repository |

- **Sign-ins:** Claude Code and Codex CLI report their sign-in through `claude auth status --json` and `codex login status`. agy has no status command, so doctor starts a new headless Session on the cheapest model, sends `hi`, and counts a non-empty reply as signed in; agy's exit code alone proves nothing, and a service error is unknown, not missing. From plan 5, a Roster Harness without a built-in check is probed the same way through its `command`, on the Roster's model. doctor splits the command with shell rules and passes `{prompt}` and `{model}` as single arguments, never through a shell. Any sign-in method is ok: a subscription, an API key or a gateway is the owner's choice of Provider. doctor passes each tool the owner's sign-in and proxy variables, and never reads a token file.
- **GitHub Free private repositories** have no rulesets. GitHub refuses the read with a plan-limit message, and doctor reports the ruleset as missing with that reason. There the merge guard is the enforcement (section 4).
- **The code owner:** doctor reads it from `[github] code_owner`, never from the repository's owner, so a repository that an organisation owns, whose CODEOWNERS names a person or a team, can pass. While `code_owner` is unset, doctor reports the CODEOWNERS item as missing and names the key. Plan 4 as built took the code owner from the repository's owner, which on an organisation-owned repository asks for `* @<organisation>`, not a valid code owner; its follow-ups change that.
- **Removed:** the issue-tracking item, and every App item while Agent identity is off.

`devctl doctor --skills` also checks what each Harness's Session would see. For each Harness the Roster names, or without a Roster for each of `claude`, `codex` and `agy` that is on `PATH`, it adds a temporary detached worktree at `HEAD` in a temporary directory, starts one new headless Session there on the cheapest model, and asks which skills it can load. A Kit or project skill the Session does not list is missing. A user-invoked skill (`disable-model-invocation: true`) is reported as not checked, because a Harness may leave it out of its list. Skills the Session sees from outside the repository, such as the owner's own skills or plugins, are listed for the owner to judge. The worktree is removed afterwards, whatever the Session did. Each probe uses a little quota. `rs-setup` runs it, and the owner reruns it after adding a skill or upgrading a Harness. From plan 5, a Roster Harness without a built-in probe is asked through its `command`.

The agy probes start agy as a child of whatever runs doctor. When an agent runs doctor from another Harness's Session, that is the use Google's consumer terms do not support; `rs-setup` warns about it (section 8), and so do `rs-lead` and `rs-preflight`. `./devctl doctor --settings` starts no probe.

### Agent identity and `devctl as`

Agent identity is optional ([ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md)). It is on when `[github]` records both Apps (section 4). Agents then make their GitHub writes through one thin command, which runs `gh` or `git push` with an App's short-lived token. It runs only when an agent calls it, never as a step that rapid-ship drives. Its interface:

```text
./devctl as worker push
./devctl as worker gh <gh arguments>
./devctl as reviewer gh <gh arguments>
```

- **Off:** while Agent identity is off, `devctl as` exits 2 and says how to turn it on.
- **`push`:** pushes the current branch to the branch of the same name on GitHub, as the Worker App. It takes no other arguments and never forces, so a non-fast-forward push fails; the agent merges the base branch rather than rewriting history. It refuses a detached `HEAD` and the default branch, and refuses `devctl as reviewer push`.
- **`gh`:** runs `gh` with the given arguments as the role's App. The first argument must be `pr`, `issue` or `api`; any other is refused, because `gh auth` can print the token and `gh alias` or `gh extension` can run other code with it. `gh pr merge --admin` is refused.
- **Exit codes:** 1 when devctl refuses; 2 when it cannot mint a token or start the tool, or when the tool timed out or printed more than devctl keeps, because devctl cannot then show its whole answer; otherwise the exit code of `gh` or `git`.
- **Merges:** `./devctl as worker gh pr merge` is a merge like any other, so the merge guard checks it first. G3 denies the other forms it recognises when they run through `./devctl as <role> gh`, such as a merge or a write to the default branch's ref through `gh api` (section 4).
- **Workflows:** neither App has the Workflows permission, so GitHub refuses an App's push that changes `.github/workflows/`. The owner pushes such a change, which is in the Protected set anyway.

Each run mints its own token and holds it only in memory:

1. Read the App's private key from the Keychain with `security find-generic-password -s rapid-ship/<role>-app/<App ID> -w`, where the App ID is the role's in `[github]`.
2. Sign a JWT and request an installation token restricted to this one repository and the App's named permissions. REST calls go through a small `http.client` wrapper that never follows a redirect.
3. Give `gh` the token only through `GH_TOKEN`, with `GH_REPO` set to the repository, in that one child's environment. Give `git push` the token only through a `GIT_ASKPASS` helper that reads it from that one git command's environment, with every configured credential helper and repository hook switched off for that command.

No key or token is written to disk, put on a command line or printed. An item that `security` wrote trusts `security` itself, so reads show no dialog, and any process the owner runs can read both keys. A Worker can therefore reach the Reviewer App; `rs-work` tells Workers never to act as it, and no technical barrier is planned until misuse is observed. With Agent identity on, the Harness guardrails deny `git push` and `gh` writes made as the owner (G7, G8).

### `devctl hook`

`devctl hook <harness> pre-tool` is the one implementation of the Harness guardrails (section 4). `<harness>` is `claude`, `codex` or `agy`, the Harnesses with wiring. It reads the Harness's event JSON on stdin and answers in that Harness's hook protocol. It applies G1 to G5 and the merge guard, and G7 and G8 when Agent identity is on. It reads `.github/CODEOWNERS` and `.rapid-ship/project.toml` from the repository, reads GitHub only for `gh pr merge`, reads the default branch's name from local git only for G3's `git push` and ref forms, and changes nothing.

## 7. Skills in the Kit

The Kit ships nine skills from `rs-setup` to `rs-preflight`, the engineering skills, and one optional skill, `rs-contribute`. Every Kit skill's name starts with `rs-`, which avoids collisions with Harness built-in commands and with an installed upstream plugin.

| Skill | Spec | Built in | What it does |
| --- | --- | --- | --- |
| `rs-setup` | 1 | plan 7 | Sets up a new repository or adopts an existing one (section 8) |
| `rs-health` | 1 | plan 7 | Audits a repository and returns a standards milestone (section 9) |
| `rs-design` | 2 | Spec 2's plan | Interviews the owner; writes feature designs, ADRs and ARCHITECTURE.md |
| `rs-breakdown` | 2 | Spec 2's plan | Turns a design into milestones, epics, stories and tasks in the tracker |
| `rs-lead` | 2 | Spec 2's plan | Builds the Lead brief, triages review findings and helps the owner fly |
| `rs-work` | 2 | Spec 2's plan | How a Worker meets the bar on one task |
| `rs-review` | 2 | Spec 2's plan | How a Reviewer judges one change |
| `rs-garden` | 3 | Spec 3's plan | Records Corrections and finds drift |
| `rs-preflight` | 3 | Spec 3's plan | Reviews with the owner whether the project is ready to widen the Mode toward Flight: the metrics to watch, Alarms and incident integrations, scheduled gardening, the escalation list, Agent identity and the ruleset. It is advisory and never gates |
| `rs-contribute` | 1 | plan 7 | Optional: sends a Kit fix back to rapid-ship |

`rs-work` and `rs-review` must work for an agent: the Lead starts a subagent with them or follows them itself. People rarely run them, but must be able to read them. There is no metrics skill: `rs-setup` records the Suggested thresholds, `rs-preflight` guides the owner through the metrics to watch before Flight, and project-defined metrics are documented in Spec 3.

### Engineering skills

The engineering skills carry rung 3 for every task. Spec 1 owns them, and plan 7 builds them.

| Skill | Source |
| --- | --- |
| `rs-tdd` | Upstream `tdd`, near verbatim |
| `rs-diagnosing-bugs` | Upstream `diagnosing-bugs`, near verbatim |
| `rs-codebase-design` | Upstream `codebase-design`, verbatim |
| `rs-pr` | Upstream `pr`; its Evidence adds the commands run and `Not covered:`. It carries the HumanLayer credit |
| `rs-writing-for-agents` | Upstream `writing-for-agents`, verbatim |
| `rs-writing` | This repository's `writing.md` |
| `rs-ponytail` | This repository's `ponytail.md` |

The forked skills come from mattpocock/skills (MIT), pinned at `49dd158`, and stay as close to upstream as rapid-ship allows. Each forked skill directory carries the upstream licence notice. This repository's upstream lock records, for each upstream file, its path, upstream commit, upstream blob SHA and status, `verbatim` or `patched`. A test requires `verbatim` files to match their blob SHA, and `patched` files to differ only inside marked rapid-ship sections. The seeded root AGENTS.md already names `rs-writing` and `rs-ponytail`. When the Kit skills land, `rapid-ship-engineering` is deleted and this repository's root AGENTS.md points to them.

[Spec 2](2026-10-16-delivery-skills-design.md) says which upstream skills `rs-design` and `rs-breakdown` draw on.

### `rs-contribute`

`rs-contribute` sends a Kit fix from a project back to rapid-ship. It is user-invoked and installed only when the owner opts in at Setup, through `[kit] optional`.

1. Describe the problem with the evidence that shows it: the command, the output and the Kit file involved.
2. Map the project file to its template through the lock.
3. Search rapid-ship's open issues and PRs for a duplicate.
4. In a cached fork of rapid-ship, fix the template and refresh the vendored copy with `rapid-ship sync --in-place`.
5. Run rapid-ship's own `./devctl check`.
6. Push the fix to the fork and open a PR to rapid-ship. Leave out project code, secrets and private paths. If the fix is unclear, open an issue instead. With Agent identity on, the guardrails may deny the agent's `git push` and `gh` writes (G7, G8), and a `devctl as` token reaches only the project's repository. The owner then pushes and opens the PR or issue in a terminal, as in `rs-setup` step 14.

A project may apply the same change to its vendored copy at once. When the fix ships, the next `rapid-ship sync` finds the file equal to the new template and keeps it managed. If a sync ran in between, the file became the project's own (section 3), and `rapid-ship sync --revert <path>` gives it back.

## 8. `rs-setup`

`rs-setup` is user-invoked. The owner runs it in their Harness Session on the `rapid-ship/init` branch, after `init` committed the Kit there with the stacks the owner confirmed (section 3). Before each write outside the repository, such as a GitHub setting, an App, the tracker or the owner's own Harness settings, it states the write and waits for the owner's yes. Before retrying a write whose result is uncertain, it re-reads the outside state. It records each gap it cannot resolve in the Setup PR's body. When a step fails, `rs-setup` explains the problem and the fix and offers to make the fix, rather than stopping with a bare error. It still stops at the first failure and shows the failing command's own output.

### Steps

1. **New or existing.** A repository with source beyond the Kit is existing. Read the stacks and directories that `init` recorded in `project.toml` (plan 6). The owner confirmed them before `init` wrote them (section 3), so do not ask again.
2. **Documents.**
   - New: ask the owner what the project does, for whom and how it runs. Fill in README.md, the root AGENTS.md's first paragraph, and ARCHITECTURE.md's purpose and context. Its parts wait for `rs-design`.
   - Existing: `init` skipped the README.md, ARCHITECTURE.md, AGENTS.md and CLAUDE.md that already exist. Merge the skeleton's sections into them from what the code shows, keeping the project's own text, and add a guide for each maintained directory that the `map` step reports. What the code does not show becomes a gap for `rs-health`.
3. **Patterns.**
   - New: walk the owner through the starter Patterns that `init` seeded with the skeleton, and adapt each one, its reference and its Lessons, to the project. Agree any further Patterns, such as how a domain object is stored. For each, write the Pattern file, a minimal reference implementation and its enforcing check. When the reference needs real product code, record the Pattern as a task for the first milestone instead.
   - Existing: offer each starter Pattern as a task. `rs-health` proposes its reference from the project's own code.
4. **Checks.**
   1. Confirm gitleaks 8.30.1 with `gitleaks version`, and for a TypeScript stack Node.js and npm; if one is missing, ask the owner to install it.
   2. New project: run `uv sync`, and `npm install` in each TypeScript stack's directory, which writes its lock. Then run `./devctl check`. The seeded skeleton passes.
   3. Existing project: devctl's checks can overlap or conflict with the project's own linters, hooks and CI, and the owner decides how to combine them. Exclude `tools/devctl` from the project's lint, type, test and uv workspace settings. Show each overlap or conflict with the settings, hooks and workflows that `init` listed, such as hooks in `.git/hooks` that `core.hooksPath` would stop running, and offer to fold them into `devctl_project`. Leave the project's own tool settings as they are in the Setup PR; step 15 offers the rules they lack. Warn about duplicate checks, which are harmless, and about checks that race, such as two hooks writing the same files, which are harmful. Never block on either.
   4. Existing suppressions: for each one the `exceptions` step reports, add its `rs-exception` marker and an entry with the reason "Existed at Setup on <date>" and the removal condition "Remove when this code next changes". Repeat `./devctl check --tier fast` until the step passes. The owner reviews the entries in the Setup PR.
   5. Run `git config core.hooksPath .githooks`. In an existing project, run it only after the owner has decided how to combine the existing hooks.
   6. Run `./devctl check` until it passes.
5. **Harness guardrails.** Show the owner the rules of section 4, the merge guard included, and say which Harnesses the Kit wires and which of them are confirmed. Where `init` skipped an existing `.claude/settings.json`, `.codex/hooks.json` or `.agents/hooks.json`, merge the Kit's entries into it. For Codex, the owner trusts the project and reviews its hooks in `/hooks`.
6. **Sandbox (an offer, not a default).** Explain that a sandbox confines the owner's own Session and every subagent it starts, because subagents inherit it. It is defense in depth, and it needs network access for git, gh, uv, the package index and the tracker. If the owner accepts, write the setting into the owner's own uncommitted settings for their Harness, such as Claude Code's `.claude/settings.local.json`, Codex's `sandbox_mode` in the owner's Codex configuration, or agy's terminal sandbox setting. agy's terminal sandbox has no network by default, so a CLI started inside it cannot reach its Provider. Never commit sandbox settings.
7. **GitHub.**
   1. Find the repository, or create it with `gh` after the owner confirms its visibility.
   2. After the owner confirms, apply the ruleset from the skill's `ruleset.json` with `gh api`, and turn on automatic deletion of head branches. The ruleset targets the default branch (`~DEFAULT_BRANCH`). Its `pull_request` rule requires code-owner review, dismisses approvals when new commits arrive, requires the most recent push to be approved by someone other than its pusher, requires every review thread to be resolved, and allows squash merges only (`allowed_merge_methods: ["squash"]`). It requires the status check `devctl check` from GitHub Actions (`integration_id` 15368). It blocks force pushes and deletion. Its bypass list holds only the repository admin role (`actor_id` 5), in pull-request mode, so the owner can merge their own PRs.
   3. The required approval count is `1` until the live trial (section 10) settles it. With Agent identity in Flight, a PR outside the Protected set has no code owner, so unless the owner reviews it, its approval must come from the Reviewer App. If GitHub does not count that approval, the count becomes `0` and code-owner review stays required, so CODEOWNERS alone decides who must approve: the owner for every path in Walk, and for the Protected set in Flight.
   4. For a public repository, require approval for workflows from all outside contributors. If the default branch is neither `main` nor `master`, record a gap: CI push runs cover only those two names. On a GitHub Free private repository, record a gap: there are no rulesets, so GitHub itself requires neither rung 2 nor rung 4 before a merge. Tell the owner that the merge guard is the enforcement there: it rejects an agent's merge while `devctl check` has not passed, or when the PR touches the Protected set.
   5. Record the code owner in `[github] code_owner`: the owner's login, or in an organisation the person or team who approves agent PRs, such as `@acme/maintainers`. Write the Walk line, such as `* @octo`, into CODEOWNERS.
8. **Agent identity (opt-in).**
   1. Recommend from this table, which [ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) records. Agent identity matters most for a solo owner on GitHub Free with a public repository: GitHub enforces the ruleset there, the owner cannot approve a PR their own account opened, and every agent comment appears publicly as the owner's.

      | Setup | Agent identity | Why |
      | --- | --- | --- |
      | Solo owner, public repository or a paid plan | Recommended | It is the only way the owner can approve an agent's PR, because GitHub never lets a PR's author approve it, and GitHub then binds the Lead |
      | Solo owner, private repository on GitHub Free | Recommended, for real reviews and metrics | Reviewer verdicts become GitHub reviews and agent PRs become countable. There is no ruleset, so the merge guard holds the bar with or without it |
      | Team | Optional | Teammates approve agent PRs anyway. The Apps add per-agent metrics, real Reviewer reviews and a Lead that CODEOWNERS binds in Flight |

   2. Explain the trade-off that ADR 0002 records: the four things Agent identity buys, and its cost of two Apps, private keys in the macOS Keychain, and agents writing to GitHub only through `devctl as`.
   3. In a team, each repository owner, a personal account or an organisation, has one Worker App and one Reviewer App. In an organisation, an organisation admin runs `rapid-ship app` once, which creates both Apps through the organisation manifest flow (section 3). Each developer holds their own private key for each App, since GitHub allows up to 25 keys per App, and keeps it in their own Keychain under an item named for the App's ID, so one person's key can be revoked alone. For an organisation's Apps, the admin makes each developer an App manager of both, and each generates their own key and imports it with `rapid-ship app --import-key`; whether an App manager may generate a key is not yet verified (section 11). For Apps a personal account owns, the account owner generates one key for each collaborator and hands it over securely, or moves the Apps to an organisation. A pair of Apps for each developer is rejected: it multiplies installations and splits one role's reviews across identities.
   4. Ask whether the owner opts in.
   5. If so, run `uvx rapid-ship app`, which creates the Apps that the repository's owner lacks; in an organisation an admin runs it. Where the Apps exist, the developer imports their own key instead (step 3). The owner installs both Apps, `rs-setup` records each App's ID and slug in `[github]`, and `./devctl doctor` then confirms each installation and key.
   6. If not, explain which metrics will report "unknown: needs Agent identity", and that agents then act as the owner, so Walk rests on the Lead brief. Flight then needs the ruleset to drop its review requirement, while the merge guard still keeps agents from merging a Protected-set PR.
9. **Escalation list and Roster.** The seeded `[escalation]` table is Walk, with two default kinds and `revision_rounds = 3`. In Walk the owner launches the Sessions and watches them, with the Workers they start; rapid-ship takes no notice of how many run, and advises running at most 3 Workers at once, for the owner's cognitive load. Ask whether the owner uses more than one Provider. If so, record the Roster with exact model IDs and a `command` for any Harness without a built-in route, and recommend a Reviewer from a different Provider than the Worker. `rs-lead` maintains both later.
10. **Tracker.** Ask which tracker the owner uses, confirm that their Harness can reach it through an MCP server or a CLI, and record it in `[tracker]`. Spec 2's plan adds this step.
11. **Metrics.** Show the default Suggested thresholds and record the owner's values in `metrics.toml`. Offer the scheduled metrics Action. Explain that the owner sets up Alarms and incident integrations, which differ from project to project, that an Alarm plugs in as a project-defined metric, and that `rs-preflight` guides that setup before Flight (Spec 3). Spec 3's plan adds this step.
12. **Contributing back.** Offer `rs-contribute`. If the owner accepts, add it to `[kit] optional` and run `uvx rapid-ship sync --in-place`.
13. **Doctor.** Run `./devctl doctor --skills`, then resolve or record each gap. The probes include agy when the Roster names it, or when there is no Roster and `agy` is on `PATH`. When they include agy and `rs-setup` itself runs inside another Harness, the agy probes would run agy inside that Session, which Google's consumer terms do not support; say so first, and offer that the owner run `./devctl doctor --skills` in a terminal instead.
14. **Setup PR.** Commit, then push `rapid-ship/init` and open the PR under the owner's sign-in: the branch adds `.github/workflows/`, which neither App may push. With Agent identity on, the guardrails may deny the agent's `git push`; the owner then runs the push and `gh pr create` in a terminal. The owner merges the PR.
15. **Tool-settings PR** (existing repositories). After the Setup PR, compare the project's own tool settings, for its linters, type checkers and formatters, with the Kit's for each stack. Leave out purely stylistic differences, such as line width, quote style and indentation; `rs-setup`'s references list the stylistic options of each tool. Show the owner each remaining rule with what it catches, including Ruff's ASYNC and FAST families where asyncio or FastAPI is used, and let the owner pick. Open a separate PR from `origin/<default branch>` that merges the picked rules into the project's settings, keeping the project's own choices, and runs the linters. Fix what they report within the diff cap. A rule whose findings do not fit leaves the PR and becomes a task for `rs-health`'s standards milestone. The settings are Protected, so the owner reviews and merges the PR.
16. **Next.** For an existing repository, offer `rs-health`. For a new one, point to `rs-design`, then `rs-breakdown`, then `rs-lead`. Before the owner widens the Mode toward Flight, point to `rs-preflight` (Spec 3).

## 9. `rs-health`

`rs-health` is user-invoked. `rs-setup` offers it to existing repositories, and the owner can rerun it at any time. It never edits the repository: its output is a standards milestone that a Lead works through like any other milestone.

- **Reads:** the code; the output of `./devctl doctor` and `./devctl check`; the CI configuration and recent runs; README.md, ARCHITECTURE.md and the AGENTS.md tree; the feature map, the Patterns and `exceptions.toml`; and the last merged PRs with their review threads.
- **Audits** by rung, citing file:line or command output for every finding:
  - rung 1: recurring tasks done several ways, each with one proposed reference implementation and the check that would enforce it; safe interfaces that are missing and the bypasses they would ban; code that departs from an existing Pattern, the starter Patterns included; and code that hides or obscures an error, such as an empty catch, a broad except that carries on, an unhandled promise or a fallback that masks a failure. Failing fast and gracefully, and never obscuring an error, is the audit's base rule, which `rs-garden` also scans for (Spec 3);
  - rung 2: missing checks and test tiers, doctor gaps, Python floor settings the project's own rules replace, advisory Rules that a check could enforce, exceptions whose removal condition has been met, settings entries that match nothing, such as a `[kit] exclude`, `[map] unguided` or `[tests] unit` entry, and tool-settings rules the project lacks (section 8, step 15);
  - rung 3: AGENTS.md, ARCHITECTURE.md and README.md text that no longer matches the code, missing directory guides, gaps in the feature map, and dead code;
  - rung 4: gaps in the Protected set, CODEOWNERS and the ruleset;
  - review comments repeated across recent PRs that a rung could prevent.
- **Returns** a standards milestone in `rs-breakdown`'s levels: one epic per area with findings, and tasks that each fit one PR within the diff cap, with acceptance criteria, a test plan and the tasks each is blocked by. The owner selects what to keep. `rs-health` writes only the selected items to the tracker, as Spec 2's mapping note describes.

The audit is shared with the gardener. `rs-health` runs it once at adoption; `rs-garden` (Spec 3) reruns it over the changes since its last pass and adds new Corrections. The audit lives in `rs-health`'s `references/audit.md`, which `rs-garden` reads.

## 10. Testing

**Unit tests**, offline. Plans 2 and 3 built the tests for the lock, `status`, `init`, `sync` and every check step. The new plans add:

- Plan 4: settings, with `[roster]` and `[escalation]` read, a partial App record or Apps without a repository refused, and the removed tables refused. doctor's parsers against recorded GitHub responses and fake Harness executables: a sign-in by any method is ok, the agy probe, the ruleset in Walk, in Flight with Agent identity and in Flight without it, CODEOWNERS against `every_pr`, App items only with Agent identity on, and `--skills` adding and removing its temporary worktree at `HEAD`. Token minting, the `GIT_ASKPASS` helper and `rapid-ship app` against a local fake HTTP server and a fake `security`; these are labelled simulated. `devctl as` with fake `gh` and `git` executables and a local bare repository: each refusal, the token present only in the one child's environment and never in argv or output, and the exit codes.
- Plan 4's follow-ups: `[github] code_owner`, and doctor's CODEOWNERS item with a login and with a team on an organisation-owned repository; `rapid-ship app`'s organisation manifest flow and `--import-key` against a local fake HTTP server and a fake `security`, labelled simulated; and Keychain items named by App ID, with two Apps' keys for one role on one machine.
- Plan 5: `devctl hook` against recorded event JSON for each Harness: each rule's deny or ask, a command list split on `;`, `&&`, `||` and `|`, G7 and G8 only with Agent identity on, no decision when no rule matches, G1 to G4 with unreadable settings, and the exit-code mapping. G3 denying `gh pr merge --admin` and each `gh api` form of section 4, REST and GraphQL, run directly and through `devctl as`, and each form of `git push` to the default branch, with `origin/HEAD` present and missing. The merge guard against a fake GitHub reader: `gh pr merge` run directly and through `devctl as`; passed, pending, failed and missing check runs; Protected paths at the base, renames by both paths, a ledger entry changed or removed, and entries added as `open` and as `implemented`, neither of them Protected; a merge without `--match-head-commit`, or naming another commit, denied with the exact retry; a denial when GitHub cannot be read or the guard itself fails; and no read for any other command. Map rule 5's `task` and Lessons, map rule 8, the `SKILL.md` rule, the diff cap's count, exclusions and declaration, and the ledger rule. The Python starter Patterns and the Python performance Pattern passing map rule 5 on a new project. Each seed held to its loader. The Roster's `command` and doctor's probes through it. `sync`'s migrations: detection, the second branch and PR, and `--in-place` writing none. doctor's wiring items.
- Plan 6: `[[stack]]` settings: names, directories inside the repository, duplicates, `agnostic` alone, and the old `stack` key. `init --stack NAME=DIRECTORY`, and detection without it: nested roots, skipped vendored and generated directories, no root found, and nothing written. Each stack's steps in its directory with their names, from fake tools; the TypeScript steps blocked without `node_modules`; `--install`. The TypeScript suppressions, the `eslint:` and `type:` references, removed Vitest tests and tautologies. CODEOWNERS and `project.toml` rendered for two stacks. doctor's Node.js and TypeScript floor items.
- Plan 7: the upstream lock (`verbatim` and `patched` files), every Kit skill through map rule 7, and `ruleset.json` passing doctor's ruleset check.

**Integration tests**, offline and labelled as such: `init` on scratch repositories for each stack, after which `./devctl check` passes; `sync --in-place` between two template versions, and `sync` proposing a migration in its own PR; and this repository's dog-food tests. From plan 6, `init` on a scratch repository with a Python `backend/` and a React TypeScript `frontend/`, after which `./devctl check` passes. That test needs network access for `npm ci` and is labelled so.

**Spikes and live trials**, recorded under `docs/trials/`:

- **The hook spike (backlog PRO-139),** plan 5's first task. In Claude Code, Codex and agy, each in a lead Session, inside a subagent and in a headless Session: whether the wired hook events fire, whether Codex hooks can ask, how each Harness treats the hook's exit 1, uv's exit 2, a hook timeout and the hook's deny answer, which fields each event carries, the review in Codex's `/hooks`, and the time a `devctl hook` run adds to each tool call, since each run starts uv and Python. The owner decides from the result; until then the guardrails are claimed for Claude Code only.
- `rapid-ship app` creating both Apps, then installing them on a second repository. On a test organisation: an admin creating the organisation's Apps, and a developer, made an App manager of both, generating a key and importing it with `--import-key`.
- Agent identity on a scratch repository: `devctl as worker push` and `devctl as worker gh pr create`; a review posted with `devctl as reviewer gh` that GitHub shows as the Reviewer App's; whether GitHub counts the Reviewer App's approval toward the ruleset's required approval (section 8, step 7); a squash merge with `devctl as worker gh pr merge`; and GitHub refusing a merge while a review thread is unresolved or `devctl check` has not passed.
- The ruleset applied and read back by doctor, and doctor's answer on a GitHub Free private repository.
- The Harness guardrails in each Harness that the spike confirmed: each deny rule and the ask rule, in the lead Session and inside a subagent. The merge guard on real PRs: it denies a merge while `devctl check` is pending or failing and a merge of a Protected-set PR, through `gh pr merge` and `devctl as worker gh pr merge`, and lets a passing, unprotected merge through; G3 denies a merge through `gh api` and a `git push` to the default branch.
- **The Roster under parallel subagents,** with Spec 2's plan, which builds `rs-lead`. A Claude Code Lead runs a dynamic workflow, or ultracode mode, that starts many background subagents in parallel, and a Codex Lead does the same with its parallel subagents. The trial checks only that every subagent started for coding work (`rs-work`) or for a review (`rs-review`) runs on the Harness and model that the Roster names. Other subagents are not checked ([Spec 2](2026-10-16-delivery-skills-design.md)).
- `rs-setup` on a new scratch repository with a Python `backend/` and a React TypeScript `frontend/`, and on an existing one, hello-rapid-ship, including `doctor --skills` for each Harness and the tool-settings PR.
- `rs-health` on an existing repository, ending with a standards milestone in the tracker.

**Dog-food:** this repository's CI runs `./devctl check --tier full`, whose `vendored` step runs `rapid-ship status --strict`.

## 11. Questions

The owner's reviews of PR #27 on 2026-10-16 and 2026-10-19 settled what this spec states. The questions still open follow.

### Open

To be settled by a spike, a trial or the owner. No drafter proposal is waiting.

- **Codex and agy hooks.** Whether their hooks fire, can ask, fire inside subagents and headless Sessions, and how they treat exit 1, uv's exit 2 and a hook timeout. The PRO-139 spike settles it. Without ask, the Codex wiring omits G5.
- **The hook's cost.** Each `devctl hook` run starts uv and Python on every matched tool call. The spike measures it, and the owner decides from the result.
- **The ruleset's approval count with Agent identity in Flight:** `1` until plan 4's live trial, a pending Owner step, shows whether GitHub counts the Reviewer App's approval; otherwise `0` with code-owner review still required.
- **Several Agents for one role,** for example one per kind of task. The owner left it open; adopting it would extend `[roster]`.
- **Who may generate a shared App's key (PRO-105).** For an organisation's Apps, each developer generates their own key as an App manager of both Apps (section 3). GitHub documents that App managers manage an App's settings, but not that this includes generating its private keys. The organisation trial among plan 4's follow-ups settles it; if App managers cannot, the organisation admin generates one key for each developer and hands it over securely.
