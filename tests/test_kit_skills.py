"""Offline: the Kit's skills as the templates hold them and as init vendors them."""

import re
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
USER_INVOKED = frozenset({"rs-setup", "rs-health", "rs-contribute"})


def test_only_the_user_invoked_kit_skills_disable_model_invocation() -> None:
    skills_dir = REPOSITORY / "rapid_ship/templates/common/.agents/skills"
    for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_path.parent.name
        text = skill_path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        front_matter = parts[1] if len(parts) >= 3 else ""
        has_disable = "disable-model-invocation: true" in front_matter
        assert has_disable == (name in USER_INVOKED), f"{name}: disable-model-invocation mismatch"


def test_every_kit_skill_mention_resolves() -> None:
    skills_dir = REPOSITORY / "rapid_ship/templates/common/.agents/skills"
    names = {path.parent.name for path in skills_dir.glob("*/SKILL.md")} | {"rs-exception"}
    for path in skills_dir.glob("**/*.md"):
        for name in re.findall(r"\brs-[a-z0-9-]+", path.read_text(encoding="utf-8")):
            assert name in names, f"{path}: {name} is not a Kit skill"
