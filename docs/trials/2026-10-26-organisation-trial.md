# Organisation trial

Trial date: 2026-10-26. Live, on the organisation `vest-fyi`, which the owner set aside for destructive tests. An agent ran the steps from a Claude Code Session, with the owner's `gh` sign-in and Keychain and the built-in browser signed in as the owner, after the owner approved a list of outside writes. The owner ran the steps that the Session's guardrails deny it, confirmed GitHub's sudo prompt, and generated and imported the keys. This is plan 4's follow-up 5 in the [plan index](../superpowers/plans/2026-10-14-kit-and-setup.md#plan-4-follow-ups-before-31-to-33-merge).

## How to read this

- Each result is live. "Not run" marks a step that did not happen; it is neither a pass nor a skip.
- `$W` is a worktree of rapid-ship's `main` at `ee43cef`, which runs `rapid-ship` 0.2.0 and vendors Kit 0.2.0. `$TRIAL` is a temporary directory that holds the clone of `vest-fyi/rs-org-trial`, the run log and the owner's two scripts. Local paths are not recorded.
- The agent logged each outside write before sending it, with the command's output and exit code; this record is written from that log. The owner's two scripts logged their own commands, outputs and exit codes.
- No token, private key, one-time code, client ID, client secret, key fingerprint or email address is recorded.

## Summary

- **The admin half passed.** The owner, an active admin of `vest-fyi`, ran `rapid-ship app` in an organisation repository. It created the Worker App (ID 5475597, `vest-fyi-rs-worker`) and the Reviewer App (ID 5475601, `vest-fyi-rs-reviewer`) through the organisation manifest flow, stored each key under `rapid-ship/<role>-app/<App ID>`, and printed install URLs that installed both Apps on `vest-fyi/rs-org-trial` alone, with exactly rapid-ship's permissions.
- **doctor passed with a team as the code owner.** With `[github] code_owner = "@vest-fyi/maintainers"`, the Walk line `* @vest-fyi/maintainers`, the team given Write, and the ruleset applied, `./devctl doctor` printed `doctor: 19 ok, 0 missing, 0 unknown`, exit 0 (Step 10).
- **`--import-key` passed live** with keys that the admin generated on GitHub: each import exited 0, and doctor again printed `19 ok`, exit 0 (Steps 15 and 16). It refused, exit 1, while the admin's Keychain item for the App existed (Step 12).
- **The App-manager half did not run.** The owner has no second GitHub account, so no member who is not an admin generated a key. Whether an App manager may generate one stays open (Spec 1 section 11).
- **GitHub's App manager settings.** Each organisation App has an "App managers" page: "These people can manage settings, permissions and webhooks for vest-fyi-rs-worker." The organisation also has a pre-defined role, "Apps manager: Grants the ability to manage all GitHub Apps owned by an organization." Neither page, nor GitHub's documentation, says whether a manager may create a private key (Step 13).
- **Defect, PRO-147.** doctor reported CODEOWNERS ok, exit 0, while GitHub reported the team as "Unknown owner", before the team existed and while it had no access to the repository (Steps 5 to 7).
- **Defect, PRO-148, low.** rapid-ship and devctl say "generate a private key in the App's settings on GitHub". An App's General page has no key section; keys are under Credentials, then Key pairs, with the button "New key" (Step 13).
- **The Session's guardrails** denied the agent's push of the trial repository's `main` and its `gh api` writes there, because the hook judges a command by the Session's own repository, rapid-ship. The owner ran those writes from a script (Step 2).

## Setup and versions

| Command | Result |
| --- | --- |
| `sw_vers -productVersion` | `15.7.7` |
| `git --version` | `git version 2.39.5 (Apple Git-154)` |
| `gh --version` | `gh version 2.102.1 (2026-10-20)` |
| `uv --version` | `uv 0.11.0 (Homebrew 2026-03-23 aarch64-apple-darwin)` |
| `claude --version` | `2.1.304 (Claude Code)` |
| `gitleaks version` | `8.30.1` |
| `uv run --project "$W" rapid-ship --version` | `rapid-ship 0.2.0`, from `ee43cef`, origin/main |

- **The organisation:** `vest-fyi`, ID 128700038, on GitHub Free (`gh api orgs/vest-fyi` printed plan `free`). It has two members, both owners. The owner's login is `proxy-hatch`, an active admin. Before the trial it had no teams and no Apps of its own.
- **`gh`'s sign-in:** `proxy-hatch`, with the scopes `gist`, `read:org`, `repo` and `workflow`. It has no `admin:org`, so the team and its access were made in the browser, as the owner, rather than by widening the token.
- **The repository:** `vest-fyi/rs-org-trial`, ID 1433936760, public, so that the ruleset applies on GitHub Free. The owner chose public; a private repository on a free organisation reports the ruleset missing (403).
- **The Keychain before the trial** held two `rapid-ship/*` items, `rapid-ship/worker-app/5376519` and `rapid-ship/reviewer-app/5376520`, which are the owner's own Apps on `proxy-hatch/rapid-ship`. Names were read with `security dump-keychain`, which prints no secrets.

## Steps

### Step 1: create the repository and vendor the Kit

| Command | Exit | Result |
| --- | --- | --- |
| `gh repo create vest-fyi/rs-org-trial --public --add-readme --clone` | 0 | the repository and its clone in `$TRIAL` |
| `uv run --project "$W" rapid-ship init --stack agnostic --repository vest-fyi/rs-org-trial` | 0 | "Vendored the agnostic Kit 0.2.0 for rs-org-trial"; it skipped the existing README.md and committed the Kit as `9b45339` on `rapid-ship/init` |
| `git config core.hooksPath .githooks` | 0 | |
| `./devctl check --tier fast` | 0 | `map`, `exceptions` and `kit` passed; `file-size` not applicable, "no [map] source_roots" |

`init` printed "CODEOWNERS has no owner line and [github] code_owner is empty; rs-setup writes both." Its `--owner` takes a login, not a team. As rs-setup's step 7.5 would, the agent wrote the Walk line `* @vest-fyi/maintainers` in `.github/CODEOWNERS` and `code_owner = "@vest-fyi/maintainers"` in `.rapid-ship/project.toml`, committed both as `b41903d`, and fast-forwarded `main` to it.

### Step 2: the owner's repository writes

The Session's guardrails denied the agent's push of `main`, with G3, "a git push to the default branch lands a change on the default branch outside the merge guard". They also denied its first `gh api -X PATCH` on the repository, with G8, "Agent identity is on, so an App makes gh writes". The hook judges a command by the repository that holds the Session's working directory (`work_tree_root(call.cwd)` in `devctl/hook.py`). Here that is rapid-ship, where Agent identity is on, even though the command ran in the trial's clone. The agent did not work around either denial. The owner ran a script that the agent wrote, `owner-step-1.sh`, in their own terminal. Its log:

| Command | Exit | Result |
| --- | --- | --- |
| `git push origin main` | 0 | `33763e8..b41903d  main -> main` |
| `gh api -X PATCH repos/vest-fyi/rs-org-trial -F delete_branch_on_merge=true --jq .delete_branch_on_merge` | 0 | `true` |
| `gh api -X PUT repos/vest-fyi/rs-org-trial/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors` | 0 | no output |
| `gh api -X POST repos/vest-fyi/rs-org-trial/rulesets --input "$TRIAL/ruleset.json" --jq .id` | 0 | `25858552` |
| `gh api repos/vest-fyi/rs-org-trial/rulesets --jq ...` | 0 | `25858552 rapid-ship active Repository` |

`ruleset.json` is the ruleset that Spec 1 section 8, step 7 describes: it targets `~DEFAULT_BRANCH`, with deletion and force pushes blocked; a `pull_request` rule with squash only, stale approvals dismissed, code-owner review, thread resolution, a count of 0 and last-push approval off; the `devctl check` status check bound to integration 15368; and the admin role (actor 5) as the only bypass, in pull-request mode. Its `pull_request` rule read back as:

```json
{"allowed_merge_methods":["squash"],"dismiss_stale_reviews_on_push":true,"dismissal_restriction":{"allowed_actors":[],"enabled":false},"require_code_owner_review":true,"require_extra_approval_for_unattributed_changes":true,"require_last_push_approval":false,"required_approving_review_count":0,"required_review_thread_resolution":true,"required_reviewers":[]}
```

GitHub added `dismissal_restriction`, `require_extra_approval_for_unattributed_changes` and `required_reviewers`, which the file does not set. doctor does not check them. The push started CI's `devctl check` run on `main`, which passed in 14s.

### Step 3: `rapid-ship app`, first run

```sh
cd "$TRIAL/rs-org-trial" && BROWSER=true PYTHONUNBUFFERED=1 uv run --project "$W" rapid-ship app
```

`BROWSER=true` kept Python's `webbrowser` from opening the default browser. The agent opened the start URL that `rapid-ship app` printed, `http://127.0.0.1:<port>/start`, in the built-in browser. `PYTHONUNBUFFERED=1` made the URL reach the log at once.

The start page posted the manifest, and GitHub showed "Confirm access" at `https://github.com/settings/apps/manifest`: sudo mode, which asks for the verification code or a passkey. The owner was away. At 13:37 CST, 15 minutes later, `rapid-ship app` printed "rapid-ship: no App was created within 15 minutes" and exited 2. `https://github.com/organizations/vest-fyi/settings/apps` read "No GitHub Apps", so nothing had been created. The agent moved the tab off the stale manifest page, so that a late confirmation there could not create an App whose callback server had stopped.

### Step 4: `rapid-ship app`, second run

The same command, at 13:42 CST, with the owner at the keyboard.

- **The Worker App.** GitHub showed "Confirm access" again, and the owner confirmed it. The owner then clicked the Create button. The callback page read "The App was created. Return to the terminal."
- **The Reviewer App.** No sudo prompt. The page at `https://github.com/settings/apps/manifest` read "Create GitHub App", with the name `vest-fyi-rs-reviewer` and the button "Create GitHub App for vest-fyi". The agent clicked it.

`rapid-ship app` printed, exit 0:

```text
Create the Worker App on GitHub. If no browser opens, open http://127.0.0.1:64543/start
Waiting up to 15 minutes.
Worker App: ID 5475597 (vest-fyi-rs-worker)
  worker_app_id = 5475597
  worker_app_slug = "vest-fyi-rs-worker"
  Install on vest-fyi/rs-org-trial: https://github.com/apps/vest-fyi-rs-worker/installations/new/permissions?suggested_target_id=128700038&repository_ids[]=1433936760
Create the Reviewer App on GitHub. If no browser opens, open http://127.0.0.1:64791/start
Waiting up to 15 minutes.
Reviewer App: ID 5475601 (vest-fyi-rs-reviewer)
  reviewer_app_id = 5475601
  reviewer_app_slug = "vest-fyi-rs-reviewer"
  Install on vest-fyi/rs-org-trial: https://github.com/apps/vest-fyi-rs-reviewer/installations/new/permissions?suggested_target_id=128700038&repository_ids[]=1433936760
Record each App's ID and slug, as printed above, in .rapid-ship/project.toml under [github]; rs-setup does this. ./devctl doctor then confirms each installation.
```

The Keychain then also held `rapid-ship/worker-app/5475597` and `rapid-ship/reviewer-app/5475601`. The items of the owner's own Apps did not stop the command. Its code skips an App whose own key GitHub shows as another account's (`_by_key` in `rapid_ship/github_app.py`), and it prints nothing about the Apps it skips. The Worker App's settings page reads "Owned by: @vest-fyi".

Result: the organisation manifest flow created both Apps on the organisation. GitHub's manifest page sits at the personal path `/settings/apps/manifest` even in the organisation flow, but it names the organisation on its button.

### Step 5: GitHub's view of the CODEOWNERS line before the team exists

| Command | Exit | Result |
| --- | --- | --- |
| `gh api repos/vest-fyi/rs-org-trial/codeowners/errors` | 0 | one error: line 6, `"kind":"Unknown owner"`, `"suggestion":"make sure the team @vest-fyi/maintainers exists, is publicly visible, and has write access to the repository"` |
| `gh api orgs/vest-fyi/teams --jq '.[].slug'` | 0 | no teams |

### Step 6: doctor before the team exists

The Apps were not yet recorded, so doctor showed no `agent identity` items.

```text
ok  github  ruleset: an active ruleset on main has every setting rs-setup applies
ok  github  CODEOWNERS: .github/CODEOWNERS on main matches Walk
ok  github  delete branch on merge: head branches are deleted after merge
ok  github  fork PR workflow approval: workflows from all outside contributors need approval
doctor: 15 ok, 0 missing, 0 unknown
```

Exit 0. Every other item was ok as well.

Result, defect PRO-147: doctor reported CODEOWNERS ok while GitHub reported its only owner as unknown. doctor compares the file with `[github] code_owner` and asks GitHub nothing more. GitHub documents that a code owner must have write permission, and a team must also be visible ([about code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)). So in this state code-owner review may require no one. The trial did not try a merge in this state.

### Step 7: create the team, then give it Write

In the browser as the owner, the agent created the team `maintainers` at `https://github.com/orgs/vest-fyi/new-team`, with visibility Visible. Each command below exited 0.

```text
$ gh api orgs/vest-fyi/teams --jq '.[] | {slug, privacy, permission}'
{"permission":"pull","privacy":"closed","slug":"maintainers"}
$ gh api orgs/vest-fyi/teams/maintainers/members --jq '.[].login'
proxy-hatch
$ gh api repos/vest-fyi/rs-org-trial/codeowners/errors --jq '.errors[] | .kind + ": " + .suggestion'
Unknown owner: make sure the team @vest-fyi/maintainers exists, is publicly visible, and has write access to the repository
$ ./devctl doctor
...
ok  github  CODEOWNERS: .github/CODEOWNERS on main matches Walk
...
doctor: 15 ok, 0 missing, 0 unknown
```

The agent then added the team under the repository's Collaborators and teams, with the role Write. Both commands exited 0.

```text
$ gh api repos/vest-fyi/rs-org-trial/teams --jq '.[] | {slug, permission}'
{"permission":"push","slug":"maintainers"}
$ gh api repos/vest-fyi/rs-org-trial/codeowners/errors
{"errors":[]}
```

Result: a visible team is still an unknown owner until it has write access, and doctor's item is the same in all three states.

### Step 8: install both Apps

The agent opened each install URL from Step 4 in the browser. Both pages read "Approve & Install on your organization", with "Only select repositories" and one repository, `vest-fyi/rs-org-trial`. The Worker App's page listed "Read access to metadata" and "Read and write access to code, issues, and pull requests". The Reviewer App's page listed "Read access to code and metadata" and "Read and write access to pull requests". The agent clicked Approve & Install on each.

```text
$ gh api orgs/vest-fyi/installations --jq '.installations[] | select(.app_slug|startswith("vest-fyi-rs")) | {id, app_id, app_slug, repository_selection, permissions}'
{"app_id":5475597,"app_slug":"vest-fyi-rs-worker","id":175348493,"permissions":{"contents":"write","issues":"write","metadata":"read","pull_requests":"write"},"repository_selection":"selected"}
{"app_id":5475601,"app_slug":"vest-fyi-rs-reviewer","id":175348545,"permissions":{"contents":"read","metadata":"read","pull_requests":"write"},"repository_selection":"selected"}
```

Exit 0. The installation page reads "Developed by vest-fyi".

### Step 9: record the Apps

The agent wrote the four values that Step 4 printed into `.rapid-ship/project.toml` and committed them on the local branch `rapid-ship/record-apps`. The ruleset now guards `main`, so the Setup PR would carry this commit. The trial did not push it. doctor reads `[github]` from the work tree, and CODEOWNERS from `main` on GitHub.

### Step 10: doctor with a team as the code owner

```text
ok  toolchain  git: 2.39.5
ok  guardrails  settings: .rapid-ship/project.toml and .rapid-ship/exceptions.toml are valid; CODEOWNERS lists 0 Protected paths
ok  toolchain  uv: /opt/homebrew/bin/uv
ok  toolchain  gh: /opt/homebrew/bin/gh
ok  toolchain  gh sign-in: gh auth status exited 0
ok  toolchain  gitleaks: 8.30.1
ok  guardrails  core.hooksPath: .githooks
ok  guardrails  CI workflow: .github/workflows/devctl-check.yml has a job named devctl check
ok  guardrails  Harness wiring: .claude/settings.json runs devctl hook claude pre-tool for Bash, Edit, Write, MultiEdit, NotebookEdit, Monitor
ok  guardrails  tools/devctl exclusions: no pyproject.toml, so no uv workspace
ok  kit  Kit files: Kit 0.2.0: 45 unchanged, 0 modified, 0 excluded; run uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.2.0 rapid-ship status to see template updates
ok  github  ruleset: an active ruleset on main has every setting rs-setup applies
ok  github  CODEOWNERS: .github/CODEOWNERS on main matches Walk
ok  github  delete branch on merge: head branches are deleted after merge
ok  github  fork PR workflow approval: workflows from all outside contributors need approval
ok  agent identity  Worker App installation: vest-fyi-rs-worker is installed on vest-fyi/rs-org-trial with exactly the worker App's permissions
ok  agent identity  Reviewer App installation: vest-fyi-rs-reviewer is installed on vest-fyi/rs-org-trial with exactly the reviewer App's permissions
ok  agent identity  Worker App key: Keychain item found; token minted (changes nothing in the repository)
ok  agent identity  Reviewer App key: Keychain item found; token minted (changes nothing in the repository)
doctor: 19 ok, 0 missing, 0 unknown
```

Exit 0. Here doctor ran with the admin's `gh` sign-in and the admin's keys from Step 4.

### Step 11: `rapid-ship app` with both Apps recorded

`BROWSER=true uv run --project "$W" rapid-ship app` printed each App's ID, slug and install URL as in Step 4, then "Both Apps are recorded; ./devctl doctor confirms each installation." Exit 0. It opened no flow and created nothing.

### Step 12: `--import-key` while the admin's item exists

```text
$ uv run --project "$W" rapid-ship app --import-key worker < /dev/null
rapid-ship: Keychain item rapid-ship/worker-app/5475597 already exists, and rapid-ship never replaces one; ./devctl doctor checks the key it holds. To replace a key that no longer works, delete the item with: security delete-generic-password -s rapid-ship/worker-app/5475597, then run this again. Nothing was stored.
```

Exit 1. No key was involved: the command checks the item before it reads stdin. One machine has one Keychain, so a developer's import of the same App on the admin's machine needs the admin's item deleted first.

### Step 13: GitHub's App manager and key pages

The agent read these pages in the browser as the owner; it changed nothing.

- `https://github.com/organizations/vest-fyi/settings/apps`, under Management: "To see or change who can manage GitHub Apps belonging to your organization, see organization role assignments. All organization owners can manage Apps, as well as users and teams with one or more of the app management permissions."
- `https://github.com/organizations/vest-fyi/settings/org_roles` lists the pre-defined role "Apps manager: Grants the ability to manage all GitHub Apps owned by an organization."
- Each App has an "App managers" tab, at `https://github.com/organizations/vest-fyi/settings/permissions/integrations/<slug>/managers`: "These people can manage settings, permissions and webhooks for vest-fyi-rs-worker." It listed the organisation's two owners and offered a Grant box for teams or users.
- An App's General page, `.../settings/apps/<slug>`, has no private-key section. Its headings are About, Basic information, Identifying and authorizing users, Post installation, Webhook, Display information and IP allow list. Keys are under Credentials, then Key pairs, at `.../settings/apps/<slug>/key_pairs`. That page listed one key, "Added by proxy-hatch" (the manifest flow's), and the button "New key".

GitHub's [About GitHub App managers](https://docs.github.com/en/apps/maintaining-github-apps/about-github-app-managers) says that "App managers can manage some or all of the GitHub App registrations owned by an account", and that the role "does not grant recipients access to install and uninstall GitHub Apps on an organization". It says nothing of keys. [Managing private keys for GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps) gives the steps Credentials, Key pairs, New key, and does not say who may take them.

Result, defect PRO-148: the missing-key messages of rapid-ship and devctl send a developer to "the App's settings", whose General page has no key section.

### Step 14: the owner generates a key for each App

The owner clicked "New key" on each App's Key pairs page. GitHub downloaded `vest-fyi-rs-worker.2026-10-25.private-key.pem` and `vest-fyi-rs-reviewer.2026-10-25.private-key.pem` to `~/Downloads`. The owner did this as the organisation's admin, not as an App manager.

### Step 15: the owner imports both keys

The owner ran `owner-step-2.sh` in their own terminal. For each role, it found the one downloaded file, deleted the admin's item from Step 4, imported the key and moved the file to the Trash. Its log:

| Command | Exit | Result |
| --- | --- | --- |
| `security delete-generic-password -s rapid-ship/worker-app/5475597` | 0 | `password has been deleted.` |
| `uv run --project "$W" rapid-ship app --import-key worker < ~/Downloads/vest-fyi-rs-worker.2026-10-25.private-key.pem` | 0 | "Stored your key for the Worker App 5475597 (vest-fyi-rs-worker) in Keychain item rapid-ship/worker-app/5475597. rapid-ship wrote it nowhere else: delete the key file that GitHub downloaded. ./devctl doctor then checks the App's installation." |
| `mv ~/Downloads/vest-fyi-rs-worker.2026-10-25.private-key.pem ~/.Trash/` | 0 | |
| `security delete-generic-password -s rapid-ship/reviewer-app/5475601` | 0 | `password has been deleted.` |
| `uv run --project "$W" rapid-ship app --import-key reviewer < ~/Downloads/vest-fyi-rs-reviewer.2026-10-25.private-key.pem` | 0 | "Stored your key for the Reviewer App 5475601 (vest-fyi-rs-reviewer) in Keychain item rapid-ship/reviewer-app/5475601. ..." |
| `mv ~/Downloads/vest-fyi-rs-reviewer.2026-10-25.private-key.pem ~/.Trash/` | 0 | |

`--import-key` stores a key only after `GET /app`, under a token that the key signs, shows the App that `[github]` records. Each import's exit 0 therefore shows that GitHub accepted the new key.

### Step 16: doctor with the imported keys

`./devctl doctor` printed the same 19 items as Step 10, both keys included, and `doctor: 19 ok, 0 missing, 0 unknown`. Exit 0. Each App's Key pairs page then listed two keys: the manifest flow's key, which no Keychain item holds any more, and the imported one.

## Deviations from the plan and the specs

| Expected | Source | Observed |
| --- | --- | --- |
| A developer who is not an admin, made an App manager of both Apps, generates a key | Plan 4's follow-up 5 | Not run: the owner has no second account. The admin generated both keys (Step 14) |
| doctor's CODEOWNERS item passes when the file "Matches the Mode and names `[github] code_owner`" | Spec 1 section 6 | As specified, it compares the file's text only, so it was ok while GitHub reported the team as an unknown owner (Steps 5 to 7, PRO-147) |
| A developer "generates a private key in the App's settings" | Spec 1 section 3, step 4, and both missing-key messages | Keys are under the App's Credentials tab, then Key pairs, with the button "New key"; the General page has none (Step 13, PRO-148) |
| The admin makes each developer an App manager of both Apps | Spec 1 sections 3 and 8 | GitHub offers both a per-App "App managers" page and the organisation role "Apps manager", which covers every App the organisation owns (Step 13) |
| The organisation manifest flow runs at `/organizations/<organisation>/settings/apps/new` | Spec 1 section 3 | rapid-ship posts there. GitHub then asked for sudo mode and showed the form at `/settings/apps/manifest`, with the button "Create GitHub App for vest-fyi"; the Apps are the organisation's (Steps 3 and 4) |

## What this trial does not cover

- **An App manager's key.** No member who is not an admin generated a key, so Spec 1 section 11's question stays open. Spec 1's fallback, where the admin generates each developer's key and the developer imports it with `--import-key`, passed (Steps 14 to 16). Only the admin's own Keychain received the keys, and no key was handed to another person.
- **A developer's doctor.** doctor ran only with the admin's `gh` sign-in. With a member's sign-in, the fork approval setting needs admin access, and the ruleset's bypass list shows only to someone who can edit it; that was not tried.
- **`rapid-ship app` as a member.** Its refusal when `gh`'s login is not an admin of the organisation was not run live.
- **The ruleset at work.** No pull request was opened, so no merge was tried. That includes a merge while the Walk line's owner was unknown.
- **Agent identity at work.** `devctl as worker push`, `gh pr create`, the Reviewer App's review and the merge guard did not run on the organisation repository.
- **Flight with a team.** The Protected-set lines with `@vest-fyi/maintainers` were not tried. Only Walk ran.
- **A private organisation repository, 2FA or SAML enforcement, and a paid organisation plan.** None of these was tried.

## Clean-up

The trial left these in place. Deleting them is the owner's decision.

- The Apps `vest-fyi-rs-worker` (5475597) and `vest-fyi-rs-reviewer` (5475601). Each has two keys on GitHub; the manifest flow's key is held nowhere. To delete an App, open its Advanced tab, `https://github.com/organizations/vest-fyi/settings/apps/<slug>/advanced`, and click "Delete GitHub App". Deleting an App also removes its installation.
- The repository `vest-fyi/rs-org-trial`, with ruleset 25858552: delete it under the repository's Settings, General, Danger Zone. `gh repo delete vest-fyi/rs-org-trial --yes` also works, but `gh` needs the `delete_repo` scope for it, which `gh auth refresh -h github.com -s delete_repo` adds.
- The team `maintainers`: delete it in the browser at `https://github.com/orgs/vest-fyi/teams/maintainers/settings`.
- The Keychain items `rapid-ship/worker-app/5475597` and `rapid-ship/reviewer-app/5475601`, which now hold the imported keys: `security delete-generic-password -s rapid-ship/worker-app/5475597`, and the same for `rapid-ship/reviewer-app/5475601`.
- The two downloaded key files in the Trash: empty the Trash.
- The clone, the run log and the owner's scripts in `$TRIAL`, which hold no secret.
