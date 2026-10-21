# Agent identity, ruleset and doctor trial

Trial date: 2026-10-21. Live: the owner ran every step in their own terminal, on GitHub, with their own sign-in, Apps and Keychain. This report is written from a record of the owner's pasted terminal output. No agent ran a trial step. The trial is Task 10 of [plan 4](../superpowers/plans/2026-10-16-doctor-and-agent-identity.md).

## How to read this

- Each result is live unless it is marked offline. "Not recorded" means that the owner's record does not hold that output. This report does not guess it.
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
- **Not run.** Step 11a's second block, the `$PR4` pair; Step 12, the change request and the workflow change; Step 13, `doctor --skills`. Step 14's clean-up is deferred, so `rs-trial` stays available.

## Setup and versions

- Kit and `rapid-ship`: 0.1.0, from `$PLAN4` at `0e1d6d0` (`v0.1.0`).
- Apps: the Worker App, ID 5376519, `proxy-hatch-rs-worker`, and the Reviewer App, ID 5376520, `proxy-hatch-rs-reviewer`. The owner created both with `rapid-ship app` on 2026-10-19, before this trial. On 2026-10-21 the owner stored their keys again under the Keychain items `rapid-ship/<role>-app/<App ID>`, and later deleted the items under the old names.
- Not recorded: the macOS, git, gh, uv and Claude Code versions, the owner's GitHub plan, and the output of `git -C "$PLAN4" rev-parse HEAD`. Step 6's 403 is what doctor reports on GitHub Free.

## Steps

### Step 1: accept the outside changes

The owner accepted the list and went on. Both Apps already existed, so the list's first change was already made.

### Step 2: record the versions and prepare `rs-trial`

The owner ran Step 2, from `gh repo create "$OWNER/rs-trial" --public --add-readme --clone` to the push of `main`. Not recorded: the versions, the GitHub plan, the fast check's exit code and every other output. Step 5's doctor ran in the resulting clone.

### Step 3: create the Apps

Not run in this trial, because the Apps existed from 2026-10-19. Not recorded: `rapid-ship app`'s output, whether GitHub accepted the manifest without `hook_attributes`, whether each App's settings page shows no webhook, and whether `security` showed a dialog while storing each key. The step's two `security find-generic-password -s rapid-ship/<role>-app` lines name items that no longer exist (Step 5).

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

The key read printed "The specified item could not be found in the keychain" and `read exit 44`. It names the item as it was before the rename, and that item no longer exists; the item is now `rapid-ship/worker-app/<App ID>`. The corrected read, `security find-generic-password -s "rapid-ship/worker-app/$WORKER_ID" -w`, was suggested. Its exit code, and whether a macOS dialog appeared, were not recorded.

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

The owner applied the ruleset that the plan index specifies, with Step 8's `gh api --method POST "repos/$OWNER/rs-trial/rulesets"`. `RULESET_ID` is 25531114.

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

As Step 11a says, the trial stopped here, and the owner decides the ruleset before Step 17. Its second block, the `$PR4` pair that would show GitHub refusing a merge while `devctl check` is pending, did not run.

### Experiments A and B, beyond the plan

The owner ran two one-variable experiments on `rs-trial`'s ruleset after Step 11a. Neither is in the plan.

- **A.** `require_last_push_approval` set to false, everything else as in Step 11a: the count 0, and `require_extra_approval_for_unattributed_changes` true. `./devctl as worker gh pr merge 3 --squash` merged pull request #3, exit 0. So approval of the most recent push was what still blocked the merge: GitHub does not take the Reviewer App's approval as approval of the most recent push. `require_extra_approval_for_unattributed_changes` true did not block this merge.
- **B.** `require_extra_approval_for_unattributed_changes` also set to false. It ran after #3 had merged, so it tested nothing: gh printed "Pull request proxy-hatch/rs-trial#3 was already merged", exit 0.

Ruleset 25531114 on `rs-trial` was left with the count 0, `require_last_push_approval` false, `require_extra_approval_for_unattributed_changes` false, and the rest as Step 11a read it back.

### Step 12: a Reviewer App change request, and a workflow change

Not run.

### Step 13: `doctor --skills` live

Not run. `PROBE_MODEL`, `haiku`, stays unconfirmed.

### Step 14: clean up

Deferred, so `rs-trial` stays available. The Apps stay as the owner's real Apps.

## The decision this trial led to

With Agent identity in Flight, an App-only merge needed `required_approving_review_count` 0 and `require_last_push_approval` false. A count of 1 failed, and a count of 0 with last-push approval on failed. On 2026-10-21 the owner decided that rs-setup's ruleset sets both, in every Mode. Spec 1 section 8, step 7 states the ruleset.

The cost the owner accepted: in a team, a code owner who pushed the last commit to an agent's pull request can approve it themselves. Dismissing stale approvals still voids an approval given before a new push. Code-owner review still holds, so CODEOWNERS alone decides who must approve: the owner for every path in Walk, and for the Protected set in Flight. In Flight with Agent identity, GitHub then requires no approval for a pull request outside the Protected set. The Reviewer App's approval there is process, which the Lead brief carries, and the merge guard still requires a passing `devctl check` and no Protected paths.

## Deviations from Checked facts and the plan's expectations

| Expected | Source | Observed |
| --- | --- | --- |
| The installation object carries `id`, `app_id`, `app_slug` and `permissions` | Checked facts, not observed before | Confirmed: all four are among its keys (Step 5) |
| A missing Keychain item exits 44 | Checked facts | Confirmed: the read of a removed item name exited 44 (Step 5) |
| An item `security` wrote trusts `security`, so reads show no dialog | Checked facts | Unconfirmed: the read of the existing item was not recorded (Step 5) |
| gh uses `GH_TOKEN` ahead of its stored sign-in | Checked facts | Consistent: pull request #1's author is the Worker App (Step 10) |
| A ruleset read on a GitHub Free private repository returns 403 "Upgrade to GitHub Pro ..." | Checked facts | Consistent: doctor printed its 403 line, which it prints only for that message (Step 6) |
| The author of a pull request opened through `devctl as` is `<worker slug>[bot]` | Task 10 Step 10 | gh's JSON printed `app/proxy-hatch-rs-worker` (Step 10) |
| The ruleset reads back as rs-setup applies it | Task 10 Steps 8 and 9 | GitHub's read-back adds parameters that rs-setup's ruleset does not set: `require_extra_approval_for_unattributed_changes` true and `required_reviewers` `[]` in `pull_request`, and `do_not_enforce_on_create` false in `required_status_checks` (Step 11a). doctor does not check them, and its tests passed on Step 9's read-back |
| GitHub may count the Reviewer App's approval toward the ruleset | Task 10 Step 11, Spec 1 section 11 | GitHub does not take it as approval of the most recent push (experiment A). Toward the count, a merge at a count of 1 was refused, but last-push approval was on too (Step 11) |
| GitHub refuses an App-token push that brings in a workflow change | Checked facts | Not tested: Step 12 did not run |
| `PROBE_MODEL` is `haiku` | Checked facts | Not tested: Step 13 did not run |

## Plan defects the trial found

1. **Step 4's settings edit is prose.** It sits above the code block, so the owner ran only the block, `worker_app_id` stayed 0 and Step 6's mint failed. The edit should be a command in the block.
2. **Steps 3 and 5 name the Keychain items as they were before their rename.** They read `rapid-ship/worker-app` and `rapid-ship/reviewer-app`; the items are `rapid-ship/<role>-app/<App ID>`.
3. **"This plan's worktree" no longer exists.** The owner used their checkout of `main` as `$PLAN4`.
4. **Step 11a changes only the count.** That cannot make an App-only merge pass while `require_last_push_approval` stays true, so a rerun of its second block needs both changes.
5. **Step 10 expects the author `<worker slug>[bot]`.** gh's JSON printed `app/proxy-hatch-rs-worker`.

## Limits

- **Reading both keys.** Spec 1 section 6 states that any process the owner runs can read both App keys. This trial did not confirm it: neither the read that names the existing item nor whether a dialog appeared was recorded (Step 5).
- **The Reviewer App's approval does not satisfy the ruleset** (Step 11, Step 11a and experiment A). GitHub does not take it as approval of the most recent push. Whether it counts toward a count of 1 is not isolated: last-push approval was on at that attempt, and `reviewDecision` was not recorded. A count of 1 with last-push approval off was not tried.
- **Why GitHub does not take it** is inferred, not verified: GitHub may take required approvals only from reviewers with write access, and the Reviewer App has Contents: read by design (Spec 1 section 3).
- **GitHub refusing a merge while `devctl check` is pending is not shown.** Step 11's first attempt was refused while the check was pending, but the approval requirement was unmet then too, so the refusal does not isolate the check. Step 11a's `$PR4` pair did not run.
- **A merge that brings in a workflow change was not tried**, nor a change request by the Reviewer App: Step 12 did not run.
- **`doctor --skills` did not run** (Step 13), so `PROBE_MODEL` is unconfirmed.
- **doctor in Flight was not recorded** (Step 11), so its Flight items with Agent identity were not observed live.
- **Experiment B tested nothing**, because #3 had already merged. Experiment A shows only that `require_extra_approval_for_unattributed_changes` true did not block that one merge.
- **Versions.** Only the Kit version is recorded, so the results are not tied to particular gh, git or macOS versions.
- **One account.** The trial used one personal account on GitHub Free, with one public and one private repository. Organisation-owned repositories were not tried.
- **The environment.** The `.venv` of the owner's checkout pointed at the repository's earlier path and needed `uv sync --locked --reinstall` (Step 9). That is an environment issue, not a product defect.
