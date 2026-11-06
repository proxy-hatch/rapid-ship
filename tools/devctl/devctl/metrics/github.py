"""Projected, serialized GitHub reads with a shared API allowance."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from typing import Protocol, cast

from devctl.doctor_items import OwnerGet, OwnerReadError, gh_get


class GitHubError(Exception):
    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status


class AllowanceUsedUp(Exception):
    def __init__(self, reset: datetime | None = None) -> None:
        self.reset = reset
        super().__init__(self.reason())

    def reason(self) -> str:
        prefix = "GitHub API allowance used up"
        if self.reset is None:
            return prefix + "; its reset time could not be read"
        return prefix + f"; it resets at {self.reset:%H:%M} UTC"


class MeasurementClosed(Exception):
    """This measurement can no longer admit requests."""


class MeasurementGet(Protocol):
    def __call__(self, path: str, jq: str | None = None) -> object: ...
    def close(self) -> None: ...


class _ScopedGet:
    def __init__(self, reader: GitHubReader, deadline: float) -> None:
        self.reader = reader
        self.deadline = deadline
        self._state = threading.Lock()
        self._closed = False

    def close(self) -> None:
        with self._state:
            self._closed = True

    def __call__(self, path: str, jq: str | None = None) -> object:
        with self.reader._serialization:
            # The state lock linearizes admission with close, but never covers network I/O.
            with self._state:
                if self._closed or time.monotonic() >= self.deadline:
                    raise MeasurementClosed()
            return self.reader._read("/" + path.lstrip("/"), jq)


class GitHubReader:
    def __init__(self, repository: str, get: OwnerGet = gh_get) -> None:
        self.repository = repository
        self._get = get
        self.requests = 0
        self._serialization = threading.Lock()
        self._exhausted: AllowanceUsedUp | None = None

    def measurement_get(self, deadline: float) -> MeasurementGet:
        return _ScopedGet(self, deadline)

    def get(self, path: str, jq: str | None = None) -> object:
        with self._serialization:
            return self._read(path, jq)

    def _read(self, path: str, jq: str | None) -> object:
        """Read with serialization held; scoped callers have already admitted the request."""
        if self._exhausted is not None:
            raise self._exhausted
        full = path.lstrip("/") if path.startswith("/") else f"repos/{self.repository}/{path}"
        self.requests += 1
        try:
            return self._get(full, jq=jq)
        except OwnerReadError as error:
            if error.status in (403, 429) and "rate limit" in error.message.lower():
                self._exhausted = AllowanceUsedUp()
                self._exhausted.reset = self._reset()
                self._exhausted.args = (self._exhausted.reason(),)
                raise self._exhausted from error
            raise _read_error(full, error) from error

    def _reset(self) -> datetime | None:
        self.requests += 1
        try:
            data = self._get("rate_limit", jq=None)
            data = cast("dict[str, dict[str, dict[str, float]]]", data)
            return datetime.fromtimestamp(data["resources"]["core"]["reset"], UTC)
        except (OwnerReadError, KeyError, TypeError, ValueError, OverflowError, OSError):
            return None

    def pages(
        self,
        path: str,
        *,
        jq: str,
        until: Callable[[Mapping[str, object]], bool] | None = None,
    ) -> Iterator[Mapping[str, object]]:
        size, yielded = 64, 0
        while True:
            separator = "&" if "?" in path else "?"
            page_path = f"{path}{separator}per_page={size}&page={yielded // size + 1}"
            try:
                page = self.get(page_path, jq=jq)
            except GitHubError as error:
                cause = error.__cause__
                if isinstance(cause, OwnerReadError) and _overflow(cause) and size > 1:
                    size //= 2
                    continue
                raise
            if not isinstance(page, list) or not all(isinstance(p, Mapping) for p in page):
                raise GitHubError(
                    None, f"GitHub returned invalid JSON for {page_path}; inspect the response"
                )
            for item in page:
                if until is not None and until(item):
                    return
                yield item
                yielded += 1
            if len(page) < size:
                return


def _overflow(error: OwnerReadError) -> bool:
    return error.status is None and error.message.startswith("gh api output exceeded ")


def _read_error(path: str, error: OwnerReadError) -> GitHubError:
    message = error.message
    if error.status is not None:
        text = f"GitHub refused {path} (HTTP {error.status}): {message}"
        if error.status == 401:
            text += "; check gh auth status"
    elif message == "gh could not start":
        text = f"GitHub read {path}: {message}; install gh and run gh auth login"
    elif message == "gh api timed out":
        text = f"GitHub read {path} timed out; check connectivity and rerun"
    elif _overflow(error):
        text = f"GitHub read {path}: {message}; narrow that item's projection"
    else:
        text = f"GitHub read {path}: {message}; inspect the response"
    return GitHubError(error.status, text)
