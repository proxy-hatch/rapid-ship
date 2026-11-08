"""Offline: the packaged templates rendered for several stacks."""

import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
from test_kit_contents import VARIABLES

from devctl.check.map import MapStep
from devctl.check.steps import CheckContext
from devctl.doctor_rules import PYTHON_PROTECTED_PATHS
from devctl.repo import Repo
from devctl.settings import load_project
from rapid_ship.kit import init as init_module
from rapid_ship.kit.init import init_repository
from rapid_ship.kit.lock import read_lock
from rapid_ship.kit.stacks import KITS, ProjectStack
from rapid_ship.kit.status import classify
from rapid_ship.kit.sync import sync_repository
from rapid_ship.kit.templates import KitError, packaged_templates, render_files


def test_a_python_backend_renders_under_its_directory() -> None:
    files = {t.path: t for t in render_files((ProjectStack("python", "backend"),), VARIABLES, ())}
    assert {
        "backend/pyproject.toml",
        "backend/src/demo_app/__init__.py",
        "backend/tests/test_settings.py",
        "backend/AGENTS.md",
        "docs/patterns/python-configuration.md",
    } <= files.keys()
    assert "pyproject.toml" not in files
    assert not any(p.startswith("src/") for p in files)
    pattern = files["docs/patterns/python-configuration.md"].content
    assert pattern is not None
    assert b"reference: backend/src/demo_app/settings.py" in pattern
    assert b"test:backend/tests/test_settings.py::test_an_out_of_range_value_is_rejected" in pattern


def test_project_toml_and_codeowners_list_every_stack() -> None:
    stacks = (ProjectStack("python", "backend"), ProjectStack("python", "worker"))
    files = {t.path: t.content for t in render_files(stacks, VARIABLES, ())}
    settings = files[".rapid-ship/project.toml"]
    assert settings is not None
    data = tomllib.loads(settings.decode())
    assert data["stack"] == [{"name": "python", "directory": d} for d in ("backend", "worker")]
    assert data["map"]["source_roots"] == ["backend/src/demo_app", "worker/src/demo_app"]
    assert data["tests"]["unit"] == ["backend/tests/unit/**", "worker/tests/unit/**"]
    assert data["escalation"] == {"every_pr": True}
    owners = files[".github/CODEOWNERS"]
    assert owners is not None
    assert owners.count(b"# /docs/patterns/python-configuration.md @octo") == 1
    assert b"# /backend/pyproject.toml @octo" in owners
    assert b"# /worker/pyproject.toml @octo" in owners


def test_the_root_guide_links_each_stack_guide() -> None:
    files = {
        t.path: t.content for t in render_files((ProjectStack("python", "backend"),), VARIABLES, ())
    }
    assert b"| The Python stack | [backend/](backend/AGENTS.md) |" in (files["AGENTS.md"] or b"")
    assert b"Mark a `dead-code` false positive" in (files["AGENTS.md"] or b"")
    assert b"[Source](src/AGENTS.md)" in (files["backend/AGENTS.md"] or b"")
    assert b"[Tests](tests/AGENTS.md)" in (files["backend/AGENTS.md"] or b"")


@pytest.mark.parametrize("parent_stack", [False, True])
def test_deep_stack_directories_have_reachable_ancestor_guides(
    git_repo: Path, run_git: Callable[..., str], parent_stack: bool
) -> None:
    stacks = [ProjectStack("python", "services/api")]
    if parent_stack:
        stacks.append(ProjectStack("python", "services"))
    init_repository(git_repo, stacks=stacks, variables=VARIABLES)
    lock = read_lock(git_repo)
    for path in ("services/AGENTS.md", "services/api/AGENTS.md"):
        assert sum(e.path == path for e in lock.entries) == 1
        assert path in (git_repo / "AGENTS.md").read_text()
    assert "[api/](api/AGENTS.md)" in (git_repo / "services/AGENTS.md").read_text()
    run_git(git_repo, "add", ".")
    context = CheckContext(Repo.discover(git_repo), load_project(git_repo), None, None)
    result = MapStep().run(context)
    assert result.status == "passed", result.details


@pytest.mark.parametrize("link", [False, True])
def test_existing_ancestor_guides_survive_init_and_sync(
    git_repo: Path, commit_all: Callable[..., None], link: bool
) -> None:
    (git_repo / "services").mkdir()
    guide = git_repo / "services/AGENTS.md"
    if link:
        (git_repo / "existing.md").write_text("existing guide\n")
        guide.symlink_to("../existing.md")
    else:
        guide.write_text("existing guide\n")
    commit_all(git_repo)
    init_repository(git_repo, stacks=[ProjectStack("python", "services/api")], variables=VARIABLES)
    sync_repository(git_repo, in_place=True)
    assert guide.read_text() == "existing guide\n"
    assert guide.is_symlink() == link


@pytest.mark.parametrize("new_directory", ["backend", "worker"])
def test_init_writes_new_project_seeds_per_stack(
    git_repo: Path, commit_all: Callable[..., None], new_directory: str
) -> None:
    existing = "worker" if new_directory == "backend" else "backend"
    (git_repo / existing).mkdir()
    (git_repo / existing / "pyproject.toml").write_text('[project]\nname = "existing"\n')
    commit_all(git_repo)
    init_repository(
        git_repo,
        stacks=[ProjectStack("python", d) for d in ("backend", "worker")],
        variables=VARIABLES,
    )
    assert (git_repo / new_directory / "pyproject.toml").is_file()
    assert not (git_repo / existing / "src").exists()
    pattern = (git_repo / "docs/patterns/python-configuration.md").read_text()
    assert f"reference: {new_directory}/src/demo_app/settings.py" in pattern
    assert classify(git_repo).strict_ok
    assert not sync_repository(git_repo, in_place=True).changed


def test_status_and_sync_render_the_new_project_seeds_that_init_wrote(
    git_repo: Path, commit_all: Callable[..., None], tmp_path: Path
) -> None:
    (git_repo / "worker").mkdir()
    (git_repo / "worker/pyproject.toml").write_text('[project]\nname = "existing"\n')
    commit_all(git_repo)
    init_repository(
        git_repo,
        stacks=[ProjectStack("python", d) for d in ("backend", "worker")],
        variables=VARIABLES,
    )
    original = (git_repo / "backend/pyproject.toml").read_bytes()
    copy = tmp_path / "templates-copy"
    shutil.copytree(packaged_templates(), copy)
    seed = copy / "python/pyproject.toml"
    seed.write_text(seed.read_text() + "\n# changed\n")
    result = sync_repository(git_repo, in_place=True, templates_root=copy)
    assert result.seeded_changed == ["backend/pyproject.toml"]
    assert (git_repo / "backend/pyproject.toml").read_bytes() == original


def test_two_stacks_cannot_write_one_path(make_templates: Callable[..., Path]) -> None:
    root = make_templates(
        changes={
            "kit.toml": (
                'seeded = ["AGENTS.md"]\n[new_project]\n'
                'python = [".gitignore"]\nagnostic = [".gitignore"]\n'
            ),
            "python/.gitignore": "python\n",
            "agnostic/.gitignore": "agnostic\n",
            "common/AGENTS.md": "root\n",
            "python/.rapid-ship/project.toml": None,
            "agnostic/.rapid-ship/project.toml": None,
            "common/.github/CODEOWNERS": None,
            "python/pyproject.toml": None,
            "python/src/__package__/__init__.py": None,
        }
    )
    stacks = (ProjectStack("python", "."), ProjectStack("agnostic", "."))
    with pytest.raises(KitError, match=r"agnostic and python both write \.gitignore"):
        render_files(stacks, VARIABLES, (), root=root)
    files = render_files(stacks, VARIABLES, (), root=root, new_projects=[stacks[0]])
    assert sum(t.path == ".gitignore" for t in files) == 1


def test_the_stack_kits_match_devctl() -> None:
    assert KITS["python"].protected == PYTHON_PROTECTED_PATHS
    assert set(KITS["python"].patterns) == {
        p.name for p in (packaged_templates() / "python/__root__/docs/patterns").glob("*.md")
    }


@pytest.mark.parametrize("existing", ["absent", "regular", "symlink"])
def test_missing_guides_are_created_without_rewriting_existing_guides(
    git_repo: Path, commit_all: Callable[..., None], tmp_path: Path, existing: str
) -> None:
    copy = tmp_path / "older-templates"
    shutil.copytree(packaged_templates(), copy)
    (copy / "python/AGENTS.md").unlink()
    init_repository(
        git_repo,
        stacks=[ProjectStack("python", "services/api")],
        variables=VARIABLES,
        templates_root=copy,
    )
    guide = git_repo / "services/AGENTS.md"
    if existing == "regular":
        guide.write_text("authored guide\n")
    elif existing == "symlink":
        (git_repo / "authored.md").write_text("authored guide\n")
        guide.symlink_to("../authored.md")
    commit_all(git_repo)
    result = sync_repository(git_repo, in_place=True)
    assert (
        "services/AGENTS.md" in result.added
        if existing == "absent"
        else "services/AGENTS.md" in result.seeded_existing
    )
    assert (
        "Directory navigation" in guide.read_text()
        if existing == "absent"
        else guide.read_text() == "authored guide\n"
    )
    assert guide.is_symlink() == (existing == "symlink")


@pytest.mark.parametrize("link", [False, True])
def test_failed_init_removes_new_guides_and_preserves_existing_ones(
    git_repo: Path, commit_all: Callable[..., None], monkeypatch: pytest.MonkeyPatch, link: bool
) -> None:
    (git_repo / "services").mkdir()
    guide = git_repo / "services/AGENTS.md"
    if link:
        (git_repo / "authored.md").write_text("authored guide\n")
        guide.symlink_to("../authored.md")
    else:
        guide.write_text("authored guide\n")
    commit_all(git_repo)

    def refuse(*args: object) -> None:
        assert (git_repo / "services/api/AGENTS.md").is_file()
        raise KitError("forced lock failure")

    monkeypatch.setattr(init_module, "write_lock", refuse)
    with pytest.raises(KitError, match="forced lock failure"):
        init_repository(
            git_repo, stacks=[ProjectStack("python", "services/api")], variables=VARIABLES
        )
    assert guide.read_text() == "authored guide\n"
    assert guide.is_symlink() == link
    assert not (git_repo / "services/api").exists()
