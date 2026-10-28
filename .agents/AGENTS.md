# Repository skill discovery

`skills/` contains relative symlinks to the canonical packaged [skills](../rapid_ship/skills/).
Edit the canonical files; these aliases let coding agents discover the same reviewed content.
The [.claude](../.claude/AGENTS.md) surface points to that same source.

Before changing skill behavior or references, read the packaged [skills guide](../rapid_ship/skills/AGENTS.md).
Keep maintainer navigation outside individual skill bundles.
After changing discovery paths or bundled references, run `uv run pytest tests/test_skill_discovery.py` from the repository root.

[hooks.json](hooks.json) seeds agy's `./devctl hook agy pre-tool` command, with no shell expansion.
It is project-owned and in the Protected set; sync never rewrites it.
After updating the Kit, update an existing hook command manually to match the new seed.
The managed [devctl](devctl) forwarding shim locates canonical root `devctl` relative to itself and preserves arguments and stdin.
Edit its template and sync; do not edit this generated copy.
Doctor checks direct and shell launch from root and `.agents/`, including a synthetic G2 deny.
These are deterministic checks, not agy/ACP Sessions; other launch directories remain unsupported by the relative command.
Each new worktree still requires explicit hook trust.
The [trial](../docs/trials/2026-10-28-agy-hook-outside-repository.md) distinguishes successful wrapper `/bin/sh -c` probes from a failed direct legacy-seed CLI launch and successful direct new-seed acceptance.
That supports a shell-syntax diagnosis; original raw subprocess argv and stderr are absent.
Live ACP verification is quota-blocked, and the original ACP cause remains unverified; no guardrail or tool `Cwd` policy changes with this launcher.
