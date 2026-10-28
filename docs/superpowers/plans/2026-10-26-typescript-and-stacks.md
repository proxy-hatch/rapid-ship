# TypeScript Stack and Several Stacks Implementation Plan

> **For implementers:** Start code only after Shawn approves PRO-169 and records the affected owner confirmations. Follow each Unit's test-first cycle and the repository's engineering guidance; checkboxes track implementation, not this document revision.

**Goal:** Let a repository hold several stacks and add the TypeScript stack, so a Python backend and React TypeScript frontend pass `./devctl check` from day one.

**Architecture:** Five code PRs add devctl's stack interfaces, then CLI rendering and TypeScript checks in parallel, then templates and integration tests. `StackStep` runs in its stack's directory, and file ownership follows the innermost stack directory. rapid-ship renders common files at the root, stack files under their directory and `__root__/` files at the root, with one guide per directory.

**Scope:** `[[stack]]` settings and lock tables, repeatable `init --stack NAME[=DIRECTORY]`, detection proposals, TypeScript tools and Patterns, doctor and CI. Unit 14 fixes `repository` from `origin` and commitless Setup (PRO-159, PRO-161) in 6.1b. This includes part of PRO-108; the rest of monorepo support stays deferred.

**Tech Stack:** Python 3.12+ standard library (`tomllib`, `json`, `re`), PyYAML, git 2.31+, uv, pytest, Ruff, mypy. Proposed TypeScript pins, subject to owner confirmation and the prototype: Node.js 24, from 24.15.0, with npm 11, TypeScript 6.0.3 (typescript-eslint 8.72.0 accepts `>=4.8.4 <6.1.0`, so not 7.0.2), ESLint 10.13.0 with `@eslint/js` 10.0.1, typescript-eslint 8.72.0, eslint-plugin-react-hooks 7.1.1 and globals 17.13.0, Prettier 3.9.10, Vitest 5.0.5 with jsdom 30.1.3, `@testing-library/react` 16.3.3 and `@testing-library/dom` 10.4.2, Vite 8.3.5 with `@vitejs/plugin-react` 6.1.2, knip 6.43.0, React and React DOM 19.3.1 with `@types/react` and `@types/react-dom` 19.3.0. `actions/setup-node` v7.1.0, commit `949feb2413d6458794dcd2491c4babbbce0c15c1`.

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), sections 3 (`init` stacks and detection, the lock), 4 (Kit contents, settings files, starter Patterns, the Protected set, CI, TypeScript guardrail settings), 5 (steps, dead code, several stacks, output, references, exceptions, diff policy), 6 (`doctor`), 8 (steps 6 and 13: the sandbox, and the Setup PR's branch) and 10 (plan 6's tests, the integration test, the live trial), as revised for the owner's descope of 2026-10-26. Plan 6 of 7 in the [plan index](2026-10-14-kit-and-setup.md), whose Conventions, Layout, Shared interfaces and "Plan 6" outline bind this plan. The [hello-rapid-ship trial](../../trials/2026-10-26-hello-rapid-ship.md) names the defects it builds on.

**Status:** revised for approval in PRO-169, its own documentation PR. Code is unbuilt and starts only after Shawn approves this plan. The fixed review base is `f107a89`; the earlier draft is `419f219`.

**Owner steps:** confirm the six decisions below by their deadlines; run Unit 13 Step 2's live trial; push workflow edits in Unit 12a, which the Worker App cannot push. Approve each G5 ask for Protected edits, including `.rapid-ship/project.toml` in Units 1, 3b and 10, and guides in Units 3b, 5, 9 and 13. In a headless Session the owner makes those edits. No agent performs an Owner step.

## Order and parallel work

Each PR is one Task as GLOSSARY.md defines it. The numbered Units below retain the index's numbering and each has its own test-first cycle.

| PR | Branch, base | Units | Builds | Counted lines, estimated |
| --- | --- | --- | --- | --- |
| PRO-169 | documentation branch, on `main` | This plan and its index entries | Plan approval only; no implementation | Markdown is excluded |
| 6.1a | `plan6-stacks`, on `main` | 1, 1b, 4, 3a, 5 | devctl stack settings, lock reader, helpers, ownership, references and doctor | about 1,250 before review additions |
| 6.1b | `plan6-stacks-init`, on 6.1a | 2, 14, 3b | init, detection, lock writer, rendering and commitless Setup | about 1,420 before fixture and shared-guide additions |
| 6.2a | `plan6-ts-steps`, on 6.1a | 6, 12a, 9 | TypeScript steps, install, CI and doctor | about 950 |
| 6.2b | `plan6-ts-rules`, on 6.1a | 7, 8 | TypeScript suppressions, references, Vitest and declarations | about 1,150 |
| 6.3 | `plan6-ts-templates`, on `main` after 6.1b and 6.2a | 10, 11, 12b, 13 | TypeScript templates, integration tests and live trial; remove devctl's temporary lock reader | about 900 |

- **6.1a first:** after plan approval and the merged wave-1 prerequisites below. It produces `ProjectStack`, `CheckContext.directory`, `StackStep`, `owners`, `jsonc`, `node` and `node_tools`.
- **Preparation during 6.1a:** after decisions 1 and 2, prototype Units 10 and 11 in an isolated scratch directory. Run `npm install --no-audit --no-fund`, `npx --no-install prettier --check .`, `npx --no-install eslint --max-warnings 0 .`, `npx --no-install tsc --noEmit`, `npx --no-install knip --include files,dependencies,unlisted,binaries,unresolved,exports,types,enumMembers,namespaceMembers` and `npx --no-install vitest run`. Each must exit 0 before its seed is accepted. A second independent preparation may build Vitest parsing and suppression scanning test-first. Neither preparation replaces its Unit's tests or review. Three plan-6 agents is the documentation's Walk advice; the owner sets the total across plans and other Tasks.
- **6.1b, 6.2a and 6.2b:** may branch from 6.1a while review continues. Before recording squash ancestry, each must merge any missing review fixes from its current remote prerequisite head (Global Constraints).

| PR | Source and test ownership |
| --- | --- |
| 6.1b | `rapid_ship/` outside devctl templates, `scripts/`, `tests/test_kit_*.py`, and `[map] exclude` in project settings |
| 6.2a | devctl `check/__init__.py`, `check/filesize.py`, `cli.py`, `doctor_local.py`, `doctor_rules.py`, `doctor_typescript.py`, `check/stacks/typescript.py`; CI templates and corresponding tests; conditional PRO-158 fallback extension |
| 6.2b | devctl `check/exceptions.py`, `check/references.py`, `check/diff.py`, `check/evidence.py`, `check/map.py`, `check/stacks/typescript_suppressions.py`, `typescript_references.py`, `vitest.py` and corresponding tests |

All three consume Unit 1b's helpers without changing them. Each sync regenerates `.rapid-ship/kit.lock`; never resolve it by hand. Shared documents are `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, root `AGENTS.md`, `README.md`, `rapid_ship/templates/AGENTS.md`, this index and Spec 1. Merge their paragraphs without dropping other Tasks' text.

- **Diff-cap margin:** estimates are not permission to exceed 1,500 counted additions plus deletions. 6.1b's nominal 80-line margin is insufficient assurance: Unit 2 rewrites roughly 71 call sites, Unit 14 changes commitless fixtures, and shared-guide tests add lines. Keep Unit 14 in 6.1b. Measure after each Unit with `./devctl check --tier full --base <base> --pr-body <body>` and retain its `diff` count. If necessary, split other independent work at a Unit boundary before publication; 6.1a can split Unit 3a. Recalculate dependent bases and verification rows. A declared overage requires the owner's prior acceptance; never hide it or weaken checks.
- **6.3 last:** Units 10 and 12b require merged 6.1b and 6.2a. Unit 11 also waits for 6.2b, brought in by a normal merge of `origin/main`. Only its tests import `doctor_typescript` and `doctor_rules`; `rapid_ship` never imports devctl.
- **Merge order:** 6.1a; then 6.1b, 6.2a and 6.2b as reviews finish; then 6.3. Record decision 3 before the first merge. After each squash merge, follow the ancestry procedure below; never use `ours` for a sibling.
- **Other plans:** plan 7's 7.2 changes init's dirty-tree message and `tests/test_kit_init.py`; its 7.1b adds a glossary bullet to the root guide. Spec 3 adds the Correction Rule there. Apply these to `common/AGENTS.md` after 6.1b. Spec 3 alone renames `optional_skills` to `optional` in PR 3.7; plan 7 uses the current reader APIs and names until then. Whichever PR lands second updates shared callers and fixtures. Plan 7 must quote the exact `cannot_run` text, `engines.node = ">=24.15.0 <25"`, proposal first line and Unit 14 report. Its ruleset step depends on Unit 14's owner-terminal default-branch push before ruleset application.
- **Ledger references:** Spec 3 passes a ledger entry's path as `holder` to `resolve`. Unit 4 resolves a unique matching stack. Ambiguity fails with candidate stacks and the supported alternatives `test:<path>::<name>` or `check:<step>` with its directory-qualified name, such as `lint (backend)`. No new reference syntax is added; Unit 5 records this contract in Spec 1 section 5.

### Merged and parallel changes that share files

Take dependencies only from `origin/main` after they merge, using a normal merge. Never merge an unmerged dependency branch. Confirm current `main` before implementation; PR numbers below identify wave-1 work, not claims that all four are merged in this draft.

| Change | Integration contract |
| --- | --- |
| PRO-166 #48 | Wait before 6.1a. Preserve Mode merge guard, `every_pr` alone, root scope Rule, Pull requests section and Flight comment when moving seeds. Rewrite its old-stack fixtures in Unit 1. |
| PRO-152 #50 | Wait before Unit 4. Preserve `TrackedFiles` in reference resolution and tracked-only map checks. Shares `check/map.py`, `check/references.py`, `check_workspace.py`, map/reference tests, `tests/test_kit_contents.py` and starter-Pattern tests. |
| PRO-147 #51 | Wait before Unit 3a. Extend its CODEOWNERS errors API and per-stack Protected paths without losing unknown-owner errors or key-page guidance. |
| PRO-155 #49 | Merged before this revision. Preserve `.agents/hooks.json`, doctor's probe and `/.agents/` in common Protected paths. Rewrite its fixtures with `stack_table`. |
| PRO-158 | Its own PR owns the Kit fallback, never head CODEOWNERS. If merged first, Unit 3a extends Python settings at depth and Unit 9 extends TypeScript settings at depth, with fallback tests. Otherwise its owner must consume those path sets before its PR merges; unresolved integration blocks the affected verification. Old branch code is evidence only. |
| PRO-156 with PRO-157 | Parallel Task owns the entire sandbox spec fix, exact uv/gh values and Session restart. Unit 13 depends on its merged setting and adds only observed TypeScript/npm needs. Plan 7 does not inherit the full fix. |
| PRO-142 | Codex wiring lands before GA. When seeds merge, retain all Claude Code, agy and Codex wiring and current common Protected paths. Plan 6 implements no Codex wiring. |
| PRO-153 | Hook fixes may add fixtures; Unit 1 repeats its old-stack search after each main merge. Plan 6 does not rewrite hook parsing. |

### The hello-rapid-ship trial's defects

Unit 14 fixes PRO-159 and PRO-161 in 6.1b. PRO-158 and PRO-156/157 remain separate dependencies as above. PRO-160's skill wording belongs to plan 7. The owner superseded PRO-162 with the golden-paths library (PRO-167); this plan adds no command or check for it. Existing map code remains source evidence until PRO-167 changes it.

## Six owner confirmations needed on PRO-169

All six remain **pending**. Approval of this plan must record each answer; recommendations below are not confirmations.

1. **TypeScript packages, pins and downloads:** approve Tech Stack and downloads for the prototype, 6.2a's knip integration test, 6.3's tests and trial. Due before the prototype or 6.2a starts; Units 6, 9, 10–13 wait. Record prototype differences and seek approval for changed packages or pins.
2. **Node.js 24:** recommend 24, with seed `engines.node = ">=24.15.0 <25"` and CI `node-version: "24"`. Due before the prototype and 6.2a; another major changes Units 9, 10 and 12a and their version tests.
3. **No Kit tag between 6.1a and 6.3:** due before 6.1a merges. Recommend holding tags while the intermediate TypeScript stack and lock transition are incomplete. Earlier tags are unaffected.
4. **Agnostic at root only:** recommend `directory = "."` and no other stack beside it. Due before Unit 1; another answer changes Units 1, 2 and their loader/CLI tests.
5. **Python and TypeScript in one directory:** recommend accepting existing projects at root or nested `app/`, with one combined guide and navigation row. Due before Unit 1; another answer changes ownership, settings, rendering and Units 7 and 10. Two new skeletons with colliding paths still refuse before writes.
6. **PRO-161 option A:** due before Unit 14. Recommend A: init creates an empty first commit on the current branch, then commits on `rapid-ship/init`. B refuses before writes and asks the owner to create the first commit. Unit 14 plans A; no answer is inferred. With A, the owner pushes the default branch from their own terminal before `rs-setup` applies the ruleset, then the Setup branch is pushed and its PR opened.

## Deviations from the index's outline

- 6.1 and 6.2 each split in two (6.1a and 6.1b, 6.2a and 6.2b): each is estimated over the 1,500-line diff cap, and the split lets three PRs build at once.
- Unit 1 keeps devctl's settings and its reading of the lock, and rapid-ship's lock writer moves to Unit 2: `rapid-ship` alone writes the lock, so it changes with `init`.
- Unit 3 splits into 3a, doctor's items (devctl, 6.1a), and 3b, the rendered seeds (rapid-ship, 6.1b). Unit 5's rewrite of this repository's `project.toml` moves into Unit 1, because the pre-commit hook's `devctl check` refuses the old key from that commit on.
- `devctl/jsonc.py` lands in 6.1a, and `typescript` joins devctl's stack names there, so 6.2a and 6.2b can build in parallel; a TypeScript stack blocks the step list until 6.2a.
- `codeowners_problems` takes every stack in one call, as the updated shared index specifies, so the common Protected set is checked once.
- A stack in a subdirectory gets a seeded stack guide, `<directory>/AGENTS.md`: map rule 2 requires a guide in every top-level directory, and Spec 1 section 4 seeds none there.
- The TypeScript seed adds `.prettierignore`: `prettier --check .` would otherwise check Kit-managed files and the seeded Markdown, which Spec 1 section 4 keeps out of the project's tools.
- The npm package name is `{{package}}`, because npm requires a lowercase name and `{{project_name}}` may hold capitals.
- The `agnostic/` template layer goes, and the Python layer's root guide, CODEOWNERS and `project.toml` move to `common/`: those files now render from every stack.
- `devctl/node.py` lands in 6.1a: 6.2a and 6.2b both run tools from `node_modules/.bin`, and they share one ESLint runner, one severity rule and one install advice.
- Unit 12 splits into 12a, CI's Node.js and `--install` (6.2a), and 12b, the integration tests (6.3): 6.2a's knip test runs in this repository's CI and needs Node.js 24 there.
- The TypeScript seed adds `.prettierrc.json` holding `{}`, Prettier's defaults: Prettier looks upward for its settings, so without it a root file outside the stack's Protected lines could switch the `format` step off.
- An `eslint-disable` or `/* eslint */` comment that names several rules is one rule, its rules sorted, as `# noqa` is.
- `init` refuses two new stacks in one directory, whose new-project seeds share paths; `status` and `sync` render a stack's new-project seeds only when the lock records its marker as seeded (decision 5).
- 6.1b checks that a root stack's seeds render as before with a recorded `cmp`, not with committed fixtures, which would freeze seed text that plan 7 edits.
- Unit 14, added to the original outline, fixes PRO-159 and PRO-161 in 6.1b. Both live in `rapid_ship/kit/init.py` and `_init`'s report, which Unit 2 rewrites, so a PR of their own would conflict with 6.1b in those files and their tests.
- PRO-159's fix defaults `repository` from `origin`, but not `owner`, which the issue also suggests. An organisation cannot be a code owner (Spec 1 section 4, `[github]`), and `init` asks GitHub nothing, so it cannot tell a person's login from an organisation's; a default would seed `* @<organisation>`. `rs-setup` writes the code owner (Spec 1 section 8, step 7.5).

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
- `rapid_ship` never imports devctl (the forbidden import-linter contract). `KITS[...].protected` copies the Python and TypeScript Protected path tuples; tests compare the copies.
- File-size cap 500 lines: `check/stacks/python.py` (476 lines) gains only `SOURCE_EXTENSIONS`; `command_line.py` (492) is untouched; `check/map.py` takes Unit 4's holder changes and Unit 8's backticked Rule references; keep it under 500 lines; TypeScript code goes into new modules, `check/stacks/typescript*.py`, `check/stacks/vitest.py` and `doctor_typescript.py`.
- No backward compatibility before GA: devctl refuses the old top-level `stack` key in `project.toml` with how to rewrite it, and the project rewrites the file. `rapid-ship` reads the lock's older `stack = "<name>"` and its `sync` rewrites it, as Spec 1 section 3 asks, because only `rapid-ship` writes the lock. This required lock-only transition is separate from seeded-file migration: sync never changes existing seeded files, and new checks fail immediately. Add no other migration infrastructure. devctl reads the older lock only from 6.1a to 6.3: this repository's lock keeps that form until 6.1b's `sync` rewrites it, and Unit 12b removes devctl's reader. The `diff` step already treats a base lock it cannot read as listing no managed path.
- The Kit after the owner's descope of 2026-10-26: no Kit skill designs, leads, implements or reviews work; `[escalation]` holds only `every_pr`; the root guide's first Rule is `Keep each change inside the scope you were asked to change.`, and its Pull requests section is the one Spec 1 section 4 quotes. Plan 6 changes none of them, and keeps each where it moves a seed. Keep `/.agents/` from PRO-155 and Codex's Protected paths when PRO-142 merges before GA. Preserve each Harness wiring file and its manifest entry.
- The comment rule: no comment, docstring, message or test name cites a plan, spec, section, ADR, PR, trial or rule ID. Seeds comment a key only for its contract.
- No `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression carries an `rs-exception` marker and an entry. Write tests first. A test module's docstring starts `Offline:` and names what it simulates, or names the network, Node.js or gitleaks it needs. A blocked, skipped or simulated check never counts as passed, so no test skips for a missing tool.
- Keep each existing test's name and change its body. A test renamed or removed against the PR's base goes under `Removed tests:` in the PR body, with the test that now covers it.
- Agent identity is on here: agents push with `./devctl as worker push` and write to GitHub with `./devctl as <role> gh`. G5 asks before each edit of a Protected path, such as `.rapid-ship/project.toml`, `pyproject.toml` or an `AGENTS.md`; in a headless Session the owner makes that edit.
- Each PR's base is the branch in the table. This repository is in Walk, and each PR touches the Protected set, so the owner merges each in GitHub's web interface. After a PR squash-merges, retarget each PR whose base was its branch with `./devctl as worker gh api -X PATCH repos/proxy-hatch/rapid-ship/pulls/<n> -f base=main`, then update every open PR of this plan:
  1. Run `git fetch origin`. For each child of 6.1a, run `git merge-base --is-ancestor origin/plan6-stacks HEAD`. If it fails, run `git merge origin/plan6-stacks` first. Resolve and check those review fixes before recording squash ancestry. Never compare with a stale local prerequisite branch.
  2. Only for 6.1a's squash commit, run `git diff --quiet <squash> origin/plan6-stacks`; exit 0 proves equal trees. Then `git merge -s ours <squash>` records that equivalent ancestry. If the comparison fails or the remote branch is unavailable, stop and resolve the prerequisite; do not use `ours`.
  3. Run a normal `git merge origin/main` to bring in siblings. Never use `ours` for a sibling or all of `main`.
  4. Regenerate the lock with `uv run rapid-ship sync --in-place`; never edit it by hand. Merge shared document text without dropping other work.
  5. Run `git diff origin/main...HEAD --stat` and `git diff <squash> HEAD`. Compare the actual diff against the current remote prerequisite and merged siblings: only this PR's work remains relative to `origin/main`, and all review fixes remain. Run the required checks on the resulting head, push and verify hosted checks before acceptance.
- Each PR stays under 1,500 counted lines. When `diff` counts more, split at a task boundary, or declare `Over the diff cap: <reason>` only after the owner accepts the overage.
- Each PR's last task runs and records `uv run pytest -q`, `./devctl check --tier fast`, `uv run rapid-ship status --strict`, `./devctl check --tier full --base <PR base> --pr-body <body file>` and, when docs change, `npm --prefix website run build` in the Verification record. The integration tests need network access and gitleaks 8.30.1; from 6.2a, the knip test and the integration tests also need Node.js 24, 24.15.0 or later, with npm. In CI, Unit 12a's `setup-node` installs it for this repository, through `website/package-lock.json`.
- This document updates the index's shared contracts for `ProjectSettings.owners`, `codeowners_problems(..., stacks)`, typed `KitManifest.new_project`, `stack_variables` by directory and `resolve(reference, context, tracked, holder)`. Implementation Tasks keep those contracts current; their Layout and behavioral-spec updates land with code. This document changes no behavioral spec.
- Ruff formats the `python` code blocks of this file: keep them valid Python in Ruff's layout.

## Review Focus

1. **A Python stack at the root beside a TypeScript stack in `frontend/`.** The root stack's directory holds the other's. Expected: `frontend/src/a.ts` belongs to TypeScript alone, `src/app/a.py` to Python, and the steps are named `lint (.)` and `lint (frontend)`. Unit 1's `test_owners_are_the_stacks_of_the_innermost_directory` and Unit 4's `test_step_names_follow_the_stacks` pin it.
2. **Detection in a repository with vendored or generated roots.** Inputs: `node_modules/x/` and `.venv/lib/x/` holding marker files, a `dist/` or `build/` copy, and a `package.json` without `tsconfig.json`. Expected: none of them is proposed, nothing is written and `init` exits 2. Unit 2's `test_detection_finds_nested_roots_and_skips_vendored_directories` pins it, and Unit 10 adds the TypeScript rows.
3. **A TypeScript stack before `npm ci`.** Inputs: no `node_modules`, no `package-lock.json`, and `--install` without a lock. Expected: steps using `node_modules/.bin` block and name `npm ci`, or `npm install` and committing the lock when absent. Audit can pass from a lock alone; without one it blocks before npm runs. Unit 6's `test_a_missing_tool_blocks_with_the_install_command`, `test_install_without_a_lock_blocks` and `test_npm_audit_reads_its_report` pin it.
4. **A knip setting that hides findings.** Inputs: `rules: {"exports": "off"}` and `rules: {"exports": "warn"}`, which still prints the finding but exits 0, `ignoreExportsUsedInFile`, two allowlist items on one line, an item in `workspaces`, and knip settings in `knip.json` or `package.json` instead of `knip.jsonc`. Expected: doctor's floor names each key under which knip exits 0 with an unused export despite `--include`; the exceptions step fails each unmarked or unplaceable item and each other settings file. Unit 9's `test_which_knip_settings_the_include_option_overrides` and `test_the_floor_names_each_gap`, and Unit 7's `test_two_items_on_one_line_fail`, `test_an_item_below_the_top_level_fails` and `test_another_knip_settings_file_fails` pin it.
5. **A Vitest test file that the tokeniser can misread.** Inputs: titles that are not plain strings, such as a template literal with `${}`, an identifier and `test.each(table)("x %s", ...)`; and JSX text with an apostrophe, such as `render(<p>Don't save</p>)`, before more tests. Expected: the diff step lists such a title as not checked and never reports it removed; the apostrophe hides no later test; a plain title moved to another file is not a removal. Unit 8's `test_a_title_that_is_not_a_plain_string_is_not_checked`, `test_jsx_text_with_an_apostrophe_keeps_the_titles`, `test_paired_jsx_apostrophes_do_not_hide_calls` and `test_jsx_text_and_attributes_are_not_javascript_calls` pin it.

6. **Shared stack directory:** Unit 10's `test_python_and_typescript_in_one_directory_keep_status_and_sync_working` covers existing projects in nested `app/` and root, one combined guide and row, and refusal of colliding new skeletons before any commit. Unit 3b's `test_status_and_sync_render_the_new_project_seeds_that_init_wrote` pins create-only sync.
7. **CODEOWNERS and Protected fallback:** Units 3a and 9 test nested Python/TypeScript settings with absent or unprotective base CODEOWNERS. Preserve PRO-147 errors and all Harness paths. The fallback never reads head CODEOWNERS. Unit 2's detection test also covers ignored, hidden, vendored and symlinked roots before writes.
8. **Review difficulty:** documents use medium review; exact bounded text corrections use easy review. First reviews of guardrail enforcement, CODEOWNERS/Protected-set/stack-detection code, and security, recovery or concurrency changes use a challenging floor. Assess Unit 14's rollback tests, Unit 12a's workflow tests and the fallback cases above at that floor. This is review guidance for these Tasks, not product orchestration logic.

## File Structure

`devctl/` means `rapid_ship/templates/common/tools/devctl/devctl/`; `sync` writes its vendored copy.

| File | PR | Responsibility |
| --- | --- | --- |
| `devctl/settings.py` | 6.1a | `StackName`, `ProjectStack`, `under`, `ProjectSettings.stacks` and `owners` |
| `devctl/jsonc.py` | 6.1a | JSON with comments and trailing commas, for `tsconfig.json` and `knip.jsonc` |
| `devctl/node.py` | 6.1a | A tool in `node_modules/.bin`, the install advice, ESLint's computed settings and when a severity is an error |
| `devctl/check/__init__.py` | 6.1a, 6.2a | Each stack's steps, their names and order, `StackStep`; 6.2a adds TypeScript and `--install` |
| `rapid_ship/kit/init.py` | 6.1b | `init`'s stacks (Unit 2), and `repository` from `origin` and the empty first commit (Unit 14) |
| `rapid_ship/kit/stacks.py` | 6.1b | Stack names, `--stack` options, detection and its proposal, each stack's `StackKit`, the derived template variables |
| `rapid_ship/templates/common/.rapid-ship/project.toml` | 6.1b | One `project.toml` seed for every set of stacks |
| `rapid_ship/templates/<stack>/AGENTS.md` | 6.1b, 6.3 | The stack guide, seeded at `<directory>/AGENTS.md` for a stack in a subdirectory |
| `rapid_ship/templates/<stack>/__root__/` | 6.1b, 6.3 | A stack's files at the repository root: its starter Patterns |
| `devctl/check/stacks/typescript.py` | 6.2a | The TypeScript steps, `install`, `SOURCE_EXTENSIONS` |
| `devctl/doctor_typescript.py` | 6.2a | doctor's `node`, `npm` and TypeScript floor items |
| `devctl/check/stacks/typescript_suppressions.py` | 6.2b | The TypeScript suppression forms, and knip's allowlist items in `knip.jsonc` |
| `devctl/check/stacks/typescript_references.py` | 6.2b | The `eslint:` and `type:` references for TypeScript |
| `devctl/check/stacks/vitest.py` | 6.2b | Vitest test identities by title chain, and tautologies |
| `rapid_ship/templates/common/.github/workflows/devctl-check.yml` | 6.2a | `setup-node` and `--install` |
| `rapid_ship/templates/typescript/` | 6.3 | The TypeScript seeds, React skeleton, starter Patterns and stack guide |

---

## PR 6.1a: devctl reads several stacks (`plan6-stacks`, on `main`)

### Unit 1: `[[stack]]` in devctl's settings and lock reader

**Files:**
- Modify: `devctl/settings.py`; `devctl/check/kit.py` (`_parsed_lock`); `rapid_ship/templates/python/.rapid-ship/project.toml:2` and `rapid_ship/templates/agnostic/.rapid-ship/project.toml:2`; this repository's `.rapid-ship/project.toml:2`, in place; `tests/devctl/check_workspace.py` (`project_settings`, and new `stack_table`)
- Create: `tests/devctl/test_devctl_settings_stacks.py`
- Modify, for the key's rewrite: each test that writes `stack = "<name>"` into a `project.toml` (`rg -l 'stack = |stack="|project_settings\(stack=' tests scripts`, about 100 lines in 28 files at `f107a89`; a lock's `stack =` in a `tests/test_kit_*.py` file is Unit 2's) and each `project_settings(stack=...)`; `tests/test_kit_contents.py::test_project_settings_seed_has_the_kit_defaults` and `tests/devctl/test_devctl_kit_step.py` (bodies only)

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


# tests/devctl/check_workspace.py
def stack_table(name: str, directory: str = ".") -> str: ...  # one [[stack]] table, as TOML
```

- `PROJECT_KEYS` gains `"stack": frozenset({"name", "directory"})`; `""` keeps `"stack"`. `Stack` is renamed `StackName`; `doctor_rules.py` imports the new name.
- `load_project` reads `stack` before the other tables:
  - a string: `.rapid-ship/project.toml: stack = "<value>" is no longer read; rewrite it as one [[stack]] table with name = "<value>" and directory = "."`;
  - absent: `.rapid-ship/project.toml [[stack]]: required; add one table for each stack, with its name and directory`;
  - each table through `_Table(item, f"{PROJECT} [[stack]] #{n}", PROJECT_KEYS["stack"])`: `name` through `choice` (`... #1 name: expected python or typescript or agnostic`); `directory` required. `"."` and `"./"` are the root, `"."`, with no symlink check, and never reach `_inside_repository`, which returns None for them because their parts are empty. Any other value is normalised by `_inside_repository` and must be an existing directory with no symlink at it or above it under the root, else `... #1 directory: expected a directory inside the repository that is not a symlink`;
  - `.rapid-ship/project.toml: two [[stack]] tables name <name> in <directory>`;
  - `.rapid-ship/project.toml: the agnostic stack cannot sit beside another stack`, and `... #<n> directory: the agnostic stack's directory is "."`.
- `owners` returns the stacks whose directory is the longest one that is `"."`, equals `path`'s directory or is a prefix of `path` at a `/`.
- `check/kit.py` reads the lock's `stack` as a string in `STACK_NAMES`, the older form, or as a list of tables, each with a `name` in `STACK_NAMES` and a string `directory`; anything else is `stack must be [[stack]] tables with name and directory`. The `diff` step reads the base's lock with the same parser. Unit 12b removes the older form.
- The Python and agnostic seeds, and this repository's `project.toml`, replace `stack = "<name>"     # python or agnostic` with Spec 1 section 4's two comment lines and one table at `"."`; the header comment and the blank line stay. Ruling: the comment names `typescript` from this PR on, because the loader accepts it.
- Until Units 4 and 3a replace them, each reader of `ProjectSettings.stack` reads `project.stacks[0].name`, so the tree stays green after this task.

- [ ] **Step 1: write the failing tests.** `test_devctl_settings_stacks.py`, docstring `Offline: [[stack]] tables in fixture repositories.`:
  - `test_stacks_load_sorted_and_normalised`: tables for `typescript` in `./frontend/` and `python` in `backend`, in that order, load as `(ProjectStack("python", "backend"), ProjectStack("typescript", "frontend"))`, and one `python` table with `directory = "./"` loads as `(ProjectStack("python", "."),)`.
  - `test_invalid_stacks_raise_settings_error`, parametrized over each message above: the old key, no table, `stack = []` (the `[[stack]]: required; ...` message), `name = "go"`, an unknown key `path` (`... #1: unknown key 'path'; it accepts directory, name`), no `directory`, the directories `../x`, `/x`, `a\\b`, `missing`, a symlink `link` and `link/sub`, two `python` tables in `backend`, `agnostic` beside `python`, and `agnostic` in `docs`.
  - `test_owners_are_the_stacks_of_the_innermost_directory`: with `python` in `.`, `python` in `frontend` and `typescript` in `frontend`, `owners("frontend/src/a.ts")` is both `frontend` stacks, `owners("src/app/a.py")` is `python` in `.`, and with only `python` in `backend`, `owners("README.md") == ()`. With only `python` in `.` and `typescript` in `frontend`, `owners("frontend/src/a.ts") == (ProjectStack("typescript", "frontend"),)`.
  - In `test_devctl_kit_step.py`, `test_both_lock_forms_are_read`: a lock with `stack = "python"` and one with a `[[stack]]` table give the same managed paths; `stack = "go"` makes the `kit` step blocked.
  - `test_project_settings_seed_has_the_kit_defaults` expects `"stack": [{"name": stack, "directory": "."}]`, and `"escalation": {"every_pr": True}` as the descope's code leaves it.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_settings_stacks.py -q`; expected FAIL with `ImportError: cannot import name 'ProjectStack'`.
- [ ] **Step 3: implement** the settings, lock reader and seeds. Rewrite fixtures with `stack_table`. Rewrite this repository's `project.toml` (Protected; G5 asks; in a headless Session the owner makes this edit). Format, lint and sync as Global Constraints require.
- [ ] **Step 4: run** `uv run pytest tests/devctl tests/test_kit_contents.py tests/test_kit_seed_keys.py -q`; expected PASS. `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 5: commit** `feat: read [[stack]] tables in devctl's settings`.

### Unit 1b: JSONC reader and Node.js helpers

**Files:** create `devctl/jsonc.py`, `devctl/node.py`, `tests/devctl/test_devctl_jsonc.py` and `tests/devctl/test_devctl_node.py`; add `node_tools` to `tests/devctl/check_workspace.py`.

**Interfaces:**

```python
# devctl/jsonc.py
def loads(text: str) -> object: ...  # ValueError for text that is not JSON once comments go


# devctl/node.py
ESLINT_PROBE = "src/index.ts"  # the file whose settings eslint --print-config computes


def node_tool(directory: Path, name: str) -> Path | None: ...  # directory/node_modules/.bin/name
def install_advice(directory: Path) -> str: ...
def cannot_run(tool: str, label: str, reason: str, directory: Path) -> str: ...
def eslint_config(directory: Path) -> Mapping[str, object] | str: ...  # a str is the reason
def is_error(severity: object) -> bool: ...


# tests/devctl/check_workspace.py
def node_tools(directory: Path, **bodies: str) -> None: ...  # fakes in node_modules/.bin
```

- `jsonc.loads` drops `//` and `/* */` comments and a trailing comma before `}` or `]`, outside strings, then calls `json.loads`.
- `devctl/node.py`, for every caller that runs a Node.js tool: the TypeScript steps, doctor's floor and the TypeScript references.
  - `install_advice` is `run npm ci there` when `directory/package-lock.json` exists, else `run npm install there and commit package-lock.json`.
  - `cannot_run` is `cannot run <tool> in <label>: <reason>; <install_advice(directory)>`, the one text for a Node.js tool that cannot run. `<label>` is the stack's directory, `.` for the root.
  - `eslint_config` runs `node_modules/.bin/eslint --print-config ESLINT_PROBE` in `directory` through `process.run_process`, 120 seconds, and returns the JSON object it prints. Otherwise it returns the reason: `eslint is not installed`, `eslint timed out after 120 seconds`, `eslint exited <code>: <its last stderr line>`, or `eslint printed no JSON object`. Callers that resolve several references keep one result per directory.
  - `is_error` is true for `2` or `"error"`, alone or first in a list.

- [ ] **Step 1: write failing tests.**
  - `test_devctl_jsonc.py`, docstring `Offline: the JSONC reader.`: `test_jsonc_reads_comments_and_trailing_commas` turns `'{\n  // c\n  "a": [1, 2,], /* b */ "s": "// kept",\n}'` into `{"a": [1, 2], "s": "// kept"}`; `test_invalid_jsonc_raises_value_error` on `'{"a": }'`.
  - `test_devctl_node.py`, docstring `Offline: the Node.js helpers against fake tools in a fake node_modules/.bin.`:
    - `test_the_install_advice_follows_the_lock`: with `frontend/package-lock.json`, `cannot_run("eslint", "frontend", "eslint is not installed", root / "frontend")` is `cannot run eslint in frontend: eslint is not installed; run npm ci there`; without it, the text ends `run npm install there and commit package-lock.json`.
    - `test_eslint_config_reads_print_config`: a fake `eslint` that logs its argv and directory and prints `{"rules": {"no-console": ["error"]}}` gives that object, and ran `--print-config src/index.ts` in `frontend`; no `node_modules` gives `eslint is not installed`; exit 2 with stderr `boom` gives `eslint exited 2: boom`; the output `x` gives `eslint printed no JSON object`.
    - `test_a_severity_is_an_error_when_it_is_2_or_error`, parametrized: `2`, `"error"`, `[2]` and `["error", {}]` are errors; `1`, `"warn"`, `0`, `"off"`, `[]` and `None` are not.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_jsonc.py tests/devctl/test_devctl_node.py -q`; expected FAIL with missing `devctl.jsonc` and `devctl.node` modules during collection.
- [ ] **Step 3: implement** the helpers and fake-tool writer. Format, lint and sync.
- [ ] **Step 4: run** the exact Step 2 command again; expected PASS. Run `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 5: commit** `feat: add the JSONC reader and the Node.js helpers`.

### Unit 4: `check` for each stack

**Files:**
- Modify: `devctl/check/steps.py` (`CheckContext`, `CommandStep.run`), `devctl/check/__init__.py` (`core_steps`), `devctl/check/stacks/python.py` (`SOURCE_EXTENSIONS`; `AuditStep` runs in `context.directory`), `devctl/check/stacks/python_dead_code.py` (`DeadCodeStep` reads and runs in `context.directory`; `toml_allowlist(text, path)`), `devctl/check/exceptions.py` (`scan`, `ExceptionsStep.run`), `devctl/check/filesize.py` (`line_counts`), `devctl/check/references.py` (`resolve`), `devctl/check/map.py` (`_pattern_problems`, `_rule_problem`), `devctl/check/diff.py` (`DiffStep.run`)
- Create: `tests/devctl/test_devctl_check_stacks.py`
- Modify: `tests/devctl/test_devctl_references.py`, `test_devctl_exceptions_step.py`, `test_devctl_exceptions_allowlists.py`, `test_devctl_filesize_step.py`, `test_devctl_dead_code.py` (call sites only)

**Interfaces:**
- Consumes: `ProjectStack`, `ProjectSettings.owners`, `under` (Unit 1).
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
def resolve(
    reference: str, context: CheckContext, tracked: TrackedFiles, holder: str
) -> str | None: ...


# devctl/check/stacks/python_dead_code.py
def toml_allowlist(text: str, path: str = PYPROJECT) -> tuple[list[AllowlistItem], list[str]]: ...
```

- `stack_steps("python")` is `([FORMAT, LINT], [TYPES, CONTRACTS, DeadCodeStep(), TESTS, AuditStep()])`, `stack_steps("agnostic")` is `([], [])`, and any other name raises `ValueError("devctl has no check steps for the <name> stack")`, which blocks the step list through `_blocked_on_error`. 6.2a adds `typescript`.
- `core_steps` builds the order of Global Constraints, wrapping each stack step in `StackStep(step, stack, step_name(step.name, stack, project.stacks), step.tier)`. `StackStep.run` calls `step.run(dataclasses.replace(context, stack=self.stack))` and returns the result with `name=self.name`.
- `CommandStep.run`, `AuditStep`, `DeadCodeStep` and `_deptry` run in `context.directory` and read `pyproject.toml` there. A project step runs as a common step, at the root.
- `exceptions.scan(root, files, managed, project)`: a `.py` or `.pyi` file with a `python` owner gets `_python_lines`; a `pyproject.toml` directly in a Python stack's directory gets `_pyproject_lines`, and `ExceptionsStep.run` appends `toml_allowlist(text, path)[1]` for it; every other file gets `_text_lines`. `toml_allowlist`'s messages name `path` where they named `pyproject.toml`, and the comment on `AllowlistItem.line` names its settings file, so that knip's items reuse the type.
- `filesize.line_counts(root, files, source_roots, managed, project)` counts a file whose owners' `SOURCE_EXTENSIONS` hold its suffix, and every file when an owner is agnostic or it has none.
- `resolve(reference, context, tracked, holder)`: `holder` is the Pattern's `reference` path, or the guide that states the Rule; when a Pattern's `reference` is missing or does not exist, the holder is the Pattern file itself. `check:<step>` resolves when a common step, or a step of a holder's stack (any stack when the holder has none), has that base name or its exact directory-qualified result name. `ruff:`, `banned:`, `contract:` and `type:` resolve against the `pyproject.toml` of the holder's Python stack, and their messages name that file by its repository path; `type:<path>` compares `path` relative to that directory with mypy's `files` and `exclude`. Read `under(stack.directory, "pyproject.toml")` through `TrackedFiles`; untracked settings or referenced files return `tracked.why_untracked` advice, including ignored paths, case mismatches and symlink targets. A holder inside a stack without that kind gives `<reference>: unknown reference kind <kind> for <holder>`. A holder with no owning stack (root guide, Pattern without a reference, Corrections ledger) selects the unique stack defining the kind. If several match, fail with sorted candidate stacks and advise `test:<path>::<name>` or `check:<step>` with its directory-qualified name, such as `lint (backend)`; do not select silently or introduce selector syntax. `test:<path>::<name>` chooses its reader by the test file, whatever the holder: Python identities for a `.py` file, and the word search for any other file until 6.2b adds Vitest's.
- `DiffStep.run` applies the removed-test, tautology and autouse rules to the changes whose owners include a Python stack.

- [ ] **Step 1: write the failing tests.** `test_devctl_check_stacks.py`, docstring `Offline: each stack's check steps in fixture repositories, with fake tools on PATH.`:
  - `test_one_python_stack_at_the_root_keeps_the_step_names`: `[step.name for step in core_steps(project)]` equals `test_devctl_step_order.PYTHON`.
  - `test_step_names_follow_the_stacks`: `python` in `backend` and `worker` gives `format (backend)`, `lint (backend)`, `format (worker)`, `lint (worker)`, `map`, `exceptions`, `file-size`, `kit`, then `types`, `contracts`, `dead-code`, `tests`, `audit` for `backend` and then `worker`, then `secrets`, `workflows`, `diff`, `evidence`. `step_name("lint", ProjectStack("python", "."), (ProjectStack("python", "."), ProjectStack("typescript", "frontend"))) == "lint (.)"`, and `step_name("lint", ProjectStack("typescript", "frontend"), (ProjectStack("python", "."), ProjectStack("typescript", "frontend"))) == "lint (frontend)"`; with `python` and `typescript` both in `app`, Python's name is `"lint (app, python)"`.
  - `test_a_stack_step_runs_in_its_directory`: a fake `uv` logs its working directory; `format (backend)` ran in `<root>/backend`, and `dead-code (backend)` read `backend/pyproject.toml`.
  - `test_a_stack_without_steps_blocks_the_step_list`: `typescript` in `frontend` gives one result, `blocked`, named `step list`, with the detail `ValueError: devctl has no check steps for the typescript stack`.
  - `test_suppressions_are_read_in_their_owners_forms`: `python` in `backend`; `x = 1  # noqa: E501` unmarked in `backend/src/app/a.py` fails, and the same line in `web/a.py` is no suppression; an unmarked `ignore_names` item in `backend/pyproject.toml` fails with `backend/pyproject.toml:4: suppression vulture.ignore_names:x needs ...`, and two items on its line give `backend/pyproject.toml:4: vulture.ignore_names holds 2 items on one line; ...`.
  - `test_file_size_counts_each_owners_source_files`: `python` in `backend`, `source_roots = ["backend/src/app", "docs/src"]`; a 501-line `backend/src/app/a.py` fails, a 501-line `backend/src/app/notes.txt` is not counted, and a 501-line `docs/src/x.txt` fails.
  - `test_references_resolve_against_the_holders_stack`: `python` in `backend` and `worker`, only `backend/pyproject.toml` selecting `BLE`. `resolve("ruff:BLE001", ctx, tracked, "backend/src/app/errors.py") is None`; for the holder `worker/src/w.py` it is `ruff:BLE001: Ruff does not select BLE001 in worker/pyproject.toml`; for `README.md` and `docs/corrections/entry.md`, it names `python (backend), python (worker)` and advises `test:<path>::<name>` or a directory-qualified `check:<step>`. Assert `check:lint (backend)` resolves and `check:lint (missing)` fails. No selector syntax is accepted. With only `python` in `backend`, the root guide and `docs/corrections/entry.md` resolve `ruff:BLE001` there. Untracked `backend/pyproject.toml` and an untracked type/test target fail with staging advice; stage each and resolution succeeds. Repeat with ignored files and untracked symlink targets, preserving PRO-152's refusals. `check:lint` resolves for `backend/AGENTS.md` and for `AGENTS.md`, and `check:nope` gives `check:nope: no devctl check step is named nope`. `type:backend/tests/test_inputs.py` resolves with `files = ["src", "tests"]` in `backend/pyproject.toml`.
  - `test_the_diff_rules_apply_to_the_python_stacks_files`: `python` in `backend`; a test removed from `backend/tests/test_a.py` fails undeclared, and one removed from `scripts/test_b.py` is not reported.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_check_stacks.py -q`; expected FAIL with `ImportError: cannot import name 'step_name'`.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q`; expected PASS, the step-order, references, exceptions, file-size, dead-code and diff tests unchanged in what they assert, apart from a `pyproject.toml` message that now names its repository path, and `test_python_only_kinds_do_not_resolve_for_the_agnostic_stack`, which now expects `ruff:S603: unknown reference kind ruff for <holder>` with its holder's path.
- [ ] **Step 5: commit** `feat: run each stack's check steps in its directory`.

### Unit 3a: doctor for each stack

**Files:**
- Modify: `devctl/doctor_local.py` (`_guardrail_item`, `_exclusions_item`, `local_items`), `devctl/doctor_rules.py` (`codeowners_problems`, and PRO-147's `_protected_paths` and `codeowners_error_problems`), `devctl/doctor_github.py` (the CODEOWNERS item's calls)
- Create: `tests/devctl/test_devctl_doctor_stacks.py`
- If PRO-158 merged first, modify `devctl/merge_guard_github.py` and `tests/devctl/test_devctl_merge_guard.py` for its Python fallback paths.
- Modify: `tests/devctl/test_devctl_doctor_github.py`, `test_devctl_doctor_github_limits.py` and PRO-147's `test_devctl_doctor_codeowners_errors.py` (call sites only)

Unit 3a starts once PRO-147 has merged and `plan6-stacks` has merged `origin/main`.

**Interfaces:**
- Produces:

```python
# devctl/doctor_rules.py
def protected_settings(stacks: Sequence[ProjectStack]) -> tuple[str, ...]: ...
def codeowners_problems(
    text: str, every_pr: bool, code_owner: str, stacks: Sequence[ProjectStack]
) -> list[str]: ...
def codeowners_error_problems(
    errors: Sequence[CodeownersError],
    text: str,
    every_pr: bool,
    stacks: Sequence[ProjectStack],
    branch: str,
) -> list[str]: ...
```

- `protected_settings` gives each Python stack's `PYTHON_PROTECTED_PATHS` under its directory, in stack order, such as `backend/pyproject.toml` and `backend/**/ruff.toml`. In Flight, `codeowners_problems` requires `PROTECTED_PATHS` and `protected_settings(stacks)`; 6.2a adds TypeScript's.
- PRO-147's `_protected_paths` becomes `(*PROTECTED_PATHS, *protected_settings(stacks))`, and its `codeowners_error_problems` takes `stacks` in place of `stack`, so that GitHub's errors count on each stack's lines under its directory.
- If PRO-158 merged first, keep its fallback trigger and common `PROTECTED_PATHS` root-anchored. Match Python settings at any depth: `/**/<path>`, retaining an existing `**/` prefix. Never read head CODEOWNERS. If PRO-158 has not merged, coordinate this contract with its owner and do not merge its branch.
- `local_items` gives one floor item per Python stack, reading `pyproject.toml` in its directory, named `Python guardrail settings` with one stack at the root and `Python guardrail settings (<directory>)` otherwise.
- `_exclusions_item` reads the root `pyproject.toml` only. It checks Ruff, mypy, vulture, deptry and pytest only with a Python stack at `"."`, because a stack's tools run in its directory and reach `tools/devctl` only from the root, and checks the uv workspace always. Without a root `pyproject.toml` it is ok with `no pyproject.toml, so no uv workspace`, unless a Python stack is at `"."`.

- [ ] **Step 1: write the failing tests.** `test_devctl_doctor_stacks.py`, docstring `Offline: doctor's per-stack items in fixture repositories; no GitHub.`:
  - `test_flight_codeowners_needs_each_python_stacks_settings_under_its_directory`: `python` in `backend`; a Flight CODEOWNERS whose settings lines are at the root gives `CODEOWNERS must name only @o for: backend/pyproject.toml, backend/**/ruff.toml, ...` in `PYTHON_PROTECTED_PATHS` order; with `/backend/...` lines it gives `[]`. With the `/backend/...` lines and a root `/pyproject.toml` line, `codeowners_error_problems` reports GitHub's unknown-owner error on the `/backend/pyproject.toml` line and ignores the same error on the root line.
  - `test_each_python_stack_gets_its_floor_item`: `python` in `backend` and `worker`, `worker/pyproject.toml` without vulture; the items are `Python guardrail settings (backend)`, ok, and `Python guardrail settings (worker)`, missing, whose detail holds `dev dependencies lack vulture`.
  - `test_the_exclusions_item_reads_the_root_pyproject`: `python` in `backend` without a root `pyproject.toml` is ok; a root one whose `[tool.uv.workspace] members = ["tools/*"]` is missing with the uv message; a root one with no Ruff exclusion is ok, because no Python stack is at the root.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_doctor_stacks.py -q`; expected FAIL with `TypeError` from `codeowners_problems`. For the conditional fallback, first add `test_kit_fallback_protects_python_settings_at_depth` in `test_devctl_merge_guard.py`: absent base CODEOWNERS and a base with no Protected lines both protect changes only to `backend/pyproject.toml` and `apps/api/pyproject.toml`. Test existing `**/ruff.toml` without doubling its prefix, current common Harness paths, and no head-CODEOWNERS read. Run `uv run pytest tests/devctl/test_devctl_merge_guard.py -q -k kit_fallback_protects_python_settings_at_depth`; expect failure before the extension and PASS afterward.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k doctor`; expected PASS.
- [ ] **Step 5: commit** `feat: give each stack its doctor items`.

### Unit 5: This repository's check, documents and PR 6.1a's verification

**Files:**
- Modify: `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, the root `AGENTS.md` (plan 6 under "Not built yet"), Spec 1's status line, section 4's `[[stack]]` bullet (agnostic at `"."`) and section 5 References (unique-stack resolution outside stack directories; ambiguity names candidates and supported test/check alternatives), the plan index (plan 6's row and outline: the five PRs, the task split and Unit 14; Shared interfaces: the Settings sketch's `StackName`, `ProjectStack.directory`, `owners`, and `codeowners_problems` with `stacks`; Layout: `jsonc.py` and `node.py`), this plan's Verification record

- [ ] **Step 1: check the names.** `uv run rapid-ship status --strict` exits 0. `./devctl check --tier full --json --base main --pr-body <draft body>` lists exactly `main`'s step names in `main`'s order, the project's three included, and exits 0.
- [ ] **Step 2: documents.** Describe `[[stack]]`, the step names, ownership and doctor's per-stack items in the files above. Record the no-owner reference contract in Spec 1 section 5, including exact directory-qualified check names and the guided ambiguity error; one-stack repositories retain their behavior. Commit `docs: describe several stacks in devctl`.
- [ ] **Step 3: verify** with `--base main`, record the five checks, and commit `docs: record PR 6.1a's verification`. The PR body's Evidence lists them, with `Not covered: rapid-ship init still writes one stack at the root (6.1b); a TypeScript stack blocks the step list until 6.2a`.

## PR 6.1b: rapid-ship writes several stacks (`plan6-stacks-init`, on `plan6-stacks`)

### Unit 2: `init --stack NAME[=DIRECTORY]`, detection, and the lock's `[[stack]]`

**Files:**
- Create: `rapid_ship/kit/stacks.py`, `tests/test_kit_stacks.py`
- Modify: `rapid_ship/kit/templates.py` (`Stack` and `STACKS` move to `stacks.py`), `rapid_ship/kit/lock.py` (`Lock.stacks`, `Lock.older_form`), `rapid_ship/kit/init.py` (`init_repository`, `InitResult.stacks`), `rapid_ship/kit/status.py` (`StatusReport.stacks`), `rapid_ship/kit/sync.py:65,105,136` (`SyncResult.lock_rewritten`), `rapid_ship/kit/existing_checks.py` (`find_existing_checks(root, directories)`), `rapid_ship/cli.py` (`--stack`, `_init`, `_status`, `_sync`)
- Modify: `scripts/smoke_distribution.py:124`, where `init` relied on the default this task removes, and step 4 of `scripts/AGENTS.md` to match
- Modify: `tests/test_kit_lock.py`, `tests/test_kit_init.py`, `tests/test_kit_init_existing_checks.py`, `tests/test_kit_cli.py`, `tests/test_kit_status.py`, `tests/test_kit_sync.py`, `tests/conftest.py`, and the other `tests/test_kit_*.py` call sites

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
    older_form: bool = False  # read from stack = "<name>"; sync rewrites it


# rapid_ship/kit/sync.py
@dataclass
class SyncResult:
    ...  # the fields as before
    lock_rewritten: bool = False  # the lock was in the older form; changed counts it


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
- `parse_stack` splits at the first `=`; the directory defaults to `"."`. `"."` and `"./"` are the root, `"."`; any other directory is normalised as `relative_parts` does, which refuses `"."` because its parts are empty. Errors: `--stack <option>: the stack is python or agnostic` (from `STACKS`), and `--stack <option>: the directory is outside the repository`.
- `checked_stacks` sorts by `(directory, name)` and raises `KitError` for `--stack <name>=<directory> is given twice`, `the agnostic stack stands alone; remove the other --stack options`, `--stack agnostic=<directory>: the agnostic stack's directory is the root`, a directory under a symlink (`safe_path`, which the root skips), and a path that exists and is not a directory (`--stack <name>=<directory>: not a directory`). A directory that does not exist yet is accepted.
- `detect_stacks` reads the paths of `git ls-files -z --cached --others --exclude-standard`, skips a path with a part in `SKIPPED` or starting with `.`, and proposes `python` for each directory holding `pyproject.toml`, with the marker paths found, sorted. Unit 10 adds `typescript` for a directory holding both `package.json` and `tsconfig.json`.
- `proposal` exactly, with a line per root and `--stack <name>` for the root, `--stack <name>=<directory>` otherwise:

```text
init wrote nothing: confirm the stacks first. It found these stack roots:
  python in . (pyproject.toml)
  python in services/api (services/api/pyproject.toml)
Confirm them with the owner, or ask the owner for the stacks, then run init again with:
  --stack python --stack python=services/api
```

  With no root: `init wrote nothing: it found no stack root, a directory with pyproject.toml (python). Ask the owner for the stacks, then run init again with --stack NAME[=DIRECTORY] for each stack, or with --stack agnostic.` Unit 10 adds ` or with package.json and tsconfig.json (typescript)` before the first full stop.
- `init_repository` keeps its preconditions first; then, without stacks, raises `KitError(proposal(detect_stacks(root)))`. In this task it renders one stack at `"."` only and raises `KitError("this rapid-ship renders one stack at the root only")` otherwise; Unit 3b removes that refusal inside this PR. Until then `init`, `status` and `sync` render `stacks[0].name` with today's `render_files`. The Python new-project seeds are written when the stack's directory holds no `pyproject.toml`.
- `read_lock` reads `stack` as a string, the older form, as `(ProjectStack(stack, "."),)` with `older_form=True`, or as a list of tables with `name` and `directory`, whose `directory` it normalises as `parse_stack` does; `write_lock` always writes `[[stack]]` tables after `kit_version`. The lock's error `stack must be python or agnostic` becomes `[[stack]] #<n>: name must be python or agnostic and directory a path inside the repository`.
- `sync` rewrites a lock in the older form even when no file changed: `lock_rewritten` is true, and `_sync` prints `Rewrote .rapid-ship/kit.lock with [[stack]] tables.` before `Wrote the changes to the work tree.` Without `--in-place`, the lock is the commit's only file.
- `find_existing_checks(root, directories)` also reads the settings files in each stack directory other than `"."`, listed as `<directory>/<name>`; hooks and workflows stay root-only.
- CLI: `--stack` is `action="append"`, `type=` a function that turns `parse_stack`'s `KitError` into `argparse.ArgumentTypeError`, `metavar="NAME[=DIRECTORY]"`, help `a stack and its directory, the root by default; repeat it for each stack. Without it, init proposes the stacks it finds and writes nothing`. `_init` prints `Vendored the {describe(stacks)} Kit ...`, unchanged for one root stack. `status` prints `stack {describe(...)}`, and `status --json` replaces `"stack"` with `"stacks": [{"name": ..., "directory": ...}]`.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_stacks.py`, docstring `Offline: stack options, detection and the lock's [[stack]] in scratch git repositories.`:
  - `test_a_stack_option_names_a_stack_and_a_directory`: `parse_stack("python")`, `parse_stack("python=.")` and `parse_stack("python=./")` each equal `ProjectStack("python", ".")`, and `parse_stack("python=./backend/") == ProjectStack("python", "backend")`; `go`, `python=../x` and `python=/x` raise `KitError` with the texts above.
  - `test_stacks_are_checked_and_sorted`: each refusal above, a directory that does not exist accepted, and `[python in worker, python in backend]` sorted.
  - `test_detection_finds_nested_roots_and_skips_vendored_directories`: tracked `pyproject.toml`, `services/api/pyproject.toml`, `node_modules/x/pyproject.toml`, `.venv/lib/pyproject.toml`, `build/pyproject.toml` and `dist/pyproject.toml` give `python` in `.` and in `services/api` only. Add ignored, hidden and symlinked marker directories: none is proposed. The proposal and refusal cases write no file or commit.
  - `test_init_without_stack_proposes_and_writes_nothing`: that repository; `init_repository(root, stacks=(), ...)` raises `KitError` whose text equals the proposal above; `git status --porcelain` is empty, and no branch `rapid-ship/init` exists. An empty repository gives the no-root text.
  - In `test_kit_lock.py`, `test_an_older_lock_reads_as_one_stack_at_the_root_and_is_rewritten`: a lock with `stack = "python"` reads as `(ProjectStack("python", "."),)` with `older_form`, and `write_lock` writes `[[stack]]\nname = "python"\ndirectory = "."`.
  - In `test_kit_sync.py`, `test_sync_rewrites_an_older_lock`: in a vendored repository whose lock's `[[stack]]` table is replaced by `stack = "python"` and whose files are current, `sync_repository(root, in_place=True)` gives `lock_rewritten` and no other change, and the lock then holds one `[[stack]]` table.
  - `test_init_needs_a_stack_without_pyproject` keeps its name and now expects the no-root proposal; `tests/test_kit_cli.py::test_init_without_a_stack_prints_the_proposal_and_exits_2` asserts `rapid-ship init` without `--stack` in a repository with `pyproject.toml` exits 2 and prints the proposal to stderr.
  - `scripts/smoke_distribution.py`: in the existing project, `init` without `--stack` exits 2 and prints `--stack python`; then `init --stack python` runs as before.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_stacks.py tests/test_kit_lock.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'rapid_ship.kit.stacks'`.
- [ ] **Step 3: implement**; update the call sites and pass `--stack python` where a test relied on the old default.
- [ ] **Step 4: run** `uv run pytest tests/test_kit_*.py -q`; expected PASS. `uv run rapid-ship status --strict`; expected exit 0. `uv build --clear`, then `uv run python scripts/smoke_distribution.py`; expected exit 0.
- [ ] **Step 5: commit** `feat: name stacks and their directories in rapid-ship init and the lock`.

### Unit 14: `init`'s `repository` from `origin`, and a repository without commits

The hello-rapid-ship trial's PRO-159 and PRO-161. They are built here because Unit 2 rewrites `init` (Deviations).

**Files:**
- Modify: `rapid_ship/kit/init.py` (`resolve_variables`, `_default_project_name`, `InitResult`, `init_repository`, `_stopped`), `rapid_ship/cli.py` (`_init`'s report, `--repository`'s help)
- Modify: `scripts/smoke_distribution.py:113-114` and step 3 of `scripts/AGENTS.md`
- Modify with implementation 6.1b: Spec 1 section 3 steps 3, 7–9 and section 8's bootstrap ordering before the ruleset and Setup PR. This document PR changes no spec behavior.
- Modify: `tests/test_kit_init_variables.py`, `tests/test_kit_init.py`, `tests/test_kit_stacks.py`, `tests/test_kit_cli.py`, `tests/test_kit_sync.py`, `tests/test_kit_hooks.py`, `tests/conftest.py` as needed, and each other test that expected the Kit as a repository's first commit on its current branch (bodies only)

**Interfaces:**
- Consumes: `init_repository(root, *, stacks, variables, templates_root)` and `InitResult` (Unit 2).
- Produces:

```python
# rapid_ship/kit/init.py
FIRST_COMMIT_MESSAGE = "chore: start the repository"


@dataclass(frozen=True)
class InitResult:
    ...  # the other fields, unchanged
    base: str = ""  # the branch, or for a detached HEAD the commit, that init started from
    first_commit: str = ""  # the empty commit init made in a repository without commits


def _origin_repository(root: Path) -> str | None: ...  # owner/name of a github.com origin
```

- `resolve_variables`: without `--repository`, `repository` is `_origin_repository(root)`, which `_GITHUB_REMOTE` parses and `_REPOSITORY` checks, as for the project name today; otherwise `""`. The project name then defaults from that repository. Only the parsed name leaves the function, never the URL, which can carry a token. Ruling: `owner` keeps no default (Deviations). `--repository`'s help becomes `owner/name on GitHub; default: the origin remote's, when it is on github.com`.
- `init_repository`: the refusal of an existing `rapid-ship/init` applies with or without commits, because an orphan branch can sit beside one. In a repository without commits, after the plan and the existing-checks listing and before the branch, `init` runs `git commit --allow-empty --quiet --message FIRST_COMMIT_MESSAGE` through `git()`, so no hook runs. It then goes on as in a repository with commits: `base` is the current branch, and `first_commit` the new commit. A refusal, a conflict or a missing stack therefore makes no commit. The path that committed the Kit on the current branch, with `base=None`, goes.
- Undo: when a later step fails, `_stopped` leaves `rapid-ship/init` as before, then runs `git update-ref -d refs/heads/<base> <first_commit>`, so the repository has no commits again. Its message then ends `back on <base>, rapid-ship/init and the empty first commit deleted`. When the empty commit itself fails, nothing was written, and the `KitError` starts `init stopped (git commit failed: ` with git's message.
- `_init`'s report when `first_commit` is set: `The repository had no commits, so init made an empty first commit, <first_commit[:12]>, on <base>.`, then the usual `Committed the Kit as <commit[:12]> on rapid-ship/init, a new branch from <base>.`, and the next step `Next: push <base> from your own terminal, because the Kit's guardrails deny an agent's push to the default branch; then open a pull request from rapid-ship/init. The rs-setup skill in your coding agent does that.` A repository with commits gets today's report.

- [ ] **Step 1: write the failing tests.**
  - In `tests/test_kit_init_variables.py`, `test_variables_default_to_the_origin_repository_name` keeps its name: with `origin` at `git@github.com:octo/Widget.git`, `repository == "octo/Widget"`, `project_name == "Widget"` and `owner == ""`. `test_a_non_github_origin_falls_back_to_the_checkout_directory` also asserts `repository == ""`, and `test_an_invalid_origin_name_is_named_without_the_url_or_its_token` still finds neither the URL nor the token in the message.
  - In `tests/test_kit_init.py`, `test_init_without_commits_makes_the_first_commit_on_the_current_branch` keeps its name. `result.branch == INIT_BRANCH` and `result.base == "main"`. `main` holds one commit, `result.first_commit`, with the message `chore: start the repository` and an empty tree: `git ls-tree -r main` prints nothing. `rapid-ship/init^` is `result.first_commit`, and the work tree is clean.
  - `test_a_failed_commit_restores_the_starting_state` keeps its name; with no commits, `git rev-parse --verify --quiet HEAD` prints nothing afterwards. `test_init_refuses_an_existing_init_branch_before_writing` gains a case: on an orphan branch `fresh` beside `rapid-ship/init`, `init` refuses and `fresh` still has no commit.
  - New, `test_a_failure_after_the_first_commit_leaves_no_commits`: with `commit_paths` in `rapid_ship.kit.init` replaced by one that raises `KitError("git commit failed: boom")`, `init_repository` raises a `KitError` whose text starts `init stopped (git commit failed: boom)`. Afterwards `main` is the current branch and has no commit, no `rapid-ship/*` branch exists, and the work tree holds no file.
  - In `tests/test_kit_stacks.py`, the empty repository of `test_init_without_stack_proposes_and_writes_nothing` still has no commit afterwards.
  - In `tests/test_kit_cli.py`, `test_init_status_and_sync_with_the_packaged_kit` keeps its name. Its empty repository gets `origin` at `https://github.com/octo/app.git`. The output holds the two report lines above and `Next: push main from your own terminal, because the Kit's guardrails deny an agent's push to the default branch; then open a pull request from rapid-ship/init. The rs-setup skill in your coding agent does that.`, and `.rapid-ship/project.toml` holds `repository = "octo/app"`. `status --strict` and `sync --in-place` follow as before.
  - `scripts/smoke_distribution.py`: the new project's `init` leaves it on `rapid-ship/init`, and its default branch holds one commit.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_init.py tests/test_kit_init_variables.py tests/test_kit_cli.py -q`; expected FAIL on the tests above.
- [ ] **Step 3: implement** and update commitless fixtures, preserving test names. `tests/conftest.py::git_repo` starts without commits: inspect every init caller, not just the new case. Update `test_kit_init.py`'s branch/count assertions (formerly lines 372–373), `test_kit_sync.py`'s no-op branch and sync base/PR assertions (formerly 63, 80, 89), `test_kit_hooks.py`'s rollback branch expectations (formerly 159, 191), `test_kit_cli.py`'s initial report (formerly 31), and the distribution smoke. After init, the current branch is `rapid-ship/init`, its parent is the empty first commit, and subsequent sync starts from that branch unless the fixture explicitly returns to `main`. Fixtures needing committed history create it explicitly; commitless refusal/rollback cases must retain no commits. Search `rg -n 'init_repository|INIT_BRANCH|rev-list|result.base|branch.*main' tests/test_kit_*.py scripts/smoke_distribution.py`; inspect every affected assertion. Keep the no-hook tests covering both the empty commit and the Kit commit.
- [ ] **Step 4: run** `uv run pytest tests/test_kit_init.py tests/test_kit_init_variables.py tests/test_kit_cli.py tests/test_kit_sync.py tests/test_kit_hooks.py tests/test_kit_stacks.py -q`; expected PASS for both initial-history cases and all rollback/hook assertions. Then `uv run pytest tests/test_kit_*.py -q`; expected PASS. `uv build --clear`, then `uv run python scripts/smoke_distribution.py`; expected exit 0. Commit `fix: take init's repository from origin, and give a repository without commits an empty first commit (PRO-159, PRO-161)`.
- [ ] **Step 5: documents.** Spec 1 section 3 step 3 (`--repository`'s default; `--owner` has none), step 7 (the empty first commit), step 8 (its undo) and step 9 (the report), and section 8 before the ruleset step and at step 13: for an initially commitless repository, init option A creates the default branch's first empty commit and the Kit branch; the owner pushes the default branch from their own terminal BEFORE `rs-setup` applies the ruleset that blocks direct pushes; then push `rapid-ship/init` and open its Setup PR. Plan 7 depends on this ordering; the `init.py` bullet of `rapid_ship/kit/AGENTS.md`; step 3 of `scripts/AGENTS.md`. Commit `docs: describe init's repository default and its empty first commit`.

### Unit 3b: Rendering under directories, the repository seeds from every stack, and PR 6.1b's verification

**Files:**
- Modify: `rapid_ship/kit/stacks.py` (`StackKit`, `KITS`, `derived_variables`, `stack_variables`), `rapid_ship/kit/templates.py` (`KitManifest.new_project`, `Template.new_project`, `render_files`, `_render_text`), `rapid_ship/kit/init.py`, `rapid_ship/kit/status.py`, `rapid_ship/kit/sync.py` (`render_files` calls; the new-project filter reads `Template.new_project`)
- Templates: move `rapid_ship/templates/python/.rapid-ship/project.toml` to `common/.rapid-ship/project.toml` and delete `agnostic/`; delete `python/.github/CODEOWNERS` and give `common/.github/CODEOWNERS` the `{{stack_patterns}}` and `{{stack_protected}}` lines; delete `python/AGENTS.md` and give `common/AGENTS.md` the `{{stack_rows}}`, `{{stack_rules}}` and `{{lint_marker}}` variables; create `python/AGENTS.md`, the stack guide; move `python/docs/patterns/python-*.md` to `python/__root__/docs/patterns/`, their paths prefixed with `{{directory}}`; `kit.toml`
- Create: `tests/test_kit_stacks_render.py`
- Modify: `tests/test_kit_contents.py`, `tests/test_kit_templates.py`, `tests/test_kit_starter_patterns.py`, `tests/test_kit_seed_keys.py` (the `rendered` and `seed` helpers render `(ProjectStack(stack, "."),)`); `rapid_ship/templates/AGENTS.md`, `rapid_ship/AGENTS.md`, `rapid_ship/kit/AGENTS.md`
- Modify: this repository's `.rapid-ship/project.toml`, whose `[map] exclude` drops `rapid_ship/templates/agnostic` (Protected; G5 asks; in a headless Session the owner makes this edit)

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
        "stack_title",
        "unit_tests",
    }
)


def derived_variables(
    stacks: Sequence[ProjectStack], variables: Mapping[str, str]
) -> dict[str, str]: ...
def stack_variables(stacks: Sequence[ProjectStack]) -> dict[str, str]: ...  # one directory


# rapid_ship/kit/templates.py
@dataclass(frozen=True)
class KitManifest:
    ...
    new_project: Mapping[StackName, frozenset[str]]  # layer-relative paths, __root__/ included


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
  - `stack_rows`: group stacks by directory. Root stacks contribute their combined `guide_rows`; each other directory contributes one row, `| The Python and TypeScript stacks | [app/](app/AGENTS.md) |` when both share `app/`; a single stack keeps its singular title;
  - `stack_rules`: each stack name's `guide_rules`, once per name;
  - `lint_marker`: `enforced by: check:lint` when every stack's `lint_rules` is true, else `advisory`.
  `<owner>` is the owner, or `<owner>` when it is empty, as `_value` renders it.
- `stack_variables(stacks)` takes all stacks in one directory, sorted by name. `directory` is `""` at `"."` and `<directory>/` otherwise. `guide_rows` combines and deduplicates their rows; `stack_title` names every stack there. Render one stack guide per non-root directory, using its first stack's guide template with these combined variables.
- For every proper non-root ancestor of a stack directory, also plan one seeded navigation guide. For `apps/web`, plan `apps/AGENTS.md` and `apps/web/AGENTS.md`. Use the first descendant stack's guide template with a neutral directory-navigation title and rows linking the immediate child guides relative to that ancestor. If an ancestor is itself a stack directory, coalesce its child rows into its stack guide; never render two guides at one path. Root `stack_rows` includes one row per stack or ancestor guide, using root-relative links, so all guides remain reachable even when an existing ancestor guide is retained. These guides are seeded, never new-project-only: existing files and symlinks are skipped by init and never rewritten by sync; absent paths use safe create-only writes and participate in rollback and lock bookkeeping.
- Rendering: `common/` renders at the root. A stack's templates render under its directory, with its directory's combined `stack_variables`. A stack's new-project templates render only for a stack in `new_projects`. Its `__root__/` files, all new-project seeds, render at the root for the first stack of each name in `new_projects`. A stack at `"."` renders no `AGENTS.md`: the root guide holds its rows. A stack template wins over a common one at the same path, except the root guide. After coalescing the stack guide only, two stacks' templates at one path, among the templates `render_files` returns, raise `KitError("<name> and <name> both write <path>; give one stack its own directory")`. A derived variable renders `""` when empty and never comments out its line, and a line that holds only a derived variable that renders `""` is dropped.
- `kit.toml`: `seeded` as today; `new_project` becomes a table of path lists by stack name, after the top-level keys, with paths relative to the stack layer, `__root__/` included:

```toml
[new_project]
python = [
    ".gitignore",
    "__root__/docs/patterns/python-configuration.md",
    "__root__/docs/patterns/python-error-handling.md",
    "__root__/docs/patterns/python-input-validation.md",
    "__root__/docs/patterns/python-performance.md",
    "pyproject.toml",
    "src/AGENTS.md",
    "src/__package__/__init__.py",
    # ... the other Python paths of today's list, unchanged
]
```

  `variables` gains the `DERIVED` names. `load_manifest` raises `KitError("kit.toml new_project: expected a table of path lists by stack name")` for another shape. `render_files` sets `Template.new_project` from that mapping; init, status and sync filter only on `Template.new_project`.
- `init` renders with `new_projects` = the stacks whose directory lacks their new-project marker. `status` and `sync` render with `new_projects` = the lock's stacks whose `under(directory, new_project_marker)` the lock records as a seeded entry: `init` wrote a stack's new-project seeds, the marker among them, only for a new project. `sync` never adds a template whose `new_project` is true.
- The common `project.toml` template holds the header, Spec 1 section 4's two stack comment lines, `{{stack_tables}}`, `source_roots = [{{source_roots}}]` and `unit = [{{unit_tests}}]   # every other test counts as behavioural`, otherwise as 6.1a's Python seed. Its `[escalation]` table holds `every_pr = true` alone, under `# The Mode. true is Walk: the owner merges every pull request. false is Flight.`, as Spec 1 section 4 shows.
- The common root guide keeps, word for word, the first Rule `Keep each change inside the scope you were asked to change.` and the `## Pull requests` section that Spec 1 section 4 quotes, between the Rules and the pointers. `{{stack_rules}}` sits after Rule 14, where the Python root guide holds its `dead-code` Rule today. The common CODEOWNERS template keeps the Flight comment that says to set `every_pr = false` in the same pull request.
- The stack guide, `python/AGENTS.md`: `# {{project_name}}: {{stack_title}}`, one sentence that the root guide, linked as `[root guide](/AGENTS.md)`, holds commands and Rules, then `## Find the change` with its table and `{{guide_rows}}`. The same template renders neutral ancestor navigation guides; it must not claim that an ancestor without a stack runs stack checks.

- [ ] **Step 1: keep the root-stack seeds for comparison** before changing the rendering. Unit 2 leaves `render_files` as the base has it, so render `render_files("python", VARIABLES, ())` and `render_files("agnostic", VARIABLES, ())` with `test_kit_contents.VARIABLES`, and write their `AGENTS.md`, `.github/CODEOWNERS` and `.rapid-ship/project.toml` under `<scratchpad>/seeds-before/<stack>/`. Nothing is committed.
- [ ] **Step 2: write the failing tests.** `tests/test_kit_stacks_render.py`, docstring `Offline: the packaged templates rendered for several stacks.`:
  - `test_a_python_backend_renders_under_its_directory`: `python` in `backend`; the paths include `backend/pyproject.toml`, `backend/src/demo_app/__init__.py`, `backend/tests/test_settings.py`, `backend/AGENTS.md` and `docs/patterns/python-configuration.md`, whose front matter has `reference: backend/src/demo_app/settings.py` and `test:backend/tests/test_settings.py::test_an_out_of_range_value_is_rejected`; no rendered path is `pyproject.toml` or starts with `src/`.
  - `test_project_toml_and_codeowners_list_every_stack`: `python` in `backend` and `worker`; `tomllib` reads `project.toml`'s `stack` as both tables, `[map] source_roots` as `["backend/src/demo_app", "worker/src/demo_app"]` and `[tests] unit` as `["backend/tests/unit/**", "worker/tests/unit/**"]`; `escalation` reads as `{"every_pr": True}`; it loads with devctl's `load_project` once the directories exist. CODEOWNERS holds the four Pattern lines once, right after `# /.rapid-ship/ @octo`, and ends with the Python settings paths under `/backend/`, then under `/worker/`. Each of `doctor_rules.PROTECTED_PATHS` has its `# /<path> @octo` line, so the common lines follow `main`'s, `/.agents/` among them once PRO-155 has merged.
  - `test_the_root_guide_links_each_stack_guide`: `python` in `backend`; the root guide holds `| The Python stack | [backend/](backend/AGENTS.md) |` and the `dead-code` Rule, and both lint Rules end `enforced by: check:lint`, because every stack is Python; `backend/AGENTS.md` links `src/AGENTS.md` and `tests/AGENTS.md`.
  - `test_deep_stack_directories_have_reachable_ancestor_guides`: initialize a new Python skeleton at `services/api`, stage the result, and run the map step; expect PASS, with `services/AGENTS.md` and `services/api/AGENTS.md` each rendered and locked exactly once. Root navigation links both; the parent guide links `api/AGENTS.md`. Repeat for a Python stack at `services` above another at `services/api`; coalesce rows without duplicate guides. Unit 10 owns initialization with Python and TypeScript sharing deep `apps/web`, after TypeScript joins rapid-ship's names and kits. Existing regular or symlinked ancestor guides retain their bytes/target through init and sync; no write follows the symlink. A forced later init failure removes only newly created guides and retains existing ones.
  - `test_two_stacks_cannot_write_one_path`: a test template tree whose `python/` and `agnostic/` layers both list `.gitignore` as a new-project seed, rendered for both stacks at `"."` with both in `new_projects`, raises the `KitError` above; with only `python` in `new_projects`, it renders one `.gitignore`.
  - `test_init_writes_new_project_seeds_per_stack`: `init_repository` with `python` in `backend` (no `backend/pyproject.toml`) and `python` in `worker` (with one) writes `backend/pyproject.toml` and the Patterns, and no new-project file under `worker/`. The other way round, with `backend/pyproject.toml` and none in `worker`, it writes `worker/pyproject.toml` and the Patterns, whose `reference` is `worker/src/demo_app/settings.py`.
  - `test_status_and_sync_render_the_new_project_seeds_that_init_wrote`: after that first `init`, `status --strict` exits 0 and `sync_repository(root, in_place=True)` changes nothing. With a copy of the templates whose `python/pyproject.toml` differs, `sync_repository(..., templates_root=copy)` gives `seeded_changed == ["backend/pyproject.toml"]` and nothing under `worker/`; the existing backend file's bytes remain unchanged. A project-authored stack guide is never overwritten; a missing guide is created only where its path is absent, and a symlink there is retained.
  - `test_the_stack_kits_match_devctl`: `KITS["python"].protected == doctor_rules.PYTHON_PROTECTED_PATHS`, and `KITS["python"].patterns` equals the file names under `python/__root__/docs/patterns/`.
  In `test_kit_contents.py`, `test_every_manifest_path_exists_in_a_layer` reads `new_project` by stack; the CODEOWNERS and root-guide tests keep their names and assertions, and read the common templates rendered for each stack. Among them are `test_root_guide_keeps_changes_in_scope_and_says_how_to_handle_pull_requests` and `test_codeowners_moves_to_flight_with_every_pr_in_one_pull_request`, from the descope's code.
- [ ] **Step 3: run** `uv run pytest tests/test_kit_stacks_render.py -q`; expected FAIL on `test_a_python_backend_renders_under_its_directory`.
- [ ] **Step 4: implement**; remove Unit 2's one-root-stack refusal.
- [ ] **Step 5: run** `uv run pytest tests/test_kit_*.py tests/test_kit_seed_keys.py -q`, then the network test `uv run pytest tests/devctl/test_devctl_check_integration.py -q -k new_project`; expected PASS. Render the three files again with `render_files((ProjectStack(stack, "."),), VARIABLES, ())` into `<scratchpad>/seeds-after/<stack>/`, and run `cmp` on each pair; expected no output and exit 0, recorded in the Verification record. `uv run rapid-ship sync --in-place` prints `Rewrote .rapid-ship/kit.lock with [[stack]] tables.` and lists no file, because this repository's root-stack seeds render as before; the lock now holds one `[[stack]]` table. `uv run rapid-ship status --strict` and `./devctl check --tier fast` exit 0. Commit `feat: render each stack under its directory and the repository seeds from every stack`, with the lock.
- [ ] **Step 6: documents.** `ARCHITECTURE.md` (the CLI's `--stack`, detection, layers, the lock), `rapid_ship/templates/AGENTS.md` (`__root__`, stack guides, derived variables), `rapid_ship/kit/AGENTS.md`, `rapid_ship/AGENTS.md`; Spec 1 section 3 (init as built, Package layout with `agnostic/` gone and `__root__/`), section 4's Kit contents (one guide per stack directory and its maintained ancestors), Protected set (the common CODEOWNERS seed lists each stack's Pattern lines once after `/.rapid-ship/` and settings under its directory), merge guard step 4 if PRO-158 merged (the Kit set, no longer the Python seed's), and Root AGENTS.md skeleton (one root-guide seed where it names two), and section 10's descope bullet to match; the index's Kit manifest block and Layout (`stacks.py`, `__root__`). Commit `docs: describe rapid-ship's several stacks`.
- [ ] **Step 7: verify** with `--base origin/plan6-stacks`, record the five checks, and commit `docs: record PR 6.1b's verification`. `Not covered: the TypeScript stack's templates (6.3). Deep Python directories and their ancestor guides are covered by test_deep_stack_directories_have_reachable_ancestor_guides`.

## PR 6.2a: the TypeScript steps and doctor (`plan6-ts-steps`, on `plan6-stacks`)

### Unit 6: The TypeScript steps, knip and `check --install`

**Files:**
- Create: `devctl/check/stacks/typescript.py`, `tests/devctl/test_devctl_typescript_steps.py`
- Modify: `devctl/check/__init__.py` (`stack_steps`, `run_check`), `devctl/cli.py` (`--install`), `devctl/check/filesize.py` (TypeScript's extensions)

**Interfaces:**
- Consumes: `node.node_tool`, `node.cannot_run` and the `node_tools` test helper (Unit 1b).
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


# devctl/check/__init__.py
def run_check(context: CheckContext, tier: Tier, *, install: bool = False) -> list[StepResult]: ...
```

- `stack_steps("typescript")` is `([FORMAT, LINT], [TYPES, DEAD_CODE, TESTS, AuditStep()])`; TypeScript has no `contracts` step. With `install`, `run_check` runs one `StackStep(InstallStep(), ...)` per TypeScript stack first, in both tiers.
- `NodeStep.run` runs `node_tool(context.directory, <tool>)` by absolute path. When it is missing it blocks with `cannot_run(<tool>, <label>, "<tool> is not installed", context.directory)`, such as `cannot run prettier in frontend: prettier is not installed; run npm ci there`. Otherwise `command_result` decides: 0 passes, a failed code fails, any other code or a timeout blocks.
- `AuditStep` first requires `package-lock.json`. Without it, block with `cannot_run("npm audit", <label>, "there is no package-lock.json", context.directory)` and do not invoke npm. With a lock, it can run without `node_modules`. It runs `npm audit --json`, 600 seconds. npm missing blocks with `npm is not on PATH; it comes with Node.js`. Exit 0 passes. Exit 1 with a JSON object whose `vulnerabilities` is a non-empty object fails with one line per package, sorted: `<name> <severity>: <titles of its advisories in via, joined by "; ", or the package names in via>`. Exit 1 with an `error` object blocks with `npm audit: <error.code> <error.summary>`; any other output or exit blocks through `command_result`.
- `InstallStep` runs `npm ci --no-audit --no-fund`, 1200 seconds; without `package-lock.json` it blocks with `cannot_run("npm ci", <label>, "there is no package-lock.json", context.directory)`. Exit 0 passes; anything else blocks.
- `--install` help: `first run npm ci in each TypeScript stack's directory`.
- Ruling: the issue types in `KNIP_INCLUDE` are knip 6.43.0's own, as its reference lists them; `nsExports` and `nsTypes` stay off, as Spec 1 section 5 names neither.

- [ ] **Step 1: write the failing tests.** `test_devctl_typescript_steps.py`, docstring `Offline: the TypeScript steps against fake tools in a fake node_modules/.bin.`, with `typescript` in `frontend` and `node_tools(root / "frontend", ...)`:
  - `test_each_step_runs_its_tool_in_the_stack_directory`: each tool logs its argv and directory; the argv are exactly the commands of Global Constraints, each run in `<root>/frontend`, and the full tier's TypeScript steps are `format (frontend)`, `lint (frontend)`, `types (frontend)`, `dead-code (frontend)`, `tests (frontend)` and `audit (frontend)`, placed as Unit 4 orders stack steps.
  - `test_exit_codes_pass_fail_or_block`, parametrized: knip 0 passes, 1 fails, 2 blocks; tsc 1 and 2 fail, 3 blocks; eslint, prettier and vitest 1 fail, 2 block.
  - `test_a_missing_tool_blocks_with_the_install_command`: no `node_modules` with `frontend/package-lock.json` gives `blocked` and `cannot run prettier in frontend: prettier is not installed; run npm ci there`; without the lock, the text ends `run npm install there and commit package-lock.json`.
  - `test_npm_audit_reads_its_report`: without a lock, blocks with the install-and-commit advice and never calls npm. With a lock and no `node_modules`, a fake `npm` printing `{"vulnerabilities": {"vite": {"severity": "high", "via": [{"title": "Path traversal"}]}}}` and exiting 1 fails with `vite high: Path traversal`; `{"error": {"code": "ENOLOCK", "summary": "no lockfile"}}` with exit 1 blocks with `npm audit: ENOLOCK no lockfile`; exit 0 passes.
  - `test_install_runs_npm_ci_first` and `test_install_without_a_lock_blocks`: `run_check(..., install=True)` gives `install (frontend)` first, which ran `npm ci --no-audit --no-fund` in `frontend`; without the lock it blocks with the text above. Without `install`, no `install` step runs.
  - Remove `test_a_stack_without_steps_blocks_the_step_list`; declare `tests/devctl/test_devctl_check_stacks.py::test_a_stack_without_steps_blocks_the_step_list` under `Removed tests:` in 6.2a's PR body, covered by `test_each_step_runs_its_tool_in_the_stack_directory`.
  - `test_file_size_counts_typescript_sources`: a 501-line `frontend/src/a.tsx` fails and a 501-line `frontend/src/a.css` is not counted.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_typescript_steps.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.check.stacks.typescript'`.
- [ ] **Step 3: implement** the TypeScript steps; remove Unit 4's temporary unsupported-stack `ValueError` branch now that every `StackName` has steps. Format, lint and sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k "typescript or stacks or step_order"`; expected PASS. Unit 9 creates and runs the knip integration test only after Unit 12a provides CI's Node.js; no earlier test imports `doctor_typescript`.
- [ ] **Step 5: commit** `feat: add the TypeScript check steps and check --install`.

### Unit 12a: CI's Node.js and `--install`

**Files:**
- Modify: `rapid_ship/templates/common/.github/workflows/devctl-check.yml`, `tests/devctl/test_devctl_ci_templates.py`; this repository's workflow through `sync`

**Interfaces:**
- Consumes: `check --install` (Unit 6).
- After `astral-sh/setup-uv`, the workflow gains, with a comment on its contract:

```yaml
      # The TypeScript steps need Node.js; a repository without a package-lock.json skips it.
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        if: hashFiles('**/package-lock.json') != ''
        with:
          node-version: "24"   # the major the TypeScript seed's engines.node names
```

  and its last step runs `./devctl check --tier full --install`. The workflow stays one file for every project. Ruling: `node-version` is fixed, because a managed workflow cannot name a stack's directory; a project that changes `engines.node` changes this line, which makes the workflow its own. In this repository, `website/package-lock.json` sets up Node.js, which 6.2a's knip test and 6.3's integration tests need.

- [ ] **Step 1: write the failing tests.** In `test_devctl_ci_templates.py`, keep `test_job_checks_out_full_history_without_credentials_and_runs_the_full_tier`, expecting `./devctl check --tier full --install`. Add `test_node_is_set_up_only_where_a_package_lock_exists`, asserting its position after `astral-sh/setup-uv`; `setup-node` is pinned by a 40-character SHA with the `# v7.1.0` comment, its `if` is `hashFiles('**/package-lock.json') != ''`, its `node-version` is `"24"`, and the run step is `./devctl check --tier full --install`. Unit 10 checks that the TypeScript seed's `engines.node` names that major.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ci_templates.py -q`; expected FAIL.
- [ ] **Step 3: implement**, sync, then run `./devctl check --tier full`; its `workflows` step, zizmor 1.30.1, passes.
- [ ] **Step 4: commit** `ci: set up Node.js and install each TypeScript stack before the check`. The owner pushes this commit, because it edits `.github/workflows/`.

### Unit 9: doctor's Node.js and TypeScript floor items, and PR 6.2a's verification

**Files:**
- Create: `devctl/doctor_typescript.py`, `tests/devctl/test_devctl_typescript_doctor.py`, `tests/devctl/test_devctl_typescript_knip_include.py`
- Modify: `devctl/doctor_local.py` (`local_items` adds the new items), `devctl/doctor_rules.py` (`TYPESCRIPT_PROTECTED_PATHS`; `protected_settings` adds TypeScript stacks)
- If PRO-158 merged first: `devctl/merge_guard_github.py` and `tests/devctl/test_devctl_merge_guard.py`, extending its Kit fallback for TypeScript settings at depth.
- Documentation: root `AGENTS.md`, `tests/AGENTS.md`, `tools/AGENTS.md`, `ARCHITECTURE.md` and Spec 1 as Step 5 describes.

**Interfaces:**
- Consumes: `jsonc.loads`, `node.eslint_config`, `node.is_error` and `node.cannot_run` (Unit 1b).
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

- `KNIP_FLOOR_KEYS` holds the top-level keys under which this Unit's knip integration test exits 0 while `unused` exists, in the order `rules`, `include`, `exclude`, `ignoreExportsUsedInFile`; `ignoreExportsUsedInFile` is always among them, because no issue-type filter reaches it.
- `node_items` gives `node` and `npm` toolchain items only with a TypeScript stack. Each TypeScript stack's `engines.node` names a minimum, its first version padded with zeros (`24.x` is 24.0.0, `>=24.15.0 <25` is 24.15.0), and a major, that version's first integer. `node` is ok when `node --version` has each stack's major and is at least its minimum: `node v24.19.0, which frontend/package.json names (>=24.15.0 <25)`. It is missing with `node is not on PATH; install Node.js <major>`, `node v<version>, but <directory>/package.json names <range>; install Node.js <major>, <minimum> or later`, or `<directory>/package.json sets no engines.node`. `npm` is ok with its version, else missing with `npm is not on PATH; it comes with Node.js`.
- `floor_item`, named `TypeScript guardrail settings` with one stack at the root and `... (<directory>)` otherwise, reads `tsconfig.json`, `package.json` and `knip.jsonc` with `jsonc.loads`, `package-lock.json`'s presence, and `node.eslint_config(directory)`. When that returns a reason, the item is unknown: `cannot_run("eslint", <label>, <reason>, directory)`. An unreadable file is unknown and names it. With no gap the item is ok: `meets the TypeScript guardrail floor`.
- `floor_gaps`, in this order, one text each:
  - `tsconfig.json: compilerOptions.<option> is not true`, and when `tsconfig.json` sets `extends`, ` (it extends <value>, which doctor does not read)` after it;
  - `eslint: <rule> is not an error`; `eslint: complexity is not an error with a maximum of 10 or less`; `eslint: @typescript-eslint/ban-ts-comment does not ban @ts-ignore and @ts-nocheck and require a description on @ts-expect-error`; `eslint: linterOptions.reportUnusedDisableDirectives is not error`. A severity is an error when `node.is_error` says so;
  - `npm: devDependencies lack <names, comma-separated>`; `npm: engines.node is not set`; `npm: package-lock.json is missing; run npm install and commit it`;
  - `knip: knip.jsonc sets <key>, which can switch a kind off` for each key of `KNIP_FLOOR_KEYS` at its top level.
- `protected_settings` adds each TypeScript stack's `TYPESCRIPT_PROTECTED_PATHS` under its directory, after the Python stacks' in stack order.

- [ ] **Step 1: write the failing tests.** `test_devctl_typescript_doctor.py`, docstring `Offline: doctor's TypeScript items with fake node, npm and eslint.`:
  - `test_the_floor_names_each_gap`: `floor_gaps` on empty inputs gives the nine tsconfig texts, the five ESLint rule texts, the complexity, ban-ts-comment and directives texts, and the devDependencies, engines and lock texts, in that order; on the values that 6.3's seed holds, with `has_lock=True`, it gives `[]`; parametrize over every `KNIP_FLOOR_KEYS` key at the top level and assert its exact `knip: knip.jsonc sets <key>, which can switch a kind off` text. Each is a separate case.
  - `test_node_must_match_engines`, parametrized: `v24.19.0` with `>=24.15.0 <25` and `v24.0.0` with `24.x` are ok; `v24.3.0` with `>=24.15.0 <25` and `v22.1.0` with `24.x` are missing with the version text; no `node` is missing; no `engines.node` is missing.
  - `test_eslint_that_cannot_run_makes_the_floor_unknown`: no `node_modules` gives `unknown` and `cannot run eslint in frontend: eslint is not installed; run npm install there and commit package-lock.json`.
  - `test_flight_codeowners_needs_the_typescript_settings_under_its_directory`: `typescript` in `frontend`; the problem lists `frontend/package.json` through `frontend/.knip.*`.
  `test_devctl_typescript_knip_include.py`, docstring `Integration test: needs network access, Node.js 24 and npm; installs knip 6.43.0 and TypeScript 6.0.3 in a scratch project.`:
  - `test_which_knip_settings_the_include_option_overrides`: a scratch project whose `src/index.ts` is its entry and imports `a` from `./used.ts`, which also exports `unused`. For no settings, `{"rules": {"exports": "off"}}`, `{"rules": {"exports": "warn"}}`, `{"include": ["files"]}`, `{"exclude": ["exports"]}` and `{"ignoreExportsUsedInFile": true}` with `unused` used in its own file, it runs knip with `--include KNIP_INCLUDE` and records its exit code, the step's verdict. With no settings knip exits 1. The top-level keys of the settings under which it exits 0 equal `doctor_typescript.KNIP_FLOOR_KEYS` as a set (Unit 9).
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_typescript_doctor.py -q`; expected FAIL with missing `devctl.doctor_typescript`. If PRO-158 merged, add `test_kit_fallback_protects_typescript_settings_at_depth`: absent base CODEOWNERS or no Protected lines protect root, `frontend/` and `apps/web/` settings, including a PR changing only `frontend/eslint.config.js`. Verify each `TYPESCRIPT_PROTECTED_PATHS` entry and no head-CODEOWNERS read. Run `uv run pytest tests/devctl/test_devctl_merge_guard.py -q -k kit_fallback_protects_typescript_settings_at_depth`; expect FAIL before extending the fallback and PASS after. Keep common paths root-anchored and stack settings at any depth, as Unit 3a defines.
- [ ] **Step 3: implement**; run this Unit's knip integration test, `uv run pytest tests/devctl/test_devctl_typescript_knip_include.py -q`, and set `KNIP_FLOOR_KEYS` from what it shows; expected PASS. Format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q`; expected PASS. Commit `feat: add doctor's Node.js and TypeScript floor items`.
- [ ] **Step 5: documents.** `ARCHITECTURE.md` (the TypeScript steps, `--install`, CI's `setup-node`, doctor's items), `tools/AGENTS.md`, `tests/AGENTS.md`, and root `AGENTS.md`'s Commands (Protected; G5 asks; in a headless Session the owner makes this edit). All prerequisite descriptions, including `ARCHITECTURE.md`, say `./devctl check` and `uv run pytest` need network, gitleaks 8.30.1 on `PATH`, and Node.js 24.15.0 or later in major 24 with npm from this PR. Spec 1 section 5's Dead code bullet on `--include`, with the knip test's result; the index's Layout (`check/stacks/typescript.py`, `doctor_typescript.py`). Commit `docs: describe the TypeScript steps and doctor's items`.
- [ ] **Step 6: verify** with `--base origin/plan6-stacks`, record the five checks, and commit `docs: record PR 6.2a's verification`. `Not covered: a real TypeScript project, which 6.3's integration tests check; the TypeScript suppressions and references (6.2b)`.

## PR 6.2b: the TypeScript rules (`plan6-ts-rules`, on `plan6-stacks`)

### Unit 7: The TypeScript suppressions, knip's allowlist, and the TypeScript references

**Files:**
- Create: `devctl/check/stacks/typescript_suppressions.py`, `devctl/check/stacks/typescript_references.py`, `tests/devctl/test_devctl_typescript_suppressions.py`, `tests/devctl/test_devctl_typescript_knip_allowlist.py`, `tests/devctl/test_devctl_typescript_references.py`
- Modify: `devctl/check/exceptions.py` (`scan`, `ExceptionsStep.run`), `devctl/check/references.py` (kinds by stack)

**Interfaces:**
- Consumes: `jsonc.loads`, `ProjectSettings.owners`, `node.node_tool`, `node.eslint_config`, `node.is_error` and `node.cannot_run` (Unit 1b); `normal_rule` (`check/exceptions.py`); `python_dead_code.AllowlistItem` (Unit 4).
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
def knip_allowlist(text: str, path: str) -> tuple[list[AllowlistItem], list[str]]: ...


# devctl/check/stacks/typescript_references.py
def resolve_eslint(
    reference: str, rule: str, tracked: TrackedFiles, stack: ProjectStack
) -> str | None: ...
def resolve_type(
    reference: str, path: str, tracked: TrackedFiles, stack: ProjectStack
) -> str | None: ...
```

- The suppression forms of a file in a TypeScript stack, each found anywhere in the line's text, and its rule:

| Form | Rule |
| --- | --- |
| `eslint-disable-next-line`, `eslint-disable-line` or `eslint-disable`, then its rules up to an optional ` -- ` description, in a script file | `eslint:<rules, sorted, comma-joined>`, or `eslint` without rules |
| a block comment `/* eslint <rule>: <value>[, <rule>: <value>]... */`, which sets rules for the file, in a script file | `eslint:<its rule names, sorted, comma-joined>` |
| `@ts-expect-error`, in a script file | `ts-expect-error` |
| `prettier-ignore`, in any file of the stack | `prettier-ignore` |
| `istanbul ignore <word>`, `c8 ignore <word>` or `v8 ignore <word>`, except the word `stop`, in a script file | `no-cover` |
| `test`, `it`, `describe`, `suite` or `bench`, any `.<word>` chain, then `.skip`, `.skipIf`, `.runIf`, `.todo` or `.fails`, in a script file | `skip`, `skipIf`, `runIf`, `todo` or `fails` |
| `skip:`, `todo:` or `fails:` with any value but `false`, on the line of a `test`, `it`, `describe`, `suite` or `bench` call, in a script file: Vitest's options object | `skip`, `todo` or `fails` |
| `@public` or `@beta` anywhere in the line's text, in a script file | `knip:@public` or `knip:@beta` |
| an item of a `KNIP_ALLOWLIST_KEYS` key in `knip.jsonc` | `knip.<key>:<item>` |

  `eslint-enable`, `eslint-env` and `global` comments are not suppressions. Vitest's `only` fails at run through `allowOnly: false`, and ESLint bans `@ts-ignore` and `@ts-nocheck`, so none of them is listed. ESLint reads an inline rule setting only from a block comment, and `linterOptions.noInlineConfig` would also switch off the `eslint-disable` comments that a marker allows, so the `/* eslint */` form is a suppression. A marker is read from the line's whole text, as for a text file. Ruling: `runIf` is listed, because it skips a test as `skipIf` does; Spec 1 section 5 names the others.
- `knip_allowlist` reads `knip.jsonc` line by line, skipping strings and comments. An array under a top-level allowlist key gives one item per string, on its own line; under `ignoreIssues`, each key of the object is one item. Errors, after a `jsonc.loads` of the whole text that compares items as a multiset:
  - `<path>:<line>: knip.<key> holds <n> items on one line; write each alone on its own line, with its own marker`;
  - `<path>: knip.<key> lists '<item>' on no line devctl can read; write it alone on its own line`;
  - `<path>: <dotted path> sets an allowlist below the top level; devctl reads knip's allowlists only at the top level of knip.jsonc`, for an allowlist key inside `workspaces` or any other object.
- `exceptions.scan`: a file with a TypeScript owner gets `_text_lines`' forms plus `line_rules` on each line; `knip.jsonc` in a TypeScript stack's directory gets its items. `ExceptionsStep.run` appends `knip_allowlist`'s errors, and `<directory>/<name>: devctl reads knip's settings only from knip.jsonc; move them there` for each `OTHER_KNIP_SETTINGS` file in a TypeScript stack's directory and for a `knip` key in its `package.json`. Invalid JSONC in `knip.jsonc` blocks the step with `<path>: <error>`.
- References retain `TrackedFiles` and the holder contract from Unit 4. Before computing ESLint settings, require tracked `under(directory, "package.json")`, `under(directory, "tsconfig.json")` and the stack's ESLint config. Before computing tsc files, require tracked `tsconfig.json` and the type-reference target. Every test/type file reference requires its target tracked, even if the tool lists it. Use `tracked.why_untracked` for ignored/untracked inputs and preserve its symlink/case validation. After these checks, run the computed ESLint/tsc commands and cache once per directory per run. `eslint:` and `type:` are the TypeScript kinds. `resolve_eslint` calls `node.eslint_config` once per stack directory in a devctl run, and resolves when `node.is_error` holds for the rule's severity; otherwise `<reference>: ESLint does not report <rule> as an error in <label>`, or `<reference>: <cannot_run("eslint", <label>, <reason>, directory)>`. `resolve_type` runs `tsc --listFilesOnly -p tsconfig.json` from `node_tool` there, once per stack directory in a run, and resolves when the file's resolved path is listed; otherwise `<reference>: tsc does not check <path>`, or `<reference>: <cannot_run("tsc", ...)>`.

- `type:<path>` selects among the holder's matching stacks by suffix: `.ts`, `.tsx`, `.mts`, `.cts` use tsc; `.py`, `.pyi` use mypy. This applies to shared directories and Unit 4's no-owner selection. No matching kind returns the unknown-kind text; multiple matching candidates fail with the candidate stacks and Unit 4's supported test/check alternatives.

- [ ] **Step 1: write the failing tests.**
  - `test_devctl_typescript_suppressions.py`, docstring `Offline: TypeScript suppression forms read from lines of text.`: `test_each_form_names_its_rule`, a table with one row per form above, among them `// eslint-disable-next-line no-console, complexity -- reason` (`eslint:complexity,no-console`), `{/* eslint-disable-next-line */}` (`eslint`), `/* eslint no-console: "off" */` (`eslint:no-console`), `/* eslint complexity: ["error", 50], no-console: "off" */` (`eslint:complexity,no-console`), `/* v8 ignore start */` (`no-cover`), `/* v8 ignore stop */` (none), `test.concurrent.skip(` (`skip`), `it.skipIf(ci)(` (`skipIf`), `describe.runIf(x)(` (`runIf`), `test("x", { skip: true }, () => {})` (`skip`), `describe("x", { todo: true }, () => {})` (`todo`), `test("x", { skip: false }, () => {})` (none), `/** @public */` (`knip:@public`), ` * @public` (`knip:@public`), ` * @beta rs-exception: EX-1` (`knip:@beta`, passing with its matching entry), and `/* eslint-enable */`, `/* eslint-env node */`, `test.only(` and `// @ts-ignore` (none). `test_an_unmarked_suppression_fails_and_a_marked_one_passes`: in `frontend/src/a.ts` of a fixture repository, `console.log(x); // eslint-disable-line no-console` fails with `frontend/src/a.ts:1: suppression eslint:no-console needs ...`, and passes with ` -- rs-exception: EX-1` after the rule and the entry `("EX-1", "frontend/src/a.ts", "eslint:no-console")`. `test_a_file_outside_the_typescript_stack_has_no_typescript_forms`: the same line in `scripts/a.ts`, with `typescript` in `frontend`, passes.
  - `test_devctl_typescript_knip_allowlist.py`, docstring `Offline: knip's allowlist items in knip.jsonc.`: `test_each_allowlist_key_names_its_rule`, parametrized over each key, such as `{\n  "ignoreDependencies": [\n    "@types/node",\n  ],\n}` giving `AllowlistItem(3, "knip.ignoreDependencies:@types/node")` and `"ignoreIssues": {\n    "src/x.ts": ["exports"],\n  }` giving `knip.ignoreIssues:src/x.ts`; `test_two_items_on_one_line_fail`; `test_an_item_below_the_top_level_fails` for `"workspaces": {"pkg": {"ignore": ["x"]}}`; `test_another_knip_settings_file_fails` for `frontend/knip.json` and a `knip` key in `frontend/package.json`; `test_scope_settings_are_not_suppressions` for `entry`, `project` and `ignoreWorkspaces`.
  - `test_devctl_typescript_references.py`, docstring `Offline: the eslint: and type: references against fake eslint and tsc.`: `test_an_eslint_reference_resolves_when_the_rule_is_an_error`, parametrized over `"error"`, `2`, `["error", {}]` (resolves) and `"warn"`, `0`, absent (not); the fake ran with `--print-config src/index.ts` in `frontend`, once for two references. `test_a_type_reference_resolves_when_tsc_lists_the_file`: fake tsc logs argv/cwd and prints absolute paths of `frontend/src/a.ts` and `frontend/src/b.ts`; both references resolve, a tracked `frontend/src/c.ts` gives `type:frontend/src/c.ts: tsc does not check frontend/src/c.ts`, and two successful references invoke tsc once with `--listFilesOnly -p tsconfig.json` in `frontend`. `test_a_typescript_reference_without_node_modules_names_npm_ci`: with `frontend/package-lock.json`, `eslint:no-console` gives `eslint:no-console: cannot run eslint in frontend: eslint is not installed; run npm ci there`. `test_a_python_kind_does_not_resolve_for_a_typescript_holder`: `ruff:BLE001` held by `frontend/src/a.ts` gives `ruff:BLE001: unknown reference kind ruff for frontend/src/a.ts`.
  - Add `test_type_references_choose_the_checker_in_a_shared_directory`: Python and TypeScript in `app`; `type:app/src/a.ts` invokes fake tsc and `type:app/src/a.py` uses mypy's tracked settings. Also cover `.mts`, `.cts` and `.pyi`, missing matching stacks and a root holder with unique versus ambiguous matching stacks.
  - Add `test_typescript_references_require_tracked_inputs`: untracked/ignored `tsconfig.json`, ESLint config, package file and target each fail with staging advice before any tool call; stage them and both resolvers succeed. A fake computed result listing an untracked target does not resolve it. Keep PRO-152's symlink and case checks. Assert ESLint and tsc still run once per validated directory for several references.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_typescript_suppressions.py tests/devctl/test_devctl_typescript_knip_allowlist.py tests/devctl/test_devctl_typescript_references.py -q`; expected FAIL with missing TypeScript suppression/reference modules.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k "typescript or exceptions or references"`; expected PASS. Commit `feat: read the TypeScript suppressions and references`.

### Unit 8: The diff policy for Vitest, and PR 6.2b's verification

**Files:**
- Create: `devctl/check/stacks/vitest.py`, `tests/devctl/test_devctl_typescript_diff.py`
- Modify: `devctl/check/evidence.py` (`_DECLARATION` and hint), `devctl/check/map.py` (`_RULE_END`); `tests/devctl/test_devctl_evidence_step.py`, `tests/devctl/test_devctl_map_documents.py`, `tests/devctl/test_devctl_merge_guard.py`
- Modify: `devctl/check/diff.py` (`_changed_tests` and `_added_tautologies` take the stack's readers; `DiffStep.run` applies the Vitest rules to a TypeScript stack's changes), `devctl/check/references.py` (`test:` reads Vitest identities for a Vitest test file)

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

- `test_identities` tokenises the source, skipping comments, strings, template literals and regular expression literals. Track JavaScript, JSX tag/attribute and JSX text modes, including nested elements, fragments and self-closing tags. JSX text and quoted attributes are opaque to JavaScript title and bracket recognition: apostrophes and literal `test(...)` text there are not JavaScript strings or calls. A JSX `{...}` expression returns to JavaScript mode with its own brace depth, then resumes the enclosing JSX mode. Closing the outer element returns to its surrounding JavaScript expression. Only a syntactic JSX opener starts these modes; comparison operators and TypeScript type parameters remain JavaScript. In JavaScript mode, track escaped quotes and backslash line continuations; reject an unterminated string instead of consuming later code. Reuse the resulting tokens for identities and tautologies. A `/` starts a regular expression after `(`, `,`, `=`, `:`, `[`, `!`, `&`, `|`, `?`, `{`, `}`, `;`, `return` or at the start of the source. A call of `describe`, `suite`, `it` or `test`, through any `.<word>` chain except `.each`, whose first argument is a plain string (`'...'`, `"..."`, or a template literal without `${`) opens a title. A `describe` or `suite` title holds until its call's closing parenthesis, and a test's identity is the chain of open titles and its own, joined by `SEPARATOR`. A test whose title, or an enclosing title, is not a plain string, or that uses `.each`, is not an identity: its line goes to the unchecked list.
- `tautologies` reports `expect(<a>).<toBe|toEqual|toStrictEqual>(<b>)` where `<a>` and `<b>` are the same text once whitespace is removed, and `expect(true).toBeTruthy()`, with the line and the call's text.
- `DiffStep` applies to a TypeScript stack's changed test files what it applies to Python's: removed identities across the change (a test moved to another file is no removal), declared or not, unit or behavioural by `[tests] unit`; added tautologies with `is always true; assert on the behaviour instead`; and a note `<path>:<line>: test title is not a plain string; not checked` for each unchecked line of a changed test file at the base. A head that does not tokenise counts as holding its base's tests, with `<path>: cannot read the tests at head (<error>)`.
- Evidence declarations accept any non-backtick identity containing `::` inside backticks, including spaces: ``- `frontend/src/a.test.ts::a > b`: gone``. Unquoted identities retain the existing single-word grammar. Update the hint to require backticks for spaces; preserve malformed/empty-reason errors. Rule references accept the same backticked spaced value. The Flight merge guard reads this same parser, so declarations still leave behavioural removals to the owner.
- `test:<path>::<name>` chooses its reader by the test file, as Unit 4 does: Python identities for a `.py` file, Vitest identities when `vitest.is_test_file(path)`, and the word search otherwise. With Vitest's, it resolves when `name` is one of the file's identities.

- [ ] **Step 1: write the failing tests.** `test_devctl_typescript_diff.py`, docstring `Offline: Vitest test identities and the diff policy in fixture repositories.`:
  - `test_identities_are_title_chains`: `describe("a", () => { it("b", () => {}); describe('c', () => { test(`d`, () => {}) }) }); test("e", () => {})` gives `["a > b", "a > c > d", "e"]`; a `/\)/` regular expression and a `"describe("` string inside a body change nothing.
  - `test_a_title_that_is_not_a_plain_string_is_not_checked`: `test(name, ...)`, ``test(`x ${y}`, ...)`` and `test.each(rows)("x %s", ...)` give no identity and three unchecked lines; removing them from a changed file gives three notes and no problem.
  - `test_jsx_text_with_an_apostrophe_keeps_the_titles`: `describe("d", () => {\n  test("a", () => { render(<p>Don't</p>); });\n});\ntest("e", () => {})` gives `["d > a", "e"]` and no unchecked line.
  - `test_paired_jsx_apostrophes_do_not_hide_calls`: on one line, `describe("d", () => { test("a", () => { render(<p>Don't</p>); }); }); test("e", () => { render(<p>Don't</p>); });` gives `["d > a", "e"]` and no unchecked line. Removing or moving either test still follows the ordinary diff rule.
  - `test_jsx_text_and_attributes_are_not_javascript_calls`: literal `test("example", () => {})` and `expect(true).toBeTruthy()` inside JSX text or a quoted attribute produce no identities or tautologies. Cover nested tags, fragments, a self-closing tag with quoted attributes, and a `{...}` expression containing a string or regular expression with braces; a real top-level test after the JSX keeps its own title. Comparison expressions and TypeScript generic calls do not enter JSX mode. An unterminated JavaScript string reports a parse error; backslash-continued strings preserve subsequent call boundaries.
  - `test_a_removed_vitest_test_fails_unless_declared`: `typescript` in `frontend`; removing `a > b` from `frontend/src/a.test.ts` fails with `removed behavioural test frontend/src/a.test.ts::a > b: declare it ...`; a body declaring it under `Removed tests:` passes with the note; moving it to `frontend/src/b.test.ts` passes.
  - `test_an_added_tautology_fails`: `expect(x).toBe(x)` and `expect( a ).toEqual(a)` added fail; `expect(x).toBe(y)` does not.
  - `test_a_test_reference_reads_vitest_titles`: `test:frontend/src/errors.test.ts::an error keeps its cause and names the next step` resolves for that file.
  - In `test_devctl_evidence_step.py`, `test_backticked_test_identities_can_hold_spaces`: the `a > b` declaration parses exactly, evidence passes, and malformed declarations still fail. In `test_devctl_map_documents.py`, `test_backticked_rule_references_can_hold_spaces`: a Rule ending ``enforced by: `test:frontend/src/a.test.ts::a > b` `` resolves a tracked test. In `test_devctl_merge_guard.py`, `test_flight_leaves_a_declared_spaced_behavioural_removal_to_the_owner` denies with the behavioural-removal message; the equivalent unit-test declaration does not trigger that denial. Run `uv run pytest tests/devctl/test_devctl_merge_guard.py -q -k spaced` before and after implementation; expect FAIL then PASS.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_typescript_diff.py tests/devctl/test_devctl_evidence_step.py tests/devctl/test_devctl_map_documents.py -q`; expected FAIL with missing Vitest module and rejected spaced declarations/Rule references.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q`; expected PASS. Commit `feat: apply the diff policy to Vitest tests`.
- [ ] **Step 5: documents.** `ARCHITECTURE.md` (the TypeScript suppressions, references and diff rules), `tools/AGENTS.md`, `tests/AGENTS.md`; the index's Suppressions paragraph: the table above as plan 6's TypeScript rule names, and knip's items. Spec 1 section 5: the `/* eslint */` comment and Vitest's options object among the TypeScript suppressions, and the `eslint-disable` and `/* eslint */` comments in Exceptions rule 1's list of comments whose several rules are one rule. Commit `docs: describe the TypeScript suppressions, references and diff rules`.
- [ ] **Step 6: verify** with `--base origin/plan6-stacks`, record the five checks, and commit `docs: record PR 6.2b's verification`. `Not covered: a dynamic skip through the test context, such as ctx.skip(), which devctl cannot see and review treats as an unmarked suppression; a Vitest options object spread over several lines, whose skip, todo or fails key is not on the call's line; a suppression form inside a string, which counts too`.

## PR 6.3: the TypeScript templates and the integration tests (`plan6-ts-templates`, on `main` once 6.1b and 6.2a have merged)

### Unit 10: The TypeScript templates

**Files:**
- Create under `rapid_ship/templates/typescript/`: `AGENTS.md` (the stack guide), `.gitignore`, `.prettierignore`, `.prettierrc.json`, `package.json`, `tsconfig.json`, `eslint.config.js`, `vite.config.ts`, `knip.jsonc`, `index.html`, `src/AGENTS.md`, `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx`
- Modify: `rapid_ship/kit/stacks.py` (`typescript` in `StackName` and `STACKS`, `KITS["typescript"]`, its detection), `rapid_ship/kit/existing_checks.py` (the TypeScript tools' settings), `rapid_ship/templates/kit.toml` (`new_project.typescript`)
- Create: `tests/test_kit_typescript.py`
- Modify: `tests/test_kit_stacks.py` (TypeScript detection rows), `tests/test_kit_init_existing_checks.py`
- Modify: this repository's `.rapid-ship/project.toml`, whose `[map] exclude` gains `rapid_ship/templates/typescript`, because its guides are template content (Protected; G5 asks; in a headless Session the owner makes this edit)

**Interfaces:**
- Consumes: `render_files`, `KITS` (Unit 3b); tests compare the seed with `doctor_typescript.TSCONFIG_FLOOR`, `DEV_PACKAGES`, `floor_gaps` and `doctor_rules.TYPESCRIPT_PROTECTED_PATHS` (Unit 9, from 6.2a on `main`); no production import; `jsonc.loads` (Unit 1b).
- `KITS["typescript"]`: markers `("package.json", "tsconfig.json")`, new-project marker `package.json`, source root `src`, no unit tests (every Vitest test counts as behavioural), row `| The React app's code and its tests | [Source](src/AGENTS.md) |`, no rules, `lint_rules=False`, patterns `typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md`, `typescript-performance.md`, protected a copied tuple equal to `TYPESCRIPT_PROTECTED_PATHS` in tests.
- Every TypeScript file but the stack guide is a new-project seed.
- `package.json`: `"name": "{{package}}"`, `"private": true`, `"version": "0.1.0"`, `"type": "module"`, `"engines": {"node": ">=24.15.0 <25"}`, scripts `dev` (`vite`) and `build` (`vite build`), `dependencies` React and React DOM, `devDependencies` the other packages of Tech Stack, each pinned to an exact version with no range. Use `globals` as `languageOptions.globals: globals.browser` in ESLint. Where the prototype proves knip needs tool scripts, add `format`, `lint`, `typecheck`, `test` and `knip`, each naming its installed tool. Remove a demonstrably unused package rather than suppressing knip. Record each difference in the PR body and obtain owner approval for package/pin changes before downloads. Add a package only when the skeleton fails without it, pinned and approved.
- `tsconfig.json`: `TSCONFIG_FLOOR` all true, with `jsx` `react-jsx`, `moduleResolution` `bundler`, `types` `["vite/client"]`, and `include` `["src", "vite.config.ts"]`; no `extends`.
- `eslint.config.js`: first `globalIgnores(["dist", "coverage"])` from `eslint/config`, because flat config does not read `.gitignore` and would lint the build output; then a flat config of `@eslint/js` recommended, typescript-eslint's `strictTypeChecked` with its project service, and eslint-plugin-react-hooks' recommended flat config. It adds `complexity: ["error", 10]`, `no-console: "error"`, `@typescript-eslint/switch-exhaustiveness-check: "error"`, `@typescript-eslint/ban-ts-comment` with `ts-ignore` and `ts-nocheck` true and `ts-expect-error` `"allow-with-description"`, `no-restricted-imports` with empty `paths` and `patterns`, `linterOptions.reportUnusedDisableDirectives: "error"`, and Unit 11's `no-restricted-syntax`. typescript-eslint's `disableTypeChecked` applies to `**/*.js`, so `eslint.config.js`, which `tsconfig.json` leaves out, is linted without type information.
- `vite.config.ts`: React's plugin; `test` with `environment: "jsdom"` and `allowOnly: false`. `knip.jsonc`: its `$schema` alone, with no `entry` or `project` while knip's Vite and Vitest plugins find them. `.gitignore`: `node_modules/`, `dist/`, `coverage/`. `.prettierrc.json`: `{}`, Prettier's defaults, so that Prettier's upward search for settings stops in the stack's directory, inside its Protected lines. `.prettierignore`: `package-lock.json`, `*.md`, `docs/`, `tools/devctl/`, `.github/`, `.githooks/`, `.rapid-ship/`, `.claude/`, `.agents/`.
- `src/App.tsx` renders `<main>` with an `h1` of `{{project_name}}`; `src/App.test.tsx` is `test("the app shows the project name", ...)`, through Testing Library, with `afterEach(cleanup)`.
- The stack guide, `typescript/AGENTS.md`, as Python's, using its directory's combined `stack_title` and `guide_rows`. Each settings file comments a key only for its contract (Spec 1 section 4).
- `existing_checks` lists, in the root and in each stack directory, the TypeScript tools' settings files by glob: `tsconfig*.json`, `eslint.config.*`, `.eslintrc*`, `.prettierrc*`, `prettier.config.*`, `biome.json*`, `vitest.config.*` and `jest.config.*`. It lists `package.json` when it holds an `eslintConfig`, `prettier` or `jest` key, as it lists `pyproject.toml` with a check's table, and `package.json (unreadable)` when it cannot parse it.

- [ ] **Step 1: record the owner's approval.** The owner answered decision 1 before 6.2a started. The PR body's Evidence section records the approval and its date.
- [ ] **Step 2: write the failing tests.** `tests/test_kit_typescript.py`, docstring `Offline: the TypeScript templates rendered for a frontend stack.`:
  - `test_the_typescript_files_render_under_the_stack_directory`: `typescript` in `frontend` renders each file above as `frontend/<path>`, each a new-project seed except `frontend/AGENTS.md`, which is seeded.
  - `test_the_typescript_settings_meet_the_floor`: `floor_gaps` on the rendered `tsconfig.json`, `package.json` and `knip.jsonc`, a `--print-config` object holding the rules above, and `has_lock=True`, gives `[]`; every version in `package.json` is exact; its name is `demo_app`; `knip.jsonc`'s keys are `{"$schema"}`; `.prettierrc.json` reads as `{}`; the first integer of `engines.node` equals the `node-version` of the workflow template's `setup-node` step.
  - `test_python_and_typescript_in_one_directory_keep_status_and_sync_working`, parametrized over `.`, `app/` and deep `apps/web/`: commit existing Python and TypeScript markers, then init both at that directory. For `app/`, use `--stack python=app --stack typescript=app`. In that nested case init exits 0, root navigation has exactly one `app/AGENTS.md` row, and that guide's title names Python and TypeScript and includes both stacks' rows. Exactly one `app/AGENTS.md` is rendered and locked. `status --strict` exits 0; `sync --in-place` exits 0 and prints `Kit is current; nothing to sync.` Pre-existing guide bytes, including a symlink at the guide path, remain untouched; an updated template is reported without rewriting it. In both directory cases, with neither project marker, both new skeletons collide at `.gitignore` (or `app/.gitignore`), init exits 2 with `python and typescript both write <path>; give one stack its own directory`, writes nothing and makes no commit, including the empty first commit. Keep root and shared `app/` coverage. For `apps/web/`, assert `apps/AGENTS.md` and `apps/web/AGENTS.md` each exist once, every guide is reachable from root navigation, and the map step passes after staging. Existing ancestor guides remain untouched.
  - `test_codeowners_lists_both_stacks_settings`: `python` in `backend` and `typescript` in `frontend`; after `# /.rapid-ship/ @octo` come the Python, then the TypeScript, Pattern lines; the file ends with the `/backend/` Python paths, then the `/frontend/` TypeScript paths; `KITS["typescript"].protected == TYPESCRIPT_PROTECTED_PATHS`. The root guide's lint Rules end `advisory`.
  - In `test_kit_stacks.py`, `test_detection_finds_nested_roots_and_skips_vendored_directories` gains `web/package.json` with `web/tsconfig.json` (`typescript` in `web`), `docs/package.json` alone (none) and `node_modules/x/` holding both (none); the no-root text names TypeScript's markers.
  - In `test_kit_init_existing_checks.py`, the listing includes `eslint.config.js`, `.eslintrc.json`, `.prettierrc`, `.prettierrc.yaml`, `prettier.config.js`, `biome.json`, `biome.jsonc`, `tsconfig.json`, `tsconfig.app.json`, `vitest.config.ts`, `vitest.config.mts` and `jest.config.js`, in the root and in a stack directory. A `package.json` with an `eslintConfig` key is listed; one with only `scripts` is not.
- [ ] **Step 3: run** `uv run pytest tests/test_kit_typescript.py -q`; expected FAIL with `KeyError: 'typescript'`.
- [ ] **Step 4: implement**; sync.
- [ ] **Step 5: run** `uv run pytest tests/test_kit_typescript.py tests/test_kit_stacks.py tests/test_kit_init_existing_checks.py -q`; expected PASS. `./devctl check --tier fast`; expected exit 0, the map step reading the new guides as template content. Commit `feat: add the TypeScript stack's templates and React skeleton`.

### Unit 11: The TypeScript starter Patterns and the performance Pattern

**Files:**
- Create under `rapid_ship/templates/typescript/`: `__root__/docs/patterns/typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md`, `typescript-performance.md`; `src/errors.ts`, `src/settings.ts`, `src/inputs.ts`, `src/profiling.tsx`; `src/errors.test.ts`, `src/settings.test.ts`, `src/inputs.test.ts`, `src/profiling.test.tsx`
- Modify: `rapid_ship/templates/typescript/eslint.config.js`, `rapid_ship/templates/kit.toml`, `tests/test_kit_starter_patterns.py`, `tests/test_kit_typescript.py`

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
export interface Sample { readonly id: string; readonly phase: string; readonly actualDuration: number }  // one onRender call
export function Profiled(props: { id: string; onSample: (sample: Sample) => void; children: ReactNode }): JSX.Element  // React's <Profiler>
```

- Another module imports every export of these four modules and of `App.tsx`: a test, `App.tsx` or `main.tsx`. The floor forbids `ignoreExportsUsedInFile`, so knip reports an export, a type included, that only its own module uses. `inputs.test.ts` imports `levelRank` and `LEVELS`, `settings.test.ts` annotates its result with `import type { Settings }`, and `profiling.test.tsx` types its samples with `Sample`. Do not export a name that nothing else imports.

| Pattern file | `task` | `reference` | `enforced_by` |
| --- | --- | --- | --- |
| `typescript-error-handling.md` | `Report an error` | `{{directory}}src/errors.ts` | `eslint:no-empty`, `eslint:@typescript-eslint/no-floating-promises`, `test:{{directory}}src/errors.test.ts::an error keeps its cause and names the next step` |
| `typescript-configuration.md` | `Read configuration` | `{{directory}}src/settings.ts` | `eslint:no-restricted-syntax`, `test:{{directory}}src/settings.test.ts::an out-of-range value is rejected` |
| `typescript-input-validation.md` | `Validate input` | `{{directory}}src/inputs.ts` | `eslint:@typescript-eslint/switch-exhaustiveness-check`, `test:{{directory}}src/inputs.test.ts::an unknown value is rejected` |
| `typescript-performance.md` | `Find slow code` | `{{directory}}src/profiling.tsx` | `test:{{directory}}src/profiling.test.tsx::the profiling entry point renders on a small input` |

- Each file states the rule of Spec 1 section 4's starter table, when it applies and the bypass it bans, then `## Lessons` on what its reference does right. The performance Pattern documents the browser's Performance panel and React DevTools' Profiler, around `<Profiled>`; no check runs a profiler.
- `eslint.config.js` gains `no-restricted-syntax` as an error with two selectors and their messages, for `process.env` and `import.meta.env`, each pointing to `docs/patterns/typescript-configuration.md`, and an override that turns it off for `src/settings.ts` alone. `eslint --print-config src/index.ts` therefore shows it as an error.
- The skeleton's tests: `an error keeps its cause and names the next step` (`loadSettings({ VITE_PAGE_SIZE: "four" })` throws a `UsageError` whose message is `VITE_PAGE_SIZE is four; set it to a whole number from 1 to 100` and whose `cause` is the `RangeError` that reading the number threw); `an out-of-range value is rejected` (`"101"` throws `UsageError`); `an unknown value is rejected` (`parseLevel("verbose")` throws a `UsageError` naming `debug, info, warning, error`); `the levels are ordered by rank` (`LEVELS.map(levelRank)` is `[0, 1, 2, 3]`); `the profiling entry point renders on a small input` (rendering `<App />` inside `<Profiled>` records at least one sample, judging no time).

- [ ] **Step 1: write the failing tests.**
  - In `tests/test_kit_starter_patterns.py`, `test_the_typescript_starter_patterns_pass_the_pattern_file_checks`: `init_repository` with `typescript` in `frontend`, then commit; the files under `docs/patterns/` that start `typescript-` are the four above, `pattern_lesson_errors` returns `[]`, and `pattern_errors` returns only four lines, one for each `eslint:` reference in the table, such as `eslint:no-empty: cannot run eslint in frontend: eslint is not installed; run npm install there and commit package-lock.json`, since the offline test installs nothing. Unit 12b's integration test resolves them.
  - In `tests/test_kit_typescript.py`, `test_the_typescript_skeleton_exports_only_what_another_module_imports`: for each rendered `frontend/src/*.ts` and `*.tsx` file, each name that an `export const`, `function`, `class`, `interface` or `type` declaration introduces appears in an `import` of another rendered file under `frontend/src/`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_starter_patterns.py tests/test_kit_typescript.py -q`; expected FAIL on the four missing TypeScript Pattern files.
- [ ] **Step 3: implement**; sync.
- [ ] **Step 4: run** `uv run pytest tests/test_kit_starter_patterns.py tests/test_kit_typescript.py -q`; expected PASS. Commit `feat: seed the TypeScript starter Patterns and the performance Pattern`.

### Unit 12b: devctl drops the older lock form, and the integration tests

**Files:**
- Modify: `devctl/check/kit.py` (`_parsed_lock`), `tests/devctl/test_devctl_kit_step.py`, `tests/devctl/test_devctl_check_integration.py`

**Interfaces:**
- Consumes: `check --install` (Unit 6), `doctor_typescript.floor_item` (Unit 9).
- `_parsed_lock` reads `stack` only as `[[stack]]` tables. A string `stack` gives `stack must be [[stack]] tables with name and directory; rapid-ship sync --in-place rewrites an older lock`, which blocks the `kit` step.

- [ ] **Step 1: write the failing tests.** In `test_devctl_kit_step.py`, `test_the_older_lock_form_blocks_the_kit_step` replaces `test_both_lock_forms_are_read`: a lock with `stack = "python"` makes the `kit` step blocked with the text above. The PR body lists the old name under `Removed tests:`. In `test_devctl_check_integration.py`, whose docstring gains `Node.js 24 and npm`:
  - `test_new_project_passes_devctl_check` gains `typescript`, which runs `npm install --no-audit --no-fund` and commits `package-lock.json` before the check; `NOT_APPLICABLE` gains its rows, `diff` and `evidence` in the full tier.
  - `test_a_python_backend_and_a_typescript_frontend_pass_devctl_check`: `init --stack python=backend --stack typescript=frontend --owner test-owner`; `uv lock` and `uv sync` in `backend`; `npm install --no-audit --no-fund` in `frontend`; commit; then `npm run build` in `frontend`, so that `dist/` exists. `./devctl check --tier full --json` exits 0; the names include `lint (backend)`, `lint (frontend)`, `dead-code (frontend)` and `audit (frontend)`; only `diff` and `evidence` are not applicable. `doctor_typescript.floor_item(root, ProjectStack("typescript", "frontend"), True)` has the status `ok`.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_kit_step.py -q`; expected FAIL on the older form.
- [ ] **Step 3: implement**; format, check, sync.
- [ ] **Step 4: run** the network tests, `uv run pytest tests/devctl/test_devctl_check_integration.py -q`; expected PASS. Fix the seed until both projects pass; each package added follows Unit 10's rule.
- [ ] **Step 5: commit** `feat: check a Python backend with a TypeScript frontend, and drop devctl's older lock form`.

### Unit 13: Live trial (Owner step), documents and PR 6.3's verification

**Files:**
- Create: `docs/trials/<run date>-typescript-and-stacks.md`
- Modify: `docs/trials/AGENTS.md`, `ARCHITECTURE.md`, `README.md`, the root `AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`; Spec 1's status line and sections 3 (existing Python and TypeScript projects sharing a directory; colliding new skeletons refused), 4 (the TypeScript seed rows, `.prettierignore`, `.prettierrc.json`, the stack guide), 5, 8 (step 6: only TypeScript/npm additions observed in this trial; PRO-156/157 owns the underlying fix) and 10 where the build differs; the plan index (plan 6 built, its row and outline); this plan's Verification record

- [ ] **Step 1 (agent): write the record's preparation.** Sections: Purpose, Versions, Setup, Procedure, Results, Limits. The procedure: in a new private scratch repository on the owner's account, commit `backend/pyproject.toml` with a one-line project, and `frontend/package.json` with `frontend/tsconfig.json`; run `uvx --from <this checkout> rapid-ship init` without `--stack` and keep its proposal. In a second new private scratch repository, cloned empty, run `init --stack python=backend --stack typescript=frontend --owner <login>`. Record that it made an empty first commit on the default branch and committed the Kit on `rapid-ship/init` (PRO-161), and that `.rapid-ship/project.toml` names the repository from `origin` (PRO-159). On `rapid-ship/init`, run `uv lock` in `backend` and `npm install` in `frontend`, and commit the two locks. Run `./devctl doctor` with the owner's gh sign-in, and record its `node`, `npm`, `Python guardrail settings (backend)`, `TypeScript guardrail settings (frontend)` and CODEOWNERS items, with the seeded CODEOWNERS's commented Protected lines under `/backend/` and `/frontend/`. Run `./devctl check --tier full`. After PRO-156/157 merges, use its Spec 1 section 8 setting for exact uv/gh domains, paths, exclusions and restart instructions. Restart the Session as that fix requires before checks. Start a headless Claude Code Session in the clone; trial npm with `~/.npm` in `filesystem.allowWrite` and `registry.npmjs.org` in `network.allowedDomains`, under the owner's accepted setting. Have it run `./devctl check --tier full --install`, and record each step's result and any other path or domain that npm needed (PRO-157). Before `rs-setup` applies its ruleset, have the owner push the default branch from their own terminal and record that result. Plan 7 owns ruleset setup; if this trial exercises it, apply it after that push and record the result, otherwise label it not exercised. Then push `rapid-ship/init` and open a PR from it whose body has `## Evidence` with the local full check's result and a `Not covered:` line, then record the CI run's `devctl check` job.
- [ ] **Step 2 (Owner): run the procedure,** keeping each command's output and exit code, and the CI run's URL and result.
- [ ] **Step 3 (implementer): write the record** from the owner's output, each result labelled as observed in a run, with no path under `/Users/`, `/home/` or `/tmp/`.
- [ ] **Step 4: documents.** Describe plan 6 as built in the files above only after the checks and Owner trial pass. Add only observed npm needs to the merged sandbox setting; do not reassign PRO-156/157's fix or invent its exact uv/gh values. Commit `docs: describe the TypeScript stack and record plan 6 as built`.
- [ ] **Step 5: verify** with `--base main`, after 6.1b, 6.2a and 6.2b have merged, record the five checks, and commit `docs: record PR 6.3's verification`. The Evidence section lists them and the owner's approval of decision 1, with `Not covered: several TypeScript stacks with different Node.js majors, which share CI's one Node.js; the merge guard on the trial's PR; PRO-158 and Units 3a/9 cover fallback behavior offline`.

## Verification record

Each PR's last task fills its row with the command, its exit code and the summary line it printed. A blocked, skipped or simulated result is written as such, never as passed.

| PR | `uv run pytest -q` | `./devctl check --tier fast` | `uv run rapid-ship status --strict` | `./devctl check --tier full --base <base> --pr-body <body>` | `npm --prefix website run build` |
| --- | --- | --- | --- | --- | --- |
| 6.1a | | | | | |
| 6.1b | | | | | |
| 6.2a | | | | | |
| 6.2b | | | | | |
| 6.3 | | | | | |

6.1b's row also records Unit 3b Step 5's `cmp` of the root-stack seeds.
