# rapid-ship

rapid-ship does for a team of coding agents what a senior engineer does for a team of people: it helps define the architecture, breaks delivery down, and sets and holds the code-quality bar. The Harness the owner works in runs the agents ([ADR 0004](docs/adr/0004-team-management-boundary.md)). These terms are the agreed language of the October 2026 re-scope; existing code may use older meanings until it is rewritten.

## Language

### Lifecycle

**Setup**:
The one-time bootstrap of a repository with the Kit.

**Mode**:
The supervision level the owner chooses for a project, set by its escalation list. Walk and Flight name the two ends; anything between is allowed. The owner decides when to change it, from the metrics.
_Avoid_: phase, stage

**Escalation list**:
The kinds of pull request a Lead must bring to the owner instead of merging them on its own. The Protected set is always on it.

**Walk**:
The Mode whose escalation list holds every pull request. The Lead merges one only when the owner says so.
_Avoid_: training wheels, supervised trial, start

**Flight**:
The Mode whose escalation list holds only the Protected set and the kinds of change the owner adds. The Lead merges everything else once its checks and review pass.
_Avoid_: unattended delivery, autonomy grant

**Pre-flight**:
An advisory readiness review that `rs-preflight` runs with the owner before the Mode widens toward Flight. It covers the metrics to watch, Alarms and incident integrations, scheduled gardening, the escalation list, and the status of Agent identity and the ruleset. It never gates and never changes the Mode.
_Avoid_: gate

**Breakdown**:
The activity of turning a design into milestones, epics, optional stories and tasks. It can happen in either Mode.
_Avoid_: plan, decompose

**Milestone**:
A dated delivery checkpoint that can be demonstrated. It is the unit of work the owner hands a Lead.

**Epic**:
One capability inside a milestone, delivered in several pull requests.

**Story**:
An optional slice of an epic that users can see, used only when the epic ships in more than one slice.

**Task**:
The work of exactly one pull request, small enough for one review and within devctl's 1,500-line diff cap ([Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md)). It has acceptance criteria, a test plan and the tasks it is blocked by, so a Lead can run independent tasks in parallel.

**Protected set**:
The kinds of change that need the owner's approval in every Mode. The merge guard holds it in every setup, in each Harness wired to `devctl hook`, and GitHub also holds it through CODEOWNERS with Agent identity and a ruleset.

### Repository kit

**Kit**:
What rapid-ship installs into a repository at Setup: a devctl, an AGENTS.md tree, skills, guardrails and a starter Pattern set for each stack.

**Stack**:
A language toolchain the Kit supports, such as Python or TypeScript, with its own check steps, settings and starter Patterns. A repository can hold several stacks, each in its own directory.

**devctl**:
A repository's own developer CLI, used by people, agents and CI to run and verify that repository. It never starts an agent to do work. Only `devctl doctor --skills` starts a short headless Session, to check which skills a Harness loads.
_Avoid_: controller

**Feature map**:
A per-feature description of what the feature does, where it is entered, what data it touches, how to observe it and how to reproduce it.

**Pattern**:
The one supported way to do a recurring task: a reference implementation, what that reference does right, and the check that enforces it. The Kit seeds a starter set for each stack, which the project owns and adapts.
_Avoid_: convention, best practice

**Rule**:
A constraint on changes, marked either as enforced by a named check or as advisory.

**Harness guardrails**:
The Kit's project settings for each Harness it wires, which connect `devctl hook` to the Harness's hook events so that it can deny or ask before risky agent actions. They stop habits and mistakes; a misbehaving agent can bypass them.

**Merge guard**:
The rule of `devctl hook`, on in every setup, that denies an agent's `gh pr merge` when `devctl check` has not passed on the pull request's head commit, or when the pull request touches the Protected set, which it reads from CODEOWNERS on the pull request's base branch, never its head. It also denies a merge that does not name the head commit it checked with `--match-head-commit`, and, with Agent identity on, one whose head commit the Reviewer App has not approved. The other guardrails deny the other ways to land a change on the default branch that the hook recognises: `gh pr merge --admin`, a `git push` to that branch, and the merges, ref writes and commits through `gh api` that [Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) lists. It matches command lines, so a script or a tool the hook does not see can get past it. It runs only in a Harness wired to `devctl hook`. On a GitHub Free private repository, which has no ruleset, it is the enforcement.

### Agents

**Harness**:
The interface that runs a coding agent's loop: a CLI such as Claude Code, Codex CLI, Antigravity CLI or pi, or a desktop app such as Claude's or Codex's.
_Avoid_: runner, provider

**Provider**:
The account a Harness uses for its models: a vendor subscription, an API key, or a gateway such as OpenRouter. rapid-ship works with any of them.

**Worker**:
The role that implements one task. The Lead starts each Worker.

**Reviewer**:
The role that independently reviews one change.

**Lead**:
The Session the owner works with, following a Lead brief: it picks up tasks, starts Workers and Reviewers as its Harness allows, brings the kinds of pull request on the escalation list to the owner, and merges the rest.
_Avoid_: coordinator, manager, orchestrator

**Lead brief**:
The instructions that tell a Lead what to work on and how: a Focus and the project's escalation list. It names no model: the Lead's Harness chooses its subagents' models. rapid-ship helps write it; how closely the Lead follows it is up to the Harness.
_Avoid_: rule, which means a constraint on changes

**Focus**:
The part of a Lead brief that says what to work on now: a milestone or chosen tasks. It changes often and is never stored.

**Session**:
One conversation in a Harness, resumable by its ID.
_Avoid_: attempt, run

**Agent identity**:
The optional pair of GitHub Apps that agents act as: one opens and merges pull requests, the other posts reviews. With it, GitHub can tell an agent's pull request or review from the owner's, the owner can approve agent pull requests, and CODEOWNERS binds the Lead in Flight while it acts through `devctl as`. Without it, agents act as the owner and the metrics that need that distinction are unknown. It matters most to a solo owner on GitHub Free with a public repository; a team shares one pair per repository owner, a person or an organisation, with a private key for each developer.

### Improving the path

**Correction**:
A change that a human, the Reviewer or an incident, such as an Alarm or an incident report, required of an agent's work.

**Corrections ledger**:
The repository's record of Corrections and of what was done to prevent each repeat. Agents may add entries, which are not checked; changing or removing an existing entry needs the owner.

**Gardening**:
A recurring pass that adds new Corrections to the Corrections ledger and finds drift: instructions, documents or code that no longer match the repository or its Patterns, and exceptions nothing uses. For each repeated Correction, and for a severe first one such as a security finding, it proposes a fix on the rung that fits: a safe interface, a check, or both, and a skill or advisory Rule only when neither can carry the fix. rapid-ship advises running it on a schedule, at least weekly, and before each Pre-flight.

### Measuring

**Revision**:
One review round on a pull request that ended in changes requested, by the Reviewer or a human.

**Revert**:
A merged pull request that a later commit on the default branch reverted, in whole or in part.

**Alarm**:
A signal, set up by the owner, that released behaviour breached a budget, such as a failed probe or a rolled-back deploy. rapid-ship guides the owner through setting it up and counts it as a metric the project defines.

**Suggested threshold**:
A limit the owner records for a metric. rapid-ship reports a breach and takes no action.
