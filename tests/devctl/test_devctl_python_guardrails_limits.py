"""Offline: the edges of the Python guardrail floor and of the tools/devctl exclusion check. Each
case edits the seeded pyproject.toml in memory; no tool runs."""

import tomllib
from typing import Any

import pytest

from devctl.check.stacks.python import guardrail_gaps
from devctl.doctor import devctl_exclusion_gaps
from rapid_ship.kit.templates import render_files

RUFF = "ruff: tools/devctl is not in exclude or extend-exclude"
MYPY = "mypy: files covers tools/devctl and no exclude pattern matches it"
PYTEST = "pytest: testpaths does not leave out tools/devctl"
UV = "uv: [tool.uv.workspace] members match tools/devctl; add it to exclude"


def seeded_pyproject() -> dict[str, Any]:
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    [template] = [t for t in render_files("python", variables, ()) if t.path == "pyproject.toml"]
    assert template.content is not None
    return tomllib.loads(template.content.decode())


def lint(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = data["tool"]["ruff"]["lint"]
    return result


def test_ruff_selectors_are_prefixes_within_one_linter() -> None:
    data = seeded_pyproject()
    # C and T are Ruff's legacy groups, and ANN covers ANN401.
    lint(data)["select"] = [
        *("E", "W", "F", "I", "B", "UP", "SIM", "C", "RUF", "PGH", "ERA", "T", "S", "TID"),
        *("PT", "PTH", "DTZ", "TD", "BLE", "ANN"),
    ]
    assert guardrail_gaps(data) == []
    lint(data)["select"] = ["ALL"]
    assert guardrail_gaps(data) == []


@pytest.mark.parametrize(
    ("dropped", "replacement", "lacks"),
    [
        ("ERA", None, "ERA"),  # E selects pycodestyle, not eradicate
        ("PT", None, "PT"),  # PTH is another linter
        ("SIM", "SIM1", "SIM"),  # a narrower selector leaves rules out
        ("C4", None, "C4"),  # C90 is another linter
        ("ANN401", "ANN", None),  # a wider selector covers the code
        ("ANN401", "ANN4", None),
        ("ANN401", "ANN402", "ANN401"),
    ],
)
def test_a_selector_covers_only_codes_that_it_prefixes_within_one_linter(
    dropped: str, replacement: str | None, lacks: str | None
) -> None:
    data = seeded_pyproject()
    select = [c for c in lint(data)["select"] if c != dropped]
    lint(data)["select"] = [*select, *([replacement] if replacement else [])]
    assert guardrail_gaps(data) == ([f"ruff: select lacks {lacks}"] if lacks else [])


def test_extend_select_counts_toward_the_floor() -> None:
    data = seeded_pyproject()
    lint(data)["select"] = [c for c in lint(data)["select"] if c != "SIM"]
    assert guardrail_gaps(data) == ["ruff: select lacks SIM"]
    lint(data)["extend-select"] = ["SIM"]
    assert guardrail_gaps(data) == []


def test_select_lists_every_missing_code_in_floor_order() -> None:
    data = seeded_pyproject()
    lint(data)["select"] = ["DTZ", "E", "B"]
    [gap] = [g for g in guardrail_gaps(data) if g.startswith("ruff: select")]
    assert gap == (
        "ruff: select lacks W, F, I, UP, SIM, C4, RUF, PGH, ERA, T20, S, TID, PT, PTH, C90, TD, "
        "BLE, ANN401"
    )


@pytest.mark.parametrize(
    ("ignore", "disabled"),
    [
        (["RUF1"], ["RUF100"]),
        (["RUF"], ["RUF100"]),
        (["PGH"], ["PGH003", "PGH004"]),
        (["ERA001"], ["ERA001"]),
        (["ALL"], ["PGH003", "PGH004", "RUF100", "ERA001"]),
        (["E501", "R", "PG"], []),  # E501 is another rule; R and PG are not the letters of any
    ],
)
def test_ignore_names_each_escape_hatch_it_covers(ignore: list[str], disabled: list[str]) -> None:
    data = seeded_pyproject()
    lint(data)["ignore"] = ignore
    assert guardrail_gaps(data) == [f"ruff: ignore disables {code}" for code in disabled]


def test_relative_imports_must_be_banned_in_all_forms() -> None:
    data = seeded_pyproject()
    lint(data)["flake8-tidy-imports"]["ban-relative-imports"] = "parents"
    assert guardrail_gaps(data) == ["ruff: relative imports are not banned"]
    del lint(data)["flake8-tidy-imports"]
    assert guardrail_gaps(data) == ["ruff: relative imports are not banned"]


@pytest.mark.parametrize(
    ("dependencies", "lacks"),
    [
        (["anyio>=4"], "ASYNC"),
        (["trio"], "ASYNC"),
        (["FastAPI[standard]>=0.115"], "ASYNC, FAST"),
        (["fast_api"], None),  # a different package
        (["requests"], None),
    ],
)
def test_async_frameworks_add_their_ruff_codes(dependencies: list[str], lacks: str | None) -> None:
    data = seeded_pyproject()
    data["project"]["dependencies"] = dependencies
    expected = [f"ruff: select lacks {lacks}"] if lacks else []
    assert guardrail_gaps(data) == expected
    lint(data)["select"] += ["ASYNC", "FAST"]
    assert guardrail_gaps(data) == []


def test_mypy_settings_must_be_true_and_all_codes_enabled() -> None:
    data = seeded_pyproject()
    data["tool"]["mypy"]["strict"] = "true"  # a string is not the boolean
    data["tool"]["mypy"]["enable_error_code"] = "ignore-without-code, truthy-bool"
    assert guardrail_gaps(data) == [
        "mypy: strict is not true",
        "mypy: enable_error_code lacks redundant-expr",
    ]
    del data["tool"]["mypy"]["enable_error_code"]
    assert "mypy: enable_error_code lacks ignore-without-code, redundant-expr, truthy-bool" in (
        guardrail_gaps(data)
    )


def test_import_linter_needs_a_layers_and_a_forbidden_contract() -> None:
    data = seeded_pyproject()
    contracts = data["tool"]["importlinter"]["contracts"]
    data["tool"]["importlinter"]["contracts"] = [c for c in contracts if c["type"] != "forbidden"]
    assert guardrail_gaps(data) == ["import-linter: no forbidden contract"]
    data["tool"]["importlinter"]["contracts"] = []
    assert guardrail_gaps(data) == [
        "import-linter: no layers contract",
        "import-linter: no forbidden contract",
    ]


def test_pytest_settings() -> None:
    data = seeded_pyproject()
    options = data["tool"]["pytest"]["ini_options"]
    options["addopts"] = '-ra "--strict-markers" --strict-config'  # quotes are shell syntax
    assert guardrail_gaps(data) == []
    options.update(xfail_strict=False, filterwarnings=["ignore", "error::UserWarning"])
    assert guardrail_gaps(data) == [
        "pytest: xfail_strict is not true",
        "pytest: filterwarnings lacks error",
    ]
    options["filterwarnings"] = "ignore::DeprecationWarning\nerror"
    options["addopts"] = "-ra 'unbalanced"  # not valid shell: split on spaces instead
    assert guardrail_gaps(data) == [
        "pytest: addopts lacks --strict-markers",
        "pytest: addopts lacks --strict-config",
        "pytest: xfail_strict is not true",
    ]


def test_dev_dependencies_compare_normalised_names() -> None:
    data = seeded_pyproject()
    data["dependency-groups"]["dev"] = ["Import_Linter>=2", "ruff", "pytest ; python_version>'3'"]
    assert guardrail_gaps(data) == ["dev dependencies lack mypy"]
    data["dependency-groups"]["dev"] = [{"include-group": "lint"}]
    assert guardrail_gaps(data) == ["dev dependencies lack ruff, mypy, pytest, import-linter"]


def test_an_empty_or_malformed_pyproject_reports_every_area_and_does_not_crash() -> None:
    floor = (
        "E, W, F, I, B, UP, SIM, C4, RUF, PGH, ERA, T20, S, TID, PT, PTH, DTZ, C90, TD, BLE, ANN401"
    )
    gaps = guardrail_gaps({})
    assert gaps == [
        f"ruff: select lacks {floor}",
        "ruff: relative imports are not banned",
        "mypy: strict is not true",
        "mypy: warn_unreachable is not true",
        "mypy: enable_error_code lacks ignore-without-code, redundant-expr, truthy-bool",
        "import-linter: no layers contract",
        "import-linter: no forbidden contract",
        "pytest: addopts lacks --strict-markers",
        "pytest: addopts lacks --strict-config",
        "pytest: xfail_strict is not true",
        "pytest: filterwarnings lacks error",
        "dev dependencies lack ruff, mypy, pytest, import-linter",
    ]
    malformed = {"tool": {"ruff": "no", "mypy": 3, "pytest": [], "importlinter": {"contracts": 1}}}
    assert guardrail_gaps({**malformed, "project": [], "dependency-groups": "no"}) == gaps


@pytest.mark.parametrize(
    "entry", ["tools/devctl", "./tools/devctl/", "tools/devctl/**", "tools", "./tools/**"]
)
def test_ruff_exclusion_paths_are_compared_without_decoration(entry: str) -> None:
    data = seeded_pyproject()
    data["tool"]["ruff"]["extend-exclude"] = []
    data["tool"]["ruff"]["exclude"] = [entry]
    assert devctl_exclusion_gaps(data, python=True) == []


def test_ruff_exclusion_must_name_tools_devctl_or_tools() -> None:
    data = seeded_pyproject()
    data["tool"]["ruff"]["extend-exclude"] = ["tools/other", "devctl", "tools/devctl/devctl"]
    assert devctl_exclusion_gaps(data, python=True) == [RUFF]


@pytest.mark.parametrize(
    ("files", "exclude", "gap"),
    [
        (["."], None, True),
        (["./"], None, True),
        (["tools"], None, True),
        (["tools/devctl/devctl"], None, True),
        (["tools/devctl/devctl/cli.py"], None, True),
        (["tools/devctl/devctl/other.py"], None, False),
        (["src", "tests"], None, False),
        (["tests", "tools"], "^tools/devctl/", False),  # a string pattern
        (["."], ["docs", "tools/devctl"], False),  # re.search, not a prefix match
        (["."], ["^docs/"], True),
        (["."], ["(unbalanced", "^other/"], True),  # an invalid pattern matches nothing
        (["."], ["(unbalanced", "devctl"], False),
    ],
)
def test_mypy_files_and_exclude(files: list[str], exclude: object, gap: bool) -> None:
    data = seeded_pyproject()
    data["tool"]["mypy"]["files"] = files
    if exclude is not None:
        data["tool"]["mypy"]["exclude"] = exclude
    assert devctl_exclusion_gaps(data, python=True) == ([MYPY] if gap else [])


@pytest.mark.parametrize(
    ("testpaths", "addopts", "gap"),
    [
        (None, [], True),  # pytest then collects from the rootdir
        ([], [], True),
        (["."], [], True),
        (["tools"], [], True),
        (["tools/devctl"], [], True),
        (["tools/devctl/tests"], [], True),
        (["./tools/devctl/"], [], True),
        (["tests", "tools/devctl2"], [], False),  # a different directory
        (["tests"], [], False),
        (["."], ["-ra", "--ignore=tools/devctl"], False),
        (None, "-ra --ignore=./tools/devctl/", False),
        (["."], ["--ignore=tools/other"], True),
    ],
)
def test_pytest_testpaths_and_ignore(
    testpaths: list[str] | None, addopts: object, gap: bool
) -> None:
    data = seeded_pyproject()
    options = data["tool"]["pytest"]["ini_options"]
    del options["testpaths"]
    if testpaths is not None:
        options["testpaths"] = testpaths
    options["addopts"] = addopts
    assert devctl_exclusion_gaps(data, python=True) == ([PYTEST] if gap else [])


@pytest.mark.parametrize(
    ("members", "exclude", "gap"),
    [
        (["tools/*"], [], True),
        (["tools/devctl"], [], True),
        (["./tools/devctl/"], [], True),
        (["**"], [], True),
        (["tools/dev?tl"], [], True),
        (["tools/*"], ["tools/*"], False),
        (["tools/*"], ["tools/devctl"], False),
        (["tools/*"], ["tools/other"], True),
        (["packages/*"], [], False),
        (["tools/devctl/*"], [], False),  # one level too deep
        ([], [], False),
    ],
)
def test_uv_workspace_members_must_leave_out_tools_devctl(
    members: list[str], exclude: list[str], gap: bool
) -> None:
    data = seeded_pyproject()
    data["tool"]["uv"] = {"workspace": {"members": members, "exclude": exclude}}
    expected = [UV] if gap else []
    assert devctl_exclusion_gaps(data, python=True) == expected
    assert devctl_exclusion_gaps(data, python=False) == expected  # either stack
