"""rapid-ship app's Keychain items, and the process runner and error that the command shares.

Each App's private key is a generic-password item named rapid-ship/<role>-app/<App ID>, with the
App ID as its account and the slug as its comment. The key reaches `security` on stdin: it is
never written to disk, put in argv or printed. devctl reads the item back with the same tool.
rapid_ship may not import devctl, so keychain_service repeats devctl's, and a test keeps the two
equal.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

# Plan 4 named each item without the App ID. rapid-ship app re-stores such an item's key under
# keychain_service and leaves the old item in place.
LEGACY_SERVICE = {"worker": "rapid-ship/worker-app", "reviewer": "rapid-ship/reviewer-app"}
MAX_SECURITY_LINE = 4095  # `security -i` reads each command into a 4096-byte buffer
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")

Runner = Callable[[list[str], str | None], subprocess.CompletedProcess[str]]

_ITEM_NOT_FOUND = 44  # the exit code of `security find-generic-password` for a missing item
_HEX = re.compile(r"(?:[0-9a-f]{2})+")
# keychain_utilities.c print_keychain_item_attributes, which find-generic-password and
# dump-keychain share: the account holds the App ID and the comment the slug, so rapid-ship reads
# both without reading the key. dump-keychain starts each item with its keychain's path.
_ACCOUNT = re.compile(r'^\s*"acct"<blob>="(\d+)"$', re.MULTILINE)
_COMMENT = re.compile(r'^\s*"icmt"<blob>="([a-z0-9][a-z0-9-]*)"$', re.MULTILINE)
_SERVICE = re.compile(r'^\s*"svce"<blob>="([^"]*)"$', re.MULTILINE)
_ITEM_START = re.compile(r"^keychain: ", re.MULTILINE)


class AppSetupError(Exception):
    """rapid-ship app cannot go on; the command exits 2."""


@dataclass(frozen=True)
class StoredApp:
    app_id: int
    slug: str


def run_command(
    argv: Sequence[str], input_text: str | None = None, *, timeout_seconds: float = 120.0
) -> subprocess.CompletedProcess[str]:
    """Run security or gh with fixed arguments and no shell.

    rapid_ship cannot use devctl's runner.
    """
    try:
        return subprocess.run(  # noqa: S603  # rs-exception: EX-11
            list(argv),
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AppSetupError(f"could not run {argv[0]}: {type(error).__name__}") from None


def keychain_service(role: str, app_id: int) -> str:
    """The Keychain item that holds the key of the role's App with app_id.

    The ID in the name lets one machine hold the keys of several Apps for one role.
    """
    return f"rapid-ship/{role}-app/{app_id}"


class KeychainStore(Protocol):
    def find(self, service: str) -> StoredApp | None: ...
    def add(self, service: str, app: StoredApp, private_key: bytes) -> None: ...
    def read_key(self, service: str) -> bytes: ...
    def listed(self, role: str) -> list[StoredApp]: ...


def _secret(output: str) -> bytes:
    text = output.rstrip("\n")
    # `security -w` prints the item as lowercase hex when any byte is not printable, as a PEM's
    # newlines are (keychain_find.c:429-437). devctl decodes it the same way.
    return bytes.fromhex(text) if _HEX.fullmatch(text) else text.encode()


def _listed_apps(dump: str, role: str) -> list[StoredApp]:
    """The role's Apps among the items that `security dump-keychain` printed, by App ID.

    An item counts only when its name is keychain_service's for the ID in its account and its
    comment is a slug, as rapid-ship app writes them.
    """
    apps: set[StoredApp] = set()
    for item in _ITEM_START.split(dump):
        service, account = _SERVICE.search(item), _ACCOUNT.search(item)
        comment = _COMMENT.search(item)
        if service is None or account is None or comment is None:
            continue
        app_id = int(account.group(1))
        if app_id > 0 and service.group(1) == keychain_service(role, app_id):
            apps.add(StoredApp(app_id, comment.group(1)))
    return sorted(apps, key=lambda app: (app.app_id, app.slug))


class MacKeychainStore:
    """Each App as a generic-password item: the App ID as account, the slug as comment, the key
    as secret. No message includes `security`'s output, which can hold the key."""

    def __init__(self, run: Runner = run_command) -> None:
        self.run = run

    def find(self, service: str) -> StoredApp | None:
        # Without -w, security prints the item's attributes only, never its secret.
        result = self.run(["security", "find-generic-password", "-s", service], None)
        if result.returncode == _ITEM_NOT_FOUND:
            return None
        if result.returncode != 0:
            raise AppSetupError(f"could not read Keychain item {service}")
        account = _ACCOUNT.search(result.stdout)
        comment = _COMMENT.search(result.stdout)
        if account is None or comment is None:
            raise AppSetupError(f"Keychain item {service} was not written by rapid-ship app")
        return StoredApp(int(account.group(1)), comment.group(1))

    def add(self, service: str, app: StoredApp, private_key: bytes) -> None:
        # The key travels as hex on stdin, never in argv. Without -U an existing item is never
        # replaced. Without -T the item trusts /usr/bin/security alone, so devctl reads it with
        # no dialog, and so can any process the owner runs (spec section 6).
        line = (
            f"add-generic-password -s {service} -a {app.app_id} -j {app.slug} "
            f"-X {private_key.hex()}\n"
        )
        if len(line) > MAX_SECURITY_LINE:
            raise AppSetupError(
                f"the private key is too long for security -i; it reads lines of at most "
                f"{MAX_SECURITY_LINE} characters, so nothing was stored"
            )
        if self.run(["security", "-i"], line).returncode != 0:
            raise AppSetupError(f"could not write Keychain item {service}")
        stored = self.run(["security", "find-generic-password", "-s", service, "-w"], None)
        held = stored.returncode == 0 and _secret(stored.stdout) == private_key
        if not held or self.find(service) != app:
            raise AppSetupError(
                f"Keychain item {service} does not hold the key and App just written"
            )

    def read_key(self, service: str) -> bytes:
        """The item's key, for re-storing it under another name."""
        result = self.run(["security", "find-generic-password", "-s", service, "-w"], None)
        if result.returncode == _ITEM_NOT_FOUND:
            raise AppSetupError(f"Keychain item {service} not found")
        if result.returncode != 0:
            raise AppSetupError(f"could not read Keychain item {service}")
        key = _secret(result.stdout)
        if not key.startswith(b"-----BEGIN "):
            raise AppSetupError(f"Keychain item {service} holds no PEM private key")
        return key

    def listed(self, role: str) -> list[StoredApp]:
        """The role's Apps whose items are named by App ID, in the keychains security searches."""
        # Without -d, dump-keychain prints each item's attributes only, never its secret.
        result = self.run(["security", "dump-keychain"], None)
        if result.returncode != 0:
            raise AppSetupError("could not list the Keychain's items")
        return _listed_apps(result.stdout, role)
