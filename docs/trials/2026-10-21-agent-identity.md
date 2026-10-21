# Agent identity, ruleset and doctor trial

Trial date: 2026-10-21. Live: the owner ran every step in their own terminal, on GitHub, with their own sign-in, Apps and Keychain. This report is written from a record of the owner's pasted terminal output, and its [rerun](#rerun-of-the-pending-steps) from a script's log. No agent ran a trial step. The trial is Task 10 of [plan 4](../superpowers/plans/2026-10-16-doctor-and-agent-identity.md).

## How to read this

- Each result is live unless it is marked offline. "Not recorded" means that the owner's record does not hold that output. This report does not guess it.
- The owner reran the pending steps at 20:26 CST the same day. The [rerun](#rerun-of-the-pending-steps) has its own section, and the step sections before it keep the first pass's results as recorded. `$TRIALS` is the rerun's temporary directory; the log's local paths are not recorded.
- `$PLAN4` is the owner's checkout of `main` at `0e1d6d0`, tag `v0.1.0`. The trial ran `rapid-ship` and the Kit from it.
- The commands are Task 10's, as the plan wrote them at `0e1d6d0`. Where the owner ran something else, the step says so.
- The scratch repositories are `proxy-hatch/rs-trial`, public, and `proxy-hatch/rs-trial-private`, private. The owner's login is `proxy-hatch`.
- No token, private key, client secret or email address is recorded.

## Summary

- **The ruleset's approval settings.** In Flight with Agent identity, the Worker App's pull request #3 had the Reviewer App's approval and a passing `devctl check`. GitHub refused to merge it under rs-setup's ruleset, with an approval count of 1 and approval of the most recent push required (Step 11). It refused again with the count at 0 (Step 11a). With approval of the most recent push also off, the Worker App merged it (the owner's experiment A, beyond the plan). So GitHub does not take the Reviewer App's approval as approval of the most recent push. Whether GitHub counts that approval toward a count of 1 is not isolated, because last-push approval was on at that attempt too and `reviewDecision` was not recorded.
- **The owner's decision**, made on 2026-10-21 from this result: the ruleset that rs-setup applies sets `required_approving_review_count` 0 and `require_last_push_approval` false in every Mode. Code-owner review, dismissal of stale approvals, review-thread resolution, squash merges only, the required `devctl check`, the force-push and deletion rules and the admin bypass stay.
- **Walk with Agent identity** behaved as the plan expected (Step 10). `devctl as` pushed and opened pull request #1 as the Worker App and approved it as the Reviewer App. devctl refused `--admin`, and GitHub refused the merge until the owner approved and resolved a review thread.
- **doctor** read both Apps on `rs-trial` and reported their four items ok (Step 5). The installation object carries `app_slug`. The applied ruleset read back as ok (Step 9). On the private repository, doctor reported the GitHub Free 403 for rulesets (Step 6).
- **Plan defects.** Step 4's settings edit was prose above its code block, so it did not run. Steps 3 and 5 name the Keychain items as they were before their rename. The steps run from "this plan's worktree", which no longer exists. Step 11a changes only the count.
- **Not run in the first pass:** Step 11a's second block, the `$PR4` pair; Step 12, the change request and the workflow change; Step 13, `doctor --skills`. Step 14's clean-up was deferred, so `rs-trial` stayed available.
- **The rerun**, at 20:26 CST under the decided ruleset, ran those steps, Step 5's key read, and a code-owner step that plan 4 added:
  - A process the owner ran read both App keys, exit 0 each, and macOS showed no dialog. Any process the owner runs can read both keys.
  - GitHub refused the Worker App's merge of #4 while `devctl check` was queued, and merged it once the check passed. GitHub enforces the required check.
  - Code-owner review holds at a count of 0. GitHub refused the Worker App's merge of #5, a change to `docs/AGENTS.md`, with the Reviewer App's approval and a passing check. It merged #5 after the owner approved.
  - At a count of 0, `reviewDecision` was `""` in every read, so only `mergeStateStatus` showed GitHub's block. The Reviewer App's change request left #6 `CLEAN`: on its own, it does not block a merge.
  - GitHub accepted the Worker App's push of a branch whose only new commit merged in a workflow change already on `main`. Step 12 expected a refusal.
  - `doctor --skills` reported the skills item as Step 13 expects. doctor does not print the model ID that `PROBE_MODEL`, `haiku`, resolved to.
  - Step 14 closed the open trial pull request. `rs-trial` and `rs-trial-private` stay.
- **Still not recorded:** the owner's GitHub plan, and items of Steps 2, 3, 6, 7, 9, 10, 11, 11a and 13 that neither pass recorded. Plan 4's Verification record lists them.

## Setup and versions

- Kit and `rapid-ship`: 0.1.0, from `$PLAN4` at `0e1d6d0` (`v0.1.0`).
- Apps: the Worker App, ID 5376519, `proxy-hatch-rs-worker`, and the Reviewer App, ID 5376520, `proxy-hatch-rs-reviewer`. The owner created both on 2026-10-19, before this trial. On 2026-10-21 the owner stored their keys again under the Keychain items `rapid-ship/<role>-app/<App ID>`, and later deleted the items under the old names.
- Not recorded for the first pass: the macOS, git, gh, uv and Claude Code versions, the owner's GitHub plan, and the output of `git -C "$PLAN4" rev-parse HEAD`. Step 6's 403 is what doctor reports on GitHub Free.
- The rerun recorded the versions it ran with: macOS 15.7.7, git 2.39.5 (Apple Git-154), gh 2.102.1, uv 0.11.0 and Claude Code 2.1.304. Its `gh api user --jq .plan.name` printed an empty line, so the GitHub plan is still not recorded. Its clone of `rs-trial` vendored devctl 0.1.0.

## Steps

### Step 1: accept the outside changes

The owner accepted the list and went on. Both Apps already existed, so the list's first change was already made.

### Step 2: record the versions and prepare `rs-trial`

The owner ran Step 2, from `gh repo create "$OWNER/rs-trial" --public --add-readme --clone` to the push of `main`. Not recorded: the versions, the GitHub plan, the fast check's exit code and every other output. Step 5's doctor ran in the resulting clone.

### Step 3: create the Apps

The Apps existed from 2026-10-19. Not recorded: whether Step 3's command ran, and its output, whether GitHub accepted the manifest without `hook_attributes`, whether each App's settings page shows no webhook, and whether `security` showed a dialog while storing each key. The step's two `security find-generic-password -s rapid-ship/<role>-app` lines name items that no longer exist (Step 5).

### Step 4: install the Apps and record them

```sh
WORKER_ID=$(python3 -c 'import tomllib; print(tomllib.load(open(".rapid-ship/project.toml", "rb"))["github"]["worker_app_id"])')
REVIEWER_ID=$(python3 -c 'import tomllib; print(tomllib.load(open(".rapid-ship/project.toml", "rb"))["github"]["reviewer_app_id"])')
git commit -am "Record the Worker and Reviewer Apps" && git push origin main
```

The first attempt failed. The step asks for the edit of `.rapid-ship/project.toml` in prose above its code block, so the owner ran only the block. `worker_app_id` stayed 0, and `git commit` printed "nothing to commit". `WORKER_ID` was then empty, so Step 6's mint failed with `ValueError: invalid literal for int() with base 10: ''`.

The owner then wrote the four values with a one-line `python3` command, whose text was not recorded: `worker_app_id` 5376519, `worker_app_slug` `"proxy-hatch-rs-worker"`, `reviewer_app_id` 5376520 and `reviewer_app_slug` `"proxy-hatch-rs-reviewer"`. The owner reran the block, and the commit and push went through; their exit codes were not recorded. Step 5 shows both Apps installed on `rs-trial`.

### Step 5: doctor reads both Apps

```sh
./devctl doctor; echo "exit $?"
uv run --project tools/devctl --frozen python -c 'import sys; from devctl.github.app import installation; print(sorted(installation("worker", sys.argv[1], int(sys.argv[2]))))' "$OWNER/rs-trial" "$WORKER_ID"
security find-generic-password -s rapid-ship/worker-app -w >/dev/null; echo "read exit $?"
```

doctor printed `doctor: 13 ok, 4 missing, 0 unknown` and exited 1.

- Worker App installation, ok: "proxy-hatch-rs-worker is installed on proxy-hatch/rs-trial with exactly the worker App's permissions". Reviewer App installation, ok, with the same detail for `proxy-hatch-rs-reviewer`.
- Worker App key and Reviewer App key, ok: "Keychain item found; token minted".
- Missing: `core.hooksPath`, a setting of the local clone; ruleset, "no ruleset targets the default branch"; delete branch on merge; and fork PR workflow approval, whose detail names `approval_policy` `first_time_contributors`. All four were expected before Steps 7 and 8.

The installation object's keys: `access_tokens_url`, `account`, `app_id`, `app_slug`, `client_id`, `created_at`, `events`, `has_multiple_single_files`, `html_url`, `id`, `permissions`, `repositories_url`, `repository_selection`, `single_file_name`, `single_file_paths`, `suspended_at`, `suspended_by`, `target_id`, `target_type`, `updated_at`. `app_slug` is there, as Checked facts expect.

The key read printed "The specified item could not be found in the keychain" and `read exit 44`. It names the item as it was before the rename, and that item no longer exists; the item is now `rapid-ship/worker-app/<App ID>`. The corrected read, `security find-generic-password -s "rapid-ship/worker-app/$WORKER_ID" -w`, was suggested. Its exit code, and whether a macOS dialog appeared, were not recorded. The rerun read both items, exit 0 each, and macOS showed no dialog (below).

### Step 6: a second, private repository

The owner created `rs-trial-private`, ran `rapid-ship init` and pushed `main`. Not recorded: the output and exit code of `rapid-ship app --repository "$OWNER/rs-trial-private"`, and whether the install URL added the repository to the existing installation.

doctor in `rs-trial-private` printed `doctor: 10 ok, 3 missing, 0 unknown` and exited 1.

- ruleset, missing: "rulesets need a public repository or a paid GitHub plan (GitHub returned 403)", as expected on GitHub Free.
- fork PR workflow approval: "not applicable: private repository".
- `core.hooksPath` and delete branch on merge: missing.
- No `agent identity` item, because this repository's `project.toml` records no Apps.

The mint first failed with Step 4's `ValueError`. After Step 4's fix it printed `minted`.

### Step 7: apply the repository settings to `rs-trial`

The owner ran both `gh api` calls. Their output and exit codes were not recorded. Step 9's doctor reports both settings ok.

### Step 8: apply the ruleset

The owner applied the ruleset that the plan index specified when the trial ran (approval count 1, last-push approval on), with Step 8's `gh api --method POST "repos/$OWNER/rs-trial/rulesets"`. `RULESET_ID` is 25531114.

### Step 9: read the ruleset back and keep it as the fixture

```sh
./devctl doctor; echo "exit $?"
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq 'del(.node_id, ._links, .created_at, .updated_at, .current_user_can_bypass) | .id = 9 | .source = "o/r"' > "$PLAN4/tests/devctl/fixtures/github/ruleset.json"
(cd "$PLAN4" && uv run pytest tests/devctl/test_devctl_doctor_github.py tests/devctl/test_devctl_doctor_github_limits.py -q)
```

doctor printed `16 ok, 1 missing, 0 unknown`; only `core.hooksPath` is missing. The exit code was not recorded.

- ruleset, ok: "an active ruleset on main has every setting rs-setup applies".
- CODEOWNERS, ok: it matches Walk.
- delete branch on merge, ok.
- fork PR workflow approval, ok: "workflows from all outside contributors need approval".
- The four `agent identity` items, ok.

Not recorded: whether GitHub's web interface names `actor_id` 5 as the admin role. Step 11a later wrote its own read-back to the same path, so Step 9's read-back is not kept.

The tests first failed to start with `Failed to spawn: pytest`. The `.venv` of the owner's checkout was created when the repository lived at an earlier path, so its console-script launchers pointed at a missing interpreter. This is an environment issue, not a product defect, and `uv sync --locked --reinstall` fixed it. Then, offline against the live read-back: `66 passed in 14.78s`.

### Step 10: Walk with Agent identity

| Command | Exit | Result |
| --- | --- | --- |
| `./devctl as worker push` | 0 | pushed `trial-walk` |
| `./devctl as worker gh pr create ...` | 0 | created `proxy-hatch/rs-trial` pull request #1 |
| `gh pr view "$PR" --json author --jq .author.login` | not recorded | `app/proxy-hatch-rs-worker` |
| `./devctl as reviewer gh pr review "$PR" --approve ...` | 0 | a review by `proxy-hatch-rs-reviewer`, state `APPROVED`, `authorAssociation` `NONE`, on commit `35e03aa` |
| `gh pr view "$PR" --json reviews,reviewDecision,mergeStateStatus` | not recorded | `reviewDecision` `REVIEW_REQUIRED`, `mergeStateStatus` `BLOCKED` |
| `./devctl as worker gh pr merge "$PR" --squash --admin` | 1 | refused by devctl before anything ran: "devctl as: refused: gh pr merge --admin is not allowed; merge through the ruleset" |
| `./devctl as worker gh pr merge "$PR" --squash` | 1 | refused by GitHub: "the base branch policy prohibits the merge" |

The author login is gh's JSON form of the Worker App's bot account; the plan expected `<worker slug>[bot]`. `REVIEW_REQUIRED` is expected, because CODEOWNERS `*` needs the owner.

The rest of Step 10 was "as expected", in the owner's words. The owner commented on the diff, which opened a thread, and approved. GitHub refused the merge while the thread was unresolved. After the owner resolved it, the Worker App merged the pull request, and its head branch was deleted. The output and exit codes of these commands were not recorded.

### Step 11: Flight with Agent identity

The owner moved `rs-trial` to Flight through their own pull request. Not recorded: the `grep -c` count of the Protected-set lines, and doctor's output after the move.

| Command | Exit | Result |
| --- | --- | --- |
| `./devctl as worker push` | not recorded | `trial-agent` reached GitHub, since pull request #3 opened from it |
| `./devctl as worker gh pr create ...` | 0 | pull request #3, by the Worker App |
| `./devctl as reviewer gh pr review "$PR2" --approve ...` | 0 | the Reviewer App's approval |
| `./devctl as worker gh pr merge "$PR2" --squash`, check pending | 1 | refused by GitHub: "the base branch policy prohibits the merge" |
| `gh pr checks "$PR2" --watch` | not recorded | `devctl check/devctl check (pull_request)` passed in 7s |
| `./devctl as worker gh pr merge "$PR2" --squash`, check passed | 1 | refused by GitHub: "the base branch policy prohibits the merge" |

Not recorded: `reviewDecision` and `mergeStateStatus` before each merge attempt.

Result: GitHub refused the merge with only the Reviewer App's approval, under a count of 1 with approval of the most recent push required. The owner's record reads this as GitHub not counting the approval toward the count. Without `reviewDecision`, the refusal does not separate the count from last-push approval, and Step 11a shows that last-push approval blocks on its own. Following the plan, the owner ran Step 11a.

The first attempt does not show GitHub enforcing `devctl check`. The check was pending, but the approval requirement was unmet too, so either could have caused the refusal.

### Step 11a: set the count to 0 and read it back

```sh
perl -pi -e 's/"required_approving_review_count": 1/"required_approving_review_count": 0/' "$TRIALS/ruleset.json"
gh api --method PUT "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --input "$TRIALS/ruleset.json"
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq '.rules[] | select(.type == "pull_request") | .parameters.required_approving_review_count'
gh api "repos/$OWNER/rs-trial/rulesets/$RULESET_ID" --jq 'del(.node_id, ._links, .created_at, .updated_at, .current_user_can_bypass) | .id = 9 | .source = "o/r"' > "$PLAN4/tests/devctl/fixtures/github/ruleset.json"
./devctl as worker gh pr merge "$PR2" --squash; echo "merge exit $?"
```

Not recorded: the `PUT` call's output and the first read-back's value. The full read-back holds the count of 0. Its `pull_request` rule:

```json
{
  "allowed_merge_methods": ["squash"],
  "dismiss_stale_reviews_on_push": true,
  "require_code_owner_review": true,
  "require_extra_approval_for_unattributed_changes": true,
  "require_last_push_approval": true,
  "required_approving_review_count": 0,
  "required_review_thread_resolution": true,
  "required_reviewers": []
}
```

Its `required_status_checks` rule also carries `"do_not_enforce_on_create": false`. Pull request #3 then had `mergeStateStatus` `BLOCKED`, `reviewDecision` `""` and one review, `APPROVED`, by `proxy-hatch-rs-reviewer`. `reviewDecision` is empty because the ruleset no longer requires an approval count.

The merge: refused by GitHub, "the base branch policy prohibits the merge", exit 1. The owner retried after reading the state above, with the same message and exit 1.

As Step 11a says, the trial stopped here, and the owner decides the ruleset before Step 17. Its second block, the `$PR4` pair that would show GitHub refusing a merge while `devctl check` is pending, did not run. The rerun ran it (below).

### Experiments A and B, beyond the plan

The owner ran two one-variable experiments on `rs-trial`'s ruleset after Step 11a. Neither is in the plan.

- **A.** `require_last_push_approval` set to false, everything else as in Step 11a: the count 0, and `require_extra_approval_for_unattributed_changes` true. `./devctl as worker gh pr merge 3 --squash` merged pull request #3, exit 0. So approval of the most recent push was what still blocked the merge: GitHub does not take the Reviewer App's approval as approval of the most recent push. `require_extra_approval_for_unattributed_changes` true did not block this merge. It is the rulesets option "Require an additional approval for unattributed Copilot pull requests", on by default: an unattributed Copilot pull request needs one more approval than the count. GitHub documents that it has no effect at a count of 0 ([available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)).
- **B.** `require_extra_approval_for_unattributed_changes` also set to false. It ran after #3 had merged, so it tested nothing: gh printed "Pull request proxy-hatch/rs-trial#3 was already merged", exit 0.

Ruleset 25531114 on `rs-trial` was left with the count 0, `require_last_push_approval` false, `require_extra_approval_for_unattributed_changes` false, and the rest as Step 11a read it back. The rerun's `PUT` set the last of these back to `true` (below).

### Step 12: a Reviewer App change request, and a workflow change

Not run in the first pass. The rerun ran it (below).

### Step 13: `doctor --skills` live

Not run in the first pass, so `PROBE_MODEL`, `haiku`, stayed unconfirmed. The rerun ran it (below).

### Step 14: clean up

Deferred in the first pass, so `rs-trial` stayed available. The Apps stay as the owner's real Apps. The rerun closed the open trial pull request (below).

## The decision this trial led to

With Agent identity in Flight, an App-only merge needed `required_approving_review_count` 0 and `require_last_push_approval` false. A count of 1 failed, and a count of 0 with last-push approval on failed. On 2026-10-21 the owner decided that rs-setup's ruleset sets both, in every Mode. Spec 1 section 8, step 7 states the ruleset.

The cost the owner accepted: in a team, a code owner who pushed the last commit to an agent's pull request can approve it themselves. Dismissing stale approvals still voids an approval given before a new push. Code-owner review still holds, so CODEOWNERS alone decides who must approve: the owner for every path in Walk, and for the Protected set in Flight. In Flight with Agent identity, GitHub then requires no approval for a pull request outside the Protected set. The same day, the owner decided that, with Agent identity, the merge guard requires the Reviewer App's approval of the head commit, beside a passing `devctl check` and no Protected paths (plan 5). The first pass did not observe GitHub enforcing code-owner review at a count of 0; the rerun showed that it holds (Limits).

doctor follows the decision. It requires neither setting in any Mode, and in Flight with Agent identity it reports either one on as missing. Its fixture, `tests/devctl/fixtures/github/ruleset.json`, is Step 11a's read-back with `require_last_push_approval` set to false by hand: the state under which experiment A merged.

## Rerun of the pending steps

Rerun: 2026-10-21 at 20:26 CST, live. The owner ran a script in their own terminal, with their own sign-in, Apps and Keychain. It cloned `proxy-hatch/rs-trial` into a new temporary directory, `$TRIALS`, and ran what plan 4's Verification record listed as pending: Step 5's key read, Step 11a's second block, a code-owner step at an approval count of 0, and Steps 12 to 14. It wrote every command, its output and its exit code to a log, and this section is written from that log. The script asked the owner before each write made as the owner and before `doctor --skills`, and logged each answer. It sent each key to `/dev/null`. The log's local paths are not recorded here.

### Rerun setup

| Command | Exit | Result |
| --- | --- | --- |
| `sw_vers -productVersion` | 0 | `15.7.7` |
| `git --version` | 0 | `git version 2.39.5 (Apple Git-154)` |
| `gh --version` | 0 | `gh version 2.102.1 (2026-10-20)` |
| `uv --version` | 0 | `uv 0.11.0 (Homebrew 2026-03-23 aarch64-apple-darwin)` |
| `claude --version` | 0 | `2.1.304 (Claude Code)` |
| `gh api user --jq .plan.name` | 0 | an empty line, so the GitHub plan is still not recorded |
| `gh repo clone proxy-hatch/rs-trial "$TRIALS/rs-trial" -- --quiet` | 0 | the clone that the later steps ran in |
| `git log -1 --oneline` | 0 | `7ca4447 Flight trial change (#3)` |
| `./devctl --version` | 0 | `devctl 0.1.0` |

The script then wrote Step 10's pull request body to `$TRIALS/pr-body.md`.

### Step 5's key read

| Command | Exit | Result |
| --- | --- | --- |
| `security find-generic-password -s rapid-ship/worker-app/5376519 -w >/dev/null` | 0 | the owner answered `n` to "Did macOS show a dialog for the Worker App's key?" |
| `security find-generic-password -s rapid-ship/reviewer-app/5376520 -w >/dev/null` | 0 | the owner answered `n` for the Reviewer App's key |

Result: a process the owner ran read both App keys, and macOS showed no dialog. Any process the owner runs can read both keys, as Spec 1 section 6 states.

### The decided ruleset

The script wrote Step 8's ruleset with Step 11a's two changes, the count 0 and `require_last_push_approval` false, applied it to ruleset 25531114 and read it back:

```sh
gh api --method PUT repos/proxy-hatch/rs-trial/rulesets/25531114 --input "$TRIALS/ruleset.json" --jq .id
gh api repos/proxy-hatch/rs-trial/rulesets/25531114 --jq '.rules[] | select(.type == "pull_request") | .parameters | .required_approving_review_count, .require_last_push_approval, .require_extra_approval_for_unattributed_changes, .require_code_owner_review'
```

The `PUT` printed `25531114`, exit 0. The read-back printed `0`, `false`, `true` and `true`, exit 0.

Result: the decided ruleset is applied. Its file leaves out `require_extra_approval_for_unattributed_changes`, which read back `true`, so the `PUT` reset experiment B's `false`. The steps below ran under the `pull_request` settings with which experiment A merged #3.

### Step 11a, second block: the pending-check pair

From `main` at `7ca4447`, the script appended a line to README.md on the branch `trial-agent-zero-202640` and committed it.

| Command | Exit | Result |
| --- | --- | --- |
| `./devctl as worker push` | 0 | pushed `trial-agent-zero-202640` |
| `./devctl as worker gh pr create ...` | 0 | pull request #4 |
| `./devctl as reviewer gh pr review 4 --approve ...` | 0 | the Reviewer App's approval |
| `gh pr view 4 --json reviewDecision,mergeStateStatus,statusCheckRollup` | 0 | `mergeStateStatus` `BLOCKED`, `reviewDecision` `""`, and the `devctl check` run `QUEUED` |
| `./devctl as worker gh pr merge 4 --squash` | 1 | refused by GitHub: "Pull request proxy-hatch/rs-trial#4 is not mergeable: the base branch policy prohibits the merge." |
| `gh pr checks 4 --watch` | 0 | `devctl check` passed in 9s |
| `./devctl as worker gh pr merge 4 --squash` | 0 | merged |
| `gh pr view 4 --json state,mergedAt` | 0 | `MERGED` at 2026-10-21T12:28:29Z |

Result: GitHub enforces a pending `devctl check`. #4 changed README.md, which has no code owner in Flight, and had the Reviewer App's approval. GitHub refused its merge while the run was queued, and merged it once the check passed.

### Code-owner review at an approval count of 0

The precondition held. `git pull --ff-only` brought `main` to `aa9dd24`, #4's merge. On `main`, CODEOWNERS line 18 read `/**/AGENTS.md @proxy-hatch`, an active line that gives `docs/AGENTS.md` to the owner, and the script printed `require_code_owner_review: true`. The script read both through `gh api` and printed no exit code for them.

The script appended a line to `docs/AGENTS.md` on the branch `trial-code-owner-202640` and committed it.

| Command | Exit | Result |
| --- | --- | --- |
| `./devctl as worker push` | 0 | pushed `trial-code-owner-202640` |
| `./devctl as worker gh pr create ...` | 0 | pull request #5 |
| `./devctl as reviewer gh pr review 5 --approve ...` | 0 | the Reviewer App's approval |
| `gh pr checks 5 --watch` | 0 | `devctl check` passed in 11s |
| `gh pr view 5 --json reviewDecision,mergeStateStatus` | 0 | `mergeStateStatus` `BLOCKED`, `reviewDecision` `""` |
| `./devctl as worker gh pr merge 5 --squash` | 1 | refused by GitHub: "the base branch policy prohibits the merge" |
| `gh pr review 5 --approve --body "Trial approval by the owner"` | 0 | the owner's approval, after the owner answered `y` to the script's question |
| `gh pr view 5 --json reviewDecision,mergeStateStatus` | 0 | `mergeStateStatus` `CLEAN`, `reviewDecision` `""` |
| `./devctl as worker gh pr merge 5 --squash` | 0 | merged |
| `gh pr view 5 --json state,mergedAt` | 0 | `MERGED` at 2026-10-21T12:33:50Z |

The owner approved through `gh` in the script, where the plan said the browser.

Result: code-owner review holds at a count of 0. With the Reviewer App's approval and a passing check, GitHub refused the Worker App's merge of a change to a Protected file. After the owner's approval, it merged. `reviewDecision` was `""` before and after the owner's approval, where the plan expected `APPROVED`; only `mergeStateStatus` showed the block. Walk's `*` line relies on the same rule and was not tried separately.

### Step 12 in the rerun: a Reviewer App change request

`git pull --ff-only` brought `main` to `fb4eaf1`, #5's merge. The script appended a line to README.md on the branch `trial-agent-2-202640` and committed it.

| Command | Exit | Result |
| --- | --- | --- |
| `./devctl as worker push` | 0 | pushed `trial-agent-2-202640` |
| `./devctl as worker gh pr create ...` | 0 | pull request #6 |
| `./devctl as reviewer gh pr review 6 --request-changes --body "Trial change request by the Reviewer App"` | 0 | the Reviewer App's change request |
| `gh pr checks 6 --watch` | 0 | `devctl check` passed in 7s |
| `gh pr view 6 --json reviewDecision,mergeStateStatus` | 0 | `mergeStateStatus` `CLEAN`, `reviewDecision` `""` |

The script did not try the merge.

Result: at a count of 0, the Reviewer App's change request alone does not block a merge. `reviewDecision` was `""`, not `CHANGES_REQUESTED`, so it does not show whether the Reviewer App requested changes. Spec 3 counts Revisions from each review's state in the pull request's reviews, so this does not affect it.

### Step 12 in the rerun: a workflow change that the agent branch takes in

The owner answered `y` to merging a one-line comment in `.github/workflows/devctl-check.yml` into `main` as themselves, with the admin bypass. From `main` at `fb4eaf1`, the script appended a comment line to that file on the branch `trial-workflow-202640` and committed it.

| Command | Exit | Result |
| --- | --- | --- |
| `git push -u origin trial-workflow-202640` | 0 | pushed as the owner |
| `gh pr create --base main --head trial-workflow-202640 ...` | 0 | pull request #7 |
| `gh pr merge trial-workflow-202640 --squash --admin --delete-branch` | 0 | merged; the local `main` fast-forwarded from `fb4eaf1` to `e0553fe` |
| `git switch trial-agent-2-202640` | 0 | |
| `git fetch origin main` | 0 | |
| `git merge --no-edit origin/main` | 0 | a merge commit that brings in the one-line change to `.github/workflows/devctl-check.yml` |
| `./devctl as worker push` | 0 | accepted: `0b1790a..4b9d1fa  trial-agent-2-202640 -> trial-agent-2-202640`; devctl printed no hint |

Result: GitHub accepted the Worker App's push, where Step 12 expected a refusal. The push's only new commit merged in a workflow change already on `main`. The trial did not try an App's direct edit of a workflow, which the old plan observed GitHub refusing (Checked facts).

### Step 13 in the rerun: `doctor --skills` live

The owner answered `y` to running `./devctl doctor --skills`. The script ran it on `main` at `e0553fe`.

| Command | Exit | Result |
| --- | --- | --- |
| `./devctl doctor --skills` | 1 | `doctor: 16 ok, 2 missing, 0 unknown` |
| `git worktree list` | 0 | only the clone, at `e0553fe [main]` |

doctor's output, with the 93 skill names outside the repository left out. None of them is `trial-notes` or `trial-release`.

```text
ok  toolchain  git: 2.39.5
ok  toolchain  uv: /opt/homebrew/bin/uv
ok  toolchain  gh: /opt/homebrew/bin/gh
ok  toolchain  gh sign-in: gh auth status exited 0
ok  toolchain  gitleaks: 8.30.1
missing  guardrails  core.hooksPath: core.hooksPath is not set; run git config core.hooksPath .githooks; the pre-commit hook runs devctl check --tier fast
ok  guardrails  CI workflow: .github/workflows/devctl-check.yml has a job named devctl check
ok  guardrails  tools/devctl exclusions: no pyproject.toml, so no uv workspace
ok  kit  Kit files: Kit 0.1.0: 35 unchanged, 1 modified, 0 excluded; modified: .github/workflows/devctl-check.yml; run uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.1.0 rapid-ship status to see template updates
missing  github  ruleset: no pull_request rule requires an approval; the pull_request rule does not require approval of the most recent push
ok  github  CODEOWNERS: .github/CODEOWNERS on main matches the Protected set (every_pr = false)
ok  github  delete branch on merge: head branches are deleted after merge
ok  github  fork PR workflow approval: workflows from all outside contributors need approval
ok  agent identity  Worker App installation: proxy-hatch-rs-worker is installed on proxy-hatch/rs-trial with exactly the worker App's permissions
ok  agent identity  Reviewer App installation: proxy-hatch-rs-reviewer is installed on proxy-hatch/rs-trial with exactly the reviewer App's permissions
ok  agent identity  Worker App key: Keychain item found; token minted (changes nothing in the repository)
ok  agent identity  Reviewer App key: Keychain item found; token minted (changes nothing in the repository)
ok  skills  skills (claude): 1 repository skills seen; outside the repository: [93 names]; not checked, user-invoked: trial-release
doctor: 16 ok, 2 missing, 0 unknown
```

Result: the skills item is as Step 13 expects: ok, with `1 repository skills seen` and `not checked, user-invoked: trial-release`, and `trial-release` is not among the names outside the repository. doctor leaves a user-invoked skill out of those names, so its output cannot show whether Claude Code listed `trial-release`. `git worktree list` shows no probe worktree left behind.

devctl 0.1.0's `harness.py` passes `--model haiku`, and the Kit files item shows that only the workflow differs from Kit 0.1.0. doctor does not print the model ID that `haiku` resolved to on Claude Code 2.1.304, so this run does not reconfirm the Checked facts' `claude-haiku-4-5-20251001`.

The two missing items are expected. `core.hooksPath` is a setting of the local clone, unset in a fresh one. The ruleset item is v0.1.0's, which requires an approval count and approval of the most recent push in Flight with Agent identity, so it reports the decided ruleset as missing. The doctor that follows the decision accepts that ruleset, in offline tests only. The modified Kit file is the workflow that #7 changed.

### Step 14 in the rerun: clean up

| Command | Exit | Result |
| --- | --- | --- |
| `gh pr list --repo proxy-hatch/rs-trial --state open --json number,title,headRefName` | 0 | one open pull request, #6, from `trial-agent-2-202640` |
| `gh pr close 6 --repo proxy-hatch/rs-trial --delete-branch` | 0 | closed #6 and deleted its branch, after the owner answered `y` |

`rs-trial` and `rs-trial-private` stay, and so do the Apps. The log does not record whether the owner removed the temporary clone.

## Deviations from Checked facts and the plan's expectations

| Expected | Source | Observed |
| --- | --- | --- |
| The installation object carries `id`, `app_id`, `app_slug` and `permissions` | Checked facts, not observed before | Confirmed: all four are among its keys (Step 5) |
| A missing Keychain item exits 44 | Checked facts | Confirmed: the read of a removed item name exited 44 (Step 5) |
| An item `security` wrote trusts `security`, so reads show no dialog | Checked facts | Confirmed by the rerun: both reads exited 0, and macOS showed no dialog. The first pass did not record the read (Step 5) |
| gh uses `GH_TOKEN` ahead of its stored sign-in | Checked facts | Consistent: pull request #1's author is the Worker App (Step 10) |
| A ruleset read on a GitHub Free private repository returns 403 "Upgrade to GitHub Pro ..." | Checked facts | Consistent: doctor printed its 403 line, which it prints only for that message (Step 6) |
| The author of a pull request opened through `devctl as` is `<worker slug>[bot]` | Task 10 Step 10 | gh's JSON printed `app/proxy-hatch-rs-worker` (Step 10) |
| The ruleset reads back as rs-setup applies it | Task 10 Steps 8 and 9 | GitHub's read-back adds parameters that rs-setup's ruleset does not set: `require_extra_approval_for_unattributed_changes` true and `required_reviewers` `[]` in `pull_request`, and `do_not_enforce_on_create` false in `required_status_checks` (Step 11a). doctor does not check them, and its tests passed on Step 9's read-back. The rerun's `PUT` also left out `require_extra_approval_for_unattributed_changes`, and it read back `true` |
| GitHub may count the Reviewer App's approval toward the ruleset | Task 10 Step 11, Spec 1 section 11 | GitHub does not take it as approval of the most recent push (experiment A). Toward the count, a merge at a count of 1 was refused, but last-push approval was on too (Step 11) |
| GitHub refuses an App-token push that brings in a workflow change | Task 10 Step 12, from Checked facts | Accepted (rerun): the Worker App's push of a branch whose only new commit merged in a workflow change already on `main` exited 0, and devctl printed no hint. An App's direct edit of a workflow was not tried; the old plan observed GitHub refusing one |
| `PROBE_MODEL` is `haiku` | Checked facts | Partly (rerun): the probe ran with devctl 0.1.0's `haiku` on Claude Code 2.1.304 and printed the expected skills item. doctor does not print the model ID that `haiku` resolved to, so `claude-haiku-4-5-20251001` is not reconfirmed |
| After a Reviewer App change request, `reviewDecision` is `CHANGES_REQUESTED` | Task 10 Step 12 | At a count of 0, `reviewDecision` was `""` and `mergeStateStatus` `CLEAN` after the check passed (rerun, #6). The change request alone does not block a merge |
| After the owner approves a Protected pull request, `reviewDecision` is `APPROVED` | Plan 4's code-owner step at a count of 0, pending before the rerun | At a count of 0, `reviewDecision` was `""` before and after the owner's approval, while `mergeStateStatus` went from `BLOCKED` to `CLEAN` (rerun, #5) |

## Plan defects the trial found

1. **Step 4's settings edit is prose.** It sits above the code block, so the owner ran only the block, `worker_app_id` stayed 0 and Step 6's mint failed. The edit should be a command in the block.
2. **Steps 3 and 5 name the Keychain items as they were before their rename.** They read `rapid-ship/worker-app` and `rapid-ship/reviewer-app`; the items are `rapid-ship/<role>-app/<App ID>`.
3. **"This plan's worktree" no longer exists.** The owner used their checkout of `main` as `$PLAN4`.
4. **Step 11a changes only the count.** That cannot make an App-only merge pass while `require_last_push_approval` stays true, so a rerun of its second block needs both changes.
5. **Step 10 expects the author `<worker slug>[bot]`.** gh's JSON printed `app/proxy-hatch-rs-worker`.

## Limits

- **Both keys are readable.** Any process the owner runs can read both App keys, as Spec 1 section 6 states. In the rerun, a script the owner ran read both Keychain items, exit 0 each, and macOS showed no dialog. A Worker can therefore act as the Reviewer App. The first pass did not record the read (Step 5).
- **The Reviewer App's approval does not satisfy the ruleset** (Step 11, Step 11a and experiment A). GitHub does not take it as approval of the most recent push. Whether it counts toward a count of 1 is not isolated: last-push approval was on at that attempt, and `reviewDecision` was not recorded. A count of 1 with last-push approval off was not tried.
- **Why GitHub does not take it** is documented, though this trial did not isolate the count: GitHub counts an approval only from someone with write permission to the repository ([about protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)), and the Reviewer App has Contents: read by design (Spec 1 section 3).
- **Code-owner review at a count of 0 holds** (rerun, #5). The decision relies on it: in Walk, code-owner review is all that keeps GitHub from merging the Worker App's pull request without the owner. The first pass did not observe it: Step 10 ran in Walk at a count of 1, and #3 changed README.md, which has no code owner in Flight. The rerun tried Flight's `/**/AGENTS.md` line only. Walk's `*` line relies on the same rule and was not tried separately.
- **GitHub refuses a merge while `devctl check` is pending** (rerun, #4). Step 11's first attempt did not isolate the check, because the approval requirement was unmet then too. #4 ran under the `pull_request` settings with which experiment A merged #3. GitHub refused its merge while the run was queued, and merged it once the check passed. A run in progress or failed was not tried.
- **Workflow changes.** GitHub accepted the Worker App's push whose only new commit merged in a workflow change already on `main` (rerun). The trial did not try an App's direct edit of a workflow, which the old plan observed GitHub refusing.
- **A change request does not block a merge at a count of 0** (rerun, #6). After the Reviewer App requested changes and the check passed, `mergeStateStatus`, read as the owner, was `CLEAN`; the script did not try the merge. With Agent identity, plan 5's merge guard, which requires the Reviewer App's approval of the head commit, is what will stop an agent's merge past a change request, and only in a Harness wired to `devctl hook`.
- **`reviewDecision` at a count of 0** was `""` in every read: with a code-owner review pending or given, and after a change request (rerun). A tool must read GitHub's block from `mergeStateStatus`, and each review's state from the pull request's reviews.
- **`PROBE_MODEL`.** The rerun's `doctor --skills` ran devctl 0.1.0, whose `harness.py` passes `--model haiku`, and printed the expected skills item. doctor does not print the model ID that `haiku` resolved to on Claude Code 2.1.304. Its output also cannot show whether Claude Code listed `trial-release`, because doctor leaves a user-invoked skill out of the names it reports.
- **doctor in Flight.** Step 11's doctor output was not recorded. The rerun's doctor, v0.1.0, ran in Flight with Agent identity: CODEOWNERS and the four `agent identity` items were ok. Its ruleset item reported the decided ruleset as missing, because v0.1.0 predates the decision. The doctor that follows the decision accepts that ruleset in offline tests only (`test_the_decided_ruleset_passes_in_every_mode`).
- **Experiment B tested nothing**, because #3 had already merged. Experiment A shows only that `require_extra_approval_for_unattributed_changes` true, the Copilot option, did not block that one merge.
- **Versions.** The first pass recorded only the Kit version, so its results are not tied to particular gh, git or macOS versions. The rerun's are (Setup and versions).
- **One account.** The trial used one personal account, whose plan was not recorded (Step 6's 403 matches GitHub Free, and the rerun's `gh api user --jq .plan.name` printed an empty line), with one public and one private repository. Organisation-owned repositories were not tried.
- **The environment.** The `.venv` of the owner's checkout pointed at the repository's earlier path and needed `uv sync --locked --reinstall` (Step 9). That is an environment issue, not a product defect.
