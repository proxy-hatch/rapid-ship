---
name: rs-health
description: Audit a repository against rapid-ship's standards and return proposed tasks.
disable-model-invocation: true
---

# Audit repository health

Read the code, CI configuration, README.md, ARCHITECTURE.md, directory guides, Patterns and exceptions. Run `references/audit.md` over the whole repository. Do not edit the repository.

Run the following reads. Set `REPO` to the GitHub owner and repository and `PR` to each merged pull request number. Read recent runs, merged pull requests, each pull request, its reviews and its review comments.

```sh
./devctl doctor
./devctl check
gh run list --repo "$REPO"
gh pr list --repo "$REPO" --state merged
gh pr view "$PR" --repo "$REPO"
gh api "repos/$REPO/pulls/$PR/reviews"
gh api "repos/$REPO/pulls/$PR/comments"
```

Treat failed or blocked reads as unknown, never zero. Name each unread source and propose no task from it. Unavailable GitHub authentication makes its reads unknown. Missing gitleaks makes the affected check unknown. An empty successful read showing no merged PRs is distinct from an unread source.

Group findings by area and propose tasks using `references/proposed-task.md`. Ask the owner which to keep. Ask which tracker to use when the Harness reaches more than one; when it reaches none, leave the picked tasks in the conversation. State each external write before making it. With Agent identity on, create each picked GitHub issue with:

```sh
./devctl as worker gh issue create --repo "$REPO"
```

With Agent identity off, use the same command without `./devctl as worker`. For another tracker use the interface the Harness reaches. Record no tracker setting.
