# Repository skill discovery

`skills/` contains relative symlinks to the canonical packaged [skills](../rapid_ship/skills/).
Edit the canonical files; these aliases let coding agents discover the same reviewed content.
The [.claude](../.claude/AGENTS.md) surface points to that same source.

Before changing skill behavior or references, read the packaged [skills guide](../rapid_ship/skills/AGENTS.md).
Keep maintainer navigation outside individual skill bundles.
After changing discovery paths or bundled references, run `uv run pytest tests/test_skill_discovery.py` from the repository root.

[hooks.json](hooks.json) wires `devctl hook` for agy; it is seeded, in the Protected set, and doctor checks it and runs its hook from this directory. The seeded launcher fails outside Git; a passing doctor item does not cover that case. The [trial](../docs/trials/2026-10-28-agy-hook-outside-repository.md) separates offline reproduction from the pending T3 runtime capture.
