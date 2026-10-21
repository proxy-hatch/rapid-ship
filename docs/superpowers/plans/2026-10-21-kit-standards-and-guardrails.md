# Kit Standards and Harness Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the hook spike first. Then give every Kit project `devctl hook` with G1 to G5, G7, G8 and the merge guard, wired for Claude Code; the README.md and ARCHITECTURE.md seeds with map rule 8 and `./devctl doctor --settings`; the Pattern `task` key and Lessons section with the Python starter Patterns; the `SKILL.md` rule; the 1,500-line diff cap and the ledger rule; one CI concurrency group for each push run; documented, validated settings; and `sync`'s migrations.

**Architecture:** Four stacked PRs, 5.1 to 5.4, each reviewed and squash-merged on its own. devctl changes only in its template under `rapid_ship/templates/common/tools/devctl/devctl/`, and `uv run rapid-ship sync --in-place` vendors it. `devctl hook claude pre-tool` turns Claude Code's PreToolUse event into a `ToolCall` (`hook_protocols.py`), splits the command line and parses the git and gh forms (`command_line.py`), applies the rules (`hook.py`) and, for `gh pr merge` alone, the merge guard (`merge_guard.py`), which reads GitHub through doctor's `OwnerGet`. The Protected-set reader and the ledger rule live in `codeowners.py`, which the hook, the guard and the `diff` step share. `rapid_ship/kit/migrations.py` holds the migrations that `sync` proposes.

**Tech Stack:** Python 3.12+ standard library (`shlex`, `json`, `base64`, `difflib`, `tomllib`), PyYAML, git 2.31+, gh, uv, pytest, Ruff, mypy, import-linter, zizmor 1.30.1, Claude Code hooks (2.1.287 on record), Docusaurus for the docs site.

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), sections 3 (migrations), 4 (Kit contents, settings files, Patterns, Harness guardrails, the merge guard, the Protected set, CI), 5 (map rules, diff policy), 6 (`doctor --settings`, `devctl hook`), 10 (plan 5's tests and trials) and 11 (open questions). Plan 5 of 7 in the [plan index](2026-10-14-kit-and-setup.md), whose Conventions, Layout, Shared interfaces and "Plan 5: Kit standards and Harness guardrails" outline bind this plan.

**Status:** planned on 2026-10-21. Plan 4 and its follow-ups are merged (#31 to #33), and `v0.1.0` is tagged at `0e1d6d0`. This document lands in PR 5.1.

**Owner steps:** Task 1 and Task 8 are Owner steps that an agent prepares. The controller never dispatches an Owner step to an implementer subagent, and no agent runs one. The agent writes the procedure and the empty record. The owner runs every Harness Session, GitHub write and push. The implementer then writes from the owner's recorded output.

## Global Constraints

- Commands (index, Conventions): `devctl hook claude pre-tool`; `devctl doctor [--skills] [--settings]`; `rapid-ship sync [--in-place] [--revert PATH]...`.
- Exit codes: 0 success; 1 a check failed, something is missing, or a request was refused; 2 the command could not run. `devctl hook` follows Claude Code's hook protocol, a workaround documented in `hook_protocols.py`, and exits 1 on an internal error, never 2 (index; Spec 1 section 4).
- "The hook only denies or asks. It never allows or approves anything; with no rule matched it gives no decision" (Spec 1 section 4).
- Claude Code wiring: `PreToolUse` for `Bash`, `Edit`, `Write`, `MultiEdit` and `NotebookEdit`, running `"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool`, as Spec 1 section 4 states it once PR 5.1 has merged. Plan 5 wires no other Harness.
- The merge guard's four messages, exactly (Spec 1 section 4, step 5):
  - `merge denied: devctl check on PR #<n> at <commit> is <state>; wait for it to pass or fix what it reports, then merge again`
  - `merge denied: PR #<n> touches the Protected set (<paths>); the owner merges it in GitHub's web interface`
  - `merge denied: PR #<n> has no Reviewer App approval of its head <commit>; have the Reviewer review that commit, then merge again`
  - `merge denied: PR #<n> merges only at the checked head <commit>; run <the same command> --match-head-commit <commit>`
- The guard's check has passed only when the latest check run named `devctl check` (`CI_JOB_NAME`) from GitHub Actions (`GITHUB_ACTIONS_APP_ID = 15368`) completed on the head commit with the conclusion `success`.
- Diff cap: a change that adds and removes more than 1,500 lines in total fails, unless the PR's Evidence section has a line starting `Over the diff cap:` with a reason. The count leaves out files ending in `.md`, `.txt` or `.log`, binary files, Kit-managed files, `.rapid-ship/kit.lock`, `uv.lock` and `package-lock.json` (Spec 1 section 5).
- Seeded escalation kinds: `"a pull request that removes a behavioural test"` and `"a pull request that declares Over the diff cap:"` (Spec 1 section 4).
- Ledger rule: a change that modifies, renames or removes a Markdown file under `docs/corrections/` other than `README.md` is Protected; an added entry is not checked, whatever its status (Spec 1 section 5).
- Map rules 5, 7 and 8 as Spec 1 section 5 words them.
- File-size cap: `LINE_CAP = 500` lines for each `.py` file under `[map] source_roots`, which in this repository include the devctl templates. Task 3 puts the hook in four new modules, Task 9 moves map rule 7 out of `check/map.py` (443 lines), and Task 13 keeps `check/stacks/python.py` (469 lines) unchanged.
- devctl source is edited only under `rapid_ship/templates/common/tools/devctl/`. Run `uv run ruff format <files>` and `uv run ruff check <files>` on the changed template files, then `uv run rapid-ship sync --in-place`. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit the vendored copy. Tests import the vendored copy (`pyproject.toml` sets `pythonpath = ["tools/devctl", "tests/devctl"]`), so a step formats, checks and syncs before each test run that expects a pass.
- devctl starts processes only through `process.run_process`, called through the module. devctl depends only on PyYAML and PyJWT; plan 5 adds no dependency.
- No `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression carries an `rs-exception` marker and an entry in `.rapid-ship/exceptions.toml`.
- Write tests first. A test module's docstring starts `Offline:` and names what it simulates. A blocked, skipped or simulated check never counts as passed.
- `uv run pytest` and `./devctl check --tier full` need network access and gitleaks 8.30.1 on `PATH`.
- From Task 6 on, a Claude Code Session started in a checkout that holds the seeded `.claude/settings.json` runs `devctl hook`. Claude Code reads its hooks when a Session starts, so a Session started earlier, or in a checkout without the file, runs none:
  - G5 asks the owner before each Edit or Write of a Protected path. This repository's CODEOWNERS covers `/**/AGENTS.md`, `/.claude/`, `/.github/`, `/.rapid-ship/` and `/pyproject.toml`, which Tasks 6 to 9 and 13 to 16 edit. The controller runs those tasks in a Session the owner watches and answers; in a headless Session each such edit is denied, and the owner makes it.
  - Agent identity is on here, so G7 and G8 deny an agent's `git push` and its `gh` writes as the owner. Agents push only with `./devctl as worker push`, and run `gh` writes as `./devctl as <role> gh`.
  - If the hook blocks every call, the owner, never an agent, starts a Session with `--settings '{"disableAllHooks": true}'` to fix it, and the PR body records that Session.
- Branches: 5.1 `plan5-hook-spike` on `main`; 5.2 `plan5-guardrails` on 5.1; 5.3 `plan5-standards` on 5.2; 5.4 `plan5-settings-migrations` on 5.3. Each PR's base is the branch below it. After the PR below squash-merges, confirm that `main`'s tree equals that PR's head (`git diff --quiet main <the branch below>`), then run `git merge -s ours main`: the branch already holds that content, and a plain merge conflicts on this plan file. The owner merges every PR, unless they ask the controller to land the stack. The Worker App cannot push a commit that changes `.github/workflows/` (plan 4's Checked facts), so the owner pushes the commits of Tasks 14 and 15 that change this repository's CI workflow.
- Each PR's last task runs and records `uv run pytest -q`, `./devctl check --tier fast`, `uv run rapid-ship status --strict`, `./devctl check --tier full --base <PR base> --pr-body <body file>` and, when docs change, `npm --prefix website run build`, in the Verification record at the end of this plan.
- Ruff formats the `python` code blocks of a Markdown file, so keep this plan's blocks valid Python in Ruff's layout.
- Commit trailer: each commit ends with `Co-Authored-By: <the model that writes the commit>`, such as `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The merge guard runs out of time.** A `gh pr merge` whose reads are slow, or whose PR lists many file pages, can outlast Claude Code's hook timeout; a killed hook lets the merge through (Spec 1 section 4). Expected: the guard denies before a read that could end after the hook run's 300-second budget, which every merge on the line shares. Task 5's `test_the_guard_denies_before_a_read_could_pass_its_budget` pins it.
2. **A command line hides a second command.** Inputs: a newline, `&`, a subshell `( … )`, `$( … )` and backticks, a `#` comment, a heredoc, a redirection such as `2>&1`, a leading `NAME=value` and an absolute path to git. Expected: each simple command is checked, no heredoc body is, and no redirection's words count as arguments. Task 3's `SHELL` rows pin it.
3. **A Session edits in a linked worktree.** Claude Code keeps `$CLAUDE_PROJECT_DIR` at the main checkout while the edit lands in a worktree. Expected: G4 and G5 judge the path against the worktree that holds it, with that worktree's CODEOWNERS. Task 4's `test_run_hook_judges_an_edit_by_its_linked_worktree` pins it.
4. **An event the hook does not expect.** Inputs: a tool the hook does not wire, a missing `tool_input`, bytes that are not JSON, an unknown or missing Harness name. Expected: no decision for an unwired tool, exit 1 for the rest, never exit 2. Task 4's `test_the_hook_never_exits_2` pins it.
5. **`gh pr merge` names another repository.** Inputs: `-R x/y` and a PR URL. Expected: the guard reads that repository, not `[github] repository`. Task 5's `test_each_target_reads_its_pull_request` pins it.
6. **The guard counts the wrong review.** With Agent identity on, a mistake here silently merges a head the Reviewer never approved, the case the check exists to stop. Inputs: no review, a person's approval, the login `o-reviewer` without `[bot]`, an approval of an older commit, a later request for changes, a later comment or dismissed review, and reviews over two pages. Expected: only the Reviewer App's latest review that approves or requests changes decides, and the guard denies unless it approves the head SHA the guard read. Task 5's `test_with_agent_identity_a_head_without_the_reviewer_apps_approval_is_denied`, `test_comments_and_dismissed_reviews_do_not_decide` and `test_reviews_are_read_page_by_page` pin it.

## File Structure

`devctl/` means the template `rapid_ship/templates/common/tools/devctl/devctl/`; `sync` writes its vendored copy.

| File | PR | Responsibility |
| --- | --- | --- |
| `devctl/codeowners.py` | 5.2 | The Protected-set lines and their matcher, moved from `check/diff.py`; the ledger rule |
| `devctl/command_line.py` | 5.2 | Shell splitting, and the git and gh forms the guardrails read |
| `devctl/hook_protocols.py` | 5.2 | `Decision`, `ToolCall`, `HookSettings`, Claude Code's event and answer, the exit-code workaround |
| `devctl/hook.py` | 5.2 | G1 to G5, G7 and G8, the hook's settings, `devctl hook` |
| `devctl/merge_guard.py` | 5.2 | `find_merge` for G3, the merge guard (G9) |
| `common/.claude/settings.json` | 5.2 | The seeded Claude Code wiring |
| `devctl/check/map_skills.py` | 5.3 | Map rule 7, moved from `check/map.py` so `map.py` stays under the cap |
| `common/README.md`, `common/ARCHITECTURE.md` | 5.3 | The seeds that map rule 8 checks |
| `python/docs/patterns/python-*.md`, `python/src/__package__/{errors,inputs,settings,profiling}.py`, `python/tests/test_{errors,inputs,settings,profiling}.py` | 5.3 | The Python starter Patterns and the performance Pattern, with reference code and tests |
| `rapid_ship/kit/migrations.py` | 5.4 | `Migration`, `MIGRATIONS`, the pending edits and their PR body |

---

## PR 5.1: the hook spike (`plan5-hook-spike`, on `main`)

### Task 1: The hook spike (PRO-139), an Owner step

**Files:**
- Create: `docs/trials/<run date>-hook-spike.md`, named by the date the owner runs it
- Modify: `docs/trials/AGENTS.md`; Spec 1 sections 4, 10 and 11 where the record differs, and its status line; the plan index; the files that hold the stale text of Step 8; this plan, for the gate in Step 9 and the Verification record

**Interfaces:**
- Produces: the record's scrubbed Claude Code events, each a fenced `json` block under a heading named by its fixture file: `bash.json`, `bash-subagent.json`, `write.json`, `edit.json`, `notebook-edit.json`, and `multi-edit.json` only if Claude Code still has that tool. Task 4 copies them into `tests/devctl/fixtures/hooks/claude/`. Ruling: the events live in the record, because PR 5.1 holds no product or test code and the docs site publishes Markdown only.

- [ ] **Step 1 (agent): write the record's preparation.** Sections: Purpose, Versions, Setup, Procedure, Results, Events, Timing, Decisions, Limits. Setup holds, as fenced blocks:
  - the stand-in hook `standin.sh <harness>`, a POSIX `sh` script. It saves stdin, with its argv, `pwd`, `$CLAUDE_PROJECT_DIR` and its start and end times in milliseconds, to a new file under `$SPIKE_DIR/events/`. It then acts on the word in `$SPIKE_DIR/mode`: `none` exits 0 with no output; `deny` and `ask` print that Harness's documented deny or ask answer with the reason `spike: <mode>` and exit 0; `exit1` and `exit2` write `spike: exit <n>` to stderr and exit with that code; `sleep` sleeps 10 seconds, twice the wiring's `timeout` of 5;
  - the scratch repository `hook-spike`, made with `git init` outside rapid-ship, with one commit and a linked worktree from `git worktree add .worktrees/wt`, holding `spike.ipynb` with one code cell and three wiring files: `.claude/settings.json` (PreToolUse, matcher `Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor`), `.codex/hooks.json` (`PreToolUse` for `Bash` and `apply_patch`) and `.agents/hooks.json` (`PreToolUse`), each running `standin.sh` with its Harness name and `timeout` 5. The agent writes each answer format and wiring file from the Harness's current hook documentation and cites the page and the date.
- [ ] **Step 2 (Owner): the event matrix.** For each Harness (Claude Code, Codex, agy) and each Session kind (a lead Session; a subagent that the lead starts; a headless Session: `claude -p`, `codex exec` and agy's documented headless mode), set mode `none` and give this prompt: "Run `git status` in the shell. Write `spike.txt` containing `x`, then edit it so it contains `y`. Replace cell 0 of `spike.ipynb` with `print(1)`." In Claude Code also ask for `git status` through the Monitor tool. Record, for each cell, whether an event was saved for the shell call and for each file edit, and keep every event file.
- [ ] **Step 3 (Owner): the answers.** In a lead Session of each Harness, repeat the shell prompt with modes `deny`, `ask`, `exit1`, `exit2` and `sleep`. Record whether the call ran, what the Session showed and where the reason appeared, and, for `ask`, whether a prompt appeared. Repeat `deny`, `ask` and `exit1` in a subagent of each Harness, because whether a deny holds there decides that Harness's wiring, and `deny` and `ask` in each headless Session. In Claude Code also record: `ask` in `bypassPermissions` mode; and, in a Session started in `hook-spike`'s main checkout, a file edit inside `.worktrees/wt`, with the event's `cwd` and the hook's `$CLAUDE_PROJECT_DIR`.
- [ ] **Step 4 (Owner): Codex's review.** Record the trust and `/hooks` review prompts on the first run, and whether a changed `.codex/hooks.json` asks for a new review.
- [ ] **Step 5 (Owner): the hook's cost.** In this repository's main checkout, run `/usr/bin/time -p ./devctl --version` once after `rm -rf tools/devctl/.venv` and 20 times after that. Record the cold time and the warm median and maximum. Ruling: `./devctl --version` stands in for `devctl hook`, which does not exist yet; it pays the same uv and Python start and imports devctl's CLI. Task 8 times the real hook.
- [ ] **Step 6 (Owner): decide.** Record two decisions: whether G1 to G4 stay in the hook, from the measured time; and whether a follow-up adds the wiring for Codex and for agy, Codex's without G5 if its hooks cannot ask. Each yes becomes a backlog item in Linear, with its own plan later.
- [ ] **Step 7 (implementer): write the record.** Fill Versions, Results, Timing and Decisions from the owner's output, and label each result as observed in a run. Record Claude Code's documented default timeout for command hooks, with the page and the date. For each Claude Code event, replace the values of `session_id`, `prompt_id`, `transcript_path`, `tool_use_id`, `agent_id` and `scratchpad_dir` with `"<redacted>"`, the scratch repository's path with `/repo` (its worktree becomes `/repo/.worktrees/wt`) and any other home or temporary path with `<redacted>`; list the replaced fields, and put the event under its fixture heading. The docs site publishes trial records, so before the commit `grep -n -e /Users/ -e /home/ -e /private/tmp -e /tmp/ <the record>` finds nothing. Add one line to `docs/trials/AGENTS.md`: a spike record keeps its scrubbed event JSON in fenced blocks, and tests copy them as fixtures.
- [ ] **Step 8 (implementer): change the documents.**
  - Spec 1, where the record differs: section 4's wiring row (for example `MultiEdit` if Claude Code no longer has it, or `Monitor` if it runs shell commands that the hook does not see), the exit-code and timeout bullets, and which repository the hook reads in a linked worktree; section 10's spike bullet, as done; section 11's "Codex and agy wiring" and "The hook's cost", with the owner's decisions; the status line.
  - The plan index: plan 5's row and outline (5.1 built). Add this plan to the 5.1 file list.
  - The stale text, because plan 4 is merged in #31 to #33 and tagged `v0.1.0`: fix every hit of `git grep -n -i -e 'not merged yet' -e 'no release tag' -e 'no release is tagged' -e 'before the first tag'`, except in a built plan's conventions and task steps, which are its record, and in this plan's own instructions.
- [ ] **Step 9 (gate).** When the record changes what Tasks 3 to 8 assume (the event fields, the deny and ask answer, exit 1 not blocking, the tool names, the hook's working directory, the default hook timeout), revise those tasks in this document within PR 5.1. If the owner moves G1 to G4 out of the hook, stop: Tasks 3, 4 and 6 change, and the owner approves the revised plan before PR 5.2 starts.
- [ ] **Step 10: verify and commit.** Run the five checks of Global Constraints with `--base main`, and record the results in the Verification record. The PR body's Evidence section lists them, with `Not covered: no product code changed; the spike's observations are the owner's runs`. Commit `docs: record the hook spike (PRO-139)`.

## PR 5.2: guardrails (`plan5-guardrails`, on `plan5-hook-spike`)

### Task 2: The Kit version, and the Protected-set reader in `codeowners.py`

**Files:**
- Modify: `pyproject.toml:7`, `uv.lock`, `rapid_ship/templates/common/tools/devctl/pyproject.toml:8`, its `uv.lock`, `devctl/__init__.py:7`
- Create: `devctl/codeowners.py`, `tests/devctl/test_devctl_codeowners.py`
- Modify: `devctl/check/diff.py:57-62` and `:112-163`, `tests/devctl/test_devctl_diff_rules.py`, `tests/devctl/test_devctl_diff_removed_tests.py`, `tests/test_kit_contents.py:9`; the plan index's "Built interfaces" line for `check/diff.py`

**Interfaces:**
- Produces:

```python
# devctl/codeowners.py
CODEOWNERS_FILES = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")  # GitHub reads the first


def glob_match(pattern: str, path: str) -> bool: ...
def codeowners_match(pattern: str, path: str) -> bool: ...
def patterns_in(text: str) -> list[str]: ...  # owned lines, commented or not; never "*"
def protected_patterns(root: Path) -> list[str] | None: ...  # None: no file; OSError: unreadable
```

- [ ] **Step 1: start Kit version 0.2.0.** Set `0.2.0` in both `pyproject.toml` files and in `__version__`, run `uv lock` and `uv lock --project rapid_ship/templates/common/tools/devctl`, sync, then `uv run pytest tests/test_kit_contents.py -q`; expected PASS. Commit `chore: start Kit version 0.2.0`. Ruling: 0.2.0, because plan 5 is the first Kit change after the `v0.1.0` tag and its migration IDs and the warning period of Task 9 name the version.
- [ ] **Step 2: write the failing test.** Move the `codeowners_match` table and the first-file test from `test_devctl_diff_rules.py` into `test_devctl_codeowners.py`, importing from `devctl.codeowners`, and add:

```python
def test_patterns_in_reads_owned_lines_commented_or_not() -> None:
    text = "* @o\n# /.github/ @o\n/docs/ @o @team/x\n## a heading\n# prose without an owner\n"
    assert patterns_in(text) == ["/.github/", "/docs/"]
```

- [ ] **Step 3: run it.** `uv run pytest tests/devctl/test_devctl_codeowners.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.codeowners'`.
- [ ] **Step 4: move the code.** `_CODEOWNERS` becomes `CODEOWNERS_FILES`; `_OWNED_LINE`, `_glob`, `glob_match`, `codeowners_match` and `protected_patterns` move unchanged, and `protected_patterns` calls `patterns_in`. `check/diff.py` imports what it uses; no re-export. Update the three test imports and the index line.
- [ ] **Step 5: run.** Format, check and sync, then `uv run pytest tests/devctl tests/test_kit_contents.py -q`; expected PASS. `uv run rapid-ship status --strict`, `./devctl check --tier fast`.
- [ ] **Step 6: commit** `refactor: move the Protected-set reader into devctl/codeowners.py`.

### Task 3: `devctl hook`'s rules

**Files:**
- Create: `devctl/command_line.py`, `devctl/hook.py`, `devctl/merge_guard.py` (forms only), `devctl/hook_protocols.py` (types only)
- Test: `tests/devctl/test_devctl_hook_rules.py`, `tests/devctl/test_devctl_merge_guard_forms.py`

**Interfaces:**
- Consumes: `codeowners.codeowners_match`, `codeowners.protected_patterns` (Task 2); `settings.load_project`, `SettingsError`.
- Produces:

```python
# devctl/hook_protocols.py: Task 3 adds the types, Task 4 the protocol
Decision = Literal["deny", "ask"] | None  # None: no decision; the hook never allows


@dataclass(frozen=True)
class ToolCall:  # one Harness's pre-tool event, normalised
    shell: str | None  # the command line of a shell tool
    edits: tuple[Path, ...]  # the absolute, normalised paths a file-edit tool writes
    cwd: Path  # the event's working directory


@dataclass(frozen=True)
class HookSettings:  # what G5, G7, G8 and the merge guard read from the repository
    agent_identity: bool
    protected: tuple[str, ...]  # Protected-set patterns; empty without a CODEOWNERS file
    repository: str | None  # [github] repository
    reviewer_app_slug: str | None  # [github] reviewer_app_slug when Agent identity is on, else None


# devctl/command_line.py, with the git push and gh api parsers hook.py and merge_guard.py share
def simple_commands(line: str) -> list[tuple[str, ...]]: ...  # ValueError: shell rules fail


@dataclass(frozen=True)
class Command:
    words: tuple[str, ...]  # the simple command as written
    program: Literal["git", "gh", "other"]
    args: tuple[str, ...]  # after the program; for git, after its global options
    through_devctl: bool  # gh run as ./devctl as <role> gh


def parse_command(words: Sequence[str]) -> Command: ...


# devctl/merge_guard.py
@dataclass(frozen=True)
class LocalBranches:  # read from local git only for a git push, a ref path or a bare merge
    default: frozenset[str]  # origin/HEAD's branch; {"main", "master"} when that ref is missing
    current: str | None  # None: a detached HEAD


@dataclass(frozen=True)
class Merge:  # a way to land a change on the default branch, also through devctl as
    form: Literal["pr-merge", "admin", "push", "rest", "graphql"]  # G3 denies all but pr-merge
    target: str | None = None  # pr-merge: the number, URL or branch; None: the branch's PR
    repository: str | None = None  # pr-merge: the -R or --repo value
    head: str | None = None  # pr-merge: the --match-head-commit value
    command: tuple[str, ...] = ()  # pr-merge: the words, without --match-head-commit


def read_branches(root: Path) -> LocalBranches: ...
def find_merge(words: Sequence[str], branches: Callable[[], LocalBranches]) -> Merge | None: ...


# devctl/hook.py
def work_tree_root(path: Path) -> Path | None: ...  # the nearest ancestor that holds .git
def read_settings(root: Path) -> HookSettings | None: ...  # None: unreadable; reason on stderr
def decide(
    call: ToolCall,
    root: Path | None,
    settings: HookSettings | None,
    branches: Callable[[], LocalBranches],
) -> tuple[Decision, str]: ...  # G1 to G5, G7 and G8; the merge guard is run_hook's (Task 5)
```

Rulings for this task, each where Spec 1 section 4 leaves the choice:
- Ruling: the types, `HookSettings` included, live in `hook_protocols.py` and the parsers in `command_line.py`, because `hook.py` imports `merge_guard.py` and both use them; one module for each keeps every file far under the cap and the imports acyclic.
- Ruling: `simple_commands` reads a line as the shell splits it, because agents often add comments, heredocs and `2>&1` to their commands:
  - It first removes each heredoc body: after a line holding `<<WORD`, `<<-WORD`, `<<'WORD'` or `<<"WORD"` (not `<<<`), the lines up to and including the one that equals `WORD` (after leading tabs for `<<-`), for each heredoc on the line in turn. It also removes a file-descriptor number written directly before `<` or `>`, as in `2>&1`, so `gh pr merge 7 >/dev/null` keeps `7`. Both passes read the raw text, quotes included; a `<<WORD` inside quotes can hide the lines after it, a bypass that Spec 1 section 4's limits accept.
  - It then splits with Step 3's lexer. A `#` word stays an argument of its own simple command, where it can add a deny but never hides the next command.
  - A punctuation token that holds `<` or `>` is a redirection: it and the word after it are dropped. Every other punctuation token (`;`, `&&`, `||`, `|`, `&`, `(`, `)`, a backtick, a newline, or a run of them such as `);`) ends the simple command, so a subshell, `$( … )` and backticks give their contents as simple commands of their own.
  - A line that shell rules cannot split, such as one with an unclosed quote outside a heredoc, is an internal error (exit 1): the shell rejects it too.
- Ruling: `parse_command` skips leading `NAME=value` words, matches the program by basename (`git`, `gh`, `devctl`), counts `devctl as <role> gh <args>` as `gh <args>`, and skips git's global options before the subcommand (`-C`, `-c`, `--git-dir`, `--work-tree`, `--namespace` and `--config-env` take a value). It follows no other wrapper, as Spec 1 section 4's limits say.
- Ruling: G1 reads every word up to `--`; in `git commit`, `-n` also counts inside a short-option cluster, up to the first letter that takes a value (`m`, `F`, `C`, `c`, `t`, `S`, `u`). A message that is literally `--no-verify` is denied too; the agent rewords it.
- Ruling: in `git push`, a short-option cluster counts each letter up to `o`; the values of `-o`, `--push-option`, `--repo`, `--receive-pack` and `--exec` are skipped; the first positional word is the remote and the rest are refspecs; `--delete` or `-d` makes each refspec a deletion of that branch.
- Ruling: `gh api`'s method comes from `-X`, `-X<METHOD>`, `--method` or `--method=`, ignoring case; without one it is `POST` when `-f`, `-F`, `--field`, `--raw-field` or `--input` is given, else `GET`. The endpoint is the first positional word, without `https://api.github.com/`, a leading `/` and the query string. The subcommand of `gh pr` and `gh issue` is the first word that is not an option, skipping the value of `-R` or `--repo`; without one there is no write.
- Ruling: `find_merge`'s target is `gh pr merge`'s first positional word. It skips the values of `-b`/`--body`, `-F`/`--body-file`, `-t`/`--subject`, `-A`/`--author-email`, `--match-head-commit` and `-R`/`--repo`, given after a space or after `=`.
- Ruling: the GraphQL form matches when a `query=<text>` field given inline names one of Spec 1's seven mutations as a whole word; `query=@<file>` and `--input` are not read.
- Ruling: a call's repository is the nearest ancestor holding `.git`, a file or a directory, of the edited path for an edit and of `cwd` for a shell command. Claude Code keeps `$CLAUDE_PROJECT_DIR` at the main checkout while a Session edits in a linked worktree, whose own lock and CODEOWNERS its PR changes. An edit outside any repository gets no decision.
- Ruling: either settings file unreadable, or `project.toml` invalid, switches off all three of G5, G7 and G8, as Spec 1 section 4 says, and `read_settings` writes one stderr line: `devctl hook: <the SettingsError or OSError message>; G5, G7 and G8 give no decision`. A missing CODEOWNERS file is an empty Protected set and leaves G7 and G8 on, because nothing is unreadable and doctor reports the missing file.
- Ruling: rules apply in the order of the simple commands, and within one command G1, G2, G3, G7, G8; for an edit G4, then G5. The first deny wins, and a deny beats an ask.
- Ruling, the messages (Spec 1 gives what each names, not its text):

| Rule | Message |
| --- | --- |
| G1 | `G1: --no-verify and git commit -n skip the pre-commit hook; run the command without them, and fix what the hook reports` |
| G2 | `G2: a force push rewrites published history; push without --force, -f, --force-with-lease, --force-if-includes or a + refspec, and merge the base branch instead` |
| G3 | `G3: <form> lands a change on the default branch outside the merge guard; open a pull request and merge it with gh pr merge <number>, without --admin`, where `<form>` is `gh pr merge --admin`, `a git push to the default branch`, `a gh api write to a merge, ref or contents endpoint` or `a GraphQL merge or ref mutation` |
| G4 | `G4: rapid-ship writes .rapid-ship/kit.lock; change Kit files with rapid-ship sync instead` |
| G5 | `G5: <path> is in the Protected set (CODEOWNERS pattern <pattern>); the owner approves this edit` |
| G7 | `G7: Agent identity is on, so the Worker App pushes; run ./devctl as worker push` |
| G8 | `G8: Agent identity is on, so an App makes gh writes; run ./devctl as <role> gh <the same gh arguments>` |

- [ ] **Step 1: write the failing tests.** `test_devctl_hook_rules.py`, docstring `Offline: devctl hook's rules on normalised tool calls, with simulated settings and branches.`:

```python
ROOT = Path("/repo")
PROTECTED = ("/.github/", "/.claude/", "/**/AGENTS.md", "/.rapid-ship/")
OFF = HookSettings(
    agent_identity=False, protected=PROTECTED, repository="o/r", reviewer_app_slug=None
)
ON = HookSettings(
    agent_identity=True, protected=PROTECTED, repository="o/r", reviewer_app_slug="o-reviewer"
)
TASK = LocalBranches(frozenset({"main"}), "task")


def unread() -> LocalBranches:
    raise AssertionError("local git was read")


def decided(line: str, settings: HookSettings | None = OFF) -> tuple[Decision, str]:
    return decide(ToolCall(line, (), ROOT), ROOT, settings, lambda: TASK)


def edited(path: str, settings: HookSettings | None = OFF) -> tuple[Decision, str]:
    return decide(ToolCall(None, (ROOT / path,), ROOT), ROOT, settings, unread)


SHELL = [  # command line, the rule that denies it with Agent identity off (None: no decision)
    ("git status", None),
    ("git commit -m x --no-verify", "G1"),
    ("git commit -n -m x", "G1"),
    ("git commit -anm x", "G1"),
    ("git commit -mn", None),
    ("git -C sub commit -n -m x", "G1"),
    ("/usr/bin/git commit --no-verify -m x", "G1"),
    ("git push --no-verify origin task", "G1"),
    ("git push --force origin task", "G2"),
    ("git push -uf origin task", "G2"),
    ("git push --force-with-lease=task origin task", "G2"),
    ("git push --force-if-includes origin task", "G2"),
    ("git push origin +task", "G2"),
    ("git push origin task", None),
    ("git push origin main", "G3"),
    ("git push origin HEAD:refs/heads/main", "G3"),
    ("git push origin :main", "G3"),
    ("git push origin --delete main", "G3"),
    ("git push --all origin", "G3"),
    ("git push --mirror origin", "G3"),
    ("gh pr merge 7 --admin --squash", "G3"),
    ("./devctl as worker gh pr merge 7 --admin", "G3"),
    ("gh api -X PUT repos/o/r/pulls/7/merge", "G3"),
    ("gh api -XPUT /repos/{owner}/{repo}/pulls/7/merge", "G3"),
    ("gh api repos/o/r/merges -f base=main -f head=task", "G3"),
    ("gh api https://api.github.com/repos/o/r/git/refs/heads/main -X PATCH -f sha=a", "G3"),
    ("gh api repos/o/r/contents/a.md --method=PUT --input body.json", "G3"),
    ("./devctl as worker gh api -X PUT repos/o/r/pulls/7/merge", "G3"),
    (
        "gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'",
        "G3",
    ),
    ("gh api graphql -F query=@merge.graphql", None),
    ("gh api repos/o/r/git/refs/heads/task -X PATCH -f sha=a", None),
    ("gh api repos/o/r/pulls/7/merge", None),
    ("gh pr merge 7 --squash", None),
    ("echo ok; git push -f origin task", "G2"),
    ("make && git commit -n -m x", "G1"),
    ("false || git push origin main", "G3"),
    ("echo ok\ngit push --force origin task", "G2"),
    ("sleep 1 & git push origin main", "G3"),
    ("(cd sub && git push -f origin task)", "G2"),
    ("GIT_TRACE=1 git push -f origin task", "G2"),
    ("sh -c 'git push --force origin task'", None),
    ("git push origin main >/dev/null", "G3"),
    ("git push -f origin task 2>&1", "G2"),
    ("cd sub  # go there\ngit push -f origin task", "G2"),
    ("echo $(git push -f origin task)", "G2"),
    ("echo `git push -f origin task`", "G2"),
    ("cat <<'EOF' > notes.md\ngit push --force origin task\nEOF", None),
    ("git commit -n -F - <<EOF\nIt's done\nEOF", "G1"),
]
IDENTITY = [  # the rule that denies it with Agent identity on; with it off, no decision
    ("git push origin task", "G7"),
    ("git push --dry-run", "G7"),
    ("./devctl as worker push", None),
    ("gh pr create --fill", "G8"),
    ("gh pr merge 7 --squash", "G8"),
    ("gh pr -R o/r comment 7 -b hi", "G8"),
    ("gh pr view 7", None),
    ("gh pr checkout 7", None),
    ("gh issue comment 3 -b hi", "G8"),
    ("gh issue list", None),
    ("gh api repos/o/r/issues -X POST -f title=x", "G8"),
    ("gh api repos/o/r/issues -X GET -f state=open", "G8"),
    ("gh api repos/o/r/pulls/7", None),
    ("./devctl as worker gh pr create --fill", None),
    ("gh release create v1", None),
    ("gh pr create --body-file - <<'EOF'\nIt's done\nEOF", "G8"),
]
EDITS = [
    (".rapid-ship/kit.lock", "deny", "G4"),
    ("AGENTS.md", "ask", "G5"),
    ("src/app/AGENTS.md", "ask", "G5"),
    (".claude/settings.json", "ask", "G5"),
    ("src/app/core.py", None, None),
]


@pytest.mark.parametrize(("line", "rule"), SHELL)
def test_each_shell_rule_denies_its_forms(line: str, rule: str | None) -> None:
    decision, reason = decided(line)
    assert decision == ("deny" if rule else None)
    assert reason.startswith(f"{rule}: ") if rule else reason == ""


@pytest.mark.parametrize(("line", "rule"), IDENTITY)
def test_g7_and_g8_apply_only_with_agent_identity(line: str, rule: str | None) -> None:
    decision, reason = decided(line, ON)
    assert decision == ("deny" if rule else None)
    assert reason.startswith(f"{rule}: ") if rule else reason == ""
    assert decided(line, OFF) == (None, "")
    assert decided(line, None) == (None, "")


@pytest.mark.parametrize(("path", "decision", "rule"), EDITS)
def test_edit_rules(path: str, decision: Decision, rule: str | None) -> None:
    found, reason = edited(path)
    assert found == decision
    assert reason.startswith(f"{rule}: ") if rule else reason == ""


def test_g1_to_g4_apply_and_g5_gives_no_decision_with_unreadable_settings() -> None:
    for line in ("git commit -n -m x", "git push -f origin task", "git push origin main"):
        assert decided(line, None)[0] == "deny"
    assert edited(".rapid-ship/kit.lock", None)[0] == "deny"
    assert edited("AGENTS.md", None) == (None, "")


def test_an_edit_outside_the_repository_gets_no_decision() -> None:
    call = ToolCall(None, (Path("/elsewhere/AGENTS.md"),), ROOT)
    assert decide(call, ROOT, OFF, unread) == (None, "")


@pytest.mark.parametrize(
    ("line", "branches", "rule"),
    [
        ("git push origin master", LocalBranches(frozenset({"main", "master"}), "task"), "G3"),
        ("git push origin master", LocalBranches(frozenset({"trunk"}), "task"), None),
        ("git push origin trunk", LocalBranches(frozenset({"trunk"}), "task"), "G3"),
        ("git push", LocalBranches(frozenset({"main"}), "main"), "G3"),
        ("git push origin HEAD", LocalBranches(frozenset({"main"}), "main"), "G3"),
        ("git push 2>&1", LocalBranches(frozenset({"main"}), "main"), "G3"),
        ("git push", TASK, None),
        ("git push", LocalBranches(frozenset({"main"}), None), None),
    ],
)
def test_a_push_to_the_default_branch(line: str, branches: LocalBranches, rule: str | None) -> None:
    assert decide(ToolCall(line, (), ROOT), ROOT, OFF, lambda: branches)[0] == (
        "deny" if rule else None
    )


def test_local_git_is_read_only_for_a_push_or_a_ref_path() -> None:
    reads: list[str] = []

    def branches() -> LocalBranches:
        reads.append("read")
        return TASK

    for line in ("git status", "gh pr view 7", "gh api -X PUT repos/o/r/pulls/7/merge"):
        decide(ToolCall(line, (), ROOT), ROOT, OFF, branches)
    assert reads == []
    for line in ("git push origin task", "gh api -X PATCH repos/o/r/git/refs/heads/x"):
        decide(ToolCall(line, (), ROOT), ROOT, OFF, branches)
    assert reads == ["read", "read"]


def test_simple_commands_split_with_shell_rules() -> None:
    found = simple_commands("a 'b;c' && d | e; f || g & h\ni")
    assert found[0] == ("a", "b;c")
    assert [words[0] for words in found[1:]] == ["d", "e", "f", "g", "h", "i"]
    with pytest.raises(ValueError, match="closing quotation"):
        simple_commands("git commit -m 'x")


def test_simple_commands_drop_redirections_and_heredoc_bodies() -> None:
    assert simple_commands("git push 2>&1 | tee log") == [("git", "push"), ("tee", "log")]
    assert simple_commands("gh pr merge 7 >/dev/null") == [("gh", "pr", "merge", "7")]
    line = "cat <<'EOF' > notes.md\nIt's done\nEOF\ngit status"
    assert simple_commands(line) == [("cat",), ("git", "status")]
```

Also in `test_devctl_hook_rules.py`, with `new_workspace` (local git only, no network):
  - `test_read_branches_from_local_git`: a fresh workspace with one commit reads `LocalBranches(frozenset({"main", "master"}), "main")`; after `update-ref refs/remotes/origin/trunk HEAD` and `symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk`, `default == frozenset({"trunk"})`; after `checkout --detach`, `current is None`.
  - `test_an_edit_in_a_linked_worktree_belongs_to_that_worktree`: with a worktree added at `<main>/.worktrees/wt`, `work_tree_root(<main>/.worktrees/wt/.rapid-ship/kit.lock) == <main>/.worktrees/wt`, and `work_tree_root(Path("/")) is None`. Task 4's `test_run_hook_judges_an_edit_by_its_linked_worktree` checks `run_hook` on such edits.
  - `test_unreadable_settings_switch_off_g5_g7_g8_and_say_why`: a `project.toml` holding `[linear]` gives `read_settings(root) is None`, and its one stderr line starts `devctl hook: `, contains `[linear] was removed` and ends `; G5, G7 and G8 give no decision`; a CODEOWNERS that is not UTF-8 gives `None` too.
  - `test_a_missing_codeowners_is_an_empty_protected_set`: with `project.toml` holding `stack = "python"` and no CODEOWNERS, `read_settings(root) == HookSettings(False, (), None, None)`.
  - `test_read_settings_takes_the_reviewer_app_slug_with_agent_identity`: with `project.toml` recording `repository = "o/r"` and both Apps, with the slugs `o-worker` and `o-reviewer`, `read_settings(root)` has `agent_identity` true and `reviewer_app_slug == "o-reviewer"`.

`test_devctl_merge_guard_forms.py`, docstring `Offline: find_merge on command lines; no git and no GitHub.`:

```python
TASK = LocalBranches(frozenset({"main"}), "task")


def unread() -> LocalBranches:
    raise AssertionError("local git was read")


FORMS = [  # command line, form, target
    ("gh pr merge", "pr-merge", None),
    ("gh pr merge 7 --squash --auto", "pr-merge", "7"),
    ("gh pr merge https://github.com/x/y/pull/7", "pr-merge", "https://github.com/x/y/pull/7"),
    ("gh pr merge task -b 'body text' --squash", "pr-merge", "task"),
    ("./devctl as worker gh pr merge 7 --squash", "pr-merge", "7"),
    ("gh pr merge --subject x 7", "pr-merge", "7"),
    ("gh pr merge --match-head-commit=abc -R x/y 7", "pr-merge", "7"),
    ("gh pr merge 2>&1", "pr-merge", None),
    ("gh pr merge 7 >/dev/null", "pr-merge", "7"),
    ("gh pr merge 7 --admin", "admin", None),
    ("./devctl as reviewer gh pr merge 7 --admin", "admin", None),
    ("git push origin main", "push", None),
    ("gh api -X PUT repos/o/r/pulls/7/merge", "rest", None),
    ("./devctl as worker gh api -X PUT repos/{owner}/{repo}/pulls/7/merge", "rest", None),
    (
        "gh api graphql -f query='mutation { updateRef(input: {}) { ref { name } } }'",
        "graphql",
        None,
    ),
    ("gh pr view 7", None, None),
    ("gh api -X GET repos/o/r/contents/a.md", None, None),
    ("git push origin task", None, None),
]


@pytest.mark.parametrize(("line", "form", "target"), FORMS)
def test_find_merge_recognises_each_form(line: str, form: str | None, target: str | None) -> None:
    merge = find_merge(simple_commands(line)[0], lambda: TASK)
    assert ((merge.form, merge.target) if merge else (None, None)) == (form, target)


def test_a_pr_merge_keeps_its_repository_head_and_command() -> None:
    words = simple_commands("gh pr merge 7 -R x/y --match-head-commit abc --squash")[0]
    assert find_merge(words, unread) == Merge(
        "pr-merge",
        "7",
        repository="x/y",
        head="abc",
        command=("gh", "pr", "merge", "7", "-R", "x/y", "--squash"),
    )
```

- [ ] **Step 2: run them.** `uv run pytest tests/devctl/test_devctl_hook_rules.py tests/devctl/test_devctl_merge_guard_forms.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.hook'`.
- [ ] **Step 3: implement** the Interfaces above. After the heredoc and descriptor passes, `simple_commands` splits with this lexer:

```python
lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&`\n")
lexer.whitespace = lexer.whitespace.replace("\n", "")  # a newline separates commands
lexer.whitespace_split = True  # keeps HEAD:refs/heads/main, +task and {owner} whole
lexer.commenters = ""  # shlex's default comment would swallow the newline after it
```

  `read_branches` runs `git symbolic-ref --quiet refs/remotes/origin/HEAD` and `git symbolic-ref --quiet --short HEAD` through `process.run_process` in `root`; any failure gives `{"main", "master"}` or `None`. `read_settings` uses `load_project` and `protected_patterns`, and takes `reviewer_app_slug` from `reviewer_app.slug` when Agent identity is on.
- [ ] **Step 4: run.** Format, check and sync, then run the two files; expected PASS. `uv run rapid-ship status --strict`, `./devctl check --tier fast`.
- [ ] **Step 5: commit** `feat: add devctl hook's rules G1 to G5, G7 and G8`.

### Task 4: Claude Code's hook protocol and `devctl hook`

**Files:**
- Modify: `devctl/hook_protocols.py`, `devctl/hook.py`, `devctl/cli.py` (`hook.register(commands)` after `identity.register`)
- Create: `tests/devctl/fixtures/hooks/claude/*.json`, copied from Task 1's record
- Test: `tests/devctl/test_devctl_hook_protocol.py`

**Interfaces:**
- Consumes: Task 3's `ToolCall`, `Decision`, `decide`, `read_settings`, `work_tree_root`, `read_branches`; `doctor_items.OwnerGet` and `gh_get`.
- Produces:

```python
# devctl/hook_protocols.py
WiredHarness = Literal["claude"]  # plan 5; each later wiring adds its Harness and protocol
WIRED_TOOLS = ("Bash", "Edit", "Write", "MultiEdit", "NotebookEdit")  # as Spec 1 section 4 has it
HOOK_COMMAND = "devctl hook claude pre-tool"


def read_event(harness: WiredHarness, payload: bytes) -> ToolCall: ...  # ValueError: malformed
def answer(harness: WiredHarness, decision: Decision, reason: str) -> tuple[str, int]: ...


# devctl/hook.py
def run_hook(call: ToolCall, owner_get: OwnerGet) -> tuple[Decision, str]: ...
def hook_command(args: argparse.Namespace) -> int: ...  # never 2
def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None: ...
```

`read_event` takes `tool_input.command` for `Bash`, `file_path` for `Edit`, `Write` and `MultiEdit`, and `notebook_path` for `NotebookEdit`; a relative path is resolved against `cwd`, and every path is normalised with `os.path.normpath`, without following symlinks. Any other tool gives `ToolCall(None, (), cwd)`. An event whose `hook_event_name` is not `PreToolUse`, or that lacks `cwd`, `tool_name` or `tool_input`, is a `ValueError`. `answer` returns `("", 0)` for no decision, and for `deny` or `ask` one line of JSON with exit 0. The module docstring documents the workaround: Claude Code blocks on exit 2, so the hook never exits 2; exit 1 is a non-blocking error, so the call goes through; and, from Spec 1 section 4, the cases before devctl runs (the shim's 127, uv's own exit 2, a parse failure, a timeout).

`hook_command` reads stdin, calls `read_event`, `run_hook` and `answer`, and writes stdout. It catches `ValueError`, `OSError`, `RepoError` and `SettingsError`, writes `devctl hook: internal error: <message>; the tool call goes through` to stderr and returns 1. Ruling: `register` declares `harness` and `event` as optional positional strings (`nargs="?"`), not argparse choices, so a missing or unknown Harness or event is the hook's exit 1 (`devctl hook: unknown Harness '<name>'; this devctl wires claude only`, or `devctl hook: usage: devctl hook claude pre-tool`), never argparse's exit 2, which Claude Code reads as block.

- [ ] **Step 1: copy the fixtures.** Copy each scrubbed event from Task 1's record into `tests/devctl/fixtures/hooks/claude/<name>.json`, byte for byte.
- [ ] **Step 2: write the failing tests.** Docstring: `Offline: Claude Code's hook protocol, from events recorded in the hook spike; no Session runs.`

```python
FIXTURES = Path(__file__).parent / "fixtures" / "hooks" / "claude"
REPO = Path("/repo")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("bash.json", ToolCall("git status", (), REPO)),
        ("bash-subagent.json", ToolCall("git status", (), REPO)),
        ("write.json", ToolCall(None, (REPO / "spike.txt",), REPO)),
        ("edit.json", ToolCall(None, (REPO / "spike.txt",), REPO)),
        ("notebook-edit.json", ToolCall(None, (REPO / "spike.ipynb",), REPO)),
    ],
)
def test_read_event_normalises_each_recorded_event(name: str, expected: ToolCall) -> None:
    assert read_event("claude", (FIXTURES / name).read_bytes()) == expected


def test_an_unwired_tool_gives_an_empty_call() -> None:
    event = json.loads((FIXTURES / "bash.json").read_text())
    event["tool_name"] = "Read"
    assert read_event("claude", json.dumps(event).encode()) == ToolCall(None, (), REPO)


@pytest.mark.parametrize("decision", ["deny", "ask"])
def test_a_decision_is_one_json_line_with_exit_0(decision: Decision) -> None:
    stdout, code = answer("claude", decision, "G1: why")
    assert code == 0
    assert json.loads(stdout) == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": "G1: why",
        }
    }


def test_no_decision_is_empty_with_exit_0() -> None:
    assert answer("claude", None, "") == ("", 0)
```

  Then, through `devctl.cli.main(["hook", "claude", "pre-tool"])` with `sys.stdin` patched and an event whose `cwd` is a `new_workspace`:
  - `test_a_recorded_bash_event_with_a_force_push_is_denied`: stdout's `permissionDecision` is `deny` and its reason starts `G2: `; exit 0.
  - `test_a_harmless_event_gets_no_decision`: stdout is empty; exit 0.
  - `test_the_hook_never_exits_2`, parametrized over: bytes that are not JSON; `{}`; a `PostToolUse` event; an event without `tool_input`; Harness `codex`; event `post-tool`; `main(["hook"])`; `main(["hook", "claude"])`; a `cwd` with an invalid `project.toml`. Each returns 0 or 1, never 2, and each error case writes a stderr line that starts `devctl hook: `.

  And, calling `run_hook` with an `owner_get` that fails the test:
  - `test_run_hook_judges_an_edit_by_its_linked_worktree`: `<main>` commits `.rapid-ship/project.toml` (`stack = "python"`) and a `.github/CODEOWNERS` holding only `* @o`; a worktree on a new branch at `<main>/.worktrees/wt` then writes its own CODEOWNERS, `* @o\n# /**/AGENTS.md @o\n`. With the event's `cwd` at `<main>`, `run_hook` denies an edit of `<wt>/.rapid-ship/kit.lock` with a reason that starts `G4: `, asks for `<wt>/AGENTS.md` with `G5: `, and gives no decision for `<main>/AGENTS.md`.
- [ ] **Step 3: run** `uv run pytest tests/devctl/test_devctl_hook_protocol.py -q`; expected FAIL with `ImportError: cannot import name 'read_event'`.
- [ ] **Step 4: implement** the Interfaces. `run_hook` finds the root with `work_tree_root`, reads the settings, caches `read_branches(root or call.cwd)` behind `functools.cache`, and returns `decide`'s answer; Task 5 adds the guard.
- [ ] **Step 5: run.** Format, check and sync, then run the test file and `tests/devctl/test_devctl_cli.py`; expected PASS. Status, fast check.
- [ ] **Step 6: commit** `feat: answer Claude Code's PreToolUse hook with devctl hook claude pre-tool`.

### Task 5: The merge guard

**Files:**
- Modify: `devctl/merge_guard.py` (`guard`), `devctl/codeowners.py` (the ledger rule), `devctl/hook.py` (`run_hook`), `devctl/doctor_items.py:26` (`_GH_TIMEOUT_SECONDS` becomes public `GH_TIMEOUT_SECONDS`), `devctl/doctor_github.py:112` (`_decoded` becomes public `decoded_contents`)
- Test: `tests/devctl/test_devctl_merge_guard.py`, `tests/devctl/test_devctl_codeowners.py`
- Modify: the plan index's "`devctl hook` and the merge guard (plan 5)" sketch and Layout, to this task's interfaces

**Interfaces:**
- Consumes: Task 3's `Merge`, `LocalBranches`, `find_merge`, `HookSettings`; `CODEOWNERS_FILES` (Task 2); `OwnerGet`, `OwnerReadError`, `gh_get`; `CI_JOB_NAME`, `GITHUB_ACTIONS_APP_ID`.
- Produces:

```python
# devctl/codeowners.py
LEDGER = "docs/corrections/"


@dataclass(frozen=True)
class FileChange:
    path: str
    status: Literal["added", "modified", "removed", "renamed"]
    previous: str | None = None  # renamed: the path before


def ledger_entry(path: str) -> bool: ...  # .md under docs/corrections/, not its README.md
def protected_changes(patterns: Sequence[str], changes: Iterable[FileChange]) -> list[str]: ...


# devctl/merge_guard.py
GUARD_BUDGET_SECONDS = 300.0


def guard(
    merge: Merge,
    settings: HookSettings | None,  # None: unreadable, so every merge is denied
    owner_get: OwnerGet,
    branches: Callable[[], LocalBranches],
    elapsed: Callable[[], float],  # seconds since the hook run started
) -> str | None: ...  # the denial message; None: no decision
```

`protected_changes` returns the sorted, unique paths that a pattern covers, both paths of a rename included, plus each existing ledger entry that a change modifies, removes or renames away from. An added entry is never checked. Ruling: `ledger_entry` takes any `.md` path below `docs/corrections/` except `docs/corrections/README.md`, because Spec 1 says "under" and a wider Protected rule fails safe. Ruling: GitHub's file statuses map as `added` and `copied` to added, `removed` to removed, `renamed` to renamed, and every other status to modified.

`guard` reads, in this order, through `owner_get`:
1. The PR. A number: `repos/<repository>/pulls/<n>`. A URL `https://github.com/<o>/<r>/pull/<n>`: that repository and number. A branch, or no target (the current branch from `branches()`): `repos/<repository>/pulls?head=<owner>:<branch>&state=open&per_page=100`, which must list exactly one PR. The repository is `merge.repository`, else the URL's, else `settings.repository`.
2. CODEOWNERS on the base: `repos/<repository>/contents/<name>?ref=<base>` for each name of `CODEOWNERS_FILES` in turn, until one exists, which is the copy GitHub reads; decoded with `decoded_contents`. A 404 moves to the next name, and three 404s are an empty Protected set.
3. The files: `repos/<repository>/pulls/<n>/files?per_page=100&page=<k>` from page 1 until a page holds fewer than 100. A 30th full page is a denial, because GitHub lists at most 3,000 files.
4. The reviews, only with Agent identity on: `repos/<repository>/pulls/<n>/reviews?per_page=100&page=<k>` from page 1 until a page holds fewer than 100. Of the reviews whose `user.login` is `<settings.reviewer_app_slug>[bot]` and whose `state` is `APPROVED` or `CHANGES_REQUESTED`, the one with the highest `id` decides; `COMMENTED`, `DISMISSED` and `PENDING` reviews are ignored. The head is approved when that review is `APPROVED` and its `commit_id` equals the head SHA the guard read.
5. The check runs: `repos/<repository>/commits/<head>/check-runs?check_name=devctl%20check&filter=latest&per_page=100`. Of the runs whose `app.id` is 15368, the one with the highest `id` decides. Its `<state>` is `missing` without one, its `status` while not `completed`, else its `conclusion`. Only `success` passes.

Then it denies with the Protected message, else the check message, else, with Agent identity on, the review message when the head is not approved, else the head message when `merge.head` differs from the head SHA it read; otherwise it returns `None`. With `settings` None, it denies before any read. `<the same command>` is `shlex.join(merge.command)`.

Rulings for this task:
- Ruling: the guard does not run inside `devctl as`; the hook runs it for `./devctl as <role> gh pr merge`, because Spec 1 section 4 gives a Harness without wiring no merge guard.
- Ruling: a `gh pr merge` that names no PR reads the current branch from local git (`LocalBranches.current`), because Spec 1's step 2 takes the PR of the current branch; the index allowed local git only for a push or a ref path, and Step 3 widens it.
- Ruling: the repository source order above, because `gh_get` runs outside the repository and `devctl as` gives gh `GH_REPO` from `[github] repository`.
- Ruling: the Protected message comes before the check message, and the check runs are read last, because waiting on a check cannot fix a PR only the owner can merge; a small PR still costs Spec 1's four reads, five with Agent identity on. The review message comes after the check message, because fixing a failed check pushes a new head, which needs a new review anyway, and before the head message, because the retry that message names would be denied without the approval.
- Ruling: of the Reviewer App's reviews that approve or request changes, the one with the highest `id` is the latest, as for the check runs. The reviews have no page limit of their own; the 300-second budget bounds their reads.
- Ruling: with `settings` None, the guard denies before any read, because it cannot tell whether Agent identity is on (Spec 1 section 4). Its reason is fixed, because `read_settings` writes the file and the key only to stderr and returns None.
- Ruling: `--match-head-commit` must equal the full 40-character head SHA, which is what GitHub compares.
- Ruling: before each read, the guard denies when `elapsed() + GH_TIMEOUT_SECONDS > GUARD_BUDGET_SECONDS`, because Claude Code lets a call through when it kills a hook at its timeout, 600 seconds by default, which Task 1 records. `run_hook` passes every guard on a line one `elapsed`, so they share the budget.
- Ruling: every other denial is `merge denied: the merge guard cannot check this merge: <reason>; fix that, then merge again`, where `<reason>` is gh's first error line (`OwnerReadError.message`), or one of: `no repository: set [github] repository in .rapid-ship/project.toml or pass -R OWNER/NAME`; `no open pull request has head <owner>:<branch>`; `<n> open pull requests have head <owner>:<branch>; name one by number`; `HEAD is detached and the command names no pull request`; `GitHub lists at most 3,000 files of a pull request, and this one has more`; `its GitHub reads would pass the 300-second budget`; `the hook cannot read .rapid-ship/project.toml or .github/CODEOWNERS`; `the guard failed: <exception type>: <message>`. The last comes from one `except Exception` around the guard, marked `# noqa: BLE001  # rs-exception: EX-12` with its entry in `.rapid-ship/exceptions.toml`.

`run_hook` then, when `decide` gives no decision, calls `guard` for each simple command whose `find_merge` form is `pr-merge`, in order, with the settings it read (None when they are unreadable) and one `elapsed` for the hook run. It answers `("deny", message)` with the first denial, else no decision, because Spec 1 section 4 checks each simple command.

- [ ] **Step 1: write the failing tests.** In `test_devctl_codeowners.py`:

```python
def test_protected_changes_apply_the_ledger_rule() -> None:
    changes = [
        FileChange("docs/corrections/c1.md", "modified"),
        FileChange("docs/corrections/c2.md", "removed"),
        FileChange("docs/c3.md", "renamed", previous="docs/corrections/c3.md"),
        FileChange("docs/corrections/c4.md", "added"),
        FileChange("docs/corrections/README.md", "modified"),
        FileChange("docs/x.md", "renamed", previous=".github/x.md"),
    ]
    assert protected_changes(["/.github/"], changes) == [
        ".github/x.md",
        "docs/corrections/c1.md",
        "docs/corrections/c2.md",
        "docs/corrections/c3.md",
    ]
```

  `test_devctl_merge_guard.py`, docstring `Offline: the merge guard against RecordedOwner, a simulated owner reader. No live GitHub.`:

```python
HEAD = "a" * 40
OTHER = "b" * 40
PR = "repos/o/r/pulls/7"
CODEOWNERS = "repos/o/r/contents/.github/CODEOWNERS?ref=main"
FILES = "repos/o/r/pulls/7/files?per_page=100&page=1"
REVIEWS = "repos/o/r/pulls/7/reviews?per_page=100&page=1"
RUNS = f"repos/o/r/commits/{HEAD}/check-runs?check_name=devctl%20check&filter=latest&per_page=100"
BY_BRANCH = "repos/o/r/pulls?head=o:task&state=open&per_page=100"
PULL = {"number": 7, "head": {"sha": HEAD}, "base": {"ref": "main"}}
OWNERS = base64.b64encode(b"* @o\n# /.github/ @o\n# /**/AGENTS.md @o\n").decode()
TASK = LocalBranches(frozenset({"main"}), "task")
OFF = HookSettings(agent_identity=False, protected=(), repository="o/r", reviewer_app_slug=None)
ON = replace(OFF, agent_identity=True, reviewer_app_slug="o-reviewer")
CHECKED = f"merge denied: devctl check on PR #7 at {HEAD} is {{}}; "
CHECKED += "wait for it to pass or fix what it reports, then merge again"
UNAPPROVED = f"merge denied: PR #7 has no Reviewer App approval of its head {HEAD}; "
UNAPPROVED += "have the Reviewer review that commit, then merge again"


def run(status: str = "completed", conclusion: str | None = "success", **fields: object) -> object:
    found = {"id": 1, "name": "devctl check", "status": status, "conclusion": conclusion}
    return {**found, "app": {"id": 15368}, **fields}


def review(state: str = "APPROVED", commit: str = HEAD, **fields: object) -> object:
    found = {"id": 1, "user": {"login": "o-reviewer[bot]"}, "state": state, "commit_id": commit}
    return {**found, **fields}


def owner(files: object = None, runs: object = None, reviews: object = None) -> RecordedOwner:
    return RecordedOwner(
        {
            PR: PULL,
            CODEOWNERS: {"encoding": "base64", "content": OWNERS},
            FILES: files or [{"filename": "src/app/core.py", "status": "modified"}],
            REVIEWS: [review()] if reviews is None else reviews,
            RUNS: {"check_runs": [run()] if runs is None else runs},
        }
    )


def guarded(line: str, reader: RecordedOwner, settings: HookSettings | None = OFF) -> str | None:
    merge = find_merge(simple_commands(line)[0], lambda: TASK)
    assert merge is not None
    return guard(merge, settings, reader, lambda: TASK, lambda: 0.0)


@pytest.mark.parametrize(
    ("settings", "paths"),
    [(OFF, [PR, CODEOWNERS, FILES, RUNS]), (ON, [PR, CODEOWNERS, FILES, REVIEWS, RUNS])],
)
def test_a_passing_unprotected_merge_at_the_checked_head_gets_no_decision(
    settings: HookSettings, paths: list[str]
) -> None:
    reader = owner()
    assert guarded(f"gh pr merge 7 --squash --match-head-commit {HEAD}", reader, settings) is None
    assert reader.paths == paths


@pytest.mark.parametrize(
    ("runs", "state"),
    [
        ([run("queued", None)], "queued"),
        ([run("in_progress", None)], "in_progress"),
        ([run(conclusion="failure")], "failure"),
        ([run(conclusion="cancelled")], "cancelled"),
        ([run(conclusion="skipped")], "skipped"),
        ([], "missing"),
        ([run(app={"id": 999})], "missing"),
        ([run(), run(conclusion="failure", id=2)], "failure"),
    ],
)
def test_a_check_that_has_not_passed_denies(runs: list[object], state: str) -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    assert guarded(line, owner(runs=runs)) == CHECKED.format(state)


@pytest.mark.parametrize(
    ("change", "paths"),
    [
        ({"filename": ".github/workflows/x.yml", "status": "modified"}, ".github/workflows/x.yml"),
        ({"filename": "docs/AGENTS.md", "status": "added"}, "docs/AGENTS.md"),
        (
            {"filename": "x.md", "status": "renamed", "previous_filename": ".github/x.md"},
            ".github/x.md",
        ),
        ({"filename": "docs/corrections/c1.md", "status": "modified"}, "docs/corrections/c1.md"),
        ({"filename": "docs/corrections/c1.md", "status": "removed"}, "docs/corrections/c1.md"),
    ],
)
def test_a_protected_change_at_the_base_denies(change: object, paths: str) -> None:
    assert guarded("gh pr merge 7", owner(files=[change])) == (
        f"merge denied: PR #7 touches the Protected set ({paths}); "
        "the owner merges it in GitHub's web interface"
    )


@pytest.mark.parametrize("status", ["open", "implemented"])
def test_an_added_ledger_entry_is_not_protected_whatever_its_status(status: str) -> None:
    reader = owner(files=[{"filename": f"docs/corrections/{status}.md", "status": "added"}])
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", reader) is None
    assert not any("corrections" in path for path in reader.paths)


@pytest.mark.parametrize(
    ("line", "retry"),
    [
        ("gh pr merge 7 --squash", "gh pr merge 7 --squash"),
        (f"gh pr merge 7 --squash --match-head-commit {OTHER}", "gh pr merge 7 --squash"),
        ("./devctl as worker gh pr merge 7 --squash", "./devctl as worker gh pr merge 7 --squash"),
    ],
)
def test_a_merge_not_pinned_to_the_checked_head_is_denied_with_the_exact_retry(
    line: str, retry: str
) -> None:
    assert guarded(line, owner()) == (
        f"merge denied: PR #7 merges only at the checked head {HEAD}; "
        f"run {retry} --match-head-commit {HEAD}"
    )


@pytest.mark.parametrize(
    "reviews",
    [
        [],
        [review(user={"login": "octo"})],
        [review(user={"login": "o-reviewer"})],
        [review(commit=OTHER)],
        [review(), review("CHANGES_REQUESTED", id=2)],
        [review("COMMENTED")],
        [review("DISMISSED")],
    ],
)
def test_with_agent_identity_a_head_without_the_reviewer_apps_approval_is_denied(
    reviews: list[object],
) -> None:
    line = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
    assert guarded(line, owner(reviews=reviews), ON) == UNAPPROVED


def test_comments_and_dismissed_reviews_do_not_decide() -> None:
    reviews = [review(), review("COMMENTED", OTHER, id=2), review("DISMISSED", id=3)]
    line = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
    assert guarded(line, owner(reviews=reviews), ON) is None
```

  Also in `test_devctl_merge_guard.py`:
  - `test_each_target_reads_its_pull_request`: `gh pr merge task` and `gh pr merge` (current branch `task`) read `BY_BRANCH` first, served `[PULL]`; `gh pr merge https://github.com/x/y/pull/7` and `gh pr merge 7 -R x/y` read `repos/x/y/pulls/7` first, with `OFF`, whose repository is `o/r`.
  - `test_a_pr_the_guard_cannot_identify_or_read_is_denied`: `reader.fail(PR, OwnerReadError(404, "HTTP 404: Not Found"))` gives `merge denied: the merge guard cannot check this merge: HTTP 404: Not Found; fix that, then merge again`; `replace(OFF, repository=None)` without `-R` gives the `no repository` reason; `BY_BRANCH` served `[]` and served two PRs give their reasons; a detached HEAD with no target gives its reason.
  - `test_an_error_inside_the_guard_is_denied`: `PR` served as `[]` gives a message starting `merge denied: the merge guard cannot check this merge: the guard failed: `.
  - `test_files_are_read_page_by_page`: page 1 holds 100 unprotected files and page 2 `.github/x`; the message names `(.github/x)`.
  - `test_codeowners_is_read_where_github_reads_it`: with `CODEOWNERS` failed with a 404 and `repos/o/r/contents/CODEOWNERS?ref=main` serving what `owner()` serves at `CODEOWNERS`, a PR changing `docs/AGENTS.md` is denied with the Protected message after reading both; with all three names failed with a 404, the same PR with `--match-head-commit <HEAD>` gets no decision.
  - `test_each_merge_on_the_line_is_guarded`: in a workspace whose `project.toml` records `repository = "o/r"`, `run_hook` on `gh pr merge 7 --match-head-commit <HEAD> && gh pr merge 8 --squash`, against `owner()`, which serves PR 7 only, reads PR 7's four paths, then `repos/o/r/pulls/8`, and denies with `merge denied: the merge guard cannot check this merge: Not Found; fix that, then merge again`.
  - `test_the_guard_denies_before_a_read_could_pass_its_budget`: an `elapsed` that answers `0.0`, then `250.0`, reads `PR` only, and the message ends `its GitHub reads would pass the 300-second budget; fix that, then merge again`.
  - `test_only_gh_pr_merge_reads_github`: `run_hook` with an `owner_get` that fails the test when called, for `git status`, `gh pr view 7`, `gh api repos/o/r/pulls/7`, `git push origin task` and `gh pr merge 7 --admin`; then `gh pr merge 7` in a workspace whose `project.toml` records `repository = "o/r"` reads `PR` first.
  - `test_with_agent_identity_a_direct_merge_meets_g8_before_the_guard`: with both Apps recorded, `gh pr merge 7` is denied with `G8: ` and reads nothing; `./devctl as worker gh pr merge 7` reaches the guard.
  - `test_reviews_are_read_page_by_page`: with `ON`, `REVIEWS` serves 100 reviews by `octo` and `repos/o/r/pulls/7/reviews?per_page=100&page=2` serves `[review(id=101)]`; the merge at `HEAD` gets no decision, and `reader.paths` holds both review pages before `RUNS`.
  - `test_the_review_message_comes_after_the_check_and_before_the_head`: with `ON` and `owner(reviews=[], runs=[run(conclusion="failure")])`, `gh pr merge 7 --match-head-commit <HEAD>` gives `CHECKED.format("failure")`; with `ON` and `owner(reviews=[])`, `gh pr merge 7 --squash`, without `--match-head-commit`, gives `UNAPPROVED`.
  - `test_without_agent_identity_the_guard_reads_no_review`: with `OFF` and `owner(reviews=[])`, the merge at `HEAD` gets no decision, and `REVIEWS` is not in `reader.paths`.
  - `test_unreadable_settings_deny_every_merge`: `guarded(f"gh pr merge 7 -R o/r --match-head-commit {HEAD}", reader, None)` gives `merge denied: the merge guard cannot check this merge: the hook cannot read .rapid-ship/project.toml or .github/CODEOWNERS; fix that, then merge again`, and `reader.paths == []`; `run_hook` on the same line, in a workspace whose `project.toml` holds `[linear]`, gives the same denial and reads nothing.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_merge_guard.py tests/devctl/test_devctl_codeowners.py -q`; expected FAIL with `ImportError: cannot import name 'guard'`.
- [ ] **Step 3: implement** the Interfaces; add EX-12 to `.rapid-ship/exceptions.toml` with `path = "rapid_ship/templates/common/tools/devctl/devctl/merge_guard.py"`, `rule = "BLE001"` and `remove_when = "The guard's reads and parsers raise only OwnerReadError, GitHubError and ValueError, so a narrow except covers them"`. Update the plan index's sketch: `Decision`, `ToolCall` and `HookSettings` in `hook_protocols.py`, `ToolCall.edits` as absolute paths, `decide`'s and `guard`'s signatures, `Merge`'s fields, `command_line.py` in the Layout, and `LocalBranches` read also for a `gh pr merge` without a target.
- [ ] **Step 4: run.** Format, check and sync, then run both files and `tests/devctl/test_devctl_doctor_github*.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add the merge guard to devctl hook`.

### Task 6: The seeded Claude Code wiring and doctor's wiring item

**Files:**
- Create: `rapid_ship/templates/common/.claude/settings.json`, `devctl/doctor_wiring.py`, `tests/devctl/test_devctl_doctor_wiring.py`
- Modify: `rapid_ship/templates/kit.toml` (`seeded` gains `".claude/settings.json"`), `devctl/doctor_local.py` (`local_items` adds the item after `_ci_item`), `tests/devctl/test_devctl_doctor_local_limits.py` (the order test gains `("guardrails", "Harness wiring")` after `("guardrails", "CI workflow")`), `tests/test_kit_contents.py` (`SEEDED`), `.claude/AGENTS.md`
- This repository: `.claude/settings.json`, which `sync --in-place` creates

**Interfaces:**
- Consumes: `WIRED_TOOLS`, `HOOK_COMMAND` (Task 4).
- Produces: in `doctor_wiring.py`, `wiring_problems(settings: object) -> list[str]` and `wiring_item(root: Path, tracked: Sequence[str]) -> Item`, which gives `Item("guardrails", "Harness wiring", ...)`. Ruling: a module of its own that imports only `doctor_items` and `hook_protocols`, because `doctor_rules.py` imports `CI_JOB_NAME` from `doctor_local.py`, so `wiring_problems` there would make the two import each other.

The seed, exactly Spec 1 section 4's wiring:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/devctl hook claude pre-tool"
          }
        ]
      }
    ]
  }
}
```

The item is ok when `.claude/settings.json` is tracked, is valid JSON, does not set `disableAllHooks` to `true`, and each tool in `WIRED_TOOLS` matches a `PreToolUse` entry with a command hook that runs `devctl hook claude pre-tool`. An untracked or invalid file, or a gap, is missing, with the file and the tools named; a file it cannot read is unknown, as `_ci_item` does. Ruling, following Claude Code's documented matcher rules: a matcher covers a tool when it is `*`, empty or absent; a matcher made only of letters, digits, `_`, `-`, spaces, `,` and `|` is a list of exact names, split on `|` and `,`; any other matcher is an unanchored regular expression that `re.search` tries on the tool's name. Ruling: a command hook counts when its `command` and `args`, joined by spaces with quotes removed, contain `devctl hook claude pre-tool`, and it sets neither `async` to `true`, which cannot block, nor `if`, which narrows it. Ruling: doctor reads only `.claude/settings.json`, the Kit's seed; local and user settings are the owner's own.

- [ ] **Step 1: write the failing tests.** Docstring `Offline: doctor's Harness wiring item on written settings files.`

```python
HOOK = {"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool'}
ALL = "Bash|Edit|Write|MultiEdit|NotebookEdit"
GAP = "no PreToolUse hook runs devctl hook claude pre-tool for "
EVERY_TOOL = "Bash, Edit, Write, MultiEdit, NotebookEdit"


def wired(matcher: str | None = ALL, **fields: object) -> dict[str, object]:
    entry: dict[str, object] = {"hooks": [{**HOOK, **fields}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return {"hooks": {"PreToolUse": [entry]}}


SEED = wired()


@pytest.mark.parametrize(
    ("settings", "problems"),
    [
        (SEED, []),
        (wired("*"), []),
        (wired(None), []),
        (wired("Bash,Edit,Write,MultiEdit,NotebookEdit"), []),
        (wired("Bash|.*Edit|Write"), []),
        (wired("Bash"), [GAP + "Edit, Write, MultiEdit, NotebookEdit"]),
        (wired("Bash,Edit"), [GAP + "Write, MultiEdit, NotebookEdit"]),
        (wired("Edit"), [GAP + "Bash, Write, MultiEdit, NotebookEdit"]),
        (wired("Bash|Edit|Write|NotebookEdit"), [GAP + "MultiEdit"]),
        (wired(**{"async": True}), [GAP + EVERY_TOOL]),
        (wired(**{"if": "Bash(git *)"}), [GAP + EVERY_TOOL]),
        ({**SEED, "disableAllHooks": True}, ["disableAllHooks is true, so no hook runs"]),
        ({}, [GAP + EVERY_TOOL]),
    ],
)
def test_wiring_problems(settings: object, problems: list[str]) -> None:
    assert wiring_problems(settings) == problems
```

  And, through `local_items` with the `ctx` and `repo_files` fixtures: the rendered seed is ok; a missing file, an untracked one and invalid JSON are missing; a file that raises `OSError` on read is unknown. `tests/test_kit_contents.py`: `.claude/settings.json` is seeded in both stacks and its parsed content equals `SEED`.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_doctor_wiring.py tests/test_kit_contents.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.doctor_wiring'`.
- [ ] **Step 3: implement**; add the seed and `git add` it before syncing, because rendering skips paths git does not keep.
- [ ] **Step 4: run.** Format, check and `uv run rapid-ship sync --in-place`, which creates `.claude/settings.json` here; then run them and `tests/devctl/test_devctl_doctor_local_limits.py`; expected PASS, and `uv run rapid-ship status --strict` exits 0. `.claude/AGENTS.md` gains one sentence: `settings.json` wires `devctl hook` for Claude Code; it is seeded, in the Protected set, and doctor checks it.
- [ ] **Step 5: commit** `feat: seed the Claude Code wiring for devctl hook, with doctor's wiring item`.

### Task 7: The CODEOWNERS placeholder comment

**Files:**
- Modify: `rapid_ship/templates/common/.github/CODEOWNERS:21`, `rapid_ship/templates/python/.github/CODEOWNERS:21`, `.github/CODEOWNERS:21` (in place), `tests/test_kit_contents.py`

- [ ] **Step 1: write the failing test** in `tests/test_kit_contents.py`:

```python
@pytest.mark.parametrize("stack", ["python", "agnostic"])
def test_codeowners_has_no_placeholder_for_harness_settings(stack: Stack) -> None:
    assert "Harness settings" not in text(stack, ".github/CODEOWNERS")
```

- [ ] **Step 2: run** it; expected FAIL.
- [ ] **Step 3: delete** line 21 (`## Harness settings for Workers and Reviewers join with rapid-ship's Spec 2. (## lines stay comments.)`) from the three files, and add no line. `PROTECTED_PATHS` stays as it is.
- [ ] **Step 4: run** it and `tests/devctl/test_devctl_doctor_github.py`; expected PASS. Sync, status.
- [ ] **Step 5: commit** `chore: drop the CODEOWNERS placeholder for Harness settings`.

### Task 8: Documents, the guardrails live trial (Owner step), and PR 5.2's verification

**Files:**
- Modify: `ARCHITECTURE.md` (`devctl hook`, the merge guard, `codeowners.py`, the wiring seed), `tools/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md` (`fixtures/hooks/claude/`), the root `AGENTS.md` (plan 5's line), Spec 1's section 4 and status line, the plan index's plan 5 row
- Create: `docs/trials/<run date>-harness-guardrails.md`

- [ ] **Step 1 (agent): documents.** Update the files above to describe what Tasks 2 to 7 built. Spec 1 section 4's "Unreadable settings" bullet gains that a missing CODEOWNERS is an empty Protected set and leaves G7 and G8 on, and the merge guard's step 4 that the guard reads the first of `.github/CODEOWNERS`, `CODEOWNERS` and `docs/CODEOWNERS` on the base, as GitHub does. Commit `docs: describe devctl hook, the merge guard and the Claude Code wiring`.
- [ ] **Step 2 (agent): prepare the trial record.** It lists the steps below with an empty results table: the command or edit, the expected decision and message, and the observed ones.
- [ ] **Step 3 (Owner): the scratch repository.** Ruling: every case whose failure would write to GitHub runs in a scratch repository, `proxy-hatch/rs-guardrail-trial`, never in `proxy-hatch/rapid-ship`. Create it private with a first commit, `gh repo create proxy-hatch/rs-guardrail-trial --private --add-readme --clone`, because `init` in a repository without commits commits on the current branch and makes no `rapid-ship/init` branch. Run `uvx --from <the plan5-guardrails worktree> rapid-ship init --stack agnostic --owner proxy-hatch --repository proxy-hatch/rs-guardrail-trial`, push the init branch and merge its PR. Record the commands and the merge.
- [ ] **Step 4 (Owner): each rule, Agent identity off.** In a lead Claude Code Session started in the scratch clone, have the agent run each line and record the decision and message: `git commit --allow-empty -n -m g1` (G1), `git push --force origin HEAD:g2` (G2), `git push origin HEAD:main` (G3), `gh api -X PUT repos/{owner}/{repo}/pulls/1/merge` (G3), `gh pr merge 1 --admin --squash` (G3), an edit of `.rapid-ship/kit.lock` (G4), an edit of `AGENTS.md` (G5: the owner sees the prompt and declines) and `git status` (no decision). Repeat the list in a subagent that the lead starts.
- [ ] **Step 5 (Owner): the merge guard, Agent identity off.** Open PR A, changing `notes.txt`, and PR B, changing `AGENTS.md`, each with an Evidence section; open PR C with an empty body, so its `evidence` step fails. Have the agent run `gh pr merge <n> --squash`, and record each message: A while its check is pending (check message); C after its check fails (check message); B after its check passes (Protected message); A after its check passes, without `--match-head-commit` (head message); then the retry it names, which merges A. Record A's merge commit.
- [ ] **Step 6 (Owner): Agent identity on.** Run `uv run rapid-ship app --repository proxy-hatch/rs-guardrail-trial` from this repository, install the existing Apps there through the URLs it prints, record their IDs and slugs in the scratch repository's `project.toml`, and merge that change in GitHub's web interface. Then record: `git push origin HEAD` (G7); `gh pr create --fill` (G8); `gh pr merge <n> --squash` (G8), and these three again in a subagent that the lead starts; `./devctl as worker gh pr merge <n> --squash` while its check is pending (check message); once it passes, `./devctl as worker gh pr merge <n> --squash --match-head-commit <head>` before the Reviewer App has approved the PR (review message); `./devctl as reviewer gh pr review <n> --approve`; `./devctl as worker gh pr merge <n> --squash` (head message); the retry it names, the same merge as before the approval, which merges; `./devctl as worker gh pr merge <C> --squash` (check message) and the same for `<B>` (Protected message); and `./devctl as worker gh api -X PUT repos/{owner}/{repo}/pulls/<n>/merge` (G3).
- [ ] **Step 7 (Owner): the hook's cost.** In the scratch clone, run `/usr/bin/time -p ./devctl hook claude pre-tool < bash.json` 20 times, with Task 4's fixture whose `cwd` is set to the clone, and record the median and the maximum.
- [ ] **Step 8 (implementer): write the record** from the owner's output: Claude Code's version, each message verbatim, PR numbers and merge commits, the timing, and every difference from the expected decision. A difference is fixed in PR 5.2 and its case rerun before the merge.
- [ ] **Step 9: verify.** Run the five checks with `--base plan5-hook-spike`, and record the results in the Verification record. The PR body's Evidence section lists them and the trial record, with `Not covered:` naming what the trial did not run. Commit `docs: record the guardrails live trial and PR 5.2's verification`.

## PR 5.3: standards (`plan5-standards`, on `plan5-guardrails`)

### Task 9: README.md and ARCHITECTURE.md seeds, map rule 8 and `doctor --settings`

**Files:**
- Create: `rapid_ship/templates/common/README.md`, `rapid_ship/templates/common/ARCHITECTURE.md`, `devctl/check/map_skills.py`, `tests/devctl/test_devctl_map_root_documents.py`, `tests/devctl/test_devctl_doctor_settings.py`
- Modify: `rapid_ship/templates/kit.toml` (`seeded` gains `"ARCHITECTURE.md"` and `"README.md"`), `rapid_ship/templates/common/AGENTS.md`, `rapid_ship/templates/python/AGENTS.md`, `devctl/check/map.py`, `devctl/check/markdown.py`, `devctl/doctor.py`, `devctl/doctor_local.py`, `tests/devctl/check_workspace.py`, `tests/devctl/test_devctl_map_skills.py`, `tests/devctl/test_devctl_map_coverage.py`, `tests/devctl/test_devctl_map_documents.py`, `tests/devctl/test_devctl_doctor_local_limits.py`, `tests/test_kit_contents.py`; this repository's root `AGENTS.md` (in place)

**Interfaces:**
- Produces:

```python
# devctl/check/map.py
GRACE_VERSION = "0.2.0"  # the Kit version in which map rules 5, 7 and 8's new parts only warn


def graced(messages: list[str]) -> tuple[list[str], list[str]]: ...  # (errors, notes)
def root_document_errors(root: Path, files: Sequence[str]) -> list[str]: ...  # rule 8: missing
def root_link_errors(root: Path, files: Sequence[str]) -> list[str]: ...  # rule 8: links


# devctl/doctor_local.py
def settings_item(root: Path) -> Item: ...  # area "guardrails", name "settings"
```

- Ruling: map rule 7's functions (`skill_alias_errors`, `skill_errors` and their helpers, `map.py:204-274` and `:428-443`) move unchanged to `check/map_skills.py` first, with `SKILLS`, so `map.py` stays under 500 lines with rules 5 and 8 added. `skill_errors` also calls `_front_matter` and `_text` (`map.py:287-302`), which rules 4 and 5 keep using, so those two move first to `check/markdown.py` as public `front_matter_of` and `text_value`. `map.py` imports `map_skills.py`, and `map_skills.py` imports them from `markdown.py` and nothing from `map.py`, so no import cycle forms.
- Ruling: `graced` turns its messages into notes `warning: <message>; this fails from the next Kit version` while `devctl.__version__ == GRACE_VERSION`, read at run time, and into errors otherwise. It covers rule 8's links (`root_link_errors`: the root guide's links to both documents, and the local links inside them), rule 5's `task` and Lessons (Task 10) and rule 7's regular `SKILL.md` (Task 12), because each fails on files an existing project already owns (Spec 1 section 3: "devctl warns for that version before it fails"). For the root guide's links the warning period goes with Task 16's migration `0.2.0-root-guide-links`, which proposes the two rows. `root_document_errors` fails at once, because `sync` creates a missing seed. The diff cap and the ledger rule judge new changes only, so they fail at once.
- Ruling: `doctor --settings` prints the git item, `settings_item` and Task 6's Harness wiring item, and makes no GitHub request, because Spec 1 section 4 relies on the doctor run at each Session's start to report missing wiring, and section 6 has most Sessions run `--settings`. `settings_item` loads `.rapid-ship/project.toml` and `.rapid-ship/exceptions.toml` with devctl's loaders and reads `.github/CODEOWNERS` with `protected_patterns`. An invalid or unreadable file is unknown (exit 2), with the `SettingsError` message that names the file and the key; a missing `.github/CODEOWNERS` is missing (exit 1). The full doctor adds `settings_item` right after git, where Spec 1 section 6 reads the settings. `--settings` and `--skills` are an argparse mutually exclusive group, because `--settings` stays a quick local read.
- Seeds, with `{{project_name}}` as their only variable, because an empty `{{owner}}` or `{{repository}}` is a `KitError` outside TOML and CODEOWNERS. README.md: what the project does and for whom, how to run it, how to check a change (`./devctl check`), and a link to `AGENTS.md`. ARCHITECTURE.md: purpose and context, a table of the main parts (Part, Where, What it does), how data moves between them, the ADRs in `docs/adr/` as a code span (a new project has no `docs/adr/`, so a link would fail rule 8), and how to work on the code, linking `AGENTS.md`.
- Both root guide templates: a first Commands bullet, ``Run `./devctl doctor --settings` first in each Session, unless the Session runs the full `./devctl doctor`; it checks the settings files and asks GitHub nothing.``, and two first rows in Find the change, ``| What the project does, and how to run and check it | [README](README.md) |`` and ``| The system's parts and how data moves between them | [Architecture](ARCHITECTURE.md) |``. This repository's root guide gains the README row and the same command line.

- [ ] **Step 1: move rule 7.** Move `_front_matter` and `_text` to `check/markdown.py` as `front_matter_of` and `text_value`, then the skill functions and `SKILLS` to `check/map_skills.py`; update `MapStep.run` and the test imports. Format, check and sync, then run `uv run pytest tests/devctl/test_devctl_map_*.py -q`; expected PASS. Commit `refactor: move map rule 7 into check/map_skills.py`.
- [ ] **Step 2: write the failing tests.** In `test_devctl_map_root_documents.py`, docstring `Offline: map rule 8 in fixture repositories.`, using `Workspace`:
  - `test_rule_8_passes_with_both_documents_linked_from_the_root_guide`: `AGENTS.md` links both, each links `AGENTS.md`; `MapStep().run(ctx).status == "passed"`.
  - `test_rule_8_reports_a_missing_document_and_a_broken_link`: without `README.md`, `root_document_errors` holds `README.md: missing at the repository root; rapid-ship init seeds it`; an ARCHITECTURE.md link to `gone.md` gives, in `root_link_errors`, rule 1's message for that link.
  - `test_a_broken_link_in_architecture_md_warns_in_kit_0_2_0_and_fails_after`: through `MapStep`, that message is a note `warning: <message>; this fails from the next Kit version` under `0.2.0` and an error under `0.3.0`.
  - `test_a_root_guide_without_the_links_warns_in_kit_0_2_0_and_fails_after`: with `devctl.__version__` patched to `0.2.0`, the step passes with the note `warning: AGENTS.md: does not link README.md; add it to the Find the change table; this fails from the next Kit version`; patched to `0.3.0`, it fails with `AGENTS.md: does not link README.md; add it to the Find the change table`.

  In `test_devctl_doctor_settings.py`, docstring `Offline: doctor --settings on fixture repositories; gh_get is replaced by a reader that fails the test.`:
  - `test_settings_reads_only_the_settings_and_asks_github_nothing`: in a workspace that commits the rendered seeds of `.rapid-ship/`, `.github/CODEOWNERS` and `.claude/settings.json`, `main(["doctor", "--settings"])` exits 0, prints `ok  guardrails  settings: ` and `ok  guardrails  Harness wiring: `, and no other item than git's.
  - `test_an_invalid_key_exits_2_and_names_the_file_and_the_key`: `stack = "python"\n[escalation]\nrevision_rounds = 0\n` exits 2 and prints `.rapid-ship/project.toml [escalation] revision_rounds: expected an integer of at least 1`.
  - `test_a_missing_codeowners_is_missing`: exits 1.
  - `test_settings_and_skills_exclude_each_other`: `pytest.raises(SystemExit)` with code 2.

  Existing tests that rule 8 would break: the order test in `test_devctl_doctor_local_limits.py` gains `("guardrails", "settings")` right after `("toolchain", "git")`, and the six `MapStep().run` tests that expect a pass or exact details (`test_devctl_map_skills.py:26`, `test_devctl_map_coverage.py:84`, `:135`, `:145` and `:161`, `test_devctl_map_documents.py:221`) write their root guide with this `Workspace` method, which keeps each line number they assert:

```python
def root_guide(self, text: str = "# Root\n") -> None:
    """Write AGENTS.md with map rule 8's two links on its first line, and both documents."""
    first, _, rest = text.partition("\n")
    self.write("AGENTS.md", f"{first} [README](README.md) [Architecture](ARCHITECTURE.md)\n{rest}")
    self.write("README.md", "# Readme\n")
    self.write("ARCHITECTURE.md", "# Architecture\n")
```

  In `tests/test_kit_contents.py`: `SEEDED` gains both files; `ROOT_GUIDE_LINKS` starts `["README.md", "ARCHITECTURE.md", ...]`; `POINTERS` gains ``"`./devctl doctor --settings`"``; the README seed contains `./devctl check` and `](AGENTS.md)`, and the ARCHITECTURE seed contains `| Part | Where | What it does |` and `` `docs/adr/` ``.
- [ ] **Step 3: run** the three files; expected FAIL with `ImportError: cannot import name 'root_document_errors'`.
- [ ] **Step 4: implement.** `root_document_errors` reuses `link_errors(root, files, ["README.md", "ARCHITECTURE.md"])`, and `root_link_errors` reuses `_guide_targets(root, "AGENTS.md")`. `git add` the seeds, then sync: this repository's `README.md` and `ARCHITECTURE.md` stay as they are and are recorded as seeded.
- [ ] **Step 5: run** them, `tests/devctl/test_devctl_map_*.py` and `tests/devctl/test_devctl_doctor*.py`; expected PASS. Status, fast check.
- [ ] **Step 6: commit** `feat: seed README.md and ARCHITECTURE.md, check them with map rule 8, and add doctor --settings`.

### Task 10: The Pattern `task` key and `## Lessons` section

**Files:**
- Modify: `rapid_ship/templates/common/docs/patterns/README.md`, `devctl/check/map.py` (`_pattern_problems`, `_document_errors`), `tests/devctl/test_devctl_map_documents.py`, `tests/test_kit_contents.py:347-365`

**Interfaces:**
- Consumes: `graced` (Task 9); `markdown.section(text, title, level)`.
- Produces: `pattern_lesson_errors(context: CheckContext, files: Sequence[str]) -> list[str]` in `map.py`, whose messages `MapStep.run` passes through `graced`. `_document_errors` passes the file's text to its callback as a fourth argument.

The seed's front-matter example gains `task: Read configuration` first, with the bullet ``- `task` is the recurring task in a few words.``, and its last paragraph becomes Spec 1's: the text states the rule, when it applies and the bypass it bans, and a non-empty `## Lessons` section explains what the reference does right.

- [ ] **Step 1: write the failing tests:**

```python
PATTERN = """---
task: Read configuration
reference: src/app/settings.py
enforced_by:
  - check:map
---
One typed settings module reads configuration.

## Lessons

It validates every value where it enters.
"""


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (PATTERN.replace("task: Read configuration\n", ""), "task is missing or empty"),
        (PATTERN.replace("task: Read configuration", 'task: ""'), "task is missing or empty"),
        (PATTERN.split("## Lessons")[0], "## Lessons is missing or empty"),
        (
            PATTERN.replace("It validates every value where it enters.\n", ""),
            "## Lessons is missing or empty",
        ),
    ],
)
def test_a_pattern_needs_a_task_and_lessons(workspace: Workspace, text: str, message: str) -> None:
    workspace.write("src/app/settings.py", "")
    workspace.write("docs/patterns/settings.md", text)
    context = workspace.context()
    errors = pattern_lesson_errors(context, context.repo.files())
    assert errors == [f"docs/patterns/settings.md: {message}"]
```

  and `test_a_complete_pattern_passes`, with `PATTERN` giving `[]`. In `test_kit_contents.py`, the Pattern README names `task`, `reference`, `enforced_by` and `## Lessons`.
- [ ] **Step 2: run**; expected FAIL with `ImportError`.
- [ ] **Step 3: implement**; sync.
- [ ] **Step 4: run** the map tests and `tests/test_kit_contents.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: require a Pattern's task and Lessons in map rule 5`.

### Task 11: The Python starter Patterns and the performance Pattern

**Files:**
- Create under `rapid_ship/templates/python/`: `docs/patterns/python-error-handling.md`, `python-configuration.md`, `python-input-validation.md`, `python-performance.md`; `src/__package__/errors.py`, `inputs.py`, `settings.py`, `profiling.py`; `tests/test_errors.py`, `tests/test_inputs.py`, `tests/test_settings.py`, `tests/test_profiling.py`
- Modify: `rapid_ship/templates/kit.toml` (`new_project` gains each path above), `rapid_ship/templates/python/pyproject.toml` (the banned members and one per-file entry), `rapid_ship/templates/python/.github/CODEOWNERS`, `tests/test_kit_contents.py`
- Create: `tests/test_kit_starter_patterns.py`

**Interfaces:**
- Consumes: map rule 5 with Task 10's parts.
- Produces, in the new project's package (Ruling: example values the owner replaces; Spec 1 says "The plan that ships each set picks its exact checks"):

```python
# src/<package>/errors.py
class UsageError(Exception):  # a problem the user can fix; raised from its cause, never instead
    def __init__(self, problem: str, next_step: str) -> None: ...  # str(): "<problem>; <next_step>"


# src/<package>/inputs.py
Level = Literal["debug", "info", "warning", "error"]


def parse_level(text: str) -> Level: ...  # UsageError naming the four values


# src/<package>/settings.py
@dataclass(frozen=True)
class Settings:
    log_level: Level  # LOG_LEVEL, default "info"
    workers: int  # WORKERS, 1 to 32, default 4


def load_settings(environ: Mapping[str, str] | None = None) -> Settings: ...  # None: os.environ


# src/<package>/profiling.py: py-spy record -o profile.svg -- python -m <package>.profiling
def main(argv: Sequence[str] | None = None) -> int: ...  # --rounds N, default 100000
```

| Pattern file | `task` | `reference` | `enforced_by` |
| --- | --- | --- | --- |
| `python-error-handling.md` | `Report an error` | `src/{{package}}/errors.py` | `ruff:BLE001`, `ruff:S110`, `test:tests/test_errors.py::test_an_error_keeps_its_cause_and_names_the_next_step` |
| `python-configuration.md` | `Read configuration` | `src/{{package}}/settings.py` | `banned:os.environ`, `banned:os.getenv`, `test:tests/test_settings.py::test_an_out_of_range_value_is_rejected` |
| `python-input-validation.md` | `Validate input` | `src/{{package}}/inputs.py` | `type:tests/test_inputs.py`, `test:tests/test_inputs.py::test_an_unknown_value_is_rejected` |
| `python-performance.md` | `Find slow code` | `src/{{package}}/profiling.py` | `test:tests/test_profiling.py::test_the_profiling_entry_point_runs_on_a_small_input` |

Each file states the rule of Spec 1 section 4's starter table, when it applies and the bypass it bans, then `## Lessons` on what its reference does right. The performance Pattern documents `uvx py-spy record -o profile.svg -- python -m <package>.profiling` and how to read the flame graph; no check runs a profiler.

- Ruling: `pyproject.toml`'s `banned-api` gains `"os.environ".msg` and `"os.getenv".msg`, both pointing to `docs/patterns/python-configuration.md`, and `per-file-ignores` gains `"src/{{package}}/settings.py" = ["TID251"]  # the one module that reads the environment`. A per-file entry in the Protected `pyproject.toml` is the owner's setting, while an inline suppression would need an `exceptions.toml` entry, and the seed must hold none.
- Ruling: `tests/test_inputs.py` is the `type:` fixture: `assert_type(parse_level("info"), Level)` sits in its test, which mypy checks under `files = ["src", "tests"]`; no `type: ignore` is needed.
- Ruling: the modules sit directly in `src/<package>/`, so map rule 2 asks for no new guide, and the profiling entry point starts no process, so no S603 exception is needed.
- Ruling: the Python CODEOWNERS seed gains, right after the `/.rapid-ship/` line, one commented line for each starter Pattern file, such as `# /docs/patterns/python-error-handling.md @{{owner}}`, so the set still ends with the settings files of the check tools, as the seed's comment says. In an existing project those files do not exist, and GitHub ignores a line for a missing file.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_starter_patterns.py`, docstring `Offline: a new Python project from init, checked with map rule 5; no network.`:
  - `test_the_python_starter_patterns_pass_map_rule_5`: `init_repository` with `stack="python"` in `git_repo`, then commit. The tracked files under `docs/patterns/` that start `python-` are exactly the four file names above, and `pattern_errors` and `pattern_lesson_errors` on its `CheckContext` both return `[]`.
  - `test_the_starter_patterns_are_new_project_seeds_only`: on a repository that already has a `pyproject.toml`, `init` writes none of the files above.

  The skeleton's own tests, which run inside the new project: `test_an_error_keeps_its_cause_and_names_the_next_step` (`load_settings({"WORKERS": "four"})` raises a `UsageError` whose text is `WORKERS is four; set it to a whole number from 1 to 32` and whose `__cause__` is the `ValueError` from `int`), `test_an_out_of_range_value_is_rejected` (`load_settings({"WORKERS": "33"})` raises `UsageError`), `test_an_unknown_value_is_rejected` (`parse_level("verbose")` raises `UsageError` whose message names `debug, info, warning, error`), and `test_the_profiling_entry_point_runs_on_a_small_input` (`main(["--rounds", "3"]) == 0`, judging no time).

  In `tests/test_kit_contents.py`, the two CODEOWNERS tests expect the Pattern lines:

```python
STARTER_PATTERNS = tuple(
    f"/docs/patterns/python-{name}.md"
    for name in ("error-handling", "configuration", "input-validation", "performance")
)
PYTHON_SET = (*PROTECTED[:9], *STARTER_PATTERNS, *PROTECTED[9:], *PYTHON_PROTECTED)


@pytest.mark.parametrize(("stack", "expected"), [("python", PYTHON_SET), ("agnostic", PROTECTED)])
def test_codeowners_has_the_walk_line_and_the_stack_protected_set(
    stack: Stack, expected: tuple[str, ...]
) -> None:
    lines = text(stack, ".github/CODEOWNERS").splitlines()
    assert active(lines) == ["* @octo"]
    protected = [line for line in lines if re.fullmatch(r"# /\S+ @octo", line)]
    assert protected == [f"# {path} @octo" for path in expected]


def test_the_python_codeowners_only_adds_the_starter_patterns_and_the_python_settings() -> None:
    python = text("python", ".github/CODEOWNERS").splitlines()
    agnostic = text("agnostic", ".github/CODEOWNERS").splitlines()
    split = agnostic.index("# /.rapid-ship/ @octo") + 1
    patterns = [f"# {path} @octo" for path in STARTER_PATTERNS]
    added = [f"# {path} @octo" for path in PYTHON_PROTECTED]
    assert python == [*agnostic[:split], *patterns, *agnostic[split:], *added]
```
- [ ] **Step 2: run** `uv run pytest tests/test_kit_starter_patterns.py -q`; expected FAIL on the assertion that names the four Pattern files, because none exists yet.
- [ ] **Step 3: implement**, `git add` the templates, sync.
- [ ] **Step 4: run** the offline file and `tests/test_kit_contents.py`; expected PASS. Then run the network test `uv run pytest tests/devctl/test_devctl_check_integration.py -q -k test_new_project_passes_devctl_check`; expected PASS for `python` and `agnostic`, which proves the skeleton's tests pass and `./devctl check` passes on a new project.
- [ ] **Step 5: commit** `feat: seed the Python starter Patterns and the performance Pattern`.

### Task 12: The `SKILL.md` rule

**Files:**
- Modify: `devctl/check/map_skills.py`, `tests/devctl/test_devctl_map_skills.py`

**Interfaces:**
- Produces: `skill_file_errors(root: Path, files: Sequence[str]) -> list[str]`, whose messages `MapStep.run` passes through `graced`.

- [ ] **Step 1: write the failing test** `test_a_symlinked_skill_md_warns_in_kit_0_2_0_and_fails_after`: a skill whose `SKILL.md` is a symlink to `real.md` in its directory gives `.agents/skills/demo/SKILL.md: is a symlink; make it a regular file, because Codex rejects a symlinked SKILL.md`, as a note under `0.2.0` and as an error under `0.3.0`; a regular `SKILL.md` gives `[]`.
- [ ] **Step 2: run**; expected FAIL with `ImportError`.
- [ ] **Step 3: implement** with `Path.is_symlink()`; sync.
- [ ] **Step 4: run** `tests/devctl/test_devctl_map_*.py`; expected PASS. Fast check.
- [ ] **Step 5: commit** `feat: require a regular SKILL.md in map rule 7`.

### Task 13: The diff cap, its escalation kind, and the ledger rule in the `diff` step

**Files:**
- Modify: `devctl/check/diff.py`, `devctl/check/evidence.py`; `rapid_ship/templates/{python,agnostic}/.rapid-ship/project.toml` and this repository's `.rapid-ship/project.toml` (in place)
- Test: `tests/devctl/test_devctl_diff_cap.py`, `tests/devctl/test_devctl_diff_rules.py`, `tests/devctl/test_devctl_diff_removed_tests.py`, `tests/devctl/test_devctl_evidence_step.py`, `tests/devctl/test_devctl_settings.py`, `tests/test_kit_contents.py:85-112`

**Interfaces:**
- Consumes: `codeowners.FileChange`, `protected_changes` (Task 5); `kit.managed_paths`, `KitLockError`.
- Produces:

```python
# devctl/check/evidence.py
def over_cap_reason(body: str) -> str | None: ...  # the reason after "Over the diff cap:"


# devctl/check/diff.py
DIFF_CAP = 1500
LOCK_FILES = frozenset({"uv.lock", "package-lock.json"})  # each stack's lock, at any depth


def counted_lines(context: CheckContext, base: str) -> int: ...
```

- `counted_lines` sums added and removed lines from `git diff --numstat -z --no-renames <base>`, plus the lines of each untracked, non-ignored text file. It leaves out paths ending `.md`, `.txt` or `.log`, binary files (`-` in numstat; for an untracked file, a NUL byte in its first 8,000 bytes, git's test), `managed_paths`, `.rapid-ship/kit.lock` and `LOCK_FILES` by basename. Without a readable lock (`KitLockError`) it counts with no managed paths: the count can only grow, and the `kit` step reports the lock.
- The cap and the ledger rule run for every stack, outside the Python branch. More than `DIFF_CAP` fails with `the change adds and removes <n> counted lines, over the 1,500-line diff cap; split it, or, once the owner accepts the overage, add 'Over the diff cap: <reason>' to the PR's Evidence section`, plus `_NO_BODY` without a body. A declared overage passes with the note `diff cap: <n> counted lines, over 1,500, declared: <reason>`; otherwise the note is `diff cap: <n> of 1,500 counted lines`. Ruling: these texts, and a note on every run so a Worker sees its count; the note comes last, after the Protected notes.
- `_protected` becomes `protected_changes` over the step's changes, mapping `A`, `M` and `D` to added, modified and removed; `--no-renames` makes a rename a removal plus an addition, so a renamed entry is listed by its old path. The ledger rule applies with or without a CODEOWNERS file. The module docstring says the merge guard enforces the Protected approval (Spec 1 section 5, item 4).
- Ruling: the lock-file names live in `diff.py`, not `check/stacks/python.py`, which has 31 lines left under the cap; plan 6 moves them per stack if it needs to.
- Both seeds and this repository's `project.toml` gain `"a pull request that declares Over the diff cap:"` as the second kind.

- [ ] **Step 1: write the failing tests.** `test_devctl_diff_cap.py`, docstring `Offline: the diff cap in fixture repositories.`, each with a base commit and a change written by `Workspace`:
  - `test_exactly_1500_counted_lines_pass` and `test_1501_counted_lines_fail_and_name_the_declaration`: a `src/app/big.py` of 1,500 or 1,501 lines; the failure message is the one above with `<n>` = 1501 and ends with `_NO_BODY`.
  - `test_a_declared_overage_passes_with_a_note`: a body whose `## Evidence` section holds a command line, the line `Over the diff cap: a generated parser` and a `Not covered:` line passes with `diff cap: 1501 counted lines, over 1,500, declared: a generated parser`.
  - `test_a_declaration_outside_evidence_or_without_a_reason_does_not_count`: the line under `## Notes`, and `Over the diff cap:` with nothing after it, both fail.
  - `test_excluded_files_do_not_count`, parametrized over `docs/a.md`, `notes.txt`, `run.log`, a 2,000-byte binary file holding a NUL byte, a path the lock records as managed, `.rapid-ship/kit.lock`, `uv.lock` and `frontend/package-lock.json`: each with 1,600 lines passes.
  - `test_untracked_files_count` and `test_the_cap_applies_to_the_agnostic_stack`.

  In `test_devctl_diff_rules.py`, `test_the_ledger_rule_lists_changed_and_removed_entries_only`: base entries `docs/corrections/c1.md` and `c2.md`; the change edits `c1.md`, deletes `c2.md` and adds `c3.md`; notes hold `protected: docs/corrections/c1.md` and `protected: docs/corrections/c2.md` and no `c3.md`. The exact `details` at `test_devctl_diff_rules.py:99` and `test_devctl_diff_removed_tests.py:117-121`, `:171-175`, `:183`, `:194` and `:205` each gain the cap note last, `diff cap: <n> of 1,500 counted lines` with that fixture's count. In `test_devctl_evidence_step.py`, `over_cap_reason` returns the reason inside Evidence and `None` outside it, inside a fence, or without a reason. The seed tests expect both kinds.
- [ ] **Step 2: run** them; expected FAIL with `ImportError: cannot import name 'over_cap_reason'`.
- [ ] **Step 3: implement**; edit this repository's `project.toml`; sync.
- [ ] **Step 4: run** `tests/devctl/test_devctl_diff_*.py`, the evidence and settings tests and `tests/test_kit_contents.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add the 1,500-line diff cap and the Corrections ledger rule`.

### Task 14: One CI concurrency group for each push run, documents, and PR 5.3's verification

**Files:**
- Modify: `rapid_ship/templates/common/.github/workflows/devctl-check.yml:18-20`, `tests/devctl/test_devctl_ci_templates.py:39-46`; this repository's workflow through `sync`
- Modify: `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, the root `AGENTS.md`, Spec 1's status line, the plan index's plan 5 row

Ruling: the group is `devctl-check-${{ github.event_name == 'push' && github.sha || github.ref }}`, so each push run has its own commit's group and pull requests keep one group per ref; `cancel-in-progress` stays `${{ github.event_name == 'pull_request' }}`. A comment above the group says so.

- [ ] **Step 1: write the failing test.** The assertion at `test_devctl_ci_templates.py:39-46` expects:

```python
assert workflow["concurrency"] == {
    "group": "devctl-check-${{ github.event_name == 'push' && github.sha || github.ref }}",
    "cancel-in-progress": "${{ github.event_name == 'pull_request' }}",
}
```

- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_ci_templates.py -q`; expected FAIL.
- [ ] **Step 3: implement**, sync, then run `./devctl check --tier full` and confirm its `workflows` step, zizmor 1.30.1, passes.
- [ ] **Step 4: commit** `ci: give each push run its own concurrency group`.
- [ ] **Step 5: documents.** Describe Tasks 9 to 14 in the files above, including the warning period of `GRACE_VERSION`; commit `docs: describe plan 5's standards`.
- [ ] **Step 6: verify.** Run the five checks with `--base plan5-guardrails`, and record them in the Verification record. When `diff` counts more than 1,500 lines, the PR body declares `Over the diff cap: <reason>` only after the owner accepts the overage; otherwise split the PR at a task boundary. Commit `docs: record PR 5.3's verification`.

## PR 5.4: settings and migrations (`plan5-settings-migrations`, on `plan5-standards`)

### Task 15: Documented seeds and the loaders' checks

**Files:**
- Modify: `devctl/settings.py`; `rapid_ship/templates/{python,agnostic}/.rapid-ship/project.toml`, `rapid_ship/templates/common/.rapid-ship/exceptions.toml`, `rapid_ship/templates/python/pyproject.toml`, both CODEOWNERS templates, `rapid_ship/templates/common/.github/workflows/devctl-check.yml`; this repository's `.rapid-ship/project.toml` and `.github/CODEOWNERS` (in place)
- Test: `tests/devctl/test_devctl_settings.py`; create `tests/test_kit_seed_comments.py`

**Interfaces:**
- Produces: in `settings.py`, `PROJECT_KEYS: dict[str, frozenset[str]]`, each table's accepted keys, with `""` for the top-level keys, `EXCEPTION_KEYS: tuple[str, ...]` (today's `_EXCEPTION_KEYS`) and `OPTIONAL_SKILLS: frozenset[str]`.

Loader changes:
- An unknown key's error names what the table accepts: `<where>: unknown key '<key>'; it accepts <keys, sorted, comma-separated>`. Ruling: this text.
- `[map] source_roots`, `[map] unguided` and `[tests] unit` must name paths inside the repository, checked as `exclude` is: `<where> <key>: expected paths inside the repository`.
- `[kit] optional` must name skills the Kit offers. `OPTIONAL_SKILLS` holds the Kit's optional names, none in 0.2.0, and a parity test in `test_devctl_settings.py` holds it equal to `kit.toml`'s `optional_skills` (`load_manifest()`), as the index does for `keychain_service`. Another name fails with `<where> optional: expected names of the Kit's optional skills: <names, sorted, comma-separated, or none in this Kit version>`.
- Spec 1 states no other range or allowed set than those the loader checks today.

Seed comments: every key line of each seeded TOML file carries a short comment on its line, or directly above it or above the run of key lines it belongs to, saying what it means, what it accepts and its default (Spec 1 section 4). `project.toml` takes Spec 1's comments from section 4's example, except `[[stack]]` (plan 6), and `[kit] optional`, which keeps `opt-in Kit skills` until Spec 3's plan widens the key. It adds a short comment on `stack`, `repository` and `source_roots`, which the example leaves without one, and Task 16's documents step adds the last two to Spec 1's example. The CI workflow does the same for each key line outside a `run:` block. Ruling: CODEOWNERS gets a `##` line above each group of Protected lines, in Spec 1 section 4's grouping, because a trailing comment would stop `patterns_in` from reading the owned line: `## CI, hooks and devctl.`, `## Skills and the Harness guardrail wiring.`, `## Agent instructions.`, `## rapid-ship settings.`, in the Python seed `## The starter Patterns.`, and `## The check tools' settings files; each can switch its check off.` Task 7 removed the seed's only note on `##` lines, so the header of both templates and of this repository's copy gains `# Lines that start with ## stay comments in Flight.`

- [ ] **Step 1: write the failing tests.** In `test_devctl_settings.py`, these rows join the table of `test_invalid_settings_raise_settings_error`:

```python
NEW_ROWS = [
    (
        PROJECT,
        'stack = "python"\n[escalation]\nevery_prs = true\n',
        ".rapid-ship/project.toml [escalation]: unknown key 'every_prs'; "
        "it accepts every_pr, kinds, revision_rounds",
    ),
    (
        PROJECT,
        'stack = "python"\n[map]\nsource_roots = ["../x"]\n',
        ".rapid-ship/project.toml [map] source_roots: expected paths inside the repository",
    ),
    (
        PROJECT,
        'stack = "python"\n[kit]\noptional = ["rs-contribute"]\n',
        ".rapid-ship/project.toml [kit] optional: expected names of the Kit's optional skills: "
        "none in this Kit version",
    ),
]
```

  with matching rows for `[map] unguided` and `[tests] unit`. `tests/test_kit_seed_comments.py`, docstring `Offline: every seed documents each key, and names every key its loader accepts.`:
  - `test_each_seeded_toml_key_has_a_comment`, over the rendered `project.toml` of both stacks and the Python `pyproject.toml`: every line that matches `^\s*[\w."-]+\s*=` has a `#` comment on it, or sits in a run of such lines, with no blank line or table header between them, directly below a comment line, as Spec 1's four App keys do.
  - `test_each_ci_workflow_key_has_a_comment`: the same rule for each line that matches `^\s*(- )?[\w-]+:` outside a `run: |` block.
  - `test_each_protected_group_is_under_a_heading`: for both templates, the line above each line that `patterns_in` reads is another such line or starts with `## `, and the header holds `# Lines that start with ## stay comments in Flight.` It fails today, because the first group sits under `# settings file can switch its check off.`
  - In `tests/test_kit_contents.py`, Task 11's `test_the_python_codeowners_only_adds_the_starter_patterns_and_the_python_settings` expects `"## The starter Patterns."` right before `*patterns`.
  - `test_each_seed_names_every_key_its_loader_accepts`: each key of `PROJECT_KEYS` appears as a key line under its table in both `project.toml` seeds, and each of `EXCEPTION_KEYS` appears in the `exceptions.toml` seed's commented example as `# <key> = `.
- [ ] **Step 2: run** them; expected FAIL.
- [ ] **Step 3: implement**; add the comments; edit this repository's two seeded copies in place; sync.
- [ ] **Step 4: run** `tests/devctl/test_devctl_settings*.py`, `tests/test_kit_seed_comments.py` and `tests/test_kit_contents.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: document every seeded key and name what each settings key accepts`.

### Task 16: `sync`'s migrations, documents, and PR 5.4's verification

**Files:**
- Create: `rapid_ship/kit/migrations.py`, `tests/test_kit_migrations.py`
- Modify: `rapid_ship/kit/sync.py` (`SyncResult`, `sync_repository`), `rapid_ship/cli.py` (`_sync`), `tests/test_kit_sync.py`; `ARCHITECTURE.md`, `rapid_ship/kit/AGENTS.md`, `rapid_ship/AGENTS.md`, the root `AGENTS.md`, `README.md`, Spec 1's section 4 example and status line, and the plan index (plan 5 built)

**Interfaces:**
- Consumes: the index's `Migration`, unchanged.
- Produces:

```python
# rapid_ship/kit/migrations.py
MIGRATIONS: tuple[Migration, ...]


@dataclass(frozen=True)
class Pending:
    migration: Migration
    before: str
    after: str


def pending(root: Path, excluded: Sequence[str]) -> list[Pending]: ...
def migration_body(found: Sequence[Pending], version: str) -> str: ...


# rapid_ship/kit/sync.py: SyncResult gains
#     migrations: list[Pending]
#     migration_branch: str | None
#     migration_pull_request: str | None
```

- `MIGRATIONS` holds one migration per table that plan 4 dropped and devctl refuses: `0.2.0-remove-agents`, `0.2.0-remove-dispatch`, `0.2.0-remove-linear`, `0.2.0-remove-release` and `0.2.0-remove-roster`, each on `.rapid-ship/project.toml`. `applies` finds the table's header, `[<name>]` or `[<name>.<sub>]`, outside a comment; `edit` deletes each such header and its lines up to the next header or the end of the file, with the blank lines that end it, and keeps comments above the header. Ruling: `[roster]` too, because devctl refuses it like the others.
- `MIGRATIONS` also holds `0.2.0-root-guide-links` on `AGENTS.md`, because map rule 8 (Task 9) changes what the seeded root guide must contain, and Spec 1 section 3 then requires a migration beside the warning period. `applies` when the text has a `## Find the change` table and no Markdown link to `README.md` or to `ARCHITECTURE.md`; `edit` inserts Task 9's row for each missing link right below the table's separator line, README's first. Ruling: a guide without that table is left to the owner, whom map rule 8's message tells what to add.
- `pending` applies the migrations in order to each file that exists and is not under `[kit] exclude`, and returns one `Pending` per migration that applies.
- Ruling: `sync` checks the migrations on every run, before its "nothing changed" return, because a project already at the current templates can still hold an old table.
- Without `--in-place`, after the sync branch and its PR, when migrations apply: create `rapid-ship/kit-migrate-<version>` at the sync branch's commit, or at `HEAD` when no template changed, refusing an existing branch; write the edits; commit `chore: migrate seeded files for rapid-ship Kit <version>`; open the PR `Migrate seeded files for rapid-ship Kit <version>` against the sync branch, or the starting branch when there is none; and stay on the migration branch, as `sync` stays on its own. On a failure it restores the files, goes back to the branch it started from and deletes the migration branch, as `_stopped` does. Ruling: these names and that base, because Spec 1 bases the branch on the sync branch.
- `migration_body` lists ``- `<path>`: <explanation>`` for each, says the files are Protected and the owner merges, and ends with `## Evidence` and `Not covered: sync did not run ./devctl check; CI runs it on this pull request.`, as `pull_request_body` does.
- With `--in-place`, `_sync` prints `migration <id>: <path>: <explanation>` and a unified diff of the edit for each, writes none, and exits 1. Ruling: exit 1, because the project still holds content devctl refuses and the owner must act.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_migrations.py`, docstring `Offline: sync's migrations against fixture repositories and a recording PR opener.`:

`OLD_SEED` is the text of `git show 247f9db:rapid_ship/templates/python/.rapid-ship/project.toml`, plan 3's seed with live `[linear]`, `[dispatch]` and `[release]` tables, rendered for `octo/demo-app` and written into the test as a string.

```python
def test_plan_3s_seed_loads_after_its_migrations(tmp_path: Path) -> None:
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship" / "project.toml").write_text(OLD_SEED)
    found = pending(tmp_path, ())
    assert [item.migration.id for item in found] == [
        "0.2.0-remove-dispatch",
        "0.2.0-remove-linear",
        "0.2.0-remove-release",
    ]
    text = found[-1].after
    assert all(not item.migration.applies(text) for item in found)
    assert "[tests]" in text
    assert "[linear]" not in text


def test_each_migration_id_is_unique_and_names_the_kit_version() -> None:
    ids = [migration.id for migration in MIGRATIONS]
    assert len(ids) == len(set(ids))
    assert all(identifier.startswith("0.2.0-") for identifier in ids)
```

  Also: the edited text loads with `devctl.settings.load_project` (devctl is importable in tests); `test_an_excluded_path_is_never_migrated`; `test_in_place_lists_each_migration_and_writes_none` (the file's bytes are unchanged and `result.migrations` lists three); `test_sync_proposes_the_migrations_on_a_second_branch_and_pr` with `PullRequests` from `test_kit_sync.py` (two calls: the sync PR, then `("rapid-ship/kit-migrate-9.9.9", "rapid-ship/kit-sync-9.9.9", "Migrate seeded files for rapid-ship Kit 9.9.9", body)`, where the body names each edit and has `## Evidence`, and HEAD is then on `rapid-ship/kit-migrate-9.9.9`); `test_the_root_guide_migration_adds_the_missing_rows` (the root guide that `v0.1.0` seeds, from `git show v0.1.0:rapid_ship/templates/common/AGENTS.md` rendered for `demo-app` and written into the test, gets both rows right below the separator, after which `applies` is False; a guide that links both, or has no Find the change table, is left alone); `test_migrations_run_when_the_kit_is_otherwise_current` (one call, based on `main`); and `test_rapid_ship_sync_in_place_exits_1_and_lists_each_migration` through `rapid_ship.cli.main`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_migrations.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'rapid_ship.kit.migrations'`.
- [ ] **Step 3: implement.** `sync.py` stays under 500 lines because the branch work for migrations lives in a helper beside `_start_branch`; `migrations.py` imports nothing from `sync.py`.
- [ ] **Step 4: run** `tests/test_kit_migrations.py` and `tests/test_kit_sync*.py`; expected PASS. `uv run rapid-ship sync --in-place` in this repository lists no migration. Status, fast check.
- [ ] **Step 5: commit** `feat: propose migrations of seeded settings from rapid-ship sync`.
- [ ] **Step 6: documents.** Describe the migrations and plan 5 as built in the files above, add Task 15's `repository` and `source_roots` comments to Spec 1 section 4's `project.toml` example, and move plan 5's row to Built; commit `docs: record plan 5 as built`.
- [ ] **Step 7: verify.** Run the five checks with `--base plan5-standards`, record them in the Verification record, and handle the diff cap as Task 14 Step 6 says. Commit `docs: record PR 5.4's verification`.

## Verification record

Each PR's last task fills its row with the command, its exit code and the summary line it printed. A blocked, skipped or simulated result is written as such, never as passed.

| PR | `uv run pytest -q` | `./devctl check --tier fast` | `uv run rapid-ship status --strict` | `./devctl check --tier full --base <base> --pr-body <body>` | `npm --prefix website run build` |
| --- | --- | --- | --- | --- | --- |
| 5.1 | | | | | |
| 5.2 | | | | | |
| 5.3 | | | | | |
| 5.4 | | | | | |
