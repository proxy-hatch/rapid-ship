"""Offline: the Kit's skills as the templates hold them and as init vendors them."""

from pathlib import Path

import pytest

from devctl.check.map_skills import skill_alias_errors, skill_errors, skill_file_errors
from devctl.check.tracked import TrackedFiles
from devctl.repo import Repo
from rapid_ship.cli import main
from rapid_ship.kit.templates import load_manifest

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


def test_the_root_guides_name_the_writing_and_ponytail_skills() -> None:
    templates = REPOSITORY / "rapid_ship/templates"
    for guide in (templates / "common/AGENTS.md", templates / "python/AGENTS.md"):
        for name in ("rs-writing", "rs-ponytail"):
            assert name in guide.read_text()
            assert (templates / "common/.agents/skills" / name / "SKILL.md").is_file()


def test_every_kit_skill_has_its_named_skill_md_and_claude_link_in_a_new_project(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(git_repo)
    assert main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0
    tracked = TrackedFiles.read(Repo.discover(git_repo))
    assert skill_errors(tracked) == []
    assert skill_file_errors(tracked) == []
    assert skill_alias_errors(tracked) == []
    templates = REPOSITORY / "rapid_ship/templates/common/.agents/skills"
    optional = load_manifest().optional_skills
    expected = {p.parent.name for p in templates.glob("*/SKILL.md")} - optional
    assert {p.name for p in (git_repo / ".claude/skills").iterdir()} == expected
