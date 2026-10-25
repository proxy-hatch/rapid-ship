"""Offline: the Python guardrail floor from spec section 4, and the tools/devctl exclusions."""

import tomllib
from typing import Any

import pytest

from devctl.check.stacks.python import guardrail_gaps
from devctl.check.stacks.python_dead_code import dead_code_gaps
from devctl.doctor import devctl_exclusion_gaps
from rapid_ship.kit.templates import render_files


def seeded_pyproject() -> dict[str, Any]:
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    [template] = [t for t in render_files("python", variables, ()) if t.path == "pyproject.toml"]
    assert template.content is not None
    return tomllib.loads(template.content.decode())


def test_seeded_python_settings_meet_the_floor() -> None:
    assert guardrail_gaps(seeded_pyproject()) == []
    assert dead_code_gaps(seeded_pyproject()) == []


def test_gaps_name_each_missing_setting() -> None:
    data = seeded_pyproject()
    lint = data["tool"]["ruff"]["lint"]
    lint["select"] = [c for c in lint["select"] if c != "SIM"]
    lint["ignore"] = [*lint.get("ignore", []), "RUF100"]
    data["tool"]["mypy"]["warn_unreachable"] = False
    data["project"]["dependencies"] = ["fastapi>=0.115"]
    data["tool"]["pytest"]["ini_options"]["addopts"] = "-ra --strict-config"
    gaps = guardrail_gaps(data)
    assert "ruff: select lacks SIM, ASYNC, FAST" in gaps
    assert "ruff: ignore disables RUF100" in gaps
    assert "mypy: warn_unreachable is not true" in gaps
    assert "pytest: addopts lacks --strict-markers" in gaps
    assert not any("--strict-config" in g for g in gaps)


def test_seeded_python_settings_leave_out_tools_devctl() -> None:
    assert devctl_exclusion_gaps(seeded_pyproject(), python=True) == []


def test_exclusion_gaps_name_each_setting() -> None:
    data = seeded_pyproject()
    data["tool"]["ruff"]["extend-exclude"] = []
    data["tool"]["mypy"]["files"] = ["."]
    data["tool"]["pytest"]["ini_options"]["testpaths"] = ["tests", "tools"]
    data["tool"]["uv"] = {"workspace": {"members": ["tools/*"]}}
    ruff = "ruff: tools/devctl is not in exclude or extend-exclude"
    pytest_gap = "pytest: testpaths does not leave out tools/devctl"
    assert devctl_exclusion_gaps(data, python=True) == [
        ruff,
        "mypy: files covers tools/devctl and no exclude pattern matches it",
        pytest_gap,
        "uv: [tool.uv.workspace] members match tools/devctl; add it to exclude",
    ]
    data["tool"]["mypy"]["exclude"] = ["^tools/devctl/"]
    data["tool"]["uv"]["workspace"]["exclude"] = ["tools/devctl"]
    assert devctl_exclusion_gaps(data, python=True) == [ruff, pytest_gap]
    assert devctl_exclusion_gaps(data, python=False) == []


VULTURE_GAP = "vulture: paths covers tools/devctl and no exclude pattern matches it"
DEPTRY_GAP = "deptry: no exclude or extend_exclude pattern matches tools/devctl"


@pytest.mark.parametrize(
    ("tool", "settings", "gaps"),
    [
        ("vulture", {"paths": ["."]}, [VULTURE_GAP]),
        ("vulture", {"paths": ["."], "exclude": ["tools/devctl"]}, []),
        # vulture matches exclude with fnmatch, which keeps case outside Windows.
        ("vulture", {"paths": ["."], "exclude": ["TOOLS/DEVCTL"]}, [VULTURE_GAP]),
        ("deptry", None, [DEPTRY_GAP]),
        ("deptry", {"extend_exclude": ["tools"]}, []),
        ("deptry", {"extend_exclude": [".*devctl"]}, []),
        # deptry also tests each path beneath tools/devctl.
        ("deptry", {"extend_exclude": ["tools/devctl/"]}, []),
        ("deptry", {"extend_exclude": ["tools/devctl/.*"]}, []),
        # deptry matches each pattern from the start of the path.
        ("deptry", {"extend_exclude": ["devctl"]}, [DEPTRY_GAP]),
    ],
)
def test_the_exclusions_keep_tools_devctl_out_of_vulture_and_deptry(
    tool: str, settings: dict[str, list[str]] | None, gaps: list[str]
) -> None:
    data = seeded_pyproject()
    if settings is None:
        del data["tool"][tool]
    else:
        data["tool"][tool] = settings
    assert devctl_exclusion_gaps(data, python=True) == gaps
