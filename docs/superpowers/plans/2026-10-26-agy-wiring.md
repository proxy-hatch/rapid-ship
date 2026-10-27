# agy Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Kit's Harness guardrails in agy, as in Claude Code: a seeded `.agents/hooks.json` that wires agy's `PreToolUse` event to `devctl hook agy pre-tool`, a protocol that answers in agy's format, so that a failure of devctl's own never blocks agy without saying why, doctor's item for that wiring, and the Protected set widened from `/.agents/skills/` to `/.agents/`. G5 is omitted for agy, because in `accept-edits` mode agy wrote the file without a prompt when a hook answered `ask`.

**Architecture:** One PR, a plan 5 follow-up (backlog item PRO-155), on branch `agy-wiring`. devctl changes only in its template under `rapid_ship/templates/common/tools/devctl/devctl/`, and `uv run rapid-ship sync --in-place` vendors it. `hook_protocols.py` gains agy's event, answer and failure answer beside Claude Code's; `hook.py` passes the Harness through and skips G5 for agy; `doctor_wiring.py` gains the agy item, which also runs the wired command once on a probe event.

**Tech Stack:** Python 3.12 standard library, pytest, agy 1.4.7 as the hook spike recorded it.

**Spec:** [Spec 1](../specs/2026-10-14-kit-and-setup-design.md), sections 4 (Harness guardrails, the Protected set) and 6 (doctor, `devctl hook`). The [hook spike's record](../../trials/2026-10-21-hook-spike.md), its agy rows and [agy's interactive runs](../../trials/2026-10-21-hook-spike.md#agys-interactive-runs-pro-143), gives every agy fact this plan uses. Listed in the [plan index](2026-10-14-kit-and-setup.md) as a plan 5 follow-up.

**Status:** planned on 2026-10-26, after the owner decided that day to wire agy before GA. Tasks 1 to 5 are built on `agy-wiring`; Task 6, the live trial in agy, is a pending Owner step.

## Global Constraints

- Wiring, seeded at `.agents/hooks.json`: one hook named `devctl`, whose `PreToolUse` entry has the matcher `run_command|write_file|edit_file` and one command handler, `"$(git rev-parse --show-toplevel)/devctl" hook agy pre-tool`, with `"timeout": 600`. agy runs the hook in the folder that holds `hooks.json`, so the command finds the shim from git's top level. These are the tool names agy 1.4.7 sent; its hooks page names others, which no recorded event used.
- agy's event has no `cwd`: a call's `Cwd` argument, resolved against the first of `workspacePaths`, stands in for it, and without one that path does. No recorded event carried `Cwd`. `run_command` gives `toolCall.args.CommandLine` as the shell command; `write_file` and `edit_file` give `toolCall.args.Path` as the edited path. Any other tool gives a call that no rule matches.
- agy's answer is one line of JSON with exit 0: `{"decision": "deny", "reason": "<reason>"}`, or `{"decision": "allow"}` for no decision, which hands the call to agy's next hook or its own permission flow. The hook never answers `auto_approve`.
- agy blocks the call on exit 1, exit 2 and a timeout. So for agy, every failure that `devctl hook` sees, a usage error, an event it cannot read and an exception included, writes one stderr line and answers `{"decision": "deny", "reason": "devctl hook: <message>"}` with exit 0. agy shows an `allow`'s reason to nobody and a deny's to the agent, so an `allow` would switch the guardrails off without a trace, for example after an agy update changes the event format; the deny blocks every wired call until the cause is fixed, and says why. An invalid `project.toml` is no such failure: it writes its stderr line, G1 to G4 and the merge guard still decide, and a call that no rule matches gets `allow`. Failures before devctl runs, such as the shim's exit 127 or uv's exit 2, still block every wired call; doctor's agy item runs the hook to catch them.
- G5 is omitted for agy. G1 to G4, G7, G8 and the merge guard apply.
- Claude Code's protocol keeps its exit codes: an internal error exits 1, now with one stderr line for an unexpected exception too, in place of a traceback. An unknown or missing Harness still exits 1, because the hook cannot tell which protocol to answer in.
- doctor's items: `Harness wiring` becomes `Claude Code wiring`, and `agy wiring` follows it, in the full doctor and in `--settings`.
- Diff cap: the PR stays under 1,500 counted lines (Spec 1 section 5). If it would pass the cap, it stops after Task 3 and the rest moves to a second PR.
- No comment, docstring, message or test name cites the spike, a spec, a plan or a decision.
- Tests first. Each new test module's docstring starts `Offline:`.
- Commits are conventional and end with `Co-Authored-By: <the model that writes the commit>`.

## Review Focus

1. **A failure of devctl's own switches the agy guardrails off without a trace, or blocks agy without a reason.** Inputs: bytes that are not JSON, an event without `toolCall` or `workspacePaths`, a wired tool without its argument, `devctl hook agy` without an event, and an exception inside the rules. Expected: each exits 0 with a `deny` whose reason is the stderr line, starting `devctl hook: `. An invalid `project.toml` is no failure: it writes the stderr line and answers `allow` with no reason, because the rules still decide. Task 2's `test_the_agy_hook_always_exits_0_with_a_decision` pins it.
2. **G5 asks where agy cannot.** Expected: an agy edit of a Protected path gets `allow`, while G4 still denies an edit of `.rapid-ship/kit.lock`, and Claude Code still asks. Task 2's `test_g5_does_not_run_for_agy` pins it.
3. **The wiring and the protocol disagree on a tool.** Expected: the seed's matcher names each tool in `WIRED_TOOLS["agy"]`, and doctor reports a matcher that misses one. Tasks 2 and 3 pin it.
4. **doctor runs a command from a tracked file.** Expected: doctor runs it only when its words are `<path>/devctl hook agy pre-tool` and nothing more, the same parse as the Claude Code item, plus `$(git rev-parse --show-toplevel)` as a program-word prefix.

## Tasks

### Task 1: This plan and the plan index

- [x] Write this plan, and add it to the plan index as a plan 5 follow-up.
- [x] Commit `docs: plan the agy wiring (PRO-155)`.

### Task 2: agy's hook protocol

**Files:** `devctl/hook_protocols.py`, `devctl/hook.py`; `.rapid-ship/exceptions.toml` (EX-30, the blind `except` in `hook_command`); `tests/devctl/fixtures/hooks/agy/*.json`, copied byte for byte from the record's agy events without their `agy-` prefix; `tests/devctl/test_devctl_hook_agy.py`; `tests/devctl/test_devctl_hook_protocol.py`; `devctl/doctor_wiring.py`, which reads Claude Code's entries of the new tables.

**Interfaces:**

```python
# devctl/hook_protocols.py
WiredHarness = Literal["claude", "agy"]
WIRED_HARNESSES: tuple[WiredHarness, ...]
WIRED_TOOLS: Mapping[WiredHarness, tuple[str, ...]]
HOOK_COMMANDS: Mapping[WiredHarness, str]  # "devctl hook <harness> pre-tool"
PROTECTED_ASK: frozenset[WiredHarness]  # the Harnesses that run G5: claude


def read_event(harness: WiredHarness, payload: bytes) -> ToolCall: ...
def answer(harness: WiredHarness, decision: Decision, reason: str) -> tuple[str, int]: ...
def failure(harness: WiredHarness, message: str) -> tuple[str, int]: ...  # exit 1; agy: deny


# devctl/hook.py
def run_hook(call, owner_get, clock=time.monotonic, *, protected_ask: bool = True): ...
def decide(call, root, settings, branches, *, protected_ask: bool = True): ...
```

- [x] **Step 1: failing tests.** Docstring `Offline: agy's hook protocol, from events agy 1.4.7 sent; no Session runs.`
  - `test_read_event_normalises_each_recorded_agy_event`: `run-command.json` and `run-command-subagent.json` give `ToolCall("git status", (), /repo)`; `write-file.json` and `edit-file.json` give `ToolCall(None, (/repo/spike.txt,), /repo)`; `invoke-subagent.json` gives `ToolCall(None, (), /repo)`. `read_file` and `send_message` give an empty call too.
  - A relative `Path` resolves against the first workspace path, and so does a `Cwd` argument, which then decides the repository that judges the command; every tool in `WIRED_TOOLS["agy"]` reads into a call a rule can match; a malformed event (not JSON, not an object, no `toolCall`, no `name`, `args` not an object, no `CommandLine`, no `Path`, no or empty `workspacePaths`, a relative workspace path) is a `ValueError`.
  - `answer("agy", ...)`: a deny is one JSON line with its reason; no decision is `{"decision": "allow"}`; both exit 0.
  - `test_each_rule_decides_through_the_agy_protocol`, through `cli.main(["hook", "agy", "pre-tool"])`: G1, G2, G3, G4, G7 and G8 deny with their prefixes, and the merge guard denies `gh pr merge 1` under invalid settings. `test_a_harmless_agy_call_gets_allow_and_no_reason`: `git status` gets `{"decision": "allow"}` and no stderr.
  - `test_g5_does_not_run_for_agy`: a `write_file` of `AGENTS.md` under `# /**/AGENTS.md @o` gets `allow` for agy, and the same edit gets an ask in Claude Code. `test_without_the_protected_ask_g4_still_denies`: `decide(..., protected_ask=False)` still denies `kit.lock` with G4 and gives no decision for `AGENTS.md`.
  - `test_the_agy_hook_always_exits_0_with_a_decision`: the inputs of Review Focus 1, each exit 0 with one stderr line and a `deny` whose reason is that line; with an invalid `project.toml` the call is no failure, so it gets an `allow` with no reason. `test_an_exception_inside_the_rules_denies_the_agy_call` and `test_a_usage_error_names_the_agy_command`.
  - In `test_devctl_hook_protocol.py`: `WIRED_TOOLS` becomes `WIRED_TOOLS["claude"]`, the unknown Harness message names `claude and agy`, and an exception inside the rules exits 1 for Claude Code with one stderr line.
- [x] **Step 2: run** them; expected FAIL on the missing names. They failed at collection, because `WIRED_TOOLS` was a tuple.
- [x] **Step 3: implement.** `hook_command` catches every exception, since any traceback would block agy, and answers through `failure`.
- [x] **Step 4: run.** Format, check and sync; the hook tests pass. Status, fast check.
- [x] **Step 5: commit** `feat: answer agy's pre-tool hook with devctl hook agy pre-tool` (8224392).

### Task 3: The seed, doctor's agy item and the Protected set

**Files:** `rapid_ship/templates/common/.agents/hooks.json`; `rapid_ship/templates/kit.toml` (`seeded`); both CODEOWNERS templates and this repository's `.github/CODEOWNERS`, edited in place; `devctl/doctor_rules.py` (`PROTECTED_PATHS`); `devctl/doctor_wiring.py`, `devctl/doctor_local.py`, `devctl/doctor.py`; this repository's `.agents/hooks.json`, written by `sync`. Tests: `tests/devctl/test_devctl_doctor_wiring_agy.py`, `test_devctl_doctor_wiring.py`, `test_devctl_doctor_local_limits.py`, `test_devctl_doctor_settings.py`, `tests/test_kit_contents.py`.

**Interfaces:** `agy_wiring_problems(hooks: object) -> list[str]` and `agy_wiring_item(root: Path, tracked: Sequence[str]) -> Item` in `doctor_wiring.py`, giving `Item("guardrails", "agy wiring", ...)`.

The item is ok when `.agents/hooks.json` is tracked and valid JSON; a named hook that is not switched off (`"enabled"` absent or `true`) has a `PreToolUse` entry with a `command` handler whose words are `devctl`, or a path ending in `/devctl`, then `hook`, `agy` and `pre-tool`; its `timeout` is at least 360 seconds, where agy's default is 30; the matchers cover each tool in `WIRED_TOOLS["agy"]`, `""` or `*` covering all and any other matcher only by `re.fullmatch`, so it covers the tool whether agy anchors it or not; and each such command, run with `/bin/sh -c` in `.agents/` on a probe `run_command` event for `git push --force`, exits 0 with a G2 deny. A file doctor cannot read, a probe that cannot start and one that does not finish in 30 seconds are unknown. Every other gap is missing.

- [x] **Step 1: failing tests.** `agy_wiring_problems` on the seed, `*`, `""`, a regular expression, a missing tool, a missing matcher, `"enabled": false`, a missing or short `timeout`, Claude Code's command, an unquoted `$(git rev-parse --show-toplevel)` and other shapes. The item: ok, untracked, invalid JSON, unreadable, a gap, a hook that exits 127, one that answers `allow` or prints no JSON, one that times out, one that cannot start, and its probe's argv, working directory and event. `test_devctl_doctor_settings.py` runs the real hook through a shim that starts this checkout's devctl, so `--settings` prints four ok items. The seed equals the tests' `SEED` in both stacks and is seeded; `PROTECTED` has `/.agents/`, which covers `.agents/hooks.json`.
- [x] **Step 2: run** them; expected FAIL. They failed at collection on the missing `agy_wiring_item`.
- [x] **Step 3: implement**, `git add` the seed, then sync.
- [x] **Step 4: run** the doctor and Kit tests; `uv run rapid-ship status --strict` exits 0.
- [x] **Step 5: commit** `feat: seed agy's wiring, with doctor's agy wiring item and /.agents/ in the Protected set` (f0d2938).

### Task 4: Documents

- [x] Spec 1 sections 4, 6, 10 and 11, its scope list and its Kit table describe the wiring as built, in place of the open decision; ARCHITECTURE.md, README.md, the root `AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `.agents/AGENTS.md` and the plan index's layout and shared interfaces follow.
- [x] Commit `docs: describe the agy wiring as built`.

### Task 5: Verification

- [x] Run `uv run pytest -q tests/devctl tests/test_kit_*.py`, `./devctl check --tier fast` and `uv run rapid-ship status --strict`, and record them below.

### Task 6 (Owner step): the guardrails in agy

- [ ] In a scratch repository that holds the wiring, in an agy lead Session in `accept-edits` mode and in a subagent it starts, the owner runs plan 5's Task 8 Step 4 list without the G5 edit and the Monitor line, and records each decision and message in a trial record. A difference is fixed before this PR merges.
- [ ] In the same Session, the owner asks for `git status` run in a subdirectory and in a second repository outside the workspace, and records whether `run_command`'s arguments carry a `Cwd` and in which form. If agy runs a command elsewhere without a `Cwd`, the limit in Spec 1 section 4 stands; if its `Cwd` takes another form, `read_event` follows it before this PR merges.
- [ ] With an invalid `.rapid-ship/project.toml`, such as an unknown key, the owner asks the same Session to run `git status` and then `gh pr merge 1`, and records what agy did with each. The hook then writes a stderr line and exits 0 with JSON: `allow` for `git status` and the merge guard's deny for the merge. The spike saw stderr only with exit 1 or 2, so whether agy follows the JSON when stderr is not empty is unobserved. If agy treats that stderr as a hook failure, the hook stops writing stderr on agy's exit-0 paths before this PR merges.
- [ ] Before the runs above, in a scratch repository whose `.agents/hooks.json` runs the hook spike's stand-in with the matcher `*`, the owner asks an agy lead Session in `accept-edits` mode to write several files, edit one, move one, delete one and run a command, and lists every tool name the stand-in's events carry. The spike asked only for a command, a write and an edit, so other tools that write or run a command were never seen. Each such tool, with the argument that names its path or command, joins the seed's matcher and `_WIRED["agy"]` before this PR merges; a tool that reaches no rule stays out, because every wired call starts devctl.

## Verification record

Task 5 fills it. A blocked, skipped or simulated result is written as such, never as passed.

| Check, at 260cd81 | Result |
| --- | --- |
| `uv run pytest -q tests/devctl tests/test_kit_*.py` | exit 1: `1 failed, 1925 passed in 1445.16s (0:24:05)`. The failure, `tests/devctl/test_devctl_process.py::test_tools_are_found_on_the_callers_path`, is a 5-second timeout on a one-line shell script while the machine's load average was over 20; this branch does not change `process.py`. Rerun alone, `uv run pytest -q tests/devctl/test_devctl_process.py` exited 0: `23 passed`. `tests/devctl/test_devctl_project_dogfood.py`, which needs network access, passed in the full run |
| `./devctl check --tier fast` | exit 0: format, lint, map, exceptions, file-size, kit and vendored passed |
| `uv run rapid-ship status --strict` | exit 0: `45 managed files unchanged.` |
| `./devctl doctor --settings`, in this repository | exit 0: `doctor: 4 ok, 0 missing, 0 unknown`; the agy wiring item ran the real hook through the shim and uv |
| The `diff` step's count, `counted_lines` against `748d17c` | 1,258 counted lines, under the cap of 1,500 |

Not run: `./devctl check --tier full`, which needs a PR body, and the website build, because no page under `website/` changed. Task 6, the live trial in agy, is a pending Owner step.
