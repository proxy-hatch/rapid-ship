# Spec 3: Metrics and gardening

**Status: revised on 2026-10-19 with the owner's decisions from the second review.** Section 17 lists what is still open, and a plan for this spec comes later. This is the third of the three specs listed in the [rapid-ship design](2026-10-14-rapid-ship-design.md), and it replaces the earlier plan for a third spec, "Metrics and the gate". Terms follow `GLOSSARY.md` at the repository root.

## 1. Scope and outcome

When this spec is built, an owner can:

- run `./devctl metrics` and read the basic metrics for the last 30 merged PRs, computed from GitHub and git without a model, with each Suggested threshold marked ok, breached or unknown;
- turn on a scheduled GitHub Action that posts the same report to one issue in the repository, using only `GITHUB_TOKEN`;
- add the project's own metrics, such as Alarms, incidents or deploy rollbacks, through settings or a few lines of Python in `devctl_project`;
- run `rs-preflight` before widening the Mode toward Flight: an advisory review of this project's metrics, Alarms, incident integrations, gardening, escalation list and enforcement, with guided setup for what is missing;
- keep a Corrections ledger in the repository that agents write and the owner signs off, with the rung or rungs that would have prevented each Correction and what was done about it;
- run `rs-garden`, by hand or on a schedule, to add new Corrections from reviews and incidents, find drift, propose rule changes as tasks and fix doc-only drift in one PR per pass.

Metrics, Alarms and incident reports matter most in Flight, where the owner reads fewer PRs. Each project and team sets them up differently: what it ships, where it runs, which monitoring it has and how it handles incidents. rapid-ship therefore ships a basic set and the plumbing for the rest, and puts its weight on advising and guiding the owner through this project's own setup (section 11).

rapid-ship reports and never acts on a report. A breached Suggested threshold changes nothing: rapid-ship never changes the Mode, opens no PR and stops no agent because of a metric ([ADR 0004](../../adr/0004-team-management-boundary.md)). The owner reads the report when choosing the Mode, and `rs-preflight` advises without gating.

Out of scope here:

- [Spec 1](2026-10-14-kit-and-setup-design.md) covers Agent identity and when to set it up, and the thin devctl command that runs `gh` and `git push` as an App. It also covers the merge guard in `devctl hook`, the starter Patterns, `rs-health` and the audit it shares with `rs-garden`, and the `rs-setup` steps that record thresholds and offer the metrics Action.
- [Spec 2](2026-10-16-delivery-skills-design.md) covers how the Reviewer posts its findings, the Lead brief's request to add in-session Corrections to the ledger, the escalation list and how `rs-lead` changes it, and the shape of a task.
- Section 13 lists what this spec needs from both.

## 2. Where the numbers come from

**Deterministic.** Every basic metric comes from GitHub's API and the repository's git history. No model reads anything, and devctl attributes no event by judgement. devctl reads no label, commit trailer or PR text that an agent writes to describe its own work. Two runs over the same GitHub state and the same git history give the same numbers. Corrections differs in where its data comes from: it counts ledger entries, which agents write, so it is agent-reported (section 9).

**Read-only.** devctl reads GitHub through `gh api` with the token `gh` has: the owner's `gh` login on the owner's machine, `GITHUB_TOKEN` in the Action. It reads git from the local `origin/<default branch>` and never fetches. Its only write is the Action's post (section 8), which runs only inside GitHub Actions.

**Agent identity.** Agent identity is on when `[github]` in `project.toml` records both Apps, each with its ID and slug (Spec 1). An agent PR is then a PR authored by the Worker App, the App that opens and merges PRs; its bot account is `<slug>[bot]`. In a team, every developer's agents act as the same two Apps (Spec 1), so this holds whoever ran the agent. devctl reads the slug from the settings and never needs an App's key. With Agent identity off, agents open PRs under the account of the person who runs them, and GitHub cannot tell an agent PR from a person's. A metric that needs that distinction reports `unknown: needs Agent identity`. The others count every PR and say so.

**Population.** Each metric names what it counts:

| Population | Meaning |
| --- | --- |
| `agent PRs` | PRs the Worker App authored. Agent identity is on |
| `all PRs` | Every PR. Agent identity is off |
| `ledger` | Entries in the Corrections ledger |
| `repository` | Events in the repository that belong to no PR. Project-defined metrics use it |

**Window.** The window is the last `window` PRs of the population merged into the default branch; `window` is 30 by default. Counting merged PRs instead of weeks judges a quiet month and a busy one on the same number of PRs.

1. devctl walks the first-parent history of `origin/<default branch>` from its tip.
2. For each commit it asks GitHub which PR merged it (`GET /repos/{owner}/{repo}/commits/{sha}/pulls`) and keeps the PR whose `merge_commit_sha` is that commit. A commit that no PR merged, such as a direct push, is skipped.
3. It keeps PRs of the population until it has `window` of them or the history ends. With fewer, the report says so, for example `12 of 30`.

The window's span runs from the merge time of its oldest PR to the time of the report. A PR that GitHub shows as merged but whose merge commit is not yet in the local `origin/<default branch>` is left out, and the report counts it as not fetched. Run `git fetch` and rerun. The Action's checkout has the whole history, so there that count is normally zero.

## 3. The basic metrics

| ID | Metric | Population | Value |
| --- | --- | --- | --- |
| `revisions` | Revisions per merged PR | `agent PRs` only | Mean Revisions per PR in the window |
| `reverts` | Reverts | `agent PRs`, or `all PRs` without Agent identity | PRs in the window that later commits reverted, in whole or in part |
| `red_merges` | Red merges | `agent PRs`, or `all PRs` without Agent identity | PRs in the window whose merge commit failed `devctl check` |
| `closed_unmerged` | Closed unmerged | `agent PRs`, or `all PRs` without Agent identity | PRs closed without merging during the span |
| `corrections` | Corrections | `ledger` | Entries dated in the span, in total and by rung. Agent-reported |

Each count lists the PRs or entries behind it, so the owner can open each one.

### Revisions per merged PR

For each PR in the window, devctl counts the distinct head commits that received a review requesting changes, submitted no later than the merge:

1. Read the PR's reviews (`GET .../pulls/{number}/reviews`) and keep those with state `CHANGES_REQUESTED`.
2. Add each dismissed review that requested changes. A dismissed review has state `DISMISSED`; the PR's `review_dismissed` event records the state it had before.
3. Count the distinct `commit_id` values. Several reviewers requesting changes on one head are one Revision, and a second review of the same head adds none.

Any reviewer counts: the Reviewer App or a person. The value is the window's total divided by the number of PRs in it. The report lists the PRs with the most Revisions. Spec 2's `revision_rounds` escalation kind also counts distinct head commits, but the Lead reads each verdict's first line, `rapid-ship review: changes requested`, and people's reviews that requested changes, so the kind works without Agent identity.

This metric needs Agent identity for two reasons. Without it, devctl cannot select agent PRs. And a Reviewer acting as the account that opened a PR cannot request changes on it, so it posts its verdict as a comment review (Spec 2), which no Revision counts.

### Reverts

A PR in the window counts as reverted when any of these holds at the time of the report:

1. A commit on `origin/<default branch>` after the PR's merge commit has a message line `This reverts commit <sha>`, where `<sha>` is the PR's merge commit in full, 40 characters. `git revert` writes this line, also when it reverts a merge commit.
2. A PR merged into the default branch after it has the body line `Reverts <owner>/<repo>#<number>`. GitHub's Revert button writes this line.
3. Later commits undid all or part of the PR, by the content check under "Partial reverts" below. This finds a revert made by hand, whole or partial.

A PR reverted more than once counts once, and a whole revert outranks a partial one. A revert made by hand that writes neither line and that the content check does not match is missed; `rs-work` undoes a merged commit only with `git revert` (Spec 2). The Kit's ruleset allows squash merges only, so each PR is one commit on the default branch. Under other merge methods only reverts of the commit GitHub records as `merge_commit_sha` are detected. Recent PRs have had less time to be reverted; the count shows what happened up to the report.

### Partial reverts

A PR is partly reverted when later commits on `origin/<default branch>` undid some of it, by restoring selected files or sections, but not all of it. Partial reverts count under `reverts`, with whole ones; there is no separate metric. devctl finds them from local git alone, so the check stays deterministic and costs no GitHub request:

- **A restored file.** A later commit leaves a file the PR changed with exactly the content it had before the PR's merge commit. For a file the PR added, that means deleting it; for a file the PR deleted, bringing it back unchanged.
- **An undone section.** A later commit, in the same file, removes lines similar to the lines that one hunk of the PR added, and adds back lines similar to the lines that hunk removed. Two sets of lines are similar when their similarity ratio is at least 0.8, as Python's `difflib.SequenceMatcher` computes it over the joined lines. Lines are compared without leading or trailing whitespace, wherever they now sit. Similarity catches a section undone with small edits, which an exact match would miss. The live trial tunes the 0.8 threshold (section 17). Only a hunk that removed at least one line and changed at least 3 non-blank lines counts, so blank lines, moved braces and pure additions never count alone.

A PR is a whole revert when every file it changed was restored. Otherwise one restored file or one undone section makes it a partial revert. Each item says whether the revert was whole or partial, and a partial one names the files and sections and the commit that undid them.

### Red merges

A PR in the window is a red merge when the CI run that checked its merge commit on the default branch failed:

1. List the runs of `.github/workflows/devctl-check.yml` for the merge commit with event `push` (`GET .../actions/workflows/devctl-check.yml/runs?head_sha=<sha>&event=push`). Take the earliest.
2. Read that run's first attempt. A rerun that passed does not clear a failure, because a flaky check is a problem too.
3. A conclusion of `failure` or `timed_out` is red, and `success` is green. Anything else, or no run at all, is unknown for that PR.

Spec 1's CI template gives each push run on the default branch its own concurrency group, so a later merge never cancels the run of an earlier one. A run cancelled anyway, for example by hand, leaves that PR unknown, and so does a workflow the project took over that still shares one group per branch. The nightly run is not counted: it belongs to no merge, and a newly published advisory can fail it with no change in the repository. CI push runs cover only `main` and `master` (Spec 1); with another default branch, every PR is unknown here.

### Closed unmerged

PRs of the population that are closed and not merged at the time of the report, and whose `closed_at` falls in the span. A PR closed and later reopened counts only if it is closed again.

With Agent identity, a PR counts only when a person closed it: the actor of its last `closed` event is neither App. A PR the Lead closed itself, for example one it replaced with a new PR, does not count. Without Agent identity, devctl cannot tell who closed a PR, so every PR closed unmerged counts.

### Corrections

The value counts ledger entries (section 9) at the tip of `origin/<default branch>` dated on or after the day the span starts. It also counts entries per rung: an entry that names two rungs counts once in the total and once under each rung. The report also counts repeats: entries whose `category` already had an earlier entry anywhere in the ledger.

Corrections is agent-reported. devctl counts the entries exactly, but agents decide which Corrections reach the ledger, and the report says so (section 9).

The ledger is complete only up to the last gardening pass, which `docs/corrections/last-pass.toml` records. A PR in the window whose merge commit is not an ancestor of that file's `through` commit is not gardened yet, and the count is then a lower bound. Without the file, no PR is gardened yet. An entry the Lead added for an in-session Correction counts as soon as it merges.

## 4. Status of a Suggested threshold

A Suggested threshold is an upper limit: the metric should be at most this value. For each metric that has one, devctl reports one status.

| Status | When |
| --- | --- |
| ok | The value is within the threshold even if every unknown part counts against it |
| breached | The known part alone exceeds the threshold |
| unknown | Neither: the metric is unknown, or its unknown part could decide the result |

For a count with `v` known items, `u` unknown items and threshold `m`: breached when `v > m`, ok when `v + u <= m`, and unknown otherwise. For Corrections, with `v` entries: breached when `v > m`, ok when `v <= m` and every PR in the window is gardened, and unknown otherwise. A window with no PRs makes every metric unknown, never zero. A metric that is unknown only because Agent identity is off shows `needs Agent identity` instead of a status.

## 5. `devctl metrics`

```text
./devctl metrics [--window <n>] [--json] [--post]
```

- `--window <n>` overrides `window` from `metrics.toml` for this run. It is an integer of at least 1, with no upper limit.
- `--json` prints the report as data instead of text.
- `--post` posts the report as the Action does (section 8). It refuses with exit 2 unless `GITHUB_ACTIONS` is `true` and `GH_TOKEN` is set. On the owner's machine, and in an agent's Session, `devctl metrics` writes nothing.

### Steps

1. Read `.rapid-ship/project.toml` and `.rapid-ship/metrics.toml` (section 6). Agent identity is on when `project.toml` records both Apps (section 2).
2. Ask GitHub for the default branch's name. Resolve `origin/<default branch>` locally; if it is missing, stop with exit 2 and say to fetch it.
3. Build the window (section 2).
4. Compute the basic metrics, then the project-defined metrics (section 7).
5. Give each Suggested threshold its status (section 4).
6. Print the report, or post it with `--post`.

If `.rapid-ship/gate.toml` still exists, the report adds one note: devctl no longer reads it, the owner may delete it, and an old threshold worth keeping belongs in `metrics.toml` (section 6).

The default window takes about 200 GitHub API requests: one per first-parent commit walked and about four per PR in the window. That stays well inside the 1,000 requests per hour that `GITHUB_TOKEN` allows per repository, and a larger window costs more. The content check for reverts reads local git only.

When GitHub's API allowance runs out during a run, devctl stops reading GitHub at once. Each metric it could not finish is unknown, with the reason and the time the allowance resets, such as `unknown: GitHub API allowance used up; it resets at 06:12 UTC`. The Action's post says the same. devctl fails fast and never hides the error: it does not retry in silence, and never reports a partial count as complete.

### Exit codes

- **0:** the report was built and no Suggested threshold is breached.
- **1:** at least one Suggested threshold is breached.
- **2:** the report could not be built: unreadable settings, `gh` missing or signed out, a GitHub error, or no `origin/<default branch>`. With `--post`, a failed post also exits 2.

Every exit 2 names what failed and the fix, for example `origin/main is missing: run git fetch origin`. devctl fails fast and never hides an error, and it guides the owner to the fix rather than stopping with a bare code. An unknown status shows in the report but never changes the exit code. An API allowance that runs out is not exit 2: the report is built, with the affected metrics unknown (section 5). With `--post`, a breach exits 0 once it has been posted, because posting it is the whole response. A project-defined metric that fails is unknown, not an error (section 7).

### Text output

```text
rapid-ship metrics for owner/name at 2026-10-16 05:41 UTC
Agent identity: on. Window: the last 30 merged agent PRs, #212 to #268, merged since 2026-09-03.

metric           population   value                                suggested  status
revisions        agent PRs    0.7 per PR                           <= 1.0     ok
reverts          agent PRs    1 (#244 in part: 1 file)             <= 1       ok
red_merges       agent PRs    0, 2 unknown (#240, #262)            <= 1       unknown
closed_unmerged  agent PRs    4 (#219, #225, #250, #266)           <= 3       breached
corrections      ledger       9 (rung 1: 2, rung 2: 5, rung 3: 3)  -          -
alarms           repository   0                                    <= 0       ok

Corrections are agent-reported: agents write the ledger entries they count.
1 Suggested threshold breached and 1 unknown. rapid-ship takes no action.
```

### JSON output

`--json` prints one object. `version` changes only when a field changes meaning.

```json
{
  "version": 1,
  "repository": "owner/name",
  "generated_at": "2026-10-16T05:41:07Z",
  "default_branch": {"name": "main", "commit": "<40-character SHA>"},
  "agent_identity": true,
  "window": {"size": 30, "prs": 30, "population": "agent", "since": "2026-09-03T11:02:44Z", "not_fetched": 0},
  "metrics": [
    {
      "id": "red_merges",
      "title": "Red merges",
      "kind": "count",
      "population": "agent",
      "value": 0,
      "unknown": 2,
      "reason": null,
      "items": [{"pr": 240, "state": "unknown", "detail": "push run cancelled"}],
      "threshold": 1,
      "status": "unknown"
    }
  ],
  "notes": []
}
```

`value` is `null` when the whole metric is unknown, and `reason` then says why, such as `needs Agent identity`. Each `reverts` item says whether the revert was whole or partial and names the commit that undid it; a partial one also names the files and sections it undid. `kind` is `incident` for an incident metric (section 7) and `count` for every other metric. An item of an incident metric also carries `time` and `cause`. The Corrections metric adds `by_rung`, `repeats` and `not_gardened`.

## 6. Settings: `.rapid-ship/metrics.toml`

`metrics.toml` replaces `.rapid-ship/gate.toml`. It is a seeded Kit file in the Protected set, like every file in `.rapid-ship/`, so changing a threshold is a PR the owner approves. It holds no secret. Like every settings file the Kit ships, it documents each key inline, and devctl validates every key.

```toml
# Suggested thresholds and project-defined metrics for ./devctl metrics.
# Changes need the owner: this file is in the Protected set.
# devctl reports a breach and takes no action. It rejects an unknown key or a value out of range.

window = 30   # integer, at least 1: the last merged PRs counted
              # (agent PRs with Agent identity, every PR without it)

[thresholds]  # upper limits, numbers of at least 0; delete a line to report that metric without one
revisions = 1.0        # mean Revisions per merged PR; needs Agent identity
reverts = 1            # PRs in the window that later commits reverted, in whole or in part
red_merges = 1         # PRs whose merge commit failed devctl check on the default branch
closed_unmerged = 3    # PRs closed without merging during the window's span
# corrections = 10     # Corrections ledger entries dated in the span; agent-reported
# alarms = 0           # a project-defined metric, by its id

# A project-defined metric. source is "issues" or "deployments".
# [[metric]]
# id = "alarms"            # lowercase letters, digits and _; not a basic metric's id
# title = "Alarms"
# source = "issues"        # counts issues with this label opened during the span
# label = "alarm"
#
# [[metric]]
# id = "rollbacks"
# title = "Deploy rollbacks"
# source = "deployments"
# environment = "production"
# count = "rollbacks"      # "rollbacks" (the default) or "failures"
```

`devctl metrics` exits 2 and lists every problem when:

- the top level or a `[[metric]]` has a key not shown above;
- `window` is not an integer of at least 1;
- a key in `[thresholds]` names no basic or project-defined metric, or its value is not a number of at least 0;
- a `[[metric]]` lacks `id`, `title` or `source`, lacks a field its source needs, or has an empty text field;
- `source` is not `issues` or `deployments`, or `count` is not `rollbacks` or `failures`;
- an `id` does not match `[a-z][a-z0-9_]*`, repeats another, or is a basic metric's ID.

Each problem names the key, what is wrong and the allowed values, such as `metrics.toml: window = 0: use an integer of at least 1`. `window` has no upper limit; section 5 says what happens when a large window uses up the GitHub API allowance.

### Default thresholds

The seeded `gate.toml` of plans 1 to 3 recorded 1.0 Revisions per PR, 1 Rollback and 0 open Alarms. The earlier design allowed 3 Revisions, 0.1 Rollbacks and 0.2 Alarms per PR. The defaults are now:

| Threshold | Default | Why |
| --- | --- | --- |
| `revisions` | 1.0 per PR | A mean of 3 would equal the default escalation at 3 Revision rounds (Spec 2), so most PRs would reach the owner before the threshold said anything |
| `reverts` | 1 in the window | One revert, whole or partial, in 30 merged PRs. Deploy rollbacks are project-defined, so they no longer share this count |
| `red_merges` | 1 in the window | A merge that breaks the default branch should be rare |
| `closed_unmerged` | 3 in the window | One closed PR in ten merged ones |
| `corrections` | none seeded | Corrections are agent-reported, and their trend matters more than a count |
| Alarms | none seeded | Alarms are project-defined. The comment suggests 0 for the metric the owner adds |

`rs-setup` shows these and records the owner's values (Spec 1). `rs-preflight` revisits them against the project's history (section 11).

### What happens to `gate.toml`

| `gate.toml` key | Now |
| --- | --- |
| `mode`, `flight_lease_until` and `owner_approves_behavioural_test_removal` | Gone. The escalation list, `[escalation]` in `project.toml`, sets the Mode and names behavioural-test removals; there is no lease |
| `[thresholds.promotion]` and `[thresholds.demotion]` | Replaced by `window` and `[thresholds]` in `metrics.toml` |

Spec 1's plan 4 stops seeding and reading `gate.toml`; this spec seeds `metrics.toml`. In an existing project, `rapid-ship sync` adds `metrics.toml` with the defaults, because it is a new seeded file. `gate.toml` belongs to the project and nothing reads it any more, so `sync` leaves it in place: a migration changes only what a seeded file must contain (Spec 1, section 3), and nothing requires `gate.toml` to go. Until the owner deletes it, `devctl metrics` notes the old file, and the owner can carry any of its values into `metrics.toml`.

## 7. Project-defined metrics

A project adds its own metric in one of two ways. A project-defined metric counts events in the window's span, belongs to no PR and is attributed to none. Its population is `repository`, and its threshold goes in `[thresholds]` under its ID.

Metrics beyond the basic set, such as Alarms, incidents and deploy rollbacks, depend on how each project runs and how each team works. Setting them up is the owner's, and rapid-ship guides it through `rs-preflight` (section 11). Most monitoring and deploy tools can open a GitHub issue or record a GitHub deployment, so the two settings sources below need no code.

### From settings

Two sources read GitHub with the same token as the basic metrics:

| `source` | Fields | Counts |
| --- | --- | --- |
| `issues` | `label` | Issues with that label opened during the span. Pull requests are not counted |
| `deployments` | `environment`; `count`, either `rollbacks` (the default) or `failures` | See below |

For `deployments`, devctl reads the deployments to `environment` and their statuses:

- **Rollbacks:** a deployment created during the span that reached `success`, whose commit is an ancestor in git of the commit of the previous deployment to that environment that reached `success`, and not the same commit. Deploying older code is a rollback, whatever tool did it.
- **Failures:** a deployment created during the span whose last status is `failure` or `error`.

A deployment whose commit is not in the local history is unknown. Each `deployments` metric names its environment; `project.toml` has no `[release]` table (Spec 1).

### Incidents

An incident is something users saw go wrong, such as an outage or corrupted data. Teams track incidents in their own tools, such as PagerDuty or alarms posted to Slack, and under their own rules, so rapid-ship ships no incident source in its settings. An incident metric is a code metric (below) written for the project, which `rs-preflight` guides the owner through building against their own incident tool (section 11).

Besides its count, an incident metric returns each incident as a record: its URL, its time and, where the record names one, its cause, a PR or a commit. `rs-garden` reads those records as a source of Corrections (section 10). Without an incident metric, gardening records no incident Corrections, although incidents remain a source of Corrections in principle.

### From code

`devctl_project` defines a metric the way it defines a check step:

```python
def metrics() -> list[Metric]:
    """Return project-defined metrics for ./devctl metrics."""
    return [ProbeFailures()]
```

A `Metric` has an `id`, a `title` and `measure(context) -> MetricResult`. The context gives the span's start and end, the window's PRs, the repository, and a read-only helper for `gh api`. A `MetricResult` holds a number, or `None` with a reason when the metric is unknown, and the items behind it, each a label with a URL or a time. An incident metric is an `IncidentMetric`, whose items are `Incident` records, each with a URL, a time and an optional `cause`, which `rs-garden` reads. devctl marks it `"kind": "incident"` in the JSON output by its class, not by its items, so the mark shows even when it found no incident or is unknown (section 5).

- An empty source is not zero. A metric returns 0 only after it read its source and found nothing. When it cannot read its source, it returns unknown with the reason.
- A metric that raises an exception or runs longer than 60 seconds is unknown, with the error as its reason. The rest of the report is unaffected.
- A metric must be deterministic and must not run a model. devctl cannot check either, so the seeded `devctl_project` says so.
- A metric that needs a credential other than the GitHub token reads it from the environment. The Kit's Action passes no other secret, so such a metric is unknown there unless the project takes the workflow over (section 8).

The seeded `devctl_project` gains a `metrics()` stub that returns an empty list. A `devctl_project` without `metrics` has no project-defined metrics, so existing projects need no change.

## 8. The scheduled metrics Action

`.github/workflows/rapid-ship-metrics.yml` is an optional managed Kit file. `rs-setup` offers it, the owner opts in, and Spec 1 records the choice under `[kit] optional`. It needs no model and no secret other than `GITHUB_TOKEN`.

- **Triggers:** a daily `schedule` and `workflow_dispatch`. GitHub runs scheduled workflows on the default branch only.
- **Permissions:** `contents: read`, `pull-requests: read`, `actions: read`, `deployments: read` and `issues: write`, and nothing else.
- **Concurrency:** one group, `rapid-ship-metrics`. A run never cancels another.
- **Steps:** checkout pinned by commit SHA, with `persist-credentials: false` and the whole history; `astral-sh/setup-uv` pinned by commit SHA; then `./devctl metrics --post` with `GH_TOKEN: ${{ github.token }}`.
- **Job name:** `rapid-ship metrics`.

### Where it posts

1. **The run's job summary** gets the report in Markdown.
2. **One open issue** titled "rapid-ship metrics" holds the latest report. devctl finds it as the open issue opened by `github-actions[bot]` whose body starts with `<!-- rapid-ship-metrics -->`, and opens one when none exists. Each run replaces the body with that marker, the Markdown report, and the report's JSON inside an HTML comment.
3. **A comment on that issue** appears only when a threshold's status differs from the status in the previous body, and lists each change, such as `closed_unmerged: ok -> breached (4, at most 3)`. When devctl has just opened the issue, it comments only if a threshold is breached or unknown. An edited body sends no notification and a comment does, so the owner hears about changes, not about every run.

The issue is a report, not a task. Closing it stops nothing; the next run opens a new one. To stop the reports, the owner disables the workflow in GitHub or removes it from `[kit] optional`. GitHub disables scheduled workflows in a public repository after 60 days without activity. The report shows when it was generated, so a stale report is visible.

A project whose own metrics need other secrets lists the workflow under `[kit] exclude` and adds them to its own copy (Spec 1). The Kit's copy reads no secret beyond `GITHUB_TOKEN`.

## 9. The Corrections ledger

The ledger is the directory `docs/corrections/`: one Markdown file per Correction, a seeded `README.md` that states the format, and `last-pass.toml`, which `rs-garden` writes. One file per entry keeps parallel PRs from conflicting, as appends to one shared file would.

### Agent-reported, signed off by the owner

Agents write the ledger: `rs-garden` from reviews and incident records, and the Lead from its Session. Corrections is therefore an agent-reported metric. devctl counts the entries exactly, but an agent can miss a Correction or misjudge one, and nothing checks what it left out.

The owner signs off on what happens to each Correction. Adding an entry is free, so an agent's PR can record a Correction without the owner. Changing what is already recorded needs the owner:

| Change in `docs/corrections/` | Protected | Held by |
| --- | --- | --- |
| Adding an entry, whatever its status | No | Not checked |
| Updating `last-pass.toml` | No | Not checked |
| Editing, renaming or removing an existing entry, including any change of status | Yes | devctl's ledger rule |
| Any change to `README.md`, the ledger's format | Yes | Its line in CODEOWNERS |

devctl does not read an added entry's status. An agent could therefore add an entry that is already `implemented`, `rejected` or `closed`, which skips the owner's sign-off. The owner accepts that limit; `rs-garden` and the Lead add entries as `open` or `proposed` only.

The diff step lists each change to an existing entry with the Protected paths, and the merge guard counts it as Protected (Spec 1). The Protected set is on the escalation list in every Mode, so the merge guard denies an agent's merge of such a PR, and the owner merges it in GitHub's web interface. CODEOWNERS matches paths only, so it holds `README.md` but cannot tell a new entry from a changed one: GitHub cannot enforce the entry rule, even with Agent identity and a ruleset. The merge guard is a guardrail, which a misbehaving agent could get around.

### What counts

A Correction is a change that a human, the Reviewer or an incident required of an agent's work: a blocking finding the agent fixed, a person's request for a change that the agent made, or an incident whose report names an agent's PR or commit as its cause. A nit is not a Correction. Neither is a question, or a suggestion that was discussed and not taken.

### An entry

File name: `<date>-<category>-<n>.md`, with the lowest `n` from 1 that is free on the writer's branch. Two PRs that pick the same name conflict at merge, and the second renames its file.

```markdown
---
date: 2026-10-16
by: reviewer
source: https://github.com/owner/name/pull/42#discussion_r1234567890
pr: 42
path: src/app/links.py
category: env-read-outside-settings
rungs: [1, 2]
prevention: Read configuration only through settings, and ban os.environ elsewhere.
status: open
---

The Worker read `LINKS_URL` with `os.environ` inside `links.py`. The Reviewer required it to come from `settings`.
```

| Field | Required | Meaning |
| --- | --- | --- |
| `date` | yes | The day the Correction was made, UTC |
| `by` | yes | `reviewer`, `human` or `incident` |
| `source` | yes | The URL of the review, thread, comment or incident record, or `session` for a Correction the owner gave in a Session |
| `pr` | no | The PR whose work was corrected |
| `path` | no | The file the Correction is about |
| `category` | yes | A short kebab-case name shared by repeats of the same mistake |
| `rungs` | yes | One or more distinct rungs from 1 to 4 that would have prevented it. A Correction that needs a safe interface and a check names both |
| `prevention` | yes | One sentence naming the mechanism that would prevent a repeat |
| `status` | yes | One of the statuses below |
| `task` | when `proposed` | The proposed task in the tracker |
| `prevented_by` | when `implemented` | References that resolve, or repository paths that exist, for the mechanism that now prevents it |
| `reason` | when `rejected` or `closed` | Why the owner chose no prevention, or why none is needed any more |

| Status | Meaning | Who sets it |
| --- | --- | --- |
| `open` | Recorded; nothing decided yet | Whoever adds the entry |
| `proposed` | A task in the tracker proposes a prevention | `rs-garden`, on a new entry or, as a Protected change, on an existing one |
| `implemented` | A mechanism now prevents a repeat | The PR that lands the prevention, signed off by the owner |
| `rejected` | The owner chose no prevention, or judged it no Correction | The owner |
| `closed` | No prevention is needed any more, for example because the code was removed or the entry repeats another | The owner, or a PR the owner signs off |

The rungs are the four in the [design](2026-10-14-rapid-ship-design.md): safe interfaces, automated checks, judgement, and the owner.

### Who writes entries

| Writer | When | `source` |
| --- | --- | --- |
| `rs-garden` | On each pass, from the reviews, review threads and comments on PRs in its range, and from the incident records dated since its last pass, when the project has an incident metric | The URL on GitHub, or the incident record's URL |
| The Lead | When the owner corrects it in the Session. The Lead brief asks for this (Spec 2); whether the Lead does it is up to its Harness | `session` |
| The PR that lands a prevention | Sets `status: implemented` and `prevented_by` on the entries it prevents. This change is Protected, so the owner signs it off | Unchanged |
| The owner | At any time, for example to reject or close an entry | Unchanged |

The Lead adds a `session` entry to the open PR the Correction concerns, or to its next PR when none is open. `rs-garden` skips any thread, review, comment or incident record whose URL is already a `source`.

### `last-pass.toml`

```toml
# Written by rs-garden: the default-branch commit that the last gardening pass covered.
through = "<40-character SHA>"   # a full commit SHA
date = 2026-10-16                # the day of the pass, UTC
```

### The check

`devctl check` gains one map rule for the ledger, in the fast tier, numbered after Spec 1's map rules:

1. Every `.md` file in `docs/corrections/` other than `README.md` has front matter with the required fields above, and no field outside the table.
2. `date` is a date; `by`, `status` and `category` take the forms above; `rungs` is a non-empty list of distinct integers from 1 to 4; `prevention` is not empty; `source` is `session` or an `https` URL.
3. A `proposed` entry has a `task`, a `rejected` or `closed` entry has a `reason`, and an `implemented` entry has a non-empty `prevented_by` list. Each item resolves as a reference of a kind the project's stacks define (Spec 1), such as `check:` or `test:`, or is a repository path that exists, such as a skill file or CODEOWNERS.
4. If `last-pass.toml` exists, it has exactly `through` and `date`, and `through` is a full SHA of a commit in the repository.

Each failure names the file, the field, what is wrong and the allowed values. The Protected classification above belongs to the diff step, which knows the base; this rule checks only the format.

## 10. Gardening and `rs-garden`

### What gardening is

Gardening is routine upkeep of a repository's standards, done in passes. Review judges one change at a time. Gardening looks across the changes merged since its last pass for what single reviews miss: the same mistake corrected again and again, and instructions, documents, Patterns and settings that have drifted from the code. Each pass records the new Corrections, proposes a prevention on the rung that fits for each repeat, and fixes doc-only drift.

`rs-garden` is the user-invoked Kit skill that runs a pass. The owner runs it by hand or on a schedule (below). Each pass has three outputs:

1. New entries in the Corrections ledger.
2. One PR with those entries, the doc-only drift fixes and an updated `last-pass.toml`.
3. Proposed tasks for rule changes, created in the backlog of the owner's tracker through the Harness's connection to it. devctl never talks to the tracker.

### What it never does

- It never merges, and never pushes to the default branch.
- It never sets an entry to `implemented`, `rejected` or `closed`. Those are the owner's sign-off; the pass PR lists the entries that look ready for one.
- It never changes a Protected path except a doc-only fix inside its own PR. The Protected set is on the escalation list in every Mode. The merge guard in `devctl hook` therefore denies an agent's merge of that PR, and the owner merges it in GitHub's web interface. With Agent identity and a ruleset, GitHub requires the owner's approval too. The merge guard is a guardrail, which a misbehaving agent could get around (Spec 1).
- It never changes CI, guardrail settings, devctl, a skill, an existing Pattern file, `exceptions.toml` or any other Protected setting. It proposes a task instead.
- It never starts, schedules or stops an agent, and never puts a task in a started state.

A **doc-only fix** changes prose in `README.md`, `ARCHITECTURE.md`, an AGENTS.md file or `docs/features/` to match what the repository already does. It adds, removes or changes no Rule, Pattern, check, setting, skill or code. Anything else is a rule change and becomes a proposed task.

### Steps

1. **Preconditions.** The work tree is clean. Fetch `origin/<default branch>`. If an open PR already changes `docs/corrections/last-pass.toml`, the previous pass is still waiting: stop and point to it. When devctl reports unreadable settings, stop and pass on its message and fix; never work around it.
2. **Range.** The range starts at `through` from `last-pass.toml` and ends at the tip of `origin/<default branch>`. On the first pass it starts just before the oldest PR in the window that `./devctl metrics --json` reports. When the default branch has not moved since `through` and no incident record is dated since the last pass, read as in step 4, report that there is nothing to garden and stop.
3. **Corrections from PRs.** Read the reviews, review threads and comments of every PR merged in the range, and of every PR closed unmerged since the `date` in `last-pass.toml`. With Agent identity, read agent PRs only. Without it, read every PR, because agent PRs cannot be told apart; the ledger then includes Corrections of people's work too. Write one entry per Correction (section 9). When the Correction is a blocking finding in a Reviewer's verdict (Spec 2, section 3.6), copy its rungs and prevention. Otherwise assign them by the ladder.
4. **Corrections from incidents.** The project has an incident metric when `./devctl metrics --json` lists a metric whose `kind` is `incident` (sections 5 and 7). Read the records it returns that are dated since the `date` in `last-pass.toml`, or since the range's start on the first pass. It returns only the records in the window's span, which starts at `window.since`. When the span starts after that date, rerun `./devctl metrics --json --window <n>` with a larger `n`, such as twice the last one, until the span starts on or before it. A larger window cannot help once the window is not full. A run can also leave the incident metric unknown, for example when the GitHub API allowance runs out. In either case, use the widest run that read the metric, and list in the PR body the interval that no run covered. When a record names its cause and the cause is an agent PR, or a commit of one, write one entry with `by: incident` and the record's URL as `source`. Without Agent identity, any PR counts as a cause. List each record that names no cause in the PR body, and record nothing for it. Without an incident metric, record no incident Corrections, and say so in the PR body.
5. **Repeats.** Group the whole ledger by `category`. Two or more entries in one category, at least one of them `open`, are a repeat. A new entry in a category whose earlier entries are `implemented` means the prevention did not hold. Say so in the PR body.
6. **Proposals.** Propose one task for each repeat, and for each severe first Correction. A Correction is severe when it is a risk of data loss, exposure or a security hole, as `rs-review`'s table names it (Spec 2), or when it came from an incident. Propose the task on the rung that fits: a safe interface for structural misuse, a check for local or stylistic problems, or both; a skill or advisory Rule only when neither can carry the fix. For a prevention that did not hold, propose a task that moves the fix to a rung that can hold it. Before creating a task, search the tracker for an open task for the same category, and reuse it if one exists. A task follows Spec 2's task shape and links the entries it would prevent. Its acceptance criteria include setting those entries to `implemented`. Write each new entry it covers as `proposed`, with `task`, and set each existing one to `proposed`; changing an existing entry makes the pass PR Protected (section 9). Without a tracker connection, leave the entries `open` and put each task draft in the PR body.
7. **Drift.** Run the shared audit over the files changed in the range, with the base rule and the starter Patterns (below). Fix doc-only drift in the pass's branch; propose a task for everything else.
8. **The pass PR.** Write `last-pass.toml` with the range's end. Run `./devctl check --tier fast`. Open one PR from a new branch based on `origin/<default branch>`: with Agent identity through `devctl as worker push` and `devctl as worker gh pr create` (Spec 1), without it with `git push` and `gh pr create`. The body states the range, the new entries, the repeats with their proposals, and the drift with where each item went. It also names any prevention that did not hold, the incident records that name no cause, any interval whose incident records it could not read, and the entries that look ready for the owner's sign-off. It ends with the Evidence section that `devctl check` requires. The diff cap leaves out `.md` files (Spec 1), so ledger entries and doc-only fixes do not count toward it.
9. **Report** to whoever ran the pass: the PR, the tasks proposed and anything skipped.

### The shared audit

`rs-health` and `rs-garden` run one audit, kept once in `.agents/skills/rs-health/references/audit.md` (Spec 1). `rs-health` runs it over the whole repository at adoption and returns a standards milestone. `rs-garden` reads the same file and runs each item over the files changed in its range. The audit must cover at least the drift that gardening finds:

| Drift | Output in `rs-garden` |
| --- | --- |
| A statement, command, path or link in `README.md`, `ARCHITECTURE.md` or an AGENTS.md file that no longer matches the repository | Doc-only fix |
| A feature file in `docs/features/` that no longer describes its feature | Doc-only fix |
| Code changed in the range that hides or obscures an error, against the base rule below | Proposed task |
| Code changed in the range that departs from its Pattern, the starter Patterns included | Proposed task |
| A recurring task done more than one way, with no Pattern | Proposed task for a Pattern |
| An exception whose removal condition now holds | Proposed task |
| A settings entry that matches nothing, such as a `[map] unguided` directory, a `[kit] exclude` path or a CODEOWNERS path | Proposed task |
| Dead code: a module, function or check step that nothing reaches | Proposed task |

`devctl check` already fails on broken AGENTS.md links, exception entries that match no suppression, and Pattern references that do not resolve. CI keeps those at zero on the default branch, so the audit does not repeat them.

### The base rule and the starter Patterns

Every pass checks the code changed in its range against one base rule, whatever Patterns the project has: **fail fast and gracefully, and never hide or obscure an error.** Failing fast means stopping at the first sign that an operation cannot succeed, instead of carrying on with bad state. Failing gracefully means the error names the problem, keeps its cause and, where it can, says how to fix it. The audit looks for:

- an exception caught and dropped, or caught by a broad handler that carries on;
- a failure turned into a default value, an empty result or a success status;
- a retry or fallback that hides a failure that persists;
- an error message that loses the cause, or gives no hint of the fix.

The Kit also seeds a starter Pattern set for each stack: error handling, configuration that is typed, validated and documented, and input validation with typed enums rather than strings (Spec 1). The project owns and adapts them. The audit checks the changed code against each Pattern the project has, these included, and each proposed task cites the Pattern's lessons: what its reference does right.

### Scheduling

rapid-ship advises running `rs-garden` on a schedule, at least weekly, and once before each Pre-flight. A regular pass keeps the Corrections count complete and each drift fix small. How the pass is scheduled is the owner's choice: any scheduler that can start a Harness with no person present will do. A scheduled pass has no one to answer a prompt, so the Harness must allow, in advance, what the pass needs: git commits and pushes, `gh` reads, opening the PR, and writing to the tracker.

One option carries a warning, which the skill gives. A Harness's own GitHub Action on a `schedule` needs a model credential as a repository secret. [ADR 0002](../../adr/0002-github-gates-merges-reviews-run-locally.md) rejected such a secret for reviews, because a branch pushed to the same repository can edit a workflow and read it. rapid-ship allows this option as a short-term workaround; backlog item PRO-138 records the gap. The option has two more limits. A PR opened with `GITHUB_TOKEN` starts no workflow, so `devctl check` does not run on the pass PR. And the Apps' keys stay in the owner's Keychain (Spec 1), so the pass cannot act as the Worker App.

## 11. `rs-preflight`

**Purpose.** Run a Pre-flight: an advisory operational-readiness review before the owner widens the Mode toward Flight, like a readiness review before a product's general release. In Flight the owner reads fewer PRs, so metrics, Alarms and incident reports become the owner's main view of what agents ship. Each project and team sets these up differently, so rapid-ship cannot ship one setup. `rs-preflight` advises and guides the owner through this project's own. It never gates anything and never changes the Mode.

**When the owner runs it.** It is user-invoked, typically:

- before the first step from Walk toward Flight, once the project has merged PRs to measure;
- before each further step, when the owner shortens the escalation list again;
- after a change in how the project runs, such as a new deploy target, a new monitoring tool or a team joining;
- after an incident, to check that it reached the metrics and the ledger.

The owner may change the Mode without running it, and nothing runs it on a schedule.

**Inputs:**

- `[escalation]`, `[github]` and `[kit] optional` from `.rapid-ship/project.toml`, and `.rapid-ship/metrics.toml`.
- The output of `./devctl doctor`: the ruleset, CODEOWNERS, both Apps' installations and the Harness guardrail wiring.
- `./devctl metrics --json`: the window, each value, each unknown with its reason, and the PRs not gardened yet.
- The ledger in `docs/corrections/` and its `last-pass.toml`.
- README.md and ARCHITECTURE.md, for what the project is and how it runs.
- The owner's answers to what those files leave open.
- The owner's tracker, through the Harness's connection, only to propose tasks.

**Steps:**

1. **Preconditions.** Work in any clean checkout at `origin/<default branch>`, on any branch. Run `./devctl doctor` first, as `rs-lead` does (Spec 2, section 6.1). When doctor reports unreadable settings, stop and show its message and fix.
2. **Context.** Read README.md and ARCHITECTURE.md. Ask the owner only what they leave open: solo or team; what the project ships and where it runs; which monitoring, alerting and error tracking exist; and how incidents are reported today.
3. **Metrics to watch, and why.** Run `./devctl metrics --json`. If it exits 2, show its message and fix, and record the gap. For each metric, show its value and say what it tells the owner in Flight:

   | Metric | What it tells the owner in Flight |
   | --- | --- |
   | `revisions` | How often review sends work back. The Reviewer now judges most PRs without the owner, so rising Revisions mean Workers miss the bar more often |
   | `reverts` | Merged work that had to be undone, in whole or in part: what got past review |
   | `red_merges` | Merges that broke the default branch although each PR's own check passed |
   | `closed_unmerged` | Work the owner threw away, often a task sliced too large or specified too loosely |
   | `corrections` | Where people still hold the bar. Repeats point to a missing rung. Agents report it (section 9) |
   | Alarms, incidents, deploy rollbacks and failures | What users saw. These matter most once the owner reads fewer PRs |

   For each unknown, say what would make it known: Agent identity for Revisions, `git fetch` for PRs not fetched, a gardening pass for PRs not gardened. Say when the window is not full, because a few PRs make every number noisy, and advise waiting for a full window before the first step toward Flight. Compare each Suggested threshold with the project's history, and suggest a change where a default does not fit.
4. **Alarms and incidents.** Guide this project's setup, one signal at a time:
   1. List the signals with the owner: monitoring alerts, uptime probes, error tracking, deploys, incident reports and user reports. A library may have only releases and user reports.
   2. For each signal the owner wants counted, choose a route that devctl reads (section 7). Most alerting and error-tracking tools can open a GitHub issue with a label, which an `issues` metric counts. Most deploy tools can record a GitHub deployment, which a `deployments` metric counts. A signal that reaches neither needs a code metric in `devctl_project` that reads the tool's API; propose it as a task.
   3. For incidents, guide building an incident metric in `devctl_project` against the owner's own incident tool, such as PagerDuty or alarms posted to Slack. It follows the owner's own rules for recording an incident and its cause. It returns each incident with its URL and, where one is named, its cause, a PR or a commit, which `rs-garden` reads for Corrections (section 7). Propose it as a task.
   4. Give the steps to take in each outside tool: what to connect, and which label or environment to use. The owner makes those changes, or confirms each write first.
   5. Check that `./devctl metrics` reports each new metric with a value, not unknown. Where the tool can send a test alert, the owner may send one and see it counted, then remove the label from that issue.
   6. Suggest a threshold for each new metric, such as 0 Alarms in the window.

   A signal that cannot reach GitHub is a gap in the review, not a zero.
5. **Scheduled gardening.** Read `last-pass.toml` and the PRs not gardened yet; until a pass covers them, the Corrections count is a lower bound. Advise running `rs-garden` on a schedule and before each Pre-flight (section 10); how to schedule it is the owner's choice. Check whether the metrics Action is on. Without it, ask how the owner will see the report regularly.
6. **The escalation list.** Show `[escalation]` and the kinds that always apply, such as the Protected set (Spec 1). Ask which kinds of change the owner still wants to see in Flight, such as migrations, public API changes, authentication or billing. Suggest kinds that fit this project from ARCHITECTURE.md. When a kind is a set of paths, note that adding them to the Protected set lets the merge guard enforce it, and GitHub too with Agent identity and a ruleset (Spec 2, section 6.2).
7. **Agent identity, ruleset and guardrails.** From doctor's output, state whether Agent identity is on with both Apps installed, and whether the default branch has the ruleset. State whether CODEOWNERS matches the Mode, and whether the Harness wiring that carries the merge guard is in place. Give the advice that Spec 1 sets out for this owner's case: solo with a public repository or a paid plan, solo with a GitHub Free private repository, or a team. Explain what holds the Protected set in Flight here: the merge guard in every setup, and GitHub as well with Agent identity and a ruleset. Say plainly that the merge guard is a guardrail, which a misbehaving agent could get around. Without Agent identity, say that Revisions stay unknown and that Flight needs the ruleset to drop its review requirement (Spec 2, section 6.5). Where the Lead runs on a Harness that the Kit has no wiring for, such as pi, or Codex and agy until their wiring lands (Spec 1), say that the guardrails, the merge guard included, do not run there, so only the pre-commit hook, CI and any ruleset hold.
8. **The review.** Show the owner, area by area, what is in place, what is missing and the advice. End with the list of gaps. Give no verdict: whether and when to widen the Mode is the owner's call.
9. **Agreed changes.** With the owner's yes, open one PR with the repository changes they agreed to: thresholds and project-defined metrics in `metrics.toml`, and the metrics Action in `[kit] optional` installed with `rapid-ship sync --in-place`. All of these files are in the Protected set, so the owner approves and merges the PR. Run `./devctl check` first. With Agent identity, push and open the PR through `devctl as worker` (Spec 1). When the PR adds the Action under `.github/workflows/`, neither App may push it, so the owner pushes the branch and opens the PR in a terminal (Spec 1). Propose a task in the tracker for each change that needs code.
10. **Next.** When the owner decides to widen the Mode, point to `rs-lead`, which prepares that PR (Spec 2, section 6.5).

**Outputs:** the review, in the conversation; optionally one PR with the agreed settings; optionally proposed tasks in the tracker. `rs-preflight` keeps no record of a review beyond the conversation and that PR.

**Never:**

- Gate a Mode change, or give a ready or not-ready verdict.
- Change `[escalation]`, CODEOWNERS, the ruleset or the Mode.
- Merge a PR.
- Make a write outside the repository, such as creating a label or connecting a tool, without stating it and getting the owner's yes.
- Ask for a credential, or write one to a file, a command line or output.
- Start, schedule or stop an agent.

## 12. Kit changes

| Path | Kind | Change |
| --- | --- | --- |
| `.rapid-ship/metrics.toml` | seeded | New: window, Suggested thresholds and settings-sourced metrics, documented inline |
| `docs/corrections/README.md` | seeded | New: the ledger format, the statuses and which changes need the owner |
| `.github/workflows/rapid-ship-metrics.yml` | managed, optional | New: the scheduled Action |
| `.agents/skills/rs-garden/` and its `.claude/skills/rs-garden` link | managed | New skill |
| `.agents/skills/rs-preflight/` and its `.claude/skills/rs-preflight` link | managed | New skill |
| `tools/devctl/devctl/` | managed | New `metrics` command; the ledger's map rule; the ledger's Protected rule in the matcher that the diff step and the merge guard share |
| `tools/devctl/devctl_project/__init__.py` | seeded | New projects get a `metrics()` stub |
| `docs/AGENTS.md` | seeded | Points to `docs/corrections/` |

Every path above is in the Protected set by its path: through `.github/`, `.agents/`, `.claude/`, `tools/devctl/`, `.rapid-ship/` and every AGENTS.md, and `docs/corrections/README.md` through its own line, `/docs/corrections/README.md`, which this spec's plan adds to the seeded CODEOWNERS (Spec 1). In an existing project, `rapid-ship sync` proposes that CODEOWNERS line as a migration in its own PR (Spec 1, section 3). Spec 1's plan 4 already stopped seeding and reading `.rapid-ship/gate.toml`. In an existing project, `rapid-ship sync` adds the new seeded files where they are missing, and lists `docs/AGENTS.md` among the seeded files whose template changed, so the owner can add the pointer (Spec 1). It leaves `gate.toml` in place (section 6).

A plan for this spec can build it in six independent slices: `metrics.toml` with the basic metrics; project-defined metrics; the Action; the ledger with its map rule and Protected rule; `rs-garden`; `rs-preflight`.

## 13. What this spec needs from Specs 1 and 2

From Spec 1:

- The Agent identity settings in `project.toml` record each App's slug as well as its ID, so metrics can match bot authors without an App's key.
- `[kit] optional` can name a Kit file, here the metrics Action, not only a skill.
- The Kit's skills include `rs-preflight`, beside `rs-garden`.
- `rs-setup` shows the default Suggested thresholds, records the owner's values in `metrics.toml`, and offers the metrics Action. When Agent identity is off, it tells the owner that Revisions will be unknown. It points the owner to `rs-preflight` for Alarms and incidents before the first step toward Flight.
- The CI template gives each push run on the default branch its own concurrency group, so a later merge never cancels an earlier merge's run (section 3).
- The diff step's list of Protected changes and the merge guard share one matcher, which also applies the ledger's Protected rule (section 9). CODEOWNERS lists `/docs/corrections/README.md` in the Protected set.
- The diff cap leaves out `.md` files, so ledger entries and doc-only fixes do not count toward it.
- `rapid-ship sync` leaves a leftover `gate.toml` in place, and lists `docs/AGENTS.md` as a seeded file whose template changed (section 6).
- The starter Patterns for each stack, and the audit in `rs-health`'s `references/audit.md`, which covers the drift in section 10, the base rule and settings entries that match nothing.
- `devctl doctor` reports the ruleset, CODEOWNERS, both Apps and the Harness wiring, which `rs-preflight` reads.
- `project.toml` has no `[release]` table.

From Spec 2:

- `rs-review` posts each verdict in the format of Spec 2's section 3.6, with each blocking finding's rungs and prevention, so `rs-garden` can read them from GitHub.
- The Lead brief asks the Lead to add Corrections the owner gives in the Session to the ledger, as `open` entries in the format of section 9. Adding an entry needs no Protected PR.
- A task that prevents a repeated Correction sets its ledger entries to `implemented`. That change is Protected, so the owner signs it off.
- The `revision_rounds` escalation kind counts rounds by distinct head commit, as section 3 counts Revisions, but reads each verdict's first line, so that it works without Agent identity.
- `rs-lead` prepares the PR that widens the Mode once the owner decides, after `rs-preflight` or without it.
- `rs-work` undoes a merged commit only with `git revert`.

## 14. Dog-fooding

*This section describes this repository's own configuration, not product behaviour.* This repository validates the spec on itself and on hello-rapid-ship. Its `rs-garden` and `rs-preflight` proposals go to Linear, its tracker. Its agents sign in with vendor subscriptions only ([ADR 0001](../../adr/0001-subscription-logins-only.md)), so it schedules `rs-garden` through a Harness scheduler or cron on the owner's subscription, not through a GitHub Action with a model credential. It is a public repository on GitHub Free with a solo owner, the case where Agent identity matters most (Spec 1). Its two Apps were created on 2026-10-19 and are being turned on in PR #33, through plan 4's pending Owner steps. Its agent-PR window starts with the first PR the Worker App opens; earlier PRs were opened under the owner's account.

## 15. What changed

The owner's reviews of PR #27 on 2026-10-16 and 2026-10-19, the last of them round 2c, settled what this spec states. The open questions are in section 17.

## 16. Testing

**Unit tests**, offline. devctl reads GitHub only through `gh`, so these tests put a fake `gh` on `PATH` that serves recorded responses; the tests that use it are labelled simulated.

- `metrics.toml` validation: each problem listed with its key and the allowed values, an unknown key, `window` below 1, a large `window` accepted, and the `source` and `count` values; the note for a leftover `gate.toml`.
- The window over a local git fixture: the first-parent walk, a skipped direct push, selection by author with and without Agent identity, a window that is not full, and a merged PR that is not fetched.
- Revisions: distinct heads, two reviewers on one head, a dismissed review that requested changes, a review after the merge ignored, approvals ignored.
- Reverts: a `git revert` line, a reverted merge commit, the Revert button's body line, both signals counting once, an abbreviated SHA not counted, and a revert by hand that restores every file.
- Partial reverts over a local git fixture, each counted under `reverts` as partial: a restored file, an added file deleted, a deleted file brought back, an undone section, a section undone after other commits moved it, a section undone with small edits above the similarity threshold, one below it not counted, a hunk under 3 non-blank lines ignored, and a pure addition removed later not counted.
- Red merges: `failure`, `timed_out` and `success`; a cancelled run and a missing run as unknown; a passing rerun that does not clear a failed first attempt.
- Closed unmerged: a PR closed by an App not counted with Agent identity; a PR closed, reopened and merged not counted.
- Corrections: totals, an entry with two rungs, repeats, and PRs not gardened after `through`.
- The status rule, table-driven over `v`, `u` and `m`; a window with no PRs; `needs Agent identity`.
- Exit codes, the fix named in each exit-2 message, and `--post` refusing outside GitHub Actions. An API allowance used up mid-run: the affected metrics unknown with the reason and reset time, and no exit 2.
- `--post` with the fake `gh`: opening the issue, replacing its body, commenting only on a status change, and the first-run comment.
- Project-defined metrics: the `issues` source, `deployments` rollbacks by ancestry and failures, a code metric returning a value, returning unknown, raising, and timing out, and an incident metric returning records with and without a cause, and marked `incident` when it returns no record and when it is unknown.
- The ledger's map rule: each required field, a field outside the table, each status's extra field, references in `prevented_by`, and `last-pass.toml`.
- The ledger's Protected rule: an added entry, whatever its status, and a `last-pass.toml` update are not Protected; an edited, renamed or removed entry and a status change are. A `README.md` change is Protected through its CODEOWNERS line.
- The JSON output against a recorded report.

**Integration tests**, offline and labelled as such:

- `init` on scratch repositories for each stack, and for one with two stacks, seeds `metrics.toml` and `docs/corrections/README.md`, and `./devctl check` passes.
- `sync` on a project that has `gate.toml` adds `metrics.toml`, leaves `gate.toml` in place, and lists `docs/AGENTS.md` as a seeded file whose template changed (Spec 1).

**Live trials**, recorded under `docs/trials/`:

- `devctl metrics` against a scratch repository on GitHub that has: a PR reverted with the Revert button and one with `git revert`, a PR partly reverted by restoring one file and another by undoing one section, a red merge, two quick merges whose push runs both complete, a PR closed unmerged, and a dismissed review that requested changes. The trial confirms the GitHub behaviour this spec relies on, including what the `review_dismissed` event records and the Revert button's body line. It records each partial revert that the content check missed or invented, including sections undone with small edits, and tunes the similarity threshold from that. It runs with and without Agent identity.
- The Action on the same repository: its permissions suffice, it opens the issue, replaces the body and comments only on a change.
- `rs-garden` on a scratch repository with prepared PRs: a blocking finding that was fixed, a nit that was skipped, a request from the owner, two Corrections in one category, a severe first Correction, an incident record, returned by a project's incident metric, that names its cause PR, another incident record dated after the last pass but before the window's span, which the pass reaches only by widening the window, a swallowed exception, a stale README command, a departure from a starter Pattern, and an exception whose removal condition holds. The trial records the entries, proposals and doc-only fixes it produced against the expected list, in at least two Harnesses, such as Claude Code and Codex. The output comes from a model, so the trial records a result; it is not a pass or fail test.
- One unattended, scheduled `rs-garden` pass, which confirms what the Harness must allow in advance.
- `rs-preflight` on hello-rapid-ship with and without Agent identity, and on a scratch service that records GitHub deployments. The trial records the review, the settings PR, the tasks it proposed and the outside steps it guided. A model writes the review, so the trial records a result, not a pass or fail.

**Dog-food:** this repository runs `devctl metrics`, `rs-garden` and `rs-preflight` on itself and on hello-rapid-ship.

## 17. Open items

The owner settled every drafter proposal on 2026-10-16 and 2026-10-19, the last ones in round 2c (section 15). What remains is a fact the live trial measures and two questions the owner left open.

- **The similarity threshold for partial reverts.** An undone section matches at a similarity ratio of at least 0.8 (section 3). The live trial records each partial revert that the content check missed or invented, and tunes the threshold from that.
- **Unknown and the exit code.** An unknown status never changes the exit code. Whether to add a `--strict` option that also exits 1 on an unknown status, like `rapid-ship status --strict`, is still open.
- **Lower limits.** Every Suggested threshold is an upper limit. A project-defined metric where more is better, such as deploys per week, has no lower limit yet.
