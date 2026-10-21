# Kit and Setup: plan index

**Spec:** [Spec 1: Kit and Setup](../specs/2026-10-14-kit-and-setup-design.md), part of the [rapid-ship design](../specs/2026-10-14-rapid-ship-design.md).

Spec 1 is built as seven plans, in this order. Each ends with a working, tested repository. Plans 1 to 3 are built, each in one PR. Plan 4 and its follow-ups are built in three PRs, #31 to #33, which are not merged yet. Plans 5 to 7 are not started. Each gets its own plan document, written from this index before its work starts, and lands in the PRs that its outline below names, each small enough for one review. Plans 4 to 7 follow the re-scope of 2026-10-16 ([ADR 0004](../../adr/0004-team-management-boundary.md)). [Spec 2](../specs/2026-10-16-delivery-skills-design.md) and [Spec 3](../specs/2026-10-16-metrics-and-gardening-design.md) get their own plans later.

| Order | Plan | Spec sections | Depends on | State |
| --- | --- | --- | --- | --- |
| 1 | [Remove the old controller](2026-10-14-remove-controller.md) | 2 | — | Built: PR #28, `codex/remove-controller` |
| 2 | [The rapid-ship CLI](2026-10-14-rapid-ship-cli.md): templates, lock, `init`, `status`, `sync`, dog-food init | 3, 4 | 1 | Built: PR #29, `codex/rapid-ship-cli` |
| 3 | [`devctl check`](2026-10-14-devctl-check.md), the CI workflow and the hook; this repository switches to `./devctl check` | 4, 5 | 2 | Built: PR #30, `codex/devctl-check` |
| 4 | [Doctor and Agent identity](2026-10-16-doctor-and-agent-identity.md): `devctl doctor`, `rapid-ship app`, the token code, `devctl as`, and the settings for the escalation list ([outline](#plan-4-doctor-and-agent-identity)) | 3, 4, 6, 10 | 3 | Built, with follow-ups 1 to 4 and 7 to 9: PRs #31, #32 and #33 (`plan4-settings-tokens`, `plan4-doctor`, `doctor-agent-identity`), not merged. Its live trials and the organisation trial (follow-up 5) are pending Owner steps. #33 turns this repository's Agent identity on (follow-up 6) |
| 5 | [Kit standards and Harness guardrails](#plan-5-kit-standards-and-harness-guardrails): the hook spike first, then `devctl hook` with the merge guard and its Claude Code wiring, the standards seeds and checks, documented settings, and `sync` migrations | 3, 4, 5, 6, 10 | 4 | Planned: four PRs |
| 6 | [TypeScript stack and several stacks in one repository](#plan-6-typescript-stack-and-several-stacks-in-one-repository) | 3, 4, 5, 6, 10 | 5 | Planned: three PRs |
| 7 | [`rs-setup` and `rs-health`](#plan-7-rs-setup-and-rs-health), with the engineering skills and `rs-contribute` | 7, 8, 9, 10 | 4, 5, 6 | Planned: three PRs |

PRs #28 to #33 form a stack on the design PR, #27: each is based on the one before, and a change to the design lands on #27 and is merged up. Each plan document lives in its plan's PRs: plans 1 to 3 in #28 to #30, and plan 4's, `2026-10-16-doctor-and-agent-identity.md`, in #31 to #33.

The first drafts of plans 4 and 5, GitHub commands and Kit skills, were deleted when plans 4 to 7 replaced them. Plan 4's outline below lists what it took from the old plan 4's branch, `codex/github-commands`, which is only in the owner's clone; the [old plan at `928fbe4`](https://github.com/proxy-hatch/rapid-ship/blob/928fbe493977ae41d2012e19baff3e861fd5b0e8/docs/superpowers/plans/2026-10-14-github-commands.md) describes it.

This index fixes the layout and the names, signatures and formats that more than one plan uses. A plan that needs a different one changes this file in the same PR. For what plans 1 to 4 built, the code and [ARCHITECTURE.md](../../../ARCHITECTURE.md) on their branches are canonical; their plan documents keep their task lists and verification records.

## Conventions for every plan

- Every command in both CLIs is one word followed by arguments:
  - `rapid-ship init [--stack NAME[=DIRECTORY]]... [--owner LOGIN] [--repository OWNER/NAME] [--name NAME] [--package NAME]`; until plan 6, `--stack {python,agnostic}` names one stack at the root
  - `rapid-ship status [--strict] [--json]`, `rapid-ship sync [--in-place] [--revert PATH]...`
  - `rapid-ship app [--repository OWNER/NAME] [--import-key {worker,reviewer}]` (plan 4; `--import-key` from its follow-ups)
  - `devctl check [--tier {fast,full}] [--json] [--base REV] [--pr-body PATH] [--install]`; `--install` from plan 6
  - `devctl doctor [--skills]`, with `--settings` from plan 5, `devctl as {worker,reviewer} push`, `devctl as {worker,reviewer} gh ARGS...` (plan 4)
  - `devctl hook claude pre-tool` (plan 5); each later wiring adds its Harness
- Exit codes in both CLIs: 0 success; 1 a check failed, something is missing, or a request was refused; 2 the command could not run. When both 1 and 2 apply, 2 wins. `KitRefusal` exits 1; `KitError`, `SettingsError`, `RepoError` and `DevctlError` exit 2. Two commands differ, as Spec 1 section 6 says: after it runs `gh` or `git`, `devctl as` returns that tool's exit code, or 2 when the tool timed out or its output was cut; `devctl hook` follows each Harness's hook protocol, a workaround documented in `hook_protocols.py`, and exits 1 on an internal error, never 2.
- Every refusal and error names the problem, what it blocks and the next step (guided rectifying), and still stops at the first error and shows its cause.
- Every settings file the Kit ships documents each key in a short inline comment wherever its format allows one, and devctl's loaders reject unknown keys, wrong types, numbers out of range and values outside their allowed set (plan 5; plan 6 for the TypeScript files).
- Write tests first. Label offline and simulated tests as such. A blocked or skipped step never counts as passed.
- Python 3.12 or later; `uv` runs everything. Settings are TOML, read with `tomllib`.
- devctl source is edited only under `rapid_ship/templates/common/tools/devctl/`. Then run `uv run rapid-ship sync --in-place`, which accepts a dirty work tree. Commit the template, the vendored copy and `.rapid-ship/kit.lock` together. Never edit the vendored copy: `sync` would make it this repository's own, and `tests/test_kit_dogfood.py` fails.
- devctl starts processes only through `process.run_process`, called through the module (`from devctl import process`). The one other caller is `repo._git` (EX-3). `rapid_ship` never imports devctl, which an import-linter `forbidden` contract enforces.
- The Python guardrail settings cover `rapid_ship`, devctl and `tests/`: no `print`, no `Any` in a signature, complexity at most 10, every test annotated. Each suppression carries an `rs-exception` marker and an entry.
- `uv run pytest` and `./devctl check --tier full` need network access and gitleaks 8.30.1 on `PATH`.
- The Kit version is the rapid-ship package version. Each Kit release is a tag `v<version>` on `main`, created by the owner. Run `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<version> rapid-ship <command>`, or `--from <local checkout>` before the first tag. `sync` needs no tag: it never merges, and a Kit file the project edited or deleted becomes the project's own. PyPI publishing is a later, separate change.
- A live trial is an Owner step: the plan names what to run and what to record under `docs/trials/`, and the owner runs or approves each external write.
- Each plan's last task runs `./devctl check`, builds the docs site with `npm --prefix website run build`, and records the actual results in the plan.

## Layout after plan 7

```text
rapid_ship/                      # the rapid-ship CLI package, run with uvx
  __init__.py  __main__.py
  cli.py                         # build_parser(), main(argv): init, status, sync; app (plan 4)
  files.py                       # atomic_replace, UnsafePath, relative_parts, safe_path, create_file
  github_app.py                  # plan 4: rapid-ship app, which finds or creates the Apps and prints install URLs
  app_import.py                  # plan 4: rapid-ship app --import-key
  app_flow.py                    # plan 4: the manifest flows, and GitHub calls made as an App
  app_keychain.py                # plan 4: Keychain storage and item names
  upstream.lock                  # plan 7: upstream files of forked skills
  kit/
    templates.py lock.py git.py init.py existing_checks.py status.py sync.py writes.py pull_request.py
    migrations.py                # plan 5: the edits sync proposes to seeded files
    stacks.py                    # plan 6: stacks, their directories, rendering under a directory
  templates/
    kit.toml                     # see "Kit manifest" below
    common/                      # files for every stack, laid out as in a project
    python/                      # Python stack additions and overrides
    typescript/                  # plan 6: TypeScript stack additions
    agnostic/                    # stack-agnostic additions
tests/
  conftest.py                    # the only conftest; plan 4 adds pytest_plugins = ["github_fixtures"]
  test_files.py test_kit_*.py    # rapid-ship CLI tests; plan 4 adds test_kit_app*.py, plan 5 test_kit_migrations*.py, plan 6 test_kit_stacks*.py, plan 7 test_kit_upstream.py
  fixtures/upstream/<repository>/<commit>/<path>   # plan 7: pristine upstream files
  devctl/                        # no __init__.py, no conftest.py; files named test_devctl_*.py
    check_workspace.py           # plan 3: project_settings, Workspace, new_workspace, fake_tool
    github_fakes.py github_fixtures.py fixtures/github/   # plan 4
    fixtures/hooks/<harness>/    # plan 5: recorded hook events, claude/ only
scripts/smoke_distribution.py
devctl, tools/devctl/            # this repository's vendored Kit
.agents/skills/rs-*, .claude/skills/rs-*   # plan 7: vendored Kit skills; rapid_ship/skills/ is gone
```

`pyproject.toml` sets `[tool.pytest.ini_options] pythonpath = ["tools/devctl", "tests/devctl"]`, so tests import the vendored devctl and its test helpers.

devctl inside any project:

```text
devctl                           # sh shim: unset UV_PROJECT_ENVIRONMENT; exec uv run --project "<root>/tools/devctl" --frozen --quiet devctl "$@"
tools/AGENTS.md                  # seeded
tools/devctl/
  pyproject.toml                 # name "devctl"; [project.scripts] devctl = "devctl.cli:main"; [tool.uv.workspace] members = []
  uv.lock
  .gitignore
  devctl/
    __init__.py                  # __version__
    cli.py                       # build_parser, main; core verbs, then devctl_project.register
    repo.py                      # Repo, RepoError
    settings.py                  # ProjectSettings and friends, SettingsError (plans 4 to 6 reshape it)
    process.py                   # ProcessResult, safe_environment, run_process
    codeowners.py                # plan 5: the Protected-set lines and their matcher, moved from check/diff.py
    check/                       # plan 3: __init__, steps, markdown, map, references, exceptions,
                                 # filesize, kit, diff, evidence, stacks/python.py, stacks/agnostic.py; plan 6 adds stacks/typescript.py
    doctor.py doctor_items.py doctor_local.py doctor_github.py doctor_rules.py doctor_skills.py
    harness.py                   # plan 4: the Claude Code skills probe
    identity.py                  # plan 4: devctl as
    github/api.py github/app.py github/askpass.py   # plan 4: REST client, App tokens, GIT_ASKPASS helper
    hook.py hook_protocols.py    # plan 5: devctl hook's rules, and Claude Code's protocol
    merge_guard.py               # plan 5: the merge guard, G9
  devctl_project/                # seeded: project verbs and extra check steps
    __init__.py
```

devctl depends only on PyYAML (`pyyaml>=6.0.3,<7`, plan 3) and `PyJWT[crypto]>=2.10,<3` (plan 4). The root dev group adds the same two, plus `types-pyyaml`, so `tests/devctl` can import devctl. pip-audit 2.10.1 and zizmor 1.30.1 run with `uv tool run --from <pin>` and are not dependencies; gitleaks 8.30.1 is a binary on `PATH`. The rapid-ship CLI depends on `tomli-w` and, since plan 4's follow-ups, on `PyJWT[crypto]>=2.10,<3`, devctl's range: `rapid-ship app` signs a token with a Keychain item's key to ask GitHub whose App it is.

A project whose root `[tool.uv.workspace] members` match `tools/devctl` must list it under `exclude`, or its own `uv lock` fails. `init` never edits that file: `rs-setup` adds the exclude (plan 7) and `devctl doctor` reports it missing (plan 4).

## Built interfaces (plans 1 to 3)

The code on `codex/devctl-check` is canonical; this list names what later plans call.

- `rapid_ship/cli.py`: `build_parser`, and `main(argv: Sequence[str] | None = None)`.
- `rapid_ship/files.py`: `atomic_replace`, `UnsafePath`, `relative_parts`, `safe_path` (refuses every symlink below the root), `create_file` (never overwrites).
- `rapid_ship/kit/`: `templates.py` (`Stack = Literal["python", "agnostic"]`, `Kind`, `Template`, `KitManifest`, `KitError`, `KitRefusal`, `load_manifest`, `render_files`, `read_optional_skills`, `read_excluded`, `is_excluded`, `installed_version`); `lock.py` (`Lock`, `LockEntry`, `LOCK_PATH`, `read_lock`, `write_lock`, `file_sha256`, `template_hash`, `entry_for`, `seeded_entry`); `git.py` (`git`, which runs no hook and passes `--literal-pathspecs` except with `literal=False` for `check-ignore`, `hooks_setup`, `work_tree_root`, `changed_paths`, `is_clean`, `head_branch`, `head_commit`, `commit_paths`, `leave_branch`); `init.py` (`INIT_BRANCH`, `init_repository`, `resolve_variables`, `InitResult`); `existing_checks.py` (`find_existing_checks`); `status.py` (`classify`, `StatusReport`, `FileStatus`, `locate`, `fingerprint`); `sync.py` (`sync_repository`, `SyncResult`, `Conflict`, `OpenPullRequest`); `pull_request.py` (`REVERT`, `push_and_open_pull_request`, `pull_request_body`); `writes.py` (`Undo`, `write_template`, `delete_file`).
- `devctl/repo.py`: `Repo` with `root`, `git_common_dir`, `discover`, `tracked_files`, `merge_base`, `files`, `git`; `RepoError`.
- `devctl/process.py`: `ProcessResult`, `safe_environment`, `run_process(argv, cwd, timeout_seconds, env=None, input_text=None)`, `MAX_OUTPUT_BYTES`. The child gets only `safe_environment(env)`: the caller's `PATH` and `HOME`, with `LANG` and `LC_ALL` set to `C.UTF-8`, then `env`. `run_process` has no cancellation, and it reports truncation in flags, never inside the output.
- `devctl/check/steps.py`: `Tier`, `Status`, `StepResult`, `CheckContext`, `Step`, `CommandStep`, `passed`, `failed`, `blocked`, `not_applicable`, `run_tool`, `command_result`. `devctl/check/__init__.py`: `core_steps`, `all_steps`, `run_check`, `exit_code`, `resolve_change`, `ChangeError`.
- `devctl/check/kit.py`: `LOCK_PATH`, `KitLockError`, `is_excluded` (devctl's copy of the CLI's, held equal by a parity test), `managed_paths`.
- `devctl/check/exceptions.py`: `MARKER`, `SuppressedLine`, `scan`, `normal_rule`. `devctl/check/evidence.py`: `evidence_section`, `removed_test_declarations`. `devctl/check/diff.py`: `codeowners_match`, `protected_patterns`, `glob_match`.
- `devctl_project/__init__.py` (seeded): `register(commands)` adds verbs; `check_steps()` returns extra steps.

### Kit manifest

`rapid_ship/templates/kit.toml` after plan 7. Paths are relative to `common/` or a stack directory, before substitution. Every other template is managed.

```toml
seeded = [".claude/settings.json", ".github/CODEOWNERS", ".rapid-ship/exceptions.toml",
  ".rapid-ship/project.toml", "AGENTS.md", "ARCHITECTURE.md", "CLAUDE.md", "README.md",
  "docs/AGENTS.md", "docs/features/README.md", "docs/patterns/README.md", "tools/AGENTS.md",
  "tools/devctl/devctl_project/__init__.py"]
new_project = [".gitignore", "pyproject.toml", "src/AGENTS.md", "src/__package__/__init__.py",
  "tests/AGENTS.md", "tests/test_import.py"]   # seeded only when init starts a Python project
executable = ["devctl", ".githooks/pre-commit", "tools/devctl/devctl/github/askpass.py"]
optional_skills = ["rs-contribute"]
variables = ["owner", "package", "project_name", "repository"]
```

Plan 4 added `askpass.py` to `executable` and dropped the `.rapid-ship/gate.toml` seed. Plan 5 adds three seeds, `.claude/settings.json`, `ARCHITECTURE.md` and `README.md`, and adds the Python starter Patterns, with their reference code and tests, to `new_project`. Plan 6 makes `new_project` a list for each stack, with paths relative to the stack's directory, and adds the TypeScript stack's. Plan 7 adds `rs-contribute`. The block above leaves out the starter Patterns and shows only the Python stack's `new_project` list. Spec 3's plan adds a `.rapid-ship/metrics.toml` seed. It also renames the manifest key `optional_skills` to `optional`, with `read_optional_skills` and `ProjectSettings.optional_skills` to match, so that `optional` can name an optional Kit file, such as its metrics Action, as well as a skill.

Template rules, as plan 2 built them:

- Managed templates are copied byte for byte, so a managed file's hash is the same in every project.
- Only seeded files substitute `{{project_name}}`, `{{package}}`, `{{owner}}` and `{{repository}}`. A template directory named `__package__` becomes the package name. An empty variable renders as `<name>` and comments out its line in a TOML file or CODEOWNERS; elsewhere it is a `KitError`.
- `.claude/skills/<name>` is always a relative symlink, generated from `.agents/skills/<name>/`. When a symlink cannot be made, `init` and `sync` exit 2 and leave nothing half-written.
- Template discovery skips `.venv`, `__pycache__`, `.DS_Store` and `.pyc` files, and, when the template root's `kit.toml` is tracked by git, every path git does not keep.
- The execute bit comes only from `executable`: `init` creates a listed path with mode `0o777` less the umask, and `sync` keeps a file's mode, adding execute bits for a listed path. A template's own git mode never reaches a project. List a new executable template before its first sync, so its vendored copy is tracked `100755`.
- `sync` creates a seeded template that a newer Kit adds only where nothing exists at its path, and records it either way. It never adds a new-project seed.

## Shared interfaces for plans 4 to 7

### Settings (plan 4; plans 5 and 6 change it)

```python
# devctl/settings.py after plan 6
Role = Literal["worker", "reviewer"]
# plan 4 has Stack = Literal["python", "agnostic"]
StackName = Literal["python", "typescript", "agnostic"]


@dataclass(frozen=True)
class ProjectStack:  # plan 6: one [[stack]] table
    name: StackName
    directory: str  # repository-relative POSIX path, inside the repository; "." is the root


@dataclass(frozen=True)
class App:
    id: int  # [github] <role>_app_id; 0 in the file means unset
    slug: str  # [github] <role>_app_slug; Spec 3 matches agent PR authors against it


@dataclass(frozen=True)
class Escalation:
    every_pr: bool  # default True: Walk
    kinds: tuple[str, ...]  # plain text for the Lead
    revision_rounds: int  # default 3, at least 1


@dataclass(frozen=True)
class ProjectSettings:
    stacks: tuple[ProjectStack, ...]  # plan 6; plan 4 has stack: Stack, one stack at the root
    repository: str | None  # "owner/name"
    code_owner: str | None  # plan 4's follow-ups: "@login" or "@organisation/team"
    worker_app: App | None  # both Apps recorded, or neither; recorded Apps need repository
    reviewer_app: App | None
    escalation: Escalation
    optional_skills: tuple[str, ...]  # [kit] optional
    excluded: tuple[str, ...]  # [kit] exclude
    source_roots: tuple[str, ...]  # [map] source_roots
    unguided: tuple[str, ...]  # [map] unguided
    map_exclude: tuple[str, ...]  # [map] exclude
    unit_tests: tuple[str, ...]  # [tests] unit

    @property
    def agent_identity(self) -> bool: ...  # both Apps recorded


def load_project(root: Path) -> ProjectSettings: ...
def load_exceptions(root: Path) -> list[ExceptionEntry]: ...
```

Plan 4 removed `GateSettings`, `load_gate`, `Mode`, `CheckContext.gate` and `release_method`. Its follow-ups added `[github] code_owner`, and removed the `[roster]` table that plan 4 first built, with its `Agent` type (follow-up 7). devctl refuses `[agents]`, `[linear]`, `[dispatch]` and `[release]`, and from the follow-ups `[roster]`. Each message says why the table went and to delete it: for `[agents]` and `[roster]`, "rapid-ship does not run agents across several Providers; delete the table". Plan 6 replaces `stack` with `[[stack]]`, with the migration that `sync` proposes (Spec 1 section 3). Spec 2's plan adds `[tracker]` and `[design]`.

### doctor (plan 4; plans 5 and 6 add items)

```python
# devctl/doctor_items.py
Status = Literal["ok", "missing", "unknown"]


@dataclass(frozen=True)
class Item:
    area: str  # toolchain, guardrails, kit, github, agent identity, skills
    name: str
    status: Status
    detail: str


@dataclass(frozen=True)
class DoctorContext:
    root: Path
    project: ProjectSettings
    owner_get: OwnerGet  # GET with the owner's gh sign-in; raises OwnerReadError
    access: GitHubAccess | None  # None while Agent identity is off


# devctl/doctor_rules.py
# Codex's wiring adds .codex/, and agy's widens .agents/skills/ to .agents/
PROTECTED_PATHS: tuple[str, ...]
PYTHON_PROTECTED_PATHS: tuple[str, ...]
TYPESCRIPT_PROTECTED_PATHS: tuple[str, ...]  # plan 6


def ruleset_problems(
    rulesets: Sequence[Mapping[str, object]],
    default_branch: str,
    *,
    every_pr: bool,
    agent_identity: bool,
) -> list[str]: ...  # plan 7's test checks rs-setup's ruleset.json with it
# plan 6: one call per stack. code_owner is [github] code_owner with its @, never the
# repository's owner
def codeowners_problems(text: str, every_pr: bool, code_owner: str, stack: Stack) -> list[str]: ...
```

### Ruleset (plan 7 applies `rs-setup/ruleset.json`; plan 4's doctor checks it)

One active ruleset on `~DEFAULT_BRANCH`. A `pull_request` rule with `required_approving_review_count` 1, `allowed_merge_methods` `["squash"]`, and `require_code_owner_review`, `dismiss_stale_reviews_on_push`, `require_last_push_approval` and `required_review_thread_resolution` set to `true`. `required_status_checks` holds `{"context": "devctl check", "integration_id": 15368}`. `non_fast_forward` and `deletion` rules are present. `bypass_actors` is exactly `[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]`.

- Plan 4's live trial settles the approval count with Agent identity in Flight (Spec 1 section 8, step 7). If GitHub does not count the Reviewer App's approval, the count becomes 0, and both plans change this paragraph.
- With `every_pr = false` and Agent identity off, doctor also accepts a `pull_request` rule with no approval, no code-owner review and no last-push approval, because Flight without Agent identity needs that (Spec 1 section 8, step 8).

### Agent identity (plan 4)

```python
# devctl/github/app.py
APP_PERMISSIONS: dict[Role, dict[str, str]]  # Spec 1 section 3


# "rapid-ship/<role>-app/<App ID>"; plan 4's first items, "rapid-ship/<role>-app", had no App ID
def keychain_service(role: Role, app_id: int) -> str: ...
def keychain_private_key(role: Role, app_id: int, keychain: Keychain | None = None) -> bytes: ...


class DevctlError(Exception): ...  # exit 2


def installation_token(
    role: Role,
    repository: str,
    app_id: int,
    *,
    keychain: Keychain | None = None,
    api_url: str = API_URL,
) -> str: ...


# devctl/identity.py: devctl as
GH_COMMANDS = frozenset({"pr", "issue", "api"})


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None: ...
```

- A token lives in memory only, one per command. `gh` receives it only as `GH_TOKEN` in its own environment, with `GH_REPO`; git receives it only through `devctl/github/askpass.py`, which reads `RAPID_SHIP_GIT_TOKEN`.
- `rapid_ship/app_keychain.py` keeps its own `keychain_service`, and `rapid_ship/app_flow.py` its own `APP_PERMISSIONS`, because `rapid_ship` cannot import devctl. A parity test keeps them equal to devctl's.

### `devctl hook` and the merge guard (plan 5)

```python
# devctl/hook.py
Decision = Literal["deny", "ask"] | None  # None: no decision; the hook never allows


@dataclass(frozen=True)
class ToolCall:  # one Harness's pre-tool event, normalised
    shell: str | None  # the command line of a shell tool
    edits: tuple[str, ...]  # repository-relative paths a file-edit tool writes
    cwd: Path


def decide(
    call: ToolCall, project: ProjectSettings | None, protected: Sequence[str] | None
) -> tuple[Decision, str]: ...  # None: unreadable; G5, G7 and G8 give no decision, G1 to G4 apply


# devctl/merge_guard.py
@dataclass(frozen=True)
class Merge:  # a way to land a change on the default branch, also through devctl as
    form: Literal["pr-merge", "admin", "push", "rest", "graphql"]  # G3 denies all but pr-merge
    target: str | None  # pr-merge: the number, URL or branch it names; None: the branch's PR


@dataclass(frozen=True)
class LocalBranches:  # read from local git, only for a git push or a ref path
    default: frozenset[str]  # origin/HEAD's branch; {"main", "master"} when that ref is missing
    current: str | None  # None: a detached HEAD


def find_merge(argv: Sequence[str], branches: Callable[[], LocalBranches]) -> Merge | None: ...
# None: not a merge; reads GitHub for nothing
# pr-merge only: G3 denies the other forms
def guard(merge: Merge, root: Path, owner_get: OwnerGet) -> tuple[Decision, str]: ...


# devctl/hook_protocols.py: Claude Code's protocol; the exit-code workaround is documented here
WiredHarness = Literal["claude"]  # plan 5; each later wiring adds its Harness and protocol


def read_event(harness: WiredHarness, payload: bytes) -> ToolCall: ...
def answer(
    harness: WiredHarness, decision: Decision, reason: str
) -> tuple[str, int]: ...  # stdout, exit code; never 2
```

`protected` comes from `devctl/codeowners.py`, the matcher the `diff` step also uses, so the hook, the merge guard and the step agree on the Protected set. The hook denies an `admin`, `push`, `rest` or `graphql` form under G3 and reads GitHub for none of them; it reads `LocalBranches` from local git only for a `git push` or a ref path. The merge guard reads GitHub only for a `pr-merge`, and only through `OwnerGet`, doctor's reader: `gh api` with `GET` under the owner's sign-in. It reads CODEOWNERS from the PR's base branch, never its head, and applies the `diff` step's ledger rule to the PR's file statuses; it never reads an added ledger entry. It requires `--match-head-commit` set to the head commit it read, and its denial gives the exact command to retry. It catches its own errors and denies, so a merge that the running guard cannot check does not pass. A hook that fails before it decides is a separate case, which Spec 1 section 4 documents with the exit-code workaround.

### CODEOWNERS (plan 2 seeds it; plans 3 to 7 read or write it)

- Walk has one active line, `* @<owner>`. Without `--owner`, `init` writes it as `# * @<owner>`, and `rs-setup` writes the line.
- The Protected set follows, commented out, as `# /<path> @<owner>` lines, in Spec 1 section 4's order. Flight uncomments them and removes the `*` line.
- The `diff` step and `devctl hook` read `<pattern> @<owner>` lines, commented or not, and never treat `*` as Protected. doctor accepts each path with or without the leading `/`, and requires the Python settings files only for the Python stack.
- As plan 3 built it, the seed has a `##` comment after `/**/CLAUDE.md`: "Harness settings for Workers and Reviewers join with rapid-ship's Spec 2." After the re-scope, plan 5 removes the comment from both CODEOWNERS templates and from this repository's CODEOWNERS, and adds no line: `/.claude/` already covers the Claude Code wiring. Codex's wiring adds `/.codex/`, and agy's widens `/.agents/skills/` to `/.agents/`, when they land. The `/**/` lines keep the leading `/` that the tests' pattern `# /\S+ @<owner>` reads. GitHub documents `**/name` without it, so before Flight confirm that GitHub requests the code owner for a nested `AGENTS.md`, as plan 3's record asks for `ruff.toml`.
- Plan 6 renders each stack's Protected lines under its directory, such as `# /frontend/package.json @<owner>`. The rule for existing Corrections ledger entries is devctl's, not a CODEOWNERS line. The ledger's format, `/docs/corrections/README.md`, is a CODEOWNERS line, which Spec 3's plan adds.

### Suppressions, PR body, feature and Pattern front matter

Plan 3 built these; Spec 1 section 5 describes them. Plan 5 adds the Pattern `task` key, the `## Lessons` section, and the Evidence line `Over the diff cap: <reason>`, read only inside `## Evidence`, like `Removed tests:`. Plan 6 adds the TypeScript suppressions, with a table of rule names like plan 3's. Plan 3 also built these details, which Spec 1 leaves out:

- A suppression's rules join sorted, separated by `,` (`E501,F401`), and an entry's `rule` is normalised the same way. The marker follows the suppression on its line: `# noqa: S603  # rs-exception: EX-1`. The seeded `exceptions.toml` holds comments only.
- [Plan 3's suppression table](2026-10-14-devctl-check.md#task-7-exceptions-step) maps each suppression form to its rule name, such as `type-ignore`, `no-cover`, `mypy:ignore-errors`, `mypy:disable-error-code`, `skip`, `importorskip`, `autouse`, `gitleaks` and `zizmor:a,b`. Every `exceptions.toml` entry uses these names, including those that `rs-setup` writes for existing suppressions (plan 7).
- The rule code lives in `devctl/check/stacks/python.py` (`comments`, `comment_rules`, `marker_rules`) and `stacks/agnostic.py` (`text_rules`).
- In the Evidence section, a command is a list item that starts with a code span, a colon and text, or a fenced block whose first non-empty line starts with `$ ` and that has another non-empty line. `Not covered:` starts a line outside code, with text after the colon. Backticks around a removed test's identity are optional, and `<name>` is `test_x` or `TestA::test_x`.

### Kit migrations (plan 5)

```python
# rapid_ship/kit/migrations.py
@dataclass(frozen=True)
class Migration:
    id: str  # "<kit version>-<slug>", unique
    path: str  # the seeded file it edits
    applies: Callable[[str], bool]  # the file holds the old content
    edit: Callable[[str], str]  # the new content; applies(edit(text)) is False
    explanation: str  # one line for the PR body


MIGRATIONS: tuple[Migration, ...]
```

`sync` without `--in-place` commits the edits of every migration that applies on `rapid-ship/kit-migrate-<version>`, based on the sync branch, and opens its own PR. With `--in-place` it lists them and writes none (Spec 1 section 3).

### Stacks (plan 6)

- `project.toml` and the lock hold one `[[stack]]` table per stack, with `name` and `directory`.
- A stack's templates render under its directory; the common templates render at the root.
- `check` runs the common steps once and each stack's steps in its directory. A stack step's name gains its directory in parentheses, such as `lint (frontend)`, unless the repository has one stack at the root.
- `devctl/check/stacks/<name>.py` supplies each stack's steps, suppression forms, reference kinds and source extensions.

## Plan 4: Doctor and Agent identity

**State:** built in PRs #31 (`plan4-settings-tokens`), #32 (`plan4-doctor`) and #33 (`doctor-agent-identity`), which are not merged yet. Its plan document, `2026-10-16-doctor-and-agent-identity.md` on those branches, holds the tasks and the verification record. The follow-ups below are built on the same PRs. Its live trials (task 10) are a pending Owner step. The outline after the follow-ups is the plan as written, without what follow-ups 7 and 9 removed.

### Plan 4 follow-ups, before #31 to #33 merge

The owner's decisions of 2026-10-19 and 2026-10-20 changed plan 4's built code: organisation-owned repositories are supported from the start, which brings backlog item PRO-105 into scope, and rapid-ship does not run agents across several Providers, so devctl knows nothing about them (follow-up 7). The decision of 2026-10-20 to wire Claude Code alone in plan 5 made four of its texts wrong (follow-up 8). The owner's review of PR #27 on 2026-10-20 has `doctor --skills` probe Claude Code alone (follow-up 9). Each change landed on the PR that holds its file and was merged up the stack. Their plan is [Plan 4 follow-ups](2026-10-20-plan4-follow-ups.md). Follow-ups 1 to 4 and 7 to 9 are built; follow-up 5 and the re-storing of this repository's two keys are pending Owner steps.

1. **Built: doctor's code owner (#31, #32).** `settings.py` accepts `[github] code_owner`, `"@<login>"` or `"@<organisation>/<team>"`, and the project templates and this repository's `project.toml` record it. `doctor_github.py`'s CODEOWNERS item checks CODEOWNERS against it instead of the repository's owner, and reports the item missing while the key is unset (Spec 1 sections 4 and 6).
2. **Built: the organisation flow (#33).** `rapid_ship/github_app.py` no longer refuses a repository that an organisation owns. When an App must be created and `gh`'s login is an active admin of the organisation, it creates the App through the organisation manifest flow at `https://github.com/organizations/<organisation>/settings/apps/new`. `rapid-ship app --import-key {worker,reviewer}`, in `rapid_ship/app_import.py`, stores a key that a developer generated on GitHub, read on stdin (Spec 1 section 3).
3. **Built: Keychain names (#31, #33).** Each item's name carries the App's ID, `rapid-ship/<role>-app/<App ID>`, in `devctl/github/app.py` and `rapid_ship/app_keychain.py`, with their parity test. Before it creates an App, `rapid-ship app` looks for one whose key the Keychain holds. It re-stores an item with the old name under its new name, reading the App ID from the item's account, and leaves the old item in place. Owner step: the owner's two items of 2026-10-19 still have the old names until the owner runs `uv run rapid-ship app` once on #33.
4. **Built: text that the owner's review of 2026-10-19 made wrong (#31, #32):**
   - the `[dispatch]` removal message in `settings.py` no longer says that the Lead brief's Focus caps parallel Workers; rapid-ship takes no notice of how many Sessions run;
   - `probed_harnesses` in `doctor_skills.py` lost its note `(Spec 1 section 6, a Proposal)`: the owner accepted it.
5. **Owner step: the organisation trial.** On a test organisation, an admin runs `rapid-ship app`; a developer, made an App manager of both Apps, generates a key and imports it with `--import-key`; and `./devctl doctor` passes with a team as the code owner. The trial settles whether an App manager may generate a private key (Spec 1 section 11).
6. **Done: this repository's Agent identity.** The owner created the Worker App (ID 5376519, `proxy-hatch-rs-worker`) and the Reviewer App (ID 5376520, `proxy-hatch-rs-reviewer`) with `rapid-ship app` on 2026-10-19, and installed both on `proxy-hatch/rapid-ship`. #33 records their IDs and slugs under `[github]` in `.rapid-ship/project.toml`, which turns this repository's Agent identity on. The message of the commit that records them says that `./devctl doctor` reported all four Agent identity items ok. The doctor output and its exit code were not kept; plan 4's verification record on #33 says what is known.
7. **Built: no `[roster]` in devctl (#31 to #33).** The owner's decision of 2026-10-20 descopes running agents across several Providers (Spec 1 section 1), so devctl knows nothing about Providers. On #31, `settings.py` dropped `[roster]` with its `Agent` type, and the project templates and this repository's `project.toml` dropped the commented table. `settings.py` kept the `Harness` alias, which `harness.py` imports on #32, until follow-up 9 deleted it; follow-up 8 corrected its comment first. devctl refuses a leftover `[roster]` table and the `[agents]` table with "rapid-ship does not run agents across several Providers; delete the table", which names no skill (2fa9963). In `tests/devctl/test_devctl_settings.py`, `test_a_leftover_roster_is_refused_and_names_rs_providers` became `test_a_leftover_roster_is_refused`, and the `REPLACED_BY` entries for `agents` and `roster` no longer name `rs-providers`. The test is new on #31, so the rename removes no test from #31's base and needs no `Removed tests:` entry. #31's comments, guides and plan text no longer name `rs-providers`, and plan 4's plan document no longer describes the Roster or the Harness sign-in items as built (95438b9). On #32, doctor dropped its Harness sign-in items, with `doctor_signin.py` and the agy sign-in probe in `harness.py`, and `--skills` probes each of `claude`, `codex` and `agy` on `PATH`, which follow-up 9 narrowed to `claude` (Spec 1 sections 4 and 6). #32 and #33 changed their own text that named `rs-providers` in 6a65864 and 3c7ecb5. On #33, the merge of #32 moved the tests that each Harness gets only its own sign-in variables from the deleted sign-in items to `--skills`, and follow-up 9 kept Claude Code's case alone (2172517).
8. **Built: text that plan 5's Claude Code wiring made wrong (#31 to #33).** The owner's decision of 2026-10-20 has plan 5 wire the Harness guardrails for Claude Code alone; Codex and agy wait for the hook spike (Spec 1 section 4). On #31, the comment on `Harness` in `settings.py` stopped saying the Kit wires all three; it became `# the Harnesses doctor --skills probes (Spec 1 section 6)` (b0bedf9), before follow-up 9 deleted the alias. ARCHITECTURE.md's CODEOWNERS bullet says "`.claude/` already covers the Claude Code wiring; Codex's and agy's wiring files join the set when they land." in place of "The Harness settings join it with plan 5.", and its plan 5 bullet follows plan 5's goal below. The copies of these texts in plan 4's plan documents changed with them. On #32, the last sentence of the comment on `PROTECTED_PATHS` in `doctor_rules.py` says that Codex's wiring adds `.codex/` and agy's widens `.agents/skills/` to `.agents/`, as in the doctor sketch above (58d52a5), and the merge of #31 in 95cbd8a brought ARCHITECTURE.md's two bullets and the plan document's copies. On #33, the merge of #32 in 11a5048 brought ARCHITECTURE.md's two bullets. Task 11 of the follow-ups plan records it.
9. **Built: `doctor --skills` probes Claude Code alone (#31 to #33).** The owner's review of PR #27 on 2026-10-20 has `doctor --skills` probe Claude Code alone until another Harness's integration lands, after the PRO-139 spike (Spec 1 section 6). On #32, `--skills` adds its temporary worktree and asks one headless Claude Code Session which skills it can load, only when `claude` is on `PATH`. The codex and agy probe code goes with its tests: their models, arguments and parsers in `harness.py`, with its import of the `Harness` alias, and their entries and the note on Google's consumer terms in `doctor_skills.py`. Each test removed against its PR's base is declared under `Removed tests:` in that PR's body, with the test that covers what remains. Built on #31: `settings.py` dropped the `Harness` alias, because no setting names a Harness and #32 needs no type for three Harnesses once it probes Claude Code alone (a24ee32). Plan 4's plan document on #31 says that #32 narrows the probe, and its task 10 expects one `skills (claude)` item and no longer warns about Google's consumer terms (d7529c5). #31's guides do not describe the probe. Built on #32: `probed_harnesses` names `claude` only when it is on `PATH`; without it, the skills item is missing with "claude is not on PATH", and codex and agy are never started. `harness.py` keeps Claude Code's arguments, `PROBE_MODEL` and parser, and the tests of the codex and agy probes went (c05e443). `doctor.py`'s `--skills` help and the root AGENTS.md doctor line no longer say "one headless Session per Harness", and ARCHITECTURE.md's plan 4 bullet and plan 4's plan document describe the Claude Code probe (c05e443, 0700157). Built on #33: the merge of #32 kept the claude case alone in the `--skills` tests of each Session's sign-in variables, and made `test_a_session_gets_its_harness_sign_in_and_no_devctl_as_variable` probe claude instead of agy (2172517). `SIGN_IN_VARIABLES` in `doctor_items.py` no longer names codex or agy (3e7ad36). No test function is removed against #32; #33's body names the dropped codex and agy cases. ARCHITECTURE.md's `--skills` bullet describes the Claude Code probe, and Step 13 of plan 4's pending Owner steps expects one `skills (claude)` item when `claude` is on `PATH` (e4ae4e2). Task 12 of the follow-ups plan records it.

### Plan 4 outline

**Goal:** Give devctl `doctor`, with `--skills`, and give the owner optional Agent identity: `rapid-ship app`, the token code and `devctl as`. Move the settings to the re-scope: the escalation list and each App's ID and slug, with `[agents]`, `[linear]`, `[dispatch]` and `[release]` removed and `gate.toml` no longer read.

**Method:** a fresh branch from the head of #30 brings over only the surviving code of `codex/github-commands` (head `901bd43`): cherry-pick where a commit applies cleanly, copy otherwise, then reshape. It landed as three reviewed PRs, #31 to #33; most of its code was reviewed on the old branch.

| Source on `codex/github-commands` | In plan 4 |
| --- | --- |
| `98082fb`, `de800ae`: the two `process.py` fixes, `process.first_line` and `run_process` finishing when macOS refuses SIGTERM | Applied by hand to the template, with their tests; `sync` regenerates the vendored copy and the lock |
| `1eb138d`: the REST client | Copied: what doctor and `devctl as` use |
| `620e5ff`, `f5177ba`: token minting and the askpass helper | Copied, without the Claim-only git helpers |
| `0c2b27f`, `51c9300`: doctor's local items and sign-ins | Copied, without the Linear item; follow-up 7 removed the sign-in items |
| `ebe3bd2`: doctor's GitHub and App items | Copied; App items only with Agent identity on; ruleset and CODEOWNERS read `[escalation]` |
| `013cdac`: `doctor --skills` | Reshaped: a temporary worktree at `HEAD` with the owner's git, no App fetch |
| `f9c3872`: worktrees | Only `probe_worktree`, reshaped |
| `3eec7a1`, `901bd43`: `rapid-ship app` | Cherry-picked or copied |
| `db12380`, `d44b673`, `eb2faa1`, `788375f`, `0b20f0b`, `6563e9a`, `2c0a333`, `9c0adcc`, `e3380ea`, `cd6fde6` | Not brought over: `dispatch`, `claims`, `claim_status`, `release`, `records`, `pr`, `review`, `merge`, the gate log and the Session registry, about 2,100 lines plus their tests |

**Files:**

- Templates, then vendored with `sync`: `rapid_ship/templates/common/tools/devctl/devctl/` `process.py`, `settings.py`, `cli.py`, `doctor*.py`, `harness.py`, `identity.py`, `github/`, `check/steps.py`, `check/diff.py`, `check/kit.py`, `check/stacks/python.py`; `tools/devctl/pyproject.toml` and `uv.lock`; `rapid_ship/templates/{python,agnostic}/.rapid-ship/project.toml` and `kit.toml`; `common/.rapid-ship/gate.toml` is deleted.
- `rapid_ship/cli.py`, `rapid_ship/github_app.py`; root `pyproject.toml` and `uv.lock`.
- This repository's `.rapid-ship/project.toml`, edited in place because it is seeded, and its `.rapid-ship/gate.toml`, deleted.
- Tests: `tests/devctl/test_devctl_settings*.py`, `test_devctl_doctor*.py`, `test_devctl_harness.py`, `test_devctl_github_api*.py`, `test_devctl_github_app*.py`, `test_devctl_askpass*.py`, `test_devctl_identity*.py`, `test_devctl_probe_worktree.py`, `github_fakes.py`, `github_fixtures.py`, `fixtures/github/`; `tests/test_kit_app*.py`; `tests/conftest.py`.
- Tests that use what task 2 removes: `tests/devctl/check_workspace.py`, `test_devctl_diff_removed_tests.py`, `test_devctl_check_cli.py`, `test_devctl_cli.py` for the `gate.toml` error, and `tests/test_kit_contents.py` for the seeded `gate.toml` and the `linear` and `dispatch` tables.
- Docs: `README.md`, `ARCHITECTURE.md`, the root `AGENTS.md` (its link to `gate.toml`), `rapid_ship/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, the status lines of Spec 1, this index and the rapid-ship design, and the trial record under `docs/trials/`.

**Tasks:**

1. Branch from #30's head. Apply `98082fb`'s `process.first_line` and `de800ae`'s `_kill_group` fix to the template's `process.py`, with their tests, then run `uv run rapid-ship sync --in-place`. Neither commit cherry-picks cleanly onto #30: both carry `kit.lock` hunks for other hashes, and `98082fb` also edits `github/app.py` and `worktrees.py`, which #30 lacks. Never cherry-pick a `kit.lock` hunk.
2. Settings: `[escalation]` and each App's ID and slug; remove `[agents]`, `[linear]`, `[dispatch]`, `[release]`, `GateSettings` and `CheckContext.gate`. The `diff` step drops its Flight note. The project templates and this repository's `project.toml` follow. The Kit stops seeding `gate.toml`, and this repository deletes its own copy and the root AGENTS.md link to it.
3. The REST client, App tokens and the askpass helper, with PyJWT. Tests against a fake HTTP server and a fake `security`, labelled simulated.
4. doctor's core and local items, without the Linear item.
5. doctor's GitHub items: the ruleset for Walk and for Flight with and without Agent identity, CODEOWNERS against `every_pr`, delete branch on merge, fork workflow approval, the plan-limit message; App items only with Agent identity on.
6. `doctor --skills`: a detached worktree at `HEAD` in a temporary directory; `claude` when it is on `PATH`.
7. `rapid-ship app`, printing each App's ID and slug, with the parity test for the Keychain services and permissions.
8. `devctl as`: `push` and `gh`, every refusal, the token only in the child's environment; tests with fake `gh` and `git` executables and a local bare repository.
9. Guides and ARCHITECTURE.md; `uv run rapid-ship sync --in-place`, then `uv run rapid-ship status --strict`.
10. Live trials, an Owner step: `rapid-ship app` on a scratch repository; Agent identity end to end, including whether GitHub counts the Reviewer App's approval; doctor reading the applied ruleset; a GitHub Free private repository's ruleset answer.
11. Verification and record.

## Plan 5: Kit standards and Harness guardrails

Its plan document, [Kit standards and Harness guardrails](2026-10-21-kit-standards-and-guardrails.md), holds the tasks of the four PRs below and lands in PR 5.1.

**Goal:** Run the hook spike in Claude Code, Codex and agy first. Then ship the standards and guardrails every project works under: `devctl hook` with G1 to G5, G7, G8 and the merge guard, and its seeded wiring for Claude Code; the README.md and ARCHITECTURE.md seeds with map rule 8, and `./devctl doctor --settings`; the Pattern `task` key and Lessons section, with the Python starter Patterns; the `SKILL.md` rule; the 1,500-line diff cap with its escalation kind, and the ledger rule; a CI concurrency group for each push run; documented and validated settings; and `sync`'s migrations. Plan 5 wires no other Harness: the spike's report decides whether a follow-up, with its own plan, adds the wiring for Codex or agy (Spec 1 section 4).

**PRs**, in order. Each is reviewed and merged on its own, and its last task records its verification:

| PR | Tasks | Content |
| --- | --- | --- |
| 5.1 | 1 | The hook spike, backlog PRO-139: a trial record, and the Spec 1 edits its result needs. No product code |
| 5.2 | 2 to 8 | Guardrails: `devctl hook`, the merge guard, the Claude Code wiring and the CODEOWNERS comment, with their live trial |
| 5.3 | 9 to 14 | Standards: the seeds, `doctor --settings`, map rules 5, 7 and 8, the Python starter Patterns, the diff cap, the ledger rule and the CI concurrency |
| 5.4 | 15 and 16 | Settings and migrations: documented seeds and `sync`'s migrations |

If review finds a PR too large, it splits at a task boundary.

**Files:**

- 5.1: the trial record under `docs/trials/` and `docs/trials/AGENTS.md`; Spec 1 sections 4 and 11 where the result changes them.
- 5.2: devctl templates under `rapid_ship/templates/common/tools/devctl/devctl/`, then vendored with `sync`: `codeowners.py`, `hook.py`, `hook_protocols.py`, `merge_guard.py`, `cli.py`, `check/diff.py`, `doctor_local.py`, `doctor_rules.py`. Kit templates: `common/.claude/settings.json`, `common/.github/CODEOWNERS`, `python/.github/CODEOWNERS`, `kit.toml`. This repository: `.github/CODEOWNERS`, edited in place, and `.claude/settings.json`, created by `sync`. Tests: `tests/devctl/test_devctl_codeowners.py`, `test_devctl_hook*.py`, `test_devctl_merge_guard*.py`, `fixtures/hooks/claude/`, `test_devctl_doctor_wiring.py`, `tests/test_kit_templates*.py`.
- 5.3: devctl templates: `check/map.py`, `check/diff.py`, `check/evidence.py`, `check/stacks/python.py`, and `cli.py` and `doctor.py` for `--settings`. Kit templates: `common/README.md`, `common/ARCHITECTURE.md`, `common/AGENTS.md`, `python/AGENTS.md`, `common/docs/patterns/README.md`, the Python starter Patterns with their reference code and tests under `python/`, `{python,agnostic}/.rapid-ship/project.toml` for the new escalation kind, `common/.github/workflows/devctl-check.yml`, `kit.toml`. This repository: the root `AGENTS.md` and `.rapid-ship/project.toml`, edited in place, and the workflow through `sync`. Tests: `tests/devctl/test_devctl_map_*.py`, `test_devctl_diff_*.py`, `test_devctl_evidence_step.py`, `test_devctl_doctor*.py`, `test_devctl_ci_templates.py`, `tests/test_kit_contents.py`, `tests/test_kit_templates*.py`.
- 5.4: devctl template `settings.py`. `rapid_ship/kit/migrations.py`, `rapid_ship/kit/sync.py`, `rapid_ship/cli.py`. Kit templates: every seeded TOML file, both CODEOWNERS templates and the CI workflow, for their comments. Tests: `tests/devctl/test_devctl_settings*.py`, `tests/test_kit_migrations*.py`, `tests/test_kit_sync*.py`, and the seed-documentation test.
- Docs, in each PR: `ARCHITECTURE.md`, the template and directory guides, and the trial record under `docs/trials/`.

**Tasks:**

1. The hook spike (PRO-139), an Owner step that an agent prepares. In Claude Code, Codex and agy, in a lead Session, inside a subagent and in a headless Session, record: whether `PreToolUse` fires for shell and file-edit tools; whether Codex hooks can ask; how each Harness treats a hook's exit 1, uv's exit 2, a hook timeout and the hook's deny answer; the fields each event carries, the working directory included; the review in Codex's `/hooks`; and the time a `devctl hook` run adds to each tool call. Write the trial record, and change Spec 1 where the result differs from it. The owner decides from the measured time whether G1 to G4 stay in the hook, and from the record whether a follow-up adds the wiring for Codex and for agy, Codex's without G5 if its hooks cannot ask. Each such follow-up gets its own plan.
2. Move the Protected-set reader and matcher from `check/diff.py` into `codeowners.py`, with no change in behaviour.
3. `devctl hook`'s rules: G1 to G5, G7 and G8 on a normalised tool call, with G3 denying `gh pr merge --admin`, each `gh api` form of Spec 1 section 4 and each form of `git push` to the default branch, tested from a table of command lines and edits, and G1 to G4 with unreadable settings.
4. Claude Code's hook protocol: its event JSON in, its decision format and exit code out, from recorded fixtures. An internal error exits 1, and `hook_protocols.py` documents the exit codes as a workaround.
5. The merge guard: `find_merge` for each form, run directly and through `devctl as <role> gh`, with G3 denying the `admin`, `push`, `rest` and `graphql` forms, and `push` with `origin/HEAD` present and missing; `guard` on `gh pr merge` against a fake `OwnerGet` for passed, pending, failed and missing check runs, Protected paths at the base, renames, ledger changes, entries added as `open` and as `implemented`, neither Protected, a merge without `--match-head-commit` or naming another commit, denied with the exact retry, and a PR it cannot read or an error inside the guard, both denied; no GitHub read for any other command.
6. The seeded `.claude/settings.json`, `kit.toml`, doctor's wiring item, and this repository's wiring through `sync`.
7. The placeholder comment about Harness settings, removed from both CODEOWNERS templates and from this repository's CODEOWNERS. `/.claude/` already covers the wiring, so doctor's `PROTECTED_PATHS` stays as it is.
8. Live trial, an Owner step: each rule in Claude Code, in the lead Session and inside a subagent; the merge guard on real PRs through `gh pr merge` and `devctl as worker gh pr merge`, and G3 denying a merge through `gh api` and a `git push` to the default branch.
9. The README.md and ARCHITECTURE.md seeds, the root guide's new rows, and map rule 8. `./devctl doctor --settings`, which reads and validates only the settings, and makes no GitHub request. The root guide asks each Session to run it first unless the Session runs the full doctor, as `rs-lead` and `rs-preflight` do (Spec 1 section 6).
10. The Pattern `task` key and `## Lessons` section: the seeded README and map rule 5.
11. The Python starter Patterns, for error handling, configuration and input validation, with reference code and tests in the new-project skeleton, passing map rule 5 and `./devctl check` on a new project; and the Python performance Pattern, which documents py-spy, with its profiling entry point and enforcing check in the skeleton (Spec 1 section 4).
12. The `SKILL.md` rule in map rule 7.
13. The diff cap: 1,500 lines, its exclusions and the `Over the diff cap:` declaration; the seeded escalation kind; and the ledger rule in the `diff` step: a change to an existing entry is Protected, and an added entry is not checked.
14. A concurrency group for each push run in the CI workflow, which zizmor still passes.
15. Documented seeds: a short comment for each key of every seeded TOML file, and for each line or key of every other settings file the Kit ships whose format allows comments, such as CODEOWNERS and the CI workflow; the loaders' range and value checks, errors that name what each key accepts, and the test that holds each seed to its loader.
16. `sync`'s migrations: `migrations.py`, the second branch and its PR, and `--in-place` listing them. The first migrations remove plan 4's tables. Task 7's comment needs none, because it changes no Protected path.

## Plan 6: TypeScript stack and several stacks in one repository

**Goal:** Support a Python backend with a React TypeScript frontend from day one. `project.toml` lists each stack with its directory, `init` writes each stack's files under its directory, and `devctl check` runs each stack's steps there. The TypeScript stack brings ESLint, Prettier, `tsc --noEmit`, Vitest and `npm audit`, with npm as the package manager, its guardrail settings, a React skeleton, its starter Patterns and CI support. This brings part of backlog PRO-108 into scope; the rest of monorepo support stays deferred.

**PRs**, in order. Each is reviewed and merged on its own, and its last task records its verification:

| PR | Tasks | Content |
| --- | --- | --- |
| 6.1 | 1 to 5 | Several stacks, with Python and the agnostic stack only |
| 6.2 | 6 to 9 | The TypeScript checks |
| 6.3 | 10 to 13 | The TypeScript templates and CI |

**Files:**

- 6.1: `rapid_ship/kit/stacks.py`, `templates.py`, `init.py`, `lock.py`, `status.py`, `sync.py`, `migrations.py`; `rapid_ship/cli.py`; the `project.toml` and CODEOWNERS templates; devctl templates `settings.py`, `check/__init__.py`, `check/steps.py`, `check/exceptions.py`, `check/filesize.py`, `check/references.py`, `doctor_local.py`, `doctor_rules.py`. This repository's `.rapid-ship/project.toml`, migrated in place. Tests: `tests/test_kit_stacks*.py`, `tests/test_kit_init*.py`, `tests/devctl/test_devctl_settings*.py`, `test_devctl_check_stacks*.py`.
- 6.2: devctl templates `check/stacks/typescript.py`, `check/diff.py`, `check/references.py`, `cli.py` for `--install`, `doctor_local.py`, `doctor_rules.py`. Tests: `tests/devctl/test_devctl_typescript*.py`, with fake tools in a fake `node_modules/.bin`.
- 6.3: `rapid_ship/templates/typescript/`: `package.json`, `tsconfig.json`, `eslint.config.js`, `vite.config.ts`, `index.html`, `.gitignore`, the `src/` skeleton and its `AGENTS.md`, the starter Patterns with their reference code and tests, and the Protected lines; `kit.toml`; `common/.github/workflows/devctl-check.yml`. Tests: `tests/test_kit_typescript*.py`, `tests/devctl/test_devctl_ci_templates.py`, and an integration test of `init` with a Python `backend/` and a TypeScript `frontend/`, labelled as needing network access.
- Docs, in each PR: `ARCHITECTURE.md`, the template and directory guides, and the trial record under `docs/trials/`.

**Tasks:**

1. `[[stack]]` in the settings and the lock, with its checks; devctl reading the old `stack` key for one Kit version, with a warning; and the migration that rewrites it.
2. `init --stack NAME[=DIRECTORY]`; without it, a recursive search for stack roots that skips vendored and generated directories, proposes what it found, with the `--stack` options and the instruction to confirm them with the owner and rerun, and writes nothing; and templates rendered under a stack's directory.
3. `project.toml` and CODEOWNERS rendered from every stack, with each stack's Protected lines under its directory; doctor's CODEOWNERS and Python floor items for each stack.
4. `check` for each stack: the common steps once, and each stack's steps in its directory with their names; file ownership for the exceptions and file-size steps; references resolved against their stack.
5. This repository stays one Python stack at the root: its `project.toml` migrates in place, and the output of `./devctl check` keeps its step names.
6. The TypeScript steps: format, lint, types, tests and audit, from `node_modules/.bin` and npm; a missing tool blocks its step with the command that installs it; `check --install`.
7. The TypeScript suppressions and their rule names, and the `eslint:` and `type:` references.
8. The diff policy for Vitest: removed tests by their title chain, and tautologies.
9. doctor's `node` and `npm` items and the TypeScript floor item.
10. The TypeScript templates: the settings of Spec 1 section 4, documented inline where the format allows, in `tsconfig.json`, `eslint.config.js` and `vite.config.ts`; the React skeleton and its `AGENTS.md`, passing `./devctl check` after `npm install`. Pin the tools and the Node.js version.
11. The TypeScript starter Patterns, with reference code and tests, passing map rule 5; and the TypeScript performance Pattern, which documents the browser's performance tools and React's Profiler, with its profiling entry point and enforcing check in the skeleton (Spec 1 section 4).
12. The CI workflow: `actions/setup-node`, pinned by commit SHA and run only when a `package-lock.json` exists, and `./devctl check --tier full --install`; zizmor still passes.
13. Live trial, an Owner step: `init` and `./devctl check` on a scratch repository with a Python `backend/` and a React TypeScript `frontend/`, locally and in CI.

## Plan 7: `rs-setup` and `rs-health`

**Goal:** Ship the Kit's first skills: the engineering skills pinned in an upstream lock, `rs-setup`, `rs-health` with the audit it shares with `rs-garden`, and the optional `rs-contribute`. Retire `rapid-ship-engineering`. Then run `rs-setup` on hello-rapid-ship and apply its GitHub settings to this repository, and rewrite the documentation site. `rs-setup` knows the stacks from plan 6, gives the advice on Agent identity, and ends an existing repository's Setup with the tool-settings PR.

**PRs**, in order. Each is reviewed and merged on its own, and its last task records its verification:

| PR | Tasks | Content |
| --- | --- | --- |
| 7.1 | 1 to 4 | The engineering skills, and `rapid-ship-engineering` retired |
| 7.2 | 5 and 6 | `rs-setup` and its `ruleset.json` |
| 7.3 | 7 and 8 | `rs-health` with the shared audit, and `rs-contribute` |
| 7.4 | 11 | The documentation site |

Tasks 9 and 10 are Owner steps after 7.3, and 7.4 follows them.

**Files:**

- 7.1: Kit skills under `rapid_ship/templates/common/.agents/skills/`, each with its generated `.claude/skills` link: `rs-tdd/`, `rs-diagnosing-bugs/`, `rs-codebase-design/`, `rs-pr/`, `rs-writing-for-agents/`, `rs-writing/`, `rs-ponytail/`. `rapid_ship/upstream.lock`, `rapid_ship/templates/kit.toml`. Removed: `rapid_ship/skills/rapid-ship-engineering/` and its `.agents/skills` and `.claude/skills` links. Updated: the root `AGENTS.md`, `rapid_ship/AGENTS.md`, `.agents/AGENTS.md`, `.claude/AGENTS.md`. Tests: `tests/test_kit_upstream.py` with `tests/fixtures/upstream/`.
- 7.2: `rs-setup/` with `ruleset.json` and its references: the advice table on Agent identity, the stylistic options of each tool, and each step's known failures with the fix it offers. Tests: `tests/devctl/test_devctl_ruleset_json.py`.
- 7.3: `rs-health/` with `references/audit.md`, `rs-contribute/`, and `kit.toml`.
- 7.4: `website/` (config, sidebar, home page), the site's pages under `docs/`, and `README.md`; `docs/getting-started.md` is deleted.
- Docs, in each PR: `ARCHITECTURE.md` and the trial record under `docs/trials/`.

**Tasks:**

1. The upstream lock and the verbatim forks, `rs-codebase-design` and `rs-writing-for-agents`, with the lock test.
2. The patched forks, `rs-tdd`, `rs-diagnosing-bugs` and `rs-pr`, whose Evidence follows Spec 1 section 5.
3. `rs-writing` and `rs-ponytail`, from this repository's engineering references.
4. Retire `rapid-ship-engineering`, and point this repository's root AGENTS.md to `rs-writing` and `rs-ponytail`.
5. `rs-setup`: Spec 1 section 8's steps, with the stacks, the starter Patterns, the advice table, the tool-settings PR and guided rectifying, and `ruleset.json` checked by `ruleset_problems`. Steps 10 (tracker) and 11 (metrics) come later, with Spec 2's and Spec 3's plans.
6. `rs-setup`'s references: the stylistic options of each tool, and each step's known failures with the explanation and the fix it offers.
7. `rs-health` and its `references/audit.md`: Spec 1 section 9, with the base rule on hidden or obscured errors.
8. `rs-contribute`, listed under `optional_skills`.
9. Live trial, an Owner step: `rs-setup` on a new scratch repository with a Python `backend/` and a React TypeScript `frontend/`, and on hello-rapid-ship, including `doctor --skills` in Claude Code and the tool-settings PR; `rs-health` on hello-rapid-ship, ending with a standards milestone in its tracker.
10. Owner step: apply `rs-setup`'s GitHub settings to `proxy-hatch/rapid-ship`.
11. The documentation site. It teaches why a reader needs rapid-ship before how to use it. Only the home page sells, with the owner's tagline of 2026-10-20: "Becoming a 100x developer starts with agents that earn your trust." and the line "Agents that prove their work earn autonomy, so you can stop watching every one of them." Everywhere else it is plain and professional. The sidebar is Start (Home, Why rapid-ship, Get started around `rs-setup`, The journey), Concepts, Guides titled by outcome, and Reference, with the design records collapsed under Project. Every page carries a Built or Designed status, shows a concrete case before it names a concept, and ends each step with output from a real run. `README.md` becomes a lean GitHub front page, and "Ship more. Supervise less." is retired. Maintainers keep the full proposal, with the page list, page templates and style rules, in Linear, in the rapid-ship project's documents.

## Plan style

Plans follow the writing-plans structure: header, global constraints, review focus, then tasks with files, interfaces, failing tests first, implementation, verification and commit. Following this repository's guidance, plans stay concise. They show code for interfaces, test cases and non-obvious steps, and point to the spec instead of repeating it. They never leave a step as "TBD", "handle edge cases" or "similar to task N".
