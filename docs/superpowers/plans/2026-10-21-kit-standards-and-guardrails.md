# Kit Standards and Harness Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the hook spike first. Then give every Kit project `devctl hook` with G1 to G5, G7, G8 and the merge guard, wired for Claude Code; the README.md and ARCHITECTURE.md seeds with map rule 8 and `./devctl doctor --settings`; the Pattern `task` key and Lessons section with the Python starter Patterns; the `SKILL.md` rule; the 1,500-line diff cap and the ledger rule; one CI concurrency group for each push run; documented, validated settings; `sync`'s migrations; and the `dead-code` check step for Python, which fails on code and declared dependencies that nothing uses, and on imports that the declared dependencies do not cover.

**Architecture:** Five stacked PRs, 5.1 to 5.5, each reviewed and squash-merged on its own. devctl changes only in its template under `rapid_ship/templates/common/tools/devctl/devctl/`, and `uv run rapid-ship sync --in-place` vendors it. `devctl hook claude pre-tool` turns Claude Code's PreToolUse event into a `ToolCall` (`hook_protocols.py`), splits the command line and parses the git and gh forms (`command_line.py`), applies the rules (`hook.py`) and, for `gh pr merge` alone, the merge guard (`merge_guard.py`), which reads GitHub through doctor's `OwnerGet`. The Protected-set reader and the ledger rule live in `codeowners.py`, which the hook, the guard and the `diff` step share. `rapid_ship/kit/migrations.py` holds the migrations that `sync` proposes. PR 5.5's `check/stacks/python_dead_code.py` runs vulture and deptry, and reads the allowlist items in `pyproject.toml` for the exceptions step.

**Tech Stack:** Python 3.12+ standard library (`shlex`, `json`, `base64`, `difflib`, `tomllib`), PyYAML, git 2.31+, gh, uv, pytest, Ruff, mypy, import-linter, zizmor 1.30.1, Claude Code hooks (2.1.304 in the hook spike), Docusaurus for the docs site. From PR 5.5, vulture 2.16 and deptry 0.25.1, as dev dependencies.

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), sections 3 (migrations), 4 (Kit contents, settings files, Patterns, Harness guardrails, the merge guard, the Protected set, CI), 5 (map rules, diff policy, dead code, exceptions), 6 (`doctor --settings`, `devctl hook`), 10 (plan 5's tests and trials) and 11 (open questions). Plan 5 of 7 in the [plan index](2026-10-14-kit-and-setup.md), whose Conventions, Layout, Shared interfaces and "Plan 5: Kit standards and Harness guardrails" outline bind this plan.

**Status:** planned on 2026-10-21. Plan 4 and its follow-ups are merged (#31 to #33), and `v0.1.0` is tagged at `0e1d6d0`. This document lands in PR 5.1. The hook spike is recorded on 2026-10-22, and Task 1 Step 9 revised Global Constraints, Review Focus and Tasks 4 and 6 to wire Claude Code's `Monitor` tool. PR 5.5 was added on 2026-10-25 for the owner's decisions of that day on the `dead-code` step, which its introduction lists.

**Owner steps:** Task 1, Task 8 and Task 17's Step 1 are Owner steps that an agent prepares. Task 17's Step 1, the owner's approval of two dev dependencies, was done on 2026-10-25. The controller never dispatches an Owner step to an implementer subagent, and no agent runs one. The agent writes the procedure and the empty record. The owner runs every Harness Session, GitHub write and push. The implementer then writes from the owner's recorded output.

## Global Constraints

- Commands (index, Conventions): `devctl hook claude pre-tool`; `devctl doctor [--skills | --settings]`; `rapid-ship sync [--in-place] [--revert PATH]...`.
- Exit codes: 0 success; 1 a check failed, something is missing, or a request was refused; 2 the command could not run. `devctl hook` follows Claude Code's hook protocol, a workaround documented in `hook_protocols.py`, and exits 1 on an internal error, never 2 (index; Spec 1 section 4).
- "The hook only denies or asks. It never allows or approves anything; with no rule matched it gives no decision" (Spec 1 section 4).
- Claude Code wiring: `PreToolUse` for `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit` and `Monitor`, running `"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool`, as Spec 1 section 4 states it once PR 5.1 has merged. Plan 5 wires no other Harness.
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
- File-size cap: `LINE_CAP = 500` lines for each `.py` file under `[map] source_roots`, which in this repository include the devctl templates. Task 3 puts the hook in four new modules, Task 9 moves map rule 7 out of `check/map.py` (443 lines), and Task 13 keeps `check/stacks/python.py` (469 lines) unchanged. Task 17 puts the dead-code step in its own module, `check/stacks/python_dead_code.py`, and adds only deptry's comment pattern to `check/stacks/python.py`, which stays under the cap.
- devctl source is edited only under `rapid_ship/templates/common/tools/devctl/`. Run `uv run ruff format <files>` and `uv run ruff check <files>` on the changed template files, then `uv run rapid-ship sync --in-place`. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit the vendored copy. Tests import the vendored copy (`pyproject.toml` sets `pythonpath = ["tools/devctl", "tests/devctl"]`), so a step formats, checks and syncs before each test run that expects a pass.
- devctl starts processes only through `process.run_process`, called through the module. devctl depends only on PyYAML and PyJWT; plan 5 adds none to devctl. PR 5.5 adds vulture and deptry to the dev group of this repository and of the Python seed, which the owner approved on 2026-10-25 (Task 17 Step 1). It also declares `cryptography`, which `rapid_ship/app_flow.py` imports, as a direct dependency of this repository.
- No `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression carries an `rs-exception` marker and an entry in `.rapid-ship/exceptions.toml`.
- Write tests first. A test module's docstring starts `Offline:` and names what it simulates. A blocked, skipped or simulated check never counts as passed.
- `uv run pytest` and `./devctl check --tier full` need network access and gitleaks 8.30.1 on `PATH`.
- Agent identity is on in this repository. In every Session, the controller's included, agents push only with `./devctl as worker push` and run `gh` writes as `./devctl as <role> gh`.
- From Task 6 on, a Claude Code Session started in a checkout that holds the seeded `.claude/settings.json` runs `devctl hook`. Claude Code reads its hooks when a Session starts, so a Session started earlier, or in a checkout without the file, runs none. The controller's Session for this plan is such a Session, so the owner approves the Protected changes at each PR, which only the owner merges. Never start a new Session in a checkout without the wiring to avoid an ask. In a Session that runs the hook:
  - G5 asks the owner before each Edit or Write of a Protected path. This repository's CODEOWNERS covers `/**/AGENTS.md`, `/.claude/`, `/.github/`, `/.rapid-ship/` and `/pyproject.toml`, which Tasks 6 to 9 and 13 to 17 edit. In a headless Session each such edit is denied, and the owner makes it.
  - G7 and G8 deny an agent's `git push` and its `gh` writes as the owner.
  - If the hook blocks every call, the owner, never an agent, starts a Session with `--settings '{"disableAllHooks": true}'` to fix it, and the PR body records that Session.
- Branches: 5.1 `plan5-hook-spike` on `main`; 5.2 `plan5-guardrails` on 5.1; 5.3 `plan5-standards` on 5.2; 5.4 `plan5-settings-migrations` on 5.3; 5.5 `plan5-dead-code` on 5.4. Each PR's base is the branch below it. Each PR touches the Protected set, so the owner merges it in GitHub's web interface. After the PR below squash-merges, GitHub deletes its branch and retargets the next PR to `main`; if it did not, the controller retargets it with `./devctl as worker gh api -X PATCH repos/proxy-hatch/rapid-ship/pulls/<n> -f base=main` (`gh pr edit` fails on GitHub's retired classic Projects API). The controller then confirms that `main`'s tree equals that PR's head (`git diff --quiet main <the branch below>`), runs `git merge -s ours main` and pushes with `./devctl as worker push`: the branch already holds that content, and a plain merge conflicts on this plan file. The Worker App cannot push a commit that edits `.github/workflows/` (plan 4's Checked facts), so the owner pushes the commits of Tasks 14 and 15 that edit this repository's CI workflow. A push whose new commits only merge in a workflow change already on the base goes through (plan 4's trial rerun of 2026-10-21), so the controller pushes the later merges of `main`.
- PR 5.5 merges before `v0.2.0` is tagged, and the owner holds the tag until then. The dead-code step's warning period is `GRACE_VERSION`, `0.2.0`, so the step must ship in that version. If `v0.2.0` is tagged first, the controller stops PR 5.5 and asks the owner: the step then needs the next Kit version and a grace version of its own.
- Each PR's last task runs and records `uv run pytest -q`, `./devctl check --tier fast`, `uv run rapid-ship status --strict`, `./devctl check --tier full --base <PR base> --pr-body <body file>` and, when docs change, `npm --prefix website run build`, in the Verification record at the end of this plan.
- Ruff formats the `python` code blocks of a Markdown file, so keep this plan's blocks valid Python in Ruff's layout.
- Commit trailer: each commit ends with `Co-Authored-By: <the model that writes the commit>`, such as `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The merge guard runs out of time.** A `gh pr merge` whose reads are slow, or whose PR lists many file pages, can outlast Claude Code's hook timeout; a killed hook lets the merge through (Spec 1 section 4). Expected: the guard denies before a read that could end after the hook run's 300-second budget, which every merge on the line shares. Task 5's `test_the_guard_denies_before_a_read_could_pass_its_budget` pins it.
2. **A command line hides a second command.** Inputs: a newline, `&`, a subshell `( … )`, `$( … )` and backticks, a `#` comment, a heredoc, a redirection such as `2>&1`, a leading `NAME=value` and an absolute path to git. Expected: each simple command is checked, no heredoc body is, and no redirection's words count as arguments. Task 3's `SHELL` rows pin it.
3. **A Session edits in a linked worktree.** Claude Code keeps `$CLAUDE_PROJECT_DIR` at the main checkout while the edit lands in a worktree. Expected: G4 and G5 judge the path against the worktree that holds it, with that worktree's CODEOWNERS. Task 4's `test_run_hook_judges_an_edit_by_its_linked_worktree` pins it.
4. **An event the hook does not expect.** Inputs: a tool the hook does not wire, a missing `tool_input`, bytes that are not JSON, an unknown or missing Harness name. Expected: no decision for an unwired tool, exit 1 for the rest, never exit 2. Task 4's `test_the_hook_never_exits_2` pins it.
5. **`gh pr merge` names another repository.** Inputs: `-R x/y` after or before `merge`, a PR URL, and a PR URL with `-R a/b`. Expected: the guard reads that repository, not `[github] repository`, and the URL's when both name one, as gh does. Task 5's `test_each_target_reads_its_pull_request` pins it.
6. **The guard counts the wrong review.** With Agent identity on, a mistake here silently merges a head the Reviewer never approved, the case the check exists to stop. Inputs: no review, a person's approval, the login `o-reviewer` without `[bot]`, an approval of an older commit, a later request for changes, a later comment or dismissed review, and reviews over two pages. Expected: only the Reviewer App's latest review that approves or requests changes decides, and the guard denies unless it approves the head SHA the guard read. Task 5's `test_with_agent_identity_a_head_without_the_reviewer_apps_approval_is_denied`, `test_comments_and_dismissed_reviews_do_not_decide` and `test_reviews_are_read_page_by_page` pin it.
7. **A shell command runs through `Monitor`.** Claude Code's `Monitor` tool runs a shell command, and the hook spike recorded its `PreToolUse` event with `tool_input.command`. A wiring or a `read_event` that leaves it out lets every shell rule and the merge guard be bypassed. Expected: the seed's matcher names `Monitor`, `read_event` reads its `command` as `Bash`'s, and doctor reports a wiring without it. Task 4's `test_a_recorded_monitor_event_with_a_force_push_is_denied` and Task 6's `wired("Bash|Edit|Write|MultiEdit|NotebookEdit")` row pin it.
8. **An allowlist item or a deptry comment hides a finding without a marker.** Inputs: `per_rule_ignores = { DEP002 = ["psycopg2"] }` under `[tool.deptry]`, `package_module_name_map = { foo-python = "foo" }` under `[tool.deptry]`, a top-level dotted key `tool.vulture.ignore_names = ["x"]`, an item in a `"""` string, two items on one line, each with its marker, `import yaml  # deptry: ignore[DEP003]` and `import yaml  # deptry: ignored` in a Python file, and a noqa comment inside a string. Expected: from the Kit version after 0.2.0, the exceptions step fails each unmarked item and comment, each line that vulture or deptry reads as a suppression, each item it cannot place on a line, and the line with two items. Task 17's `test_an_item_devctl_cannot_place_on_a_line_fails`, `test_two_items_on_one_line_fail`, `test_deptrys_inline_comment_is_a_suppression` and `test_vulture_and_deptry_read_the_whole_line` pin it.
9. **A project's settings switch a kind off.** Inputs: `min_confidence = 100` in `[tool.vulture]` and `ignore = ["DEP002"]` in `[tool.deptry]`. Expected: vulture's `--min-confidence 0` on the step's command line replaces the file's value. deptry's command line names no `--ignore`, so each code in `ignore` is an allowlist item that fails without its marker. Task 17's `test_both_tools_pass_and_run_through_uv` pins the command lines, and `test_each_allowlist_key_names_its_rule` the `ignore` item.
10. **An existing project's settings stop a tool.** Inputs: a dev group without vulture or deptry, and no `[tool.vulture] paths`. Expected: the step runs neither tool and names each setting to add; in Kit 0.2.0 it is not applicable with those warnings, and from the next version it is blocked. Task 17's `test_without_the_tools_or_paths_the_step_warns_in_kit_0_2_0_and_blocks_after` pins it.

## File Structure

`devctl/` means the template `rapid_ship/templates/common/tools/devctl/devctl/`; `sync` writes its vendored copy.

| File | PR | Responsibility |
| --- | --- | --- |
| `devctl/codeowners.py` | 5.2 | The Protected-set lines and their matcher, moved from `check/diff.py`; the ledger rule |
| `devctl/command_line.py` | 5.2 | Shell splitting, and the git and gh forms the guardrails read |
| `devctl/hook_protocols.py` | 5.2 | `Decision`, `ToolCall`, `HookSettings`, Claude Code's event and answer, the exit-code workaround |
| `devctl/hook.py` | 5.2 | G1 to G5, G7 and G8, the hook's settings, `devctl hook` |
| `devctl/merge_guard.py` | 5.2 | `find_merge` for G3, the merge guard (G9) |
| `devctl/merge_guard_github.py` | 5.2 | The merge guard's GitHub reads: the PR, CODEOWNERS on its base, its files, reviews and check runs |
| `common/.claude/settings.json` | 5.2 | The seeded Claude Code wiring |
| `devctl/check/map_skills.py` | 5.3 | Map rule 7, moved from `check/map.py` so `map.py` stays under the cap |
| `common/README.md`, `common/ARCHITECTURE.md` | 5.3 | The seeds that map rule 8 checks |
| `python/docs/patterns/python-*.md`, `python/src/__package__/{errors,inputs,settings,profiling}.py`, `python/tests/test_{errors,inputs,settings,profiling}.py` | 5.3 | The Python starter Patterns and the performance Pattern, with reference code and tests |
| `rapid_ship/kit/migrations.py` | 5.4 | `Migration`, `MIGRATIONS`, the pending edits and their PR body |
| `devctl/check/stacks/python_dead_code.py` | 5.5 | The `dead-code` step for Python, its floor settings, and the allowlist items that `pyproject.toml` holds |

---

## PR 5.1: the hook spike (`plan5-hook-spike`, on `main`)

### Task 1: The hook spike (PRO-139), an Owner step

**Files:**
- Create: `docs/trials/<run date>-hook-spike.md`, named by the date the owner runs it
- Modify: `docs/trials/AGENTS.md`; Spec 1 sections 4, 10 and 11 where the record differs, and its status line; the plan index; the files that hold the stale text of Step 8; this plan, for the gate in Step 9 and the Verification record

**Interfaces:**
- Produces: the record's scrubbed Claude Code events, each a fenced `json` block under a heading named by its fixture file: `bash.json`, `bash-subagent.json`, `write.json`, `edit.json`, `notebook-edit.json` and `monitor.json`. No event named `MultiEdit`, so the record has no `multi-edit.json`. Task 4 copies them into `tests/devctl/fixtures/hooks/claude/`. Ruling: the events live in the record, because PR 5.1 holds no product or test code and the docs site publishes Markdown only.

- [ ] **Step 1 (agent): write the record's preparation.** Sections: Purpose, Versions, Setup, Procedure, Results, Events, Timing, Decisions, Limits. Setup holds, as fenced blocks:
  - the stand-in hook `standin.sh <harness>`, a POSIX `sh` script. It saves stdin, with its argv, `pwd`, `$CLAUDE_PROJECT_DIR` and its start and end times in milliseconds, to a new file under `$SPIKE_DIR/events/`. It then acts on the word in `$SPIKE_DIR/mode`: `none` exits 0 with no output; `deny` and `ask` print that Harness's documented deny or ask answer with the reason `spike: <mode>` and exit 0; `exit1` and `exit2` write `spike: exit <n>` to stderr and exit with that code; `sleep` sleeps 10 seconds, twice the wiring's `timeout` of 5;
  - the scratch repository `hook-spike`, made with `git init` outside rapid-ship, with one commit and a linked worktree from `git worktree add .worktrees/wt`, holding `spike.ipynb` with one code cell and three wiring files: `.claude/settings.json` (PreToolUse, matcher `Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor`), `.codex/hooks.json` (`PreToolUse` for `Bash` and `apply_patch`) and `.agents/hooks.json` (`PreToolUse`), each running `standin.sh` with its Harness name and `timeout` 5. The agent writes each answer format and wiring file from the Harness's current hook documentation and cites the page and the date.
- [ ] **Step 2 (Owner): the event matrix.** For each Harness (Claude Code, Codex, agy) and each Session kind (a lead Session; a subagent that the lead starts; a headless Session: `claude -p`, `codex exec` and agy's documented headless mode), set mode `none` and give this prompt: "Run `git status` in the shell. Write `spike.txt` containing `x`, then edit it so it contains `y`. Replace cell 0 of `spike.ipynb` with `print(1)`." In Claude Code also ask for `git status` through the Monitor tool. Record, for each cell, whether an event was saved for the shell call and for each file edit, and keep every event file.
- [ ] **Step 3 (Owner): the answers.** In a lead Session of each Harness, repeat the shell prompt with modes `deny`, `ask`, `exit1`, `exit2` and `sleep`. Record whether the call ran, what the Session showed and where the reason appeared, and, for `ask`, whether a prompt appeared. Repeat `deny`, `ask` and `exit1` in a subagent of each Harness, because whether a deny holds there decides that Harness's wiring, and `deny` and `ask` in each headless Session. In Claude Code also record: `ask` in `bypassPermissions` mode; and, in a Session started in `hook-spike`'s main checkout, a file edit inside `.worktrees/wt`, with the event's `cwd` and the hook's `$CLAUDE_PROJECT_DIR`.
- [ ] **Step 4 (Owner): Codex's review.** Record the trust and `/hooks` review prompts on the first run, and whether a changed `.codex/hooks.json` asks for a new review.
- [ ] **Step 5 (Owner): the hook's cost.** In this repository's main checkout, run `/usr/bin/time -p ./devctl --version` once after `rm -rf tools/devctl/.venv` and 20 times after that. Record the cold time and the warm median and maximum. Ruling: `./devctl --version` stands in for `devctl hook`, which does not exist yet; it pays the same uv and Python start and imports devctl's CLI. Task 8 times the real hook.
- [ ] **Step 6 (Owner): decide.** Record two decisions: whether G1 to G4 stay in the hook, from the measured time; and whether a follow-up adds the wiring for Codex and for agy, Codex's without G5 if its hooks cannot ask. Each yes becomes a backlog item in Linear, with its own plan later.
- [ ] **Step 7 (implementer): write the record.** Fill Versions, Results, Timing and Decisions from the owner's output, and label each result as observed in a run. Record Claude Code's documented default timeout for command hooks, with the page and the date. For each Claude Code event, replace the values of `session_id`, `prompt_id`, `transcript_path`, `tool_use_id`, `agent_id` and `scratchpad_dir` with `"<redacted>"`, the scratch repository's path with `/repo` (its worktree becomes `/repo/.worktrees/wt`) and any other home or temporary path with `<redacted>`; list the replaced fields, and put the event under its fixture heading. Results names each event's scrubbed `tool_input` value, such as its `command`, `file_path` or `notebook_path`, because Task 4 expects them. The docs site publishes trial records, so before the commit `grep -n -e /Users/ -e /home/ -e /private/tmp -e /tmp/ <the record>` finds nothing. Add one line to `docs/trials/AGENTS.md`: a spike record keeps its scrubbed event JSON in fenced blocks, and tests copy them as fixtures.
- [ ] **Step 8 (implementer): change the documents.**
  - Spec 1, where the record differs: section 4's wiring row (for example `MultiEdit` if Claude Code no longer has it, or `Monitor` if it runs shell commands that the hook does not see), the exit-code and timeout bullets, and which repository the hook reads in a linked worktree; section 10's spike bullet, as done; section 11's "Codex and agy wiring" and "The hook's cost", with the owner's decisions; the status line.
  - The plan index: plan 5's row and outline (5.1 built). Add this plan to the 5.1 file list.
  - The stale text, because plan 4 is merged in #31 to #33 and tagged `v0.1.0`: fix every hit of `git grep -n -i -e 'not merged yet' -e 'no release tag' -e 'no release is tagged' -e 'before the first tag'`, except in a built plan's conventions and task steps, which are its record, and in this plan's own instructions. Ruling: the index's Conventions bullet on Kit releases (`2026-10-14-kit-and-setup.md:41`) binds plans 6 and 7, so it is not a built plan's record: it keeps the tag form, `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<version> rapid-ship <command>`, and gives `--from <local checkout>` for a version that has no tag yet.
- [ ] **Step 9 (gate).** When the record changes what Tasks 3 to 8 assume (the event fields; the recorded command text and file paths, which Task 4 expects as `git status`, `/repo/spike.txt` and `/repo/spike.ipynb` with `cwd` `/repo`; the deny and ask answer; exit 1 not blocking; Claude Code's documented `"onFailure": "block"` hook setting, from v2.1.295, which makes a failed or timed-out hook block the call, against Spec 1 section 4's "the call goes through" and the premise of the guard's budget; the tool names; the hook's working directory; the default hook timeout), revise those tasks in this document within PR 5.1. The record reports `"onFailure": "block"`; if the spike's decisions use it, Tasks 3 to 6 and Spec 1 change within PR 5.1 under this step. If the owner moves G1 to G4 out of the hook, stop: Tasks 3, 4 and 6 change, and the owner approves the revised plan before PR 5.2 starts.
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
def read_settings(root: Path) -> HookSettings | str: ...  # str: why they are unreadable
def decide(
    call: ToolCall,
    root: Path | None,
    settings: HookSettings | None,
    branches: Callable[[], LocalBranches],
) -> tuple[Decision, str]: ...  # G1 to G5, G7 and G8; the merge guard is run_hook's (Task 5)
```

Rulings for this task, each where Spec 1 section 4 leaves the choice:
- Ruling: the types, `HookSettings` included, live in `hook_protocols.py` and the parsers in `command_line.py`, because `hook.py` imports `merge_guard.py` and both use them; one module for each keeps every file far under the cap and the imports acyclic.
- Ruling: `simple_commands` reads a line as the shell splits it, because agents often add comments, heredocs, substitutions and `2>&1` to their commands. One scan reads the line from left to right as the shell does, quotes included, and Step 3's lexer then splits the text the scan keeps:
  - The scan reads single quotes, double quotes, a backslash escape, `$'…'` with its escapes and `$"…"` as the shell does. It marks quoted or escaped text, so the lexer never reads it as an operator: `';'` and `\;` are words. An unclosed quote is an error.
  - It removes each comment, from a `#` that starts an unquoted word to the end of its line, and joins each backslash-newline outside single quotes. A `#` inside a word, as in `a#b`, after an escaped space as in `a\ #b`, or after a backslash-newline inside a word, is part of that word. Kept as words, a comment such as `# don't` would open a quote that never closes, so the hook would exit 1 and the call would run unchecked; a kept backslash-newline would end the simple command, so `gh pr merge 7 \` with `--admin` on the next line would pass G3.
  - An unquoted `<<` outside comments and arithmetic opens a heredoc: `<<WORD`, `<<-WORD`, `<<'WORD'`, `<<"WORD"` or `<<\WORD`, with or without blanks between `<<` and the word. `<<<` opens none. At the next newline outside quotes, the scan skips the body of each heredoc opened before it, in turn: the lines up to and including the one that equals `WORD` (after leading tabs for `<<-`), or to the end of the text when no line does, as the shell reads it. A `<<` in quotes or in a comment hides no line.
  - It reads each substitution where it stands: `$( … )`, backticks, `<( … )` and `>( … )`, and `$( … )` and backticks inside double quotes too, where `<(` and `>(` are plain text. The commands inside a substitution come ahead of the line's other commands, innermost first, so the rules check them. The command that holds a substitution keeps its other words, and `$(...)` (`SUBSTITUTED`) stands where the substitution was, joined to the text around it, because the hook cannot know what it prints. So `git push origin $(git rev-parse HEAD):main --force` keeps `$(...):main` and `--force`: G2 still sees `--force`, and G3 the destination `main`.
  - It skips arithmetic, where `<<` is a shift: the arithmetic command `(( … ))`, a C-style `for (( … ))`, `$(( … ))` and the older `$[ … ]`, inside double quotes too for the last two. Each substitution inside arithmetic still gives its commands, and `$(( … ))` and `$[ … ]` leave `$(...)` in their word. As in bash, a `((` or `$((` whose first `)` at the outer level has no second `)` directly after it opens a subshell instead: `((a) )` and `$((a) )`.
  - After the scan, a file-descriptor number written directly before `<` or `>`, as in `2>&1`, is removed, so `gh pr merge 7 >/dev/null` keeps `7`. Step 3's lexer then splits the text, and the reserved words `!`, `{`, `do`, `elif`, `else`, `if`, `then`, `time`, `until` and `while` are dropped at the start of a simple command, so `if git push origin main; then …` gives the program `git`.
  - A punctuation token that holds `<` or `>` is a redirection: it and the word after it are dropped, and the simple command goes on. A separator before the `<` or `>` in the same token, as in `)>` or `;>`, still ends the command; the `&` of `&>` and `&>>` belongs to the redirection. Every other punctuation token (`;`, `&&`, `||`, `|`, `&`, `(`, `)`, a newline, or a run of them such as `);`) ends the simple command, so a subshell gives its contents as simple commands of their own.
  - A line that shell rules cannot split raises `ValueError`, because the shell rejects it too: one with an unclosed quote, substitution or `$[ … ]`, or a `<<` without a word. `run_hook` denies such a line when its text holds `gh`, `pr` and `merge` in that order, because the merge guard cannot check that merge (Task 5); any other such line is an internal error (exit 1).
  - Two misreads remain, and Spec 1 section 4's limits accept them: the scan does not read a substitution inside a heredoc body, which bash expands in an unquoted heredoc, and a `)` in a `case` pattern or in a `${ … }` expansion ends a `$( … )` early.
- Ruling: `parse_command` skips leading `NAME=value` words, matches the program by basename (`git`, `gh`, `devctl`), counts `devctl as <role> gh <args>` as `gh <args>`, and skips git's global options before the subcommand (`-C`, `-c`, `--git-dir`, `--work-tree`, `--namespace` and `--config-env` take a value). It follows no other wrapper, as Spec 1 section 4's limits say.
- Ruling: G1 reads every word up to `--`; in `git commit`, `-n` also counts inside a short-option cluster, up to the first letter that takes a value (`m`, `F`, `C`, `c`, `t`, `S`, `u`). A message that is literally `--no-verify` is denied too; the agent rewords it.
- Ruling: in `git push`, a short-option cluster counts each letter up to `o`; the values of `-o`, `--push-option`, `--repo`, `--receive-pack` and `--exec` are skipped; the first positional word is the remote and the rest are refspecs; `--delete` or `-d` makes each refspec a deletion of that branch; `--branches`, git's newer name for `--all`, counts as `--all`.
- Ruling: `gh api`'s method comes from `-X`, `-X<METHOD>`, `--method` or `--method=`, ignoring case; without one it is `POST` when `-f`, `-F`, `--field`, `--raw-field` or `--input` is given, else `GET`. The endpoint is the first positional word, without `https://api.github.com/`, a leading `/` and the query string. The subcommand of `gh pr` and `gh issue` is the first word that is not an option, skipping the value of `-R` or `--repo`; without one there is no write.
- Ruling: `find_merge` finds `merge` with the `gh pr` subcommand parser above, and records a `-R` or `--repo` value given before `merge` in `Merge.repository`. Its target is `gh pr merge`'s first positional word. It skips the values of `-b`/`--body`, `-F`/`--body-file`, `-t`/`--subject`, `-A`/`--author-email`, `--match-head-commit` and `-R`/`--repo`, given after a space or after `=`.
- Ruling: the GraphQL form matches when a `query=<text>` field given inline names one of Spec 1's seven mutations as a whole word; `query=@<file>` and `--input` are not read.
- Ruling: a call's repository is the nearest ancestor holding `.git`, a file or a directory, of the edited path for an edit and of `cwd` for a shell command. Claude Code keeps `$CLAUDE_PROJECT_DIR` at the main checkout while a Session edits in a linked worktree, whose own lock and CODEOWNERS its PR changes. An edit outside any repository gets no decision.
- Ruling: either settings file unreadable, or `project.toml` invalid, switches off all three of G5, G7 and G8, as Spec 1 section 4 says, and `read_settings` writes one stderr line, `devctl hook: <the SettingsError or OSError message>; G5, G7 and G8 give no decision`, and returns that message, which the merge guard's denial carries (Task 5). A missing CODEOWNERS file is an empty Protected set and leaves G7 and G8 on, because nothing is unreadable and doctor reports the missing file.
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
  - `test_unreadable_settings_switch_off_g5_g7_g8_and_say_why`: a `project.toml` holding `[linear]` makes `read_settings(root)` return a `str` that contains `[linear] was removed`, and its one stderr line starts `devctl hook: `, contains that `str` and ends `; G5, G7 and G8 give no decision`; a CODEOWNERS that is not UTF-8 gives a `str` too.
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
    ("gh pr -R x/y merge 7", "pr-merge", "7"),
    ("gh pr merge 2>&1", "pr-merge", None),
    ("gh pr merge 7 >/dev/null", "pr-merge", "7"),
    ("gh pr merge 7 --admin", "admin", None),
    ("./devctl as reviewer gh pr merge 7 --admin", "admin", None),
    ("gh pr --repo=x/y merge 7 --admin", "admin", None),
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


def test_a_repository_given_before_merge_is_kept() -> None:
    words = simple_commands("gh pr -R x/y merge 7")[0]
    assert find_merge(words, unread) == Merge(
        "pr-merge", "7", repository="x/y", command=("gh", "pr", "-R", "x/y", "merge", "7")
    )
```

- [ ] **Step 2: run them.** `uv run pytest tests/devctl/test_devctl_hook_rules.py tests/devctl/test_devctl_merge_guard_forms.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.hook'`.
- [ ] **Step 3: implement** the Interfaces above. After the scan and the descriptor pass, `simple_commands` splits with this lexer:

```python
lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&`\n")
lexer.whitespace = lexer.whitespace.replace("\n", "")  # a newline separates commands
lexer.whitespace_split = True  # keeps HEAD:refs/heads/main, +task and {owner} whole
lexer.commenters = ""  # the scan removed the comments
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
WIRED_TOOLS = ("Bash", "Edit", "Write", "MultiEdit", "NotebookEdit", "Monitor")  # Spec 1 section 4
HOOK_COMMAND = "devctl hook claude pre-tool"


def read_event(harness: WiredHarness, payload: bytes) -> ToolCall: ...  # ValueError: malformed
def answer(harness: WiredHarness, decision: Decision, reason: str) -> tuple[str, int]: ...


# devctl/hook.py
def run_hook(call: ToolCall, owner_get: OwnerGet) -> tuple[Decision, str]: ...
def hook_command(args: argparse.Namespace) -> int: ...  # never 2
def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None: ...
```

`read_event` takes `tool_input.command` for `Bash` and `Monitor`, which runs a shell command, `file_path` for `Edit`, `Write` and `MultiEdit`, and `notebook_path` for `NotebookEdit`; a relative path is resolved against `cwd`, and every path is normalised with `os.path.normpath`, without following symlinks. Any other tool gives `ToolCall(None, (), cwd)`. An event whose `hook_event_name` is not `PreToolUse`, or that lacks `cwd`, `tool_name` or `tool_input`, is a `ValueError`. `answer` returns `("", 0)` for no decision, and for `deny` or `ask` one line of JSON with exit 0. The module docstring documents the workaround: Claude Code blocks on exit 2, so the hook never exits 2; exit 1 is a non-blocking error, so the call goes through; and, from Spec 1 section 4, the cases before devctl runs (the shim's 127, uv's own exit 2, a parse failure, a timeout).

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
        ("monitor.json", ToolCall("git status", (), REPO)),
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
  - `test_a_recorded_monitor_event_with_a_force_push_is_denied`: `monitor.json` with its `tool_input.command` set to `git push --force origin task`; stdout's `permissionDecision` is `deny` and its reason starts `G2: `; exit 0.
  - `test_a_harmless_event_gets_no_decision`: stdout is empty; exit 0.
  - `test_the_hook_never_exits_2`, parametrized over: bytes that are not JSON; `{}`; a `PostToolUse` event; an event without `tool_input`; Harness `codex`; event `post-tool`; `main(["hook"])`; `main(["hook", "claude"])`; a `cwd` with an invalid `project.toml`. Each case returns 1 and writes a stderr line that starts `devctl hook: `, except the `cwd` with an invalid `project.toml`, which returns 0 and writes `read_settings`'s stderr line, which starts `devctl hook: ` too.

  And, calling `run_hook` with an `owner_get` that fails the test:
  - `test_run_hook_judges_an_edit_by_its_linked_worktree`: `<main>` commits `.rapid-ship/project.toml` (`stack = "python"`) and a `.github/CODEOWNERS` holding only `* @o`; a worktree on a new branch at `<main>/.worktrees/wt` then writes its own CODEOWNERS, `* @o\n# /**/AGENTS.md @o\n`. With the event's `cwd` at `<main>`, `run_hook` denies an edit of `<wt>/.rapid-ship/kit.lock` with a reason that starts `G4: `, asks for `<wt>/AGENTS.md` with `G5: `, and gives no decision for `<main>/AGENTS.md`.
- [ ] **Step 3: run** `uv run pytest tests/devctl/test_devctl_hook_protocol.py -q`; expected FAIL with `ImportError: cannot import name 'read_event'`.
- [ ] **Step 4: implement** the Interfaces. `run_hook` finds the root with `work_tree_root`, reads the settings, passing `decide` None when `read_settings` gives a reason, caches `read_branches(root or call.cwd)` behind `functools.cache`, and returns `decide`'s answer; Task 5 adds the guard.
- [ ] **Step 5: run.** Format, check and sync, then run the test file and `tests/devctl/test_devctl_cli.py`; expected PASS. Status, fast check.
- [ ] **Step 6: commit** `feat: answer Claude Code's PreToolUse hook with devctl hook claude pre-tool`.

### Task 5: The merge guard

**Files:**
- Modify: `devctl/merge_guard.py` (`guard`), `devctl/codeowners.py` (the ledger rule), `devctl/hook.py` (`run_hook`), `devctl/doctor_items.py:26` (`_GH_TIMEOUT_SECONDS` becomes public `OWNER_GET_TIMEOUT_SECONDS`), `devctl/doctor_github.py:112` (`_decoded` becomes public `decoded_contents`), `.rapid-ship/exceptions.toml` (EX-12)
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
    settings: HookSettings | None,  # None: none were read, so every merge is denied
    owner_get: OwnerGet,
    branches: Callable[[], LocalBranches],
    elapsed: Callable[[], float],  # seconds since the hook run started
) -> str | None: ...  # the denial message; None: no decision
```

`protected_changes` returns the sorted, unique paths that a pattern covers, both paths of a rename included, plus each existing ledger entry that a change modifies, removes or renames away from. An added entry is never checked. Ruling: `ledger_entry` takes any `.md` path below `docs/corrections/` except `docs/corrections/README.md`, because Spec 1 says "under" and a wider Protected rule fails safe. Ruling: GitHub's file statuses map as `added` and `copied` to added, `removed` to removed, `renamed` to renamed, and every other status to modified.

`guard` reads, in this order, through `owner_get`:
1. The PR. A number: `repos/<repository>/pulls/<n>`. A URL `https://github.com/<o>/<r>/pull/<n>`: that repository and number. A branch, or no target (the current branch from `branches()`): `repos/<repository>/pulls?head=<owner>:<branch>&state=open&per_page=100`, which must list exactly one PR. The repository is the URL's, else `merge.repository`, else `settings.repository`.
2. CODEOWNERS on the base: `repos/<repository>/contents/<name>?ref=<base>` for each name of `CODEOWNERS_FILES` in turn, until one exists, which is the copy GitHub reads; decoded with `decoded_contents`. A 404 moves to the next name, and three 404s are an empty Protected set.
3. The files: `repos/<repository>/pulls/<n>/files?per_page=100&page=<k>` from page 1 until a page holds fewer than 100. A 30th full page is a denial, because GitHub lists at most 3,000 files.
4. The reviews, only with Agent identity on: `repos/<repository>/pulls/<n>/reviews?per_page=100&page=<k>` from page 1 until a page holds fewer than 100. Of the reviews whose `user.login` is `<settings.reviewer_app_slug>[bot]` and whose `state` is `APPROVED` or `CHANGES_REQUESTED`, the one with the highest `id` decides; `COMMENTED`, `DISMISSED` and `PENDING` reviews are ignored. The head is approved when that review is `APPROVED` and its `commit_id` equals the head SHA the guard read.
5. The check runs: `repos/<repository>/commits/<head>/check-runs?check_name=devctl%20check&filter=latest&per_page=100`. Of the runs whose `app.id` is 15368, the one with the highest `id` decides. Its `<state>` is `missing` without one, its `status` while not `completed`, else its `conclusion`. Only `success` passes.

Then it denies with the Protected message, else the check message, else, with Agent identity on, the review message when the head is not approved, else the head message when `merge.head` differs from the head SHA it read; otherwise it returns `None`. With `settings` None, it denies before any read. `<the same command>` is `shlex.join(merge.command)`.

Rulings for this task:
- Ruling: the guard does not run inside `devctl as`; the hook runs it for `./devctl as <role> gh pr merge`, because Spec 1 section 4 gives a Harness without wiring no merge guard.
- Ruling: a `gh pr merge` that names no PR reads the current branch from local git (`LocalBranches.current`), because Spec 1's step 2 takes the PR of the current branch; the index allowed local git only for a push or a ref path, and Step 3 widens it.
- Ruling: the repository source order above. A URL's repository comes first, because gh's PR finder (`pkg/cmd/pr/shared/finder.go`) takes it before it consults `-R` or `GH_REPO`, so the guard checks the PR that gh merges: with gh 2.102.1, `gh pr view https://github.com/cli/cli/pull/1 -R proxy-hatch/rapid-ship` shows cli/cli#1 (checked 2026-10-22). `settings.repository` comes last, because `gh_get` runs outside the repository and `devctl as` gives gh `GH_REPO` from `[github] repository`.
- Ruling: the Protected message comes before the check message, and the check runs are read last, because waiting on a check cannot fix a PR only the owner can merge; a small PR still costs Spec 1's four reads, five with Agent identity on. The review message comes after the check message, because fixing a failed check pushes a new head, which needs a new review anyway, and before the head message, because the retry that message names would be denied without the approval.
- Ruling: of the Reviewer App's reviews that approve or request changes, the one with the highest `id` is the latest, as for the check runs. The reviews have no page limit of their own; the 300-second budget bounds their reads.
- Ruling: without settings the guard cannot tell whether Agent identity is on, so a merge is denied before any read (Spec 1 section 4). When `read_settings` gives a reason, `run_hook` denies the merge itself with the catch-all message below and that reason, and calls no `guard`, so the agent sees the file and the key to fix; `guard`'s `HookSettings | None` cannot carry the reason. `guard` gets None only when no repository holds the event's `cwd`, so `run_hook` read no settings, and then denies with a fixed reason.
- Ruling: `--match-head-commit` must equal the full 40-character head SHA, which is what GitHub compares.
- Ruling: before each read, the guard denies when `elapsed() + OWNER_GET_TIMEOUT_SECONDS > GUARD_BUDGET_SECONDS`, because Claude Code lets a call through when it kills a hook at its timeout, 600 seconds by default, which Task 1 records. `run_hook` passes every guard on a line one `elapsed`, so they share the budget. The constant is doctor_items' 60-second gh timeout, named `OWNER_GET_TIMEOUT_SECONDS` because `identity.py:26` already has a public `GH_TIMEOUT_SECONDS` of 600 seconds for `devctl as`, which would deny every guarded merge before its first read.
- Ruling: every other denial is `merge denied: the merge guard cannot check this merge: <reason>; fix that, then merge again`, where `<reason>` is gh's first error line (`OwnerReadError.message`), or one of: `no repository: set [github] repository in .rapid-ship/project.toml or pass -R OWNER/NAME`; `no open pull request has head <owner>:<branch>`; `<n> open pull requests have head <owner>:<branch>; name one by number`; `HEAD is detached and the command names no pull request`; `GitHub lists at most 3,000 files of a pull request, and this one has more`; `its GitHub reads would pass the 300-second budget`; the `str` that `read_settings` gives, in `run_hook`'s denial; `the hook cannot read .rapid-ship/project.toml or .github/CODEOWNERS`, for `settings` None; `the guard failed: <exception type>: <message>`. The last comes from one `except Exception` around the guard, marked `# noqa: BLE001  # rs-exception: EX-12` with its entry in `.rapid-ship/exceptions.toml`.

`run_hook` then, when `decide` gives no decision, calls `guard` for each simple command whose `find_merge` form is `pr-merge`, in order, with the settings it read (None when it read none) and one `elapsed` for the hook run; when `read_settings` gave a reason, it denies the first such command with that reason instead. It answers `("deny", message)` with the first denial, else no decision, because Spec 1 section 4 checks each simple command.

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
  - `test_each_target_reads_its_pull_request`: `gh pr merge task` and `gh pr merge` (current branch `task`) read `BY_BRANCH` first, served `[PULL]`; `gh pr merge https://github.com/x/y/pull/7`, `gh pr merge https://github.com/x/y/pull/7 -R a/b`, `gh pr merge 7 -R x/y` and `gh pr -R x/y merge 7` read `repos/x/y/pulls/7` first, with `OFF`, whose repository is `o/r`.
  - `test_a_pr_the_guard_cannot_identify_or_read_is_denied`: `reader.fail(PR, OwnerReadError(404, "HTTP 404: Not Found"))` gives `merge denied: the merge guard cannot check this merge: HTTP 404: Not Found; fix that, then merge again`; `replace(OFF, repository=None)` without `-R` gives the `no repository` reason; `BY_BRANCH` served `[]` and served two PRs give their reasons; a detached HEAD with no target gives its reason.
  - `test_an_error_inside_the_guard_is_denied`: `PR` served as `[]` gives a message starting `merge denied: the merge guard cannot check this merge: the guard failed: `.
  - `test_files_are_read_page_by_page`: page 1 holds 100 unprotected files and page 2 `.github/x`; the message names `(.github/x)`.
  - `test_codeowners_is_read_where_github_reads_it`: with `CODEOWNERS` failed with a 404 and `repos/o/r/contents/CODEOWNERS?ref=main` serving what `owner()` serves at `CODEOWNERS`, a PR changing `docs/AGENTS.md` is denied with the Protected message after reading both; with all three names failed with a 404, the same PR with `--match-head-commit <HEAD>` gets no decision.
  - `test_each_merge_on_the_line_is_guarded`: in a workspace whose `project.toml` records `repository = "o/r"`, `run_hook` on `gh pr merge 7 --match-head-commit <HEAD> && gh pr merge 8 --squash`, against `owner()`, which serves PR 7 only, reads PR 7's four paths, then `repos/o/r/pulls/8`, and denies with `merge denied: the merge guard cannot check this merge: Not Found; fix that, then merge again`.
  - `test_the_guard_denies_before_a_read_could_pass_its_budget`: an `elapsed` that answers `0.0`, then `250.0`, reads `PR` only, and the message ends `its GitHub reads would pass the 300-second budget; fix that, then merge again`.
  - `test_only_gh_pr_merge_reads_github`: `run_hook` with an `owner_get` that fails the test when called, for `git status`, `gh pr view 7`, `gh api repos/o/r/pulls/7`, `git push origin task` and `gh pr merge 7 --admin`; then `gh pr merge 7` in a workspace whose `project.toml` records `repository = "o/r"` reads `PR` first.
  - `test_with_agent_identity_a_direct_merge_meets_g8_before_the_guard`: with both Apps recorded, `gh pr merge 7` is denied with `G8: ` and reads nothing; `./devctl as worker gh pr merge 7` reaches the guard.
  - `test_reviews_are_read_page_by_page`: with `ON`, `REVIEWS` serves 100 reviews by `octo` and `repos/o/r/pulls/7/reviews?per_page=100&page=2` serves `[review(id=101)]`; the merge at `HEAD` gets no decision, and `reader.paths` holds both review pages before `RUNS`.
  - `test_the_denials_come_in_the_order_protected_check_review_head`: with `ON` and `owner(files=[{"filename": ".github/x", "status": "modified"}], reviews=[], runs=[run(conclusion="failure")])`, `gh pr merge 7 --match-head-commit <HEAD>` gives `merge denied: PR #7 touches the Protected set (.github/x); the owner merges it in GitHub's web interface`; with `ON` and `owner(reviews=[], runs=[run(conclusion="failure")])`, the same command gives `CHECKED.format("failure")`; with `ON` and `owner(reviews=[])`, `gh pr merge 7 --squash`, without `--match-head-commit`, gives `UNAPPROVED`.
  - `test_without_agent_identity_the_guard_reads_no_review`: with `OFF` and `owner(reviews=[])`, the merge at `HEAD` gets no decision, and `REVIEWS` is not in `reader.paths`.
  - `test_unreadable_settings_deny_every_merge`: `guarded(f"gh pr merge 7 -R o/r --match-head-commit {HEAD}", reader, None)` gives `merge denied: the merge guard cannot check this merge: the hook cannot read .rapid-ship/project.toml or .github/CODEOWNERS; fix that, then merge again`, and `reader.paths == []`; `run_hook` on the same line, in a workspace whose `project.toml` holds `[linear]`, gives a denial that starts `merge denied: the merge guard cannot check this merge: `, contains `[linear] was removed` and ends `; fix that, then merge again`, and reads nothing.
- [ ] **Step 2: run** `uv run pytest tests/devctl/test_devctl_merge_guard.py tests/devctl/test_devctl_codeowners.py -q`; expected FAIL with `ImportError: cannot import name 'guard'`.
- [ ] **Step 3: implement** the Interfaces; add EX-12 to `.rapid-ship/exceptions.toml` with `path = "rapid_ship/templates/common/tools/devctl/devctl/merge_guard.py"`, `rule = "BLE001"` and `remove_when = "The guard's reads and parsers raise only OwnerReadError, GitHubError and ValueError, so a narrow except covers them"`. Update the plan index's sketch: `Decision`, `ToolCall` and `HookSettings` in `hook_protocols.py`, `ToolCall.edits` as absolute paths, `decide`'s and `guard`'s signatures, `Merge`'s fields, `command_line.py` in the Layout, and `LocalBranches` read also for a `gh pr merge` without a target.
- [ ] **Step 4: run.** Format, check and sync, then run both files and `tests/devctl/test_devctl_doctor_github*.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add the merge guard to devctl hook`.

### Task 6: The seeded Claude Code wiring and doctor's wiring item

**Files:**
- Create: `rapid_ship/templates/common/.claude/settings.json`, `devctl/doctor_wiring.py`, `tests/devctl/test_devctl_doctor_wiring.py`
- Modify: `rapid_ship/templates/kit.toml` (`seeded` gains `".claude/settings.json"`), `devctl/doctor_local.py` (`local_items` adds the item after `_ci_item`), `tests/devctl/test_devctl_doctor_local_limits.py` (the order test gains `("guardrails", "Harness wiring")` after `("guardrails", "CI workflow")`, and the two summary tests their counts), `tests/test_kit_contents.py` (`SEEDED`), `.claude/AGENTS.md`
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
        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor",
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

The item is ok when `.claude/settings.json` is tracked, is valid JSON, does not set `disableAllHooks` to `true`, and each tool in `WIRED_TOOLS` matches a `PreToolUse` entry with a command hook that runs `devctl hook claude pre-tool`. An untracked or invalid file, or a gap, is missing, with the file and the tools named; a file it cannot read is unknown, as `_ci_item` does. Ruling, following Claude Code's documented matcher rules: a matcher covers a tool when it is `*`, empty or absent; a matcher made only of letters, digits, `_`, `-`, spaces, `,` and `|` is a list of exact names, split on `|` and `,`; any other matcher is an unanchored regular expression that `re.search` tries on the tool's name. Ruling: a command hook counts when its `command` and `args`, joined by spaces, contain `devctl hook claude pre-tool` (a hook without `args` is shell form, which removes quotes first), and it sets neither `async` nor `asyncRewake` to `true`, which both run in the background and cannot block, nor `if`, which narrows it. Ruling: in exec form, a hook with `args`, Claude Code starts `command` with no shell, keeps quotes and `$` literally and replaces only `${...}` placeholders, so the hook counts only when `command` has no quote and no `$` outside a `${...}` placeholder. Ruling: doctor reads only `.claude/settings.json`, the Kit's seed; local and user settings are the owner's own.

- [ ] **Step 1: write the failing tests.** Docstring `Offline: doctor's Harness wiring item on written settings files.`

```python
HOOK = {"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool'}
ALL = "Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor"
GAP = "no PreToolUse hook runs devctl hook claude pre-tool for "
EVERY_TOOL = "Bash, Edit, Write, MultiEdit, NotebookEdit, Monitor"


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
        (wired("Bash,Edit,Write,MultiEdit,NotebookEdit,Monitor"), []),
        (wired("Bash|Monitor|.*Edit|Write"), []),
        (wired("Bash"), [GAP + "Edit, Write, MultiEdit, NotebookEdit, Monitor"]),
        (wired("Bash,Edit"), [GAP + "Write, MultiEdit, NotebookEdit, Monitor"]),
        (wired("Edit"), [GAP + "Bash, Write, MultiEdit, NotebookEdit, Monitor"]),
        (wired("Bash|Edit|Write|NotebookEdit|Monitor"), [GAP + "MultiEdit"]),
        (wired("Bash|Edit|Write|MultiEdit|NotebookEdit"), [GAP + "Monitor"]),
        (wired(**{"async": True}), [GAP + EVERY_TOOL]),
        (wired(**{"if": "Bash(git *)"}), [GAP + EVERY_TOOL]),
        ({**SEED, "disableAllHooks": True}, ["disableAllHooks is true, so no hook runs"]),
        ({}, [GAP + EVERY_TOOL]),
    ],
)
def test_wiring_problems(settings: object, problems: list[str]) -> None:
    assert wiring_problems(settings) == problems
```

  And, through `local_items` with the `ctx` and `repo_files` fixtures: the rendered seed is ok; a missing file, an untracked one and invalid JSON are missing; a file that raises `OSError` on read is unknown. `tests/test_kit_contents.py`: `.claude/settings.json` is seeded in both stacks and its parsed content equals `SEED`. In `tests/devctl/test_devctl_doctor_local_limits.py`, beside the order test: `test_every_item_is_printed_then_the_summary` expects `doctor: 4 ok, 6 missing, 1 unknown` and `len(lines) == 12`, and `test_doctor_reads_the_project_and_reports_every_local_item_ok` tracks the rendered `.claude/settings.json` seed through `repo_files` and expects `doctor: 10 ok, 1 missing, 0 unknown`.
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
- Modify: `ARCHITECTURE.md` (`devctl hook`, the merge guard, `codeowners.py`, the wiring seed), `tools/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tests/AGENTS.md` (`fixtures/hooks/claude/`), the root `AGENTS.md` (plan 5's line), Spec 1's sections 4 and 6 and status line, the plan index's plan 5 row and Layout (`doctor_wiring.py`), this plan's Verification record
- Create: `docs/trials/<run date>-harness-guardrails.md`

- [ ] **Step 1 (agent): documents.** Update the files above to describe what Tasks 2 to 7 built. Spec 1 section 4's "Unreadable settings" bullet gains that a missing CODEOWNERS is an empty Protected set and leaves G7 and G8 on, and the merge guard's step 4 that the guard reads the first of `.github/CODEOWNERS`, `CODEOWNERS` and `docs/CODEOWNERS` on the base, as GitHub does. Spec 1 section 6's `devctl hook` paragraph says that the hook reads `.rapid-ship/project.toml` and the first of those three CODEOWNERS names from the repository that holds the call, and reads the default and current branch from local git only for G3's `git push` and ref forms and for a `gh pr merge` that names no pull request. The plan index's Layout gains `doctor_wiring.py`, doctor's Harness wiring item (Task 6). Commit `docs: describe devctl hook, the merge guard and the Claude Code wiring`.
- [ ] **Step 2 (agent): prepare the trial record.** It lists the steps below with an empty results table: the command or edit, the expected decision and message, and the observed ones.
- [x] **Step 3 (Owner): the scratch repository.** Ruling: every case whose failure would write to GitHub runs in a scratch repository, `proxy-hatch/rs-guardrail-trial`, never in `proxy-hatch/rapid-ship`. Create it private with a first commit, `gh repo create proxy-hatch/rs-guardrail-trial --private --add-readme --clone`, because `init` in a repository without commits commits on the current branch and makes no `rapid-ship/init` branch. Run `uvx --from <the plan5-guardrails worktree> rapid-ship init --stack agnostic --owner proxy-hatch --repository proxy-hatch/rs-guardrail-trial`, push the init branch and merge its PR. Record the commands and the merge.
- [x] **Step 4 (Owner): each rule, Agent identity off.** In a lead Claude Code Session started in the scratch clone, have the agent run each line and record the decision and message: `git commit --allow-empty -n -m g1` (G1), `git push --force origin HEAD:g2` (G2), `git push origin HEAD:main` (G3), `gh api -X PUT repos/{owner}/{repo}/pulls/1/merge` (G3), `gh pr merge 1 --admin --squash` (G3), an edit of `.rapid-ship/kit.lock` (G4), an edit of `AGENTS.md` (G5: the owner sees the prompt and declines), `git push --force origin HEAD:g2` run through the Monitor tool (G2, because the hook spike found that Monitor runs shell commands) and `git status` (no decision). Repeat the list in a subagent that the lead starts.
- [x] **Step 5 (Owner): the merge guard, Agent identity off.** Open PR A, changing `notes.txt`, and PR B, changing `AGENTS.md`, each with an Evidence section; open PR C with an empty body, so its `evidence` step fails. Have the agent run `gh pr merge <n> --squash`, and record each message: A while its check is pending (check message); C after its check fails (check message); B after its check passes (Protected message); A after its check passes, without `--match-head-commit` (head message); then the retry it names, which merges A. Record A's merge commit.
- [x] **Step 6 (Owner): Agent identity on.** Run `uv run rapid-ship app --repository proxy-hatch/rs-guardrail-trial` from this repository, install the existing Apps there through the URLs it prints, record their IDs and slugs in the scratch repository's `project.toml`, and merge that change in GitHub's web interface. Then record: `git push origin HEAD` (G7); `gh pr create --fill` (G8); `gh pr merge <n> --squash` (G8), and these three again in a subagent that the lead starts; `./devctl as worker gh pr merge <n> --squash` while its check is pending (check message); once it passes, `./devctl as worker gh pr merge <n> --squash --match-head-commit <head>` before the Reviewer App has approved the PR (review message); `./devctl as reviewer gh pr review <n> --approve`; `./devctl as worker gh pr merge <n> --squash` (head message); the retry it names, the same merge as before the approval, which merges; `./devctl as worker gh pr merge <C> --squash` (check message) and the same for `<B>` (Protected message); and `./devctl as worker gh api -X PUT repos/{owner}/{repo}/pulls/<n>/merge` (G3).
- [x] **Step 7 (Owner): the hook's cost.** In the scratch clone, run `/usr/bin/time -p ./devctl hook claude pre-tool < bash.json` 20 times, with Task 4's fixture whose `cwd` is set to the clone, and record the median and the maximum.
- [x] **Step 8 (implementer): write the record** from the owner's output: Claude Code's version, each message verbatim, PR numbers and merge commits, the timing, and every difference from the expected decision. A difference is fixed in PR 5.2 and its case rerun before the merge.
- [x] **Step 9: verify.** Run the five checks with `--base plan5-hook-spike`, and record the results in the Verification record. The PR body's Evidence section lists them and the trial record, with `Not covered:` naming what the trial did not run. Commit `docs: record the guardrails live trial and PR 5.2's verification`.

## PR 5.3: standards (`plan5-standards`, on `plan5-guardrails`)

### Task 9: README.md and ARCHITECTURE.md seeds, map rule 8 and `doctor --settings`

**Files:**
- Create: `rapid_ship/templates/common/README.md`, `rapid_ship/templates/common/ARCHITECTURE.md`, `devctl/check/map_skills.py`, `tests/devctl/test_devctl_map_root_documents.py`, `tests/devctl/test_devctl_doctor_settings.py`
- Modify: `rapid_ship/templates/kit.toml` (`seeded` gains `"ARCHITECTURE.md"` and `"README.md"`), `rapid_ship/templates/common/AGENTS.md`, `rapid_ship/templates/python/AGENTS.md`, `devctl/check/map.py`, `devctl/check/markdown.py`, `devctl/doctor.py`, `devctl/doctor_local.py`, `tests/devctl/check_workspace.py`, `tests/devctl/test_devctl_map_skills.py`, `tests/devctl/test_devctl_map_coverage.py`, `tests/devctl/test_devctl_map_documents.py`, `tests/devctl/test_devctl_map_links.py`, `tests/devctl/test_devctl_doctor_local_limits.py`, `tests/devctl/test_devctl_doctor_local.py`, `tests/test_kit_contents.py`; this repository's root `AGENTS.md` (in place)

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
- Ruling: `doctor --settings` builds no `DoctorContext`: it prints the git item, `settings_item(root)` and Task 6's `wiring_item(root, tracked)`, then exits by `doctor_exit_code`, and makes no GitHub request, because Spec 1 section 4 relies on the doctor run at each Session's start to report missing wiring, and section 6 has most Sessions run `--settings`. The full doctor keeps `load_project` first, so it exits 2 on an invalid `project.toml` before any item. `settings_item` loads `.rapid-ship/project.toml` and `.rapid-ship/exceptions.toml` with devctl's loaders and reads CODEOWNERS with `protected_patterns`, which takes the first of its three names. An invalid or unreadable file is unknown (exit 2), with the `SettingsError` message that names the file and the key; no CODEOWNERS file, a `None` from `protected_patterns`, is missing (exit 1). The full doctor adds `settings_item` right after git, where Spec 1 section 6 reads the settings. `--settings` and `--skills` are an argparse mutually exclusive group, because `--settings` stays a quick local read.
- Seeds, with `{{project_name}}` as their only variable, because an empty `{{owner}}` or `{{repository}}` is a `KitError` outside TOML and CODEOWNERS. README.md: what the project does and for whom, how to run it, how to check a change (`./devctl check`), and a link to `AGENTS.md`. ARCHITECTURE.md: purpose and context, a table of the main parts (Part, Where, What it does), how data moves between them, the ADRs in `docs/adr/` as a code span (a new project has no `docs/adr/`, so a link would fail rule 8), and how to work on the code, linking `AGENTS.md`.
- Both root guide templates: a first Commands bullet, ``Run `./devctl doctor --settings` first in each Session, unless the Session runs the full `./devctl doctor`; it checks the settings files and asks GitHub nothing.``, and two first rows in Find the change, ``| What the project does, and how to run and check it | [README](README.md) |`` and ``| The system's parts and how data moves between them | [Architecture](ARCHITECTURE.md) |``. This repository's root guide gains the README row and the same command line.

- [ ] **Step 1: move rule 7.** Move `_front_matter` and `_text` to `check/markdown.py` as `front_matter_of` and `text_value`, then the skill functions and `SKILLS` to `check/map_skills.py`; update `MapStep.run` and the test imports, among them `test_devctl_map_links.py:11`, which imports `skill_alias_errors` from `devctl.check.map`. Format, check and sync, then run `uv run pytest tests/devctl/test_devctl_map_*.py -q`; expected PASS. Commit `refactor: move map rule 7 into check/map_skills.py`.
- [ ] **Step 2: write the failing tests.** In `test_devctl_map_root_documents.py`, docstring `Offline: map rule 8 in fixture repositories.`, using `Workspace`:
  - `test_rule_8_passes_with_both_documents_linked_from_the_root_guide`: `AGENTS.md` links both, each links `AGENTS.md`; `MapStep().run(ctx).status == "passed"`.
  - `test_rule_8_reports_a_missing_document_and_a_broken_link`: `AGENTS.md` links both documents, `ARCHITECTURE.md` links `gone.md`, and `README.md` is missing. `root_document_errors` holds `README.md: missing at the repository root; restore it from git or write a new one (rapid-ship sync seeds it only while the Kit lock does not list it)`, and `root_link_errors` holds only rule 1's message for the `gone.md` link.
  - `test_a_broken_link_in_architecture_md_warns_in_kit_0_2_0_and_fails_after`: through `MapStep`, that message is a note `warning: <message>; this fails from the next Kit version` under `0.2.0` and an error under `0.3.0`.
  - `test_a_root_guide_without_the_links_warns_in_kit_0_2_0_and_fails_after`: with `devctl.__version__` patched to `0.2.0`, the step passes with the note `warning: AGENTS.md: does not link README.md; add it to the Find the change table; this fails from the next Kit version`; patched to `0.3.0`, it fails with `AGENTS.md: does not link README.md; add it to the Find the change table`.

  In `test_devctl_doctor_settings.py`, docstring `Offline: doctor --settings on fixture repositories; gh_get is replaced by a reader that fails the test.`:
  - `test_settings_reads_only_the_settings_and_asks_github_nothing`: in a workspace that commits the rendered seeds of `.rapid-ship/`, `.github/CODEOWNERS` and `.claude/settings.json`, `main(["doctor", "--settings"])` exits 0, prints `ok  guardrails  settings: ` and `ok  guardrails  Harness wiring: `, and no other item than git's.
  - `test_an_invalid_key_exits_2_and_names_the_file_and_the_key`: `stack = "python"\n[escalation]\nrevision_rounds = 0\n` exits 2 and prints on stdout the line `unknown  guardrails  settings: .rapid-ship/project.toml [escalation] revision_rounds: expected an integer of at least 1`.
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

  Existing doctor tests that the settings item and `--settings` break: in `test_devctl_doctor_local_limits.py`, `test_every_item_is_printed_then_the_summary` expects `doctor: 4 ok, 6 missing, 2 unknown` and `len(lines) == 13`, because its repository has no `project.toml`, a `SettingsError` that `settings_item` reports as unknown, and `test_doctor_reads_the_project_and_reports_every_local_item_ok` also writes the rendered `.rapid-ship/exceptions.toml` and `.github/CODEOWNERS` seeds and expects `doctor: 11 ok, 1 missing, 0 unknown`. The four `doctor_command(argparse.Namespace(skills=False))` calls, `test_devctl_doctor_local.py:105` and `:153` and `test_devctl_doctor_local_limits.py:402` and `:430`, pass `argparse.Namespace(skills=False, settings=False)`.

  In `tests/test_kit_contents.py`: `SEEDED` gains both files; `ROOT_GUIDE_LINKS` starts `["README.md", "ARCHITECTURE.md", ...]`; `POINTERS` gains ``"`./devctl doctor --settings`"``; the README seed contains `./devctl check` and `](AGENTS.md)`, and the ARCHITECTURE seed contains `| Part | Where | What it does |` and `` `docs/adr/` ``.
- [ ] **Step 3: run** the three files; expected FAIL with `ImportError: cannot import name 'root_document_errors'`.
- [ ] **Step 4: implement.** `root_document_errors` checks only that both files exist, and fails at once. `root_link_errors` returns `link_errors` over those of `README.md` and `ARCHITECTURE.md` that exist (`(root / name).is_file()`), because `root_document_errors` already reports a missing one, and the root guide's missing links to either document, found with `_guide_targets(root, "AGENTS.md")`; `MapStep.run` passes them through `graced`. `git add` the seeds, then sync: this repository's `README.md` and `ARCHITECTURE.md` stay as they are and are recorded as seeded.
- [ ] **Step 5: run** them, `tests/devctl/test_devctl_map_*.py` and `tests/devctl/test_devctl_doctor*.py`; expected PASS. Status, fast check.
- [ ] **Step 6: commit** `feat: seed README.md and ARCHITECTURE.md, check them with map rule 8, and add doctor --settings`.

### Task 10: The Pattern `task` key and `## Lessons` section

**Files:**
- Modify: `rapid_ship/templates/common/docs/patterns/README.md`, `devctl/check/map.py` (`_pattern_problems`, `_document_errors`), `tests/devctl/test_devctl_map_documents.py`, `tests/test_kit_contents.py:347-365`

**Interfaces:**
- Consumes: `graced` (Task 9); `markdown.section(text, title, level)`.
- Produces: `pattern_lesson_errors(context: CheckContext, files: Sequence[str]) -> list[str]` in `map.py`, whose messages `MapStep.run` passes through `graced`. `_document_errors` passes the file's text to its callback as a fourth argument. Ruling: `pattern_lesson_errors` skips a file for which `front_matter_of` (Task 9) gives a message, because `pattern_errors` already reports that file: the file cannot be read, or its front matter is missing, not closed, not YAML or not a mapping.

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

  and `test_a_complete_pattern_passes`, with `PATTERN` giving `[]`, and `test_a_front_matter_problem_is_left_to_pattern_errors`, parametrized over `PATTERN` less its closing `---` line, `PATTERN` less its front matter, and `PATTERN` whose front matter is the list `- task`; each gives `[]`. In `test_kit_contents.py`, the Pattern README names `task`, `reference`, `enforced_by` and `## Lessons`.
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


# src/<package>/profiling.py: uvx py-spy record -o profile.svg -- .venv/bin/python -m <package>.profiling
def main(argv: Sequence[str] | None = None) -> int: ...  # --rounds N, default 5000000
```

| Pattern file | `task` | `reference` | `enforced_by` |
| --- | --- | --- | --- |
| `python-error-handling.md` | `Report an error` | `src/{{package}}/errors.py` | `ruff:BLE001`, `ruff:S110`, `test:tests/test_errors.py::test_an_error_keeps_its_cause_and_names_the_next_step` |
| `python-configuration.md` | `Read configuration` | `src/{{package}}/settings.py` | `banned:os.environ`, `banned:os.getenv`, `test:tests/test_settings.py::test_an_out_of_range_value_is_rejected` |
| `python-input-validation.md` | `Validate input` | `src/{{package}}/inputs.py` | `type:tests/test_inputs.py`, `test:tests/test_inputs.py::test_an_unknown_value_is_rejected` |
| `python-performance.md` | `Find slow code` | `src/{{package}}/profiling.py` | `test:tests/test_profiling.py::test_the_profiling_entry_point_runs_on_a_small_input` |

Each file states the rule of Spec 1 section 4's starter table, when it applies and the bypass it bans, then `## Lessons` on what its reference does right. The performance Pattern documents `uvx py-spy record -o profile.svg -- .venv/bin/python -m <package>.profiling`, run after `uv sync`, and how to read the flame graph; no check runs a profiler.

- Ruling: `pyproject.toml`'s `banned-api` gains `"os.environ".msg` and `"os.getenv".msg`, both pointing to `docs/patterns/python-configuration.md`, and `per-file-ignores` gains `"src/{{package}}/settings.py" = ["TID251"]  # the one module that reads the environment`. A per-file entry in the Protected `pyproject.toml` is the owner's setting, while an inline suppression would need an `exceptions.toml` entry, and the seed must hold none.
- Ruling: `tests/test_inputs.py` is the `type:` fixture: `assert_type(parse_level("info"), Level)` sits in its test, which mypy checks under `files = ["src", "tests"]`; no `type: ignore` is needed.
- Ruling: the modules sit directly in `src/<package>/`, so map rule 2 asks for no new guide, and the profiling entry point starts no process, so no S603 exception is needed.
- Ruling: the Python CODEOWNERS seed gains, right after the `/.rapid-ship/` line, one commented line for each starter Pattern file, such as `# /docs/patterns/python-error-handling.md @{{owner}}`, so the set still ends with the settings files of the check tools, as the seed's comment says. In an existing project those files do not exist, and GitHub ignores a line for a missing file.
- Ruling: `test_the_python_codeowners_only_adds_the_python_settings` keeps its name, and only its body changes, because the `diff` step reports a renamed test as a removed behavioural test, which PR 5.3's body would then have to declare under `Removed tests:`, making PR 5.3 an escalation kind.

- [ ] **Step 1: write the failing tests.** `tests/test_kit_starter_patterns.py`, docstring `Offline: a new Python project from init, checked with map rule 5; no network.`:
  - `test_the_python_starter_patterns_pass_map_rule_5`: `init_repository` with `stack="python"` in `git_repo`, then commit. The tracked files under `docs/patterns/` that start `python-` are exactly the four file names above, and `pattern_errors` and `pattern_lesson_errors` on its `CheckContext` both return `[]`.
  - `test_the_starter_patterns_are_new_project_seeds_only`: on a repository that already has a `pyproject.toml`, `init` writes none of the files above.

  The skeleton's own tests, which run inside the new project: `test_an_error_keeps_its_cause_and_names_the_next_step` (`load_settings({"WORKERS": "four"})` raises a `UsageError` whose text is `WORKERS is four; set it to a whole number from 1 to 32` and whose `__cause__` is the `ValueError` from `int`), `test_an_out_of_range_value_is_rejected` (`load_settings({"WORKERS": "33"})` raises `UsageError`), `test_an_unknown_value_is_rejected` (`parse_level("verbose")` raises `UsageError` whose message names `debug, info, warning, error`), and `test_the_profiling_entry_point_runs_on_a_small_input` (`main(["--rounds", "3"]) == 0`, judging no time).

  In `tests/test_kit_contents.py`, `test_python_seed_has_the_spec_guardrails` (:255) expects `banned-api` to hold exactly `os.environ` and `os.getenv`, each with a `msg` that names `docs/patterns/python-configuration.md`, and the two CODEOWNERS tests expect the Pattern lines:

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


def test_the_python_codeowners_only_adds_the_python_settings() -> None:
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
- Modify: `devctl/check/map_skills.py`, `devctl/check/map.py` (`MapStep.run`), `tests/devctl/test_devctl_map_skills.py`

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

  In `test_devctl_diff_rules.py`, `test_the_ledger_rule_lists_changed_and_removed_entries_only`: base entries `docs/corrections/c1.md` and `c2.md`; the change edits `c1.md`, deletes `c2.md` and adds `c3.md`; notes hold `protected: docs/corrections/c1.md` and `protected: docs/corrections/c2.md` and no `c3.md`. The exact `details` at `test_devctl_diff_rules.py:99` and `:141-143` (`test_agnostic_stack_lists_only_protected_paths`, which Task 2's move of the matcher table shifts up), and `test_devctl_diff_removed_tests.py:118-122`, `:171-175`, `:183`, `:194` and `:205` each gain the cap note last, `diff cap: <n> of 1,500 counted lines` with that fixture's count. In `test_devctl_evidence_step.py`, `over_cap_reason` returns the reason inside Evidence and `None` outside it, inside a fence, or without a reason. The seed tests expect both kinds.
- [ ] **Step 2: run** them; expected FAIL with `ImportError: cannot import name 'over_cap_reason'`.
- [ ] **Step 3: implement**; edit this repository's `project.toml`; sync.
- [ ] **Step 4: run** `tests/devctl/test_devctl_diff_*.py`, the evidence and settings tests and `tests/test_kit_contents.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: add the 1,500-line diff cap and the Corrections ledger rule`.

### Task 14: One CI concurrency group for each push run, documents, and PR 5.3's verification

**Files:**
- Modify: `rapid_ship/templates/common/.github/workflows/devctl-check.yml:18-20`, `tests/devctl/test_devctl_ci_templates.py:39-46`; this repository's workflow through `sync`
- Modify: `ARCHITECTURE.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, the root `AGENTS.md`, Spec 1's sections 4 and 6 and status line, the plan index's Conventions, Layout, CODEOWNERS section and plan 5 row, this plan's Verification record

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
- [ ] **Step 5: documents.** Describe Tasks 9 to 14 in the files above, including the warning period of `GRACE_VERSION`. Spec 1 section 4's ARCHITECTURE.md bullet names the ADRs in `docs/adr/` as a code span, as Task 9's seed does, in place of "links to the ADRs". Spec 1 section 6's doctor row and the index's Conventions write `doctor [--skills | --settings]`. The index's Layout gains `check/map_skills.py`, and its CODEOWNERS section the Python seed's commented starter Pattern lines right after `/.rapid-ship/` (Task 11). Commit `docs: describe plan 5's standards`.
- [ ] **Step 6: verify.** Run the five checks with `--base plan5-guardrails`, and record them in the Verification record. When `diff` counts more than 1,500 lines, the PR body declares `Over the diff cap: <reason>` only after the owner accepts the overage; otherwise split the PR at a task boundary. Commit `docs: record PR 5.3's verification`.

## PR 5.4: settings and migrations (`plan5-settings-migrations`, on `plan5-standards`)

### Task 15: Documented seeds and the loaders' checks

**Files:**
- Modify: `devctl/settings.py`; `rapid_ship/templates/{python,agnostic}/.rapid-ship/project.toml`, `rapid_ship/templates/common/.rapid-ship/exceptions.toml`, `rapid_ship/templates/python/pyproject.toml`, `rapid_ship/templates/common/.github/workflows/devctl-check.yml`; this repository's `.rapid-ship/project.toml` and `.rapid-ship/exceptions.toml` (in place)
- Test: `tests/devctl/test_devctl_settings.py`; create `tests/test_kit_seed_keys.py`

**Interfaces:**
- Produces: in `settings.py`, `PROJECT_KEYS: dict[str, frozenset[str]]`, each table's accepted keys, with `""` for the top-level keys, `EXCEPTION_KEYS: tuple[str, ...]` (today's `_EXCEPTION_KEYS`) and `OPTIONAL_SKILLS: frozenset[str]`.

Loader changes:
- An unknown key's error names what the table accepts: `<where>: unknown key '<key>'; it accepts <keys, sorted, comma-separated>`. Ruling: this text.
- `[map] source_roots`, `[map] unguided` and `[tests] unit` must name paths inside the repository, checked as `exclude` is: `<where> <key>: expected paths inside the repository`.
- `[kit] optional` must name skills the Kit offers. `OPTIONAL_SKILLS` holds the Kit's optional names, none in 0.2.0, and a parity test in `test_devctl_settings.py` holds it equal to `kit.toml`'s `optional_skills` (`load_manifest()`), as the index does for `keychain_service`. Another name fails with `<where> optional: expected names of the Kit's optional skills: <names, sorted, comma-separated, or none in this Kit version>`.
- Spec 1 states no other range or allowed set than those the loader checks today.

Seed comments: a seeded settings file comments a key only where its name and value do not show its contract: the values or units it accepts, a default that is not obvious, or a constraint (Spec 1 section 4). That covers both `project.toml` seeds, the `exceptions.toml` seed's commented example, the Python `pyproject.toml` and the CI workflow outside its `run:` blocks. CODEOWNERS is unchanged. `project.toml` follows Spec 1 section 4's example, with `stack` in place of `[[stack]]` (plan 6). `[kit] optional`'s comment says what the key accepts, `opt-in Kit skills; none in this Kit version`: it keeps `skills` until Spec 3's plan widens the key, and drops the `rs-contribute` example, which the loader rejects in 0.2.0, until plan 7 ships that skill. Ruling: the `repository` comment sits on the line above `repository`, because `test_without_an_owner_the_code_owner_seed_is_empty_not_a_placeholder` in `test_kit_contents.py` requires the line above `code_owner`'s comment to be exactly `repository = "octo/demo-app"`.

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

  with matching rows for `[map] unguided` and `[tests] unit`. `tests/test_kit_seed_keys.py`, docstring `Offline: every seed names every key its loader accepts.`, holds `test_each_seed_names_every_key_its_loader_accepts`: each key of `PROJECT_KEYS` appears as a key line under its table in both `project.toml` seeds, and each of `EXCEPTION_KEYS` appears in the `exceptions.toml` seed's commented example as `# <key> = `.
- [ ] **Step 2: run** them; expected FAIL.
- [ ] **Step 3: implement**; add the comments; edit this repository's two seeded copies in place; sync.
- [ ] **Step 4: run** `tests/devctl/test_devctl_settings*.py`, `tests/test_kit_seed_keys.py` and `tests/test_kit_contents.py`; expected PASS. Status, fast check.
- [ ] **Step 5: commit** `feat: document every seeded key and name what each settings key accepts`.

### Task 16: `sync`'s migrations, documents, and PR 5.4's verification

**Files:**
- Create: `rapid_ship/kit/migrations.py`, `tests/test_kit_migrations.py`
- Modify: `rapid_ship/kit/sync.py` (`SyncResult`, `sync_repository`), `rapid_ship/cli.py` (`_sync`), `tests/test_kit_sync.py`; `ARCHITECTURE.md`, `rapid_ship/kit/AGENTS.md`, `rapid_ship/AGENTS.md`, the root `AGENTS.md`, `README.md`, Spec 1's section 4 example and status line, the plan index (plan 5 built), and this plan's Verification record

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
- `migration_body` lists ``- `<path>`: <explanation>`` for each, says the files are Protected and the owner merges, and ends with `## Evidence`, the line ``- `rapid-ship sync`: <n> migrations for Kit <version>`` and `Not covered: sync did not run ./devctl check; CI runs it on this pull request.`, as `pull_request_body` does, because the `evidence` step needs a command with its result.
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

  Also: the edited text loads with `devctl.settings.load_project` (devctl is importable in tests); `test_an_excluded_path_is_never_migrated`; `test_in_place_lists_each_migration_and_writes_none` (the file's bytes are unchanged and `result.migrations` lists three); `test_sync_proposes_the_migrations_on_a_second_branch_and_pr` with `PullRequests` from `test_kit_sync.py` (two calls: the sync PR, then `("rapid-ship/kit-migrate-9.9.9", "rapid-ship/kit-sync-9.9.9", "Migrate seeded files for rapid-ship Kit 9.9.9", body)`, where the body names each edit and its `## Evidence` section holds ``- `rapid-ship sync`: <n> migrations for Kit 9.9.9``, with that fixture's count, before its `Not covered:` line, and HEAD is then on `rapid-ship/kit-migrate-9.9.9`); `test_the_root_guide_migration_adds_the_missing_rows` (the root guide that `v0.1.0` seeds, from `git show v0.1.0:rapid_ship/templates/common/AGENTS.md` rendered for `demo-app` and written into the test, gets both rows right below the separator, after which `applies` is False; a guide that links both, or has no Find the change table, is left alone); `test_migrations_run_when_the_kit_is_otherwise_current` (one call, based on `main`); and `test_rapid_ship_sync_in_place_exits_1_and_lists_each_migration` through `rapid_ship.cli.main`.
- [ ] **Step 2: run** `uv run pytest tests/test_kit_migrations.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'rapid_ship.kit.migrations'`.
- [ ] **Step 3: implement.** `sync.py` stays under 500 lines because the branch work for migrations lives in a helper beside `_start_branch`; `migrations.py` imports nothing from `sync.py`.
- [ ] **Step 4: run** `tests/test_kit_migrations.py` and `tests/test_kit_sync*.py`; expected PASS. `uv run rapid-ship sync --in-place` in this repository lists no migration. Status, fast check.
- [ ] **Step 5: commit** `feat: propose migrations of seeded settings from rapid-ship sync`.
- [ ] **Step 6: documents.** Describe the migrations and plan 5 as built in the files above, add Task 15's `repository` and `source_roots` comments to Spec 1 section 4's `project.toml` example, the `repository` comment on the line above the key as in the seed, and move plan 5's row to Built; commit `docs: record plan 5 as built`.
- [ ] **Step 7: verify.** Run the five checks with `--base plan5-standards`, record them in the Verification record, and handle the diff cap as Task 14 Step 6 says. Commit `docs: record PR 5.4's verification`.

## PR 5.5: the dead-code step (`plan5-dead-code`, on `plan5-settings-migrations`)

The PR's first commit, `docs: plan the dead-code step (PR 5.5)`, adds this task and the Spec, index and root-document edits it builds on. The owner's decisions of 2026-10-25 set its scope:

- The step is named `dead-code`. It is a `devctl check` step on rung 2, Automated checks, and the agnostic stack has none.
- deptry runs every rule, DEP001 to DEP005, and its inline `# deptry: ignore` comment is a suppression.
- devctl carries no module-reachability check of its own. Spec 1 section 5 states the gap for Python, and the gardener's audit lists the modules that Python's tools do not report.
- vulture and deptry are approved as dev dependencies (Step 1).
- The owner holds `v0.2.0` until PR 5.5 merges.

### Task 17: The `dead-code` step for Python, this repository's dead code, and PR 5.5's verification

**Files:**
- Create: `devctl/check/stacks/python_dead_code.py`; `tests/devctl/test_devctl_dead_code.py`, `tests/devctl/test_devctl_exceptions_allowlists.py`
- Modify: `devctl/check/__init__.py` (`core_steps`), `devctl/check/exceptions.py` (`scan`, `ExceptionsStep.run`), `devctl/check/stacks/python.py` (`DEV_TOOLS`, `requirement_names`, `comment_rules`), `devctl/doctor_local.py` (`KIT_SOURCE_NOTE`, `_guardrail_item`, `devctl_exclusion_gaps`), `devctl/settings.py` (`Escalation`, `ExceptionEntry`, `load_project`, `load_exceptions`), `devctl/command_line.py:85-86`; `rapid_ship/templates/python/pyproject.toml`, `rapid_ship/templates/python/tests/test_settings.py`, `rapid_ship/templates/python/AGENTS.md` (the `dead-code` Rule), `rapid_ship/templates/common/.rapid-ship/exceptions.toml` (the `rule` comment); this repository's `pyproject.toml`, `uv.lock` and `.rapid-ship/exceptions.toml` (in place), and the files that Step 7 fixes or marks
- Test: `tests/devctl/test_devctl_step_order.py`, `tests/devctl/test_devctl_python_steps.py:107-122`, `tests/devctl/test_devctl_python_guardrails.py`, `tests/devctl/test_devctl_python_guardrails_limits.py:171-200`, `tests/devctl/test_devctl_doctor_local_limits.py:365`, `tests/devctl/test_devctl_settings.py` (the rows that build an `Escalation`), `tests/devctl/test_devctl_exceptions_step.py`, `tests/devctl/check_workspace.py:35`, `tests/test_kit_contents.py:265-319`, `tests/devctl/test_devctl_check_integration.py`
- Docs: `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `scripts/AGENTS.md`, the root `AGENTS.md`, `README.md`, Spec 1's status line, the plan index (plan 5 built, and its Settings sketch), this plan's Verification record

**Interfaces:**
- Consumes: `run_tool`, `command_result`, `output_tail`, `passed`, `failed`, `blocked`, `not_applicable` (`check/steps.py`); `toml_table`, `toml_strings`, `requirement_names` (`check/stacks/python.py`); `graced` (`check/map.py`). The new module imports nothing from `check/exceptions.py`. `exceptions.py` imports `toml_allowlist` and applies its own `normal_rule` to each item's rule, so no import cycle forms.
- Produces:

```python
# devctl/check/stacks/python_dead_code.py
VULTURE = ("uv", "run", "--locked", "vulture", "--min-confidence", "0")
# deptry runs every rule; the step appends the report's path.
DEPTRY = ("uv", "run", "--locked", "deptry", ".", "--no-ansi", "--json-output")
DEAD_CODE_TOOLS = ("vulture", "deptry")
VULTURE_CODES = ("V101", "V102", "V103", "V104", "V105", "V106", "V107", "V201")
ALLOWLIST_KEYS = (
    "vulture.ignore_names",
    "vulture.ignore_decorators",
    "deptry.ignore",
    "deptry.per_rule_ignores",
    "deptry.package_module_name_map",
    "deptry.optional_dependencies_dev_groups",
    "deptry.pep621_dev_dependency_groups",
)


class DeadCodeStep:
    name = "dead-code"
    tier: Tier = "full"

    def run(self, context: CheckContext) -> StepResult: ...


@dataclass(frozen=True)
class AllowlistItem:
    line: int  # 1-based, in pyproject.toml
    rule: str  # "<key under [tool]>:<item>", not normalised; exceptions.py normalises it


def toml_allowlist(text: str) -> tuple[list[AllowlistItem], list[str]]: ...  # items, errors
def dead_code_gaps(pyproject: Mapping[str, object]) -> list[str]: ...  # doctor's Python floor
def tool_line_rules(source: str, recorded: Mapping[int, Sequence[str]]) -> dict[int, list[str]]: ...


# devctl/check/stacks/python.py
DEV_TOOLS = ("ruff", "mypy", "pytest", "import-linter", "vulture", "deptry")
_DEPTRY_IGNORE = re.compile(r"#\s*deptry:\s*ignore(?:\[(?P<codes>[^\]]*)\])?", re.IGNORECASE)
DEPTRY_CODES = r"[A-Z0-9,\s]+"  # deptry's own pattern for the codes in its bracket


def requirement_names(value: object) -> set[str]: ...  # renamed from _requirement_names
def comment_rules(comment: str) -> list[str]: ...  # also "deptry" or "deptry:<codes>"
```

- `core_steps` puts `DeadCodeStep()` after `CONTRACTS` and before `TESTS`, on the Python stack only. Ruling: this order, so the static steps run before the tests; Spec 1 section 5's table lists the row there.
- `DeadCodeStep.run`:
  1. Reads `pyproject.toml` with `tomllib`. A missing file lists no dev dependency and no paths. Invalid TOML blocks with `pyproject.toml: <tomllib's message>` and runs no tool.
  2. Collects the gaps, in this order: `[dependency-groups] dev lacks <tools, in DEAD_CODE_TOOLS order>; add them to pyproject.toml and run uv lock`, when `requirement_names` of that group lacks a tool; and `[tool.vulture] paths is not set; list the directories vulture scans, such as ["src", "tests"]`, when `toml_strings` of that key is empty. With any gap it runs no tool and passes the gaps through `graced`: under `GRACE_VERSION` the step is not applicable with the notes, otherwise it is blocked with the messages. Ruling: these texts, and graced's own suffix, whose "fails" also covers a blocked step.
  3. Runs vulture from the repository root, 600 seconds: exit 0 passes, 3 fails (`command_result` with `failed_codes=frozenset({3})`), anything else blocks. Exit 1 is invalid input, and 2 is a bad argument, a bad `[tool.vulture]` value or uv's missing tool. Exit 3 can also follow a syntax error, which Ruff and mypy report in the same run.
  4. Runs `*DEPTRY, <scratch>/deptry.json`, 600 seconds, in a `tempfile.TemporaryDirectory(prefix="devctl-dead-code-")`. Exit 0 passes, whatever the report holds. Exit 1 fails with one line per violation, `<file>:<line>:<column>: <code> <message>`, or `<file>: <code> <message>` when the line is `null`. Exit 1 blocks with `deptry exited 1 and wrote no readable report` when the report is missing, is not a non-empty list, or holds an item without a string `error.code`, `error.message` and `location.file`. Any other exit or a timeout blocks through `command_result(..., frozenset())`.
  5. Merges the two results: blocked when either is blocked, else failed when either failed, else passed. The details are vulture's lines, then deptry's, each prefixed with `vulture: ` or `deptry: `. Ruling: both tools always run, so one run reports both.
- `toml_allowlist` reads `pyproject.toml`'s text:
  - A header line `[<dotted bare keys>]` or `[[...]]`, with an optional comment after it, sets the current table; names drop their leading `tool.`.
  - An allowlist array opens on a line `<bare key> = [` when `<table>.<key>` is `vulture.ignore_names`, `vulture.ignore_decorators`, `deptry.ignore`, `deptry.optional_dependencies_dev_groups` or `deptry.pep621_dev_dependency_groups`, or when the table is `deptry.per_rule_ignores`, whatever the key. It closes on the line that holds `]` outside a string. The array's key name is `<table>.<key>`.
  - The items are the TOML strings on each line of an open array, the opening and closing lines included, before the first `#` outside a string. One regular expression finds basic strings (`"…"`, with backslash escapes) and literal strings (`'…'`), and `tomllib` decodes each. A line that holds `"""` or `'''` gives no item.
  - While the table is `deptry.package_module_name_map`, each line that starts with a key, bare or quoted, then `=`, gives one item: that key, under the key name `deptry.package_module_name_map`. The value's lines give none.
  - Each item becomes `AllowlistItem(line, f"{key_name}:{item}")`.
  - A line that gives two or more items also gives the error `pyproject.toml:<line>: <key name> holds <n> items on one line; write each alone on its own line, with its own marker`. Its items stay in the result, so the line's markers still match.
  - `tomllib` then parses the whole text. Each item of those keys that the scan did not find, compared as a multiset, gives the error `pyproject.toml: <key name> lists '<item>' on no line devctl can read; write it alone on its own line under [tool.<table>]`, where `<table>` is `vulture`, `deptry`, `deptry.per_rule_ignores` or `deptry.package_module_name_map`. A parsed `package_module_name_map` item is a key of that table. Ruling: these texts.
  - Invalid TOML raises `tomllib.TOMLDecodeError`.
- `comment_rules` also reads deptry's inline comment with `_DEPTRY_IGNORE`. A bare `# deptry: ignore` gives the rule `deptry`. With codes, it gives `deptry:<codes>`, sorted as `_codes` does, such as `deptry:DEP001,DEP003` for `# deptry: ignore[DEP003, DEP001]`. Ruling: these rule names, in zizmor's `<tool>:<codes>` form. Ruling (review round 1): deptry 0.25.1's own pattern, read from its compiled module and checked in a scratch project, is `#\s*deptry:\s*ignore(?:\[([A-Z0-9,\s]+)\])?`. It matches with case and with no word boundary after `ignore`, so `# deptry: ignored` hides a finding, and it reads codes only in upper case: with any other bracket, such as `[dep003]`, it ignores every rule on the line. `_DEPTRY_IGNORE` has no word boundary and ignores case, so devctl reads every spelling that deptry accepts, and a spelling that deptry skips only needs a marker. A bracket that `DEPTRY_CODES` does not match whole gives the rule `deptry`.
- `dead_code_gaps` gives `vulture: paths is not set` when `[tool.vulture] paths` is empty, and `ruff: external lacks V` unless every code of `VULTURE_CODES` starts with an item of `[tool.ruff.lint] external`. doctor's Python floor item joins `guardrail_gaps` and `dead_code_gaps`, in that order. Ruling: these texts.
- `devctl_exclusion_gaps`, with `python`, gains two checks in `doctor_local.py`, beside the mypy one they follow:
  - `vulture: paths covers tools/devctl and no exclude pattern matches it`, when a `paths` entry, normalised as `_normalised` does, is `.`, `tools`, `tools/devctl` or under it, and no `exclude` pattern matches `/repository/tools/devctl/devctl/cli.py`. A pattern without `*`, `?` or `[` becomes `*<pattern>*`, and the match is vulture's: `scavenge` calls `fnmatch.fnmatch`, which keeps case outside Windows.
  - `deptry: no exclude or extend_exclude pattern matches tools/devctl`, unless `re.match(<pattern>, path)` holds for `tools/devctl` or `tools/devctl/devctl/cli.py` and a pattern of `exclude` (deptry's default list when the key is absent) or of `extend_exclude`. deptry joins its patterns as `^(<a>|<b>)` and tests each directory and file it reaches, relative to the root and without `./`; a match skips everything beneath it, so `tools/devctl/` and `tools/devctl/.*` count. A pattern that Python's `re` cannot compile does not count.
  - In this repository, which holds the Kit templates, `_exclusions_item` still skips the `python` branch, so `KIT_SOURCE_NOTE` becomes `ruff, mypy, pytest, vulture and deptry not checked: this repository holds the Kit templates`. `devctl_exclusion_gaps`'s docstring names the same five tools.
  - Ruling: these texts. The vulture probe's root is a stand-in, so an absolute `exclude` pattern is not compared with the real root.
- `exceptions.scan`: on the Python stack, the root `pyproject.toml` gives `_text_lines`' rules plus `normal_rule(item.rule)` for each allowlist item on its line, with the markers on that line. `ExceptionsStep.run` appends `toml_allowlist`'s errors for the same file, and blocks with `pyproject.toml: <tomllib's message>` when the file is invalid TOML. Ruling: `scan` keeps its signature, and the step reads the file twice. The agnostic stack reads no allowlist, because it has no `dead-code` step. Plan 6 runs this for each Python stack's directory.
- Ruling (review round 1): vulture 2.16 and deptry 0.25.1 search a line's whole text, strings included, and act on its first match, so `def f(tag: str = "# noqa")` and `# noqa_hidden` each hide vulture's findings on their line. `tool_line_rules`, in `python_dead_code.py`, reads each line of a Python file with the tools' own patterns. A reading that the line's comment rules do not already name adds a rule: vulture's `noqa`, or the codes it names among `VULTURE_CODES`, `F401` and `F841`; and deptry's `deptry` or `deptry:<codes>` on a line of an import statement or an `import_module` call. A string such as `'# noqa: E501'` names no code that vulture acts on, so it stays no suppression.
- Ruling (review round 2): each tool searches only the first line of what it reports. vulture 2.16 checks its noqa on the first line of the node it reports, or of its first decorator (`lines.get_first_line_number`), and numbers lines with `str.splitlines`, which also splits at a form feed or U+2028. deptry 0.25.1 checks its comment on the first line of a `from ... import` statement or `import_module` call, and at each name's own line in a plain `import`: a probe hid `from ddd4 import (  # deptry: ignore` and reported `from ddd3 import (`, whose closing line held the comment in a string, and hid `ccc2` but not `ccc1` in `import ccc1, \` followed by `    ccc2; TAG = '# deptry: ignore'`. `tool_line_rules` therefore reads vulture's pattern only on a line where a node starts, with the text that vulture numbers there, and deptry's on a `from ... import` statement's or call's first line, and on a plain `import` statement's first line and each of its name lines. A string's later lines, such as a docstring's, add no rule. In source that devctl cannot parse, every line counts for vulture, whose Python may parse it. A string that opens on a node's line with the comment and runs on leaves no room for a marker, so its text is reworded (Spec 1 section 5).
- Ruling (review round 1): Kit 0.2.0's suppressions fail on lines that an existing project already owns, so they warn for one Kit version first (Spec 1 section 3). `SuppressedLine.graced` names the rules that come from an allowlist item, a deptry comment or `tool_line_rules`. `ExceptionsStep.run` passes their missing markers and `toml_allowlist`'s errors through `graced`. A missing marker on any other suppression fails at once.
- Ruling: deptry runs every rule, so `DEPTRY` names no `--ignore`. A rule code in `[tool.deptry] ignore` would then switch that rule off for the whole project, so each code is an allowlist item with its marker, as each `per_rule_ignores` item is. deptry's inline comment acts on the import on its line, and only for DEP001, DEP003 and DEP004.
- Ruling: `Escalation.revision_rounds` and `ExceptionEntry.remove_when` are dead: no devctl code reads them. `rs-lead` reads `revision_rounds` from the file (Spec 2), and `rs-health` reads `remove_when` from the file. Delete both fields. `load_project` still checks `revision_rounds` (an integer of at least 1), and `load_exceptions` still requires `remove_when`. The index's Settings sketch changes to match in Step 9.
- Ruling: the seed's `Settings.log_level` is reported, because the seed sets it only through keyword arguments and nothing reads `.log_level`. `test_unset_values_take_their_defaults` keeps its name and reads both fields: `settings = load_settings({})`, then `assert (settings.log_level, settings.workers) == ("info", 4)`. The skeleton's settings are examples that the project's code reads later. Until then, the test's read is the use, and a use in a test counts.
- Ruling: the seed sets deptry's `known_first_party` to its package. deptry counts as local only the modules directly in the directory it scans, and the package sits under `src/`. `uv sync` installs it, so without the key its own absolute imports could read as DEP003, or as DEP001 if it is not installed. That reading of deptry's `core.py` is unverified until deptry runs. The seed's integration tests show whether the seed passes, first in Step 7 item 1 and again in Step 8.
- Ruling: never hide a finding with a form that devctl cannot see and no marker records: a leading `_` added to a name, an `__all__` entry, a `getattr` string, `del name`, a vulture whitelist module, or a bare reference to the name in a test or any other scanned file. Each is a suppression without an exception, and review rejects it (Spec 1 section 5).
- The seed's `pyproject.toml` gains these keys. Each comment states only the key's contract, as Task 15 does after the owner relaxed it on 2026-10-25:

    ```toml
    [dependency-groups]
    dev = [                # the check tools that devctl runs
        "deptry>=0.25,<1",
        "import-linter>=2.15,<3",
        "mypy>=1.20,<3",
        "pytest>=9,<10",
        "ruff>=0.17,<1",
        "vulture>=2.16,<3",
    ]

    # in [tool.ruff.lint], after select:
    external = ["V"]   # vulture's noqa codes, which Ruff keeps instead of reporting RUF102

    # at the end of the file:
    [tool.vulture]
    # devctl's dead-code step needs it, because vulture has no default. With tests listed, a use in a
    # test counts as a use.
    paths = ["src", "tests"]

    [tool.deptry]
    # Regular expressions, each matched from the start of a path relative to this directory.
    # devctl's imports are not the project's.
    extend_exclude = ["tools/devctl"]
    # deptry counts as the project's own only the modules directly in this directory, and the package
    # sits under src/.
    known_first_party = ["{{package}}"]
    ```

- [x] **Step 1 (Owner): approve the new dev dependencies.** Done on 2026-10-25: the owner approved adding `vulture>=2.16,<3` (2.16, MIT, one pure-Python wheel) and `deptry>=0.25,<1` (0.25.1, MIT, compiled `cp310-abi3` wheels) to this repository's dev group and the Python seed's, and their download when Task 17 reaches Step 7. `uv lock` adds to `uv.lock` vulture, deptry, requirements-parser, tomli (for Python below 3.15), and anything they require that the lock lacks. click, colorama and packaging are already locked. The PR body's Evidence section records the approval and its date.
- [ ] **Step 2: write the failing tests.**

  `tests/devctl/test_devctl_dead_code.py`, docstring `Offline: the dead-code step against a simulated uv that stands in for vulture and deptry.` A fake `uv`, written with `fake_tool`, prints `<tool>.out`, copies `deptry.json` to the path after `--json-output`, and exits with `<tool>.exit` (0 when absent), where `<tool>` is its third argument. Unless a test says otherwise, the workspace's `pyproject.toml` holds `[dependency-groups]\ndev = ["deptry", "vulture"]\n\n[tool.vulture]\npaths = ["src"]\n`.
  - `test_both_tools_pass_and_run_through_uv`: the result is `("passed",)`. The logged argv are `["run", "--locked", "vulture", "--min-confidence", "0"]`, then `["run", "--locked", "deptry", ".", "--no-ansi", "--json-output", <path>]`, where `<path>` ends with `deptry.json`. Both ran in the repository root.
  - `test_unused_code_fails_with_vultures_lines`: `vulture.out` is `src/app/a.py:3: unused function 'helper' (60% confidence)\n` and `vulture.exit` is 3. The result is `("failed", "vulture: src/app/a.py:3: unused function 'helper' (60% confidence)")`.
  - `test_a_dependency_finding_fails_with_deptrys_line`, parametrized: deptry exits 1. A report item with `{"code": "DEP002", "message": "'tomli-w' defined as a dependency but not used in the codebase"}`, module `tomli-w` and location `{"file": "pyproject.toml", "line": null, "column": null}` gives `("failed", "deptry: pyproject.toml: DEP002 'tomli-w' defined as a dependency but not used in the codebase")`. An item with `{"code": "DEP003", "message": "'cryptography' imported but it is a transitive dependency"}` at `{"file": "src/app/a.py", "line": 3, "column": 1}` gives `deptry: src/app/a.py:3:1: DEP003 'cryptography' imported but it is a transitive dependency`.
  - `test_deptry_exit_1_without_a_readable_report_is_blocked`, parametrized over no report, `[]`, `{"error": {}}` and `[{"error": {"code": "DEP002"}}]`: the status is `blocked` and the first detail is `deptry: deptry exited 1 and wrote no readable report`.
  - `test_any_other_exit_is_blocked`, parametrized over vulture exiting 1, vulture exiting 2 and deptry exiting 2: the status is `blocked`. The first detail starts with `<tool>: uv run --locked <tool>` and ends with `exited <code>`.
  - `test_a_blocked_tool_outranks_a_failed_one`: vulture exits 3 with one finding and deptry exits 2. The status is `blocked`, and the details hold the vulture finding first, then the deptry line.
  - `test_without_the_tools_or_paths_the_step_warns_in_kit_0_2_0_and_blocks_after`, parametrized. `TOOLS` is `[dependency-groups] dev lacks vulture, deptry; add them to pyproject.toml and run uv lock`, and `PATHS` is `[tool.vulture] paths is not set; list the directories vulture scans, such as ["src", "tests"]`. A dev group of `["ruff"]` with the paths gives `TOOLS`; both tools without `[tool.vulture]` give `PATHS`; `["ruff"]` without `[tool.vulture]`, and a missing `pyproject.toml`, give `TOOLS` then `PATHS`. With `devctl.__version__` set to `0.2.0`, the result is `("not_applicable", *(f"warning: {m}; this fails from the next Kit version" for m in messages))`. With `0.3.0` it is `("blocked", *messages)`. No `uv.log` exists afterwards.
  - `test_an_invalid_pyproject_blocks_the_dead_code_step`: `[tool.vulture\n` gives the status `blocked`, a first detail that starts with `pyproject.toml: `, and no `uv.log`.
  - `test_the_floor_names_vultures_paths_and_ruffs_external`, on `dead_code_gaps`: `{}` gives `["vulture: paths is not set", "ruff: external lacks V"]`. `paths = ["src"]` with `external = ["V"]` gives `[]`, and so does `external = ["V1", "V2"]`. `external = ["V1"]` gives `["ruff: external lacks V"]`.

  `tests/devctl/test_devctl_exceptions_allowlists.py`, docstring `Offline: allowlist items in pyproject.toml as suppressions, in fixture repositories.` Each test writes `.rapid-ship/kit.lock`, `pyproject.toml` and `exceptions.toml` as `test_devctl_exceptions_step.py`'s `setup` does:
  - `test_a_marked_item_with_its_entry_passes`: `[tool.vulture]\npaths = ["src"]\nignore_names = [\n    "do_[A-Z]*",  # rs-exception: EX-1\n]\n` with the entry `("EX-1", "pyproject.toml", "vulture.ignore_names:do_[A-Z]*")` passes.
  - `test_an_unmarked_item_fails`: the same file without the marker and the entry fails with `("pyproject.toml:4: suppression vulture.ignore_names:do_[A-Z]* needs '# rs-exception: EX-<n>' and an entry in .rapid-ship/exceptions.toml",)`.
  - `test_each_allowlist_key_names_its_rule`, parametrized, on `toml_allowlist`:
    - `[tool.vulture]\nignore_names = ["pytestmark"]\n` gives `([AllowlistItem(2, "vulture.ignore_names:pytestmark")], [])`.
    - `[tool.vulture]\nignore_decorators = [\n    "@app.route",\n]\n` gives `AllowlistItem(3, "vulture.ignore_decorators:@app.route")`.
    - `[tool.deptry]\nignore = ["DEP003"]\n` gives `AllowlistItem(2, "deptry.ignore:DEP003")`.
    - `[tool.deptry.per_rule_ignores]\nDEP002 = [\n    "psycopg2",\n]\n` gives `AllowlistItem(3, "deptry.per_rule_ignores.DEP002:psycopg2")`.
    - `[tool.deptry]\noptional_dependencies_dev_groups = [\n    "docs",\n]\n` gives `AllowlistItem(3, "deptry.optional_dependencies_dev_groups:docs")`.
    - `[tool.deptry.package_module_name_map]\nfoo-python = "foo"\n"bar-py" = [\n    "bar",\n]\n` gives `AllowlistItem(2, "deptry.package_module_name_map:foo-python")` and `AllowlistItem(3, "deptry.package_module_name_map:bar-py")`, and no item for line 4.
  - `test_two_items_on_one_line_fail`: `[tool.vulture]\npaths = ["src"]\nignore_names = ["a", "b"]  # rs-exception: EX-1  # rs-exception: EX-2\n`, with an entry for each item, fails with only `pyproject.toml:3: vulture.ignore_names holds 2 items on one line; write each alone on its own line, with its own marker`.
  - `test_an_item_devctl_cannot_place_on_a_line_fails`, parametrized:
    - `[tool.deptry]\nper_rule_ignores = { DEP002 = ["psycopg2"] }\n` gives `pyproject.toml: deptry.per_rule_ignores.DEP002 lists 'psycopg2' on no line devctl can read; write it alone on its own line under [tool.deptry.per_rule_ignores]`.
    - `[tool.deptry]\npackage_module_name_map = { foo-python = "foo" }\n` gives `pyproject.toml: deptry.package_module_name_map lists 'foo-python' on no line devctl can read; write it alone on its own line under [tool.deptry.package_module_name_map]`.
    - `tool.vulture.ignore_names = ["x"]\n` and `[tool.vulture]\nignore_names = ["""x"""]\n` each give `pyproject.toml: vulture.ignore_names lists 'x' on no line devctl can read; write it alone on its own line under [tool.vulture]`.
    - Each text is the only error in `toml_allowlist`'s result and the only detail of the failed step.
  - `test_scope_settings_are_not_suppressions`: vulture's `paths` and `exclude`, deptry's `extend_exclude`, `known_first_party` and `non_dev_dependency_groups`, and Ruff's `per-file-ignores` give `([], [])`, and the step passes with no entry.
  - `test_the_agnostic_stack_reads_no_allowlist`: on the agnostic stack, the unmarked item of `test_an_unmarked_item_fails` passes.
  - `test_an_invalid_pyproject_blocks_the_exceptions_step`: `[tool.vulture\n` blocks the step, and its first detail starts with `pyproject.toml: `.

  Changed tests:
  - `test_devctl_exceptions_step.py` gains `test_deptrys_inline_comment_is_a_suppression`, parametrized over `src/app/run.py` holding `import yaml  # deptry: ignore` (rule `deptry`), `import yaml  # deptry: ignored` (rule `deptry`), `import yaml  # deptry: ignore[DEP003, DEP001]` (rule `deptry:DEP001,DEP003`), `import yaml  # Deptry: Ignore[DEP003]` (rule `deptry:DEP003`), and `import yaml  # deptry: ignore[dep003]` and `import yaml  # deptry: ignore[DEP003, dep001]` (rule `deptry`, as review round 1 rules). Without a marker the step fails with `src/app/run.py:1: suppression <rule> needs '# rs-exception: EX-<n>' and an entry in .rapid-ship/exceptions.toml`. With `  # rs-exception: EX-1` after the comment and the entry `("EX-1", "src/app/run.py", <rule>)` it passes.
  - Review round 1 adds `test_vulture_and_deptry_read_the_whole_line` and `test_a_line_that_vulture_or_deptry_reads_as_a_suppression_needs_its_marker` to `test_devctl_exceptions_step.py`, and `test_kit_0_2_0s_suppressions_warn_in_it_and_fail_after` and `test_in_kit_0_2_0_the_step_passes_with_only_warnings` to `test_devctl_exceptions_allowlists.py`. Both files' `setup` runs the step as devctl `0.3.0` unless a test names another version. Review round 2 adds a docstring, a multi-line string and a form feed to `TOOL_LINES`, and `test_where_the_source_does_not_parse_every_line_counts_for_vulture`.
  - `test_devctl_step_order.py`: `PYTHON` gains `"dead-code"` after `"contracts"`. The fast slice stays `PYTHON[:6]`.
  - `test_devctl_python_steps.py:107-122`: the list gains `("dead-code", "full")` after `("contracts", "full")`.
  - `test_devctl_doctor_local_limits.py:365`: the Kit source's note reads `ruff, mypy, pytest, vulture and deptry not checked: this repository holds the Kit templates`.
  - `test_devctl_python_guardrails_limits.py:171-200`: `dev dependencies lack mypy` becomes `dev dependencies lack mypy, vulture, deptry`, and `dev dependencies lack ruff, mypy, pytest, import-linter` becomes `dev dependencies lack ruff, mypy, pytest, import-linter, vulture, deptry`, in both tests.
  - `test_devctl_python_guardrails.py`: `test_seeded_python_settings_meet_the_floor` also asserts `dead_code_gaps(seeded_pyproject()) == []`. A new `test_the_exclusions_keep_tools_devctl_out_of_vulture_and_deptry`, parametrized on `devctl_exclusion_gaps(data, python=True)` from the seed: vulture `paths = ["."]` gives the vulture gap, adding `exclude = ["tools/devctl"]` clears it, and `exclude = ["TOOLS/DEVCTL"]` does not; deptry without `[tool.deptry]` gives the deptry gap; `extend_exclude` of `["tools"]`, `[".*devctl"]`, `["tools/devctl/"]` or `["tools/devctl/.*"]` clears it, and `["devctl"]` does not, because deptry anchors each pattern at the start of the path.
  - `test_kit_contents.py::test_python_seed_has_the_spec_guardrails`: the dev names are `{"deptry", "import-linter", "mypy", "pytest", "ruff", "vulture"}`; `data["tool"]["ruff"]["lint"]["external"] == ["V"]`; `data["tool"]["vulture"] == {"paths": ["src", "tests"]}`; `data["tool"]["deptry"] == {"extend_exclude": ["tools/devctl"], "known_first_party": ["demo_app"]}`.
  - `test_kit_contents.py::test_the_python_root_guide_adds_its_rows_and_rules`, renamed from `..._and_lint_enforced_rules`: the Python guide holds one `dead-code` Rule, which names `# noqa: V<code>`, `# deptry: ignore[<code>]`, `ignore_names` and a vulture whitelist module. Without it, the guide still equals the agnostic one as before. The Rule is `advisory` (Spec 1 section 4), and the seeded `exceptions.toml` comment on `rule` gains the allowlist form `<tool>.<key>:<item>`.
  - The rows that build an `Escalation`, in `check_workspace.py:35` and `test_devctl_settings.py`, drop `revision_rounds`. The row whose file sets `revision_rounds = 2` still loads, and the row at `test_devctl_settings.py:359` still fails with `revision_rounds: expected an integer of at least 1`.
  - `test_devctl_check_integration.py` gains `test_a_new_project_fails_the_dead_code_step_on_unused_code_and_a_dependency`. The module docstring already says that its tests need network access and gitleaks. The test runs `init`, then writes `src/<package>/extra.py` with `def unused_helper() -> None:` and a docstring. It sets `dependencies = ["pyyaml>=6.0.3,<7"]`, then runs `uv lock --quiet` and `uv sync --quiet` and commits. `./devctl check --tier full --json` exits 1. Only `dead-code` failed; every other step passed or is not applicable as `NOT_APPLICABLE` says. Its details hold a line that starts `vulture: ` and ends `unused function 'unused_helper' (60% confidence)`, a line that starts `deptry: pyproject.toml: DEP002 'pyyaml'`, and no other `deptry: ` line. Ruling: `pyyaml`, because the vendored devctl imports `yaml`. The DEP002 line therefore also proves that `extend_exclude` keeps `tools/devctl` out, and the absence of other deptry lines that the seed passes every deptry rule. Ruling: the name `unused_helper`, because vulture treats every file under pytest's `test_…0` directory as a test file and never reports a `test_*` function there.
- [ ] **Step 3: run** `uv run pytest tests/devctl/test_devctl_dead_code.py tests/devctl/test_devctl_exceptions_allowlists.py -q`; expected FAIL with `ModuleNotFoundError: No module named 'devctl.check.stacks.python_dead_code'`.
- [ ] **Step 4: implement** the module, `core_steps`, the exceptions step, `DEV_TOOLS`, the rename, the deptry comment in `comment_rules`, doctor's two items, the two fields and the seed. Format and check the template files, then run `uv run rapid-ship sync --in-place`.
- [ ] **Step 5: run** these offline files: the two new files, `tests/devctl/test_devctl_exceptions_step.py`, `test_devctl_step_order.py`, `test_devctl_python_steps.py`, `test_devctl_python_guardrails*.py`, `test_devctl_doctor_local*.py`, `test_devctl_settings*.py`, `tests/test_kit_contents.py` and `tests/test_kit_seed_keys.py`; expected PASS. `uv run rapid-ship status --strict` exits 0, and `./devctl check --tier fast` exits 0.
- [ ] **Step 6: commit** `feat: add the dead-code check step for Python`.
- [ ] **Step 7: make this repository pass the step.**
  1. Run `./devctl check --tier full`. Expected: `not applicable dead-code` with the two warnings, because this repository's dev group lacks both tools and it sets no `[tool.vulture] paths`; every other step as before. Its `tests` step runs the whole suite, so this is the first run of the seed's integration tests in `test_devctl_check_integration.py`, Step 2's new test among them. When one of them fails on the seed, fix the seed, amend Step 6's commit, and run item 1 again before item 2.
  2. Edit `pyproject.toml` (Protected; G5 asks). The dev group gains `"vulture>=2.16,<3"` and `"deptry>=0.25,<1"`. `[project] dependencies` gains `"cryptography>=50,<51"`: `rapid_ship/app_flow.py:32-34` imports it, and only the `pyjwt[crypto]` extra declares it now, which deptry reports as DEP003. Its bounds run from the major version that `uv.lock` holds, 50.0.2, to the next, as the other dependencies' bounds do. `[tool.ruff.lint]` gains `external = ["V"]`. Add:

     ```toml
     [tool.vulture]
     # this repository: the vendored devctl is read here, not its template copy, the seeds or
     # the virtual environment in tools/devctl/.venv, which vulture would otherwise walk
     paths = ["rapid_ship", "scripts", "tests", "tools/devctl/devctl", "tools/devctl/devctl_project"]
     exclude = ["rapid_ship/templates/"]

     [tool.deptry]
     # this repository: the templates and the vendored devctl, whose imports are devctl's own
     extend_exclude = ["rapid_ship/templates", "tools/devctl"]
     ```

     vulture does not skip `.venv` and reads every `.py` file under a directory it is given. The paths therefore name devctl's two packages, not `tools/devctl`.
  3. Run `uv lock`, then `uv sync --locked`. Record the packages that `uv.lock` gained in the task report. `cryptography` is already locked through `pyjwt[crypto]`, so its declaration adds no package.
  4. Run the step's two commands, `uv run --locked vulture --min-confidence 0` and `uv run --locked deptry .`. Handle each finding by these rules, and record each finding with what was done in the task report:
     - Delete code that nothing reaches.
     - Mark a false positive: code that a framework, the standard library, pytest or reflection reaches by name. A single definition gets `# noqa: V<code>  # rs-exception: EX-<n>` on the line vulture reports, which is the first decorator's line for a decorated definition. Codes: V101 attribute, V102 class, V103 function, V104 import, V105 method, V106 property, V107 variable or argument, V201 unreachable code. A name that the same caller reaches in several files gets one `ignore_names` item, alone on its line with its marker. Each marked item or comment gets an entry in `.rapid-ship/exceptions.toml`, numbered from EX-13. A finding in the vendored devctl is marked in its template, and its entry's path is the template's, as EX-1 to EX-3 and EX-12 are.
     - Fix a deptry finding by declaring, moving or removing the dependency. A false positive on an import gets `# deptry: ignore[<code>]  # rs-exception: EX-<n>` on the import's line, and one on a declared dependency gets a `per_rule_ignores` item with its marker, each with its entry.
     - Expected outcome, from an approximation of vulture's rules over this repository at `5dfbab5`, which counted about 33 findings. The lines are `711aa24`'s:

       | Finding | Expected handling |
       | --- | --- |
       | `Escalation.revision_rounds`, `ExceptionEntry.remove_when` (`devctl/settings.py`) | Deleted in Step 4 |
       | `no_package_metadata` as an unread parameter (`tests/test_kit_cli.py:268,286`) | Fix: `@pytest.mark.usefixtures("no_package_metadata")` on both tests, and drop the parameter |
       | `do_GET`, `do_POST`, `do_PATCH`, `do_PUT`, `do_DELETE` in `rapid_ship/app_flow.py`, `tests/devctl/github_fakes.py` and `tests/test_kit_app.py` | `ignore_names` item `"do_[A-Z]*"`: `BaseHTTPRequestHandler` calls `do_<METHOD>` by name |
       | `log_message` in the same three files | `ignore_names` item `"log_message"`: the base class calls it |
       | `pytest_plugins` (`tests/conftest.py:14`) | `# noqa: V107`: pytest reads it by name |
       | `pytestmark` (three test modules) | `ignore_names` item `"pytestmark"`: pytest reads it by name |
       | `daemon_threads`, and `handle_error` with `client_address` (`rapid_ship/app_flow.py:132,164`) | `# noqa: V107` and `# noqa: V105, V107`: `socketserver` reads and calls them |
       | `namespace`, `option_string` (`rapid_ship/cli.py:45,47`) | `# noqa: V107` on each line: argparse passes them to `Action.__call__` |
       | `whitespace_split`, `commenters` (`devctl/command_line.py:85-86`) | `# noqa: V101` on each line, in the template: `shlex` reads them |
       | The fixtures `isolated_home`, `no_package_metadata` and `default_hooks_directory`, and `isolated_home` as an unread parameter of three fixtures (`tests/devctl/github_fixtures.py:105,198,246`) | `# noqa: V103` on each decorator line and `# noqa: V107` on each parameter's line: pytest calls a fixture by name, and a fixture cannot use `usefixtures` |
       | `size` of `Terminal.read` (`tests/test_kit_app_import.py:58`) | `# noqa: V107`: the override keeps `BytesIO.read`'s signature, which mypy checks |
       | `Timer.daemon` (`devctl/process.py:197`) | Expected to be clear through vulture's `threading` whitelist; marked like the attributes above if reported |
       | deptry: DEP003 `cryptography` (`rapid_ship/app_flow.py:32-34`) | Cleared by the declaration in item 2 |

       That is about 17 entries. A finding that the table does not name follows the same rules. deptry is expected to report nothing else: `jwt` and `tomli_w` resolve through installed metadata, `scripts/smoke_distribution.py` imports only the standard library, and `extend_exclude` keeps out the templates and the vendored devctl, whose `yaml` import would be DEP004 here.
  5. When both commands exit 0, run `./devctl check --tier full`; expected exit 0, with `passed dead-code` and `passed exceptions`.
  6. Commit `fix: remove this repository's dead code, declare cryptography and list the dead-code step's false positives`.
- [ ] **Step 8: run** `uv run pytest tests/devctl/test_devctl_check_integration.py -q -k "new_project"`, which needs network access; expected PASS. `test_new_project_passes_devctl_check` proves that the seed passes `dead-code` with every deptry rule on, `known_first_party` included, and the new test proves that the step fails on both kinds of finding.
- [ ] **Step 9: documents.**
  - `ARCHITECTURE.md`: a `dead-code` row in the step table; the agnostic sentence; how vulture and deptry run; the missing-tools and missing-paths case in the warning-period paragraph; line 3's "Of plan 5, PRs 5.1 to 5.4 are built" back to "Plan 5 is built in PRs 5.1 to 5.5", with the dead-code step in its list, and without its sentence "Its PR 5.5, the `dead-code` check step for Python, is planned."; line 20 without "Plan 5's PR 5.5"; and Designed, not built back to "is built", without the PR 5.5 sentences.
  - `tools/AGENTS.md`: the step, its floor settings and the allowlist reader live in `check/stacks/python_dead_code.py`, deptry's comment pattern in `check/stacks/python.py`, and doctor's vulture and deptry exclusions in `doctor_local.py`.
  - `tests/AGENTS.md`: a row for the two new test files.
  - `rapid_ship/templates/AGENTS.md`: the Python seed's `[tool.vulture] paths` and `[tool.deptry] extend_exclude` keep `tools/devctl` out of the step, and its `known_first_party` names the package under `src/`.
  - `scripts/AGENTS.md`: the dependencies that the smoke needs become "`tomli-w`, `cryptography` and PyJWT with its `crypto` extra".
  - The root `AGENTS.md`: "Plans 1 to 5 are built"; "Plan 5 is built in PRs 5.1 to 5.5", with the `dead-code` check step for Python in its list; and the "Not built yet" bullet for PR 5.5 removed.
  - `README.md`: "plans 1 to 5 work today"; the `dead-code` step in the sentence on what plan 5 adds; and the bullet for plan 5's last PR removed, with "The other two plans follow in order:" back.
  - Spec 1's status line: "Plan 5 is built in PRs 5.1 to 5.4, its PR 5.5 is planned," becomes "Plan 5 is built in PRs 5.1 to 5.5,", and "PR 5.5 is planned to build" becomes "PR 5.5 builds".
  - The plan index: line 5 becomes "Plan 5 is built in five PRs: 5.1 records the hook spike, 5.2 builds `devctl hook`, the merge guard and the Claude Code wiring, 5.3 builds the standards, 5.4 comments each seeded settings key's contract and builds `sync`'s migrations, and 5.5 adds the `dead-code` check step for Python." Plan 5's row State starts "Built:" again and ends "; PR 5.5, the `dead-code` step, on `plan5-dead-code`". Its outline's State changes PR 5.5's sentences to "PR 5.5 is built on `plan5-dead-code`, Task 17: the `dead-code` check step for Python, with vulture and deptry." The Settings sketch's `Escalation` drops `revision_rounds`, and its class line gains the comment `# revision_rounds is checked, not kept: rs-lead reads it from the file`.

  Commit `docs: describe the dead-code step and record plan 5 as built`.
- [ ] **Step 10: verify.** Run the five checks of Global Constraints with `--base plan5-settings-migrations` and record them in the Verification record. The PR body's Evidence section lists them and the owner's approval of Step 1, with `Not covered: knip, which plan 6 builds; a Python module that nothing imports, whose definitions vulture counts as used`. When `diff` counts more than 1,500 lines, Task 14 Step 6 applies. The estimate is about 1,000. Commit `docs: record PR 5.5's verification`.

## Verification record

Each PR's last task fills its row with the command, its exit code and the summary line it printed. A blocked, skipped or simulated result is written as such, never as passed.

| PR | `uv run pytest -q` | `./devctl check --tier fast` | `uv run rapid-ship status --strict` | `./devctl check --tier full --base <base> --pr-body <body>` | `npm --prefix website run build` |
| --- | --- | --- | --- | --- | --- |
| 5.1 | exit 0 at 738c845: `1320 passed in 217.00s (0:03:36)` | exit 0 at 738c845: format, lint, map, exceptions, file-size, kit and vendored passed | exit 0 at 738c845: `36 managed files unchanged.` | exit 0 at 738c845, with `--base main` and the draft body `pr-5.1-body.md`: every step passed; the diff step listed the Protected paths `AGENTS.md`, `docs/superpowers/AGENTS.md` and `docs/trials/AGENTS.md` | exit 0 at 738c845: `[SUCCESS] Generated static files in "build".`, with no broken-link or anchor warning |
| 5.2 | exit 0: `1735 passed in 236.36s (0:03:56)` | exit 0: format, lint, map, exceptions, file-size, kit and vendored passed | exit 0: `43 managed files unchanged.` | exit 0, with `--base origin/plan5-hook-spike` (`d18217b`) and the draft body `plan5-2.md`: every step passed, `tests` and `evidence` included; the diff step listed 26 Protected paths, among them the vendored devctl, the AGENTS.md files, `.claude/settings.json`, `.github/CODEOWNERS`, `.rapid-ship/` and `pyproject.toml` | exit 0: `[SUCCESS] Generated static files in "build".`, with no broken-link or anchor warning |
| 5.3 | at 5073ca8: `1806 passed in 272.02s (0:04:32)`, no failure; the exit code was not captured, and the full check's `tests` step passed | exit 0 at 5073ca8: format, lint, map, exceptions, file-size, kit and vendored passed | exit 0 at 5073ca8: `44 managed files unchanged.` | exit 0 at 5073ca8, with `--base origin/plan5-guardrails` (`ef017f6`) and the body `plan5-3.md`: every step passed, `tests`, `diff` and `evidence` included; the diff step listed 18 Protected paths and the note `diff cap: 1813 counted lines, over 1,500, declared: ...` | exit 0 at 5073ca8: `[SUCCESS] Generated static files in "build".` |
| 5.4 | exit 0 at 38d55b8: `1852 passed in 306.54s (0:05:06)` | exit 0 at 38d55b8: format, lint, map, exceptions, file-size, kit and vendored passed | exit 0 at 38d55b8: `44 managed files unchanged.` | exit 0 at 38d55b8, with `--base origin/plan5-standards` (`5dfbab5`) and the final body `pr-5.4-body.md`: every step passed, `tests`, `diff` and `evidence` included; the diff step listed 11 Protected paths, among them `.github/CODEOWNERS`, the CI workflow, `.rapid-ship/`, the vendored `settings.py` and five AGENTS.md files, and the note `diff cap: 1492 of 1,500 counted lines` | exit 0 at 38d55b8: `[SUCCESS] Generated static files in "build".`, with no broken-link or anchor warning |
| 5.5 | exit 0 at bbc212e: `1900 passed in 224.05s (0:03:44)` | exit 0 at bbc212e: format, lint, map, exceptions, file-size, kit and vendored passed | exit 0 at bbc212e: `45 managed files unchanged.` | exit 0 at bbc212e, with `--base plan5-settings-migrations` (`711aa24`) and the draft body `pr-5.5-body.md`: every step passed, `dead-code`, `tests`, `diff` and `evidence` included; the diff step listed 15 Protected paths, among them `pyproject.toml`, `.rapid-ship/exceptions.toml`, the vendored devctl and four AGENTS.md files, and the note `diff cap: 1142 of 1,500 counted lines` | exit 0 at bbc212e: `[SUCCESS] Generated static files in "build".`, with no broken-link or anchor warning |

Row 5.2's checks first ran on 2026-10-23 on `03de0bf` with the trial record's changes, against a draft body written before the trial. They ran again the same day on `5129a95` with the review fixes to the trial record, before the row was filled in, against a draft body whose Evidence section lists the five checks and the trial record. The row gives the second run's results.

PR 5.3's `diff` step, run against `plan5-guardrails` (`ef017f6`), counts more lines than the cap: 1,618 at `981114f`, where the whole-branch review ran, and 1,780 at `f493308`, after the review's fixes. Of the 1,780, devctl's tests hold 748, the devctl template 646, the Python skeleton template 222, the other tests 144 and the remaining files 20. Task 14 Step 6 applies: the PR body declares `Over the diff cap: <reason>` only after the owner accepts the overage; otherwise the PR is split at a task boundary. The owner accepted the overage on 2026-10-23, so PR 5.3's body declares it; at 646b7ed, after the last review fix, the step counts 1,813.

PR 5.4's `diff` step, run against `origin/plan5-standards` (`5dfbab5`) at 38d55b8, after the whole-branch review's fixes, counts 1,492 lines, under the cap, so its body declares no overage. The full check read the final `pr-5.4-body.md`, whose Evidence names 38d55b8 and these results. `uv run rapid-ship sync --in-place`, run at 38d55b8, printed `Kit is current; nothing to sync.`, exited 0 and listed no migration. The row's first run, at a795579 before the review fixes, counted 1,214 lines and read an earlier draft of the body.

PR 5.5's `diff` step, run against `plan5-settings-migrations` (`711aa24`) at bbc212e, counts 1,142 lines, under the cap, so its body declares no overage. At bbc212e, `uv run rapid-ship sync --in-place` printed `Kit is current; nothing to sync.` and exited 0, and the step's two commands, `uv run --locked vulture --min-confidence 0` and `uv run --locked deptry .`, each exited 0. Task 17 Step 7's first full check, at c438514 and without `--base`, compared the branch with `main`: its `dead-code` step was not applicable with the two warnings, its `tests` step passed, and only the diff cap failed, at 4,260 counted lines for PRs 5.2 to 5.5 together.
