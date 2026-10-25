"""rapid-ship app: find or create the owner's Worker and Reviewer Apps, and print how to install
them.

`rapid-ship app` in section 3 of docs/superpowers/specs/2026-10-14-kit-and-setup-design.md
says which App the command uses for each role.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from rapid_ship.app_flow import (
    API_URL,
    APP_PERMISSIONS,
    GITHUB_URL,
    MAX_MESSAGE_CHARACTERS,
    TITLES,
    AppOwner,
    CreatedApp,
    KeyRefused,
    OwnedApp,
    app_of_key,
    as_record,
    create_app,
    is_id,
    orphaned,
)
from rapid_ship.app_keychain import (
    LEGACY_SERVICE,
    SLUG,
    AppSetupError,
    KeychainStore,
    StoredApp,
    keychain_service,
    run_command,
)

OwnerGet = Callable[[str], object]
AppOfKey = Callable[[bytes, int], OwnedApp]

_ROLES = ("worker", "reviewer")
_SETTINGS = ".rapid-ship/project.toml"
_GH_TIMEOUT_SECONDS = 60.0
_REPOSITORY = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")
_LOGIN = re.compile(r"[A-Za-z0-9-]+")


class GitHubNotFound(AppSetupError):
    """GitHub answered 404: the owner's gh login sees nothing at the path."""


class _Refused(Exception):
    """The repository cannot take the owner's Apps; the command exits 1."""


def _first_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    return lines[0][:MAX_MESSAGE_CHARACTERS] if lines else f"exit code {result.returncode}"


def gh_owner_get(path: str) -> object:
    """GET path from GitHub's REST API as the owner's gh login, and parse the JSON reply."""
    result = run_command(
        ["gh", "api", "--method", "GET", path], timeout_seconds=_GH_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        # gh prints GitHub's status at the end of its error, as in "gh: Not Found (HTTP 404)".
        error = GitHubNotFound if "(HTTP 404)" in result.stderr else AppSetupError
        raise error(f"gh api {path} failed: {_first_line(result)}")
    try:
        return json.loads(result.stdout)
    except (ValueError, RecursionError):
        raise AppSetupError(f"gh api {path} printed no JSON") from None


def current_repository() -> str:
    """The OWNER/NAME of the GitHub repository that gh finds for the current directory."""
    result = run_command(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        timeout_seconds=_GH_TIMEOUT_SECONDS,
    )
    name = result.stdout.strip()
    if result.returncode != 0 or not name:
        raise AppSetupError(
            f"gh cannot tell this directory's GitHub repository ({_first_line(result)}); "
            "give --repository OWNER/NAME"
        )
    return name


def recorded_apps(root: Path, repository: str) -> dict[str, StoredApp]:
    """The Apps that root's .rapid-ship/project.toml records, when its repository is repository.

    A missing file, or one for another repository, records none. 0 and "" leave a role unset.
    """
    try:
        text = (root / _SETTINGS).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as error:
        raise AppSetupError(f"{_SETTINGS} cannot be read: {type(error).__name__}") from None
    try:
        github = as_record(tomllib.loads(text).get("github"))
    except tomllib.TOMLDecodeError as error:
        raise AppSetupError(f"{_SETTINGS} is not valid TOML: {error}") from None
    named = github.get("repository")
    if not isinstance(named, str) or named.casefold() != repository.casefold():
        return {}
    apps: dict[str, StoredApp] = {}
    for role in _ROLES:
        app_id, slug = github.get(f"{role}_app_id", 0), github.get(f"{role}_app_slug", "")
        if app_id == 0 and slug == "":
            continue
        if not is_id(app_id) or not isinstance(slug, str) or not SLUG.fullmatch(slug):
            raise AppSetupError(
                f"{_SETTINGS}: [github] {role}_app_id and {role}_app_slug must record an App's "
                'ID and slug, or be 0 and ""'
            )
        apps[role] = StoredApp(app_id, slug)
    return apps


def install_url(slug: str, owner_id: int, repository_id: int) -> str:
    return (
        f"{GITHUB_URL}/apps/{slug}/installations/new/permissions"
        f"?suggested_target_id={owner_id}&repository_ids[]={repository_id}"
    )


@dataclass(frozen=True)
class _Target:
    owner: AppOwner
    owner_id: int
    repository_id: int


def _target(repository: str, owner_get: OwnerGet) -> _Target:
    """The repository's owner and ID.

    A user's repository is refused unless the owner's gh login is that user. An organisation's is
    not: its members use its Apps, and _require_admin checks the login before one is created.
    """
    if not _REPOSITORY.fullmatch(repository) or ".." in repository:
        raise AppSetupError(f"the repository must be OWNER/NAME, not {repository!r}")
    found = as_record(owner_get(f"repos/{repository}"))
    owner = as_record(found.get("owner"))
    login, owner_id, repository_id = owner.get("login"), owner.get("id"), found.get("id")
    if not isinstance(login, str) or not is_id(owner_id) or not is_id(repository_id):
        raise AppSetupError(f"GitHub's record of {repository} has no owner login or no ID")
    if owner.get("type") == "Organization":
        # The login goes into the paths of GitHub's API and of the organisation's settings pages.
        if not _LOGIN.fullmatch(login):
            raise AppSetupError(f"GitHub's record of {repository} has no usable owner login")
        return _Target(AppOwner(login, "organisation"), owner_id, repository_id)
    if owner.get("type") != "User":
        raise AppSetupError(
            f"GitHub's record of {repository} names an owner that is neither a user nor an "
            "organisation"
        )
    user = as_record(owner_get("user")).get("login")
    if not isinstance(user, str):
        raise AppSetupError("GitHub's record of your account has no login")
    if login.casefold() != user.casefold():
        raise _Refused(
            f"{repository} belongs to {login}, and gh is signed in as {user}. A private App "
            "installs only on its owner's repositories; sign gh in as the owner"
        )
    return _Target(AppOwner(login, "user"), owner_id, repository_id)


def _require_admin(repository: str, organisation: str, owner_get: OwnerGet) -> None:
    """Refused unless the owner's gh login is an active admin of the organisation.

    Only an organisation's admins create its Apps. GitHub answers 404 when the login is not a
    member; a member's role is admin, member or billing_manager.
    """
    try:
        membership = as_record(owner_get(f"user/memberships/orgs/{organisation}"))
    except GitHubNotFound:
        membership = {}
    if membership.get("state") != "active" or membership.get("role") != "admin":
        raise _Refused(
            f"{repository} belongs to the organisation {organisation}, and gh's login is not an "
            f"admin of {organisation}: an organisation admin creates its Apps once; ask one to "
            "run rapid-ship app, or, if the Apps exist, record their IDs and run rapid-ship app "
            "--import-key <role>"
        )


@dataclass(frozen=True)
class _Choice:
    """What run_app does for one role: use app, or create the App when app is None.

    Any stop ends the command with exit 1 before it changes anything.
    """

    app: StoredApp | None
    recorded: bool = False  # .rapid-ship/project.toml records app
    # The key in app's LEGACY_SERVICE item, to copy to keychain_service's item. It is read with
    # the other reads, so a key that cannot be read stops the command before any App is created.
    old_key: bytes | None = field(default=None, repr=False)
    stops: tuple[str, ...] = ()  # why the command must not go on, one message each


def _owned(app: StoredApp, target: _Target, owner_get: OwnerGet) -> bool | None:
    """Whether the repository's owner owns app, as GitHub shows it at app's slug.

    None when GitHub does not show app to the owner's gh login: it answers 404, or the slug now
    names another App. GitHub answers 404 for any private App, even its owner's, and rapid-ship
    creates private Apps. So None cannot tell the owner's App from a deleted or renamed one.
    """
    try:
        found = as_record(owner_get(f"apps/{app.slug}"))
    except GitHubNotFound:
        return None
    app_id, owner_id = found.get("id"), as_record(found.get("owner")).get("id")
    if not is_id(app_id) or not is_id(owner_id):
        raise AppSetupError(f"GitHub's record of the App {app.slug} has no App ID or no owner ID")
    # Another App at the slug, once app was renamed or deleted, tells nothing about whose app is.
    if app_id != app.app_id:
        return None
    return owner_id == target.owner_id


def _choose_recorded(role: str, recorded: StoredApp, store: KeychainStore) -> _Choice:
    """The recorded App, whose key is in its item or its LEGACY_SERVICE item. Never a new App."""
    # exists, not find: devctl reads the item by its name alone, even one rapid-ship did not write.
    if store.exists(keychain_service(role, recorded.app_id)):
        return _Choice(recorded, recorded=True)
    old = store.find(LEGACY_SERVICE[role])
    if old is not None and old.app_id == recorded.app_id:
        return _Choice(recorded, recorded=True, old_key=store.read_key(LEGACY_SERVICE[role]))
    return _Choice(recorded, recorded=True, stops=(_no_key(role, recorded),))


def _candidates(role: str, store: KeychainStore) -> list[tuple[str, StoredApp]]:
    """The role's items named by App ID, then the LEGACY_SERVICE item if it holds another App."""
    listed, old = store.listed(role), store.find(LEGACY_SERVICE[role])
    candidates = [(keychain_service(role, app.app_id), app) for app in listed]
    if old is not None and old.app_id not in {app.app_id for app in listed}:
        candidates.append((LEGACY_SERVICE[role], old))
    return candidates


def _by_key(
    role: str,
    unshown: list[tuple[str, StoredApp]],
    target: _Target,
    store: KeychainStore,
    app_of: AppOfKey,
) -> _Choice:
    """The first item whose own key shows its App as the owner's, else a stop for each item
    whose key cannot tell. An App of another account is skipped. The key stays in memory."""
    stops: list[str] = []
    for service, app in unshown:
        key = store.read_key(service)
        try:
            shown = app_of(key, app.app_id)
        except KeyRefused as refusal:
            stops.append(_unconfirmed(role, service, app, target, str(refusal)))
            continue
        if shown.app.app_id == app.app_id and shown.owner_id == target.owner_id:
            old_key = key if service == LEGACY_SERVICE[role] else None
            return _Choice(shown.app, old_key=old_key)
    return _Choice(None, stops=tuple(stops))


def _choose(
    role: str,
    recorded: StoredApp | None,
    target: _Target,
    store: KeychainStore,
    owner_get: OwnerGet,
    app_of: AppOfKey,
) -> _Choice:
    """The role's App: the recorded one, else the owner's App whose key this machine holds.

    GitHub shows gh no private App, so each item whose App GitHub does not show asks GitHub with
    its own key. When no item's App is the owner's, an item whose key cannot tell stops the
    command, so that rapid-ship creates no second App beside the owner's private one.
    """
    if recorded is not None:
        return _choose_recorded(role, recorded, store)
    unshown: list[tuple[str, StoredApp]] = []
    for service, app in _candidates(role, store):
        owned = _owned(app, target, owner_get)
        if owned:
            old_key = store.read_key(service) if service == LEGACY_SERVICE[role] else None
            return _Choice(app, old_key=old_key)
        if owned is None:
            unshown.append((service, app))
    return _by_key(role, unshown, target, store, app_of)


def _restore(role: str, app: StoredApp, key: bytes, store: KeychainStore) -> None:
    """Store the key read from the LEGACY_SERVICE item in the item named by App ID. rapid-ship
    deletes nothing."""
    old, new = LEGACY_SERVICE[role], keychain_service(role, app.app_id)
    store.add(new, app, key)
    sys.stdout.write(
        f"Re-stored the {TITLES[role]}'s key from Keychain item {old} as {new}. The old item "
        "stays; once ./devctl doctor passes, you can delete it with: "
        f"security delete-generic-password -s {old}\n"
    )


def _ensure_app(
    role: str,
    choice: _Choice,
    target: _Target,
    store: KeychainStore,
    create: Callable[[str, AppOwner], CreatedApp],
) -> tuple[StoredApp, bool]:
    """The role's App and whether its permissions are rapid-ship's. A found App is not checked."""
    if choice.app is not None:
        if choice.old_key is not None:
            _restore(role, choice.app, choice.old_key, store)
        return choice.app, True
    created = create(role, target.owner)
    try:
        # Before anything else: GitHub shows the key only once.
        store.add(keychain_service(role, created.app.app_id), created.app, created.private_key)
    except AppSetupError as error:
        settings = f"{target.owner.apps_settings_url}/{created.app.slug}/advanced"
        raise orphaned(error, settings) from None
    return created.app, created.permissions == APP_PERMISSIONS[role]


def _no_key(role: str, app: StoredApp) -> str:
    return (
        f"{_SETTINGS} records the {TITLES[role]} {app.app_id} ({app.slug}), and this machine "
        f"has no key for it in Keychain item {keychain_service(role, app.app_id)}. Generate a "
        "private key in the App's settings on GitHub, then run "
        f"rapid-ship app --import-key {role} with the key on stdin"
    )


def _unconfirmed(role: str, service: str, app: StoredApp, target: _Target, reason: str) -> str:
    # An App that still exists is recorded before its item goes: with neither, the next run
    # would create a second App beside it.
    return (
        f"Keychain item {service} holds a key of the {TITLES[role]} {app.app_id} ({app.slug}). "
        "GitHub does not show that App to gh, as it shows no private App, and the key cannot "
        f"confirm whose App it is: {reason}. If the App is {target.owner.login}'s and still "
        f"exists, first record its ID and slug under [github] in {_SETTINGS}. Then, if GitHub no "
        "longer has this key, delete the item, generate a new private key in the App's settings "
        f"on GitHub and run rapid-ship app --import-key {role} with the new key on stdin. If "
        "GitHub has no such App any more, delete the item and record nothing. Delete the item "
        f"with: security delete-generic-password -s {service}"
    )


def _report(role: str, app: StoredApp, repository: str, target: _Target, matches: bool) -> None:
    sys.stdout.write(
        f"{TITLES[role]}: ID {app.app_id} ({app.slug})\n"
        f"  {role}_app_id = {app.app_id}\n"
        f'  {role}_app_slug = "{app.slug}"\n'
        f"  Install on {repository}: "
        f"{install_url(app.slug, target.owner_id, target.repository_id)}\n"
    )
    if not matches:
        wanted = ", ".join(f"{name} {level}" for name, level in APP_PERMISSIONS[role].items())
        sys.stdout.write(
            f"  Its permissions differ from rapid-ship's ({wanted}): "
            f"fix the permissions at {target.owner.apps_settings_url}/{app.slug}/permissions\n"
        )


def run_app(
    repository: str,
    *,
    store: KeychainStore,
    owner_get: OwnerGet,
    open_browser: Callable[[str], object],
    recorded: Mapping[str, StoredApp] | None = None,
    api_url: str = API_URL,
    timeout_seconds: float = 900.0,
) -> int:
    """Find or create each App, then print every App's ID and its install URL for repository.

    recorded holds the Apps that the repository's .rapid-ship/project.toml records. 0 when both
    Apps are ready; 1 when the repository is refused, an App's permissions differ, a recorded
    App's key must be imported or a Keychain item's key cannot confirm whose App it is; 2 when
    the command cannot go on. An organisation's repository is refused when an App must be created
    and gh's login is not an admin of the organisation.
    """
    create = partial(
        create_app, open_browser=open_browser, api_url=api_url, timeout_seconds=timeout_seconds
    )
    app_of = partial(app_of_key, api_url=api_url)
    recorded = recorded or {}
    try:
        target = _target(repository, owner_get)
        # Every read comes first, so a read that fails changes nothing and opens no browser.
        choices = {
            role: _choose(role, recorded.get(role), target, store, owner_get, app_of)
            for role in _ROLES
        }
        stops = [stop for choice in choices.values() for stop in choice.stops]
        if stops:
            sys.stderr.write("".join(f"rapid-ship: {stop}\n" for stop in stops))
            return 1
        creates = any(choice.app is None for choice in choices.values())
        if creates and target.owner.kind == "organisation":
            _require_admin(repository, target.owner.login, owner_get)
        exit_code = 0
        for role, choice in choices.items():
            app, matches = _ensure_app(role, choice, target, store, create)
            _report(role, app, repository, target, matches)
            exit_code = exit_code if matches else 1
    except _Refused as refusal:
        sys.stderr.write(f"rapid-ship: refused: {refusal}\n")
        return 1
    except AppSetupError as error:
        sys.stderr.write(f"rapid-ship: {error}\n")
        return 2
    if all(choice.recorded for choice in choices.values()):
        sys.stdout.write("Both Apps are recorded; ./devctl doctor confirms each installation.\n")
    else:
        sys.stdout.write(
            "Record each App's ID and slug, as printed above, in .rapid-ship/project.toml under "
            "[github]; rs-setup does this. ./devctl doctor then confirms each installation.\n"
        )
    return exit_code
