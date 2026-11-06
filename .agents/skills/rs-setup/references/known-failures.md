# Known failures

Preserve the failing command's output. Explain the cause and offer the fix before acting; never increase permissions to bypass a refusal.

## Init

| Output or condition | Cause | Fix |
| --- | --- | --- |
| Managed Kit path already exists; exit 1 | Init writes nothing on a conflict. | Inspect the paths with the owner before resolving them. |
| `init wrote nothing: confirm the stacks first.`; exit 2, once stack detection is available | The proposed roots need confirmation. | Show the proposal and rerun only with the owner's confirmed roots. |

## Checks

| Output or condition | Cause | Fix |
| --- | --- | --- |
| `install gitleaks 8.30.1; devctl check blocks its secrets step without it` | The pinned tool is missing. | Ask the owner to install it. |
| `gitleaks <version> is installed; devctl check pins 8.30.1` | The installed version differs. | Ask the owner to install the pinned version. |
| `uv sync` cannot reach the network | Dependencies cannot be fetched. | Restore network access and rerun. |
| Workspace members include `tools/devctl` | A members glob covers the Kit's own project. | Add `exclude = ["tools/devctl"]` to the root workspace. |
| A tool step is blocked | Its tool or configuration is missing. | Record the gap; leave existing tool settings unchanged. |
| Existing hooks under `.git/hooks` | Setting `core.hooksPath` stops them running. | Show the owner and agree how to combine them before setting the path. |
| Project skill copies in `.claude/skills` | Map expects links. | Replace copies with links after reviewing their contents. |

## Guardrails

| Output or condition | Cause | Fix |
| --- | --- | --- |
| `Claude Code wiring` or `agy wiring` reports missing hooks | Existing settings omitted the Kit entries. | Merge the Kit entries into the existing file. |
| agy hook fails before devctl runs | The launcher failed. | Inspect the hook and its launch path; a failure blocks wired calls. |
| Codex wiring absent | Its wiring may not be available yet. | Once merged and trialed, merge its entries and have the owner trust the project and review `/hooks`. |

## Sandbox

| Output or condition | Cause | Fix |
| --- | --- | --- |
| `Failed to initialize cache at` | uv cannot write its cache. | Allow `~/.cache/uv` in the accepted sandbox settings. |
| `uv tool run` cannot write under `~/.local/share/uv/tools` | Its tools directory is outside writable paths. | Allow that directory. |
| `x509: OSStatus -26276` | gh cannot use the sandbox proxy's certificate. | Offer the scoped gh exclusion. |
| An exclusion matches only the exact command line | The command carries additional arguments. | Review the scoped exclusion and actual command. |
| devctl GitHub request fails behind the sandbox proxy | The request is still blocked. | Record the gap; use the owner's terminal when appropriate. |
| Local settings are tracked | The ignore rule is missing. | Use `git check-ignore -q .claude/settings.local.json` and add it to the file from `git rev-parse --git-path info/exclude` if needed. This works in a linked worktree too. |
| Old Session does not use the setting | It started before the change. | Start a new sandbox Session and repeat all three checks. |

## GitHub

| Output or condition | Cause | Fix |
| --- | --- | --- |
| Ruleset 403 naming the GitHub Free private plan limit | GitHub does not offer the ruleset there. | Record the gap and explain merge-guard enforcement. |
| Default branch is not `main` or `master` | CI push triggers cover those names. | Record the coverage gap. |
| Existing `rapid-ship` ruleset | A POST would create another. | Read its ID and use PUT. |
| `G8: Agent identity is on, so an App makes gh writes; run ./devctl as <role> gh ` | The guard denies a direct write. | Give the exact settings command to the owner for their terminal. |
| gh is signed in as another account | The wrong owner credentials are active. | Ask the owner to correct authentication. |
| `Repository rule violations` | The default branch may not have been bootstrapped before the ruleset. | Re-read the branch and rulesets; ask the owner to bootstrap from their terminal. |
| CODEOWNERS reports an owner without write access or a team not visible | GitHub cannot use that owner. | Ask the owner to correct access or visibility. |

## Mode

| Output or condition | Cause | Fix |
| --- | --- | --- |
| `merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #` | Walk reserves merges to the owner. | Ask the owner to merge. |
| `, so the owner merges it` | In Flight the PR declares a removed behavioural test or an overage. | Ask the owner to review and merge. |

## Agent identity, doctor and pull requests

| Output or condition | Cause | Fix |
| --- | --- | --- |
| `rapid-ship app` exits 1 | An App, key, account, token or organisation permission is unavailable or inconsistent. | Preserve its output and resolve the named cause with the owner. |
| `claude` is not on PATH | Doctor cannot probe skills. | Install Claude Code or record the missing probe. |
| A skill probe misses a skill | The Harness did not discover it. | Inspect its discovery path and rerun the probe. |
| `G7: Agent identity is on, so the Worker App pushes; run ./devctl as worker push` | The guard denies the owner's direct push. | For the workflow-bearing Setup branch, give the owner the push command. |
| Worker App cannot push a workflow | The App lacks workflow permission. | The owner pushes from their terminal. |
| Sync conflict | A managed target conflicts with local state. | Inspect the reported path and resolve it with the owner. |
| Linter findings exceed the cap | The selected rule needs more than one PR. | Drop it from this PR and propose a task. |

## TypeScript

| Output or condition | Cause | Fix |
| --- | --- | --- |
| `lint (frontend)` is blocked and says `is not installed; run npm ci there` | Stack dependencies are absent. | Run `npm ci` in that stack after network access is available. |
| Node or TypeScript floor item fails | The stack's tools or required settings differ. | Inspect doctor's item and offer the named fix. |
