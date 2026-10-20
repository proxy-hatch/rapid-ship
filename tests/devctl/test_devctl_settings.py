"""devctl settings loading, defaults and errors (offline)."""

import json
import re
from pathlib import Path

import pytest

from devctl.settings import (
    EXCEPTIONS,
    PROJECT,
    REMOVED_TABLES,
    App,
    Escalation,
    ProjectSettings,
    SettingsError,
    load_exceptions,
    load_project,
)
from rapid_ship.kit.init import resolve_variables
from rapid_ship.kit.templates import KitError, render_files

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = {"project_name": "demo-app", "package": "demo_app", "owner": "", "repository": ""}
LOADERS = {PROJECT: load_project, EXCEPTIONS: load_exceptions}
SEEDED_KIND = "a pull request that removes a behavioural test"
APPS = (
    '[github]\nrepository = "o/r"\n'
    'worker_app_id = 101\nworker_app_slug = "o-rs-worker"\n'
    'reviewer_app_id = 202\nreviewer_app_slug = "o-rs-reviewer"\n'
)


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_the_seeded_settings_load_with_the_spec_defaults(tmp_path: Path) -> None:
    for template in render_files("python", VARIABLES, ()):
        if template.path.startswith(".rapid-ship/"):
            assert template.content is not None
            write(tmp_path, template.path, template.content.decode())

    project = load_project(tmp_path)

    assert project == ProjectSettings(
        stack="python",
        repository=None,
        code_owner=None,  # init ran without --owner, so the seed holds code_owner = ""
        worker_app=None,
        reviewer_app=None,
        escalation=Escalation(every_pr=True, kinds=(SEEDED_KIND,), revision_rounds=3),
        optional_skills=(),
        excluded=(),
        source_roots=("src/demo_app",),
        unguided=(),
        map_exclude=(),
        unit_tests=("tests/unit/**",),
    )
    assert not project.agent_identity
    assert load_exceptions(tmp_path) == []
    assert not (tmp_path / ".rapid-ship/gate.toml").exists()


def test_absent_keys_take_their_defaults(tmp_path: Path) -> None:
    write(tmp_path, PROJECT, 'stack = "agnostic"\n')

    project = load_project(tmp_path)

    assert project.escalation == Escalation(every_pr=True, kinds=(), revision_rounds=3)
    assert project.unit_tests == ("tests/unit/**",)
    assert (project.worker_app, project.reviewer_app, project.agent_identity) == (
        None,
        None,
        False,
    )


# devctl knows nothing about Providers (Spec 1 section 4): a [roster] table left from plan 4 is
# refused whatever it holds.
@pytest.mark.parametrize(
    "roster",
    [
        "[roster]\n",
        '[roster.worker]\nharness = "codex"\nmodel = "m"\n',
        '[roster.reviewer]\nharness = "claude"\nmodel = "claude-opus-5-5"\n',
    ],
)
def test_a_leftover_roster_is_refused_and_names_rs_providers(tmp_path: Path, roster: str) -> None:
    write(tmp_path, PROJECT, 'stack = "python"\n' + roster)

    with pytest.raises(SettingsError) as raised:
        load_project(tmp_path)

    assert str(raised.value) == (
        f"{PROJECT}: [roster] was removed: multi-provider is the optional rs-providers skill, "
        "which writes .rapid-ship/providers.md; delete the table"
    )


def test_both_apps_turn_agent_identity_on(tmp_path: Path) -> None:
    write(tmp_path, PROJECT, 'stack = "python"\n' + APPS)

    project = load_project(tmp_path)

    assert (project.worker_app, project.reviewer_app) == (
        App(101, "o-rs-worker"),
        App(202, "o-rs-reviewer"),
    )
    assert project.agent_identity


@pytest.mark.parametrize("code_owner", ["@octocat", "@Octo-Cat", "@my-org/platform-team"])
def test_a_code_owner_loads_as_codeowners_writes_it(tmp_path: Path, code_owner: str) -> None:
    write(tmp_path, PROJECT, f'stack = "python"\n[github]\ncode_owner = "{code_owner}"\n')

    assert load_project(tmp_path).code_owner == code_owner


@pytest.mark.parametrize("github", ['[github]\ncode_owner = ""\n', "[github]\n", ""])
def test_an_empty_or_absent_code_owner_is_unset(tmp_path: Path, github: str) -> None:
    write(tmp_path, PROJECT, 'stack = "python"\n' + github)

    assert load_project(tmp_path).code_owner is None


@pytest.mark.parametrize(
    "value", ['"octocat"', '"@"', '"@org/"', '"@-bad"', '"@a/b/c"', '"@octocat "', "7"]
)
def test_an_invalid_code_owner_names_the_file_the_key_and_both_forms(
    tmp_path: Path, value: str
) -> None:
    write(tmp_path, PROJECT, f'stack = "python"\n[github]\ncode_owner = {value}\n')

    with pytest.raises(SettingsError) as raised:
        load_project(tmp_path)

    message = str(raised.value)
    assert message.startswith(PROJECT)
    assert "code_owner" in message
    assert '"@login" or "@organisation/team"' in message


def test_an_escalation_list_for_flight_loads(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n[escalation]\nevery_pr = false\n'
        'kinds = ["a database migration", "a public API change"]\nrevision_rounds = 2\n',
    )

    assert load_project(tmp_path).escalation == Escalation(
        every_pr=False, kinds=("a database migration", "a public API change"), revision_rounds=2
    )


# What replaced each removed table (Spec 1 section 4), written out so the test does not compare
# the code with itself.
REPLACED_BY = {
    "agents": "rs-providers",
    "dispatch": "no longer starts Workers",
    "linear": "never talks to the issue tracker",
    "release": "Spec 3",
    "roster": "rs-providers",
}


def test_every_removed_table_is_tested() -> None:
    assert sorted(REMOVED_TABLES) == sorted(REPLACED_BY)


def test_the_dispatch_message_claims_no_worker_cap() -> None:
    # rapid-ship takes no notice of how many Sessions run (ADR 0004), so nothing caps Workers.
    assert "cap" not in REMOVED_TABLES["dispatch"]


def test_the_agents_message_points_at_no_roster_table() -> None:
    # devctl reads no [roster] table, so the message must not send the owner to one.
    assert "[roster" not in REMOVED_TABLES["agents"]


@pytest.mark.parametrize(("table", "replacement"), sorted(REPLACED_BY.items()))
def test_a_removed_table_names_what_replaced_it(
    tmp_path: Path, table: str, replacement: str
) -> None:
    write(tmp_path, PROJECT, f'stack = "python"\n[{table}]\n')

    with pytest.raises(SettingsError) as raised:
        load_project(tmp_path)

    message = str(raised.value)
    assert message.startswith(f"{PROJECT}: [{table}] was removed: ")
    assert replacement in message


def test_kit_exclude_is_loaded_and_normalised(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n[kit]\n'
        'exclude = ["devctl", "tools/devctl/", "./.agents/skills/rs-tdd"]\n',
    )

    assert load_project(tmp_path).excluded == ("devctl", "tools/devctl", ".agents/skills/rs-tdd")


def test_map_exclude_is_loaded_and_normalised(tmp_path: Path) -> None:
    write(
        tmp_path,
        PROJECT,
        'stack = "python"\n[map]\nexclude = ["pkg/templates/", "./other/dir"]\n',
    )

    assert load_project(tmp_path).map_exclude == ("pkg/templates", "other/dir")


def test_this_repository_settings_load() -> None:
    project = load_project(ROOT)
    assert (project.repository, project.source_roots) == ("proxy-hatch/rapid-ship", ("rapid_ship",))
    # .github/CODEOWNERS names @proxy-hatch on every line.
    assert project.code_owner == "@proxy-hatch"
    # Nothing is excluded here, so status --strict holds every Kit file to its template.
    assert project.excluded == ()
    assert project.escalation.every_pr  # Walk
    assert not (ROOT / ".rapid-ship/gate.toml").exists()


def test_a_missing_file_is_a_settings_error(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match=re.escape(".rapid-ship/project.toml: missing")):
        load_project(tmp_path)


EXCEPTION = (
    '[[exception]]\nid = "EX-1"\npath = "a.py"\nrule = "S603"\nreason = "r"\nremove_when = "w"\n'
)
NO_REVIEWER_APP = APPS.replace("reviewer_app_id = 202", "reviewer_app_id = 0").replace(
    'reviewer_app_slug = "o-rs-reviewer"', 'reviewer_app_slug = ""'
)


@pytest.mark.parametrize(
    ("relative", "text", "message"),
    [
        (PROJECT, "", "stack: required"),
        (PROJECT, "stack = \n", "project.toml: Invalid value"),
        (PROJECT, 'stack = "rust"\n', "stack: expected python or agnostic"),
        (PROJECT, 'stack = "python"\n[test]\nunit = []\n', "unknown key 'test'"),
        (
            PROJECT,
            'stack = "python"\n[github]\nworker_app_id = true\n',
            "worker_app_id: expected an integer of at least 0",
        ),
        (
            PROJECT,
            'stack = "python"\n[github]\nrepository = "o/r"\nworker_app_id = 101\n',
            "worker_app_id and worker_app_slug go together",
        ),
        (
            PROJECT,
            'stack = "python"\n' + NO_REVIEWER_APP,
            "Agent identity needs both the Worker App and the Reviewer App",
        ),
        (
            PROJECT,
            'stack = "python"\n' + APPS.replace('repository = "o/r"\n', ""),
            "Apps are recorded but repository is not",
        ),
        (
            PROJECT,
            'stack = "python"\n' + APPS.replace('"o-rs-worker"', '"O RS Worker"'),
            "worker_app_slug: expected an App slug",
        ),
        (
            PROJECT,
            'stack = "python"\n[escalation]\nevery_pr = "no"\n',
            "every_pr: expected true or false",
        ),
        (
            PROJECT,
            'stack = "python"\n[escalation]\nrevision_rounds = 0\n',
            "revision_rounds: expected an integer of at least 1",
        ),
        (
            PROJECT,
            'stack = "python"\n[escalation]\nkinds = ["", "x"]\n',
            "kinds: expected a list of non-empty strings",
        ),
        (PROJECT, 'stack = "python"\n[escalation]\nmode = "flight"\n', "unknown key 'mode'"),
        (
            PROJECT,
            'stack = "python"\n[github]\nrepository = "not a repo"\n',
            "repository: expected owner/name",
        ),
        (
            PROJECT,
            'stack = "python"\n[github]\nrepository = "owner/.."\n',
            "repository: expected owner/name",
        ),
        (
            PROJECT,
            'stack = "python"\n[tests]\nunit = "tests/unit/**"\n',
            "unit: expected a list of non-empty strings",
        ),
        (
            PROJECT,
            'stack = "python"\n[kit]\nexclude = "devctl"\n',
            "exclude: expected a list of non-empty strings",
        ),
        (
            PROJECT,
            'stack = "python"\n[kit]\nexclude = ["../outside"]\n',
            "exclude: expected paths inside the repository",
        ),
        (
            PROJECT,
            'stack = "python"\n[kit]\nexclude = ["/etc"]\n',
            "exclude: expected paths inside the repository",
        ),
        (
            PROJECT,
            'stack = "python"\n[map]\nexclude = ["../x"]\n',
            "exclude: expected paths inside the repository",
        ),
        (EXCEPTIONS, EXCEPTION.replace('remove_when = "w"\n', ""), "remove_when: required"),
        (EXCEPTIONS, EXCEPTION + EXCEPTION, "EX-1 is listed twice"),
        (EXCEPTIONS, EXCEPTION.replace("EX-1", "EX-01"), "id: expected EX-<n>"),
        (
            EXCEPTIONS,
            EXCEPTION.replace('"a.py"', '"../a.py"'),
            "path: expected a path inside the repository",
        ),
    ],
)
def test_invalid_settings_raise_settings_error(
    tmp_path: Path, relative: str, text: str, message: str
) -> None:
    write(tmp_path, relative, text)

    with pytest.raises(SettingsError, match=re.escape(message)):
        LOADERS[relative](tmp_path)


@pytest.mark.parametrize(
    ("repository", "valid"),
    [
        ("octo/demo", True),
        ("octo-cat/my.app", True),
        ("octo/.github", True),
        ("octo/a..b", True),
        ("octo", False),
        ("octo/", False),
        ("octo/.", False),
        ("octo/..", False),
        ("-octo/demo", False),
        ("octo/de mo", False),
        ("octo/demo\n", False),
    ],
)
def test_devctl_and_init_accept_the_same_repositories(
    tmp_path: Path, repository: str, valid: bool
) -> None:
    # devctl is vendored into projects without rapid-ship, so it keeps its own copy of the pattern.
    write(tmp_path, PROJECT, f'stack = "python"\n[github]\nrepository = {json.dumps(repository)}\n')

    try:
        load_project(tmp_path)
        devctl_accepts = True
    except SettingsError:
        devctl_accepts = False
    try:
        # --name keeps the repository's own name, such as .github, out of the project-name check.
        resolve_variables(tmp_path, name="demo-app", repository=repository)
        init_accepts = True
    except KitError:
        init_accepts = False

    assert (devctl_accepts, init_accepts) == (valid, valid)
