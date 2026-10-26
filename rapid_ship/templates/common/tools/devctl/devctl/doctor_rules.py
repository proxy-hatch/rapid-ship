"""What doctor expects of a ruleset, CODEOWNERS and an App installation.

These checks are pure: they take what GitHub returned and name each way it differs.
doctor_github.py reads GitHub and builds the items.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from devctl.doctor_local import CI_JOB_NAME
from devctl.github.app import APP_PERMISSIONS
from devctl.settings import Role, Stack

ADMIN_ROLE_ID = 5  # the repository admin role
GITHUB_ACTIONS_APP_ID = 15368  # gh api /apps/github-actions
# The Protected set of the seeded CODEOWNERS, in its order, with the devctl shim.
PROTECTED_PATHS = (
    ".github/",
    ".githooks/",
    "devctl",
    "tools/devctl/",
    ".agents/skills/",
    ".claude/",
    "**/AGENTS.md",
    "**/CLAUDE.md",
    ".rapid-ship/",
    ".gitleaks.toml",
    ".gitleaksignore",
    "zizmor.yml",
    "zizmor.yaml",
)
# The Python guardrail settings: every file Ruff, mypy, pytest and import-linter read settings
# from, in the template's last lines. Ruff reads the nearest ruff.toml, so those match at any depth.
PYTHON_PROTECTED_PATHS = (
    "pyproject.toml",
    "**/ruff.toml",
    "**/.ruff.toml",
    "mypy.ini",
    ".mypy.ini",
    "pytest.ini",
    ".pytest.ini",
    "pytest.toml",
    ".pytest.toml",
    "setup.cfg",
    "tox.ini",
    ".importlinter",
)
NO_PULL_REQUEST_RULE = "the ruleset has no pull_request rule"
NO_RULESET = "no ruleset targets the default branch"
_COMMENT = re.compile(r"\s+#.*$")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: object) -> set[str]:
    return {s for s in value if isinstance(s, str)} if isinstance(value, list) else set()


def _target_problems(ruleset: Mapping[str, object], default_branch: str) -> list[str]:
    ref_name = _mapping(_mapping(ruleset.get("conditions")).get("ref_name"))
    names = {"~DEFAULT_BRANCH", "~ALL", f"refs/heads/{default_branch}"}
    if names & _strings(ref_name.get("include")) and not names & _strings(ref_name.get("exclude")):
        return []
    return ["the ruleset does not target the default branch"]


def _pull_request_problems(params: Mapping[str, object]) -> list[str]:
    """Every Mode requires code-owner review, and none requires an approval count or approval of
    the most recent push."""
    holds = [
        (
            params.get("require_code_owner_review") is True,
            "the pull_request rule does not require code-owner review",
        ),
        (
            params.get("dismiss_stale_reviews_on_push") is True,
            "the pull_request rule does not dismiss stale approvals on push",
        ),
        (
            params.get("allowed_merge_methods") == ["squash"],
            "the pull_request rule must allow squash merges only",
        ),
        (
            params.get("required_review_thread_resolution") is True,
            "the pull_request rule does not require review threads to be resolved",
        ),
    ]
    return [problem for ok, problem in holds if not ok]


def _status_check_problems(params: Mapping[str, object]) -> list[str]:
    checks = params.get("required_status_checks")
    bound = isinstance(checks, list) and any(
        isinstance(check, Mapping)
        and check.get("context") == CI_JOB_NAME
        and check.get("integration_id") == GITHUB_ACTIONS_APP_ID
        for check in checks
    )
    if bound:
        return []
    return [
        f"the {CI_JOB_NAME} status check is not bound to GitHub Actions "
        f"(integration {GITHUB_ACTIONS_APP_ID})"
    ]


def _bypass_problems(actors: object) -> list[str]:
    found = (
        [
            (a.get("actor_id"), a.get("actor_type"), a.get("bypass_mode"))
            if isinstance(a, Mapping)
            else None
            for a in actors
        ]
        if isinstance(actors, list)
        else None
    )
    if found == [(ADMIN_ROLE_ID, "RepositoryRole", "pull_request")]:
        return []
    return ["the bypass list must hold only the admin role in pull_request mode"]


def _rules(ruleset: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    """The ruleset's rules: type -> parameters, empty for a rule such as deletion that has none."""
    rules = ruleset.get("rules")
    found: dict[str, Mapping[str, object]] = {}
    for entry in rules if isinstance(rules, list) else []:
        kind = _mapping(entry).get("type")
        if isinstance(kind, str):
            found[kind] = _mapping(_mapping(entry).get("parameters"))
    return found


def _one_ruleset_problems(ruleset: Mapping[str, object], default_branch: str) -> list[str]:
    rules = _rules(ruleset)
    pull_request = rules.get("pull_request")
    return [
        *_target_problems(ruleset, default_branch),
        *([] if ruleset.get("enforcement") == "active" else ["the ruleset is not active"]),
        *([NO_PULL_REQUEST_RULE] if pull_request is None else _pull_request_problems(pull_request)),
        *_status_check_problems(rules.get("required_status_checks", {})),
        *([] if "non_fast_forward" in rules else ["force pushes are not blocked"]),
        *([] if "deletion" in rules else ["deletion is not blocked"]),
        *_bypass_problems(ruleset.get("bypass_actors")),
    ]


def _closest(rulesets: Sequence[Mapping[str, object]], default_branch: str) -> list[str]:
    """No problem when one ruleset has none, because GitHub applies every ruleset that matches.
    Otherwise the problems of the ruleset with the fewest."""
    found = [_one_ruleset_problems(r, default_branch) for r in rulesets]
    return [] if any(not problems for problems in found) else min(found, key=len)


# GitHub counts an approval only from someone with write access to the repository, and the Reviewer
# App has Contents: read.
_NOT_FROM_THE_REVIEWER = (
    "which GitHub takes only from someone with write access and not from the Reviewer App, so "
    "every agent PR waits for a person; set the count to 0 and approval of the most recent push "
    "off, or use Walk (every_pr = true)"
)


def _requires_approval(count: object) -> bool:
    return isinstance(count, int) and not isinstance(count, bool) and count > 0


def _app_merge_problems(rulesets: Sequence[Mapping[str, object]], default_branch: str) -> list[str]:
    """The approvals that make every agent PR wait for a person in Flight with Agent identity,
    because GitHub takes neither from the Reviewer App. GitHub applies every active ruleset on the
    branch, so a requirement in any one of them applies. While approval of the most recent push is
    on, GitHub refuses the Worker App's merge on the Reviewer App's approval even at a count of 0;
    whether a count above 0 alone blocks it is unconfirmed."""
    params = [
        _rules(ruleset).get("pull_request", {})
        for ruleset in rulesets
        if ruleset.get("enforcement") == "active" and not _target_problems(ruleset, default_branch)
    ]
    blocks = [
        (
            any(_requires_approval(p.get("required_approving_review_count")) for p in params),
            "the pull_request rule requires an approval, " + _NOT_FROM_THE_REVIEWER,
        ),
        (
            any(p.get("require_last_push_approval") is True for p in params),
            "the pull_request rule requires approval of the most recent push, "
            + _NOT_FROM_THE_REVIEWER,
        ),
    ]
    return [problem for blocked, problem in blocks if blocked]


def ruleset_problems(
    rulesets: Sequence[Mapping[str, object]],
    default_branch: str,
    *,
    every_pr: bool,
    agent_identity: bool,
) -> list[str]:
    """What keeps the default branch from matching the ruleset the Mode needs.

    rulesets are in the shape GET /repos/{o}/{r}/rulesets/{id} returns. Every setup needs the same
    ruleset, code-owner review included. Walk, and Flight without Agent identity, accept a ruleset
    with or without an approval count or approval of the most recent push. Flight with Agent
    identity needs every enforced ruleset without them.
    """
    if not rulesets:
        return [NO_RULESET]
    problems = _closest(rulesets, default_branch)
    if every_pr or not agent_identity:
        return problems
    return [*problems, *_app_merge_problems(rulesets, default_branch)]


@dataclass(frozen=True)
class _Line:
    number: int  # from 1, as GitHub counts CODEOWNERS lines
    pattern: str
    owners: tuple[str, ...]  # in lower case


@dataclass(frozen=True)
class CodeownersError:
    """One error that GET /repos/{o}/{r}/codeowners/errors reports, such as an unknown owner."""

    line: int
    kind: str
    suggestion: str | None


def _active_lines(text: str) -> list[_Line]:
    """Each active CODEOWNERS line, the owners in lower case.

    GitHub compares logins, an organisation's included, without regard to case; doctor compares a
    team's name the same way. Blank lines and comments, whole-line or after the owners, are not
    active.
    """
    lines: list[_Line] = []
    # Only a newline ends a line, as in git; str.splitlines also ends one at \f, \x85 or U+2028.
    for number, raw in enumerate(text.split("\n"), start=1):
        line = _COMMENT.sub("", raw.strip())
        if line and not line.startswith("#"):
            pattern, *owners = line.split()
            lines.append(_Line(number, pattern, tuple(owner.lower() for owner in owners)))
    return lines


def _protected_paths(stack: Stack) -> tuple[str, ...]:
    return (*PROTECTED_PATHS, *(PYTHON_PROTECTED_PATHS if stack == "python" else ()))


def _applied(lines: Sequence[_Line]) -> dict[str, _Line]:
    """The line GitHub applies for each pattern, which is the pattern's last line, keyed by the
    pattern without a leading /."""
    return {line.pattern.removeprefix("/"): line for line in lines}


def _walk_problems(lines: Sequence[_Line], code_owner: str) -> list[str]:
    wanted = f"* {code_owner}"
    if len(lines) != 1:
        return [f"Walk needs exactly one active CODEOWNERS line, {wanted}; found {len(lines)}"]
    if (lines[0].pattern, lines[0].owners) != ("*", (code_owner.lower(),)):
        return [f"the one active CODEOWNERS line is not {wanted}"]
    return []


def _protected_set_problems(lines: Sequence[_Line], code_owner: str, stack: Stack) -> list[str]:
    problems: list[str] = []
    if any(line.pattern == "*" for line in lines):
        problems.append(
            "with every_pr = false, CODEOWNERS must have no * line; only the Protected set is owned"
        )
    owned = {path: line.owners for path, line in _applied(lines).items()}
    required = _protected_paths(stack)
    unowned = [path for path in required if owned.get(path) != (code_owner.lower(),)]
    if unowned:
        problems.append(f"CODEOWNERS must name only {code_owner} for: {', '.join(unowned)}")
    return problems


def codeowners_problems(text: str, every_pr: bool, code_owner: str, stack: Stack) -> list[str]:
    """What keeps CODEOWNERS from matching the Mode: the * line when every_pr is true, the
    Protected set otherwise. code_owner is [github] code_owner, with its @: a login or an
    organisation's team."""
    lines = _active_lines(text)
    if every_pr:
        return _walk_problems(lines, code_owner)
    return _protected_set_problems(lines, code_owner, stack)


def _checked_lines(text: str, every_pr: bool, stack: Stack) -> set[int]:
    """The numbers of the lines codeowners_problems compares with the code owner: every active line
    when every_pr is true, the line GitHub applies for each Protected path otherwise."""
    lines = _active_lines(text)
    if every_pr:
        return {line.number for line in lines}
    applied = _applied(lines)
    return {applied[path].number for path in _protected_paths(stack) if path in applied}


def _line_numbers(numbers: Sequence[int]) -> str:
    if len(numbers) == 1:
        return f"line {numbers[0]}"
    *others, last = numbers
    return f"lines {', '.join(map(str, others))} and {last}"


def codeowners_error_problems(
    errors: Sequence[CodeownersError], text: str, every_pr: bool, stack: Stack
) -> list[str]:
    """GitHub's report of the errors on the lines of text that codeowners_problems checks: one
    problem for each kind and suggestion, which names its lines in order."""
    checked = _checked_lines(text, every_pr, stack)
    grouped: dict[tuple[str, str | None], set[int]] = {}
    for error in sorted(errors, key=lambda error: error.line):
        if error.line in checked:
            grouped.setdefault((error.kind, error.suggestion), set()).add(error.line)
    problems: list[str] = []
    for (kind, suggestion), lines in grouped.items():
        reported = f"GitHub reports {kind} on {_line_numbers(sorted(lines))}"
        problems.append(f"{reported}: {suggestion}" if suggestion else reported)
    return problems


def installation_problems(found: Mapping[str, object], role: Role) -> list[str]:
    """How an installation's permissions differ from the role's, which must match exactly."""
    granted = found.get("permissions")
    if not isinstance(granted, Mapping):
        return ["the installation lists no permissions"]
    wanted = APP_PERMISSIONS[role]
    problems: list[str] = []
    for name, level in sorted(wanted.items()):
        has = granted.get(name)
        if has is None:
            problems.append(f"{name}: {level} is not granted")
        elif has != level:
            problems.append(f"{name} is {has}, not {level}")
    problems.extend(
        f"{name}: {has} must not be granted"
        for name, has in sorted(granted.items(), key=lambda entry: str(entry[0]))
        if name not in wanted
    )
    return problems
