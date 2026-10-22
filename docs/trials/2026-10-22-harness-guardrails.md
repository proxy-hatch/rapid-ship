# Harness guardrails live trial

Status: prepared on 2026-10-22 as Task 8 Step 2 of [plan 5](../superpowers/plans/2026-10-21-kit-standards-and-guardrails.md). The owner has not run it, so every results table is empty. The owner runs Steps 3 to 7 and keeps their output. Step 8 then fills Versions, the results tables, Timing and Differences from that output, and renames this file to the run date.

## Purpose

Plan 5 gives every Kit project `devctl hook`, which the seeded `.claude/settings.json` wires to Claude Code's `PreToolUse` event ([Spec 1 section 4](../superpowers/specs/2026-10-14-kit-and-setup-design.md#harness-guardrails)). Its unit tests run the hook on recorded events. This trial runs it in live Claude Code Sessions and on real pull requests, as [Spec 1 section 10](../superpowers/specs/2026-10-14-kit-and-setup-design.md#10-testing) lists. It records:

- G1 to G5 in a lead Session and in a subagent, including a shell command run through the `Monitor` tool;
- the merge guard with Agent identity off: a pending check, a failed check, a Protected-set pull request, a merge without `--match-head-commit`, and the retry that merges;
- with Agent identity on: G7, G8, G3 through `./devctl as worker gh api`, and the merge guard through `./devctl as worker gh pr merge`, including a head commit that the Reviewer App has not approved;
- how long one hook call takes.

Ruling (plan 5, Task 8 Step 3): every case whose failure would write to GitHub runs in the scratch repository `proxy-hatch/rs-guardrail-trial`, never in `proxy-hatch/rapid-ship`. Its Kit comes from branch `plan5-guardrails` (PR 5.2), the revision under test.

The expected messages are copied from `hook.py`, `merge_guard.py` and `merge_guard_github.py` on `plan5-guardrails` when this record was prepared. As an offline check, the preparer piped Step 4's calls and Step 6's G7, G8 and G3 calls through `devctl hook` in a local clone with a local origin. The preparer also ran the merge guard against a fake GitHub reader. Each produced the expected message. That check is a simulation, not a result of this trial.

## How to record

1. Approve each prompt for that one call only. Never choose "Yes, and don't ask again": it saves an allow rule for the whole repository.
2. Decline only the G5 prompt, row 7 of Step 4, in the lead Session and in the subagent. Approve every other prompt, so that the agent reaches each call.
3. Record the observed decision as one of these:
   - `deny`: the call did not run, and the Session showed the hook's reason;
   - `ask`: Claude Code asked you, and its prompt showed the hook's reason;
   - `none`: the call ran, perhaps after a prompt of Claude Code's own that shows no reason from the hook.
4. Record the observed message exactly as the Session shows it, with any words Claude Code adds. For a call that ran, record its result instead: the exit code, a pull request number or a merge commit.
5. Read each call from the Session's tool calls, not from the agent's summary. A model can skip, change or retry a call. If the agent declines to make a call, ask once more; if it still declines, record `not run` and its reason.
6. Save each Session's transcript in `$TRIAL_DIR`, for example with `/export`. Step 8 copies the messages from it.
7. Record no token, private key, email address or local path. The documentation site publishes this record.

No row expects either of these outcomes. Record each one as a difference:

- An internal error of the hook. It writes `devctl hook: internal error: <error>; the tool call goes through` to stderr and exits 1. Claude Code documents a `PreToolUse:<tool> hook error` notice for exit 1, and the call goes through ([hook spike](2026-10-21-hook-spike.md#what-each-harness-documents)).
- A merge that the guard cannot check. The guard denies it with `merge denied: the merge guard cannot check this merge: <reason>; fix that, then merge again`.

## Versions

| Item | Command | Version |
| --- | --- | --- |
| Claude Code | `claude --version` | |
| gh | `gh --version` | |
| git | `git --version` | |
| uv | `uv --version` | |
| rapid-ship commit tested | `git -C "$RS_WORKTREE" rev-parse --short HEAD` | |
| Kit | the first line of `rapid-ship init`'s output in Step 3 | |
| devctl in the scratch clone | `./devctl --version` in `$TRIAL_CLONE` | |
| Operating system | `uname -sr` | |

Conditions, from Step 4 and each new Session:

- Claude Code login, from the `Login method` row of `/status` (not the email), and the managed source on its `Setting sources` line:
- Permission mode of each lead Session, from the status bar:
- Mods turned off for the trial, and the user-level hooks, plugins and mods that stayed on, from `/hooks` and `/plugin`:
- Allow rules that `/permissions` listed before Step 4:
- The Kit's hook in `/hooks` in each new Session, with its matcher, command and source:

## The scratch repository

`proxy-hatch/rs-guardrail-trial` is private. Step 3 creates it with a README commit and merges the Kit as pull request #1. Its CODEOWNERS is the Kit's Walk seed: `* @proxy-hatch`, then the Protected-set lines, commented out. G5 and the merge guard read the commented lines too, so `AGENTS.md` is in the Protected set through the pattern `/**/AGENTS.md`.

In the tables below, `<A>` to `<D>` stand for the numbers of the pull requests in this table. `<A head>` to `<D head>` stand for their head commits, as full 40-character SHAs.

| Pull request | Branch | Change | Body | Number | Head commit | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Kit | `rapid-ship/init` | the Kit from `$RS_WORKTREE` | Evidence | | | |
| A | `trial-a` | adds `notes.txt` | Evidence | | | |
| B | `trial-b` | adds a line to `AGENTS.md`, a Protected path | Evidence | | | |
| C | `trial-c` | adds `notes-c.txt` | empty, so the `evidence` step fails | | | |
| Apps | `trial-identity` | records both Apps in `.rapid-ship/project.toml` | Evidence | | | |
| D | `trial-d` | adds `notes-d.txt`; the Worker App pushes it and opens the pull request | Evidence | | | |

## Procedure

Paste these lines into each new terminal. Replace the placeholder with the absolute path of the worktree:

```sh
RS_WORKTREE='<the plan5-guardrails worktree>'
TRIAL_DIR="${TRIAL_DIR:-$HOME/guardrail-trial}"
TRIAL_CLONE="$TRIAL_DIR/rs-guardrail-trial"
export RS_WORKTREE TRIAL_DIR TRIAL_CLONE
```

- `$RS_WORKTREE` is the checkout of branch `plan5-guardrails`.
- `$TRIAL_DIR` holds the trial's files outside every repository: the pull request body, the transcripts and the timings.
- `$TRIAL_CLONE` is the clone of the scratch repository. Every Claude Code Session of the trial starts there.

Claude Code reads its hooks when a Session starts, from `.claude/settings.json` in the directory where the Session starts. Start each Session fresh in `$TRIAL_CLONE`, after Step 3 has merged the Kit and pulled `main`. A Session started before that, or in another directory, runs no hook.

### Step 3 (Owner): the scratch repository

In a repository without commits, `rapid-ship init` commits on the current branch and makes no `rapid-ship/init` branch. `gh repo create` therefore adds a README first. `--refresh` keeps uvx from reusing an earlier build of the worktree.

The block runs in a subshell and stops at the first command that fails. It also stops when `origin/HEAD` names a branch other than `main`, because Step 4's row 3 assumes `main`. Record the failing command's output, fix the cause, and run the remaining lines by hand.

```sh
(
set -eu
mkdir "$TRIAL_DIR"
printf '%s\n' '## Evidence' '' '- `git show --stat HEAD`: shows the trial change' '' 'Not covered: a trial change that no test covers.' > "$TRIAL_DIR/evidence.md"
cd "$TRIAL_DIR"
gh repo create proxy-hatch/rs-guardrail-trial --private --add-readme --clone
cd "$TRIAL_CLONE"
origin_head=$(git symbolic-ref refs/remotes/origin/HEAD)
echo "$origin_head"
[ "$origin_head" = refs/remotes/origin/main ]
git -C "$RS_WORKTREE" rev-parse HEAD
uvx --refresh --from "$RS_WORKTREE" rapid-ship init --stack agnostic --owner proxy-hatch --repository proxy-hatch/rs-guardrail-trial
diff -r -x __pycache__ "$RS_WORKTREE/rapid_ship/templates/common/tools/devctl/devctl" tools/devctl/devctl
echo "devctl matches the worktree"
git push -u origin rapid-ship/init
gh pr create --base main --head rapid-ship/init --title "chore: vendor the rapid-ship Kit" --body-file "$TRIAL_DIR/evidence.md"
sleep 30 # gives GitHub time to start the check
gh pr checks rapid-ship/init --watch
gh pr merge rapid-ship/init --squash
git switch main
git pull --ff-only
gh pr list --state merged --head rapid-ship/init --json number,mergeCommit --jq '.[] | "#\(.number) \(.mergeCommit.oid)"'
)
```

| Command | Expected | Observed |
| --- | --- | --- |
| `gh repo create ...` | the private repository, with one commit, cloned into `$TRIAL_CLONE` | |
| `echo "$origin_head"` | `refs/remotes/origin/main` | |
| `git -C "$RS_WORKTREE" rev-parse HEAD` | the commit of `plan5-guardrails` under test | |
| `uvx --refresh --from ... rapid-ship init ...` | first `Vendored the agnostic Kit 0.2.0 for rs-guardrail-trial (package rs_guardrail_trial).`, last `Next: open a pull request from rapid-ship/init. The rs-setup skill in your coding agent does it.`, exit 0 | |
| `diff -r ...`, then `echo` | `devctl matches the worktree`, and no difference before it | |
| `git push -u origin rapid-ship/init` | exit 0 | |
| `gh pr create ...` | the URL of pull request #1 | |
| `gh pr checks rapid-ship/init --watch` | `devctl check` passes | |
| `gh pr merge rapid-ship/init --squash` | exit 0 | |
| `gh pr list --state merged ...` | `#1` and its merge commit | |

### Step 4 (Owner): each rule, Agent identity off

1. In a terminal, run `git -C "$TRIAL_CLONE" status --short --branch`. Expected: only `## main...origin/main`.
2. Start `claude` in `$TRIAL_CLONE`. Accept its trust prompt if it shows one.
3. Run `/hooks`. Check that `PreToolUse` lists the matcher `Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor` and the command `"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool`. Record what it shows under Conditions.
4. Fill the other Conditions from `/status`, `/permissions` and `/plugin`. Turn off each active mod in the Installed tab of `/plugin`: a mod that handles `tool.check` can approve a call that the hook blocked ([hook spike](2026-10-21-hook-spike.md#what-each-harness-documents)).
5. Give the lead prompt. Record each call in the lead column of the table.
6. In the same Session, give the subagent prompt. Record each call in the subagent column.
7. Save the transcript in `$TRIAL_DIR`, then run the checks after the table in a terminal.

The lead prompt:

```text
This is a trial of this repository's guardrail hook, in a scratch repository. Make each numbered call below as its own tool call, in order, exactly as written. Some calls are expected to be denied or to ask me. After a denial or a declined prompt, go on to the next call; do not retry, change or work around it.
1. In the shell: git commit --allow-empty -n -m g1
2. In the shell: git push --force origin HEAD:g2
3. In the shell: git push origin HEAD:main
4. In the shell: gh api -X PUT repos/{owner}/{repo}/pulls/1/merge
5. In the shell: gh pr merge 1 --admin --squash
6. With a file-edit tool: add the line "# g4" at the end of .rapid-ship/kit.lock
7. With a file-edit tool: add the line "G5 trial." at the end of AGENTS.md
8. With the Monitor tool: run git push --force origin HEAD:g2
9. In the shell: git status
```

The subagent prompt is this line, then a blank line and the lead prompt:

```text
Start one subagent and give it the task below word for word. Do none of it yourself.
```

| # | Call | Expected decision and message | Lead Session: observed decision and message | Subagent: observed decision and message |
| --- | --- | --- | --- | --- |
| 1 | Bash: `git commit --allow-empty -n -m g1` | deny: `G1: --no-verify and git commit -n skip the pre-commit hook; run the command without them, and fix what the hook reports` | | |
| 2 | Bash: `git push --force origin HEAD:g2` | deny: `G2: a force push rewrites published history; push without --force, -f, --force-with-lease, --force-if-includes or a + refspec, and merge the base branch instead` | | |
| 3 | Bash: `git push origin HEAD:main` | deny: `G3: a git push to the default branch lands a change on the default branch outside the merge guard; open a pull request and merge it with gh pr merge <number>, without --admin` | | |
| 4 | Bash: `gh api -X PUT repos/{owner}/{repo}/pulls/1/merge` | deny: `G3: a gh api write to a merge, ref or contents endpoint lands a change on the default branch outside the merge guard; open a pull request and merge it with gh pr merge <number>, without --admin` | | |
| 5 | Bash: `gh pr merge 1 --admin --squash` | deny: `G3: gh pr merge --admin lands a change on the default branch outside the merge guard; open a pull request and merge it with gh pr merge <number>, without --admin` | | |
| 6 | Edit or Write of `.rapid-ship/kit.lock` | deny: `G4: rapid-ship writes .rapid-ship/kit.lock; change Kit files with rapid-ship sync instead` | | |
| 7 | Edit or Write of `AGENTS.md`; you decline the prompt | ask: `G5: AGENTS.md is in the Protected set (CODEOWNERS pattern /**/AGENTS.md); the owner approves this edit` | | |
| 8 | Monitor: `git push --force origin HEAD:g2` | deny: the G2 message of row 2 | | |
| 9 | Bash: `git status` | none: the status of `main` | | |

After both Sessions' runs:

| Command | Expected | Observed |
| --- | --- | --- |
| `git -C "$TRIAL_CLONE" status --short` | no output: no edit was made | |
| `git -C "$TRIAL_CLONE" log --oneline -1` | the squash merge of pull request #1: no commit was made | |
| `git -C "$TRIAL_CLONE" ls-remote --heads origin g2` | no output: no branch `g2` reached GitHub | |

If a check shows a change, record it as a difference, and restore the clone to `origin/main` before Step 5.

### Step 5 (Owner): the merge guard, Agent identity off

1. Start a new lead Session in `$TRIAL_CLONE`, and check `/hooks` as in Step 4.
2. In a terminal, run the block below. It opens B and C, then A last, so that A's check is still pending at row 1. It stops at the first command that fails.
3. At once, give row 1's prompt.
4. Wait for each check with `gh pr checks <n> --watch`, which exits 1 when a check fails. Give each later row's prompt when its condition holds.
5. Save the transcript in `$TRIAL_DIR`, then run `gh pr list` as after the table.

```sh
(
set -eu
cd "$TRIAL_CLONE"
git switch main
git pull --ff-only
git switch -c trial-b main
printf '\nTrial B.\n' >> AGENTS.md
git commit -am "Add a line to AGENTS.md"
git push -u origin trial-b
gh pr create --base main --head trial-b --title "Trial B: AGENTS.md" --body-file "$TRIAL_DIR/evidence.md"
git switch -c trial-c main
printf 'C\n' > notes-c.txt
git add notes-c.txt
git commit -m "Add notes-c.txt"
git push -u origin trial-c
gh pr create --base main --head trial-c --title "Trial C: no Evidence" --body ""
git switch -c trial-a main
printf 'A\n' > notes.txt
git add notes.txt
git commit -m "Add notes.txt"
git push -u origin trial-a
gh pr create --base main --head trial-a --title "Trial A: notes.txt" --body-file "$TRIAL_DIR/evidence.md"
git switch main
)
```

Each row's prompt is: "In the shell, run `<call>` exactly as written, once. If it is denied, do not retry, change or work around it." Row 5's prompt is: "In the shell, run the command that the last denial names, exactly as written, once."

If A's check completed before row 1 ran, rerun the check with this command, then repeat row 1 at once and record both attempts:

```sh
gh run rerun "$(gh run list --branch trial-a --workflow devctl-check.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
```

| # | When | Call | Expected decision and message | Observed decision and message |
| --- | --- | --- | --- | --- |
| 1 | at once, after `gh pr create` opened A | `gh pr merge <A> --squash` | deny: `merge denied: devctl check on PR #<A> at <A head> is <state>; wait for it to pass or fix what it reports, then merge again` | |
| 2 | after C's check failed | `gh pr merge <C> --squash` | deny: `merge denied: devctl check on PR #<C> at <C head> is failure; wait for it to pass or fix what it reports, then merge again` | |
| 3 | after B's check passed | `gh pr merge <B> --squash` | deny: `merge denied: PR #<B> touches the Protected set (AGENTS.md); the owner merges it in GitHub's web interface` | |
| 4 | after A's check passed | `gh pr merge <A> --squash` | deny: `merge denied: PR #<A> merges only at the checked head <A head>; run gh pr merge <A> --squash --match-head-commit <A head>` | |
| 5 | after row 4 | the command that row 4 names | none: GitHub merges A | |

In row 1, `<state>` is GitHub's status of the check run, `queued` or `in_progress`, or `missing` before GitHub has created the run.

After the rows, run this in a terminal, and fill in the scratch repository's table from its output:

```sh
gh pr list --state all --json number,headRefName,state,headRefOid,mergeCommit --jq '.[] | "#\(.number) \(.headRefName) \(.state) \(.headRefOid) \(.mergeCommit.oid // "-")"'
```

Expected: the Kit's pull request and A `MERGED`, each with a merge commit; B and C `OPEN`.

### Step 6 (Owner): Agent identity on

Turn Agent identity on in the scratch repository:

1. In a terminal, run `cd "$RS_WORKTREE"`, then `uv run rapid-ship app --repository proxy-hatch/rs-guardrail-trial`. It finds the Apps whose keys this machine's Keychain holds. If it opens a browser to create an App, stop and record it: the trial uses the existing Apps.
2. Open each `Install on proxy-hatch/rs-guardrail-trial:` URL that it printed. Install that App on this repository only.
3. Run the block below. In the editor, set `worker_app_id`, `worker_app_slug`, `reviewer_app_id` and `reviewer_app_slug` under `[github]` to the values that `rapid-ship app` printed.
4. Once the pull request's check has passed, merge it in GitHub's web interface.

```sh
(
set -eu
cd "$TRIAL_CLONE"
git switch main
git pull --ff-only
git switch -c trial-identity main
"${EDITOR:-vi}" .rapid-ship/project.toml
git diff
git commit -am "Record the Worker and Reviewer Apps"
git push -u origin trial-identity
gh pr create --base main --head trial-identity --title "Record the Worker and Reviewer Apps" --body-file "$TRIAL_DIR/evidence.md"
sleep 30 # gives GitHub time to start the check
gh pr checks trial-identity --watch
)
```

| Command or action | Expected | Observed |
| --- | --- | --- |
| `uv run rapid-ship app --repository proxy-hatch/rs-guardrail-trial` | for each App, `Worker App: ID <id> (<slug>)` or `Reviewer App: ID <id> (<slug>)`, its two `project.toml` lines and an `Install on proxy-hatch/rs-guardrail-trial:` URL; exit 0 | |
| Install both Apps | each App installed on `proxy-hatch/rs-guardrail-trial` | |
| `gh pr create ...` for `trial-identity` | the URL of the Apps pull request | |
| `gh pr checks trial-identity --watch` | `devctl check` passes | |
| Merge in GitHub's web interface | the Apps pull request merged; record its merge commit | |

Then run the rows:

1. Prepare D's branch in a terminal. The agent pushes it as the Worker App in row 3.

   ```sh
   (
   set -eu
   cd "$TRIAL_CLONE"
   git switch main
   git pull --ff-only
   git switch -c trial-d main
   printf 'D\n' > notes-d.txt
   git add notes-d.txt
   git commit -m "Add notes-d.txt"
   )
   ```

2. Start a new lead Session in `$TRIAL_CLONE`, and check `/hooks` as in Step 4.
3. Give the first lead prompt. Replace `<TRIAL_DIR>` with the absolute path of `$TRIAL_DIR`. Row 5 must run right after row 4, while D's check is pending. If D's check completed first, rerun it with Step 5's `gh run rerun` command, with `trial-d` in place of `trial-a`, and repeat row 5 at once.
4. Give the subagent prompt, with `<D>` replaced.
5. In a terminal, wait with `gh pr checks <D> --watch`. Then read `<D head>` with `gh pr view <D> --json headRefOid --jq .headRefOid`.
6. Give the second lead prompt. Replace each placeholder in angle brackets; keep gh's `{owner}` and `{repo}` as written.
7. Save the transcript in `$TRIAL_DIR`, then run the commands after the tables in a terminal.

The first lead prompt:

```text
This is a trial of this repository's guardrail hook, in a scratch repository. Run each numbered command below in the shell as its own tool call, in order, exactly as written. Some are expected to be denied. After a denial, go on to the next command; do not retry, change or work around it.
1. git push origin HEAD
2. gh pr create --fill
3. ./devctl as worker push
4. ./devctl as worker gh pr create --base main --head trial-d --title "Trial D: notes-d.txt" --body-file <TRIAL_DIR>/evidence.md
5. ./devctl as worker gh pr merge <D> --squash, where <D> is the number of the pull request that command 4 opened
6. gh pr merge <D> --squash
```

The subagent prompt:

```text
Start one subagent and give it the task below word for word. Do none of it yourself.

This is a trial of this repository's guardrail hook, in a scratch repository. Run each numbered command below in the shell as its own tool call, in order, exactly as written. Some are expected to be denied. After a denial, go on to the next command; do not retry, change or work around it.
1. git push origin HEAD
2. gh pr create --fill
3. gh pr merge <D> --squash
```

The second lead prompt:

```text
Run each numbered command below in the shell as its own tool call, in order, exactly as written. Some are expected to be denied. After a denial, go on to the next command; do not retry, change or work around it.
7. ./devctl as worker gh pr merge <D> --squash --match-head-commit <D head>
8. ./devctl as reviewer gh pr review <D> --approve
9. ./devctl as worker gh pr merge <D> --squash
10. Run the command that the denial of command 9 names, exactly as written.
11. ./devctl as worker gh pr merge <C> --squash
12. ./devctl as worker gh pr merge <B> --squash
13. ./devctl as worker gh api -X PUT repos/{owner}/{repo}/pulls/<D>/merge
```

Lead Session:

| # | Call | Expected decision and message | Observed decision and message |
| --- | --- | --- | --- |
| 1 | `git push origin HEAD`, on `trial-d` | deny: `G7: Agent identity is on, so the Worker App pushes; run ./devctl as worker push` | |
| 2 | `gh pr create --fill` | deny: `G8: Agent identity is on, so an App makes gh writes; run ./devctl as <role> gh pr create --fill` | |
| 3 | `./devctl as worker push` | none: the Worker App pushes `trial-d` | |
| 4 | `./devctl as worker gh pr create --base main --head trial-d ...` | none: the Worker App opens D | |
| 5 | `./devctl as worker gh pr merge <D> --squash`, right after row 4 | deny: `merge denied: devctl check on PR #<D> at <D head> is <state>; wait for it to pass or fix what it reports, then merge again` | |
| 6 | `gh pr merge <D> --squash` | deny: `G8: Agent identity is on, so an App makes gh writes; run ./devctl as <role> gh pr merge <D> --squash` | |
| 7 | `./devctl as worker gh pr merge <D> --squash --match-head-commit <D head>`, after D's check passed | deny: `merge denied: PR #<D> has no Reviewer App approval of its head <D head>; have the Reviewer review that commit, then merge again` | |
| 8 | `./devctl as reviewer gh pr review <D> --approve` | none: the Reviewer App approves `<D head>` | |
| 9 | `./devctl as worker gh pr merge <D> --squash` | deny: `merge denied: PR #<D> merges only at the checked head <D head>; run ./devctl as worker gh pr merge <D> --squash --match-head-commit <D head>` | |
| 10 | the command that row 9 names, the same as row 7 | none: GitHub merges D | |
| 11 | `./devctl as worker gh pr merge <C> --squash` | deny: `merge denied: devctl check on PR #<C> at <C head> is failure; wait for it to pass or fix what it reports, then merge again` | |
| 12 | `./devctl as worker gh pr merge <B> --squash` | deny: `merge denied: PR #<B> touches the Protected set (AGENTS.md); the owner merges it in GitHub's web interface` | |
| 13 | `./devctl as worker gh api -X PUT repos/{owner}/{repo}/pulls/<D>/merge` | deny: `G3: a gh api write to a merge, ref or contents endpoint lands a change on the default branch outside the merge guard; open a pull request and merge it with gh pr merge <number>, without --admin` | |

In rows 2 and 6, `<role>` is part of G8's message, not a placeholder. In row 5, `<state>` is as in Step 5's row 1.

Subagent:

| # | Call | Expected decision and message | Observed decision and message |
| --- | --- | --- | --- |
| 1 | `git push origin HEAD` | deny: the G7 message of the lead's row 1 | |
| 2 | `gh pr create --fill` | deny: the G8 message of the lead's row 2 | |
| 3 | `gh pr merge <D> --squash` | deny: the G8 message of the lead's row 6 | |

After the rows, replace `<D>` with D's number and run these in a terminal. They read who opened, approved and merged D:

```sh
gh api "repos/proxy-hatch/rs-guardrail-trial/pulls/<D>" --jq '{author: .user.login, merged, merge_commit_sha}'
gh api "repos/proxy-hatch/rs-guardrail-trial/pulls/<D>/reviews" --jq '.[] | {author: .user.login, state, commit_id}'
gh pr list --state all --json number,headRefName,state,headRefOid,mergeCommit --jq '.[] | "#\(.number) \(.headRefName) \(.state) \(.headRefOid) \(.mergeCommit.oid // "-")"'
```

| Read | Expected | Observed |
| --- | --- | --- |
| D | author `<worker slug>[bot]`, `merged` true, a merge commit | |
| D's reviews | one review: author `<reviewer slug>[bot]`, state `APPROVED`, `commit_id` `<D head>` | |
| Every pull request | the Kit's, A, the Apps' and D `MERGED`; B and C `OPEN` | |

### Step 7 (Owner): the hook's cost

Run this after Step 6, so that the hook reads the settings with Agent identity on. The block copies Task 4's fixture `bash.json`, a `git status` call, and sets its `cwd` to the clone. It runs the hook once without timing it, then 20 times under `/usr/bin/time -p`. It prints the median, the maximum and the 20 sorted times.

```sh
git -C "$TRIAL_CLONE" switch main
git -C "$TRIAL_CLONE" pull --ff-only
(
set -eu
: "${RS_WORKTREE:?paste the Procedure's variables first}" "${TRIAL_DIR:?}" "${TRIAL_CLONE:?}"
cd "$TRIAL_CLONE"
python3 - "$RS_WORKTREE/tests/devctl/fixtures/hooks/claude/bash.json" "$PWD" > "$TRIAL_DIR/bash.json" <<'EOF'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fixture:
    event = json.load(fixture)
event["cwd"] = sys.argv[2]
print(json.dumps(event, indent=2))
EOF
./devctl hook claude pre-tool < "$TRIAL_DIR/bash.json"
for i in $(seq 1 20); do
  /usr/bin/time -p ./devctl hook claude pre-tool < "$TRIAL_DIR/bash.json" 2>&1 >/dev/null | awk '/^real/ {print $2}'
done | sort -n > "$TRIAL_DIR/hook-times.txt"
awk '{t[NR] = $1} END {print "median", (t[10] + t[11]) / 2, "max", t[NR]}' "$TRIAL_DIR/hook-times.txt"
paste -sd ' ' "$TRIAL_DIR/hook-times.txt"
)
```

| Command | Expected | Observed |
| --- | --- | --- |
| The untimed `./devctl hook claude pre-tool` | no output: no decision for `git status` | |
| The `awk` line | `median <seconds> max <seconds>` | |
| The `paste` line | 20 times, in seconds | |

When the steps are done, turn back on the mods that Step 4 turned off. Keep the scratch repository until Step 8 and any rerun are done.

### Rerunning a case after a fix

Step 8 fixes each difference in PR 5.2 and reruns its case:

1. In `$TRIAL_CLONE`, on an up-to-date `main`, run `uvx --refresh --from "$RS_WORKTREE" rapid-ship sync`. It pushes a branch and opens a pull request with the changed Kit files.
2. Merge that pull request in GitHub's web interface. Then run `git switch main` and `git pull --ff-only`.
3. Start a new Session in `$TRIAL_CLONE`, and rerun the case. Record the rerun on its own, with the commit of `$RS_WORKTREE` that it tested.

## Timing

Step 7 fills this section. For comparison, the hook spike's stand-in, `./devctl --version`, took a warm median of 0.10 seconds and a maximum of 0.14 ([hook spike](2026-10-21-hook-spike.md#timing)).

| Measure | Seconds |
| --- | --- |
| Median of 20 runs | |
| Maximum of 20 runs | |

The 20 times, sorted:

## Differences from the expected decisions

Step 8 lists each row whose observed decision or message differs from the expected one, with its fix in PR 5.2 and the rerun. None is recorded yet.

## Limits

Known before the run; Step 8 adds the run's own limits.

- The trial covers Claude Code alone, because plan 5 wires no other Harness. The follow-ups that wire Codex (PRO-142) and agy (PRO-143) repeat it there.
- No headless Session runs. The hook spike observed a deny hold in a headless Claude Code Session, with a stand-in hook.
- Each case runs once, on one machine, with one version of Claude Code.
- No row exercises the guard's other denials: a merge it cannot check, unreadable settings, or a read that would pass its 300-second budget. Task 5's unit tests cover them with a fake GitHub reader.
- Step 7 times a call that gets no decision and reads nothing from GitHub. A `gh pr merge` also pays the guard's GitHub reads: four or more, and five or more with Agent identity on.
- The rows run each command in the form that Spec 1 section 4 lists. They do not try the bypasses that section's limits accept, such as a script or a tool that the hook does not see.
