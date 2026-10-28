# agy hook launch, trust and command context

The Kit now seeds `./devctl hook agy pre-tool`, removing shell expansion from the configured command.
Managed `.agents/devctl` forwards to canonical root `devctl` by its own location.
Deterministic tests cover direct and shell invocation from root and `.agents/`, including spaces, arguments, stdin and real allow/G2-deny decisions.
No agy protocol, tool `Cwd` policy or guardrail changes with this launcher.

This is not a verified fix for the original ACP failures.
CLI-mode probes succeeded with the old launcher after trust; both original failed Workers also received delivered trust answers.
Their hook subprocess diagnostics remain unavailable.
The original ACP profile is quota-blocked until approximately 2026-11-04; live ACP verification remains pending.
Shellless ACP invocation is an unverified hypothesis, not an established cause.

## Revision and environment record

- `3a4fc85fa33328d05c7cb498b0eaf0ba31354bd1`: original failures, old launcher, and Kit used by the coordinator's scratch probes.
- `92d8b89092a1c2e1b12846caf2a35f6b8047e9c8`: first investigation; diagnostic documents only.
- `4aff27be83561731d70ce96d3ca5d60242dec419`: second investigation; trust and tool-context evidence, still no behavior changes.
- The implementation starts from `4aff27b`. Its tests and source are in this report's commit; review base stays `3a4fc85`.

The first investigation observed agy 1.4.7, Darwin 24.6.0 arm64 and uv 0.13.6.
The offline driver ran on CPython 3.13.12 and repeated on 3.15.2 with the same results; the repository pins 3.13.
The installed agy executable was Mach-O arm64, SHA-256 `b7a13e53c9f49921692676ef8edc2e60ceb67064c00bc732d9a364ec3ad75b32`.
REA identified it without starting an agent. No configured native analysis engine was available, so no native control flow was recovered.
The initial `./devctl doctor --settings` reported `4 ok, 0 missing, 0 unknown` on the old implementation.

## Original failures and trust evidence

On 2026-10-28, two T3-started agy Workers in fresh worktrees at `3a4fc85` reported:

```text
External hook 'devctl' failed to execute
```

Their timelines show the same generic failure for in-workspace `Read` calls.
Outside-workspace file reads have a separate containment refusal.
The Harness's capacity label conflicted with the detailed hook failure; those errors alone were not quota evidence.

Targeted read-only queries of runtime requests, command receipts and delivery records found:

| Worker | Trust created, UTC | `trust` recorded, UTC | Delivery completed, UTC |
| --- | --- | --- | --- |
| A | 08:08:58.659 | 08:09:25.247 | 08:09:25.275 |
| B | 08:10:16.621 | 08:10:24.055 | 08:10:24.070 |

Both deliveries succeeded on the first attempt, followed by agy's `Response received`.
Both workspace paths were present in the trust file at inspection time; it has no per-entry timestamp.
Later lead responses were rejected as already answered and did not resolve these requests.
Command-ID shape and focused inspection of T3 0.1.3 support a client-origin response, but identify no person or connection.
No evidence shows agy answering its own trust question or an incorrect mapping of `trust`.
The actual outgoing ACP bytes were not retained.

The inspected T3 package SHA-256 was `afb814bffbbb32a0a9c4ed68d7569bebb93cbd9a980aec9b6f2777c61ee59e7a`;
the server JavaScript's was `20efabeb8343c4963a8c25c539a8227411f5248838fcc8375dd517b26d8ec739`.
REA reported native companion integrity mismatches and exhausted its JavaScript analyzer heap.
These findings use focused extracted-source reads, not a complete semantic graph or observed ACP exchange.
Installed bytes do not establish which bytes handled the earlier requests.

Selected logs retained no hook cwd, shell exit or stderr for the original failures.
This was a bounded search, not proof that no diagnostic record exists elsewhere.
The `Read` label cannot establish which native event reached a hook, or whether failure happened during initialization.
A launcher change cannot repair a trust or initialization failure that prevents the launcher from running.

## Real T3 probes of the old launcher

The coordinator supplied three private scratch-project records from agy 1.4.7.
Raw events, local paths, accounts, profile paths and request identifiers remain private.
Probes 2 and 3 wrapped the unchanged seed from `3a4fc85`:

```sh
"$(git rev-parse --show-toplevel)/devctl" hook agy pre-tool
```

| Observation | Probe 1: top-level | Probe 2: delegated | Probe 3: delegated |
| --- | --- | --- | --- |
| Explicit trust | Required before hook ran | Required before hook ran | Required before hook ran |
| Hook cwd and Git top level | Repository root | Worktree root | Worktree root |
| Tool `Cwd` | Key present; value not captured | Global skills directory | Missing global skills directory |
| Old launcher | Not invoked by capture hook | Exit 0, `allow`, empty stderr; 2.42 s | Exit 0, `allow`; 1.32 s |
| Tool execution | First `pwd` failed; retry printed root | Wrapper denied; nothing executed | Hook allowed; command failed because requested directory did not exist |

Probe 3's separate file read worked and invoked no hook, as the seed's matcher specifies.
The successful delegated probes used CLI mode; the original failures used ACP mode, which these probes did not reach.
A missing tool directory is therefore an observed command error separate from devctl's successful launch.
It does not establish the original ACP hook failure's cause.

Each fresh worktree prompted for hook trust. No implementation here answers trust automatically.
The hook cwd differs from both tool `args.Cwd` and environment `PWD`.
Probe 1 set `PWD` to root; probes 2 and 3 left it unset.
The four project/Git variables `AGY_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, `GIT_DIR` and `GIT_WORK_TREE` were unset.
Captures listed the root before skills folders in `workspacePaths`; command argument keys included `CommandLine`, `Cwd` and `WaitMsBeforeAsync`.
These observations are not a universal Harness contract.
The earlier [interactive hook spike](2026-10-21-hook-spike.md#agys-interactive-runs-pro-143) observed `.agents/` as hook cwd.

## Offline old-launcher evidence

The first synthetic reproduction passed JSON on stdin through `/bin/sh -c` without running event commands.
From `.agents/`, `git status` received `allow` and `git push --force` received G2 `deny`, both exit 0.
Four outside-Git cases exited 127 without stdout: harmless or guarded commands with valid workspace context, missing context, or a non-repository context.
Git could not find a root, so substitution produced `/devctl`.
Valid `workspacePaths` on stdin cannot repair a launcher that fails before devctl starts.
These results explain that deterministic launch dependency, not the observed ACP failures.

Private artifacts remain under `/tmp/rs-pro-172/worker-1/`: `reproduce.py`, `launch-results.json`, `check-launch-contract.py` and `red-launch-contract.log`.
The four red outside-Git assertions are not the accepted new contract: the new relative seed supports root and `.agents/` only.
Doctor at that revision probed only through a shell from `.agents/`.

The second investigation replayed probe 2's event shape in 14 synthetic cases at `4aff27b`.
Only devctl and local Git reads ran; no requested command, file edit or GitHub request ran.
An explicit non-Git `Cwd` selected no repository even when `workspacePaths[0]` named one:

- G1, G2 and recognized G3 forms still denied. The merge guard denied a merge it could not check.
- G7/G8 had no Agent identity settings and gave no decision; workspace-Cwd controls denied with G7/G8.
- G3 used `main`/`master` and could not learn a custom default branch.
- G4 denied a lock edit inside the workspace, but gave no decision on an edit outside every repository.
- G5 remained omitted for agy, regardless of cwd.

Private replay artifacts: `/tmp/rs-pro-172/worker-2/probe-coverage.py` and `coverage-results.json`.
Two setup errors preceded the successful 14-case replay; neither was a product regression.
These existing coverage limits remain unchanged. Replacing explicit `Cwd` with workspace root could apply the wrong repository's settings.

## Shell-free launch contract and verification

The new seed is exactly `./devctl hook agy pre-tool`; matcher and timeout remain unchanged.
The managed executable `.agents/devctl` locates `../devctl` relative to its own script path and forwards all arguments and stdin.
Root `devctl` stays canonical and unchanged. The configured command needs no shell expansion; the executable shims still use `/bin/sh`.

Doctor permits static path quoting and exactly the hook arguments.
It rejects substitution, environment/tilde expansion, newlines and extra commands without running them.
It sends synthetic force-push events to each validated command, directly and through `/bin/sh -c`, from root and `.agents/`.
Every answer must be exit 0 with G2 `deny`; timeout, malformed answers and unusable launchers remain failures.
These are deterministic local checks, not agy or ACP Sessions.

Tests use rendered temporary files with spaces in their root path and a controlled canonical-shim stand-in.
They verify exact argument/stdin preservation, absolute-path forwarding from another cwd, both stacks, and real allow/G2-deny rules.
`CommandLine` stays data; no dangerous event command executes.

Recorded implementation checks:

- Red: `uv run pytest -q --tb=short tests/test_kit_contents.py -k 'agy_seed_launch or agy_forwarder'`: 6 failed, 4 passed. Four direct launches tried the literal substitution path; two forwarding tests found no shim.
- Red: `uv run pytest -q --tb=short tests/devctl/test_devctl_doctor_wiring_agy.py`: 14 failed, 67 passed. This exposed accepted shell expansion and missing launch coverage; two defect setups also lacked the not-yet-added forwarder.
- A further red case, `./devctl` followed by a newline and the hook arguments, exposed shell/direct disagreement. Doctor now rejects it before execution.
- Green: `uv run pytest -q --tb=short tests/devctl/test_devctl_hook_agy.py tests/devctl/test_devctl_doctor_wiring_agy.py tests/devctl/test_devctl_doctor_settings.py tests/devctl/test_devctl_hook_protocol.py tests/devctl/test_devctl_doctor_wiring.py tests/test_kit_contents.py`: 319 passed, including Claude compatibility.
- `uv run rapid-ship sync --in-place`, then `uv run rapid-ship status --strict`: 46 managed files unchanged after sync.
- `./devctl check --tier fast`: all seven steps passed.
- `./devctl doctor --settings`: `4 ok, 0 missing, 0 unknown`, with the real canonical launcher in all four deterministic contexts.

Logs are private under `/tmp/rs-pro-172/worker-3/`.
Historical checks apply only to their original revisions: first investigation 276 focused tests and fast tier passed; second investigation 145 focused tests, 14 synthetic cases and fast tier passed.

## Remaining limits and live proof

Existing projects must update their seeded `.agents/hooks.json` command manually after sync adds the managed forwarder.
This worktree's hook file was copied byte for byte from the new template; no owner or global hook was changed.
The relative command cannot launch from arbitrary other directories, even with valid stdin workspace context.
Each new worktree still needs explicit hook trust. No automatic approval or fail-open behavior was added.
The launcher sacrifices no additional guardrail; the existing G5 omission and outside-repository settings/Cwd limits remain.

The Task lead must arrange a real T3 agy probe at the fixed implementation revision, recording CLI or ACP mode explicitly.
It should capture the hook cwd, same-call `Cwd`, ordered workspace paths, launcher exit/stdout/stderr, and harmless tool output after explicit trust.
Read should be checked separately for whether a hook fires. Keep credentials, prompts and personal identifiers private.
ACP verification remains blocked until its quota recovers, approximately 2026-11-04.
A CLI-mode success cannot substitute for that ACP result or complete the original agy plan's full guardrail trial.
The lead also owns independent review, heavy checks and the documentation build; none is claimed here.
