"""PRs closed without merging during the window's span, and who closed each of them."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from devctl.metrics.github import GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.window import Window

_CLOSED = "[.[] | {number, user: {login: .user.login}, merged_at, closed_at, updated_at}]"
_EVENTS = "[.[] | {event, actor: {login: .actor.login}}]"
_NO_CLOSER = "its last closed event names no actor, or it has no closed event"


def _time(value: object) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None


def _login(account: object) -> str | None:
    login = account.get("login") if isinstance(account, Mapping) else None
    return login if isinstance(login, str) else None


def _stale(pull: Mapping[str, object], since: datetime) -> bool:
    """Whether the PR was last updated before since. A closed PR is never updated before it
    closed, so it and every PR after it in the list closed before since.
    """
    updated = _time(pull.get("updated_at"))
    return updated is not None and updated < since


def _closer(reader: GitHubReader, number: int) -> str | None:
    """The actor of the PR's last closed event, which decides: a PR that was closed, reopened
    and closed again has two.
    """
    closer = None
    for event in reader.pages(f"issues/{number}/events", jq=_EVENTS):
        if event.get("event") == "closed":
            closer = _login(event.get("actor"))
    return closer


def closed_unmerged(
    reader: GitHubReader, window: Window, since: datetime, app_logins: frozenset[str]
) -> Measured:
    """The population's PRs that were closed without merging on or after since.

    With Agent identity the population is the Worker App's PRs, and a PR counts only when someone
    other than an App closed it. Without it, every closed PR counts and no event is read.
    """
    identity = window.agent_login is not None
    items: list[dict[str, object]] = []
    # A PR updated between two page reads moves to the top and shifts the rest down, so one PR
    # can end a page and start the next.
    seen: set[int] = set()
    pulls = reader.pages(
        "pulls?state=closed&sort=updated&direction=desc",
        jq=_CLOSED,
        until=lambda pull: _stale(pull, since),
    )
    for pull in pulls:
        number = cast("int", pull["number"])
        if number in seen:
            continue
        seen.add(number)
        closed = _time(pull.get("closed_at"))
        if pull.get("merged_at") is not None or closed is None or closed < since:
            continue
        if identity and _login(pull.get("user")) != window.agent_login:
            continue
        item: dict[str, object] = {"pr": number, "state": "counted"}
        if identity:
            closer = _closer(reader, number)
            if closer is None:
                item = {"pr": number, "state": "unknown", "detail": _NO_CLOSER}
            elif closer in app_logins:
                continue
        items.append(item)
    unknown = sum(item["state"] == "unknown" for item in items)
    items.sort(key=lambda item: -cast("int", item["pr"]))
    return Measured(len(items) - unknown, unknown=unknown, items=tuple(items))
