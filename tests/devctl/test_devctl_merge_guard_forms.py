"""Offline: find_merge on command lines; no git and no GitHub."""

from __future__ import annotations

import pytest

from devctl.command_line import simple_commands
from devctl.merge_guard import LocalBranches, Merge, find_merge

TASK = LocalBranches(frozenset({"main"}), "task")


def unread() -> LocalBranches:
    raise AssertionError("local git was read")


FORMS = [  # command line, form, target
    ("gh pr merge", "pr-merge", None),
    ("gh pr merge 7 --squash --auto", "pr-merge", "7"),
    ("gh pr merge https://github.com/x/y/pull/7", "pr-merge", "https://github.com/x/y/pull/7"),
    ("gh pr merge task -b 'body text' --squash", "pr-merge", "task"),
    ("./devctl as worker gh pr merge 7 --squash", "pr-merge", "7"),
    ("gh pr merge --subject x 7", "pr-merge", "7"),
    ("gh pr merge --match-head-commit=abc -R x/y 7", "pr-merge", "7"),
    ("gh pr -R x/y merge 7", "pr-merge", "7"),
    ("gh pr merge 2>&1", "pr-merge", None),
    ("gh pr merge 7 >/dev/null", "pr-merge", "7"),
    ("gh pr merge 7 --admin", "admin", None),
    ("./devctl as reviewer gh pr merge 7 --admin", "admin", None),
    ("gh pr --repo=x/y merge 7 --admin", "admin", None),
    ("git push origin main", "push", None),
    ("gh api -X PUT repos/o/r/pulls/7/merge", "rest", None),
    ("./devctl as worker gh api -X PUT repos/{owner}/{repo}/pulls/7/merge", "rest", None),
    (
        "gh api graphql -f query='mutation { updateRef(input: {}) { ref { name } } }'",
        "graphql",
        None,
    ),
    ("gh pr view 7", None, None),
    ("gh api -X GET repos/o/r/contents/a.md", None, None),
    ("git push origin task", None, None),
]


@pytest.mark.parametrize(("line", "form", "target"), FORMS)
def test_find_merge_recognises_each_form(line: str, form: str | None, target: str | None) -> None:
    merge = find_merge(simple_commands(line)[0], lambda: TASK)
    assert ((merge.form, merge.target) if merge else (None, None)) == (form, target)


def test_a_pr_merge_keeps_its_repository_head_and_command() -> None:
    words = simple_commands("gh pr merge 7 -R x/y --match-head-commit abc --squash")[0]
    assert find_merge(words, unread) == Merge(
        "pr-merge",
        "7",
        repository="x/y",
        head="abc",
        command=("gh", "pr", "merge", "7", "-R", "x/y", "--squash"),
    )


def test_a_repository_given_before_merge_is_kept() -> None:
    words = simple_commands("gh pr -R x/y merge 7")[0]
    assert find_merge(words, unread) == Merge(
        "pr-merge", "7", repository="x/y", command=("gh", "pr", "-R", "x/y", "merge", "7")
    )
