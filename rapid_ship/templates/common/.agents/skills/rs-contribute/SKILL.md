---
name: rs-contribute
description: Send a fix for a rapid-ship Kit file back to rapid-ship as a pull request.
disable-model-invocation: true
---

# Contribute a Kit fix

1. Describe the problem, the command and output that show it, and the Kit file involved. Leave project code, secrets and private paths out of the contribution.
2. Read the project's Kit lock to identify the vendored file. Map it to the template using the layer and precedence rules in the clone's `rapid_ship/templates/AGENTS.md`. A `.claude/skills/<name>` link maps to `rapid_ship/templates/common/.agents/skills/<name>/`.
3. Search for duplicates with `gh search issues` and `gh search prs`, both with `--repo proxy-hatch/rapid-ship --state open`. If the fix is unclear, propose an issue instead.
4. Ask the owner before creating a fork. After yes, run `gh repo fork proxy-hatch/rapid-ship --clone=false`. Clone the owner's fork once to `${XDG_CACHE_HOME:-$HOME/.cache}/rapid-ship/fork`, fetch upstream and update the base before each fix. Create a branch for the fix. In the clone run `uv sync --locked`, fix the template, then run `uv run rapid-ship sync --in-place` and `./devctl check`.
5. The clone records rapid-ship's own Apps. In a wired Session its guardrails deny the agent's push and PR creation. State the writes and give the owner these **Owner terminal commands**, with the correct branch and fork remote:

```sh
git push -u origin "$BRANCH"
gh pr create --repo proxy-hatch/rapid-ship
```

The owner also opens an issue from their terminal if needed. Resolve an uncertain external write by reading its result before retrying.

The project may apply the same fix to its vendored copy immediately. If a sync runs before the fix ships, `rapid-ship sync --revert <path>` gives the file back to the Kit.
