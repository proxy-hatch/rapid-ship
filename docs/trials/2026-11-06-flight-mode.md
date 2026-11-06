# Dog-fooding Flight: local verification

This repository changes to Flight with `every_pr = false` and an active Protected set.
This is a repository policy change; the Kit still supports both Walk and Flight.
The owner merges this Protected Mode-change PR, after its prerequisite PR #59.
The change includes MAIN-GREEN at `dc40a420d024aad10b93b716b8769307aa7061ec`.
Its prerequisite merge has an empty remerge diff and identical lock and test blobs.

## Before Flight records

The [check plan's remaining limits](../superpowers/plans/2026-10-14-devctl-check.md)
identify three prerequisites: complete settings coverage, no conflicting uv extras, and live CODEOWNERS matching evidence.
The [plan index](../superpowers/plans/2026-10-14-kit-and-setup.md#codeowners-plan-2-seeds-it-plans-3-to-7-read-or-write-it)
also requires evidence for nested guides.
The [Agent identity trial](2026-10-21-agent-identity.md#code-owner-review-at-an-approval-count-of-0)
records GitHub blocking a nested `docs/AGENTS.md` change under `/**/AGENTS.md` until the owner's approval.
That historical observation is not a new root Ruff trial.

Root `ruff.toml` and `.ruff.toml` have explicit root entries here, alongside `/**/` entries for nested settings.
The current doctor requires explicit root entries for most Python settings; those remain.
All nested Python settings entries use `/**/<path>`, retaining the planned multi-stack doctor interface.
Local matcher probes cover root, one-level and two-level settings paths.
They do not show GitHub requesting an owner.
A live root Ruff request remains unverified; record it on the first PR that changes that file.
No such file exists in this tree, and this task made no external writes.

## Settings and Pattern inventory

The inventory uses tracked files, including the entire template tree, and check-step source.
Line numbers below refer to this change's `.github/CODEOWNERS`.
All active rules name the configured owner, and no catch-all remains.

| Settings or inputs read by checks | CODEOWNERS lines | Scope inspected |
| --- | --- | --- |
| `.rapid-ship/project.toml`, `exceptions.toml`, `kit.lock` | 12 | Mode, stacks, map, tests, exceptions and Kit checks |
| `.github/workflows/`, `.github/CODEOWNERS` | 4 | Workflow audit, CI and Protected policy |
| `.gitleaks.toml`; optional `.gitleaksignore` | 28–29 | Secrets; inspected `extend.useDefault` and allowlist conditions |
| Optional `zizmor.yml`, `zizmor.yaml`, `.github/` settings | 30–31, 4 | Workflow audit; no standalone settings file exists |
| Root `pyproject.toml` | 32, 54 | Build metadata and dependencies; `tool.hatch`, `ruff` and its nested lint tables, `mypy`, `pytest.ini_options`, `importlinter` and contracts, `vulture`, `deptry` |
| `tools/devctl/pyproject.toml` | 7, 54 | Build metadata, dependencies, `tool.hatch`, `tool.uv.workspace` |
| `rapid_ship/templates/python/pyproject.toml` | 15, 54 | All nested tool tables listed for root, as starter settings |
| `rapid_ship/templates/common/tools/devctl/pyproject.toml` | 15, 54 | Build metadata, dependencies, `tool.hatch`, `tool.uv.workspace` |
| Optional root/nested Ruff files | 33–34, 44–45 | Both `ruff.toml` and `.ruff.toml`; neither exists |
| Optional mypy, pytest, setup, tox and import-linter files | 35–43, 55–63 | Both dotted and undotted names in the Protected contract; none exists |
| Root/nested `uv.toml`, `uv.lock` | 46–47, 64–65 | Locked check-tool execution, audit export and dependency inputs; three tracked locks, no `uv.toml` |
| `.python-version`, root/nested `.gitignore` and `.ignore` | 48–52 | Interpreter selection and source discovery/exclusion, including Ruff’s `.ignore` inputs |
| `rapid_ship/templates/kit.toml`, template settings and workflow trees | 15 | Kit/vendored comparisons and distribution inputs; Python and agnostic project seeds, exceptions, Harness wiring and devctl metadata |
| `.agents/hooks.json`, `.claude/settings.json` | 8–9 | Harness wiring checked by doctor |
| `docs/patterns/README.md` | 14 | No project Pattern implementation files exist |
| Four Python Pattern templates | 15, 23–26 | Configuration, error handling, input validation and performance |
| Common Pattern README template | 15 | Pattern format seeded into projects |

All four tracked `pyproject.toml` files were parsed, including their nested tool tables.
None declares `tool.uv.conflicts`; no standalone `uv.toml` exists.
This finding concerns this tree, not audit support for projects that declare conflicting extras.
Website package settings are not inputs to a devctl check step; no TypeScript stack is configured here.
The explicit project additions protect the App flow, key import/storage, public CLI, and Kit lock/template models (lines 16–22).
The entire template tree is Protected because it supplies the check implementation and settings.

## Local verification and limits

Baseline: 196 existing merge-guard and doctor/CODEOWNERS tests passed after importing MAIN-GREEN, before changing Flight settings.
The existing `test_a_passing_unprotected_merge_at_the_checked_head_gets_no_decision` covers the allowed Flight path.
Other existing cases deny Protected changes, missing checks, missing exact-head Reviewer App approval and mismatched heads.
The Flight body tests cover declared behavioural-test removals and diff-cap overages.
These tests use simulated GitHub responses; they are not hosted CI or live approvals.

A local Correction probe reproduced missing `.ignore` coverage before adding its rules.
The repository's `devctl.codeowners` matcher returned false for `.ignore`, `a/.ignore` and `a/b/.ignore`.
After adding `/.ignore` and `/**/.ignore`, all three paths match the configured owner, `@proxy-hatch`.
All active rules name that owner; 91 probes derived from the prior rules retain their coverage.
These are local matcher observations, not evidence of GitHub requesting an owner.
No Ruff discovery reproduction was run for this Correction.

`./devctl doctor --settings` passes on the local Flight configuration.
The merge guard currently takes Mode, Apps and unit-test patterns from work-tree settings; CODEOWNERS comes from the PR base.
The separate base-policy change has not landed in the inspected base, so this record does not claim its behavior.
No concrete conflict with the planned multi-stack or base-policy interfaces was found.

Publication still requires privacy review, exact-final-head independent review and hosted full CI before Reviewer App approval.
The owner must run `./devctl doctor` after merging to validate the new default-branch CODEOWNERS and live settings.
Pre-merge local settings checks cannot establish that the new CODEOWNERS is live.
No full local test suite, website build, remote merge or live root Ruff trial ran for this change.

Local tools: git 2.39.5; resolved stable CPython 3.15.2 (`releaselevel = final`).

| Command | Local result |
| --- | --- |
| `./devctl doctor --settings` | Exit 0; settings and both Harness wiring checks pass |
| `uv run pytest tests/devctl/test_devctl_merge_guard.py tests/devctl/test_devctl_doctor_github.py tests/devctl/test_devctl_doctor_github_limits.py tests/devctl/test_devctl_doctor_codeowners_errors.py tests/devctl/test_devctl_doctor_settings.py` | Exit 0; 196 passed, baseline and Flight tree |
| `./devctl check --tier fast` | Exit 0; all seven steps pass |
| `uv run rapid-ship status --strict` | Exit 0; Kit remains required and unchanged |
| `git diff --check` | Exit 0 |

Correction validation used the repository configuration and configured scan scope, without overrides.
The exact full-tier tool commands and affected tests below ran locally; hosted CI remains the check of record.

| Correction command | Local result |
| --- | --- |
| `uv run --locked mypy` | Exit 0; no issues in 145 source files |
| `uv run --locked vulture --min-confidence 0` | Exit 0; no findings |
| `uv run --locked deptry . --no-ansi --json-output <temporary-report-path>` | Exit 0; 19 files scanned, JSON report `[]` |
| `uv run --locked pytest -q tests/devctl/test_devctl_codeowners.py` | Exit 0; 21 passed, offline matcher tests |
