# Architecture

rapid-ship is being rebuilt as a Kit that projects vendor into their repositories; the [rapid-ship design](docs/superpowers/specs/2026-10-14-rapid-ship-design.md) describes it. [Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) builds the Kit and Setup in seven plans, listed in its [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md). Plans 1 to 4 are built and merged, plan 4 and its follow-ups in PRs #31 to #33, and the first release, `v0.1.0`, is tagged. Plan 5 is built in PRs 5.1 to 5.5: the hook spike's record; `devctl hook` with the merge guard and its Claude Code wiring; the standards, such as the README.md and ARCHITECTURE.md seeds, `doctor --settings`, the Python starter Patterns, the diff cap and the ledger rule; settings seeds that comment each key's contract; and the `dead-code` check step for Python. This page describes what the repository holds today, how the parts fit together and how to work on them.

## What exists today

| Part | Where | What it does |
| --- | --- | --- |
| `rapid-ship` CLI | `rapid_ship/cli.py`, `rapid_ship/kit/`, `rapid_ship/github_app.py`, `app_import.py`, `app_flow.py`, `app_keychain.py` | `init`, `status` and `sync`: writes the Kit into a repository and keeps it current. `app`: finds or creates the Worker and Reviewer Apps of the repository's owner, a person or an organisation, for Agent identity; `app --import-key` stores a developer's own key for an App that exists |
| Kit templates | `rapid_ship/templates/` | `kit.toml` and three layers, `common/`, `python/` and `agnostic/`, which the commands render and the wheel ships |
| devctl | `tools/devctl/`, run through the `devctl` shim | `devctl check`, the one entry point for every check, in the pre-commit hook and in CI; `devctl doctor`, which reports what this machine and repository lack; `devctl as`, Agent identity's command for `gh` and `git push`; `devctl hook`, the Harness guardrails with the merge guard, which Claude Code runs before each shell command and file edit |
| This repository's check steps | `tools/devctl/devctl_project/` | `vendored`, `distribution` and `python-3.12`, after the Kit's steps |
| Vendored Kit | `devctl`, `tools/devctl/` (the `devctl` package, `pyproject.toml`, `uv.lock`, `.gitignore`), `.githooks/pre-commit`, `.github/workflows/devctl-check.yml` | Managed files from this repository's own `rapid-ship init`, kept equal to the templates. `rapid-ship` writes `.rapid-ship/kit.lock` itself; it is not a template |
| Seeded files | `.rapid-ship/project.toml` and `exceptions.toml`, `tools/devctl/devctl_project/`, `.github/CODEOWNERS`, `.claude/settings.json`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`, `docs/AGENTS.md`, `tools/AGENTS.md`, `docs/features/README.md`, `docs/patterns/README.md` | Kit files this repository owns; `sync` never rewrites them |
| File helpers | `rapid_ship/files.py` | Atomic replacement, create-only writes and safe paths for the Kit writers |
| Distribution smoke | `scripts/smoke_distribution.py` | Checks the built wheel and runs its `rapid-ship` in scratch repositories |
| Engineering skill | `rapid_ship/skills/rapid-ship-engineering/`, linked from `.agents/skills/` and `.claude/skills/` | Guides agents working on this repository until plan 7's Kit skills replace it |
| Documentation site | `website/` | Builds the Markdown in this repository; rewritten once the product works |

Nothing here runs as a service. Plans 6 and 7 of Spec 1, Spec 2 and Spec 3 are designed but not built ([Designed, not built](#designed-not-built)).

## The rapid-ship CLI

`rapid-ship` writes and updates the Kit. Run it with `uv run rapid-ship` here. In another repository, run `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<version> rapid-ship <command>` for a release the owner tagged `v<version>` on `main`, the first being `v0.1.0`, or `uvx --from <local checkout> rapid-ship <command>` for a version that has no tag yet. The package is not on PyPI. A command exits 0 on success, 1 when a check failed or the repository's state refused the request, and 2 when it could not run.

- `init` vendors the Kit at the top of a git work tree. The work tree must be clean, with no `.rapid-ship/kit.lock` and no branch `rapid-ship/init`. Without `--stack`, a repository with `pyproject.toml` gets the Python stack, and one without it cannot run (exit 2); pass `--stack python` or `--stack agnostic`. `--owner`, `--repository`, `--name` and `--package` fill the template variables. `init` commits the Kit on a new branch, `rapid-ship/init`; a repository with no commits gets the Kit as its first commit on the current branch instead.
- `init` never edits an existing file and runs no project code or git hook. It writes nothing when a managed file already exists. It skips an existing seeded file, a symlink included, and lists it for `rs-setup`. Before it writes, it looks for the tool settings, hooks and workflows the repository already has, such as Ruff or mypy settings, `.pre-commit-config.yaml`, executable hooks in the git hooks directory and files in `.github/workflows/`. After a successful run it lists them, because devctl's checks can overlap or conflict with them. A conflict or failure lists nothing, and a file it cannot read is listed as unreadable. A failed switch, write or commit removes what `init` created and returns to the starting branch.
- `status` compares the repository with the lock and the installed templates, and never writes. It reports each managed file as unchanged, modified or missing, each seeded file whose template changed as `template updated`, and each path under `[kit] exclude` as excluded. A managed lock entry that the installed template no longer matches, or that the installed Kit dropped, is `outdated`; this repository shows it right after a template edit and before `sync --in-place`. A managed template of the installed Kit that the lock does not list yet, such as a file a newer Kit added, is `not installed`. `--strict` exits 1 unless every managed file that is not excluded is unchanged and matches the current template. `--json` prints the report as data.
- `sync` brings the vendored Kit to the installed templates. It replaces unchanged managed files, adds new ones and deletes unchanged ones the Kit dropped. A managed file the project edited or deleted becomes the project's own: sync leaves it as it is, records it as seeded and prints how to give it back with `sync --revert <path>`. It never changes a seeded or project-authored file, and records the new template hash of a seeded file whose template changed. Without `--in-place` it commits on `rapid-ship/kit-sync-<version>` and opens a PR with `gh`; with `--in-place` it writes the work tree only. A failed write restores the work tree.

## Kit templates and layers

`rapid_ship/templates/kit.toml` lists the seeded files, the new-project seeds, the executable files, the optional skills and the template variables. Every other template is managed.

- `common/` holds the files for every stack: the `devctl` shim, `tools/devctl/`, the CI workflow, the pre-commit hook, the settings seeds, CODEOWNERS, the guide skeletons and the README.md and ARCHITECTURE.md seeds.
- `python/` adds or overrides files for the Python stack: a seeded `pyproject.toml` with the guardrail settings, a source and test skeleton, four starter Patterns with their reference code and tests, and its own `project.toml`, root guide and CODEOWNERS. Its CODEOWNERS adds the Python tools' settings files to the Protected set. Where a stack file and a common file share a path, the stack's wins.
- `agnostic/` holds only the stack-agnostic `.rapid-ship/project.toml` today.

A managed file is copied byte for byte, and `sync` replaces it with each new template. A seeded file substitutes `{{project_name}}`, `{{package}}`, `{{owner}}`, `{{repository}}` and `{{code_owner}}`, is written once and then belongs to the project. An empty owner or repository renders as `<owner>` or `<repository>` and comments out its line, which only TOML and CODEOWNERS templates allow. `{{code_owner}}` is `@` and the owner, or empty without an owner, so the seed's `code_owner = ""` stays unset rather than a placeholder. The Python stack's new-project seeds, a `pyproject.toml`, a skeleton package and test, and the four starter Patterns with their reference code and tests, are written only when `init` finds no `pyproject.toml`. Each `.claude/skills/<name>` is a relative symlink to `.agents/skills/<name>`; the Kit has no skills yet. A project lists the Kit paths it owns under `[kit] exclude` in `.rapid-ship/project.toml`, and `sync` never touches them.

`README.md` and `ARCHITECTURE.md` are seeded skeletons whose only variable is `{{project_name}}`; `init` skips one that exists, and map rule 8 checks both. The root guide skeletons gain a first command, `./devctl doctor --settings`, and a README and an Architecture row in Find the change. After their Rules, both hold a Pull requests section: how an agent opens, reviews, merges and undoes a pull request, through `./devctl as` when Agent identity is on.

The Python starter Patterns are `docs/patterns/python-error-handling.md`, `python-configuration.md`, `python-input-validation.md` and `python-performance.md`. Each Pattern has a `task`, a `reference` module in `src/<package>/` (`errors.py`, `settings.py`, `inputs.py` and `profiling.py`) with a test in `tests/`, its `enforced_by` checks and a `## Lessons` section. The seeded `pyproject.toml` bans `os.environ` and `os.getenv` through Ruff's `banned-api` and allows them in `settings.py` alone with a per-file entry, and the Python CODEOWNERS seed lists the four Pattern files, commented out, right after `/.rapid-ship/`. The performance Pattern documents `uvx py-spy record -o profile.svg -- .venv/bin/python -m <package>.profiling`, whose `--rounds` option defaults to 5,000,000; no check runs a profiler.

The `project.toml` seeds hold the settings of the re-scope: `[github]` with the code owner and each App's ID and slug, and `[escalation] every_pr`, the Mode: `true`, the seed, is Walk, and `false` is Flight. The merge guard enforces the Mode, and doctor checks CODEOWNERS and the ruleset against it. The table has no other key, so devctl rejects the `kinds` and `revision_rounds` it once held as unknown keys. devctl refuses the `[agents]`, `[linear]`, `[dispatch]` and `[release]` tables from before the re-scope, and the `[roster]` table that plan 4 built. Each message says why the table went and asks the project to delete it. For `[agents]` and `[roster]`, the reason is that rapid-ship does not run agents across several Providers; the owner's Harness chooses each agent's model. The Kit no longer seeds or reads `gate.toml`. The design sets no cap on the number of agents; it only advises at most 3 agents at work at once in Walk.

A seed comments a key only where its name and value do not show its contract: the values or units it accepts, a default that is not obvious, or a constraint, such as a Protected file. The `exceptions.toml` seed's commented example names each key. `tests/test_kit_seed_keys.py` holds each seed to the keys its loader accepts: `PROJECT_KEYS` and `EXCEPTION_KEYS` in devctl's `settings.py`. The loader's error for an unknown key names what its table accepts. It requires `[map] source_roots`, `[map] unguided` and `[tests] unit` to name paths inside the repository, and accepts in `[kit] optional` only the Kit's optional skills, `OPTIONAL_SKILLS`, none in Kit 0.2.0; a test holds that set equal to `kit.toml`'s `optional_skills`.

## The lock

`.rapid-ship/kit.lock` records the Kit version, the stack, the variables and one entry per Kit file: a content hash for a managed file, a link target for a managed symlink and the template's hash for a seeded file. An entry moves from managed to seeded when the project edits or deletes the file, and back through `sync --revert`. The Kit version is the package version. `rapid-ship` writes the lock; nobody edits it by hand.

## devctl and `devctl check`

The `devctl` shim runs devctl with `uv run --project tools/devctl --frozen`, so devctl has its own `pyproject.toml`, `uv.lock` and environment, apart from the project's. It depends only on PyYAML and PyJWT with its crypto extra. devctl has `--version`, `check`, `doctor`, `as` and `hook`, plus any verbs the project registers in `tools/devctl/devctl_project/`; this repository registers none.

`./devctl check [--tier fast|full] [--json] [--base REV] [--pr-body PATH]` runs the steps below in order and prints one line per step: passed, failed, blocked or not applicable. It exits 0 when every applicable step passed, 1 when a step failed and 2 when a step could not run. A blocked step never counts as passed, and 2 outranks 1. The default tier is `full`.

| Step | Tier | Fails when |
| --- | --- | --- |
| `format`, `lint` | fast | `ruff format --check` or `ruff check` reports a finding |
| `map` | fast | An AGENTS.md link is broken, a maintained directory has no guide, a guide is unreachable from the root guide, a feature file, Pattern file or Rule lacks its fields or names something that does not exist, a Pattern lacks its `task` or a non-empty `## Lessons` section, a skill lacks its front matter, a regular `SKILL.md` or its `.claude/skills` link, or `README.md` or `ARCHITECTURE.md` is missing, unlinked from the root guide or holds a broken local link |
| `exceptions` | fast | A suppression lacks its `rs-exception: EX-<n>` marker and entry in `.rapid-ship/exceptions.toml`, or an entry matches nothing |
| `file-size` | fast | A source file exceeds 500 lines without an exception |
| `kit` | fast | The lock is unreadable, or a managed file that is not excluded is missing |
| `types`, `contracts` | full | mypy or import-linter's `lint-imports` fails |
| `dead-code` | full | vulture reports unused code, or deptry a missing (DEP001), unused (DEP002), transitive (DEP003), misplaced dev (DEP004) or standard-library (DEP005) dependency; DEP002 never checks a dev dependency |
| `tests` | full | pytest fails |
| `audit` | full | pip-audit 2.10.1 finds a known vulnerability in the locked dependencies |
| `secrets` | full | gitleaks finds a secret in the change's commits, or in the whole history without a base. gitleaks must be on `PATH`; CI installs 8.30.1 |
| `workflows` | full | zizmor 1.30.1 reports a finding in a GitHub Actions workflow |
| `diff` | full | The change removes a test without declaring it, turns an assertion into a tautology, adds an `autouse` fixture without an exception, or adds and removes more than 1,500 counted lines without declaring the overage. It also lists each Protected path the change touches, and each Corrections ledger entry it changes or removes, without failing |
| `evidence` | full, PRs only | The PR body lacks its `## Evidence` section with a command, its result and a `Not covered:` line |

The agnostic stack has no `format`, `lint`, `types`, `contracts`, `dead-code`, `tests` or `audit` step. pip-audit and zizmor run through `uv tool run --from <pin>`; they are not dependencies. vulture and deptry are dev dependencies and run through `uv run --locked`, as Ruff and mypy do, because deptry maps each import to a distribution installed in the project's environment.

The `dead-code` step, in `check/stacks/python_dead_code.py`, runs both tools every time from the repository root, and each line of its details starts with the tool's name. `uv run --locked vulture --min-confidence 0` reads `[tool.vulture]`, and its command-line value replaces the file's `min_confidence`, so a project cannot switch a kind off: exit 0 passes, 3 fails, and any other exit blocks. `uv run --locked deptry . --no-ansi --json-output <file>` runs every deptry rule, DEP001 to DEP005, with `[tool.deptry]`. deptry exits 1 for findings and for its own errors, so on exit 1 the step reads the JSON report: one line per finding fails, and a missing or unreadable report blocks. A blocked tool outranks a failed one. When the dev group lacks vulture or deptry, or `[tool.vulture] paths` is unset, the step runs neither tool and blocks, naming each setting to add. The exceptions step reads deptry's `# deptry: ignore` comment, bare or with codes, in any case. vulture and deptry search a line's whole text, strings included, but only on the first line of what they report: a node's for vulture, in its own line numbering, and for deptry a `from ... import` statement's or `import_module` call's, and each name's own in a plain `import`. The exceptions step reads those lines as the tools do (`tool_line_rules`): there, a `# noqa` that vulture acts on and deptry's comment are suppressions, in a string too, and a string's later lines are not. It reads each allowlist item in the root `pyproject.toml`, such as an `ignore_names` item of vulture or a `per_rule_ignores` item of deptry, as a suppression. Each item sits alone on its own line with its marker, and its rule is the key's name under `[tool]`, a colon and the item, such as `vulture.ignore_names:pytestmark`. An item that devctl cannot place on a line, and a line with two items, fail. doctor's Python floor reports a missing `[tool.vulture] paths` and a Ruff `external` without `V`, and its `tools/devctl` exclusions item reports vulture's `paths` and deptry's patterns when they reach devctl.

The `diff` and `evidence` steps need a change. In CI the base is the PR's base and the body comes from the PR event. Locally, `--base` names the base, or devctl uses the merge base with `origin`'s default branch, and `--pr-body` names a file with the body. Without a base the `diff` step is not applicable, and outside a PR so is `evidence`.

The `diff` step's cap counts the lines a change adds and removes, from `git diff --numstat` and the untracked files that git does not ignore. It leaves out files ending in `.md`, `.txt` or `.log`, binary files, Kit-managed files, `.rapid-ship/kit.lock`, and `uv.lock` and `package-lock.json` at any depth. A file is Kit-managed when the lock in the work tree lists it as managed, or when the lock at the base lists it as managed and the change deletes it. A file that a Kit sync drops does not count, and a project's edit to a Kit file that the same change makes its own does: `sync` records that file as seeded, so the work tree's lock no longer lists it as managed. A lock that cannot be read lists no file, so the count only grows. More than 1,500 counted lines fails, unless the PR's Evidence section has a line starting `Over the diff cap:` with a reason. A declared overage passes with a note, and every run notes its count. In Flight, the merge guard leaves such a PR to the owner. The ledger rule is the step's other new check: a change that modifies, renames or removes a Markdown file under `docs/corrections/` other than its `README.md` is Protected, with or without a CODEOWNERS file, and is listed with the Protected paths. An added entry is not checked.

Before GA, the documentation release (plan 7's PR 7.4), the Kit keeps no backward compatibility (Spec 1 section 3): the project updates its own seeded files, and a check that requires the new content fails at once. So plan 5's map rules fail at once, although three of them fail on files that an existing project already owns: map rule 5's `task` key and `## Lessons` section, rule 7's regular `SKILL.md` and rule 8's links, which are the root guide's links to both documents and the local links inside them. `sync` does not edit those files. In the same way, the `dead-code` step blocks a Python project without its settings. The exceptions step fails on the dead-code tools' suppressions that lack their marker, also on lines that an existing project already owns.

### This repository's own steps

`tools/devctl/devctl_project/` adds three steps after the Kit's:

- `vendored` (fast) runs `uv run --locked rapid-ship status --strict`, so the check fails until the vendored Kit equals its templates.
- `distribution` (full) runs `uv build` in a copy of the files git keeps, then `scripts/smoke_distribution.py`. The smoke checks that the wheel ships every template, installs it into a fresh environment, checks `rapid-ship --version`, and runs `init`, `status --strict` and `./devctl --version` in scratch projects.
- `python-3.12` (full) runs the tests on Python 3.12, the oldest version `pyproject.toml` supports.

### Hook, CI and CODEOWNERS

- The pre-commit hook, `.githooks/pre-commit`, runs `./devctl check --tier fast`. `git config core.hooksPath .githooks` enables it, and `git commit --no-verify` skips it once.
- CI runs `./devctl check --tier full` in `.github/workflows/devctl-check.yml`, a managed Kit file. It runs on each PR, including body edits, on pushes to `main` or `master`, nightly and on demand. A push run has its own concurrency group, its commit's, so a later push never replaces the queued run of an earlier commit; a pull request has one group per ref and cancels its older run. It has `contents: read` only, installs gitleaks 8.30.1 checked against its SHA-256, and its job is named `devctl check`, which Spec 1's ruleset requires.
- `.github/CODEOWNERS` is seeded. In Walk its one active line, `* @proxy-hatch`, assigns every path to the owner. Below it, commented out for Flight, is the Protected set: `.github/`, `.githooks/`, devctl, the skills, `.claude/`, every AGENTS.md and CLAUDE.md, `.rapid-ship/`, and the settings files of the check tools. `.claude/` already covers the Claude Code wiring; Codex's and agy's wiring files join the set when they land. The `diff` step, `devctl hook` and the merge guard read these lines, commented or not, through `devctl/codeowners.py`.

`.github/workflows/docs.yml` is this repository's own: it builds the documentation site and deploys `main` to GitHub Pages.

## `devctl doctor` and Agent identity

`./devctl doctor [--skills | --settings]` reports each item as ok, missing or unknown, then a summary line, and exits 0 when every item is ok, 1 when one is missing and 2 when one could not be checked. It changes nothing in the repository and never reads a token file. The modules are `doctor.py`, which runs and prints the items, `doctor_local.py` for this machine and the repository, `doctor_github.py` with the rules in `doctor_rules.py` for GitHub, `doctor_wiring.py` for the Harness wiring item, `doctor_skills.py` for `--skills`, `harness.py` for its headless Claude Code Session, and `doctor_items.py` for the types they share. No item checks a Harness's sign-in.

- **Local items:** git 2.31 or later, the settings files, uv, gh and its sign-in, gitleaks 8.30.1, `core.hooksPath`, the CI job named `devctl check`, the Claude Code wiring in `.claude/settings.json`, the Python guardrail settings with the `dead-code` step's, `tools/devctl` left out of the project's own tools, vulture and deptry included, and the Kit files against the lock.
- **GitHub items:** read with the owner's `gh` sign-in, always as `GET`: the ruleset for the current Mode, CODEOWNERS against `every_pr` and `[github] code_owner`, branch deletion after merge and fork-PR workflow approval. While `code_owner` is unset, the CODEOWNERS item is missing and names the key. A GitHub Free private repository has no rulesets, and the item says so.
- **Agent identity items:** only while `[github]` records both Apps: each App's installation, its exact permissions and its slug, read as the App, and each key in its Keychain item, `rapid-ship/<role>-app/<App ID>`, proved by minting a token that is dropped unprinted.
- **`--settings`:** only git, the settings item and the Harness wiring item, with no GitHub request. The settings item loads `.rapid-ship/project.toml` and `.rapid-ship/exceptions.toml` with devctl's loaders and reads the CODEOWNERS file that the Protected set comes from. An unreadable or invalid file is unknown, and the message names the file and the key; no CODEOWNERS file is missing. `--settings` builds no `DoctorContext`, because loading the project would stop doctor before the settings item reports it, and the full doctor adds the same item right after git. Each Session runs it first unless it runs the full doctor, as the root guide's first command says. `--settings` and `--skills` exclude each other.
- **`--skills`:** when `claude` is on `PATH`, a detached worktree at `HEAD` in a temporary directory, one headless Claude Code Session on its cheapest model, and a comparison of the skills it lists with the ones committed at `HEAD`. The worktree is removed whatever the Session did. doctor probes Claude Code alone until the Kit integrates another Harness.

Agent identity is optional ([ADR 0002](docs/adr/0002-github-gates-merges-reviews-run-locally.md)). Each repository owner, a person or an organisation, has one Worker App and one Reviewer App, and each developer keeps their own key for each App in the macOS Keychain, in an item named `rapid-ship/<role>-app/<App ID>`. A key reaches `security` only on stdin, and rapid-ship never replaces or deletes an existing item.

- `rapid-ship app` uses, for each role, the App that `[github]` records, or else an App of the repository's owner whose key this machine holds. It confirms such an App with `GET /apps/<slug>`, or, because GitHub shows no private App that way, with `GET /app` under a token that the item's key signs. An item whose key cannot confirm its App stops the command with exit 1, unless another item holds the owner's App, so that no second App is created beside it. Only a role with neither gets a new App, through GitHub's manifest flow. For an organisation, that is the organisation's manifest flow, which only an active admin of the organisation may run. The command prints each App's `[github]` lines and install URL.
- `rapid-ship app --import-key {worker,reviewer}` stores a developer's own key, read on stdin, for the App that `[github]` records, once `GET /app` under a token that the key signs shows that App. A developer of an organisation uses it for the organisation's Apps. Whether an App manager may generate a key is unverified until the organisation trial, an Owner step ([Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) section 11).

`./devctl as worker push` pushes the current branch, never forcing, and `./devctl as {worker,reviewer} gh` runs `gh pr`, `gh issue` or `gh api` as that App. Each run mints one installation token in `devctl/github/app.py`, holds it in memory and gives it only to that `gh`, as `GH_TOKEN`, or to that `git push`, through `devctl/github/askpass.py` with every credential helper and repository hook switched off. No key or token is written to disk, put on a command line or printed.

## `devctl hook` and the merge guard

`devctl hook claude pre-tool` holds the Harness guardrails ([Spec 1](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md) section 4). The seeded `.claude/settings.json` has Claude Code run it before each `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit` and `Monitor` call; `Monitor` runs a shell command too. The hook reads Claude Code's `PreToolUse` event on stdin and answers with a deny, an ask or no decision, always with exit 0. It never allows a call. It never exits 2, which Claude Code reads as block: an internal error exits 1 with one stderr line, and the call goes through.

| Rule | Decision |
| --- | --- |
| G1 | Deny `--no-verify` in a git command, and `git commit -n` |
| G2 | Deny a force push: `--force`, `-f`, `--force-with-lease`, `--force-if-includes` or a `+` refspec |
| G3 | Deny the other ways to land a change on the default branch: `gh pr merge --admin`, a `git push` to it, and the `gh api` merges, ref writes and file commits, REST or GraphQL, that Spec 1 lists |
| G4 | Deny an edit of `.rapid-ship/kit.lock` |
| G5 | Ask the owner before an edit of a Protected path |
| G7 | With Agent identity on, deny `git push`, and name `./devctl as worker push` |
| G8 | With Agent identity on, deny a `gh pr`, `gh issue` or `gh api` write made as the owner, and name `./devctl as <role> gh` |
| G9, the merge guard | Deny `gh pr merge` until it has checked the pull request on GitHub (below) |

The modules are in `tools/devctl/devctl/`:

- `hook.py` runs the command. `decide` applies G1 to G5, G7 and G8, and `run_hook` then runs the merge guard on each `gh pr merge` of the command line.
- `hook_protocols.py` holds the types the rules share, `WIRED_TOOLS` and Claude Code's event and answer. It documents the exit-code workaround.
- `command_line.py` splits a command line as the shell does, so a command after `;`, `&&`, `|`, `&` or a newline, or inside `$( … )` or backticks, is checked too. It parses `git push`, `gh api`, and the `gh pr` and `gh issue` subcommands.
- `merge_guard.py` holds `find_merge`, which names each way to land a change on the default branch for G3 and the guard, and `guard`. `merge_guard_github.py` holds the guard's GitHub reads.
- `codeowners.py` reads the Protected set from the first of `.github/CODEOWNERS`, `CODEOWNERS` and `docs/CODEOWNERS`, and applies the Corrections ledger rule. The hook, the guard and the `diff` step share it.

The hook judges an edit in the repository that holds the edited path, a linked worktree included, and a shell command in the one that holds the event's `cwd`. It reads that repository's `.rapid-ship/project.toml` and CODEOWNERS on each call. When either cannot be read, or `project.toml` is invalid, G1 to G4 still apply, G5, G7 and G8 give no decision, and the guard denies every merge. A missing CODEOWNERS is an empty Protected set.

The merge guard checks `gh pr merge`, run directly or through `./devctl as <role> gh`, once no other rule has denied the command line. With Agent identity on, G8 denies a direct `gh pr merge`, so an agent merges through `./devctl as worker gh pr merge`. The guard reads GitHub with the owner's `gh` sign-in, always as `GET`: the pull request with its body, CODEOWNERS on its base branch, its files, its reviews while Agent identity is on, and the `devctl check` runs on its head commit. In Walk it reads only the pull request. It takes the repository from a PR URL, else from `-R`, else from `[github] repository`. It denies with the first of these that applies:

1. In Walk (`[escalation] every_pr = true`), every merge: the owner merges every pull request.
2. The pull request touches the Protected set. The owner merges it in GitHub's web interface.
3. In Flight, the body's Evidence section declares a removed behavioural test or an overage of the diff cap. The guard reads the section with the `evidence` step's parsers, `removed_test_declarations` and `over_cap_reason`, and classes each removed test as the `diff` step does, by `[tests] unit`, so a declared removed unit test does not stop the merge. The owner merges the pull request.
4. `devctl check` has not passed on the head commit.
5. With Agent identity on, the Reviewer App has not approved the head commit.
6. The command does not carry `--match-head-commit` with the head the guard checked. The message gives the exact command to retry.

It also denies a merge it cannot check, its own errors included. It denies rather than start a read that could end more than 300 seconds after the hook started, because Claude Code lets a call through when it kills a hook at its timeout. The seed sets no `timeout`, so that timeout is Claude Code's default of 600 seconds.

`doctor_wiring.py` is doctor's Harness wiring item. It reads only `.claude/settings.json`. The item is ok when the file is tracked, is valid JSON, does not set `disableAllHooks` and runs `devctl hook claude pre-tool` for each tool in `WIRED_TOOLS`. A hook counts only when the words Claude Code passes, in exec or shell form, are `devctl` or a path that ends in `/devctl`, then `hook`, `claude` and `pre-tool`. In shell form, that first word holds only path characters, `$NAME` and `${NAME}`, so `false&&` or `X=` glued before the path does not count. A hook that runs in the background, has an `if` condition or sets a `timeout` below 360 seconds does not count.

These guardrails stop habits and mistakes; a misbehaving agent can bypass them. [Spec 1 section 4](docs/superpowers/specs/2026-10-14-kit-and-setup-design.md#harness-guardrails) lists what the hook and the guard do not see. They run only in a Claude Code Session started in a checkout that holds the wiring, because Claude Code reads its hooks when a Session starts.

## Dog-fooding

This repository ran `init` on itself, so `devctl` and `tools/devctl/` are the vendored Kit and `.rapid-ship/` holds its seeded settings and the lock. Ruff and mypy check `tools/devctl/` and skip `rapid_ship/templates/`, so devctl is checked once, and pytest imports the vendored copy. Its `.rapid-ship/project.toml` records the Worker App, `proxy-hatch-rs-worker` (ID 5376519), and the Reviewer App, `proxy-hatch-rs-reviewer` (ID 5376520), under `[github]`, so Agent identity is on here. The owner's Keychain holds both keys, in `rapid-ship/worker-app/5376519` and `rapid-ship/reviewer-app/5376520`.

`sync --in-place` wrote this repository's `.claude/settings.json`, so a Claude Code Session started in a checkout that holds it runs `devctl hook`. Agent identity is on here, so G7 and G8 deny an agent's `git push` and `gh` writes made as the owner. G5 asks the owner before each edit of a Protected path, such as an `AGENTS.md` file. A Session started before the file existed runs no hook.

To change devctl, the hook or the CI workflow:

1. Edit the template under `rapid_ship/templates/common/`.
2. Run `uv run rapid-ship sync --in-place`.
3. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together.

Never edit the vendored copy itself. `sync` would record the edited file as this repository's own and stop updating it, and `status --strict` passes such a file. `tests/test_kit_dogfood.py` therefore fails on any Kit-managed file that the lock records as seeded; `uv run rapid-ship sync --in-place --revert <path>` gives it back. `tests/devctl/test_devctl_project_dogfood.py` syncs a template edit in a copy of this repository and checks that this repository's own steps still run. A seeded file, such as `.github/CODEOWNERS` or `tools/devctl/devctl_project/__init__.py`, is edited in place.

## Designed, not built

[Plan 5, Kit standards and Harness guardrails](docs/superpowers/plans/2026-10-14-kit-and-setup.md#plan-5-kit-standards-and-harness-guardrails), is built. Its hook spike (backlog item PRO-139) is recorded, and the [live trial](docs/trials/2026-10-23-harness-guardrails.md) of `devctl hook` in headless Claude Code Sessions gave every expected decision and message. From the spike, a follow-up wires Codex without G5 (PRO-142), and agy waits for its interactive runs (PRO-143).

Spec 1's [plan index](docs/superpowers/plans/2026-10-14-kit-and-setup.md) defines two more plans, not started:

- **[Plan 6, TypeScript stack and several stacks in one repository](docs/superpowers/plans/2026-10-14-kit-and-setup.md#plan-6-typescript-stack-and-several-stacks-in-one-repository):** one `[[stack]]` table per stack, each stack's files and check steps in its own directory, and a TypeScript stack for React that checks with ESLint, Prettier, `tsc --noEmit`, Vitest and `npm audit`, with its starter Patterns and CI support.
- **[Plan 7, `rs-setup` and `rs-health`](docs/superpowers/plans/2026-10-14-kit-and-setup.md#plan-7-rs-setup-and-rs-health):** the Kit's first skills, with the forked engineering skills and the optional `rs-contribute`. They replace `rapid-ship-engineering`.

Two more specs get their own plans later:

- **[Spec 2, Delivery skills](docs/superpowers/specs/2026-10-16-delivery-skills-design.md):** `rs-design`, `rs-breakdown`, `rs-lead`, `rs-work`, `rs-review` and the tracker mapping notes.
- **[Spec 3, Metrics and gardening](docs/superpowers/specs/2026-10-16-metrics-and-gardening-design.md):** `devctl metrics`, the scheduled metrics Action, Suggested thresholds, project-defined metrics, the Corrections ledger, `rs-garden`, and `rs-preflight`, the advisory readiness review before the owner widens the Mode toward Flight.

Decisions with lasting trade-offs are in [ADR 0002](docs/adr/0002-github-gates-merges-reviews-run-locally.md) (GitHub gates merges, the merge guard also checks each agent merge, and Agent identity is optional) and [ADR 0004](docs/adr/0004-team-management-boundary.md) (the team-management boundary). ADR 0003, which deferred rapid-orchestrator, was withdrawn before merge; [its text](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/adr/0003-walk-on-bare-sessions-orchestrator-deferred.md) stays at commit `401b57d`.

## What was removed

The earlier controller, a local orchestrator also named devctl, was removed on 2026-10-14. Its last version is the git tag `archive/controller-2026-10`. Spec 1's section 2 lists the parts that later plans reuse, retrieved with `git show archive/controller-2026-10:<path>`. The [tag](https://github.com/proxy-hatch/rapid-ship/tree/archive/controller-2026-10) also keeps its runtime trials, designs and guides, and its plans of 2026-10-10 and 2026-10-12 in [`docs/superpowers/plans`](https://github.com/proxy-hatch/rapid-ship/tree/archive/controller-2026-10/docs/superpowers/plans). Only its getting-started guide, which names old commands such as `devctl run`, stays under `docs/`, and it starts with a "Historical" line.

## Develop rapid-ship

You need uv, Python 3.12 or later, network access and gitleaks 8.30.1 on `PATH`.

```sh
uv sync --locked
git config core.hooksPath .githooks
./devctl check
```

After changing a template, run `uv run rapid-ship sync --in-place`, then `uv run rapid-ship status --strict`. Run one area's tests with `uv run pytest tests/test_<area>.py`, and devctl's with `uv run pytest tests/devctl`. On a branch, `./devctl check` compares the change with `origin`'s default branch; pass `--pr-body <file>` to check a PR body's Evidence section locally.

## Documentation site

The site reads this file, the README and the Markdown under `docs/` directly, excluding maintainer `AGENTS.md` files. Public images come from `asset/public/`. To preview it, use Node.js 22+ (CI uses 24):

```sh
npm --prefix website ci --no-audit --no-fund
npm --prefix website start
# Production build, including internal link and anchor checks:
npm --prefix website run build
```

The site pins four patched transitive dependencies while upstream catches up. As of 2026-10-11, the remaining [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) has no published fix; it concerns deeply nested build patterns. Pages serves static output, without a Node server. Recheck `npm audit` when updating the lockfile.

The docs workflow builds PRs and deploys successful `main` builds to GitHub Pages. Repository Pages settings must use GitHub Actions.
