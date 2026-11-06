"""Offline: doctor's per-stack items in fixture repositories; no GitHub."""

import dataclasses
from pathlib import Path

import pytest

from devctl.doctor_items import Item
from devctl.doctor_local import local_items
from devctl.doctor_rules import (
    PROTECTED_PATHS,
    PYTHON_PROTECTED_PATHS,
    CodeownersError,
    codeowners_error_problems,
    codeowners_problems,
)
from devctl.settings import ProjectStack
from github_fakes import MakeContext, RepoFiles

STACKS = (ProjectStack("python", "backend"), ProjectStack("python", "worker"))


def test_flight_codeowners_needs_each_python_stacks_settings_under_its_directory() -> None:
    common = "".join(f"/{p} @o\n" for p in PROTECTED_PATHS)
    root = "".join(f"/{p} @o\n" for p in PYTHON_PROTECTED_PATHS)
    nested = "".join(f"/backend/{p} @o\n" for p in PYTHON_PROTECTED_PATHS)
    assert codeowners_problems(common + root, False, "@o", STACKS[:1]) == [
        "CODEOWNERS must name only @o for: "
        + ", ".join(f"backend/{p}" for p in PYTHON_PROTECTED_PATHS)
    ]
    text = common + nested + root
    assert codeowners_problems(text, False, "@o", STACKS[:1]) == []
    nested_line = len(PROTECTED_PATHS) + 1
    root_line = nested_line + len(PYTHON_PROTECTED_PATHS)
    assert codeowners_error_problems(
        [
            CodeownersError(nested_line, "Unknown owner", None),
            CodeownersError(root_line, "Unknown owner", None),
        ],
        text,
        False,
        STACKS[:1],
        "main",
    ) == [f"GitHub reports Unknown owner on line {nested_line} of .github/CODEOWNERS on main"]


@pytest.mark.usefixtures("fake_run")
def test_each_python_stack_gets_its_floor_item(ctx: MakeContext, repo_files: RepoFiles) -> None:
    source = Path(__file__).resolve().parents[2] / "rapid_ship/templates/python/pyproject.toml"
    floor = source.read_text()
    repo_files.write("backend/pyproject.toml", floor)
    repo_files.write(
        "worker/pyproject.toml",
        "\n".join(line for line in floor.splitlines() if '"vulture' not in line),
    )
    context = ctx()
    context = dataclasses.replace(
        context, project=dataclasses.replace(context.project, stacks=STACKS)
    )
    items = [i for i in local_items(context) if i.name.startswith("Python guardrail settings")]
    assert [(i.name, i.status) for i in items] == [
        ("Python guardrail settings (backend)", "ok"),
        ("Python guardrail settings (worker)", "missing"),
    ]
    assert "dev dependencies lack vulture" in items[1].detail


@pytest.mark.usefixtures("fake_run")
def test_the_exclusions_item_reads_the_root_pyproject(
    ctx: MakeContext, repo_files: RepoFiles
) -> None:
    context = ctx()
    context = dataclasses.replace(
        context, project=dataclasses.replace(context.project, stacks=STACKS[:1])
    )

    def item() -> Item:
        return next(i for i in local_items(context) if i.name == "tools/devctl exclusions")

    assert item().status == "ok"
    assert item().detail == "no pyproject.toml, so no uv workspace"
    repo_files.write("pyproject.toml", '[tool.uv.workspace]\nmembers = ["tools/*"]\n')
    assert item().status == "missing"
    assert "uv: [tool.uv.workspace] members match tools/devctl" in item().detail
    repo_files.write("pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    assert item().status == "ok"
