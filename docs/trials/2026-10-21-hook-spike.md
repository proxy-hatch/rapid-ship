# Hook spike (PRO-139)

Status: prepared on 2026-10-21 as Task 1 Step 1 of [plan 5](../superpowers/plans/2026-10-21-kit-standards-and-guardrails.md). No Harness Session has run yet. The owner runs Steps 2 to 6. Step 7 fills Versions, Results, Events, Timing and Decisions from the owner's output, and renames this file to the owner's run date.

## Purpose

[Spec 1](../superpowers/specs/2026-10-14-kit-and-setup-design.md) wires Claude Code's hooks to `devctl hook` and leaves Codex and agy without wiring until this spike reports. The spike runs a stand-in hook in each of the three Harnesses, in a lead Session, in a subagent and in a headless Session, because `devctl hook` does not exist yet. It records:

- whether each wired event fires, and which fields it carries;
- how each Harness treats the hook's deny and ask answers, exit 1, exit 2 (the code uv exits with when it fails), and a hook that outlives its timeout;
- whether Codex hooks can ask, and how Codex's trust and `/hooks` review work;
- in Claude Code, a hook's ask in `bypassPermissions` mode, and which directory and hook a Session uses for an edit inside a linked worktree;
- how long `./devctl --version` takes, as a stand-in for the cost of `devctl hook` on every matched tool call.

From this record the owner decides whether G1 to G4 stay in the hook, and whether a follow-up adds the wiring for Codex and for agy (Spec 1 sections 4 and 11). Task 4 copies the Claude Code events under [Events](#events) into test fixtures.

## Versions

Step 7 fills this table from the owner's runs.

| Item | Command | Version |
| --- | --- | --- |
| Claude Code | `claude --version` | |
| Codex CLI | `codex --version` | |
| Antigravity CLI (agy) | `agy --version` | |
| uv | `uv --version` | |
| rapid-ship commit timed in Step 5 | `git rev-parse --short HEAD` | |
| Operating system | `uname -sr` | |

Conditions, from Steps 2 and 3:

- Claude Code login, a personal subscription or a Team or Enterprise `/login`, and the managed source on the `Setting sources` line of `/status`, if any:
- Mods turned off for the spike:
- User-level hooks, plugins and mods that stayed on, for each Harness:
- Permission mode or approval policy of each Harness's lead Session:
- Saved allow rules found before Step 3:

## Setup

### What each Harness documents

The stand-in's answers and the wiring files follow each Harness's hook documentation as read on 2026-10-21. The pages were fetched as raw Markdown, not through a summariser. "Not documented" means the pages read say nothing on the point; the spike observes it.

**Claude Code.** Sources, read 2026-10-21: the [hooks reference](https://code.claude.com/docs/en/hooks), the [tools reference](https://code.claude.com/docs/en/tools-reference), [permissions](https://code.claude.com/docs/en/permissions), [permission modes](https://code.claude.com/docs/en/permission-modes), [headless mode](https://code.claude.com/docs/en/headless), [mods](https://code.claude.com/docs/en/plugins/mods/overview) and [settings](https://code.claude.com/docs/en/settings).

- Wiring file: `.claude/settings.json`, with `hooks.PreToolUse` holding matcher groups and their command handlers (hooks reference). Claude Code reads it from the `.claude/` folder of the directory the Session starts in, with no fallback to a parent directory (permissions).
- Matcher: a value made only of letters, digits, `_`, `-`, spaces, `,` and `|` is a list of exact tool names, so `Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor` matches those six names exactly (hooks reference).
- Tools: the tools reference lists `Bash`, `Edit`, `Write`, `NotebookEdit` and `Monitor`, which runs a command in the background under Bash's permission rules. It does not list `MultiEdit`; the permissions page calls it "the legacy `MultiEdit` tool".
- Input: one JSON object on stdin with `session_id`, `prompt_id`, `transcript_path`, `cwd`, `scratchpad_dir`, `permission_mode`, `effort`, `hook_event_name`, `tool_name`, `tool_input` and `tool_use_id`. Inside a subagent it also carries `agent_id` and `agent_type`. For `Write`, `Edit` and `Read`, `tool_input.file_path` is always absolute (hooks reference).
- Deny: exit 0 and print `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"<reason>"}}`. Claude sees the reason (hooks reference).
- Ask: the same object with `"ask"`. The user sees the reason in the permission prompt, and a hook's ask forces a prompt in auto mode too. In a `-p` run where nobody can answer the prompt, Claude Code denies the call and Claude reads the reason in the tool result. Deny and ask rules still apply whatever the hook returns (hooks reference, permissions). The pages do not say what a hook's ask does in `bypassPermissions` mode.
- Exit 2: blocks the call, and Claude sees stderr as the reason (hooks reference).
- Exit 1 and any other code: a non-blocking error. The call goes ahead, and the transcript shows a `PreToolUse:<tool> hook error` notice with the first line of stderr. A handler that sets `"onFailure": "block"`, from v2.1.295, blocks instead; the spike's wiring does not set it (hooks reference).
- Timeout: `timeout` is in seconds, and the default for a command hook is 600. A `PreToolUse` hook that reaches its timeout is cancelled, its output is discarded and the call continues through the permission flow, unless the handler sets `"onFailure": "block"` (hooks reference).
- `$CLAUDE_PROJECT_DIR`: the project root where the Session started. It stays there when Claude enters a worktree, while the input's `cwd` follows Claude (hooks reference).
- Subagents: hooks from settings files also run inside subagents (hooks reference).
- Other hooks: hooks in the user's `~/.claude/settings.json` and in enabled plugins run on the same events. `/hooks` labels each hook with its source (hooks reference).
- Mods: a mod is a plugin whose JavaScript hooks run inside Claude Code. A mod that handles `tool.check` answers after the `PreToolUse` hooks. With neither managed settings on the machine nor a Team or Enterprise `/login` as the Session's credential, it can approve a call that a `PreToolUse` hook blocked or would prompt for (permissions). `/plugin` names the mods a Session loaded, and its Installed tab disables one (mods). `/status` names a managed settings source (settings).
- Saved approvals: "Yes, and don't ask again" saves an allow rule to `.claude/settings.local.json` at the repository's root, for every later Session there. `/permissions` lists each rule with its file (permissions).
- Headless: `claude -p` runs the hooks in a project's `.claude/settings.json`, even in a folder that was never trusted, unless `--bare` is set (headless mode). From v2.1.302, a `-p` run with no permission mode set starts in Manual mode, which denies calls that need approval (permission modes).

**Codex CLI.** Sources, read 2026-10-21: [hooks](https://learn.chatgpt.com/docs/hooks), which `developers.openai.com/codex/hooks` redirects to, [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [developer commands](https://learn.chatgpt.com/docs/developer-commands) and [approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security).

- Wiring file: `<repo>/.codex/hooks.json`, or `[hooks]` in `.codex/config.toml`, with the same three levels as Claude Code: event, matcher group and handlers. Project hooks load only when the project's `.codex/` layer is trusted (hooks).
- Trust and review: Codex runs a non-managed hook, such as a project hook, only after the owner reviews and trusts its exact definition in `/hooks`. Trust is recorded against the hook's hash, so a new or changed hook is skipped until it is trusted, and Codex warns at startup when hooks need review. `--dangerously-bypass-hook-trust` runs enabled hooks without persisted trust for one invocation (hooks).
- Other hooks: `~/.codex/hooks.json`, `~/.codex/config.toml` and enabled plugins also hold hooks (hooks). `/hooks` shows each hook's source and can disable a non-managed hook, and `/status` shows the approval policy (developer commands).
- Matcher: a regular expression on the tool name. Shell commands, unified exec included, match as `Bash`. Edits through `apply_patch` match as `apply_patch`, `Edit` or `Write`, and the input still says `apply_patch`. Hosted tools such as web search run no hook (hooks).
- Command: runs with the Session's `cwd` as its working directory. For repository hooks the page advises a path from `git rev-parse --show-toplevel` (hooks).
- Input: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`, `permission_mode`, `turn_id`, `tool_name`, `tool_use_id` and `tool_input`. For `Bash` and `apply_patch`, `tool_input.command` holds the command or the patch (hooks).
- Deny: the same `hookSpecificOutput` object as Claude Code's with `"deny"`; the older `{"decision":"block","reason":"..."}`; or exit 2 with the reason on stderr (hooks).
- Ask: `permissionDecision: "ask"` is "parsed but not supported yet": Codex marks the hook run as failed, reports the error and continues the tool call (hooks). The stand-in prints it anyway, because it is the documented shape and Step 3 observes what Codex does with it.
- Exit 1 and other codes: not documented for command hooks.
- Timeout: `timeout` is in seconds, and the default is 600 for every event except `SessionEnd` and `Interrupt` (hooks). What a `PreToolUse` command hook's timeout does to the call is not documented.
- Subagents: not stated for `PreToolUse`. The input table says a subagent's hooks carry the parent Session's ID, and `SubagentStart` and `SubagentStop` events exist (hooks).
- Headless: `codex exec` runs in a read-only sandbox by default, and `--sandbox workspace-write` allows edits in the workspace (non-interactive mode). The workspace includes the current directory and temporary directories (approvals and security). The exec page does not mention hooks, and the pages do not say whether a hook runs inside the sandbox.

**Antigravity CLI (agy).** Sources, read 2026-10-21: [hooks](https://antigravity.google/docs/hooks), [permissions](https://antigravity.google/docs/permissions), [the `/permissions` command](https://antigravity.google/docs/cli/commands/permissions), [headless mode](https://antigravity.google/docs/cli/headless), [subagents](https://antigravity.google/docs/subagents) and [execution modes](https://antigravity.google/docs/cli/modes).

- Wiring file: `.agents/hooks.json` at the project root. It maps a hook name to its events: `{"<name>": {"PreToolUse": [{"matcher": "...", "hooks": [...]}]}}`. `/hooks` in the TUI lists the loaded hooks. Hooks in `~/.gemini/config/hooks.json`, in `~/.gemini/antigravity-cli/settings.json` and in installed plugins also load (hooks). No trust or review step is documented.
- Matcher: a regular expression on the tool name, where `""` or `"*"` matches every tool. The shell tool is `run_command`; file edits use `write_to_file`, `replace_file_content` and `multi_replace_file_content`; `invoke_subagent` starts subagents. No notebook tool is listed (hooks).
- Handler: `type` is `command`, the only type; `command` is a shell command; `timeout` is in seconds, with a default of 30 (hooks). The page does not say which directory the command runs in.
- Input: camelCase JSON with `toolCall.name`, `toolCall.args`, `stepIdx`, `conversationId`, `workspacePaths`, `transcriptPath`, `artifactDirectoryPath` and `modelName` (hooks).
- Answer: JSON on stdout with a required `decision` and an optional `reason`. `allow` delegates to the next hook or the default policy, `deny` hard-blocks, and `ask` prompts while respecting "Always Allow"; `auto_approve`, `force_ask` and `deny_unless_prior_grant` also exist (hooks). Because `decision` is required, mode `none` also tests what agy does with no answer. The documented way to give no decision is `allow`, which the stand-in prints in mode `allow`.
- Permissions: the CLI asks before a shell command by default, and reads and writes inside the workspace are auto-allowed. Allow, ask and deny rules live in `~/.gemini/antigravity-cli/settings.json`. Each rule names a resource, such as `command(git)` or `write_file(src/)`, and no listed resource kind covers `invoke_subagent` (permissions). `/permissions` lists the rules in the Project, Shared and Global scopes (`/permissions` command).
- Exit codes and the timeout's effect: not documented.
- Subagents: the agent starts one with `invoke_subagent`, in workspace mode `inherit`, `branch` (its own Git worktree) or `share`. A subagent inherits the parent's command prefixes, file scopes and sandbox settings (subagents). Hooks in subagents are not documented.
- Headless: `agy -p "<prompt>"`. A tool that needs approval it cannot get is soft-denied: the run continues and exits 0. Reads and writes inside the workspace are auto-allowed; shell commands default to Ask, so they are soft-denied unless granted (headless mode). Hooks in headless mode are not documented.

### The stand-in hook

`standin.sh <harness>`, where `<harness>` is `claude`, `codex` or `agy`, is a POSIX `sh` script. For each call it saves one file in `$SPIKE_DIR/events/`, named `<start ms>-<harness>-<pid>.txt`. The file holds its argv (`$0` and the arguments), `pwd`, `$CLAUDE_PROJECT_DIR` (`(unset)` when it is not set), the mode and `start_ms`, then the event between `--- stdin` and `--- end stdin`, then `end_ms` and the exit code. A file without `end_ms` means the Harness ended the hook before it finished.

It then acts on the word in `$SPIKE_DIR/mode`:

| Mode | stdout | stderr | Exit |
| --- | --- | --- | --- |
| `none` | nothing | nothing | 0 |
| `deny` | the Harness's deny answer, reason `spike: deny` | nothing | 0 |
| `ask` | the Harness's ask answer, reason `spike: ask` | nothing | 0 |
| `allow` | agy's allow answer, reason `spike: allow`; nothing for Claude Code and Codex | nothing | 0 |
| `exit1` | nothing | `spike: exit 1` | 1 |
| `exit2` | nothing | `spike: exit 2` | 2 |
| `sleep` | nothing, after sleeping 10 seconds, twice the wiring's `timeout` of 5 | nothing | 0 |
| any mode, for agy's `invoke_subagent` | agy's allow answer, reason `spike: allow` | nothing | 0 |

Any other word, or a missing mode file, acts as `none`. An unknown Harness name saves the event, writes `spike: unknown harness <name>` to stderr and exits 1. Mode `allow` is a fallback for agy, whose pages make `decision` required: Step 2 uses it if agy treats the empty answer of `none` as a failure.

For agy, a call to `invoke_subagent` gets agy's allow answer in every mode, before the mode applies. agy's wiring matches every tool, so the hook also sees the lead's call that starts a subagent. A deny, a declined ask or a failed hook on that call would end a subagent run before the subagent starts. The permission resources that agy lists do not include `invoke_subagent`, so an ask on it would likely prompt on every run.

| Harness | Answer in modes `deny` and `ask`, from the pages above | Answer in mode `allow` |
| --- | --- | --- |
| Claude Code and Codex | `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"<mode>","permissionDecisionReason":"spike: <mode>"}}` | nothing, as in `none` |
| agy | `{"decision":"<mode>","reason":"spike: <mode>"}` | `{"decision":"allow","reason":"spike: allow"}` |

### The scratch repository

Each wiring file runs `standin.sh` with its Harness's name and a `timeout` of 5 seconds:

- `.claude/settings.json`: `PreToolUse` with the matcher `Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor`, running `"$CLAUDE_PROJECT_DIR"/standin.sh claude`, the form Spec 1 gives `devctl hook`.
- `.codex/hooks.json`: `PreToolUse` with the matcher `Bash|apply_patch`, running `"$(git rev-parse --show-toplevel)/standin.sh" codex`, the form the Codex page advises.
- `.agents/hooks.json`: `PreToolUse` with the matcher `*`, running the same git-root form with `agy`. It matches every tool because Spec 1's agy wiring names no tool and agy lists no notebook tool. Every agy tool call therefore gets the mode's answer, except `invoke_subagent`, which the stand-in always allows.

The block below creates the scratch repository `hook-spike` outside rapid-ship, at `$SPIKE_REPO`, which defaults to `$HOME/hook-spike`. It keeps the stand-in's files in `$SPIKE_DIR`, which defaults to `$SPIKE_REPO/.spike` and is ignored by git. `SPIKE_DIR` sits inside the repository because a Codex workspace-write sandbox can write there, and the Codex pages do not say whether a hook runs inside the sandbox. `standin.sh` holds the absolute `SPIKE_DIR`, so it works whatever directory and environment a Harness gives the hook.

The block needs git 2.28 or later, and perl or a `date` that supports `%N`. It refuses an existing `$SPIKE_REPO`. It makes one commit on `main` holding `standin.sh`, the three wiring files, `spike.ipynb` with one code cell (`print(0)`) and `.gitignore`, then adds the linked worktree `.worktrees/wt` on branch `wt`. It sets the mode to `none`. Paste it into a terminal:

```sh
SPIKE_REPO="${SPIKE_REPO:-$HOME/hook-spike}"
SPIKE_DIR="${SPIKE_DIR:-$SPIKE_REPO/.spike}"
export SPIKE_REPO SPIKE_DIR
(
set -eu
case $SPIKE_DIR in
  /*) ;;
  *) echo "SPIKE_DIR must be an absolute path" >&2; exit 1 ;;
esac
case $SPIKE_REPO$SPIKE_DIR in
  *"'"*) echo "SPIKE_REPO and SPIKE_DIR must not contain a single quote" >&2; exit 1 ;;
esac
if [ -e "$SPIKE_REPO" ]; then echo "$SPIKE_REPO already exists" >&2; exit 1; fi
mkdir -p "$SPIKE_REPO" "$SPIKE_DIR/events"
printf 'none\n' > "$SPIKE_DIR/mode"
cd "$SPIKE_REPO"
git init -q -b main
{
printf '#!/bin/sh\n'
printf "SPIKE_DIR='%s'\n" "$SPIKE_DIR"
cat <<'EOF'
# standin.sh <harness>: the stand-in hook of the PRO-139 hook spike.
# It saves the event it reads on stdin, then acts on the word in $SPIKE_DIR/mode.
harness=${1-}

now_ms() {
  t=$(date +%s%N 2>/dev/null) || t=
  case $t in
    '' | *[!0-9]*) perl -MTime::HiRes=time -e 'printf "%d\n", time() * 1000' ;;
    *) printf '%s\n' "${t%??????}" ;;
  esac
}

finish() {
  printf 'end_ms: %s\nexit: %s\n' "$(now_ms)" "$1" >> "$event"
  exit "$1"
}

answer() {
  case $harness in
    claude | codex)
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"spike: %s"}}\n' "$1" "$1" ;;
    agy)
      printf '{"decision":"%s","reason":"spike: %s"}\n' "$1" "$1" ;;
  esac
}

start=$(now_ms)
mode=$(cat "$SPIKE_DIR/mode" 2>/dev/null | tr -d '[:space:]')
mkdir -p "$SPIKE_DIR/events"
event="$SPIKE_DIR/events/$start-$harness-$$.txt"
{
  printf 'argv: %s\n' "$0 $*"
  printf 'pwd: %s\n' "$(pwd)"
  printf 'CLAUDE_PROJECT_DIR: %s\n' "${CLAUDE_PROJECT_DIR-(unset)}"
  printf 'mode: %s\n' "$mode"
  printf 'start_ms: %s\n' "$start"
  printf '%s\n' '--- stdin'
  cat
} > "$event"
[ -z "$(tail -c 1 "$event")" ] || printf '\n' >> "$event"
printf '%s\n' '--- end stdin' >> "$event"

case $harness in
  claude | codex | agy) ;;
  *) printf 'spike: unknown harness %s\n' "$harness" >&2; finish 1 ;;
esac

# agy's matcher * also matches invoke_subagent. Allowing it in every mode lets a subagent run reach the subagent.
if [ "$harness" = agy ] && grep -q '"name" *: *"invoke_subagent"' "$event"; then answer allow; finish 0; fi

case $mode in
  deny | ask) answer "$mode"; finish 0 ;;
  # allow is the no-decision answer that agy documents; Claude Code and Codex get the empty answer of none.
  allow) if [ "$harness" = agy ]; then answer allow; fi; finish 0 ;;
  exit1 | exit2) printf 'spike: exit %s\n' "${mode#exit}" >&2; finish "${mode#exit}" ;;
  # sleep gets no stdout or stderr, so a Harness that ends the hook is not left waiting on it.
  sleep) sleep 10 < /dev/null > /dev/null 2>&1; finish 0 ;;
  *) finish 0 ;;
esac
EOF
} > standin.sh
chmod +x standin.sh
mkdir .claude .codex .agents
cat > .claude/settings.json <<'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/standin.sh claude",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
cat > .codex/hooks.json <<'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|apply_patch",
        "hooks": [
          {
            "type": "command",
            "command": "\"$(git rev-parse --show-toplevel)/standin.sh\" codex",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
cat > .agents/hooks.json <<'EOF'
{
  "spike": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "\"$(git rev-parse --show-toplevel)/standin.sh\" agy",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
cat > spike.ipynb <<'EOF'
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "cell-0",
   "metadata": {},
   "outputs": [],
   "source": ["print(0)"]
  }
 ],
 "metadata": {
  "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
  "language_info": {"name": "python"}
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
EOF
printf '.spike/\n.worktrees/\n' > .gitignore
git add -A
git commit -q -m "hook spike"
git worktree add -q .worktrees/wt
git log --oneline
git worktree list
)
```

## Procedure

The owner runs Steps 2 to 6 on one machine, in order. Note what each Session shows as it happens, because the event files do not hold it. Keep every file under `$SPIKE_DIR/kept/`: Step 7 reads them.

Answer the permission prompts for tool calls the same way in every run, so that a saved answer cannot hide the hook's effect. The trust prompts and Codex's `/hooks` review follow Steps 2 and 4 instead.

1. Approve a prompt for that one call only. Never choose an answer that lasts for the Session or saves a rule, such as Claude Code's "Yes, and don't ask again" or agy's "Always Allow". Claude Code saves such a rule for the whole scratch repository. agy's `ask` answer respects "Always Allow", and agy's subagents inherit the parent's allowed command prefixes (Setup).
2. In Step 3's `ask` runs, decline only the prompt for the call under test: `git status`, or the write of `spike.txt` in a write-prompt run. Approve any other prompt, such as one for a read before the write, so that the agent reaches the call under test. A declined prompt then shows as a call that did not run.
3. Record each prompt, the call it was for and your answer: in Step 2 under Notes, and in Step 3 under Owner's answer in Results.

Paste these helpers into each new terminal:

```sh
SPIKE_REPO="${SPIKE_REPO:-$HOME/hook-spike}"
SPIKE_DIR="${SPIKE_DIR:-$SPIKE_REPO/.spike}"
spike_mode() { printf '%s\n' "$1" >| "$SPIKE_DIR/mode"; }
spike_reset() { rm -f "$SPIKE_REPO/spike.txt" "$SPIKE_REPO/.worktrees/wt/spike.txt"; git -C "$SPIKE_REPO" checkout -q -- spike.ipynb; }
spike_keep() { mkdir -p "$SPIKE_DIR/kept/$1" && mv "$SPIKE_DIR"/events/* "$SPIKE_DIR/kept/$1"/ && ls "$SPIKE_DIR/kept/$1"; }
```

- `spike_mode <mode>` sets the stand-in's mode.
- `spike_reset` removes `spike.txt` and restores `spike.ipynb`, so each run starts from the same files.
- `spike_keep <run>` moves the saved events to `$SPIKE_DIR/kept/<run>` and lists them. If it fails, the run saved no event: zsh reports `no matches found`, and bash reports `mv: ... No such file or directory`. Name each run `<harness>-<session>-<mode>`, for example `codex-subagent-deny`.

Start each Session in `$SPIKE_REPO`:

| Harness | Lead Session | Headless Session |
| --- | --- | --- |
| Claude Code | `claude` | `claude -p "<prompt>" --permission-mode acceptEdits` |
| Codex | `codex` | `codex exec --sandbox workspace-write "<prompt>"` |
| agy | `agy` | `agy -p "<prompt>"` |

The headless options let the file edits run without a prompt. In Claude Code a hook runs before the permission check, so the option does not change what the hook sees. agy's headless mode soft-denies shell commands by default; record it when it does.

The prompts:

- The edit prompt: "Run `git status` in the shell. Write `spike.txt` containing `x`, then edit it so it contains `y`. Replace cell 0 of `spike.ipynb` with `print(1)`." In Claude Code, add: "Then run `git status` through the Monitor tool."
- The shell prompt: "Run `git status` in the shell."
- The write prompt: "Write `spike.txt` containing `x`." agy's `ask` runs and its headless `deny` run use it instead of the shell prompt. agy asks before a shell command by default, and its headless mode soft-denies one, whatever the hook answers (Setup). A write inside the workspace is auto-allowed, so a prompt or a block on the write comes from the hook. G5 also asks before a file edit.
- For a subagent, give the lead: "Start one subagent and give it this task word for word. Do none of it yourself: <prompt>". In agy, add: "Use the inherit workspace."

### Step 2 (Owner): the event matrix

- [ ] Start the first Session of each Harness in `$SPIKE_REPO`. Accept its trust prompt if it shows one, and check in `/hooks` that the spike's hook is loaded. For Codex, also do the first item of Step 4 now.
- [ ] Before the first run, list what else runs on each Harness's tool calls: in Claude Code, `/hooks`, `/plugin` (its dim line names the active mods) and `/status`; in Codex, `/hooks`, `/plugins` and `/status`; in agy, `/hooks`. In Claude Code, turn off each active mod from the Installed tab in `/plugin`, because a mod that handles `tool.check` can approve a call that the hook blocked (Setup).
- [ ] Fill each row of Conditions under Versions:
  - the Claude Code login, from the `Login method` row of `/status` (not the email), and the managed source on its `Setting sources` line;
  - the permission mode or approval policy of each lead Session: the status bar under the prompt in Claude Code and agy, and `/status` in Codex;
  - the mods you turned off, and the hooks, plugins and mods that stay on.
- [ ] Run `spike_mode none`.
- [ ] For each Harness, and for each Session kind (lead, subagent, headless): run `spike_reset`, give the edit prompt, wait until the Session finishes, then run `spike_keep <harness>-<session>-none`.
- [ ] Record for each run whether an event was saved for the shell call, the write, the edit and the notebook edit, and in Claude Code for the Monitor call. Record the tool name each event carries, and anything the Session showed about the hook.
- [ ] Record whether any Claude Code event names `MultiEdit`.
- [ ] If agy's `none` runs show hook errors or blocked calls, record that. Then run `spike_mode allow`, repeat agy's three runs and name them `agy-<session>-allow`. Run `spike_mode none` afterwards.

### Step 3 (Owner): the answers

- [ ] Before the first run, check that no saved rule allows `git` or a write to `spike.txt`. Run `/permissions` in Claude Code, and `/permissions` in agy with its Project, Shared and Global scopes. Delete a rule that a spike run saved, and record any other under Conditions.
- [ ] In a lead Session of each Harness, for each of the modes `deny`, `ask`, `exit1`, `exit2` and `sleep`: run `spike_mode <mode>` and `spike_reset`, give the shell prompt, or the write prompt for agy's `ask`, then run `spike_keep <harness>-lead-<mode>`.
- [ ] Record for each run: whether the call ran (`git status`, or for the write prompt whether `spike.txt` exists); what the Session showed; your answer to each prompt; where the reason (`spike: <mode>` or `spike: exit <n>`) appeared, whether to the agent, to you or nowhere; for `ask`, whether a prompt appeared and what it said; for `sleep`, about how long the call waited and whether the event file has `end_ms`.
- [ ] In a subagent of each Harness, repeat `deny`, `ask` and `exit1` with the same prompts, and record the same. Whether a deny holds in a subagent decides that Harness's wiring.
- [ ] In a headless Session of each Harness, repeat `deny` and `ask`, giving agy the write prompt for both. Record the same, with the run's exit code and output. For agy, also record whether stderr shows agy's soft-deny notice or `spike: <mode>`.
- [ ] Claude Code in `bypassPermissions` mode. On its first use, Claude Code shows a warning dialog. Accepting it sets `skipDangerousModePermissionPrompt` to `true` in `~/.claude/settings.json`, which lasts after the spike; declining it exits Claude Code ([permission modes](https://code.claude.com/docs/en/permission-modes)). First check whether the key is set: `grep -n skipDangerousModePermissionPrompt ~/.claude/settings.json`. Then start `claude --permission-mode bypassPermissions` in `$SPIKE_REPO`, run `spike_mode ask`, give the shell prompt, and run `spike_keep claude-bypass-ask`. Record whether a prompt appeared and whether `git status` ran. End the Session. If the key was not set before, remove it from `~/.claude/settings.json` or set it to `false`.
- [ ] Claude Code and the linked worktree: run `spike_mode none` and `spike_reset`, start `claude` in `$SPIKE_REPO`, which is the main checkout, and give "Write `.worktrees/wt/spike.txt` containing `x`." Then run `spike_keep claude-worktree-none`. Record the event's `cwd` and `tool_input.file_path`, the hook's `CLAUDE_PROJECT_DIR`, and the argv path, which shows which `standin.sh` ran.
- [ ] Run `spike_mode none`, and turn back on the mods that Step 2 turned off.

### Step 4 (Owner): Codex's review

- [ ] On the first `codex` run in `$SPIKE_REPO`, during Step 2: record the trust prompt's text and your choice, any startup warning about hooks, and what `/hooks` shows before and after you trust the spike's hook. Record whether the hook ran before you trusted it.
- [ ] Record whether `codex exec` ran the trusted hook in Step 2. If it saved no event, repeat that run once with `--dangerously-bypass-hook-trust`, and record it as a separate run.
- [ ] Change the hook: set `"timeout": 6` in `.codex/hooks.json`. Start `codex`, run `spike_mode none`, give the shell prompt, then run `spike_keep codex-changed-none`. Record whether Codex asked for a new review, and whether the changed hook ran before you trusted it.
- [ ] Restore the file with `git -C "$SPIKE_REPO" checkout -- .codex/hooks.json`.

### Step 5 (Owner): the hook's cost

Run these from the root of rapid-ship's main checkout, with uv on `PATH`. Paste the Procedure helpers into the same terminal first. The block runs in a subshell and stops before it deletes anything when `SPIKE_DIR` is unset or the directory has no `./devctl`. The `rm -rf` deletes devctl's environment, and the first run creates it again. `./devctl --version` stands in for `devctl hook`, which does not exist yet: it pays the same uv and Python start and imports devctl's CLI.

```sh
(
set -eu
: "${SPIKE_DIR:?paste the Procedure helpers into this terminal first}"
if [ ! -x ./devctl ] || [ ! -d tools/devctl ]; then echo "run this from the root of rapid-ship's main checkout" >&2; exit 1; fi
mkdir -p "$SPIKE_DIR/kept"
rm -rf tools/devctl/.venv
/usr/bin/time -p ./devctl --version 2>&1 | tee "$SPIKE_DIR/kept/devctl-cold.txt"
for i in $(seq 1 20); do
  /usr/bin/time -p ./devctl --version 2>&1 >/dev/null | awk '/^real/ {print $2}'
done | sort -n > "$SPIKE_DIR/kept/devctl-warm.txt"
awk '{t[NR] = $1} END {print "median", (t[10] + t[11]) / 2, "max", t[NR]}' "$SPIKE_DIR/kept/devctl-warm.txt"
)
```

- [ ] Record the cold `real` time, the warm median and maximum, and the commit (`git rev-parse --short HEAD`).

### Step 6 (Owner): decide

- [ ] Decide from Timing whether G1 to G4 stay in the hook. If they move out, Tasks 3, 4 and 6 change, and PR 5.2 waits until you approve the revised plan (Task 1 Step 9).
- [ ] Decide whether a follow-up adds the wiring for Codex, and whether one adds it for agy. Codex's wiring omits G5 if Step 3 showed that its hooks cannot ask.
- [ ] Make each yes a backlog item (this repository tracks them in Linear), and note its ID under Decisions.

## Results

Step 7 fills these tables from the owner's notes and kept files, and labels each result as observed in a run.

### Event matrix (Step 2)

| Harness | Session | Shell | Write | Edit | Notebook edit | Monitor | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | lead | | | | | | |
| Claude Code | subagent | | | | | | |
| Claude Code | headless | | | | | | |
| Codex | lead | | | | | n/a | |
| Codex | subagent | | | | | n/a | |
| Codex | headless | | | | | n/a | |
| agy | lead | | | | | n/a | |
| agy | subagent | | | | | n/a | |
| agy | headless | | | | | n/a | |

Step 7 adds a row for each `agy-<session>-allow` run, if Step 2 needed the fallback.

### Answers (Step 3)

| Harness | Session | Mode | Call ran | Session showed | Reason appeared | Ask prompt | Owner's answer | `end_ms` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | lead | `deny` | | | | n/a | | |
| Claude Code | lead | `ask` | | | | | | |
| Claude Code | lead | `exit1` | | | | n/a | | |
| Claude Code | lead | `exit2` | | | | n/a | | |
| Claude Code | lead | `sleep` | | | | n/a | | |
| Claude Code | subagent | `deny` | | | | n/a | | |
| Claude Code | subagent | `ask` | | | | | | |
| Claude Code | subagent | `exit1` | | | | n/a | | |
| Claude Code | headless | `deny` | | | | n/a | | |
| Claude Code | headless | `ask` | | | | | | |
| Claude Code | lead, `bypassPermissions` | `ask` | | | | | | |
| Codex | lead | `deny` | | | | n/a | | |
| Codex | lead | `ask` | | | | | | |
| Codex | lead | `exit1` | | | | n/a | | |
| Codex | lead | `exit2` | | | | n/a | | |
| Codex | lead | `sleep` | | | | n/a | | |
| Codex | subagent | `deny` | | | | n/a | | |
| Codex | subagent | `ask` | | | | | | |
| Codex | subagent | `exit1` | | | | n/a | | |
| Codex | headless | `deny` | | | | n/a | | |
| Codex | headless | `ask` | | | | | | |
| agy | lead | `deny` | | | | n/a | | |
| agy | lead | `ask` | | | | | | |
| agy | lead | `exit1` | | | | n/a | | |
| agy | lead | `exit2` | | | | n/a | | |
| agy | lead | `sleep` | | | | n/a | | |
| agy | subagent | `deny` | | | | n/a | | |
| agy | subagent | `ask` | | | | | | |
| agy | subagent | `exit1` | | | | n/a | | |
| agy | headless | `deny` | | | | n/a | | |
| agy | headless | `ask` | | | | | | |

agy's `ask` rows and its headless `deny` row are runs of the write prompt. In agy's subagent rows, the stand-in allowed the lead's `invoke_subagent` call (Setup).

The edit inside the linked worktree, in Claude Code:

| Event `cwd` | `tool_input.file_path` | `CLAUDE_PROJECT_DIR` | `standin.sh` that ran |
| --- | --- | --- | --- |
| | | | |

### Codex review (Step 4)

- Trust prompt on the first run:
- Hooks before review:
- `/hooks` review:
- `codex exec` with the trusted hook:
- The changed hook:

## Events

Step 7 puts each Claude Code event here as a fenced `json` block under the heading of its fixture file, and Task 4 copies each block byte for byte into `tests/devctl/fixtures/hooks/claude/`. Step 7 replaces the values of `session_id`, `prompt_id`, `transcript_path`, `tool_use_id`, `agent_id` and `scratchpad_dir` with `"<redacted>"`. It replaces the scratch repository's path with `/repo`, so its worktree becomes `/repo/.worktrees/wt`, and any other home or temporary path with `<redacted>`. It lists the fields it replaced.

### bash.json

From the run `claude-lead-none`. Step 7 adds it.

### bash-subagent.json

From the run `claude-subagent-none`. Step 7 adds it.

### write.json

From the run `claude-lead-none`. Step 7 adds it.

### edit.json

From the run `claude-lead-none`. Step 7 adds it.

### notebook-edit.json

From the run `claude-lead-none`. Step 7 adds it.

### multi-edit.json

Only if Step 2 saw a `MultiEdit` event. Otherwise Step 7 removes this heading and says so.

## Timing

Claude Code's documented default `timeout` for a command hook is 600 seconds ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-10-21). Step 7 fills the rest from Step 5.

| Measure | Seconds |
| --- | --- |
| Cold run, after `rm -rf tools/devctl/.venv` | |
| Warm median of 20 runs | |
| Warm maximum of 20 runs | |

## Decisions

Step 7 records the owner's decisions from Step 6.

### G1 to G4 in the hook

### Codex and agy wiring

## Limits

- On 2026-10-21 the record holds only its preparation: no Harness Session has run, and every result above is empty.
- The stand-in is not `devctl hook`. It answers by mode, not by rules, and it starts `sh`, not uv and Python. Step 5 times `./devctl --version` instead, which runs no rule; Task 8 times the real hook.
- Each run happens once, on one machine, with one version of each Harness. A model can skip or reorder a requested call, so the event files, not the Session's summary, show what the hook saw.
- The documented behaviour in Setup holds for the pages as read on 2026-10-21. Where a page documents nothing, such as agy's exit codes or Codex's exit 1, only the runs answer the question.
- agy's wiring matches every tool, so its runs also save events for reads and listings. The stand-in allows agy's `invoke_subagent` in every mode, so the spike does not observe a deny or an ask on starting a subagent.
- Other hooks, plugins and mods on the owner's machine also run on these events. Conditions under Versions lists those that stayed on.
- Desktop apps and IDE extensions are out of scope.
