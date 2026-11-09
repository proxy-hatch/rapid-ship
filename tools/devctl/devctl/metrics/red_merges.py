"""The earliest push run's first attempt determines each merge's CI result."""

from typing import cast

from devctl.metrics.github import GitHubError, GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.window import Window

CI_WORKFLOW = "devctl-check.yml"
RUNS = "[.workflow_runs[] | {id, run_number, run_attempt, conclusion}]"


def red_merges(reader: GitHubReader, window: Window) -> Measured:
    items: list[dict[str, object]] = []
    red = unknown = 0
    for pr in window.prs:
        try:
            runs = list(
                reader.pages(
                    f"actions/workflows/{CI_WORKFLOW}/runs?head_sha={pr.merge_commit}&event=push",
                    jq=RUNS,
                )
            )
        except GitHubError as error:
            if error.status != 404:
                raise
            return Measured(
                0,
                unknown=len(window.prs),
                items=tuple(
                    {"pr": p.number, "state": "unknown", "detail": f"no {CI_WORKFLOW} workflow"}
                    for p in window.prs
                ),
            )
        conclusion = None
        if runs:
            first = min(runs, key=lambda run: cast("int", run["run_number"]))
            if cast("int", first["run_attempt"]) > 1:
                first = cast(
                    "dict[str, object]",
                    reader.get(f"actions/runs/{first['id']}/attempts/1", jq="{conclusion}"),
                )
            conclusion = first["conclusion"]
        if conclusion in ("failure", "timed_out"):
            red += 1
            items.append({"pr": pr.number, "state": "counted"})
        elif conclusion != "success":
            unknown += 1
            detail = f"push run {conclusion or 'pending'}" if runs else "no push run"
            items.append({"pr": pr.number, "state": "unknown", "detail": detail})
    return Measured(red, unknown=unknown, items=tuple(items))
