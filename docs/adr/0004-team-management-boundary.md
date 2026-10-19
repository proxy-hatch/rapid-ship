---
status: accepted
---

# rapid-ship stops at the team-management boundary

rapid-ship does for a team of coding agents what a senior engineer does for a team of people. It helps define the architecture, breaks delivery into milestones, epics, stories and tasks, and sets and holds the code-quality bar. It does not run the team. Starting, watching, resuming and handing over agent Sessions, and routing their work to review and merge, belong to the Harness the owner works in: Claude Code, Codex CLI and Antigravity CLI each start subagents of their own. rapid-ship equips that Harness with a Lead brief, skills, instructions and guardrails. How closely the Harness follows them is the Harness's concern.

The same boundary applies to autonomy. rapid-ship reports metrics, records the owner's Suggested thresholds and reports a breach. It never moves a project between Walk and Flight; the owner decides how the project ships.

Within that boundary, rapid-ship's weight goes into advice. The signals that matter most for Flight, such as Alarms, incident reports and deploy rollbacks, are set up differently in every project and team, so rapid-ship cannot measure them for everyone. It guides the owner through setting them up, at Setup and again in the Pre-flight review that `rs-preflight` runs before the owner widens the Mode. Each signal then plugs in as a project-defined metric. Pre-flight advises and never gates.

An earlier ADR, 0003, deferred rapid-orchestrator and had the Lead launch bare Sessions. It was withdrawn before merge; [its text](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/adr/0003-walk-on-bare-sessions-orchestrator-deferred.md) stays at commit `401b57d`.

## Considered options

- **Walk on bare Sessions, the withdrawn ADR 0003.** The Lead launched each Worker and Reviewer through a devctl command, tracked each as a claim on its task, and woke on events from a devctl watcher. Rejected after design: stopped Sessions, handovers, stale claims and sandboxed launches made it brittle, and it duplicated what the Harnesses now do natively.
- **rapid-orchestrator**, a service that runs Sessions. Rejected, not deferred: a dedicated service is as brittle and competes with the Harnesses.
- **A Flight lease and a Pre-flight gate.** The lease returned a project to Walk when its metrics regressed or stopped arriving. Pre-flight admitted a project to Flight only after its metrics, its rungs and a set of attack pull requests passed. Rejected: when and how to change the way a project ships is the owner's call, made from the metrics. Pre-flight returned on 2026-10-19 as an advisory review only.
- **An Investigator**, an Agent that attributed each rollback and Alarm to the pull requests behind it. Rejected: the basic metrics come from GitHub and git with no model, and an owner who wants rollbacks or Alarms counted adds them as project-defined metrics. Incidents still feed the Corrections ledger: once the project has a metric of its own that returns incidents with their causes, gardening reads them as it reads review threads.
- **Flight's credential safeguards**, pieces 1, 2 and 5 of the eight that the research on Flight without an orchestrator proposed, which the [orchestrator note](../archive/orchestrator/README.md) summarises. Piece 1 keeps the owner's GitHub credential out of every Session. Piece 2 turns the Reviewer's verdict into a check run that default-branch code posts after it verifies the head commit. Piece 5 is a merge-time gate that fails closed. Rejected on 2026-10-19. Piece 1 needs Sessions that run apart from the owner's sign-ins, which is the owner's and the Harness's choice. Pieces 2 and 5 need a gate App and workflows that post verdicts and merge, the flow this ADR leaves to the Harness. The owner accepts Flight with their GitHub sign-in and both App keys within the Lead's reach.
- **A cap on how many Workers run at once**: first a five-Worker cap, then a Walk cap that the Lead brief asked for. Rejected: the owner launches the Walk Sessions and watches them, with the Workers they start, and can judge their own capacity.

## Consequences

- devctl never starts an agent to do work, never tracks or resumes one, and never pushes, reviews or merges as a step in a flow. It keeps no record of running agents. Only `devctl doctor`'s probes start a short headless Session, to check a Harness's sign-in and the skills it loads.
- Under the optional Agent identity ([ADR 0002](0002-github-gates-merges-reviews-run-locally.md)), agents call one thin devctl command for `gh` and `git push`. It runs only when an agent calls it, never as a step that rapid-ship drives.
- Without the credential safeguards, a misbehaving Lead can bypass the guardrails, the merge guard included, and act as the owner or as either App. CODEOWNERS binds the Lead in Flight only while the Lead acts through `devctl as`.
- The Lead brief's choice of models is advice. rapid-ship cannot see which model a Harness gave a subagent, so it cannot enforce "no silent model fallback".
- rapid-ship takes no notice of how many Sessions or agents run at once, and has no cap setting. Its documentation advises at most 3 Workers at once in Walk, for the owner's cognitive load.
- rapid-ship runs no gate for entering or leaving Flight. `rs-preflight` reviews readiness with the owner and changes nothing.
