# agy hook launch outside the repository

The seeded agy launcher fails outside Git before devctl can read the event.
An offline reproduction confirms this at `3a4fc85fa33328d05c7cb498b0eaf0ba31354bd1`.
The actual working directory, environment and event of a T3-started hook remain unobserved.
This record does not yet establish the cause of the reported T3 failure or verify a fix.

## Reported failure

On 2026-10-28, the task coordinator reported two T3-started agy Workers blocked at their first commands.
Both used fresh worktrees at `3a4fc85` and reported:

```text
External hook 'devctl' failed to execute
```

One Worker reported a global skills directory as the hook's working directory; that claim is unverified.
The second reported that file reads outside its worktree were denied too.
The Harness's capacity label conflicted with the detailed hook-failure response.
These are attributed reports, not observations from this investigation, and supply no evidence of exhausted quota.
A later probe must carry its instructions inline rather than require reads of private files outside its workspace.

## Observed environment

| Item | Observation on 2026-10-28 |
| --- | --- |
| Repository revision | `3a4fc85fa33328d05c7cb498b0eaf0ba31354bd1`; clean at investigation start |
| `agy --version` | `1.4.7`; no agy Session started |
| Installed agy artifact | Mach-O arm64; SHA-256 `b7a13e53c9f49921692676ef8edc2e60ceb67064c00bc732d9a364ec3ad75b32` |
| `uname -srm` | `Darwin 24.6.0 arm64` |
| `uv --version` | `0.13.6` |
| Offline reproduction driver | CPython `3.13.12`, repeated under `3.15.2` with the same results; the repository pins `3.13` |
| First command, `./devctl doctor --settings` | exit 0: `4 ok, 0 missing, 0 unknown` |

REA identified the installed executable without executing an agent.
Native analysis was unavailable: Ghidra and IDA were not configured, and Hopper was absent.
No analysis engine was installed or configured, and no native control flow was recovered.
The REA target was closed after the inspection.

## Offline launch reproduction

This experiment uses synthetic events and the unchanged command read from the Kit template:

```sh
"$(git rev-parse --show-toplevel)/devctl" hook agy pre-tool
```

A Python driver invokes that exact string with `/bin/sh -c`, passing JSON on stdin.
It runs from this worktree's `.agents/` and from a scratch directory outside every Git repository.
The child receives the existing `PATH` and `HOME` only; Git environment overrides are absent.
These are controlled conditions, not observed agy environment variables.
The `CommandLine` values below are event data; no requested tool command runs.

| Hook cwd | Synthetic event | Exit | Answer |
| --- | --- | --- | --- |
| Worktree `.agents/` | `git status`, valid `workspacePaths` | 0 | `allow` |
| Worktree `.agents/` | `git push --force`, valid `workspacePaths` | 0 | `deny`, reason starts `G2:` |
| Outside Git | `git status`, valid `workspacePaths` | 127 | no stdout |
| Outside Git | `git push --force`, valid `workspacePaths` | 127 | no stdout |
| Outside Git | `git status`, missing `workspacePaths` | 127 | no stdout |
| Outside Git | `git status`, `workspacePaths` names a non-repository directory | 127 | no stdout |

Each outside-Git invocation writes:

```text
fatal: not a git repository (or any of the parent directories): .git
/bin/sh: /devctl: No such file or directory
```

The shell substitution returns no top-level path, so the shell tries `/devctl`.
Supplying a valid repository in stdin cannot help this command: it reads no event before locating devctl.
The earlier [hook spike](2026-10-21-hook-spike.md#agys-interactive-runs-pro-143) observed hooks running in `/repo/.agents/`.
That observation does not establish a universal launch-directory contract for agy or for T3.

Doctor's `_probe_item` in `doctor_wiring.py` always launches from the wiring file's parent inside the repository.
Its synthetic event names that same repository.
The passing settings check therefore does not cover outside-repository launch.

The private scratch artifacts are under `/tmp/rs-pro-172/worker-1/`:

- `reproduce.py`: the driver; `launch-results.json`: its six recorded results.
- `check-launch-contract.py`: expected outside-Git decisions checked against those results.
- `red-launch-contract.log`: four failing subtests, each `127 != 0`; no green fix result yet.

Reproduction command, from the tested worktree:

```sh
python3 /tmp/rs-pro-172/worker-1/reproduce.py
python3 /tmp/rs-pro-172/worker-1/check-launch-contract.py
```


## Baseline validation

These checks cover the unchanged implementation and this diagnostic documentation, not a fix:

- `uv run --python 3.15 pytest -q tests/devctl/test_devctl_hook_agy.py tests/devctl/test_devctl_doctor_wiring_agy.py tests/devctl/test_devctl_doctor_settings.py tests/devctl/test_devctl_hook_protocol.py tests/devctl/test_devctl_doctor_wiring.py tests/test_kit_contents.py`: 276 passed.
- `./devctl check --tier fast`: format, lint, map, exceptions, file-size, kit and vendored passed.
- `uv run --python 3.15 rapid-ship sync --in-place`, then `uv run --python 3.15 rapid-ship status --strict`: exit 0; 45 managed files unchanged.

The full tier and documentation build are reserved for the task lead's final-head verification.

## Required live capture

The coordinator must arrange an isolated scratch-project probe through T3.
This Worker cannot start another agent or change owner/global hooks.
The scratch-only `capture-context.py` and `capture-hooks.json` are prepared beside the reproduction artifacts; neither is installed in this repository.

The project-local capture hook must record the following, then deny the call without running it:

- Actual process cwd.
- Only these environment values: `PWD`, `PATH`, `AGY_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, `GIT_DIR`, `GIT_WORK_TREE`.
- Event key names, `workspacePaths`, `toolCall.name`, argument key names, and the `Cwd` and `Path` arguments when present.

Do not retain prompts, credentials, Session identifiers, file content or full events.
An inline brief asks the probe to attempt `pwd` once and stop after the diagnostic denial.
Record whether the capture hook ran, its selected context and the agent-visible denial.
If it does not run, collect the launcher error before changing the experiment.
Keep raw selected context private; scrub paths before adding observed fixtures or publishing results.

## Status and remaining limits

No launcher or protocol behavior has changed. G1 to G4, G7, G8 and the merge guard remain as implemented.
G5 remains omitted for agy because of the previously observed behavior of `ask` on file writes.
Outside Git, the current launcher prevents all those rules from running and fails before a decision.
The prior spike observed agy blocking a call when its hook fails; this reproduction runs no agy Session.

Choosing reliable repository context awaits the live capture.
If that capture supports an event-based launcher, regression tests must exercise the real seeded command outside Git before implementation.
They must cover harmless and guarded calls, missing/unusable context, malformed input and quoted paths without executing event text.
Any no-context fallback must document each unavailable guardrail and keep unrelated internal failures visible.
A real T3-started agy Session on the fixed revision must then execute a harmless command successfully.
Neither the offline reproduction nor a passing doctor check substitutes for that proof.
