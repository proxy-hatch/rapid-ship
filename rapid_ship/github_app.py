"""rapid-ship app: find or create the owner's Worker and Reviewer Apps, and print how to install
them.

For each role, the command uses the App that .rapid-ship/project.toml records, else an App of
the repository's owner whose key the Keychain holds, else it creates the App through GitHub's
manifest flow (app_flow.py). Spec 1 section 3: app creates only the Apps that do not exist yet.
GitHub shows the owner's gh no private App, so a Keychain item whose App GitHub does not show
stops the command instead: rapid-ship cannot tell whether that App exists. The stop prints the
[github] lines, repository among them, with which the next run uses that App.
The Keychain keeps each key in an item named by App ID (app_keychain.py); a key kept under plan
4's name is re-stored under the new name, and the old item stays.
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
    CreatedApp,
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

_ROLES = ("worker", "reviewer")
_SETTINGS = ".rapid-ship/project.toml"
_GH_TIMEOUT_SECONDS = 60.0
_REPOSITORY = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")


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
    owner_id: int
    owner_login: str
    repository_id: int


def _target(repository: str, owner_get: OwnerGet) -> _Target:
    """The repository's owner and ID. Refused unless the owner's gh login owns the repository."""
    if not _REPOSITORY.fullmatch(repository) or ".." in repository:
        raise AppSetupError(f"the repository must be OWNER/NAME, not {repository!r}")
    found = as_record(owner_get(f"repos/{repository}"))
    owner = as_record(found.get("owner"))
    login, owner_id, repository_id = owner.get("login"), owner.get("id"), found.get("id")
    if not isinstance(login, str) or not is_id(owner_id) or not is_id(repository_id):
        raise AppSetupError(f"GitHub's record of {repository} has no owner login or no ID")
    # A private App installs only on the account that owns it.
    if owner.get("type") != "User":
        raise _Refused(
            f"{repository} belongs to the organization {login}. rapid-ship app creates private "
            "Apps on your personal account, and they install only on its repositories"
        )
    user = as_record(owner_get("user")).get("login")
    if not isinstance(user, str):
        raise AppSetupError("GitHub's record of your account has no login")
    if login.casefold() != user.casefold():
        raise _Refused(
            f"{repository} belongs to {login}, and gh is signed in as {user}. A private App "
            "installs only on its owner's repositories; sign gh in as the owner"
        )
    return _Target(owner_id, login, repository_id)


@dataclass(frozen=True)
class _Choice:
    """What run_app does for one role: use app, or create the App when app is None.

    Any stop ends the command with exit 1 before it changes anything.
    """

    app: StoredApp | None
    recorded: bool = False  # .rapid-ship/project.toml records app
    # The key in app's plan 4 item, to copy to keychain_service's item. It is read with the other
    # reads, so a key that cannot be read stops the command before any App is created.
    old_key: bytes | None = field(default=None, repr=False)
    stops: tuple[str, ...] = ()  # why the command must not go on, one message each
    unconfirmed: tuple[StoredApp, ...] = ()  # the Apps of items that GitHub does not show


def _owned(app: StoredApp, target: _Target, owner_get: OwnerGet) -> bool | None:
    """Whether GitHub's App with app's slug is app, and the repository's owner owns it.

    None when GitHub does not show the App to the owner's gh login. GitHub answers 404 for any
    private App, even its owner's, and rapid-ship creates private Apps. So None cannot tell the
    owner's App from a deleted or renamed one.
    """
    try:
        found = as_record(owner_get(f"apps/{app.slug}"))
    except GitHubNotFound:
        return None
    app_id, owner_id = found.get("id"), as_record(found.get("owner")).get("id")
    if not is_id(app_id) or not is_id(owner_id):
        raise AppSetupError(f"GitHub's record of the App {app.slug} has no App ID or no owner ID")
    # The ID too, so an item whose slug now names another App is skipped.
    return app_id == app.app_id and owner_id == target.owner_id


def _choose_recorded(role: str, recorded: StoredApp, store: KeychainStore) -> _Choice:
    """The recorded App, whose key is in its item or in plan 4's item. Never a new App."""
    if store.find(keychain_service(role, recorded.app_id)) is not None:
        return _Choice(recorded, recorded=True)
    old = store.find(LEGACY_SERVICE[role])
    if old is not None and old.app_id == recorded.app_id:
        return _Choice(recorded, recorded=True, old_key=store.read_key(LEGACY_SERVICE[role]))
    return _Choice(recorded, recorded=True, stops=(_no_key(role, recorded),))


def _choose(
    role: str,
    recorded: StoredApp | None,
    target: _Target,
    store: KeychainStore,
    owner_get: OwnerGet,
) -> _Choice:
    """The role's App: the recorded one, else the owner's App whose key this machine holds.

    When GitHub shows no item's App as the owner's, an item whose App GitHub does not show at all
    stops the command, so that rapid-ship creates no second App beside the owner's private one.
    """
    if recorded is not None:
        return _choose_recorded(role, recorded, store)
    listed, old = store.listed(role), store.find(LEGACY_SERVICE[role])
    candidates = [(keychain_service(role, app.app_id), app) for app in listed]
    if old is not None and old.app_id not in {app.app_id for app in listed}:
        candidates.append((LEGACY_SERVICE[role], old))
    unconfirmed: list[tuple[str, StoredApp]] = []
    for service, app in candidates:
        owned = _owned(app, target, owner_get)
        if owned:
            old_key = store.read_key(service) if service == LEGACY_SERVICE[role] else None
            return _Choice(app, old_key=old_key)
        if owned is None:
            unconfirmed.append((service, app))
    return _Choice(
        None,
        stops=tuple(_unconfirmed(role, service, app) for service, app in unconfirmed),
        unconfirmed=tuple(app for _, app in unconfirmed),
    )


def _restore(role: str, app: StoredApp, key: bytes, store: KeychainStore) -> None:
    """Store the key read from plan 4's item in the item named by App ID. rapid-ship deletes
    nothing."""
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
    create: Callable[[str, str], CreatedApp],
) -> tuple[StoredApp, bool]:
    """The role's App and whether its permissions are rapid-ship's. A found App is not checked."""
    if choice.app is not None:
        if choice.old_key is not None:
            _restore(role, choice.app, choice.old_key, store)
        return choice.app, True
    created = create(role, target.owner_login)
    try:
        # Before anything else: GitHub shows the key only once.
        store.add(keychain_service(role, created.app.app_id), created.app, created.private_key)
    except AppSetupError as error:
        raise orphaned(error, f"{GITHUB_URL}/settings/apps/{created.app.slug}/advanced") from None
    return created.app, created.permissions == APP_PERMISSIONS[role]


def _no_key(role: str, app: StoredApp) -> str:
    return (
        f"{_SETTINGS} records the {TITLES[role]} {app.app_id} ({app.slug}), and this machine "
        f"has no key for it in Keychain item {keychain_service(role, app.app_id)}. Generate a "
        "private key in the App's settings on GitHub, then run "
        f"rapid-ship app --import-key {role} with the key on stdin"
    )


def _unconfirmed(role: str, service: str, app: StoredApp) -> str:
    return (
        f"Keychain item {service} holds a key of the {TITLES[role]} {app.app_id} ({app.slug}), "
        "and GitHub does not show that App to gh, as it shows no private App. If GitHub has no "
        f"such App any more, delete the item with: security delete-generic-password -s {service}"
    )


def _lines_to_record(repository: str, choices: Mapping[str, _Choice]) -> str:
    """The [github] lines with which the next run uses the Apps of items GitHub does not show.

    "" when there are none. recorded_apps reads IDs only under the target repository, and devctl
    refuses a table with one App, so the lines name the repository and every App found but not
    recorded, and say when the next run must still create an App.
    """
    if not any(choice.unconfirmed for choice in choices.values()):
        return ""
    lines, notes = [f'repository = "{repository}"'], []
    for role, choice in choices.items():
        if choice.recorded:
            continue
        app = choice.app or next(iter(choice.unconfirmed), None)
        if app is None:
            notes.append(
                f"That run creates the {TITLES[role]} and prints its lines. Record them too "
                "before you run ./devctl or commit: devctl refuses a [github] table that records "
                "only one App."
            )
            continue
        lines += [f"{role}_app_id = {app.app_id}", f'{role}_app_slug = "{app.slug}"']
        if len(choice.unconfirmed) > 1:
            notes.append(
                f"Several Keychain items hold a {TITLES[role]}'s key, and the lines name the "
                f"first above; record the one {repository} uses."
            )
    return (
        f"rapid-ship: To use the Keychain's Apps, record these lines under [github] in "
        f"{repository}'s {_SETTINGS}, then run rapid-ship app again in its work tree:\n"
        + "".join(f"  {line}\n" for line in lines)
        + "".join(f"rapid-ship: {note}\n" for note in notes)
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
            f"fix the permissions at {GITHUB_URL}/settings/apps/{app.slug}/permissions\n"
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
    App's key must be imported or a Keychain item's App cannot be confirmed; 2 when the command
    cannot go on.
    """
    create = partial(
        create_app, open_browser=open_browser, api_url=api_url, timeout_seconds=timeout_seconds
    )
    recorded = recorded or {}
    try:
        target = _target(repository, owner_get)
        # Every read comes first, so a read that fails changes nothing and opens no browser.
        choices = {
            role: _choose(role, recorded.get(role), target, store, owner_get) for role in _ROLES
        }
        stops = [stop for choice in choices.values() for stop in choice.stops]
        if stops:
            sys.stderr.write("".join(f"rapid-ship: {stop}\n" for stop in stops))
            sys.stderr.write(_lines_to_record(repository, choices))
            return 1
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
