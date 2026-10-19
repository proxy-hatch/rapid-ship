# rapid-ship design

*Revised on 2026-10-16 to stop at the team-management boundary ([ADR 0004](../../adr/0004-team-management-boundary.md)), and on 2026-10-19 after the owner's second review. Replaces the 2026-10-10 framework design. Terms follow `GLOSSARY.md` at the repository root.*

## The problem

Coding agents can now finish most well-specified tasks, and every major Harness can run a team of them: a lead Session starts subagents, runs them in parallel and collects their results. What no Harness supplies is what a senior engineer gives a team of people: an architecture to build into, delivery broken into small tasks, and a code-quality bar held on every change. Models may learn to slice work well on their own; today they often slice it too large, and the large changes cause bugs. Left alone, agents also take shortcuts: they weaken a test, edit the CI that judges them, or repeat a mistake they were corrected for the day before.

rapid-ship supplies those three things to a repository and to whichever Harness the owner works in. The approach follows the owner's *Trust-First Agentic Engineering Playbook*: enforce each rule at the layer that fits its purpose, turn every repeated correction into a rule that prevents it, and widen autonomy as measured results support it, which the owner judges.

## The boundary

rapid-ship does for a team of coding agents what a senior engineer does for a team of people. It does not run the team ([ADR 0004](../../adr/0004-team-management-boundary.md)).

| rapid-ship | The owner's Harness |
| --- | --- |
| Helps write ARCHITECTURE.md, ADRs and feature designs, and breaks a design down in the owner's issue tracker | Starts, watches, resumes and hands over Sessions |
| Installs the Kit: devctl, instructions, starter Patterns, guardrails and skills | Runs Workers and Reviewers as subagents or as other vendors' CLIs |
| Helps the owner write the Lead brief | Follows the Lead brief as closely as it can, including each subagent's model |
| Reports metrics and Suggested threshold breaches, and reviews readiness for Flight with the owner | Pushes, opens PRs, posts reviews and merges, within the guardrails and the ruleset |
| Records Corrections and finds drift through [gardening](#gardening) | Reaches the tracker and other tools through its MCP servers or CLIs |

rapid-ship never pushes, reviews or merges as a step in a flow, and never moves a project between Modes. devctl never talks to the issue tracker. rapid-ship runs no service, daemon, container or local database: it is files in the repository, plus a small command that writes them. It works with any Harness, including API-backed ones such as pi, and with any Provider, whether a subscription, an API key or a gateway. Nothing it ships needs an API key. It works with GitHub today, through `gh`. Other Git hosts, such as Bitbucket, may follow if owners ask for them or contribute them.

## Who does what

The **owner** designs with rapid-ship's help, chooses the Mode, and decides on every PR the escalation list brings them.

The **Lead** is the Session the owner works with. At the start of a Session the owner runs `rs-lead`. It runs `./devctl doctor` first, then builds the **Lead brief** from `.rapid-ship/project.toml` and from what the owner wants done now:

- The **Focus** says what to work on now: a milestone or chosen tasks. It changes often and is never stored.
- The **escalation list** names the kinds of PR the Lead must bring to the owner instead of merging them itself. It sets the [Mode](#modes).
- The optional **Roster** names the Agent, a Harness and an exact model, for each role. Any Harness can fill a role: Claude Code, Codex and agy come with built-in headless command templates, and for another, such as pi, the owner supplies one. Only an owner who uses more than one Provider needs a Roster; otherwise the Lead's Harness chooses its subagents' models.

The escalation list and the Roster live in `project.toml`, which is in the Protected set, so changing the Mode or the Roster is a PR the owner approves. How closely the Lead follows the brief, including using each model exactly as named, is up to its Harness. rapid-ship cannot see which model a subagent received, so "no silent model fallback" is advice.

The **Worker** and the **Reviewer** are roles the Lead's Harness runs. A Worker implements one task by following `rs-work`. A Reviewer judges one change by following `rs-review` and tags each finding blocking or nit, with the rung that would stop it recurring. A Reviewer starts in a checkout of the base branch and reads the change only through git, so the PR under review cannot change the instructions or hooks it runs under. The Lead tells a generic subagent to follow the skill, or follows it itself. A Reviewer from a different Provider than the Worker is recommended.

No Harness runs another vendor's model as a native subagent. A Roster that crosses Providers has three routes. The Lead can run the other Harness's headless command from its shell, such as `codex exec`, `agy -p`, `claude -p` or the template the owner supplied. It never passes `claude -p` the `--bare` flag, because bare mode would skip the Kit's hooks and CLAUDE.md. It can use OpenAI's official Codex plugin for Claude Code. Or it can use agy's catalog of Claude and GPT-OSS models. When `rs-lead` offers to run agy from another Harness's shell, it warns that Google's consumer terms do not support that use.

The skills describe how a Lead runs a task, and rapid-ship runs none of it. The Lead starts a Worker for each task in the Focus whose blockers are done. The Worker works test-first, runs `./devctl check` before it reports done, and opens a PR, and CI runs the check in full. A Reviewer posts its findings on the PR, and the Lead sends each blocking finding back to a Worker until none is left. The Lead then brings the PR to the owner if its kind is on the escalation list, and merges it otherwise.

rapid-ship takes no notice of how many Sessions or Workers run at once, and sets no cap. In Walk the owner launches the Sessions and watches them, with the Workers they start, so the documentation advises running at most 3 Workers at once, for the owner's cognitive load.

## Design and Breakdown

`rs-design` interviews the owner first, then writes a spec. It maintains ARCHITECTURE.md and the ADRs, which live in the repository. Feature designs live wherever the owner keeps them: in the tracker's documents or in the repository.

`rs-breakdown` turns a design into four levels. Breakdown happens whenever there is new work, in either Mode.

| Level | What it is |
| --- | --- |
| Milestone | A dated delivery checkpoint that can be demonstrated: the unit of work the owner hands a Lead |
| Epic | One capability inside a milestone, delivered in several PRs. It links to its spec |
| Story | Optional: a user-visible slice of an epic, used only when the epic ships in more than one slice |
| Task | Exactly one PR, small enough for one review and within devctl's 1,500-line diff cap, with acceptance criteria, a test plan and blocked-by links, so a Lead can run independent tasks in parallel |

`rs-breakdown` keeps tasks small because agents that slice work themselves still make the pieces too large.

The levels are tracker-neutral, and rapid-ship supports whichever tracker the owner uses. The skills reach it through the Harness's own connection, an MCP server or a CLI. Each tracker gets one mapping note. Linear's is first: one Linear project per product, a milestone as a project milestone, an epic as a parent issue, a story as a sub-issue, and a task as a leaf issue with "blocked by" relations.

## Standards

The Kit gives each area that rapid-ship touches a base to build on, so a newly onboarded project starts from it. `rs-setup` establishes the standards with the owner in a new repository. In an existing one, `rs-health` audits them and turns its findings into a standards milestone that a Lead works through; it never edits the repository itself.

- **Instructions:** AGENTS.md files, one per maintained directory, are the single instruction source. A real `CLAUDE.md` contains `@AGENTS.md`.
- **README.md and ARCHITECTURE.md:** the Kit seeds skeletons, and `devctl check` verifies that they and their links exist.
- **Stacks:** the Kit supports Python and TypeScript, the latter for React with room for tools such as Tailwind. The TypeScript stack checks with ESLint, Prettier, `tsc --noEmit`, Vitest and `npm audit`, and uses npm as its package manager. A repository can hold several stacks, such as a Python backend in `backend/` and a TypeScript frontend in `frontend/`. The Kit stays at the root, `project.toml` lists each stack with its directory, and `devctl check` runs each stack's steps in that directory.
- **Linters, static analysers and profilers:** each stack's linters, formatters, type checkers and other static analysers, with their settings, which `devctl check` runs; and a profiler for finding slow code ([Open](#open)).
- **Settings files:** every settings file the Kit ships documents its keys briefly inline and is validated, by devctl or by the tool that reads it: allowed keys, numeric ranges and enums.
- **Patterns:** the Kit seeds a starter Pattern set for each stack, which the project then owns and adapts. It covers error handling (fail fast, fail gracefully, and never hide or obscure an error), configuration (typed, validated and documented, with numeric ranges, enums and short inline docs), and input validation with typed enums rather than strings. A Pattern file names the recurring task, its reference implementation and the check that enforces it. It also explains what the reference does right, so an agent learns the lesson and not only the location. `devctl check` verifies that the reference and the check exist. In a new repository `rs-setup` adapts the starter set with the owner. In an existing one, `rs-health` finds recurring tasks done several ways and proposes one reference for each. Agents may add a Pattern; changing an existing one needs the owner.
- **Feature map:** one file per feature says where it is entered, what data it touches, and how to observe and reproduce it.

When `rs-setup` adopts an existing repository, it compares the project's own linter, type-checker and formatter settings with the Kit's. It ignores purely stylistic differences, such as line width. At the end of Setup it offers the meaningful rules the project lacks as a separate PR, which merges them into the project's settings and runs the linters with them.

Throughout, rapid-ship prefers guided rectifying to a bare exit: when a command or a check stops, it explains the problem and the fix. It still fails fast and never hides or obscures an error.

## How the bar is held

Every rule sits on one of four rungs. A rule goes on the rung that fits its purpose, and one bad pattern can need more than one rung.

| Rung | What it is | Example |
| --- | --- | --- |
| 1. Safe interfaces | One supported way to do a recurring task, with the bypass banned | Configuration is read only through `settings`; `os.environ` is banned elsewhere |
| 2. Automated checks | `devctl check`, required in CI | Lint, types, static analysis, tests, import contracts, the diff policy |
| 3. Judgement | Skills, advisory Rules and the Reviewer | "Prefer deep modules with small interfaces" |
| 4. The owner | Human approval | Changes to CI, guardrails, skills or settings |

A safe interface removes a structural way to misuse something. A check catches local or stylistic problems, such as line length or `Any` in weakly typed code. The two often work together: in rung 1's example, `settings` is the interface and a lint rule bans the bypass. Skills and advisory Rules are the fallback for what no interface or check can carry.

`devctl check` covers everything a machine can decide without a model, so CI stays deterministic and needs no model sign-in. Beyond lint, types and tests, it confirms that the instructions, README.md, ARCHITECTURE.md, the feature map and the Patterns exist and that their links resolve. Its diff policy fails a change that quietly deletes a test or turns an assertion into a tautology; every removed test is declared in the PR. Its diff cap fails a change of more than 1,500 added and removed lines, unless the PR declares `Over the diff cap:` with a reason. The count leaves out `.md`, `.txt` and `.log` files, binary files, lock files and Kit-managed files. There are no ratchets: an unsafe pattern is prohibited outright, and a legitimate exception is an entry in an exceptions file that only the owner can approve.

**Harness guardrails** bring the rungs into each Harness's own loop. One devctl command, `devctl hook`, holds every rule, and the Kit's seeded settings for Claude Code, Codex and agy connect it to each Harness's hook events. It denies `--no-verify`, force pushes, `gh pr merge --admin`, a `git push` to the default branch, the merges, ref writes and commits through `gh api` that Spec 1 lists, and hand edits to `.rapid-ship/kit.lock`. It asks before an edit to the Protected set. These settings files join the Protected set. No hook runs `devctl check` when an agent stops, because that is too heavy: the pre-commit hook and CI run it, and `rs-work` tells a Worker to run it before reporting done.

**The merge guard** is a rule of `devctl hook`, on in every setup, in each Harness whose hooks run `devctl hook`. It denies an agent's `gh pr merge` when `devctl check` has not passed on the PR's head commit, when the PR touches the Protected set, or when the running guard cannot check it. With or without Agent identity, the guardrails deny the other ways to land a change on the default branch that the hook recognises: `gh pr merge --admin`; a `git push` to the default branch; through `gh api`, a REST merge of a PR or a branch, a write to the default branch's ref, or a commit through the Contents API; and the GraphQL mutations that merge, enable auto-merge, queue a merge, update a ref or commit to a branch. [Spec 1](2026-10-14-kit-and-setup-design.md#the-merge-guard) lists each form. `gh pr merge` is then the only recognised way for an agent to merge, and the guard checks it. The hook reads GitHub only for `gh pr merge`, so other tool calls make no GitHub request for it. It matches command lines, so a misbehaving agent can get past it, for example through a script or a tool the hook does not see, such as an MCP server's merge tool. The owner merges a Protected-set PR in GitHub's web interface.

When one of its rules fails, `devctl hook` lets the call through, so a bug in a rule never stops work; only the merge guard denies a merge it cannot check. That holds only once the hook runs and has parsed the event, and Spec 1 documents the hook's exit codes as a workaround for the Harnesses' hook protocols. In Claude Code, the call goes through, a merge included, when `uv` is missing, Python fails while loading devctl, the hook cannot parse the event, or Claude Code kills the hook at its hook timeout. When uv itself fails, it exits 2, which Claude Code reads as block, so every wired call stops until the setup is fixed. While the hook cannot read its settings, it still denies what needs no settings and the merge guard still works, but it no longer asks before Protected edits or applies Agent identity's denies. The `./devctl doctor` run that `rs-lead` makes at the start of each Session is what catches a broken setup: it starts devctl the same way as the hook, so a uv or Python failure stops it too, and it reports settings it cannot read and wiring that lacks the Kit's hooks. The seeded root AGENTS.md asks other Sessions for a settings-only check (a proposal in Spec 1). The design relies on the guardrails in Claude Code, whose hooks also fire inside subagents. For Codex and agy they stay unconfirmed until a spike, the first task of plan 5 (backlog item PRO-139), and until then `rs-lead` warns that a Codex or agy Worker may run without them. Sandboxing is a recommendation that `rs-setup` offers, not a default, because subagents inherit the sandbox of the owner's own Session. Any other Harness, such as pi, gets AGENTS.md, `.agents/skills`, the pre-commit hook and CI, but no guardrails, so the merge guard does not run there. The pre-commit hook, CI and any ruleset still hold, and `rs-lead` and `rs-preflight` say so. Supporting another Harness takes one more template layer.

The **Protected set** is the kinds of change that need the owner's approval in every Mode. It covers changes to CI and the guardrail settings, devctl, the skills and the other agent instructions, rapid-ship's settings and exceptions, the check tools' settings files, an existing Pattern, and an existing entry in the Corrections ledger. It holds in every setup: the merge guard denies an agent's merge of a Protected-set PR, and with Agent identity and a ruleset, GitHub also requires the owner's approval through CODEOWNERS. GitHub reads CODEOWNERS from the base branch, so a PR cannot exempt itself there.

**GitHub gates merges where it offers rulesets**: on public repositories, and on private ones with a paid plan. One ruleset on the default branch requires a PR with code-owner review, every review thread resolved, and a passing `devctl check` reported by GitHub Actions. It allows squash merges only and blocks force pushes. Only the repository admin role may bypass it, and only when merging a PR. `rs-setup` applies it and `devctl doctor` checks it. A GitHub Free private repository has no rulesets, so there the merge guard is the enforcement: it rejects an agent's merge while `devctl check` has not passed on the PR's head. The guardrails also deny an agent's `git push` to the default branch, which a repository without a ruleset would accept.

**Agent identity** is optional ([ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md)). `rapid-ship app` creates two GitHub Apps: one opens and merges PRs, the other posts reviews. With it on, agents make their GitHub writes through `devctl as`, one thin command that runs `gh` and `git push` with an App's short-lived token. The Harness guardrails then deny `git push` and `gh` writes made as the owner. GitHub never lets a PR's author approve or request changes on it, on any plan, so Agent identity buys four things:

1. The owner can formally approve agent PRs, so merges need no admin bypass. In a team, teammates' approvals cover this without it.
2. Reviewer verdicts are real GitHub reviews, so Revisions can be counted.
3. Agent PRs can be told apart, which every per-agent-PR metric needs.
4. CODEOWNERS binds the Lead in Flight while the Lead acts through `devctl as`, because an App cannot use the owner's bypass.

Without it, agents act as the owner. Agent identity matters most for a solo owner on GitHub Free with a public repository: GitHub enforces the ruleset there, the owner cannot approve a PR their own account opened, and every agent comment appears publicly as the owner's. `rs-setup` gives this advice, and the owner opts in or not:

| Setup | Agent identity | Why |
| --- | --- | --- |
| Solo owner, public repository or paid plan | Recommended | It is the only way the owner can approve agent PRs, and GitHub binds the Lead |
| Solo owner, GitHub Free private repository | Recommended, for real reviews and metrics | There is no ruleset, so the merge guard holds the bar with or without it |
| Team | Optional | Teammates approve agent PRs anyway. The Apps add per-agent metrics, real Reviewer reviews and a Lead that CODEOWNERS binds in Flight |

A team shares one Worker App and one Reviewer App per repository owner. For an organisation, an admin creates them once (backlog item PRO-105). Each developer holds their own private key for each App, since GitHub allows up to 25 keys per App, and keeps it in their own Keychain, so one person's key can be revoked alone. For an organisation's Apps, the admin makes each developer an App manager of both, and each generates their own key. For Apps a personal account owns, the account owner generates one key for each collaborator and hands it over securely, or moves the Apps to an organisation. These key steps are not yet verified ([Open](#open)). A pair of Apps for each developer was rejected: it multiplies installations and splits one role's reviews across identities.

One limit is worth stating plainly. Agents run on the owner's machine under the owner's sign-ins, with both App keys within reach, and a misbehaving agent can bypass any guardrail, the merge guard included. It could then act as the owner, with or without Agent identity. Guardrails stop habits and mistakes, not a determined agent. The owner accepts this in every Mode, Flight included ([ADR 0004](../../adr/0004-team-management-boundary.md)).

## Modes

The Mode is the owner's choice, set by the escalation list. In **Walk** every PR is on it. In **Flight** only the Protected set and the kinds the owner adds are on it, such as migrations or public API changes; the Lead merges everything else once its checks and review pass. Anything between is allowed. In every Mode, three kinds go to the owner by default: a PR that removes a behavioural test, a PR that declares `Over the diff cap:`, and a PR that reached 3 Revision rounds.

The merge guard enforces the Protected set in every Mode, and GitHub does too through CODEOWNERS with Agent identity and a ruleset. The kinds the owner adds are advice to the Lead, because CODEOWNERS and the merge guard recognise a change only by the paths it touches. `rs-lead` writes the escalation list into `project.toml` and proposes the matching CODEOWNERS change as a Protected PR. With Agent identity, CODEOWNERS `*` enforces Walk, and Flight narrows CODEOWNERS to the Protected set. Without it, an agent's PR comes from the owner's account, so under a ruleset a solo owner can merge it only through the admin bypass. The guardrails deny the Lead `gh pr merge --admin` and the other recognised ways to land a change on the default branch, and the merge guard denies its merge of a red or Protected-set PR. Flight is still available without Agent identity: the ruleset must then drop its review requirement so that the Lead can merge, and the merge guard holds the Protected set. `rs-lead` explains this; the owner decides and changes the repository setting.

When to fly is the owner's call, made from the metrics. rapid-ship has no gate into Flight and never returns a project to Walk. It helps the owner fly in three ways:

1. **Which PRs reach the owner.** A shorter escalation list in the Lead brief speeds up delivery.
2. **Which review findings trigger another round.** The Lead always fixes blocking findings and skips nits, which upholds quality and maintainability without endless rounds. These triage rules live in the text of `rs-review` and `rs-lead`, not in settings.
3. **Pre-flight.** Before the owner widens the Mode toward Flight, `rs-preflight` reviews the project's readiness with them, like an operational-readiness review before a release. It covers the metrics to watch, the Alarms and incident integrations this project needs, scheduled [gardening](#gardening), the escalation list, and the status of Agent identity and the ruleset. It advises, and never gates or changes the Mode.

## Metrics

rapid-ship provides a basic set of metrics that a project can extend. Each comes deterministically from GitHub and git, with no model and no attribution step.

| Metric | Without Agent identity |
| --- | --- |
| Revisions per merged agent PR | Unknown |
| Reverts: merged PRs that a later commit reverted, in whole or, where it can be detected, in part | Counted over all PRs |
| Red default-branch CI after a merge | Counted over all PRs |
| Agent PRs the owner closed unmerged | Counted over all PRs |
| Corrections by rung, from the Corrections ledger | Counted |

The owner reads them with `devctl metrics`, or from an optional scheduled GitHub Action that posts the same report. Without Agent identity, a metric that must tell agents from the owner reports "unknown: needs Agent identity". No metric relies on markers that agents set on their own work. Corrections are the one agent-reported metric: agents write the ledger entries, so the count is only as complete as their records, and the owner signs off on what happens to each. A missing metric is unknown, never zero.

The owner records **Suggested thresholds** at Setup. rapid-ship reports a breach and takes no action.

The signals that matter most for Flight, such as Alarms, incident reports and deploy rollbacks, depend on how each project and team runs its software. rapid-ship cannot measure them for everyone, so it guides the owner through setting them up, in `rs-setup` and again in Pre-flight. Each plugs in as a project-defined metric, and incidents also feed gardening as Corrections.

## Gardening

Gardening is rapid-ship's name for the regular upkeep of a codebase that agents work in. Agents repeat mistakes they were corrected for, and instructions, documents and code drift apart as the code changes. Small, regular passes keep both in check, as weeding keeps a garden. Each pass records what was corrected, finds what drifted, and proposes a rule that prevents each repeated Correction. The `rs-garden` skill runs a pass. This section is gardening's reference until the documentation site gives it a page of its own.

A pass covers two things:

- **Corrections**, from three sources:
  - the review threads on PRs, from the Reviewer and the owner. A model reads the threads, so this works without Agent identity;
  - Corrections the owner gives in a Session, which the Lead brief asks the Lead to add to the ledger; that part is advisory;
  - incidents, such as metric Alarms and incident reports, traced to a change. Each project connects these differently, and rapid-ship guides the owner to connect them where the Harness can reach them.
- **Drift**: a stale AGENTS.md, ARCHITECTURE.md or README.md, code that departs from its Pattern, exceptions nothing uses, and dead code. "Fail fast, fail gracefully, never obscure an error" is a base rule of every pass, so it also looks for code that hides or obscures an error.

Agents may add entries to the Corrections ledger. Changing or removing an existing entry, or its status, is a Protected change, so the owner signs off on what happens to each Correction.

The gardener shares one audit with `rs-health`, which runs it once at adoption. The gardener reruns it over the changes since its last pass and adds the new Corrections. For each repeated Correction, and for a severe first one such as a security finding, it proposes a fix on the rung that fits: a safe interface for structural misuse, a check for local or stylistic problems, or both; a skill or advisory Rule only when neither can carry it. Rule changes come back as proposed tasks. Doc-only drift fixes come back as one PR per pass.

`rs-garden` is a skill the owner runs. rapid-ship advises running it on a schedule; how to schedule it is the owner's choice.

## What rapid-ship ships

- **The `rapid-ship` command** writes and updates the Kit. `init` vendors it, `status` compares the repository with the Kit lock, `sync` proposes Kit updates as a PR, and `app` creates the Apps for Agent identity. When a Kit update changes what a seeded file must contain, `sync` proposes the migration edits in a PR of their own and never edits that file silently; where it is cheap, a new rule only warns for one Kit version first. `uvx` fetches the command from a git tag of this repository; it is not on PyPI yet. `rs-setup`, not a command, marks an existing project's suppressions.
- **The Kit** is what `init` vendors: devctl's source, the instruction and document skeletons, the Pattern and feature-map formats, a starter Pattern set for each stack, the Harness guardrail settings, a pre-commit hook, a CI workflow, CODEOWNERS, the `.rapid-ship/` settings and the skills. `init` records each file as managed, which `sync` keeps current, or seeded, which the project owns from the start. A managed file the project edits becomes its own until `rapid-ship sync --revert`.
- **devctl** is the repository's own CLI for people, agents and CI. Its commands are `check`, `doctor` and `metrics`, plus `as`, the thin command for `gh` and `git push` under Agent identity, and `hook`, which holds the Harness guardrails and the merge guard. `doctor` reports what the machine and repository lack, including settings it cannot read. `doctor --skills` asks each Harness which Kit skills it loads, and doctor checks the Apps only under Agent identity. A project adds its own verbs.

Nine skills, from `rs-setup` to `rs-preflight`, carry the work. The Kit also ships seven engineering skills: `rs-tdd` and `rs-diagnosing-bugs`, forked for TDD and debugging, and `rs-codebase-design`, `rs-pr`, `rs-writing-for-agents`, `rs-writing` and `rs-ponytail`. Every Kit skill's name starts with `rs-`.

| Skill | What it does |
| --- | --- |
| `rs-setup` | Sets up a new repository or adopts an existing one: the Kit, the README, ARCHITECTURE and AGENTS documents, the starter Patterns, the Harness guardrails and the ruleset; optionally Agent identity and the metrics Action |
| `rs-health` | Audits a repository and returns a standards milestone |
| `rs-design` | Interviews the owner; writes feature designs, ADRs and ARCHITECTURE.md |
| `rs-breakdown` | Turns a design into milestones, epics, stories and tasks in the tracker |
| `rs-lead` | Builds the Lead brief, triages review findings and helps the owner fly |
| `rs-work` | How a Worker meets the bar on one task |
| `rs-review` | How a Reviewer judges one change |
| `rs-garden` | Records Corrections and finds drift |
| `rs-preflight` | Reviews readiness with the owner before the Mode widens toward Flight; it advises and never gates |

There is no metrics skill: `rs-setup` records the thresholds, `rs-preflight` reviews which metrics to watch, and project-defined metrics are documented.

Each skill is one real directory under `.agents/skills/<name>/`, which Codex and agy read. Claude Code, the only major agent that cannot ([skills layout research](../../trials/2026-10-16-skills-layout.md)), gets a relative symlink per skill, `.claude/skills/<name> -> ../../.agents/skills/<name>`, recorded in the Kit lock. `SKILL.md` itself is never a symlink, because Codex rejects one. opencode and Gemini CLI read both directories and warn about duplicates. `rs-work` and `rs-review` ship with no per-Harness subagent definitions. The owner's machine must run macOS for now, and `devctl check` also runs on Linux, as CI does. Windows is not supported yet, because git there can check the skill links out as plain files (backlog item PRO-104).

## Dog-fooding

*This section describes this repository's own configuration, not product behaviour.* rapid-ship vendors its own Kit and is validated on itself and on its sample project, hello-rapid-ship. It is a public repository on GitHub Free with one owner, the setup where Agent identity matters most, so it is turning Agent identity on in PR #33. The owner created both Apps on 2026-10-19; installing them, recording them and confirming them with `./devctl doctor` are pending Owner steps of plan 4. It records its own choices as rules in its root AGENTS.md: Linear is its tracker; its agents sign in with vendor subscriptions only, and the owner accepts the risk of running agy inside another Session ([ADR 0001](../../adr/0001-subscription-logins-only.md)); and agy is never a Reviewer here.

## Delivery

Three specs:

1. **[Kit and Setup](2026-10-14-kit-and-setup-design.md):** the `rapid-ship` command; `devctl check`, `doctor`, `as` and `hook`; the Harness guardrails and the merge guard; the README and ARCHITECTURE seeds; the starter Patterns; the Python and TypeScript stacks; optional Agent identity; `rs-setup` and `rs-health`. The [plan index](../plans/2026-10-14-kit-and-setup.md) lists its seven plans:
   - Plans 1 to 3 built `init`, `status`, `sync` and `devctl check`.
   - Plan 4, doctor and Agent identity, is built in PRs #31 to #33, not yet merged.
   - Plan 5, Kit standards and Harness guardrails, starts with a spike that checks whether the Codex and agy hooks fire, including inside subagents (backlog item PRO-139).
   - Plan 6 adds the TypeScript stack and several stacks in one repository, which brings part of backlog item PRO-108 into scope.
   - Plan 7 builds `rs-setup` and `rs-health`, which need to know the stacks.
2. **[Delivery skills](2026-10-16-delivery-skills-design.md):** `rs-design`, `rs-breakdown`, `rs-lead`, `rs-work`, `rs-review` and the tracker mapping notes.
3. **[Metrics and gardening](2026-10-16-metrics-and-gardening-design.md):** `devctl metrics`, the scheduled Action, Suggested thresholds, project-defined metrics, the Corrections ledger, `rs-garden` and `rs-preflight`.

Specs 2 and 3 get their own plans later. Deferred until the product works: the rest of monorepo support (PRO-108), shared Apps for organisations (PRO-105), Git hosts other than GitHub, mapping notes for other trackers, Windows, and rewriting the documentation site.

[ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) and [ADR 0004](../../adr/0004-team-management-boundary.md) record decisions with lasting trade-offs. [ADR 0001](../../adr/0001-subscription-logins-only.md) is this repository's own rule, and [ADR 0003](../../adr/0003-walk-on-bare-sessions-orchestrator-deferred.md) is superseded.

## Open

- **The ruleset's approval count with Agent identity in Flight.** It stays `1` until the live ruleset trial. If GitHub does not count the Reviewer App's approval, it becomes `0` with code-owner review still required, so CODEOWNERS alone decides who must approve. The trial decides, and Spec 1 records the result.
- **The Codex and agy guardrails.** Until plan 5's spike (PRO-139) confirms that their hooks fire, including inside subagents, the design claims the guardrails for Claude Code only.
- **Merge guard details (proposals).** [Spec 1](2026-10-14-kit-and-setup-design.md#11-questions) lists every merge guard proposal; these two change what holds.
  1. Walk without a ruleset. The guardrails keep the owner's bypass from the Lead, so under a ruleset Walk holds without Agent identity. On a repository without one, such as a GitHub Free private repository, a Lead in Walk could still merge a green, unprotected PR with `gh pr merge`. Proposal: while `every_pr = true`, the guard denies every agent merge.
  2. Where it reads the Protected set. GitHub reads CODEOWNERS from the base branch. Proposal: the guard reads it from the PR's base branch too, never from the PR's head, so a PR cannot exempt itself from the guard.
- **Keys for a shared App (PRO-105).** As built in plan 4, the Keychain holds one key per role on a machine, with no App owner or App ID in the item's name, and only `rapid-ship app` writes it, for Apps it creates. A developer with Apps of their own therefore cannot also hold an organisation App's key, and nothing imports a key generated in GitHub's App settings. The team design needs Keychain items keyed by App owner or App ID, and a command that imports a key. Proposal, not yet verified: for an organisation's Apps, the organisation admin makes each developer an App manager of both Apps, so each developer generates their own key and nobody else handles it. GitHub documents that App managers manage an App's settings, but not that this includes generating its private keys. The cost is that an App manager can also change the App's settings. GitHub offers App managers only to organisations, so for Apps a personal account owns, the account owner generates one key for each collaborator and hands it over securely, or moves the Apps to an organisation.
- **A profiler for each stack (proposal).** Standards name profilers, but no stack picks one yet. Proposal: Python names the standard library's `cProfile`, and TypeScript names Node's `--cpu-prof`. A Pattern for performance work documents each, and `devctl check` never runs one, because timings are not deterministic.

## What changed

**On 2026-10-16** the design moved to the team-management boundary. These parts were cut:

- `devctl dispatch`, `pr`, `review`, `merge` and `watch`; Claims, Release, Takeover, the Session registry and the gate log.
- The Lead's event loop (the Walk-flow draft), per-role sandboxed launches, `attempt_limit`, `review_round_limit` and the five-Worker cap.
- rapid-orchestrator, dropped rather than deferred.
- The Flight lease, automatic demotion, the Pre-flight gate, the attack-PR set and the Investigator. Rollbacks became a project-defined metric.
- Linear as the only tracker, subscription sign-ins as a product rule, Agent identity as a requirement, doctor's tracker item, and the test-bed spec.
- The activity "Plan" became Breakdown, and `rs-plan` and `rs-walk` gave way to `rs-breakdown` and `rs-lead`.

**On 2026-10-19**, after the owner's second review:

- The cap on parallel Workers left the Focus, the Lead brief and the settings. rapid-ship only advises at most 3 Workers at once in Walk.
- The Stop-hook check was dropped as too heavy. The merge guard joined `devctl hook`, so the Protected set and a passing `devctl check` hold at merge in every setup, and the guardrails deny the other ways the hook recognises to land a change on the default branch, a `git push` to it included.
- Pre-flight returned as `rs-preflight`, an advisory review that never gates.
- The Kit ships a starter Pattern set for each stack, not only the Pattern format. Spec 1 gained the TypeScript stack and several stacks in one repository as plan 6, and `rs-setup` and `rs-health` moved to plan 7.
- The diff cap became 1,500 lines, not counting `.md`, `.txt` and `.log` files, and a PR over it goes to the owner by default.
- A Roster may name any Harness, and a Reviewer starts from the base branch.
- Changing or removing a Corrections ledger entry became a Protected change.
- [ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) gained the advice on when to set up Agent identity and the team design, and [ADR 0004](../../adr/0004-team-management-boundary.md) records Flight's credential safeguards as rejected.
