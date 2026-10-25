"""rapid-ship app --import-key: store a developer's own key for an App that [github] records.

Step 4 of `rapid-ship app`, in section 3 of
docs/superpowers/specs/2026-10-14-kit-and-setup-design.md, describes the command. The key stays
in memory and reaches `security` only on stdin.
"""

from __future__ import annotations

import sys
from typing import BinaryIO

from rapid_ship.app_flow import API_URL, TITLES, KeyRefused, KeyUnusable, app_of_key
from rapid_ship.app_keychain import AppSetupError, KeychainStore, StoredApp, keychain_service

MAX_KEY_BYTES = 64 * 1024  # far more than any App key: GitHub's are under 2 KiB

_SETTINGS = ".rapid-ship/project.toml"


class _Refused(Exception):
    """Nothing is stored; the command exits 1."""


def _read_key(role: str, stdin: BinaryIO | None) -> bytes:
    """The PEM key on stdin, without the whitespace around it, and with one newline after it.

    stdin is None when file descriptor 0 is closed, which holds no key either.
    """
    if stdin is None:
        raise _Refused("stdin holds no key")
    if stdin.isatty():  # a pasted key would show on the screen
        raise _Refused(
            f"give the key on stdin, as in: rapid-ship app --import-key {role} "
            "< the-downloaded.private-key.pem"
        )
    data = stdin.read(MAX_KEY_BYTES + 1)
    if len(data) > MAX_KEY_BYTES:
        raise _Refused(f"stdin holds more than {MAX_KEY_BYTES // 1024} KiB, more than any App key")
    key = data.strip()
    if not key:
        raise _Refused("stdin holds no key")
    # The PEM parser skips text before the key, and devctl reads an item only when it starts with
    # the key.
    if not key.startswith(b"-----BEGIN "):
        raise _Refused("stdin holds no PEM private key: it must start with a -----BEGIN line")
    return key + b"\n"


def _confirm(role: str, app: StoredApp, key: bytes, api_url: str) -> None:
    """Refused unless GitHub shows app to a token that the key signs."""
    title = f"{TITLES[role]} {app.app_id} ({app.slug})"
    try:
        shown = app_of_key(key, app.app_id, api_url=api_url).app
    except KeyUnusable as unusable:
        raise _Refused(str(unusable)) from None
    except KeyRefused as refusal:
        raise _Refused(
            f"GitHub refused a token that the key on stdin signs for the {title}: {refusal}"
        ) from None
    if shown != app:
        raise _Refused(
            f"GitHub shows the key's App as {shown.app_id} ({shown.slug}), not the {title} that "
            f"{_SETTINGS} records"
        )


def import_key(
    role: str,
    repository: str,
    recorded: StoredApp | None,
    stdin: BinaryIO | None,
    *,
    store: KeychainStore,
    api_url: str = API_URL,
) -> int:
    """Store the key on stdin for the role's App, which recorded holds when the repository's
    .rapid-ship/project.toml records it.

    0 when the key is stored; 1 when nothing is stored because no App is recorded, the item
    exists, stdin holds no usable key or GitHub does not show the recorded App to a token that
    the key signs; 2 when the command cannot go on.
    """
    try:
        if recorded is None:
            raise _Refused(
                f"{_SETTINGS} records no {TITLES[role]} for {repository}, so no key can be "
                f"checked against it. Run rapid-ship app --import-key {role} in the repository's "
                "work tree once [github] records the App's ID and slug"
            )
        service = keychain_service(role, recorded.app_id)
        if store.exists(service):
            raise _Refused(
                f"Keychain item {service} already exists, and rapid-ship never replaces one; "
                "./devctl doctor checks the key it holds. To replace a key that no longer works, "
                f"delete the item with: security delete-generic-password -s {service}, then run "
                "this again"
            )
        key = _read_key(role, stdin)
        _confirm(role, recorded, key, api_url)
        store.add(service, recorded, key)
    except _Refused as refusal:
        sys.stderr.write(f"rapid-ship: {refusal}. Nothing was stored.\n")
        return 1
    except AppSetupError as error:
        sys.stderr.write(f"rapid-ship: {error}\n")
        return 2
    sys.stdout.write(
        f"Stored your key for the {TITLES[role]} {recorded.app_id} ({recorded.slug}) in "
        f"Keychain item {service}. rapid-ship wrote it nowhere else: delete the key file that "
        "GitHub downloaded. ./devctl doctor then checks the App's installation.\n"
    )
    return 0
