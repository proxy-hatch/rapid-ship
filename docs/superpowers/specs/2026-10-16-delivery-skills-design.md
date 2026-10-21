# Spec 2: Delivery skills

**Status: written on 2026-10-16, revised on 2026-10-19 with the owner's review decisions, which settled every proposal, and revised on 2026-10-20 to descope running agents across several Providers and to follow Spec 1's guardrail wiring for Claude Code alone.** It applies the owner's re-scope decisions of 2026-10-16, of the second review on 2026-10-19 and of 2026-10-20, and replaces the withdrawn Walk-flow draft. Section 13 lists what the trials still confirm and what is still open. This is the second of the three specs listed in the [rapid-ship design](2026-10-14-rapid-ship-design.md), after [Spec 1](2026-10-14-kit-and-setup-design.md) and beside [Spec 3](2026-10-16-metrics-and-gardening-design.md). Terms follow `GLOSSARY.md` at the repository root, and [ADR 0004](../../adr/0004-team-management-boundary.md) sets the boundary.

## 1. Outcome and scope

When this spec is built, an owner can take a feature from an idea to merged pull requests with five skills, in any supported Harness:

1. `rs-design` interviews the owner, then writes the feature design, ADRs and ARCHITECTURE.md changes.
2. `rs-breakdown` turns an approved design into milestones, epics, optional stories and tasks in the owner's tracker.
3. `rs-lead` builds the Lead brief at the start of a Session: what to work on now, which review findings trigger another round, and which pull requests come back to the owner.
4. `rs-work` tells a Worker how to meet the bar on one task.
5. `rs-review` tells a Reviewer how to judge one change.

The Lead's Harness does the running. It starts subagents or headless Sessions, waits for them, resumes them and stops them. rapid-ship ships only the instructions and the guardrails around them. No rapid-ship code in this spec starts, watches, resumes or hands over a Session. Agents push, review and merge while they follow these skills; rapid-ship never performs one of those actions as a step of its own.

This spec also defines:

- the tracker mapping notes, Linear's first (section 5);
- how the skills read the `[escalation]` table that Spec 1 seeds in `.rapid-ship/project.toml`, and two new tables, `[tracker]` and `[design]` (section 3.4);
- the review verdict format (section 3.6);
- what a Lead brief may and may not claim about each Harness (section 9).

Other specs own the rest:

- [Spec 1](2026-10-14-kit-and-setup-design.md) builds the Kit: `devctl check` and `doctor`, the Harness guardrails with their merge guard, the README.md and ARCHITECTURE.md seeds, the Pattern mechanism, optional Agent identity, `rs-setup`, `rs-health`, and the forked engineering skills such as `rs-tdd` and `rs-pr`.
- [Spec 3](2026-10-16-metrics-and-gardening-design.md) builds `devctl metrics`, the scheduled metrics Action, Suggested thresholds, the Corrections ledger, `rs-garden`, and `rs-preflight`, the advisory Pre-flight review before the owner widens the Mode.

## 2. How the skills fit together

```text
owner ─► rs-design ─► spec, ADRs ─► rs-breakdown ─► tracker: milestone ▸ epics ▸ (stories) ▸ tasks
                                                                        │
owner ─► rs-lead (Focus + project.toml) ─► Lead brief ─► Lead Session ◄─┘
                                                           │ starts, as its Harness allows
                                     ┌─────────────────────┴─────────────────────┐
                              Workers (rs-work)                          Reviewers (rs-review)
                              one task, one worktree, one PR             one verdict per head commit
                                     └──────────────► pull requests ◄────────────┘
                                 merged by the Lead, or brought to the owner (escalation list)
```

| Skill | Invoked by | Runs in | Writes |
| --- | --- | --- | --- |
| `rs-design` | The owner | The owner's Session | A feature spec, ADRs, GLOSSARY.md and ARCHITECTURE.md changes |
| `rs-breakdown` | The owner | The owner's Session | Tracker records |
| `rs-lead` | The owner, at the start of a Lead Session | The Session that becomes the Lead | The Lead brief, in the conversation only |
| `rs-work` | The Lead, once per Worker, or the Lead itself | A subagent or a headless Session in the task's worktree | One branch and one pull request |
| `rs-review` | The Lead, once per head commit | A subagent or a headless Session with its own context, in a checkout of the base branch | One review on that head commit |

`rs-design`, `rs-breakdown` and `rs-lead` are user-invoked (`disable-model-invocation: true`). `rs-work` and `rs-review` stay model-invocable, so a subagent can load them by name.

Two Spec 1 and Spec 3 skills reuse formats from this spec. `rs-health` writes its standards milestone with `rs-breakdown`'s levels and task template. `rs-garden` proposes rule changes as tasks in the same template, and reads the review verdicts of section 3.6 for Corrections.

## 3. Shared conventions

### 3.1 Where the skills live

Each skill is one real directory in `.agents/skills/<name>/`, which Codex and agy read. Claude Code gets a relative symlink per skill, `.claude/skills/<name> -> ../../.agents/skills/<name>`, recorded in the Kit lock (Spec 1). `SKILL.md` itself is never a symlink, because Codex rejects one by design. No per-Harness subagent definition ships. A Lead tells its Harness's generic subagent to follow the skill, or follows the skill itself.

```text
.agents/skills/
  rs-design/     SKILL.md, references/spec-template.md, references/adr-template.md,
                 references/grilling.md, references/domain-modeling.md
  rs-breakdown/  SKILL.md, references/levels.md, references/task-template.md,
                 references/trackers/linear.md
  rs-lead/       SKILL.md, references/brief-template.md, references/flight.md
  rs-work/       SKILL.md
  rs-review/     SKILL.md, references/verdict-format.md
```

Forked text comes from mattpocock/skills at `49dd158`, under Spec 1's upstream lock and with rapid-ship's changes inside marked sections:

| Skill | Upstream skills |
| --- | --- |
| `rs-design` | `grilling`, `domain-modeling`, `to-spec` |
| `rs-breakdown` | `to-tickets` |
| `rs-work` | `implement` |
| `rs-review` | `code-review` |

`rs-work` and `rs-review` are written for an agent that has only the skill and its spawn prompt:

- They list the inputs they need, and stop when one is missing.
- They use numbered steps and generic actions, not one Harness's tool names.
- They end with a fixed report format.
- They never rely on the Lead's conversation.

A person can still read them as the project's definition of done and of review.

### 3.2 Working with the tracker

rapid-ship supports any tracker, and devctl never talks to it. The skills reach the tracker through the connection the owner's Harness already has: an MCP server or a CLI. One mapping note per tracker says how the Breakdown levels map onto it (section 5.4). When the Harness has no connection to the tracker, the skill names the connection the mapping note needs, and stops.

Every skill that writes to the tracker follows three rules:

1. State each write in the conversation before sending it.
2. Re-read the tracker before retrying a write whose result is uncertain.
3. Never guess a state that cannot be read. Ask the owner.

### 3.3 With and without Agent identity

Agent identity is optional (Spec 1). It is on when `[github]` in `project.toml` records both Apps, each with its ID and slug (Spec 1, section 4). Agents then make their GitHub writes through `devctl as`, which runs `gh` or `git push` with an App's short-lived token. The Worker App pushes, opens and merges pull requests. The Reviewer App posts reviews. The Harness guardrails then deny `git push` and `gh` writes made as the owner (Spec 1). With Agent identity off, agents act as the owner through `git` and `gh`.

| Action | Agent identity on | Agent identity off |
| --- | --- | --- |
| A Worker pushes and opens a pull request | `./devctl as worker push`, then `./devctl as worker gh pr create` | `git push`, then `gh pr create`, as the owner |
| A Reviewer posts its verdict | `./devctl as reviewer gh api` to `POST /repos/{owner}/{repo}/pulls/{number}/reviews`, with event `APPROVE` or `REQUEST_CHANGES` | `gh api` to the same endpoint, as the owner, with event `COMMENT`. GitHub never lets a pull request's author approve it or request changes on it |
| A Reviewer resolves a review thread | `./devctl as reviewer gh api graphql`, with the `resolveReviewThread` mutation | `gh api graphql` with the same mutation, as the owner |
| The Lead merges a pull request it may merge | `./devctl as worker gh pr merge <number> --squash` | `gh pr merge <number> --squash`, as the owner. GitHub accepts it only when the ruleset requires no approval (section 6.5) |
| The owner approves an agent pull request | A normal GitHub approval | Not possible, because the owner is its author. The owner merges it in GitHub's web interface, through the admin bypass |
| Revisions | Countable from GitHub (Spec 3) | "unknown: needs Agent identity" (Spec 3) |

No agent runs `gh pr merge --admin`, pushes to the default branch, or merges, writes a ref or commits through `gh api`, with or without Agent identity. The Harness guardrails deny each form of these that Spec 1 lists, and `devctl as` also refuses `--admin` and a push to the default branch (Spec 1). An agent merges only with `gh pr merge`, and in every setup the merge guard, a rule of `devctl hook`, checks that merge before it runs (section 6.2). The guardrails match command lines, so a script or a tool the hook does not see can get past them. The verdict text of section 3.6 is for the Lead and the owner. No metric counts it.

### 3.4 Settings the skills read

Spec 1 seeds `[escalation]` in `.rapid-ship/project.toml`. This spec reads it, and adds `[tracker]` and `[design]`. The file is in the Protected set, so changing the Mode, the tracker or the spec location is a pull request the owner approves.

```toml
[escalation]                     # seeded by Spec 1; section 6.2 says how rs-lead reads it
every_pr = true                  # Walk. false: the Protected set and the kinds below
kinds = [
  "a pull request that removes a behavioural test",
  "a pull request that declares Over the diff cap:",
]
revision_rounds = 3              # a PR that reached this many Revision rounds goes to the owner

[tracker]                        # added by this spec
name = "linear"                  # selects .agents/skills/rs-breakdown/references/trackers/linear.md
note = ""                        # optional: a project-owned mapping note, for a tracker the Kit has none for

[tracker.linear]                 # the keys the mapping note defines
team = ""
project = ""

[design]                         # added by this spec
specs = "docs/specs"             # a repository directory, or "tracker" for tracker documents
```

devctl rejects an unknown key (Spec 1), so Spec 2's plan teaches its settings loader `[tracker]` and `[design]`. An unknown key or a wrong type in either makes the settings unreadable, and `devctl check` reports a blocked step (exit 2). Any key under `[tracker.<name>]` is accepted, because the mapping note defines those keys. devctl only validates `[tracker]`; it never contacts the tracker.

No setting names a Harness or a model: the Lead's Harness chooses its subagents' models.

The Focus is never stored. `rs-lead` asks for it in each Session. No setting limits how many Sessions or Workers run.

### 3.5 Branches and pull requests

- One task has one branch and one pull request. The branch name contains the task's tracker ID, such as `pro-123-reject-duplicate-emails`, so the tracker's GitHub integration links it.
- The pull request body starts with `Task: <ID>` and the task's link. `rs-pr` (Spec 1) writes the rest: a summary, the `## Evidence` section with each command run and its result, a `Not covered:` line, and `Removed tests:` with a reason for each removed test. An `Over the diff cap:` line, with its reason, puts the pull request on the escalation list (section 6.2). It appears only when the owner accepted the overage before the work. Without that acceptance, a Worker stops as `blocked` before it builds a pull request the owner may reject. devctl's `evidence` and `diff` steps check these (Spec 1).
- A branch that falls behind its base merges the base branch. It is never rebased after a push, because the guardrails deny force pushes.
- Every merge is a squash merge; the ruleset allows no other method (Spec 1).
- A pull request that changes a path in the Protected set is brought to the owner in every Mode, and the owner merges it in GitHub's web interface (section 6.2).

### 3.6 The review verdict

A Reviewer posts one verdict per head commit. The verdict applies to that commit only; a new head commit needs a new review. The review body:

```text
rapid-ship review: changes requested
Head: 3f2c1ab9e0d4c7b2a1f6e5d4c3b2a1f0e9d8c7b6
Task: PRO-123

This PR changes agent instructions: .agents/skills/rs-work/SKILL.md

<One paragraph: what the change does, and the main reason for the verdict.>

Blocking
1. src/app/links.py:42. URLs are joined by string concatenation, so a path with "?" breaks
   the link. Category: url-built-by-concatenation. Rungs: 1, 2. Prevention: build URLs only
   through links.build, and ban urljoin elsewhere.

Nits
1. src/app/links.py:57. The name tmp hides what the value holds. Rung: 3.
```

- The first line is exactly `rapid-ship review: approve` or `rapid-ship review: changes requested`. The verdict is approve only when no blocking finding remains.
- `Head` is the full SHA the Reviewer judged. The review is posted with that SHA as its `commit_id`, so it stays tied to that commit.
- The "changes agent instructions" line appears only when the pull request changes a skill, an AGENTS.md or CLAUDE.md file, or Harness settings. It names the paths.
- Each finding has a severity, a location when it has one, the problem and its consequence, and the rungs that would prevent a repeat: 1 safe interface, 2 check, 3 judgement, 4 the owner. A blocking finding also names its category and its prevention in one sentence. The category is a short kebab-case name: an existing one from the Corrections ledger when the mistake repeats one, otherwise a new one. `rs-garden` reads these fields to write ledger entries (Spec 3).
- The layout is fixed text, not a fenced data block. `rs-garden` reads it as a model does, and no metric parses it.
- Each blocking finding with a location is also posted as an inline comment on that line, which opens a review thread. Nits stay in the body and open no thread.
- A thread is resolved only by a later Reviewer that verified the fix, or by the owner. A Worker replies on the thread with the fixing commit and never resolves it. While the ruleset requires resolved threads (Spec 1), GitHub refuses the merge as long as a blocking finding's thread is open.

## 4. `rs-design`

**Purpose.** Help the owner decide what to build and record it: a feature design, ADRs, glossary terms and ARCHITECTURE.md. The skill interviews first and writes second.

**Inputs:**

- The owner's goal: a feature, an architecture change, or bringing ARCHITECTURE.md and the ADRs up to date.
- README.md, ARCHITECTURE.md, GLOSSARY.md, `docs/adr/`, the AGENTS.md guides, the Patterns and the feature files.
- The code in the area.
- Existing specs, in the repository or in tracker documents.
- `[design] specs` from `project.toml`.

**Steps:**

1. Ask which of the three goals the owner has.
2. Read the inputs. Explore the code for facts, through subagents where the Harness offers them. Finding facts is the agent's job: never ask the owner for a fact the repository holds.
3. Interview in rounds, following the forked `grilling` reference. Keep a tree of decisions. Each round asks every question whose prerequisites are settled. Number the questions, and give each a recommended answer worded so that "yes" accepts it. The decisions are the owner's. The interview ends when no question is left and the owner confirms the shared understanding.
4. Sharpen the language, following the forked `domain-modeling` reference. Add or correct the GLOSSARY.md entries for terms the design introduces. Read the ADRs before reopening a settled decision.
5. Propose an ADR for each decision that is hard to reverse, surprising without context, and the result of a real trade-off. An ADR that replaces another marks the old one superseded.
6. Propose the test seams: the highest seam that can show each behaviour, and as few seams as possible. The owner confirms them.
7. Write the spec from `references/spec-template.md`: the problem, the outcome the owner can demonstrate, the behaviours as numbered items, the decisions, testing (seams, tiers and existing tests to copy), what is out of scope, and open questions. Leave out file paths and code, which go stale. A prototype snippet that states a decision more exactly than prose is the exception.
8. Handle architecture. ARCHITECTURE.md describes what exists, so a design that changes a boundary records the change among its decisions, and the task that builds the boundary updates ARCHITECTURE.md (section 5.2). When the owner asked to bring ARCHITECTURE.md up to date, compare it with the code and propose the corrections.
9. Save. A spec goes to the `[design] specs` directory, or to a tracker document when the setting is `tracker`. ADRs, GLOSSARY.md and ARCHITECTURE.md always live in the repository. Put any repository files in one pull request on a new branch, pushed as section 3.3 says. The owner merges it.
10. Offer `rs-breakdown` for the approved spec.

**Outputs:** an approved feature spec; any ADRs; GLOSSARY.md and ARCHITECTURE.md changes; at most one documentation pull request.

**Never:**

- Decide for the owner, or question the project's purpose.
- Write production code or tests. A throwaway prototype that settles a question stays out of the pull request.
- Create tracker records; that is `rs-breakdown`'s job.
- Record an ADR for a decision without a real trade-off.
- Make ARCHITECTURE.md describe something that does not exist yet.

## 5. `rs-breakdown`

**Purpose.** Turn an approved design into milestones, epics, optional stories and tasks in the owner's tracker, sized so that a Lead can run independent tasks in parallel.

### 5.1 Levels

| Level | What it is | What it carries |
| --- | --- | --- |
| Milestone | A dated delivery checkpoint that can be demonstrated: the unit the owner hands a Lead | A name, the date the owner sets, a demo statement saying what the owner will see on that date, and links to its specs |
| Epic | One capability inside a milestone, delivered in several pull requests | A link to its spec |
| Story | Optional: a slice of an epic that users can see, used only when the epic ships in more than one slice | The user-visible outcome |
| Task | Exactly one pull request within devctl's diff cap: 1,500 added and removed lines, not counting files the cap excludes by extension, such as `.md`, `.txt` and `.log`, or binary, lock and Kit-managed files (Spec 1) | Acceptance criteria, a test plan and its blocked-by links (section 5.2) |

Only a task becomes a pull request. A Lead runs tasks; it never runs an epic or a story as one unit of work.

### 5.2 Task template

```markdown
## What to build
The behaviour this task makes work, as a user or caller sees it.

## Acceptance criteria
- [ ] The success case
- [ ] Each failure case
- [ ] Each boundary case that matters

## Test plan
- Seam: the interface the tests drive
- Tier: unit or behavioural, as the test settings in `project.toml` class the test files (Spec 1)
- One test per criterion above, written to fail first
- `./devctl check` passes

## Scope
- Expected areas: modules or directories
- Not in this task: exclusions
- Documents to update: ARCHITECTURE.md, an AGENTS.md guide, a feature file, a Pattern, or none

## Escalation
None, or the Protected paths and escalation kinds this task will touch.

## Links
- Spec, epic and story
- Corrections this task prevents: ledger entries, or none
- Blocked by: the tracker's native relation; listed here only when the tracker has none
```

### 5.3 Inputs, steps, outputs

**Inputs:** the approved spec; ARCHITECTURE.md, GLOSSARY.md, the ADRs and the code; the tracker's mapping note; `[tracker]`, `[escalation]` and the test settings from `project.toml`; the tracker's existing milestones and open tasks.

**Steps:**

1. Read the spec and the code it touches. Look for prefactoring that makes the change easy, and put it first.
2. Draft the milestones, each with a demo statement. The owner sets each date.
3. Draft the epics, one capability each, each linking to its spec. Add stories only for an epic that ships in more than one user-visible slice.
4. Draft the tasks as vertical slices, following the forked `to-tickets` reference: each cuts through every layer it needs and can be verified on its own. Keep code, its tests and its documentation updates in one task; never split a change from its tests. Sequence a wide refactor as expand, migrate in batches, then contract.
5. Size each task. Estimate its diff, tests and documentation included. Split any task likely to exceed the diff cap.
6. Add a blocked-by link only where a task needs another task's merged code or a decision. Give each shared interface to one task. Flag tasks that would change the same files, then link them or merge them.
7. Check coverage. Map every behaviour in the spec to a task. List deferred behaviour explicitly, so it cannot vanish.
8. Mark escalation. In each task, name the Protected paths and the escalation kinds it will touch. A task that prevents a Correction changes its existing ledger entry, which counts as Protected (Spec 3).
9. Present the draft as a numbered list: each task's title, what blocks it and what it delivers. Ask about granularity, the links, and tasks to merge or split. Repeat until the owner approves.
10. Publish to the tracker through the Harness's connection, following the mapping note (section 3.2). Publish in dependency order, so each blocked-by link points at a real record.
11. Report the milestone's link and its frontier: the tasks with no open blockers, which a Lead can start at once.

**Outputs:** tracker records for the approved milestones, epics, stories and tasks. No repository change.

**Never:**

- Create a record the owner has not approved.
- Write code.
- Copy tasks into a second tracker.
- Move a task into a started state; that is the Lead's job.
- Reach the tracker through devctl.

### 5.4 Tracker mapping notes

A mapping note is one Markdown file per tracker, at `.agents/skills/rs-breakdown/references/trackers/<name>.md`. `rs-lead` and `rs-work` read the same note. It answers seven questions:

1. How the Harness connects to the tracker, and how to confirm that the connection works.
2. Which record each Breakdown level becomes.
3. How a blocked-by link is expressed.
4. Which states mean unstarted, started, done and canceled, and who moves a task between them.
5. How a pull request links to its task.
6. Which labels the skills use.
7. How to list a milestone's frontier.

The Kit ships Linear's note first. A note for another tracker is a Kit change, collected under backlog item PRO-106. Until the Kit has one, a project writes its own note outside the Kit's managed files and names it in `[tracker] note`.

### 5.5 The Linear mapping note

| Level | Linear record |
| --- | --- |
| Product | One Linear project |
| Milestone | A project milestone, with its target date |
| Epic | A parent issue in that milestone, linking to its spec |
| Story | An optional sub-issue of the epic |
| Task | A leaf issue under its story or epic: the only level that becomes a pull request |
| Blocked by | Linear's "blocked by" relation |

- **Connection:** Linear's official MCP server, `https://mcp.linear.app/mcp`, or Linear's API. Read the project to confirm the connection.
- **States** follow Linear's state types. `rs-breakdown` publishes approved tasks in an unstarted state, such as Todo. The Lead moves a task to a started state, such as In Progress, when it starts the task's Worker.
- **GitHub integration.** Linear's GitHub integration moves an issue when its pull request opens and when it merges. The owner turns it on in Linear's settings; In Review on open and Done on merge is the recommended setup. It has no event for a pull request closed without merging. When that happens while the task is still started, the Lead asks the owner what happened.
- **Scope changes** happen in Linear. A deferred task moves back to Backlog, and a dropped one to Canceled. Cancelling an issue closes its linked open pull requests.
- **Pull request links:** the issue identifier appears in the branch name and in the body's `Task:` line.
- **Labels:** `needs-human` marks a task that waits for the owner's decision. A Lead never starts one.
- **Frontier:** the milestone's tasks that are in an unstarted state, have no `needs-human` label, and whose "blocked by" issues are all Done.

## 6. `rs-lead`

**Purpose.** Build the Lead brief at the start of a Session. The Session that runs `rs-lead` becomes the Lead. How closely it follows the brief is up to its Harness, which also chooses its subagents' models ([ADR 0004](../../adr/0004-team-management-boundary.md)).

### 6.1 Inputs, steps, outputs

**Inputs:**

- The Focus, from the owner: a milestone or chosen tasks.
- What `./devctl doctor` reports.
- `[escalation]` and `[tracker]` from `project.toml`, and whether Agent identity is on (section 3.3).
- `.github/CODEOWNERS` and the default branch's ruleset, read with `gh`.
- The Focus's records in the tracker, through the Harness's connection.
- The Lead's own Harness. `rs-lead` asks the owner when it cannot tell.

**Steps:**

1. Run `./devctl doctor` before anything else. When it cannot read the settings, it exits 2 and names the problem. Then stop and help the owner fix the settings: while `devctl hook` cannot read them, it still applies G1 to G4, and the merge guard denies every merge, but G5, G7 and G8 give no decision, so the asks before Protected edits and Agent identity's denies are lost (Spec 1). Every other Session, such as a Worker's or a Reviewer's, runs `./devctl doctor --settings` first, as the seeded root AGENTS.md asks; it reads only the settings (Spec 1, section 6).
2. Read the settings, CODEOWNERS and the ruleset. Check the Session's checkout: it has no local changes, and after `git fetch`, `HEAD` is the commit that `origin/<default branch>` names. Any branch is fine, so a Session in its own worktree qualifies. Section 9.2 says why.
3. Ask for the Focus: a milestone or chosen tasks. Read its tasks from the tracker, and show the frontier (section 5.5).
4. State that the Lead's Harness chooses its subagents' models. Give each warning of section 6.4 that applies.
5. State the Mode from the escalation list (section 6.2). Check that CODEOWNERS agrees with it, and explain any mismatch (section 6.5).
6. Fill `references/brief-template.md` (section 6.6).
7. Show the brief, and tell the owner its limit: rapid-ship cannot see which model a subagent receives or whether the Lead follows the brief, while CI and any ruleset hold either way. The owner confirms the brief or changes the Focus.
8. Follow the brief as the Lead. The owner may instead copy the brief into another Session.
9. When the owner asks to change the Mode, prepare the pull request that changes `project.toml`, and CODEOWNERS where needed (section 6.5). The owner approves and merges it.

**Outputs:** the Lead brief, in the conversation only; optionally one pull request that changes `[escalation]`, and CODEOWNERS where needed.

**Never:**

- Store the Focus.
- Change the ruleset or any other repository setting.
- Merge a pull request that changes `project.toml` or CODEOWNERS.
- Change the Mode because of a metric. The owner decides.
- Promise that the Harness will follow the brief.
- Start a Worker before the owner confirms the brief.

### 6.2 The escalation list and the Mode

The escalation list is the Protected set plus what `[escalation]` adds:

| Kind | Setting | What holds it |
| --- | --- | --- |
| The Protected set | Always on | In every setup, the merge guard (Spec 1): a rule of `devctl hook` that denies an agent's `gh pr merge` of a pull request that touches the Protected set. With or without Agent identity, the guardrails deny the other ways to land a change on the default branch that the hook recognises: `gh pr merge --admin`, a `git push` to that branch, and the merges, ref writes and commits through `gh api` that Spec 1 lists. `gh pr merge` is then the only recognised way for an agent to merge. The owner merges such a pull request in GitHub's web interface. The guardrails also ask the owner before an agent edits a Protected path. With Agent identity and a ruleset, GitHub enforces the Protected set too, through CODEOWNERS and the ruleset. Otherwise the merge guard holds it alone, and it is a guardrail: advice that a misbehaving agent can bypass, for example through a script or a tool the hook does not see |
| Every pull request | `every_pr = true` | With Agent identity: GitHub, through the CODEOWNERS line `* @<owner>` and the ruleset. Without it: the ruleset requires an approval that the owner cannot give their own pull request, which leaves only the owner's admin bypass, and the guardrails deny agents `gh pr merge --admin` and the other recognised ways to land a change on the default branch (Spec 1). That is a guardrail: advice that a misbehaving agent can bypass. Without a ruleset, with or without Agent identity: the brief and the owner's instruction, which are advice; the merge guard still denies a merge of a pull request whose head has not passed `devctl check` or that touches the Protected set, and with Agent identity one whose head the Reviewer App has not approved |
| A pull request that removes a behavioural test | Seeded in `kinds` | The brief. devctl's `diff` step classes each removed test as unit or behavioural (Spec 1) |
| A pull request that declares `Over the diff cap:` | Seeded in `kinds` | The brief. devctl's `diff` step reports the declaration (Spec 1) |
| A pull request that reached N rounds ending in changes requested | `revision_rounds` | The brief |
| Each kind the owner adds | `kinds` | The brief. The Lead judges whether a pull request is of that kind |

In every setup, the merge guard also denies an agent's merge while `devctl check` has not passed on the pull request's head commit. With Agent identity on, in every Mode, it denies the merge until the Reviewer App has approved that head commit too. A GitHub Free private repository has no rulesets, so there the merge guard is what rejects a failing check at merge. The merge guard acts only on `gh pr merge`, which the other guardrails leave as the only recognised way for an agent to merge, and only in a Harness whose hooks run `devctl hook` (section 6.4).

Agents run under the owner's sign-ins and, with Agent identity on, within reach of both App keys; the owner accepts that ([ADR 0004](../../adr/0004-team-management-boundary.md)). The guardrails, the merge guard included, stop habits and mistakes, and a misbehaving agent can bypass them (Spec 1). Without Agent identity, the owner's credentials can merge through the admin bypass, and only the guardrails keep the Lead from it.

With `every_pr = true` the Mode is Walk. With `every_pr = false` it is Flight, and the kinds the owner adds place it anywhere between the two ends. When an added kind is a set of paths, `rs-lead` offers to add those paths to the Protected set in CODEOWNERS instead, where the merge guard enforces them, and GitHub too with Agent identity and a ruleset.

In Walk the Lead brings every pull request to the owner and merges one only when the owner says so. The owner also launches the Sessions and watches them, with the Workers they start. rapid-ship neither asks nor counts how many Sessions or Workers run. Its documentation advises running at most 3 Workers at once in Walk, for the owner's cognitive load.

A pull request on the escalation list goes through three steps:

1. The Lead takes it to "ready for the owner": `devctl check` passed on its head, the latest verdict on that head is approve, and no blocking thread is open. At the revision-round limit, the Lead stops the rounds instead.
2. The Lead tells the owner the link, the task, which kinds put it on the list, the last verdict, and the nits it skipped.
3. The Lead moves on to other tasks, and merges a pull request on the list only when the owner says so. The owner merges a Protected pull request in GitHub's web interface. For any other pull request on the list, with Agent identity, the owner approves, then merges or asks the Lead to merge. The Lead can merge only a head the Reviewer App approved, so to merge without that approval the owner merges in GitHub's web interface (Spec 1). Without Agent identity, the owner merges it in GitHub's web interface, through the admin bypass where the ruleset requires an approval, or, without a ruleset, merges it or asks the Lead to.

The Lead merges any other pull request itself when `devctl check` passed on its head, the latest verdict on that head is approve, and no blocking thread is open. It merges with `gh pr merge <number> --squash --match-head-commit <head SHA>`, through `./devctl as worker gh` with Agent identity, because the merge guard denies a merge that does not name the head it checked (Spec 1). With Agent identity, the merge guard also enforces the approve verdict: it denies the merge until the Reviewer App has approved that head.

### 6.3 Finding triage

The same rules appear in `rs-review`'s text, so the Reviewer and the Lead agree:

- The Lead sends every blocking finding back to a Worker.
- The Lead never starts a round for nits and never sends them to a Worker. They stay in the review for the owner to see.
- The Lead never overrules a blocking finding. When it disagrees, it brings the pull request to the owner with both views.
- A finding without a severity counts as blocking.
- A round is a head commit that received a verdict of changes requested: a review whose body starts `rapid-ship review: changes requested`, or a person's review that requested changes. Several such reviews of one head are one round. Spec 3's Revisions metric also counts distinct head commits, but reads GitHub's review states, so it needs Agent identity; the Lead's count works without it. When a pull request reaches `revision_rounds` rounds, the Lead brings it to the owner instead of starting another round.

### 6.4 Harness warnings

`rs-lead` gives each warning that applies to the Lead's own Harness, which also runs its Workers and Reviewers.

- **A Harness without Kit wiring.** The Kit ships guardrail settings only for Claude Code (Spec 1). Codex and agy get theirs only if the hook spike, backlog item PRO-139, the first task of Spec 1's plan 5, confirms their hooks and a follow-up wires them. A Lead on any other Harness, Codex and agy included until then, and the Workers and Reviewers it starts, run without the Harness guardrails, the merge guard included; the pre-commit hook, CI and any ruleset still hold. `rs-lead` gives this warning when the Kit has no wiring for the Lead's Harness.
- **Headless approvals.** A headless Worker can do only what the project's Harness settings allow without a prompt. `rs-lead` names what is missing and the owner decides. It never adds a bypass flag such as `--dangerously-skip-permissions`.

### 6.5 Helping the owner fly

When the owner wants fewer pull requests brought to them, `rs-lead` first offers `rs-preflight` (Spec 3): an advisory readiness review of the metrics to watch, Alarms and incident integrations, scheduled gardening, the escalation list, Agent identity and the ruleset. `rs-preflight` never gates and never changes the Mode. When to fly is the owner's call. Then:

- **With Agent identity,** `rs-lead` prepares one Protected pull request with two changes: `[escalation] every_pr = false`, with the kinds the owner adds, and CODEOWNERS with the `* @<owner>` line removed and the Protected set uncommented (Spec 1). Once the owner merges it, the Lead merges other pull requests as the Worker App while it acts through `devctl as`. The Worker App cannot use the owner's bypass, so GitHub still requires the owner for every Protected path. The ruleset's required approvals stay at 1 until the live trial shows whether GitHub counts the Reviewer App's approval. If it does not, the count becomes 0 and code-owner review stays required, so CODEOWNERS alone decides who must approve (Spec 1). Either way, the merge guard denies the Lead's merge until the Reviewer App has approved the head commit (Spec 1).
- **Without Agent identity,** an agent's pull request comes from the owner's account, so the owner's own review cannot meet a required review. For a solo owner, the Lead can merge only if the ruleset drops its review requirement. CODEOWNERS then binds no one on GitHub. The merge guard still denies the Lead's merge of a Protected pull request, or of one whose head has not passed `devctl check`; it is a guardrail, which a misbehaving agent can bypass. It cannot require the Reviewer's approval, which comes from the owner's account, so only the Lead brief holds the Lead to the Reviewer's verdict. Flight without Agent identity is a supported choice. `rs-lead` explains this trade, and offers Agent identity as the alternative; [ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) says when it is recommended. The owner decides and changes the repository setting; `rs-lead` never changes it.
- **Without a ruleset,** such as in a private repository on GitHub Free (backlog PRO-100), GitHub enforces no escalation kind in any Mode. The merge guard is then the only check at merge: it rejects a pull request whose head has not passed `devctl check`, a Protected pull request and, with Agent identity, one whose head the Reviewer App has not approved. `rs-lead` says so.

Returning to Walk is the reverse pull request, which `rs-lead` prepares whenever the owner asks. Metrics never move the Mode.

### 6.6 The brief template

`references/brief-template.md` holds this text. `rs-lead` fills the angle brackets and drops lines that do not apply.

```markdown
# Lead brief: <repository>, <date>

You are the Lead. Deliver the Focus through Workers and Reviewers, following this brief
and the repository's AGENTS.md.

## Focus
- Work on: <milestone and link | task IDs>.
- The frontier now: <task IDs>.

## Mode: <Walk | Flight>
- Bring these pull requests to the owner: <every pull request | the Protected set, and the
  kinds listed>. Merge one only when the owner tells you to, and never one that touches the
  Protected set: the owner merges those.
- <Flight:> Merge any other pull request yourself, with a squash merge, when `devctl check`
  passed on its head, the latest verdict on that head is approve, and no blocking thread is open.
- Merge with `<gh | ./devctl as worker gh> pr merge <number> --squash --match-head-commit <head SHA>`.
  The merge guard denies a merge without `--match-head-commit`; its message gives the command to retry.
  <With Agent identity:> It also denies a merge until the Reviewer App has approved that head.

## Running a task
1. Pick a frontier task: unstarted, not labelled needs-human, every blocker done.
2. Fetch, then create its worktree and branch from the default branch:
   `git worktree add -b <branch> <path> origin/<default branch>`. Where your Harness gives
   each subagent its own worktree, you may use that instead.
3. Move the task to its started state in the tracker.
4. Start a Worker in that worktree. Tell it: follow `.agents/skills/rs-work/SKILL.md`; the
   task ID and text; the worktree, branch and base commit; whether Agent identity is <on|off>;
   that it must run `./devctl check` before it reports, and never push to the default branch,
   force-push, skip hooks or review its own change; and to end with the rs-work report.
5. Wait for every Worker you started before you summarize.
6. Treat a Worker's report as a claim. Read the pull request's `devctl check` result yourself.
7. For each new head commit, start a new Reviewer with its own context: never the Worker
   that wrote the change, and never yourself if you wrote it. Start it in a checkout of the
   base branch, such as your own checkout at `origin/<default branch>`, never in the task's
   worktree. Tell it: follow the base branch's `.agents/skills/rs-review/SKILL.md` in that
   checkout; the pull request, the head SHA and the task.
8. Triage the verdict (below). Send blocking findings to a Worker for that pull request,
   with the pull request, the findings and the task.
9. Bring the pull request to the owner, or merge it, as the Mode says.

## Review findings
- Always have a Worker fix every blocking finding.
- Never start a round for nits, and never send them to a Worker.
- Never overrule a blocking finding. If you disagree, bring the pull request to the owner
  with both views.
- A finding without a severity is blocking.
- After <N> rounds that ended in changes requested, stop and bring the pull request to the owner.

## Bringing a pull request to the owner
- Say the link, the task, why it is on the escalation list, the last verdict, and the nits
  you skipped. Then continue with other tasks.

## Tracker: <name>
- <States, links and labels from the mapping note.>
- Never guess a state. If a pull request closed without merging while its task is still
  started, ask the owner what happened.

## Corrections
- When the owner corrects work in this Session, add a Correction to the Corrections ledger:
  one new file in `docs/corrections/`, in the format its README states, with `source: session`
  and the rungs that would prevent a repeat. Add it to the open pull request the Correction
  concerns, or to your next pull request when none is open.

## Stop and ask the owner when
- A task needs a decision its spec does not make. Label it needs-human, then continue with
  other tasks.
- A check is blocked. A missing tool or credential is not a pass.
- A guardrail refuses an action. Never work around a guardrail.

## Never
- Use `--no-verify`, force-push, push to the default branch, run `gh pr merge --admin`, or merge, write a ref or commit through `gh api`.
- Edit `.rapid-ship/kit.lock` by hand, or change a Protected path without the owner.
- Merge a pull request on the escalation list unless the owner tells you to.
- Add a permission-bypass flag to a Worker or a Reviewer.
```

The spawn details in steps 4 and 7 restate the constraints that matter, because only Claude Code documents that subagents inherit the project's instructions (section 9.2). The Corrections ledger's place and format are Spec 3's. A pull request may add a new entry without the owner. A change to an existing entry, such as its status, or its removal counts as Protected, so the owner signs off on it (Spec 3).

## 7. `rs-work`

**Purpose.** Tell a Worker how to meet the project's bar on one task, and nothing beyond that task.

**Inputs,** from the spawn prompt:

- The task's ID and text: acceptance criteria, test plan, scope and links.
- The worktree path, the branch and the base commit.
- Whether Agent identity is on.
- For a fix round: the pull request and its blocking findings.

**Steps:**

1. Check the inputs. If one is missing, stop and report `blocked`.
2. Check the workspace: you are in the worktree, on the branch, with no uncommitted changes, and the base commit is in its history. If not, stop and report `blocked`.
3. Read the task, the spec it links, the AGENTS.md guides of the areas you will touch, their Rules, the Patterns, and GLOSSARY.md.
4. Scope the change. List the areas you expect to change. Stop and report `blocked` if the task needs a path outside its scope, a Protected path it does not name, a decision its spec leaves open, or a diff over the diff cap. Say what is needed. Never widen the task yourself. Declare `Over the diff cap:` only when the Lead says the owner accepted the overage; that pull request then goes to the owner in every Mode.
5. Work test-first with `rs-tdd`. For each acceptance criterion, write a test, watch it fail, make it pass, and commit. The pre-commit hook runs `./devctl check --tier fast`.
6. Follow the Patterns. Use each Pattern's reference implementation; never add a second way to do the same task.
7. Never add a suppression on your own. An exception needs an entry in `.rapid-ship/exceptions.toml`, which is Protected: stop and report `blocked`.
8. Update the documents the task names. When the task prevents Corrections in the ledger, set each entry's `status` to `implemented` and its `prevented_by` to the new mechanism (Spec 3). That change to existing entries counts as Protected, so the owner signs off on it.
9. Run the full `./devctl check` before you report done; no hook runs it when you stop. Fix every failure in the code. Never weaken a test, delete one to pass, or skip a hook. A blocked step (exit 2) is not a pass: report it.
10. Push the branch and open the pull request as section 3.3 says. Write its body with `rs-pr`, as section 3.5 says: the `Task:` line, Evidence, `Not covered:`, and each removed test with its reason.
11. End with the report below.

**A fix round:**

1. Work in the same worktree and branch. If the branch is behind its base, merge the base branch.
2. Fix each blocking finding. When it concerns behaviour, write the failing test first.
3. Reply on each finding's thread with the commit that fixes it. Never resolve a thread.
4. Run `./devctl check`, push, update the Evidence section, and report.

**Outputs:** one branch and one pull request, or new commits on it in a fix round; a reply on each fixed finding's thread; and this report:

```text
rs-work report
Task: <ID>
Result: pr-opened | fixed | blocked
PR: <url>   Head: <full SHA>
Check: ./devctl check -> exit <code>
Not done: <list, or none>
Blocker: <what the Lead or the owner must decide, or none>
```

**Never:**

- Review or approve your own change, or resolve a review thread.
- Merge, push to the default branch, force-push, or use `--no-verify`.
- Edit `.rapid-ship/kit.lock`, or a Protected path the task does not name.
- Act as the Reviewer App.
- Start a second task, or open a second pull request for this one.
- Undo a merged commit by hand. Use `git revert`, which keeps the `This reverts commit` line that Spec 3 counts Reverts by.

## 8. `rs-review`

**Purpose.** Tell a Reviewer how to judge one change against its task and the project's standards, and how to post one verdict on one head commit.

**Inputs,** from the spawn prompt:

- The pull request and the head SHA to review.
- The task's ID.
- Whether Agent identity is on.

**Steps:**

1. Check the inputs. If one is missing, stop and report it.
2. Check your checkout. It must be a checkout of the pull request's base branch with no local changes: after `git fetch`, `git merge-base --is-ancestor HEAD origin/<base branch>` succeeds. If not, stop and report it. You run under the instructions and hooks of your checkout, so they must come from the base branch, never from the change under review.
3. Check independence. If your Session or subagent wrote any commit in this pull request, stop and report that you are not independent.
4. Pin the head. Read the pull request's current head SHA. If it differs from the one you were given, stop and report that the head moved.
5. Read the change only through git: `gh pr diff <number>`, or `git fetch origin pull/<number>/head` and then `git show <head SHA>:<path>` and `git diff origin/<base branch>...<head SHA>`. Never check out the head, run its code or edit it.
6. Read the task and its spec, then the standards from your checkout: the AGENTS.md guides and their Rules, the Patterns, GLOSSARY.md and the ADRs. When the pull request changes a standard or an agent instruction, judge by your checkout's version, which is the base branch's.
7. Read `devctl check`'s result on the head. A failed step is a blocking finding. If the check has not finished, say so in the summary.
8. Judge the task. Is each acceptance criterion met, and tested by a test that can fail? Are the failure and boundary cases covered? Does the change do anything the task did not ask for? Does the Evidence match the diff? Is each removed test declared, with a sound reason?
9. Judge the standards: the Rules, the Patterns, the ADRs, the glossary's terms, and the documents the change makes wrong. Apply the forked smell baseline as judgement calls, which the repository's documented standards override. Skip what `devctl check` already enforces.
10. Classify each finding with the table below. Give it its rungs and, when blocking, its category and its prevention. Take the category from `docs/corrections/` when the mistake repeats an entry there.
11. For a re-review, check each blocking thread of earlier verdicts. Resolve the thread when its fix holds, with GitHub's `resolveReviewThread` mutation. Otherwise, keep that thread open and list the finding again under Blocking, without a second inline comment.
12. Check that this head has no review whose body starts with `rapid-ship review:`. Then post yours in the format of section 3.6, on the head SHA as `commit_id`, as section 3.3 says: through `POST /repos/{owner}/{repo}/pulls/{number}/reviews` with the body, the event and an inline comment for each blocking finding with a location.
13. End with the report below.

| Blocking | Nit |
| --- | --- |
| An acceptance criterion is missing, partial or wrong | A naming, wording or structure preference with no concrete consequence |
| Behaviour without a test that can fail, or a test that cannot detect the claimed behaviour | An optional improvement the task did not ask for |
| A removed test that is undeclared or has no sound reason | |
| A broken Rule, a bypassed Pattern, or a second way to do a recurring task | |
| A risk of data loss, exposure or a security hole | |
| Behaviour outside the task | |
| A document the change makes wrong | |
| A failed `devctl check` step | |

A finding whose consequence you cannot name is a nit. Pick its rungs by what would prevent a repeat: 1 when one supported interface with the bypass banned would remove the misuse, 2 when a deterministic check could catch it, 3 when only judgement can, 4 when only the owner should decide. A finding can name more than one rung.

**Outputs:** one review on the pinned head commit; the threads it verified and resolved; and this report:

```text
rs-review report
PR: <url>   Head: <full SHA>
Verdict: approve | changes requested
Blocking: <n>   Nits: <n>
Review: <url>
```

**Never:**

- Edit code, commit or push.
- Check out the head of the pull request, or run its code.
- Approve a change you wrote, or review a head other than the one you pinned.
- Post a second verdict for a head.
- Resolve a thread whose fix you did not verify.
- Merge, or act as the Worker App.
- Start further Reviewers unless the Lead asked you to.

## 9. What a Lead brief may claim about each Harness

A Lead brief is advice to a Harness that rapid-ship does not control, so it relies only on documented behaviour. The facts here come from rapid-ship's [Harness research of 2026-10-16](../../trials/2026-10-16-harness-native-features.md), done with Claude Code 2.1.287, Codex CLI 0.162.0 and agy 1.3.5, and from each vendor's documentation listed in section 9.4. The research marked several points unconfirmed; section 13.1 lists them.

### 9.1 What the brief may rely on in all three

1. **Project instructions in AGENTS.md.** Codex and agy read AGENTS.md. Claude Code reads it through the Kit's CLAUDE.md, which contains `@AGENTS.md`.
2. **Skills in `.agents/skills`.** Codex and agy read that directory; Claude Code reads the `.claude/skills` links.
3. **Parallel subagents.** The Lead can start several, wait for all of them, and return one summary. The brief states how the work is divided, that the Lead waits, and what the summary holds.
4. **A Reviewer as a separate subagent** with its own context.
5. **Hooks that deny a tool call,** which carry the Harness guardrails and the merge guard where the Kit wires them: in Claude Code, and in Codex or agy only once their wiring lands (Spec 1). Whether Codex's and agy's hooks also fire inside subagents and headless Sessions is unconfirmed until the hook spike, backlog item PRO-139 (section 9.2).
6. **Headless entry points** for starting a Session of the same Harness: `claude -p`, `codex exec` and `codex review`, and `agy -p`.

### 9.2 What the brief must not assume

| | Claude Code | Codex CLI | agy |
| --- | --- | --- | --- |
| Model per subagent | An alias or full ID on each spawn. With `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable overrides it | Any model of the parent's Provider, on each spawn | Only `inherit`, `flash` or `pro`. An exact slug applies to the whole Session |
| Subagents inherit the project's instructions | Documented: CLAUDE.md, settings hooks and permissions | Only the sandbox and approval settings are documented | Only permissions, command prefixes and the sandbox are documented |
| Settings hooks fire inside subagents | Documented | Unconfirmed until the hook spike (PRO-139) | Unconfirmed until the hook spike (PRO-139) |
| A worktree per subagent | `isolation: worktree`, branched from the default branch | Unconfirmed; `codex --worktree` covers a whole Session | A `branch` workspace mode; how to request it is unconfirmed |
| Native review command | `/code-review` | `/review` and `codex review` | None |
| Parallel limits | 20 concurrent subagents by default, nested 3 deep | Set by `agents.max_concurrent_threads_per_session`. The docs caution against parallel write-heavy work | None documented; nesting capped at 10 |
| Headless approvals | Fail without allow rules | An action that needs a new approval fails, and the error returns to the parent | Soft-denied, and the process still exits 0 |

The brief therefore:

- Restates the task, the worktree, the branch, the forbidden actions and the report format in every spawn prompt.
- Has the Lead create each Worker's worktree with `git worktree add`, unless its Harness isolates subagents natively. A worktree isolates files only, not processes, credentials or ports.
- Says "wait for every Worker" rather than "run in the foreground". In Claude Code's fork mode, the default in interactive Sessions since v2.1.232, subagents always run in the background.
- Treats a native review command as an extra input to a Reviewer, never as a substitute for `rs-review`. Claude Code's `/code-review` follows CLAUDE.md, but it does not produce the verdict format of section 3.6.
- Never requires an experimental, interactive-only or paid-only feature: Claude Code's agent teams, dynamic workflows, agent view, routines and `/code-review ultra`; agy's `/boost` and `/teamwork-preview`; Codex's `codex app-server`. Codex removed `codex mcp-server` in 0.154.0.
- Asks for a Lead started from a clean checkout at `origin/<default branch>`, on any branch, because a Claude Code subagent in its own worktree takes its instruction files from the main conversation, not from its worktree.
- Starts every Reviewer in a checkout of the base branch, so the Reviewer runs under the base branch's instructions and hooks, never under those of the change it reviews.
- Never claims that the Harness will follow it, or which model a subagent received. rapid-ship cannot see either. CI and any ruleset hold regardless.

### 9.3 Other Harnesses and desktop apps

rapid-ship supports any Harness, including API-backed ones such as pi. Any Harness other than the three gets AGENTS.md, `.agents/skills`, the pre-commit hook and CI from the Kit, but no guardrail settings, as Codex and agy do until their wiring lands (Spec 1). A brief for it relies only on the points of section 9.1 that its vendor documents. pi, for example, has no built-in subagents, so a pi Lead follows `rs-work` itself and starts its Reviewer as a new headless pi Session from its shell. Claude's desktop app reads the same settings files as the CLI, so a Claude Code brief applies there. The Codex desktop app shares the CLI's skill loader; whether it reads every location the CLI reads is unconfirmed.

### 9.4 Sources

Harness behaviour (section 9 and the warnings in section 6.4), read on 2026-10-16:

- Claude Code: [subagents](https://code.claude.com/docs/en/sub-agents), [agents](https://code.claude.com/docs/en/agents), [headless mode](https://code.claude.com/docs/en/headless), [memory and AGENTS.md](https://code.claude.com/docs/en/memory), [hooks](https://code.claude.com/docs/en/hooks), [worktrees](https://code.claude.com/docs/en/worktrees), [skills](https://code.claude.com/docs/en/skills), [desktop](https://code.claude.com/docs/en/desktop), [local code review](https://code.claude.com/docs/en/code-review-local.md).
- Codex: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents.md), [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode.md), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md.md), [hooks](https://learn.chatgpt.com/docs/hooks.md), [code review](https://learn.chatgpt.com/docs/code-review.md), [skills](https://learn.chatgpt.com/docs/build-skills), [MCP server removal](https://learn.chatgpt.com/docs/mcp-server.md).
- agy: [subagents](https://antigravity.google/docs/subagents?tab=cli), [headless](https://antigravity.google/docs/cli/headless), [models](https://antigravity.google/docs/models), [rules](https://antigravity.google/docs/rules), [skills](https://antigravity.google/docs/skills), [permissions](https://antigravity.google/docs/permissions), [sandbox](https://antigravity.google/docs/sandbox), [hooks](https://antigravity.google/docs/hooks).
- pi: [README](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md).

Forked skills: [mattpocock/skills at `49dd158`](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336): `grilling`, `domain-modeling`, `to-spec`, `to-tickets`, `implement` and `code-review`.

## 10. This repository's own configuration

*This section describes this repository's own configuration, not product behaviour.* rapid-ship validates these skills on itself and on its sample project, hello-rapid-ship.

- **Tracker:** Linear, team PRO, with one project per product: "rapid-ship" and "hello-rapid-ship". Parent issues with sub-issues are already in use (PRO-99). Neither project has milestones yet, so the first `rs-breakdown` run creates them. Maintainers connect Linear through its official MCP server or API, never a third-party CLI.
- **Reviewers:** agy is never a Reviewer in this repository. That is the owner's judgement for this repository, not a product rule.
- **Sign-ins:** this repository's agents sign in with vendor subscriptions only. Its root AGENTS.md states the rule.

## 11. What changed on 2026-10-16, 2026-10-19 and 2026-10-20

The owner's reviews of PR #27 on 2026-10-16, 2026-10-19 and 2026-10-20, and the decision of 2026-10-20 to descope running agents across several Providers (Spec 1, section 1), settled what this spec states. The open questions are in section 13.

## 12. Testing

The skills are instructions, so most of their validation is dog-fooding: real runs on this repository and on hello-rapid-ship, recorded under `docs/trials/`. A simulated run never counts as a trial. The deterministic parts get offline tests.

### Offline tests

- devctl's settings loader: valid `[tracker]` and `[design]` tables load, with any keys under `[tracker.<name>]`. An unknown key or a wrong type in either makes the settings unreadable, and `devctl check` reports a blocked step.
- Spec 1's map rule for skills covers the front matter and `.claude/skills` links of the five skills. Spec 1's upstream lock test covers the forked files.
- Every link inside the five skills resolves to a file in the skill.

### Dog-food trials

| Skill | Trial | It passes when |
| --- | --- | --- |
| `rs-design` | On hello-rapid-ship, design one small feature from a one-line idea. On rapid-ship, design the next feature the owner picks | Every question carried a recommended answer, the owner made every decision, the spec follows the template, and an ADR exists only for a real trade-off. The owner judges the result |
| `rs-breakdown` | Break the hello-rapid-ship design into one milestone in its tracker project. On rapid-ship, break down Spec 3 for its plan | Every task has the template's sections and native blocked-by links, the frontier holds at least two independent tasks, and every resulting pull request stays within the diff cap without an `Over the diff cap:` declaration |
| `rs-lead` | Start a Lead with the brief in Claude Code, in Codex and in agy, on hello-rapid-ship in Walk, and once from a worktree on another branch. Once, make `project.toml` unreadable first | The brief has every template section, claims nothing section 9 rules out, and gives each warning of section 6.4 that applies. With unreadable settings, `rs-lead` stops at its first step and names the problem doctor reported |
| `rs-work` | A Worker on each Harness implements a task. The seeded tasks include one too large for the diff cap and one that requires removing a test | A failing test precedes its code in the branch's history; `devctl check` passed before the pull request opened; the body carries Evidence, `Not covered:` and the declared removal; the oversized task stopped as `blocked` |
| `rs-review` | Review hello-rapid-ship pull requests with seeded defects: a missed acceptance criterion, a test that cannot fail, a Pattern bypass and a naming nit. Add one pull request that also weakens `rs-review`'s own text. Run once with Agent identity and once without | The first three are blocking with a plausible rung and the naming issue is a nit; the Reviewer ran in a checkout of the base branch and judged the weakened skill by the base version; there is one verdict per head; with Agent identity it is a real review from the Reviewer App, without it a `COMMENT` review; the next Reviewer resolves exactly the threads it verified |
| Flight help | On hello-rapid-ship with Agent identity, the pull request that sets `every_pr = false` and narrows CODEOWNERS | After it merges, the Lead merges a pull request outside the escalation list as the Worker App, GitHub refuses a Protected pull request without the owner's approval, the merge guard denies the Lead's merge of a Protected pull request, of one whose head failed `devctl check` and of one whose head the Reviewer App has not approved, and the guardrails deny `gh pr merge --admin`. Without Agent identity, `rs-lead`'s explanation is recorded and the ruleset is left unchanged |

The trials on Linear also confirm the facts the mapping note relies on: the integration's moves on open and on merge, no move on a close without merging, and a cancelled issue closing its linked pull requests. `./devctl doctor --skills` lists the five skills in Claude Code.

Each `rs-lead` trial also records what the Lead did: a worktree per Worker, every Worker awaited, a fresh Reviewer per head in a checkout of the base branch, nits skipped, blocking findings fixed, escalation at the round limit, and in-session Corrections appended. These observations improve the brief's wording and are never a pass or a fail of rapid-ship, because adherence is the Harness's.

## 13. Open items

### 13.1 Facts that the spike and the trials confirm

The owner decided how each of these is settled. Only the result is pending.

1. **Codex and agy hooks.** Whether their hooks fire inside subagents and headless Sessions, and whether Codex hooks can ask. The hook spike, backlog item PRO-139, settles this as the first task of Spec 1's plan 5, and its report decides whether a follow-up wires each. Until a Harness's wiring lands, section 6.4's warning for a Harness without Kit wiring applies to it.
2. **Other Harness facts** from section 9.2: whether Codex and agy subagents receive the AGENTS.md chain, whether Codex can give a subagent its own worktree, and how agy requests its `branch` mode. The `rs-lead` trials settle them.
3. **Codex Workers in a linked worktree.** The withdrawn Walk-flow draft recorded that Codex's `workspace-write` sandbox cannot commit in a linked worktree on macOS. If the trial shows that this still holds, it decides between the Lead committing for the Worker and the owner choosing another sandbox.
4. **The ruleset's approval count in Flight with Agent identity.** Required approvals stay at 1 until the live trial shows whether GitHub counts the Reviewer App's approval (section 6.5, and Spec 1).
5. **Linear's GitHub integration:** its moves on open and on merge, no move on a close without merging, and a cancelled issue closing its linked pull requests (section 12).

### 13.2 Left open by the owner

None.
