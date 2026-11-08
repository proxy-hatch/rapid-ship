"""Review rounds ending in changes requested, deduplicated by head commit."""

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from devctl.metrics.github import GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.window import Window

REVIEWS = "[.[] | {id, state, commit_id, submitted_at}]"
EVENTS = (
    "[.[] | {event, created_at, dismissed_review: {state: .dismissed_review.state, "
    "review_id: (.dismissed_review.review_id // .dismissed_review.id)}}]"
)


def _is_pre_merge(submitted: object, merged_at: datetime | None) -> bool:
    return (
        isinstance(submitted, str)
        and merged_at is not None
        and datetime.fromisoformat(submitted.replace("Z", "+00:00")) <= merged_at
    )


def revisions(reader: GitHubReader, window: Window) -> Measured:
    items = []
    total = 0
    for pr in window.prs:
        heads: set[str] = set()
        dismissed_reviews: dict[object, Mapping[str, object]] = {}
        for review in reader.pages(f"pulls/{pr.number}/reviews", jq=REVIEWS):
            if review["state"] == "DISMISSED" and review.get("id") is not None:
                dismissed_reviews[review["id"]] = review
            if review["state"] == "CHANGES_REQUESTED" and _is_pre_merge(
                review.get("submitted_at"), pr.merged_at
            ):
                heads.add(cast("str", review["commit_id"]))
        if dismissed_reviews:
            for event in reader.pages(f"issues/{pr.number}/events", jq=EVENTS):
                data = event.get("dismissed_review")
                if (
                    event["event"] == "review_dismissed"
                    and isinstance(data, dict)
                    and str(data.get("state")).lower() == "changes_requested"
                ):
                    orig_review = dismissed_reviews.get(data.get("review_id"))
                    if orig_review is not None and _is_pre_merge(
                        orig_review.get("submitted_at"), pr.merged_at
                    ):
                        heads.add(cast("str", orig_review["commit_id"]))
        if heads:
            items.append({"pr": pr.number, "state": "counted", "revisions": len(heads)})
        total += len(heads)
    return Measured(
        total / len(window.prs),
        items=tuple(sorted(items, key=lambda item: -cast("int", item["revisions"]))),
    )
