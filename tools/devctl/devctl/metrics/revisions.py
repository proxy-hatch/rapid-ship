"""Review rounds ending in changes requested, deduplicated by head commit."""

from datetime import datetime
from typing import cast

from devctl.metrics.github import GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.window import Window

REVIEWS = "[.[] | {state, commit_id, submitted_at}]"
EVENTS = (
    "[.[] | {event, created_at, dismissed_review: {state: .dismissed_review.state, "
    "commit_id: .dismissed_review.commit_id}}]"
)


def revisions(reader: GitHubReader, window: Window) -> Measured:
    items = []
    total = 0
    for pr in window.prs:
        heads: set[str] = set()
        dismissed = False
        for review in reader.pages(f"pulls/{pr.number}/reviews", jq=REVIEWS):
            dismissed |= review["state"] == "DISMISSED"
            submitted = review.get("submitted_at")
            if (
                review["state"] == "CHANGES_REQUESTED"
                and isinstance(submitted, str)
                and pr.merged_at is not None
                and datetime.fromisoformat(submitted.replace("Z", "+00:00")) <= pr.merged_at
            ):
                heads.add(cast("str", review["commit_id"]))
        if dismissed:
            for event in reader.pages(f"issues/{pr.number}/events", jq=EVENTS):
                data = event.get("dismissed_review")
                if (
                    event["event"] == "review_dismissed"
                    and isinstance(data, dict)
                    and str(data.get("state")).lower() == "changes_requested"
                ):
                    heads.add(data["commit_id"])
        if heads:
            items.append({"pr": pr.number, "state": "counted", "revisions": len(heads)})
        total += len(heads)
    return Measured(
        total / len(window.prs),
        items=tuple(sorted(items, key=lambda item: -cast("int", item["revisions"]))),
    )
