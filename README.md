![rapid-ship — Ship more. Supervise less.](asset/public/banner.jpeg)

[![devctl check](https://github.com/proxy-hatch/rapid-ship/actions/workflows/devctl-check.yml/badge.svg?branch=main)](https://github.com/proxy-hatch/rapid-ship/actions/workflows/devctl-check.yml)

**Hand more of your delivery to coding agents, and keep the evidence that the work is right.**

rapid-ship does for a team of coding agents what senior engineers do for a team of people: it helps define the architecture, breaks delivery into tasks, and sets and holds the code-quality bar. The Harness you work in, such as Claude Code, Codex CLI or Antigravity CLI, runs the agents.

rapid-ship installs a Kit into your repository: a project CLI called devctl, an AGENTS.md tree, starter Patterns, guardrail settings, a CI workflow and a set of skills. A repository can hold several stacks, such as a Python backend and a React TypeScript frontend. Tasks live in whichever issue tracker your Harness can reach.

`devctl check` is the one entry point for every check, in the pre-commit hook and in CI. In each Harness wired to the guardrails, the merge guard denies an agent's merge until `devctl check` passes on the PR's head commit. It also leaves every PR that touches the Protected set for you to merge. Where GitHub offers rulesets, a ruleset on your default branch also requires the check and code-owner review. Optional Agent identity gives your agents their own GitHub Apps, on a repository that you or an organisation owns.

You choose the Mode. In Walk the Lead, your lead agent, merges a PR only when you say so. In Flight the Lead merges a change itself once its checks and review pass. It still brings you every change to the Protected set, such as CI, guardrails, agent instructions and settings, and any other kind of change you name. Before you widen the Mode toward Flight, `rs-preflight` reviews your project's readiness with you; it advises and never gates. Flight lasts until you change the Mode. rapid-ship sets no cap on how many Workers run at once; in Walk, where you watch them, it advises at most 3.

## Status

rapid-ship is being rebuilt. [Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) is built in seven plans, and plans 1 to 3 work today: `rapid-ship init` vendors the Kit into a repository, `status` compares the repository with the Kit, `sync` proposes Kit updates as a PR, and `./devctl check` runs the checks in the pre-commit hook and in CI. No release is tagged yet; [Architecture](ARCHITECTURE.md) says how to run `rapid-ship` from a checkout. The other four plans follow in order:

- Plan 4 adds `devctl doctor` and the optional Agent identity. It is built in PRs #31 to #33, which are not merged yet.
- Plan 5 adds Kit standards, the Python starter Patterns, the Harness guardrails and the merge guard.
- Plan 6 adds the TypeScript stack and several stacks in one repository.
- Plan 7 adds the setup skills, `rs-setup` and `rs-health`.

[Spec 2](docs/superpowers/specs/2026-10-16-delivery-skills-design.md) adds the delivery skills, and [Spec 3](docs/superpowers/specs/2026-10-16-metrics-and-gardening-design.md) the metrics, gardening and `rs-preflight`.

*Dog-fooding:* this repository is built with its own Kit, and tracks its own tasks in Linear.

The earlier version, a local controller also named devctl, was removed on 2026-10-14. Its code and guides are kept at the git tag [`archive/controller-2026-10`](https://github.com/proxy-hatch/rapid-ship/tree/archive/controller-2026-10). Only its getting-started walkthrough remains on this site, marked historical.

## Read more

- [rapid-ship design](docs/superpowers/specs/2026-10-14-rapid-ship-design.md): the problem, where rapid-ship stops and your Harness takes over, and how the code-quality bar is held.
- [Spec 1: Kit and Setup](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md): what is built first, in [seven plans](docs/superpowers/plans/2026-10-14-kit-and-setup.md).
- [Architecture](ARCHITECTURE.md): what this repository holds today and how to develop it.

## Credits

Our engineering workflows adapt [Matt Pocock's skills](https://github.com/mattpocock/skills/), with [Ponytail](https://github.com/DietrichGebert/ponytail) by Dietrich Gebert. Thank you for sharing them. [Skill sources and credits](docs/credits.md).
