"""Offline: skill links and discovery aliases in this checkout."""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from rapid_ship.kit.templates import load_manifest, read_optional_skills

REPOSITORY = Path(__file__).resolve().parents[1]

TEMPLATE_SKILLS = tuple(
    sorted(
        path.parent.name
        for path in (REPOSITORY / "rapid_ship/templates/common/.agents/skills").glob("*/SKILL.md")
    )
)
_OPTIONAL = load_manifest().optional_skills - set(read_optional_skills(REPOSITORY))
KIT_SKILLS = tuple(name for name in TEMPLATE_SKILLS if name not in _OPTIONAL)
OWN_SKILLS = ("rapid-ship-engineering",)


def test_bundled_skill_dependencies_resolve_inside_package() -> None:
    templates = REPOSITORY / "rapid_ship/templates/common/.agents/skills"
    for document in sorted(templates.rglob("*.md")):
        skill_dir = document.parent
        while skill_dir.parent != templates and skill_dir != templates:
            skill_dir = skill_dir.parent
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            link = urlparse(target)
            if link.scheme or not link.path:
                continue
            dependency = (document.parent / unquote(link.path)).resolve()
            assert dependency.is_relative_to(skill_dir), (document, target)
            assert dependency.is_file(), (document, target)


@pytest.mark.parametrize("skill", KIT_SKILLS)
def test_checkout_discovery_resolves_to_packaged_skill(skill: str) -> None:
    discovered = REPOSITORY / ".agents/skills" / skill
    assert discovered.is_dir()
    assert not discovered.is_symlink()
    assert (discovered / "SKILL.md").is_file()

    claude = REPOSITORY / ".claude/skills" / skill
    assert claude.is_symlink()
    assert claude.readlink() == Path(f"../../.agents/skills/{skill}")


@pytest.mark.parametrize("surface", [".agents", ".claude"])
def test_checkout_discovers_exactly_the_packaged_skills(surface: str) -> None:
    discovered = {
        path.name
        for path in (REPOSITORY / surface / "skills").iterdir()
        if not path.name.startswith(".")
    }
    assert discovered == set(KIT_SKILLS) | set(OWN_SKILLS)
