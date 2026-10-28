# Codex guardrails

[hooks.json](hooks.json) is the seeded Codex wiring, in the Protected set. Its `PreToolUse` matcher sends `Bash` and `apply_patch` to `devctl hook codex pre-tool`. The command resolves devctl from the current git top level, including a linked worktree or a subdirectory.

Change the [template](../rapid_ship/templates/common/.codex/hooks.json), then sync. Existing seeded files belong to their projects; sync preserves them. Keep the matcher equal to `WIRED_TOOLS["codex"]` in [hook_protocols.py](../rapid_ship/templates/common/tools/devctl/devctl/hook_protocols.py).

Shawn reviews and trusts the exact definition in Codex `/hooks`, with the project trusted. A changed hook needs another review. Agents never bypass hook trust. `./devctl doctor --settings` checks local wiring and runs a denial probe; it cannot verify persisted trust or user-level settings.

G5 is absent because Codex runs an ask without a prompt. Internal errors exit 1 with stderr and no stdout, which lets the call through; recognized merge failures deny. The [implementation plan](../docs/superpowers/plans/2026-10-27-codex-wiring.md) keeps trust and the live trial as pending Owner steps.
