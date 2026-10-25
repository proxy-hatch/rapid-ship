"""Offline: rapid-ship app finds each role's App before it creates one, with a simulated Keychain
and GitHub.

For each role, the command uses the App that .rapid-ship/project.toml records, else an App of the
repository's owner whose key the Keychain holds, else it creates one: Spec 1 section 3,
`rapid-ship app`. No test reads the real Keychain or contacts GitHub.
"""

import html
import subprocess
import webbrowser
from collections.abc import Mapping
from functools import partial
from pathlib import Path

import pytest
from test_kit_app import (
    ORG_ADMIN,
    OWNER_READS,
    PUBLIC_APPS,
    Captured,
    FakeConversions,
    FakeSecurity,
    FakeStore,
    github_browser,
    reads,
    rsa_key,
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
# The owner's private Apps, as OWNER_READS has them, and a stand-in for each key, for tests that
# never sign a token with it; tests that do use rsa_key.
APPS = {"worker": StoredApp(11, "o-rs-worker"), "reviewer": StoredApp(12, "o-rs-reviewer")}
KEYS = {
    role: f"-----BEGIN RSA PRIVATE KEY-----\n{role}\n-----END RSA PRIVATE KEY-----\n".encode()
    for role in ROLES
}
# `security dump-keychain` without -d, in the format of keychain_utilities.c
# print_keychain_item_attributes: an unrelated generic password, an internet password, a Worker
# App's item named by its ID, an item under the old name, a Reviewer App's item, and an item
# named like rapid-ship's whose account is not the App ID in its name.
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


# Each account as GET /app shows an App's owner: the user o, and the organisation org.
ACCOUNTS: dict[str, dict[str, object]] = {
    "o": {"login": "o", "id": 1, "type": "User"},
    "org": {"login": "org", "id": 4, "type": "Organization"},
}
# No server listens here, so a test that would contact GitHub's API by mistake fails instead.
NO_API = "http://127.0.0.1:1"


def keychain(*, old_names: bool, keys: Mapping[str, bytes] = KEYS) -> FakeStore:
    """A Keychain with the owner's two Apps, under the old names or under names with App IDs."""
    store = FakeStore()
    for role, app in APPS.items():
        name = LEGACY_SERVICE[role] if old_names else keychain_service(role, app.app_id)
        store.apps[name], store.keys[name] = app, keys[role]
    return store


def keyed_keychain(
    api: FakeConversions, apps: Mapping[str, StoredApp], owner: str, *, old_names: bool = False
) -> FakeStore:
    """A Keychain with each role's App and a real key, which GET /app accepts as owner's App."""
    store = FakeStore()
    for role, app in apps.items():
        name = LEGACY_SERVICE[role] if old_names else keychain_service(role, app.app_id)
        store.apps[name], store.keys[name] = app, rsa_key(f"{owner}/{role}")
        api.register(store.keys[name], app, ACCOUNTS[owner])
    return store


def run(
    store: FakeStore,
    recorded: dict[str, StoredApp],
    log: list[str],
    opened: list[str],
    answers: Mapping[str, object] = OWNER_READS,
    api_url: str = NO_API,
) -> int:
    """Run app for o/r with a browser that never calls back, so a wrong create ends in 0.1 s."""
    return run_app(
        "o/r",
        store=store,
        owner_get=reads(answers, log),
        open_browser=opened.append,
        recorded=recorded,
        api_url=api_url,
        timeout_seconds=0.1,
    )


def app_reads(log: list[str]) -> list[str]:
    return [path for path in log if path.startswith("apps/")]


def test_the_owners_old_items_are_re_stored_under_the_recorded_app_ids(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_no_key_is_re_stored_while_another_recorded_app_has_no_key_here(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Worker App's old item holds its key, and this machine has no Reviewer App key."""
    store = FakeStore()
    old = LEGACY_SERVICE["worker"]
    store.apps[old], store.keys[old] = APPS["worker"], KEYS["worker"]
    before = dict(store.apps)
    log: list[str] = []
    opened: list[str] = []
    assert run(store, dict(APPS), log, opened) == 1
    assert (store.apps, opened, app_reads(log)) == (before, [], [])
    out, err = capsys.readouterr()
    assert err == (
        "rapid-ship: .rapid-ship/project.toml records the Reviewer App 12 (o-rs-reviewer), and "
        "this machine has no key for it in Keychain item rapid-ship/reviewer-app/12. Generate a "
        "private key in the App's settings on GitHub, then run rapid-ship app --import-key "
        "reviewer with the key on stdin\n"
    )
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


@pytest.mark.parametrize(
    ("repository", "old_names"), [("o/r", False), ("o/r", True), ("org/r", False)]
)
def test_without_recorded_apps_a_private_app_is_confirmed_with_its_own_key(
    repository: str, old_names: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """A second repository of the same owner, a user or an organisation, gets no second pair of
    Apps. GitHub shows gh no private App, so GET /app, under a token that the item's key signs,
    tells which account owns it. A member who is not an admin uses the organisation's Apps too.
    Old items, which a user's repository needed, are re-stored under the new name."""
    owner = repository.split("/")[0]
    apps = {role: StoredApp(app.app_id, f"{owner}-rs-{role}") for role, app in APPS.items()}
    log: list[str] = []
    opened: list[str] = []
    with serve_conversions() as api:
        store = keyed_keychain(api, apps, owner, old_names=old_names)
        keys = {role: rsa_key(f"{owner}/{role}") for role in ROLES}
        before = dict(store.apps)
        code = run_app(
            repository,
            store=store,
            owner_get=reads(OWNER_READS, log),
            open_browser=opened.append,
            api_url=api.url,
            timeout_seconds=0.1,
        )
    assert (code, opened) == (0, [])
    assert app_reads(log) == [f"apps/{owner}-rs-worker", f"apps/{owner}-rs-reviewer"]
    assert "user/memberships/orgs/org" not in log
    assert [path for path, _ in api.requests] == ["/app", "/app"]
    for role, app in apps.items():
        assert store.apps[keychain_service(role, app.app_id)] == app
        assert store.keys[keychain_service(role, app.app_id)] == keys[role]
    assert all(store.apps[name] == app for name, app in before.items())  # nothing replaced
    out, err = capsys.readouterr()
    assert err == ""
    assert ("Re-stored the Worker App's key" in out) is old_names
    assert f"Worker App: ID 11 ({owner}-rs-worker)" in out
    owner_id = ACCOUNTS[owner]["id"]
    assert f"suggested_target_id={owner_id}&repository_ids[]=" in out
    assert "Record each App's ID and slug, as printed above" in out
    assert "BEGIN" not in out


@pytest.mark.parametrize(
    ("repository", "holder", "new_page"),
    [
        ("org/r", "o", "https://github.com/organizations/org/settings/apps/new"),
        ("o/r", "org", "https://github.com/settings/apps/new"),
    ],
)
def test_keychain_apps_whose_keys_show_another_accounts_app_are_skipped(
    repository: str, holder: str, new_page: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """An organisation admin who holds the keys of their own Apps, and a developer who holds an
    organisation's. GitHub shows gh neither private App, and GET /app under each item's key names
    another account than the repository's owner. So the owner's Apps are created, the items stay,
    and no message tells the developer to record another account's App."""
    held = {role: StoredApp(app.app_id + 10, f"{holder}-rs-{role}") for role, app in APPS.items()}
    log: list[str] = []
    captured: Captured = []
    with serve_conversions() as api:
        store = keyed_keychain(api, held, holder)
        before = dict(store.apps)
        code = run_app(
            repository,
            store=store,
            owner_get=reads({**OWNER_READS, **ORG_ADMIN}, log),
            open_browser=github_browser(captured),
            api_url=api.url,
            timeout_seconds=10,
        )
    assert code == 0
    assert app_reads(log) == [f"apps/{holder}-rs-worker", f"apps/{holder}-rs-reviewer"]
    assert [path for path, _ in api.requests if path == "/app"] == ["/app", "/app"]
    pages = [html.unescape(action).split("?state=", 1)[0] for action, _ in captured]
    assert pages == [new_page] * 2
    owner = repository.split("/")[0]
    assert [manifest["name"] for _, manifest in captured] == [
        f"{owner}-rs-worker",
        f"{owner}-rs-reviewer",
    ]
    assert sorted(set(store.apps) - set(before)) == [
        "rapid-ship/reviewer-app/12",
        "rapid-ship/worker-app/11",
    ]
    assert all(store.apps[name] == app for name, app in before.items())
    out, err = capsys.readouterr()
    assert err == ""
    assert f"https://github.com/apps/{owner}-rs-worker/installations/new/permissions" in out
    assert "ID 21" not in out
    assert "ID 22" not in out
    assert "BEGIN" not in out


@pytest.mark.parametrize("old_names", [False, True])
@pytest.mark.parametrize("key", ["refused", "unusable"])
def test_without_recorded_apps_a_private_app_in_the_keychain_stops_the_command(
    old_names: bool, key: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub shows gh no private App, and the item's key cannot tell whose App it is: GitHub
    refuses a token that the key signs, as it does once the App or that key is deleted, or the key
    cannot sign one. rapid-ship creates no App beside one that may still exist, and prints no
    [github] lines for an App it could not confirm as the owner's."""
    keys = {role: rsa_key(f"gone/{role}") for role in ROLES} if key == "refused" else KEYS
    reason = {
        "refused": "GitHub returned 401: A JSON web token could not be decoded",
        "unusable": "the key is not a readable, unencrypted PEM private key",
    }[key]
    store = keychain(old_names=old_names, keys=keys)
    before = dict(store.apps)
    log: list[str] = []
    opened: list[str] = []
    with serve_conversions() as api:  # it knows neither key
        assert run(store, {}, log, opened, api_url=api.url) == 1
    assert (store.apps, opened) == (before, [])
    assert app_reads(log) == ["apps/o-rs-worker", "apps/o-rs-reviewer"]
    worker = LEGACY_SERVICE["worker"] if old_names else "rapid-ship/worker-app/11"
    reviewer = LEGACY_SERVICE["reviewer"] if old_names else "rapid-ship/reviewer-app/12"
    out, err = capsys.readouterr()

    def stop(service: str, title: str, role: str) -> str:
        """Deleting the item of an App that still exists would let the next run create a second
        App, so the advice records such an App before the item is deleted."""
        app = APPS[role]
        return (
            f"rapid-ship: Keychain item {service} holds a key of the {title} {app.app_id} "
            f"({app.slug}). GitHub does not show that App to gh, as it shows no private App, and "
            f"the key cannot confirm whose App it is: {reason}. If the App is o's and still "
            "exists, first record its ID and slug under [github] in .rapid-ship/project.toml. "
            "Then, if GitHub no longer has this key, delete the item, generate a new private key "
            f"in the App's settings on GitHub and run rapid-ship app --import-key {role} with the "
            "new key on stdin. If GitHub has no such App any more, delete the item and record "
            f"nothing. Delete the item with: security delete-generic-password -s {service}\n"
        )

    assert err == stop(worker, "Worker App", "worker") + stop(reviewer, "Reviewer App", "reviewer")
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
    others = {
        "rapid-ship/worker-app/21": StoredApp(21, "u-rs-worker"),  # another account's App
        "rapid-ship/worker-app/23": StoredApp(23, "o-rs-worker"),  # its slug is App 11's now
        "rapid-ship/reviewer-app": StoredApp(31, "u-rs-reviewer"),  # the old item of u's App
    }
    store = FakeStore()
    for name, app in others.items():
        store.apps[name], store.keys[name] = app, KEYS["worker"]
    # GitHub's App at App 23's slug is App 11, so App 23 is confirmed with its own key: u's App.
    store.keys["rapid-ship/worker-app/23"] = rsa_key("u/renamed")
    answers = {
        **SHOWN,
        "apps/u-rs-worker": {"id": 21, "owner": {"login": "u", "id": 6}},
        "apps/u-rs-reviewer": {"id": 31, "owner": {"login": "u", "id": 6}},
    }
    log: list[str] = []
    captured: Captured = []
    with serve_conversions() as conversions:
        u = {"login": "u", "id": 6, "type": "User"}
        conversions.register(rsa_key("u/renamed"), StoredApp(23, "u-rs-worker-2"), u)
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
    assert [path for path, _ in conversions.requests if path == "/app"] == ["/app"]
    assert [manifest["name"] for _, manifest in captured] == ["o-rs-worker", "o-rs-reviewer"]
    assert sorted(set(store.apps) - set(others)) == [
        "rapid-ship/reviewer-app/12",
        "rapid-ship/worker-app/11",
    ]
    assert all(store.apps[name] == app for name, app in others.items())


def test_an_item_whose_slug_now_names_another_app_is_confirmed_with_its_own_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The owner renamed private App 23, and another account's public App took its old slug.
    The App that GitHub shows at the item's slug is not the item's App, so it tells nothing about
    App 23: GET /app under the item's key shows App 23 as the owner's, and no App is created."""
    item = keychain_service("worker", 23)
    store = FakeStore()
    store.apps[item] = StoredApp(23, "o-rs-worker")  # the slug when the item was written
    store.keys[item] = rsa_key("o/renamed")
    reviewer = keychain_service("reviewer", 12)
    store.apps[reviewer], store.keys[reviewer] = APPS["reviewer"], KEYS["reviewer"]
    before = dict(store.apps)
    answers = {
        **OWNER_READS,
        "apps/o-rs-worker": {"id": 99, "slug": "o-rs-worker", "owner": {"login": "u", "id": 6}},
        "apps/o-rs-reviewer": PUBLIC_APPS["apps/o-rs-reviewer"],
    }
    log: list[str] = []
    opened: list[str] = []
    with serve_conversions() as api:
        api.register(store.keys[item], StoredApp(23, "o-rs-worker-2"), ACCOUNTS["o"])
        assert run(store, {}, log, opened, answers, api.url) == 0
    assert (store.apps, opened) == (before, [])
    assert app_reads(log) == ["apps/o-rs-worker", "apps/o-rs-reviewer"]
    assert [path for path, _ in api.requests] == ["/app"]
    out, err = capsys.readouterr()
    assert err == ""
    assert "Worker App: ID 23 (o-rs-worker-2)" in out
    assert 'worker_app_slug = "o-rs-worker-2"' in out


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
    """The Worker App must be created, and the Reviewer App's old item holds no key. The key
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


def test_a_recorded_apps_item_that_rapid_ship_did_not_write_is_used_as_it_is(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Items added by hand under the recorded Apps' names, with no account and no comment, beside
    the old items. devctl reads an item by its name alone, so the command uses each item as it
    is and re-stores nothing."""
    security = FakeSecurity()
    for role, app in APPS.items():
        security.items[keychain_service(role, app.app_id)] = {"-X": KEYS[role].hex()}
        old = {"-a": str(app.app_id), "-j": app.slug, "-X": KEYS[role].hex()}
        security.items[LEGACY_SERVICE[role]] = old
    before = {name: dict(item) for name, item in security.items.items()}
    log: list[str] = []
    opened: list[str] = []
    code = run_app(
        "o/r",
        store=MacKeychainStore(run=security),
        owner_get=reads(OWNER_READS, log),
        open_browser=opened.append,
        recorded=dict(APPS),
        api_url=NO_API,
        timeout_seconds=0.1,
    )
    assert code == 0
    assert (security.items, security.inputs, opened, app_reads(log)) == (before, [], [], [])
    out, err = capsys.readouterr()
    assert err == ""
    assert "Re-stored" not in out
    assert out.endswith("Both Apps are recorded; ./devctl doctor confirms each installation.\n")


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


def test_apps_recorded_without_the_repository_are_found_by_their_keys(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """rapid-ship init without --repository seeds repository = "", so IDs recorded under it are
    not the target's. The command finds the Apps by their Keychain items instead, and creates
    none."""
    opened: list[str] = []
    ids = "".join(
        f'{role}_app_id = {app.app_id}\n{role}_app_slug = "{app.slug}"\n'
        for role, app in APPS.items()
    )
    write_settings(git_repo, f'stack = "python"\n[github]\nrepository = ""\n{ids}')
    monkeypatch.chdir(git_repo)
    assert recorded_apps(git_repo, "o/r") == {}
    with serve_conversions() as api:
        store = keyed_keychain(api, APPS, "o")
        monkeypatch.setattr(cli, "MacKeychainStore", lambda: store)
        monkeypatch.setattr(cli, "gh_owner_get", reads(OWNER_READS))
        monkeypatch.setattr(cli, "run_app", partial(run_app, api_url=api.url, timeout_seconds=0.1))
        monkeypatch.setattr(webbrowser, "open", opened.append)
        assert cli.main(["app", "--repository", "o/r"]) == 0
    assert opened == []
    out, err = capsys.readouterr()
    assert err == ""
    assert "Worker App: ID 11 (o-rs-worker)" in out
    assert "Reviewer App: ID 12 (o-rs-reviewer)" in out
    assert out.endswith("./devctl doctor then confirms each installation.\n")
