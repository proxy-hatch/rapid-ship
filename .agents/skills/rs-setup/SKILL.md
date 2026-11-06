---
name: rs-setup
description: Set up a new repository, or adopt an existing one, after rapid-ship init vendored the Kit.
disable-model-invocation: true
---

# Set up the Kit

Guide the owner through each step. Stop at the first failure and preserve its output. Explain the problem and propose a fix before applying it. Never silently rewrite the repository, increase permissions to evade a refusal, or change Protected settings without the owner's yes. State each outside write and wait for the owner's yes. Re-read outside state before retrying an uncertain write. Record unresolved gaps in the Setup PR.

Read `.rapid-ship/kit.lock` for `kit_version`. Run rapid-ship as `uvx --from git+https://github.com/proxy-hatch/rapid-ship@v<kit_version> rapid-ship <command>`. If the tag does not exist, ask for the checkout used by init. Run sync only with `--in-place`.

## 1. New or existing

A repository with source beyond the Kit is existing. Read each `[[stack]]` table's `name` and `directory` in `.rapid-ship/project.toml`; the owner already confirmed these roots. Do not ask again.

## 2. Documents

For a new project, ask what it does, who uses it and how it runs. Fill README.md, the root AGENTS.md introduction, and ARCHITECTURE.md's purpose and context. Add parts when code exists. For an existing project, merge the skeleton sections into existing documents using the code as evidence; preserve project text. Add the maintained-directory guides the map step reports, including each stack's `<directory>/AGENTS.md`, and link them from the root guide. Name the project's actual terms and decision files in its root guide. Record what code cannot establish as a gap for `rs-health`.

## 3. Patterns

For a new project, walk through each starter Pattern and adapt its reference and Lessons. Agree further Patterns and write each Pattern, minimal reference and enforcing check. If a reference needs product code, offer it as a task. For an existing project offer each starter Pattern as a task, including `typescript-error-handling.md`, `typescript-configuration.md`, `typescript-input-validation.md` and `typescript-performance.md` where applicable. Shape proposals using `.agents/skills/rs-health/references/proposed-task.md`. State each write and write the tasks the owner picks to a tracker the Harness can reach; use `./devctl as worker gh` for GitHub issues when Agent identity is on. If no tracker is reachable, leave them in the conversation.

## 4. Checks

Confirm `gitleaks version` is 8.30.1. For TypeScript, confirm Node.js 24 and npm, with `engines.node = ">=24.15.0 <25"`; ask the owner to install missing tools. For a new project run `uv sync` in each Python stack and `npm install` in each TypeScript stack, then `./devctl check`.

For an existing project, show overlaps in settings, hooks and workflows that init listed. Offer to fold them into `devctl_project`; duplicate checks are harmless, but checks that both write a file can race. Do not block on either. Keep existing tool settings unchanged in the Setup PR and record missing check tools as blocked. Exclude `tools/devctl` from project lint, type, test and dead-code scans. If workspace members cover it, add `exclude = ["tools/devctl"]` under the root `[tool.uv.workspace]`.

For every suppression reported by `exceptions`, add its `rs-exception` marker and entry with reason `Existed at Setup on <date>` and removal condition `Remove when this code next changes`. Repeat the fast check until it passes.

In each Python stack's `pyproject.toml`, add vulture and deptry to the dev group, `[tool.vulture] paths` for source and tests, Ruff `lint.external = ["V"]`, and deptry's exclusion for `tools/devctl` and `known_first_party` for packages below the root. Run `uv lock`. Fix each dead-code finding or mark it with the tool's suppression and an `rs-exception` marker on the reported line, or a marked `per_rule_ignores` item for a dependency. Each entry uses reason `Existed at Setup on <date>` and removal condition `Delete it, or replace this reason with what uses it`. Repeat both dead-code commands until they pass.

For each TypeScript knip finding, fix it or mark the reported export with `/** @public */` and its `rs-exception` marker, or add an item under the matching top-level `ignore*` key of `knip.jsonc`, alone on its line with its marker. Use the dead-code reasons above. Mark TypeScript suppressions reported by `exceptions` with the suppression reasons above.

For existing hooks, wait for the owner's decision on combining them before `git config core.hooksPath .githooks`. Run `./devctl check` until it passes; record blocked tools rather than changing their existing settings.

## 5. Harness guardrails

Show the owner the guardrails and merge guard. Claude Code is wired; agy is wired without G5 once its wiring is merged and trialed, and Codex is wired without G5 once its wiring is merged and trialed. Their hooks do not ask before Protected edits. Other unwired Harnesses lack these guardrails. Merge the Kit entries where init skipped `.claude/settings.json`, `.agents/hooks.json` or, once available, `.codex/hooks.json`. For Codex, the owner trusts the project and reviews hooks in `/hooks`; preserve `/.codex/` in CODEOWNERS.

## 6. Sandbox

Offer a sandbox; wait for the owner's yes. It confines the owner's Session and inherited subagent Sessions as defense in depth. It needs network access for git, gh, uv, package registries and the tracker. Never commit local settings.

Claude Code alone uses `.claude/settings.local.json`: `network.allowedDomains` includes `github.com`, `api.github.com`, `codeload.github.com`, `objects.githubusercontent.com`, `pypi.org`, `files.pythonhosted.org`, and for TypeScript `registry.npmjs.org`. `filesystem.allowWrite` includes `~/.cache/uv` and `~/.local/share/uv/tools`; TypeScript may also need `~/.npm`. `excludedCommands` includes `gh *` and, until the sandbox fix is merged and trialed, `./devctl as *`. Run `git check-ignore -q .claude/settings.local.json`; if needed add that path to the file from `git rev-parse --git-path info/exclude`.

Codex uses `sandbox_mode` in the owner's uncommitted Codex configuration. agy uses its terminal sandbox setting, with network allowed first. Do not copy Claude's JSON into either. Start a new sandbox Session before running `./devctl --version`, `./devctl check --tier fast` and `gh auth status`; record each actual output and exit code. A blocked command is not a pass. Consult [known failures](references/known-failures.md) without increasing permissions.

## 7. GitHub

Find the repository or, after the owner confirms visibility and the write, create it. Read `gh api repos/<owner>/<name>/branches/<default>` and `gh api 'repos/<owner>/<name>/rulesets?targets=branch'` first. If the remote default branch is missing, stop and ask the owner to push it from their own terminal. Agents cannot push the default branch. Re-read the branch before enabling a ruleset.

After the owner's yes for each outside write, create the ruleset when none is named `rapid-ship`:

```sh
gh api --method POST repos/<owner>/<name>/rulesets --input .agents/skills/rs-setup/ruleset.json
```

For an existing `rapid-ship` ruleset, update it instead:

```sh
gh api --method PUT repos/<owner>/<name>/rulesets/<id> --input .agents/skills/rs-setup/ruleset.json
```

Enable branch deletion with `gh api --method PATCH repos/<owner>/<name> -F delete_branch_on_merge=true`. For a public repository require approval of external contributor workflows with `gh api --method PUT repos/<owner>/<name>/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors`. If Agent identity is on, G8 denies these writes: give each exact command to the owner for their terminal. Agent GitHub writes otherwise use `./devctl as`. Re-read uncertain results before retrying.

If `[github] repository` is empty, record `owner/name` before Agent identity. Record the code owner and the Walk `* @owner` line in CODEOWNERS. Protect the Kit and each stack's settings, prefixed by `/<directory>/` for a subdirectory. The ruleset requires code-owner review, resolved threads, a passing `devctl check`, squash merges and no force push or deletion. The approval count is zero; the admin bypass is pull-request only. If the default branch is neither main nor master, record the CI push coverage gap. A 403 naming the GitHub Free private plan limit is a gap: the merge guard enforces agent merges there.

## 8. Agent identity

Explain the trade-offs in [Agent identity](references/agent-identity.md), recommend from its table and ask whether the owner opts in. If yes, run `rapid-ship app` using the versioned command above; an organisation admin creates the Apps. Where Apps exist, the developer imports their own key with `rapid-ship app --import-key`. The owner installs both Apps; record their IDs and slugs in `[github]`, then run doctor. If no, explain the missing metrics, reviews and enforcement described in the reference.

## 9. Mode

Walk sets `every_pr = true`: `merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #` is the merge guard's denial. The owner starts and manages Sessions; at most 3 agents at once is advised in Walk. The owner can widen toward Flight in one Protected PR setting `every_pr = false` and changing CODEOWNERS; offer a readiness review first.

## 10. Metrics

This Kit version records no metrics settings; go on to step 11.

## 11. Optional skills

Offer `rs-contribute` once. Add accepted skills to `[kit] optional` and run the versioned `rapid-ship sync --in-place`.

## 12. Doctor

Run `./devctl doctor --skills`; it probes Claude Code alone when `claude` is on PATH. Resolve or record each gap using [known failures](references/known-failures.md).

## 13. Setup PR

Commit and offer the owner terminal commands to push `rapid-ship/init` and open the PR; the branch contains a workflow the Worker App cannot push. The owner merges it. End the body with the Evidence section required by `devctl check`. Add `Over the diff cap: dead code marked at Setup` only when those marks put the PR over the cap.

## 14. Tool-settings PR

For an existing project, after Setup merges, compare its settings with each stack's Kit settings. Exclude stylistic choices listed in [stylistic options](references/stylistic-options.md). Explain each remaining rule and let the owner pick. From `origin/<default branch>`, merge selected rules into existing settings in a separate Protected PR. Run linters and fix findings within the cap. Drop any rule whose findings exceed it and offer a task for those findings. The owner reviews and merges the PR.

## 15. Next

For an existing repository offer `rs-health`. The Kit is ready: the owner starts and manages their own Sessions, which follow AGENTS.md, its Pull requests section included, and the engineering skills. `./devctl check`, the guardrails and the merge guard hold the bar.
