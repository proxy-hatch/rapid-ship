"""Offline: sync's migrations against fixture repositories and a recording PR opener."""

import functools
from collections.abc import Callable
from pathlib import Path

import pytest
from test_kit_sync import PullRequests

from devctl.check.map import root_link_errors
from devctl.settings import REMOVED_TABLES, SettingsError, load_project
from rapid_ship.cli import main
from rapid_ship.kit.migrations import MIGRATIONS, ROOT_ROWS, migration_body, pending
from rapid_ship.kit.pull_request import push_and_open_pull_request
from rapid_ship.kit.sync import sync_repository
from rapid_ship.kit.templates import KitError, KitRefusal, installed_version, packaged_templates

PROJECT = ".rapid-ship/project.toml"
MIGRATE = "rapid-ship/kit-migrate-9.9.9"

# Plan 3's seed, with live [linear], [dispatch] and [release] tables
# (git show 247f9db:rapid_ship/templates/python/.rapid-ship/project.toml), rendered for
# octo/demo-app.
OLD_SEED = """\
# rapid-ship project settings. No secrets. Changes need the owner (Protected set).
stack = "python"

# rs-setup records the Worker and Reviewer Agents: a Harness (claude, codex or agy)
# and an exact model ID each, used as named.
# [agents.worker]
# harness = "agy"
# model = "gemini-3.8-flash-high"
#
# [agents.reviewer]
# harness = "claude"
# model = "<exact model ID>"

[github]
repository = "octo/demo-app"
worker_app_id = 0    # rapid-ship app records the App IDs
reviewer_app_id = 0

[kit]
optional = []        # opt-in Kit skills, such as "rs-contribute"
# Kit files or directories the project owns instead. rapid-ship sync never
# creates, replaces, deletes or reports them. A skill directory covers its
# .claude/skills link.
exclude = []

[linear]
team_id = ""
project_id = ""

[dispatch]
max_workers = 5
attempt_limit = 3
worktree_root = "../demo-app.worktrees"

[map]
source_roots = ["src/demo_app"]
unguided = []
# Directories whose AGENTS.md files are template content, not guides. The map
# check ignores those files: it requires none and checks no links in them.
exclude = []

[tests]
unit = ["tests/unit/**"]   # every other test counts as behavioural

[release]
method = "none"   # github-deployments, tags or none
"""

# The root guide that v0.1.0 seeds (git show v0.1.0:rapid_ship/templates/common/AGENTS.md),
# rendered for demo-app. A backslash joins a long line to the next.
OLD_GUIDE = """\
# demo-app

demo-app is this repository's product. Replace this paragraph with one that says what it does \
and who uses it.

## Commands

- `./devctl check` runs every check CI requires. Add `--tier fast` for the quick subset.
- `./devctl doctor` reports missing tools, settings and GitHub configuration.
- `./devctl --help` lists the project's own verbs.

## Find the change

| Work | Start here |
| --- | --- |
| What a feature does, where it starts and how to reproduce it | [Feature \
map](docs/features/README.md) |
| The one supported way to do a recurring task | [Patterns](docs/patterns/README.md) |
| Where feature and Pattern files live | [Documentation](docs/AGENTS.md) |
| This project's devctl verbs and check steps | [Tools](tools/AGENTS.md) |

Add a row for each directory guide.

## Rules

- Mark every suppression with `rs-exception: EX-<n>` and list it in \
`.rapid-ship/exceptions.toml`. enforced by: check:exceptions
- Declare each removed test under `Removed tests:` in the PR body, with a reason. enforced by: \
check:diff
- Keep each change inside its task's paths. advisory
- Editing or deleting a Kit-managed file (`kind = "managed"` in `.rapid-ship/kit.lock`) makes it \
this project's own and stops its Kit updates. To change behaviour and keep updates, use \
`tools/devctl/devctl_project/` or the settings in `.rapid-ship/`. To own a Kit file outright, \
list it under `[kit] exclude`. To give one back to the Kit, run `rapid-ship sync --revert \
<path>`. advisory

## Shared language and decisions

- Terms are in `GLOSSARY.md`, and decisions in `docs/adr/`.
- Follow the `rs-writing` skill for prose and the `rs-ponytail` skill for building only what is \
needed.
"""

SEED_IDS = ["0.2.0-remove-dispatch", "0.2.0-remove-linear", "0.2.0-remove-release"]
ROOT_GUIDE_LINKS = next(item for item in MIGRATIONS if item.id == "0.2.0-root-guide-links")
SYNC_BRANCH = "rapid-ship/kit-sync-9.9.9"
NEWER_DEVCTL = {"common/devctl": "#!/bin/sh\necho newer\n"}
FIRST_PR, SECOND_PR = (f"https://github.com/octo/demo-app/pull/{n}" for n in (1, 2))


def write(root: Path, path: str, text: str) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text(text)


def table_section(guide: str) -> str:
    return guide.split("## Find the change\n", 1)[1].split("\n## ", 1)[0]


def cli_sync(monkeypatch: pytest.MonkeyPatch, templates: Path) -> PullRequests:
    """Make rapid-ship sync use templates and record each pull request it opens."""
    pulls = PullRequests()
    monkeypatch.setattr("rapid_ship.kit.templates.packaged_templates", lambda: templates)
    opener = functools.partial(sync_repository, open_pull_request=pulls)
    monkeypatch.setattr("rapid_ship.cli.sync_repository", opener)
    return pulls


def test_plan_3s_seed_loads_after_its_migrations(tmp_path: Path) -> None:
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship" / "project.toml").write_text(OLD_SEED)
    with pytest.raises(SettingsError, match=r"\[dispatch\] was removed"):
        load_project(tmp_path)
    found = pending(tmp_path, ())
    assert [item.migration.id for item in found] == SEED_IDS
    text = found[-1].after
    assert all(not item.migration.applies(text) for item in found)
    assert "[tests]" in text
    assert "[linear]" not in text
    # Each migration starts from the text the one before it left, and the file ends cleanly.
    assert [item.before for item in found[1:]] == [item.after for item in found[:-1]]
    assert text.endswith(
        '\n[tests]\nunit = ["tests/unit/**"]   # every other test counts as behavioural\n'
    )
    (tmp_path / PROJECT).write_text(text)
    assert load_project(tmp_path).repository == "octo/demo-app"


def test_each_migration_id_is_unique_and_names_the_kit_version() -> None:
    ids = [migration.id for migration in MIGRATIONS]
    assert len(ids) == len(set(ids))
    assert all(identifier.startswith("0.2.0-") for identifier in ids)


def test_each_table_devctl_refuses_has_a_migration() -> None:
    removals = [item for item in MIGRATIONS if item.id.startswith("0.2.0-remove-")]
    assert {item.id.removeprefix("0.2.0-remove-") for item in removals} == set(REMOVED_TABLES)
    assert {item.path for item in removals} == {PROJECT}


def test_a_removed_table_keeps_the_comments_above_each_header(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n'
        "\n"
        "# Kept: the comment above a removed header.\n"
        "[linear]\n"
        'team_id = ""\n'
        "\n"
        "[agents.worker]  # a sub-table\n"
        'harness = "agy"\n'
        "# [agents.reviewer] in a comment is not a header\n"
        "\n"
        "# Kept: the comment above the next header.\n"
        "[tests]\n"
        "unit = []\n"
        "\n"
        "[release]\n"
        'method = "none"\n',
    )

    found = pending(tmp_path, ())

    assert [item.migration.id for item in found] == [
        "0.2.0-remove-agents",
        "0.2.0-remove-linear",
        "0.2.0-remove-release",
    ]
    assert found[-1].after == (
        'stack = "python"\n'
        "\n"
        "# Kept: the comment above a removed header.\n"
        "# Kept: the comment above the next header.\n"
        "[tests]\n"
        "unit = []\n"
    )


def test_an_excluded_path_is_never_migrated(tmp_path: Path) -> None:
    write(tmp_path, PROJECT, OLD_SEED)
    write(tmp_path, "AGENTS.md", OLD_GUIDE)

    assert [item.migration.path for item in pending(tmp_path, (".rapid-ship",))] == ["AGENTS.md"]
    assert pending(tmp_path, (PROJECT, "AGENTS.md")) == []


def test_the_root_guide_migration_adds_the_missing_rows(tmp_path: Path) -> None:
    write(tmp_path, "AGENTS.md", OLD_GUIDE)

    [found] = pending(tmp_path, ())

    assert found.migration.id == "0.2.0-root-guide-links"
    assert not found.migration.applies(found.after)
    # Task 9's two rows, README's first, right below the separator: the current seed's table.
    current = (packaged_templates() / "common/AGENTS.md").read_text()
    assert table_section(found.after) == table_section(current)
    readme_only = found.after.replace("| [Architecture](ARCHITECTURE.md) |", "| Architecture |")
    assert found.migration.applies(readme_only)
    added = table_section(found.migration.edit(readme_only))
    assert (added.count("(README.md)"), added.count("(ARCHITECTURE.md)")) == (1, 1)
    without_table = OLD_GUIDE.replace("## Find the change", "## Directory guides")
    assert not found.migration.applies(without_table)


@pytest.mark.parametrize(
    ("readme", "linked"),
    [
        ("| Run it | [README](README.md) |\n", True),
        ("| Run it | [README](./README.md#checks) |\n", True),
        ("| Run it | [README][readme] |\n\n[readme]: README.md\n", True),
        ("| Run it | [readme] |\n\n[readme]: README.md\n", True),
        ("| Run it | README |\n\n[readme]: README.md\n", False),
        ("| Run it | `[README](README.md)` |\n", False),
        ("\n```markdown\n| Run it | [README](README.md) |\n```\n", False),
        ("\n~~~\n[readme]: README.md\n~~~\n", False),
    ],
    ids=[
        "inline",
        "relative-with-fragment",
        "reference",
        "shortcut-reference",
        "unused-definition",
        "code-span",
        "fenced",
        "fenced-definition",
    ],
)
def test_the_root_guide_migration_reads_links_as_map_rule_8_does(
    tmp_path: Path, readme: str, linked: bool
) -> None:
    guide = (
        "# demo-app\n\n## Find the change\n\n| Work | Start here |\n| --- | --- |\n"
        "| The parts | [Architecture](ARCHITECTURE.md) |\n" + readme
    )
    write(tmp_path, "AGENTS.md", guide)
    write(tmp_path, "README.md", "# demo-app\n")
    write(tmp_path, "ARCHITECTURE.md", "# Architecture\n")

    errors = root_link_errors(tmp_path, ["AGENTS.md", "README.md", "ARCHITECTURE.md"])

    unlinked = "AGENTS.md: does not link README.md; add it to the Find the change table"
    assert errors == ([] if linked else [unlinked])
    assert ROOT_GUIDE_LINKS.applies(guide) is not linked


@pytest.mark.parametrize(
    "fenced",
    ["```markdown\n| Work | Start here |\n| --- | --- |\n```\n", "~~~sh\n# a comment\n~~~\n"],
    ids=["example-table", "comment-line"],
)
def test_the_root_guide_migration_skips_fenced_code(tmp_path: Path, fenced: str) -> None:
    table = "| Work | Start here |\n| --- | --- |\n"
    guide = f"# demo-app\n\n## Find the change\n\n{fenced}\n{table}| Tools | [Tools](tools/) |\n"
    write(tmp_path, "AGENTS.md", guide)
    write(tmp_path, "README.md", "# demo-app\n")
    write(tmp_path, "ARCHITECTURE.md", "# Architecture\n")

    [found] = pending(tmp_path, ())
    write(tmp_path, "AGENTS.md", found.after)

    rows = "".join(f"{row}\n" for _, row in ROOT_ROWS)
    assert found.after == guide.replace(f"{table}| Tools", f"{table}{rows}| Tools")
    assert root_link_errors(tmp_path, ["AGENTS.md", "README.md", "ARCHITECTURE.md"]) == []
    assert not found.migration.applies(found.after)


def test_the_migration_body_lists_each_edit_and_its_evidence(tmp_path: Path) -> None:
    write(tmp_path, PROJECT, OLD_SEED)

    body = migration_body(pending(tmp_path, ()), "9.9.9")

    assert body.count(f"- `{PROJECT}`: ") == 3
    assert "Protected" in body
    assert body.split("\n## Evidence\n", 1)[1] == (
        "\n- `rapid-ship sync`: 3 migrations for Kit 9.9.9\n\n"
        "Not covered: sync did not run ./devctl check; CI runs it on this pull request.\n"
    )


def test_the_migration_body_counts_one_migration_in_the_singular(tmp_path: Path) -> None:
    write(tmp_path, "AGENTS.md", OLD_GUIDE)

    body = migration_body(pending(tmp_path, ()), "0.2.0")

    assert "\n- `rapid-ship sync`: 1 migration for Kit 0.2.0\n" in body


def test_in_place_lists_each_migration_and_writes_none(
    git_repo: Path, vendored: Path, commit_all: Callable[..., None]
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)

    result = sync_repository(git_repo, in_place=True, templates_root=vendored, kit_version="9.9.9")

    assert [item.migration.id for item in result.migrations] == SEED_IDS
    assert (git_repo / PROJECT).read_bytes() == OLD_SEED.encode()
    assert (result.migration_branch, result.migration_pull_request) == (None, None)


def test_sync_proposes_the_migrations_on_a_second_branch_and_pr(
    git_repo: Path,
    vendored: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    new = make_templates("new", NEWER_DEVCTL)
    pulls = PullRequests()

    result = sync_repository(
        git_repo, in_place=False, templates_root=new, kit_version="9.9.9", open_pull_request=pulls
    )

    assert [call[:3] for call in pulls.calls] == [
        (SYNC_BRANCH, "main", "Sync rapid-ship Kit to 9.9.9"),
        (MIGRATE, SYNC_BRANCH, "Migrate seeded files for rapid-ship Kit 9.9.9"),
    ]
    body = pulls.calls[1][3]
    for item in result.migrations:
        assert f"- `{PROJECT}`: {item.migration.explanation}" in body
    evidence = body.split("\n## Evidence\n", 1)[1].splitlines()
    assert evidence.index("- `rapid-ship sync`: 3 migrations for Kit 9.9.9") < next(
        index for index, line in enumerate(evidence) if line.startswith("Not covered:")
    )
    assert result.migration_branch == MIGRATE
    assert (result.pull_request, result.migration_pull_request) == (FIRST_PR, SECOND_PR)
    assert run_git(git_repo, "branch", "--show-current").strip() == MIGRATE
    assert run_git(git_repo, "log", "-1", "--format=%s").strip() == (
        "chore: migrate seeded files for rapid-ship Kit 9.9.9"
    )
    assert run_git(git_repo, "rev-parse", "HEAD^") == run_git(git_repo, "rev-parse", SYNC_BRANCH)
    assert run_git(git_repo, "status", "--porcelain") == ""
    assert (git_repo / PROJECT).read_text() == result.migrations[-1].after


def test_migrations_run_when_the_kit_is_otherwise_current(
    git_repo: Path, vendored: Path, commit_all: Callable[..., None], run_git: Callable[..., str]
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    main_head = run_git(git_repo, "rev-parse", "main")
    pulls = PullRequests()

    result = sync_repository(
        git_repo,
        in_place=False,
        templates_root=vendored,
        kit_version="9.9.9",
        open_pull_request=pulls,
    )

    assert (result.changed, result.branch) == (False, None)
    [(branch, base, title, _)] = pulls.calls
    assert (branch, base, title) == (
        MIGRATE,
        "main",
        "Migrate seeded files for rapid-ship Kit 9.9.9",
    )
    assert run_git(git_repo, "branch", "--show-current").strip() == MIGRATE
    assert run_git(git_repo, "rev-parse", "HEAD^") == main_head


def test_an_existing_migration_branch_is_refused_before_any_write(
    git_repo: Path,
    vendored: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    run_git(git_repo, "branch", MIGRATE)
    new = make_templates("new", {"common/devctl": "#!/bin/sh\necho newer\n"})
    pulls = PullRequests()

    with pytest.raises(KitRefusal, match=f"gh pr list --head {MIGRATE}"):
        sync_repository(
            git_repo,
            in_place=False,
            templates_root=new,
            kit_version="9.9.9",
            open_pull_request=pulls,
        )

    assert pulls.calls == []
    assert (git_repo / "devctl").read_text() == "#!/bin/sh\necho devctl\n"
    assert run_git(git_repo, "branch", "--show-current").strip() == "main"
    assert run_git(git_repo, "branch", "--list", "rapid-ship/kit-sync-*") == ""


def test_a_failed_migration_commit_restores_the_file_and_deletes_its_branch(
    git_repo: Path, vendored: Path, commit_all: Callable[..., None], run_git: Callable[..., str]
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    run_git(git_repo, "config", "commit.gpgsign", "true")
    run_git(git_repo, "config", "gpg.program", "false")
    pulls = PullRequests()

    with pytest.raises(KitError) as stopped:
        sync_repository(
            git_repo,
            in_place=False,
            templates_root=vendored,
            kit_version="9.9.9",
            open_pull_request=pulls,
        )

    assert str(stopped.value).endswith(f"back on main, {MIGRATE} deleted")
    assert (git_repo / PROJECT).read_bytes() == OLD_SEED.encode()
    assert run_git(git_repo, "status", "--porcelain", "--untracked-files=all") == ""
    assert run_git(git_repo, "branch", "--show-current").strip() == "main"
    assert run_git(git_repo, "branch", "--list", "rapid-ship/*") == ""
    assert pulls.calls == []


def test_a_failed_migration_after_the_sync_pr_goes_back_to_the_sync_branch(
    git_repo: Path,
    vendored: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    pulls = PullRequests()

    def open_then_break_signing(root: Path, branch: str, base: str, title: str, body: str) -> str:
        # Once the sync commit is made, every later commit fails to sign.
        run_git(root, "config", "commit.gpgsign", "true")
        run_git(root, "config", "gpg.program", "false")
        return pulls(root, branch, base, title, body)

    with pytest.raises(KitError) as stopped:
        sync_repository(
            git_repo,
            in_place=False,
            templates_root=make_templates("new", NEWER_DEVCTL),
            kit_version="9.9.9",
            open_pull_request=open_then_break_signing,
        )

    assert str(stopped.value).endswith(
        f"back on {SYNC_BRANCH}, {MIGRATE} deleted; the sync pull request {FIRST_PR} is open"
    )
    assert [call[0] for call in pulls.calls] == [SYNC_BRANCH]
    assert run_git(git_repo, "branch", "--show-current").strip() == SYNC_BRANCH
    assert run_git(git_repo, "branch", "--list", MIGRATE) == ""
    assert run_git(git_repo, "log", "-1", "--format=%s").strip() == (
        "chore: sync rapid-ship Kit to 9.9.9"
    )
    assert (git_repo / PROJECT).read_bytes() == OLD_SEED.encode()
    assert run_git(git_repo, "status", "--porcelain", "--untracked-files=all") == ""


def test_a_failed_migration_push_names_the_migration_commit_and_the_sync_pr(
    git_repo: Path,
    vendored: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    pulls = PullRequests()

    def record_then_push(root: Path, branch: str, base: str, title: str, body: str) -> str:
        if not pulls.calls:
            return pulls(root, branch, base, title, body)
        # git push fails: the repository has no origin.
        return push_and_open_pull_request(root, branch, base, title, body)

    with pytest.raises(KitError) as stopped:
        sync_repository(
            git_repo,
            in_place=False,
            templates_root=make_templates("new", NEWER_DEVCTL),
            kit_version="9.9.9",
            open_pull_request=record_then_push,
        )

    message = str(stopped.value)
    assert message.endswith(
        f"; the commit is on the local branch {MIGRATE}; the sync pull request {FIRST_PR} is open"
    )
    assert "sync commit" not in message
    assert run_git(git_repo, "branch", "--show-current").strip() == MIGRATE
    assert run_git(git_repo, "log", "-1", "--format=%s").strip() == (
        "chore: migrate seeded files for rapid-ship Kit 9.9.9"
    )


def test_rapid_ship_sync_in_place_exits_1_and_lists_each_migration(
    git_repo: Path,
    vendored: Path,
    commit_all: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    monkeypatch.setattr("rapid_ship.kit.templates.packaged_templates", lambda: vendored)
    monkeypatch.chdir(git_repo)

    assert main(["sync", "--in-place"]) == 1

    out = capsys.readouterr().out
    listed = [line for line in out.splitlines() if line.startswith("migration ")]
    assert [line.split(": ", 2)[:2] for line in listed] == [
        [f"migration {identifier}", PROJECT] for identifier in SEED_IDS
    ]
    assert f"--- a/{PROJECT}\n+++ b/{PROJECT}\n" in out
    assert "\n-[dispatch]\n" in out
    assert "Kit is current" not in out
    assert out.endswith("make each edit by hand.\n")
    assert (git_repo / PROJECT).read_bytes() == OLD_SEED.encode()


def test_rapid_ship_sync_prints_the_sync_and_the_migration_pull_requests(
    git_repo: Path,
    vendored: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    commit_all(git_repo)
    cli_sync(monkeypatch, make_templates("new", NEWER_DEVCTL))
    monkeypatch.chdir(git_repo)

    assert main(["sync"]) == 0

    out = capsys.readouterr().out
    version = installed_version()
    assert f"Opened {FIRST_PR} on rapid-ship/kit-sync-{version}.\n" in out
    assert out.endswith(f"Opened {SECOND_PR} on rapid-ship/kit-migrate-{version}.\n")


def test_a_sync_that_conflicts_and_migrates_does_not_say_nothing_was_written(
    git_repo: Path,
    vendored: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write(git_repo, PROJECT, OLD_SEED)
    write(git_repo, "docs/guide.md", "ours\n")
    commit_all(git_repo)
    pulls = cli_sync(monkeypatch, make_templates("new", {"common/docs/guide.md": "Kit\n"}))
    monkeypatch.chdir(git_repo)

    assert main(["sync"]) == 1

    out = capsys.readouterr().out
    migrate = f"rapid-ship/kit-migrate-{installed_version()}"
    assert "Conflict: docs/guide.md: exists and is not managed" in out
    assert "Nothing was written" not in out
    assert out.endswith(f"Opened {FIRST_PR} on {migrate}.\n")
    assert [call[0] for call in pulls.calls] == [migrate]
