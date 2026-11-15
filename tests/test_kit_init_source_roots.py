"""rapid-ship init: the source root of each existing Python stack, in scratch repositories
(offline)."""

import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from test_kit_contents import VARIABLES

from devctl.check.map import MapStep
from devctl.check.steps import CheckContext
from devctl.repo import Repo
from devctl.settings import load_project
from rapid_ship.cli import main
from rapid_ship.kit.git import head_commit
from rapid_ship.kit.init import init_repository, resolve_variables
from rapid_ship.kit.lock import LOCK_PATH, read_lock
from rapid_ship.kit.stacks import KITS, ProjectStack, StackName, derived_variables
from rapid_ship.kit.status import classify
from rapid_ship.kit.sync import sync_repository
from rapid_ship.kit.templates import KitError

ROOT = ProjectStack("python", ".")
GREETING = ProjectStack("python", "tools/greeting-tools")
TOOLS_X = ProjectStack("python", "tools/x")
WORKSPACE = '[tool.uv.workspace]\nmembers = ["tools/*"]\n'


def write_files(root: Path, files: Mapping[str, str]) -> None:
    """Write each file; a path that ends with a slash is an empty directory."""
    for relative, text in files.items():
        path = root / relative
        if relative.endswith("/"):
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)


def add_project(
    root: Path, directory: str, name: str, package: str, *, layout: str = "src", extra: str = ""
) -> None:
    """Write an existing Python project under root/directory: its pyproject.toml, its package
    and the guides that the navigation row of its stack guide names."""
    base = root if directory == "." else root / directory
    write_files(
        base,
        {
            "pyproject.toml": f'[project]\nname = "{name}"\n{extra}',
            f"{package if layout == 'flat' else f'src/{package}'}/__init__.py": "",
            "src/AGENTS.md": "# Source\n",
            "tests/AGENTS.md": "# Tests\n",
        },
    )


def source_roots(root: Path) -> list[str]:
    settings = tomllib.loads((root / ".rapid-ship/project.toml").read_text())
    return list(settings["map"]["source_roots"])


@pytest.fixture
def workspace(git_repo: Path, commit_all: Callable[..., None]) -> Path:
    """A uv workspace after init: the root project rs-existing and the member greeting-tools."""
    add_project(git_repo, ".", "rs-existing", "rs_existing", extra=WORKSPACE)
    add_project(git_repo, "tools/greeting-tools", "greeting-tools", "greeting_tools")
    commit_all(git_repo)
    variables = resolve_variables(git_repo, repository="octo/rs-existing")
    init_repository(git_repo, stacks=[ROOT, GREETING], variables=variables)
    return git_repo


def test_each_existing_stack_gets_its_own_source_root(workspace: Path) -> None:
    assert source_roots(workspace) == [
        "src/rs_existing",
        "tools/greeting-tools/src/greeting_tools",
    ]


def test_the_lock_records_the_source_root_of_each_existing_stack(workspace: Path) -> None:
    variables = read_lock(workspace).variables
    assert variables["source_root:."] == "src/rs_existing"
    assert variables["source_root:tools/greeting-tools"] == "src/greeting_tools"


def test_the_map_step_passes_on_the_initialized_workspace(workspace: Path) -> None:
    context = CheckContext(Repo.discover(workspace), load_project(workspace), None, None)
    result = MapStep().run(context)
    assert result.status == "passed", result.details


def test_status_and_sync_render_the_same_project_settings(workspace: Path) -> None:
    report = classify(workspace)
    assert not [f.path for f in report.files if f.state == "template updated"]
    assert report.strict_ok
    assert not sync_repository(workspace, in_place=True).changed


def test_a_root_package_that_differs_from_the_repository_name(
    git_repo: Path,
    commit_all: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    add_project(git_repo, ".", "acme", "acme")
    commit_all(git_repo)
    monkeypatch.chdir(git_repo)

    assert main(["init", "--stack", "python", "--repository", "octo/acme-api"]) == 0

    assert "for acme-api (package acme).\n" in capsys.readouterr().out
    assert source_roots(git_repo) == ["src/acme"]
    assert read_lock(git_repo).variables["source_root:."] == "src/acme"


def test_the_package_option_wins_for_the_root_stack(
    git_repo: Path, commit_all: Callable[..., None]
) -> None:
    add_project(git_repo, ".", "acme", "acme")
    write_files(git_repo, {"src/custom/__init__.py": ""})
    commit_all(git_repo)

    init_repository(
        git_repo, stacks=[ROOT], variables=resolve_variables(git_repo, package="custom")
    )

    assert source_roots(git_repo) == ["src/custom"]


@pytest.mark.parametrize("directory", [".", "tools/flat-tools"])
def test_a_flat_layout_gets_its_own_source_root(
    git_repo: Path, commit_all: Callable[..., None], directory: str
) -> None:
    add_project(git_repo, directory, "flat-tools", "flat_tools", layout="flat")
    commit_all(git_repo)

    init_repository(
        git_repo,
        stacks=[ProjectStack("python", directory)],
        variables=resolve_variables(git_repo),
    )

    assert source_roots(git_repo) == [f"{directory}/flat_tools".removeprefix("./")]
    assert read_lock(git_repo).variables[f"source_root:{directory}"] == "flat_tools"
    assert classify(git_repo).strict_ok
    assert not sync_repository(git_repo, in_place=True).changed


def test_a_src_layout_wins_over_a_flat_one(git_repo: Path, commit_all: Callable[..., None]) -> None:
    add_project(git_repo, ".", "acme", "acme")
    write_files(git_repo, {"acme/__init__.py": ""})
    commit_all(git_repo)

    init_repository(git_repo, stacks=[ROOT], variables=resolve_variables(git_repo))

    assert source_roots(git_repo) == ["src/acme"]


def test_a_new_stack_keeps_the_project_package_beside_an_existing_one(
    git_repo: Path, commit_all: Callable[..., None]
) -> None:
    add_project(git_repo, ".", "acme", "acme")
    commit_all(git_repo)

    init_repository(
        git_repo,
        stacks=[ROOT, ProjectStack("python", "services/new")],
        variables=resolve_variables(git_repo),
    )

    assert source_roots(git_repo) == ["src/acme", "services/new/src/acme"]
    assert (git_repo / "services/new/src/acme/__init__.py").is_file()
    recorded = {key for key in read_lock(git_repo).variables if key.startswith("source_root:")}
    assert recorded == {"source_root:."}


def test_rendering_uses_the_recorded_source_root_of_the_stack_that_has_one() -> None:
    stacks = (ProjectStack("python", "backend"), ProjectStack("python", "worker"))
    variables = {**VARIABLES, "source_root:backend": "backend_core", "source_root:other": "x"}

    roots = derived_variables(stacks, variables)["source_roots"]

    assert roots == '"backend/backend_core", "worker/src/demo_app"'


@pytest.mark.parametrize("directory", [".", "services/api"])
@pytest.mark.parametrize("kind", [name for name, kit in KITS.items() if kit.source_root])
def test_every_source_root_that_init_writes_exists_afterwards(
    git_repo: Path, run_git: Callable[..., str], kind: StackName, directory: str
) -> None:
    init_repository(git_repo, stacks=[ProjectStack(kind, directory)], variables=VARIABLES)

    tracked = run_git(git_repo, "ls-files").splitlines()
    assert source_roots(git_repo)
    for source_root in source_roots(git_repo):
        assert any(path.startswith(f"{source_root}/") for path in tracked), source_root


ACME = {"pyproject.toml": '[project]\nname = "acme"\n'}
MEMBER_FIX = (
    "Fix tools/x/pyproject.toml so that it has a [project] name whose package directory exists, "
    "or run init without --stack python=tools/x."
)
ROOT_FIX = (
    "Pass --package naming the package directory, then run init again. If the repository root "
    "holds no package, run init without the --stack option that names the root."
)
ROOT_OK = {**ACME, "src/acme/__init__.py": ""}


@pytest.mark.parametrize(
    ("files", "stacks", "package", "message"),
    [
        pytest.param(
            {"pyproject.toml": '[project]\nname = "acme-api"\n'},
            [ROOT],
            None,
            "init wrote nothing: the python stack in . has no package directory: init looked "
            f"in src/acme_api or acme_api and found no tracked file. {ROOT_FIX}",
            id="root: no package directory",
        ),
        pytest.param(
            ROOT_OK,
            [ROOT],
            "wrong",
            "init wrote nothing: the python stack in . has no package directory: init looked "
            f"in src/wrong or wrong and found no tracked file. {ROOT_FIX}",
            id="root: the package option names none",
        ),
        pytest.param(
            {**ACME, "src/acme/": ""},
            [ROOT],
            None,
            "init wrote nothing: the python stack in . has no package directory: init looked "
            f"in src/acme or acme and found no tracked file. {ROOT_FIX}",
            id="root: an empty directory",
        ),
        pytest.param(
            {**ACME, ".gitignore": "src/acme/\n", "src/acme/__init__.py": ""},
            [ROOT],
            None,
            "init wrote nothing: the python stack in . has no package directory: init looked "
            f"in src/acme or acme and found no tracked file. {ROOT_FIX}",
            id="root: a directory that git ignores",
        ),
        pytest.param(
            {**ACME, "src/Acme/__init__.py": ""},
            [ROOT],
            None,
            "init wrote nothing: the python stack in . has no package directory: init looked "
            f"in src/acme or acme and found no tracked file. {ROOT_FIX}",
            id="root: a directory that differs in case",
        ),
        pytest.param(
            {**ROOT_OK, "tools/x/pyproject.toml": "[tool.ruff]\n"},
            [ROOT, TOOLS_X],
            None,
            "init wrote nothing: the python stack in tools/x has no package directory: "
            "tools/x/pyproject.toml has no [project] name, so init could not tell where to "
            f"look. {MEMBER_FIX}",
            id="member: no [project] name",
        ),
        pytest.param(
            {**ROOT_OK, "tools/x/pyproject.toml": '[project]\nname = "x-y"\n'},
            [ROOT, TOOLS_X],
            None,
            "init wrote nothing: the python stack in tools/x has no package directory: init "
            "looked in tools/x/src/x_y or tools/x/x_y and found no tracked file. "
            f"{MEMBER_FIX}",
            id="member: no package directory",
        ),
    ],
)
def test_init_stops_before_any_write_when_a_stack_has_no_package_directory(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    files: Mapping[str, str],
    stacks: list[ProjectStack],
    package: str | None,
    message: str,
) -> None:
    write_files(git_repo, files)
    commit_all(git_repo)
    before = (head_commit(git_repo), run_git(git_repo, "status", "--porcelain"))

    with pytest.raises(KitError) as caught:
        init_repository(
            git_repo, stacks=stacks, variables=resolve_variables(git_repo, package=package)
        )

    assert str(caught.value) == message
    assert (head_commit(git_repo), run_git(git_repo, "status", "--porcelain")) == before
    assert run_git(git_repo, "branch", "--list", "rapid-ship/init") == ""
    assert not (git_repo / LOCK_PATH).exists()


def test_init_stops_before_any_write_when_a_stack_pyproject_is_unreadable(
    git_repo: Path, commit_all: Callable[..., None], run_git: Callable[..., str]
) -> None:
    write_files(git_repo, {**ROOT_OK, "tools/x/pyproject.toml": "[project\n"})
    commit_all(git_repo)
    before = head_commit(git_repo)

    with pytest.raises(
        KitError, match=r"^init wrote nothing: cannot read tools/x/pyproject\.toml"
    ) as caught:
        init_repository(git_repo, stacks=[ROOT, TOOLS_X], variables=resolve_variables(git_repo))

    assert str(caught.value).endswith(f" {MEMBER_FIX}")
    assert head_commit(git_repo) == before
    assert run_git(git_repo, "branch", "--list", "rapid-ship/init") == ""
    assert not (git_repo / LOCK_PATH).exists()


def test_a_repository_without_commits_gets_no_empty_first_commit_on_that_error(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    # An ignored pyproject.toml keeps the tree clean, which a commitless repository needs.
    write_files(git_repo, {"pyproject.toml": '[project]\nname = "acme-api"\n'})
    (git_repo / ".git/info/exclude").write_text("/pyproject.toml\n")
    assert run_git(git_repo, "status", "--porcelain") == ""

    with pytest.raises(KitError, match="found no tracked file"):
        init_repository(git_repo, stacks=[ROOT], variables=resolve_variables(git_repo))

    assert head_commit(git_repo) is None
    assert run_git(git_repo, "branch", "--list") == ""


def test_init_with_an_unreadable_root_pyproject_exits_2_and_writes_nothing(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_files(git_repo, {"pyproject.toml": "[project\n"})
    commit_all(git_repo)
    before = head_commit(git_repo)
    monkeypatch.chdir(git_repo)

    assert main(["init", "--stack", "python"]) == 2

    error = capsys.readouterr().err
    assert error.startswith("rapid-ship: init wrote nothing: cannot read pyproject.toml (")
    assert error.endswith(". Fix it, or pass --package to name the package without it.\n")
    assert head_commit(git_repo) == before
    assert run_git(git_repo, "branch", "--list", "rapid-ship/init") == ""
    assert not (git_repo / LOCK_PATH).exists()


def test_the_package_option_is_the_next_step_for_a_root_package_the_name_does_not_give(
    git_repo: Path,
    commit_all: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    add_project(git_repo, ".", "acme-api", "acme_core")
    commit_all(git_repo)
    monkeypatch.chdir(git_repo)

    assert main(["init", "--stack", "python"]) == 2
    assert capsys.readouterr().err == (
        "rapid-ship: init wrote nothing: the python stack in . has no package directory: init "
        f"looked in src/acme_api or acme_api and found no tracked file. {ROOT_FIX}\n"
    )
    assert main(["init", "--stack", "python", "--package", "acme_core"]) == 0

    assert source_roots(git_repo) == ["src/acme_core"]


def test_a_workspace_root_without_a_package_is_left_out_of_the_stacks(
    git_repo: Path, commit_all: Callable[..., None], run_git: Callable[..., str]
) -> None:
    """The way out that the root stack's error names: init's proposal lists the root, but a
    virtual uv workspace root has no package for --package to name."""
    write_files(git_repo, {"pyproject.toml": '[tool.uv.workspace]\nmembers = ["packages/*"]\n'})
    add_project(git_repo, "packages/a", "a-pkg", "a_pkg")
    commit_all(git_repo)
    variables = resolve_variables(git_repo)

    with pytest.raises(KitError, match="holds no package, run init without the --stack option"):
        init_repository(
            git_repo, stacks=[ROOT, ProjectStack("python", "packages/a")], variables=variables
        )
    assert not (git_repo / LOCK_PATH).exists()

    init_repository(git_repo, stacks=[ProjectStack("python", "packages/a")], variables=variables)

    assert source_roots(git_repo) == ["packages/a/src/a_pkg"]
    assert classify(git_repo).strict_ok
