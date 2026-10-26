# rs-setup and rs-health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Kit's first skills: the seven engineering skills, with the five forks pinned in an upstream lock; `rs-setup`, which knows plan 6's stacks, gives the advice on Agent identity and ends an existing repository's Setup with the tool-settings PR; `rs-health` with the audit it shares with `rs-garden`; and the optional `rs-contribute`. Retire `rapid-ship-engineering`. Then trial both skills, apply `rs-setup`'s GitHub settings to this repository, and rewrite the documentation site, whose release is GA.

**Architecture:** Every Kit skill is one managed template directory under `rapid_ship/templates/common/.agents/skills/<name>/`, which `render_files` already renders with its `.claude/skills/<name>` link; this repository vendors each through `uv run rapid-ship sync --in-place`. `rapid_ship/upstream.lock` records each forked file's upstream blob, and `tests/test_kit_upstream.py` holds the forks to pristine fixtures. `rs-setup` applies `ruleset.json`, which doctor's `ruleset_problems` checks. The site keeps Docusaurus with Markdown pages under `docs/`, and its build fails a page without a status.

**Tech Stack:** Markdown skills with YAML front matter; TOML; JSON; Python 3.12+ standard library (`hashlib`, `difflib`, `tomllib`, `json`); pytest; gh; Docusaurus 3.10.2 in `md` format on Node.js 22 or later.

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), sections 7 (skills), 8 (`rs-setup`), 9 (`rs-health`) and 10 (plan 7's tests and trials), with the [rapid-ship design](../specs/2026-10-14-rapid-ship-design.md)'s "What rapid-ship ships" and [Spec 3](../specs/2026-10-16-metrics-and-gardening-design.md) section 10, "The shared audit", which fixes what `audit.md` must cover. Plan 7 of 7 in the [plan index](2026-10-14-kit-and-setup.md), whose Conventions, Shared interfaces and "Plan 7" outline bind this plan. Plan 6's document, `docs/superpowers/plans/2026-10-26-typescript-and-stacks.md`, which lands in its PR 6.1a, fixes the values that 7.2 quotes. The site's page list, page templates and style rules come from the owner's documentation site proposal of 2026-10-20 in Linear (rapid-ship project, "Documentation site proposal (plan 7, PR 7.4)"); Task 11 copies the templates and style rules into `docs/AGENTS.md`.

**Status:** planned on 2026-10-26, while plan 6 is planned in its own worktree. Revised the same day for two reviews and the owner's decisions of 2026-10-26: PR 7.4 stays one PR, all of Spec 2 is descoped, and GA also waits for Spec 3's plan. This document lands in PR 7.1a as its first commit.

**Owner steps:** Tasks 9 and 10, and pushing each commit that edits `.github/workflows/`. The agent writes each procedure and its empty record. The owner runs every Harness Session, GitHub write and push in them, and the implementer then writes the record from the owner's output. No implementer subagent runs an Owner step.

## Order and parallel work

| PR | Branch, worktree | Base | Tasks | Counted lines, estimated |
| --- | --- | --- | --- | --- |
| 7.1a | `plan7-skills`, `.worktrees/plan7` | `main` | this document, 1 | about 350 |
| 7.1b | `plan7-engineering`, `.worktrees/plan7-engineering` | 7.1a's head, or `main` once 7.1a has merged | 2, 3, 4 | about 350 |
| 7.2 | `plan7-setup`, `.worktrees/plan7-setup` | as 7.1b | 5, 6 | about 150 |
| 7.3 | `plan7-health`, `.worktrees/plan7-health` | as 7.1b | 7, 8 | about 150 |
| 7.4 | `plan7-site`, `.worktrees/plan7-site` | as 7.1b | 11, 12, and the records of Tasks 9 and 10 | about 200 |

- **7.1a first.** `main`'s `tests/test_skill_discovery.py` fails once any Kit skill is vendored. Task 1 rewrites it and creates `tests/test_kit_skills.py`, which 7.1b extends and which guards 7.2 and 7.3, so every other plan 7 PR branches from 7.1a's head and opens with the base `plan7-skills`. Before Task 1, 7.1a merges `origin/main`, which since `99b68a0` holds PRO-146's reworded doctor messages and test names.
- **Landing on `main`.** After 7.1a squash-merges, each branch above lands by the squash-merge stack procedure. Merge any later 7.1a commit into it first. Check that `git diff <7.1a head> origin/main` is empty. Retarget with `./devctl as worker gh api -X PATCH repos/proxy-hatch/rapid-ship/pulls/<n> -f base=main`, run `git merge -s ours origin/main`, and check that its diff against `main` equals its diff against 7.1a's head. Push with `./devctl as worker push` and wait for its `devctl check`. A later merge of `origin/main`, after a sibling lands, is a normal merge whose conflicts are the File overlap rows. Before 7.1a merges, a local full check uses `--base origin/plan7-skills`.
- **Merge order:** 7.1a; then 7.1b, 7.2 and 7.3 as their reviews finish; 7.4 last. 7.2 does not wait for plan 6's code: it writes its several-stack and TypeScript parts from plan 6's document, and Task 9 Step 1 checks them against the merged code.
- **Workers.** The design advises at most 3 Workers at once in Walk, and plan 6 uses three at its peak; the owner accepted more PRs in parallel on 2026-10-26. One order for both plans within that advice: wave 1, 6.1a once the hello-rapid-ship trial ends, 7.1a then 7.1b, and 7.3; wave 2, 6.1b, 6.2a and 6.2b; wave 3, 6.3, 7.2 and 7.4's Task 11. Spec 3's plan needs the same slots, so the owner sets the final order. Building every PR at once takes up to eight Workers.
- **Owner steps and 7.4.** Task 10 runs once 7.2's `ruleset.json` has passed review (decision 4), or, if the owner declines, once 7.2 and 7.3 have merged. Task 9 runs once plan 6, 7.2 and 7.3 have merged. 7.4 is one PR: the owner declined an early and a late half on 2026-10-26. Its Task 11 starts in wave 3, and Task 12 follows Tasks 9 and 10. 7.4 merges, and the owner tags `v1.0.0`, once Spec 3's plan has merged, because GA waits for it.
- **Critical path to GA:** the owner's hello-rapid-ship trial of the current Kit, which plan 6's code waits for (owner, 2026-10-26) → 6.1a → {6.1b, 6.2a, 6.2b} → 6.3 → Task 9 → 7.4, beside Spec 3's plan. 7.1a, 7.1b, 7.2 and 7.3 stay off it while they merge before 6.3 does. While Task 9 runs, an agent writes Task 12's five guides that need no Owner run.
- **Trial records.** The records of Tasks 9 and 10, each with its line in `docs/trials/AGENTS.md`, are commits on `plan7-site`, which is created then if it does not exist yet. Task 9's fix PRs, and its Step 1 drift fixes, are separate PRs from `main`.
- **Reviews after 7.1b merges.** A branch that merges `origin/main` after 7.1b loses `rapid-ship-engineering`. With Spec 2 descoped, no Kit skill replaces its clarify and review modes. Reviewers then follow `rs-ponytail` and the root guide's Rules with the Harness's own review, such as Claude Code's `/code-review`, and architecture work uses `rs-codebase-design`. A branch keeps its copy until it merges `origin/main`.

**Where 7.2 depends on plan 6.** Task numbers are those of plan 6's document: 6.1a holds Tasks 1, 4, 3a and 5; 6.1b Tasks 2 and 3b; 6.2a Tasks 6 and 9; 6.2b Tasks 7 and 8; 6.3 Tasks 10 to 13. 7.2 writes each part below from that document and quotes its values exactly. Nobody runs `rs-setup` before Task 9, which follows plan 6, so 7.2 merges once its review passes. Task 9 Step 1 checks each quoted value against the merged code.

| `rs-setup` content | Plan 6's PR and task | Values quoted |
| --- | --- | --- |
| Step "New or existing": the stacks, from each `[[stack]]` table's `name` and `directory` in `.rapid-ship/project.toml` | 6.1a Task 1 | `[[stack]]`, `name`, `directory` |
| Step "Documents": the seeded stack guide `<directory>/AGENTS.md`, which the root guide links | 6.1b Task 3b | the root guide's row `The Python stack`, linking `backend/AGENTS.md` |
| Step "Checks", new project: `uv sync` in each Python stack's directory, `npm install` in each TypeScript stack's | 6.1a Task 4, 6.1b Task 3b | none |
| Step "Checks": Node.js and npm at the major that each TypeScript stack's `engines.node` names | 6.2a Task 9, 6.3 Task 10 | `24.x`; doctor's `node` and `npm` texts |
| Step "Checks", existing project: devctl's exclusions and the uv workspace's `exclude` in the root `pyproject.toml`; the dead-code settings (`[tool.vulture] paths`, `lint.external`, deptry's exclusion) in each Python stack's own `pyproject.toml` | 6.1a Tasks 3a and 4 | doctor's exclusions item reads only the root `pyproject.toml`, and checks the tools only with a Python stack at `.` |
| Step "Checks", existing TypeScript project: knip's findings and the TypeScript suppressions marked at Setup (Task 5) | 6.2a Task 6, 6.2b Task 7 | `@public`; `knip.jsonc`'s top-level `ignore*` keys; the rules `knip:@public` and `knip.<key>:<item>` |
| Step "Checks", decision 1: the TypeScript devDependencies and pins added to an existing project, and ESLint and Prettier plugins for tools such as Tailwind CSS | 6.3 Task 10 | plan 6's Tech Stack pins |
| Step "Patterns": the TypeScript starter Patterns offered as tasks | 6.3 Task 11 | `typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md`, `typescript-performance.md` |
| Step "GitHub": the Walk line, and the Protected lines for a stack in a subdirectory | 6.1b Task 3b, 6.1a Task 3a, 6.2a Task 9 | `/<directory>/` before each of `PYTHON_PROTECTED_PATHS` and `TYPESCRIPT_PROTECTED_PATHS` |
| `stylistic-options.md`'s Prettier and ESLint lists, and the tool-settings PR's TypeScript rules | 6.2a Task 9, 6.3 Task 10 | `TSCONFIG_FLOOR`, `ESLINT_ERRORS`, the seed's `eslint.config.js` rules |
| `known-failures.md`'s Init row for `init` without `--stack` | 6.1b Task 2 | `init wrote nothing: confirm the stacks first.` |
| `known-failures.md`'s TypeScript rows | 6.1a Task 4, 6.2a Tasks 6 and 9 | `lint (frontend)`; `<tool> is not installed in <label>; run npm ci there`; the floor item texts |
| Task 9's trial with a Python `backend/` and a React TypeScript `frontend/` | all of plan 6 | none |

**7.3 does not depend on plan 6.** `rs-health` reads doctor's and check's output whatever the stacks are, and names "each stack's floor items". `rs-contribute` maps a vendored path to its template by the layout that the clone's `rapid_ship/templates/AGENTS.md` describes, which 6.1b updates, so the skill holds before and after plan 6. 7.3 still edits files that 6.1a and 6.1b change, as File overlap lists.

**File overlap** (resolve as the last column says, never by dropping a side):

| Files | Touched by | Resolution |
| --- | --- | --- |
| `.rapid-ship/kit.lock` | 7.1a, 7.1b, 7.2, 7.3 and every plan 6 PR | Never hand-merge: take `origin/main`'s lock, run `uv run rapid-ship sync --in-place`, commit the result |
| devctl's `settings.py` (template and vendored copy), `tests/devctl/test_devctl_settings.py` | 7.3 (`OPTIONAL_SKILLS`, one comment), 6.1a (`[[stack]]`) | Keep both; 7.3 changes one line in each |
| `rapid_ship/templates/kit.toml` | 7.3 (`optional_skills`), 6.1b (`new_project` becomes a table by stack, after the top-level keys) | Keep `optional_skills` among the top-level keys. 7.1 edits neither `kit.toml` nor a root guide template |
| Every `.rapid-ship/project.toml` seed under `rapid_ship/templates/`, and this repository's `.rapid-ship/project.toml` | 7.3 (the `[kit] optional` comment), 6.1a (`[[stack]]`), 6.1b (moves the Python seed to `common/`, deletes `agnostic/`) | Apply 7.3's comment to each seed where it then lives |
| The Kit version in both `pyproject.toml` files, devctl's `__version__` and both `uv.lock` files | 7.3 (decision 3) and any plan 6 PR that sets a version | Keep the higher version, then rerun both `uv lock` commands |
| `ARCHITECTURE.md`, the root `AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, `README.md`'s status lines, Spec 1's status line, the index's rows for plans 6 and 7 | every PR of plans 6 and 7; 7.4 trims `README.md` | Keep both sides' clauses; 7.4's trimmed README takes `main`'s status facts |
| Spec 1 section 2, items 3 and 4, on adjacent lines | 7.1b (item 3), 7.4 (item 4) | Keep both items' edits |
| Spec 1 sections 7 to 9, the design, the index | the Spec 2 descoping PR (`.worktrees/descope-spec2`), 7.1b, 7.4 | Keep both sides' clauses |
| The index's sentence on which plans are started | this document's commit and plan 6's | Keep both plans' clauses |
| `docs/credits.md`, `docs/AGENTS.md`, `website/`, `.github/workflows/docs.yml` | 7.1b (`docs/credits.md` text only), 7.4 | 7.4 changes no credits text, only where the sidebar shows it |
| `docs/trials/AGENTS.md` | 7.4 (Tasks 9 and 10), plan 6's Task 13 | Keep both lines |
| This plan's Verification record | every PR of plan 7 | Each PR fills its own subsection |

## Owner decisions needed

1. **An existing repository that lacks a check tool.** The step blocks, so `./devctl check` cannot pass, yet Spec 1 limits the Setup PR's tool edits to devctl's exclusions and the `dead-code` step's needs. Recommended: the Setup PR adds each missing tool at the seed's version range with only the settings it needs to run, and the tool-settings PR still offers the rules.
2. **How `rs-health` writes to the tracker, with Spec 2 and its mapping notes descoped.** Recommended: it asks which tracker, and writes the selected milestone, epics and tasks at the glossary's levels through the Harness's connection; with Agent identity on, GitHub Issues writes run as `./devctl as worker gh issue create`. The alternative returns Markdown for the owner to file.
3. **GA's version.** Recommended: `1.0.0`, set in 7.3's last task so that Task 9 records it, and tagged `v1.0.0` by the owner on 7.4's merge commit once Spec 3's plan has merged; the "before GA" texts then say that the policy after GA is not designed yet.
4. **Task 10 once 7.2's `ruleset.json` passes review,** not after 7.3 as the index orders it. Recommended: yes. The remaining PRs of plans 6 and 7 and Spec 3's plan then dog-food the ruleset, which shows a ruleset problem before Task 9. Each needs the code owner's approval or the admin bypass, a passing `devctl check`, resolved threads and a squash merge, which the owner gives already. It does not shorten the path to GA.

## Deviations from the index's outline

- 7.1 splits into 7.1a (this document and Task 1) and 7.1b (Tasks 2 to 4): every other plan 7 PR needs Task 1's test rewrite, and branching each from 7.1a's head lets it land by the squash-merge stack procedure without conflicts.
- 7.1 leaves `kit.toml` unchanged, because every template it does not list is managed and no 7.1 skill is optional or executable; 7.3 adds `optional_skills = ["rs-contribute"]`.
- 7.3 also changes devctl's `OPTIONAL_SKILLS` and the seeds' `[kit] optional` comment, because the loader and the parity test in `tests/devctl/test_devctl_settings.py` reject an optional skill outside that set.
- 7.3 also sets the Kit version to `1.0.0`, pending decision 3, so that Task 9 records GA's version.
- 7.1a keeps `tests/test_skill_discovery.py`'s three test names with new bodies, because the `diff` step reads a deleted test as a removal.
- 7.4 holds a second task, Task 12, for Get started, the Guides and GA's texts, so that Task 11 can start before the trials; it stays one PR.
- The proposal's guide "Add a TypeScript frontend" becomes "Set up a Python backend and a TypeScript frontend", because `init` refuses a repository that has a Kit lock and `sync` never adds a new-project seed, so no Kit command adds a stack later.
- 7.4 puts `GLOSSARY.md` in place of `README.md` in `docs.yml`'s path filters, because `.github/AGENTS.md` asks the filters to follow the site's inputs; the owner pushes that commit, because the Worker App cannot push a workflow change.
- The README shows the logo where the proposal keeps a regenerated banner, and 7.4 deletes `asset/public/banner.jpeg`: its image carries the retired "Ship more. Supervise less.", and the logo needs no new artwork. `docs/branding.md` keeps the banner prompt, less its tagline line, for a later banner.
- Task 9's existing-repository trial runs on a new public repository, `proxy-hatch/rs-existing`, not on hello-rapid-ship: hello-rapid-ship was recreated on 2026-10-26 for the owner's trial of the current Kit, so it will hold a Kit lock, which `init` refuses. A public repository also lets the trial apply the ruleset and rerun with it present.
- Spec 2 is descoped (owner, 2026-10-26): `rs-setup` builds neither step 10 (tracker), which Spec 2's plan was to add, nor step 16's pointers to Spec 2's skills, and the pages describe the owner's own Sessions where Spec 2 described a Lead.

## Global Constraints

- Commands and exit codes follow the index's Conventions. `rapid-ship init [--stack NAME[=DIRECTORY]]...` is plan 6's form; after plan 6, `init` without `--stack` proposes the stacks it finds, writes nothing and exits 2. A test that calls `init` uses the CLI with `--stack python` or `--stack agnostic`, which is valid before and after plan 6.
- A Kit skill is one real directory, `rapid_ship/templates/common/.agents/skills/<name>/`, with a regular `SKILL.md` whose front matter `name` is the directory name and whose `description` is not empty. Exactly `rs-setup`, `rs-health` and `rs-contribute` set `disable-model-invocation: true`, each with a one-line, human-facing description.
- Skills are Kit-managed here. Edit the template, then run `uv run rapid-ship sync --in-place`, and commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit `.agents/skills/rs-*` directly.
- Kit skill text is vendored into other projects. It never cites rapid-ship's specs, plans, ADRs, trials, Linear or a backlog ID, and never names this repository's own choices (Linear, subscription sign-ins, agy). It states the behaviour itself.
- Spec 2 is descoped. No skill, page or task builds, names or points to `rs-design`, `rs-breakdown`, `rs-lead`, `rs-work`, `rs-review` or a Lead brief. Where Spec 1 still describes them, the text describes the owner's own Sessions instead.
- The comment rule: no comment, docstring, test name or message cites a plan, spec, section, ADR, PR, trial or rule ID. A test module's docstring starts `Offline:` and names what it simulates.
- No Kit skill template writes gitleaks's allow comment literally: the exceptions step counts it in every file, and this repository's template copies are not Kit-managed.
- Upstream: `mattpocock/skills` at `49dd158d1076134a641b33efb035946536778336`, MIT. Fetch a file with `gh api "repos/mattpocock/skills/contents/<path>?ref=49dd158d1076134a641b33efb035946536778336" -H 'Accept: application/vnd.github.raw' > <fixture>`, and check it with `git hash-object <fixture>`.
- Diff cap: 1,500 counted lines per PR. Not counted: `.md`, `.txt` and `.log` files, Kit-managed files, `.rapid-ship/kit.lock`, and each stack's lock file (`uv.lock`, `package-lock.json`). Counted: `rapid_ship/upstream.lock`, and fixtures and templates with any other suffix, such as `LICENSE` and the `.sh` script. The PR table gives the estimates. A PR that would pass the cap splits at a task boundary.
- Agent identity is on here. Agents push with `./devctl as worker push` and run `gh` writes as `./devctl as <role> gh`. The Worker App can push a merge that only brings in workflow changes already on the base, but not a commit that edits `.github/workflows/`; the owner pushes those. In a Session wired to `devctl hook`, G5 asks the owner before each edit of a Protected path: every `AGENTS.md`, `pyproject.toml`, `.rapid-ship/` and `.github/`. `sync` writes the vendored skills through a shell command, which G5 does not see. Every PR touches the Protected set, so the owner merges it in GitHub's web interface.
- Each PR's last task runs these and records, in its own subsection of the Verification record, each command, its exit code and its summary line:
  - `uv run pytest -q`: exit 0, `<n> passed`, with no failure or error;
  - `./devctl check --tier fast`: exit 0;
  - `uv run rapid-ship status --strict`: exit 0, `<n> managed files unchanged.`;
  - `./devctl check --tier full --base <PR base> --pr-body <body file>`: exit 0, every step passed, `diff` noting `diff cap: <n> of 1,500 counted lines`, and `evidence` passed;
  - when docs change, `npm --prefix website run build`: exit 0, `[SUCCESS] Generated static files in "build".`

  Before 7.1a merges, the PR base of the other PRs is `origin/plan7-skills`.
- Commit trailer: `Co-Authored-By: <the model that writes the commit>`, such as `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **`rs-setup` runs with Agent identity already on,** as in a rerun, or with Apps recorded before the GitHub step. G8 denies the agent's `gh api` writes as the owner, and G7 its push. Expected: the skill gives the owner the exact command for a terminal and never works around the guardrail. Pinned by Task 5's `test_rs_setup_states_each_guard`, Task 6's known-failure rows, and Task 9 Step 5's rerun.
2. **A repository that already has a ruleset.** Expected: `rs-setup` lists the rulesets first, updates the one named `rapid-ship` with `PUT` after the owner's yes, and never creates a second. It re-reads a write whose result is uncertain before any retry. Pinned by `test_rs_setup_states_each_guard` and Task 9 Step 5's rerun.
3. **`rs-health` reads GitHub in a way that G8 denies.** With Agent identity on, `gh api graphql` and any `gh api` with `-f`, `-F` or a method other than `GET` are writes as the owner. Expected: it reads with `GET` REST calls and `gh pr view` or `list` only. Pinned by Task 7's `test_rs_health_runs_no_command_the_guardrails_deny`.
4. **`rs-contribute` from the fork's clone.** rapid-ship's own `project.toml` turns Agent identity on, so in a wired Session G7 and G8 deny the push and `gh pr create` there, whatever the project's setting. Expected: the skill says so and gives the owner the commands. Pinned by Task 8's `test_rs_contribute_hands_the_owner_its_writes`. Task 9 does not run it, because it would open a real PR on rapid-ship.
5. **An existing repository whose `[tool.uv.workspace] members` cover `tools/devctl`.** Its `uv lock` fails. Expected: `rs-setup` adds `exclude = ["tools/devctl"]` there, and doctor's devctl exclusions item is ok. Pinned by `test_rs_setup_states_each_guard` and Task 9 Step 5, whose prepared project has such a workspace.
6. **Sandbox settings reach a commit.** Expected: before writing `.claude/settings.local.json`, `rs-setup` runs `git check-ignore -q .claude/settings.local.json`. When the file is not ignored, it adds it to `.git/info/exclude`, never to a tracked file. Pinned by `test_rs_setup_states_each_guard` and Task 9 Step 4, where the owner accepts the sandbox.
7. **A fork drifts from upstream.** Inputs: an edit outside a marked section, an unclosed begin marker, a fixture that is not upstream's file, and a file in a forked skill with no lock entry. Expected: `tests/test_kit_upstream.py` fails each. Pinned by Task 1's tests.
8. **A site page without a status, or with a speed claim.** Expected: the site build fails and names the file; a design record that quotes "100x" still builds. Pinned by Task 11 Step 1's three runs.

## File Structure

`skills/` means `rapid_ship/templates/common/.agents/skills/`.

| File | PR | Responsibility |
| --- | --- | --- |
| `rapid_ship/upstream.lock` | 7.1a, 7.1b | Each forked file's upstream path, commit, blob and status |
| `tests/fixtures/upstream/mattpocock/skills/<commit>/` | 7.1a, 7.1b | Pristine upstream files, byte for byte |
| `tests/test_kit_upstream.py`, `tests/test_kit_skills.py` | 7.1a; 7.1b extends the second | The forks against upstream; the Kit's skills as templates and as `init` vendors them |
| `skills/rs-codebase-design/`, `skills/rs-writing-for-agents/` | 7.1a | Verbatim forks |
| `skills/rs-tdd/`, `skills/rs-diagnosing-bugs/`, `skills/rs-pr/` | 7.1b | Patched forks: rapid-ship's Evidence and skill names, in marked sections |
| `skills/rs-writing/`, `skills/rs-ponytail/` | 7.1b | This repository's writing and Ponytail guidance, made project-agnostic |
| `skills/rs-setup/` (`SKILL.md`, `ruleset.json`, `references/agent-identity.md`, `references/stylistic-options.md`, `references/known-failures.md`) | 7.2 | Setup, the ruleset it applies, and its references |
| `skills/rs-health/` (`SKILL.md`, `references/audit.md`) | 7.3 | The audit and the standards milestone; `rs-garden` reads `audit.md` |
| `skills/rs-contribute/SKILL.md` | 7.3 | The optional skill that sends a Kit fix back |
| `docs/start/`, `docs/concepts/`, `docs/reference/`, `docs/guides/`, `website/src/pages/index.md`, `website/page-rules.js`, `website/src/theme/DocItem/Content/index.js` | 7.4 | Site pages, Home, the build's page rules and the status badge |

---

## PR 7.1a: the upstream lock (`plan7-skills`, on `main`)

### Task 1: The upstream lock and the verbatim forks

**Files:**
- Create: `rapid_ship/upstream.lock`; `skills/rs-codebase-design/` (`SKILL.md`, `DEEPENING.md`, `DESIGN-IT-TWICE.md`, `LICENSE.txt`); `skills/rs-writing-for-agents/` (`SKILL.md`, `SKILL-MECHANICS.md`, `LICENSE.txt`); the fixtures of these files and of `LICENSE`; `tests/test_kit_upstream.py`; `tests/test_kit_skills.py`
- Modify: `tests/test_skill_discovery.py`; through `sync`: `.agents/skills/rs-codebase-design/`, `.agents/skills/rs-writing-for-agents/`, their `.claude/skills/` links, `.rapid-ship/kit.lock`; this plan's Verification record

**Interfaces:**
- Produces `rapid_ship/upstream.lock`, one `[[file]]` table per forked file, read only by the test:

```toml
# Upstream files that the Kit's forked skills copy. path is relative to rapid_ship/templates/common.
[[file]]
path = ".agents/skills/rs-tdd/SKILL.md"
repository = "mattpocock/skills"
commit = "49dd158d1076134a641b33efb035946536778336"
upstream = "skills/engineering/tdd/SKILL.md"
blob = "01eadaa34e7c9a63a67d6dc3cce1cc81b0e49985"  # git's blob SHA-1 of the upstream file
status = "patched"  # verbatim or patched
```

- The 17 forked files. Task 1 adds the seven rows of `rs-codebase-design` and `rs-writing-for-agents`, with their `LICENSE.txt`, and Task 2 the other ten.

| Fork, under `.agents/skills/` | Upstream, under `skills/` | Blob | Status |
| --- | --- | --- | --- |
| `rs-codebase-design/SKILL.md` | `engineering/codebase-design/SKILL.md` | `3f63c8146dd2604b419c929e9876b90c30d410e9` | verbatim |
| `rs-codebase-design/DEEPENING.md` | `engineering/codebase-design/DEEPENING.md` | `cd94075cfd754d147555c5d747a16431ed4c7dd8` | verbatim |
| `rs-codebase-design/DESIGN-IT-TWICE.md` | `engineering/codebase-design/DESIGN-IT-TWICE.md` | `d0990138c35c800bd821289a73115e52680c1620` | verbatim |
| `rs-writing-for-agents/SKILL.md` | `productivity/writing-for-agents/SKILL.md` | `a37608daf6e835e767deecfb498facecaaba82ba` | verbatim |
| `rs-writing-for-agents/SKILL-MECHANICS.md` | `productivity/writing-for-agents/SKILL-MECHANICS.md` | `9cdbdb22aadc438755392216e75ad9a14cc9832e` | verbatim |
| `rs-tdd/SKILL.md` | `engineering/tdd/SKILL.md` | `01eadaa34e7c9a63a67d6dc3cce1cc81b0e49985` | patched |
| `rs-tdd/tests.md` | `engineering/tdd/tests.md` | `7ab86479f925a1f9e8ba680af33cb3b12e015381` | verbatim |
| `rs-tdd/mocking.md` | `engineering/tdd/mocking.md` | `71cbfee674d93244ce81d1830b930ca9a69200bd` | verbatim |
| `rs-diagnosing-bugs/SKILL.md` | `engineering/diagnosing-bugs/SKILL.md` | `d039541ddd1c46e6ddbd662fe99d49b686fc5e12` | patched |
| `rs-diagnosing-bugs/scripts/hitl-loop.template.sh` | `engineering/diagnosing-bugs/scripts/hitl-loop.template.sh` | `243198464a8401a7ba1d63b3708fa43c3d067665` | verbatim |
| `rs-pr/SKILL.md` | `engineering/pr/SKILL.md` | `84dd4fb2f068e9f6282690235d20dd505b418119` | patched |
| `rs-pr/CREDITS.md` | `engineering/pr/CREDITS.md` | `5314bda2fa6005e264c9b5c1de7c425e719dc91f` | verbatim |
| each of the five skills' `LICENSE.txt` | `LICENSE`, at the repository root, not under `skills/` | `f1dd2c09108dde1a5f56097cee8461b3ea834499` | verbatim |

- Ruling: a forked `SKILL.md` differs from upstream in its front matter's `name` line, `name: rs-<upstream name>`, because map rule 7 requires the directory's name. The test restores that one line before it compares, so a verbatim fork may differ there only.
- Ruling: a patched file differs from upstream only between a line `<!-- rapid-ship: begin -->` and a line `<!-- rapid-ship: end -->`, markers included. Markers pair in order: an unclosed begin, an end without a begin, and a begin inside an open section are each a change at their own line. Only Markdown files are patched.
- Ruling: the hitl script is forked verbatim with git mode `100644`, as upstream keeps it. No patch removes the two lines that name it, and `kit.toml`'s `executable` stays as it is.
- Ruling: each fork carries upstream's `LICENSE` as `LICENSE.txt`, which the diff cap does not count. No fork copies an `agents/openai.yaml`, Codex's display metadata, because the Kit integrates Claude Code first.
- `tests/test_kit_upstream.py` holds its helpers. `blob_sha(data: bytes) -> str` is git's SHA-1 of `b"blob <len>\0" + data`. `restore_name(text: str, upstream_name: str) -> str` swaps the front matter's `name: rs-<upstream_name>` back. `unmarked_changes(upstream: str, fork: str) -> list[int]` runs `difflib.SequenceMatcher(None, upstream_lines, fork_lines, autojunk=False).get_opcodes()`. It returns the 1-based fork line of each non-equal opcode whose fork lines lie outside every marked section, and of each marker that does not pair. A removal has no fork lines; it counts as inside when a begin marker precedes its position and that section's end marker follows it.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_upstream.py`, docstring `Offline: the Kit's forked skills against pristine upstream fixtures.`:
  - `test_the_lock_names_one_upstream_commit`: every entry's `repository` is `mattpocock/skills` and its `commit` is `49dd158d1076134a641b33efb035946536778336`; `status` is `verbatim` or `patched`.
  - `test_each_fixture_is_the_pristine_upstream_file`: for each entry, `blob_sha` of `tests/fixtures/upstream/<repository>/<commit>/<upstream>` equals `blob`.
  - `test_verbatim_files_equal_their_upstream_file`: for each verbatim entry, `blob_sha` of the fork, after `restore_name` for a `SKILL.md`, equals `blob`.
  - `test_patched_files_differ_only_inside_marked_sections`: for each patched entry, `unmarked_changes(fixture, restore_name(fork)) == []`, the fork holds at least one begin marker, and its blob differs from `blob`.
  - `test_every_file_of_a_forked_skill_is_in_the_lock`: within each skill directory that the lock names, the template's files equal the lock's paths.
  - `test_unmarked_changes_reports_only_changes_outside_a_section`, parametrized over literal texts: an edited line outside the markers gives its line number; the same edit inside them gives `[]`; an upstream line removed between markers gives `[]`; one removed outside them gives the line before the removal; a begin marker with no end gives the begin marker's line; a stray end marker gives its line.
  - `restore_name` fails the test when the front matter's name is not `rs-` plus upstream's name.

  `tests/test_kit_skills.py`, docstring `Offline: the Kit's skills as the templates hold them and as init vendors them.`, with `USER_INVOKED = frozenset({"rs-setup", "rs-health", "rs-contribute"})`:
  - `test_only_the_user_invoked_kit_skills_disable_model_invocation`: a Kit skill template's front matter holds `disable-model-invocation: true` exactly when its name is in `USER_INVOKED`. No upstream front matter sets the key, so it passes at once; it guards 7.2 and 7.3.

  Rewrite `tests/test_skill_discovery.py` under its three names. `KIT_SKILLS` holds the names of `rapid_ship/templates/common/.agents/skills/*/SKILL.md`, less each of `load_manifest().optional_skills` that `read_optional_skills(REPOSITORY)` does not name. `OWN_SKILLS = ("rapid-ship-engineering",)` until Task 4 deletes it.
  - `test_bundled_skill_dependencies_resolve_inside_package`: every Markdown link in each Kit skill template resolves to a file inside that skill's own directory.
  - `test_checkout_discovery_resolves_to_packaged_skill`, over `KIT_SKILLS`: `.agents/skills/<skill>` is a directory, not a symlink, with a regular `SKILL.md`, and `.claude/skills/<skill>` is a symlink to `../../.agents/skills/<skill>`.
  - `test_checkout_discovers_exactly_the_packaged_skills`: each surface's entries, hidden names aside, equal `KIT_SKILLS` plus `OWN_SKILLS`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_upstream.py tests/test_skill_discovery.py -q`; expected FAIL with `FileNotFoundError` for `rapid_ship/upstream.lock`.
- [ ] **Step 3: fetch the fixtures** with the Global Constraints command, for `LICENSE` and this task's five other files, and check each with `git hash-object` against the table.
- [ ] **Step 4: write the forks and the lock.** Copy each fixture to its fork path and `LICENSE` to each `LICENSE.txt`; change only each `SKILL.md`'s `name`. Add the seven rows. `git add` the templates, then run `uv run rapid-ship sync --in-place`.
- [ ] **Step 5: run** `uv run pytest tests/test_kit_upstream.py tests/test_skill_discovery.py tests/test_kit_skills.py -q`; expected PASS. Then `uv run rapid-ship status --strict` and `./devctl check --tier fast`; both exit 0.
- [ ] **Step 6: commit** `feat: fork rs-codebase-design and rs-writing-for-agents, pinned in an upstream lock`.
- [ ] **Step 7: verify.** Run the five checks with `--base main` and record them. Evidence: `Not covered: the patched forks, rs-writing and rs-ponytail, which 7.1b adds`. Commit `docs: record PR 7.1a's verification`. 7.1b, 7.2, 7.3 and 7.4 branch from this head.

## PR 7.1b: the engineering skills (`plan7-engineering`, on 7.1a's head)

### Task 2: The patched forks, `rs-tdd`, `rs-diagnosing-bugs` and `rs-pr`

**Files:**
- Create: `skills/rs-tdd/` (`SKILL.md`, `tests.md`, `mocking.md`, `LICENSE.txt`), `skills/rs-diagnosing-bugs/` (`SKILL.md`, `scripts/hitl-loop.template.sh`, `LICENSE.txt`), `skills/rs-pr/` (`SKILL.md`, `CREDITS.md`, `LICENSE.txt`), and their fixtures
- Modify: `rapid_ship/upstream.lock` (the other ten rows), `tests/devctl/test_devctl_evidence_step.py`; through `sync`: the vendored copies, links and lock

**Interfaces:**
- Consumes: Task 1's lock format and markers; `devctl.check.evidence.EvidenceStep`; `check_workspace.Workspace.context(pr_body=...)`.
- Each patch sits in its own marked section and says only this:
  - `rs-tdd/SKILL.md`: (a) after the paragraph on pre-agreed seams, "A task's test plan names its agreed seams."; (b) the Skill tool is called with `"rs-codebase-design"`; (c) refactoring "belongs to the review stage", with no `code-review` skill named; (d) a closing `## Evidence` section. It says: before reporting the work done, run `./devctl check`. In the PR's Evidence section, laid out as `rs-pr` shows, list each test that went red then green, with the command and its result. Name each agreed seam left untested on the `Not covered:` line.
  - `rs-diagnosing-bugs/SKILL.md`: Phase 6's checklist gains one item: `./devctl check` passes, and the PR's Evidence section lists the Phase 1 loop's command, with its red result before the fix and its green result after, and a `Not covered:` line.
  - `rs-pr/SKILL.md`: one section spans the whole template block, fences included, so no marker lands in a body copied from it. The template's `## Evidence` holds ``- `<command>`: <exit code and the summary line it printed>``, upstream's Before and After lines, and `Not covered: <what the commands do not show>`. A second section in `### Evidence` says to list each command as that item. It adds `Removed tests:` with one ``- `<path>::<test>`: <reason>`` item per removed test, and `Over the diff cap: <reason>` only after the owner accepted the overage before the work. CI's `evidence` and `diff` steps fail a body without them. The front matter's HumanLayer credit and `CREDITS.md` stay verbatim.

- [ ] **Step 1: write the failing tests.** Add the ten rows to the lock; Task 1's tests then fail until the forks exist. In `tests/devctl/test_devctl_evidence_step.py`:
  - `test_the_rs_pr_template_passes_the_evidence_step`: the lines inside the first fenced `markdown` block of `rapid_ship/templates/common/.agents/skills/rs-pr/SKILL.md`, as the PR body, give `EvidenceStep().run(context).status == "passed"`.
  - `test_the_rs_pr_template_without_not_covered_fails`: the same body less its `Not covered:` line fails, and its details hold `Evidence: add a line starting 'Not covered:' that names what the commands do not show`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_upstream.py tests/devctl/test_devctl_evidence_step.py -q`; expected FAIL on the missing forks.
- [ ] **Step 3: fetch** the seven new upstream files and check each blob.
- [ ] **Step 4: write the forks,** copying each fixture and adding only the patches above; sync.
- [ ] **Step 5: run** both files and `tests/test_skill_discovery.py`; expected PASS. Status, fast check.
- [ ] **Step 6: commit** `feat: fork rs-tdd, rs-diagnosing-bugs and rs-pr with rapid-ship's Evidence`.

### Task 3: `rs-writing` and `rs-ponytail`

**Files:**
- Create: `skills/rs-writing/` (`SKILL.md`, `TECHNICAL-ENGLISH-LICENSE.txt`, `ASD-STE100-SKILL-LICENSE.txt`), `skills/rs-ponytail/` (`SKILL.md`, `PONYTAIL-LICENSE.txt`)
- Modify: `tests/test_kit_skills.py`; through `sync`: the vendored copies, links and lock

**Interfaces:**
- `rs-writing/SKILL.md`: `name: rs-writing`; `description: Use when writing or editing commits, PRs, reviews, documentation, code comments, agent reports or instructions.` Its body is `rapid_ship/skills/rapid-ship-engineering/references/writing.md`, made project-agnostic: the code-comment row says to follow the comment Rules in the root `AGENTS.md`. It ends with the sources paragraph of `SOURCES.md`'s "Technical writing" section, with its pinned links and the two licence files.
- `rs-ponytail/SKILL.md`: `name: rs-ponytail`; `description: Use before implementing or reviewing a change, to build only what the task needs while keeping required behaviour, validation and checks.` Its body is `references/ponytail.md`, whose comment bullet becomes the comment rule: comment only a contract, rationale, invariant or external constraint that the code does not express. It keeps its Ponytail v5.1.0 credit and licence.
- Neither skill names rapid-ship, this repository or a plan.

- [ ] **Step 1: write the failing test.** In `tests/test_kit_skills.py`, `test_each_skill_the_root_guide_names_ships_in_the_kit`: for each `rapid_ship/templates/*/AGENTS.md`, every name that ``re.findall(r"`(rs-[a-z0-9-]+)` skill", text)`` finds is a Kit skill template with a `SKILL.md`, and the guides name at least one. The pattern finds "the `rs-writing` skill" and skips the `rs-exception` marker. It reads the root guides by glob, because plan 6's 6.1b moves the Python root guide to `common/` and adds stack guides.
- [ ] **Step 2: run** it; expected FAIL naming `rs-ponytail` and `rs-writing`.
- [ ] **Step 3: write both skills**; sync.
- [ ] **Step 4: run** `tests/test_kit_skills.py` and `tests/test_skill_discovery.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add rs-writing and rs-ponytail to the Kit`.

### Task 4: Retire `rapid-ship-engineering`, documents, and PR 7.1b's verification

**Files:**
- Delete: `rapid_ship/skills/`, with its `AGENTS.md`; `.agents/skills/rapid-ship-engineering`; `.claude/skills/rapid-ship-engineering`
- Modify: `tests/test_skill_discovery.py` (`OWN_SKILLS` goes), `tests/test_kit_skills.py`; the root `AGENTS.md`, `rapid_ship/AGENTS.md`, `.agents/AGENTS.md`, `.claude/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, `pyproject.toml` (the sdist comment on checkout skill aliases), `docs/credits.md`, `ARCHITECTURE.md`, Spec 1's section 2 item 3 and status line, the index's plan 7 row, this plan's Verification record

**Interfaces:**
- The root `AGENTS.md`: Writing reads `.agents/skills/rs-writing/SKILL.md`. Development reads `.agents/skills/rs-ponytail/SKILL.md` before coding or review, and names `rs-tdd`, `rs-diagnosing-bugs`, `rs-codebase-design` and `rs-pr`. The source-map row drops "and the engineering skill". This repository loses the clarify and review modes, which no Kit skill replaces now that Spec 2 is descoped; review uses the Harness's own, with `rs-ponytail`.
- `docs/credits.md`: one row per forked skill, with its upstream link at `49dd158`, the HumanLayer credit for `rs-pr`, and the Ponytail, technical-english and asd-ste100 sources of `rs-ponytail` and `rs-writing`. It links `rapid_ship/upstream.lock` on GitHub instead of the deleted `SOURCES.md`.

- [ ] **Step 1: write the test.** In `tests/test_kit_skills.py`, `test_every_kit_skill_has_its_named_skill_md_and_claude_link_in_a_new_project`: in `git_repo`, after `monkeypatch.chdir`, `main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0`. Then `skill_errors`, `skill_file_errors` and `skill_alias_errors` over the tracked files are each `[]`, and the entries of `.claude/skills/` are the Kit's non-optional skills.
- [ ] **Step 2: retire.** Run `git rm -r rapid_ship/skills .agents/skills/rapid-ship-engineering .claude/skills/rapid-ship-engineering`, and delete `OWN_SKILLS`. Run `uv run pytest tests/test_kit_skills.py tests/test_skill_discovery.py tests/test_kit_upstream.py -q`; expected PASS.
- [ ] **Step 3: documents.** Update the files above. `ARCHITECTURE.md`'s "Engineering skill" row becomes the Kit skills, and its templates paragraph drops "the Kit has no skills yet". Commit `refactor: retire rapid-ship-engineering for the Kit's skills`.
- [ ] **Step 4: verify.** Run the five checks with the PR's base, and `uv run rapid-ship sync --in-place`, which prints `Kit is current; nothing to sync.` The PR removes no test. Its body's Evidence lists the checks, with `Not covered: the skills' behaviour in a Session, which Task 9 exercises`. Commit `docs: record PR 7.1b's verification`.

## PR 7.2: `rs-setup` (`plan7-setup`, on 7.1a's head)

### Task 5: `rs-setup` and its `ruleset.json`

**Files:**
- Create: `skills/rs-setup/SKILL.md`, `skills/rs-setup/ruleset.json`, `tests/devctl/test_devctl_ruleset_json.py`
- Modify: through `sync`: the vendored copies, link and lock

**Interfaces:**
- Consumes: `devctl.doctor_rules.ruleset_problems(rulesets, default_branch, *, every_pr, agent_identity) -> list[str]`; the recorded `tests/devctl/fixtures/github/ruleset.json`.
- `ruleset.json`, the body of `POST /repos/{owner}/{repo}/rulesets`:

```json
{
  "name": "rapid-ship",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "allowed_merge_methods": ["squash"],
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "do_not_enforce_on_create": false,
        "required_status_checks": [{"context": "devctl check", "integration_id": 15368}],
        "strict_required_status_checks_policy": false
      }
    }
  ],
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]
}
```

- `SKILL.md`: `name: rs-setup`; `description: Set up a new repository, or adopt an existing one, after rapid-ship init vendored the Kit.`; `disable-model-invocation: true`. Its rules come first: Spec 1 section 8's opening paragraph, with each outside write stated before the owner's yes. Spec 1 section 8's steps follow in order, numbered 1 to 14, without step 10 (tracker), which went with Spec 2, and step 11 (metrics), which Spec 3's plan inserts after the escalation list. Rulings that the spec leaves to the skill:
  - **Running `rapid-ship`:** `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<kit_version> rapid-ship <command>`, with `kit_version` from `.rapid-ship/kit.lock`. When that tag does not exist, the skill asks the owner for the checkout that `init` ran from. It runs `sync` only with `--in-place`.
  - **Stacks:** it reads each `[[stack]]` table's `name` and `directory` in `.rapid-ship/project.toml`, which `init` wrote with the stacks the owner confirmed, and never asks again.
  - **Checks, existing project:** it adds `exclude = ["tools/devctl"]` under the root `pyproject.toml`'s `[tool.uv.workspace]` when its `members` cover it, and, by decision 1, each check tool the project lacks. It writes the dead-code settings into each Python stack's own `pyproject.toml`. The Setup reasons are exact: `Existed at Setup on <date>` with `Remove when this code next changes` for a suppression, and `Delete it, or replace this reason with what uses it` for marked dead code.
  - **Existing TypeScript dead code:** for each knip finding, it fixes the code or marks it: a `/** @public */` tag with its `rs-exception` marker on the reported export, or an item under the matching top-level `ignore*` key of `knip.jsonc`, alone on its line with its marker. Each mark gets an entry with the dead-code Setup reasons, and each TypeScript suppression that the `exceptions` step reports gets its marker and the suppression's Setup reasons.
  - **Sandbox:** `.claude/settings.local.json`, kept out of git through `.git/info/exclude` when `git check-ignore -q .claude/settings.local.json` finds it not ignored.
  - **GitHub:** each write comes after the owner's yes, through `gh` under the owner's sign-in:
    - `gh api 'repos/<owner>/<name>/rulesets?targets=branch'` first;
    - with no ruleset named `rapid-ship`, `gh api --method POST repos/<owner>/<name>/rulesets --input .agents/skills/rs-setup/ruleset.json`; with one, `gh api --method PUT repos/<owner>/<name>/rulesets/<id> --input .agents/skills/rs-setup/ruleset.json`;
    - `gh api --method PATCH repos/<owner>/<name> -F delete_branch_on_merge=true`;
    - for a public repository, `gh api --method PUT repos/<owner>/<name>/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors`.

    With Agent identity on, G8 denies these writes and G7 the agent's push. The skill then gives the owner each exact command for a terminal, and agents' own GitHub writes run through `./devctl as`. A 403 that names the plan limit is the GitHub Free private gap; the skill records it, with the explanation that the merge guard is the enforcement there.
  - **Setup PR:** the body ends with the Evidence section that `devctl check` requires. It adds `Over the diff cap: dead code marked at Setup` only when the marks pass the cap.
  - **Next:** for an existing repository it offers `rs-health`; for a new one it says the owner runs their own Sessions on the first tasks with the engineering skills. It names only skills present in `.agents/skills/`, so it stays true before Spec 3's skills ship.

- [ ] **Step 1: write the failing tests.** `tests/devctl/test_devctl_ruleset_json.py`, docstring `Offline: rs-setup's ruleset.json against doctor's ruleset rules and a ruleset that GitHub returned, and the commands rs-setup states.`:
  - `test_rs_setups_ruleset_passes_doctor_in_every_mode`, over `every_pr` and `agent_identity`, each `True` and `False`: `ruleset_problems([ruleset], "main", every_pr=..., agent_identity=...) == []`.
  - `test_the_ruleset_is_the_body_github_accepted`: it equals the recorded fixture less `id`, `source` and `source_type`, and less `require_extra_approval_for_unattributed_changes` and `required_reviewers`, which GitHub adds with their defaults.
  - `test_rs_setup_applies_the_settings_doctor_checks`: `SKILL.md` contains `--input .agents/skills/rs-setup/ruleset.json`, `-F delete_branch_on_merge=true` and `-f approval_policy=all_external_contributors`.
  - `test_rs_setup_states_each_guard`: the text of `rs-setup/**/*.md` contains `rulesets?targets=branch`, `--method PUT repos/<owner>/<name>/rulesets/<id>`, `git check-ignore -q .claude/settings.local.json`, `.git/info/exclude`, `exclude = ["tools/devctl"]` and `./devctl as`.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ruleset_json.py -q`; expected FAIL with `FileNotFoundError`.
- [ ] **Step 3: write** `ruleset.json` and `SKILL.md`; sync.
- [ ] **Step 4: run** it, `tests/test_kit_skills.py` and `tests/test_skill_discovery.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add rs-setup with the ruleset it applies`.

### Task 6: `rs-setup`'s references, several stacks, documents, and PR 7.2's verification

**Files:**
- Create: `skills/rs-setup/references/agent-identity.md`, `stylistic-options.md`, `known-failures.md`
- Modify: `skills/rs-setup/SKILL.md` (links to the three; the several-stack and TypeScript parts), `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, the index's plan 7 row, this plan's Verification record

**Interfaces:**
- `agent-identity.md`: Spec 1 section 8 step 8.1's table, word for word except that the owner's own Sessions stand where it names a Lead; the four things that Agent identity buys and what is lost without it; its cost; step 8.3's team key model; and step 8.6's consequences without it. It links nothing outside the skill.
- `stylistic-options.md`: what the tool-settings PR leaves out, by tool. Ruff: `line-length`, `indent-width`, `[tool.ruff.format]` (`quote-style`, `indent-style`, `line-ending`, `skip-magic-trailing-comma`, `docstring-code-format`, `docstring-code-line-length`), and the rules that only enforce them (`E501`, `Q`, `COM`). Prettier: every option. ESLint: `@stylistic/*` and the core formatting rules that Prettier replaces. mypy, pytest, import-linter, `tsconfig.json`, Vitest and knip have none. The rules to offer are the details of doctor's floor items, plus Ruff's `ASYNC` and `FAST` where the project imports asyncio or FastAPI.
- `known-failures.md`: one table per step, with the output the owner sees, its cause and the fix the skill offers. Each row quotes doctor's and devctl's messages as `main` holds them. It needs at least these rows:
  - Init: `init` exiting 1 because a managed Kit path already exists, which writes nothing; `init` without `--stack` printing its proposal and exiting 2.
  - Checks: gitleaks missing or not 8.30.1; `uv sync` without network; a `members` glob that covers `tools/devctl`; a blocked tool step; hooks in `.git/hooks` that `core.hooksPath` would stop running; project skills whose `.claude/skills` entries are copies, not links, which the `map` step fails.
  - Guardrails and sandbox: a `.claude/settings.json` that lacks the Kit's hooks; a sandbox without network access; a `settings.local.json` that git does not ignore.
  - GitHub: a ruleset 403 on GitHub Free; a default branch other than `main` or `master`; an existing `rapid-ship` ruleset; G8 denying a `gh api` write with Agent identity on; `gh` signed in as another account.
  - Agent identity, doctor and the PRs: `rapid-ship app` exiting 1 for each of Spec 1 section 3's causes; `claude` not on `PATH` for `--skills`; a skill that the probe misses; G7 denying the push; the Worker App refused a workflow push; a `sync` conflict; linter findings past the cap in the tool-settings PR.
  - TypeScript: the rows of "Where 7.2 depends on plan 6".

- [ ] **Step 1: write the three references** without their TypeScript rows, and link each from the steps that use it; sync.
- [ ] **Step 2: run** `tests/test_skill_discovery.py`, whose links test now covers them, and `tests/devctl/test_devctl_ruleset_json.py`; expected PASS. Status, fast check. Commit `feat: add rs-setup's references`.
- [ ] **Step 3: several stacks and TypeScript.** Write each part of "Where 7.2 depends on plan 6" from plan 6's document, quoting its values exactly; sync. Commit `feat: rs-setup for several stacks and the TypeScript stack`.
- [ ] **Step 4: documents and verification.** Describe `rs-setup` in the files above. Run the five checks with the PR's base and record them. Evidence: `Not covered: rs-setup in a Session, which Task 9 runs; the values quoted from plan 6's document, which Task 9 Step 1 checks against plan 6's merged code`. Commit `docs: record PR 7.2's verification`.

## PR 7.3: `rs-health` and `rs-contribute` (`plan7-health`, on 7.1a's head)

### Task 7: `rs-health` and the shared audit

**Files:**
- Create: `skills/rs-health/SKILL.md`, `skills/rs-health/references/audit.md`, `tests/test_kit_health_and_contribute.py`
- Modify: through `sync`: the vendored copies, link and lock

**Interfaces:**
- Consumes: `devctl.hook.decide(call, root, settings, branches) -> tuple[Decision, str]`, whose `branches` is a `Callable[[], LocalBranches]`; `devctl.hook_protocols.ToolCall` and `HookSettings`; `devctl.merge_guard.LocalBranches`.
- `SKILL.md`: `name: rs-health`; `description: Audit a repository against rapid-ship's standards and return a standards milestone.`; `disable-model-invocation: true`. It never edits the repository. It reads what Spec 1 section 9 lists, through `./devctl doctor`, `./devctl check`, `gh run list`, `gh pr list --state merged`, `gh pr view`, and `GET` REST reads of each PR's reviews and review comments. Every command sits in a fenced `sh` block, with placeholders as shell variables such as `$REPO`. It runs `references/audit.md` over the whole repository and returns the milestone at the glossary's levels: one epic per area with findings, and tasks that each fit one PR within the diff cap, each with acceptance criteria, a test plan and the tasks it is blocked by. The owner selects what to keep, and decision 2 says how the selection reaches the tracker.
- `audit.md`: `rs-health` runs it over the whole repository and `rs-garden` over the files changed in a range, so each item says how it applies to a range. It holds:
  - Spec 1 section 9's audit by rung, naming "each stack's floor items" where the spec names the Python floor;
  - Spec 3 section 10's drift table and its base rule, with the four signs the audit looks for;
  - the starter Patterns, each finding citing the Pattern's Lessons;
  - the Setup reasons of Task 5, which mark entries to remove;
  - what `devctl check` already fails on, which the audit does not repeat;
  - a citation of file:line or command output for every finding.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_health_and_contribute.py`, docstring `Offline: rs-health's audit and commands, and rs-contribute's opt-in, in scratch repositories.`:
  - `test_the_shared_audit_lives_where_rs_garden_reads_it`: `rapid_ship/templates/common/.agents/skills/rs-health/references/audit.md` exists, and `rs-health/SKILL.md` links `references/audit.md`.
  - `test_rs_health_runs_no_command_the_guardrails_deny`: take every fenced `sh` block in `rs-health/SKILL.md` and `references/audit.md`, join each line that ends in `\` with the next, and drop comments and blank lines. `decide` answers each command `(None, "")` for `ToolCall(shell=command, edits=(), cwd=tmp_path)` with root `tmp_path`, `HookSettings(agent_identity=True, protected=(), repository="o/r", reviewer_app_slug="o-reviewer")` and branches `lambda: LocalBranches(frozenset({"main"}), "feature")`. At least five commands are checked.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_health_and_contribute.py -q`; expected FAIL on the missing audit.
- [ ] **Step 3: write** both files; sync.
- [ ] **Step 4: run** it, `tests/test_kit_skills.py` and `tests/test_skill_discovery.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add rs-health with the audit it shares with rs-garden`.

### Task 8: `rs-contribute`, the optional skill, the GA version, and PR 7.3's verification

**Files:**
- Create: `skills/rs-contribute/SKILL.md`
- Modify: `rapid_ship/templates/kit.toml` (`optional_skills = ["rs-contribute"]`); devctl's template `settings.py` (`OPTIONAL_SKILLS: frozenset[str] = frozenset({"rs-contribute"})`); the `[kit] optional` comment, to `opt-in Kit skills: rs-contribute`, in every `.rapid-ship/project.toml` seed under `rapid_ship/templates/` and, edited in place, in this repository's `.rapid-ship/project.toml`; the comment in `test_kit_optional_names_only_the_kits_optional_skills` that says this Kit offers none; `tests/test_kit_health_and_contribute.py`. By decision 3, the Kit version in both `pyproject.toml` files, devctl's `__version__` and both `uv.lock` files. Documents: `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, the index's plan 7 row, this plan's Verification record.

**Interfaces:**
- `SKILL.md`: `name: rs-contribute`; `description: Send a fix for a rapid-ship Kit file back to rapid-ship as a pull request.`; `disable-model-invocation: true`. It follows Spec 1 section 7's six steps, with these rulings:
  - the fork is the owner's GitHub fork of `proxy-hatch/rapid-ship`, created with `gh repo fork proxy-hatch/rapid-ship --clone=false` after the owner's yes;
  - it is cloned once to `${XDG_CACHE_HOME:-$HOME/.cache}/rapid-ship/fork` and brought up to date before each fix;
  - it maps a vendored path to its template by the layers and precedence that the clone's `rapid_ship/templates/AGENTS.md` describes, and a `.claude/skills/<name>` link to `rapid_ship/templates/common/.agents/skills/<name>/`;
  - it searches for duplicates with `gh search issues` and `gh search prs`, with `--repo proxy-hatch/rapid-ship --state open`;
  - in the clone it runs `uv sync --locked`, fixes the template, then runs `uv run rapid-ship sync --in-place` and `./devctl check`;
  - the clone records rapid-ship's own Apps, so in a wired Session G7 and G8 deny the push and `gh pr create` there, and the skill gives the owner both commands for a terminal;
  - the project may apply the same fix to its vendored copy at once; if a `sync` runs before the fix ships, `rapid-ship sync --revert <path>` gives the file back.
- `rapid_ship/templates/AGENTS.md` gains one sentence: a vendored path maps back to its template by these layer rules, which `rs-contribute` follows.

- [ ] **Step 1: write the failing tests.** In `tests/test_kit_health_and_contribute.py`:
  - `test_rs_contribute_installs_only_when_opted_in`: after `main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0`, `.agents/skills/rs-contribute` does not exist. Write `optional = ["rs-contribute"]` under `[kit]` in `.rapid-ship/project.toml`, commit, and run `main(["sync", "--in-place"]) == 0`. Then `.agents/skills/rs-contribute/SKILL.md` exists; `.claude/skills/rs-contribute` links to `../../.agents/skills/rs-contribute`; the lock records both as managed; devctl's `load_project` reads `("rs-contribute",)`; and `skill_errors` is `[]`.
  - `test_rs_contribute_hands_the_owner_its_writes`: `rs-contribute/SKILL.md` contains `gh repo fork proxy-hatch/rapid-ship --clone=false`, `gh search issues`, `gh search prs`, `--repo proxy-hatch/rapid-ship --state open`, `rapid-ship sync --revert` and `rapid_ship/templates/AGENTS.md`.
- [ ] **Step 2: run** them; expected FAIL with `unknown optional Kit skill 'rs-contribute'`, and on the missing `SKILL.md`.
- [ ] **Step 3: implement** the skill, `kit.toml`, `OPTIONAL_SKILLS` and the comments; sync.
- [ ] **Step 4: run** the file, `tests/devctl/test_devctl_settings.py`, `tests/test_kit_seed_keys.py`, `tests/test_kit_contents.py` and `tests/test_kit_skills.py`; expected PASS. Status, fast check. Commit `feat: add the optional rs-contribute skill`.
- [ ] **Step 5: the GA version.** Set `1.0.0` in both `pyproject.toml` files and in `__version__`, as plan 5's Task 2 Step 1 set `0.2.0`. Run `uv lock` and `uv lock --project rapid_ship/templates/common/tools/devctl`, sync, then `uv run pytest tests/test_kit_contents.py -q`; expected PASS. Commit `chore: set the Kit version to 1.0.0 for GA`. Skip this step if the owner declines decision 3.
- [ ] **Step 6: documents and verification.** Describe both skills in the files above. Run the five checks with the PR's base and record them. Evidence: `Not covered: rs-health in a Session, which Task 9 runs; rs-contribute's push and PR, which would open a real PR on rapid-ship`. Commit `docs: record PR 7.3's verification`.

## Owner steps

### Task 9: Live trial of `rs-setup` and `rs-health` (Owner step)

**Files:**
- Create, on `plan7-site`: `docs/trials/<run date>-rs-setup-and-rs-health.md`
- Modify, on `plan7-site`: `docs/trials/AGENTS.md`

Preconditions: plan 6, 7.2 and 7.3 are merged. Record `origin/main`'s commit, and run `rapid-ship` as `uvx --from <a checkout of that commit> rapid-ship`. Each step's commands and output feed 7.4's pages. The record therefore keeps every command and its output verbatim, scrubbed of home and temporary paths, as plan 5's spike record did.

- [ ] **Step 1 (agent): prepare.**
  - Check each value in "Where 7.2 depends on plan 6" against `origin/main` with `git grep -n -F '<value>' origin/main -- rapid_ship/templates`. A value that differs becomes a fix PR to `rs-setup` from `main`, merged before Step 3.
  - Prepare the first commit of `proxy-hatch/rs-existing`, an existing Python project without the Kit, in a scratch directory. It holds a small greeting CLI, `rs_existing`, under `src/` with tests, and its own `pyproject.toml`. Its Ruff, mypy and pytest settings differ from the Kit's in at least one stylistic option, such as `line-length = 100`, and lack at least one floor rule, such as Ruff's `BLE`. It also holds one `# noqa` suppression, one unused function, one declared dependency that nothing imports, a `.pre-commit-config.yaml`, a workflow `.github/workflows/test.yml`, and a `[tool.uv.workspace]` whose `members` glob `tools/*` covers one member package and, once the Kit lands, `tools/devctl`.
  - Write the record with these steps, the prepared commit's SHA, and an empty results table: the command or prompt, the expected result, and the observed one.
- [ ] **Step 2 (Owner): seed rs-existing.** Create the public repository `proxy-hatch/rs-existing`, push the prepared commit to its `main`, clone it, and run `uvx pre-commit install`, which puts a hook in `.git/hooks`.
- [ ] **Step 3 (Owner): Get started.** Follow Task 12's Get started outline exactly, on a new public repository, `proxy-hatch/rs-get-started`. Run `init --stack python`, then `/rs-setup` without Agent identity. Open the red PR, which deletes the skeleton test and has no body: `diff` and `evidence` fail, and the merge guard denies the agent's merge. Then open the green `hello` PR and merge it.
- [ ] **Step 4 (Owner): two stacks, new.** On a new private repository, `proxy-hatch/rs-two-stacks`, run `init --stack python=backend --stack typescript=frontend`, then `/rs-setup`. Accept Agent identity with the existing Apps, and the sandbox. Record the GitHub Free ruleset gap, `npm install`, `./devctl check` passing, and doctor.
- [ ] **Step 5 (Owner): rs-existing, existing.** Run `init` without `--stack` and record its proposal, then rerun it with the proposed `--stack` options. Run `/rs-setup`, with the existing suppressions and dead code marked, the hook and workflow overlaps shown, `./devctl doctor --skills` in Claude Code, the Setup PR and the tool-settings PR. Then rerun `rs-setup`'s GitHub step with Agent identity on and the ruleset present (Review Focus 1 and 2).
- [ ] **Step 6 (Owner): `rs-health`** on rs-existing, ending with a standards milestone in its tracker. Record the milestone's link.
- [ ] **Step 7 (implementer): write the record** from the owner's output, and add its line to `docs/trials/AGENTS.md`. Each difference from the expected result becomes a fix PR from `main`, and its case is rerun, before 7.4 merges. `grep -n -e /Users/ -e /home/ -e /private/tmp -e /tmp/` on the record finds nothing. Commit `docs: record the rs-setup and rs-health trial` on `plan7-site`.

### Task 10: Apply `rs-setup`'s GitHub settings to `proxy-hatch/rapid-ship` (Owner step)

**Files:**
- Create, on `plan7-site`: `docs/trials/<run date>-rapid-ship-github-settings.md`
- Modify, on `plan7-site`: `docs/trials/AGENTS.md`

- [ ] **Step 1 (Owner), in a terminal,** from a checkout of 7.2's reviewed head: read the rulesets, then apply `ruleset.json` with `POST`, or with `PUT` to an existing `rapid-ship` ruleset, as `rs-setup` does. Set `delete_branch_on_merge` and the fork PR approval with Task 5's two commands. G8 denies these writes to an agent here, because Agent identity is on.
- [ ] **Step 2 (Owner):** run `./devctl doctor`; the ruleset, delete branch on merge and fork PR workflow approval items are ok.
- [ ] **Step 3 (implementer): write the record** with each command, its exit code and doctor's lines, and add its line to `docs/trials/AGENTS.md`. Record the consequence: every later PR needs the code owner's approval or the admin bypass, a passing `devctl check`, resolved threads and a squash merge. Commit `docs: record rapid-ship's GitHub settings` on `plan7-site`.

## PR 7.4: the documentation site and GA (`plan7-site`, on 7.1a's head)

### Task 11: The site's structure, Home, Why rapid-ship, The journey, Concepts and Reference

**Files:**
- Create: `website/src/pages/index.md` (Home), `website/page-rules.js`, `website/src/theme/DocItem/Content/index.js`; `docs/start/why-rapid-ship.md`, `docs/start/the-journey.md`; `docs/concepts/` (`life-of-one-change.md`, `evidence-not-reports.md`, `four-rungs.md`, `agent-identity.md`, `guardrails-and-their-limits.md`, `stacks.md`); `docs/reference/` (`rapid-ship-cli.md`, `devctl-check.md`, `devctl-doctor-and-as.md`, `devctl-hook.md`, `settings-files.md`, `feature-map-and-pattern-formats.md`, `supported-setups.md`, `skills.md`)
- Delete: `docs/getting-started.md`, `asset/public/banner.jpeg`
- Modify: `website/docusaurus.config.js`, `website/sidebars.js`, `website/src/css/custom.css`, `.github/workflows/docs.yml` (both path lists: `GLOSSARY.md` replaces `README.md`; the owner pushes this commit), `README.md`, `docs/branding.md`, `asset/AGENTS.md`, `docs/AGENTS.md`, `website/AGENTS.md`, Spec 1 section 2 item 4, the design's Delivery paragraph, `ARCHITECTURE.md`'s documentation-site section and its "What was removed" paragraph, the index's plan 7 row, this plan's Verification record

**Interfaces:**
- Front matter of every page under `docs/start/`, `docs/concepts/`, `docs/guides/` and `docs/reference/`: `status`, one of `built`, `in-review` or `designed`, and `status_detail`, the plan or spec, such as `plan 5` or `Spec 3`.
- `website/page-rules.js` exports `pageProblems(relativePath, frontMatter, content)`, which returns a list of strings. Both rules apply to the pages under those four directories and to `GLOSSARY.md`: a page lacks a valid `status` or a non-empty `status_detail`; or a page contains `100x`, `powerful`, `seamless` or `effortless`, in any case. Home, `ARCHITECTURE.md`, `docs/credits.md`, `docs/superpowers/`, `docs/adr/` and `docs/trials/` are exempt. `parseFrontMatter` in `docusaurus.config.js` calls it for every document and throws an `Error` with the problems joined, each starting with the repository-relative path. `GLOSSARY.md` joins `include`; the same hook gives it `slug: /reference/glossary`, `status: built` and `status_detail: the glossary`. `README.md` leaves `include`, because Home replaces it.
- `website/src/theme/DocItem/Content/index.js` wraps the theme's component, as Docusaurus's "wrap" swizzle does. It shows a badge such as `Built · plan 5`, from `status` and `status_detail`, above the content when `status` is set.
- Home (`website/src/pages/index.md`) opens with the owner's tagline, "Becoming a 100x developer starts with agents that earn your trust.", and the line "Agents that prove their work earn autonomy, so you can stop watching every one of them." A plain subheading follows: what rapid-ship gives your coding agents, that you start by deciding on every pull request, and that your Harness still runs the agents. Then one line says what works today and links The journey.
- Sidebar: Start (Home as `{type: 'link', label: 'Home', href: '/'}`, then Why rapid-ship and The journey as Step 3 writes them; Task 12 adds Get started), Concepts as `{type: 'autogenerated', dirName: 'docs/concepts'}`, Reference as `{type: 'autogenerated', dirName: 'docs/reference'}` with the glossary, and Project, collapsed and last: Contribute (`ARCHITECTURE.md`), Design records (`docs/superpowers`, `docs/adr`, `docs/trials`) and Credits. Navbar: Concepts, Reference, GitHub; Task 12 adds Get started and Guides. `docs/branding.md` leaves the sidebar.
- Pages. The status is the one `main` should hold at 7.4's review; Task 12 Step 2 rechecks each.

| Page | After it, the reader can | From | Status |
| --- | --- | --- | --- |
| Why rapid-ship | Say which of their problems it solves, who it is for and what it is not; it credits the owner's Trust-First Agentic Engineering Playbook | design: The problem, The boundary, Who does what; Spec 1 §1; ADR 0004 | built, the design |
| The journey | Say what works today and what comes next, from the first check to Flight, one row per plan and spec | design: Who does what, Modes, Delivery; §1 of Specs 1 and 3 | built, plans 1 to 7 |
| The life of one change | Say who acts at each step, the owner's own Sessions included, and what evidence each step leaves | design: Who does what, How the bar is held; Spec 1 §§4 to 6, §8 | built, plans 3 to 7 |
| Evidence, not reports | Read a `devctl check` result and an Evidence section, and say what a pass does not prove | Spec 1 §5 Steps, Output, Evidence, Where `check` runs | built, plans 3 and 5 |
| The four rungs | Put a new rule on the rung that fits, with exceptions instead of ratchets, and the Protected set | design: Standards; Spec 1 §4 Patterns, Protected set; §5 Exceptions | built, plans 3 and 5 |
| Agent identity | Decide whether their setup needs it | Spec 1 §3 `rapid-ship app`, §6 Agent identity; ADR 0002 | built, plan 4 |
| Guardrails and their limits | Know what the guardrails and the merge guard deny, and what they cannot stop | Spec 1 §4 Harness guardrails, The merge guard | built, plan 5 |
| Stacks | Lay out a Python backend and a TypeScript frontend | design: Standards; Spec 1 §5 Several stacks | built, plan 6 |
| `rapid-ship` CLI; `devctl check`; `devctl doctor` and `devctl as`; `devctl hook`; Settings files; Feature map and Pattern formats | Look up a command, option, default, exit code, key or field | Spec 1 §§3 to 6; the index's Conventions | built, plans 2 to 6 |
| Supported setups | Check their setup before installing | design: What rapid-ship ships; Spec 1 §1 | built, plans 5 and 6 |
| Skills | Pick the skill for a job and know who runs it | Spec 1 §7; Spec 3 §§10, 11 | built, plan 7 and Spec 3's plan |

- `docs/AGENTS.md` gains the page templates and style rules, so agents writing pages need not reach Linear. A concept page runs 500 to 900 words: title, a one-sentence subtitle, the case, the definition, the model, who does what, limits and next. A reference page holds the synopsis, options with their defaults, exit codes and one example. The proposal's eight style rules follow, one line each. One of them reads: "Label every block 'Terminal' or 'Your coding agent', and follow it with the expected result from a real run." A reference example comes from a local run or a trial record, with the version and date it was recorded with. Pages cite no Linear ID.
- `README.md` becomes a lean GitHub front page. The logo replaces the banner. Then come the subheading, the senior-engineer line, the evidence line, an honest Status, a link to the site and the credits. Its paragraphs on Modes, the merge guard, stacks and the tracker move to Why rapid-ship and The journey, with their status. `docs/branding.md`'s banner prompt drops the tagline line, and the config's `tagline` and footer drop it too.

- [ ] **Step 1: page rules first.** Write `page-rules.js` and wire it into `parseFrontMatter`. Add a concept page without `status`; `npm --prefix website run build` fails and names the file. Add the status, then a `powerful` in its body; the build fails again. Remove both: the build passes, although the plan index and this plan quote "100x". Record the three runs in 7.4's subsection of the Verification record.
- [ ] **Step 2: structure.** Build Home, the badge, the sidebar and the navbar; add `GLOSSARY.md`; take `README.md` out of `include`; delete `docs/getting-started.md`; edit `docs.yml`'s path lists. The build passes with no broken link or anchor. Commit `feat: rebuild the documentation site's structure with status badges`, and have the owner push it, since it edits a workflow.
- [ ] **Step 3: pages.** Write each page from the sources its row names, and add Why rapid-ship and The journey to Start. Write Stacks, Supported setups and the Reference pages from `main` once plan 6 has merged, and Skills once 7.2 and 7.3 have. Record each Terminal example from a real local run, or quote a trial record's, with the version and the date. Commit `docs: write Why rapid-ship, The journey, the Concepts and the Reference`.
- [ ] **Step 4: README and guides.** Trim `README.md`, delete `asset/public/banner.jpeg`, and update `docs/branding.md`, `asset/AGENTS.md`, `docs/AGENTS.md` and `website/AGENTS.md`. Update Spec 1 section 2 item 4 and `ARCHITECTURE.md`'s "What was removed" paragraph, which both say the getting-started guide remains, and the design's Delivery line. Check Home and one concept page by eye in `npm --prefix website run serve`, at desktop and phone widths, in light and dark mode. Commit `docs: trim the README to a GitHub front page`.

### Task 12: Get started, the Guides, GA, and PR 7.4's verification

**Files:**
- Create: `docs/start/get-started.md`; `docs/guides/` (`set-up-a-repository-with-rs-setup.md`, `add-the-kit-to-an-existing-repository.md`, `audit-a-repository-with-rs-health.md`, `set-up-a-python-backend-and-a-typescript-frontend.md`, `give-your-agents-their-own-github-identity.md`, `turn-on-the-merge-guard-in-claude-code.md`, `keep-the-kit-current.md`, `write-a-prs-evidence-section.md`, `record-an-exception.md`, `turn-a-review-comment-into-a-check.md`, `write-a-pattern.md`)
- Modify: `website/sidebars.js` (Get started in Start; Guides as `{type: 'autogenerated', dirName: 'docs/guides'}`); `website/docusaurus.config.js` (the navbar); `docs/AGENTS.md`; every page of Task 11 whose status or content differs from `main`; each GA text that Step 3's commands find, among them `README.md`, `ARCHITECTURE.md:83`, the root `AGENTS.md`, `rapid_ship/templates/AGENTS.md:15`, the comment at `tests/devctl/test_devctl_exceptions_allowlists.py:182`, Spec 1's status line and sections 3 to 5, the design's status line and "What rapid-ship ships", and the index's Conventions; the index's plan 7 row; this plan's Verification record

**Interfaces:**
- Get started covers one Python stack in a new repository:
  1. Prerequisites, each with its check command: macOS, uv, `gh auth status`, `gitleaks version` (8.30.1) and Claude Code.
  2. Terminal: create and clone an empty public repository, and run `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v1.0.0 rapid-ship init --stack python --owner <you>`.
  3. Your coding agent: `/rs-setup`. It shows its plan, applies the ruleset after your yes, and `./devctl doctor` reports no gap.
  4. Terminal: delete the skeleton test on a branch, push it, and open a PR with no body; CI's `devctl check` fails at `diff` and `evidence`. Your coding agent: ask it to merge the PR; the merge guard denies it.
  5. Your coding agent: a small `hello` command, test-first. Its PR carries an Evidence section, the check passes, and you merge it.
  6. What the loop gives you, a link for each step, and the page's limits.

  It gives no time promise until a trial has measured one.
- Guide template: the title states the outcome; then the subtitle, the status, "Works with", before you start, the example, the steps, what you have now, your own project, "Recorded with" and next.

| Guide | From | Outputs from |
| --- | --- | --- |
| Set up a repository with `rs-setup` | Spec 1 §8 | Task 9 Steps 3 and 4 |
| Add the Kit to an existing repository | Spec 1 §3 `init`, Who owns what; §5 Exceptions; §§8, 9 | Task 9 Steps 5 and 6 |
| Audit a repository with `rs-health` | Spec 1 §9 | Task 9 Step 6 |
| Set up a Python backend and a TypeScript frontend | Spec 1 §4 TypeScript guardrail settings; §5 Several stacks | Task 9 Step 4 |
| Give your agents their own GitHub identity | Spec 1 §3 `rapid-ship app`; §6 Agent identity | Task 9 Step 4, and plan 4's trial record |
| Turn on the merge guard in Claude Code | Spec 1 §4 Harness guardrails, The merge guard; §6 `devctl hook` | Task 9 Step 3, and plan 5's guardrails trial record |
| Keep the Kit current | Spec 1 §3 `status`, `sync`, Who owns what, Lock file | a local run |
| Write a PR's Evidence section | Spec 1 §5 Diff policy, Evidence | a local run |
| Record an exception | Spec 1 §5 Exceptions | a local run |
| Turn a review comment into a check | Spec 1 §3 Who owns what; §5 Steps | a local run |
| Write a Pattern | Spec 1 §4 Patterns, Starter Patterns; §5 Map rules, References | a local run |

- `docs/AGENTS.md` gains the rule, from GA on: a PR that changes user-visible behaviour updates its pages, their status and its row in The journey in the same PR. Spec 3's plan writes its own pages under these directories, with Task 11's front matter, and this PR's build checks them.
- GA: each text that says the Kit keeps no backward compatibility before GA now says that rapid-ship reached GA with `v1.0.0`, and that the policy after GA is not designed yet (decision 3).

- [ ] **Step 1: local guides.** While Task 9 runs, record the five local guides' runs on scratch repositories at the GA version, and write those guides.
- [ ] **Step 2: trial pages.** Write Get started and the other six guides from Task 9's record, and from Task 10's where a page cites it. Recheck every Task 11 page's status and content against `main`, and rerecord an example whose output changed. The build passes.
- [ ] **Step 3: GA text.** Run `git grep -n -i -e 'before GA' -e 'backward compatib' -- . ':!docs/trials' ':!docs/superpowers/plans'` and `git grep -n -i -e 'before GA' -e 'backward compatib' -- docs/superpowers/plans/2026-10-14-kit-and-setup.md`. Update every hit, a devctl message included. Rerun both; they print only lines that state the policy after GA or record what a built PR did. Commit `docs: write Get started and the Guides for GA`.
- [ ] **Step 4: verify.** Run the five checks with the PR's base. Evidence: `Not covered: whether each page's prose matches the code beyond its recorded examples; Spec 3's pages, which its plan writes`. After the merge, the owner tags `v1.0.0` on the merge commit and checks `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v1.0.0 rapid-ship --help`. Commit `docs: record PR 7.4's verification`.

## Verification record

Each PR's last task fills its own subsection with each command, its exit code and the summary line it printed. A blocked, skipped or simulated result is written as such, never as passed.

### 7.1a

Pending.

### 7.1b

Pending.

### 7.2

Pending.

### 7.3

Pending.

### 7.4

Pending.
