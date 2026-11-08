# GitHub workflows

- [workflows/devctl-check.yml](workflows/devctl-check.yml) is the managed Kit workflow. It installs gitleaks, then runs `./devctl check --tier full`, the same command as a local full check; the `python-3.12` step covers the oldest supported Python. Change it only through its template, `rapid_ship/templates/common/.github/workflows/devctl-check.yml`, then sync.
- [workflows/docs.yml](workflows/docs.yml) builds documentation for relevant changes and deploys successful main-branch builds.
- [CODEOWNERS](CODEOWNERS) is this repository's own seeded file. For dog-fooding Flight, its active lines assign only the Protected set to `@proxy-hatch`; there is no Walk `*` rule. The set covers guardrails, Patterns, check settings at root and nested depths, and project access, CLI and Kit data models. Keep root settings entries for current doctor compatibility and `/**/<path>` entries for nested Python settings. GitHub reads CODEOWNERS from the pull request's base branch and requests the owner's review. Merge blocking also requires the ruleset's code-owner review rule. Edit this file, not the Kit templates, and keep `[github] code_owner` equal to its owner. After the Mode change merges, the owner runs `./devctl doctor` to validate the default branch and live GitHub settings. Before merge, `doctor --settings` validates only the local file. Agents merge only non-Protected PRs with passing checks, exact-head Reviewer App approval and no open owner question; the owner merges this Protected Mode change.

Keep pull-request checks separate from deployment permissions.
When adding a build input, update the docs workflow path filters if that input affects the website.
Preserve locked dependency installation and the existing per-job permission boundaries.
Run the affected workflow's commands locally where supported; report hosted runs and deployments separately from local results.
