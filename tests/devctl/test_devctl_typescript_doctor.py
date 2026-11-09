"""Offline: doctor's TypeScript items with fake node, npm and eslint."""

import json

import pytest

from check_workspace import Workspace, fake_tool
from devctl.doctor_rules import TYPESCRIPT_PROTECTED_PATHS, codeowners_problems, protected_settings
from devctl.doctor_typescript import (
    DEV_PACKAGES,
    ESLINT_ERRORS,
    KNIP_FLOOR_KEYS,
    TSCONFIG_FLOOR,
    floor_gaps,
    floor_item,
    node_items,
)
from devctl.settings import ProjectStack

STACK = ProjectStack("typescript", "frontend")


def good_floor() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    return (
        {"compilerOptions": dict.fromkeys(TSCONFIG_FLOOR, True)},
        {
            "rules": {
                **{key: [2] for key in ESLINT_ERRORS},
                "complexity": [2, 10],
                "@typescript-eslint/ban-ts-comment": [
                    2,
                    {
                        "ts-ignore": True,
                        "ts-nocheck": True,
                        "ts-expect-error": "allow-with-description",
                    },
                ],
            },
            "linterOptions": {"reportUnusedDisableDirectives": 2},
        },
        {
            "devDependencies": dict.fromkeys(DEV_PACKAGES, "1.0.0"),
            "engines": {"node": ">=24.15.0 <25"},
        },
    )


def test_the_floor_names_each_gap() -> None:
    gaps = floor_gaps({}, {}, {}, {}, False)
    assert gaps == [
        *[f"tsconfig.json: compilerOptions.{key} is not true" for key in TSCONFIG_FLOOR],
        *[f"eslint: {rule} is not an error" for rule in ESLINT_ERRORS],
        "eslint: complexity is not an error with a maximum of 10 or less",
        "eslint: @typescript-eslint/ban-ts-comment does not ban @ts-ignore and @ts-nocheck "
        "and require a description on @ts-expect-error",
        "eslint: linterOptions.reportUnusedDisableDirectives is not error",
        f"npm: devDependencies lack {', '.join(DEV_PACKAGES)}",
        "npm: engines.node is not set",
        "npm: package-lock.json is missing; run npm install and commit it",
    ]
    assert floor_gaps(*good_floor(), {}, True) == []
    assert floor_gaps({"extends": "./base.json"}, {}, {}, {}, False)[0].endswith(
        " (it extends ./base.json, which doctor does not read)"
    )


@pytest.mark.parametrize("key", KNIP_FLOOR_KEYS)
def test_the_floor_rejects_each_knip_switch(key: str) -> None:
    assert floor_gaps(*good_floor(), {key: False}, True) == [
        f"knip: knip.jsonc sets {key}, which can switch a kind off"
    ]


@pytest.mark.parametrize(
    ("version", "engine", "status"),
    [
        ("v24.19.0", ">=24.15.0 <25", "ok"),
        ("v24.0.0", "24.x", "ok"),
        ("v24.3.0", ">=24.15.0 <25", "missing"),
        ("v22.1.0", "24.x", "missing"),
        (None, "24.x", "missing"),
        ("v24.19.0", None, "missing"),
    ],
)
def test_node_must_match_engines(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
    version: str | None,
    engine: str | None,
    status: str,
) -> None:
    workspace.write("frontend/package.json", json.dumps({"engines": {"node": engine}}))
    tool_dir = workspace.root / "bin"
    fake_tool(tool_dir, "npm", 'sys.stdout.write("11.17.0")')
    if version:
        fake_tool(tool_dir, "node", f"sys.stdout.write({version!r})")
    monkeypatch.setenv("PATH", str(tool_dir))
    items = node_items(workspace.root, (STACK,))
    assert items[0].status == status
    assert items[1].status == "ok"
    if version and engine and status == "ok":
        assert items[0].detail == f"node {version}, which frontend/package.json names ({engine})"
    if engine is None:
        assert items[0].detail == "frontend/package.json sets no engines.node"
    if version and engine and status == "missing":
        minimum = "24.15.0" if "15" in engine else "24.0.0"
        assert items[0].detail == (
            f"node {version}, but frontend/package.json names {engine}; "
            f"install Node.js 24, {minimum} or later"
        )
    if version is None:
        assert items[0].detail == "node is not on PATH; install Node.js 24"
    assert node_items(workspace.root, ()) == []


def test_eslint_that_cannot_run_makes_the_floor_unknown(workspace: Workspace) -> None:
    for name in ("tsconfig.json", "package.json", "knip.jsonc"):
        workspace.write(f"frontend/{name}", "{}")
    result = floor_item(workspace.root, STACK, True)
    assert result.status == "unknown"
    assert (
        result.detail == "cannot run eslint in frontend: eslint is not installed; "
        "run npm install there and commit package-lock.json"
    )


def test_flight_codeowners_needs_the_typescript_settings_under_its_directory() -> None:
    assert protected_settings((STACK,)) == tuple(
        f"frontend/{path}" for path in TYPESCRIPT_PROTECTED_PATHS
    )

    problems = codeowners_problems("", False, "@owner", (STACK,))
    for path in TYPESCRIPT_PROTECTED_PATHS:
        assert any(f"frontend/{path}" in problem for problem in problems)
