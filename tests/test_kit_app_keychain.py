"""Offline: rapid-ship app finds each role's App before it creates one, with a simulated Keychain
and GitHub.

For each role, the command uses the App that .rapid-ship/project.toml records, else an App of the
repository's owner whose key the Keychain holds, else it creates one. GitHub shows gh no private
App, even its owner's, so a Keychain item whose App GitHub does not show stops the command before
it creates anything. A key kept under plan 4's item name, which has no App ID, is re-stored under
the new name, and the old item stays. No test reads the real Keychain or contacts GitHub.
"""

import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest
from test_kit_app import (
    OWNER_READS,
    PUBLIC_APPS,
    Captured,
    FakeSecurity,
    FakeStore,
    github_browser,
    reads,
    serve_conversions,
)

from rapid_ship import cli
from rapid_ship.app_keychain import (
    LEGACY_SERVICE,
    AppSetupError,
    MacKeychainStore,
    StoredApp,
    keychain_service,
)
from rapid_ship.github_app import recorded_apps, run_app

ROLES = ("worker", "reviewer")
# The owner's private Apps, as OWNER_READS has them, and a stand-in for each key: rapid-ship
# never parses a key.
APPS = {"worker": StoredApp(11, "o-rs-worker"), "reviewer": StoredApp(12, "o-rs-reviewer")}
KEYS = {
    role: f"-----BEGIN RSA PRIVATE KEY-----\n{role}\n-----END RSA PRIVATE KEY-----\n".encode()
    for role in ROLES
}
# `security dump-keychain` without -d, in the format of keychain_utilities.c
# print_keychain_item_attributes: an unrelated generic password, an internet password, a Worker
# App's item named by its ID, plan 4's item, a Reviewer App's item, and an item named like
# rapid-ship's whose account is not the App ID in its name.
DUMP = r"""keychain: "/Users/o/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="Wi-Fi"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="home"
    "cdat"<timedate>=0x32303236313031393132303030305A00  "20261019120000Z\000"
    "crtr"<uint32>=<NULL>
    "cusi"<sint32>=<NULL>
    "desc"<blob>="AirPort network password"
    "gena"<blob>=<NULL>
    "icmt"<blob>=<NULL>
    "invi"<sint32>=<NULL>
    "mdat"<timedate>=0x32303236313031393132303030305A00  "20261019120000Z\000"
    "nega"<sint32>=<NULL>
    "prot"<blob>=<NULL>
    "scrp"<sint32>=<NULL>
    "svce"<blob>="Wi-Fi"
    "type"<uint32>=<NULL>
keychain: "/Users/o/Library/Keychains/login.keychain-db"
version: 512
class: "inet"
attributes:
    0x00000007 <blob>="github.com"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="12"
    "atyp"<blob>="dflt"
    "cdat"<timedate>=0x32303236313031393132303030305A00  "20261019120000Z\000"
    "crtr"<uint32>=<NULL>
    "cusi"<sint32>=<NULL>
    "desc"<blob>=<NULL>
    "icmt"<blob>="o-rs-worker"
    "invi"<sint32>=<NULL>
    "mdat"<timedate>=0x32303236313031393132303030305A00  "20261019120000Z\000"
    "nega"<sint32>=<NULL>
    "path"<blob>=<NULL>
    "port"<uint32>=0x00000000
    "prot"<blob>=<NULL>
    "ptcl"<uint32>="htps"
    "scrp"<sint32>=<NULL>
    "sdmn"<blob>=<NULL>
    "srvr"<blob>="github.com"
    "type"<uint32>=<NULL>
keychain: "/Users/o/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="rapid-ship/worker-app/12"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="12"
    "cdat"<timedate>=0x32303236313032303039303030305A00  "20261020090000Z\000"
    "crtr"<uint32>=<NULL>
    "cusi"<sint32>=<NULL>
    "desc"<blob>=<NULL>
    "gena"<blob>=<NULL>
    "icmt"<blob>="o-rs-worker"
    "invi"<sint32>=<NULL>
    "mdat"<timedate>=0x32303236313032303039303030305A00  "20261020090000Z\000"
    "nega"<sint32>=<NULL>
    "prot"<blob>=<NULL>
    "scrp"<sint32>=<NULL>
    "svce"<blob>="rapid-ship/worker-app/12"
    "type"<uint32>=<NULL>
keychain: "/Users/o/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="rapid-ship/worker-app"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="5376519"
    "cdat"<timedate>=0x32303236313031393132303030305A00  "20261019120000Z\000"
    "crtr"<uint32>=<NULL>
    "cusi"<sint32>=<NULL>
    "desc"<blob>=<NULL>
    "gena"<blob>=<NULL>
    "icmt"<blob>="proxy-hatch-rs-worker"
    "invi"<sint32>=<NULL>
    "mdat"<timedate>=0x32303236313031393132303030305A00  "20261019120000Z\000"
    "nega"<sint32>=<NULL>
    "prot"<blob>=<NULL>
    "scrp"<sint32>=<NULL>
    "svce"<blob>="rapid-ship/worker-app"
    "type"<uint32>=<NULL>
keychain: "/Users/o/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="rapid-ship/reviewer-app/13"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="13"
    "cdat"<timedate>=0x32303236313032303039303030305A00  "20261020090000Z\000"
    "crtr"<uint32>=<NULL>
    "cusi"<sint32>=<NULL>
    "desc"<blob>=<NULL>
    "gena"<blob>=<NULL>
    "icmt"<blob>="o-rs-reviewer"
    "invi"<sint32>=<NULL>
    "mdat"<timedate>=0x32303236313032303039303030305A00  "20261020090000Z\000"
    "nega"<sint32>=<NULL>
    "prot"<blob>=<NULL>
    "scrp"<sint32>=<NULL>
    "svce"<blob>="rapid-ship/reviewer-app/13"
    "type"<uint32>=<NULL>
keychain: "/Users/o/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="rapid-ship/worker-app/14"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="15"
    "cdat"<timedate>=0x32303236313032303039303030305A00  "20261020090000Z\000"
    "crtr"<uint32>=<NULL>
    "cusi"<sint32>=<NULL>
    "desc"<blob>=<NULL>
    "gena"<blob>=<NULL>
    "icmt"<blob>="o-rs-worker"
    "invi"<sint32>=<NULL>
    "mdat"<timedate>=0x32303236313032303039303030305A00  "20261020090000Z\000"
    "nega"<sint32>=<NULL>
    "prot"<blob>=<NULL>
    "scrp"<sint32>=<NULL>
    "svce"<blob>="rapid-ship/worker-app/14"
    "type"<uint32>=<NULL>
"""
# GitHub's answers once the owner has made both Apps public.
SHOWN = {**OWNER_READS, **PUBLIC_APPS}
SETTINGS = """[github]
repository = "O/R"
worker_app_id = 11
worker_app_slug = "o-rs-worker"
reviewer_app_id = 0
reviewer_app_slug = ""
"""


def keychain(*, old_names: bool) -> FakeStore:
    """A Keychain with the owner's two Apps, under plan 4's names or under names with App IDs."""
    store = FakeStore()
    for role, app in APPS.items():
        name = LEGACY_SERVICE[role] if old_names else keychain_service(role, app.app_id)
        store.apps[name], store.keys[name] = app, KEYS[role]
    return store


def run(
    store: FakeStore,
    recorded: dict[str, StoredApp],
    log: list[str],
    opened: list[str],
    answers: Mapping[str, object] = OWNER_READS,
) -> int:
    """Run app for o/r with a browser that never calls back, so a wrong create ends in 0.1 s."""
    return run_app(
        "o/r",
        store=store,
        owner_get=reads(answers, log),
        open_browser=opened.append,
        recorded=recorded,
        timeout_seconds=0.1,
    )


def app_reads(log: list[str]) -> list[str]:
    return [path for path in log if path.startswith("apps/")]


def test_the_owners_old_items_are_re_stored_under_the_recorded_app_ids(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The owner's two items from before the rename, in the repository that records their Apps."""
    store = keychain(old_names=True)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, dict(APPS), log, opened) == 0
    assert (opened, app_reads(log)) == ([], [])
    for role, app in APPS.items():
        assert store.apps[keychain_service(role, app.app_id)] == app
        assert store.keys[keychain_service(role, app.app_id)] == KEYS[role]
        assert store.keys[LEGACY_SERVICE[role]] == KEYS[role]  # left in place
    out, err = capsys.readouterr()
    assert (
        "Re-stored the Worker App's key from Keychain item rapid-ship/worker-app as "
        "rapid-ship/worker-app/11. The old item stays; once ./devctl doctor passes, you can "
        "delete it with: security delete-generic-password -s rapid-ship/worker-app\n"
    ) in out
    assert "delete it with: security delete-generic-password -s rapid-ship/reviewer-app\n" in out
    assert "Worker App: ID 11 (o-rs-worker)" in out
    assert "BEGIN" not in out + err
    assert err == ""


def test_a_recorded_app_whose_item_exists_is_used_as_it_is(
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = keychain(old_names=False)
    before = dict(store.apps)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, dict(APPS), log, opened) == 0
    assert (store.apps, opened, app_reads(log)) == (before, [], [])
    out = capsys.readouterr().out
    assert "Reviewer App: ID 12 (o-rs-reviewer)" in out
    assert "Re-stored" not in out
    assert "Record each App's ID" not in out
    assert out.endswith("Both Apps are recorded; ./devctl doctor confirms each installation.\n")


@pytest.mark.parametrize("old_item_app_id", [None, 7])
def test_a_recorded_app_with_no_key_here_says_to_import_one(
    old_item_app_id: int | None, capsys: pytest.CaptureFixture[str]
) -> None:
    """A developer whose repository records the Apps, with no key or another App's old item."""
    store = FakeStore()
    if old_item_app_id is not None:
        for role in ROLES:
            name = LEGACY_SERVICE[role]
            store.apps[name], store.keys[name] = StoredApp(old_item_app_id, "x"), KEYS[role]
    before = dict(store.apps)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, dict(APPS), log, opened) == 1
    assert (store.apps, opened, app_reads(log)) == (before, [], [])
    out, err = capsys.readouterr()
    assert (
        "rapid-ship: .rapid-ship/project.toml records the Worker App 11 (o-rs-worker), and this "
        "machine has no key for it in Keychain item rapid-ship/worker-app/11. Generate a private "
        "key in the App's settings on GitHub, then run rapid-ship app --import-key worker with "
        "the key on stdin\n"
    ) in err
    assert "then run rapid-ship app --import-key reviewer with the key on stdin\n" in err
    assert out == ""


@pytest.mark.parametrize("old_names", [False, True])
def test_without_recorded_apps_the_owners_apps_in_the_keychain_are_used(
    old_names: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """A second repository of the same owner gets no second pair of Apps. GitHub shows these
    Apps to gh because the owner made them public."""
    store = keychain(old_names=old_names)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, {}, log, opened, SHOWN) == 0
    assert opened == []
    assert app_reads(log) == ["apps/o-rs-worker", "apps/o-rs-reviewer"]
    for role, app in APPS.items():
        assert store.apps[keychain_service(role, app.app_id)] == app
        assert store.keys[keychain_service(role, app.app_id)] == KEYS[role]
    out = capsys.readouterr().out
    assert ("Re-stored the Worker App's key" in out) is old_names
    assert "Worker App: ID 11 (o-rs-worker)" in out
    assert "Record each App's ID and slug, as printed above" in out


@pytest.mark.parametrize("old_names", [False, True])
def test_without_recorded_apps_a_private_app_in_the_keychain_stops_the_command(
    old_names: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub answers 404 for the owner's private App, as for a deleted one, so rapid-ship cannot
    confirm it. It creates no second pair, and says how to record the Apps."""
    store = keychain(old_names=old_names)
    before = dict(store.apps)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, {}, log, opened) == 1
    assert (store.apps, opened) == (before, [])
    assert app_reads(log) == ["apps/o-rs-worker", "apps/o-rs-reviewer"]
    worker = LEGACY_SERVICE["worker"] if old_names else "rapid-ship/worker-app/11"
    out, err = capsys.readouterr()
    assert (
        f"rapid-ship: Keychain item {worker} holds a key of the Worker App 11 (o-rs-worker), and "
        "GitHub does not show that App to gh, as it shows no private App. To use it, record "
        'worker_app_id = 11 and worker_app_slug = "o-rs-worker" under [github] in '
        ".rapid-ship/project.toml, then run rapid-ship app again. If GitHub has no such App any "
        f"more, delete the item with: security delete-generic-password -s {worker}\n"
    ) in err
    assert 'record reviewer_app_id = 12 and reviewer_app_slug = "o-rs-reviewer" under' in err
    assert out == ""


def test_an_app_github_shows_as_the_owners_is_used_beside_an_item_it_does_not_show() -> None:
    store = keychain(old_names=False)
    gone = "rapid-ship/worker-app/9"  # private or deleted: GitHub's 404 either way
    store.apps[gone], store.keys[gone] = StoredApp(9, "gone-rs-worker"), KEYS["worker"]
    before = dict(store.apps)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, {}, log, opened, SHOWN) == 0
    assert (store.apps, opened) == (before, [])
    assert app_reads(log) == ["apps/gone-rs-worker", "apps/o-rs-worker", "apps/o-rs-reviewer"]


def test_an_item_named_by_app_id_is_used_before_the_old_item_of_the_same_app(
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = keychain(old_names=False)
    for role, app in APPS.items():
        store.apps[LEGACY_SERVICE[role]], store.keys[LEGACY_SERVICE[role]] = app, KEYS[role]
    before = dict(store.apps)
    log: list[str] = []
    assert run(store, {}, log, [], SHOWN) == 0
    assert store.apps == before
    assert app_reads(log) == ["apps/o-rs-worker", "apps/o-rs-reviewer"]
    assert "Re-stored" not in capsys.readouterr().out


def test_keychain_apps_that_github_does_not_show_as_the_owners_are_skipped() -> None:
    """Apps that GitHub shows as another account's are skipped, and the owner's are created."""
    others = {
        "rapid-ship/worker-app/21": StoredApp(21, "u-rs-worker"),  # another account's App
        "rapid-ship/worker-app/23": StoredApp(23, "o-rs-worker"),  # its slug is App 11's now
        "rapid-ship/reviewer-app": StoredApp(31, "u-rs-reviewer"),  # plan 4's item of u's App
    }
    store = FakeStore()
    for name, app in others.items():
        store.apps[name], store.keys[name] = app, KEYS["worker"]
    answers = {
        **SHOWN,
        "apps/u-rs-worker": {"id": 21, "owner": {"login": "u", "id": 6}},
        "apps/u-rs-reviewer": {"id": 31, "owner": {"login": "u", "id": 6}},
    }
    log: list[str] = []
    captured: Captured = []
    with serve_conversions() as conversions:
        code = run_app(
            "o/r",
            store=store,
            owner_get=reads(answers, log),
            open_browser=github_browser(captured),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 0
    assert app_reads(log) == ["apps/u-rs-worker", "apps/o-rs-worker", "apps/u-rs-reviewer"]
    assert [manifest["name"] for _, manifest in captured] == ["o-rs-worker", "o-rs-reviewer"]
    assert sorted(set(store.apps) - set(others)) == [
        "rapid-ship/reviewer-app/12",
        "rapid-ship/worker-app/11",
    ]
    assert all(store.apps[name] == app for name, app in others.items())


def test_every_read_comes_before_any_change(capsys: pytest.CaptureFixture[str]) -> None:
    """An unusable GitHub record of the Reviewer App stops the command before the Worker App's
    key is re-stored and before any browser opens."""
    store = keychain(old_names=True)
    before = dict(store.apps)
    answers = {**SHOWN, "apps/o-rs-reviewer": {"slug": "o-rs-reviewer"}}
    opened: list[str] = []
    code = run_app(
        "o/r",
        store=store,
        owner_get=reads(answers),
        open_browser=opened.append,
        timeout_seconds=0.1,
    )
    assert code == 2
    assert (store.apps, opened) == (before, [])
    assert capsys.readouterr().err == (
        "rapid-ship: GitHub's record of the App o-rs-reviewer has no App ID or no owner ID\n"
    )


@pytest.mark.parametrize("reviewer_recorded", [False, True])
def test_an_old_key_that_cannot_be_read_stops_the_command_before_any_app_is_created(
    reviewer_recorded: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """The Worker App must be created, and the Reviewer App's plan 4 item holds no key. The key
    is read before the browser opens, so no App exists when the command stops."""
    store = FakeStore()
    store.apps[LEGACY_SERVICE["reviewer"]] = APPS["reviewer"]  # no key in the item
    before = dict(store.apps)
    recorded = {"reviewer": APPS["reviewer"]} if reviewer_recorded else {}
    opened: list[str] = []
    assert run(store, recorded, [], opened, SHOWN) == 2
    assert (store.apps, opened) == (before, [])
    err = capsys.readouterr().err
    assert err == "rapid-ship: Keychain item rapid-ship/reviewer-app not found\n"


def test_re_storing_through_security_passes_the_key_on_stdin_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    security = FakeSecurity()
    for role, app in APPS.items():
        item = {"-a": str(app.app_id), "-j": app.slug, "-X": KEYS[role].hex()}
        security.items[LEGACY_SERVICE[role]] = item
    opened: list[str] = []
    code = run_app(
        "o/r",
        store=MacKeychainStore(run=security),
        owner_get=reads(SHOWN),
        open_browser=opened.append,
        timeout_seconds=0.1,
    )
    assert code == 0
    assert opened == []
    for role, app in APPS.items():
        new = keychain_service(role, app.app_id)
        assert security.items[new] == security.items[LEGACY_SERVICE[role]]
    assert ["security", "dump-keychain"] in security.argvs
    keys = [KEYS[role].hex() for role in ROLES]
    assert not [arg for argv in security.argvs for arg in argv if any(k in arg for k in keys)]
    assert len(security.inputs) == 2  # one `security -i` add for each role
    out, err = capsys.readouterr()
    assert "BEGIN" not in out + err


def test_listed_reads_attributes_only_and_keeps_the_roles_items_named_by_app_id() -> None:
    argvs: list[list[str]] = []

    def dump(argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        argvs.append(argv)
        return subprocess.CompletedProcess(argv, 0, DUMP, "")

    store = MacKeychainStore(run=dump)
    assert store.listed("worker") == [StoredApp(12, "o-rs-worker")]
    assert store.listed("reviewer") == [StoredApp(13, "o-rs-reviewer")]
    assert argvs == [["security", "dump-keychain"]] * 2


def test_listed_reports_a_dump_that_failed_without_its_output() -> None:
    def failed(argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, DUMP, "security: something went wrong")

    with pytest.raises(AppSetupError) as caught:
        MacKeychainStore(run=failed).listed("worker")
    assert str(caught.value) == "could not list the Keychain's items"


def test_read_key_returns_the_key_and_never_reports_it() -> None:
    security = FakeSecurity()
    item = {"-a": "11", "-j": "o-rs-worker", "-X": KEYS["worker"].hex()}
    security.items["rapid-ship/worker-app"] = item
    security.items["not-a-key"] = {"-a": "11", "-j": "s", "-X": b"hunter2".hex()}
    store = MacKeychainStore(run=security)
    assert store.read_key("rapid-ship/worker-app") == KEYS["worker"]
    assert security.argvs == [
        ["security", "find-generic-password", "-s", "rapid-ship/worker-app", "-w"]
    ]
    with pytest.raises(AppSetupError) as missing:
        store.read_key("rapid-ship/reviewer-app")
    assert str(missing.value) == "Keychain item rapid-ship/reviewer-app not found"
    with pytest.raises(AppSetupError) as caught:
        store.read_key("not-a-key")
    assert str(caught.value) == "Keychain item not-a-key holds no PEM private key"


def write_settings(root: Path, text: str) -> None:
    (root / ".rapid-ship").mkdir(exist_ok=True)
    (root / ".rapid-ship" / "project.toml").write_text(text)


def test_recorded_apps_are_those_of_the_target_repository(tmp_path: Path) -> None:
    assert recorded_apps(tmp_path, "o/r") == {}  # no settings file
    write_settings(tmp_path, SETTINGS)
    assert recorded_apps(tmp_path, "o/r") == {"worker": StoredApp(11, "o-rs-worker")}
    assert recorded_apps(tmp_path, "o/other") == {}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (SETTINGS.replace("11", "-1"), "[github] worker_app_id and worker_app_slug must record"),
        (SETTINGS.replace('"o-rs-worker"', '"O_RS"'), "[github] worker_app_id and"),
        (SETTINGS.replace("reviewer_app_id = 0", "reviewer_app_id = 12"), "reviewer_app_slug"),
        (SETTINGS.replace("[github]", "[github"), "is not valid TOML"),
    ],
    ids=["negative ID", "bad slug", "ID without slug", "not TOML"],
)
def test_recorded_apps_refuses_settings_it_cannot_use(
    tmp_path: Path, text: str, message: str
) -> None:
    write_settings(tmp_path, text)
    with pytest.raises(AppSetupError) as caught:
        recorded_apps(tmp_path, "o/r")
    assert str(caught.value).startswith(".rapid-ship/project.toml")
    assert message in str(caught.value)


def test_cli_app_passes_the_apps_that_the_work_tree_records(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[object] = []

    def record(repository: str, **kwargs: object) -> int:
        calls.append(kwargs["recorded"])
        return 0

    monkeypatch.setattr(cli, "run_app", record)
    write_settings(git_repo, SETTINGS)
    (git_repo / "sub").mkdir()
    monkeypatch.chdir(git_repo / "sub")
    assert cli.main(["app", "--repository", "o/r"]) == 0
    assert calls == [{"worker": StoredApp(11, "o-rs-worker")}]
    write_settings(git_repo, "[github")
    assert cli.main(["app", "--repository", "o/r"]) == 2
    assert len(calls) == 1
    assert "rapid-ship: .rapid-ship/project.toml is not valid TOML" in capsys.readouterr().err
