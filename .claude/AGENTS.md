# Claude skill discovery

`skills/` provides Claude's aliases to discovery paths:
- For Kit-managed skills, symlinks to [`.agents/skills/`](../.agents/AGENTS.md).
- For repository skills, symlinks to canonical packaged [skills](../rapid_ship/skills/).

Read the shared [discovery guidance](../.agents/AGENTS.md) before changing an alias or its target.
Edit canonical files so both agent discovery surfaces receive the same content.

Preserve each symlink's repository-relative target.
The parameterized checks in [test_skill_discovery.py](../tests/test_skill_discovery.py) cover both discovery surfaces.

[settings.json](settings.json) wires `devctl hook` for Claude Code; it is seeded, in the Protected set, and doctor checks it.
