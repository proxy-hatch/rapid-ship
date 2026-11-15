"""rapid-ship init's template variables and the project name and package defaults (offline)."""

from collections.abc import Callable
from pathlib import Path

import pytest

from rapid_ship.kit.init import _github_repository, resolve_variables
from rapid_ship.kit.templates import KitError


def test_variables_default_from_the_directory(tmp_path: Path) -> None:
    assert resolve_variables(tmp_path / "Rapid-Ship.app") == {
        "project_name": "Rapid-Ship.app",
        "package": "rapid_ship_app",
        "owner": "",
        "repository": "",
    }


@pytest.mark.parametrize(
    "options",
    [
        {"name": "my project"},
        {"package": "class"},
        {"package": "3d"},
        {"owner": "-octo"},
        {"owner": 'octo"x'},
        {"owner": "o" * 40},
        {"repository": "octo"},
        {"repository": "octo/demo\nx"},
        {"repository": "octo/."},
        {"repository": "octo/.."},
    ],
)
def test_invalid_variables_are_refused(tmp_path: Path, options: dict[str, str]) -> None:
    with pytest.raises(KitError):
        resolve_variables(tmp_path / "demo", **options)


def test_variables_default_from_a_relative_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "demo-app").mkdir()
    monkeypatch.chdir(tmp_path / "demo-app")

    assert resolve_variables(Path())["project_name"] == "demo-app"


def test_explicit_variables_replace_the_defaults(tmp_path: Path) -> None:
    variables = resolve_variables(
        tmp_path / "demo",
        name="my.app",
        package="my_pkg",
        owner="octo-cat",
        repository="octo-cat/my.app",
    )

    assert variables == {
        "project_name": "my.app",
        "package": "my_pkg",
        "owner": "octo-cat",
        "repository": "octo-cat/my.app",
    }


def test_an_invalid_value_is_named_with_its_option(tmp_path: Path) -> None:
    with pytest.raises(KitError, match="owner '-x' is not a GitHub login; check --owner"):
        resolve_variables(tmp_path / "demo", owner="-x")


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("git@github.com:octo/Widget.git", "Widget"),
        ("git@github.com:octo/widget", "widget"),
        ("github.com:octo/widget.git", "widget"),
        ("https://github.com/octo/widget", "widget"),
        ("https://github.com/octo/widget.git", "widget"),
        ("http://github.com/octo/widget.git", "widget"),
        ("https://octo@github.com/octo/widget", "widget"),
        ("https://x-access-token:SECRET@github.com/octo/widget.git", "widget"),
        ("ssh://git@github.com/octo/widget.git", "widget"),
        ("https://github.com/octo/widget/", "widget"),
        ("https://github.com/octo/widget.git/", "widget"),
        ("https://GitHub.COM/octo/widget.git", "widget"),
        ("git@github.com:octo/my.app.git", "my.app"),
        ("https://github.com/octo/_bad", "_bad"),
    ],
)
def test_a_github_remote_url_gives_its_repository_name(url: str, name: str) -> None:
    assert _github_repository(url) == f"octo/{name}"


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/octo/widget.git",
        "git@gitlab.com:octo/widget.git",
        "https://github.com.example.invalid/octo/widget.git",
        "https://github.com@example.invalid/octo/widget.git",
        "https://example.invalid/github.com/octo/widget.git",
        "https://github.com/octo",
        "https://github.com/octo/widget/extra",
        "https://github.com/octo/widget?token=SECRET",
        "https://github.com/octo/.git",
        "/srv/git/widget.git",
        "../widget",
        "",
    ],
)
def test_another_host_or_an_unparsable_url_gives_no_name(url: str) -> None:
    assert _github_repository(url) is None


def test_variables_default_to_the_origin_repository_name(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    run_git(git_repo, "remote", "add", "origin", "git@github.com:octo/Widget.git")

    variables = resolve_variables(git_repo)

    assert variables["project_name"] == "Widget"
    assert variables["package"] == "widget"
    assert variables["repository"] == "octo/Widget"
    assert variables["owner"] == ""


def test_the_repository_option_beats_the_origin_remote(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    run_git(git_repo, "remote", "add", "origin", "https://github.com/octo/from-origin.git")

    variables = resolve_variables(git_repo, repository="octo/from-option")

    assert variables["project_name"] == "from-option"


def test_the_name_option_beats_the_repository_and_the_origin(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    run_git(git_repo, "remote", "add", "origin", "https://github.com/octo/from-origin.git")

    variables = resolve_variables(git_repo, name="mine", repository="octo/from-option")

    assert variables["project_name"] == "mine"


def test_a_remote_that_is_not_origin_does_not_name_the_project(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    run_git(git_repo, "remote", "add", "upstream", "https://github.com/octo/upstream-name.git")

    assert resolve_variables(git_repo)["project_name"] == "project"
    assert resolve_variables(git_repo)["repository"] == ""


def test_a_non_github_origin_falls_back_to_the_checkout_directory(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    run_git(git_repo, "remote", "add", "origin", "https://gitlab.com/octo/widget.git")

    assert resolve_variables(git_repo)["project_name"] == "project"
    assert resolve_variables(git_repo)["repository"] == ""


def test_a_repository_without_a_remote_uses_its_directory_name(git_repo: Path) -> None:
    assert resolve_variables(git_repo)["project_name"] == "project"
    assert resolve_variables(git_repo)["repository"] == ""


def test_a_linked_worktree_without_a_remote_uses_the_main_checkout_name(
    git_repo: Path, commit_all: Callable[..., None], run_git: Callable[..., str], tmp_path: Path
) -> None:
    commit_all(git_repo)
    linked = tmp_path / "random-worktree-name"
    run_git(git_repo, "worktree", "add", "-q", str(linked), "-b", "feature")

    assert resolve_variables(linked)["project_name"] == "project"


def test_a_linked_worktree_shares_the_origin_name(
    git_repo: Path, commit_all: Callable[..., None], run_git: Callable[..., str], tmp_path: Path
) -> None:
    run_git(git_repo, "remote", "add", "origin", "https://github.com/octo/Widget.git")
    commit_all(git_repo)
    linked = tmp_path / "random-worktree-name"
    run_git(git_repo, "worktree", "add", "-q", str(linked), "-b", "feature")

    assert resolve_variables(linked)["project_name"] == "Widget"


def test_an_invalid_origin_name_is_named_without_the_url_or_its_token(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    run_git(
        git_repo, "remote", "add", "origin", "https://x-access-token:SECRET@github.com/octo/_bad"
    )

    with pytest.raises(KitError, match="_bad") as raised:
        resolve_variables(git_repo)

    assert "SECRET" not in str(raised.value)
    assert "github.com" not in str(raised.value)


def test_a_repository_name_that_is_not_a_project_name_needs_the_name_option(tmp_path: Path) -> None:
    with pytest.raises(KitError, match=r"project name '\.github' .*check --name"):
        resolve_variables(tmp_path / "demo", repository="octo/.github")

    variables = resolve_variables(tmp_path / "demo", name="demo", repository="octo/.github")

    assert variables["repository"] == "octo/.github"


def project_with(tmp_path: Path, text: str | bytes) -> Path:
    root = tmp_path / "demo"
    root.mkdir()
    (root / "pyproject.toml").write_bytes(text.encode() if isinstance(text, str) else text)
    return root


def test_the_package_defaults_to_the_root_projects_name(tmp_path: Path) -> None:
    root = project_with(tmp_path, '[project]\nname = "acme"\n')

    variables = resolve_variables(root, repository="octo/acme-api")

    assert (variables["project_name"], variables["package"]) == ("acme-api", "acme")


@pytest.mark.parametrize(
    ("name", "package"),
    [
        ("Acme", "acme"),
        ("acme-api", "acme_api"),
        ("Foo.Bar-baz__qux", "foo_bar_baz_qux"),
        ("a--b..c_-d", "a_b_c_d"),
    ],
)
def test_the_root_projects_name_becomes_an_import_name(
    tmp_path: Path, name: str, package: str
) -> None:
    root = project_with(tmp_path, f'[project]\nname = "{name}"\n')

    assert resolve_variables(root)["package"] == package


def test_the_package_option_beats_the_root_projects_name(tmp_path: Path) -> None:
    root = project_with(tmp_path, '[project]\nname = "acme"\n')

    assert resolve_variables(root, package="my_pkg")["package"] == "my_pkg"


@pytest.mark.parametrize(
    "text",
    ["", "[tool.ruff]\n", "[project]\n", '[project]\nname = ""\n', "[project]\nname = 3\n"],
)
def test_a_root_project_without_a_name_keeps_the_project_name_default(
    tmp_path: Path, text: str
) -> None:
    root = project_with(tmp_path, text)

    assert resolve_variables(root, name="demo-app")["package"] == "demo_app"


@pytest.mark.parametrize("content", [b"[project\n", b"\xff\xfe[project]\n"])
def test_an_unreadable_root_pyproject_names_the_file_and_the_way_out(
    tmp_path: Path, content: bytes
) -> None:
    root = project_with(tmp_path, content)

    with pytest.raises(KitError, match=r"cannot read pyproject\.toml \(.+\)\. .*pass --package"):
        resolve_variables(root)

    assert resolve_variables(root, package="my_pkg")["package"] == "my_pkg"


def test_a_root_pyproject_that_is_a_directory_or_a_symlink_is_unreadable(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    (folder / "pyproject.toml").mkdir(parents=True)
    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / "real.toml").write_text('[project]\nname = "acme"\n')
    (linked / "pyproject.toml").symlink_to("real.toml")

    for root in (folder, linked):
        with pytest.raises(KitError, match=r"cannot read pyproject\.toml"):
            resolve_variables(root)


def test_a_root_project_name_that_is_no_package_name_needs_the_package_option(
    tmp_path: Path,
) -> None:
    root = project_with(tmp_path, '[project]\nname = "3d-engine"\n')

    with pytest.raises(
        KitError, match="package '3d_engine' is not a Python package name; check --package"
    ):
        resolve_variables(root)

    assert resolve_variables(root, package="engine3d")["package"] == "engine3d"
