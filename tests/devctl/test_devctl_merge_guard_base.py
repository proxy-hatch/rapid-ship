"""Offline: policy reads stay on the PR response's base SHA while its branch moves."""

from __future__ import annotations

import pytest

from devctl.doctor_items import OwnerReadError
from test_devctl_merge_guard import (
    FLIGHT,
    HEAD,
    IDENTITY,
    IN_WALK,
    PR,
    PULL,
    TOUCHES,
    UNAPPROVED,
    WALK,
    contents,
    guarded,
    owner,
)

BASE_SHA = "c" * 40
BASE_SETTINGS = f"repos/o/r/contents/.rapid-ship/project.toml?ref={BASE_SHA}"
BASE_OWNERS = f"repos/o/r/contents/.github/CODEOWNERS?ref={BASE_SHA}"
LINE = f"gh pr merge 7 --match-head-commit {HEAD}"


@pytest.mark.parametrize(
    ("policy", "denial"), [(WALK, IN_WALK), (IDENTITY, UNAPPROVED)], ids=["walk", "apps"]
)
def test_moving_branch_settings_cannot_weaken_the_pr_base_policy(policy: str, denial: str) -> None:
    reader = owner(base=FLIGHT, reviews=[])
    reader.serve(PR, {**PULL, "base": {"ref": "main", "sha": BASE_SHA}})
    reader.serve("repos/o/r/contents/.rapid-ship/project.toml?ref=main", contents(FLIGHT))
    reader.serve(BASE_SETTINGS, contents(policy))
    reader.serve(BASE_OWNERS, contents(""))
    assert guarded(LINE, reader) == denial
    assert BASE_SETTINGS in reader.paths
    assert "repos/o/r/contents/.rapid-ship/project.toml?ref=main" not in reader.paths


@pytest.mark.parametrize("location", [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"])
def test_codeowners_uses_the_same_base_sha_in_every_location(location: str) -> None:
    reader = owner()
    reader.serve(PR, {**PULL, "base": {"ref": "main", "sha": BASE_SHA}})
    reader.serve(BASE_SETTINGS, contents(FLIGHT))
    if location != ".github/CODEOWNERS":
        reader.fail(BASE_OWNERS, OwnerReadError(404, "Not Found"))
    reader.serve(f"repos/o/r/contents/{location}?ref={BASE_SHA}", contents("/src/ @o\n"))
    reader.serve("repos/o/r/contents/.github/CODEOWNERS?ref=main", contents(""))
    assert guarded(LINE, reader) == TOUCHES.format("src/app/core.py")
    assert all(f"?ref={BASE_SHA}" in path for path in reader.paths if "/contents/" in path)


@pytest.mark.parametrize(
    "base",
    [
        {"ref": "main"},
        *[{"ref": "main", "sha": sha} for sha in [None, 1, "", "c" * 39, "g" * 40, "main"]],
    ],
    ids=["missing", "null", "number", "empty", "short", "non-hex", "branch"],
)
def test_absent_or_malformed_base_sha_denies_before_reading_policy(base: object) -> None:
    reader = owner()
    reader.serve(PR, {**PULL, "base": base})
    denial = guarded(LINE, reader)
    assert denial is not None
    assert "the pull request's base" in denial
    assert reader.paths == [PR]
