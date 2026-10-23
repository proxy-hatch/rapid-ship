"""The merge guard's GitHub reads: the pull request, CODEOWNERS on its base branch, its files,
its reviews and its check runs (Spec 1 section 4, steps 2 to 4).

Each read goes through OwnerGet, doctor's GET with the owner's gh sign-in. A read that gh cannot
make raises OwnerReadError, a response that is not the shape GitHub documents GitHubError, and a
pull request the guard cannot identify Unchecked with the reason; merge_guard.guard denies each.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from itertools import count
from urllib.parse import quote

from devctl.codeowners import CODEOWNERS_FILES, FileChange, FileStatus, patterns_in
from devctl.doctor_github import decoded_contents
from devctl.doctor_items import OwnerGet, OwnerReadError
from devctl.doctor_local import CI_JOB_NAME
from devctl.doctor_rules import GITHUB_ACTIONS_APP_ID
from devctl.github.api import GitHubError, json_list, json_object

_PAGE = 100  # GitHub's largest page
_FILE_PAGES = 30  # GitHub lists at most 3,000 files of a pull request
# The fields of a changed file that the guard reads. A page of 100 files with their patches can
# pass gh_get's output cap, so gh prints only these.
_FILE_FIELDS = "[.[] | {filename, status, previous_filename}]"
_VERDICTS = frozenset({"APPROVED", "CHANGES_REQUESTED"})  # the reviews that decide
# A pull request's URL as gh reads one, whose repository wins over -R.
_PR_URL = re.compile(
    r"https?://github\.com/(?P<repository>[^/]+/[^/]+)/pull/(?P<number>[0-9]+)(?:[/?#].*)?"
)
_PR_NUMBER = re.compile(r"#?(?P<number>[0-9]+)")  # gh drops a leading "#"
_SHA = re.compile(r"[0-9a-f]{40}")  # GitHub compares --match-head-commit with the full SHA
# GitHub's file statuses: copied is an added file, and changed or unchanged a modified one.
_STATUSES: Mapping[str, FileStatus] = {
    "added": "added",
    "copied": "added",
    "removed": "removed",
    "renamed": "renamed",
}
_NO_REPOSITORY = (
    "no repository: set [github] repository in .rapid-ship/project.toml or pass -R OWNER/NAME"
)
_DETACHED = "HEAD is detached and the command names no pull request"
_TOO_MANY_FILES = "GitHub lists at most 3,000 files of a pull request, and this one has more"


class Unchecked(Exception):
    """The guard cannot check the merge, for the reason it carries."""


@dataclass(frozen=True)
class PullRequest:
    """The pull request the guard checks, as it read it."""

    repository: str  # owner/name
    number: int
    head: str  # the head commit's full SHA
    base: str  # the base branch


def find_pull(
    read: OwnerGet,
    target: str | None,
    repository: str | None,
    current: Callable[[], str | None],
) -> PullRequest:
    """The pull request that gh pr merge names: by number, by URL, by branch, or, without a
    target, the current branch's, which current reads from local git.

    repository is the -R value, else [github] repository; a URL's own repository wins over it, as
    it does in gh.
    """
    url = _PR_URL.fullmatch(target) if target else None
    if url:
        repository = url["repository"]
    if repository is None:
        raise Unchecked(_NO_REPOSITORY)
    found = url or (_PR_NUMBER.fullmatch(target) if target else None)
    if found:
        return _pull(read(f"repos/{repository}/pulls/{found['number']}"), repository)
    branch = target or current()
    if branch is None:
        raise Unchecked(_DETACHED)
    return _pull(_by_branch(read, repository, branch), repository)


def _by_branch(read: OwnerGet, repository: str, branch: str) -> object:
    """The one open PR whose head is owner:branch, where owner is the repository's owner unless
    branch already names one."""
    head = branch if ":" in branch else f"{repository.partition('/')[0]}:{branch}"
    path = f"repos/{repository}/pulls?head={quote(head, safe=':/')}&state=open&per_page={_PAGE}"
    listed = json_list(read(path), "the pull request list")
    if not listed:
        raise Unchecked(f"no open pull request has head {head}")
    if len(listed) > 1:
        raise Unchecked(f"{len(listed)} open pull requests have head {head}; name one by number")
    return listed[0]


def _pull(found: object, repository: str) -> PullRequest:
    pull = json_object(found, "the pull request")
    head = _text(json_object(pull.get("head"), "the head"), "sha", "the pull request's head")
    if not _SHA.fullmatch(head):
        raise GitHubError(None, f"the pull request's head is not a full SHA: {head!r}")
    base = _text(json_object(pull.get("base"), "the base"), "ref", "the pull request's base")
    return PullRequest(repository, _number(pull, "number", "the pull request"), head, base)


def base_patterns(read: OwnerGet, pull: PullRequest) -> list[str]:
    """The Protected-set patterns of the CODEOWNERS file GitHub reads on the base branch.

    GitHub reads the first of CODEOWNERS_FILES that exists, so a 404 moves to the next name, and
    none at all is an empty Protected set.
    """
    ref = quote(pull.base, safe="/")
    for name in CODEOWNERS_FILES:
        try:
            found = read(f"repos/{pull.repository}/contents/{name}?ref={ref}")
        except OwnerReadError as error:
            if error.status == 404:
                continue
            raise
        return patterns_in(decoded_contents(json_object(found, f"the {name} contents")))
    return []


def changed_files(read: OwnerGet, pull: PullRequest) -> list[FileChange]:
    """The PR's changed files, page by page; a full last page that GitHub lists is a denial."""
    path = f"repos/{pull.repository}/pulls/{pull.number}/files"
    limit = (_FILE_PAGES, _TOO_MANY_FILES)
    entries = _pages(read, path, "the pull request's files", limit, jq=_FILE_FIELDS)
    return [_change(json_object(entry, "a changed file")) for entry in entries]


def _change(entry: Mapping[str, object]) -> FileChange:
    path = _text(entry, "filename", "a changed file")
    status = entry.get("status")
    mapped = _STATUSES.get(status, "modified") if isinstance(status, str) else "modified"
    if mapped == "renamed":
        return FileChange(path, mapped, _text(entry, "previous_filename", "a renamed file"))
    return FileChange(path, mapped)


def reviewer_approved(read: OwnerGet, pull: PullRequest, slug: str | None) -> bool:
    """Whether the Reviewer App, <slug>[bot], approved the head commit.

    Of its reviews that approve or request changes, the one with the highest id is the latest and
    decides; comments, dismissed and pending reviews are ignored. The reviews have no page limit
    of their own: the guard's budget bounds their reads.
    """
    path = f"repos/{pull.repository}/pulls/{pull.number}/reviews"
    reviews = [json_object(entry, "a review") for entry in _pages(read, path, "the reviews")]
    deciding = [
        review
        for review in reviews
        if slug is not None
        and _login(review) == f"{slug}[bot]"
        and review.get("state") in _VERDICTS
    ]
    if not deciding:
        return False
    latest = max(deciding, key=lambda review: _number(review, "id", "a review"))
    return latest.get("state") == "APPROVED" and latest.get("commit_id") == pull.head


def _login(review: Mapping[str, object]) -> object:
    user = review.get("user")  # null for a deleted account
    return user.get("login") if isinstance(user, dict) else None


def check_state(read: OwnerGet, pull: PullRequest) -> str:
    """The state of the latest devctl check run from GitHub Actions on the head commit: missing
    without one, its status while it has not completed, else its conclusion."""
    path = f"repos/{pull.repository}/commits/{pull.head}/check-runs"
    query = f"check_name={quote(CI_JOB_NAME)}&filter=latest&per_page={_PAGE}"
    listed = json_object(read(f"{path}?{query}"), "the check runs")
    runs = [
        json_object(run, "a check run")
        for run in json_list(listed.get("check_runs"), "the run list")
    ]
    ours = [run for run in runs if run.get("name") == CI_JOB_NAME and _from_actions(run)]
    if not ours:
        return "missing"
    latest = max(ours, key=lambda run: _number(run, "id", "a check run"))
    status = _text(latest, "status", "the check run")
    return status if status != "completed" else _text(latest, "conclusion", "the check run")


def _from_actions(run: Mapping[str, object]) -> bool:
    app = run.get("app")
    return isinstance(app, dict) and app.get("id") == GITHUB_ACTIONS_APP_ID


def _pages(
    read: OwnerGet,
    path: str,
    what: str,
    limit: tuple[int, str] | None = None,
    jq: str | None = None,
) -> Iterator[object]:
    """Each entry of a listing, read 100 to a page from page 1 until a page holds fewer.

    limit is the last page GitHub lists and the reason that a full page there raises as
    Unchecked, because GitHub lists no more. jq, gh's filter, must keep one entry for each.
    """
    for page in count(1):
        entries = json_list(read(f"{path}?per_page={_PAGE}&page={page}", jq), what)
        yield from entries
        if len(entries) < _PAGE:
            return
        if limit is not None and page == limit[0]:
            raise Unchecked(limit[1])


def _text(fields: Mapping[str, object], key: str, what: str) -> str:
    value = fields.get(key)
    if isinstance(value, str) and value:
        return value
    raise GitHubError(None, f"{what} has no {key}")


def _number(fields: Mapping[str, object], key: str, what: str) -> int:
    value = fields.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise GitHubError(None, f"{what} has no numeric {key}")
