---
status: accepted
---

# GitHub gates merges; Agent identity is optional

Checks run in the project's CI on GitHub. Where GitHub offers rulesets, on public repositories and on private ones with a paid plan, the ruleset decides what merges, and with Agent identity CODEOWNERS also decides whose approval a merge needs. The merge guard, a rule of `devctl hook` that is on in every setup in each Harness wired to it, also denies an agent's merge when `devctl check` has not passed on the pull request's head commit, or when the pull request touches the Protected set. A GitHub Free private repository has no rulesets, so there the merge guard is the enforcement.

rapid-ship therefore keeps no local evidence store, policy store or merge broker. Reviews run wherever the Lead's Harness runs them: a subagent following `rs-review`, another vendor's CLI, or the Lead itself. rapid-ship ships the review skill, not a review runner.

Agent identity is an optional feature. `rapid-ship app` creates two GitHub Apps: the Worker App opens and merges pull requests, and the Reviewer App posts reviews. With Agent identity on, agents make their GitHub writes through `devctl as`, one thin command that runs `gh` and `git push` with an App's short-lived token. The Kit's Harness guardrails then deny `git push` and `gh` writes made as the owner. `rs-setup` explains what Agent identity buys and costs and gives the advice below, and the owner opts in or not.

GitHub never lets a pull request's author approve or request changes on it, on any plan. Agent identity therefore buys four things:

1. The owner can formally approve agent pull requests, so merges need no admin bypass. In a team, teammates' approvals cover this without it.
2. The Reviewer's verdicts are real GitHub reviews, so Revisions can be counted.
3. Agent pull requests can be told apart from the owner's, which every per-agent-PR metric needs.
4. CODEOWNERS binds the Lead in Flight while the Lead acts through `devctl as`, because an App cannot use the owner's bypass.

Without Agent identity, agents act as the owner and these four are lost:

1. The owner cannot approve an agent's pull request, so a solo owner merges it through the admin bypass.
2. The Reviewer's verdicts are comments from the owner's account, not reviews.
3. Revisions and the other per-agent-PR metrics report "unknown: needs Agent identity". Metrics over all pull requests still work: Reverts, red default-branch CI after a merge, and pull requests closed unmerged.
4. In Flight, the ruleset must drop its review requirement so that the Lead can merge without a person's approval. CODEOWNERS then binds no one, and the merge guard holds the Protected set: it denies an agent's merge of a Protected-set pull request, which the owner merges in GitHub's web interface. `rs-lead` explains this, and the owner decides.

## When to set up Agent identity

Agent identity matters most for a solo owner on GitHub Free with a public repository. GitHub enforces the ruleset there, the owner cannot approve a pull request their own account opened, and every agent comment and review appears publicly as the owner's.

| Setup | Agent identity | Why |
| --- | --- | --- |
| Solo owner, public repository or paid plan | Recommended | It is the only way the owner can approve agent pull requests, and GitHub binds the Lead |
| Solo owner, GitHub Free private repository | Recommended, for real reviews and metrics | There is no ruleset, so the merge guard holds the bar with or without it |
| Team | Optional | Teammates approve agent pull requests anyway. The Apps add per-agent metrics, real Reviewer reviews and a Lead that CODEOWNERS binds in Flight |

A team shares one Worker App and one Reviewer App per repository owner, the personal account or organisation that owns the repositories. For an organisation, an admin creates them once (backlog item PRO-105). Each developer holds their own private key for each App, since GitHub allows up to 25 keys per App, and keeps it in their own Keychain. One person's key can then be revoked without touching anyone else's. Who generates each key depends on who owns the Apps:

- **An organisation:** the admin makes each developer an App manager of both Apps, and each developer generates their own key. GitHub documents that App managers manage an App's settings, but not that this includes generating its private keys.
- **A personal account:** GitHub offers App managers only to organisations. The account owner generates one key for each collaborator and hands it over securely, or moves the Apps to an organisation.

These key steps are a proposal, not yet verified ([rapid-ship design](../superpowers/specs/2026-10-14-rapid-ship-design.md#open)). PRO-105 settles them, and how a developer imports such a key and keeps it beside the keys of Apps they own: as built, the Keychain holds one key per role on a machine.

## Considered options

- **Agent identity as a requirement** (the design before 2026-10-16). Rejected: it costs every owner two Apps, keys in the macOS Keychain and extra Harness settings, while a team's approvals already cover its first benefit.
- **Agents always act under the owner's GitHub account, with no App option.** Rejected: the owner could never approve agent pull requests, Revisions could never be counted, and CODEOWNERS could never bind the Lead in Flight.
- **A pair of Apps for each developer in a team.** Rejected: it multiplies the installations to manage, and splits one role's reviews across several identities.
- **devctl commands that push, review and merge as steps of a flow.** Rejected with the flow itself ([ADR 0004](0004-team-management-boundary.md)). Only the thin command for `gh` and `git push` remains, and only under Agent identity.
- **A Reviewer in GitHub Actions.** Rejected: CI stays deterministic and needs no model sign-in, a model token in GitHub secrets is reachable by a same-repository branch that edits the workflow, and reviewing is the Lead's Harness's job.
- **A local broker with sealed receipts** (the design before 2026-10-14). Rejected: about 1,100 lines that no command could reach, guarding what GitHub already binds to the head commit.

## Consequences

- Where GitHub offers rulesets, one ruleset on the default branch requires a pull request with code-owner review, every review thread resolved, and a passing `devctl check` reported by GitHub Actions. It allows squash merges only and blocks force pushes. Only the repository admin role may bypass it, and only when merging a pull request.
- GitHub Free private repositories have no rulesets, so GitHub gates no merge there (backlog item PRO-100). The merge guard rejects an agent's merge there while `devctl check` has not passed on the head commit.
- With or without Agent identity, the Kit's Harness guardrails deny the other ways to land a change on the default branch that `devctl hook` recognises: a `git push` to that branch, and the merges, ref writes and commits through `gh api`, REST and GraphQL, that [Spec 1](../superpowers/specs/2026-10-14-kit-and-setup-design.md#the-merge-guard) lists. `gh pr merge` is then the only recognised way for an agent to merge, and the merge guard checks each such command. The hook matches command lines, so a script or a tool it does not see gets past it. The owner merges a Protected-set pull request in GitHub's web interface.
- The Kit's Harness guardrails deny every agent `gh pr merge --admin`, with or without Agent identity.
- With Agent identity, CODEOWNERS `*` enforces Walk: every pull request needs the owner's approval, and an App cannot bypass the ruleset.
- Neither App has the Workflows, Administration or Checks permission, and neither is a code owner, so an App's approval never stands in for the owner's.
- Each App's private key is stored in the macOS Keychain, which makes Agent identity macOS-only. In a team, each developer keeps their own key in their own Keychain, once PRO-105 settles how a key is imported. devctl mints a short-lived installation token for each command and holds it only in memory. No key or token is written to disk, a command line or output.
- Any process the owner runs can read both keys, so a Worker can reach the Reviewer App. `rs-work` tells Workers never to post reviews or act as that App. No technical barrier is planned until misuse is observed.
- A misbehaving agent on the owner's machine can bypass any guardrail, the merge guard included, and act as the owner, with or without Agent identity. Guardrails stop habits and mistakes, not a determined agent.
- A scheduled gardening pass in GitHub Actions needs a model credential as a repository secret, which is the risk that rejected a Reviewer in GitHub Actions. [Spec 3](../superpowers/specs/2026-10-16-metrics-and-gardening-design.md) keeps that option as a short-term workaround that carries this warning, and backlog item PRO-138 records the gap.
