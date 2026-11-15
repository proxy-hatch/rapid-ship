"""rapid-ship init: the source root of each existing stack, and the guided errors that name the way
out, in scratch repositories (offline)."""

import re
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
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
from rapid_ship.kit.way_out import no_source_root

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


def uv_app(root: Path, directory: str, name: str) -> None:
    """What uv init --no-package writes: a pyproject.toml with a [project] name and no
    [build-system], and main.py, with no package directory."""
    base = root if directory == "." else root / directory
    write_files(
        base,
        {"pyproject.toml": f'[project]\nname = "{name}"\nversion = "0.1.0"\n', "main.py": "pass\n"},
    )


def source_roots(root: Path) -> list[str]:
    settings = tomllib.loads((root / ".rapid-ship/project.toml").read_text())
    return list(settings["map"]["source_roots"])


def assert_source_roots_hold_tracked_files(root: Path, run_git: Callable[..., str]) -> None:
    tracked = run_git(root, "ls-files").splitlines()
    assert source_roots(root)
    for source_root in source_roots(root):
        assert any(path.startswith(f"{source_root}/") for path in tracked), source_root


FIRST_WAY = re.compile(
    r"Create (?P<file>\S+), move the product code into (?P<directory>\S+) and commit them, "
    r"then run init again\."
)


def follow_the_first_way_out(
    root: Path,
    error: str,
    code: Sequence[str],
    run_git: Callable[..., str],
    commit_all: Callable[..., None],
) -> None:
    """Do the steps that the error names: create the file, git mv each product file into the
    directory, and commit."""
    step = FIRST_WAY.search(error)
    assert step, f"the error names no package directory to create: {error}"
    created = root / step["file"]
    created.parent.mkdir(parents=True, exist_ok=True)
    created.write_text("")
    for path in code:
        run_git(root, "mv", path, step["directory"] + Path(path).name)
    commit_all(root, "Package the product code")


@pytest.fixture
def init_cli(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Callable[..., tuple[int, str]]:
    """rapid-ship init OPTIONS in git_repo: its exit code and what it wrote to stderr."""
    monkeypatch.chdir(git_repo)

    def run(*options: str) -> tuple[int, str]:
        code = main(["init", *options])
        return code, capsys.readouterr().err

    return run


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


def give_agnostic_a_source_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates a stack kind other than Python that has a source root: the agnostic kit with
    one."""
    monkeypatch.setitem(KITS, "agnostic", replace(KITS["agnostic"], source_root="src"))


def test_a_recorded_source_root_applies_to_the_python_stack_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    give_agnostic_a_source_root(monkeypatch)
    stacks = (ProjectStack("python", "."), ProjectStack("agnostic", "."))
    variables = {**VARIABLES, "source_root:.": "flat_pkg"}

    roots = derived_variables(stacks, variables)["source_roots"]

    assert roots == '"src", "flat_pkg"'


SOURCE_ROOT_KINDS = [name for name, kit in KITS.items() if kit.source_root]
# A kind whose marker is not listed gets an empty file. A kind that needs more than that fails
# the tests below until its content is added here.
MARKER_CONTENT = {"pyproject.toml": '[project]\nname = "demo-app"\n'}


def existing_project(root: Path, kind: StackName, directory: str, *, code: bool) -> None:
    """The marker that makes the stack an existing one and, with code, a file in its source root."""
    kit = KITS[kind]
    files: dict[str, str] = {}
    if kit.new_project_marker:
        files[kit.new_project_marker] = MARKER_CONTENT.get(kit.new_project_marker, "")
    if code:
        files[f"{kit.source_root.format(**VARIABLES)}/product.txt"] = ""
    write_files(root if directory == "." else root / directory, files)


@pytest.mark.parametrize("directory", [".", "services/api"])
@pytest.mark.parametrize("kind", SOURCE_ROOT_KINDS)
def test_every_source_root_that_init_writes_exists_afterwards(
    git_repo: Path, run_git: Callable[..., str], kind: StackName, directory: str
) -> None:
    init_repository(git_repo, stacks=[ProjectStack(kind, directory)], variables=VARIABLES)

    assert_source_roots_hold_tracked_files(git_repo, run_git)


@pytest.mark.parametrize("directory", [".", "services/api"])
@pytest.mark.parametrize("kind", SOURCE_ROOT_KINDS)
def test_every_source_root_of_an_existing_stack_holds_a_tracked_file(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    kind: StackName,
    directory: str,
) -> None:
    existing_project(git_repo, kind, directory, code=True)
    commit_all(git_repo)

    init_repository(git_repo, stacks=[ProjectStack(kind, directory)], variables=VARIABLES)

    assert_source_roots_hold_tracked_files(git_repo, run_git)


@pytest.mark.parametrize("directory", [".", "services/api"])
@pytest.mark.parametrize("kind", SOURCE_ROOT_KINDS)
def test_init_stops_for_an_existing_stack_with_no_tracked_file_in_its_source_root(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    kind: StackName,
    directory: str,
) -> None:
    existing_project(git_repo, kind, directory, code=False)
    commit_all(git_repo)
    before = (head_commit(git_repo), run_git(git_repo, "status", "--porcelain"))

    with pytest.raises(KitError, match="found no tracked file"):
        init_repository(git_repo, stacks=[ProjectStack(kind, directory)], variables=VARIABLES)

    assert (head_commit(git_repo), run_git(git_repo, "status", "--porcelain")) == before
    assert run_git(git_repo, "branch", "--list", "rapid-ship/init") == ""
    assert not (git_repo / LOCK_PATH).exists()


ACME = {"pyproject.toml": '[project]\nname = "acme"\n'}
ROOT_OK = {**ACME, "src/acme/__init__.py": ""}
X_Y = '[project]\nname = "x-y"\n'
# The way out for a directory that holds no product code. While another --stack option remains,
# leaving this one out works. For the only stack it would make init print its proposal again.
ROOT_LEAVE_OUT = "If the root holds no product code, run init without --stack python."
ROOT_REPLACE = (
    "If the root holds no product code, replace --stack python with a --stack option for each "
    "stack that has product code, or with --stack agnostic when none has."
)
MEMBER_FIX = "Fix tools/x/pyproject.toml and commit the fix, then run init again. "
ROOT_FIX = (
    "Fix pyproject.toml and commit the fix, then run init again, or pass --package with the "
    "package directory's name, not its path, so that init does not read the file."
)
MEMBER_NO_NAME = (
    "init wrote nothing: the python stack in tools/x has no package directory: "
    "tools/x/pyproject.toml has no [project] name, so init could not tell where to look. Add a "
    "[project] name to tools/x/pyproject.toml, create tools/x/src/<name>/__init__.py, where "
    "<name> is that name in lowercase with each run of - _ or . replaced by _, move the "
    "product code into tools/x/src/<name>/ and commit them, then run init again. "
)


def leave_out(directory: str) -> str:
    return f"If {directory} holds no product code, run init without --stack python={directory}."


def replace_option(directory: str) -> str:
    return (
        f"If {directory} holds no product code, replace --stack python={directory} with a "
        "--stack option for each stack that has product code, or with --stack agnostic when "
        "none has."
    )


def root_error(package: str, way_out: str = ROOT_REPLACE) -> str:
    return (
        "init wrote nothing: the python stack in . has no package directory: init looked in "
        f"src/{package} or {package} and found no tracked file. Create src/{package}/__init__.py, "
        f"move the product code into src/{package}/ and commit them, then run init again. If the "
        "product code is already in a package directory with another name, pass --package "
        f"with that directory's name, not its path. {way_out}"
    )


def member_error(directory: str, package: str, way_out: str) -> str:
    return (
        f"init wrote nothing: the python stack in {directory} has no package directory: init "
        f"looked in {directory}/src/{package} or {directory}/{package} and found no tracked "
        f"file. Create {directory}/src/{package}/__init__.py, move the product code into "
        f"{directory}/src/{package}/ and commit them, then run init again. {way_out}"
    )


@pytest.mark.parametrize(
    ("files", "stacks", "package", "message"),
    [
        pytest.param(
            {"pyproject.toml": '[project]\nname = "acme-api"\n'},
            [ROOT],
            None,
            root_error("acme_api"),
            id="root: no package directory",
        ),
        pytest.param(
            ROOT_OK, [ROOT], "wrong", root_error("wrong"), id="root: the package option names none"
        ),
        pytest.param(
            {**ACME, "src/acme/": ""},
            [ROOT],
            None,
            root_error("acme"),
            id="root: an empty directory",
        ),
        pytest.param(
            {**ACME, ".gitignore": "src/acme/\n", "src/acme/__init__.py": ""},
            [ROOT],
            None,
            root_error("acme"),
            id="root: a directory that git ignores",
        ),
        pytest.param(
            {**ACME, "src/Acme/__init__.py": ""},
            [ROOT],
            None,
            root_error("acme"),
            id="root: a directory that differs in case",
        ),
        pytest.param(
            {**ACME, "src/acme_extra/__init__.py": ""},
            [ROOT],
            None,
            root_error("acme"),
            id="root: a sibling directory that shares the prefix",
        ),
        pytest.param(
            {**ACME, "tools/x/pyproject.toml": X_Y, "tools/x/src/x_y/__init__.py": ""},
            [ROOT, TOOLS_X],
            None,
            root_error("acme", ROOT_LEAVE_OUT),
            id="root: another stack remains",
        ),
        pytest.param(
            {**ROOT_OK, "tools/x/pyproject.toml": X_Y},
            [ROOT, TOOLS_X],
            None,
            member_error("tools/x", "x_y", leave_out("tools/x")),
            id="member: no package directory",
        ),
        pytest.param(
            {**ACME, "tools/x/pyproject.toml": X_Y},
            [TOOLS_X],
            None,
            member_error("tools/x", "x_y", replace_option("tools/x")),
            id="member: no package directory, the only stack",
        ),
        pytest.param(
            {**ROOT_OK, "tools/x/pyproject.toml": "[tool.ruff]\n"},
            [ROOT, TOOLS_X],
            None,
            MEMBER_NO_NAME + leave_out("tools/x"),
            id="member: no [project] name",
        ),
        pytest.param(
            {**ACME, "tools/x/pyproject.toml": "[tool.ruff]\n"},
            [TOOLS_X],
            None,
            MEMBER_NO_NAME + replace_option("tools/x"),
            id="member: no [project] name, the only stack",
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


@pytest.mark.parametrize(
    ("stacks", "way_out"),
    [
        pytest.param([ROOT, TOOLS_X], leave_out("tools/x"), id="another stack remains"),
        pytest.param([TOOLS_X], replace_option("tools/x"), id="the only stack"),
    ],
)
def test_init_stops_before_any_write_when_a_stack_pyproject_is_unreadable(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    stacks: list[ProjectStack],
    way_out: str,
) -> None:
    write_files(git_repo, {**ROOT_OK, "tools/x/pyproject.toml": "[project\n"})
    commit_all(git_repo)
    before = head_commit(git_repo)

    with pytest.raises(KitError) as caught:
        init_repository(git_repo, stacks=stacks, variables=resolve_variables(git_repo))

    message = str(caught.value)
    assert message.startswith("init wrote nothing: cannot read tools/x/pyproject.toml (")
    assert message.endswith(f"). {MEMBER_FIX}{way_out}")
    # init could not read the name, so it cannot know where the package directory is.
    assert "src/" not in message
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
    init_cli: Callable[..., tuple[int, str]],
) -> None:
    write_files(git_repo, {"pyproject.toml": "[project\n"})
    commit_all(git_repo)
    before = head_commit(git_repo)

    code, error = init_cli("--stack", "python")

    assert code == 2
    assert error.startswith("rapid-ship: init wrote nothing: cannot read pyproject.toml (")
    assert error.endswith(f"). {ROOT_FIX}\n")
    assert "src/" not in error
    assert head_commit(git_repo) == before
    assert run_git(git_repo, "branch", "--list", "rapid-ship/init") == ""
    assert not (git_repo / LOCK_PATH).exists()


@pytest.mark.parametrize("way", ["fix the file", "pass --package"])
def test_an_unreadable_root_pyproject_is_left_by_the_way_the_error_names(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
    way: str,
) -> None:
    write_files(git_repo, {"pyproject.toml": "[project\n", "src/acme/__init__.py": ""})
    commit_all(git_repo)
    assert init_cli("--stack", "python")[0] == 2

    if way == "fix the file":
        write_files(git_repo, ACME)
        commit_all(git_repo, "Fix pyproject.toml")
        assert init_cli("--stack", "python") == (0, "")
    else:
        assert init_cli("--stack", "python", "--package", "acme") == (0, "")

    assert source_roots(git_repo) == ["src/acme"]
    assert_source_roots_hold_tracked_files(git_repo, run_git)


def test_the_package_option_is_the_next_step_for_a_root_package_the_name_does_not_give(
    git_repo: Path, commit_all: Callable[..., None], init_cli: Callable[..., tuple[int, str]]
) -> None:
    add_project(git_repo, ".", "acme-api", "acme_core")
    commit_all(git_repo)

    assert init_cli("--stack", "python") == (2, f"rapid-ship: {root_error('acme_api')}\n")
    # A path is not the directory's name, and the error that says so leads on to the name.
    assert init_cli("--stack", "python", "--package", "src/acme_core") == (
        2,
        "rapid-ship: package 'src/acme_core' is not a Python package name; --package takes the "
        "package directory's name, not a path.\n",
    )
    assert init_cli("--stack", "python", "--package", "acme_core") == (0, "")

    assert source_roots(git_repo) == ["src/acme_core"]


def test_a_workspace_root_without_a_package_is_left_out_of_the_stacks(
    git_repo: Path, commit_all: Callable[..., None]
) -> None:
    """The way out that the root stack's error names while another stack remains: init's proposal
    lists the root, but a virtual uv workspace root has no package for --package to name."""
    write_files(git_repo, {"pyproject.toml": '[tool.uv.workspace]\nmembers = ["packages/*"]\n'})
    add_project(git_repo, "packages/a", "a-pkg", "a_pkg")
    commit_all(git_repo)
    variables = resolve_variables(git_repo)

    with pytest.raises(KitError) as caught:
        init_repository(
            git_repo, stacks=[ROOT, ProjectStack("python", "packages/a")], variables=variables
        )
    assert str(caught.value) == root_error("project", ROOT_LEAVE_OUT)
    assert not (git_repo / LOCK_PATH).exists()

    init_repository(git_repo, stacks=[ProjectStack("python", "packages/a")], variables=variables)

    assert source_roots(git_repo) == ["packages/a/src/a_pkg"]
    assert classify(git_repo).strict_ok


def test_an_unpackaged_uv_app_at_the_root_follows_the_first_way_out(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
) -> None:
    uv_app(git_repo, ".", "acme-api")
    commit_all(git_repo)
    options = ["--stack", "python"]

    code, error = init_cli(*options)
    assert (code, error) == (2, f"rapid-ship: {root_error('acme_api')}\n")

    follow_the_first_way_out(git_repo, error, ["main.py"], run_git, commit_all)
    assert init_cli(*options) == (0, "")

    assert source_roots(git_repo) == ["src/acme_api"]
    assert_source_roots_hold_tracked_files(git_repo, run_git)


def test_an_unpackaged_uv_member_follows_the_first_way_out(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
) -> None:
    members = '[tool.uv.workspace]\nmembers = ["tools/x-y"]\n'
    add_project(git_repo, ".", "rs-existing", "rs_existing", extra=members)
    uv_app(git_repo, "tools/x-y", "x-y")
    commit_all(git_repo)
    options = ["--stack", "python", "--stack", "python=tools/x-y"]

    code, error = init_cli(*options)
    assert (code, error) == (
        2,
        f"rapid-ship: {member_error('tools/x-y', 'x_y', leave_out('tools/x-y'))}\n",
    )

    follow_the_first_way_out(git_repo, error, ["tools/x-y/main.py"], run_git, commit_all)
    assert init_cli(*options) == (0, "")

    assert source_roots(git_repo) == ["src/rs_existing", "tools/x-y/src/x_y"]
    assert_source_roots_hold_tracked_files(git_repo, run_git)


@pytest.mark.parametrize("way", ["create the package", "pass --stack agnostic"])
def test_a_root_pyproject_without_product_code_follows_the_way_out_the_error_names(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
    way: str,
) -> None:
    write_files(
        git_repo,
        {"pyproject.toml": "[tool.ruff]\nline-length = 100\n", "docs/index.md": "# Docs\n"},
    )
    commit_all(git_repo)
    options = ["--stack", "python", "--repository", "octo/docs-site"]

    code, error = init_cli(*options)
    assert (code, error) == (2, f"rapid-ship: {root_error('docs_site')}\n")

    if way == "create the package":
        follow_the_first_way_out(git_repo, error, [], run_git, commit_all)
        assert init_cli(*options) == (0, "")
        assert source_roots(git_repo) == ["src/docs_site"]
        assert_source_roots_hold_tracked_files(git_repo, run_git)
    else:
        assert init_cli("--stack", "agnostic", "--repository", "octo/docs-site") == (0, "")
        assert source_roots(git_repo) == []


def test_a_sole_member_without_product_code_is_replaced_by_the_agnostic_stack(
    git_repo: Path, commit_all: Callable[..., None], init_cli: Callable[..., tuple[int, str]]
) -> None:
    write_files(git_repo, {**ACME, "tools/x/pyproject.toml": X_Y})
    commit_all(git_repo)

    assert init_cli("--stack", "python=tools/x") == (
        2,
        f"rapid-ship: {member_error('tools/x', 'x_y', replace_option('tools/x'))}\n",
    )
    assert init_cli("--stack", "agnostic") == (0, "")

    assert source_roots(git_repo) == []


def test_a_member_without_a_project_name_follows_the_way_out(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
) -> None:
    write_files(
        git_repo,
        {**ROOT_OK, "tools/x/pyproject.toml": "[tool.ruff]\n", "tools/x/main.py": "pass\n"},
    )
    commit_all(git_repo)
    options = ["--stack", "python", "--stack", "python=tools/x"]

    assert init_cli(*options) == (2, f"rapid-ship: {MEMBER_NO_NAME}{leave_out('tools/x')}\n")

    # The steps: a [project] name, then <name> as the error defines it for the package directory.
    write_files(
        git_repo,
        {
            "tools/x/pyproject.toml": '[project]\nname = "X.Tool__x"\n',
            "tools/x/src/x_tool_x/__init__.py": "",
        },
    )
    run_git(git_repo, "mv", "tools/x/main.py", "tools/x/src/x_tool_x/main.py")
    commit_all(git_repo, "Name and package the member")
    assert init_cli(*options) == (0, "")

    assert source_roots(git_repo) == ["src/acme", "tools/x/src/x_tool_x"]
    assert_source_roots_hold_tracked_files(git_repo, run_git)


def test_an_unreadable_member_pyproject_is_fixed_and_committed_as_the_error_says(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
) -> None:
    write_files(
        git_repo,
        {**ROOT_OK, "tools/x/pyproject.toml": "[project\n", "tools/x/src/x_y/__init__.py": ""},
    )
    commit_all(git_repo)
    options = ["--stack", "python", "--stack", "python=tools/x"]

    code, error = init_cli(*options)
    assert code == 2
    assert error.endswith(f"). {MEMBER_FIX}{leave_out('tools/x')}\n")

    write_files(git_repo, {"tools/x/pyproject.toml": X_Y})
    commit_all(git_repo, "Fix tools/x/pyproject.toml")
    assert init_cli(*options) == (0, "")

    assert source_roots(git_repo) == ["src/acme", "tools/x/src/x_y"]
    assert_source_roots_hold_tracked_files(git_repo, run_git)


@pytest.mark.parametrize(
    "member",
    [
        pytest.param("[tool.ruff]\n", id="no [project] name"),
        pytest.param("[project\n", id="unreadable"),
        pytest.param(X_Y, id="no package directory"),
    ],
)
def test_leaving_out_a_member_without_product_code_works_as_written(
    git_repo: Path, commit_all: Callable[..., None], member: str
) -> None:
    write_files(git_repo, {**ROOT_OK, "tools/x/pyproject.toml": member})
    commit_all(git_repo)
    variables = resolve_variables(git_repo)

    with pytest.raises(KitError) as caught:
        init_repository(git_repo, stacks=[ROOT, TOOLS_X], variables=variables)
    assert str(caught.value).endswith(leave_out("tools/x"))

    init_repository(git_repo, stacks=[ROOT], variables=variables)

    assert source_roots(git_repo) == ["src/acme"]


def test_the_package_default_applies_to_the_agnostic_stack_too(
    git_repo: Path,
    commit_all: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_files(git_repo, ACME)
    commit_all(git_repo)
    monkeypatch.chdir(git_repo)

    assert main(["init", "--stack", "agnostic", "--repository", "octo/acme-api"]) == 0

    assert "for acme-api (package acme).\n" in capsys.readouterr().out


def test_an_existing_stack_of_another_kind_follows_the_way_out_the_error_names(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
    init_cli: Callable[..., tuple[int, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    give_agnostic_a_source_root(monkeypatch)
    write_files(git_repo, {"app.py": "pass\n"})
    commit_all(git_repo)

    code, error = init_cli("--stack", "agnostic")
    assert (code, error) == (
        2,
        "rapid-ship: init wrote nothing: the agnostic stack in . has no source root: init looked "
        "in src and found no tracked file. Move the product code into src/ and commit it, then "
        "run init again. If the root holds no product code, replace --stack agnostic with a "
        "--stack option for each stack that has product code, or with --stack agnostic when none "
        "has.\n",
    )

    (git_repo / "src").mkdir()
    run_git(git_repo, "mv", "app.py", "src/app.py")
    commit_all(git_repo, "Move the product code into src/")
    assert init_cli("--stack", "agnostic") == (0, "")

    assert source_roots(git_repo) == ["src"]
    assert not [key for key in read_lock(git_repo).variables if key.startswith("source_root:")]
    assert classify(git_repo).strict_ok


def test_the_error_of_a_stack_of_another_kind_in_a_directory_names_that_directory() -> None:
    stack = ProjectStack("agnostic", "frontend")

    error = no_source_root(stack, [stack, ROOT], ["frontend/src"])

    assert str(error) == (
        "init wrote nothing: the agnostic stack in frontend has no source root: init looked in "
        "frontend/src and found no tracked file. Move the product code into frontend/src/ and "
        "commit it, then run init again. If frontend holds no product code, run init without "
        "--stack agnostic=frontend."
    )
