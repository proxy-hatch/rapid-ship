# rapid-ship design

*Revised on 2026-10-16 to stop at the team-management boundary ([ADR 0004](../../adr/0004-team-management-boundary.md)), on 2026-10-19 after the owner's second review, on 2026-10-20, when the owner descoped running agents across several Providers, had plan 5 wire the Harness guardrails for Claude Code alone, and had `doctor --skills` probe Claude Code alone, on 2026-10-25, when the owner decided that the Kit keeps no backward compatibility before GA, and on 2026-10-26, when the owner descoped Spec 2's delivery skills and chose to start and manage their own Sessions, had the merge guard enforce each Mode, and made Spec 3 part of GA. The owner's reviews of PR #27 on 2026-10-16 and 2026-10-19, and the decisions of 2026-10-20, 2026-10-21, 2026-10-25 and 2026-10-26, settled what this design states, and [Open](#open) lists what is still open. Replaces the 2026-10-10 framework design. Terms follow `GLOSSARY.md` at the repository root.*

## The problem

Coding agents can now finish most well-specified tasks, and every major Harness can run a team of them: one Session starts subagents, runs them in parallel and collects their results. What no Harness supplies is what a senior engineer gives a team of people: standards to build into, changes kept small, and a code-quality bar held on every change. Models may learn to size their changes well on their own; today they often make them too large, and the large changes cause bugs. Left alone, agents also take shortcuts: they weaken a test, edit the CI that judges them, or repeat a mistake they were corrected for the day before.

rapid-ship supplies those three things to a repository and to whichever Harness the owner works in: seeded documents, instructions and Patterns that `rs-health` audits, devctl's 1,500-line diff cap, and checks and guardrails on every change. The owner starts and manages their own Sessions. The approach follows the owner's *Trust-First Agentic Engineering Playbook*: enforce each rule at the layer that fits its purpose, turn every repeated correction into a rule that prevents it, and widen autonomy as measured results support it, which the owner judges.

## The boundary

rapid-ship does for a team of coding agents what a senior engineer does for a team of people. It does not run the team ([ADR 0004](../../adr/0004-team-management-boundary.md)).

| rapid-ship | The owner's Harness |
| --- | --- |
| Seeds README.md and ARCHITECTURE.md, and audits a repository's standards with `rs-health` | Starts, watches, resumes and hands over Sessions |
| Installs the Kit: devctl, instructions, starter Patterns, guardrails and skills | Runs the agents the owner starts, as Sessions or subagents |
| Seeds the instructions every Session reads, among them how to open, review and merge a PR | Follows them as closely as it can, and chooses each agent's model |
| Reports metrics and Suggested threshold breaches, and reviews readiness for Flight with the owner | Pushes, opens PRs, posts reviews and merges, within the guardrails and the ruleset |
| Records Corrections and finds drift through [gardening](#gardening) | Reaches the tracker and other tools through its MCP servers or CLIs |

rapid-ship never pushes, reviews or merges as a step in a flow, and never moves a project between Modes. devctl never talks to the issue tracker. rapid-ship runs no service, daemon, container or local database: it is files in the repository, plus a small command that writes them. It takes no position on which Harness, Provider or billing, whether a subscription, an API key or a gateway, powers an owner's agents, and the Kit integrates with Claude Code first. Nothing it ships needs an API key. It works with GitHub today, through `gh`. Other Git hosts, such as Bitbucket, may follow if owners ask for them or contribute them.

Running agents across several Provider subscriptions is out of scope, because it is outside rapid-ship's goal of accelerating software delivery while holding the code-quality bar; agent control surfaces such as [T3 Code](https://github.com/pingdotgg/t3code) do it.

## Who does what

The **owner** starts and steers their own Sessions, as many as the work needs, chooses the Mode, and merges each PR that the Mode leaves to them. On 2026-10-26 the owner descoped the delivery skills that would have designed, broken down, led, implemented and reviewed the work ([ADR 0004](../../adr/0004-team-management-boundary.md)).

The Mode lives in `project.toml`, which is in the Protected set, so changing the Mode is a PR the owner approves. rapid-ship names no model: the owner's Harness chooses each agent's model, and rapid-ship cannot see which model an agent received. How closely an agent follows its instructions is up to its Harness.

A **Worker** is an agent that implements a change. A **Reviewer** is an agent that reviews a change it did not write. Both are roles that any Session can take, not skills. With Agent identity on, a Worker acts as the Worker App and a Reviewer as the Reviewer App.

The seeded root AGENTS.md has a Pull requests section that every Session reads. It tells each agent to run `./devctl check` before opening a PR, to review a change only from a Session that did not write it, and never to approve a change it wrote. It also says to merge with `--match-head-commit`, to declare an overage of the diff cap only after the owner accepted it, and to undo a merged change only with `git revert`. [Spec 1](2026-10-14-kit-and-setup-design.md) gives the section's text.

rapid-ship runs none of the work. It holds the bar on each change through `devctl check`, the Harness guardrails, the merge guard and any ruleset, whichever Session made the change.

rapid-ship takes no notice of how many Sessions or agents run at once, and sets no cap. In Walk the owner launches the Sessions and watches them, with the subagents they start, so the documentation advises running at most 3 agents at once, for the owner's cognitive load.

## Standards

The Kit gives each area that rapid-ship touches a base to build on, so a newly onboarded project starts from it. `rs-setup` establishes the standards with the owner in a new repository. In an existing one, `rs-health` audits them and returns proposed tasks, each one PR within the diff cap. It writes the ones the owner picks to whatever tracker the owner's Harness reaches, and never edits the repository itself.

- **Instructions:** AGENTS.md files, one per maintained directory, are the single instruction source. A real `CLAUDE.md` contains `@AGENTS.md`.
- **README.md and ARCHITECTURE.md:** the Kit seeds skeletons, and `devctl check` verifies that they and their links exist.
- **Stacks:** the Kit supports Python and TypeScript, the latter for React with room for tools such as Tailwind. The TypeScript stack checks with ESLint, Prettier, `tsc --noEmit`, Vitest and `npm audit`, and uses npm as its package manager. A repository can hold several stacks, such as a Python backend in `backend/` and a TypeScript frontend in `frontend/`. The Kit stays at the root, `project.toml` lists each stack with its directory, and `devctl check` runs each stack's steps in that directory.
- **Linters, static analysers and profilers:** each stack's linters, formatters, type checkers and other static analysers, with their settings, which `devctl check` runs. The Python and TypeScript stacks each name a profiler for finding slow code: for Python, a sampling profiler such as py-spy; for the TypeScript stack (React), the browser's performance tools and React's Profiler. A performance Pattern documents each, and `devctl check` never runs a profiler, because timings are not deterministic.
- **Settings files:** every settings file the Kit ships comments a key inline where its name and value do not show its contract, and is validated, by devctl or by the tool that reads it: allowed keys, numeric ranges and enums.
- **Patterns:** the Kit seeds a starter Pattern set for each stack, which the project then owns and adapts. It covers error handling (fail fast, fail gracefully, and never hide or obscure an error), configuration (typed, validated and documented, with numeric ranges, enums and short inline docs), and input validation with typed enums rather than strings. A Pattern file names the recurring task, its reference implementation and the check that enforces it. It also explains what the reference does right, so an agent learns the lesson and not only the location. `devctl check` verifies that the reference and the check exist. In a new repository `rs-setup` adapts the starter set with the owner. In an existing one, `rs-health` finds recurring tasks done several ways and proposes one reference for each. Agents may add a Pattern; changing an existing one needs the owner.
- **Feature map:** one file per feature says where it is entered, what data it touches, and how to observe and reproduce it.

When `rs-setup` adopts an existing repository, it compares the project's own linter, type-checker and formatter settings with the Kit's. It ignores purely stylistic differences, such as line width. At the end of Setup it offers the meaningful rules the project lacks as a separate PR, which merges them into the project's settings and runs the linters with them.

Throughout, rapid-ship prefers guided rectifying to a bare exit: when a command or a check stops, it explains the problem and the fix. It still fails fast and never hides or obscures an error.

## How the bar is held

Every rule sits on one of four rungs. A rule goes on the rung that fits its purpose, and one bad pattern can need more than one rung.

| Rung | What it is | Example |
| --- | --- | --- |
| 1. Safe interfaces | One supported way to do a recurring task, with the bypass banned | Configuration is read only through `settings`; `os.environ` is banned elsewhere |
| 2. Automated checks | `devctl check`, required in CI | Lint, types, static analysis, dead code, tests, import contracts, the diff policy |
| 3. Judgement | Skills, advisory Rules and review | "Prefer deep modules with small interfaces" |
| 4. The owner | Human approval | Changes to CI, guardrails, skills or settings |

A safe interface removes a structural way to misuse something. A check catches local or stylistic problems, such as line length or `Any` in weakly typed code. The two often work together: in rung 1's example, `settings` is the interface and a lint rule bans the bypass. Skills and advisory Rules are the fallback for what no interface or check can carry.

`devctl check` covers everything a machine can decide without a model, so CI stays deterministic and needs no model sign-in. Beyond lint, types and tests, it confirms that the instructions, README.md, ARCHITECTURE.md, the feature map and the Patterns exist and that their links resolve. Its diff policy fails a change that quietly deletes a test or turns an assertion into a tautology; every removed test is declared in the PR. Its diff cap fails a change of more than 1,500 added and removed lines, unless the PR declares `Over the diff cap:` with a reason. An agent declares it only after the owner accepted the overage, before the work. In every Mode the owner merges a PR that declares a removed behavioural test or an overage ([Modes](#modes)). The count leaves out `.md`, `.txt` and `.log` files, binary files, lock files and Kit-managed files. There are no ratchets: an unsafe pattern is prohibited outright, and a legitimate exception is an entry in an exceptions file that only the owner can approve.

**Harness guardrails** bring the rungs into each Harness's own loop. One devctl command, `devctl hook`, holds every rule, and the Kit's seeded settings connect it to a Harness's hook events. It denies `--no-verify`, force pushes, `gh pr merge --admin`, a `git push` to the default branch, the merges, ref writes and commits through `gh api` that Spec 1 lists, and hand edits to `.rapid-ship/kit.lock`. It asks before an edit to the Protected set. Plan 5 seeds the settings for Claude Code alone; Codex and agy get theirs only if plan 5's hook spike confirms their hooks. These settings files join the Protected set. No hook runs `devctl check` when an agent stops, because that is too heavy: the pre-commit hook and CI run it, and the seeded root AGENTS.md tells every Session to run it before opening a PR.

**The merge guard** is a rule of `devctl hook`, on in every setup, in each Harness whose hooks run `devctl hook`. It enforces each [Mode](#modes). In Walk it denies every agent's `gh pr merge`, so the owner merges each PR. In Flight it denies an agent's `gh pr merge` when the PR touches the Protected set, when the PR's body declares a removed behavioural test or an overage of the diff cap, when `devctl check` has not passed on the PR's head commit, when Agent identity is on and the Reviewer App has not approved the head commit, or when the running guard cannot check it. It also requires the merge to name the head commit it checked with `--match-head-commit`, so GitHub refuses the merge if the head moves after the check. A merge without it is denied with the exact command to retry. With or without Agent identity, the guardrails deny the other ways to land a change on the default branch that the hook recognises: `gh pr merge --admin`; a `git push` to the default branch; through `gh api`, a REST merge of a PR or a branch, a write to the default branch's ref, or a commit through the Contents API; and the GraphQL mutations that merge, enable auto-merge, queue a merge, update a ref or commit to a branch. [Spec 1](2026-10-14-kit-and-setup-design.md#the-merge-guard) lists each form. `gh pr merge` is then the only recognised way for an agent to merge, and the guard checks it. The hook reads GitHub only for `gh pr merge`, so other tool calls make no GitHub request for it. It matches command lines, so a misbehaving agent can get past it, for example through a script or a tool the hook does not see, such as an MCP server's merge tool. The owner merges a Protected-set PR in GitHub's web interface.

When one of its rules fails, `devctl hook` lets the call through, so a bug in a rule never stops work; only the merge guard denies a merge it cannot check. That holds only once the hook runs and has parsed the event, and Spec 1 documents the hook's exit codes as a workaround for the Harnesses' hook protocols. In Claude Code, the call goes through, a merge included, when `uv` is missing, Python fails while loading devctl, the hook cannot parse the event, or Claude Code kills the hook at its hook timeout. When uv itself fails, it exits 2, which Claude Code reads as block, so every wired call stops until the setup is fixed. While the hook cannot read its settings, it still denies what needs no settings and the merge guard denies every merge, but it no longer asks before Protected edits or applies Agent identity's denies. The `./devctl doctor --settings` run that the seeded root AGENTS.md asks of every Session at its start is what catches a broken setup: it starts devctl the same way as the hook, so a uv or Python failure stops it too, and it reports settings it cannot read and wiring that lacks the Kit's hooks. It makes no GitHub request; the full `./devctl doctor` also checks GitHub. The design relies on the guardrails in Claude Code, whose hooks also fire inside subagents. A spike, the first task of plan 5 (backlog item PRO-139), checks Codex's and agy's hooks, and its report decides whether a follow-up wires each. Sandboxing is a recommendation that `rs-setup` offers, not a default, because subagents inherit the sandbox of the owner's own Session. Any other Harness, such as pi, and Codex and agy until their wiring lands, gets AGENTS.md, `.agents/skills`, the pre-commit hook and CI, but no guardrails, so the merge guard does not run there. The pre-commit hook, CI and any ruleset still hold, and `rs-setup` and `rs-preflight` say so. Supporting another Harness takes one more template layer.

The **Protected set** is the kinds of change that need the owner's approval in every Mode. It covers changes to CI and the guardrail settings, devctl, the skills and the other agent instructions, rapid-ship's settings and exceptions, the check tools' settings files, an existing Pattern, the Corrections ledger's format, and an existing entry in the ledger. It holds in every setup: the merge guard denies an agent's merge of a Protected-set PR, and with Agent identity and a ruleset, GitHub also requires the owner's approval through CODEOWNERS. GitHub and the merge guard both read CODEOWNERS from the PR's base branch, never its head, so a PR cannot exempt itself.

**GitHub gates merges where it offers rulesets**: on public repositories, and on private ones with a paid plan. One ruleset on the default branch requires a PR with code-owner review, every review thread resolved, and a passing `devctl check` reported by GitHub Actions. It requires no approval count and no approval of the most recent push, because plan 4's live trial found that GitHub does not take the Reviewer App's approval. It allows squash merges only and blocks force pushes. Only the repository admin role may bypass it, and only when merging a PR. `rs-setup` applies it and `devctl doctor` checks it. A GitHub Free private repository has no rulesets, so there the merge guard is the enforcement: it rejects every agent merge in Walk, and in Flight an agent's merge while `devctl check` has not passed on the PR's head. The guardrails also deny an agent's `git push` to the default branch, which a repository without a ruleset would accept.

**Agent identity** is optional ([ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md)). `rapid-ship app` creates two GitHub Apps: one opens and merges PRs, the other posts reviews. With it on, agents make their GitHub writes through `devctl as`, one thin command that runs `gh` and `git push` with an App's short-lived token. The Harness guardrails then deny `git push` and `gh` writes made as the owner. GitHub never lets a PR's author approve or request changes on it, on any plan, so Agent identity buys four things:

1. The owner can formally approve agent PRs, so merges need no admin bypass. In a team, teammates' approvals cover this without it.
2. Reviews posted as the Reviewer App are real GitHub reviews, so Revisions can be counted and the merge guard can require that App's approval before an agent merges.
3. Agent PRs can be told apart, which every per-agent-PR metric needs.
4. CODEOWNERS binds agents in Flight while they act through `devctl as`, because an App cannot use the owner's bypass.

Without it, agents act as the owner. Agent identity matters most for a solo owner on GitHub Free with a public repository: GitHub enforces the ruleset there, the owner cannot approve a PR their own account opened, and every agent comment appears publicly as the owner's. `rs-setup` gives this advice, and the owner opts in or not:

| Setup | Agent identity | Why |
| --- | --- | --- |
| Solo owner, public repository or paid plan | Recommended | It is the only way the owner can approve agent PRs, and GitHub binds agents |
| Solo owner, GitHub Free private repository | Recommended, for real reviews and metrics | There is no ruleset, so the merge guard holds the bar with or without it |
| Team | Optional | Teammates approve agent PRs anyway. The Apps add per-agent metrics, real reviews from the Reviewer App, and agents that CODEOWNERS binds in Flight |

A team shares one Worker App and one Reviewer App per repository owner. Repositories that an organisation owns are supported from the start (backlog item PRO-105): an organisation admin runs `rapid-ship app` once, and it creates both Apps on the organisation through GitHub's organisation manifest flow. Each developer holds their own private key for each App, since GitHub allows up to 25 keys per App, and keeps it in their own Keychain, so one person's key can be revoked alone. Each Keychain item's name carries its App's ID, so one machine can hold the keys of several Apps, such as a developer's own and their organisation's. For an organisation's Apps, the admin makes each developer an App manager of both, and each generates their own key and imports it with `rapid-ship app`; whether an App manager may generate a key is not yet verified ([Open](#open)). For Apps a personal account owns, the account owner generates one key for each collaborator and hands it over securely, or moves the Apps to an organisation. In an organisation the code owner is a person or a team, never the organisation, so `project.toml` records the code owner and doctor checks CODEOWNERS against it. A pair of Apps for each developer was rejected: it multiplies installations and splits one role's reviews across identities.

One limit is worth stating plainly. Agents run on the owner's machine under the owner's sign-ins, with both App keys within reach, and a misbehaving agent can bypass any guardrail, the merge guard included. It could then act as the owner, with or without Agent identity. Guardrails stop habits and mistakes, not a determined agent. The owner accepts this in every Mode, Flight included ([ADR 0004](../../adr/0004-team-management-boundary.md)).

## Modes

The Mode is the owner's choice, set by `[escalation] every_pr` in `project.toml` and a CODEOWNERS file that matches it. In **Walk** (`every_pr = true`), CODEOWNERS names the code owner for every path, and the owner merges every PR. In **Flight** (`every_pr = false`), CODEOWNERS names only the Protected set. An agent may then merge a PR once `devctl check` passed on its head commit and, with Agent identity, the Reviewer App approved that commit. The owner still merges a PR that touches the Protected set, or whose body declares a removed behavioural test or `Over the diff cap:`. Anything between is allowed: in Flight the owner can add paths to the Protected set in CODEOWNERS, such as migrations or a public API, and those paths are then held like the rest of the set.

The merge guard enforces each Mode in every setup, in each Harness wired to `devctl hook`: in Walk it denies every agent merge, and in Flight it denies an agent's merge of each PR that the owner still merges. GitHub also enforces the Mode through CODEOWNERS, with Agent identity and a ruleset: CODEOWNERS `*` enforces Walk, and Flight narrows CODEOWNERS to the Protected set. Without Agent identity, an agent's PR comes from the owner's account, so under a ruleset a solo owner can merge a PR that needs code-owner review only through the admin bypass. The guardrails deny agents `gh pr merge --admin` and the other recognised ways to land a change on the default branch. Without a ruleset, such as on a GitHub Free private repository, GitHub enforces neither Mode, with or without Agent identity, so the merge guard alone holds each. Flight is still available without Agent identity, with the same ruleset: it requires no approval for a PR outside the Protected set, so an agent can merge one, and a solo owner merges a Protected-set PR through the admin bypass in GitHub's web interface. `rs-setup` and `rs-preflight` explain this, and the owner decides.

The owner changes the Mode in one Protected PR, by hand or through any Session. The PR sets `every_pr` and changes CODEOWNERS to match, and `devctl doctor` checks that the two agree.

When to fly is the owner's call, made from the metrics. rapid-ship has no gate into Flight and never returns a project to Walk. It helps the owner fly in two ways:

1. **Which PRs reach the owner.** In Flight only the Protected set, a declared removed behavioural test and a declared overage reach the owner, which speeds up delivery. Each path the owner adds to the Protected set sends its PRs back to them.
2. **Pre-flight.** Before the owner widens the Mode toward Flight, `rs-preflight` reviews the project's readiness with them, like an operational-readiness review before a release. It covers the metrics to watch, the Alarms and incident integrations this project needs, scheduled [gardening](#gardening), which PRs the owner still merges in Flight, and the status of Agent identity and the ruleset. It advises, and never gates or changes the Mode.

## Metrics

rapid-ship provides a basic set of metrics that a project can extend. Each comes deterministically from GitHub and git, with no model and no attribution step.

| Metric | Without Agent identity |
| --- | --- |
| Revisions per merged agent PR | Unknown |
| Reverts: merged PRs that a later commit reverted, in whole or, where it can be detected, in part | Counted over all PRs |
| Red default-branch CI after a merge | Counted over all PRs |
| Agent PRs the owner closed unmerged | Counted over all PRs |
| Corrections by rung, from the Corrections ledger | Counted |

The owner reads them with `devctl metrics`, or from an optional scheduled GitHub Action that posts the same report. Without Agent identity, a metric that must tell agents from the owner reports "unknown: needs Agent identity". No metric relies on markers that agents set on their own work. Revisions count only change requests posted as GitHub reviews, so a review done inside a Session, or posted as a comment, goes uncounted. Corrections are the one agent-reported metric: agents write the ledger entries, so the count is only as complete as their records, and the owner signs off on what happens to each. A missing metric is unknown, never zero.

The owner records **Suggested thresholds** at Setup. rapid-ship reports a breach and takes no action.

The signals that matter most for Flight, such as Alarms, incident reports and deploy rollbacks, depend on how each project and team runs its software. rapid-ship cannot measure them for everyone, so it guides the owner through setting them up, in `rs-setup` and again in Pre-flight. Each plugs in as a project-defined metric. Incidents come from a metric written for the project against the owner's own incident tool, such as PagerDuty or alarms posted to Slack. The incidents it returns with their causes also feed gardening as Corrections.

## Gardening

Gardening is rapid-ship's name for the regular upkeep of a codebase that agents work in. Agents repeat mistakes they were corrected for, and instructions, documents and code drift apart as the code changes. Small, regular passes keep both in check, as weeding keeps a garden. Each pass records what was corrected, finds what drifted, and proposes a rule that prevents each repeated Correction. The `rs-garden` skill runs a pass. This section is gardening's reference until the documentation site gives it a page of its own.

A pass covers two things:

- **Corrections**, from three sources:
  - the review threads on PRs, from Reviewers and the owner. A model reads the threads, so this works without Agent identity;
  - Corrections the owner gives in a Session, which an advisory Rule in the seeded root AGENTS.md asks the corrected agent to add to the ledger as an open entry with `source: session`;
  - incidents, such as metric Alarms and incident reports, traced to a change. Each project tracks incidents in its own tool, so `rs-preflight` guides the owner through a project-defined incident metric that returns each incident with its cause. Without one, gardening records no incident Corrections.
- **Drift**: a stale AGENTS.md, ARCHITECTURE.md or README.md, code that departs from its Pattern, exceptions nothing uses, and dead code. "Fail fast, fail gracefully, never obscure an error" is a base rule of every pass, so it also looks for code that hides or obscures an error.

Agents may add entries to the Corrections ledger. Changing or removing an existing entry, or its status, is a Protected change, so the owner signs off on what happens to each Correction. An added entry is not checked, so an agent could add one that is already closed; the owner accepts that limit.

The gardener shares one audit with `rs-health`, which runs it once at adoption. The gardener reruns it over the changes since its last pass and adds the new Corrections. For each repeated Correction, and for a severe first one such as a security finding, it proposes a fix on the rung that fits: a safe interface for structural misuse, a check for local or stylistic problems, or both; a skill or advisory Rule only when neither can carry it. Rule changes come back as proposed tasks, in the shape that `rs-health` uses. Doc-only drift fixes come back as one PR per pass.

`rs-garden` is a skill the owner runs. rapid-ship advises running it on a schedule, at least weekly, and before each Pre-flight; how to schedule it is the owner's choice.

## What rapid-ship ships

- **The `rapid-ship` command** writes and updates the Kit. `init` vendors it, `status` compares the repository with the Kit lock, `sync` proposes Kit updates as a PR, and `app` creates the Apps for Agent identity. `sync` never edits a seeded file; it lists each one whose template changed. Before GA, the documentation release, the Kit keeps no backward compatibility: when a Kit update changes what a seeded file must contain, the project fixes the file, and a check that requires the new content fails at once. The policy for after GA is designed then. `uvx` fetches the command from a git tag of this repository; it is not on PyPI yet. `rs-setup`, not a command, marks an existing project's suppressions.
- **The Kit** is what `init` vendors: devctl's source, the instruction and document skeletons, the Pattern and feature-map formats, a starter Pattern set for each stack, the Harness guardrail settings, a pre-commit hook, a CI workflow, CODEOWNERS, the `.rapid-ship/` settings and the skills. `init` records each file as managed, which `sync` keeps current, or seeded, which the project owns from the start. A managed file the project edits becomes its own until `rapid-ship sync --revert`.
- **devctl** is the repository's own CLI for people, agents and CI. Its commands are `check`, `doctor` and `metrics`, plus `as`, the thin command for `gh` and `git push` under Agent identity, and `hook`, which holds the Harness guardrails and the merge guard. `doctor` reports what the machine and repository lack, including settings it cannot read, and `doctor --settings` checks only the settings, for the start of every Session. `doctor --skills` asks Claude Code, when it is installed, which Kit skills it loads, and doctor checks the Apps only under Agent identity. A project adds its own verbs.

Four skills carry the work: `rs-setup`, `rs-health`, `rs-garden` and `rs-preflight`. The Kit also ships seven engineering skills: `rs-tdd` and `rs-diagnosing-bugs`, forked for TDD and debugging, and `rs-codebase-design`, `rs-pr`, `rs-writing-for-agents`, `rs-writing` and `rs-ponytail`. Optional skills, such as `rs-contribute`, install only when the owner lists them under `[kit] optional`. Every Kit skill's name starts with `rs-`.

| Skill | What it does |
| --- | --- |
| `rs-setup` | Sets up a new repository or adopts an existing one: the Kit, the README, ARCHITECTURE and AGENTS documents, the starter Patterns, the Harness guardrails and the ruleset; optionally Agent identity and the metrics Action |
| `rs-health` | Audits a repository and returns proposed tasks, and writes the ones the owner picks to the tracker the Harness reaches |
| `rs-garden` | Records Corrections and finds drift |
| `rs-preflight` | Reviews readiness with the owner before the Mode widens toward Flight; it advises and never gates |

There is no metrics skill: `rs-setup` records the thresholds, `rs-preflight` reviews which metrics to watch, and project-defined metrics are documented. There is no review skill either: the Pull requests section of the seeded root AGENTS.md says how to review a change and post the review.

Each skill is one real directory under `.agents/skills/<name>/`, which Codex and agy read. Claude Code, the only major agent that cannot ([skills layout research](../../trials/2026-10-16-skills-layout.md)), gets a relative symlink per skill, `.claude/skills/<name> -> ../../.agents/skills/<name>`, recorded in the Kit lock. `SKILL.md` itself is never a symlink, because Codex rejects one. opencode and Gemini CLI read both directories and warn about duplicates. The owner's machine must run macOS for now, and `devctl check` also runs on Linux, as CI does. Windows is not supported yet, because git there can check the skill links out as plain files (backlog item PRO-104).

## Dog-fooding

*This section describes this repository's own configuration, not product behaviour.* rapid-ship vendors its own Kit and is validated on itself and on its sample project, hello-rapid-ship. It is a public repository on GitHub Free with one owner, the setup where Agent identity matters most, so PR #33 turns Agent identity on. The owner created both Apps on 2026-10-19 and installed them on this repository, and #33 records them under `[github]`. It records its own choices as rules in its root AGENTS.md: Linear is its tracker; its agents sign in with vendor subscriptions only; and agy is never a Reviewer here.

## Delivery

Two specs remain. Spec 2, the delivery skills, was descoped on 2026-10-26, and Spec 3 keeps its number:

- **Spec 1, [Kit and Setup](2026-10-14-kit-and-setup-design.md):** the `rapid-ship` command; `devctl check`, `doctor`, `as` and `hook`; the Harness guardrails and the merge guard; the README and ARCHITECTURE seeds; the starter Patterns; the Python and TypeScript stacks; optional Agent identity; `rs-setup` and `rs-health`. The [plan index](../plans/2026-10-14-kit-and-setup.md) lists its seven plans:
  - Plans 1 to 3 built `init`, `status`, `sync` and `devctl check`.
  - Plan 4, doctor and Agent identity, built `app`, `devctl doctor` and `devctl as`, merged in PRs #31 to #33. Its follow-ups, built in the same PRs, support organisation-owned repositories (backlog item PRO-105).
  - Plan 5, Kit standards and Harness guardrails, is built in PRs #35 and #37 to #40 and wires Claude Code alone. From its hook spike (backlog item PRO-139), a follow-up wires Codex (PRO-142), and agy waits for its interactive runs (PRO-143).
  - Plan 6 adds the TypeScript stack and several stacks in one repository, which brings part of backlog item PRO-108 into scope.
  - Plan 7 builds `rs-setup` and `rs-health`, which need to know the stacks.
- **Spec 3, [Metrics and gardening](2026-10-16-metrics-and-gardening-design.md):** `devctl metrics`, the scheduled Action, Suggested thresholds, project-defined metrics, the Corrections ledger, `rs-garden` and `rs-preflight`.

Spec 3 gets its own plan. Plan 7's last PR rewrites the documentation site and is GA, the documentation release. It lands after Spec 3 is built, so GA includes Spec 3. Deferred until the product works: the rest of monorepo support (PRO-108), Git hosts other than GitHub, and Windows.

[ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) and [ADR 0004](../../adr/0004-team-management-boundary.md) record decisions with lasting trade-offs. ADR 0003 was withdrawn before merge.

## Open

- **The Codex and agy guardrails.** Plan 5 wires Claude Code alone. Its spike (PRO-139) checks whether Codex's and agy's hooks fire, including inside subagents, and its report decides whether a follow-up wires each. Until then both are Harnesses without Kit wiring.
- **Who may generate a shared App's key (PRO-105).** For an organisation's Apps, each developer generates their own private key as an App manager of both Apps, so nobody else handles it. GitHub documents that App managers manage an App's settings, but not that this includes generating its private keys. The organisation trial among plan 4's follow-ups settles it; if App managers cannot, the organisation admin generates one key for each developer and hands it over securely. The App manager route costs this: an App manager can also change the App's settings.
