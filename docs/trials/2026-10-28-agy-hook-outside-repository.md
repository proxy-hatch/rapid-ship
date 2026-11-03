# agy hook launch, trust and command context

The Kit now seeds `./devctl hook agy pre-tool`, removing shell expansion from the configured command.
Managed `.agents/devctl` forwards to canonical root `devctl` by its own location.
Deterministic tests cover direct and shell invocation from root and `.agents/`, including spaces, arguments, stdin and real allow/G2-deny decisions.
A delegated T3 agy Session using the new seed passed [CLI-mode acceptance](#live-cli-mode-acceptance).
No agy protocol, tool `Cwd` policy or guardrail changes with this launcher.

Direct legacy-seed launch failed in a confirmed T3 CLI-mode Worker after explicit trust; the new seed passed direct live CLI-mode acceptance.
Earlier probes succeeded only when agy launched an absolute wrapper that ran the old seed through `/bin/sh -c`.
This supports a diagnosis that agy's T3 hook launcher does not support the old seed's shell syntax, including in CLI mode.
The original raw subprocess argv and stderr remain unavailable; this is a supported diagnosis, not direct syscall evidence.
Both original failed Workers also received delivered trust answers.
The original ACP profile is quota-blocked until approximately 2026-11-04; live ACP verification remains pending.
The original ACP cause remains unverified, so this is not a verified ACP fix.

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
In probes 2 and 3, agy launched an absolute wrapper; that wrapper ran the unchanged seed from `3a4fc85` through `/bin/sh -c`:

```sh
"$(git rev-parse --show-toplevel)/devctl" hook agy pre-tool
```

| Observation | Probe 1: top-level | Probe 2: delegated | Probe 3: delegated |
| --- | --- | --- | --- |
| Explicit trust | Required before hook ran | Required before hook ran | Required before hook ran |
| Hook cwd and Git top level | Repository root | Worktree root | Worktree root |
| Tool `Cwd` | Key present; value not captured | Global skills directory | Missing global skills directory |
| Old seed through wrapper `/bin/sh -c` | Not invoked by capture hook | Exit 0, `allow`, empty stderr; 2.42 s | Exit 0, `allow`; 1.32 s |
| Tool execution | First `pwd` failed; retry printed root | Wrapper denied; nothing executed | Hook allowed; command failed because requested directory did not exist |

Probe 3's separate file read worked and invoked no hook, as the seed's matcher specifies.
The delegated probes used CLI mode, but did not test agy directly launching the old seed's shell syntax.
The original failures used ACP mode, which these probes did not reach.
A missing tool directory is an observed command error separate from devctl's successful launch through the wrapper's shell.
Neither observation establishes the original ACP hook failure's cause.

Each fresh worktree prompted for hook trust. No implementation here answers trust automatically.
The hook cwd differs from both tool `args.Cwd` and environment `PWD`.
Probe 1 set `PWD` to root; probes 2 and 3 left it unset.
The four project/Git variables `AGY_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, `GIT_DIR` and `GIT_WORK_TREE` were unset.
Captures listed the root before skills folders in `workspacePaths`; command argument keys included `CommandLine`, `Cwd` and `WaitMsBeforeAsync`.
These observations are not a universal Harness contract.
The earlier [interactive hook spike](2026-10-21-hook-spike.md#agys-interactive-runs-pro-143) observed `.agents/` as hook cwd.

## Later direct legacy-seed CLI failure

The coordinator confirmed a later delegated Worker used T3's CLI profile on 2026-10-28 at 10:27 UTC.
Its worktree stayed at the unchanged review base `3a4fc85`, with the old seed configured directly as agy's hook command.
After an explicit `trust` answer, its first `./devctl doctor --settings` call failed with `External hook 'devctl' failed to execute`.
That command set `Cwd` to the correct worktree root.
The Worker made no changes, and its source revision never moved to the new implementation.
This failed direct legacy-seed launch differs from probes 2 and 3, where agy launched an absolute wrapper that supplied `/bin/sh -c`.
Together with the new seed's direct CLI-mode acceptance below, it supports the shell-syntax diagnosis; original raw subprocess argv and stderr are absent.
It does not test the new launcher or establish the original ACP cause.
The earlier CLI success cannot be generalized to every delegated configuration.
The manager withdrew the temporary relaxation: no agy Workers until the PR merges.

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

## Live CLI-mode acceptance

On 2026-10-28, the coordinator exported `e343ca97befac72d8eb6e48e8584e553d0b9eeeb` with `git archive`.
From that export, `rapid-ship init --stack agnostic --owner probe --repository probe/probe --name probe` rendered a fresh repository with no remote.
The committed implementation was used; later documentation-only corrections were absent from the export.
The seeded `.agents/hooks.json` blob was `d2c3bf2`, mode `100644`, with command `./devctl hook agy pre-tool`.
The managed `.agents/devctl` blob was `bcc8a11`, mode `100755`.
Both blobs matched the implementation commit; no capture wrapper replaced the hook.

A Codex parent delegated a real agy Session with worktree isolation in T3's CLI mode.
agy directly launched the new shell-free seed.
The new workspace asked for hook trust; the coordinator answered `trust` once.
Each command explicitly set `Cwd` to that worktree's root:

- `./devctl doctor --settings`: exit 0, `4 ok, 0 missing, 0 unknown`. The agy item denied its synthetic force-push probes in deterministic direct/shell checks from root and `.agents/`.
- `pwd`: exit 0 and printed the worktree root.
- `git push --force`: the pre-tool hook denied it with G2's force-push message. No remote existed, so nothing could have been published if the probe had failed.

These are live CLI-mode results using the new seed, separate from the earlier deterministic tests.
They are not ACP proof.

The coordinator also observed T3 displaying the G2 message on an earlier `Read` activity item.
That appears to be an attribution error because the seed does not hook Read; whether it explains the original Read-labelled failures remains unverified.
The scratch T3 project and worktree were removed after the run.

## Remaining limits

Existing projects must update their seeded `.agents/hooks.json` command manually after sync adds the managed forwarder.
The implementation worktree's hook file was copied byte for byte from the new template; no owner or global hook was changed.
The relative command cannot launch from arbitrary other directories, even with valid stdin workspace context.
Each new worktree still needs explicit hook trust. No automatic approval or fail-open behavior was added.
The launcher sacrifices no additional guardrail; the existing G5 omission and outside-repository settings/Cwd limits remain.

ACP verification remains blocked until its quota recovers, approximately 2026-11-04; the original ACP cause remains unverified.
The CLI evidence supports the shell-syntax diagnosis, but original raw subprocess argv and stderr are absent.
A CLI-mode success cannot substitute for that ACP result or complete the original agy plan's full guardrail trial.
Independent source review and the scoped documentation re-review approved the implementation and corrections.
The lead's final-head review, full check and documentation build are recorded separately.
