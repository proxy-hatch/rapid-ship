# rapid-ship

rapid-ship is being rebuilt as a Kit that a repository vendors: a project CLI called devctl, an AGENTS.md tree, starter Patterns, guardrail settings, a CI workflow and `rs-` skills. The `rapid-ship` command writes and updates the Kit. Nothing runs as a service, and the owner's Harness runs the agents ([ADR 0004](docs/adr/0004-team-management-boundary.md)). The [rapid-ship design](docs/superpowers/specs/2026-10-14-rapid-ship-design.md) describes the product. [Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) is built in the seven plans of its [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md), and [ARCHITECTURE.md](ARCHITECTURE.md) describes what exists today.

Plans 1 to 5 are built: `rapid-ship init`, `status`, `sync` and `app`, and `devctl check`, `doctor`, `as` and `hook`. Plan 4 and its follow-ups are merged in PRs #31 to #33, and the owner tagged `v0.1.0`: `rapid-ship app` supports repositories that an organisation owns, and `app --import-key` stores a developer's own key. Plan 5 is built in PRs 5.1 to 5.5: the hook spike (PRO-139); `devctl hook claude pre-tool` with G1 to G5, G7, G8, the merge guard and the seeded Claude Code wiring; the README.md and ARCHITECTURE.md seeds with map rule 8, `doctor --settings`, the Pattern `task` key and Lessons section, the Python starter Patterns, the `SKILL.md` rule, the 1,500-line diff cap, the Corrections ledger rule and one CI concurrency group for each push run; settings seeds that comment each key's contract, with loaders that name what each key accepts; and the `dead-code` check step for Python, with vulture and deptry. Before GA, the documentation release (plan 7's PR 7.4), the Kit keeps no backward compatibility: `sync` never edits a seeded file, and a new check fails at once ([Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) section 3). This repository vendors its own Kit, so `devctl`, `tools/devctl/`, `.githooks/`, `.github/workflows/devctl-check.yml` and the settings in `.rapid-ship/` come from its templates. Not built yet:

- Plan 6, the TypeScript stack and several stacks in one repository.
- [Plan 7](docs/superpowers/plans/2026-10-26-rs-setup-and-rs-health.md), `rs-setup` and `rs-health`: document written, awaiting owner approval; implementation unbuilt.
- [Spec 3](docs/superpowers/specs/2026-10-16-metrics-and-gardening-design.md)'s metrics, gardening and `rs-preflight`. Its plan is written next. GA includes Spec 3, so plan 7's PR 7.4 lands after it.

The settings hold the code owner, the Mode (`[escalation] every_pr`) and each App's ID and slug. devctl refuses the `[agents]`, `[linear]`, `[dispatch]` and `[release]` tables from before the re-scope, and the `[roster]` table that plan 4 built. rapid-ship does not run agents across several Providers, so nothing replaces `[agents]` or `[roster]`. The Kit no longer seeds or reads `gate.toml`. The design sets no cap on the number of agents; it only advises at most 3 agents at work at once in Walk.

## Commands

- Run `./devctl doctor --settings` first in each Session, unless the Session runs the full `./devctl doctor`; it checks the settings files and asks GitHub nothing.
- Setup: `uv sync --locked`, then `git config core.hooksPath .githooks`.
- Full check, the same tier CI runs: `./devctl check`. It and `uv run pytest` need network access and gitleaks 8.30.1 on `PATH`.
- Fast check, which the pre-commit hook runs: `./devctl check --tier fast`.
- Doctor: `./devctl doctor` reports what this machine, this repository and its GitHub settings lack; `--skills` also starts one headless Claude Code Session when `claude` is on `PATH`, and `--settings` checks only git, the settings files and the Claude Code wiring.
- Tests: `uv run pytest`; devctl's tests only: `uv run pytest tests/devctl`.
- After changing a Kit template: `uv run rapid-ship sync --in-place`, then `uv run rapid-ship status --strict`.
- Documentation site: `npm --prefix website ci --no-audit --no-fund` once, then `npm --prefix website run build`.

## Find the change

Read the directory guide before editing there; parent instructions still apply. Small resource and reference folders inherit their nearest guide.

| Work | Start here |
| --- | --- |
| What the project does, and how to run and check it | [README](README.md) |
| The `rapid-ship` package, its file helpers and the engineering skill | [Source map](rapid_ship/AGENTS.md) |
| `rapid-ship init`, `status` and `sync`, and the lock | [Kit CLI](rapid_ship/kit/AGENTS.md) |
| Kit templates, including the source of the vendored `devctl`, `tools/devctl/devctl/`, hook and CI workflow: edit the template, then sync | [Kit templates](rapid_ship/templates/AGENTS.md) |
| The vendored devctl, and this repository's own check steps in `tools/devctl/devctl_project/` | [Tools](tools/AGENTS.md) |
| This repository's Kit settings (`.rapid-ship/`); `rapid-ship` writes the lock, so never edit it by hand | [project.toml](.rapid-ship/project.toml), [exceptions.toml](.rapid-ship/exceptions.toml), [kit.lock](.rapid-ship/kit.lock) |
| The secrets step's settings: gitleaks's default rules, plus an allowlist for the placeholder key that a plan document quotes. Protected | [.gitleaks.toml](.gitleaks.toml) |
| Tests | [Tests](tests/AGENTS.md) |
| The distribution smoke that the `distribution` check step runs | [Scripts](scripts/AGENTS.md) |
| Designs, plans, ADRs and trials | [Documentation](docs/AGENTS.md) |
| Documentation site and public images | [Website](website/AGENTS.md), [assets](asset/AGENTS.md) |
| CI, documentation deployment and CODEOWNERS, which lists the Protected set | [Workflows](.github/AGENTS.md) |
| Agent skill discovery | [`.agents/skills`](.agents/AGENTS.md), [`.claude/skills`](.claude/AGENTS.md) |

When adding or moving a maintained directory, update its guide and parent navigation in the same change. Keep one canonical implementation and point to it. Build output, caches, worktrees and ignored local state are generated, not source directories to document.

## Writing

Read `.agents/skills/rapid-ship-engineering/references/writing.md` before writing commits, PRs, documentation or agent reports. Use the terms in [GLOSSARY.md](GLOSSARY.md), and read the [ADRs](docs/adr/) before reopening a settled decision.

Lead with the outcome or problem. Prefer one precise finding over several vague ones; name the problem, consequence and file:line. Keep exact commands, limits and safety conditions.

Prefer clear names, types, and simple control flow. Add comments only when they convey a contract, rationale, invariant, or external constraint that the code does not adequately express. Keep local explanations beside the relevant code and broader design reasoning in linked documentation; a comment never cites the document, plan, trial or decision behind the code, such as a spec section, ADR, PR or rule ID, because documentation points to code, not the reverse. Update comments with behaviour changes, and investigate existing constraint comments before removing them. The Kit seeds this rule and the Development bullets on workarounds, tests and refactors as Rules in each project's root guide.

## Development

- Before coding or review, read `.agents/skills/rapid-ship-engineering/references/ponytail.md`. Use the engineering skill for clarification, TDD, debugging, architecture work and review.
- Build what the current plan names. Write the test first, and keep each task small enough to check on its own.
- A comment does not make a workaround acceptable. Fix the root cause within scope, or explicitly report the limitation. A necessary workaround must have a verified reason, appropriate validation, and a tracked removal condition when temporary.
- Do not invent explanations, weaken tests, or suppress correctness checks to make a change appear complete.
- Do not introduce unnecessary abstractions or broaden a refactor just to eliminate a useful comment.
- Work on a branch and merge through a PR after independent review.
- Put each rule that prevents a repeated Correction on the rung that fits its purpose. A safe interface removes structural misuse; a check catches local or stylistic problems; one bad pattern can need both. Use a skill or advisory Rule only for what neither can carry.
- A missing metric is unknown, not zero. A Suggested threshold breach is reported, never acted on.

## This repository's own rules

These are this repository's choices, not product behaviour. Product text names them only in a section marked as dog-fooding.

- Linear is this repository's tracker. Maintainers keep its tasks there; GitHub holds code, checks and PRs. Connect Linear through its official MCP or API, never a third-party CLI.
- Outside contributors cannot see Linear. They use GitHub issues and PRs, and maintainers triage those into Linear. Do not copy Linear tasks into GitHub issues: backlog item PRO-103 covers exposing selected Linear issues on GitHub.
- Agents sign in with vendor subscriptions only, never an API key, gateway or proxy, because Providers have suspended accounts that used third-party clients or gateways.
- agy is never a Reviewer.
- This repository records its Worker App, `proxy-hatch-rs-worker`, and its Reviewer App, `proxy-hatch-rs-reviewer`, under `[github]` in [project.toml](.rapid-ship/project.toml), so Agent identity is on here.

## Safety

- Label offline and simulated tests. A blocked, skipped or simulated check never counts as passed; missing credentials block the step.
- A review applies to one head commit. A Worker's own report is not independent verification.
- Record an external operation before sending it. Resolve an uncertain result before retrying.
- Worktrees isolate source only, not processes, credentials or ports.
- No silent increase in permissions or automatic approval.
- Never write a GitHub App private key or token to disk, a command line or output.
