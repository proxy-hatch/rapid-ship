# Metrics and Gardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Spec 3: `./devctl metrics` with its settings in `.rapid-ship/metrics.toml`, the five basic metrics and their Suggested thresholds, project-defined metrics and the optional scheduled metrics Action; the Corrections ledger with its map rule, its seeded README and the Rule for a Correction given in a Session; `rs-garden`, which reruns the audit it shares with `rs-health`; `rs-preflight`; and `rs-setup`'s metrics step. Then trial them, dog-food them on this repository, and write their pages for the documentation site, whose release, plan 7's PR 7.4, is GA.

**Architecture:** Nine PRs, 3.1 to 3.9. devctl's new code is one package, `devctl/metrics/`, plus `devctl/ledger.py`, which the ledger's map rule (`check/map_ledger.py`) and the Corrections metric share. `devctl metrics` reads GitHub only through doctor's `gh_get` (`gh api --method GET` under the run's sign-in), wrapped in a reader that pages and stops at once when the API allowance runs out. It reads git only from the local `origin/<default branch>`. Each metric is a function from the window to a `Measured` value, and one status rule judges every threshold. The ledger's Protected rule and the CI concurrency group that Red merges needs are already built (plan 5). The skills are Markdown templates under `rapid_ship/templates/common/.agents/skills/`.

**Tech Stack:** Python 3.12+ standard library (`difflib`, `tomllib`, `json`, `datetime`, `threading`, `abc`), PyYAML, git 2.31+, gh, uv, pytest; GitHub Actions with `actions/checkout` and `astral-sh/setup-uv` at the CI workflow's pins; Markdown skills; Docusaurus for the pages.

**Spec:** [Spec 3: Metrics and gardening](../specs/2026-10-16-metrics-and-gardening-design.md), every section, as PR #47 revised it. [Spec 1](../specs/2026-10-14-kit-and-setup-design.md) supplies what Spec 3's section 13 lists: the Protected set and the ledger rule (section 4), map rules (section 5), the root guide's Rules and Pull requests section (section 4), `rs-setup` step 10 (section 8) and `rs-health`'s audit (section 9). The [plan index](2026-10-14-kit-and-setup.md)'s Conventions, Layout and Shared interfaces bind this plan.

**Status:** planned on 2026-10-27 from `descope-spec2` (PR #47) at `38e192b`, while plans 6 and 7 are planned in their own worktrees. This document lands in PR 3.1.

**Owner steps:** the decisions below; Task 14, the live trials and this repository's dog-food runs; and pushing PR 3.7's commit that adds this repository's `.github/workflows/rapid-ship-metrics.yml`, which the Worker App cannot push. The agent writes each procedure, the scripts the owner runs and the empty record. No implementer subagent runs an Owner step.

## Order and parallel work

| PR | Branch, worktree | Base | Tasks | Builds | Counted lines, estimated |
| --- | --- | --- | --- | --- | --- |
| 3.1 | `spec3-plan`, `.worktrees/spec3-plan` | `descope-spec2`, then `main` | this document, 1 | `metrics.toml` and its loader, the status rule | about 700 |
| 3.2 | `spec3-ledger`, `.worktrees/spec3-ledger` | `main` | 2, 3 | the ledger's parser and map rule 9, its seeds, the `session` Rule | about 800 |
| 3.3 | `spec3-window`, `.worktrees/spec3-window` | 3.1's planning commit | 4 | the GitHub reader with the API allowance, the window | about 900 |
| 3.4 | `spec3-command`, `.worktrees/spec3-command` | `main` | 5, 6 | Revisions, Red merges, and `devctl metrics` with its text, JSON and exit codes | about 1,150 |
| 3.5 | `spec3-reverts`, `.worktrees/spec3-reverts` | `main` | 7, 8 | Reverts, whole and partial; Closed unmerged; Corrections | about 1,200 |
| 3.6 | `spec3-project-metrics`, `.worktrees/spec3-project-metrics` | `main` | 9 | project-defined metrics: settings sources and code metrics | about 800 |
| 3.7 | `spec3-action`, `.worktrees/spec3-action` | `main` | 10, 11 | `[kit] optional` for Kit files, `--post` and the Action | about 750 |
| 3.8 | `spec3-skills`, `.worktrees/spec3-skills` | `main` | 12, 13 | `rs-garden`, `rs-preflight`, `rs-setup`'s metrics step | about 200 |
| 3.9 | `spec3-pages`, `.worktrees/spec3-pages` | `main` | 15, 16, and Task 14's records | the integration tests, the trial records and the site's Spec 3 pages | about 150 |

The diff cap leaves out `.md` files and Kit-managed files, so the skills, the pages and the vendored copy under `tools/devctl/` do not count. The devctl template under `rapid_ship/templates/` counts once.

**Dependencies.**

- 3.1 waits for PR #47 to merge. 3.3 starts at once from 3.1's planning commit, the commit that adds this document, because it needs nothing that Task 1 builds.
- 3.2 edits the root guide seeds after the code PR on `escalation-and-pr-guide` (the merge guard's Mode rules and the Pull requests section). Start 3.2 from `main` once that PR has merged.
- 3.4 needs 3.1 and 3.3. 3.5 needs 3.4 and 3.2, because Corrections reads the ledger with `devctl/ledger.py`. 3.6 and 3.7 need 3.4 only.
- 3.8 needs plan 7's PRs 7.1a, 7.2 and 7.3: 7.1a's `tests/test_kit_skills.py`, `rs-setup`, and `rs-health`'s `references/audit.md` and `references/proposed-task.md`. It names `devctl metrics --json` fields that 3.4 builds, so it starts after 3.4 too. Task 13's `rs-preflight` needs nothing from plan 7, and may be written first on the branch.
- Task 14 runs once 3.5 to 3.8 have merged. 3.9 follows Task 14 and plan 6's PR 6.3, whose two-stack integration test Task 15 extends.

**GA.** Plan 7's PR 7.4, the documentation release, is GA. It merges after 3.9, after plan 7's Owner steps (its Tasks 9 and 10) and after plan 6. 3.9 lands before 7.4, so 7.4's page rules check Spec 3's pages. The owner then tags the release on 7.4's merge commit.

**Combined order** (decision 1). The design advises at most 3 agents at once in Walk. Spec 3's chain, 3.1 and 3.3, then 3.4, then 3.5 to 3.7, then 3.8, then its trials, is the longest to GA, so it starts in wave 1. Each wave starts once the PRs it needs have merged.

| Wave | Workers |
| --- | --- |
| 1 | 6.1a, 3.1, 3.3 |
| 2 | 3.4, 6.1b, 3.2 |
| 3 | 3.5, 6.2a, 6.2b |
| 4 | 3.6, 3.7, 7.1a then 7.1b |
| 5 | 6.3, 7.3, 7.2 |
| 6 | 3.8, 7.4's Task 11 |
| Owner | plan 7's Tasks 9 and 10 and this plan's Task 14, side by side |
| 7 | 3.9, 7.4's Task 12 |

**Landing on `main`.** Each PR is reviewed and squash-merged on its own, and the owner merges each one, because each touches the Protected set. After a squash merge, retarget each open PR whose base was that branch with `./devctl as worker gh api -X PATCH repos/proxy-hatch/rapid-ship/pulls/<n> -f base=main`. Then update every open PR of this plan with a normal `git merge origin/main`. Use `git merge -s ours` only when the branch holds the squashed PR's whole head and `git diff --quiet <squash commit> <that head>` holds. 3.3 holds only 3.1's planning commit, so it takes a normal merge: keep `main`'s copy of this document plus 3.3's own Verification subsection. Resolve `.rapid-ship/kit.lock` by taking `origin/main`'s and running `uv run rapid-ship sync --in-place`. Push with `./devctl as worker push` and wait for that head's `devctl check`.

**File overlap** with plans 6 and 7 and the open PRs. Resolve as the last column says, never by dropping a side.

| Files | This plan | Also changed by | Resolution |
| --- | --- | --- | --- |
| `.rapid-ship/kit.lock` | every PR that syncs | every PR of plans 6 and 7, the agy wiring | Take `origin/main`'s, run `sync --in-place`, commit the result |
| `rapid_ship/templates/kit.toml` | 3.1, 3.2 (`seeded`), 3.7 (`optional`) | agy wiring (`seeded`), 6.1b and 6.3 (`new_project` by stack), 7.3 (`optional_skills = ["rs-contribute"]`) | Keep every entry, sorted. Whichever of 3.7 and 7.3 lands second writes `rs-contribute` under the key `optional` |
| The root guide seeds, `common/AGENTS.md` and `python/AGENTS.md` | 3.2 (the `session` Rule, last) | the `escalation-and-pr-guide` PR, 6.1b (moves the Python root guide to `common/`) | 3.2 starts after the escalation PR. If 6.1b lands first, add the Rule last in each root guide's Rules where 6.1b put them |
| The CODEOWNERS seeds | 3.2 (`/docs/corrections/README.md` after `/.rapid-ship/`) | agy wiring (`/.agents/`), 6.1b (one seed rendered from every stack), 6.3 (TypeScript lines) | Keep both; the ledger line stays right after `/.rapid-ship/` |
| `devctl/doctor_rules.py` `PROTECTED_PATHS` | 3.2 | agy wiring, 6.1a and 6.2a | Keep both |
| `devctl/settings.py`, `tests/devctl/test_devctl_settings.py` | 3.7 (`OPTIONAL`, `ProjectSettings.optional`) | escalation PR, 6.1a (`[[stack]]`), 7.3 (`OPTIONAL_SKILLS`) | Keep both; 3.7's names win |
| `rapid_ship/kit/templates.py`, `sync.py`, `status.py`, `tests/test_kit_templates.py`, `tests/test_kit_sync.py` | 3.7 (the rename) | 6.1b (stacks) | Keep both |
| Every `.rapid-ship/project.toml` seed, and this repository's | 3.7 (the `[kit] optional` comment; this repository opts in) | escalation PR, 6.1a, 6.1b (moves the seed to `common/`), 7.3 (the same comment) | One comment: `opt-in Kit skills and files: .github/workflows/rapid-ship-metrics.yml, rs-contribute` |
| `devctl/cli.py` | 3.4 (one registration) | 6.2a (`--install`) | Keep both |
| `devctl/check/references.py` | 3.2 calls `resolve` | 6.1a and 6.2b resolve by stack | 3.2 calls the signature on `main` |
| `tests/test_kit_contents.py`, `tests/test_kit_seed_keys.py` | 3.1, 3.2 | agy wiring, 6.1b, 6.3, 7.3 | Keep every test |
| `tests/test_kit_skills.py` (7.1a) | 3.8 (`USER_INVOKED`) | 7.1a, 7.1b | Add `rs-garden` and `rs-preflight` |
| `skills/rs-setup/SKILL.md` | 3.8 (step 10) | 7.2 creates it | 3.8 starts after 7.2 |
| This repository's `docs/AGENTS.md`, `website/docusaurus.config.js`, `docs/trials/AGENTS.md` | 3.2, 3.9 | 7.4, plan 6's Task 13 | Keep both sides' lines |
| `ARCHITECTURE.md`, the root `AGENTS.md`, `README.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, Spec 3's status line, the index | every PR | every PR of plans 6 and 7 | Keep both sides' clauses |

## Owner decisions needed

1. **The combined order above,** which starts Spec 3 in wave 1 beside 6.1a, because its chain to GA is the longest. Recommended: accept it. It keeps three Workers at a time and puts plan 7's skills in waves 4 and 5, just before 3.8 needs them.
2. **Spec 3's open questions (section 17).** Recommended: build no `--strict` option and no lower limits before GA, and ship the 0.8 similarity threshold until Task 14's trial measures it. Each can follow GA as its own task if a project asks for it.
3. **The trials' scope.** Recommended: one public scratch repository, `proxy-hatch/rs-metrics-trial`, serves the metrics, Action, `rs-garden` and deployments trials, with one owner script that prepares it. `rs-garden`'s second Harness is agy, which the Kit wires before GA, not Codex, which has no wiring yet. GA waits for every Spec 3 trial, which runs beside plan 7's Task 9, because the pages show output from real runs.
4. **`rs-garden` and `rs-preflight` are user-invoked,** with `disable-model-invocation: true` like the other user-invoked Kit skills, so no Session starts gardening on its own. Recommended: yes. A scheduled pass starts the skill by name, for example `claude -p "/rs-garden"`. If Task 14 shows that a Harness cannot start it unattended, `rs-garden` drops the key.
5. **This repository's dog-food.** Recommended: PR 3.7 opts this repository into the metrics Action, which keeps one issue titled "rapid-ship metrics" on this public repository, and the owner pushes that commit. The owner runs `rs-garden` by hand each week until the unattended trial passes, then from a scheduler on the owner's machine with the owner's subscription; its proposals go to Linear.

## Deviations from Spec 3's slices

- Spec 3 section 12 names six slices. They become nine PRs under the diff cap: the window, the command and the reverts each need a PR of their own, and the site's pages need the trials' output.
- The ledger's map rule is map rule 9, after Spec 1's eight. The `session` Rule is the last seeded Rule in both root guides.
- An entry whose front matter is invalid counts as an unknown part of Corrections, not as an error of the report. CI keeps the ledger valid on the default branch.
- `--post` prints the issue's URL and the status changes, not the report, which the job summary and the issue hold.
- The `issues` source reads the repository's issue list, which shares the core API allowance, not the search API, which has its own allowance and result cap.
- This repository's site leaves out `docs/corrections/`: its entries are records, not pages.

## Global Constraints

- Command: `./devctl metrics [--window <n>] [--json] [--post]`. `--window` is an integer of at least 1 with no upper limit. Exit 0: the report was built and no Suggested threshold is breached. Exit 1: at least one is breached. Exit 2: the report could not be built, or with `--post` the post failed. An unknown status never changes the exit code. With `--post`, a breach exits 0 once posted. An API allowance that runs out is not exit 2 (Spec 3 section 5).
- Every exit 2 names what failed and the fix, such as `origin/main is missing: run git fetch origin`.
- devctl reads GitHub only with `gh api --method GET`, through `doctor_items.gh_get`, and git only from the local `origin/<default branch>`; it never fetches. Its only write is `--post`, which refuses with exit 2 unless `GITHUB_ACTIONS` is `true` and `GH_TOKEN` is set.
- Populations: `agent` (PRs that the Worker App authored, `<worker_app_slug>[bot]`), `all`, `ledger`, `repository`. A metric that needs Agent identity and lacks it is unknown with the reason `needs Agent identity`, shown in place of a status.
- Status rule, for value `v`, unknown parts `u` and threshold `m`: breached when `v > m`; ok when `v + u <= m` and the value is complete; unknown otherwise. A window with no PRs makes every metric unknown, never zero.
- Default thresholds: `revisions = 1.0`, `reverts = 1`, `red_merges = 1`, `closed_unmerged = 3`; `corrections` and `alarms` commented out; `window = 30`. The seed is Spec 3 section 6's block, verbatim.
- Partial reverts: similarity ratio at least `0.8` by `difflib.SequenceMatcher` over the joined lines, stripped of leading and trailing whitespace; only a hunk that removed at least 1 line and changed at least 3 non-blank lines counts.
- Red merges read `.github/workflows/devctl-check.yml`'s runs with event `push` for the merge commit, the earliest run's first attempt: `failure` and `timed_out` are red, `success` green, anything else unknown.
- Allowance message: `unknown: GitHub API allowance used up; it resets at 06:12 UTC`, with the reset time in UTC as `HH:MM`.
- A code metric that raises or runs longer than 60 seconds is unknown, with the error as its reason.
- The Action: `.github/workflows/rapid-ship-metrics.yml`, job name `rapid-ship metrics`, issue title `rapid-ship metrics`, body marker `<!-- rapid-ship-metrics -->`, issue author `github-actions[bot]`, concurrency group `rapid-ship-metrics`.
- The ledger: `docs/corrections/`, one `<date>-<category>-<n>.md` per entry, `README.md` and `last-pass.toml`. Fields, statuses, `by` values and rungs 1 to 4 as in Spec 3 section 9. The Rule, exactly: ``When the owner corrects you in a Session, add an open entry to the Corrections ledger with `source: session`. advisory``.
- devctl source is edited only under `rapid_ship/templates/common/tools/devctl/`. Run `uv run ruff format <files>` and `uv run ruff check <files>` on the changed templates, then `uv run rapid-ship sync --in-place`, before each test run that expects a pass. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit the vendored copy or the lock by hand.
- devctl starts processes only through `process.run_process`, called through the module, and depends only on PyYAML and PyJWT; this plan adds no dependency. Each `.py` file under `[map] source_roots` stays under 500 lines; `check/map.py` (420 lines) gains two lines.
- The comment rule: no comment, docstring, message or test name cites a plan, spec, section, ADR, PR, trial or rule ID. Kit skill text and seeds never name this repository's own choices, such as Linear or agy, and cite no rapid-ship document.
- No backward compatibility before GA: devctl only notes a leftover `gate.toml`; nothing migrates it.
- No `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression has an `rs-exception` marker and an entry. Write tests first. A test module's docstring starts `Offline:` and names what it simulates; a test that uses a fake `gh` says `simulated`. A blocked, skipped or simulated check never counts as passed.
- Keep each existing test's name. A test renamed or removed against the PR's base goes under `Removed tests:` in the PR body.
- Agent identity is on here. Agents push with `./devctl as worker push` and write to GitHub with `./devctl as <role> gh`. In a wired Session, G5 asks the owner before each edit of a Protected path, such as `.rapid-ship/`, `.github/`, `pyproject.toml` or any `AGENTS.md`. The Worker App cannot push a commit that edits `.github/workflows/`; a commit that edits only the template under `rapid_ship/templates/` goes through, and if GitHub refuses it, the owner pushes it.
- Diff cap: 1,500 counted lines per PR. Split at a task boundary, or declare `Over the diff cap: <reason>` only after the owner accepted the overage.
- Each PR's last task runs and records, in its own subsection of the Verification record, each command with its exit code and summary line: `uv run pytest -q`; `./devctl check --tier fast`; `uv run rapid-ship status --strict`; `./devctl check --tier full --base <PR base> --pr-body <body file>`; and, when docs change, `npm --prefix website run build`. Before 3.1 merges, 3.3's base is `origin/spec3-plan`.
- Ruff formats the `python` blocks of this file: keep them valid Python in Ruff's layout.
- Commit trailer: `Co-Authored-By: <the model that writes the commit>`, such as `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The API allowance runs out part way.** Inputs: a large `--window`, or the Action and a person sharing an hour's allowance, so a read in the walk or inside a metric gets 403 or 429 with a rate-limit message. Expected: no later read starts; each metric that did not finish is unknown with the reason and the reset time; no count is reported as complete; the exit code follows the finished thresholds, never 2. Task 4's `test_the_allowance_stops_every_later_read` and Task 6's `test_the_allowance_used_up_mid_run_leaves_the_rest_unknown` pin it.
2. **History that is not one squash merge per PR.** Inputs: a direct push to the default branch, a merge commit with two parents, a PR merged on GitHub after the last `git fetch`, and a commit whose `pulls` list names a PR merged by another commit. Expected: the push is skipped, the walk follows first parents, the unfetched PR counts under `not_fetched`, and the other PR is skipped. Task 4's window tests pin it.
3. **A later change that looks like a revert.** Inputs: a refactor that rewrites a hunk the PR added, a renamed file restored under its old name, a binary file restored, and a short hunk. Expected: only the content rules match; a rename undone is a whole revert; a binary file counts as restored but never as a section. Task 7's `test_a_rename_undone_is_a_whole_revert` and `test_a_binary_file_counts_only_when_restored` pin it.
4. **A project's code metric misbehaves.** Inputs: `measure` raises, sleeps past 60 seconds, returns `None`, returns a negative or NaN value, or returns plain items from an `IncidentMetric`; `metrics()` raises or returns a duplicate ID. Expected: each misbehaving metric is unknown with a reason and the rest of the report is unaffected; a broken `metrics()` exits 2 naming `devctl_project`. Task 9's tests pin it.
5. **Front matter that YAML reads unexpectedly.** Inputs: `rungs: [1, 1]`, `rungs: 2`, `rungs: [true]`, `date: 2026-10-16T05:00:00`, `pr: "42"`, `status: Open`, `source: http://...`, and a field outside the table. Expected: each fails the map rule with the file, the field and the allowed values, and Corrections counts the entry as unknown. Task 2's `test_each_invalid_field_names_what_it_accepts` pins it.
6. **The issue the Action keeps.** Inputs: a person edited the body and removed its JSON; two open issues carry the marker; an issue with the marker opened by another account. Expected: devctl takes the lowest-numbered open issue that `github-actions[bot]` opened; a body without readable JSON counts as no previous statuses. Task 11's `test_the_issue_is_github_actions_lowest_open_one` and `test_a_body_without_json_has_no_previous_statuses` pin it.

## File Structure

`devctl/` means `rapid_ship/templates/common/tools/devctl/devctl/`, and `skills/` means `rapid_ship/templates/common/.agents/skills/`; `sync` writes their vendored copies.

| File | PR | Responsibility |
| --- | --- | --- |
| `common/.rapid-ship/metrics.toml` | 3.1 | The seeded settings, Spec 3 section 6's block |
| `devctl/metrics/settings.py` | 3.1 | `load_metrics`, which lists every problem; the `gate.toml` note |
| `devctl/metrics/model.py` | 3.1 | `Measured`, `MetricReport`, the status rule |
| `devctl/ledger.py` | 3.2 | A ledger entry and `last-pass.toml`, read and validated |
| `devctl/check/map_ledger.py` | 3.2 | Map rule 9 |
| `common/docs/corrections/README.md` | 3.2 | The seeded ledger format |
| `devctl/metrics/github.py` | 3.3 | The read-only reader: pages, request count, the allowance |
| `devctl/metrics/window.py` | 3.3 | The default branch, the window, `not_fetched` |
| `devctl/metrics/revisions.py`, `red_merges.py` | 3.4 | Two basic metrics |
| `devctl/metrics/report.py`, `command.py` | 3.4 | The report, its text and JSON, `devctl metrics` |
| `devctl/metrics/reverts.py`, `partial_reverts.py` | 3.5 | Reverts from git and PR bodies, and the content check |
| `devctl/metrics/closed_unmerged.py`, `corrections.py` | 3.5 | Two basic metrics |
| `devctl/metrics/api.py` | 3.6 | What `devctl_project` imports: `Metric`, `IncidentMetric`, `MetricContext`, `MetricResult`, `Item`, `Incident` |
| `devctl/metrics/project.py`, `sources.py` | 3.6 | Running code metrics; the `issues` and `deployments` sources |
| `devctl/metrics/post.py`, `common/.github/workflows/rapid-ship-metrics.yml` | 3.7 | The post and the Action |
| `skills/rs-garden/SKILL.md` | 3.8 | Gardening passes |
| `skills/rs-preflight/SKILL.md`, `skills/rs-preflight/references/project-metrics.md` | 3.8 | The Pre-flight review, and how to add a project-defined metric |
| `tests/devctl/metrics_fakes.py` | 3.3 | A merged history in a local repository with its recorded GitHub responses, and a fake `gh` on `PATH` |

---

## PR 3.1: settings (`spec3-plan`, on `descope-spec2`)

### Task 1: `metrics.toml`, its loader and the status rule

**Files:**
- Create: `rapid_ship/templates/common/.rapid-ship/metrics.toml`; `devctl/metrics/__init__.py`, whose only content is the docstring `"""devctl metrics: the report on merged pull requests, the Corrections ledger and the project's own metrics."""`; `devctl/metrics/settings.py`, `devctl/metrics/model.py`; `tests/devctl/test_devctl_metrics_settings.py`, `tests/devctl/test_devctl_metrics_model.py`
- Modify: `rapid_ship/templates/kit.toml` (`seeded` gains `.rapid-ship/metrics.toml`), `tests/test_kit_seed_keys.py`, `tests/test_kit_contents.py`, `tests/test_kit_sync.py`; through `sync`: the vendored package, this repository's `.rapid-ship/metrics.toml`, which `sync` creates, and `.rapid-ship/kit.lock`

**Interfaces:**
- Consumes: `devctl.settings.SettingsError`.
- Produces:

```python
# devctl/metrics/settings.py
METRICS = ".rapid-ship/metrics.toml"
GATE = ".rapid-ship/gate.toml"
BASIC_METRICS = ("revisions", "reverts", "red_merges", "closed_unmerged", "corrections")


@dataclass(frozen=True)
class IssuesSource:
    label: str


@dataclass(frozen=True)
class DeploymentsSource:
    environment: str
    count: Literal["rollbacks", "failures"]  # "rollbacks" when absent


@dataclass(frozen=True)
class SettingsMetric:
    metric_id: str
    title: str
    source: IssuesSource | DeploymentsSource


@dataclass(frozen=True)
class MetricsSettings:
    window: int
    thresholds: Mapping[str, float]  # metric ID -> upper limit
    metrics: tuple[SettingsMetric, ...]  # in file order


class MetricsSettingsError(SettingsError):  # str() joins problems with newlines
    problems: tuple[str, ...]


def load_metrics(root: Path, code_metric_ids: Collection[str] = ()) -> MetricsSettings: ...
def gate_note(root: Path) -> str | None: ...


# devctl/metrics/model.py
Population = Literal["agent", "all", "ledger", "repository"]
Kind = Literal["count", "incident"]
ThresholdStatus = Literal["ok", "breached", "unknown"]
NEEDS_IDENTITY = "needs Agent identity"


@dataclass(frozen=True)
class Measured:
    value: float | None  # None: the whole metric is unknown
    reason: str | None = None  # why value is None
    unknown: int = 0  # unknown parts
    complete: bool = True  # False: value is a lower bound, as with PRs not gardened yet
    items: tuple[Mapping[str, object], ...] = ()  # JSON-ready; each has "state"
    extra: Mapping[str, object] = field(default_factory=dict)  # by_rung, repeats, not_gardened


@dataclass(frozen=True)
class MetricReport:
    metric_id: str
    title: str
    kind: Kind
    population: Population
    measured: Measured
    threshold: float | None
    status: ThresholdStatus | Literal["needs Agent identity"] | None  # None: no threshold


def threshold_status(measured: Measured, threshold: float) -> ThresholdStatus: ...
def judge(
    metric_id: str,
    title: str,
    kind: Kind,
    population: Population,
    measured: Measured,
    threshold: float | None,
) -> MetricReport: ...
```

- `load_metrics` collects every problem before it raises, in file order. Each names the key, what is wrong and the allowed values. Rulings on the forms the tests pin: `metrics.toml: window = 0: use an integer of at least 1`; `metrics.toml: unknown key 'mode'; it accepts window, thresholds, metric`; `metrics.toml [thresholds] alarm = 0: alarm names no metric; use one of <the known IDs, comma-separated>`; `metrics.toml [thresholds] reverts = -1: use a number of at least 0`; `metrics.toml [[metric]] #1: id = "Bad-ID": use lowercase letters, digits and _, starting with a letter`; `metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"`; `metrics.toml [[metric]] #2: label is not read by source "deployments"; it reads environment and count`. A TOML boolean is neither an integer nor a number. A missing file raises `.rapid-ship/metrics.toml: missing; run rapid-ship sync to add it with the defaults`.
- A threshold's key is valid when it names a basic metric, a `[[metric]]` ID or one of `code_metric_ids`. An ID is invalid when it repeats another, is a basic metric's, or fails `[a-z][a-z0-9_]*`.
- `gate_note` returns `.rapid-ship/gate.toml: devctl no longer reads it; delete it, and carry any threshold worth keeping into .rapid-ship/metrics.toml` while the file exists.
- `threshold_status`: unknown when `value` is `None`; breached when `value > threshold`; ok when `value + unknown <= threshold` and `complete`; unknown otherwise. `judge` gives `status=None` without a threshold, `"needs Agent identity"` when `measured.reason == NEEDS_IDENTITY`, and `threshold_status` otherwise.

- [ ] **Step 1: write the failing tests.** `test_devctl_metrics_settings.py`, docstring `Offline: metrics.toml in temporary directories.`:
  - `test_the_seed_loads_with_the_defaults`: the rendered seed gives `window == 30`, `thresholds == {"revisions": 1.0, "reverts": 1, "red_merges": 1, "closed_unmerged": 3}` and `metrics == ()`.
  - `test_every_problem_is_listed`: one file with `window = 0`, `mode = "walk"`, `[thresholds] alarm = 0` and `reverts = -1`, and a `[[metric]]` with `id = "Bad-ID"`, `title = "Bad"` and `source = "pagerduty"`; `problems` equals the six messages above, in that order.
  - `test_window_has_no_upper_limit`: `window = 100000` loads.
  - `test_a_threshold_names_a_basic_settings_or_code_metric`: `alarms = 0` with an `issues` metric `alarms`, and `probe_failures = 0` with `code_metric_ids={"probe_failures"}`, both load.
  - `test_each_source_needs_its_fields_and_reads_no_other`, parametrized: `issues` without `label`; `deployments` without `environment`; `count = "both"`; `label` on `deployments`; an empty `title`.
  - `test_ids_are_new_and_well_formed`: a repeated ID, `id = "reverts"`, and `id = "9x"` each give one problem.
  - `test_count_defaults_to_rollbacks` and `test_a_boolean_is_not_a_number` (`window = true`, `reverts = true`).
  - `test_a_missing_file_names_the_fix` and `test_the_gate_note_appears_only_while_gate_toml_exists`.

  `test_devctl_metrics_model.py`, docstring `Offline: the status rule.`: `test_threshold_status`, parametrized over `(value, unknown, complete, threshold, expected)`: `(2, 0, True, 1, "breached")`, `(1, 0, True, 1, "ok")`, `(0, 2, True, 1, "unknown")`, `(0, 1, True, 1, "ok")`, `(2, 5, True, 1, "breached")`, `(1, 0, False, 1, "unknown")`, `(None, 0, True, 1, "unknown")`, `(0.7, 0, True, 1.0, "ok")`; and `test_judge_shows_needs_agent_identity_in_place_of_a_status`.

  In `tests/test_kit_seed_keys.py`, `test_the_metrics_seed_names_every_key_its_loader_accepts`: the seed holds `window`, `[thresholds]` with each default key, and in its commented example `id`, `title`, `source`, `label`, `environment` and `count`. In `tests/test_kit_contents.py`, `test_every_stack_seeds_the_shared_files` expects `.rapid-ship/metrics.toml`. In `tests/test_kit_sync.py`, `test_sync_adds_metrics_toml_and_leaves_gate_toml`: a vendored project with a `gate.toml` and no `metrics.toml` gets the seed from `sync --in-place`, and its `gate.toml` is unchanged.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_metrics_settings.py tests/devctl/test_devctl_metrics_model.py tests/test_kit_seed_keys.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.metrics'`.
- [ ] **Step 3: implement** the seed, `kit.toml`, `settings.py` and `model.py`. Read the file with `tomllib`. Sync.
- [ ] **Step 4: run** the tests above with `tests/test_kit_contents.py` and `tests/test_kit_sync.py`; expected PASS. Then `uv run rapid-ship status --strict` and `./devctl check --tier fast`; both exit 0.
- [ ] **Step 5: commit** `feat: seed metrics.toml and validate it`.
- [ ] **Step 6: documents and verification.** `tools/AGENTS.md` and `ARCHITECTURE.md` name `devctl/metrics/` as built in part; `rapid_ship/templates/AGENTS.md` names the seed. Run the five checks with `--base main` and record them. Evidence: `Not covered: devctl metrics itself, which 3.4 adds`. Commit `docs: record PR 3.1's verification`.

## PR 3.2: the Corrections ledger (`spec3-ledger`, on `main`)

### Task 2: The ledger's parser and map rule 9

**Files:**
- Create: `devctl/ledger.py`, `devctl/check/map_ledger.py`, `tests/devctl/test_devctl_ledger.py`, `tests/devctl/test_devctl_map_ledger.py`
- Modify: `devctl/check/map.py` (`MapStep.run` adds `*ledger_errors(context, files)`); through `sync`: the vendored copies and the lock

**Interfaces:**
- Consumes: `codeowners.ledger_entry(path) -> bool`; `check.markdown.front_matter(text)`; `check.references.resolve(reference, context) -> str | None` and `path_exists(root, path) -> bool`.
- Produces:

```python
# devctl/ledger.py
LAST_PASS = "docs/corrections/last-pass.toml"
STATUSES = ("open", "proposed", "implemented", "rejected", "closed")
WRITERS = ("reviewer", "human", "incident")  # the values of `by`
REQUIRED_FIELDS = ("date", "by", "source", "category", "rungs", "prevention", "status")
OPTIONAL_FIELDS = ("pr", "path", "task", "prevented_by", "reason")


@dataclass(frozen=True)
class Entry:
    file: str  # the entry's own repository path
    date: datetime.date
    by: str
    source: str  # "session" or an https URL
    category: str
    rungs: tuple[int, ...]
    prevention: str
    status: str
    pr: int | None = None
    path: str | None = None
    task: str | None = None
    prevented_by: tuple[str, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class LastPass:
    through: str  # a full commit SHA
    date: datetime.date


def read_entry(file: str, text: str) -> Entry | list[str]: ...  # the entry, or every problem
def read_last_pass(text: str) -> LastPass | list[str]: ...


# devctl/check/map_ledger.py
def ledger_errors(context: CheckContext, files: Sequence[str]) -> list[str]: ...
```

- Each problem starts `<file>: <field>:` and says what is wrong and what the field accepts, such as `docs/corrections/a.md: rungs: [1, 1] repeats a rung; use distinct integers from 1 to 4`. Rulings: `date` is a YAML date or a string that `datetime.date.fromisoformat` reads, never a date with a time; `category` matches `[a-z0-9]+(?:-[a-z0-9]+)*`; a boolean is not an integer; `pr` is an integer of at least 1; `task` is non-empty text; `source` is `session` or starts with `https://`.
- `ledger_errors` checks each file in `files` for which `ledger_entry` holds and that exists, at any depth below `docs/corrections/`, as the ledger's Protected rule does. For an `implemented` entry, each `prevented_by` item passes when `resolve(item, context)` is `None` or `path_exists(root, item)`; otherwise it fails with resolve's message and `or a repository path that exists`. For `last-pass.toml`, `through` must name a commit: `context.repo.git("cat-file", "-e", f"{through}^{{commit}}")` must not raise `RepoError`. It reads the work tree; the Corrections metric reads `origin/<default branch>`.

- [ ] **Step 1: write the failing tests.** `test_devctl_ledger.py`, docstring `Offline: ledger entries and last-pass.toml from literal texts.`:
  - `test_a_valid_entry_reads_every_field`: Spec 3 section 9's example entry gives `Entry(file=..., date=date(2026, 10, 16), by="reviewer", ..., rungs=(1, 2), pr=42, path="src/app/links.py", status="open")`.
  - `test_each_invalid_field_names_what_it_accepts`, parametrized over `(front matter change, expected fragment)`: a missing `prevention`; `owner: x` (a field outside the table); `date: 2026-10-16T05:00:00`; `by: bot`; `source: http://x`; `category: Env_Read`; `rungs: []`, `[1, 1]`, `2`, `[true]` and `[5]`; `pr: "42"`; `status: Open`; `proposed` without `task`; `rejected` and `closed` without `reason`; `implemented` with `prevented_by: []`; and no front matter.
  - `test_last_pass_has_exactly_through_and_date`: a third key, a short SHA and a missing `date` each fail.

  `test_devctl_map_ledger.py`, docstring `Offline: map rule 9 in fixture repositories.`, built with `check_workspace.Workspace`:
  - `test_a_valid_ledger_passes`: two entries, the README and a `last-pass.toml` whose `through` is the workspace's first commit; the map step passes.
  - `test_an_invalid_entry_fails_the_map_step`: the step fails with the entry's problem in its details.
  - `test_prevented_by_resolves_a_reference_or_a_path`: `check:map` and `CODEOWNERS` pass; `check:nonesuch` and `docs/missing.md` fail.
  - `test_through_must_name_a_commit`: 40 zeros fail with `through names no commit in this repository`.
  - `test_the_readme_and_other_files_are_not_entries` and `test_an_entry_in_a_subdirectory_is_checked`.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ledger.py tests/devctl/test_devctl_map_ledger.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.ledger'`.
- [ ] **Step 3: implement** `ledger.py`, `map_ledger.py` and the two lines in `map.py`; format, check and sync.
- [ ] **Step 4: run** both files and `tests/devctl/test_devctl_map_*.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: check the Corrections ledger's format in the map step`.

### Task 3: The ledger's seeds, the `session` Rule, and PR 3.2's verification

**Files:**
- Create: `rapid_ship/templates/common/docs/corrections/README.md`
- Modify: `rapid_ship/templates/kit.toml` (`seeded` gains `docs/corrections/README.md`); `common/docs/AGENTS.md`; `common/AGENTS.md` and `python/AGENTS.md` (the Rule, last); `common/.github/CODEOWNERS` and `python/.github/CODEOWNERS`; `devctl/doctor_rules.py` (`PROTECTED_PATHS` gains `docs/corrections/README.md` after `.rapid-ship/`); `tests/test_kit_contents.py`, `tests/devctl/test_devctl_codeowners.py`, `tests/devctl/test_devctl_doctor_github.py`. This repository, by hand: `.github/CODEOWNERS`, `docs/AGENTS.md`, and the root `AGENTS.md`'s Development list. Through `sync`: `docs/corrections/README.md` and the lock. Documents: `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, this plan's Verification record.

**Interfaces:**
- The README states, for the agent that writes an entry: the file name `<date>-<category>-<n>.md` with the lowest free `n`, and renaming on a merge conflict; the fields and statuses, word for word with `devctl.ledger`'s names; what counts as a Correction; which changes need the owner; and that a `session` entry goes on the open PR that the Correction concerns, or on the next PR when none is open. It cites no rapid-ship document.
- `common/docs/AGENTS.md` gains `- [corrections](corrections/README.md) holds the Corrections ledger, one file per Correction. Its README defines the format and which changes need the owner.`
- Each CODEOWNERS seed gains `# /docs/corrections/README.md @{{owner}}` right after `# /.rapid-ship/ @{{owner}}`.
- This repository's root `AGENTS.md` gains, under Development: ``- When the owner corrects you in a Session, add an open entry to the Corrections ledger with `source: session`.``

- [ ] **Step 1: write the failing tests.**
  - `tests/test_kit_contents.py`: `test_root_guide_skeleton_has_its_headings_rules_links_and_pointers` and `test_the_python_root_guide_adds_its_rows_and_rules` expect the Rule last, with `advisory`. `test_the_ledger_readme_names_every_field_and_status`: every name in `REQUIRED_FIELDS`, `OPTIONAL_FIELDS`, `STATUSES` and `WRITERS` appears in the seeded README, as does `source: session`. `test_codeowners_has_the_walk_line_and_the_stack_protected_set` expects the ledger line right after `/.rapid-ship/` in both seeds.
  - `tests/devctl/test_devctl_codeowners.py`, `test_the_ledger_readme_is_protected_through_its_codeowners_line`: `protected_changes(patterns_in(<the rendered seed>), [FileChange("docs/corrections/README.md", "modified")]) == ["docs/corrections/README.md"]`, while an added `docs/corrections/2026-10-16-x-1.md` and a modified `docs/corrections/last-pass.toml` are not listed.
  - In `tests/devctl/test_devctl_doctor_github.py`, `test_flight_codeowners_needs_the_ledger_readme`: a Flight CODEOWNERS without the line reports `/docs/corrections/README.md` missing; Walk reports nothing.
- [ ] **Step 2: run** them; expected FAIL on the missing README and the missing lines.
- [ ] **Step 3: implement** the seeds, `kit.toml` and `PROTECTED_PATHS`; edit this repository's three files; sync.
- [ ] **Step 4: run** `tests/test_kit_contents.py`, `tests/test_kit_dogfood.py`, `tests/devctl/test_devctl_codeowners.py` and the doctor tests; expected PASS. Status, fast check. Commit `feat: seed the Corrections ledger and the Rule for Corrections given in a Session`.
- [ ] **Step 5: documents and verification.** Describe the ledger in the files above. Run the five checks with `--base main` and record them. Evidence: `Not covered: Corrections as a metric, which 3.5 adds; whether agents follow the advisory Rule`. Commit `docs: record PR 3.2's verification`.

## PR 3.3: the window (`spec3-window`, on 3.1's planning commit)

### Task 4: The GitHub reader, the API allowance and the window

**Files:**
- Create: `devctl/metrics/github.py`, `devctl/metrics/window.py`; `devctl/metrics/__init__.py` with Task 1's docstring, word for word, so that the two branches add the same file; `tests/devctl/metrics_fakes.py`, `tests/devctl/test_devctl_metrics_github.py`, `tests/devctl/test_devctl_metrics_window.py`
- Modify: through `sync`: the vendored copies and the lock; `tests/AGENTS.md`; this plan's Verification record

**Interfaces:**
- Consumes: `doctor_items.OwnerGet`, `gh_get`, `OwnerReadError(status, message)`; `repo.Repo` with `git(*args) -> str` and `RepoError`; `github_fakes.RecordedOwner` and `github_fakes.git` in tests.
- Produces:

```python
# devctl/metrics/github.py
class GitHubError(Exception):  # exit 2: names the path and the fix
    ...


class AllowanceUsedUp(Exception):
    reset: datetime | None  # UTC

    def reason(self) -> str: ...  # "GitHub API allowance used up; it resets at 06:12 UTC"


class GitHubReader:
    requests: int

    def __init__(self, repository: str, get: OwnerGet = gh_get) -> None: ...
    def get(self, path: str) -> object: ...  # below repos/<repository>/; "/x": the API path x
    def pages(
        self, path: str, until: Callable[[Mapping[str, object]], bool] | None = None
    ) -> Iterator[Mapping[str, object]]: ...


# devctl/metrics/window.py
class MetricsError(Exception):  # exit 2, with the fix
    ...


@dataclass(frozen=True)
class PullRequest:
    number: int
    author: str  # user.login
    merged_at: datetime | None
    closed_at: datetime | None
    merge_commit: str | None
    body: str
    url: str


@dataclass(frozen=True)
class Window:
    branch: str
    tip: str  # origin/<branch>'s commit
    size: int
    agent_login: str | None  # "<worker_app_slug>[bot]" with Agent identity, else None
    prs: tuple[PullRequest, ...]  # the population's PRs, newest first, at most size
    merged: tuple[PullRequest, ...]  # every PR the walk found, of any author, newest first
    not_fetched: int

    @property
    def since(self) -> datetime | None: ...  # merged_at of the oldest PR in prs


def default_branch(reader: GitHubReader) -> str: ...
def build_window(
    repo: Repo, reader: GitHubReader, branch: str, size: int, agent_login: str | None
) -> Window: ...
def is_ancestor(repo: Repo, commit: str, of: str) -> bool: ...  # False also for a missing commit
```

- `pages` adds `per_page=100&page=<n>` with `?` or `&`, and stops after a page of fewer than 100 items or before the first item for which `until` holds.
- The allowance: an `OwnerReadError` with status 403 or 429 whose message contains `rate limit`, in any case. The reader then reads `rate_limit` once, through `get("/rate_limit")`, for `resources.core.reset`, in epoch seconds, and raises `AllowanceUsedUp`; when that read fails, `reset` is `None` and the reason ends `; its reset time could not be read`. From then on, `get` raises the same `AllowanceUsedUp` without a call.
- Any other `OwnerReadError` becomes `GitHubError`: status `None` gives `gh could not run (<message>): install gh, then sign in with gh auth login`; 401 gives `GitHub refused <path> (HTTP 401): <message>; check gh auth status`; any other gives `GitHub refused <path> (HTTP <status>): <message>`.
- `build_window`: resolve the tip with `git rev-parse --verify --quiet refs/remotes/origin/<branch>^{commit}`; when it is missing, raise `MetricsError("origin/<branch> is missing: run git fetch origin")`. Walk `git rev-list --first-parent <tip>`. For each commit, read `commits/<sha>/pulls` and keep the PR whose `merge_commit_sha` is that commit; add it to `merged`, and to `prs` when `agent_login` is `None` or equals its author. Stop when `prs` holds `size` PRs or the history ends. `not_fetched` counts the population's PRs in one page of `pulls?state=closed&base=<branch>&sort=updated&direction=desc` that GitHub shows as merged and whose merge commit `is_ancestor` of the tip denies. `AllowanceUsedUp` propagates.
- `default_branch` reads `default_branch` from the repository.
- `metrics_fakes.MergedHistory(path)` builds a local repository with `merge(number, files, author="o-worker[bot]", body="", *, parents=1)`, which commits on `main` and serves `commits/<sha>/pulls` through a `RecordedOwner`; `push(files)`, which commits with no PR; and `publish()`, which sets `refs/remotes/origin/main`. `fake_gh(directory, served)` writes a `gh` executable with `check_workspace.fake_tool` that answers `gh api --method GET <path>` from `served`, answers an error entry with gh's stderr and exit 1, and logs each argv.

- [ ] **Step 1: write the failing tests.** `test_devctl_metrics_github.py`, docstring `Offline: the metrics reader against a recorded owner_get.`:
  - `test_pages_reads_until_a_short_page`: 100 items, then 3, give 103 items from `...?per_page=100&page=1` and `&page=2`; `test_pages_stops_before_the_item_until_selects`.
  - `test_the_allowance_stops_every_later_read`: a read fails with `OwnerReadError(403, "API rate limit exceeded for installation ID 1.")`, and `rate_limit` serves `resources.core.reset` for 2026-10-16 06:12 UTC; `AllowanceUsedUp.reason()` is `GitHub API allowance used up; it resets at 06:12 UTC`, and a later `get` raises it with `RecordedOwner.paths` unchanged.
  - `test_a_429_is_the_allowance_too` and `test_without_a_reset_time_the_reason_says_so`.
  - `test_other_errors_name_the_path_and_the_fix`, over status `None`, 401 and 500.

  `test_devctl_metrics_window.py`, docstring `Offline: the window over a local repository and recorded GitHub responses.`:
  - `test_the_walk_follows_first_parents_and_skips_direct_pushes`: three squash merges, a direct push, and a PR merged with a two-parent merge commit; `prs` holds the four PRs, newest first, and no commit of the merged branch is read.
  - `test_agent_identity_selects_the_worker_apps_prs` and `test_without_agent_identity_every_pr_counts`.
  - `test_a_window_that_is_not_full`: 2 PRs with `size` 30; `since` is the older PR's merge time.
  - `test_a_merged_pr_missing_locally_counts_as_not_fetched`.
  - `test_a_pr_merged_by_another_commit_is_skipped`.
  - `test_a_missing_origin_branch_names_the_fetch`.
  - `test_the_window_stops_at_size_without_reading_further`: `RecordedOwner.paths` names `size` commits and the one `pulls` page.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_metrics_github.py tests/devctl/test_devctl_metrics_window.py -q`; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** both modules and the fakes; format, check and sync.
- [ ] **Step 4: run** both files; expected PASS. Status, fast check. Commit `feat: read the metrics window from git and GitHub`.
- [ ] **Step 5: documents and verification.** `tests/AGENTS.md` names `metrics_fakes.py`. Run the five checks with the PR's base and record them. Evidence: `Not covered: the GitHub responses themselves, which Task 14 checks against real repositories`. Commit `docs: record PR 3.3's verification`.

## PR 3.4: `devctl metrics` (`spec3-command`, on `main` after 3.1 and 3.3)

### Task 5: Revisions and Red merges

**Files:**
- Create: `devctl/metrics/revisions.py`, `devctl/metrics/red_merges.py`, `tests/devctl/test_devctl_metrics_revisions.py`, `tests/devctl/test_devctl_metrics_red_merges.py`
- Modify: through `sync`: the vendored copies and the lock

**Interfaces:**
- Consumes: `GitHubReader`, `Window`, `Measured`.
- Produces:

```python
# devctl/metrics/revisions.py
def revisions(reader: GitHubReader, window: Window) -> Measured: ...


# devctl/metrics/red_merges.py
CI_WORKFLOW = "devctl-check.yml"


def red_merges(reader: GitHubReader, window: Window) -> Measured: ...
```

- `revisions` reads `pulls/<n>/reviews` page by page. It keeps reviews with state `CHANGES_REQUESTED` submitted no later than `merged_at`. Only when a review has state `DISMISSED` does it read `issues/<n>/events` and add each `review_dismissed` event whose `dismissed_review.state`, compared without case, is `changes_requested`, with that review's `commit_id`. A PR's Revisions are its distinct `commit_id`s. The value is their total divided by the window's PR count. Its items list each PR with at least one Revision, most first, as `{"pr": n, "state": "counted", "revisions": k}`. The caller gives `Measured(None, NEEDS_IDENTITY)` without Agent identity.
- `red_merges` reads `actions/workflows/devctl-check.yml/runs?head_sha=<sha>&event=push` for each merge commit, takes the run with the lowest `run_number`, and, when its `run_attempt` is above 1, reads `actions/runs/<id>/attempts/1`. A 404 means no run. Items: `{"pr": n, "state": "counted"}` for each red PR, and `{"pr": n, "state": "unknown", "detail": <why>}`, such as `push run cancelled` or `no push run`.

- [ ] **Step 1: write the failing tests**, docstrings `Offline: <metric> against recorded GitHub responses.`:
  - Revisions: `test_distinct_heads_count_once` (two reviewers request changes on head A, a second review on A, one on B: 2); `test_a_dismissed_change_request_counts` (a dismissed approval does not); `test_a_review_after_the_merge_is_ignored`; `test_approvals_and_comments_are_ignored`; `test_events_are_read_only_after_a_dismissed_review` (by `RecordedOwner.paths`); `test_the_value_is_the_mean_and_items_list_the_most_revised_first`.
  - Red merges: `test_failure_and_timed_out_are_red_and_success_green`; `test_a_cancelled_or_missing_run_is_unknown`; `test_a_passing_rerun_does_not_clear_a_failed_first_attempt`; `test_the_earliest_push_run_decides`; `test_a_missing_workflow_leaves_every_pr_unknown`.
- [ ] **Step 2: run** them; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** both; format, check, sync.
- [ ] **Step 4: run** them; expected PASS. Commit `feat: count Revisions and Red merges`.

### Task 6: The command, its report and its exit codes, and PR 3.4's verification

**Files:**
- Create: `devctl/metrics/report.py`, `devctl/metrics/command.py`, `tests/devctl/test_devctl_metrics_command.py`, `tests/devctl/test_devctl_metrics_report.py`, `tests/devctl/fixtures/metrics/report.json`
- Modify: `devctl/cli.py` (`build_parser` calls `command.register(commands)` after `hook.register`); through `sync`: the vendored copies and the lock. Documents: `tools/AGENTS.md`, `ARCHITECTURE.md`, the root `AGENTS.md`'s commands, Spec 3's status line, the index's Spec 3 section, this plan's Verification record

**Interfaces:**
- Consumes: Tasks 1, 4 and 5; `settings.load_project`; `repo.Repo.discover`.
- Produces:

```python
# devctl/metrics/report.py
@dataclass(frozen=True)
class Report:
    repository: str
    generated_at: datetime
    window: Window | None  # None: the window could not be read
    agent_identity: bool
    metrics: tuple[MetricReport, ...]
    notes: tuple[str, ...]


def render_text(report: Report) -> str: ...
def render_json(report: Report) -> str: ...
def exit_code(report: Report) -> int: ...  # 1 when any status is "breached", else 0


# devctl/metrics/command.py
def build_report(
    root: Path, window_size: int | None, reader: GitHubReader, now: Callable[[], datetime]
) -> Report: ...
def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None: ...
```

- Steps, as Spec 3 section 5 orders them. `[github] repository` unset raises `MetricsError('[github] repository is not set in .rapid-ship/project.toml; set it to "owner/name"')`. Metrics run in Spec 3 section 3's order, `revisions`, `reverts`, `red_merges`, `closed_unmerged` and `corrections`, then the project-defined metrics, each through one helper that turns `AllowanceUsedUp` into `Measured(None, error.reason())`. When `build_window` raises it, every metric is unknown with that reason and `window` is `None`. Later tasks add Reverts, Closed unmerged, Corrections and the project-defined metrics to the same list.
- `render_json` writes Spec 3 section 5's object exactly: `version` 1, `generated_at` and `since` as `YYYY-MM-DDTHH:MM:SSZ`, `window.population` `agent` or `all`, each metric's `id`, `title`, `kind`, `population`, `value`, `unknown`, `reason`, `items`, `threshold` and `status`, plus `by_rung`, `repeats` and `not_gardened` from `extra`.
- `render_text` follows Spec 3 section 5's sample: the title line, the identity and window line, the table with the columns `metric`, `population`, `value`, `suggested` and `status`, the line `Corrections are agent-reported: agents write the ledger entries they count.`, and a last line that counts breached and unknown thresholds and ends `rapid-ship takes no action.` A window that is not full reads `Window: 12 of 30 merged agent PRs, ...`; an empty one `Window: no merged agent PRs yet.`; an unknown value `unknown: <reason>`. Each note follows on its own line. When `not_fetched` is above 0, a note reads `<n> merged PRs are not in origin/<branch> yet: run git fetch origin and rerun`.
- The handler prints `devctl metrics: <message>` to stderr and returns 2 for `SettingsError`, `MetricsError`, `GitHubError` and `RepoError`. `--window` uses an argparse type that rejects values below 1, so argparse exits 2.

- [ ] **Step 1: write the failing tests.** `test_devctl_metrics_report.py`, docstring `Offline: the report's text and JSON from built reports.`: `test_the_json_matches_the_recorded_report` against `fixtures/metrics/report.json`; `test_the_text_follows_its_layout`, comparing every line of a report with one breach and one unknown; `test_a_window_that_is_not_full_or_empty_says_so`.

  `test_devctl_metrics_command.py`, docstring `Offline: ./devctl metrics through main() with a fake gh on PATH; simulated.`, with `metrics_fakes.fake_gh` and a `MergedHistory` checkout:
  - `test_no_breach_exits_0_and_a_breach_exits_1`.
  - `test_an_unknown_status_never_changes_the_exit_code`.
  - `test_each_failure_exits_2_and_names_its_fix`, parametrized: an invalid `metrics.toml` lists every problem; gh not on `PATH`; gh answering 401; no `origin/main`; no `[github] repository`.
  - `test_the_allowance_used_up_mid_run_leaves_the_rest_unknown`: the allowance runs out in Red merges; Revisions keeps its value; Red merges and every later GitHub metric are unknown with the reset time; the exit code is 0 or 1 by the finished thresholds.
  - `test_an_empty_window_makes_every_metric_unknown`; `test_without_agent_identity_revisions_needs_it`.
  - `test_window_overrides_the_setting` and `test_window_below_1_is_a_usage_error`.
  - `test_the_gate_note_and_the_not_fetched_note_are_printed`; `test_every_gh_call_is_a_get`, from the fake's log.
- [ ] **Step 2: run** them; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** `report.py`, `command.py` and the registration; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k metrics` and `tests/devctl/test_devctl_cli.py`; expected PASS. Run `./devctl metrics` in this repository and keep its output for the PR body. Status, fast check. Commit `feat: add devctl metrics`.
- [ ] **Step 5: documents and verification.** Run the five checks with `--base main` and record them. Evidence: the local `./devctl metrics` run, and `Not covered: Reverts, Closed unmerged and Corrections, which 3.5 adds`. Commit `docs: record PR 3.4's verification`.

## PR 3.5: Reverts, Closed unmerged and Corrections (`spec3-reverts`, on `main` after 3.2 and 3.4)

### Task 7: Reverts, whole and partial

**Files:**
- Create: `devctl/metrics/reverts.py`, `devctl/metrics/partial_reverts.py`, `tests/devctl/test_devctl_metrics_reverts.py`, `tests/devctl/test_devctl_metrics_partial_reverts.py`
- Modify: `devctl/metrics/command.py` (adds `reverts`); through `sync`: the vendored copies and the lock

**Interfaces:**
- Consumes: `Window.prs`, `Window.merged`, `Window.tip`; `Repo.git`; `window.is_ancestor`.
- Produces:

```python
# devctl/metrics/partial_reverts.py
SIMILARITY = 0.8
MIN_CHANGED_LINES = 3


@dataclass(frozen=True)
class Undoing:
    commit: str  # the earliest later commit that undid part of the PR
    whole: bool  # every file the PR changed was restored
    files: tuple[str, ...]  # restored files
    sections: tuple[str, ...]  # "<path>:<first>-<last>", the PR's hunk in its merge commit


def undoing(repo: Repo, merge_commit: str, tip: str) -> Undoing | None: ...


# devctl/metrics/reverts.py
def reverts(repo: Repo, window: Window, repository: str) -> Measured: ...
```

- `reverts` counts a PR once. A whole revert outranks a partial one. Signal 1: a commit in `<merge>..<tip>` has a message line matching `^This reverts commit ([0-9a-f]{40})\b` with the merge commit's full SHA. Signal 2: a PR in `merged` that merged after it has a body line `Reverts <owner>/<repo>#<n>`, compared without case. Signal 3: `undoing`, checked only for PRs that neither signal marked. Items: `{"pr": n, "state": "counted", "revert": "whole" | "partial", "commit": <sha>}`, and for a partial one `files` and `sections`. The text value reads `1 (#244 in part: 1 file)`.
- `undoing` diffs the merge commit against its first parent with `--no-renames`, so a rename is a deletion plus an addition. Restored file: a later commit in `git log --first-parent --format=%H <merge>..<tip> -- <file>` leaves `git rev-parse <commit>:<file>` equal to `<merge>^1:<file>`, both missing counting as equal. Undone section: for each `-U0` hunk of the PR with at least 1 removed line and at least `MIN_CHANGED_LINES` non-blank changed lines, a later commit's `-U0` hunk in the same file removes lines similar to the hunk's added lines and adds lines similar to its removed lines. Lines are stripped, joined with `\n`, and compared with `difflib.SequenceMatcher(None, a, b).ratio() >= SIMILARITY`. A binary file (`-` in `--numstat`) counts only as restored. `whole` holds when every changed file was restored.

- [ ] **Step 1: write the failing tests.** `test_devctl_metrics_reverts.py`, docstring `Offline: Reverts over local repositories.`: `test_a_git_revert_line_counts`; `test_a_reverted_merge_commit_counts`; `test_the_revert_buttons_body_line_counts`; `test_both_signals_count_once`; `test_an_abbreviated_sha_does_not_count`; `test_a_revert_by_hand_that_restores_every_file_is_whole`.

  `test_devctl_metrics_partial_reverts.py`, docstring `Offline: the content check over local repositories.`, each expecting a partial revert, or none where the name says so: `test_a_restored_file`; `test_an_added_file_deleted`; `test_a_deleted_file_brought_back`; `test_an_undone_section`; `test_a_section_undone_after_other_commits_moved_it`; `test_a_section_undone_with_small_edits_above_the_threshold`; `test_a_section_below_the_threshold_does_not_count`; `test_a_hunk_under_3_non_blank_lines_is_ignored`; `test_a_pure_addition_removed_later_does_not_count`; `test_a_rename_undone_is_a_whole_revert`; `test_a_binary_file_counts_only_when_restored`.
- [ ] **Step 2: run** them; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** both modules and add `reverts` to the command; format, check, sync.
- [ ] **Step 4: run** them and the command tests; expected PASS. Commit `feat: count whole and partial Reverts`.

### Task 8: Closed unmerged and Corrections, and PR 3.5's verification

**Files:**
- Create: `devctl/metrics/closed_unmerged.py`, `devctl/metrics/corrections.py`, `tests/devctl/test_devctl_metrics_closed_unmerged.py`, `tests/devctl/test_devctl_metrics_corrections.py`
- Modify: `devctl/metrics/command.py`, `tests/devctl/fixtures/metrics/report.json`; through `sync`: the vendored copies and the lock. Documents: `ARCHITECTURE.md`, `tools/AGENTS.md`, this plan's Verification record

**Interfaces:**
- Consumes: `GitHubReader`, `Window`; `devctl.ledger.read_entry`, `read_last_pass`, `LAST_PASS`; `codeowners.ledger_entry`; `window.is_ancestor`.
- Produces:

```python
# devctl/metrics/closed_unmerged.py
def closed_unmerged(
    reader: GitHubReader, window: Window, since: datetime, app_logins: frozenset[str]
) -> Measured: ...


# devctl/metrics/corrections.py
def corrections(repo: Repo, window: Window, since: datetime) -> Measured: ...
```

- `closed_unmerged` pages `pulls?state=closed&sort=updated&direction=desc` until an item's `updated_at` is before `since`. It keeps the population's PRs with no `merged_at` and a `closed_at` in the span. With Agent identity, it reads `issues/<n>/events` page by page and counts the PR only when the actor of the last `closed` event is not in `app_logins`, the two Apps' `<slug>[bot]`; without it, it reads no events.
- `corrections` reads entries at the window's tip, never the work tree: `git ls-tree -r --name-only <tip> -- docs/corrections/`, then `git show <tip>:<file>` for each path where `ledger_entry` holds. It counts entries dated on or after `since`'s UTC day. An entry that fails `read_entry` counts as unknown, with its path. `extra` holds `by_rung`, from `"1"` to `"4"`; `repeats`, the entries whose `category` has an earlier entry anywhere in the ledger, ordered by date and then file name; and `not_gardened`, the PRs in the window whose merge commit is not an ancestor of `through`, or every PR when `last-pass.toml` is absent at the tip. `complete` is false while `not_gardened` is not empty.

- [ ] **Step 1: write the failing tests.** Closed unmerged, docstring `Offline: Closed unmerged against recorded GitHub responses.`: `test_a_pr_a_person_closed_counts`; `test_a_pr_an_app_closed_does_not_count_with_agent_identity`; `test_a_pr_closed_reopened_and_merged_does_not_count`; `test_a_pr_closed_before_the_span_does_not_count`; `test_without_agent_identity_every_closed_pr_counts_and_no_events_are_read`.

  Corrections, docstring `Offline: Corrections over local repositories.`: `test_entries_in_the_span_are_counted_by_rung` (an entry with two rungs counts once in the total and once under each rung); `test_repeats_need_an_earlier_entry_of_the_category`; `test_prs_after_through_are_not_gardened`; `test_without_last_pass_no_pr_is_gardened`; `test_an_invalid_entry_is_unknown`; `test_entries_are_read_at_origin_not_in_the_work_tree`.
- [ ] **Step 2: run** them; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** both and add them to the command; refresh `report.json`; format, check, sync.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k "metrics or ledger"`; expected PASS. Status, fast check. Commit `feat: count Closed unmerged and Corrections`.
- [ ] **Step 5: documents and verification.** Run `./devctl metrics --json` here and keep its output for the PR body. Run the five checks with `--base main` and record them. Evidence: `Not covered: the similarity threshold's fit, which Task 14 measures`. Commit `docs: record PR 3.5's verification`.

## PR 3.6: project-defined metrics (`spec3-project-metrics`, on `main` after 3.4)

### Task 9: Settings sources and code metrics

**Files:**
- Create: `devctl/metrics/api.py`, `devctl/metrics/project.py`, `devctl/metrics/sources.py`, `tests/devctl/test_devctl_metrics_project.py`, `tests/devctl/test_devctl_metrics_sources.py`
- Modify: `devctl/metrics/command.py`; `rapid_ship/templates/common/tools/devctl/devctl_project/__init__.py` (the `metrics()` stub); `tests/test_kit_contents.py`; through `sync`: the vendored copies and the lock. This repository's own `tools/devctl/devctl_project/` gains no stub. Documents: `tools/AGENTS.md`, `ARCHITECTURE.md`, this plan's Verification record

**Interfaces:**
- Consumes: `MetricsSettings`, `SettingsMetric`, `load_metrics(root, code_metric_ids)`; `GitHubReader`; `Window`; `window.is_ancestor`.
- Produces:

```python
# devctl/metrics/api.py, which devctl_project imports
@dataclass(frozen=True)
class Item:
    label: str
    url: str | None = None
    time: datetime | None = None


@dataclass(frozen=True)
class Incident:
    url: str
    time: datetime
    cause: int | str | None = None  # a PR number, or a commit's full SHA


@dataclass(frozen=True)
class MetricResult:
    value: float | None
    reason: str | None = None
    items: tuple[Item | Incident, ...] = ()


@dataclass(frozen=True)
class MetricContext:
    repository: str
    since: datetime
    until: datetime
    prs: tuple[int, ...]
    get: Callable[[str], object]  # GET of a full API path, such as "repos/o/r/issues"


class Metric(ABC):
    id: str
    title: str

    @abstractmethod
    def measure(self, context: MetricContext) -> MetricResult: ...


class IncidentMetric(Metric):  # its items are Incident records
    ...


# devctl/metrics/project.py
MEASURE_SECONDS = 60.0


def project_metrics() -> tuple[Metric, ...]: ...
def measure(
    metric: Metric, context: MetricContext, timeout: float = MEASURE_SECONDS
) -> Measured: ...


# devctl/metrics/sources.py
def count_issues(
    reader: GitHubReader, label: str, since: datetime, until: datetime
) -> Measured: ...
def count_deployments(
    repo: Repo,
    reader: GitHubReader,
    environment: str,
    count: Literal["rollbacks", "failures"],
    since: datetime,
    until: datetime,
) -> Measured: ...
```

- `project_metrics` returns `devctl_project.metrics()` when the function exists, else `()`. It raises `MetricsSettingsError`, prefixed `devctl_project.metrics():`, when `metrics()` raises or returns something other than `Metric` instances, or when an ID is invalid, repeats, or matches a basic or settings metric. The command calls it before `load_metrics`, with its IDs as `code_metric_ids`.
- `measure` runs `metric.measure` in a daemon thread and waits `timeout` seconds; a metric still running is unknown with `measure ran longer than 60 seconds`. An exception gives unknown with `<type>: <message>`, and `AllowanceUsedUp` its own reason. A result is unknown when it is not a `MetricResult`, has no reason with a `None` value, has a value that is not a finite number of at least 0, or, for an `IncidentMetric`, holds an item that is not an `Incident`. Items become `{"label", "url", "time", "state": "counted"}`, or for an incident `{"url", "time", "cause", "state": "counted"}`. Its kind is `incident` when the metric is an `IncidentMetric`, whatever it returned.
- The command runs the settings sources through the same guard as `measure`: a `GitHubError` inside a project-defined metric makes that metric unknown with the error as its reason, and never exits 2.
- `count_issues` pages `issues?labels=<label, URL-encoded>&state=all&sort=created&direction=desc` until an item's `created_at` is before `since`. It counts items created in the span without a `pull_request` key.
- `count_deployments` pages `deployments?environment=<environment>`, newest first, and reads `deployments/<id>/statuses` for those it needs. Rollbacks: a deployment created in the span that has a `success` status, whose commit `is_ancestor` of the commit of the latest earlier deployment that has one, and is not the same commit. Failures: a deployment created in the span whose newest status is `failure` or `error`. A deployment whose commit is not in local history is an unknown item.
- The seeded stub returns `[]`. Its docstring says each metric must be deterministic and must not run a model, which devctl cannot check, and that a metric needing another credential reads it from the environment.

- [ ] **Step 1: write the failing tests.** `test_devctl_metrics_project.py`, docstring `Offline: code metrics with monkeypatched devctl_project.metrics.`: `test_a_code_metric_returns_a_value`; `test_a_code_metric_returns_unknown_with_a_reason`; `test_a_raising_metric_is_unknown_and_the_rest_stands`; `test_a_metric_past_its_timeout_is_unknown` (with `timeout=0.1`); `test_a_bad_result_is_unknown`, parametrized over `None`, `MetricResult(-1)`, `MetricResult(float("nan"))`, `MetricResult(None)` and an `IncidentMetric` that returns an `Item`; `test_an_incident_metric_returns_records_with_and_without_a_cause`; `test_an_incident_metric_is_marked_incident_when_empty_and_when_unknown`; `test_metrics_that_raises_or_repeats_an_id_exits_2`; `test_a_project_without_metrics_has_none`; `test_a_threshold_may_name_a_code_metric`.

  `test_devctl_metrics_sources.py`, docstring `Offline: the issues and deployments sources against recorded GitHub responses and a local repository.`: `test_issues_count_only_labelled_issues_opened_in_the_span`; `test_pull_requests_are_not_issues`; `test_a_deployment_of_an_older_commit_is_a_rollback`; `test_redeploying_the_same_commit_is_not_a_rollback`; `test_failures_count_the_last_status`; `test_a_deployment_outside_local_history_is_unknown`; `test_a_source_github_refuses_is_unknown_not_exit_2`.

  In `tests/test_kit_contents.py`, `test_devctl_project_is_seeded_and_the_environment_is_ignored` also expects `metrics()` returning `[]`.
- [ ] **Step 2: run** them; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** the three modules, the stub and the command's project-defined metrics, settings metrics before code metrics, each with population `repository`; format, check, sync.
- [ ] **Step 4: run** them and the command tests; expected PASS. Status, fast check. Commit `feat: add project-defined metrics`.
- [ ] **Step 5: documents and verification.** Run the five checks with `--base main` and record them. Evidence: `Not covered: a real incident tool, which a project's own metric reads`. Commit `docs: record PR 3.6's verification`.

## PR 3.7: the scheduled Action (`spec3-action`, on `main` after 3.4)

### Task 10: `[kit] optional` names Kit files too

**Files:**
- Modify: `rapid_ship/templates/kit.toml` (`optional_skills` becomes `optional`), `rapid_ship/kit/templates.py`, `sync.py`, `status.py`; `devctl/settings.py` (`OPTIONAL_SKILLS` becomes `OPTIONAL`, `ProjectSettings.optional_skills` becomes `optional`); the `[kit] optional` comment in each `project.toml` seed and in this repository's; `tests/test_kit_templates.py`, `tests/test_kit_sync.py`, `tests/test_kit_dogfood.py`, `tests/devctl/test_devctl_settings.py`, `tests/devctl/check_workspace.py`; the index's Kit manifest paragraph

**Interfaces:**
- `KitManifest.optional: frozenset[str]` holds skill names and template paths; `read_optional(root: Path) -> tuple[str, ...]` replaces `read_optional_skills`. `render_files` skips a template whose path, or whose skill, is in `manifest.optional` and not opted in. An unknown name raises `KitError("unknown optional Kit skill or file '<name>'")`, and a malformed list `expected a list of optional Kit skills or files`.
- devctl's `OPTIONAL: frozenset[str]` equals `kit.toml`'s `optional`, held by the parity test; its error reads `names of the Kit's optional skills and files: <names>`.
- Keep every test's name: `test_skill_links_follow_installed_skills_and_optional_skills_need_opt_in` and the others change their bodies only.

- [ ] **Step 1: write the failing test.** In `tests/test_kit_templates.py`, `test_an_optional_kit_file_needs_opt_in`: a template tree whose `kit.toml` lists `optional = [".github/workflows/extra.yml"]` renders no such file until `[kit] optional` names it. In `tests/test_kit_sync.py`, `test_opting_out_of_an_optional_file_deletes_an_unchanged_copy`.
- [ ] **Step 2: run** them; expected FAIL with `KeyError` or `TypeError` on the manifest.
- [ ] **Step 3: implement** the rename; sync.
- [ ] **Step 4: run** `uv run pytest tests/test_kit_*.py tests/devctl/test_devctl_settings.py -q`; expected PASS. Status, fast check. Commit `refactor: let [kit] optional name Kit files as well as skills`.

### Task 11: `--post`, the Action, this repository's opt-in, and PR 3.7's verification

**Files:**
- Create: `devctl/metrics/post.py`, `rapid_ship/templates/common/.github/workflows/rapid-ship-metrics.yml`, `tests/devctl/test_devctl_metrics_post.py`, `tests/devctl/test_devctl_metrics_workflow.py`
- Modify: `devctl/metrics/command.py` and `report.py` (`render_markdown`); `tests/devctl/metrics_fakes.py` (`fake_gh` also answers `--method POST` and `PATCH` with `--input -`, and logs each body it read on stdin); `kit.toml` and devctl's `OPTIONAL` (add `.github/workflows/rapid-ship-metrics.yml`); this repository's `.rapid-ship/project.toml` (`optional` names it; decision 5), then `sync` writes `.github/workflows/rapid-ship-metrics.yml`; the lock. Documents: `.github/AGENTS.md`, `tools/AGENTS.md`, `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, this plan's Verification record

**Interfaces:**
- Produces:

```python
# devctl/metrics/post.py
ISSUE_TITLE = "rapid-ship metrics"
MARKER = "<!-- rapid-ship-metrics -->"
ACTIONS_LOGIN = "github-actions[bot]"
GitHubWrite = Callable[[str, str, Mapping[str, object]], object]  # method, path, body -> JSON


def gh_write(method: str, path: str, body: Mapping[str, object]) -> object: ...
def status_changes(previous: Mapping[str, str], report: Report) -> list[str]: ...
def post(report: Report, reader: GitHubReader, write: GitHubWrite, summary: Path | None) -> str: ...


# devctl/metrics/report.py
def render_markdown(report: Report) -> str: ...
```

- `--post` refuses with exit 2 and `--post runs only in GitHub Actions with GH_TOKEN set; run ./devctl metrics without it to read the report` unless `GITHUB_ACTIONS == "true"` and `GH_TOKEN` is set.
- `gh_write` runs `gh api --method <method> <path> --input -` with the JSON body on stdin, through `run_process` and `owner_environment("gh")`; `post` passes paths below `repos/<repository>/`. A failure raises `GitHubError`, which exits 2.
- `post` appends `render_markdown` to the job summary file, `GITHUB_STEP_SUMMARY`. It finds the lowest-numbered issue in `issues?state=open&creator=github-actions%5Bbot%5D` whose body starts with `MARKER`. With one, it sets the body with `PATCH issues/<n>`; without one, it opens one with `POST issues`. The body is `MARKER`, the Markdown report, then `<!-- rapid-ship-metrics-json` and the report's JSON, with every `>` written `>`, then `-->`. It comments with `POST issues/<n>/comments` when `status_changes` is not empty, comparing with the statuses in the previous body's JSON; a body without readable JSON has none. On a new issue it comments only when a status is `breached` or `unknown`, listing each. It returns the issue's URL, which the command prints with each change.
- `status_changes` lists `<id>: <old> -> <new> (<value>, at most <threshold>)`, such as `closed_unmerged: ok -> breached (4, at most 3)`, with `none` for a status the previous report lacked.
- The workflow, whose action pins equal `devctl-check.yml`'s:

```yaml
# Managed by rapid-ship. Change the template in rapid-ship, then run `rapid-ship sync`.
name: rapid-ship metrics

on:
  schedule:
    - cron: "41 5 * * *"   # daily at 05:41 UTC; GitHub runs it on the default branch
  workflow_dispatch:

permissions: {}

concurrency:
  group: rapid-ship-metrics
  cancel-in-progress: false

jobs:
  metrics:
    name: rapid-ship metrics
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    permissions:
      contents: read
      pull-requests: read
      actions: read
      deployments: read
      issues: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
          fetch-depth: 0
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
      - name: Post the metrics report
        env:
          GH_TOKEN: ${{ github.token }}
        run: ./devctl metrics --post
```

- [ ] **Step 1: write the failing tests.** `test_devctl_metrics_post.py`, docstring `Offline: --post with a recorded reader and a recording writer; simulated.`. Every test clears `GITHUB_ACTIONS` and `GH_TOKEN` with `monkeypatch` first, because CI sets `GITHUB_ACTIONS`:
  - `test_post_is_refused_outside_github_actions`: without either variable, exit 2 and the message above.
  - `test_the_first_run_opens_the_issue_and_comments_only_on_a_breach_or_unknown`.
  - `test_a_later_run_replaces_the_body_and_comments_only_on_a_change`.
  - `test_the_issue_is_github_actions_lowest_open_one`: the marker on an issue opened by `octo`, and two issues opened by `github-actions[bot]`.
  - `test_a_body_without_json_has_no_previous_statuses`.
  - `test_the_job_summary_gets_the_markdown_report`.
  - `test_a_breach_exits_0_once_posted_and_a_failed_post_exits_2`, through `main()` with `fake_gh` and both variables set.
  - `test_the_json_comment_cannot_end_early`: a detail holding `-->` round-trips.

  `test_devctl_metrics_workflow.py`, docstring `Offline: the metrics workflow template.`: `test_triggers_permissions_and_concurrency`; `test_checkout_has_full_history_without_credentials`; `test_actions_are_pinned_like_the_ci_workflow`; `test_it_runs_post_with_the_github_token_only`; `test_the_vendored_copy_matches_its_template`.
- [ ] **Step 2: run** them; expected FAIL with `ModuleNotFoundError`.
- [ ] **Step 3: implement** `post.py`, `render_markdown`, the option and the template; list the template under `optional`; opt this repository in; sync. The full tier's `workflows` step runs zizmor on this repository's copy.
- [ ] **Step 4: run** `uv run pytest tests/devctl -q -k "metrics or settings"` and `tests/test_kit_*.py`, then `./devctl check --tier full --base main`; expected PASS, with `workflows` passed. Commit `feat: post the metrics report from a scheduled Action`. Commit the vendored workflow separately, `chore: run the metrics Action in this repository`, and have the owner push that commit.
- [ ] **Step 5: documents and verification.** Run the five checks with `--base main` and record them. Evidence: `Not covered: a real run of the Action, which Task 14 makes; its first scheduled run here after the merge`. Commit `docs: record PR 3.7's verification`.

## PR 3.8: the skills (`spec3-skills`, on `main` after 3.4, 7.1a, 7.2 and 7.3)

### Task 12: `rs-garden`

**Files:**
- Create: `skills/rs-garden/SKILL.md`, `tests/test_kit_garden_and_preflight.py`
- Modify: `tests/test_kit_skills.py` (`USER_INVOKED` gains `rs-garden` and `rs-preflight`); through `sync`: `.agents/skills/rs-garden/`, its `.claude/skills/rs-garden` link and the lock

**Interfaces:**
- Consumes: `.agents/skills/rs-health/references/audit.md` and `references/proposed-task.md` (plan 7's PR 7.3); `docs/corrections/README.md`; `./devctl metrics --json`'s `window.since`, `kind` and `items`; `devctl.hook.decide`, `hook_protocols.ToolCall`, `HookSettings` and `merge_guard.LocalBranches` in the test.
- `SKILL.md`: `name: rs-garden`; `description: Run a gardening pass: record new Corrections, find drift, propose prevention tasks and fix doc-only drift in one PR.`; `disable-model-invocation: true` (decision 4). It follows Spec 3 section 10: what gardening is, the three outputs, what it never does, the doc-only rule, steps 1 to 9, and scheduling with the warning about a Harness's own GitHub Action. It names the audit and the task shape as code spans with their repository paths, never as Markdown links, so plan 7's link test passes. Every command sits in a fenced `sh` block with `$REPO`, `$N` and `$THROUGH` as placeholders. Those blocks hold the Agent identity forms (`./devctl as worker push`, `./devctl as worker gh pr create`, `./devctl as worker gh issue create`), and the prose gives the forms without it. It adds entries only as `open` or `proposed`, and lists the entries that look ready for the owner's sign-off in the PR body. It names no tracker product.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_garden_and_preflight.py`, docstring `Offline: rs-garden's and rs-preflight's text and the commands they run.`:
  - `test_the_skills_run_no_command_the_guardrails_deny`: the fenced `sh` commands of `rs-garden/SKILL.md`, `rs-preflight/**/*.md` and `rs-setup/SKILL.md`, with continuation lines joined and comments dropped, each get `decide(...) == (None, "")` with Agent identity on, built as plan 7's `test_rs_health_runs_no_command_the_guardrails_deny` builds the call. At least ten commands are checked.
  - `test_rs_garden_reads_the_shared_audit_and_task_shape`: the skill names both paths, and both templates exist.
  - `test_rs_garden_names_its_inputs_and_outputs`: the skill contains `docs/corrections/last-pass.toml`, `./devctl metrics --json`, `"kind": "incident"`, `./devctl check --tier fast`, `status: open`, `status: proposed` and `Evidence`.
- [ ] **Step 2: run** it; expected FAIL on the missing skill.
- [ ] **Step 3: write** the skill; sync.
- [ ] **Step 4: run** it, `tests/test_kit_skills.py` and `tests/test_skill_discovery.py`; expected PASS for `rs-garden`'s tests. Commit `feat: add rs-garden`.

### Task 13: `rs-preflight`, `rs-setup`'s metrics step, and PR 3.8's verification

**Files:**
- Create: `skills/rs-preflight/SKILL.md`, `skills/rs-preflight/references/project-metrics.md`
- Modify: `skills/rs-setup/SKILL.md` (step 10), `tests/test_kit_garden_and_preflight.py`; through `sync`: the vendored copies, links and lock. Documents: `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, the root `AGENTS.md`, Spec 3's status line, the index, this plan's Verification record

**Interfaces:**
- `rs-preflight/SKILL.md`: `name: rs-preflight`; `description: Review with the owner whether this project is ready to widen the Mode toward Flight. Advisory; it never changes the Mode.`; `disable-model-invocation: true`. It follows Spec 3 section 11: purpose, when to run it, inputs, steps 1 to 10 with the table of what each metric tells the owner, outputs, and the Never list. It runs `./devctl doctor` first and `./devctl metrics --json` next. Its settings PR goes through `./devctl as worker` when Agent identity is on. When that PR adds the Action, the owner pushes the branch and opens the PR in a terminal.
- `references/project-metrics.md`: the two settings sources with a `[[metric]]` example each; a code metric; and an `IncidentMetric` that reads issues labelled `incident` and takes its cause from a body line `Cause: #<n>` or `Cause: <full SHA>`, as one fenced `python` block.
- `rs-setup` step 10, inserted after step 9: show the default thresholds and record the owner's values in `.rapid-ship/metrics.toml`; offer the Action, which `[kit] optional` and `sync --in-place` install, in the Setup PR that the owner pushes; with Agent identity off, say that Revisions report `needs Agent identity`; say that the owner sets up Alarms and incidents, which plug in as project-defined metrics, and that `rs-preflight` guides that before Flight.

- [ ] **Step 1: write the failing tests**, in the same file:
  - `test_rs_preflight_names_each_metric_and_its_inputs`: the skill contains each basic metric's ID, `./devctl doctor`, `./devctl metrics --json`, `every_pr`, `CODEOWNERS` and `last-pass.toml`.
  - `test_the_incident_metric_example_runs`: the reference's `python` block, executed with `devctl.metrics.api` importable, defines an `IncidentMetric` whose `measure`, against a `RecordedOwner` that serves two labelled issues, returns two `Incident` records, one with `cause == 12`.
  - `test_rs_setup_records_thresholds_and_offers_the_action`: `rs-setup/SKILL.md` contains `.rapid-ship/metrics.toml`, `.github/workflows/rapid-ship-metrics.yml`, `needs Agent identity` and `rs-preflight`.
- [ ] **Step 2: run** them; expected FAIL on the missing skill.
- [ ] **Step 3: write** both skills' files and the step; sync.
- [ ] **Step 4: run** `uv run pytest tests/test_kit_garden_and_preflight.py tests/test_kit_skills.py tests/test_skill_discovery.py -q`; expected PASS. Status, fast check. Commit `feat: add rs-preflight and rs-setup's metrics step`.
- [ ] **Step 5: documents and verification.** Run the five checks with `--base main` and record them. Evidence: `Not covered: the skills in a Session, which Task 14 runs`. Commit `docs: record PR 3.8's verification`.

## Owner steps

### Task 14: Live trials and this repository's dog-food runs (Owner step)

**Files:**
- Create, on `spec3-pages`: `docs/trials/<run date>-metrics-and-gardening.md`
- Modify, on `spec3-pages`: `docs/trials/AGENTS.md`

Preconditions: 3.5 to 3.8 have merged. Record `origin/main`'s commit, and run `rapid-ship` as `uvx --from <a checkout of that commit> rapid-ship`. A Session in a rapid-ship worktree runs rapid-ship's own hook, which denies pushes and `gh` writes on another repository, so every scratch-repository write goes into one logged script that the owner runs in a terminal.

- [ ] **Step 1 (agent): prepare.** Write `trial-setup.sh`, which logs each command, its output and its exit code, and the record's procedure with an empty results table: each command or prompt, the expected result and the observed one. The script creates the public repository `proxy-hatch/rs-metrics-trial` from `init --stack python`, records this repository's two Apps for it, and adds a project incident metric: an `IncidentMetric` in `devctl_project` that reads issues labelled `incident`, as `rs-preflight`'s reference shows. It opens and merges, as the Worker App where the case needs an agent PR:
  - for Reverts: a PR reverted with GitHub's Revert button (an owner click), one with `git revert`, one partly reverted by restoring one file, and one by undoing one section with small edits;
  - for Red merges: two PRs that pass alone and break the default branch together, and two quick merges whose push runs both complete;
  - for Closed unmerged: a PR the owner closes, and one the Worker App closes;
  - for Revisions: a change request from the Reviewer App that the owner dismisses;
  - for `rs-garden`: a review comment that the agent fixed, an optional suggestion that it did not take, a request from the owner, a `session` entry, two Corrections in one category, a severe first Correction, two `incident` issues naming a cause PR, one dated before the window's span, a swallowed exception, a stale README command, a function only a test calls, a departure from a starter Pattern, and an exception whose removal condition holds;
  - for deployments: GitHub deployments to `production`, including a rollback to an older commit and a failure.
- [ ] **Step 2 (Owner): run the script,** and the Revert button and dismissal clicks it lists.
- [ ] **Step 3 (Owner): `devctl metrics`.** Run `./devctl metrics` and `--json` in a clone, with Agent identity on and then with the App lines removed locally and not committed. Add `[[metric]]` entries for `incident` issues and `production` rollbacks and failures, and rerun. Record what the `review_dismissed` event and the Revert button's body line held, and each partial revert that the content check missed or invented, against the prepared list.
- [ ] **Step 4 (Owner): the Action.** Opt the scratch repository in, push the workflow, and run it with `workflow_dispatch` three times: the first opens the issue; the second, with nothing changed, posts no comment; the third, after the owner closes another PR unmerged, comments the change. Record the permissions it needed.
- [ ] **Step 5 (Owner): `rs-garden`** on the scratch repository in Claude Code and in agy (decision 3), each in a fresh clone. Record the entries, proposals and doc-only fixes against the prepared list, and the widened window that reached the earlier incident. Then run one unattended pass, `claude -p "/rs-garden"` from a scheduler, and record what the Harness had to allow in advance (decision 4).
- [ ] **Step 6 (Owner): `rs-preflight`** on hello-rapid-ship with Agent identity and with it removed locally, and on the scratch repository with its deployments. Record the review, the settings PR, the proposed tasks and the outside steps it guided.
- [ ] **Step 7 (Owner): dog-food here and on hello-rapid-ship.** On this repository, run `./devctl metrics`; the first `rs-garden` pass, whose PR the owner merges and whose proposals go to Linear; and `rs-preflight`. On hello-rapid-ship, run `./devctl metrics` and one `rs-garden` pass. Turn on the weekly pass of decision 5 once Step 5's unattended pass has worked.
- [ ] **Step 8 (implementer): write the record** from the owner's output, scrubbed of home and temporary paths, and add its line to `docs/trials/AGENTS.md`. `grep -n -e /Users/ -e /home/ -e /private/tmp -e /tmp/` on the record finds nothing. Each difference from the expected result becomes a fix PR from `main` and is rerun before 3.9 merges. When the trial moves the similarity threshold, that fix PR changes `SIMILARITY`, its tests, and Spec 3 sections 3 and 17. Commit `docs: record the metrics and gardening trials` on `spec3-pages`.

## PR 3.9: integration tests and pages (`spec3-pages`, on `main` after Task 14 and plan 6's PR 6.3)

### Task 15: Integration tests

**Files:**
- Modify: plan 6's integration test of `init` with a Python `backend/` and a TypeScript `frontend/`, or create `tests/test_kit_metrics_integration.py` beside it; `tests/AGENTS.md`

- [ ] **Step 1: write the tests**, docstring `Offline except for uv, npm and gitleaks: init and sync on scratch repositories.`, labelled as needing network access:
  - `test_init_seeds_the_metrics_and_ledger_files_for_each_stack`, over `--stack python`, `--stack agnostic`, `--stack typescript` and `--stack python=backend --stack typescript=frontend`: `.rapid-ship/metrics.toml`, `docs/corrections/README.md` and the root guide's `session` Rule exist, and `./devctl check` exits 0.
  - `test_sync_adds_the_new_seeds_keeps_gate_toml_and_lists_the_changed_guides`: a project vendored from the Kit before 3.1, with a `gate.toml`, gets `metrics.toml` and `docs/corrections/README.md` from `sync --in-place`, keeps `gate.toml`, and `status` lists `AGENTS.md` and `docs/AGENTS.md` as `template updated`.
- [ ] **Step 2: run** them; expected PASS, since the code is built. If one fails, fix the cause in a separate PR from `main` first.
- [ ] **Step 3: commit** `test: init and sync seed the metrics and ledger files`.

### Task 16: Spec 3's pages, documents, and PR 3.9's verification

**Files:**
- Create: `docs/concepts/metrics-and-corrections.md`; `docs/guides/measure-agent-delivery-with-devctl-metrics.md`, `docs/guides/count-alarms-incidents-and-rollbacks.md`, `docs/guides/keep-a-corrections-ledger-with-rs-garden.md`, `docs/guides/review-readiness-for-flight-with-rs-preflight.md`; `docs/reference/devctl-metrics.md`, `docs/reference/corrections-ledger.md`
- Modify: `website/docusaurus.config.js` (`exclude` gains `docs/corrections/**`); `docs/AGENTS.md`; `ARCHITECTURE.md`, the root `AGENTS.md`, `README.md`, Spec 3's status line, the index; this plan's Verification record

**Interfaces:**
- Every page carries plan 7's front matter, `status: built` and `status_detail: Spec 3`, and follows its page templates in `docs/AGENTS.md`: a concept page shows the case before the term; a guide's title states its outcome, and each step ends with output from Task 14's record, with the version and date it was recorded with; a reference page holds the synopsis, options and defaults, exit codes and one example. `devctl-metrics.md` lists every `metrics.toml` key and every JSON field. Pages link the ledger's README on GitHub, because the site leaves `docs/corrections/` out.

- [ ] **Step 1: write the pages** from Spec 3 and Task 14's record.
- [ ] **Step 2: build** with `npm --prefix website run build`; expected `[SUCCESS] Generated static files in "build".` with no broken link. Commit `docs: write Spec 3's pages`.
- [ ] **Step 3: documents and verification.** Mark Spec 3 built in `ARCHITECTURE.md`, the root `AGENTS.md`, `README.md`, Spec 3's status line and the index. Run the five checks with `--base main` and record them. Evidence: `Not covered: whether each page's prose matches the code beyond its recorded examples`. Commit `docs: record PR 3.9's verification`. Plan 7's PR 7.4 then lands, and it is GA.

## Verification record

Each PR's last task fills its own subsection with each command, its exit code and the summary line it printed. A blocked, skipped or simulated result is written as such, never as passed.

### 3.1

Pending.

### 3.2

Pending.

### 3.3

Pending.

### 3.4

Pending.

### 3.5

Pending.

### 3.6

Pending.

### 3.7

Pending.

### 3.8

Pending.

### 3.9

Pending.
