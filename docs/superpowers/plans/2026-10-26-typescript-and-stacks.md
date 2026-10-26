# TypeScript Stack and Several Stacks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support a Python backend with a React TypeScript frontend from day one. `project.toml` and the lock list each stack with its directory as `[[stack]]` tables. `rapid-ship init --stack NAME[=DIRECTORY]` writes each stack's files under its directory, and without `--stack` it proposes the stack roots it finds and writes nothing. `./devctl check` runs the common steps once and each stack's steps in its directory. The TypeScript stack brings Prettier, ESLint, `tsc --noEmit`, knip, Vitest and `npm audit`, with npm, its guardrail settings, a React skeleton, its starter Patterns, doctor's Node.js and floor items, and CI support. This brings part of backlog item PRO-108 into scope; the rest of monorepo support stays deferred.

**Architecture:** Five PRs. devctl learns several stacks first (6.1a), so that the rapid-ship CLI (6.1b) and the TypeScript checks (6.2a, 6.2b) build on it at the same time; the TypeScript templates and CI (6.3) come last. A stack's check step runs through `StackStep`, which hands the step a `CheckContext` whose `directory` is the stack's and names the result. A file belongs to the stacks of the innermost stack directory that holds it, and the exceptions, file-size and diff steps and the references read it in those stacks' forms. rapid-ship renders a stack's templates under its directory, the files under a stack layer's `__root__/` at the repository root, and the repository-level seeds (`project.toml`, CODEOWNERS, the root guide) from every stack through derived template variables that `rapid_ship/kit/stacks.py` computes.

**Tech Stack:** Python 3.12+ standard library (`tomllib`, `json`, `re`), PyYAML, git 2.31+, uv, pytest, Ruff, mypy. For the TypeScript stack, the latest releases on npm on 2026-10-26 that install together: Node.js 24 with npm 11, TypeScript 6.0.3 (typescript-eslint 8.72.0 accepts `>=4.8.4 <6.1.0`, so not 7.0.2), ESLint 10.13.0 with `@eslint/js` 10.0.1, typescript-eslint 8.72.0, eslint-plugin-react-hooks 7.1.1 and globals 17.13.0, Prettier 3.9.10, Vitest 5.0.5 with jsdom 30.1.3, `@testing-library/react` 16.3.3 and `@testing-library/dom` 10.4.2, Vite 8.3.5 with `@vitejs/plugin-react` 6.1.2, knip 6.43.0, React and React DOM 19.3.1 with `@types/react` and `@types/react-dom` 19.3.0. `actions/setup-node` v7.1.0, commit `949feb2413d6458794dcd2491c4babbbce0c15c1`.

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), sections 3 (`init` stacks and detection, the lock), 4 (Kit contents, settings files, starter Patterns, the Protected set, CI, TypeScript guardrail settings), 5 (steps, dead code, several stacks, output, references, exceptions, diff policy), 6 (`doctor`) and 10 (plan 6's tests, the integration test, the live trial). Plan 6 of 7 in the [plan index](2026-10-14-kit-and-setup.md), whose Conventions, Layout, Shared interfaces and "Plan 6" outline bind this plan.

**Status:** planned on 2026-10-26 from `main` at `ee43cef`, while plan 7 is planned beside it. This document lands in PR 6.1a.

**Owner steps:** Task 10 Step 1 (approve the TypeScript seed's packages), Task 13 (the live trial), and pushing each commit that edits this repository's `.github/workflows/` (Task 12), which the Worker App cannot push. The controller never dispatches an Owner step to an implementer, and no agent runs one.

## Order and parallel work

Task numbers follow the index's outline. Within a PR, tasks run in the order listed.

| PR | Branch, base | Tasks | Builds | Counted lines, estimated |
| --- | --- | --- | --- | --- |
| 6.1a | `plan6-stacks`, on `main` | 1, 4, 3a, 5 | devctl: `[[stack]]` settings and lock reading, each stack's steps in its directory, file ownership, references per stack, doctor per stack, the JSONC reader; this repository's `project.toml` | about 1,100 |
| 6.1b | `plan6-stacks-init`, on 6.1a | 2, 3b | rapid-ship: `init --stack NAME[=DIRECTORY]`, detection and its proposal, the lock's `[[stack]]`, rendering under directories, the repository seeds from every stack | about 1,350 |
| 6.2a | `plan6-ts-steps`, on 6.1a | 6, 9 | devctl: the TypeScript steps, knip, `check --install`, doctor's `node`, `npm` and TypeScript floor items | about 900 |
| 6.2b | `plan6-ts-rules`, on 6.1a | 7, 8 | devctl: the TypeScript suppressions and knip's allowlist, the `eslint:`, `type:` and `test:` references, the Vitest diff policy | about 1,150 |
| 6.3 | `plan6-ts-templates`, on 6.1b, with 6.2a and 6.2b merged in before review | 10, 11, 12, 13 | rapid-ship: the TypeScript templates and starter Patterns, CI's `setup-node` and `--install`, the integration tests, the live trial | about 850 |

- **6.1a first.** Every other PR uses its `ProjectStack`, `CheckContext.directory`, `StackStep`, `ProjectSettings.owners` and `devctl/jsonc.py`.
- **Then 6.1b, 6.2a and 6.2b at the same time,** each on its own branch from 6.1a's head, built and reviewed in parallel: three Workers, the most Walk advises. They share no source or test file. 6.1b changes only `rapid_ship/` outside its devctl templates, `tests/test_kit_*.py` and `tests/fixtures/kit/`. 6.2a and 6.2b change only devctl templates, their vendored copies and `tests/devctl/`. 6.2a owns `check/__init__.py`, `check/filesize.py`, `cli.py`, `doctor_local.py`, `doctor_rules.py`, `doctor_typescript.py`, `check/stacks/typescript.py` and `tests/devctl/check_workspace.py`. 6.2b owns `check/exceptions.py`, `check/references.py`, `check/diff.py`, `check/stacks/typescript_suppressions.py`, `check/stacks/typescript_references.py` and `check/stacks/vitest.py`, and keeps its test helpers in its own test files.
- **Files they still share:** `.rapid-ship/kit.lock`, which each PR that syncs devctl changes. Never resolve it by hand: take either side, then run `uv run rapid-ship sync --in-place` and commit the result. The documents `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, the plan index and Spec 1's status line: each PR edits its own paragraph, and a conflict there is merged by hand.
- **6.3 last.** Tasks 10 and 11 start once 6.1b is merged, because they need rendering under a directory and the stack registry. Task 12 needs 6.2a's `--install`. The integration tests and Task 13 run only after 6.2a and 6.2b are merged into the branch.
- **Merge order:** 6.1a; then 6.1b, 6.2a and 6.2b in the order their reviews finish; then 6.3. After each squash merge, retarget the next PR to `main` and merge `main` into it as the Global Constraints say.
- **Outside this plan:** the PRO-146 worktree edits `settings.py`, `doctor_github.py`, `doctor_local.py` and their tests, as 6.1a does; start 6.1a after it merges, or merge it in first. Plan 7's planning commit edits the same index sentence and table rows as this document. Plan 7's PR 7.1 edits `kit.toml` and the root guide template, which 6.1b restructures: land 6.1b first, or move 7.1's `kit.toml` edits onto the `[new_project]` table when it rebases.

## Owner decisions needed

1. Approve the TypeScript seed's packages at the pins in Tech Stack, and their download in the integration tests and the trial. Recommendation: approve (Task 10 Step 1).
2. Name Node.js 24 as the supported major: the seed's `engines.node = "24.x"` and CI's `node-version: "24"`. Recommendation: 24, the active LTS, which jsdom 30.1.3 requires (`^24.15.0`).
3. Hold the next Kit tag until PR 6.3 merges. Recommendation: hold; between 6.1a and 6.2a a TypeScript stack blocks the step list, and 6.1b changes the lock's format.
4. Keep the agnostic stack at the repository root (`directory = "."`), since it has no files or steps of its own. Recommendation: yes; both CLIs refuse another directory.

## Deviations from the index's outline

- 6.1 and 6.2 each split in two (6.1a and 6.1b, 6.2a and 6.2b): each is estimated over the 1,500-line diff cap, and the split lets three PRs build at once.
- Task 1 keeps devctl's settings and its reading of the lock, and rapid-ship's lock writer moves to Task 2: `rapid-ship` alone writes the lock, so it changes with `init`.
- Task 3 splits into 3a, doctor's items (devctl, 6.1a), and 3b, the rendered seeds (rapid-ship, 6.1b). Task 5's rewrite of this repository's `project.toml` moves into Task 1, because the pre-commit hook's `devctl check` refuses the old key from that commit on.
- `devctl/jsonc.py` lands in 6.1a, and `typescript` joins devctl's stack names there, so 6.2a and 6.2b can build in parallel; a TypeScript stack blocks the step list until 6.2a.
- `codeowners_problems` takes every stack in one call, not one call per stack as the index sketches, so the common Protected set is checked once.
- A stack in a subdirectory gets a seeded stack guide, `<directory>/AGENTS.md`: map rule 2 requires a guide in every top-level directory, and Spec 1 section 4 seeds none there.
- The TypeScript seed adds `.prettierignore`: `prettier --check .` would otherwise check Kit-managed files and the seeded Markdown, which Spec 1 section 4 keeps out of the project's tools.
- The npm package name is `{{package}}`, because npm requires a lowercase name and `{{project_name}}` may hold capitals.
- The `agnostic/` template layer goes, and the Python layer's root guide, CODEOWNERS and `project.toml` move to `common/`: those files now render from every stack.

## Global Constraints

- Commands (index, Conventions): `rapid-ship init [--stack NAME[=DIRECTORY]]... [--owner LOGIN] [--repository OWNER/NAME] [--name NAME] [--package NAME]`; `devctl check [--tier {fast,full}] [--json] [--base REV] [--pr-body PATH] [--install]`. Exit codes: 0 success; 1 a check failed or a request was refused; 2 the command could not run, and 2 wins over 1. `init` without `--stack` proposes and exits 2 (Spec 1 section 3).
- Stack names: `python`, `typescript`, `agnostic`. A directory is `"."` or a repository-relative POSIX path inside the repository, not a symlink and not under one. Two tables never name the same stack and directory. `agnostic` stands alone, at `"."`.
- Step names: with one stack at `"."`, a stack step keeps its name, such as `lint`. Otherwise it is `<step> (<directory>)`, such as `lint (frontend)` or `lint (.)`, and `<step> (<directory>, <stack>)` when another stack shares its directory.
- Step order: each stack's fast steps (`format`, `lint`), stack by stack; then `map`, `exceptions`, `file-size`, `kit`; then each stack's full steps; then `secrets`, `workflows`, `diff`, `evidence`; then the project's steps. With one Python stack at the root, this is today's order exactly. `check --install` puts one `install` step per TypeScript stack first.
- Stacks are sorted by `(directory, name)` everywhere: in `ProjectSettings.stacks`, the lock, `project.toml` and step order.
- Ownership: a file belongs to the stacks whose directory is the innermost one that holds it, one or two stacks; outside every stack directory it has only the forms every stack shares, gitleaks's and zizmor's (Spec 1 section 5).
- Source extensions for `file-size`: `.py`, `.pyi` for Python; `.ts`, `.tsx` for TypeScript; every file for agnostic and for a file outside every stack.
- TypeScript commands, from the stack's directory, each tool from `node_modules/.bin` by absolute path: `prettier --check .`; `eslint --max-warnings 0 .`; `tsc --noEmit`; `knip --include files,dependencies,unlisted,binaries,unresolved,exports,types,enumMembers,namespaceMembers`; `vitest run`; and `npm audit --json` through npm. knip exits 0 to pass, 1 to fail, 2 to block (Spec 1 section 5).
- devctl source is edited only under `rapid_ship/templates/common/tools/devctl/`. Run `uv run ruff format <files>` and `uv run ruff check <files>` on the changed templates, then `uv run rapid-ship sync --in-place`, before each test run that expects a pass. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit the vendored copy or the lock by hand.
- devctl starts processes only through `process.run_process`, called through the module, and depends only on PyYAML and PyJWT; this plan adds no dependency to devctl or to this repository.
- File-size cap 500 lines: `check/stacks/python.py` (476 lines) gains only `SOURCE_EXTENSIONS`; `command_line.py` (492) is untouched; TypeScript code goes into new modules, `check/stacks/typescript*.py`, `check/stacks/vitest.py` and `doctor_typescript.py`.
- No backward compatibility before GA: devctl refuses the old top-level `stack` key in `project.toml` with how to rewrite it, and the project rewrites the file. The one reader of an old format is the lock's, in both CLIs, which Spec 1 section 3 asks for: only `rapid-ship` writes the lock, and the `diff` step reads the lock at the base.
- The comment rule: no comment, docstring, message or test name cites a plan, spec, section, ADR, PR, trial or rule ID. Seeds comment a key only for its contract.
- No `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression carries an `rs-exception` marker and an entry. Write tests first. A test module's docstring starts `Offline:` and names what it simulates, or names the network, Node.js or gitleaks it needs. A blocked, skipped or simulated check never counts as passed, so no test skips for a missing tool.
- Keep each existing test's name and change its body. A test renamed or removed against the PR's base goes under `Removed tests:` in the PR body, with the test that now covers it.
- Agent identity is on here: agents push with `./devctl as worker push` and write to GitHub with `./devctl as <role> gh`. G5 asks before each edit of a Protected path, such as `.rapid-ship/project.toml`, `pyproject.toml` or an `AGENTS.md`; in a headless Session the owner makes that edit.
- Each PR's base is the branch in the table; each touches the Protected set, so the owner merges it in GitHub's web interface. After the PR below squash-merges, confirm `main`'s tree equals its head (`git diff --quiet origin/main <that branch>`), retarget the next PR with `./devctl as worker gh api -X PATCH repos/proxy-hatch/rapid-ship/pulls/<n> -f base=main`, run `git merge -s ours origin/main`, push and wait for its `devctl check`.
- Each PR stays under 1,500 counted lines. When `diff` counts more, split at a task boundary, or declare `Over the diff cap: <reason>` only after the owner accepts the overage.
- Each PR's last task runs and records `uv run pytest -q`, `./devctl check --tier fast`, `uv run rapid-ship status --strict`, `./devctl check --tier full --base <PR base> --pr-body <body file>` and, when docs change, `npm --prefix website run build` in the Verification record. The integration tests need network access, gitleaks 8.30.1, and from 6.3 Node.js 24 with npm.
- Ruff formats the `python` code blocks of this file: keep them valid Python in Ruff's layout.
- Commit trailer: `Co-Authored-By: <the model that writes the commit>`, such as `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A Python stack at the root beside a TypeScript stack in `frontend/`.** The root stack's directory holds the other's. Expected: `frontend/src/a.ts` belongs to TypeScript alone, `src/app/a.py` to Python, and the steps are named `lint (.)` and `lint (frontend)`. Task 1's `test_owners_are_the_stacks_of_the_innermost_directory` and Task 4's `test_step_names_follow_the_stacks` pin it.
2. **Detection in a repository with vendored or generated roots.** Inputs: `node_modules/x/` and `.venv/lib/x/` holding marker files, a `dist/` or `build/` copy, and a `package.json` without `tsconfig.json`. Expected: none of them is proposed, nothing is written and `init` exits 2. Task 2's `test_detection_finds_nested_roots_and_skips_vendored_directories` pins it, and Task 10 adds the TypeScript rows.
3. **A TypeScript stack before `npm ci`.** Inputs: no `node_modules`, no `package-lock.json`, and `--install` without a lock. Expected: each TypeScript step blocks and names `npm ci` in that directory, or `npm install` and committing `package-lock.json` without a lock; nothing passes. Task 6's `test_a_missing_tool_blocks_with_the_install_command` and `test_install_without_a_lock_blocks` pin it.
4. **A knip setting that hides findings.** Inputs: `rules: {"exports": "off"}`, `ignoreExportsUsedInFile`, two allowlist items on one line, an item in `workspaces`, and knip settings in `knip.json` or `package.json` instead of `knip.jsonc`. Expected: doctor's floor names each kind switch that `--include` does not override; the exceptions step fails each unmarked or unplaceable item and each other settings file. Tasks 6, 7 and 9 pin it.
5. **A Vitest test whose title is not a plain string.** Inputs: a template literal with `${}`, an identifier, and `test.each(table)("x %s", ...)`. Expected: the diff step lists such a test as not checked and never reports it removed; a plain title moved to another file is not a removal. Task 8's `test_a_title_that_is_not_a_plain_string_is_not_checked` pins it.

## File Structure

`devctl/` means `rapid_ship/templates/common/tools/devctl/devctl/`; `sync` writes its vendored copy.

| File | PR | Responsibility |
| --- | --- | --- |
| `devctl/settings.py` | 6.1a | `StackName`, `ProjectStack`, `under`, `ProjectSettings.stacks` and `owners` |
| `devctl/jsonc.py` | 6.1a | JSON with comments and trailing commas, for `tsconfig.json` and `knip.jsonc` |
| `devctl/check/__init__.py` | 6.1a, 6.2a | Each stack's steps, their names and order, `StackStep`; 6.2a adds TypeScript and `--install` |
| `rapid_ship/kit/stacks.py` | 6.1b | Stack names, `--stack` options, detection and its proposal, each stack's `StackKit`, the derived template variables |
| `rapid_ship/templates/common/.rapid-ship/project.toml` | 6.1b | One `project.toml` seed for every set of stacks |
| `rapid_ship/templates/<stack>/AGENTS.md` | 6.1b, 6.3 | The stack guide, seeded at `<directory>/AGENTS.md` for a stack in a subdirectory |
| `rapid_ship/templates/<stack>/__root__/` | 6.1b, 6.3 | A stack's files at the repository root: its starter Patterns |
| `devctl/check/stacks/typescript.py` | 6.2a | The TypeScript steps, `install`, `SOURCE_EXTENSIONS` |
| `devctl/doctor_typescript.py` | 6.2a | doctor's `node`, `npm` and TypeScript floor items |
| `devctl/check/stacks/typescript_suppressions.py` | 6.2b | The TypeScript suppression forms, and knip's allowlist items in `knip.jsonc` |
| `devctl/check/stacks/typescript_references.py` | 6.2b | The `eslint:` and `type:` references for TypeScript |
| `devctl/check/stacks/vitest.py` | 6.2b | Vitest test identities by title chain, and tautologies |
| `rapid_ship/templates/typescript/` | 6.3 | The TypeScript seeds, React skeleton, starter Patterns and stack guide |

---

## PR 6.1a: devctl reads several stacks (`plan6-stacks`, on `main`)

### Task 1: `[[stack]]` in devctl's settings and lock reader, and the JSONC reader

**Files:**
- Modify: `devctl/settings.py`; `devctl/check/kit.py` (`_parsed_lock`); `rapid_ship/templates/python/.rapid-ship/project.toml:2` and `rapid_ship/templates/agnostic/.rapid-ship/project.toml:2`; this repository's `.rapid-ship/project.toml:2`, in place; `tests/devctl/check_workspace.py` (`project_settings`, and a new `stack_table`)
- Create: `devctl/jsonc.py`, `tests/devctl/test_devctl_settings_stacks.py`, `tests/devctl/test_devctl_jsonc.py`
- Modify, for the key's rewrite: each test that writes `stack = "<name>"` into a `project.toml` (`grep -rln 'stack = ' tests`, about 110 lines in 30 files) and each `project_settings(stack=...)`; `tests/test_kit_contents.py::test_project_settings_seed_has_the_spec_defaults` and `tests/devctl/test_devctl_kit_step.py` (bodies only)

**Interfaces:**
- Produces:

```python
# devctl/settings.py
StackName = Literal["python", "typescript", "agnostic"]
STACK_NAMES: tuple[StackName, ...] = ("python", "typescript", "agnostic")


@dataclass(frozen=True)
class ProjectStack:
    name: StackName
    directory: str  # "." or a POSIX path inside the repository, without "./" or a trailing "/"


def under(directory: str, path: str) -> str: ...  # ("backend", "a.toml") -> "backend/a.toml"


@dataclass(frozen=True)
class ProjectSettings:
    stacks: tuple[ProjectStack, ...]  # replaces stack; sorted by (directory, name), at least one
    ...  # the other fields as before

    def owners(self, path: str) -> tuple[ProjectStack, ...]: ...  # () outside every stack


# devctl/jsonc.py
def loads(text: str) -> object: ...  # ValueError for text that is not JSON once comments go


# tests/devctl/check_workspace.py
def stack_table(name: str, directory: str = ".") -> str: ...  # one [[stack]] table, as TOML
```

- `PROJECT_KEYS` gains `"stack": frozenset({"name", "directory"})`; `""` keeps `"stack"`. `Stack` is renamed `StackName`; `doctor_rules.py` imports the new name.
- `load_project` reads `stack` before the other tables:
  - a string: `.rapid-ship/project.toml: stack = "<value>" is no longer read; rewrite it as one [[stack]] table with name = "<value>" and directory = "."`;
  - absent: `.rapid-ship/project.toml [[stack]]: required; add one table for each stack, with its name and directory`;
  - each table through `_Table(item, f"{PROJECT} [[stack]] #{n}", PROJECT_KEYS["stack"])`: `name` through `choice` (`... #1 name: expected python or typescript or agnostic`); `directory` required, normalised by `_inside_repository`, and an existing directory with no symlink at it or above it under the root, else `... #1 directory: expected a directory inside the repository that is not a symlink`;
  - `.rapid-ship/project.toml: two [[stack]] tables name <name> in <directory>`;
  - `.rapid-ship/project.toml: the agnostic stack cannot sit beside another stack`, and `... #<n> directory: the agnostic stack's directory is "."`.
- `owners` returns the stacks whose directory is the longest one that is `"."`, equals `path`'s directory or is a prefix of `path` at a `/`.
- `check/kit.py` reads the lock's `stack` as a string in `STACK_NAMES`, the older form, or as a list of tables, each with a `name` in `STACK_NAMES` and a string `directory`; anything else is `stack must be [[stack]] tables with name and directory`. The `diff` step reads the base's lock with the same parser.
- `jsonc.loads` drops `//` and `/* */` comments and a trailing comma before `}` or `]`, outside strings, then calls `json.loads`.
- The Python and agnostic seeds, and this repository's `project.toml`, replace `stack = "<name>"     # python or agnostic` with Spec 1 section 4's two comment lines and one table at `"."`; the header comment and the blank line stay. Ruling: the comment names `typescript` from this PR on, because the loader accepts it.
- Until Tasks 4 and 3a replace them, each reader of `ProjectSettings.stack` reads `project.stacks[0].name`, so the tree stays green after this task.

- [ ] **Step 1: write the failing tests.** `test_devctl_settings_stacks.py`, docstring `Offline: [[stack]] tables in fixture repositories.`:
  - `test_stacks_load_sorted_and_normalised`: tables for `typescript` in `./frontend/` and `python` in `backend`, in that order, load as `(ProjectStack("python", "backend"), ProjectStack("typescript", "frontend"))`.
  - `test_invalid_stacks_raise_settings_error`, parametrized over each message above: the old key, no table, `name = "go"`, an unknown key `path` (`... #1: unknown key 'path'; it accepts directory, name`), no `directory`, the directories `../x`, `/x`, `a\\b`, `missing`, a symlink `link` and `link/sub`, two `python` tables in `backend`, `agnostic` beside `python`, and `agnostic` in `docs`.
  - `test_owners_are_the_stacks_of_the_innermost_directory`: with `python` in `.`, `python` in `frontend` and `typescript` in `frontend`, `owners("frontend/src/a.ts")` is both `frontend` stacks, `owners("src/app/a.py")` is `python` in `.`, and with only `python` in `backend`, `owners("README.md") == ()`.
  - In `test_devctl_kit_step.py`, `test_both_lock_forms_are_read`: a lock with `stack = "python"` and one with a `[[stack]]` table give the same managed paths; `stack = "go"` makes the `kit` step blocked.
  - `test_devctl_jsonc.py`, docstring `Offline: the JSONC reader.`: `test_jsonc_reads_comments_and_trailing_commas` turns `'{\n  // c\n  "a": [1, 2,], /* b */ "s": "// kept",\n}'` into `{"a": [1, 2], "s": "// kept"}`; `test_invalid_jsonc_raises_value_error` on `'{"a": }'`.
  - `test_project_settings_seed_has_the_spec_defaults` expects `"stack": [{"name": stack, "directory": "."}]`.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_settings_stacks.py tests/devctl/test_devctl_jsonc.py -q`; expected FAIL with `ImportError: cannot import name 'ProjectStack'`.
- [ ] **Step 3: implement** the settings, the lock reader, the JSONC reader and the seeds; rewrite this repository's `project.toml` (Protected; G5 asks) and the test fixtures with `stack_table`; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl tests/test_kit_contents.py tests/test_kit_seed_keys.py -q`; expected PASS. `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 5: commit** `feat: read [[stack]] tables in devctl's settings`.

### Task 4: `check` for each stack

**Files:**
- Modify: `devctl/check/steps.py` (`CheckContext`, `CommandStep.run`), `devctl/check/__init__.py` (`core_steps`), `devctl/check/stacks/python.py` (`SOURCE_EXTENSIONS`; `AuditStep` runs in `context.directory`), `devctl/check/stacks/python_dead_code.py` (`DeadCodeStep` reads and runs in `context.directory`; `toml_allowlist(text, path)`), `devctl/check/exceptions.py` (`scan`, `ExceptionsStep.run`), `devctl/check/filesize.py` (`line_counts`), `devctl/check/references.py` (`resolve`), `devctl/check/map.py` (`_pattern_problems`, `_rule_problem`), `devctl/check/diff.py` (`DiffStep.run`)
- Create: `tests/devctl/test_devctl_check_stacks.py`
- Modify: `tests/devctl/test_devctl_references.py`, `test_devctl_exceptions_step.py`, `test_devctl_exceptions_allowlists.py`, `test_devctl_filesize_step.py`, `test_devctl_dead_code.py` (call sites only)

**Interfaces:**
- Consumes: `ProjectStack`, `ProjectSettings.owners`, `under` (Task 1).
- Produces:

```python
# devctl/check/steps.py
@dataclass(frozen=True)
class CheckContext:
    repo: Repo
    project: ProjectSettings
    base: str | None
    pr_body: str | None
    stack: ProjectStack | None = None  # the stack whose step runs; None for a common step

    @property
    def directory(self) -> Path: ...  # repo.root / stack.directory, or repo.root


# devctl/check/__init__.py
def stack_steps(name: StackName) -> tuple[list[Step], list[Step]]: ...  # (fast, full)
def step_name(step: str, stack: ProjectStack, stacks: Sequence[ProjectStack]) -> str: ...
def base_name(name: str) -> str: ...  # "lint (frontend)" -> "lint"


@dataclass
class StackStep:  # not frozen: Step's members are settable
    step: Step
    stack: ProjectStack
    name: str
    tier: Tier

    def run(self, context: CheckContext) -> StepResult: ...


# devctl/check/references.py
def resolve(reference: str, context: CheckContext, holder: str) -> str | None: ...


# devctl/check/stacks/python_dead_code.py
def toml_allowlist(text: str, path: str = PYPROJECT) -> tuple[list[AllowlistItem], list[str]]: ...
```

- `stack_steps("python")` is `([FORMAT, LINT], [TYPES, CONTRACTS, DeadCodeStep(), TESTS, AuditStep()])`, `stack_steps("agnostic")` is `([], [])`, and any other name raises `ValueError("devctl has no check steps for the <name> stack")`, which blocks the step list through `_blocked_on_error`. 6.2a adds `typescript`.
- `core_steps` builds the order of Global Constraints, wrapping each stack step in `StackStep(step, stack, step_name(step.name, stack, project.stacks), step.tier)`. `StackStep.run` calls `step.run(dataclasses.replace(context, stack=self.stack))` and returns the result with `name=self.name`.
- `CommandStep.run`, `AuditStep`, `DeadCodeStep` and `_deptry` run in `context.directory` and read `pyproject.toml` there. A project step runs as a common step, at the root.
- `exceptions.scan(root, files, managed, project)`: a `.py` or `.pyi` file with a `python` owner gets `_python_lines`; a `pyproject.toml` directly in a Python stack's directory gets `_pyproject_lines`, and `ExceptionsStep.run` appends `toml_allowlist(text, path)[1]` for it; every other file gets `_text_lines`. `toml_allowlist`'s messages name `path` where they named `pyproject.toml`.
- `filesize.line_counts(root, files, source_roots, managed, project)` counts a file whose owners' `SOURCE_EXTENSIONS` hold its suffix, and every file when an owner is agnostic or it has none.
- `resolve(reference, context, holder)`: `holder` is the Pattern's `reference` path, or the guide that states the Rule. `check:<step>` resolves when a common step, or a step of a holder's stack (any stack when the holder has none), has that base name. `ruff:`, `banned:`, `contract:` and `type:` resolve against the `pyproject.toml` of the holder's Python stack, and their messages name that file by its repository path; `type:<path>` compares `path` relative to that directory with mypy's `files` and `exclude`. A holder with no Python stack gives `<reference>: unknown reference kind <kind> for <holder>`. `test:<path>::<name>` reads Python identities for a `.py` file and keeps the word search for any other file until 6.2b.
- `DiffStep.run` applies the removed-test, tautology and autouse rules to the changes whose owners include a Python stack.

- [ ] **Step 1: write the failing tests.** `test_devctl_check_stacks.py`, docstring `Offline: each stack's check steps in fixture repositories, with fake tools on PATH.`:
  - `test_one_python_stack_at_the_root_keeps_the_step_names`: `[step.name for step in core_steps(project)]` equals `test_devctl_step_order.PYTHON`.
  - `test_step_names_follow_the_stacks`: `python` in `backend` and `worker` gives `format (backend)`, `lint (backend)`, `format (worker)`, `lint (worker)`, `map`, `exceptions`, `file-size`, `kit`, then `types`, `contracts`, `dead-code`, `tests`, `audit` for `backend` and then `worker`, then `secrets`, `workflows`, `diff`, `evidence`. `step_name("lint", ProjectStack("python", "."), (ProjectStack("python", "."), ProjectStack("typescript", "frontend"))) == "lint (.)"`, and with `python` and `typescript` both in `app`, `"lint (app, python)"`.
  - `test_a_stack_step_runs_in_its_directory`: a fake `uv` logs its working directory; `format (backend)` ran in `<root>/backend`, and `dead-code (backend)` read `backend/pyproject.toml`.
  - `test_a_stack_without_steps_blocks_the_step_list`: `typescript` in `frontend` gives one result, `blocked`, named `step list`, with the detail `ValueError: devctl has no check steps for the typescript stack`.
  - `test_suppressions_are_read_in_their_owners_forms`: `python` in `backend`; `x = 1  # noqa: E501` unmarked in `backend/src/app/a.py` fails, and the same line in `web/a.py` is no suppression; an unmarked `ignore_names` item in `backend/pyproject.toml` fails with `backend/pyproject.toml:4: suppression vulture.ignore_names:x needs ...`, and two items on its line give `backend/pyproject.toml:4: vulture.ignore_names holds 2 items on one line; ...`.
  - `test_file_size_counts_each_owners_source_files`: `python` in `backend`, `source_roots = ["backend/src/app", "docs/src"]`; a 501-line `backend/src/app/a.py` fails, a 501-line `backend/src/app/notes.txt` is not counted, and a 501-line `docs/src/x.txt` fails.
  - `test_references_resolve_against_the_holders_stack`: `python` in `backend` and `worker`, only `backend/pyproject.toml` selecting `BLE`. `resolve("ruff:BLE001", ctx, "backend/src/app/errors.py") is None`; for the holder `worker/src/w.py` it is `ruff:BLE001: Ruff does not select BLE001 in worker/pyproject.toml`; for `README.md` it is `ruff:BLE001: unknown reference kind ruff for README.md`. `check:lint` resolves for `backend/AGENTS.md` and for `AGENTS.md`, and `check:nope` gives `check:nope: no devctl check step is named nope`. `type:backend/tests/test_inputs.py` resolves with `files = ["src", "tests"]` in `backend/pyproject.toml`.
  - `test_the_diff_rules_apply_to_the_python_stacks_files`: `python` in `backend`; a test removed from `backend/tests/test_a.py` fails undeclared, and one removed from `scripts/test_b.py` is not reported.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_check_stacks.py -q`; expected FAIL with `ImportError: cannot import name 'step_name'`.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q`; expected PASS, the step-order, references, exceptions, file-size, dead-code and diff tests unchanged in what they assert, apart from a `pyproject.toml` message that now names its repository path.
- [ ] **Step 5: commit** `feat: run each stack's check steps in its directory`.

### Task 3a: doctor for each stack

**Files:**
- Modify: `devctl/doctor_local.py` (`_guardrail_item`, `_exclusions_item`, `local_items`), `devctl/doctor_rules.py` (`codeowners_problems`), `devctl/doctor_github.py:135`
- Create: `tests/devctl/test_devctl_doctor_stacks.py`
- Modify: `tests/devctl/test_devctl_doctor_github.py` and `test_devctl_doctor_github_limits.py` (call sites only)

**Interfaces:**
- Produces:

```python
# devctl/doctor_rules.py
def protected_settings(stacks: Sequence[ProjectStack]) -> tuple[str, ...]: ...
def codeowners_problems(
    text: str, every_pr: bool, code_owner: str, stacks: Sequence[ProjectStack]
) -> list[str]: ...
```

- `protected_settings` gives each Python stack's `PYTHON_PROTECTED_PATHS` under its directory, in stack order, such as `backend/pyproject.toml` and `backend/**/ruff.toml`. In Flight, `codeowners_problems` requires `PROTECTED_PATHS` and `protected_settings(stacks)`; 6.2a adds TypeScript's.
- `local_items` gives one floor item per Python stack, reading `pyproject.toml` in its directory, named `Python guardrail settings` with one stack at the root and `Python guardrail settings (<directory>)` otherwise.
- `_exclusions_item` reads the root `pyproject.toml` only. It checks Ruff, mypy, vulture, deptry and pytest only with a Python stack at `"."`, because a stack's tools run in its directory and reach `tools/devctl` only from the root, and checks the uv workspace always. Without a root `pyproject.toml` it is ok with `no pyproject.toml, so no uv workspace`, unless a Python stack is at `"."`.

- [ ] **Step 1: write the failing tests.** `test_devctl_doctor_stacks.py`, docstring `Offline: doctor's per-stack items in fixture repositories; no GitHub.`:
  - `test_flight_codeowners_needs_each_python_stacks_settings_under_its_directory`: `python` in `backend`; a Flight CODEOWNERS whose settings lines are at the root gives `CODEOWNERS must name only @o for: backend/pyproject.toml, backend/**/ruff.toml, ...` in `PYTHON_PROTECTED_PATHS` order; with `/backend/...` lines it gives `[]`.
  - `test_each_python_stack_gets_its_floor_item`: `python` in `backend` and `worker`, `worker/pyproject.toml` without vulture; the items are `Python guardrail settings (backend)`, ok, and `Python guardrail settings (worker)`, missing, whose detail holds `dev dependencies lack vulture`.
  - `test_the_exclusions_item_reads_the_root_pyproject`: `python` in `backend` without a root `pyproject.toml` is ok; a root one whose `[tool.uv.workspace] members = ["tools/*"]` is missing with the uv message; a root one with no Ruff exclusion is ok, because no Python stack is at the root.
- [ ] **Step 2: run** it; expected FAIL with `TypeError` from `codeowners_problems`.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k doctor`; expected PASS.
- [ ] **Step 5: commit** `feat: give each stack its doctor items`.

### Task 5: This repository's check, documents and PR 6.1a's verification

**Files:**
- Modify: `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, the root `AGENTS.md` (plan 6 under "Not on this branch yet"), Spec 1's status line and section 4's `[[stack]]` bullet (agnostic at `"."`), the plan index (plan 6's row and outline: the five PRs and the task split; Shared interfaces: the Settings sketch's `StackName`, `ProjectStack.directory`, `owners`, and `codeowners_problems` with `stacks`; Layout: `jsonc.py`), this plan's Verification record

- [ ] **Step 1: check the names.** `uv run rapid-ship status --strict` exits 0. `./devctl check --tier full --json --base main --pr-body <draft body>` lists exactly `main`'s step names in `main`'s order, the project's three included, and exits 0.
- [ ] **Step 2: documents.** Describe `[[stack]]`, the step names, ownership and doctor's per-stack items in the files above. Commit `docs: describe several stacks in devctl`.
- [ ] **Step 3: verify** with `--base main`, record the five checks, and commit `docs: record PR 6.1a's verification`. The PR body's Evidence lists them, with `Not covered: rapid-ship init still writes one stack at the root (6.1b); a TypeScript stack blocks the step list until 6.2a`.

## PR 6.1b: rapid-ship writes several stacks (`plan6-stacks-init`, on `plan6-stacks`)

### Task 2: `init --stack NAME[=DIRECTORY]`, detection, and the lock's `[[stack]]`

**Files:**
- Create: `rapid_ship/kit/stacks.py`, `tests/test_kit_stacks.py`
- Modify: `rapid_ship/kit/templates.py` (`Stack` and `STACKS` move to `stacks.py`), `rapid_ship/kit/lock.py` (`Lock.stacks`), `rapid_ship/kit/init.py` (`init_repository`, `InitResult.stacks`), `rapid_ship/kit/status.py` (`StatusReport.stacks`), `rapid_ship/kit/sync.py:105,136`, `rapid_ship/kit/existing_checks.py` (`find_existing_checks(root, directories)`), `rapid_ship/cli.py` (`--stack`, `_init`, `_status`)
- Modify: `tests/test_kit_lock.py`, `tests/test_kit_init.py`, `tests/test_kit_init_existing_checks.py`, `tests/test_kit_cli.py`, `tests/test_kit_status.py`, `tests/conftest.py`, and the other `tests/test_kit_*.py` call sites

**Interfaces:**
- Produces:

```python
# rapid_ship/kit/stacks.py
StackName = Literal["python", "agnostic"]
STACKS: tuple[StackName, ...] = ("python", "agnostic")
SKIPPED = frozenset(
    {"node_modules", "venv", "dist", "build", "vendor", "third_party", "__pycache__"}
)  # detection also skips every hidden directory


@dataclass(frozen=True)
class ProjectStack:
    name: StackName
    directory: str  # "." or a POSIX path inside the repository


def under(directory: str, path: str) -> str: ...
def parse_stack(option: str) -> ProjectStack: ...  # "NAME[=DIRECTORY]"; KitError
def checked_stacks(root: Path, stacks: Sequence[ProjectStack]) -> tuple[ProjectStack, ...]: ...
def detect_stacks(root: Path) -> list[tuple[ProjectStack, tuple[str, ...]]]: ...
def proposal(found: Sequence[tuple[ProjectStack, tuple[str, ...]]]) -> str: ...
def describe(stacks: Sequence[ProjectStack]) -> str: ...  # "python", or "python (backend), ..."


# rapid_ship/kit/lock.py
@dataclass(frozen=True)
class Lock:
    kit_version: str
    stacks: tuple[ProjectStack, ...]  # replaces stack
    variables: Mapping[str, str]
    entries: tuple[LockEntry, ...]


# rapid_ship/kit/init.py
def init_repository(
    root: Path,
    *,
    stacks: Sequence[ProjectStack],  # empty: detect, propose, raise KitError
    variables: Mapping[str, str],
    templates_root: Path | None = None,
) -> InitResult: ...
```

- 6.3 adds `typescript` to `StackName` and `STACKS`.
- `parse_stack` splits at the first `=`; the directory defaults to `"."` and is normalised as `relative_parts` does. Errors: `--stack <option>: the stack is python or agnostic` (from `STACKS`), and `--stack <option>: the directory is outside the repository`.
- `checked_stacks` sorts by `(directory, name)` and raises `KitError` for `--stack <name>=<directory> is given twice`, `the agnostic stack stands alone; remove the other --stack options`, `--stack agnostic=<directory>: the agnostic stack's directory is the root`, a directory under a symlink (`safe_path`), and a path that exists and is not a directory (`--stack <name>=<directory>: not a directory`). A directory that does not exist yet is accepted.
- `detect_stacks` reads the paths of `git ls-files -z --cached --others --exclude-standard`, skips a path with a part in `SKIPPED` or starting with `.`, and proposes `python` for each directory holding `pyproject.toml`, with the marker paths found, sorted. Task 10 adds `typescript` for a directory holding both `package.json` and `tsconfig.json`.
- `proposal` exactly, with a line per root and `--stack <name>` for the root, `--stack <name>=<directory>` otherwise:

```text
init wrote nothing: confirm the stacks first. It found these stack roots:
  python in . (pyproject.toml)
  python in services/api (services/api/pyproject.toml)
Confirm them with the owner, or ask the owner for the stacks, then run init again with:
  --stack python --stack python=services/api
```

  With no root: `init wrote nothing: it found no stack root, a directory with pyproject.toml (python). Ask the owner for the stacks, then run init again with --stack NAME[=DIRECTORY] for each stack, or with --stack agnostic.` Task 10 adds ` or with package.json and tsconfig.json (typescript)` before the first full stop.
- `init_repository` keeps its preconditions first; then, without stacks, raises `KitError(proposal(detect_stacks(root)))`. In this task it renders one stack at `"."` only and raises `KitError("this rapid-ship renders one stack at the root only")` otherwise; Task 3b removes that refusal inside this PR. Until then `init`, `status` and `sync` render `stacks[0].name` with today's `render_files`. The Python new-project seeds are written when the stack's directory holds no `pyproject.toml`.
- `read_lock` reads `stack` as a string, the older form, as `(ProjectStack(stack, "."),)`, or as a list of tables with `name` and `directory`; `write_lock` always writes `[[stack]]` tables after `kit_version`. The lock's error `stack must be python or agnostic` becomes `[[stack]] #<n>: name must be python or agnostic and directory a path inside the repository`.
- `find_existing_checks(root, directories)` also reads the settings files in each stack directory other than `"."`, listed as `<directory>/<name>`; hooks and workflows stay root-only.
- CLI: `--stack` is `action="append"`, `type=` a function that turns `parse_stack`'s `KitError` into `argparse.ArgumentTypeError`, `metavar="NAME[=DIRECTORY]"`, help `a stack and its directory, the root by default; repeat it for each stack. Without it, init proposes the stacks it finds and writes nothing`. `_init` prints `Vendored the {describe(stacks)} Kit ...`, unchanged for one root stack. `status` prints `stack {describe(...)}`, and `status --json` replaces `"stack"` with `"stacks": [{"name": ..., "directory": ...}]`.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_stacks.py`, docstring `Offline: stack options, detection and the lock's [[stack]] in scratch git repositories.`:
  - `test_a_stack_option_names_a_stack_and_a_directory`: `parse_stack("python") == ProjectStack("python", ".")`, `parse_stack("python=./backend/") == ProjectStack("python", "backend")`; `go`, `python=../x` and `python=/x` raise `KitError` with the texts above.
  - `test_stacks_are_checked_and_sorted`: each refusal above, a directory that does not exist accepted, and `[python in worker, python in backend]` sorted.
  - `test_detection_finds_nested_roots_and_skips_vendored_directories`: tracked `pyproject.toml`, `services/api/pyproject.toml`, `node_modules/x/pyproject.toml`, `.venv/lib/pyproject.toml`, `build/pyproject.toml` and `dist/pyproject.toml` give `python` in `.` and in `services/api` only.
  - `test_init_without_stack_proposes_and_writes_nothing`: that repository; `init_repository(root, stacks=(), ...)` raises `KitError` whose text equals the proposal above; `git status --porcelain` is empty, and no branch `rapid-ship/init` exists. An empty repository gives the no-root text.
  - In `test_kit_lock.py`, `test_an_older_lock_reads_as_one_stack_at_the_root_and_is_rewritten`: a lock with `stack = "python"` reads as `(ProjectStack("python", "."),)`, and `write_lock` writes `[[stack]]\nname = "python"\ndirectory = "."`.
  - `test_init_needs_a_stack_without_pyproject` keeps its name and now expects the no-root proposal; `tests/test_kit_cli.py` asserts `rapid-ship init` without `--stack` in a repository with `pyproject.toml` exits 2 and prints the proposal to stderr.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_stacks.py tests/test_kit_lock.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'rapid_ship.kit.stacks'`.
- [ ] **Step 3: implement**; update the call sites and pass `--stack python` where a test relied on the old default.
- [ ] **Step 4: run** `uv run pytest tests/test_kit_*.py -q`; expected PASS. `uv run rapid-ship status --strict`; expected exit 0.
- [ ] **Step 5: commit** `feat: name stacks and their directories in rapid-ship init and the lock`.

### Task 3b: Rendering under directories, the repository seeds from every stack, and PR 6.1b's verification

**Files:**
- Modify: `rapid_ship/kit/stacks.py` (`StackKit`, `KITS`, `derived_variables`, `stack_variables`), `rapid_ship/kit/templates.py` (`KitManifest.new_project`, `Template.new_project`, `render_files`, `_render_text`), `rapid_ship/kit/init.py`, `rapid_ship/kit/status.py`, `rapid_ship/kit/sync.py` (`render_files` calls; the new-project filter reads `Template.new_project`)
- Templates: move `rapid_ship/templates/python/.rapid-ship/project.toml` to `common/.rapid-ship/project.toml` and delete `agnostic/`; delete `python/.github/CODEOWNERS` and give `common/.github/CODEOWNERS` the `{{stack_patterns}}` and `{{stack_protected}}` lines; delete `python/AGENTS.md` and give `common/AGENTS.md` the `{{stack_rows}}`, `{{stack_rules}}` and `{{lint_marker}}` variables; create `python/AGENTS.md`, the stack guide; move `python/docs/patterns/python-*.md` to `python/__root__/docs/patterns/`, their paths prefixed with `{{directory}}`; `kit.toml`
- Create: `tests/test_kit_stacks_render.py`, `tests/fixtures/kit/python/` and `tests/fixtures/kit/agnostic/` (each `AGENTS.md`, `.github/CODEOWNERS`, `.rapid-ship/project.toml`)
- Modify: `tests/test_kit_contents.py`, `tests/test_kit_templates.py`, `tests/test_kit_starter_patterns.py`, `tests/test_kit_seed_keys.py` (the `rendered` and `seed` helpers render `(ProjectStack(stack, "."),)`); `rapid_ship/templates/AGENTS.md`, `rapid_ship/AGENTS.md`, `rapid_ship/kit/AGENTS.md`

**Interfaces:**
- Produces:

```python
# rapid_ship/kit/stacks.py
@dataclass(frozen=True)
class StackKit:  # what a stack adds outside its own templates
    markers: tuple[str, ...]  # files that make a directory this stack's root
    new_project_marker: str | None  # new-project seeds are written only without this file
    source_root: str  # under its directory; "{package}" is the package; "" for none
    unit_tests: tuple[str, ...]  # [tests] unit globs, under its directory
    guide_rows: tuple[str, ...]  # Find-the-change rows, linked from its directory
    guide_rules: tuple[str, ...]  # Rules bullets it adds to the root guide
    lint_rules: bool  # its lint step enforces the commented-out-code and TODO Rules
    patterns: tuple[str, ...]  # its starter Pattern files in docs/patterns/, in CODEOWNERS order
    protected: tuple[str, ...]  # its check tools' settings files, under its directory


KITS: dict[StackName, StackKit]
DERIVED = frozenset(
    {
        "directory",
        "guide_rows",
        "lint_marker",
        "source_roots",
        "stack_patterns",
        "stack_protected",
        "stack_rows",
        "stack_rules",
        "stack_tables",
        "unit_tests",
    }
)


def derived_variables(
    stacks: Sequence[ProjectStack], variables: Mapping[str, str]
) -> dict[str, str]: ...
def stack_variables(stack: ProjectStack) -> dict[str, str]: ...  # directory and guide_rows


# rapid_ship/kit/templates.py
@dataclass(frozen=True)
class Template:
    path: str
    kind: Kind
    content: bytes | None
    link: str | None
    new_project: bool = False  # sync never adds it; init writes it for a stack without its marker


def render_files(
    stacks: Sequence[ProjectStack],
    variables: Mapping[str, str],
    optional: Sequence[str],
    *,
    new_projects: Collection[ProjectStack] | None = None,  # None: every stack
    root: Path | None = None,
) -> list[Template]: ...
```

- `KITS["python"]`: markers `("pyproject.toml",)`, new-project marker `pyproject.toml`, source root `src/{package}`, unit tests `("tests/unit/**",)`, rows `| Product code | [Source](src/AGENTS.md) |` and `| Tests, and which count as unit tests | [Tests](tests/AGENTS.md) |`, rules today's `dead-code` bullet from `python/AGENTS.md`, `lint_rules=True`, patterns `python-error-handling.md`, `python-configuration.md`, `python-input-validation.md`, `python-performance.md`, protected the paths of devctl's `PYTHON_PROTECTED_PATHS`. `KITS["agnostic"]`: no markers, no new-project marker, no source root, unit tests `("tests/unit/**",)`, no rows, rules or patterns, `lint_rules=False`, nothing protected.
- `derived_variables`, for the common templates:
  - `stack_tables`: one `[[stack]]\nname = "<name>"\ndirectory = "<directory>"` per stack, separated by a blank line;
  - `source_roots` and `unit_tests`: the TOML array items, `"<under(directory, item)>"` joined by `", "`;
  - `stack_patterns`: `# /docs/patterns/<file> @<owner>` for each Pattern of each stack name, once per name;
  - `stack_protected`: `# /<under(directory, path)> @<owner>` for each stack's protected path;
  - `stack_rows`: a stack at `"."` gives its `guide_rows`; a stack in a subdirectory gives `| The <Python or TypeScript> stack | [<directory>/](<directory>/AGENTS.md) |`;
  - `stack_rules`: each stack name's `guide_rules`, once per name;
  - `lint_marker`: `enforced by: check:lint` when every stack's `lint_rules` is true, else `advisory`.
  `<owner>` is the owner, or `<owner>` when it is empty, as `_value` renders it.
- `stack_variables(stack)`: `directory` is `""` at `"."` and `<directory>/` otherwise; `guide_rows` is the stack's rows, one per line.
- Rendering: `common/` renders at the root. A stack's templates render under its directory, with its `stack_variables`; its `__root__/` files render at the root, for the first stack of each name only. A stack at `"."` renders no `AGENTS.md`: the root guide holds its rows. A stack template wins over a common one at the same path, except the root guide. Two stacks' templates at one path raise `KitError("<name> and <name> both write <path>; give one stack its own directory")`. A derived variable renders `""` when empty and never comments out its line, and a line that holds only a derived variable that renders `""` is dropped.
- `kit.toml`: `seeded` as today; `new_project` becomes a table of lists by stack, after the top-level keys; `variables` gains the `DERIVED` names. `load_manifest` raises `KitError("kit.toml new_project: expected a table of path lists by stack name")` for another shape.
- `init` renders with `new_projects` = the stacks whose directory lacks their new-project marker. `status` and `sync` render with `new_projects=None`, and `sync` never adds a template whose `new_project` is true.
- The common `project.toml` template holds the header, Spec 1 section 4's two stack comment lines, `{{stack_tables}}`, `source_roots = [{{source_roots}}]` and `unit = [{{unit_tests}}]   # every other test counts as behavioural`, otherwise as 6.1a's Python seed.
- The stack guide, `python/AGENTS.md`: `# {{project_name}}: the Python stack`, one sentence that `./devctl check` runs this stack's steps in this directory and that the root guide, linked as `[root guide](/AGENTS.md)`, holds the commands and Rules, then `## Find the change` with its table and `{{guide_rows}}`.

- [ ] **Step 1: capture the regression fixtures** before changing the rendering. Task 2 leaves `render_files` as the base has it, so render `render_files("python", VARIABLES, ())` and `render_files("agnostic", VARIABLES, ())` with `test_kit_contents.VARIABLES`, and write their `AGENTS.md`, `.github/CODEOWNERS` and `.rapid-ship/project.toml` under `tests/fixtures/kit/<stack>/`. Commit `test: keep the root-stack seeds as fixtures`.
- [ ] **Step 2: write the failing tests.** `tests/test_kit_stacks_render.py`, docstring `Offline: the packaged templates rendered for several stacks.`:
  - `test_one_stack_at_the_root_renders_its_seeds_as_before`, parametrized over `python` and `agnostic`: the three files equal their fixtures byte for byte.
  - `test_a_python_backend_renders_under_its_directory`: `python` in `backend`; the paths include `backend/pyproject.toml`, `backend/src/demo_app/__init__.py`, `backend/tests/test_settings.py`, `backend/AGENTS.md` and `docs/patterns/python-configuration.md`, whose front matter has `reference: backend/src/demo_app/settings.py` and `test:backend/tests/test_settings.py::test_an_out_of_range_value_is_rejected`; no rendered path is `pyproject.toml` or starts with `src/`.
  - `test_project_toml_and_codeowners_list_every_stack`: `python` in `backend` and `worker`; `tomllib` reads `project.toml`'s `stack` as both tables, `[map] source_roots` as `["backend/src/demo_app", "worker/src/demo_app"]` and `[tests] unit` as `["backend/tests/unit/**", "worker/tests/unit/**"]`; it loads with devctl's `load_project` once the directories exist. CODEOWNERS holds the four Pattern lines once, right after `# /.rapid-ship/ @octo`, and ends with the Python settings paths under `/backend/`, then under `/worker/`.
  - `test_the_root_guide_links_each_stack_guide`: `python` in `backend`; the root guide holds `| The Python stack | [backend/](backend/AGENTS.md) |` and the `dead-code` Rule, and both lint Rules end `enforced by: check:lint`, because every stack is Python; `backend/AGENTS.md` links `src/AGENTS.md` and `tests/AGENTS.md`.
  - `test_two_stacks_cannot_write_one_path`: a test template tree whose `python/` and `agnostic/` layers both hold `.gitignore`, rendered for both stacks at `"."`, raises the `KitError` above.
  - `test_init_writes_new_project_seeds_per_stack`: `init_repository` with `python` in `backend` (no `backend/pyproject.toml`) and `python` in `worker` (with one) writes `backend/pyproject.toml` and the Patterns, and no new-project file under `worker/`.
  - `test_the_stack_kits_match_devctl`: `KITS["python"].protected == doctor_rules.PYTHON_PROTECTED_PATHS`, and `KITS["python"].patterns` equals the file names under `python/__root__/docs/patterns/`.
  In `test_kit_contents.py`, `test_every_manifest_path_exists_in_a_layer` reads `new_project` by stack; the CODEOWNERS and root-guide tests keep their names and assertions.
- [ ] **Step 3: run** `uv run pytest tests/test_kit_stacks_render.py -q`; expected FAIL on `test_a_python_backend_renders_under_its_directory`.
- [ ] **Step 4: implement**; remove Task 2's one-root-stack refusal.
- [ ] **Step 5: run** `uv run pytest tests/test_kit_*.py tests/test_kit_seed_keys.py -q`, then the network test `uv run pytest tests/devctl/test_devctl_check_integration.py -q -k new_project`; expected PASS. `uv run rapid-ship sync --in-place` prints `Kit is current; nothing to sync.`, because this repository's root-stack seeds render as before; the lock keeps `stack = "python"` until a sync changes it, and both CLIs read either form. `uv run rapid-ship status --strict` exits 0. Commit `feat: render each stack under its directory and the repository seeds from every stack`.
- [ ] **Step 6: documents.** `ARCHITECTURE.md` (the CLI's `--stack`, detection, layers, the lock), `rapid_ship/templates/AGENTS.md` (`__root__`, stack guides, derived variables), `rapid_ship/kit/AGENTS.md`, `rapid_ship/AGENTS.md`; Spec 1 section 3 (init as built), section 4's Kit contents (the stack guide row) and Package layout (`agnostic/` gone); the index's Kit manifest block and Layout (`stacks.py`, `__root__`). Commit `docs: describe rapid-ship's several stacks`.
- [ ] **Step 7: verify** with `--base origin/plan6-stacks`, record the five checks, and commit `docs: record PR 6.1b's verification`. `Not covered: the TypeScript stack's templates (6.3); a nested stack directory such as apps/web, whose top-level apps/ needs its own guide`.

## PR 6.2a: the TypeScript steps and doctor (`plan6-ts-steps`, on `plan6-stacks`)

### Task 6: The TypeScript steps, knip and `check --install`

**Files:**
- Create: `devctl/check/stacks/typescript.py`, `tests/devctl/test_devctl_typescript_steps.py`, `tests/devctl/test_devctl_typescript_knip_include.py`
- Modify: `devctl/check/__init__.py` (`stack_steps`, `run_check`), `devctl/cli.py` (`--install`), `devctl/check/filesize.py` (TypeScript's extensions), `tests/devctl/check_workspace.py` (`node_tools`)

**Interfaces:**
- Produces:

```python
# devctl/check/stacks/typescript.py
SOURCE_EXTENSIONS = (".ts", ".tsx")
KNIP_INCLUDE = (
    "files,dependencies,unlisted,binaries,unresolved,exports,types,enumMembers,namespaceMembers"
)


@dataclass
class NodeStep:  # not frozen: Step's members are settable
    name: str
    tier: Tier
    argv: tuple[str, ...]  # the tool in node_modules/.bin, then its arguments
    failed_codes: frozenset[int]
    timeout_seconds: float = 1800.0

    def run(self, context: CheckContext) -> StepResult: ...


FORMAT = NodeStep("format", "fast", ("prettier", "--check", "."), frozenset({1}))
LINT = NodeStep("lint", "fast", ("eslint", "--max-warnings", "0", "."), frozenset({1}))
TYPES = NodeStep("types", "full", ("tsc", "--noEmit"), frozenset({1, 2}))
DEAD_CODE = NodeStep("dead-code", "full", ("knip", "--include", KNIP_INCLUDE), frozenset({1}))
TESTS = NodeStep("tests", "full", ("vitest", "run"), frozenset({1}))


class AuditStep:  # npm audit --json, read like pip-audit's report
    name = "audit"
    tier: Tier = "full"

    def run(self, context: CheckContext) -> StepResult: ...


class InstallStep:  # npm ci
    name = "install"
    tier: Tier = "fast"

    def run(self, context: CheckContext) -> StepResult: ...


def install_command(directory: Path) -> str: ...  # the advice a block names


# devctl/check/__init__.py
def run_check(context: CheckContext, tier: Tier, *, install: bool = False) -> list[StepResult]: ...


# tests/devctl/check_workspace.py
def node_tools(directory: Path, **bodies: str) -> None: ...  # fakes in node_modules/.bin
```

- `stack_steps("typescript")` is `([FORMAT, LINT], [TYPES, DEAD_CODE, TESTS, AuditStep()])`; TypeScript has no `contracts` step. With `install`, `run_check` runs one `StackStep(InstallStep(), ...)` per TypeScript stack first, in both tiers.
- `NodeStep.run` runs `<directory>/node_modules/.bin/<tool>` by absolute path. When it is missing it blocks with `<tool> is not installed in <label>; <install_command>`, where `<label>` is the stack's directory (`.` for the root) and `install_command` is `run npm ci there` when `package-lock.json` exists, else `run npm install there and commit package-lock.json`. Otherwise `command_result` decides: 0 passes, a failed code fails, any other code or a timeout blocks.
- `AuditStep` runs `npm audit --json`, 600 seconds. npm missing blocks with `npm is not on PATH; it comes with Node.js`. Exit 0 passes. Exit 1 with a JSON object whose `vulnerabilities` is a non-empty object fails with one line per package, sorted: `<name> <severity>: <titles of its advisories in via, joined by "; ", or the package names in via>`. Exit 1 with an `error` object blocks with `npm audit: <error.code> <error.summary>`; any other output or exit blocks through `command_result`.
- `InstallStep` runs `npm ci --no-audit --no-fund`, 1200 seconds; without `package-lock.json` it blocks with `<label> has no package-lock.json; run npm install there and commit it`. Exit 0 passes; anything else blocks.
- `--install` help: `first run npm ci in each TypeScript stack's directory`.
- Ruling: the issue types in `KNIP_INCLUDE` are knip 6.43.0's own, as its reference lists them; `nsExports` and `nsTypes` stay off, as Spec 1 section 5 names neither.

- [ ] **Step 1: write the failing tests.** `test_devctl_typescript_steps.py`, docstring `Offline: the TypeScript steps against fake tools in a fake node_modules/.bin.`, with `typescript` in `frontend` and `node_tools(root / "frontend", ...)`:
  - `test_each_step_runs_its_tool_in_the_stack_directory`: each tool logs its argv and directory; the argv are exactly the commands of Global Constraints, each run in `<root>/frontend`, and the full tier's TypeScript steps are `format (frontend)`, `lint (frontend)`, `types (frontend)`, `dead-code (frontend)`, `tests (frontend)` and `audit (frontend)`, placed as Task 4 orders stack steps.
  - `test_exit_codes_pass_fail_or_block`, parametrized: knip 0 passes, 1 fails, 2 blocks; tsc 1 and 2 fail, 3 blocks; eslint, prettier and vitest 1 fail, 2 block.
  - `test_a_missing_tool_blocks_with_the_install_command`: no `node_modules` with `frontend/package-lock.json` gives `blocked` and `prettier is not installed in frontend; run npm ci there`; without the lock, `... run npm install there and commit package-lock.json`.
  - `test_npm_audit_reads_its_report`: a fake `npm` printing `{"vulnerabilities": {"vite": {"severity": "high", "via": [{"title": "Path traversal"}]}}}` and exiting 1 fails with `vite high: Path traversal`; `{"error": {"code": "ENOLOCK", "summary": "no lockfile"}}` with exit 1 blocks with `npm audit: ENOLOCK no lockfile`; exit 0 passes.
  - `test_install_runs_npm_ci_first` and `test_install_without_a_lock_blocks`: `run_check(..., install=True)` gives `install (frontend)` first, which ran `npm ci --no-audit --no-fund` in `frontend`; without the lock it blocks with the text above. Without `install`, no `install` step runs.
  - `test_file_size_counts_typescript_sources`: a 501-line `frontend/src/a.tsx` fails and a 501-line `frontend/src/a.css` is not counted.
  `test_devctl_typescript_knip_include.py`, docstring `Integration test: needs network access, Node.js 24 and npm; installs knip 6.43.0 and TypeScript 6.0.3 in a scratch project.`:
  - `test_which_knip_settings_the_include_option_overrides`: a scratch project whose `src/index.ts` is its entry and imports `a` from `./used.ts`, which also exports `unused`. For no settings, `{"rules": {"exports": "off"}}`, `{"include": ["files"]}`, `{"exclude": ["exports"]}` and `{"ignoreExportsUsedInFile": true}` with `unused` used in its own file, it runs knip with `--include KNIP_INCLUDE` and records whether `unused` is reported. With no settings it is. The settings that hide it equal `doctor_typescript.KNIP_FLOOR_KEYS` as a set (Task 9).
- [ ] **Step 2: run** the offline file; expected FAIL with `ModuleNotFoundError: No module named 'devctl.check.stacks.typescript'`.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k "typescript or stacks or step_order"`; expected PASS. Run the knip test after Task 9 defines `KNIP_FLOOR_KEYS`.
- [ ] **Step 5: commit** `feat: add the TypeScript check steps and check --install`.

### Task 9: doctor's Node.js and TypeScript floor items, and PR 6.2a's verification

**Files:**
- Create: `devctl/doctor_typescript.py`, `tests/devctl/test_devctl_typescript_doctor.py`
- Modify: `devctl/doctor_local.py` (`local_items` adds the new items), `devctl/doctor_rules.py` (`TYPESCRIPT_PROTECTED_PATHS`; `protected_settings` adds TypeScript stacks)

**Interfaces:**
- Consumes: `jsonc.loads` (Task 1), `typescript.install_command` (Task 6).
- Produces:

```python
# devctl/doctor_typescript.py
TSCONFIG_FLOOR = (
    "strict",
    "noUncheckedIndexedAccess",
    "exactOptionalPropertyTypes",
    "noImplicitOverride",
    "noImplicitReturns",
    "noFallthroughCasesInSwitch",
    "verbatimModuleSyntax",
    "isolatedModules",
    "noEmit",
)
ESLINT_ERRORS = (
    "no-empty",
    "no-console",
    "@typescript-eslint/no-floating-promises",
    "@typescript-eslint/switch-exhaustiveness-check",
    "react-hooks/rules-of-hooks",
)
DEV_PACKAGES = (
    "@eslint/js",
    "@testing-library/react",
    "eslint",
    "eslint-plugin-react-hooks",
    "jsdom",
    "knip",
    "prettier",
    "typescript",
    "typescript-eslint",
    "vitest",
)
ESLINT_PROBE = "src/index.ts"  # the file eslint --print-config computes the stack's settings for
KNIP_FLOOR_KEYS: tuple[str, ...]  # the knip settings that --include does not override


def node_items(root: Path, stacks: Sequence[ProjectStack]) -> list[Item]: ...
def floor_item(root: Path, stack: ProjectStack, several: bool) -> Item: ...
def floor_gaps(
    tsconfig: Mapping[str, object],
    eslint_config: Mapping[str, object],
    package: Mapping[str, object],
    knip: Mapping[str, object],
    has_lock: bool,
) -> list[str]: ...


# devctl/doctor_rules.py
TYPESCRIPT_PROTECTED_PATHS = (
    "package.json",
    ".npmrc",
    "tsconfig*.json",
    "eslint.config.*",
    ".prettierrc*",
    "prettier.config.*",
    ".prettierignore",
    "vite.config.*",
    "vitest.config.*",
    "knip.*",
    ".knip.*",
)
```

- `KNIP_FLOOR_KEYS` holds the settings that Task 6's knip test shows hiding a finding, in the order `rules`, `include`, `exclude`, `ignoreExportsUsedInFile`; `ignoreExportsUsedInFile` is always among them, because no issue-type filter reaches it.
- `node_items` gives `node` and `npm` toolchain items only with a TypeScript stack. `node` is ok when `node --version`'s major equals the first integer of each TypeScript stack's `engines.node`: `node v24.19.0, which frontend/package.json names (24.x)`. It is missing with `node is not on PATH; install Node.js <major>`, `node v<version>, but <directory>/package.json names <range>; install Node.js <major>`, or `<directory>/package.json sets no engines.node`. `npm` is ok with its version, else missing with `npm is not on PATH; it comes with Node.js`.
- `floor_item`, named `TypeScript guardrail settings` with one stack at the root and `... (<directory>)` otherwise, reads `tsconfig.json`, `package.json` and `knip.jsonc` with `jsonc.loads`, `package-lock.json`'s presence, and the JSON of `node_modules/.bin/eslint --print-config src/index.ts`, 120 seconds. When ESLint cannot run, the item is unknown: `cannot run eslint in <label>: <reason>; <install_command>`. An unreadable file is unknown and names it.
- `floor_gaps`, in this order, one text each:
  - `tsconfig.json: compilerOptions.<option> is not true`, and when `tsconfig.json` sets `extends`, ` (it extends <value>, which doctor does not read)` after it;
  - `eslint: <rule> is not an error`; `eslint: complexity is not an error with a maximum of 10 or less`; `eslint: @typescript-eslint/ban-ts-comment does not ban @ts-ignore and @ts-nocheck and require a description on @ts-expect-error`; `eslint: linterOptions.reportUnusedDisableDirectives is not error`. A severity is an error when it is `2` or `"error"`, alone or first in a list;
  - `npm: devDependencies lack <names, comma-separated>`; `npm: engines.node is not set`; `npm: package-lock.json is missing; run npm install and commit it`;
  - `knip: knip.jsonc sets <key>, which can switch a kind off` for each key of `KNIP_FLOOR_KEYS` at its top level.
- `protected_settings` adds each TypeScript stack's `TYPESCRIPT_PROTECTED_PATHS` under its directory, after the Python stacks' in stack order.

- [ ] **Step 1: write the failing tests.** `test_devctl_typescript_doctor.py`, docstring `Offline: doctor's TypeScript items with fake node, npm and eslint.`:
  - `test_the_floor_names_each_gap`: `floor_gaps` on empty inputs gives the nine tsconfig texts, the five ESLint rule texts, the complexity, ban-ts-comment and directives texts, and the devDependencies, engines and lock texts, in that order; on the values that 6.3's seed holds, with `has_lock=True`, it gives `[]`; `{"ignoreExportsUsedInFile": true}` in knip gives the knip text.
  - `test_node_must_match_engines`, parametrized: `v24.19.0` with `24.x` is ok; `v22.1.0` is missing with the version text; no `node` is missing; no `engines.node` is missing.
  - `test_eslint_that_cannot_run_makes_the_floor_unknown`: no `node_modules` gives `unknown` and `cannot run eslint in frontend: eslint is not installed; run npm install there and commit package-lock.json`.
  - `test_flight_codeowners_needs_the_typescript_settings_under_its_directory`: `typescript` in `frontend`; the problem lists `frontend/package.json` through `frontend/.knip.*`.
- [ ] **Step 2: run** it; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement**; run Task 6's knip test, `uv run pytest tests/devctl/test_devctl_typescript_knip_include.py -q`, and set `KNIP_FLOOR_KEYS` from what it shows; expected PASS. Format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q`; expected PASS. Commit `feat: add doctor's Node.js and TypeScript floor items`.
- [ ] **Step 5: documents.** `ARCHITECTURE.md` (the TypeScript steps, `--install`, doctor's items), `tools/AGENTS.md`, `tests/AGENTS.md`; Spec 1 section 5's Dead code bullet on `--include`, with the knip test's result; the index's Layout (`check/stacks/typescript.py`, `doctor_typescript.py`). Commit `docs: describe the TypeScript steps and doctor's items`.
- [ ] **Step 6: verify** with `--base origin/plan6-stacks`, record the five checks, and commit `docs: record PR 6.2a's verification`. `Not covered: a real TypeScript project, which 6.3's integration tests check; the TypeScript suppressions and references (6.2b)`.

## PR 6.2b: the TypeScript rules (`plan6-ts-rules`, on `plan6-stacks`)

### Task 7: The TypeScript suppressions, knip's allowlist, and the TypeScript references

**Files:**
- Create: `devctl/check/stacks/typescript_suppressions.py`, `devctl/check/stacks/typescript_references.py`, `tests/devctl/test_devctl_typescript_suppressions.py`, `tests/devctl/test_devctl_typescript_knip_allowlist.py`, `tests/devctl/test_devctl_typescript_references.py`
- Modify: `devctl/check/exceptions.py` (`scan`, `ExceptionsStep.run`), `devctl/check/references.py` (kinds by stack)

**Interfaces:**
- Consumes: `jsonc.loads`, `ProjectSettings.owners` (Task 1); `normal_rule` (`check/exceptions.py`).
- Produces:

```python
# devctl/check/stacks/typescript_suppressions.py
SCRIPT_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
KNIP_ALLOWLIST_KEYS = (
    "ignore",
    "ignoreFiles",
    "ignoreBinaries",
    "ignoreDependencies",
    "ignoreMembers",
    "ignoreUnresolved",
    "ignoreIssues",
    "tags",
)
KNIP_SETTINGS = "knip.jsonc"
OTHER_KNIP_SETTINGS = (
    "knip.json",
    ".knip.json",
    ".knip.jsonc",
    "knip.ts",
    "knip.config.ts",
    "knip.js",
    "knip.config.js",
)


def line_rules(path: str, line: str) -> list[str]: ...  # one line of a TypeScript stack's file


@dataclass(frozen=True)
class KnipItem:
    line: int  # 1-based, in knip.jsonc
    rule: str  # "knip.<key>:<item>"


def knip_allowlist(text: str, path: str) -> tuple[list[KnipItem], list[str]]: ...  # items, errors


# devctl/check/stacks/typescript_references.py
def resolve_eslint(reference: str, rule: str, stack_directory: Path) -> str | None: ...
def resolve_type(reference: str, path: str, root: Path, stack_directory: Path) -> str | None: ...
```

- The suppression forms of a file in a TypeScript stack, each found anywhere in the line's text, and its rule:

| Form | Rule |
| --- | --- |
| `eslint-disable-next-line`, `eslint-disable-line` or `eslint-disable`, then its rules up to an optional ` -- ` description, in a script file | `eslint:<rules, sorted, comma-joined>`, or `eslint` without rules |
| `@ts-expect-error`, in a script file | `ts-expect-error` |
| `prettier-ignore`, in any file of the stack | `prettier-ignore` |
| `istanbul ignore <word>`, `c8 ignore <word>` or `v8 ignore <word>`, except the word `stop`, in a script file | `no-cover` |
| `test`, `it`, `describe`, `suite` or `bench`, any `.<word>` chain, then `.skip`, `.skipIf`, `.runIf`, `.todo` or `.fails`, in a script file | `skip`, `skipIf`, `runIf`, `todo` or `fails` |
| `@public` or `@beta` in a `/** ... */` comment, in a script file | `knip:@public` or `knip:@beta` |
| an item of a `KNIP_ALLOWLIST_KEYS` key in `knip.jsonc` | `knip.<key>:<item>` |

  `eslint-enable`, `eslint-env` and `global` comments are not suppressions. Vitest's `only` fails at run through `allowOnly: false`, and ESLint bans `@ts-ignore` and `@ts-nocheck`, so none of them is listed. A marker is read from the line's whole text, as for a text file. Ruling: `runIf` is listed, because it skips a test as `skipIf` does; Spec 1 section 5 names the others.
- `knip_allowlist` reads `knip.jsonc` line by line, skipping strings and comments. An array under a top-level allowlist key gives one item per string, on its own line; under `ignoreIssues`, each key of the object is one item. Errors, after a `jsonc.loads` of the whole text that compares items as a multiset:
  - `<path>:<line>: knip.<key> holds <n> items on one line; write each alone on its own line, with its own marker`;
  - `<path>: knip.<key> lists '<item>' on no line devctl can read; write it alone on its own line`;
  - `<path>: <dotted path> sets an allowlist below the top level; devctl reads knip's allowlists only at the top level of knip.jsonc`, for an allowlist key inside `workspaces` or any other object.
- `exceptions.scan`: a file with a TypeScript owner gets `_text_lines`' forms plus `line_rules` on each line; `knip.jsonc` in a TypeScript stack's directory gets its items. `ExceptionsStep.run` appends `knip_allowlist`'s errors, and `<directory>/<name>: devctl reads knip's settings only from knip.jsonc; move them there` for each `OTHER_KNIP_SETTINGS` file in a TypeScript stack's directory and for a `knip` key in its `package.json`. Invalid JSONC in `knip.jsonc` blocks the step with `<path>: <error>`.
- References: `eslint:` and `type:` are the TypeScript kinds. `resolve_eslint` runs `node_modules/.bin/eslint --print-config src/index.ts` in the stack's directory, 120 seconds, once per stack directory in a devctl run, and resolves when the rule's severity is an error as Task 9 defines it; otherwise `<reference>: ESLint does not report <rule> as an error in <directory>`, or `<reference>: cannot run eslint in <directory>; run npm ci there, or npm install when it has no package-lock.json`. `resolve_type` runs `node_modules/.bin/tsc --listFilesOnly -p tsconfig.json` there, once per stack directory in a run, and resolves when the file's resolved path is listed; otherwise `<reference>: tsc does not check <path>`, or the same `cannot run` text for tsc.

- [ ] **Step 1: write the failing tests.**
  - `test_devctl_typescript_suppressions.py`, docstring `Offline: TypeScript suppression forms read from lines of text.`: `test_each_form_names_its_rule`, a table with one row per form above, among them `// eslint-disable-next-line no-console, complexity -- reason` (`eslint:complexity,no-console`), `{/* eslint-disable-next-line */}` (`eslint`), `/* v8 ignore start */` (`no-cover`), `/* v8 ignore stop */` (none), `test.concurrent.skip(` (`skip`), `it.skipIf(ci)(` (`skipIf`), `describe.runIf(x)(` (`runIf`), `/** @public */` (`knip:@public`), and `/* eslint-enable */`, `test.only(` and `// @ts-ignore` (none). `test_an_unmarked_suppression_fails_and_a_marked_one_passes`: in `frontend/src/a.ts` of a fixture repository, `console.log(x); // eslint-disable-line no-console` fails with `frontend/src/a.ts:1: suppression eslint:no-console needs ...`, and passes with ` -- rs-exception: EX-1` after the rule and the entry `("EX-1", "frontend/src/a.ts", "eslint:no-console")`. `test_a_file_outside_the_typescript_stack_has_no_typescript_forms`: the same line in `scripts/a.ts`, with `typescript` in `frontend`, passes.
  - `test_devctl_typescript_knip_allowlist.py`, docstring `Offline: knip's allowlist items in knip.jsonc.`: `test_each_allowlist_key_names_its_rule`, parametrized over each key, such as `{\n  "ignoreDependencies": [\n    "@types/node",\n  ],\n}` giving `KnipItem(3, "knip.ignoreDependencies:@types/node")` and `"ignoreIssues": {\n    "src/x.ts": ["exports"],\n  }` giving `knip.ignoreIssues:src/x.ts`; `test_two_items_on_one_line_fail`; `test_an_item_below_the_top_level_fails` for `"workspaces": {"pkg": {"ignore": ["x"]}}`; `test_another_knip_settings_file_fails` for `frontend/knip.json` and a `knip` key in `frontend/package.json`; `test_scope_settings_are_not_suppressions` for `entry`, `project` and `ignoreWorkspaces`.
  - `test_devctl_typescript_references.py`, docstring `Offline: the eslint: and type: references against fake eslint and tsc.`: `test_an_eslint_reference_resolves_when_the_rule_is_an_error`, parametrized over `"error"`, `2`, `["error", {}]` (resolves) and `"warn"`, `0`, absent (not); the fake ran with `--print-config src/index.ts` in `frontend`, once for two references. `test_a_type_reference_resolves_when_tsc_lists_the_file`. `test_a_typescript_reference_without_node_modules_names_npm_ci`. `test_a_python_kind_does_not_resolve_for_a_typescript_holder`: `ruff:BLE001` held by `frontend/src/a.ts` gives `ruff:BLE001: unknown reference kind ruff for frontend/src/a.ts`.
- [ ] **Step 2: run** the three files; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k "typescript or exceptions or references"`; expected PASS. Commit `feat: read the TypeScript suppressions and references`.

### Task 8: The diff policy for Vitest, and PR 6.2b's verification

**Files:**
- Create: `devctl/check/stacks/vitest.py`, `tests/devctl/test_devctl_typescript_diff.py`
- Modify: `devctl/check/diff.py` (`_changed_tests` and `_added_tautologies` take the stack's readers; `DiffStep.run` applies the Vitest rules to a TypeScript stack's changes), `devctl/check/references.py` (`test:` reads Vitest identities for a TypeScript holder)

**Interfaces:**
- Produces:

```python
# devctl/check/stacks/vitest.py
TEST_FILE = re.compile(r".*\.(test|spec)\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$")
SEPARATOR = " > "  # between the titles of a test's chain, as Vitest's reporter writes them


def is_test_file(path: str) -> bool: ...
def test_identities(source: str) -> tuple[list[str], list[int]]: ...  # names, unchecked lines
def tautologies(source: str) -> list[tuple[int, str]]: ...
```

- `test_identities` tokenises the source, skipping comments, strings, template literals and regular expression literals; a `/` starts a regular expression after `(`, `,`, `=`, `:`, `[`, `!`, `&`, `|`, `?`, `{`, `}`, `;`, `return` or at the start of the source. A call of `describe`, `suite`, `it` or `test`, through any `.<word>` chain except `.each`, whose first argument is a plain string (`'...'`, `"..."`, or a template literal without `${`) opens a title. A `describe` or `suite` title holds until its call's closing parenthesis, and a test's identity is the chain of open titles and its own, joined by `SEPARATOR`. A test whose title, or an enclosing title, is not a plain string, or that uses `.each`, is not an identity: its line goes to the unchecked list.
- `tautologies` reports `expect(<a>).<toBe|toEqual|toStrictEqual>(<b>)` where `<a>` and `<b>` are the same text once whitespace is removed, and `expect(true).toBeTruthy()`, with the line and the call's text.
- `DiffStep` applies to a TypeScript stack's changed test files what it applies to Python's: removed identities across the change (a test moved to another file is no removal), declared or not, unit or behavioural by `[tests] unit`; added tautologies with `is always true; assert on the behaviour instead`; and a note `<path>:<line>: test title is not a plain string; not checked` for each unchecked line of a changed test file at the base. A head that does not tokenise counts as holding its base's tests, with `<path>: cannot read the tests at head (<error>)`.
- `test:<path>::<name>` with a TypeScript holder resolves when `name` is one of the file's identities.

- [ ] **Step 1: write the failing tests.** `test_devctl_typescript_diff.py`, docstring `Offline: Vitest test identities and the diff policy in fixture repositories.`:
  - `test_identities_are_title_chains`: `describe("a", () => { it("b", () => {}); describe('c', () => { test(`d`, () => {}) }) }); test("e", () => {})` gives `["a > b", "a > c > d", "e"]`; a `/\)/` regular expression and a `"describe("` string inside a body change nothing.
  - `test_a_title_that_is_not_a_plain_string_is_not_checked`: `test(name, ...)`, ``test(`x ${y}`, ...)`` and `test.each(rows)("x %s", ...)` give no identity and three unchecked lines; removing them from a changed file gives three notes and no problem.
  - `test_a_removed_vitest_test_fails_unless_declared`: `typescript` in `frontend`; removing `a > b` from `frontend/src/a.test.ts` fails with `removed behavioural test frontend/src/a.test.ts::a > b: declare it ...`; a body declaring it under `Removed tests:` passes with the note; moving it to `frontend/src/b.test.ts` passes.
  - `test_an_added_tautology_fails`: `expect(x).toBe(x)` and `expect( a ).toEqual(a)` added fail; `expect(x).toBe(y)` does not.
  - `test_a_test_reference_reads_vitest_titles`: `test:frontend/src/errors.test.ts::an error keeps its cause and names the next step` resolves for that file.
- [ ] **Step 2: run** it; expected FAIL with `ModuleNotFoundError: No module named 'devctl.check.stacks.vitest'`.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q`; expected PASS. Commit `feat: apply the diff policy to Vitest tests`.
- [ ] **Step 5: documents.** `ARCHITECTURE.md` (the TypeScript suppressions, references and diff rules), `tools/AGENTS.md`, `tests/AGENTS.md`; the index's Suppressions paragraph: the table above as plan 6's TypeScript rule names, and knip's items. Commit `docs: describe the TypeScript suppressions, references and diff rules`.
- [ ] **Step 6: verify** with `--base origin/plan6-stacks`, record the five checks, and commit `docs: record PR 6.2b's verification`. `Not covered: a dynamic skip through the test context, such as ctx.skip(), which devctl cannot see and review treats as an unmarked suppression; a suppression form inside a string, which counts too`.

## PR 6.3: the TypeScript templates and CI (`plan6-ts-templates`, on `plan6-stacks-init`)

### Task 10: The TypeScript templates

**Files:**
- Create under `rapid_ship/templates/typescript/`: `AGENTS.md` (the stack guide), `.gitignore`, `.prettierignore`, `package.json`, `tsconfig.json`, `eslint.config.js`, `vite.config.ts`, `knip.jsonc`, `index.html`, `src/AGENTS.md`, `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx`
- Modify: `rapid_ship/kit/stacks.py` (`typescript` in `StackName` and `STACKS`, `KITS["typescript"]`, its detection), `rapid_ship/kit/existing_checks.py` (the TypeScript tools' settings), `rapid_ship/templates/kit.toml` (`new_project.typescript`)
- Create: `tests/test_kit_typescript.py`
- Modify: `tests/test_kit_stacks.py` (TypeScript detection rows), `tests/test_kit_init_existing_checks.py`

**Interfaces:**
- Consumes: `render_files`, `KITS` (Task 3b); `doctor_typescript.TSCONFIG_FLOOR`, `DEV_PACKAGES`, `floor_gaps`, `doctor_rules.TYPESCRIPT_PROTECTED_PATHS` (Task 9); `jsonc.loads` (Task 1).
- `KITS["typescript"]`: markers `("package.json", "tsconfig.json")`, new-project marker `package.json`, source root `src`, no unit tests (every Vitest test counts as behavioural), row `| The React app's code and its tests | [Source](src/AGENTS.md) |`, no rules, `lint_rules=False`, patterns `typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md`, `typescript-performance.md`, protected `TYPESCRIPT_PROTECTED_PATHS`.
- Every TypeScript file but the stack guide is a new-project seed.
- `package.json`: `"name": "{{package}}"`, `"private": true`, `"version": "0.1.0"`, `"type": "module"`, `"engines": {"node": "24.x"}`, scripts `dev` (`vite`) and `build` (`vite build`), `dependencies` React and React DOM, `devDependencies` the other packages of Tech Stack, each pinned to an exact version with no range. Add a package only when the skeleton fails without it, pinned and listed in the PR body under the owner's approval.
- `tsconfig.json`: `TSCONFIG_FLOOR` all true, with `jsx` `react-jsx`, `moduleResolution` `bundler`, `types` `["vite/client"]`, and `include` the files ESLint and tsc check; no `extends`.
- `eslint.config.js`: a flat config of `@eslint/js` recommended, typescript-eslint's `strictTypeChecked` with its project service, and eslint-plugin-react-hooks' recommended flat config. It adds `complexity: ["error", 10]`, `no-console: "error"`, `@typescript-eslint/switch-exhaustiveness-check: "error"`, `@typescript-eslint/ban-ts-comment` with `ts-ignore` and `ts-nocheck` true and `ts-expect-error` `"allow-with-description"`, `no-restricted-imports` with empty `paths` and `patterns`, `linterOptions.reportUnusedDisableDirectives: "error"`, and Task 11's `no-restricted-syntax`.
- `vite.config.ts`: React's plugin; `test` with `environment: "jsdom"` and `allowOnly: false`. `knip.jsonc`: its `$schema` alone, with no `entry` or `project` while knip's Vite and Vitest plugins find them. `.gitignore`: `node_modules/`, `dist/`, `coverage/`. `.prettierignore`: `package-lock.json`, `*.md`, `docs/`, `tools/devctl/`, `.github/`, `.githooks/`, `.rapid-ship/`, `.claude/`, `.agents/`.
- `src/App.tsx` renders `<main>` with an `h1` of `{{project_name}}`; `src/App.test.tsx` is `test("the app shows the project name", ...)`, through Testing Library, with `afterEach(cleanup)`.
- The stack guide, `typescript/AGENTS.md`, as Python's with `the TypeScript stack`. Each settings file comments a key only for its contract (Spec 1 section 4).

- [ ] **Step 1 (Owner): approve the packages.** The owner approves the TypeScript seed's packages at the pins of Tech Stack, and their download by the integration tests and the trial. The PR body's Evidence section records the approval and its date.
- [ ] **Step 2: write the failing tests.** `tests/test_kit_typescript.py`, docstring `Offline: the TypeScript templates rendered for a frontend stack.`:
  - `test_the_typescript_files_render_under_the_stack_directory`: `typescript` in `frontend` renders each file above as `frontend/<path>`, each a new-project seed except `frontend/AGENTS.md`, which is seeded.
  - `test_the_typescript_settings_meet_the_floor`: `floor_gaps` on the rendered `tsconfig.json`, `package.json` and `knip.jsonc`, a `--print-config` object holding the rules above, and `has_lock=True`, gives `[]`; every version in `package.json` is exact; its name is `demo_app`; `knip.jsonc`'s keys are `{"$schema"}`.
  - `test_codeowners_lists_both_stacks_settings`: `python` in `backend` and `typescript` in `frontend`; after `# /.rapid-ship/ @octo` come the Python, then the TypeScript, Pattern lines; the file ends with the `/backend/` Python paths, then the `/frontend/` TypeScript paths; `KITS["typescript"].protected == TYPESCRIPT_PROTECTED_PATHS`. The root guide's lint Rules end `advisory`.
  - In `test_kit_stacks.py`, `test_detection_finds_nested_roots_and_skips_vendored_directories` gains `web/package.json` with `web/tsconfig.json` (`typescript` in `web`), `docs/package.json` alone (none) and `node_modules/x/` holding both (none); the no-root text names TypeScript's markers.
  - In `test_kit_init_existing_checks.py`, the listing includes `eslint.config.js`, `.eslintrc.json`, `.prettierrc`, `prettier.config.js`, `biome.json`, `tsconfig.json`, `vitest.config.ts` and `jest.config.js`, in the root and in a stack directory.
- [ ] **Step 3: run** `uv run pytest tests/test_kit_typescript.py -q`; expected FAIL with `KeyError: 'typescript'`.
- [ ] **Step 4: implement**; sync.
- [ ] **Step 5: run** the offline files; expected PASS. Commit `feat: add the TypeScript stack's templates and React skeleton`.

### Task 11: The TypeScript starter Patterns and the performance Pattern

**Files:**
- Create under `rapid_ship/templates/typescript/`: `__root__/docs/patterns/typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md`, `typescript-performance.md`; `src/errors.ts`, `src/settings.ts`, `src/inputs.ts`, `src/profiling.tsx`; `src/errors.test.ts`, `src/settings.test.ts`, `src/inputs.test.ts`, `src/profiling.test.tsx`
- Modify: `rapid_ship/templates/typescript/eslint.config.js`, `rapid_ship/templates/kit.toml`, `tests/test_kit_starter_patterns.py`

**Interfaces:** the skeleton's reference code (Ruling: example values the owner replaces, as for Python):

```text
// src/errors.ts
export class UsageError extends Error  // constructor(problem, nextStep, options?: ErrorOptions); message "<problem>; <nextStep>"
// src/inputs.ts
export const LEVELS = ["debug", "info", "warning", "error"] as const; export type Level = (typeof LEVELS)[number]
export function parseLevel(text: string): Level  // UsageError naming the four levels
export function levelRank(level: Level): number  // a switch over every Level
// src/settings.ts
export interface Settings { readonly logLevel: Level; readonly pageSize: number }  // VITE_LOG_LEVEL, default "info"; VITE_PAGE_SIZE, 1 to 100, default 20
export function loadSettings(env?: Readonly<Record<string, string | undefined>>): Settings  // undefined: import.meta.env
// src/profiling.tsx
export function Profiled(props: { id: string; onSample: (sample: Sample) => void; children: ReactNode }): JSX.Element  // React's <Profiler>
```

| Pattern file | `task` | `reference` | `enforced_by` |
| --- | --- | --- | --- |
| `typescript-error-handling.md` | `Report an error` | `{{directory}}src/errors.ts` | `eslint:no-empty`, `eslint:@typescript-eslint/no-floating-promises`, `test:{{directory}}src/errors.test.ts::an error keeps its cause and names the next step` |
| `typescript-configuration.md` | `Read configuration` | `{{directory}}src/settings.ts` | `eslint:no-restricted-syntax`, `test:{{directory}}src/settings.test.ts::an out-of-range value is rejected` |
| `typescript-input-validation.md` | `Validate input` | `{{directory}}src/inputs.ts` | `eslint:@typescript-eslint/switch-exhaustiveness-check`, `test:{{directory}}src/inputs.test.ts::an unknown value is rejected` |
| `typescript-performance.md` | `Find slow code` | `{{directory}}src/profiling.tsx` | `test:{{directory}}src/profiling.test.tsx::the profiling entry point renders on a small input` |

- Each file states the rule of Spec 1 section 4's starter table, when it applies and the bypass it bans, then `## Lessons` on what its reference does right. The performance Pattern documents the browser's Performance panel and React DevTools' Profiler, around `<Profiled>`; no check runs a profiler.
- `eslint.config.js` gains `no-restricted-syntax` as an error with two selectors and their messages, for `process.env` and `import.meta.env`, each pointing to `docs/patterns/typescript-configuration.md`, and an override that turns it off for `src/settings.ts` alone. `eslint --print-config src/index.ts` therefore shows it as an error.
- The skeleton's tests: `an error keeps its cause and names the next step` (`loadSettings({ VITE_PAGE_SIZE: "four" })` throws a `UsageError` whose message is `VITE_PAGE_SIZE is four; set it to a whole number from 1 to 100` and whose `cause` is the `RangeError` that reading the number threw); `an out-of-range value is rejected` (`"101"` throws `UsageError`); `an unknown value is rejected` (`parseLevel("verbose")` throws a `UsageError` naming `debug, info, warning, error`); `the profiling entry point renders on a small input` (rendering `<App />` inside `<Profiled>` records at least one sample, judging no time).

- [ ] **Step 1: write the failing test.** In `tests/test_kit_starter_patterns.py`, `test_the_typescript_starter_patterns_pass_map_rule_5`: `init_repository` with `typescript` in `frontend`, then commit; the files under `docs/patterns/` that start `typescript-` are the four above, `pattern_lesson_errors` returns `[]`, and `pattern_errors` returns only the three `eslint:` references' `cannot run eslint in frontend; ...` lines, since the offline test installs nothing. Task 12's integration test resolves them.
- [ ] **Step 2: run** it; expected FAIL on the four file names.
- [ ] **Step 3: implement**; sync.
- [ ] **Step 4: run** the offline file; expected PASS. Commit `feat: seed the TypeScript starter Patterns and the performance Pattern`.

### Task 12: The CI workflow, and the integration tests

**Files:**
- Modify: `rapid_ship/templates/common/.github/workflows/devctl-check.yml`, `tests/devctl/test_devctl_ci_templates.py`; this repository's workflow through `sync`
- Modify: `tests/devctl/test_devctl_check_integration.py`

**Interfaces:**
- After `astral-sh/setup-uv`, the workflow gains, with a comment on its contract:

```yaml
      # The TypeScript steps need Node.js; a repository without a package-lock.json skips it.
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        if: hashFiles('**/package-lock.json') != ''
        with:
          node-version: "24"   # the major the TypeScript seed's engines.node names
```

  and its last step runs `./devctl check --tier full --install`. The workflow stays one file for every project. Ruling: `node-version` is fixed, because a managed workflow cannot name a stack's directory; a project that changes `engines.node` changes this line, which makes the workflow its own. In this repository, `website/package-lock.json` sets up Node.js, which the integration tests need.

- [ ] **Step 1: write the failing tests.** In `test_devctl_ci_templates.py`: `setup-node` is pinned by a 40-character SHA with the `# v7.1.0` comment, its `if` is `hashFiles('**/package-lock.json') != ''`, its `node-version` equals the major of the TypeScript seed's `engines.node`, and the run step is `./devctl check --tier full --install`. In `test_devctl_check_integration.py`, whose docstring gains `Node.js 24 and npm`:
  - `test_new_project_passes_devctl_check` gains `typescript`, which runs `npm install --no-audit --no-fund` and commits `package-lock.json` before the check; `NOT_APPLICABLE` gains its rows, `diff` and `evidence` in the full tier.
  - `test_a_python_backend_and_a_typescript_frontend_pass_devctl_check`: `init --stack python=backend --stack typescript=frontend --owner test-owner`; `uv lock` and `uv sync` in `backend`; `npm install --no-audit --no-fund` in `frontend`; commit. `./devctl check --tier full --json` exits 0; the names include `lint (backend)`, `lint (frontend)`, `dead-code (frontend)` and `audit (frontend)`; only `diff` and `evidence` are not applicable.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ci_templates.py -q`; expected FAIL.
- [ ] **Step 3: implement**, sync, then run `./devctl check --tier full`; its `workflows` step, zizmor 1.30.1, passes.
- [ ] **Step 4: run** the network tests, `uv run pytest tests/devctl/test_devctl_check_integration.py -q`; expected PASS. Fix the seed until both projects pass; each package added follows Task 10's rule.
- [ ] **Step 5: commit** `ci: set up Node.js and install each TypeScript stack before the check`. The owner pushes this commit, because it edits `.github/workflows/`.

### Task 13: Live trial (Owner step), documents and PR 6.3's verification

**Files:**
- Create: `docs/trials/<run date>-typescript-and-stacks.md`
- Modify: `docs/trials/AGENTS.md`, `ARCHITECTURE.md`, `README.md`, the root `AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`; Spec 1's status line and sections 3, 4 (the TypeScript seed rows, `.prettierignore`, the stack guide), 5 and 10 where the build differs; the plan index (plan 6 built, its row and outline); this plan's Verification record

- [ ] **Step 1 (agent): write the record's preparation.** Sections: Purpose, Versions, Setup, Procedure, Results, Limits. The procedure: in a new private scratch repository on the owner's account, commit `backend/pyproject.toml` with a one-line project, and `frontend/package.json` with `frontend/tsconfig.json`; run `uvx --from <this checkout> rapid-ship init` without `--stack` and keep its proposal. In a second new scratch repository, run `init --stack python=backend --stack typescript=frontend --owner <login>`; `uv lock` in `backend`, `npm install` in `frontend`, commit; `./devctl doctor --settings`; `./devctl check --tier full`; push the branch, open a PR, and record the CI run's `devctl check` job.
- [ ] **Step 2 (Owner): run the procedure,** keeping each command's output and exit code, and the CI run's URL and result.
- [ ] **Step 3 (implementer): write the record** from the owner's output, each result labelled as observed in a run, with no path under `/Users/`, `/home/` or `/tmp/`.
- [ ] **Step 4: documents.** Describe plan 6 as built in the files above. Commit `docs: describe the TypeScript stack and record plan 6 as built`.
- [ ] **Step 5: verify** with `--base main`, after 6.1b, 6.2a and 6.2b have merged, record the five checks, and commit `docs: record PR 6.3's verification`. The Evidence section lists them and the owner's approval of Task 10 Step 1, with `Not covered: a TypeScript stack in a nested directory; several TypeScript stacks with different Node.js majors, which share CI's one Node.js`.

## Verification record

Each PR's last task fills its row with the command, its exit code and the summary line it printed. A blocked, skipped or simulated result is written as such, never as passed.

| PR | `uv run pytest -q` | `./devctl check --tier fast` | `uv run rapid-ship status --strict` | `./devctl check --tier full --base <base> --pr-body <body>` | `npm --prefix website run build` |
| --- | --- | --- | --- | --- | --- |
| 6.1a | | | | | |
| 6.1b | | | | | |
| 6.2a | | | | | |
| 6.2b | | | | | |
| 6.3 | | | | | |
