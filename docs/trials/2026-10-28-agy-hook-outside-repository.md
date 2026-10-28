# agy hook launch, trust and command context

Two real T3 probes ran hooks from their repository roots after explicit workspace trust.
The delegated probe ran the unchanged seeded launcher successfully: exit 0, `allow`, no stderr.
Its tool argument `Cwd` named a global skills directory; that was not the hook process's cwd.
The earlier outside-Git launch failure remains a valid offline result, but does not explain these live observations.

Targeted records show that both original failed Workers received `trust` answers through T3, with successful response delivery.
Their underlying hook subprocess errors remain unavailable, so this investigation establishes no source fix.
No launcher, protocol, trust setting or guardrail behavior changed.

## Reported failure

On 2026-10-28, the task coordinator reported two T3-started agy Workers blocked at their first commands.
Both used fresh worktrees at `3a4fc85` and reported:

```text
External hook 'devctl' failed to execute
```

One Worker attributed the failure to a global skills directory. Later probes distinguish the tool argument from the hook cwd.
Both original timelines also label in-workspace `Read` calls with the same generic hook error. Outside-workspace file reads have a separate boundary refusal.
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


## First-round baseline validation

The first investigation recorded these checks before the new T3 evidence arrived.
They cover the unchanged implementation and its initial diagnostic documentation, not a fix:

- `uv run --python 3.15 pytest -q tests/devctl/test_devctl_hook_agy.py tests/devctl/test_devctl_doctor_wiring_agy.py tests/devctl/test_devctl_doctor_settings.py tests/devctl/test_devctl_hook_protocol.py tests/devctl/test_devctl_doctor_wiring.py tests/test_kit_contents.py`: 276 passed.
- `./devctl check --tier fast`: format, lint, map, exceptions, file-size, kit and vendored passed.
- `uv run --python 3.15 rapid-ship sync --in-place`, then `uv run --python 3.15 rapid-ship status --strict`: exit 0; 45 managed files unchanged.

The full tier and documentation build are reserved for the task lead's final-head verification.

## Real T3 probes

The coordinator supplied private records and selected-context captures from two scratch projects on 2026-10-28.
Both used agy 1.4.7. Probe 2 used an agnostic Kit from `3a4fc85` and a scratch-only diagnostic wrapper.
Raw events, local paths, account identities and request identifiers remain private.

| Observation | Probe 1: top-level Session | Probe 2: delegated worktree |
| --- | --- | --- |
| Trust | Waited about 3.5 minutes for an explicit answer | Pending at 08:48:07Z; explicitly answered about 50 seconds later; parent answered nothing |
| Hook cwd | Repository root | Child worktree root |
| Git top level from hook cwd | Same repository root | Same worktree root, exit 0 |
| Event `workspacePaths` | Root first, then skills directories | Worktree root first, then skills directories |
| Tool argument `Cwd` | Key present; value not captured | Global skills directory |
| Unchanged seeded launcher | Not invoked by this capture hook | Exit 0, `{"decision": "allow"}`, empty stderr, 2.42 seconds |
| Tool execution | First `pwd` failed after hook allow; second printed workspace root | Wrapper deliberately denied `pwd`; no tool command executed |

Each new workspace path prompted for hook trust before the capture hook ran.
The longer pending requests contradict an unconditional automatic trust answer or a seconds-long trust timeout.
They do not establish the behavior of every T3 configuration.
Both probes used a different Provider account from the original failures; this difference establishes neither cause nor exhausted quota.

For both probes, `AGY_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, `GIT_DIR` and `GIT_WORK_TREE` were unset.
`PATH` had 22 entries; its private values are not reproduced here.
Probe 1 had `PWD` equal to the root; probe 2 had no `PWD`.
The process cwd and the environment variable `PWD` are therefore separate evidence.

The captures contain event keys `artifactDirectoryPath`, `conversationId`, `stepIdx`, `toolCall`, `transcriptPath` and `workspacePaths`.
For `run_command`, argument keys were `CommandLine`, `Cwd` and `WaitMsBeforeAsync`.
These are observed keys, not a promise that future events have the same shape.

Neither probe establishes the delegated command's execution directory.
Probe 1 observed execution without capturing `Cwd`; probe 2 captured `Cwd` but denied execution.
Do not infer that the command executed in either the global skills directory or the workspace root.

## Original trust requests

Read-only queries selected the two requests from T3's runtime-request projection, event ledger, command receipts and effect outbox.
The provider conversation databases supplied only their relevant error fields, not full transcripts.

| Original Worker | Trust request created, UTC | Answer recorded, UTC | Value | Response delivery completed, UTC |
| --- | --- | --- | --- | --- |
| A | 08:08:58.659 | 08:09:25.247 | `trust` | 08:09:25.275 |
| B | 08:10:16.621 | 08:10:24.055 | `trust` | 08:10:24.070 |

Both accepted commands are `runtime-request.respond`; both delivery effects succeeded on their first attempt, without a recorded error.
The agy tool completion followed at 08:09:25.296Z and 08:10:24.082Z, respectively, with `Response received`.
Both workspace paths are also present in the relevant agy trust file at inspection time.
That file has no per-entry answer timestamp, so it alone cannot date the trust decision.

The leads' MCP responses came later: A sent `trust` at 08:10:11.199Z; B sent `deny` at 08:10:31.887Z.
Both were rejected as already answered. The lead logs' later times describe recording those results.
Thus neither later lead response resolved the original request.

The accepted command IDs are bare UUIDs.
In the inspected T3 0.1.3 package, the client response path generates bare UUIDs, while the MCP response path prefixes IDs with `mcp:`.
This supports a T3 client response as the resolver, rather than either lead's MCP call.
The retained records do not identify the client connection, person or UI gesture; that attribution remains an inference, not an identified actor.
No evidence shows agy choosing its own trust answer.

Static inspection of the shipped adapter found that an exact `trust` answer selects the `trust` option.
Trust questions take the user-input path before the ordinary automatic tool-permission policy.
T3 records a request as resolved before delivering its response, so completed state alone is insufficient.
Here, the successful delivery effects and subsequent agy completions provide additional evidence.
No incorrect mapping or failed delivery was found for these two requests; the actual outgoing ACP bytes were not retained in the inspected records.

The inspected package's SHA-256 was `afb814bffbbb32a0a9c4ed68d7569bebb93cbd9a980aec9b6f2777c61ee59e7a`.
The server JavaScript's SHA-256 was `20efabeb8343c4963a8c25c539a8227411f5248838fcc8375dd517b26d8ec739`.
REA's package analysis reported native companion integrity mismatches and exhausted its JavaScript analyzer heap.
The conclusions above use focused reads of the extracted JavaScript, not a complete semantic graph or an observed ACP exchange.
The installed package identity does not prove that identical bytes handled the earlier requests.

## Original hook errors: what remains unknown

The original provider error fields repeat `External hook 'devctl' failed to execute` without hook cwd, shell exit status or stderr.
The selected T3 provider logs summarize requests and response shapes rather than preserving hook subprocess diagnostics.
The retained server trace starts after these failures; the desktop trace does not identify their trust responder.
These are bounded negative searches, not proof that no other diagnostic record exists.

The timeline's `Read` label is insufficient to infer the event name seen by the hook.
The seed matches only `run_command`, `write_file` and `edit_file`; an unwired event that reaches devctl gets no decision.
The records do not distinguish hook initialization failure, unexpected matcher behavior or an ACP display label different from the native tool name.
Outside-workspace reads are separately refused by T3's client-file containment check.
Changing devctl's launcher cannot be claimed to fix a trust or initialization failure that prevents that launcher from running.

## Offline coverage replay of probe 2's shape

A synthetic event uses a real workspace root and an existing non-Git scratch directory as `args.Cwd`.
Its workspace list preserves the captured root-first, skills-after structure; private values are replaced.
For each case the unchanged seeded launcher runs from this worktree root with the synthetic event on stdin.
Only devctl and its local Git reads run. No event command, file edit or GitHub request is executed.

`read_event` resolves an absolute `Cwd` to itself, and `work_tree_root` finds no repository there.
The event's `workspacePaths[0]` does not override an explicit absolute `Cwd`.
The following 14 cases all exited 0 with empty stderr:

| Synthetic case | Decision | Coverage |
| --- | --- | --- |
| `pwd`, non-Git `Cwd` | `allow` | No rule matches |
| `git commit --no-verify` | `deny`, G1 | Does not need repository settings |
| `git push --force` | `deny`, G2 | Does not need repository settings |
| `git push origin HEAD:main` | `deny`, G3 | Default-branch fallback includes `main` and `master` |
| `git push origin HEAD:production` | `allow` | A custom default branch cannot be learned from the unrelated non-Git cwd |
| `gh pr merge 1 --admin` | `deny`, G3 | Recognized forbidden merge form |
| `git push origin HEAD:feature`, non-Git `Cwd` | `allow` | G7 has no Agent identity settings |
| `gh issue create --title probe`, non-Git `Cwd` | `allow` | G8 has no Agent identity settings |
| `gh pr merge 1`, non-Git `Cwd` | `deny`, merge guard | Cannot read settings; no GitHub request |
| Same feature push, workspace `Cwd` | `deny`, G7 | Control: workspace Agent identity is on |
| Same issue creation, workspace `Cwd` | `deny`, G8 | Control: workspace Agent identity is on |
| Absolute edit of workspace `.rapid-ship/kit.lock`, non-Git `Cwd` | `deny`, G4 | Edit path selects its repository |
| Absolute edit of non-Git scratch `.rapid-ship/kit.lock` | `allow` | No repository holds the edited path |
| Absolute edit of workspace `AGENTS.md` | `allow` | G5 is already omitted for agy |

This does not show that every guardrail disappears outside Git.
G1/G2 and recognized G3 forms remain, the merge guard denies an unverifiable merge, and edit-path lookup still applies.
G7/G8 lack repository settings, G3 cannot learn a custom default branch, and G4 needs an edit path inside a repository.
G5 remains omitted regardless of cwd.

Private replay artifacts: `/tmp/rs-pro-172/worker-2/probe-coverage.py` and `coverage-results.json` beside it.
Run from the tested worktree:

```sh
uv run --python 3.15 python /tmp/rs-pro-172/worker-2/probe-coverage.py
```

The first driver attempt lacked dependencies; a second used an incorrect seed JSON lookup.
Both setup errors were corrected before the 14-case replay passed. Neither was a product regression.

## Next evidence and policy boundary

No code fix is justified by the original generic failures alone.
The smallest next step is a coordinator-arranged delegated probe, with no automatic trust answer:

1. Capture the actual hook process cwd, the same call's `args.Cwd`, and its ordered `workspacePaths`.
2. Run the exact seeded command, recording exit, stdout, stderr and elapsed time.
3. For the single harmless `pwd` call, return the seeded decision and capture the actual tool output instead of deliberately denying it.
4. To diagnose the original failures, repeat under the original Provider configuration in an isolated workspace with explicit trust.
   Keep the Kit revision, matcher and timeout fixed; record the trust answer's transport and delivery outcome.
   If the wrapper never starts, collect the Harness's initialization/trust refusal before changing Kit code.
5. Exercise one in-workspace read separately and record its native tool name and whether the wrapper is invoked.

Keep credentials, prompts, account names and full transcripts out of the capture.
A successful probe of `pwd` alone does not validate guarded commands or plan 5's full agy trial.

Replacing an explicit tool `Cwd` with `workspacePaths[0]` is a policy change, not a launcher repair.
It could apply the wrong repository's settings to a command intentionally run elsewhere.
First observe execution and argument context on the same call, including a deliberate second-repository command.
If they disagree, resolve whether the adapter reports the wrong directory or the Harness executes in the wrong directory.
A later robustness change for genuinely outside-Git hook launch must retain its own regression test and state that it does not repair pre-launch trust failures.

## Second-round validation

- `uv run --python 3.15 python /tmp/rs-pro-172/worker-2/probe-coverage.py`: 14 synthetic cases passed; no requested tool executed.
- `uv run pytest -q tests/devctl/test_devctl_hook_agy.py tests/devctl/test_devctl_doctor_wiring_agy.py tests/devctl/test_devctl_hook_protocol.py`: 145 passed.
- `./devctl check --tier fast`: format, lint, map, exceptions, file-size, kit and vendored passed.
- `git diff --check`: passed.

Only diagnostic documents changed. No Kit template content, launcher or protocol changed, so no sync was needed in this round.
The full tier, documentation build, final-head review and further live probes remain with the Task lead.
