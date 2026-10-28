# rs-setup and rs-health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the engineering skills, `rs-setup`, `rs-health`, optional `rs-contribute`, and a verified documentation site for GA after Spec 3 and Owner Tasks 9 and 10.

**Architecture:** Every Kit skill is one managed template directory under `rapid_ship/templates/common/.agents/skills/<name>/`, which `render_files` already renders with its `.claude/skills/<name>` link; this repository vendors each through `uv run rapid-ship sync --in-place`. `rapid_ship/upstream.lock` records each forked file's upstream blob, and `tests/test_kit_upstream.py` holds the forks to pristine fixtures. `rs-setup` applies `ruleset.json`, which doctor's `ruleset_problems` checks. `rs-health`'s references hold the audit and the task shape, which `rs-garden` reads by path. The site keeps Docusaurus with Markdown pages under `docs/`, and its build fails a page without a status.

**Tech Stack:** Markdown skills with YAML front matter; TOML; JSON; Python 3.12+ standard library (`hashlib`, `difflib`, `tomllib`, `json`); pytest; gh; Docusaurus 3.10.2 in `md` format on Node.js 22 or later.

**Spec:** [Spec 1](../specs/2026-10-14-kit-and-setup-design.md) sections 7–10; the [rapid-ship design](../specs/2026-10-14-rapid-ship-design.md), Standards and What rapid-ship ships; [Spec 3](../specs/2026-10-16-metrics-and-gardening-design.md) section 10; and the [plan index](2026-10-14-kit-and-setup.md), Conventions, Shared interfaces and Plan 7.

**Status:** revised on 2026-10-28, awaiting owner approval in a standalone document PR before implementation. This document owns no code. Five later code PRs implement the unchecked tasks below. PR 7.4 stays one PR and lands after Spec 3 and Owner Tasks 9 and 10. Codex wiring (PRO-142, stacked on PRO-155) lands before GA. No delivery or review skill or tracker setting is added.

**Source baseline:** plan 6 was read at `419f2196484353375ebe6049ff8c6a150476c6d1`, then reconciled with revision `94cf880377dd30cc9c26546fdae5b68d5b85525c` through read-only git objects. Its document merges first. Consume its current shared signatures without redefining them.

**Owner steps:** naming Task 9's existing repository (decision 2); Tasks 9 and 10; and pushing each commit that edits `.github/workflows/`. The agent writes each procedure and its empty record. The owner runs every Harness Session, GitHub write and push in them, and the implementer then writes the record from the owner's output. No implementer subagent runs an Owner step.

## Order and parallel work

| PR | Branch | Base | Tasks | Counted lines, estimated |
| --- | --- | --- | --- | --- |
| Document | separate documentation branch | `main`, after plan 6's document | Plan approval only | Markdown excluded |
| 7.1a | `plan7-upstream` | approved plan on `main` | 1 | about 350 |
| 7.1b | `plan7-engineering` | 7.1a's head | 2, 3, 4 | about 400 |
| 7.2 | `plan7-setup` | 7.1a's head | 5, 6 | about 200 |
| 7.3 | `plan7-health` | 7.1a's head | 7, 8 | about 150 |
| 7.4 | `plan7-site` | `main` for structure; normally merge 7.1a before dependent work | 11, 12; records of Owner Tasks 9 and 10 | about 250 |

- **7.1a first.** Task 1 rewrites skill discovery before Kit skills are vendored. Other code PRs may branch from its reviewed head.
- **Parallel work.** The owner accepted parallel work on 2026-10-27. Start 7.1b, 7.2 and 7.3 once 7.1a's head exists. Task 11 Steps 1 and 2 may start independently. No fixed cap or wave barrier applies; per-task prerequisites still hold.
- **Merged prerequisites.** Task 4's Pull requests pointer and Task 7's `HookSettings` tests require merged PRO-166 (`escalation-and-pr-guide`). Merge `origin/main` normally before those steps. PRO-155 supplies agy wiring; PRO-172's executable-hook fix must merge before agy trials. PRO-142 supplies Codex wiring and must merge before GA and its trial.
- **7.2's Health dependency.** Prepare 7.2 and 7.3 in parallel. Before Task 5's green test run and 7.2's final validation, merge `origin/main` containing merged 7.3. Its `rs-health` skill and `references/proposed-task.md` must be present. Land 7.3 before 7.2.
- **7.2's quotations.** Task 5 writes all Setup skill content from the dependency tables. Task 6 owns references and reconciles quotation drift. Approved pending wiring may be described conditionally; no live claim precedes the wiring's merge and trial.
- **Owner steps.** Task 10's early application was approved on 2026-10-28. The manager prepared an owner-run ruleset and fork-approval script; execution and results remain unverified. Task 10 records actual full-doctor output. Task 9 waits for its named prerequisites and the owner's repository decision.
- **GA.** 7.4 lands as one PR after Spec 3 and Tasks 9 and 10. Task 12 rechecks all site pages and guides after Spec 3. The owner confirms the GA version before Task 12 sets or tags it.
- **Trial records.** Tasks 9 and 10 record results on `plan7-site`, including their entries in `docs/trials/AGENTS.md`. Trial defects become separate fix PRs from `main` and must be rerun before GA.
- **Spec 3 pages.** Spec 3 writes its own pages using the index's [Documentation site pages](2026-10-14-kit-and-setup.md#documentation-site-pages-plan-7-spec-3s-plan-writes-its-own-pages) contract. It need not wait for Task 11's `docs/AGENTS.md` edit. Task 12 links those pages from The journey and Skills.
- **After retirement.** Reviews follow the root guide's Pull requests section, `rs-ponytail` and the Harness's own review. Architecture work uses `rs-codebase-design`.

### Landing a code branch after its parent squash-merges

1. Run `git fetch origin` in the child's worktree.
2. Read the final remote parent head as `<parent-head>` and its exact squash commit on `main` as `<parent-squash>`.
3. Run `git merge-base --is-ancestor <parent-head> HEAD`; if it fails, normally merge `<parent-head>` and verify the review fixes.
4. Run `git diff --quiet <parent-squash> <parent-head>`; stop if the trees differ.
5. Run `git merge -s ours <parent-squash>` to record only that parent's squash ancestry.
6. Run a normal `git merge origin/main` to retain sibling changes.
7. Regenerate the lock with `uv run rapid-ship sync --in-place`; never hand-edit it.
8. Check `git diff origin/main...HEAD --stat` and the full diff; only the child's PR scope may remain.
9. Retarget the PR to `main`, push with `./devctl as worker push`, and verify its exact head and required checks.

Before the parent merges, use `--base origin/plan7-upstream` for dependent PR checks. Never apply `-s ours` to `origin/main`.

**Where 7.2 depends on plan 6.** The revised document assigns 6.1a Tasks 1, 1b, 4, 3a and 5; 6.1b Tasks 2, 14 and 3b; 6.2a Tasks 6, 12a and 9; 6.2b Tasks 7 and 8; and 6.3 Tasks 10, 11, 12b and 13. 7.2 may quote that approved document before its code merges. Task 6 reconciles merged changes; Task 9 checks every quotation against merged code.

| `rs-setup` content | Plan 6's PR and task | Values quoted |
| --- | --- | --- |
| Step 1, New or existing: the stacks, from each `[[stack]]` table's `name` and `directory` in `.rapid-ship/project.toml` | 6.1a Task 1 | `[[stack]]`, `name`, `directory` |
| Step 2, Documents: the seeded stack guide `<directory>/AGENTS.md`, which the root guide links | 6.1b Task 3b | the root guide's row `The Python stack`, linking `backend/AGENTS.md` |
| Step 3, Patterns: the TypeScript starter Patterns offered as tasks | 6.3 Task 11 | `typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md`, `typescript-performance.md` |
| Step 4, Checks, new project: `uv sync` in each Python stack's directory, `npm install` in each TypeScript stack's | 6.1a Task 4, 6.1b Task 3b | none |
| Step 4, Checks: Node.js and npm at the major that each TypeScript stack's `engines.node` names | 6.2a Task 9, 6.3 Task 10 | Node.js 24; `engines.node = ">=24.15.0 <25"`; `doctor_typescript.py`’s `node_items`, `floor_item` and floor constants |
| Step 4, Checks, existing project: devctl's exclusions and the uv workspace's `exclude` in the root `pyproject.toml`; the dead-code settings (`[tool.vulture] paths`, `lint.external`, deptry's exclusion) in each Python stack's own `pyproject.toml` | 6.1a Tasks 3a and 4 | doctor's exclusions item reads only the root `pyproject.toml`, and checks the tools only with a Python stack at `.` |
| Step 4, Checks, existing TypeScript project: knip's findings and the TypeScript suppressions marked at Setup (Task 5) | 6.2a Task 6, 6.2b Task 7 | `@public`; `knip.jsonc`'s top-level `ignore*` keys; the rules `knip:@public` and `knip.<key>:<item>` |
| Step 4, Checks, decision 1: the TypeScript devDependencies and pins added to an existing project, and ESLint and Prettier plugins for tools such as Tailwind CSS | 6.3 Task 10 | plan 6's Tech Stack pins and Task 10's `package.json` devDependencies |
| Step 6, Sandbox: the network domains, write paths and command exclusions of the setting it writes, for uv, `uv tool run`, gh and npm, and `known-failures.md`'s sandbox rows | PRO-156 with PRO-157 owns the pending Spec 1 step 6 fix; plan 6 Task 13 adds npm needs | Task 5's explicit sandbox values; reconcile after those fixes merge |
| Step 7, GitHub: the Walk line, and the Protected lines for a stack in a subdirectory | 6.1b Task 3b, 6.1a Task 3a, 6.2a Task 9 | `/<directory>/` before each of `PYTHON_PROTECTED_PATHS` and `TYPESCRIPT_PROTECTED_PATHS` |
| Step 7, GitHub: `[github] repository`, which `init` fills from a GitHub `origin` remote | 6.1b Task 14 (PRO-159) | `rapid_ship/kit/init.py`'s origin repository parsing and `rapid_ship/cli.py`'s report |
| Step 13, Setup PR: the `rapid-ship/init` branch, which `init` also makes in a repository without commits | 6.1b Task 14 (PRO-161), pending Spec 1 bootstrap-order update | `rapid_ship/cli.py`: `from your own terminal, because the Kit's guardrails deny an agent's push to the default branch`; owner pushes before step 7 applies a ruleset |
| `stylistic-options.md`'s Prettier and ESLint lists, and the tool-settings PR's TypeScript rules | 6.2a Task 9, 6.3 Task 10 | `TSCONFIG_FLOOR`, `ESLINT_ERRORS`, the seed's `eslint.config.js` rules |
| `known-failures.md`'s Init row for `init` without `--stack` | 6.1b Task 2 | `init wrote nothing: confirm the stacks first.` |
| `known-failures.md`'s TypeScript rows | 6.1a Task 4, 6.2a Tasks 6 and 9 | `lint (frontend)`; `is not installed; run npm ci there`; `devctl/node.py`'s `cannot_run`; `doctor_typescript.py`'s floor constants |
| Task 9's trial with a Python `backend/` and a React TypeScript `frontend/` | all of plan 6 | none |

**Where 7.2 depends on guardrail and standards changes.**

| `rs-setup` content | Branch | Values quoted |
| --- | --- | --- |
| Step 5, Harness guardrails: the Harnesses the Kit wires, agy's wiring file, and agy without G5; `known-failures.md`'s agy rows | `agy-wiring` | `.agents/hooks.json`; `devctl hook agy pre-tool`; doctor's `Claude Code wiring` and `agy wiring` items |
| Step 7, GitHub: the Protected lines | `agy-wiring` | `/.agents/` in place of `/.agents/skills/` |
| Step 9, Mode, and `known-failures.md`'s merge guard rows | `escalation-and-pr-guide` | `merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #`; `, so the owner merges it` in `devctl/merge_guard.py` |
| Step 15, Next: the section that the owner's Sessions follow | `escalation-and-pr-guide` | `## Pull requests` |
| Steps 5 and 6: Codex wiring, trust review and sandbox | PRO-142, stacked on PRO-155; merge and trial before GA | `.codex/hooks.json`, `devctl hook codex pre-tool`, doctor’s `Codex wiring` item, `/.codex/`, owner trust review in `/hooks`, owner configuration `sandbox_mode` |
| Known failures: rejected CODEOWNERS owner and key guidance | PRO-147 with PRO-148; merge before quoting final messages | `devctl/doctor_github.py`'s CODEOWNERS errors and `devctl/doctor_local.py`'s key guidance |
| Audit, trial and pages: golden paths | the golden-paths library (PRO-167), merged before Tasks 7, 9 and final pages | No feature-file work, feature-map audit or drift requirements; no new check or command |

**7.3 does not depend on plan 6.** `rs-health` reads doctor's and check's output whatever the stacks are, and names "each stack's floor items". `rs-contribute` maps a vendored path to its template by the layout that the clone's `rapid_ship/templates/AGENTS.md` describes, which 6.1b updates, so the skill holds before and after plan 6. Task 7 starts after PRO-166 merges, with `every_pr=True` and `unit_tests=()` in each `HookSettings`. 7.3 still edits files that 6.1a and 6.1b change, as File overlap lists.

**File overlap** (resolve as the last column says, never by dropping a side):

| Files | Touched by | Resolution |
| --- | --- | --- |
| `.rapid-ship/kit.lock` | 7.1a, 7.1b, 7.2, 7.3, every plan 6 PR, the descope's code, the agy wiring and Spec 3's PRs | Never hand-merge: take `origin/main`'s lock, run `uv run rapid-ship sync --in-place`, commit the result |
| devctl's `settings.py` (template and vendored copy), `tests/devctl/test_devctl_settings.py` | 7.3 (`OPTIONAL_SKILLS`, one comment), 6.1a (`[[stack]]`), the descope's code (`Escalation`) | Keep every side; 7.3 changes one line in each |
| `rapid_ship/templates/kit.toml` | 7.3 (`optional_skills`), 6.1b (`new_project` becomes a table by stack, after the top-level keys), the agy wiring, Spec 3's plan | Spec 3 PR 3.7 alone renames `optional_skills` to `optional` and the reader/property. Add `rs-contribute` using main's name/API; whichever PR lands second updates callers and fixtures. 7.1 does not edit `kit.toml` |
| `tests/test_kit_skills.py` | 7.1a, 7.1b, 7.2, 7.3 and Spec 3 | Keep every side’s tests and expand name coverage only as skills ship |
| Both root-guide seeds, `rapid_ship/templates/common/AGENTS.md` and `rapid_ship/templates/python/AGENTS.md`, and `tests/test_kit_contents.py` | 7.1b (the glossary bullet), the descope's code (the scope Rule, the Pull requests section), 6.1b (moves the root guide's text into `common/`), Spec 3's plan (the Rule for a Correction given in a Session) | Keep every side's lines. Apply 7.1b's bullet where the root guide's text then lives |
| `rapid_ship/kit/init.py`, `tests/test_kit_init.py` | 7.2 (the dirty-tree refusal's last line), 6.1b (`init`'s rework, with the fixes of PRO-159 and PRO-161) | Keep both; 7.2 changes one message line and one assertion |
| Every `.rapid-ship/project.toml` seed under `rapid_ship/templates/`, and this repository's `.rapid-ship/project.toml` | 7.3 (the `[kit] optional` comment), 6.1a (`[[stack]]`), 6.1b (moves the Python seed to `common/`, deletes `agnostic/`), the descope's code (drops `kinds` and `revision_rounds`) | Apply 7.3's comment to each seed where it then lives |
| The Kit version in both `pyproject.toml` files, devctl's `__version__` and both `uv.lock` files | 7.4 (decision 3), and any plan 6 or Spec 3 PR that sets a version | Keep the higher version, then rerun both `uv lock` commands |
| `ARCHITECTURE.md`, the root `AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, `README.md`'s status lines, Spec 1's status line, the index's rows for plans 6 and 7 | every PR of plans 6 and 7, the descope's code, the agy wiring and Spec 3's PRs; 7.4 trims `README.md` | Keep both sides' clauses; 7.4's trimmed README takes `main`'s status facts |
| Spec 1 section 2, items 3 and 4, on adjacent lines | 7.1b (item 3), 7.4 (item 4) | Keep both items' edits |
| Spec 1 sections 3, 4, 8 and 10 | 7.1b (section 4's skeleton item 6), 7.2 (section 3 step 1; section 8 step 4.3 only after owner decision 1), Task 9's record PR (section 10 after owner decision 2), PRO-156/157 (sandbox), plan 6 Task 14 (PRO-159/161 bootstrap), PRO-147/148, the agy and Codex wiring (sections 4, 6 and 8), Spec 3's plan | Keep both sides' clauses |
| The index's sentence on which plans are started | this document's commit and plan 6's | Keep both plans' clauses |
| `docs/credits.md`, `docs/AGENTS.md`, `website/`, `.github/workflows/docs.yml` | 7.1b (`docs/credits.md` text only), 7.4 | 7.4 changes no credits text, only where the sidebar shows it |
| `docs/trials/AGENTS.md` | 7.4 (Tasks 9 and 10), plan 6's Task 13, the agy wiring's trial | Keep every line |
| This plan's Verification record | every PR of plan 7 | Each PR fills its own subsection |

## Owner decisions needed

These three decisions remain open for the standalone plan PR. Recommendations are not approval.

1. **Existing repository lacking a check tool.** Spec 1 §8 step 4.3 leaves existing tool settings unchanged in the Setup PR. Recommend adding missing tools at the seed's version range with minimal operational settings: `ruff`: `extend-exclude = ["tools/devctl"]`; `mypy`: `files` naming actual source/test roots and `exclude` covering `tools/devctl`; `import-linter`: `root_packages` naming product packages only, excluding devctl; `pytest`: `testpaths` naming actual test roots outside `tools/devctl`. Preserve existing stylistic and rule choices. vulture and deptry are already specified. If approved, future 7.2 updates §8 step 4.3 before using this behavior; otherwise record the blocked tool and keep that contract.
2. **Task 9's existing repository.** Recommend a new public `proxy-hatch/rs-existing`, prepared with the adoption cases below. hello-rapid-ship was recreated and now has a Kit lock. The owner may instead name an existing project. Task 9's record PR updates Spec 1 §10 after confirmation.
3. **GA 1.0.0.** Recommend setting `1.0.0` in Task 12 and tagging `v1.0.0` after 7.4 merges. Keep version-dependent commands conditional until confirmed. The policy after GA remains undesigned.

## Deviations from the index's outline

- 7.1 splits into 7.1a (Task 1, on `plan7-upstream`) and 7.1b (Tasks 2 to 4). The plan document lands separately; code branches use the guarded squash-ancestry procedure.
- 7.1 leaves `kit.toml` unchanged, because every template it does not list is managed and no 7.1 skill is optional or executable; 7.3 adds `rs-contribute` using main's current manifest name/API; Spec 3 PR 3.7 owns the rename.
- 7.1b changes the root guide's glossary bullet, and 7.2 one `init` message (PRO-160). Kit 0.2.0 seeds no `GLOSSARY.md` or `docs/adr/`, yet both root-guide seeds say that terms and decisions are there, and the trial's Worker searched for them. The bullet now says that a new project has neither until it records the first. `init`'s dirty-tree refusal names `rs-setup`, which a repository does not hold while `init` has written nothing, so it names the coding agent instead. The other names resolve when their skills ship: `rs-writing` and `rs-ponytail` in 7.1b, pinned by Task 3's test, and `rs-setup`, which `init`'s report names, in 7.2, pinned by Task 5's.
- 7.3 also changes devctl's `OPTIONAL_SKILLS` and the seeds' `[kit] optional` comment, because the loader and the parity test in `tests/devctl/test_devctl_settings.py` reject an optional skill outside that set.
- 7.4 sets the Kit version for GA (decision 3), because GA waits for Spec 3's build.
- 7.1a keeps `tests/test_skill_discovery.py`'s three test names with new bodies, because the `diff` step reads a deleted test as a removal.
- 7.4 holds a second task, Task 12, for Get started, the Guides and GA, so that Task 11 can start before the trials; it stays one PR.
- The proposal's guide "Add a TypeScript frontend" becomes "Set up a Python backend and a TypeScript frontend", because `init` refuses a repository that has a Kit lock and `sync` never adds a new-project seed, so no Kit command adds a stack later.
- 7.4 writes "Modes: Walk to Flight", because Spec 1 holds the Mode and the merge guard’s Mode rules. The proposal's guide "Turn on the merge guard in Claude Code" becomes "Turn on the guardrails in Claude Code, agy and Codex", because both follow-up wirings land before GA.
- 7.4 puts `GLOSSARY.md` in place of `README.md` in `docs.yml`'s path filters, because `.github/AGENTS.md` asks the filters to follow the site's inputs; the owner pushes that commit, because the Worker App cannot push a workflow change.
- The README shows the logo where the proposal keeps a regenerated banner, and 7.4 deletes `asset/public/banner.jpeg`: its image carries the retired "Ship more. Supervise less.", and the logo needs no new artwork. `docs/branding.md` keeps the banner prompt, less its tagline line, for a later banner.
- Task 9's existing-repository trial runs on the repository that the owner names (decision 2), not on hello-rapid-ship, which is now a new project with a Kit lock.

## Global Constraints

- Commands and exit codes follow the index's Conventions. `rapid-ship init [--stack NAME[=DIRECTORY]]...` is plan 6's form; after plan 6, `init` without `--stack` proposes the stacks it finds, writes nothing and exits 2. A test that calls `init` uses the CLI with `--stack python` or `--stack agnostic`, which is valid before and after plan 6.
- A Kit skill is one real directory, `rapid_ship/templates/common/.agents/skills/<name>/`, with a regular `SKILL.md` whose front matter `name` is the directory name and whose `description` is not empty. Exactly `rs-setup`, `rs-health` and `rs-contribute` set `disable-model-invocation: true`, each with a one-line, human-facing description; Spec 3's plan adds `rs-garden` and `rs-preflight`.
- Skills are Kit-managed here. Edit the template, then run `uv run rapid-ship sync --in-place`, and commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit `.agents/skills/rs-*` directly.
- Kit skill text is vendored into other projects. It never cites rapid-ship's specs, plans, ADRs, trials, Linear or a backlog ID, and never names this repository's own choices, such as Linear, subscription sign-ins or agy never reviewing. It states the behaviour itself.
- Spec 2 is descoped. No skill, page or task builds, names or links `rs-design`, `rs-breakdown`, `rs-lead`, `rs-work`, `rs-review`, a Lead, a Lead brief or Spec 2's document. The owner starts and manages their own Sessions, which follow the seeded root guide, its Pull requests section included, and the engineering skills. No Kit skill reviews.
- The comment rule: no comment, docstring, test name or message cites a plan, spec, section, ADR, PR, trial or rule ID. A test module's docstring starts `Offline:` and names what it simulates.
- No Kit skill template writes gitleaks's allow comment literally: the exceptions step counts it in every file, and this repository's template copies are not Kit-managed.
- Upstream: `mattpocock/skills` at `49dd158d1076134a641b33efb035946536778336`, MIT. Fetch a file with `gh api "repos/mattpocock/skills/contents/<path>?ref=49dd158d1076134a641b33efb035946536778336" -H 'Accept: application/vnd.github.raw' > <fixture>`, and check it with `git hash-object <fixture>`.
- Diff cap: 1,500 counted lines per PR. Not counted: `.md`, `.txt` and `.log` files, Kit-managed files, `.rapid-ship/kit.lock`, and each stack's lock file (`uv.lock`, `package-lock.json`). Counted: `rapid_ship/upstream.lock`, and fixtures and templates with any other suffix, such as `LICENSE` and the `.sh` script. The PR table gives the estimates. A PR that would exceed the cap splits at a task boundary.
- Agent identity is on here, and this repository is in Walk. Agents push with `./devctl as worker push` and run `gh` writes as `./devctl as <role> gh`. The Worker App can push a merge that only brings in workflow changes already on the base, but not a commit that edits `.github/workflows/`; the owner pushes those. In a Claude Code Session, G5 asks the owner before each edit of a Protected path: every `AGENTS.md`, `pyproject.toml`, `.rapid-ship/`, `.github/` and `.agents/skills/`, which agy's wiring widens to `.agents/`. agy runs no G5. `sync` writes the vendored skills through a shell command, which G5 does not see. In Walk the merge guard denies every agent merge, so the owner merges each plan 7 PR in GitHub's web interface.
- Each PR's last task runs these and records, in its own subsection of the Verification record, each command, its exit code and its summary line:
  - `uv run pytest -q`: exit 0, `<n> passed`, with no failure or error;
  - `./devctl check --tier fast`: exit 0;
  - `uv run rapid-ship status --strict`: exit 0, `<n> managed files unchanged.`;
  - `./devctl check --tier full --base <PR base> --pr-body <body file>`: exit 0, every step passed, `diff` noting `diff cap: <n> of 1,500 counted lines`, and `evidence` passed;
  - when docs change, `npm --prefix website run build`: exit 0, `[SUCCESS] Generated static files in "build".`

  Before 7.1a merges, 7.1b, 7.2 and 7.3 use `origin/plan7-upstream` as their PR base. 7.4 retains `main` as its PR and check base.
- Commit trailer: `Co-Authored-By: <the model that writes the commit>`, such as `Co-Authored-By: GPT-6.1 Sol <noreply@openai.com>`.

## Review Focus

1. **Setup reruns with Agent identity or an existing ruleset.** Read remote branches and rulesets before writes; hand denied writes to the owner. Re-read uncertain results before retry. Task 5's `test_rs_setup_states_each_guard` pins text only; Task 9 Step 5 tests reruns live.
2. **Sandbox in a linked worktree.** Keep local settings untracked and activate them in a new Session before verification. Task 5's guard test pins text only; Task 9 Step 4 exercises the Harness-specific settings and three commands.
3. **Health reads fail or block.** Report each unread source as unknown, never zero; propose no task from it. Task 7's `test_rs_health_reports_an_unread_source_as_unknown` pins text only; Task 9 Step 6 records a blocked read and recovery live.
4. **Contribute from the cached fork.** Give the owner the `git push` and `gh pr create` that the project's credentials cannot perform. Task 8's handoff test asserts both commands and their hook denials; it opens no real upstream PR.
5. **Adoption detects a uv workspace member.** Show the proposal, then use only the owner's confirmed root Python stack. Exclude `tools/devctl` from the workspace. Task 5's guard test pins text only; Task 9 Step 5 records detection, confirmation and checks.

## File Structure

`skills/` means `rapid_ship/templates/common/.agents/skills/`.

| File | PR | Responsibility |
| --- | --- | --- |
| `rapid_ship/upstream.lock` | 7.1a, 7.1b | Each forked file's upstream path, commit, blob and status |
| `tests/fixtures/upstream/mattpocock/skills/<commit>/` | 7.1a, 7.1b | Pristine upstream files, byte for byte |
| `tests/test_kit_upstream.py`, `tests/test_kit_skills.py` | 7.1a; 7.1b and 7.2 extend the second | The forks against upstream; the Kit's skills as templates, as `init` vendors them and as `rapid-ship` names them |
| `skills/rs-codebase-design/`, `skills/rs-writing-for-agents/` | 7.1a | Verbatim forks |
| `skills/rs-tdd/`, `skills/rs-diagnosing-bugs/`, `skills/rs-pr/` | 7.1b | Patched forks: rapid-ship's Evidence and skill names, in marked sections |
| `skills/rs-writing/`, `skills/rs-ponytail/` | 7.1b | This repository's writing and Ponytail guidance, made project-agnostic |
| The root-guide seeds' "Shared language and decisions" section | 7.1b | Where terms and decisions go, and the two skills to follow |
| `skills/rs-setup/` (`SKILL.md`, `ruleset.json`, `references/agent-identity.md`, `references/stylistic-options.md`, `references/known-failures.md`) | 7.2 | Setup, the ruleset it applies, and its references |
| `skills/rs-health/` (`SKILL.md`, `references/audit.md`, `references/proposed-task.md`) | 7.3 | The audit and the proposed tasks; `rs-garden` reads both references |
| `skills/rs-contribute/SKILL.md` | 7.3 | The optional skill that sends a Kit fix back |
| `docs/start/`, `docs/concepts/`, `docs/reference/`, `docs/guides/`, `website/src/pages/index.md`, `website/page-rules.js`, `website/src/theme/DocItem/Content/index.js` | 7.4 | Site pages, Home, the build's page rules and the status badge |

---

## PR 7.1a: the upstream lock (`plan7-upstream`, on `main`)

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
- Ruling: each fork carries upstream's `LICENSE` as `LICENSE.txt`, which the diff cap does not count. No fork copies an `agents/openai.yaml`, Codex's display metadata, because display metadata is outside this Kit contract.
- `tests/test_kit_upstream.py` holds its helpers. `blob_sha(data: bytes) -> str` is git's SHA-1 of `b"blob <len>\0" + data`. `restore_name(text: str, upstream_name: str) -> str` swaps the front matter's `name: rs-<upstream_name>` back. `unmarked_changes(upstream: str, fork: str) -> list[int]` runs `difflib.SequenceMatcher(None, upstream_lines, fork_lines, autojunk=False).get_opcodes()`. It returns the 1-based fork line of each non-equal opcode whose fork lines lie outside every marked section, and of each marker that does not pair. A removal has no fork lines; it counts as inside when a begin marker precedes its position and that section's end marker follows it.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_upstream.py`, docstring `Offline: the Kit's forked skills against pristine upstream fixtures.`:
  - `test_the_lock_names_one_upstream_commit`: every entry's `repository` is `mattpocock/skills` and its `commit` is `49dd158d1076134a641b33efb035946536778336`; `status` is `verbatim` or `patched`.
  - `test_each_fixture_is_the_pristine_upstream_file`: for each entry, `blob_sha` of `tests/fixtures/upstream/<repository>/<commit>/<upstream>` equals `blob`.
  - `test_verbatim_files_equal_their_upstream_file`: for each verbatim entry, `blob_sha(restore_name(fork_text, upstream_name).encode())` equals `blob` for a `SKILL.md`; other files use their raw bytes. `upstream_name` is the parent directory name of the entry’s `upstream` path, such as `tdd`.
  - `test_patched_files_differ_only_inside_marked_sections`: for each patched entry, `unmarked_changes(fixture_text, restore_name(fork_text, upstream_name)) == []`, the fork holds at least one begin marker, and its blob differs from `blob`.
  - `test_every_file_of_a_forked_skill_is_in_the_lock`: within each skill directory that the lock names, the template's files equal the lock's paths.
  - `test_unmarked_changes_reports_only_changes_outside_a_section`, parametrized over literal texts: an edited line outside the markers gives its line number; the same edit inside them gives `[]`; an upstream line removed between markers gives `[]`; one removed outside them gives the line before the removal; a begin marker with no end gives the begin marker's line; a stray end marker gives its line.
  - `test_restore_name_rejects_a_name_without_the_rs_prefix`: `restore_name("---\nname: tdd\n---\n", "tdd")` raises `ValueError`, naming the expected `rs-tdd`.

  `tests/test_kit_skills.py`, docstring `Offline: the Kit's skills as the templates hold them and as init vendors them.`, with `USER_INVOKED = frozenset({"rs-setup", "rs-health", "rs-contribute"})`, which Spec 3's plan extends:
  - `test_only_the_user_invoked_kit_skills_disable_model_invocation`: a Kit skill template's front matter holds `disable-model-invocation: true` exactly when its name is in `USER_INVOKED`. No upstream front matter sets the key, so it passes at once; it guards 7.2 and 7.3.

  Rewrite `tests/test_skill_discovery.py` under its three names, with docstring `Offline: skill links and discovery aliases in this checkout.` `KIT_SKILLS` holds the names of `rapid_ship/templates/common/.agents/skills/*/SKILL.md`, less each of `load_manifest().optional_skills` that `read_optional_skills(REPOSITORY)` does not name. `OWN_SKILLS = ("rapid-ship-engineering",)` until Task 4 deletes it.
  - `test_bundled_skill_dependencies_resolve_inside_package`: every Markdown link in each Kit skill template resolves to a file inside that skill's own directory.
  - `test_checkout_discovery_resolves_to_packaged_skill`, over `KIT_SKILLS`: `.agents/skills/<skill>` is a directory, not a symlink, with a regular `SKILL.md`, and `.claude/skills/<skill>` is a symlink to `../../.agents/skills/<skill>`.
  - `test_checkout_discovers_exactly_the_packaged_skills`: each surface's entries, hidden names aside, equal `KIT_SKILLS` plus `OWN_SKILLS`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_upstream.py tests/test_skill_discovery.py -q`; expected FAIL with `FileNotFoundError` for `rapid_ship/upstream.lock`.
- [ ] **Step 3: fetch the fixtures** with the Global Constraints command, for `LICENSE` and this task's five other files, and check each with `git hash-object` against the table.
- [ ] **Step 4: write the forks and the lock.** Copy each fixture to its fork path and `LICENSE` to each `LICENSE.txt`; change only each `SKILL.md`'s `name`. Add the seven rows. `git add` the templates, then run `uv run rapid-ship sync --in-place`.
- [ ] **Step 5: run** `uv run pytest tests/test_kit_upstream.py tests/test_skill_discovery.py tests/test_kit_skills.py -q`; expected exit 0, `<n> passed`. Then `uv run rapid-ship status --strict` and `./devctl check --tier fast`; both exit 0.
- [ ] **Step 6: commit** `feat: fork rs-codebase-design and rs-writing-for-agents, pinned in an upstream lock`.
- [ ] **Step 7: verify.** Run the five checks with `--base main` and record them. Evidence: `Not covered: the patched forks, rs-writing and rs-ponytail, which 7.1b adds`. Commit `docs: record PR 7.1a's verification`. 7.1b, 7.2 and 7.3 branch from this head. 7.4 starts independently from `main` and keeps `main` as its PR and check base.

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
  - `rs-pr/SKILL.md`: one section spans the whole template block, fences included, so no marker lands in a body copied from it. The copyable block contains neither `Removed tests:` nor `Over the diff cap:`; prose explains when to add them. The template’s `## Evidence` holds ``- `<command>`: <exit code and the summary line it printed>``, upstream's Before and After lines, and `Not covered: <what the commands do not show>`. A second section in `### Evidence` says to list each command as that item. It adds `Removed tests:` with one ``- `<path>::<test>`: <reason>`` item per removed test, and `Over the diff cap: <reason>` only after the owner accepted the overage before the work. CI's `evidence` and `diff` steps fail a body without them. The front matter's HumanLayer credit and `CREDITS.md` stay verbatim.

- [ ] **Step 1: write the failing tests.** Add the ten rows to the lock; Task 1's tests then fail until the forks exist. In `tests/devctl/test_devctl_evidence_step.py`:
  - `test_the_rs_pr_template_passes_the_evidence_step`: the lines inside the first fenced `markdown` block of `rapid_ship/templates/common/.agents/skills/rs-pr/SKILL.md`, as the PR body, give `EvidenceStep().run(context).status == "passed"`, `over_cap_reason(body) is None`, and `removed_test_declarations(body) == ({}, [])`. Import both parsers from `devctl.check.evidence`.
  - `test_the_rs_pr_template_without_not_covered_fails`: the same body less its `Not covered:` line fails, and its details hold `Evidence: add a line starting 'Not covered:' that names what the commands do not show`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_upstream.py tests/devctl/test_devctl_evidence_step.py -q`; expected FAIL on the missing forks.
- [ ] **Step 3: fetch** the seven new upstream files and check each blob.
- [ ] **Step 4: write the forks,** copying each fixture and adding only the patches above; sync.
- [ ] **Step 5: verify.** Run `uv run pytest tests/test_kit_upstream.py tests/devctl/test_devctl_evidence_step.py tests/test_skill_discovery.py -q`; expected exit 0, `<n> passed`. Run `uv run rapid-ship status --strict`; expected exit 0, `<n> managed files unchanged.` Run `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 6: commit** `feat: fork rs-tdd, rs-diagnosing-bugs and rs-pr with rapid-ship's Evidence`.

### Task 3: `rs-writing`, `rs-ponytail` and the root guide's pointers

**Files:**
- Create: `skills/rs-writing/` (`SKILL.md`, `TECHNICAL-ENGLISH-LICENSE.txt`, `ASD-STE100-SKILL-LICENSE.txt`), `skills/rs-ponytail/` (`SKILL.md`, `PONYTAIL-LICENSE.txt`)
- Modify: `tests/test_kit_skills.py`, `tests/test_kit_contents.py`; the root-guide seeds `rapid_ship/templates/common/AGENTS.md` and `rapid_ship/templates/python/AGENTS.md`, or, after plan 6's 6.1b, the one template that then holds the root guide's text; through `sync`: the vendored copies, links and lock

**Interfaces:**
- `rs-writing/SKILL.md`: `name: rs-writing`; `description: Use when writing or editing commits, PRs, reviews, documentation, code comments, agent reports or instructions.` Its body is `rapid_ship/skills/rapid-ship-engineering/references/writing.md`, made project-agnostic: the code-comment row says to follow the comment Rules in the root `AGENTS.md`. It ends with the sources paragraph of `SOURCES.md`'s "Technical writing" section, with its pinned links and the two licence files.
- `rs-ponytail/SKILL.md`: `name: rs-ponytail`; `description: Use before implementing or reviewing a change, to build only what the task needs while keeping required behaviour, validation and checks.` Its body is `references/ponytail.md`, whose comment bullet becomes the comment rule: comment only a contract, rationale, invariant or external constraint that the code does not express. It keeps its Ponytail v5.1.0 credit and licence.
- Neither skill names rapid-ship, this repository or a plan.
- The root guide's "Shared language and decisions" section holds exactly these two bullets, in every seed that holds the root guide's text:

```markdown
- Record the project's terms in `GLOSSARY.md` and its decisions in `docs/adr/`. A new project has neither until it records the first.
- Follow the `rs-writing` skill for prose and the `rs-ponytail` skill for building only what is needed.
```

- [ ] **Step 1: write the failing tests.**
  - In `tests/test_kit_skills.py`, `test_the_root_guides_name_the_writing_and_ponytail_skills`: for each root-guide seed, assert it names both `rs-writing` and `rs-ponytail`, and both have a template `SKILL.md`. Scope this intermediate check to those two names; Task 12 expands it once all named skills ship.

  - In `tests/test_kit_contents.py`, `test_root_guide_says_where_terms_and_decisions_go`, over the stacks that `test_root_guide_skeleton_has_its_headings_rules_links_and_pointers` covers: the bullets of the rendered guide's `## Shared language and decisions` section equal the two lines above. `POINTERS` stays as it is.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_skills.py tests/test_kit_contents.py -q`; expected failure on missing `rs-ponytail`, `rs-writing` and the glossary bullet.
- [ ] **Step 3: write both skills and the bullet**; sync.
- [ ] **Step 4: verify.** Run `uv run pytest tests/test_kit_skills.py tests/test_kit_contents.py tests/test_skill_discovery.py -q`; expected exit 0, `<n> passed`. Run `uv run rapid-ship status --strict`; expected exit 0, `<n> managed files unchanged.` Run `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 5: commit** `feat: add rs-writing and rs-ponytail, and say where a new project's terms and decisions go`.

### Task 4: Retire `rapid-ship-engineering`, documents, and PR 7.1b's verification

**Files:**
- Delete: `rapid_ship/skills/`, with its `AGENTS.md`; `.agents/skills/rapid-ship-engineering`; `.claude/skills/rapid-ship-engineering`
- Modify: `tests/test_skill_discovery.py` (`OWN_SKILLS` goes), `tests/test_kit_skills.py`; the root `AGENTS.md`, `rapid_ship/AGENTS.md`, `.agents/AGENTS.md`, `.claude/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, `pyproject.toml` (the sdist comment on checkout skill aliases), `docs/credits.md`, `docs/getting-started.md`, `ARCHITECTURE.md`, Spec 1's section 2 item 3, section 4's skeleton item 6 and status line, the index's plan 7 row, this plan's Verification record

**Interfaces:**
- The root `AGENTS.md`: Writing reads `.agents/skills/rs-writing/SKILL.md`. Development reads `.agents/skills/rs-ponytail/SKILL.md` before coding or review, and names `rs-tdd`, `rs-diagnosing-bugs`, `rs-codebase-design` and `rs-pr`. The source-map row drops "and the engineering skill". No Kit skill replaces the clarify and review modes: reviews follow the guide's Pull requests section, `rs-ponytail` and the Harness's own review.
- `docs/credits.md`: one row per forked skill, with its upstream link at `49dd158`, the HumanLayer credit for `rs-pr`, and the Ponytail, technical-english and asd-ste100 sources of `rs-ponytail` and `rs-writing`. It links `rapid_ship/upstream.lock` on GitHub instead of the deleted `SOURCES.md`.
- Spec 1 section 4's skeleton item 6 says that the pointer to `GLOSSARY.md` and `docs/adr/` tells a new project where to record them.

- [ ] **Step 1: write the test.** In `tests/test_kit_skills.py`, `test_every_kit_skill_has_its_named_skill_md_and_claude_link_in_a_new_project`: in `git_repo`, after `monkeypatch.chdir`, `main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0`. Then `skill_errors`, `skill_file_errors` and `skill_alias_errors` over the tracked files are each `[]`, and the entries of `.claude/skills/` are the Kit's non-optional skills.
- [ ] **Step 2: retire.** Run `git rm -r rapid_ship/skills .agents/skills/rapid-ship-engineering .claude/skills/rapid-ship-engineering`, and delete `OWN_SKILLS`. Run `uv run pytest tests/test_kit_skills.py tests/test_skill_discovery.py tests/test_kit_upstream.py -q`; expected exit 0, `<n> passed`.
- [ ] **Step 3: documents.** After normally merging main with PRO-166, update the files above. Replace both retired-skill prompts in `docs/getting-started.md` with the Harness’s own review and `rs-tdd`. `ARCHITECTURE.md`'s "Engineering skill" row becomes the Kit skills, and its templates paragraph drops "the Kit has no skills yet". Commit `refactor: retire rapid-ship-engineering for the Kit's skills`.
- [ ] **Step 4: verify.** Run the five checks with the PR's base, and `uv run rapid-ship sync --in-place`, which prints `Kit is current; nothing to sync.` The PR removes no test. Its body's Evidence lists the checks, with `Not covered: the skills' behaviour in a Session, which Task 9 exercises`. Commit `docs: record PR 7.1b's verification`.

## PR 7.2: `rs-setup` (`plan7-setup`, on 7.1a's head)

### Task 5: `rs-setup`, its `ruleset.json`, and the skill `init` names

**Files:**
- Create: `skills/rs-setup/SKILL.md`, `skills/rs-setup/ruleset.json`, `tests/devctl/test_devctl_ruleset_json.py`
- Modify: `rapid_ship/kit/init.py` (the dirty-tree refusal's last line), `tests/test_kit_init.py`, `tests/test_kit_skills.py`; through `sync`: the vendored copies, link and lock

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

- `SKILL.md`: `name: rs-setup`; `description: Set up a new repository, or adopt an existing one, after rapid-ship init vendored the Kit.`; `disable-model-invocation: true`. Its rules come first: guided rectifying, no silent repository-wide rewrites, and the owner’s yes before outside writes or Protected settings changes. Preserve the first failure’s own output. State a proposed fix before applying it; never increase permissions to evade a refusal. Spec 1 section 8's 15 steps follow, numbered as Spec 1 numbers them: 1 New or existing, 2 Documents, 3 Patterns, 4 Checks, 5 Harness guardrails, 6 Sandbox, 7 GitHub, 8 Agent identity, 9 Mode, 10 Metrics, 11 Optional skills, 12 Doctor, 13 Setup PR, 14 Tool-settings PR, 15 Next. No step writes a tracker setting; the Kit records none. Rulings that the spec leaves to the skill:
  - **Metrics (step 10):** one line until Spec 3's plan writes the step: "This Kit version records no metrics settings; go on to step 11."
  - **Running `rapid-ship`:** `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<kit_version> rapid-ship <command>`, with `kit_version` from `.rapid-ship/kit.lock`. When that tag does not exist, the skill asks the owner for the checkout that `init` ran from. It runs `sync` only with `--in-place`.
  - **Stacks:** it reads each `[[stack]]` table's `name` and `directory` in `.rapid-ship/project.toml`, which `init` wrote with the stacks the owner confirmed, and never asks again.
  - **Documents, existing project:** where the project keeps its terms or decisions in files other than `GLOSSARY.md` and `docs/adr/`, the merged root guide's bullet names those files.
  - **Patterns:** a Pattern offered as a task takes the shape that `.agents/skills/rs-health/references/proposed-task.md` gives, named as a code span, because a skill's links resolve only inside its own directory. It writes the tasks the owner picks as `rs-health` does (Task 7).
  - **Checks, existing project:** it adds `exclude = ["tools/devctl"]` under the root `pyproject.toml`'s `[tool.uv.workspace]` when its `members` cover it, and, only if decision 1 is approved and Spec 1 §8 step 4.3 is updated in 7.2, each missing check tool with that decision’s minimal settings. Until then, leave the project’s own tool settings unchanged and record the missing tool as blocked. It writes the dead-code settings into each Python stack's own `pyproject.toml`. The Setup reasons are exact: `Existed at Setup on <date>` with `Remove when this code next changes` for a suppression, and `Delete it, or replace this reason with what uses it` for marked dead code.
  - **Existing TypeScript dead code:** for each knip finding, it fixes the code or marks it: a `/** @public */` tag with its `rs-exception` marker on the reported export, or an item under the matching top-level `ignore*` key of `knip.jsonc`, alone on its line with its marker. Each mark gets an entry with the dead-code Setup reasons, and each TypeScript suppression that the `exceptions` step reports gets its marker and the suppression's Setup reasons.
  - **Harness guardrails (step 5):** it names Claude Code, agy once PRO-155/172 is merged and trialed, and Codex once PRO-142 is merged and trialed. Codex is required before GA. agy and Codex omit G5; their hooks do not ask before Protected edits. Where `init` skipped `.claude/settings.json`, `.agents/hooks.json` or `.codex/hooks.json`, merge the Kit’s entries. For Codex the owner trusts the project and reviews its hooks in `/hooks`; preserve `/.codex/` in CODEOWNERS. Other unwired Harnesses lack these guardrails.
  - **Sandbox (step 6):** offer it; wait for the owner's yes. PRO-156 with PRO-157 owns the pending spec recipe and restart fix; use its merged behavior rather than duplicate that fix.
    - Claude Code alone uses `.claude/settings.local.json` and its sandbox JSON keys. Run `git check-ignore -q .claude/settings.local.json`; if needed, add the path to the file named by `git rev-parse --git-path info/exclude`. Never assume `.git` is a directory.
    - Claude Code's `network.allowedDomains` includes `github.com`, `api.github.com`, `codeload.github.com`, `objects.githubusercontent.com`, `pypi.org` and `files.pythonhosted.org`; add `registry.npmjs.org` for TypeScript. `filesystem.allowWrite` includes `~/.cache/uv` and `~/.local/share/uv/tools`; plan 6 Task 13 validates npm's additional `~/.npm` need. `excludedCommands` includes `gh *` and, until PRO-156 merges and its trial removes the need, `./devctl as *`.
    - Codex uses `sandbox_mode` in the owner's uncommitted Codex configuration. agy uses its terminal sandbox setting, with network allowed first. Scope each setting to that Harness; never copy Claude sandbox JSON into Codex or agy settings.
    - Restart or start a new sandbox Session before testing `./devctl --version`, `./devctl check --tier fast` and `gh auth status`. Record each exit code and actual result. A blocked command is not a pass; use the known-failures reference without increasing permissions.
  - **GitHub (step 7):** plan 6 Task 14 owns the pending PRO-161 spec update for bootstrap order. First read `gh api repos/<owner>/<name>/branches/<default>` and the rulesets. On a missing remote default branch, stop for the owner to push it from their own terminal before enabling the ruleset. Re-read the branch after that push. Agents cannot push the default branch. Label guarded Owner terminal commands separately from agent command fences. Each outside write follows the owner's yes:
    - `gh api 'repos/<owner>/<name>/rulesets?targets=branch'` first;
    - with no ruleset named `rapid-ship`, `gh api --method POST repos/<owner>/<name>/rulesets --input .agents/skills/rs-setup/ruleset.json`; with one, `gh api --method PUT repos/<owner>/<name>/rulesets/<id> --input .agents/skills/rs-setup/ruleset.json`;
    - `gh api --method PATCH repos/<owner>/<name> -F delete_branch_on_merge=true`;
    - for a public repository, `gh api --method PUT repos/<owner>/<name>/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors`.

    With `[github] repository` still empty, as for a repository that step 7.1 created after `init`, it records `owner/name` there before step 8. With Agent identity on, G8 denies these writes and G7 the agent's push. The skill then gives the owner each exact command for a terminal, and agents' own GitHub writes run through `./devctl as`. A 403 that names the plan limit is the GitHub Free private gap; the skill records it, with the explanation that the merge guard is the enforcement there.
  - **Mode (step 9):** it quotes the merge guard's Walk denial, advises at most 3 agents at once in Walk, and says that the owner widens the Mode in one Protected PR that sets `every_pr = false` and changes CODEOWNERS.
  - **Setup PR (step 13):** the body ends with the Evidence section that `devctl check` requires. It adds `Over the diff cap: dead code marked at Setup` only when the marks pass the cap.
  - **Next (step 15):** for an existing repository it offers `rs-health`. It then says that the Kit is ready: the owner starts and manages their own Sessions, which follow AGENTS.md, its Pull requests section included, and the engineering skills, while `./devctl check`, the guardrails and the merge guard hold the bar. Every Kit Markdown file names only skills supplied by the current Kit, except the `rs-exception` marker. Invoke only installed skills; optional offers may name a supplied template. Until their skills ship, say “a gardening pass” or “a readiness review”; step 9 follows this rule too.
- `rapid_ship/kit/init.py`'s dirty-tree refusal ends `Your coding agent can help commit or stash them; then run rapid-ship init again.`

- [ ] **Step 1: write the failing tests.** `tests/devctl/test_devctl_ruleset_json.py`, docstring `Offline: rs-setup's ruleset.json against doctor's ruleset rules and a ruleset that GitHub returned, and the commands rs-setup states.`:
  - `test_rs_setups_ruleset_passes_doctor_in_every_mode`, over `every_pr` and `agent_identity`, each `True` and `False`: `ruleset_problems([ruleset], "main", every_pr=..., agent_identity=...) == []`.
  - `test_the_ruleset_is_the_body_github_accepted`: it equals the recorded fixture less `id`, `source` and `source_type`, and less `require_extra_approval_for_unattributed_changes` and `required_reviewers`, which GitHub adds with their defaults.
  - `test_rs_setup_applies_the_settings_doctor_checks`: `SKILL.md` contains `--input .agents/skills/rs-setup/ruleset.json`, `-F delete_branch_on_merge=true` and `-f approval_policy=all_external_contributors`.
  - `test_rs_setup_states_each_guard`: the text of `rs-setup/**/*.md` contains `rulesets?targets=branch`, `--method PUT repos/<owner>/<name>/rulesets/<id>`, `git check-ignore -q .claude/settings.local.json`, `git rev-parse --git-path info/exclude`, `gh auth status`, `exclude = ["tools/devctl"]`, `.agents/hooks.json`, `.codex/hooks.json`, `/hooks`, `sandbox_mode`, `./devctl as`, the restart instruction, all six base domains, and both uv write paths. These assertions check text only; Task 9 checks behavior.

  In `tests/test_kit_skills.py`, `test_each_skill_the_rapid_ship_cli_names_ships_in_the_kit`: every word that `re.findall(r"\brs-[a-z0-9-]+", text)` finds in `rapid_ship/*.py` and `rapid_ship/kit/*.py`, other than `rs-exception`, is a Kit skill template with a `SKILL.md`.

  In `tests/test_kit_init.py`, `test_a_dirty_tree_is_listed_up_to_20_paths_and_nothing_is_written` keeps its name; its body asserts that the refusal's last line holds `coding agent` and `commit or stash`, and no `rs-` name.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ruleset_json.py tests/test_kit_skills.py tests/test_kit_init.py -q`; expected FAIL with `FileNotFoundError`, on `rs-setup` as a name with no template, and on the refusal's `rs-setup`.
- [ ] **Step 3: write** `ruleset.json`, `SKILL.md` and the refusal's line; sync.
- [ ] **Step 4: verify.** Run `uv run pytest tests/devctl/test_devctl_ruleset_json.py tests/test_kit_skills.py tests/test_kit_init.py tests/test_skill_discovery.py -q`; expected exit 0, `<n> passed`. Run `uv run rapid-ship status --strict`; expected exit 0, `<n> managed files unchanged.` Run `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 5: commit** `feat: add rs-setup with the ruleset it applies`.

### Task 6: Setup references, quotation drift, and PR 7.2's verification

**Files:**
- Create: `skills/rs-setup/references/agent-identity.md`, `stylistic-options.md`, `known-failures.md`
- Modify: `skills/rs-setup/SKILL.md` (reference links and quoted values that reconciliation finds changed), `tests/devctl/test_devctl_ruleset_json.py`, `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, Spec 1 section 3 step 1 (the refusal no longer names `rs-setup`) and section 8 step 4.3 only if owner decision 1 is approved; section 10 waits for Task 9’s repository confirmation and record PR, the index's plan 7 row, this plan's Verification record

**Interfaces:**
- `agent-identity.md`: Spec 1 section 8 step 8.1's table, word for word; the four things that Agent identity buys and what is lost without it; its cost; step 8.3's team key model; and step 8.6's consequences without it. It links nothing outside the skill.
- `stylistic-options.md`: what the tool-settings PR leaves out, by tool. Ruff: `line-length`, `indent-width`, `[tool.ruff.format]` (`quote-style`, `indent-style`, `line-ending`, `skip-magic-trailing-comma`, `docstring-code-format`, `docstring-code-line-length`), and the rules that only enforce them (`E501`, `Q`, `COM`). Prettier: every option. ESLint: `@stylistic/*` and the core formatting rules that Prettier replaces. mypy, pytest, import-linter, `tsconfig.json`, Vitest and knip have none. The rules to offer are the details of doctor's floor items, plus Ruff's `ASYNC` and `FAST` where the project imports asyncio or FastAPI.
- `known-failures.md`: one table per step, with the output the owner sees, its cause and the fix the skill offers. Each row quotes doctor's and devctl's messages as `main` holds them. It needs at least these rows:
  - Init: `init` exiting 1 because a managed Kit path already exists, which writes nothing; `init` without `--stack` printing its proposal and exiting 2.
  - Checks: gitleaks missing or not 8.30.1; `uv sync` without network; a `members` glob that covers `tools/devctl`; a blocked tool step; hooks in `.git/hooks` that `core.hooksPath` would stop running; project skills whose `.claude/skills` entries are copies, not links, which the `map` step fails.
  - Guardrails: a `.claude/settings.json` that lacks the Kit's hooks; a `.agents/hooks.json` that lacks the Kit's hook; an agy hook that fails before devctl runs, which blocks every wired agy call; missing Codex wiring, its doctor item and the owner’s `/hooks` trust review. PRO-172’s merged fix is canonical.
  - Sandbox: uv's `Failed to initialize cache at`; `uv tool run` refused a write under `~/.local/share/uv/tools`; gh's `x509: OSStatus -26276`; an exclusion that holds only for a line that is exactly that command; devctl's GitHub request failing behind the sandbox's proxy, while `main` still fails there; a `settings.local.json` that git does not ignore; a linked worktree whose `.git` is a file, resolved through `git rev-parse --git-path info/exclude`; an old Session that has not activated new settings.
  - GitHub: a ruleset 403 on GitHub Free; a default branch other than `main` or `master`; an existing `rapid-ship` ruleset; G8 denying a `gh api` write with Agent identity on; `gh` signed in as another account; `Repository rule violations` when the default branch was not bootstrapped before the ruleset; doctor’s CODEOWNERS item reporting an owner without write access or a team that is not visible (PRO-147/148).
  - Mode: the merge guard's Walk denial, and its Flight denial of a PR that declares a removed behavioural test or an overage.
  - Agent identity, doctor and the PRs: `rapid-ship app` exiting 1 for each of Spec 1 section 3's causes; `claude` not on `PATH` for `--skills`; a skill that the probe misses; G7 denying the push; the Worker App refused a workflow push; a `sync` conflict; linter findings past the cap in the tool-settings PR.
  - TypeScript: the rows of "Where 7.2 depends on plan 6".

- [ ] **Step 1: write the failing text-contract test.** Add `test_known_failures_quote_what_the_kit_prints` to `tests/devctl/test_devctl_ruleset_json.py`. Import `G7` and `G8` from `devctl.hook`. Assert `G7`, `G8.partition("{arguments}")[0]`, `merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #`, and `, so the owner merges it` occur in `known-failures.md`. Also import `devctl.merge_guard` and read its actual source with `inspect.getsource(merge_guard)`. Assert both merge-denial fragments occur in that source as well as `known-failures.md`. A change to either source message or its quotation must fail the test. This tests quotation drift, not live behavior.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ruleset_json.py -q`; expected failure because `known-failures.md` does not exist.
- [ ] **Step 3: write the references and reconcile.** Task 5 owns every `SKILL.md` section. Link the three references and correct only drifted quotations there. Normally merge `origin/main` after PRO-166, PRO-155, PRO-147/148 and available wiring/sandbox fixes land. Map every dependency row to the exact source file/constant or literal fragment; preserve conditional wording for unmerged work. Quote the merged messages, then sync. Never merge an unmerged dependency branch or assign its spec edits here.
- [ ] **Step 4: verify references.** Run `uv run pytest tests/test_skill_discovery.py tests/devctl/test_devctl_ruleset_json.py -q`; expected exit 0, `<n> passed`. Run `uv run rapid-ship status --strict`; expected exit 0, `<n> managed files unchanged.` Run `./devctl check --tier fast`; expected exit 0. Commit `feat: add rs-setup references and pin their error quotations`.
- [ ] **Step 5: documents and verification.** Describe Setup in the listed files. If decision 1 is approved, update Spec 1 §8 step 4.3 in this future code PR; otherwise retain its current constraint. Run the Global Constraints checks with the PR's base and record actual output. Evidence names all unmerged wiring or plan-6 quotations as Not covered until Task 9 checks them. Commit `docs: record PR 7.2 verification`.

## PR 7.3: `rs-health` and `rs-contribute` (`plan7-health`, on 7.1a's head)

### Task 7: `rs-health`, the shared audit and the task shape

**Prerequisites:** merged PRO-166 for hook settings and the golden-paths library (PRO-167) for current audit requirements.

**Files:**
- Create: `skills/rs-health/SKILL.md`, `skills/rs-health/references/audit.md`, `skills/rs-health/references/proposed-task.md`, `tests/test_kit_health_and_contribute.py`
- Modify: through `sync`: the vendored copies, link and lock

**Interfaces:**
- Consumes: `devctl.hook.decide(call, root, settings, branches) -> tuple[Decision, str]`, whose `branches` is a `Callable[[], LocalBranches]`; `devctl.hook_protocols.ToolCall` and `HookSettings`; `devctl.merge_guard.LocalBranches`.
- `SKILL.md`: `name: rs-health`; `description: Audit a repository against rapid-ship's standards and return proposed tasks.`; `disable-model-invocation: true`. It never edits the repository. After the golden-paths library (PRO-167) merges, read the sources in Spec 1 section 9 with its obsolete feature-map reads removed, through `./devctl doctor`, `./devctl check`, `gh run list`, `gh pr list --state merged`, `gh pr view`, and `GET` REST reads of each PR's reviews and review comments. Every command sits in a fenced `sh` block, with placeholders as shell variables such as `$REPO`. It runs `references/audit.md` over the whole repository and returns proposed tasks, grouped by area, each in the shape of `references/proposed-task.md`. A failed or blocked read is unknown, never zero; an empty successful read is distinct. Name each unread source and propose no task from it. The owner picks which to keep. It states each write, then writes the picked tasks to the tracker that the owner's Harness reaches, for example through an MCP server, or as GitHub issues. With Agent identity on, it opens an issue with `./devctl as worker gh issue create`; with it off, with the same command less `./devctl as worker`, which it gives in prose. When the Harness reaches more than one tracker, it asks which. When it reaches none, it leaves the tasks in the conversation. It records no tracker setting.
- `proposed-task.md`: one proposed task is one PR within devctl's diff cap of 1,500 counted lines. It holds a title that states the outcome; the finding, with its file:line or command output; its rung; acceptance criteria; a test plan; and the tasks it waits on. A task from a Pattern finding cites the Pattern's Lessons. In a tracker, each task is one record, such as one issue, and "waits on" links the records. Spec 3 reuses this file and adds its own fields. Cross-skill references use code spans, not Markdown links outside the skill.
- `audit.md`: `rs-health` runs it over the whole repository; Spec 3 reuses it over a changed range. Each item says how it applies to a range. Follow the shared-reference contract that Spec 3 adds to the index; do not define a second reference pair. It holds:
  - Spec 1 section 9's audit by rung, naming "each stack's floor items" where the spec names the Python floor;
  - Spec 3 section 10's drift table and base rule, with feature-map drift removed after the golden-paths library (PRO-167); rs-health may propose the first golden paths at adoption without defining their format, location, a command or a check;
  - the starter Patterns, each finding citing the Pattern's Lessons;
  - the Setup reasons of Task 5, which mark entries to remove;
  - what `devctl check` already fails on, which the audit does not repeat;
  - a citation of file:line or command output for every finding, which becomes the task's finding.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_health_and_contribute.py`, docstring `Offline: rs-health's references and commands, and rs-contribute's opt-in, in scratch repositories.`:
  - `test_the_shared_audit_and_proposed_task_references_resolve`: `rapid_ship/templates/common/.agents/skills/rs-health/references/audit.md` and `references/proposed-task.md` exist, and `rs-health/SKILL.md` links both.
  - `test_rs_health_runs_no_command_the_guardrails_deny`: take every fenced `sh` block in `rs-health/SKILL.md` and its references, join each line that ends in `\` with the next, and drop comments and blank lines. `decide` answers each command `(None, "")` for `ToolCall(shell=command, edits=(), cwd=tmp_path)` with root `tmp_path`, `HookSettings(agent_identity=True, protected=(), repository="o/r", reviewer_app_slug="o-reviewer", every_pr=True, unit_tests=())` and branches `lambda: LocalBranches(frozenset({"main"}), "feature")`. At least five commands are checked, one of them `./devctl as worker gh issue create`.
  - `test_rs_health_reports_an_unread_source_as_unknown`: assert the skill states that failed and blocked reads are unknown, not zero; names each unread source; and prohibits proposing a task from it. Include examples of unavailable GitHub authentication, missing gitleaks and no merged PRs, distinguishing an empty successful read from an unread one. This is a text-only contract; Task 9 Step 6 tests a live blocked read and recovery.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_health_and_contribute.py -q`; expected FAIL on the missing references.
- [ ] **Step 3: write** the three files; sync.
- [ ] **Step 4: verify.** Run `uv run pytest tests/test_kit_health_and_contribute.py tests/test_kit_skills.py tests/test_skill_discovery.py -q`; expected exit 0, `<n> passed`. Run `uv run rapid-ship status --strict`; expected exit 0, `<n> managed files unchanged.` Run `./devctl check --tier fast`; expected exit 0.
- [ ] **Step 5: commit** `feat: add rs-health with the audit and task shape it shares with rs-garden`.

### Task 8: `rs-contribute`, the optional skill, and PR 7.3's verification

**Files:**
- Create: `skills/rs-contribute/SKILL.md`
- Modify: `rapid_ship/templates/kit.toml` (add `rs-contribute` under the current optional-entry key; do not rename it); devctl's template `settings.py` (`OPTIONAL_SKILLS: frozenset[str] = frozenset({"rs-contribute"})`); the `[kit] optional` comment, to `opt-in Kit skills: rs-contribute`, in every `.rapid-ship/project.toml` seed under `rapid_ship/templates/` and, edited in place, in this repository's `.rapid-ship/project.toml`; the comment in `test_kit_optional_names_only_the_kits_optional_skills` that says this Kit offers none; `tests/test_kit_health_and_contribute.py`. Documents: `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md`, the index's plan 7 row, this plan's Verification record.

**Interfaces:**
- Consume `load_manifest().optional_skills` and `read_optional_skills` until Spec 3 PR 3.7 renames the key and reader/property. Use the names on main when this PR lands; whichever PR lands second updates shared callers and fixtures. Never independently rename.
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
  - `test_rs_contribute_installs_only_when_opted_in`: after `main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0`, `.agents/skills/rs-contribute` does not exist. Replace the seed’s `optional = []` line with `optional = ["rs-contribute"]` under `[kit]` in `.rapid-ship/project.toml`, commit, and run `main(["sync", "--in-place"]) == 0`. Then `.agents/skills/rs-contribute/SKILL.md` exists; `.claude/skills/rs-contribute` links to `../../.agents/skills/rs-contribute`; the lock records both as managed; devctl's `load_project` reads `("rs-contribute",)`; and `skill_errors` is `[]`.
  - `test_rs_contribute_hands_the_owner_its_writes`: `rs-contribute/SKILL.md` contains `gh repo fork proxy-hatch/rapid-ship --clone=false`, `gh search issues`, `gh search prs`, `--repo proxy-hatch/rapid-ship --state open`, `rapid-ship sync --revert`, `rapid_ship/templates/AGENTS.md`, `git push` and `gh pr create --repo proxy-hatch/rapid-ship`. Assert `decide` denies both owner commands with `ToolCall(shell=command, edits=(), cwd=tmp_path)`, root `tmp_path`, `HookSettings(agent_identity=True, protected=(), repository="proxy-hatch/rapid-ship", reviewer_app_slug="r", every_pr=True, unit_tests=())`, and `lambda: LocalBranches(frozenset({"main"}), "feature")`. The text labels them Owner terminal commands; the test never sends them.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_health_and_contribute.py -q`; expected failure with `unknown optional Kit skill 'rs-contribute'` and missing `SKILL.md`.
- [ ] **Step 3: implement** the skill, `kit.toml`, `OPTIONAL_SKILLS` and the comments; sync.
- [ ] **Step 4: verify.** Run `uv run pytest tests/test_kit_health_and_contribute.py tests/devctl/test_devctl_settings.py tests/test_kit_seed_keys.py tests/test_kit_contents.py tests/test_kit_skills.py -q`; expected exit 0, `<n> passed`. Run `uv run rapid-ship status --strict`; expected exit 0, `<n> managed files unchanged.` Run `./devctl check --tier fast`; expected exit 0. Commit `feat: add the optional rs-contribute skill`.
- [ ] **Step 5: documents and verification.** Add `test_every_kit_skill_mention_resolves` to `tests/test_kit_skills.py`: every `\brs-[a-z0-9-]+` in `rapid_ship/templates/common/.agents/skills/**/*.md` resolves to a Kit skill template, excluding `rs-exception`. Until Spec 3 supplies gardening/readiness skills, say “a gardening pass” and “a readiness review”. Root-guide expansion waits for Task 12 so 7.1a and parallel intermediate heads do not fail on future skill names. Describe both skills in the files above. Run the five checks with the PR's base and record them. Evidence: `Not covered: rs-health in a Session, which Task 9 runs; rs-contribute's push and PR, which would open a real PR on rapid-ship`. Commit `docs: record PR 7.3's verification`.

## Owner steps

### Task 9: Live trial of `rs-setup` and `rs-health` (Owner step)

**Files:**
- Create, on `plan7-site`: `docs/trials/<run date>-rs-setup-and-rs-health.md`
- Modify, on `plan7-site`: `docs/trials/AGENTS.md`; Spec 1 section 10’s existing-repository trial line after owner decision 2

Preconditions: plan 6, 7.1b, 7.2, 7.3, PRO-166, PRO-155, PRO-172, PRO-142 and the golden-paths library (PRO-167) are merged. PRO-156/157’s sandbox spec and restart fix is merged; retain `./devctl as *` only while its verified removal condition is unmet. Plan 6 Task 14’s PRO-161 bootstrap-order spec update is merged, and the owner has named the existing repository (decision 2). Record `origin/main`'s commit, and run `rapid-ship` as `uvx --from <a checkout of that commit> rapid-ship`. Each step's commands and output feed 7.4's pages. The record therefore keeps every command and its output verbatim, scrubbed of home and temporary paths, as plan 5's spike record did.

- [ ] **Step 1 (agent): prepare.**
  - Check both dependency tables against `origin/main` under all of `rapid_ship`, including `rapid_ship/kit/init.py` and `rapid_ship/cli.py`. Run `git grep -n -F 'init wrote nothing: confirm the stacks first.' origin/main -- rapid_ship`, and repeat with literal fragments `merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #`, `, so the owner merges it`, `is not installed; run npm ci there`, and `knip:@public`. For descriptive rows, inspect the exact source file/constants named there; never grep placeholders such as `<tool>` or `<n>`. A value that differs becomes a fix PR to `rs-setup` from `main`, merged before Step 3.
  - For the recommended repository, `proxy-hatch/rs-existing`, prepare its first commit in a scratch directory: an existing Python project without the Kit. It holds a small greeting CLI, `rs_existing`, under `src/` with tests, and its own `pyproject.toml`. Its Ruff, mypy and pytest settings differ from the Kit's in at least one stylistic option, such as `line-length = 100`, and lack at least one floor rule, such as Ruff's `BLE`. It also holds one `# noqa` suppression, one unused function, one declared dependency that nothing imports, a `.pre-commit-config.yaml`, a workflow `.github/workflows/test.yml`, and a `[tool.uv.workspace]` whose `members` glob `tools/*` covers one member package and, once the Kit lands, `tools/devctl`. For a repository of the owner's own, list which of these cases it holds instead.
  - Write the record with these steps, the prepared commit's SHA, and an empty results table: the command or prompt, the expected result, and the observed one.
- [ ] **Step 2 (Owner): seed the existing repository.** For `proxy-hatch/rs-existing`, create the public repository, push the prepared commit to its `main`, clone it, and run `uvx pre-commit install`, which puts a hook in `.git/hooks`. For the owner's own repository, clone it.
- [ ] **Step 3 (Owner): Get started.** Follow Task 12's Get started outline exactly, on a new public repository, `proxy-hatch/rs-get-started`. Run `init --stack python`, then `/rs-setup` without Agent identity. Open the red PR, which deletes the skeleton test and has no body: `diff` and `evidence` fail, and the merge guard denies the agent's merge. Record the owner-terminal remote default-branch bootstrap before ruleset application. Then open the green test-first `hello` PR with Evidence, and have the owner merge it.
- [ ] **Step 4 (Owner): two stacks, new.** On a new private repository, `proxy-hatch/rs-two-stacks`, run `init --stack python=backend --stack typescript=frontend`, then `/rs-setup`. Accept Agent identity with the existing Apps and the sandbox. Record the owner-terminal remote default-branch push before any ruleset attempt. Run Setup steps 5 and 6 in Claude Code, agy and Codex Sessions: record each wiring merge, Codex trust review in `/hooks`, and each Harness’s own sandbox settings. Start new sandbox Sessions before `./devctl --version`, `./devctl check --tier fast` and `gh auth status`; record output and exits for all three in each Harness. Record npm installation, full check and doctor output, including the GitHub Free private ruleset gap. Any unrun Harness or command is explicitly Not covered in the trial and guide; a text check is never a live pass.
- [ ] **Step 5 (Owner): the existing repository.** Run `init` without `--stack` and record its proposal, expecting `--stack python --stack python=tools/<member>`. Ask the owner to confirm the roots; for the prepared project, confirm only `--stack python` because the member belongs to the root workspace. Record both proposal and confirmation before rerunning with only the confirmed options. Run `/rs-setup`, with the existing suppressions and dead code marked, the hook and workflow overlaps shown, `./devctl doctor --skills` in Claude Code, the Setup PR and the tool-settings PR. Then rerun `rs-setup`'s GitHub step with Agent identity on and the ruleset present (Review Focus 1 and 2).
- [ ] **Step 6 (Owner): `rs-health`** on the existing repository, ending with the tasks the owner picks in a tracker that the Harness reaches, such as that repository's GitHub issues through `./devctl as worker gh issue create`. First run in a Session with an unavailable read source, such as GitHub authentication; record the failed read, unknown result, and absence of proposals based on it. Restore access and rerun. Record the owner-picked task links and one task’s full text. If no tracker is reachable, keep picked tasks in the conversation. Never treat blocked reads as zero or task evidence.
- [ ] **Step 7 (implementer): write the record** from the owner's output, and add its line to `docs/trials/AGENTS.md`. Each difference from the expected result becomes a fix PR from `main`, and its case is rerun, before 7.4 merges. `grep -n -e /Users/ -e /home/ -e /private/tmp -e /tmp/` on the record finds nothing. Commit `docs: record the rs-setup and rs-health trial` on `plan7-site`.

### Task 10: Apply `rs-setup`'s GitHub settings to `proxy-hatch/rapid-ship` (Owner step)

Early application was approved on 2026-10-28. The manager prepared an owner-run script; this plan records no execution or pass.

**Files:**
- Create, on `plan7-site`: `docs/trials/<run date>-rapid-ship-github-settings.md`
- Modify, on `plan7-site`: `docs/trials/AGENTS.md`

- [ ] **Step 1 (Owner), in a terminal,** use the manager-prepared script after its ruleset payload passes `ruleset_problems` for all four Mode/identity combinations. Read current rulesets, then apply `ruleset.json` with `POST`, or with `PUT` to an existing `rapid-ship` ruleset, as `rs-setup` does. Set `delete_branch_on_merge` and the fork PR approval with Task 5's two commands. G8 denies these writes to an agent here, because Agent identity is on.
- [ ] **Step 2 (Owner):** run full `./devctl doctor` and retain its actual output and exit code. Expected: ruleset, delete branch on merge and fork PR workflow approval items are ok. Missing, unknown or blocked results require follow-up and do not pass.
- [ ] **Step 3 (implementer): write the record** with each command, its exit code and doctor's lines, and add its line to `docs/trials/AGENTS.md`. Record the consequence: every later PR needs the code owner's approval or the admin bypass, a passing `devctl check`, resolved threads and a squash merge. Commit `docs: record rapid-ship's GitHub settings` on `plan7-site`.

## PR 7.4: the documentation site and GA (`plan7-site`, on `main` for independent structure)

### Task 11: The site's structure, Home, Why rapid-ship, The journey, Concepts and Reference

**Files:**
- Create: `website/src/pages/index.md` (Home), `website/page-rules.js`, `website/page-rules.test.js`, `website/src/theme/DocItem/Content/index.js`; `docs/start/why-rapid-ship.md`, `docs/start/the-journey.md`; `docs/concepts/` (`life-of-one-change.md`, `evidence-not-reports.md`, `four-rungs.md`, `modes.md`, `agent-identity.md`, `guardrails-and-their-limits.md`, `stacks.md`); `docs/reference/` (`rapid-ship-cli.md`, `devctl-check.md`, `devctl-doctor-and-as.md`, `devctl-hook.md`, `settings-files.md`, `pattern-format.md`, `supported-setups.md`, `skills.md`)
- Delete: `docs/getting-started.md`, `asset/public/banner.jpeg`
- Modify: `website/docusaurus.config.js`, `website/sidebars.js`, `website/src/css/custom.css`, `.github/workflows/docs.yml` (both path lists: `GLOSSARY.md` replaces `README.md`; the owner pushes this commit), `README.md`, `docs/branding.md`, `asset/AGENTS.md`, `docs/AGENTS.md`, `website/AGENTS.md`, Spec 1 section 2 item 4, the design's Delivery paragraph, `ARCHITECTURE.md`'s documentation-site section and its "What was removed" paragraph, the index's plan 7 row, this plan's Verification record

**Interfaces:**
- Consume the index's [Documentation site pages](2026-10-14-kit-and-setup.md#documentation-site-pages-plan-7-spec-3s-plan-writes-its-own-pages) contract: front matter, `pageProblems`, status badge and the concept/reference/guide templates. That contract is canonical for Spec 3 too. `parseFrontMatter` invokes the validator and names repository-relative paths in failures; it gives `GLOSSARY.md` the contract's slug and status. `README.md` leaves `include` because Home replaces it.
- Home (`website/src/pages/index.md`) opens with the owner's tagline, "Becoming a 100x developer starts with agents that earn your trust.", and the line "Agents that prove their work earn autonomy, so you can stop watching every one of them." A plain subheading follows: what rapid-ship gives your coding agents, that you start by deciding on every pull request, and that your Harness still runs the agents. Then one line says what works today and links The journey.
- Sidebar: Start (Home as `{type: 'link', label: 'Home', href: '/'}`, then Why rapid-ship and The journey as Step 3 writes them; Task 12 adds Get started), Concepts as `{type: 'autogenerated', dirName: 'docs/concepts'}`, Reference with `{type: 'autogenerated', dirName: 'docs/reference'}` followed by the explicit doc item `GLOSSARY`, and Project, collapsed and last: Contribute (`ARCHITECTURE.md`), Design records (`docs/superpowers`, `docs/adr`, `docs/trials`) and Credits. Navbar: Concepts, Reference, GitHub; Task 12 adds Get started and Guides. `docs/branding.md` leaves the sidebar.
- Pages. The status is the one `main` should hold at 7.4's review; Task 12 Step 3 rechecks each.

| Page | After it, the reader can | From | Status |
| --- | --- | --- | --- |
| Why rapid-ship | Say which of their problems it solves, who it is for and what it is not; it credits the owner's Trust-First Agentic Engineering Playbook | design: The problem, The boundary, Who does what; Spec 1 §1; ADR 0004 | built, the design |
| The journey | Say what works today and what comes next, from the first check to Flight, one row per plan and Spec 3 | design: Who does what, Modes, Delivery; §1 of Specs 1 and 3 | built, plans 1 to 7 and Spec 3 |
| The life of one change | Say who acts at each step, the owner's own Sessions included, and what evidence each step leaves | design: Who does what, How the bar is held; Spec 1 §§4 to 6, §8 | built, plans 3 to 7 |
| Evidence, not reports | Read a `devctl check` result and an Evidence section, and say what a pass does not prove | Spec 1 §5 Steps, Output, Evidence, Where `check` runs | built, plans 3 and 5 |
| The four rungs | Put a new rule on the rung that fits, with exceptions instead of ratchets, and the Protected set | design: Standards; Spec 1 §4 Patterns, Protected set; §5 Exceptions | built, plans 3 and 5 |
| Modes: Walk to Flight | Choose a Mode, know what enforces it in their setup, and widen it in one Protected PR | design: Modes; Spec 1 §4 Settings files (`[escalation]`), The merge guard, The Protected set and CODEOWNERS | built, Spec 1 |
| Agent identity | Decide whether their setup needs it | Spec 1 §3 `rapid-ship app`, §6 Agent identity; ADR 0002 | built, plan 4 |
| Guardrails and their limits | Know what the guardrails and the merge guard deny in Claude Code, agy and Codex, and what they cannot stop | Spec 1 §4 Harness guardrails, The merge guard | built, Spec 1 |
| Stacks | Lay out a Python backend and a TypeScript frontend | design: Standards; Spec 1 §5 Several stacks | built, plan 6 |
| `rapid-ship` CLI; `devctl check`; `devctl doctor` and `devctl as`; `devctl hook`; Settings files; Pattern format | Look up a command, option, default, exit code, key or field | Spec 1 §§3 to 6; the index's Conventions | built, plans 2 to 6 |
| Supported setups | Check their setup before installing | design: What rapid-ship ships; Spec 1 §1, §4 Harness guardrails | built, plans 5 and 6 |
| Skills | Pick the skill for a job and know who runs it | Spec 1 §7; Spec 3 §§10, 11 | built, plan 7 and Spec 3 |

- `docs/AGENTS.md` records the index's three page templates and style rules. Spec 3 consumes the index directly before that edit lands. No page cites a Linear ID.
- `README.md` becomes a lean GitHub front page. The logo replaces the banner. Then come the subheading, the senior-engineer line, the evidence line, an honest Status, a link to the site and the credits. Its paragraphs on the Kit's parts, the merge guard, Agent identity and the Modes move to Why rapid-ship and The journey, with their status. `docs/branding.md`'s banner prompt drops the tagline line, and the config's `tagline` and footer drop it too.

- [ ] **Step 1: page rules first.** Write `website/page-rules.test.js` using `node:test`: missing/invalid status, blank status_detail and each banned claim in mixed case produce a path-bearing problem; a complete page and exempt design record produce `[]`. Run `node --test website/page-rules.test.js`; expected failure on the missing validator. Write `page-rules.js` and wire it into `parseFrontMatter`. Rerun the test; expected exit 0, zero failures. Add a concept page without `status`; `npm --prefix website run build` fails and names the file. Add the status, then a `powerful` in its body; the build fails again. Restore valid front matter and remove the banned word: `npm --prefix website run build` exits 0 with `[SUCCESS] Generated static files in "build".`, although the plan index and this plan quote "100x". Record the three runs in 7.4's subsection of the Verification record.
- [ ] **Step 2: structure.** Build Home, the badge, the sidebar and the navbar; add `GLOSSARY.md`; take `README.md` out of `include`; delete `docs/getting-started.md`; edit `docs.yml`'s path lists. The build passes with no broken link or anchor. Commit `feat: rebuild the documentation site's structure with status badges`, and have the owner push it, since it edits a workflow.
- [ ] **Step 3: pages.** Write each page from the sources its row names, and add Why rapid-ship and The journey to Start. Write Modes once PRO-166 has merged, Guardrails and their limits once agy and Codex wiring and trials have landed, Stacks, Supported setups and the Reference pages once plan 6 has, and Skills once 7.2, 7.3 and Spec 3 have. Final pages also wait for the golden-paths library (PRO-167); remove feature-map terminology without defining a new format or check. Record each Terminal example from a real local run, or quote a trial record's, with the version and the date. Commit `docs: write Why rapid-ship, The journey, the Concepts and the Reference`.
- [ ] **Step 4: README and guides.** Trim `README.md`, delete `asset/public/banner.jpeg`, and update `docs/branding.md`, `asset/AGENTS.md`, `docs/AGENTS.md` and `website/AGENTS.md`. Update Spec 1 section 2 item 4 and `ARCHITECTURE.md`'s "What was removed" paragraph, which both say the getting-started guide remains, and the design's Delivery line. Check Home and one concept page by eye in `npm --prefix website run serve`, at desktop and phone widths, in light and dark mode. Commit `docs: trim the README to a GitHub front page`.

### Task 12: GA's version, Get started, the Guides, GA's texts, and PR 7.4's verification

**Files:**
- Create: `docs/start/get-started.md`; `docs/guides/` (`set-up-a-repository-with-rs-setup.md`, `add-the-kit-to-an-existing-repository.md`, `audit-a-repository-with-rs-health.md`, `set-up-a-python-backend-and-a-typescript-frontend.md`, `give-your-agents-their-own-github-identity.md`, `turn-on-the-guardrails-in-claude-code-agy-and-codex.md`, `keep-the-kit-current.md`, `write-a-prs-evidence-section.md`, `record-an-exception.md`, `turn-a-review-comment-into-a-check.md`, `write-a-pattern.md`)
- Modify: the Kit version in both `pyproject.toml` files, devctl's `__version__` and both `uv.lock` files; `website/sidebars.js` (Get started in Start; Guides as `{type: 'autogenerated', dirName: 'docs/guides'}`); `website/docusaurus.config.js` (the navbar); `docs/AGENTS.md`; every page of Task 11 whose status or content differs from `main`, The journey and Skills among them, which link Spec 3's pages; each GA text that Step 4's commands find, among them `README.md`, `ARCHITECTURE.md:83`, the root `AGENTS.md`, `rapid_ship/templates/AGENTS.md:15`, the test comment in `tests/devctl/test_devctl_exceptions_allowlists.py`, Spec 1's status line and sections 3 to 5, the design's status line and "What rapid-ship ships", and the index's Conventions; the index's plan 7 row; this plan's Verification record

**Interfaces:**
- Get started covers one Python stack in a new repository:
  1. Prerequisites, each with its check command: macOS, uv, `gh auth status`, `gitleaks version` (8.30.1) and Claude Code.
  2. Terminal: create and clone an empty public repository, and run `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v1.0.0 rapid-ship init --stack python --owner <you>`.
  3. Your coding agent: `/rs-setup`. It shows its plan, asks you to bootstrap the remote default branch from your own terminal before enabling a ruleset, applies the ruleset after your yes, and `./devctl doctor` reports no gap.
  4. Terminal: delete the skeleton test on a branch, push it, and open a PR with no body; CI's `devctl check` fails at `diff` and `evidence`. Your coding agent: ask it to merge the PR; the merge guard denies it, because in Walk you merge every PR.
  5. Your coding agent: a small `hello` command, test-first. Its PR carries an Evidence section, the check passes, and you merge it.
  6. What the loop gives you, a link for each step, and the page's limits.

  It gives no time promise until a trial has measured one.
- Guides use the index’s shared Guide page template.

| Guide | From | Outputs from |
| --- | --- | --- |
| Set up a repository with `rs-setup` | Spec 1 §8 | Task 9 Steps 3 and 4 |
| Add the Kit to an existing repository | Spec 1 §3 `init`, Who owns what; §5 Exceptions; §§8, 9 | Task 9 Steps 5 and 6 |
| Audit a repository with `rs-health` | Spec 1 §9 | Task 9 Step 6 |
| Set up a Python backend and a TypeScript frontend | Spec 1 §4 TypeScript guardrail settings; §5 Several stacks | Task 9 Step 4 |
| Give your agents their own GitHub identity | Spec 1 §3 `rapid-ship app`; §6 Agent identity | Task 9 Step 4, and plan 4's trial record |
| Turn on the guardrails in Claude Code, agy and Codex | Spec 1 §4 Harness guardrails, The merge guard; §6 `devctl hook` | Task 9 Steps 3 and 4, plan 5’s trial and the agy/Codex wiring trials; label any unrun Setup sandbox Session Not covered |
| Keep the Kit current | Spec 1 §3 `status`, `sync`, Who owns what, Lock file | a local run |
| Write a PR's Evidence section | Spec 1 §5 Diff policy, Evidence | a local run |
| Record an exception | Spec 1 §5 Exceptions | a local run |
| Turn a review comment into a check | Spec 1 §3 Who owns what; §5 Steps | a local run |
| Write a Pattern | Spec 1 §4 Patterns, Starter Patterns; §5 Map rules, References | a local run |

- `docs/AGENTS.md` gains the rule, from GA on: a PR that changes user-visible behaviour updates its pages, their status and its row in The journey in the same PR.
- GA: each text that says the Kit keeps no backward compatibility before GA now says that rapid-ship reached GA with `v1.0.0`, and that the policy after GA is not designed yet (decision 3).

- [ ] **Step 1: GA's version.** Set the version that decision 3 names, recommended `1.0.0`, in both `pyproject.toml` files and in `__version__`, as plan 5's Task 2 Step 1 set `0.2.0`. Run `uv lock` and `uv lock --project rapid_ship/templates/common/tools/devctl`, sync, then `uv run pytest tests/test_kit_contents.py -q`; expected exit 0, `<n> passed`. Commit `chore: set the Kit version to 1.0.0 for GA`.
- [ ] **Step 2: local guides.** While Task 9 runs, record the five local guides' runs on scratch repositories at the candidate version and merged head, and write those guides. These early runs do not prove the final GA head.
- [ ] **Step 3: trial pages.** Write Get started and the other six guides from Task 9's record, and from Task 10's where a page cites it. Rerecord with a local run each example whose output names the Kit version, such as `init`'s first line. Once Spec 3 is built, recheck every Task 11 page and every Task 12 guide against `main`, including local-run guides, and recheck all status badges, rerecord an example whose output changed, and link Spec 3's pages from The journey and Skills. The build passes.
- [ ] **Step 4: GA text.** Run `git grep -n -i -e 'before GA' -e 'backward compatib' -- . ':!docs/trials' ':!docs/superpowers/plans'` and `git grep -n -i -e 'before GA' -e 'backward compatib' -- docs/superpowers/plans/2026-10-14-kit-and-setup.md`. Rewrite current product/status hits and the test comment so neither phrase remains. Keep historical records in the excluded trial and plan directories. Rerun both commands; expected no output and exit 1 from each. Reword historical statements in the index without changing their recorded behavior, so they also contain neither search phrase. Commit `docs: write Get started and the Guides for GA`.
- [ ] **Step 5: verify.** Expand `test_every_kit_skill_mention_resolves` to every root-guide seed after 7.1b, Setup, Health and Spec 3’s skills merge; retain the `rs-exception` exclusion. Run `uv run pytest tests/test_kit_skills.py -q`; expected exit 0, `<n> passed`. Run `node --test website/page-rules.test.js`; expected exit 0, zero failures. Run the five Global Constraints checks with the PR’s base. Evidence: `Not covered: whether each page's prose, Spec 3's pages included, matches the code beyond its recorded examples`. After the merge, the owner tags `v1.0.0` on the merge commit and checks `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v1.0.0 rapid-ship --help`. Commit `docs: record PR 7.4's verification`.

## Document self-review, 2026-10-28

Checked Spec 1 §§7–10 coverage against Tasks 1–12, helper argument/return types, staged skill-name tests and the five Review Focus pins. Reconciled the 18 fit and 19 quality findings with later owner decisions. Sandbox and bootstrap spec changes remain with PRO-156/157 and plan 6 Task 14; tool adoption and the existing-repository trial retain their owner conditions. This revision implements no task and records no live trial pass. The lead runs full checks and the site build after review.

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
