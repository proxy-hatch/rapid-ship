# Spec 1: Kit and Setup

**Status:** revised on 2026-10-16 for the team-management boundary ([ADR 0004](../../adr/0004-team-management-boundary.md)), on 2026-10-19 for the owner's second review of the design PR, on 2026-10-20 for the owner's decisions to descope running agents across several Providers, to ship the Harness guardrail wiring for Claude Code first and to probe Claude Code alone in `doctor --skills`, and on 2026-10-22 for the hook spike's result, the owner's decisions on it and `devctl hook` as plan 5's PR 5.2 built it, on 2026-10-23 for the standards as its PR 5.3 built them, and on 2026-10-25 for the documented settings as its PR 5.4 built them, for the owner's comment rule, which the root guide seeds as Rules and which narrows the seeds' comments to each key's contract, for the owner's decisions of that day on the `dead-code` check step (section 5), and for the owner's decision that the Kit keeps no backward compatibility before GA, which drops `sync`'s migrations and the warning periods of the map rules, the `dead-code` step and the dead-code tools' suppressions, and on 2026-10-26 for the same decision's removal of `rapid-ship app`'s support for Keychain items named without the App ID, for the owner's ruling that the map rules read tracked files only (sections 5 and 8), and for the owner's descope of that day: Spec 2's delivery skills will not be built and its document is deleted, so the owner starts and manages their own Sessions (section 1). `[escalation]` keeps only `every_pr`, the merge guard enforces each Mode, and the seeded root guide gains a Pull requests section instead of a review skill (section 4). `rs-setup` loses its tracker step (section 8), `rs-health` returns proposed tasks (section 9), and GA, which now includes Spec 3, follows Spec 3's build (section 3). Plans 1 to 4 are built and merged, plan 4 in PRs #31 to #33 with its follow-ups, which support organisation-owned repositories, remove the `[roster]` table from devctl and narrow `doctor --skills` to Claude Code. The owner tagged the first release, `v0.1.0`, at `0e1d6d0`. Plan 5 is built in PRs 5.1 to 5.5, and plans 6 and 7 are planned in the [plan index](../plans/2026-10-14-kit-and-setup.md). Of plan 5, the hook spike is recorded in [its trial record](../../trials/2026-10-21-hook-spike.md), and PR 5.2 builds `devctl hook`, the merge guard and the Claude Code wiring, whose live trial ran on 2026-10-23 and is recorded in [its trial record](../../trials/2026-10-23-harness-guardrails.md). PR 5.3 builds the README.md and ARCHITECTURE.md seeds with map rule 8, `doctor --settings`, the Pattern `task` key and Lessons section with the Python starter Patterns, the `SKILL.md` rule, the diff cap, the ledger rule and one CI concurrency group for each push run. PR 5.4 builds the seeds' comments on each key's contract and the loaders' errors that name what each key accepts, and makes plan 5's new map rules fail at once (sections 3 and 5). PR 5.5 builds the `dead-code` step for Python, and plan 6 builds it for TypeScript (section 5). This is the first of the two specs in the [rapid-ship design](2026-10-14-rapid-ship-design.md), beside [Spec 3](2026-10-16-metrics-and-gardening-design.md), and its terms follow `GLOSSARY.md` at the repository root. [Section 11](#11-questions) lists what is still open.

## 1. Scope and outcome

When this spec is built, an owner has the agent in their Harness Session run `uvx rapid-ship init` in a new or existing repository, then runs the `rs-setup` skill in that Session, and ends with:

- the Kit vendored and recorded in its lock, with one or more stacks, each in its own directory: Python, TypeScript for React, or the stack-agnostic one;
- `devctl check` in the pre-commit hook and in CI as a required status check, and run by each agent before it opens a pull request (section 4, Root AGENTS.md skeleton);
- the Kit's Harness guardrails, with the merge guard, for Claude Code, and for Codex and agy only once the hook spike confirms their hooks and a follow-up wires them (section 4);
- README.md, ARCHITECTURE.md, the AGENTS.md tree, the feature map and the starter Patterns, each verified by `devctl check`;
- the ruleset and CODEOWNERS applied for Walk, and `devctl doctor` reporting no gap that the owner has not accepted;
- optionally, Agent identity: two GitHub Apps that agents act as through `devctl as`;
- Suggested thresholds recorded and, optionally, the scheduled metrics Action installed, both as [Spec 3](2026-10-16-metrics-and-gardening-design.md) defines them;
- for an existing repository, a separate PR that offers the tool-settings rules the project lacks, and proposed standards tasks from `rs-health`, the ones the owner picks written to the tracker that the owner's Harness reaches.

This spec covers the `rapid-ship` command (section 3), the Kit's files (section 4), `devctl check` (section 5), devctl's other commands (section 6), the skills the Kit ships (section 7), and the skills `rs-setup` (section 8) and `rs-health` (section 9).

Out of scope:

- Skills that design, break down, lead, implement or review work. The owner descoped them, and Spec 2 with them, on 2026-10-26: the owner starts and manages their own Sessions, which follow the seeded AGENTS.md and the engineering skills (sections 4 and 7), while `devctl check`, the guardrails and the merge guard hold the bar.
- [Spec 3: Metrics and gardening](2026-10-16-metrics-and-gardening-design.md), which GA includes: `devctl metrics`, the scheduled metrics Action, Suggested thresholds and where they are recorded, project-defined metrics, the Corrections ledger, `rs-garden`, and `rs-preflight`, the advisory Pre-flight review before the owner widens the Mode toward Flight. `rs-garden` reruns the audit that section 9 defines.
- Anything that starts an agent Session to do work, watches or resumes one, or pushes, reviews or merges as a step in a flow ([ADR 0004](../../adr/0004-team-management-boundary.md)).
- Running agents across several Provider subscriptions, which is outside rapid-ship's goal of accelerating software delivery while holding the code-quality bar; agent control surfaces such as [T3 Code](https://github.com/pingdotgg/t3code) do it.

rapid-ship works with GitHub today, through `gh` and GitHub's rulesets. Other Git hosts, such as Bitbucket, may follow if owners ask for them or contribute them. rapid-ship works with any issue tracker that the owner's Harness can reach through an MCP server or a CLI, and devctl never talks to the tracker. The owner's machine must run macOS for now: Agent identity keeps its App keys in the macOS Keychain, and on Windows git can check the skill links out as plain files. `devctl check` also runs on Linux, as CI does.

### Dog-fooding

*This paragraph describes this repository's own configuration, not product behaviour.* rapid-ship vendors its own Kit (section 3) and is validated on itself and on its sample project, hello-rapid-ship. Its tracker is Linear. Its agents sign in with vendor subscriptions only, and agy is never a Reviewer here. This repository records these choices as rules in its root AGENTS.md; no Kit file enforces them. It is also a public repository on GitHub Free with one owner, the setup where Agent identity matters most, so PR #33 turns Agent identity on. The owner created its Worker and Reviewer Apps with `rapid-ship app` on 2026-10-19 and installed both on this repository, and #33 records them in `[github]` ([plan 4](../plans/2026-10-14-kit-and-setup.md#plan-4-doctor-and-agent-identity), follow-up 6). The owner's Keychain holds their keys in the items named by App ID (section 3).

## 2. Removing the old controller

Built in plan 1. The last commit that contains the controller is tagged `archive/controller-2026-10` (`f7b877b`).

1. The controller code and its tests were deleted: `rapid_ship/execution/`, `rapid_ship/trust/` and `rapid_ship/project/`; the old `cli.py`, `models.py`, `storage.py`, `logs.py`, `protocol_json.py`, `metrics.py`, `github_metrics.py` and templates; the root controller `devctl` with its build and smoke scripts; the `tests/typecheck_*.py` fixtures; and `examples/`.
2. `rapid_ship/files.py` stayed. `rapid_ship/process.py` moved into devctl in plan 3. The console script is `rapid-ship`.
3. The `rapid-ship` and `rapid-ship-improve` skills were deleted. `rapid-ship-engineering` stays until plan 7's Kit skills replace it; the optional `rs-contribute` replaces `rapid-ship-improve`.
4. The controller-era records and guides left the current documentation. Only `docs/getting-started.md` remains, with a "Historical" line under its title. The tag [`archive/controller-2026-10`](https://github.com/proxy-hatch/rapid-ship/tree/archive/controller-2026-10) keeps the deleted records and guides.
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

`uvx` fetches the package from a git tag of this repository: `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<version> rapid-ship <command>`. Each Kit release is a tag `v<version>` on `main`, created by the owner, and the Kit version is the package version. The first, `v0.1.0`, is tagged at `0e1d6d0`. For a version that has no tag yet, run `uvx --from <local checkout> rapid-ship <command>`. Publishing to PyPI waits until the Kit settles. This spec writes `uvx rapid-ship` for short.

`rapid-ship` has four commands. `init`, `status` and `sync` are built (plan 2). `app` belongs to Agent identity and is built in plan 4. `rs-setup` marks an existing project's suppressions itself (section 8). Every command exits 0 on success, 1 when a check failed or the repository's state refused the request, and 2 when it could not run.

Both CLIs prefer guided rectifying to a bare exit. Each refusal and error names the problem, what it blocks and the next step, such as the command to run. A command still fails fast and gracefully: it stops at the first error and shows the underlying cause, such as git's own message, and never hides or rewords it.

### `rapid-ship init`

1. **Preconditions:** the current directory is inside a git work tree with a clean status, with no `.rapid-ship/kit.lock` and no branch `rapid-ship/init`. `init` installs at the top of the work tree, even when run from a subdirectory. A stack can live in a subdirectory (step 2). When the work tree is not clean, `init` writes nothing and exits 1. It lists the uncommitted and untracked paths, at most 20 and then how many more, and says that `rs-setup` can help commit or stash them before `init` runs again.
2. **Stacks:** a stack is `python`, `typescript` or `agnostic`, and it lives in one directory of the repository. As built, a repository with `pyproject.toml` gets the `python` stack; otherwise `init` needs `--stack python` or `--stack agnostic`, and without either it exits 2. A repository has one stack, at its root. Plan 6 adds the TypeScript stack and several stacks: `--stack NAME[=DIRECTORY]`, repeatable, names each stack and its directory, which defaults to the root. `agnostic` cannot sit beside another stack.
   - **Detection (plan 6):** without `--stack`, `init` searches the repository recursively for stack roots, at any depth. It skips vendored and generated directories, such as `node_modules`, `.venv`, `dist` and `build`. A directory with `pyproject.toml` is a `python` root, and one with `package.json` and `tsconfig.json` is a `typescript` root.
   - **Never a silent guess:** `init` proposes what it found and writes nothing. It prints each root and the `--stack` options that name them, such as `--stack python=backend --stack typescript=frontend`, and exits 2. When it finds no root, it asks for `--stack`, which can name `agnostic`.
   - **Confirmation:** the agent that runs `init` in the owner's Session, before the owner runs `rs-setup` there, confirms the stack roots with the owner. When detection is unclear, it asks the owner for them. It then reruns `init` with them as `--stack NAME=DIRECTORY`. `rs-setup` does not exist until `init` writes it, so the proposal that `init` prints carries these instructions. An owner who runs `init` in a terminal follows the same proposal.
3. **Variables:** `--owner`, `--repository`, `--name` and `--package` fill the template variables. The project name defaults to the GitHub repository name, from `--repository` or the `origin` remote, then to the main checkout's directory name. Without `--owner`, CODEOWNERS names `<owner>` with its line commented out, and `rs-setup` writes the code owner (section 8, step 7).
4. **Plan the writes.** Each Kit file is managed (`sync` updates it later) or seeded (written once, then owned by the project). Section 4 lists both kinds.
5. **Conflicts:** if any managed file already exists, `init` writes nothing, lists the conflicts and exits 1. If a seeded file exists, even as a symlink, `init` skips it and lists it for `rs-setup` to merge. For a tool settings file, `rs-setup` also offers the rules it lacks in a separate PR at the end of Setup (section 8, step 14).
6. **List existing checks:** before writing, `init` collects the tool settings, hooks and workflows already in the repository: Ruff, mypy, pytest, flake8, pylint, isort and Black settings, `.pre-commit-config.yaml`, Husky and lefthook files, a configured `core.hooksPath`, executable hooks in git's hooks directory, and workflows in `.github/workflows/`. It reads them without running project code or a hook, and lists an unreadable file as unreadable. Plan 6 adds ESLint, Prettier, Biome, `tsconfig.json`, Vitest and Jest settings.
7. **Write and commit:** it creates the branch `rapid-ship/init` at `HEAD` and switches to it, from any branch, the default branch included, or from a detached `HEAD`. It writes with the safe-path helpers (never outside the repository, never through a symlink, never over an existing file), and commits exactly the created files and `.rapid-ship/kit.lock` with the message `chore: vendor the rapid-ship Kit <version>`. A repository with no commits gets the Kit as its first commit on the current branch. Every git command runs with `core.hooksPath=/dev/null`, so no git hook runs, not even one from a tracked hooks path such as husky's.
8. **Failure:** when the switch, a write, `git add` or `git commit` fails, for example without a git identity, `init` removes the files and directories it created and unstages them. It then returns to the starting branch or commit and deletes `rapid-ship/init`. The error includes git's message.
9. **Report:** it prints what it created and skipped, the existing checks, the branch and the commit, and the next step: open a PR from `rapid-ship/init`, which `rs-setup` does. For a repository that had no commits, it says that the Kit is its first commit.

`init` never edits an existing file, never runs project code and never runs a git hook, the Kit's own hooks included.

### `rapid-ship status`

Read-only. It compares the repository with the lock and the installed templates.

| Class | Meaning |
| --- | --- |
| unchanged | A managed file matches its locked hash |
| modified | A managed file differs from its locked hash. The next `sync` makes it the project's own unless it is reverted |
| missing | A managed file is absent. The next `sync` makes it the project's own unless it is reverted |
| template updated | A seeded file's template changed since it was seeded, or since the project made a managed file its own. The file itself is never compared |
| excluded | The project listed the path under `[kit] exclude` and owns it |
| outdated | A managed lock entry that the installed template no longer matches, or that the installed Kit dropped |
| not installed | A managed template of the installed Kit that the lock does not list yet, such as a file a newer Kit added |

Files not in the lock are the project's and are not reported. When `status` lists a modified or missing file, it also prints how to revert it: `rapid-ship sync --revert <path>`. `--strict` exits 1 unless every managed file that is not excluded is unchanged and current. A file that `sync` made the project's own has a seeded entry, so `--strict` no longer checks it. `--json` prints the report as data.

### `rapid-ship sync`

1. **Preconditions:** a clean work tree, unless `--in-place` is given. `--in-place` keeps uncommitted edits: it replaces only files equal to their locked content and makes the rest the project's own (step 4). `sync` compares template hashes, not version numbers; when nothing changed it says so and stops.
2. Without `--in-place`, it creates the branch `rapid-ship/kit-sync-<version>` at `HEAD`. It refuses a detached `HEAD` and an existing branch of that name.
3. It replaces each unchanged managed file with its new template, adds new managed files, including the optional skills listed under `[kit] optional`, and deletes unchanged managed files that the Kit dropped. It never creates, replaces, deletes or reports a path under `[kit] exclude`. A new managed template whose path already holds a different file that the lock does not list is a conflict: `sync` leaves the path alone, lists it and exits 1.
4. A managed file that the project edited to equal the new template stays managed; `sync` only updates the lock. Any other managed file that the project edited or deleted, or whose symlink target it changed, becomes the project's own: `sync` leaves it as it is, records it in the lock as seeded with the current template's hash, and lists it under a heading that says the project owns it now, with one line on how to give it back. An edited file that the Kit dropped keeps a seeded entry with its locked hash; a dropped file that is already gone leaves the lock.
5. `--revert <path>`, repeatable, gives a file back to the Kit: `sync` writes the current template over it and records it as managed again. It accepts a path whose current template is managed: a file the project owns after step 4, or a modified or missing managed file that this sync would otherwise make the project's own. Naming an unchanged managed file changes nothing. Any other path refuses the whole sync with exit 1 before anything is written, and the reason names the path: a path that is not a Kit file, a path under `[kit] exclude`, a seeded template, or a file the Kit dropped.
6. It never changes an existing seeded or project-authored file. It creates a seeded file that a newer Kit adds only where nothing exists at its path, and records the template either way. It lists seeded files whose template changed, including managed files the project made its own.
7. It updates the lock. Without `--in-place`, it commits, pushes the branch and opens a PR with `gh` under the owner's sign-in, and the owner merges the PR. As in `init`, no git hook runs. With `--in-place` it writes the work tree only. A failed write restores the work tree.

`sync` without `--in-place` is an owner command. Its push runs inside its own process, where the Harness guardrails cannot see it, so skills run `sync` only with `--in-place`.

**Kit changes to seeded content.** A Kit version can change what a seeded file must contain, such as a settings table that devctl no longer accepts, links that a new map rule requires, or Protected paths that CODEOWNERS must list. Before GA, the documentation release (plan 7's PR 7.4, which lands after Spec 3 is built), the Kit keeps no backward compatibility: the project updates its seeded files itself. `sync` does not edit a seeded file; it lists each one whose template changed (step 6), and `status` reports it as `template updated`. A check that requires the new content fails at once, with no warning first. devctl refuses the tables that plan 4 dropped, and its message says to delete the table (section 4). It refuses the `[escalation]` keys that the owner removed on 2026-10-26 as unknown keys (section 4). Map rules 5, 7 and 8 fail on files that an existing project already owns (section 5). So does the exceptions step on the dead-code tools' unmarked suppressions, and the `dead-code` step blocks a Python project whose `pyproject.toml` lacks its tools or vulture's `paths` (section 5). In Walk, the seeded Mode, no check requires a Protected path that a newer Kit adds to CODEOWNERS. G5, the merge guard and the `diff` step read the Protected set from CODEOWNERS's own lines (section 4), so they leave out such a path until the project adds its line. doctor's CODEOWNERS item reports the missing path only in Flight (section 6). The policy for after GA is designed then. The owner decided this on 2026-10-25, because rapid-ship has no consumers yet.

### `rapid-ship app`

Part of Agent identity (section 6); built in plan 4. Each repository owner, a personal account or an organisation, has two GitHub Apps. They belong to that account, not to one project: `app` creates each App that does not exist yet, then prints how to install both on the current repository. A private App installs only on its owner's repositories, so `app` creates the Apps on the account that owns the repository:

- **A personal account:** GitHub's manifest flow on the owner's own account. `app` exits 1 unless `gh` is signed in as that account.
- **An organisation:** GitHub's organisation manifest flow, at `https://github.com/organizations/<organisation>/settings/apps/new`, which an organisation admin runs once. When an App must be created and `gh`'s login is not an active admin of the organisation, `app` exits 1 and opens no browser. It says to ask an admin to run `rapid-ship app`, or, where the Apps exist, to record their IDs and import a key (step 4). The organisation's repositories then share both Apps, and each developer holds their own key (section 8, step 8).

For each role, `app` reads everything it needs before it changes anything, then uses the first of these:

- **The recorded App.** When `[github]` records the role's App for this repository, `app` uses it and never creates one. When this machine has no key for it, `app` exits 1 and names `--import-key` (step 4).
- **An App whose key this machine holds.** An App of the repository's owner, found by its Keychain item (step 2). `GET /apps/<slug>` with the owner's `gh` sign-in confirms a public App. GitHub answers 404 for any private App, even the owner's, so `GET /app` under a token that the item's key signs shows which account owns it. An App of another account is skipped. When no item holds a key of the owner's App, an item whose key GitHub refuses, or that cannot sign a token, stops the command with exit 1: `app` cannot tell whether that App exists, so it creates no second App beside it.
- **A new App,** through the manifest flow of step 1.

| App | Permissions | Used by |
| --- | --- | --- |
| Worker App | Contents, Pull requests and Issues: read and write. Metadata: read | `devctl as worker`: pushes, opens and merges PRs, comments |
| Reviewer App | Pull requests: read and write. Contents and Metadata: read | `devctl as reviewer`: posts reviews |

Neither App has the Workflows, Administration or Checks permission, and neither is a code owner, so an App's approval never stands in for the owner's.

1. To create an App, `app` runs GitHub's manifest flow. A local HTTP server on `127.0.0.1` opens the browser at a page that posts the manifest. The App is private and has no webhook. `app` exchanges GitHub's one-time code at `POST /app-manifests/{code}/conversions`.
2. It stores each private key in the macOS Keychain, by passing it to `security` on stdin, under an item whose name carries the role and the App's ID: `rapid-ship/<role>-app/<App ID>`, such as `rapid-ship/worker-app/5376519`. One machine can then hold the keys of several Apps, such as a developer's own and their organisation's. The item's account holds the App's ID, and its comment the slug. A key is never written to disk, put on a command line or printed. rapid-ship never replaces or deletes an existing Keychain item.
3. It prints each App's ID and slug, and the URL that installs it on the repository; `--repository OWNER/NAME` names another repository. The owner installs both Apps, and `rs-setup` records the IDs and slugs in `project.toml`.
4. Where the Apps already exist, such as an organisation's, a developer adds their own key. In an organisation, an admin generates one for each developer in each App's settings, under Credentials, Key pairs, New key, and hands it over securely. The developer runs `rapid-ship app --import-key {worker,reviewer}`. It reads the key on stdin, up to 64 KiB, and `GET /app` under a token that the key signs must show the ID and slug that `[github]` records. Only then does it store the key as step 2 does. It stores nothing and exits 1 when `[github]` records no App for the role, the Keychain item exists, stdin is a terminal or holds no unencrypted RSA PEM private key, or GitHub refuses the token or shows another App. No message echoes the input. GitHub's settings page downloads the key as a file, which rapid-ship never writes; it tells the developer to delete the download. Whether an App manager who is not an admin may generate a key is unverified (section 11).

### Who owns what

`sync` sorts every path into one of four groups, and respects the project's choices in each.

| Group | Examples | What `sync` does |
| --- | --- | --- |
| Language-agnostic Kit | devctl core, the `rs-` skills, the CI workflow, the pre-commit hook | Replaces unchanged files. A file the project edited or deleted becomes the project's own until `sync --revert` |
| Stack Kit | Each stack's guardrail seeds and check steps, under the stack's directory | The same; where a stack file and a common file share a path, the stack's wins |
| Project extensions | `tools/devctl/devctl_project/`, the project's own skills under `.agents/skills/`, extra workflows | Never touches them. Seeded files are reported when their template changes |
| Project overrides | A Kit path listed under `[kit] exclude` | Never touches it again |

Editing or deleting a managed Kit file makes it the project's own: the next `sync` records it as seeded, stops updating it and reports only later template changes (step 4), and `sync --revert <path>` gives it back (step 5). The seeded root `AGENTS.md` tells agents so. To change behaviour and keep Kit updates, a project uses `devctl_project` and its settings. A project that wants its own version of a Kit file, or none, lists it under `[kit] exclude`. Excluding a skill's directory also excludes its `.claude/skills` link. `[kit] exclude` is the only record of an exclusion: `status`, `sync`, `devctl check` and `devctl doctor` all read it there.

### Package layout

```text
rapid_ship/
  cli.py              # init, status, sync; app from plan 4
  files.py            # atomic_replace, safe_path, create_file
  github_app.py       # plan 4: rapid-ship app, which finds or creates the Apps and prints install URLs
  app_import.py       # plan 4: rapid-ship app --import-key
  app_flow.py         # plan 4: the manifest flows, and GitHub calls made as an App
  app_keychain.py     # plan 4: Keychain storage and item names
  kit/                # templates, lock, git, init, existing_checks, status, sync, writes, pull_request; stacks (plan 6)
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

An entry moves from managed to seeded when the project edits or deletes the file (`sync` step 4), and back to managed through `sync --revert` (step 5). A seeded entry's `template_sha256` is the hash of the template's content, or of a symlink template's target.

From plan 6 the lock records each stack and its directory as `[[stack]]` tables, as `project.toml` does, in place of `stack`. `rapid-ship` rewrites an older lock itself, since nobody else writes it.

### This repository's vendored Kit

*This repository's own development, not product behaviour.* This repository ran `init` on itself, so `devctl`, `tools/devctl/`, `.githooks/pre-commit`, `.github/workflows/devctl-check.yml` and `.rapid-ship/` come from its templates. `uv run rapid-ship sync --in-place` refreshes the vendored copy from the working-tree templates, so a template change and its vendored copy land in the same PR. Three project steps in `devctl_project` guard this: `vendored` runs `rapid-ship status --strict`, `distribution` builds the wheel and runs `scripts/smoke_distribution.py`, and `python-3.12` runs the tests on the oldest supported Python. In this repository nothing is excluded and no managed file may become the project's own: `status --strict` holds every managed file to its template, and `tests/test_kit_dogfood.py` fails when the lock records a Kit-managed file as seeded, which `--strict` allows.

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
| `.rapid-ship/project.toml` | seeded | Stacks, repository, Agent identity, the Mode, Kit, map and test settings |
| `.rapid-ship/exceptions.toml` | seeded | Break-glass exceptions |
| `AGENTS.md`, `docs/AGENTS.md`, `tools/AGENTS.md` | seeded | The root guide and the first directory guides |
| `CLAUDE.md` | seeded | `@AGENTS.md`, so Claude Code reads the same instructions |
| `README.md`, `ARCHITECTURE.md` | seeded, plan 5 | Skeletons that `devctl check` verifies |
| `.claude/settings.json` | seeded, plan 5 | Harness guardrail wiring for Claude Code. Codex gets its wiring file in a follow-up, and agy only if the owner decides on one after its interactive runs (section 4) |
| `.github/CODEOWNERS` | seeded | The owner for every path in Walk; below it, commented out, the Protected set |
| `docs/features/README.md` | seeded | The feature-file format |
| `docs/patterns/README.md` | seeded | The Pattern-file format |
| `.gitignore`, `pyproject.toml`, `src/AGENTS.md`, `src/<package>/__init__.py`, `tests/AGENTS.md`, `tests/test_import.py` | seeded, Python, only when there is no `pyproject.toml` yet | Guardrail settings, dev dependencies and a skeleton that passes `check` |
| The Python starter Patterns in `docs/patterns/`, with their reference code and tests | seeded, Python, plan 5, with the skeleton above | Error handling, configuration, input validation and performance (Patterns, below) |
| `.gitignore`, `package.json`, `tsconfig.json`, `eslint.config.js`, `vite.config.ts`, `knip.jsonc`, `index.html`, `src/AGENTS.md`, `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx` | seeded, TypeScript, plan 6, only when there is no `package.json` yet | Guardrail settings, dev dependencies and a React skeleton that passes `check` |
| The TypeScript starter Patterns in `docs/patterns/`, with their reference code and tests | seeded, TypeScript, plan 6, with the skeleton above | The same three Patterns |

devctl runs through uv for every stack, so a TypeScript project needs uv as well as Node.js and npm. Its own lock keeps its dependencies apart from the project's. Kit-owned code is excluded from the project's lint, type, test and dead-code settings; this repository checks it upstream.

A stack's files are written under its directory. With the Python stack in `backend/`, for example, the seed is `backend/pyproject.toml` (plan 6). The Kit's common files, such as devctl, the root guides, CI and the hook, stay at the repository root.

The Kit aims to give each area it touches a base template that a new project builds on and owns: the guides, the settings files, the starter Patterns, the CI workflow, the hook and each stack's guardrail settings.

### Settings files

None of these holds a secret. All are in the Protected set. Each is documented where it lives and validated where it is read:

- Every settings file the Kit ships, seeded or managed, states a key's or rule's contract in a short comment where its format allows one and its name and value do not: the values or units it accepts, a default that is not obvious, or a constraint, such as a Protected file. It drops every other comment, as the root guide's comment Rules ask. That covers the TOML files, CODEOWNERS, the CI workflow and, from plan 6, `tsconfig.json` and `knip.jsonc`, which TypeScript and knip read as JSON with comments, `eslint.config.js` and `vite.config.ts`. On 2026-10-25 the owner relaxed plan 5's first rule, a comment on every key, to this one.
- devctl rejects an unknown key, a wrong type, a number outside its range and a value outside its allowed set in the files it reads. The error names the file, the key and what it accepts, so a typo cannot silently keep a default. A tool's own settings file is validated by the tool that reads it, such as Ruff, `tsc` or ESLint.
- Plain JSON seeds, such as the Harness wiring file `.claude/settings.json` and `package.json`, cannot hold comments. This section describes them, and doctor checks the wiring file (section 6).
- A test holds each seed to its loader: every key the loader accepts appears in the seed (plan 5).

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
# The GitHub repository, written "owner/name".
repository = "owner/name"
# The code owner that CODEOWNERS names, written as CODEOWNERS writes it: "@login" or "@organisation/team".
code_owner = "@owner"
# Agent identity: each App's ID and slug, as rapid-ship app prints them. 0 and "" mean off.
# Record both Apps or neither.
worker_app_id = 0
worker_app_slug = ""
reviewer_app_id = 0
reviewer_app_slug = ""

[escalation]
# The Mode. true is Walk: the owner merges every pull request. false is Flight.
every_pr = true

[kit]
optional = []          # opt-in Kit files and skills, such as "rs-contribute"
exclude = []           # Kit files or directories the project owns instead

[map]
# Source directories: each child directory needs a guide, and file-size caps their source files at 500 lines.
source_roots = ["backend/src/<package>", "frontend/src"]
unguided = []
exclude = []           # directories whose AGENTS.md files are template content

[tests]
unit = ["backend/tests/unit/**"]   # every other test counts as behavioural
```

- **`[[stack]]` (plan 6):** one table per stack. `name` is `python`, `typescript` or `agnostic`, and `agnostic` cannot sit beside another stack. `directory` is a path inside the repository, relative to its root, and not a symlink; `"."` is the root. Two tables cannot name the same stack and directory. Until plan 6 the file holds one top-level key, `stack = "python"`, which TOML cannot hold beside `[[stack]]`. Plan 6 lands before GA, when the Kit keeps no backward compatibility (section 3): devctl rejects the old key with an error that says to rewrite it as one table at `"."`, and the project rewrites it.
- **`[github]`:** `repository` is `owner/name`. `code_owner` is the code owner that CODEOWNERS names, written as CODEOWNERS writes it: `@<login>` for a person, or `@<organisation>/<team>` for a team. doctor's CODEOWNERS item checks CODEOWNERS against it, never against the repository's owner, because an organisation itself cannot be a code owner. Agent identity is on when both Apps are recorded, each with its ID and slug. A partial record, or Apps recorded without `repository`, is a settings error. [Spec 3](2026-10-16-metrics-and-gardening-design.md) matches an agent PR's author against the Worker App's slug, so it needs no App key.
- **`[escalation]`:** `every_pr` sets the Mode. `true`, the seed, is Walk: the merge guard denies every agent merge, so the owner merges every pull request, and CODEOWNERS names the code owner for every path. `false` is Flight: CODEOWNERS names only the Protected set, and an agent may merge a pull request that the merge guard allows. The guard leaves to the owner each one that touches the Protected set or declares a removed behavioural test or an overage of the diff cap (section 4). Each path the owner adds to the Protected set moves Flight toward Walk. With Agent identity and a ruleset, GitHub also enforces CODEOWNERS. doctor checks CODEOWNERS and the ruleset against `every_pr` (section 6), and the owner changes `every_pr` and CODEOWNERS together, in one Protected PR. On 2026-10-26 the owner removed the table's `kinds` and `revision_rounds`, which only the descoped `rs-lead` would have read. devctl rejects them as it rejects any unknown key, with no message of their own, because the Kit keeps no backward compatibility before GA (section 3).
- **`[kit]`, `[map]`, `[tests]`:** built in plans 2 and 3. `[map] exclude` lets this repository keep the template guides under `rapid_ship/templates/` out of the map rules. Spec 3's plan lets `[kit] optional` name an optional Kit file, such as the metrics Action, as well as a skill. With several stacks, `source_roots` and `unit` name paths inside each stack's directory. `[tests] unit` classes each removed test as unit or behavioural, for the `diff` step's report and for the merge guard in Flight (sections 4 and 5).
- **Removed by plan 4 and its follow-ups:** `[agents]` and a leftover `[roster]`, which devctl refuses with "rapid-ship does not run agents across several Providers; delete the table" (section 1); `[linear]`, because devctl never talks to the tracker; `[dispatch]` (`max_workers`, `attempt_limit`, `worktree_root`), because nothing dispatches and rapid-ship takes no notice of how many Sessions run; and `[release]`, which nothing reads, because a project defines its own deploy metrics (Spec 3).

Plan 4 stopped seeding `.rapid-ship/gate.toml`, and devctl stopped reading it. The Mode lives in `[escalation] every_pr`, Flight has no lease, and the test-removal switch became the merge guard's rule that leaves a PR declaring a removed behavioural test to the owner in Flight (section 4). The file's threshold tables described automatic promotion and demotion, which no longer exist. Spec 3's plan seeds `.rapid-ship/metrics.toml`, which holds the Suggested thresholds ([Spec 3](2026-10-16-metrics-and-gardening-design.md)). `sync` never deletes a seeded file, so an existing project keeps its old `gate.toml` until the owner deletes it; this repository deleted its own in plan 4.

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
4. **Rules,** in the table below. Each rule ends with `enforced by: <reference>` or `advisory` (section 5).
5. **Pull requests:** how an agent opens, reviews and merges a pull request, below.
6. Pointers to `GLOSSARY.md`, `docs/adr/`, and the `rs-writing` and `rs-ponytail` skills (section 7).

The skeleton seeds these Rules, in this order. Rules 2 to 14 carry the owner's comment rule of 2026-10-25, with the owner's clarification of 2026-10-26 that code does not cite the document behind it: one Rule for each of its clauses or for each check that enforces part of it. The suppression and removed-test Rules predate it. The first Rule asks for the scope the agent was asked to change: since the owner's descope of 2026-10-26, no task template lists a change's paths. The Python guide adds a `dead-code` Rule after rule 14, from section 5's Exceptions. It is `advisory`: `check:exceptions` fails an unmarked comment or item, but devctl cannot detect the forms that the Rule forbids. Spec 3's plan adds an `advisory` Rule for Corrections that the owner gives inside a Session ([Spec 3](2026-10-16-metrics-and-gardening-design.md)).

| Rule | Marker |
| --- | --- |
| Keep each change inside the scope you were asked to change. | `advisory` |
| Prefer clear names, types, and simple control flow. | `advisory` |
| Add comments only when they convey a contract, rationale, invariant, or external constraint that the code does not adequately express. | `advisory` |
| Delete commented-out code. | Python: `enforced by: check:lint` (Ruff `ERA001`). Agnostic: `advisory` |
| Keep local explanations beside the relevant code and broader design reasoning in linked documentation. | `advisory` |
| Do not cite the document, plan or decision behind the code in a comment; documentation points to code, not the reverse. | `advisory` |
| A comment does not make a workaround acceptable. Fix the root cause within scope, or explicitly report the limitation. | `advisory` |
| A necessary workaround must have a verified reason, appropriate validation, and a tracked removal condition when temporary. | `advisory` |
| Give each TODO its author and the issue that tracks it. | Python: `enforced by: check:lint` (Ruff `TD002`, `TD003`). Agnostic: `advisory` |
| Mark every suppression with `rs-exception: EX-<n>` and list it in `.rapid-ship/exceptions.toml`, with its reason and removal condition. | `enforced by: check:exceptions` |
| Do not invent explanations, weaken tests, or suppress correctness checks to make a change appear complete. | `advisory` |
| Declare each removed test under `Removed tests:` in the PR body, with a reason. | `enforced by: check:diff` |
| Update comments with behaviour changes, and investigate existing constraint comments before removing them. | `advisory` |
| Do not introduce unnecessary abstractions or broaden a refactor just to eliminate a useful comment. | `advisory` |
| Mark a `dead-code` false positive where devctl can see it, with its `rs-exception` marker: `# noqa: V<code>` or `# deptry: ignore[<code>]` on the reported line, or a `DEP002` item in `[tool.deptry.per_rule_ignores]` for a dependency. For one definition, prefer the comment to an `ignore_names` item. Never hide a finding with a form that devctl cannot detect, which review treats as an unmarked suppression (section 5, Exceptions). | Python: `advisory`. Agnostic: not seeded |
| Editing or deleting a Kit-managed file makes it the project's own and stops its Kit updates; the Rule says how to keep updates, own a file outright or give it back ("Who owns what", section 3). | `advisory` |

After the Rules and before the pointers, both seeds of the root guide, the common one and the Python one, hold this section word for word. It holds what the descoped delivery skills would have taught every agent: how to open, review and merge a pull request. Its bullets are instructions, not Rules, so map rule 6 does not apply to them.

```markdown
## Pull requests

- Run `./devctl check` and fix what it reports before you open a pull request.
- With Agent identity on, push with `./devctl as worker push` and open the pull request with `./devctl as worker gh pr create`.
- Review a change from a Session that did not write it. With Agent identity on, approve with `./devctl as reviewer gh pr review <number> --approve`, or request changes with `./devctl as reviewer gh pr review <number> --request-changes --body <findings>`. Never approve a change you wrote.
- Merge with `gh pr merge <number> --squash --match-head-commit <sha>`; the merge guard checks the pull request first. In Walk, the owner merges every pull request.
- Declare `Over the diff cap:` in the pull request body only after the owner accepted the overage.
- Undo a merged change only with `git revert`.
```

Where the Kit wires the Harness, the guardrails enforce part of it. With Agent identity on, G7 and G8 deny an agent's `git push` and `gh` writes made as the owner. The merge guard denies every agent merge in Walk; in Flight it denies the merge of a PR that declares a removed behavioural test or an overage, and any merge before `devctl check` passes (Harness guardrails, below). The rest is advice: no check can tell which Session wrote a change, or whether the owner accepted an overage before the work. `git revert` writes the `This reverts commit` line that Spec 3's Reverts metric reads.

AGENTS.md files are the single instruction source. The seeded `CLAUDE.md` is a real file containing `@AGENTS.md`.

### README.md and ARCHITECTURE.md

Plan 5 seeds both. For a new repository `rs-setup` fills them in with the owner; in an existing one `init` skips them where they exist, and `rs-setup` merges the skeleton's sections into them (section 8).

- **README.md:** what the project does and for whom, how to run it, how to check a change (`./devctl check`), and where the agent instructions start (`AGENTS.md`).
- **ARCHITECTURE.md:** the system's purpose and context, a table of its main parts (part, where, what it does), how data moves between them, the ADRs in `docs/adr/`, named as a code span because a new project has no `docs/adr/` yet and map rule 8 would fail a link to it, and how to work on the code. The project keeps it current as the code changes, and `rs-health` and `rs-garden` report text that no longer matches the code (section 9).

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

### Harness guardrails

The Kit brings the rungs into the agent's loop through the Harness's hooks. One devctl command, `devctl hook` (section 6), holds every rule, and each Harness's seeded settings file only wires that command to the Harness's hook events. A Kit update therefore changes the rules for every project, while each project keeps its own settings files.

rapid-ship works with any Harness, a CLI or a desktop app, on any Provider: a subscription, an API key or a gateway, such as pi on a model through OpenRouter. The Kit ships wiring for one Harness, Claude Code (plan 5). Every other Harness, Codex and agy included until their wiring lands, gets AGENTS.md, `.agents/skills`, the pre-commit hook and CI. Its Sessions run without the Harness guardrails, the merge guard included, until it has wiring, which takes one more wiring file and one more `devctl hook` protocol. The pre-commit hook, CI and any ruleset still hold, so GitHub alone holds the bar at merge: the ruleset's required `devctl check` where a ruleset exists, and the owner's approval, of every PR in Walk and of the Protected set in Flight, only with Agent identity and a ruleset. Without both, Walk in such a Harness rests on the seeded root guide's Pull requests section, which is advice. `rs-setup` (section 8, step 5) and `rs-preflight` ([Spec 3](2026-10-16-metrics-and-gardening-design.md)) say so.

Plan 5 wires Claude Code alone, to keep its focus narrow. The hook spike, the first task of plan 5 (backlog item PRO-139), ran a stand-in hook in Claude Code, Codex and agy, in a lead Session, inside a subagent and in a headless Session ([its record](../../trials/2026-10-21-hook-spike.md)). Claude Code's hooks fired in all three, and a deny held in each. Codex's hooks fired and denied in all three, but on an ask Codex ran the call with no prompt. agy's interactive Sessions ran later, on 2026-10-26: its hooks fired in a lead Session and in a subagent, a deny held in each, exit 1, exit 2 and a hook timeout blocked the call, and in `accept-edits` mode an ask on a file write gave no prompt. The owner decided on 2026-10-22 that a follow-up wires Codex after plan 5, without G5 (backlog item PRO-142), and that agy waits until its interactive runs are done (PRO-143).

| Rule | When | Decision |
| --- | --- | --- |
| G1. A git command with `--no-verify`, or `git commit -n` | Before a shell command | Deny |
| G2. `git push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes`, or a refspec that starts with `+` | Before a shell command | Deny |
| G3. Another way to land a change on the default branch: `gh pr merge` with `--admin`, a `git push` to the default branch, or a `gh api` call that merges, writes the default branch's ref or commits a file. Step 1 of the merge guard lists each form the hook recognises | Before a shell command | Deny, with or without Agent identity, and name `gh pr merge <number>` without `--admin` |
| G4. A file-edit tool writing `.rapid-ship/kit.lock` | Before a file edit | Deny: `rapid-ship` writes the lock |
| G5. A file-edit tool writing a path in the Protected set | Before a file edit | Ask the owner |
| G7. With Agent identity on: `git push` in any form | Before a shell command | Deny, and name `./devctl as worker push` |
| G8. With Agent identity on: a `gh` write as the owner, which is any `gh pr` subcommand other than `view`, `list`, `status`, `diff`, `checks` or `checkout`; any `gh issue` subcommand other than `view`, `list` or `status`; or `gh api` with a method other than `GET` or with `-f`, `-F`, `--field`, `--raw-field` or `--input` | Before a shell command | Deny, and name `./devctl as <role> gh` |
| G9, the merge guard. An agent's `gh pr merge`, with or without Agent identity | Before a shell command | Deny in Walk; when the PR touches the Protected set; in Flight, when its body declares a removed behavioural test or an overage of the diff cap; while `devctl check` has not passed on the PR's head commit; or, with Agent identity on, while the Reviewer App has not approved the head commit |

No rule runs when an agent stops, and no rule has the number G6. Running `devctl check` at the end of every turn or subagent costs too much, so rung 2 holds through the pre-commit hook and CI, and the seeded root guide asks each agent to run `./devctl check` before it opens a pull request (Root AGENTS.md skeleton, above).

- **Commands:** the hook splits the command line with shell rules and checks each simple command, in order. Simple commands are joined by `;`, `&&`, `||`, `|`, `&` or a newline. A subshell gives its contents as commands of their own. So do `$( … )`, backticks, `<( … )` and `>( … )`, inside double quotes too, and so does a substitution inside arithmetic: `(( … ))`, `$(( … ))` or `$[ … ]`. The hook checks them before the line's other commands. The command that holds a substitution keeps its other words. The hook cannot know what a substitution prints, so it reads `$(...)` in its place, joined to the text around it: `$(git rev-parse HEAD):main` ends in `:main`. A quoted or escaped operator, such as `';'`, is a word. The hook drops comments, heredoc bodies, redirections such as `2>&1`, and a reserved word such as `if` before a command, and it joins a line that a backslash continues. It skips leading `NAME=value` words, matches `git` and `gh` by their basename, and skips git's global options, such as `-C <path>`. A line that shell rules cannot split, such as one with an unclosed quote, is an internal error. The exception is a line whose text holds `gh`, `pr` and `merge` in that order: the merge guard denies it, because it cannot check the merge. Within one simple command the rules apply in the order G1, G2, G3, G7, G8, and for an edit G4, then G5. The first deny wins, and a deny beats an ask. For G3 and the merge guard, a `gh` command run through `./devctl as <role> gh` counts as the `gh` command it runs. G8 never applies to it, because it runs as an App.
- **The Protected set** for G5 is read from the Protected-set lines of the CODEOWNERS file that GitHub reads, the first of `.github/CODEOWNERS`, `CODEOWNERS` and `docs/CODEOWNERS`, commented or not, never the `*` line. The `diff` step and the merge guard read the same lines with the same matcher, from `devctl/codeowners.py`. G4 and G5 compare an edited path in any case, because macOS's default file system ignores case: `agents.md` writes `AGENTS.md`. On a file system that keeps case, G5 therefore also asks before a new file whose name differs from a Protected path only in case.
- **Decisions:** the hook only denies or asks. It never allows or approves anything; with no rule matched it gives no decision, and the Harness's own permission flow continues.
- **Exit codes, a workaround:** devctl's convention, where exit 2 means "could not run", collides with the Harnesses' hook protocols: Claude Code reads a hook's exit 2 as "block". While each Harness defines its own protocol there is no neutral choice. `devctl hook` therefore answers in the protocol of each Harness it is wired for, which in plan 5 is Claude Code's alone. It keeps that mapping in one module, `hook_protocols.py`, and documents it there as a workaround. It never exits 2. An internal error exits 1 with a message, and the call goes through: Claude Code treats exit 1 as a non-blocking error, as the hook spike observed. In the spike Codex also ran the call after exit 1, and both Harnesses blocked the call on exit 2; agy's exit codes were not observed. The merge guard is the exception: once it has recognised a merge, it catches its own errors and denies the merge.
- **When the hook fails before it decides:** the workaround holds only while `devctl hook` runs and has parsed the event. In Claude Code, these are non-blocking errors, so the call goes through, a merge included: `uv` is not on `PATH`, and the `devctl` shim exits 127; Python fails while it loads devctl; the hook cannot parse the event; or Claude Code kills the hook at its hook timeout, 600 seconds by default. The hook spike observed a hook ended before it finished, and the call went through. Claude Code documents a handler setting, `"onFailure": "block"` from v2.1.295, that blocks the call in these cases instead; the seed leaves it unset (section 11). When uv itself fails, for example because it finds no Python, it exits 2. Claude Code reads that as block, so every wired call stops until the setup is fixed. The `./devctl doctor` run at the start of a Session is what catches a broken setup: it starts through the same shim, so a uv or Python failure stops it too, and it reports wiring that lacks the Kit's hooks (section 6). It cannot catch a hook timeout, or an event format that a Harness update changed. In the spike Codex also ran the call after a hook timeout. Each follow-up that wires Codex or agy records these cases for its Harness first.
- **Unreadable settings:** G1 to G4 need no settings and always apply. When the hook cannot read `.rapid-ship/project.toml` or its CODEOWNERS file, or `project.toml` is invalid, G5, G7 and G8 give no decision, and the hook writes the reason to stderr. A missing CODEOWNERS file is not unreadable: it is an empty Protected set, so G5 asks for nothing, and G7 and G8 stay on. A full `./devctl doctor` run reports the missing file. Checking the settings on every tool call costs too much, so broken settings are caught once, at the start of a Session: `./devctl doctor` exits 2 and names the file and the key (section 6). The merge guard then denies every merge, because it cannot tell the Mode, or whether Agent identity is on and so whether a merge needs the Reviewer App's approval. Its denial carries the reason.
- **Limits:** the hook reads the command line as the Harness passes it. It does not follow scripts, aliases, `sh -c` strings or shell redirections that write files, and it does not read a request body from a file or stdin. It does not read a substitution inside a heredoc body, and a `)` in a `case` pattern or in a `${ … }` expansion ends a `$( … )` early. It follows no wrapper other than `./devctl as`, such as `env`, `exec` or `xargs`. It matches options as written, so it misses `git -c core.hooksPath=<path>`, which skips the pre-commit hook, and an abbreviated long option such as `--no-verif`. G8 counts gh's aliases `gh pr ls` and `gh pr co` as writes, a false deny; `gh pr list` and `gh pr checkout` pass. It sees only the tools it is wired to, so a merge through another tool, such as an MCP server's merge tool, is outside it. Other `gh` commands that write, such as `gh release` or `gh workflow run`, are outside G8, and `devctl as` refuses them. These rules stop habits and mistakes. A misbehaving agent can bypass every one of them, the merge guard included, for example through a script, its own HTTP client, a tool the hook does not see or a Harness without the wiring. Where a ruleset exists, GitHub enforces the required `devctl check`, and with Agent identity the owner's approval through CODEOWNERS too.

| Harness | Seeded file | Wiring |
| --- | --- | --- |
| Claude Code | `.claude/settings.json` | `PreToolUse` for `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit` and `Monitor`, running `"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool`. Settings hooks also fire inside subagents and headless Sessions. `Monitor` runs a shell command, so the hook reads its `command` as `Bash`'s. `MultiEdit` is legacy, and the matcher keeps it for versions that still have it. `WIRED_TOOLS` in `hook_protocols.py` lists these six tools, and doctor checks the wiring file against it. The seed sets no `timeout`, so Claude Code's default of 600 seconds applies, which the merge guard's budget relies on (its step 6). doctor reports a hook whose `timeout` is below 360 seconds (section 6) |

When a Session started in the main checkout edits a file in a linked worktree, the event's `cwd` and `$CLAUDE_PROJECT_DIR` stay at the main checkout, and only the edit's absolute path names the worktree (hook spike). The hook therefore reads the settings of the repository that holds the edited path, and for a shell command those of the repository that holds `cwd`. That repository is the nearest ancestor that holds `.git`, a directory or a linked worktree's file. An edit outside every repository gets no decision.

The file is seeded, not managed, because many repositories already have a `.claude/settings.json`; `init` skips an existing one and `rs-setup` merges the Kit's entries into it. `devctl doctor` reports the file when it lacks the Kit's hooks (section 6).

The follow-up that wires Codex (PRO-142) seeds `.codex/hooks.json`, which wires `PreToolUse` for `Bash` and `apply_patch` to `devctl hook codex pre-tool`. Codex runs project hooks only in a trusted project, after the owner reviews them in `/hooks`, and a changed hook needs a new review; the spike observed both. Codex hooks cannot ask: on an ask, Codex reports the hook as failed and runs the call. Its wiring therefore omits G5 and leaves those edits to CODEOWNERS and the merge guard. A follow-up that wires agy, if the owner decides on one (PRO-143), would seed `.agents/hooks.json`, which wires `PreToolUse` to `devctl hook agy pre-tool`. The spike tried these files and events with a stand-in hook command, because it ran before `devctl hook` exists, and plan 5's `devctl hook` takes only `claude`. Each wiring that lands adds its seeded file, its `devctl hook` protocol, its doctor item and its Protected-set change (below).

Sandboxing is not part of the Kit. A Harness's subagents inherit the sandbox of the owner's own Session, so a sandbox is the owner's choice for their whole Session. `rs-setup` offers it (section 8).

#### The merge guard

G9, the merge guard, enforces the Mode on an agent's merge. In Walk (`every_pr = true`) it denies every agent merge, so the owner merges every pull request. In Flight it leaves to the owner each pull request that touches the Protected set or whose body declares a removed behavioural test or an overage of the diff cap, and it denies any other merge until `devctl check` has passed on the head commit. With Agent identity on, it also keeps an agent from merging until the Reviewer App has approved the head commit. It is on in every setup and every Mode, with or without Agent identity and with or without a ruleset, in each Harness whose hooks run `devctl hook` (the wiring table above). The owner decided on 2026-10-26 that the guard enforces each Mode; before, only advice held an agent to it. Without Agent identity, an agent's review comes from the owner's account, so the guard cannot tell it from the owner's own, and it checks no review. With Agent identity and a ruleset, which public repositories and paid plans have, GitHub enforces the check too, and the Protected set and Walk through CODEOWNERS (The Protected set and CODEOWNERS, below). No ruleset reads a PR's body, and neither App is a code owner, so no ruleset requires the Reviewer App's approval: the guard alone holds the declarations and that approval. A GitHub Free private repository has no rulesets, so there the guard is the enforcement: an agent's merge of a PR whose check failed is rejected when the agent tries it. The guard reads GitHub only for `gh pr merge`. G3 denies outright the other ways to land a change on the default branch that the hook recognises, a `git push` to it included, so `gh pr merge` is the only recognised way left (step 1). The owner merges each PR that the guard leaves to the owner, for example in GitHub's web interface. The Protected set therefore needs the owner in every Mode, with or without Agent identity.

1. **Commands.** The guard checks `gh pr merge`, with any arguments, `--auto` included, run directly or through `./devctl as <role> gh`. G3 denies outright each other way to land a change on the default branch that the hook recognises, run directly or, for `gh`, through `./devctl as <role> gh`:
   - `gh pr merge` with `--admin`;
   - `git push` to the default branch: a refspec whose destination is that branch, such as `main`, `HEAD:main`, `HEAD:refs/heads/main` or `HEAD:heads/main`, or the deletion `:main` or `--delete main`; a pattern whose destination covers that branch, such as `refs/heads/*:refs/heads/*`; the matching refspec `:`; `--all`, its newer name `--branches`, or `--mirror`; or `HEAD`, `@` or no refspec while the current branch is the default branch. The hook cannot read a variable or a substitution, so a destination that holds one, such as `"$(git branch --show-current)"`, `HEAD:$BRANCH` or `HEAD:${BRANCH:-main}`, counts as the current branch. The hook reads the default branch's name locally from `refs/remotes/origin/HEAD`, and treats both `main` and `master` as the default branch when that ref is missing. It reads the refspecs on the command line, not git's push settings;
   - `gh api` with a method other than `GET`, set with `-X` or `--method` or implied by `-f`, `-F`, `--field`, `--raw-field` or `--input`, on one of these paths: `repos/<owner>/<repo>/pulls/<number>/merge`, a PR's merge; `repos/<owner>/<repo>/merges`, the Merges API; `repos/<owner>/<repo>/git/refs/heads/<default branch>`, the default branch's ref; or `repos/<owner>/<repo>/contents/<path>`, the Contents API, which commits a file to a branch. A path matches with or without a leading `/` and as a full API URL, gh's `{owner}` and `{repo}` placeholders included;
   - `gh api graphql` with a query, given inline, that names the `mergePullRequest`, `enablePullRequestAutoMerge`, `enqueuePullRequest`, `mergeBranch`, `updateRef`, `updateRefs` or `createCommitOnBranch` mutation.

   Every other tool call pays only for this match. The guard reads GitHub for `gh pr merge` and for nothing else. The hook reads the default and current branch from local git only for G3's `git push` and ref forms, and for a `gh pr merge` that names no pull request.
2. **The pull request.** The number, URL or branch that `gh pr merge` names, or without one the PR of the current branch. The guard reads it from the repository of a PR URL, else from `-R` or `--repo`, given before or after `merge`, else from `[github] repository`. A URL's repository wins over `-R`, as it does in gh. For a branch, or the current branch read from local git, exactly one open PR must have the head `<owner>:<branch>`. The PR that the guard reads carries its body, which step 5 reads in Flight.
3. **The check.** The guard reads the PR's head commit and that commit's check runs from GitHub, through `gh api` with `GET` under the owner's sign-in. The check has passed when the latest check run named `devctl check` from GitHub Actions, the one the ruleset requires (section 8), has completed on that commit with the conclusion `success`. A pending, failed, cancelled, skipped or missing run has not passed.
4. **The files.** It lists the PR's changed files from GitHub, each with its status and, for a rename, its previous path. It reads them 100 to a page, and a 30th full page is a denial, because GitHub lists at most 3,000 files. gh prints only those fields of each file, so a page whose patches are large stays within the 1 MiB that devctl reads of a command's output. It matches both paths of each file against the Protected-set lines of CODEOWNERS on the PR's base branch, never its head, so a PR cannot exempt itself. As GitHub does, it reads the first of `.github/CODEOWNERS`, `CODEOWNERS` and `docs/CODEOWNERS` that exists on the base; with none, the Protected set is empty. It uses the matcher the `diff` step uses, and it applies the ledger rule (section 5): a Corrections ledger entry that the PR changes, renames or removes is Protected. An entry that the PR adds is not checked, whatever its status.

   **The review.** With Agent identity on, the guard also lists the PR's reviews from GitHub, paginated. Only the Reviewer App's reviews count: those whose author is `<slug>[bot]`, where `<slug>` is `[github] reviewer_app_slug`. Of them, the latest that approves or requests changes decides; comments, dismissed reviews and pending reviews are ignored. That review must approve the head commit the guard read. A person's approval does not replace it: to merge without the Reviewer App's approval, the owner merges in GitHub's web interface. Without Agent identity, the guard reads no reviews.
5. **Decision and message.** The guard denies with the first of these that applies, in this order:
   1. In Walk (`every_pr = true`): `merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #<n>`.
   2. When the PR touches the Protected set: `merge denied: PR #<n> touches the Protected set (<paths>); the owner merges it in GitHub's web interface`.
   3. In Flight (`every_pr = false`), when the PR body's Evidence section declares a removed behavioural test, an entry in its `Removed tests:` list whose path matches none of `[tests] unit`'s patterns, classified exactly as the `diff` step classifies it (section 5), or an overage, as an `Over the diff cap:` line: `merge denied: PR #<n> declares <what>, so the owner merges it`. `<what>` is `a removed behavioural test` or `an overage of the diff cap`, and both, joined by ` and `, when both apply. A declared removed unit test does not stop the merge. The guard reads the body with devctl's Evidence parsers, `removed_test_declarations` and `over_cap_reason`, so it reads the section as the `diff` and `evidence` steps do (section 5).
   4. While the check has not passed: `merge denied: devctl check on PR #<n> at <commit> is <state>; wait for it to pass or fix what it reports, then merge again`.
   5. With Agent identity on, while the Reviewer App has not approved the head commit: `merge denied: PR #<n> has no Reviewer App approval of its head <commit>; have the Reviewer review that commit, then merge again`.
   6. When the command does not carry `--match-head-commit` set to the head commit the guard checked, because the option is missing or names another commit: `merge denied: PR #<n> merges only at the checked head <commit>; run <the same command> --match-head-commit <commit>`, the exact command to retry. With the option set, GitHub refuses the merge if the head moves after the guard's read. The option must name the full 40-character SHA, which GitHub compares.

   Walk comes first, because in Walk no agent merges. The Protected set and the declarations come before the check, because waiting on the check cannot fix a PR that only the owner merges. When the guard cannot read GitHub or identify the PR, or fails itself, it denies with `merge denied: the merge guard cannot check this merge: <reason>; fix that, then merge again`. The reason is gh's first error line or names what is missing, so a merge that the running guard cannot check does not pass. When the hook cannot read its settings, the guard cannot tell the Mode or whether Agent identity is on, so it denies every merge and says so. When the hook fails before the guard decides, the guardrail bullets above say what happens. Otherwise it gives no decision.
6. **Cost.** Only `gh pr merge` pays. In Walk the guard reads the PR, then denies. In Flight, without Agent identity, it makes four reads or more through `gh api`: the PR, CODEOWNERS on the base branch, one read for each name until one exists, its files, paginated, and its check runs. With Agent identity on, it also reads the PR's reviews, paginated, before the check runs, so five reads or more. Each read may take up to 60 seconds. The guard denies rather than start a read that could end more than 300 seconds after the hook run started, a budget that every merge on the line shares. Claude Code lets the call through when it kills the hook at its timeout, 600 seconds by default.
7. **Limits.** The guard reads GitHub when the command runs. A push that lands between that read and the merge moves the head, so GitHub refuses the merge because of `--match-head-commit` (step 5). It counts any approval the Reviewer App posts, and any Session on the owner's machine can act as that App (section 6), so the guard cannot tell whether the Session that approved also wrote the change. It reads only what the PR's body declares: a removed test or an overage that the body does not declare fails the `diff` step, so the check does not pass. It cannot see `GH_REPO` set on the command line or in the environment. For a merge that names no PR, it looks up the local branch's name, which can differ from the branch gh resolves. In either case it can check another PR than the one gh merges, and `--match-head-commit` then makes GitHub refuse the merge, because that PR's head differs. It and G3 recognise only the forms of step 1. A push destination that holds a variable or a substitution counts as the current branch, so one that names the default branch from another branch, such as `HEAD:$BRANCH` with `BRANCH=main`, is not denied. Like every guardrail, they can be bypassed by a misbehaving agent, for example through a script or a tool the hook does not see.

### The Protected set and CODEOWNERS

The Protected set is the kinds of change that need the owner's approval in every Mode. CODEOWNERS assigns them to the owner, and GitHub reads it from the PR's base branch, so a PR cannot exempt itself. The merge guard holds the Protected set in every setup: it denies an agent's merge of a Protected-set PR, which the owner then merges in GitHub's web interface. With Agent identity and a ruleset that requires code-owner review, GitHub holds it too. The seeded CODEOWNERS has one active line in Walk, `* @<owner>`. Below it, commented out for Flight, is the Protected set:

- `/.github/`, `/.githooks/`, `/devctl`, `/tools/devctl/`;
- the skills and the Harness guardrail wiring: `/.agents/skills/` and `/.claude/`, which covers `.claude/settings.json`. Codex's wiring adds `/.codex/` when it lands, and agy's widens `/.agents/skills/` to `/.agents/` to cover `.agents/hooks.json`;
- every `AGENTS.md` and `CLAUDE.md` (`/**/AGENTS.md`, `/**/CLAUDE.md`);
- `/.rapid-ship/`, which holds the stacks, the Mode and the exceptions;
- the settings files of the check tools, because a settings file can switch its check off: `/.gitleaks.toml`, `/.gitleaksignore`, `/zizmor.yml` and `/zizmor.yaml`; for the Python stack `/pyproject.toml`, `/**/ruff.toml`, `/**/.ruff.toml`, `/mypy.ini`, `/.mypy.ini`, `/pytest.ini`, `/.pytest.ini`, `/pytest.toml`, `/.pytest.toml`, `/setup.cfg`, `/tox.ini` and `/.importlinter`; and for the TypeScript stack (plan 6), in its directory, `package.json`, `.npmrc`, `tsconfig*.json`, `eslint.config.*`, `.prettierrc*`, `prettier.config.*`, `.prettierignore`, `vite.config.*`, `vitest.config.*`, `knip.*` and `.knip.*`. A stack in a subdirectory gets its lines under that directory, such as `/backend/pyproject.toml` and `/frontend/package.json` (plan 6);
- `/docs/corrections/README.md`, the Corrections ledger's format, which Spec 3's plan seeds with this line;
- one line for each existing Pattern file, and any paths the project adds for access, the data model or the public API. The Python seed lists its four starter Pattern files, commented out, right after `/.rapid-ship/`, so the set still ends with the check tools' settings files.

A change to or removal of an existing Corrections ledger entry is Protected too. CODEOWNERS cannot tell a new file from a changed one, so devctl carries that rule: the `diff` step lists such a change with the Protected paths, and the merge guard treats it as Protected (section 5). Adding an entry is not Protected, and devctl does not read an added entry's status. An agent could therefore add an entry that is already `implemented`, `rejected` or `closed`; the owner accepts that limit.

Plan 5 removes the seed's placeholder comment about Harness settings and adds no line, because `/.claude/` already covers the Claude Code wiring. Codex's and agy's wiring change the lines above, and doctor's list of Protected paths to match, when they land. Flight uncomments the Protected set and removes the `*` line. The owner makes that change, with `every_pr = false`, in one Protected PR, by hand or through any Session, and doctor checks that the two match (section 6). With Agent identity and a ruleset, the `*` line makes GitHub enforce Walk too, because an App cannot bypass the ruleset. Without Agent identity, under a ruleset, an agent's PR comes from the owner's account, and only the owner's bypass can merge it, which the guardrails deny to agents (G3). Without a ruleset, GitHub enforces no Mode. In every setup the merge guard enforces the Mode, the Protected set and a passing `devctl check` (The merge guard, above). In a Harness without Kit wiring no merge guard runs, so unless Agent identity and a ruleset let GitHub enforce Walk, Walk rests on the seeded root guide's Pull requests section, which is advice.

### CI workflow

`.github/workflows/devctl-check.yml` (built in plan 3):

- **Triggers:** `pull_request`, including body edits; `push` to `main` or `master`; a nightly `schedule`; and `workflow_dispatch`. A workflow cannot name the default branch, and a push run skipped by a condition would report a passing `devctl check` on the same commit, so the branches are listed. `rs-setup` records a Setup gap when the default branch has another name.
- **Permissions:** `contents: read` only. The job uses no secrets, so fork PRs behave the same.
- **Concurrency:** PR runs share one group per ref and cancel superseded runs. As built in plan 3, push runs share their ref's group too, so GitHub cancels a pending push run when a newer one queues. Plan 5 gives each push run a group of its own commit, `devctl-check-${{ github.event_name == 'push' && github.sha || github.ref }}`, and leaves `cancel-in-progress` as it was, so every merge gets its run; [Spec 3](2026-10-16-metrics-and-gardening-design.md) counts red merges from them.
- **Steps:** checkout and `astral-sh/setup-uv`, both pinned by commit SHA, with `persist-credentials: false` and full history for the diff policy. Install gitleaks 8.30.1, verified by its SHA-256. Run `./devctl check --tier full`. Plan 6 adds `actions/setup-node`, pinned by commit SHA, which runs only when the repository holds a `package-lock.json`, and the run becomes `./devctl check --tier full --install`, which installs each TypeScript stack's locked dependencies first. The workflow stays the same file in every project.
- **Job name:** `devctl check`, which the ruleset requires.

The nightly run checks the default branch. Spec 3 counts a red default-branch run after a merge as a metric.

### Python guardrail settings

New projects get these settings in the seeded `pyproject.toml`. An existing project keeps its own settings in the Setup PR, apart from devctl's exclusions and what the `dead-code` step needs to run (section 8, step 4.5). At the end of Setup, `rs-setup` offers the meaningful rules they lack in a separate PR (section 8, step 14), and `devctl doctor` reports what is still missing.

- **Ruff:** E, W, F, I, B, UP, SIM, C4, RUF, PGH, ERA, T20, S, TID, PT, PTH, DTZ, C90, TD, BLE and ANN401. C90's `max-complexity` is 10. Relative imports are banned. A `banned-api` table holds the members that Patterns ban: the seed starts with `os.environ` and `os.getenv`, which the configuration Pattern bans outside the settings module through a per-file entry, and other Patterns add theirs. PGH003, PGH004, RUF100 and ERA001 control escape hatches. `rs-setup` adds ASYNC and FAST where it finds asyncio or FastAPI; the seed does not.
- **mypy:** strict over source and tests, with `warn_unreachable` and the error codes `ignore-without-code`, `redundant-expr` and `truthy-bool`.
- **import-linter:** one `layers` contract, whose layers stay optional until the architecture names them, and one `forbidden` contract that keeps pytest out of production code.
- **pytest:** `--strict-markers --strict-config`, `xfail_strict = true`, `filterwarnings = ["error"]`.
- **vulture**, for unused code: `[tool.vulture] paths` names the source and test directories, `["src", "tests"]` in the seed, so a use in a test counts as a use. The seed sets no `ignore_names` and no `ignore_decorators`. Ruff's `lint.external` lists `V`, so Ruff keeps vulture's codes in a `# noqa` comment instead of reporting RUF102.
- **deptry**, for dependencies that do not match the imports: `[tool.deptry] extend_exclude` leaves out `tools/devctl`, because devctl's imports are not the project's. The seed's `known_first_party` names its package, which sits under `src/`: deptry finds the project's own modules only directly in the directory it scans. deptry reads every `[dependency-groups]` group as dev, and it never checks a dev dependency for use.
- **Dev dependencies:** ruff, mypy, pytest, import-linter, vulture (`>=2.16,<3`) and deptry (`>=0.25,<1`) in the project's lock.

There is no ratchet. Unsafe patterns are prohibited. A legitimate exception is a listed break-glass entry (section 5).

### TypeScript guardrail settings

Plan 6 adds the TypeScript stack, for React with TypeScript, with npm as the package manager. New projects get these settings in the stack's seeded files; an existing project gets them as a Python project does.

- **TypeScript:** `tsconfig.json` sets `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`, `isolatedModules` and `noEmit`.
- **ESLint:** a flat `eslint.config.js` with ESLint's recommended rules, typescript-eslint's `strictTypeChecked` set and the React Hooks plugin's recommended rules. It adds `complexity` at 10, `no-console`, `@typescript-eslint/switch-exhaustiveness-check`, and `@typescript-eslint/ban-ts-comment`, which bans `@ts-ignore` and `@ts-nocheck` and requires a description on `@ts-expect-error`. An unused disable comment is an error (`reportUnusedDisableDirectives`). A `no-restricted-imports` rule starts empty, and Patterns fill it, as they fill Ruff's `banned-api`. The lint step allows no warnings.
- **Prettier:** its defaults. Line width and other style options are the project's choice.
- **Vitest:** `vitest run`, with `allowOnly: false`. React component tests use jsdom and Testing Library.
- **knip:** `knip.jsonc`, which knip reads as JSON with comments, so a key carries a comment where section 4 asks for one. knip runs in its default mode. A test file is then an entry file, so a use in a test counts as a use, as for Python code. The seed sets no `ignore*` key, no `tags`, no `rules`, no `include` and no `exclude`. It names `entry` and `project` files only where knip's Vite and Vitest plugins do not find them.
- **npm:** `package-lock.json` is committed, and `engines.node` names the supported Node.js major version.
- **Other tools:** Tailwind CSS and tools like it are welcome. The Kit neither seeds nor blocks them, and `rs-setup` adds their ESLint and Prettier plugins where the project uses them.
- **Dev dependencies:** ESLint with its TypeScript and React Hooks plugins, Prettier, TypeScript, Vitest, jsdom, Testing Library and knip, in the stack's `package.json` and lock. Plan 6 pins their versions.

## 5. `devctl check`

`check` is the single entry point for hooks and CI. It covers everything a machine can decide, and it never runs a model. Built in plan 3. Plan 5 adds map rule 8, the Pattern `task` key and Lessons section, the `SKILL.md` rule, the diff cap, the ledger rule and, for Python, the `dead-code` step. Plan 6 runs each stack's steps in its own directory and adds the TypeScript stack.

### Steps

| Step | Tier | Fails when |
| --- | --- | --- |
| format | fast | Formatting differs (Python: `ruff format --check`; TypeScript: `prettier --check .`) |
| lint | fast | The linter reports a finding (Python: `ruff check`; TypeScript: `eslint --max-warnings 0 .`) |
| map | fast | A map rule below fails |
| exceptions | fast | A suppression lacks a listed exception, or an exception matches nothing |
| file-size | fast | A source file exceeds 500 lines without an exception |
| kit | fast | The lock is unreadable, or a managed file that is not excluded is missing. The message names both choices: `rapid-ship sync --revert <path>` restores the file, and `rapid-ship sync` keeps the deletion as the project's own, after which this step passes |
| types | full | The type checker fails (Python: mypy; TypeScript: `tsc --noEmit`) |
| contracts | full | An import contract is broken (Python: `lint-imports`; TypeScript has no contracts step yet, which a tool such as dependency-cruiser could fill later) |
| dead-code | full | Code or a declared dependency that nothing uses, or an import that the declared dependencies do not cover (Python: vulture for unused code and deptry for dependencies; TypeScript: knip). Plan 5 builds it for Python and plan 6 for TypeScript |
| tests | full | The test suite fails (Python: pytest; TypeScript: `vitest run`) |
| audit | full | A locked dependency has a known vulnerability (Python: pip-audit 2.10.1; TypeScript: `npm audit`) |
| secrets | full | gitleaks finds a secret in the change's commits, or in the whole history without a base. gitleaks must be on `PATH` |
| workflows | full | zizmor 1.30.1 reports a finding in a GitHub Actions workflow |
| diff | full | The diff policy below fails |
| evidence | full, PRs only | The PR body lacks its Evidence section |

Each stack supplies its own tools. The agnostic stack has no `format`, `lint`, `types`, `contracts`, `dead-code`, `tests` or `audit` step. pip-audit and zizmor run through `uv tool run --from <pin>` and are not dependencies. vulture and deptry are dev dependencies and run through `uv run --locked`, as Ruff and mypy do, because deptry maps each import to a distribution installed in the project's environment. The TypeScript stack runs each tool from `node_modules/.bin` in its directory and `npm audit` through npm, and it never installs anything: a missing tool blocks its step, and the message names the command that installs it, `npm ci` in that directory. A project adds steps in `devctl_project`.

### Dead code

The `dead-code` step holds one rule in every stack that has language tools: it fails on code and declared dependencies that nothing uses, and on imports that the declared dependencies do not cover. Each stack maps the rule to its tools.

| Stack | Command, from the stack's directory | Reports | Exit codes |
| --- | --- | --- | --- |
| Python | `uv run --locked vulture --min-confidence 0`, with `[tool.vulture]` from `pyproject.toml` | Unused imports, variables, arguments, attributes, functions, methods, properties and classes, and unreachable code | 0 passes, 3 fails, any other blocks |
| Python | `uv run --locked deptry . --no-ansi --json-output <file>`, with `[tool.deptry]` from `pyproject.toml` | Every deptry rule: a missing (DEP001), unused (DEP002), transitive (DEP003), misplaced dev (DEP004) or standard-library (DEP005) dependency. DEP002 never checks a dev dependency | 0 passes; 1 fails with the report's findings, or blocks when the report is missing or unreadable; any other blocks |
| TypeScript | `knip --include files,dependencies,unlisted,binaries,unresolved,exports,types,enumMembers,namespaceMembers`, from `node_modules/.bin` | Unused files, dependencies and devDependencies, exports, exported types, and enum and namespace members; unlisted dependencies and binaries; and unresolved imports | 0 passes, 1 fails, 2 blocks |

- A use in a test counts as a use of code, so a change can add a function with its tests before the change that calls it. Code that only tests reach is left to the gardener ([Spec 3](2026-10-16-metrics-and-gardening-design.md)). deptry does not read the root `tests` directory, which its default `exclude` leaves out, so a dependency that only tests import fails; it belongs in the dev group.
- devctl sets vulture's kinds on the command line. vulture's command-line value replaces the file's, so a project's `min_confidence` cannot switch a kind off. deptry runs every rule, so its command line names none, and a rule code in its `ignore` key is a suppression instead. Plan 6 verifies whether knip's `--include` overrides its `rules`, `include` and `exclude` settings (Exceptions, below).
- The Python step runs both tools every time. Its details give each tool's lines, each starting with the tool's name. A blocked tool outranks a failed one. deptry's exit 1 means findings or an error, so the step reads its JSON report, as the `audit` step reads pip-audit's.
- Before it runs a tool, the Python step reads `pyproject.toml`. When `[dependency-groups] dev` lacks vulture or deptry, or `[tool.vulture] paths` is unset, it runs neither tool and names each gap: `[dependency-groups] dev lacks <tools>; add them to pyproject.toml and run uv lock`, and `[tool.vulture] paths is not set; list the directories vulture scans, such as ["src", "tests"]`. Without paths, vulture stops with its own "Please pass at least one file or directory".
- These gaps block the step, and findings fail it, from the Kit version that ships the step. Before GA the Kit keeps no backward compatibility (section 3), so an existing project adds the tools and their settings itself, as section 8, step 4.5 describes. `sync` does not add them, and doctor's Python floor reports each (section 6).
- What the tools cannot see: vulture matches names, so any use of a name keeps every definition of that name alive, a bare reference in a test included. deptry never checks a dev dependency for use (DEP002). Neither tool sees code that is reachable but never runs. The audit that `rs-health` and the gardener share covers these (section 9).
- Python's tools do not report a module that nothing imports when its definitions are used inside it or share a name used elsewhere, or when it holds only top-level statements: vulture reports an unused module only through its unused definitions. No maintained Python tool reported such modules when the step was designed on 2026-10-25, and devctl adds no module-reachability logic of its own. Until a maintained tool reports them, the gardener's audit lists them ([Spec 3](2026-10-16-metrics-and-gardening-design.md), section 10). For TypeScript, knip's `files` reports them.

### Several stacks

Plan 6 runs the common steps once, at the repository root: map, exceptions, file-size, kit, secrets, workflows, diff and evidence. It runs each stack's own steps, format, lint, types, contracts, dead-code, tests and audit, once per stack, in that stack's directory, with that stack's tools and settings. With one stack at the root, the step names stay as they are. Otherwise each stack's step is named with its directory, such as `lint (frontend)`. The exit code follows the rules below over every step.

A file belongs to the stack whose directory contains it, the innermost one when directories nest. The exceptions step reads each file's suppressions in its stack's forms, and the file-size step counts its stack's source files: `.py` and `.pyi` for Python, `.ts` and `.tsx` for TypeScript. A file outside every stack's directory has only the forms that every stack shares, those of gitleaks and zizmor.

### Output and exit codes

- `./devctl check [--tier fast|full] [--json] [--base REV] [--pr-body PATH] [--install]`. The default tier is `full`. `--install`, from plan 6, first runs `npm ci` in each TypeScript stack's directory; CI uses it.
- One line per step: passed, failed, blocked, or not applicable, with details below a step that did not pass. `--json` prints the same as a list of `{"name", "status", "details"}` objects.
- Exit 0: every applicable step passed. Exit 1: at least one step failed. Exit 2: at least one step could not run, for example a missing tool or an unreadable setting. A blocked step never counts as passed, and 2 outranks 1.
- The `diff` and `evidence` steps need a change. In CI the base is the PR's base and the body comes from the PR event. Locally, `--base` names the base, or devctl uses the merge base with `origin`'s default branch, and `--pr-body` names a file with the body. Without a base `diff` is not applicable; outside a PR, `evidence` is not applicable.

### Map rules

The map rules read only the files that git tracks, staged ones included, so the pre-commit hook sees a file that the commit adds. A guide, link target, maintained directory, feature file, Pattern, skill or root document counts only when git tracks it, and so does each path that a feature file, Pattern or reference names, and the `pyproject.toml` that references read. An untracked file does not count, even when git does not ignore it.

1. Every Markdown link in every AGENTS.md resolves to a tracked file or to a directory that holds one. A link that starts with `/` resolves against the repository root, as GitHub resolves it.
2. Every maintained directory has a tracked AGENTS.md. Maintained directories are the top-level directories and the immediate children of each source root that hold a tracked file, except hidden directories and those listed in `[map] unguided`. AGENTS.md files under a `[map] exclude` directory are template content: the map rules ignore them.
3. Every AGENTS.md is reachable by links from the root AGENTS.md.
4. Every file in `docs/features/` other than its README has front matter with `purpose`, `entry_points`, `data`, `observe` and `reproduce`. Each path it names is a tracked file or a directory that holds one. `entry_points` is not empty. Each `reproduce` command is `./devctl` followed by a registered verb.
5. Every file in `docs/patterns/` other than its README has front matter with a non-empty `task`, a `reference` that is a tracked file or a directory that holds one, and a non-empty `enforced_by` list whose references resolve, and the file has a non-empty `## Lessons` section. Plan 5 adds `task` and the Lessons section.
6. Every bullet under a `Rules` heading in any AGENTS.md ends with `enforced by: <reference>` or `advisory`. Each reference resolves.
7. Every skill directory under `.agents/skills/`, from the Kit or the project, has a `SKILL.md` whose front matter `name` equals the directory name and whose `description` is not empty, and a relative symlink at `.claude/skills/<name>` that points to it. No other entry exists under `.claude/skills/`. A skill directory that is itself a symlink must be relative and stay inside the repository. Plan 5 adds: `SKILL.md` is a regular file, not a symlink.
8. Plan 5: `README.md` and `ARCHITECTURE.md` exist at the repository root, every local link in them resolves, and the root AGENTS.md links to both.

Spec 3 adds a rule for the Corrections ledger after these.

Plan 5's additions fail at once, as the rest of the rules do. Three of them fail on files that an existing project already owns: rule 5's `task` and Lessons, rule 7's regular `SKILL.md` and rule 8's links, which are the root guide's links to both documents and the local links inside them. Before GA the Kit keeps no backward compatibility (section 3), so the project fixes those files.

### References

A reference names the check that enforces a Rule or Pattern. The stack defines the kinds, and `check` resolves each one.

| Reference | Resolves when |
| --- | --- |
| `check:<step>` | The devctl check step exists |
| `test:<path>::<name>` | The test exists in a tracked file |
| `ruff:<code>` | The rule is selected in the Ruff settings (Python) |
| `banned:<module.member>` | The member is in Ruff's `banned-api` table (Python) |
| `contract:<name>` | An import-linter contract has that name (Python) |
| `type:<path>` | The file is tracked and the stack's type checker checks it: mypy (Python), or `tsc` through `tsconfig.json` (TypeScript, plan 6) |
| `eslint:<rule>` | The rule is on, as an error, in the configuration that `eslint --print-config` computes for the stack (TypeScript, plan 6) |

These map to the four Pattern enforcement types: import contract, banned-API rule, type fixture and architecture test.

With several stacks, a reference resolves against the stack that holds the Pattern's `reference`, or the AGENTS.md that states the Rule.

### Exceptions

A suppression is a line that switches a check off. For Python these are `# noqa`, `# type: ignore`, the `# mypy:` file comments, `# pragma: no cover`, pytest's skip, skipif, xfail and importorskip, and deptry's `# deptry: ignore` comment, bare or with codes such as `# deptry: ignore[DEP003]`. vulture reads `# noqa` with its own codes, such as `V103` for an unused function, so one comment form serves Ruff and vulture. Ruff, mypy and pytest read only comments and the syntax tree, but vulture 2.16 and deptry 0.25.1 search a line's whole text, strings included, and act on its first match. Each searches only the first line of what it reports: vulture the line where a node starts, which for a decorated definition is its first decorator's, and deptry the first line of a `from ... import` statement or `import_module` call, and each name's own line in a plain `import`. devctl reads those lines as the tools do. There, a `# noqa` that vulture acts on, bare or naming one of its codes, and a `# deptry: ignore` are suppressions, in a string too; a string's later lines hide nothing. A string that opens on such a line with the comment and runs on leaves no room for a marker, so its text is reworded. vulture numbers lines as Python's `str.splitlines` does, which also splits at a form feed or U+2028, so devctl reads the text that vulture reads for each line. In source that devctl cannot parse, every line counts for vulture. deptry matches its comment case-sensitively, with no word boundary after `ignore`, and reads codes only in upper case: with any other bracket it ignores every rule on the line, so devctl's rule for that comment is `deptry`. gitleaks's inline allow comment and `# zizmor: ignore[...]` are suppressions in every stack.

A dead-code tool's allowlist is a suppression too. Each item of an allowlist key in a tool's settings file is one suppression, written alone on its own line:

- Python, in `pyproject.toml`: each item of vulture's `ignore_names` and `ignore_decorators`; each rule code in deptry's `ignore`, which switches that rule off everywhere; each item of the arrays under deptry's `[tool.deptry.per_rule_ignores]`; each group in deptry's `optional_dependencies_dev_groups` and its deprecated `pep621_dev_dependency_groups`, which make an optional group a dev group that DEP002 skips; and each key of `[tool.deptry.package_module_name_map]`, which can map an unused dependency onto a module the code imports.
- TypeScript (plan 6), in `knip.jsonc`: each item of `ignore`, `ignoreFiles`, `ignoreBinaries`, `ignoreDependencies`, `ignoreMembers`, `ignoreUnresolved`, `ignoreIssues` and `tags`.

For TypeScript (plan 6) the suppressions are `eslint-disable` comments in each form, `@ts-expect-error`, `prettier-ignore`, the coverage tools' ignore comments, Vitest's `skip`, `skipIf`, `todo` and `fails`, and knip's `@public` and `@beta` tags before a declaration. ESLint bans `@ts-ignore` and `@ts-nocheck`, and Vitest's `allowOnly: false` fails `only`. Plan 6 names each form's rule, as plan 3 did for Python.

1. Each suppression carries `rs-exception: EX-<n>` on the same line, in a comment. One marker matches one rule. A `# noqa`, `# type: ignore` or `# deptry: ignore` comment that names several codes is one rule, its codes sorted, such as `S603,S607` or `deptry:DEP001,DEP003`. Any other line that switches off two rules needs two markers and two entries. A line holds at most one allowlist item.
2. `EX-<n>` exists in `.rapid-ship/exceptions.toml` with a matching path and rule, a reason and a removal condition. An allowlist item's path is its settings file. Its rule is the key's name under the tool, a colon and the item, such as `vulture.ignore_names:pytestmark`, `deptry.ignore:DEP003`, `deptry.per_rule_ignores.DEP002:psycopg2`, `deptry.package_module_name_map:foo-python` or `knip.ignoreDependencies:@types/node`.
3. Each ID is used exactly once. An entry that matches no suppression fails as stale.
4. File-size exceptions are path entries with `rule = "file-size"` and no inline marker. They fail as stale once the file is under the cap.
5. devctl also parses each settings file that holds an allowlist. It fails an item that it cannot place alone on its own line, such as an item in an inline table, and a line that holds two items, so no item escapes its marker.

Kit 0.2.0 adds the dead-code tools' suppressions: the allowlist items, deptry's comment, and the lines that vulture and deptry read beyond a comment. A missing marker on one of them, and each error of rule 5, fails at once, as a missing marker on any other suppression does. Before GA the Kit keeps no backward compatibility (section 3), so this holds on lines that an existing project already owns too.

Settings that choose what a tool reads are not suppressions: vulture's `paths` and `exclude`; deptry's `exclude`, `extend_exclude`, `known_first_party`, `non_dev_dependency_groups`, `requirements_files` and `requirements_files_dev`; and knip's `entry`, `project` and `ignoreWorkspaces`. Nor are knip's `rules`, `include`, `exclude` and `ignoreExportsUsedInFile`, which can switch a kind off. Plan 6 verifies which of these four `--include` overrides, and doctor's TypeScript floor reports a project that sets one of the others. Nor is knip's `ignoreGlobalBinaries`: its default, true, which the seed keeps, drops each `binaries` finding for a common global command such as `git`. Setting it to false only reports more, so doctor does not report it. Two of deptry's settings can still hide a finding. Each module in `known_first_party` counts as the project's own, so an import of it gives no DEP001, DEP003 or DEP004 finding. Each group in `non_dev_dependency_groups` holds production dependencies for deptry, so an import of one of its packages gives no DEP004 finding. They stay settings, not allowlist keys, because they describe the project's layout: the seed's `known_first_party` names its package under `src/`. The owner's review covers them: all of these settings live in a Protected file, so the owner reviews each change, as with Ruff's per-file entries.

For one definition, prefer an inline `# noqa: V<code>` to an `ignore_names` item. The comment spares that definition alone, and its entry fails as stale once the definition is deleted. An item spares every definition of that name.

Some forms hide a finding where no marker can record it: a vulture whitelist module, the form the vulture README recommends; any other bare reference to a name in a scanned file, a test included; a leading `_` added to a name; an `__all__` entry; and a `getattr` string. devctl cannot detect them, so review treats each as a suppression without an exception. deptry also honours its comment in a notebook (`.ipynb`) code cell, which devctl does not read; review catches it.

Kit-managed files that are not excluded are not scanned. An added suppression needs an edit to `exceptions.toml`, which is Protected. Nothing is counted, so removing one suppression cannot pay for adding another. For an existing project, `rs-setup` marks each existing suppression and each existing dead-code finding at Setup (section 8).

### Diff policy

The diff policy compares the change with its base. It is adapted from no_human's test-tamper guard (MIT), using each test's identity instead of its net counts.

1. **Removed tests:** a test present at the base and absent everywhere at the head fails, unless the PR body declares it under `Removed tests:` with a reason. A test's identity is its name within its file (`test_x` or `TestA::test_x`), so a test moved to another file is not a removal. The step classes each removed test as unit or behavioural: a test is a unit test only when its path matches `[tests] unit`; every other test, such as an integration or end-to-end test, is behavioural. The class labels the step's report, and the merge guard uses it in Flight: it leaves a PR that declares a removed behavioural test to the owner, and a declared removed unit test does not stop an agent's merge. In Walk the owner merges every PR (section 4).
   For Vitest (plan 6), a test's identity is the chain of its `describe`, `it` and `test` titles in its file. A title that is not a plain string cannot be compared, and the step lists that test as not checked.
2. **Tautologies:** an assertion that the change turns into a tautology, such as `assert True`, `x == x` or Vitest's `expect(x).toBe(x)`, fails.
3. **Faking fixtures:** a new `autouse` fixture in a `conftest.py` fails without an exception. Vitest names its setup files in its configuration, which is Protected.
4. **Protected paths:** the step lists each Protected path the change touches, and each ledger entry that item 6 makes Protected. It does not fail; the merge guard enforces the approval, and so does GitHub through CODEOWNERS with Agent identity and a ruleset.
5. **Diff cap (plan 5):** a change that adds and removes more than 1,500 lines in total fails, unless the PR's Evidence section has a line starting `Over the diff cap:` with a reason. The count leaves out files ending in `.md`, `.txt` or `.log`, binary files, Kit-managed files, `.rapid-ship/kit.lock` and each stack's lock file (`uv.lock`, `package-lock.json`), so documentation, logs and a Kit sync do not count. A declared overage passes with a note. The owner merges a PR that declares one in every Mode: in Walk the owner merges every PR, and in Flight the merge guard leaves it to the owner (section 4). The seeded root guide asks an agent to declare an overage only after the owner accepted it (section 4).
6. **Corrections ledger (plan 5):** a change that modifies, renames or removes an existing entry, a Markdown file under `docs/corrections/` other than `README.md`, is Protected. The step lists each such change with the Protected paths, and the merge guard treats it as Protected. Adding an entry is not Protected, and the step does not read an added entry's status, a limit the owner accepts (section 4). An agent can therefore add a Correction without the owner, while changing or removing one, its status included, needs the owner's review. CODEOWNERS cannot tell a new entry from a changed one, so devctl carries this rule; CODEOWNERS holds only the ledger's `README.md` (section 4). [Spec 3](2026-10-16-metrics-and-gardening-design.md) defines the ledger, whose entries agents report.

Skip markers are suppressions, so the exceptions step handles them.

### Evidence

On a PR, the body must contain an `## Evidence` section with at least one command and its result, and a line starting `Not covered:`. When the change removes tests, the section also lists them under `Removed tests:`. The agent that opens the PR writes the section by following the `rs-pr` engineering skill. In Flight the merge guard reads its `Removed tests:` list and its `Over the diff cap:` line (section 4). CI reruns the check when the PR body is edited.

```markdown
## Evidence

- `./devctl check`: exit 0; every step passed except evidence, not applicable

Removed tests:
- `tests/test_flags.py::test_legacy_flag`: the flag was deleted in this PR

Not covered: behaviour on Windows.
```

### Where `check` runs

1. The pre-commit hook runs the fast tier. `git commit --no-verify` skips it, which the Kit's Harness guardrails deny to agents.
2. The seeded root guide asks each agent to run it, and fix what it reports, before it opens a PR (section 4). That run is advisory.
3. CI runs the full tier on every PR. A ruleset requires it where GitHub offers one, and in every setup the merge guard denies an agent's merge until it passes; this is the enforcement.
4. The nightly CI run checks the default branch.

## 6. Other devctl commands

devctl keeps only commands used repeatedly. The owner asked to keep this surface small, so a new need becomes an option of an existing command where one fits.

| Command | Built in | What it does |
| --- | --- | --- |
| `check` | plan 3 | Section 5 |
| `doctor [--skills \| --settings]` | plan 4; `--settings` in plan 5 | Reports what this machine and repository lack. `rs-preflight` runs it first in full, and `rs-setup` and `rs-health` run it too; every other Session runs `--settings` first |
| `as {worker,reviewer} ...` | plan 4 | Agent identity's thin command for `gh` and `git push` |
| `hook claude pre-tool` | plan 5 | The Harness guardrails, with the merge guard, in Claude Code |
| `metrics` | Spec 3 | The metrics report |

A project adds its own verbs in `devctl_project`. devctl never starts an agent to do work, never tracks or resumes one, and never talks to the issue tracker. Only `doctor --skills` starts a short headless Session, to check which skills a Harness loads.

### `devctl doctor`

doctor changes nothing in the repository. It reports each item as ok, missing or unknown, then a summary line. It exits 0 when everything is ok, 1 when something is missing and 2 when an item could not be checked. Plan 4 built it from the old branch, reshaped as below. It reads GitHub with the owner's `gh` sign-in, always as `GET`.

**At the start of each Session.** While `devctl hook` cannot read the settings, it still applies G1 to G4, and the merge guard denies every merge, but G5, G7 and G8 give no decision: the asks before Protected edits and Agent identity's denies are lost. Checking the settings on every tool call costs too much, so a Session catches broken settings once, at its start. doctor reads `.rapid-ship/project.toml` before its other items, after git, and an unreadable file or an invalid key makes it exit 2 and name the file and the key. doctor starts through the same `devctl` shim as the hook, so a uv or Python failure that breaks the hook stops doctor too (section 4). `rs-preflight` runs the full `./devctl doctor` first ([Spec 3](2026-10-16-metrics-and-gardening-design.md)), and `rs-setup` and `rs-health` run it as part of their work (sections 8 and 9). A full run also reads GitHub and, with Agent identity on, mints a token for each App. The seeded root AGENTS.md therefore asks every other Session to run `./devctl doctor --settings` first: it reads and validates only the settings files, and makes no GitHub request. It prints git, the settings item and the Harness wiring item, and it excludes `--skills`. GitHub drift, such as a changed ruleset, therefore shows only in a full run, which the owner can start at any time.

| Area | Item | ok when |
| --- | --- | --- |
| toolchain | git | git 2.31 or later |
| toolchain | uv, gh | On `PATH` |
| toolchain | node, npm (plan 6) | On `PATH` when the repository has a TypeScript stack, at the Node.js major version its `package.json` names |
| toolchain | gh sign-in | `gh auth status` succeeds |
| toolchain | gitleaks | Version 8.30.1, which `devctl check` pins |
| guardrails | settings (plan 5) | `.rapid-ship/project.toml` and `.rapid-ship/exceptions.toml` load, and a CODEOWNERS file exists. An unreadable file or an invalid key is unknown, and the message names the file and the key; no CODEOWNERS file is missing |
| guardrails | `core.hooksPath` | Set to `.githooks` |
| guardrails | CI | The workflow has a job named `devctl check` |
| guardrails | Python floor | The settings of section 4 are present (Python stack) |
| guardrails | TypeScript floor (plan 6) | The settings of section 4 are present, read from `tsconfig.json` and from `eslint --print-config` (TypeScript stack) |
| guardrails | devctl exclusions | `tools/devctl` is excluded from the project's Ruff, mypy, pytest, vulture, deptry and uv workspace |
| guardrails | Harness wiring (plan 5) | `.claude/settings.json` is tracked and valid JSON, does not set `disableAllHooks`, and has a `PreToolUse` command hook that runs `devctl hook claude pre-tool`, and nothing more, for each tool of section 4's wiring. The hook's words are `devctl` or a path that ends in `/devctl`, then `hook`, `claude` and `pre-tool`, as Claude Code passes them. In exec form, with `args`, they are `command` and each `args` element, and `command` holds no quote and no `$` outside a `${…}` placeholder. In shell form they are the command's words after quote removal, and the first word holds only path characters, `$NAME` and `${NAME}`. A `$` in single quotes or after a backslash does not count, and neither does an operator, `#`, `=` or other punctuation glued before the path, as in `false&&"$CLAUDE_PROJECT_DIR"/devctl`. A hook that runs in the background, has an `if` condition or sets a `timeout` below 360 seconds does not count; that timeout is the merge guard's 300-second budget plus 60 seconds for devctl to start. A file doctor cannot read is unknown. Each later wiring adds an item for its file |
| kit | Kit files | The `rapid-ship status` summary has nothing missing |
| github | ruleset | An active ruleset on the default branch matches section 8 for the current Mode and Agent identity |
| github | CODEOWNERS | Matches the Mode and names `[github] code_owner`: the `*` line when `every_pr = true`, the Protected set otherwise |
| github | delete branch on merge | On |
| github | fork PR workflow approval | A public repository requires approval for workflows from all outside contributors |
| agent identity | Worker App, Reviewer App installation | Only with Agent identity on: installed on this repository with exactly the permissions of section 3 |
| agent identity | Worker App, Reviewer App key | Only with Agent identity on: the Keychain item exists and mints a token. Minting changes nothing in the repository |

- **GitHub Free private repositories** have no rulesets. GitHub refuses the read with a plan-limit message, and doctor reports the ruleset as missing with that reason. There the merge guard is the enforcement (section 4).
- **The code owner:** doctor reads it from `[github] code_owner`, never from the repository's owner, so a repository that an organisation owns, whose CODEOWNERS names a person or a team, can pass. While `code_owner` is unset, doctor reports the CODEOWNERS item as missing and names the key, without reading CODEOWNERS. The comparison ignores case.
- **Removed:** the issue-tracking item, the Harness sign-in items, and every App item while Agent identity is off.

`devctl doctor --skills` also checks what a Claude Code Session would see, only when `claude` is on `PATH`. It adds a temporary detached worktree at `HEAD` in a temporary directory, starts one new headless Claude Code Session there on the cheapest model, and asks which skills it can load. A Kit or project skill the Session does not list is missing. A user-invoked skill (`disable-model-invocation: true`) is reported as not checked, because the Session may leave it out of its list. Skills the Session sees from outside the repository, such as the owner's own skills or plugins, are listed for the owner to judge. The worktree is removed afterwards, whatever the Session did. The probe uses a little quota. doctor passes Claude Code the owner's sign-in and proxy variables, and never reads a token file. `rs-setup` runs it, and the owner reruns it after adding a skill or upgrading Claude Code.

doctor probes Claude Code alone until the Kit integrates another Harness, which waits for that Harness's wiring follow-up (section 4). doctor without `--skills` starts no probe.

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
- **Reviews:** a review that the merge guard counts is posted with `./devctl as reviewer gh pr review <number> --approve`, or `--request-changes`, from a Session that did not write the change, as the seeded root guide's Pull requests section says (section 4).
- **Merges:** `./devctl as worker gh pr merge` is a merge like any other, so the merge guard checks it first. G3 denies the other forms it recognises when they run through `./devctl as <role> gh`, such as a merge or a write to the default branch's ref through `gh api` (section 4).
- **Workflows:** neither App has the Workflows permission, so GitHub refuses an App's push of its own change under `.github/workflows/`. The owner pushes such a change, which is in the Protected set anyway. GitHub accepted an App's push whose only new commit merged in a workflow change already on the base branch ([plan 4's trial](../../trials/2026-10-21-agent-identity.md#rerun-of-the-pending-steps)). So an agent pushing as the Worker App can merge in the base branch when the merge takes each workflow file as the base branch has it. A merge that resolves a conflict in a workflow file makes the agent's own change there; only a clean merge was tried.

Each run mints its own token and holds it only in memory:

1. Read the App's private key from the Keychain with `security find-generic-password -s rapid-ship/<role>-app/<App ID> -w`, where the App ID is the role's in `[github]`.
2. Sign a JWT and request an installation token restricted to this one repository and the App's named permissions. REST calls go through a small `http.client` wrapper that never follows a redirect.
3. Give `gh` the token only through `GH_TOKEN`, with `GH_REPO` set to the repository, in that one child's environment. Give `git push` the token only through a `GIT_ASKPASS` helper that reads it from that one git command's environment, with every configured credential helper and repository hook switched off for that command.

No key or token is written to disk, put on a command line or printed. An item that `security` wrote trusts `security` itself, so reads show no dialog, and any process the owner runs can read both keys. Any agent can therefore act as the Reviewer App, on a change it wrote too. The seeded root guide's Pull requests section tells agents never to approve a change they wrote (section 4), and no technical barrier is planned until misuse is observed. With Agent identity on, the Harness guardrails deny `git push` and `gh` writes made as the owner (G7, G8).

### `devctl hook`

`devctl hook <harness> pre-tool` is the one implementation of the Harness guardrails (section 4). `<harness>` names a Harness with Kit wiring: `claude` in plan 5, and each later wiring adds its Harness with its protocol. It reads the Harness's event JSON on stdin and answers in that Harness's hook protocol. It applies G1 to G5 and the merge guard, and G7 and G8 when Agent identity is on. It reads `.rapid-ship/project.toml` and the first of `.github/CODEOWNERS`, `CODEOWNERS` and `docs/CODEOWNERS` from the repository that holds the call: for an edit the one that holds the edited path, a linked worktree included, and for a shell command the one that holds `cwd`. It reads GitHub only for `gh pr merge`, with doctor's `GET` under the owner's sign-in. It reads the default and current branch from local git only for G3's `git push` and ref forms and for a `gh pr merge` that names no pull request. It changes nothing. A missing or unknown Harness or event exits 1, like an internal error, never 2.

## 7. Skills in the Kit

The Kit ships four skills, `rs-setup`, `rs-health`, `rs-garden` and `rs-preflight`, the engineering skills, and one optional skill, `rs-contribute`. Every Kit skill's name starts with `rs-`, which avoids collisions with Harness built-in commands and with an installed upstream plugin.

| Skill | Spec | Built in | What it does |
| --- | --- | --- | --- |
| `rs-setup` | 1 | plan 7 | Sets up a new repository or adopts an existing one (section 8) |
| `rs-health` | 1 | plan 7 | Audits a repository and returns proposed standards tasks (section 9) |
| `rs-garden` | 3 | Spec 3's plan | Records Corrections and finds drift |
| `rs-preflight` | 3 | Spec 3's plan | Reviews with the owner whether the project is ready to widen the Mode toward Flight: the metrics to watch, Alarms and incident integrations, scheduled gardening, the Mode and the Protected set, Agent identity and the ruleset. It is advisory and never gates |
| `rs-contribute` | 1 | plan 7 | Optional: sends a Kit fix back to rapid-ship |

No Kit skill designs, breaks down, leads, implements or reviews work: the owner descoped those skills on 2026-10-26 (section 1). The owner's own Sessions follow the seeded AGENTS.md, its Pull requests section included, and the engineering skills. There is no metrics skill: `rs-setup` records the Suggested thresholds, `rs-preflight` guides the owner through the metrics to watch before Flight, and project-defined metrics are documented in Spec 3.

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

### `rs-contribute`

`rs-contribute` sends a Kit fix from a project back to rapid-ship. It is user-invoked and installed only when the owner opts in at Setup, through `[kit] optional`.

1. Describe the problem with the evidence that shows it: the command, the output and the Kit file involved.
2. Map the project file to its template through the lock.
3. Search rapid-ship's open issues and PRs for a duplicate.
4. In a cached fork of rapid-ship, fix the template and refresh the vendored copy with `rapid-ship sync --in-place`.
5. Run rapid-ship's own `./devctl check`.
6. Push the fix to the fork and open a PR to rapid-ship. Leave out project code, secrets and private paths. If the fix is unclear, open an issue instead. With Agent identity on, the guardrails may deny the agent's `git push` and `gh` writes (G7, G8), and a `devctl as` token reaches only the project's repository. The owner then pushes and opens the PR or issue in a terminal, as in `rs-setup` step 13.

A project may apply the same change to its vendored copy at once. When the fix ships, the next `rapid-ship sync` finds the file equal to the new template and keeps it managed. If a sync ran in between, the file became the project's own (section 3), and `rapid-ship sync --revert <path>` gives it back.

## 8. `rs-setup`

`rs-setup` is user-invoked. The owner runs it in their Harness Session on the `rapid-ship/init` branch, after `init` committed the Kit there with the stacks the owner confirmed (section 3). Before each write outside the repository, such as a GitHub setting, an App, the tracker or the owner's own Harness settings, it states the write and waits for the owner's yes. Before retrying a write whose result is uncertain, it re-reads the outside state. It records each gap it cannot resolve in the Setup PR's body. When a step fails, `rs-setup` explains the problem and the fix and offers to make the fix, rather than stopping with a bare error. It still stops at the first failure and shows the failing command's own output.

### Steps

1. **New or existing.** A repository with source beyond the Kit is existing. Read the stacks and directories that `init` recorded in `project.toml` (plan 6). The owner confirmed them before `init` wrote them (section 3), so do not ask again.
2. **Documents.**
   - New: ask the owner what the project does, for whom and how it runs. Fill in README.md, the root AGENTS.md's first paragraph, and ARCHITECTURE.md's purpose and context. Its parts wait until the code has them; `rs-health` and `rs-garden` report parts that the code has and the document lacks.
   - Existing: `init` skipped the README.md, ARCHITECTURE.md, AGENTS.md and CLAUDE.md that already exist. Merge the skeleton's sections into them from what the code shows, keeping the project's own text, and add a guide for each maintained directory that the `map` step reports. What the code does not show becomes a gap for `rs-health`.
3. **Patterns.**
   - New: walk the owner through the starter Patterns that `init` seeded with the skeleton, and adapt each one, its reference and its Lessons, to the project. Agree any further Patterns, such as how a domain object is stored. For each, write the Pattern file, a minimal reference implementation and its enforcing check. When the reference needs real product code, propose the Pattern as a task instead, as `rs-health` proposes its tasks (section 9).
   - Existing: offer each starter Pattern as a task. `rs-health` proposes its reference from the project's own code.
4. **Checks.** Before each `./devctl check` in this step, stage the files that `rs-setup` has written with `git add`, because the map rules read only tracked files (section 5). Otherwise the `map` step fails on a maintained directory's new guide, and checks no other new guide or Pattern file until the commit.
   1. Confirm gitleaks 8.30.1 with `gitleaks version`, and for a TypeScript stack Node.js and npm; if one is missing, ask the owner to install it.
   2. New project: run `uv sync`, and `npm install` in each TypeScript stack's directory, which writes its lock. Then run `./devctl check`. The seeded skeleton passes.
   3. Existing project: devctl's checks can overlap or conflict with the project's own linters, hooks and CI, and the owner decides how to combine them. Exclude `tools/devctl` from the project's lint, type, test, dead-code and uv workspace settings. Show each overlap or conflict with the settings, hooks and workflows that `init` listed, such as hooks in `.git/hooks` that `core.hooksPath` would stop running, and offer to fold them into `devctl_project`. Leave the project's own tool settings as they are in the Setup PR; step 14 offers the rules they lack. Warn about duplicate checks, which are harmless, and about checks that race, such as two hooks writing the same files, which are harmful. Never block on either.
   4. Existing suppressions: for each one the `exceptions` step reports, add its `rs-exception` marker and an entry with the reason "Existed at Setup on <date>" and the removal condition "Remove when this code next changes". Repeat `./devctl check --tier fast` until the step passes. The owner reviews the entries in the Setup PR.
   5. Existing dead code (Python stack): the `dead-code` step blocks until the project has its settings (section 5). Add vulture and deptry to the dev group, `[tool.vulture] paths` naming the project's source and test directories, `lint.external = ["V"]` in the project's Ruff settings, and deptry's exclusion of `tools/devctl`, with `known_first_party` naming the project's packages that sit below the root, then run `uv lock`. For each finding the `dead-code` step reports, either fix it, by deleting the code or dependency or by declaring the dependency that an import needs, or mark it: `# noqa: V<code>` or `# deptry: ignore[<code>]` with its `rs-exception` marker on the reported line, or a `per_rule_ignores` item with its marker for a declared dependency. Give each mark an entry with the reason "Existed at Setup on <date>" and the removal condition "Delete it, or replace this reason with what uses it". `rs-health`'s audit lists these entries as dead code to remove (section 9). Repeat the step's two commands (section 5) until both exit 0. When the marks put the Setup PR over the diff cap, its Evidence section declares `Over the diff cap: dead code marked at Setup`, and the owner, who merges the Setup PR, accepts it.
   6. Run `git config core.hooksPath .githooks`. In an existing project, run it only after the owner has decided how to combine the existing hooks.
   7. Run `./devctl check` until it passes.
5. **Harness guardrails.** Show the owner the rules of section 4, the merge guard included, and say which Harnesses the Kit wires: Claude Code, and Codex or agy only where their wiring has landed. Say that a Session on any other Harness runs without the guardrails. Where `init` skipped an existing wiring file, such as `.claude/settings.json`, merge the Kit's entries into it. Once Codex's wiring lands, the owner trusts the project and reviews its hooks in `/hooks`.
6. **Sandbox (an offer, not a default).** Explain that a sandbox confines the owner's own Session and every subagent it starts, because subagents inherit it. It is defense in depth, and it needs network access for git, gh, uv, the package index and the tracker. If the owner accepts, write the setting into the owner's own uncommitted settings for their Harness, such as Claude Code's `.claude/settings.local.json`, Codex's `sandbox_mode` in the owner's Codex configuration, or agy's terminal sandbox setting. agy's terminal sandbox has no network by default, so the owner must allow that access first. Never commit sandbox settings.
7. **GitHub.**
   1. Find the repository, or create it with `gh` after the owner confirms its visibility.
   2. After the owner confirms, apply the ruleset from the skill's `ruleset.json` with `gh api`, and turn on automatic deletion of head branches. The ruleset targets the default branch (`~DEFAULT_BRANCH`). Its `pull_request` rule requires code-owner review, dismisses approvals when new commits arrive, requires every review thread to be resolved, and allows squash merges only (`allowed_merge_methods: ["squash"]`). It does not require the most recent push to be approved by someone other than its pusher. It requires the status check `devctl check` from GitHub Actions (`integration_id` 15368). It blocks force pushes and deletion. Its bypass list holds only the repository admin role (`actor_id` 5), in pull-request mode, so the owner can merge their own PRs.
   3. The required approval count is `0`, and approval of the most recent push is off, in every Mode. GitHub counts an approval only from someone with write access to the repository ([about protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)), and the Reviewer App has Contents: read (section 3), so its approval never counts. With Agent identity in Flight, [plan 4's live trial](../../trials/2026-10-21-agent-identity.md) found that GitHub refused the Worker App's merge with the Reviewer App's approval until both were off. The cost is that, in a team, a code owner who pushed the last commit to an agent's PR can approve it themselves. Code-owner review stays required, so CODEOWNERS alone decides who must approve: the owner for every path in Walk, and for the Protected set in Flight. In Flight, with or without Agent identity, GitHub therefore requires no approval for a PR outside the Protected set. With Agent identity, the merge guard requires the Reviewer App's approval of the head commit instead (section 4).
   4. For a public repository, require approval for workflows from all outside contributors. If the default branch is neither `main` nor `master`, record a gap: CI push runs cover only those two names. On a GitHub Free private repository, record a gap: there are no rulesets, so GitHub itself requires neither rung 2 nor rung 4 before a merge. Tell the owner that the merge guard is the enforcement there: it rejects every agent merge in Walk. In Flight it rejects an agent's merge of a PR that touches the Protected set or declares a removed behavioural test or an overage of the diff cap, and any agent merge while `devctl check` has not passed or, with Agent identity on, while the Reviewer App has not approved the head commit.
   5. Record the code owner in `[github] code_owner`: the owner's login, or in an organisation the person or team who approves agent PRs, such as `@acme/maintainers`. Write the Walk line, such as `* @octo`, into CODEOWNERS.
8. **Agent identity (opt-in).**
   1. Recommend from this table, which [ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) records. Agent identity matters most for a solo owner on GitHub Free with a public repository: GitHub enforces the ruleset there, the owner cannot approve a PR their own account opened, and every agent comment appears publicly as the owner's.

      | Setup | Agent identity | Why |
      | --- | --- | --- |
      | Solo owner, public repository or a paid plan | Recommended | It is the only way the owner can approve an agent's PR, because GitHub never lets a PR's author approve it, and GitHub then holds agents to CODEOWNERS |
      | Solo owner, private repository on GitHub Free | Recommended, for real reviews and metrics | Reviews posted as the Reviewer App become GitHub reviews that the merge guard counts, and agent PRs become countable. There is no ruleset, so the merge guard holds the bar with or without it |
      | Team | Optional | Teammates approve agent PRs anyway. The Apps add per-agent metrics, real reviews from the Reviewer App, and agents that CODEOWNERS binds in Flight |

   2. Explain the trade-off that ADR 0002 records: the four things Agent identity buys, and its cost of two Apps, private keys in the macOS Keychain, and agents writing to GitHub only through `devctl as`.
   3. In a team, each repository owner, a personal account or an organisation, has one Worker App and one Reviewer App. In an organisation, an organisation admin runs `rapid-ship app` once, which creates both Apps through the organisation manifest flow (section 3). Each developer holds their own private key for each App, since GitHub allows up to 25 keys per App, and keeps it in their own Keychain under an item named for the App's ID, so one person's key can be revoked alone. For an organisation's Apps, an organisation admin generates one key for each developer in each App's settings, under Credentials, Key pairs, New key, and hands it over securely. The developer imports it with `rapid-ship app --import-key` and deletes the downloaded file. Whether an App manager who is not an admin may generate a key is unverified (section 11). For Apps a personal account owns, the account owner generates one key for each collaborator and hands it over securely, or moves the Apps to an organisation. A pair of Apps for each developer is rejected: it multiplies installations and splits one role's reviews across identities.
   4. Ask whether the owner opts in.
   5. If so, run `uvx rapid-ship app`, which creates the Apps that the repository's owner lacks; in an organisation an admin runs it. Where the Apps exist, the developer imports the key that an admin generated for them instead (step 3). The owner installs both Apps, `rs-setup` records each App's ID and slug in `[github]`, and `./devctl doctor` then confirms each installation and key.
   6. If not, explain which metrics will report "unknown: needs Agent identity", and that agents then act as the owner, so Walk rests on the merge guard and the guardrails. Flight keeps the same ruleset, code-owner review included (section 11). GitHub requires no approval for a PR outside the Protected set, so an agent can merge it once the merge guard allows (step 7.3). A Protected-set PR needs the code owner's approval. A solo owner cannot give it to a PR their own account opened, so they merge such a PR through the admin bypass in GitHub's web interface, as in Walk. The guardrails deny agents `gh pr merge --admin`, and the merge guard denies an agent's merge of a Protected-set PR. It cannot require a review, which comes from the owner's account, so only the seeded root guide's Pull requests section and the owner's instruction hold an agent to a review.
9. **Mode.** Explain that the seeded Mode is Walk (`every_pr = true`): the merge guard denies every agent merge, so the owner merges every pull request (section 4). The owner starts the Sessions and watches them; rapid-ship takes no notice of how many run, and advises running at most 3 agents at once in Walk, for the owner's cognitive load. Later the owner widens the Mode toward Flight in one Protected PR that sets `every_pr = false` and changes CODEOWNERS (section 4); `rs-preflight` can review readiness first, and advises only (Spec 3).
10. **Metrics.** Show the default Suggested thresholds and record the owner's values in `metrics.toml`. Offer the scheduled metrics Action. Explain that the owner sets up Alarms and incident integrations, which differ from project to project, that an Alarm plugs in as a project-defined metric, and that `rs-preflight` guides that setup before Flight (Spec 3). Spec 3's plan adds this step.
11. **Optional skills.** Offer each optional skill once; today that is `rs-contribute`, which sends a Kit fix back to rapid-ship. Add each skill the owner accepts to `[kit] optional` and run `uvx rapid-ship sync --in-place`.
12. **Doctor.** Run `./devctl doctor --skills`, then resolve or record each gap. `--skills` probes Claude Code alone, and only when `claude` is on `PATH` (section 6).
13. **Setup PR.** Commit, then push `rapid-ship/init` and open the PR under the owner's sign-in: the branch adds `.github/workflows/`, which neither App may push. With Agent identity on, the guardrails may deny the agent's `git push`; the owner then runs the push and `gh pr create` in a terminal. The owner merges the PR.
14. **Tool-settings PR** (existing repositories). After the Setup PR, compare the project's own tool settings, for its linters, type checkers and formatters, with the Kit's for each stack. Leave out purely stylistic differences, such as line width, quote style and indentation; `rs-setup`'s references list the stylistic options of each tool. Show the owner each remaining rule with what it catches, including Ruff's ASYNC and FAST families where asyncio or FastAPI is used, and let the owner pick. Open a separate PR from `origin/<default branch>` that merges the picked rules into the project's settings, keeping the project's own choices, and runs the linters. Fix what they report within the diff cap. A rule whose findings do not fit leaves the PR and becomes a finding that `rs-health` proposes as a task (section 9). The settings are Protected, so the owner reviews and merges the PR.
15. **Next.** For an existing repository, offer `rs-health`. Then say that the Kit is ready: the owner starts and manages their own Sessions, which follow AGENTS.md, its Pull requests section included, and the engineering skills, while `./devctl check`, the guardrails and the merge guard hold the bar. Before the owner widens the Mode toward Flight, point to `rs-preflight` (Spec 3).

## 9. `rs-health`

`rs-health` is user-invoked. `rs-setup` offers it to existing repositories, and the owner can rerun it at any time. It never edits the repository: its output is a list of proposed standards tasks, which the owner picks from and hands to their own Sessions.

- **Reads:** the code; the output of `./devctl doctor` and `./devctl check`; the CI configuration and recent runs; README.md, ARCHITECTURE.md and the AGENTS.md tree; the feature map, the Patterns and `exceptions.toml`; and the last merged PRs with their review threads.
- **Audits** by rung, citing file:line or command output for every finding:
  - rung 1: recurring tasks done several ways, each with one proposed reference implementation and the check that would enforce it; safe interfaces that are missing and the bypasses they would ban; code that departs from an existing Pattern, the starter Patterns included; and code that hides or obscures an error, such as an empty catch, a broad except that carries on, an unhandled promise or a fallback that masks a failure. Failing fast and gracefully, and never obscuring an error, is the audit's base rule, which `rs-garden` also scans for (Spec 3);
  - rung 2: missing checks and test tiers, doctor gaps, Python floor settings the project's own rules replace, advisory Rules that a check could enforce, exceptions whose removal condition has been met, settings entries that match nothing, such as a `[kit] exclude`, `[map] unguided` or `[tests] unit` entry, and tool-settings rules the project lacks (section 8, step 14);
  - rung 3: AGENTS.md, ARCHITECTURE.md and README.md text that no longer matches the code, missing directory guides, gaps in the feature map, and dead code: the entries marked at Setup (section 8, step 4.5) and what the `dead-code` step cannot see, which the shared audit lists ([Spec 3](2026-10-16-metrics-and-gardening-design.md), section 10);
  - rung 4: gaps in the Protected set, CODEOWNERS and the ruleset;
  - review comments repeated across recent PRs that a rung could prevent.
- **Returns** proposed tasks, grouped by area. Each is one PR within the diff cap, with acceptance criteria, a test plan and the tasks it waits on. Their shape lives in `rs-health`'s references, which `rs-garden` reuses. The owner picks which tasks to keep. `rs-health` states each write, then writes the picked tasks to whatever tracker the owner's Harness reaches, for example through an MCP server or as GitHub issues, which it opens through `./devctl as worker gh` while Agent identity is on (G8). Otherwise it leaves them in the conversation. The Kit records no tracker setting, and devctl never talks to the tracker (section 1).

The audit is shared with the gardener. `rs-health` runs it once at adoption; `rs-garden` (Spec 3) reruns it over the changes since its last pass and adds new Corrections. The audit lives in `rs-health`'s `references/audit.md`, which `rs-garden` reads.

## 10. Testing

**Unit tests**, offline. Plans 2 and 3 built these:

- Lock reading and writing, and status classification.
- `init`: conflicts, seeded skips, symlinked targets, the never-overwrite rule, no git hook running from a tracked hooks path, and the listing of tool settings, hooks and workflows already in the repository.
- `sync`: unchanged files replaced; edited and deleted files made the project's own and never changed; `--revert` and its refusals; excluded paths never touched; project extensions untouched; the stack version winning over the common one.
- Each check step's rules, with fixture repositories: map, references, exceptions, removed tests, tautologies, evidence.
- The removed-test rule: a moved test passes, an undeclared removal fails, a declared one passes, and each removal is classed unit or behavioural by its path.

The new plans add:

- Plan 4: settings, with `[escalation]` read, a partial App record or Apps without a repository refused, and the removed tables refused. doctor's parsers against recorded GitHub responses and fake Harness executables: the ruleset in Walk, in Flight with Agent identity and in Flight without it, CODEOWNERS against `every_pr`, App items only with Agent identity on, and `--skills` adding and removing its temporary worktree at `HEAD`. Token minting, the `GIT_ASKPASS` helper and `rapid-ship app` against a local fake HTTP server and a fake `security`; these are labelled simulated. `devctl as` with fake `gh` and `git` executables and a local bare repository: each refusal, the token present only in the one child's environment and never in argv or output, and the exit codes.
- Plan 4's follow-ups: `[github] code_owner`, and doctor's CODEOWNERS item with a login and with a team on an organisation-owned repository; `rapid-ship app`'s organisation manifest flow and `--import-key` against a local fake HTTP server and a fake `security`, labelled simulated; Keychain items named by App ID, with two Apps' keys for one role on one machine; and, with `[roster]` out of devctl, a leftover `[roster]` table and an `[agents]` table refused with "rapid-ship does not run agents across several Providers; delete the table", no Harness sign-in item, and `--skills` probing Claude Code alone, only when `claude` is on `PATH`.
- Plan 5: `devctl hook` against recorded Claude Code event JSON: each rule's deny or ask, a command line split as the shell does, with `;`, `&&`, `||`, `|`, `&` and a newline joining commands, and subshells, `$( … )` and backticks giving commands of their own, G7 and G8 only with Agent identity on, no decision when no rule matches, G1 to G4 with unreadable settings, and the exit-code mapping. G3 denying `gh pr merge --admin` and each `gh api` form of section 4, REST and GraphQL, run directly and through `devctl as`, and each form of `git push` to the default branch, with `origin/HEAD` present and missing. The merge guard against a fake GitHub reader: `gh pr merge` run directly and through `devctl as`; passed, pending, failed and missing check runs; Protected paths at the base, renames by both paths, a ledger entry changed or removed, and entries added as `open` and as `implemented`, neither of them Protected; a merge without `--match-head-commit`, or naming another commit, denied with the exact retry; a denial when GitHub cannot be read or the guard itself fails; with Agent identity on, a merge that the Reviewer App approved at the head commit passing, and no review, another login's approval, an approval of an older commit and a later request for changes each denied, comments and dismissed reviews ignored, and reviews read page by page; with Agent identity off, no review read; unreadable settings denying every merge; and no read for any other command. Map rule 5's `task` and Lessons, map rule 8 and the `SKILL.md` rule, each failing the map step, the diff cap's count, exclusions and declaration, and the ledger rule. `doctor --settings` on fixture repositories, asking GitHub nothing, with an invalid key exiting 2 and naming the file and the key. The CI workflow's concurrency group. The Python starter Patterns and the Python performance Pattern passing map rule 5 on a new project. Each seed held to its loader. doctor's wiring item. PR 5.5's `dead-code` step against a simulated uv: vulture's findings and exit codes, deptry's report with every rule on, a blocked tool outranking a failed one, and a project without the tools or vulture's `paths` blocking the step. deptry's inline comment, the allowlist items in `pyproject.toml` and the lines that vulture and deptry read beyond a comment as suppressions, with an item that devctl cannot place on a line, and a line with two items, failing. doctor's Python floor and devctl exclusions items for the new settings. The Python seed passing the step.
- Plan 6: `[[stack]]` settings: names, directories inside the repository, duplicates, `agnostic` alone, and the old `stack` key rejected. `init --stack NAME=DIRECTORY`, and detection without it: nested roots, skipped vendored and generated directories, no root found, and nothing written. Each stack's steps in its directory with their names, from fake tools; the TypeScript steps blocked without `node_modules`; `--install`. The TypeScript suppressions, the `eslint:` and `type:` references, removed Vitest tests and tautologies. CODEOWNERS and `project.toml` rendered for two stacks. doctor's Node.js and TypeScript floor items. The `dead-code` step from a fake knip, with its issue types on the command line; knip's suppressions: `@public`, `@beta` and the items of `knip.jsonc`; and which of knip's `rules`, `include` and `exclude` settings `--include` overrides.
- Plan 7: the upstream lock (`verbatim` and `patched` files), every Kit skill through map rule 7, and `ruleset.json` passing doctor's ruleset check.
- The descope of 2026-10-26: `[escalation] kinds` and `revision_rounds` refused as unknown keys. The merge guard against a fake GitHub reader: its Walk denial, with and without Agent identity; its Flight denial of a body that declares a removed behavioural test, an overage of the diff cap or both, and no denial for a body whose `Removed tests:` entries all match `[tests] unit`; and the six denials in their order. Both root-guide seeds holding the first Rule's new text and the Pull requests section.

**Integration tests**, each labelled with what it needs: `init` on scratch repositories for each stack, after which `./devctl check` passes; from plan 5, a new Python project with an unused function and a declared dependency that nothing imports, which fails the `dead-code` step and no other step; `sync --in-place` between two template versions; and this repository's dog-food tests. The `init` tests need network access, for `uv sync` and pip-audit's lookups in the Python stack, and gitleaks on `PATH`. From plan 6, `init` on a scratch repository with a Python `backend/` and a React TypeScript `frontend/`, after which `./devctl check` passes. That test needs network access for `npm ci` and is labelled so.

**Spikes and live trials**, recorded under `docs/trials/`:

- **The hook spike (backlog PRO-139),** plan 5's first task, done on 2026-10-21 and 2026-10-22 and recorded in [its trial record](../../trials/2026-10-21-hook-spike.md). In Claude Code, Codex and agy, each in a lead Session, inside a subagent and in a headless Session, it recorded whether the wired hook events fire, whether Codex hooks can ask, how each Harness treats the hook's exit 1, exit 2, a hook timeout and the hook's deny answer, which fields each event carries, the review in Codex's `/hooks`, and the time a `./devctl --version` run takes, as a stand-in for `devctl hook`. agy ran only headless; its lead and subagent runs followed on 2026-10-26 (PRO-143). From the result, the owner kept G1 to G4 in the hook, made the Codex wiring without G5 a follow-up (PRO-142), and left agy until its interactive runs are done (PRO-143). Plan 5 wires Claude Code, `Monitor` included.
- `rapid-ship app` creating both Apps, then installing them on a second repository. On a test organisation: an admin creating the organisation's Apps and generating a key, and `--import-key` storing it, which the [organisation trial](../../trials/2026-10-26-organisation-trial.md) ran on 2026-10-26, with `./devctl doctor` passing with a team as the code owner.
- Agent identity on a scratch repository: `devctl as worker push` and `devctl as worker gh pr create`; a review posted with `devctl as reviewer gh` that GitHub shows as the Reviewer App's; whether GitHub takes the Reviewer App's approval, which [plan 4's trial](../../trials/2026-10-21-agent-identity.md) found it does not (section 8, step 7); a squash merge with `devctl as worker gh pr merge`; and GitHub refusing a merge while a review thread is unresolved or `devctl check` has not passed.
- The ruleset applied and read back by doctor, and doctor's answer on a GitHub Free private repository.
- **The Harness guardrails in Claude Code,** plan 5's Task 8, run on 2026-10-23 in headless Sessions and recorded in [its trial record](../../trials/2026-10-23-harness-guardrails.md): each deny rule and the ask rule, in the lead Session and inside a subagent. Every rule gave its expected decision and message. G5's ask showed as a denial, because a headless Session cannot ask, so the trial observed no ask prompt; the hook spike observed one. A follow-up that wires Codex or agy repeats this trial there. The merge guard on real PRs: it denies a merge while `devctl check` is pending or failing and a merge of a Protected-set PR, through `gh pr merge` and `devctl as worker gh pr merge`, and lets a passing, unprotected merge through; with Agent identity on, it denies a merge that the Reviewer App has not approved, and lets the same merge through once the Reviewer App approves its head; G3 denies a merge through `gh api` and a `git push` to the default branch.
- `rs-setup` on a new scratch repository with a Python `backend/` and a React TypeScript `frontend/`, and on an existing one, hello-rapid-ship, including `doctor --skills` in Claude Code and the tool-settings PR.
- `rs-health` on an existing repository, ending with the tasks the owner picked in a tracker that the Harness reaches.

**Dog-food:** this repository's CI runs `./devctl check --tier full`, whose `vendored` step runs `rapid-ship status --strict`.

## 11. Questions

The owner's reviews of PR #27 on 2026-10-16, 2026-10-19 and 2026-10-20, the owner's decisions of 2026-10-20 to descope running agents across several Providers and to ship the guardrail wiring for Claude Code alone in plan 5, and the owner's decisions of 2026-10-22 on the hook spike settled what this spec states. From the spike, G1 to G4 stay in the hook, and a follow-up wires Codex without G5 (PRO-142). Plan 4's live trial answered one more: the ruleset's approval count is `0`, and approval of the most recent push is off, with code-owner review required, because GitHub counts an approval only from someone with write access to the repository ([GitHub's documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)), and the Reviewer App has Contents: read (section 8, step 7.3). The owner's decision of 2026-10-21 answered another: one ruleset serves every setup, and code-owner review stays required in Flight without Agent identity too (section 8, step 8.6). At a count of `0`, an agent acting from the owner's account can merge a PR outside the Protected set in Flight anyway, since no file in it has a code owner. Code-owner review then also makes GitHub refuse an agent's merge of a Protected-set PR, unless the agent uses the admin bypass. That matters most in a Harness without Kit wiring, where no merge guard runs, although nothing there denies the agent the bypass either. The cost: the owner merges a Protected-set PR that their own account opened through the admin bypass in GitHub's web interface, as in Walk. The owner's decisions of 2026-10-26 settled the descope: Spec 2 is deleted, the merge guard enforces each Mode, `[escalation]` keeps only `every_pr`, the seeded root guide's Pull requests section replaces a review skill, and `rs-health` writes the tasks the owner picks to whatever tracker the Harness reaches, with no tracker setting. In Flight the guard leaves only a declared removed behavioural test to the owner, not a removed unit test, so `[tests] unit` stays. The questions still open follow.

### Open

To be settled by a spike, a trial or the owner. No drafter proposal is waiting.

- **agy wiring (PRO-143).** agy's interactive runs of 2026-10-26 are in [the spike's record](../../trials/2026-10-21-hook-spike.md#agys-interactive-runs-pro-143). Its hooks fire in a lead Session and inside a subagent, a deny holds in each, and exit 1, exit 2 and a hook timeout block the call. A hook's ask adds its reason to a prompt that agy shows anyway, but in `accept-edits` mode an ask on a file write gives no prompt. The owner decides whether a follow-up wires agy, and whether that wiring omits G5. Until its wiring lands, agy is a Harness without Kit wiring (section 4), as Codex is until PRO-142 lands.
- **`"onFailure": "block"` in the Claude Code seed.** From v2.1.295, Claude Code documents this handler setting, which blocks the call when the hook fails or times out, where the default lets it through (section 4). The seed leaves it unset. Setting it would block a call whenever the hook fails or times out: a merge that the guard could not finish, but also every wired call while uv, Python or devctl is broken, and any call that meets an internal error of the hook. The hook spike did not exercise it. The owner decides whether the seed sets it.
- **Whether an App manager may generate a shared App's key (PRO-105).** A team member gets their key for an organisation's App from an organisation admin, who generates it in the App's settings, under Credentials, Key pairs, New key (sections 3 and 8). Whether an App manager who is not an admin may generate one is unverified. The [organisation trial](../../trials/2026-10-26-organisation-trial.md) of 2026-10-26 ran with no developer account, and the owner decided the same day to leave the question unverified. The trial showed the rest working: an admin's `rapid-ship app` created both Apps on the organisation, and `--import-key` stored keys that the admin generated, after which `./devctl doctor` passed with a team as the code owner. GitHub offers an App managers page for each App, which says its people "can manage settings, permissions and webhooks", and an organisation role, Apps manager, for every App the organisation owns. Neither says whether a manager may create a key. If a member who is not an admin, granted on both Apps' App managers pages, can click New key, each developer could generate their own key instead.
