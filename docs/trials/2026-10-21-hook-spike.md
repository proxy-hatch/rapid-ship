# Hook spike (PRO-139)

Status: prepared on 2026-10-21 as Task 1 Step 1 of [plan 5](../superpowers/plans/2026-10-21-kit-standards-and-guardrails.md). The owner ran Steps 2 to 6 on 2026-10-21 from 22:02 to 22:18 and on 2026-10-22 from 19:45 to 20:18, in UTC+8. Step 7 filled Versions, Results, Events, Timing, Decisions and Limits on 2026-10-22 from the owner's results file, the kept event files and the headless output.

## Purpose

[Spec 1](../superpowers/specs/2026-10-14-kit-and-setup-design.md) wires Claude Code's hooks to `devctl hook` and leaves Codex and agy without wiring until this spike reports. The spike runs a stand-in hook in each of the three Harnesses, in a lead Session, in a subagent and in a headless Session, because `devctl hook` does not exist yet. It records:

- whether each wired event fires, and which fields it carries;
- how each Harness treats the hook's deny and ask answers, exit 1, exit 2 (the code uv exits with when it fails), and a hook that outlives its timeout;
- whether Codex hooks can ask, and how Codex's trust and `/hooks` review work;
- in Claude Code, a hook's ask in `bypassPermissions` mode, and which directory and hook a Session uses for an edit inside a linked worktree;
- how long `./devctl --version` takes, as a stand-in for the cost of `devctl hook` on every matched tool call.

From this record the owner decides whether G1 to G4 stay in the hook, and whether a follow-up adds the wiring for Codex and for agy (Spec 1 sections 4 and 11). Task 4 copies the Claude Code events under [Events](#events) into test fixtures.

## Versions

From the owner's results file, written when the runs started.

| Item | Command | Version |
| --- | --- | --- |
| Claude Code | `claude --version` | 2.1.304 |
| Codex CLI | `codex --version` | codex-cli 0.163.0 |
| Antigravity CLI (agy) | `agy --version` | 1.4.3 |
| uv | `uv --version` | 0.11.0 (Homebrew, aarch64-apple-darwin) |
| rapid-ship commit timed in Step 5 | `git rev-parse --short HEAD` | `0e1d6d0`, tagged `v0.1.0` |
| Operating system | `uname -sr` | Darwin 24.6.0 |

Conditions, from Steps 2 and 3:

- Claude Code login, a personal subscription or a Team or Enterprise `/login`, and the managed source on the `Setting sources` line of `/status`, if any: a Claude Max subscription, in the owner's words. The owner named no managed source.
- Mods turned off for the spike: many, "including mcp and skills", in the owner's words. The record has no list of them.
- User-level hooks, plugins and mods that stayed on, for each Harness:
  - Claude Code: two user-level `PreToolUse` hooks in the owner's `~/.claude/settings.json`, an iTerm2 status script and an inline shell command.
  - Codex: `/hooks` listed two `PreToolUse` hooks, installed and active, and each `codex exec` output shows two `PreToolUse` hook runs for each shell call. The owner described the plugins as "quite a few".
  - agy: none besides `spike`.
- Permission mode or approval policy of each Harness's lead Session:
  - Claude Code: the owner gave none. Every lead and subagent event carries `permission_mode` `auto`, the `bypassPermissions` run carries `bypassPermissions`, and the headless runs carry `acceptEdits`.
  - Codex: the interactive events carry `permission_mode` `default`. The `codex exec` events carry `bypassPermissions`, and the output header of each `codex exec` run shows `approval: never` and `sandbox: workspace-write`.
  - agy: not recorded, because its interactive Sessions did not run.
- Saved allow rules found before Step 3: none in each Harness, in the owner's answers.
- Models named in the events: Codex used `gpt-6.1-sol` in its first lead Session and `gpt-6-luna` after it, and agy used `gemini-3.8-flash-high`. Claude Code's events name no model; each carries `effort` `{"level": "max"}`.

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
- Permissions: the CLI's permission rules ask before a shell command by default, and allow reads and writes inside the workspace. Allow, ask and deny rules live in `~/.gemini/antigravity-cli/settings.json`. Each rule names a resource, such as `command(git)` or `write_file(src/)`, and no listed resource kind covers `invoke_subagent` (permissions). `/permissions` lists the rules in the Project, Shared and Global scopes (`/permissions` command).
- Execution modes: in the `default` mode, the CLI also pauses for a diff review before it creates or modifies a file, under a `Create file` header for a new file. The `accept-edits` mode approves file writes and creations, and `agy --mode=accept-edits` starts a Session in it. Shell commands follow the permission rules in every mode. The status bar shows `[accept-edits]` or `[plan]`, and the page names no indicator for `default`. `--mode` overrides the `agentMode` setting for one run (execution modes). The pages do not say whether `accept-edits` also approves a hook's `ask` on a write.
- Exit codes and the timeout's effect: not documented.
- Subagents: the agent starts one with `invoke_subagent`, in workspace mode `inherit`, `branch` (its own Git worktree) or `share`. A subagent inherits the parent's command prefixes, file scopes and sandbox settings (subagents), and its `accept-edits` mode (execution modes). Hooks in subagents are not documented.
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

For agy, a call to `invoke_subagent` gets agy's allow answer in every mode, before the mode applies. agy's wiring matches every tool, so the hook also sees the lead's call that starts a subagent. A deny or a declined ask on that call would end a subagent run before the subagent starts. A failed hook might do the same, because agy documents no exit codes ([What each Harness documents](#what-each-harness-documents)). The permission resources that agy lists do not include `invoke_subagent`, so an ask on it would likely prompt on every run.

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
| agy | `agy --mode=accept-edits` | `agy -p "<prompt>"` |

The headless options let the file edits run without a prompt. In Claude Code a hook runs before the permission check, so the option does not change what the hook sees. In agy, `--mode=accept-edits` approves file writes without agy's diff review, in the lead Session and its subagents. agy's headless mode soft-denies shell commands by default; record it when it does.

The prompts:

- The edit prompt: "Run `git status` in the shell. Write `spike.txt` containing `x`, then edit it so it contains `y`. Replace cell 0 of `spike.ipynb` with `print(1)`." In Claude Code, add: "Then run `git status` through the Monitor tool."
- The shell prompt: "Run `git status` in the shell."
- The write prompt: "Write `spike.txt` containing `x`." agy's `ask` runs and its headless `deny` run use it instead of the shell prompt. agy asks before a shell command by default, and its headless mode soft-denies one, whatever the hook answers (Setup). agy's permission rules allow a write inside the workspace, but its `default` mode adds a diff review before the write. In `accept-edits` mode and in headless mode, agy allows the write without a prompt (Setup), so a prompt or a block on the write comes from the hook. G5 also asks before a file edit.
- For a subagent, give the lead: "Start one subagent and give it this task word for word. Do none of it yourself: <prompt>". In agy, add: "Use the inherit workspace."

### Step 2 (Owner): the event matrix

- [ ] Start the first Session of each Harness in `$SPIKE_REPO`. Accept its trust prompt if it shows one, and check in `/hooks` that the spike's hook is loaded. For Codex, also do the first item of Step 4 now.
- [ ] Before the first run, list what else runs on each Harness's tool calls: in Claude Code, `/hooks`, `/plugin` (its dim line names the active mods) and `/status`; in Codex, `/hooks`, `/plugins` and `/status`; in agy, `/hooks`. In Claude Code, turn off each active mod from the Installed tab in `/plugin`, because a mod that handles `tool.check` can approve a call that the hook blocked (Setup).
- [ ] Fill each row of Conditions under Versions:
  - the Claude Code login, from the `Login method` row of `/status` (not the email), and the managed source on its `Setting sources` line;
  - the permission mode or approval policy of each lead Session: the status bar under the prompt in Claude Code, and `/status` in Codex. agy's status bar must show `[accept-edits]`. If it shows nothing or `[plan]`, end the agy Session and start it again with `agy --mode=accept-edits`;
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

Each result below is observed in the run it names. A result that is an inference, or only the owner's words, says so.

### How the runs went

The owner ran Steps 2 to 6 through a guide script kept outside this repository. For each run, the guide set the mode, gave the prompt, kept the events when the owner said that the Session had finished, and wrote the owner's answers to a results file. Step 7 took each result from the event files and the headless output. It took the owner's answers only for what those files cannot show: whether a call ran, what the Session showed, and the prompts. Four points affect how to read the results.

1. **Stray folders.** When the owner went on before a Session had finished, the guide kept that run too early. The run's later events stayed in `$SPIKE_DIR/events/`, and the guide moved them to `kept/_stray-<time>/` when the next run started. Step 7 maps each stray folder to its run by the events' start time, mode and Session:

   | Folder | Events, with the stand-in's mode | Run | Evidence |
   | --- | --- | --- | --- |
   | `_stray-221151` | Claude Code `Bash`, `Write`, `NotebookEdit`, `Edit` and `Monitor`, each with `agent_id`; `none` | `claude-subagent-none` | The guide kept that run 14 seconds before the first event |
   | `_stray-221502` | Claude Code `Bash`, answered with the deny answer; `deny` | `claude-lead-deny` | The guide kept that run 1 second before the event |
   | `_stray-221622` | Claude Code `Bash`; `ask` | `claude-lead-ask` | The same Session as that run's event, from a later prompt |
   | `_stray-194519` | Claude Code `Bash`, exit 2, at 22:18 on 2026-10-21; `exit2` | `claude-lead-exit2` | The guide kept that run 1 second before the event, and moved the event when the runs went on, on 2026-10-22 |
   | `_stray-195944` | One Codex lead `Bash` event and six subagent `Bash` events with `agent_id`; `none` | `codex-subagent-none` | The guide kept that run 21 seconds before the first event; all seven events have one `session_id` |

2. **An invalid run.** `claude-lead-exit1` saved no event, and no Claude Code lead event has the mode `exit1`. The owner's answers for it describe the `ask` prompt of `_stray-221622`. This record counts the run as invalid. `claude-subagent-exit1` shows what Claude Code does with exit 1.
3. **Runs that did not happen.** The owner skipped agy's interactive Sessions. Every `agy-lead-*` and `agy-subagent-*` folder is empty, and the guide kept each one within seconds of the one before it. The owner answered "yes" to "Did agy's none runs show hook errors or blocked calls?" only to move on, so the answer is not an observation. It started the `allow` runs, and of those only the headless run ran.
4. **Codex worktrees.** `codex-subagent-none` and each Codex lead and subagent run of Step 3 ran in a worktree that Codex made outside the scratch repository (path `<redacted>`). The hook there ran that worktree's `standin.sh`, which the wiring finds with `git rev-parse --show-toplevel`, and saved its events in the same `SPIKE_DIR`. `codex-lead-none`, the `codex exec` runs and `codex-changed-none` ran in the scratch repository.

### Event matrix (Step 2)

Each cell names the tool of the event that the run saved for that call. Where no file-edit tool ran, the cell names the shell command that made the change.

| Harness | Session | Shell | Write | Edit | Notebook edit | Monitor | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | lead (`claude-lead-none`) | `Bash` | `Write` | `Edit` | `NotebookEdit` | `Monitor` | No prompt. No event names `MultiEdit` |
| Claude Code | subagent (`claude-subagent-none`, in `_stray-221151`) | `Bash` | `Write` | `Edit` | `NotebookEdit` | `Monitor` | Each event carries `agent_id` and `agent_type` `general-purpose`. No prompt |
| Claude Code | headless (`claude-headless-none`) | `Bash`, twice | `Write` | `Edit` | `NotebookEdit` | `Monitor` | Exit 0. The second `Bash` call is `ls -la /repo`. No event carries `scratchpad_dir` |
| Codex | lead (`codex-lead-none`) | `Bash` | `Bash`: `printf x > spike.txt` | `Bash`: a `python3` heredoc | `apply_patch` | n/a | Eight events: seven `Bash`, among them reads of plugin skill files, and one `apply_patch`. No prompt |
| Codex | subagent (`codex-subagent-none`, in `_stray-195944`) | `Bash` | `Bash`: `printf 'x' > spike.txt` | `Bash`: `printf 'y' > spike.txt` | `Bash`: `python3 -c` | n/a | The six subagent events carry `agent_id` and `agent_type` `worker`. No prompt |
| Codex | headless (`codex-headless-none`) | `Bash`: `git status --short --branch && rg --files …` | `Bash`: one `python3 -c` wrote both files | the same call | the same call | n/a | Exit 0. Three `Bash` events |
| agy | lead | not run | not run | not run | not run | n/a | Skipped by the owner |
| agy | subagent | not run | not run | not run | not run | n/a | Skipped by the owner |
| agy | headless (`agy-headless-none`) | `run_command` | not reached | not reached | not reached | n/a | Exit 0. The stand-in gave no answer, then agy soft-denied the shell command: `a tool required the "command" permission that headless mode cannot prompt for`. The run ended with no output |
| agy | headless, mode `allow` (`agy-headless-allow`) | `run_command` | not reached | not reached | not reached | n/a | Exit 0. The stand-in answered `allow`, and agy soft-denied the shell command, as in `none` |

agy's `allow` runs in a lead Session and in a subagent did not run.

### Fixture events (Step 2)

Task 4 copies the blocks under [Events](#events). Each block's scrubbed values match what Task 4 expects: `command` `git status`, `/repo/spike.txt` and `/repo/spike.ipynb`, with `cwd` `/repo`.

| Fixture | Run, and its event file | `tool_name` | Scrubbed `tool_input` value | `cwd` |
| --- | --- | --- | --- | --- |
| `bash.json` | `claude-lead-none`, `1792591708677-claude-11892.txt` | `Bash` | `command`: `git status` | `/repo` |
| `bash-subagent.json` | `claude-subagent-none`, `_stray-221151/1792591849756-claude-12657.txt` | `Bash` | `command`: `git status` | `/repo` |
| `write.json` | `claude-lead-none`, `1792591718058-claude-12178.txt` | `Write` | `file_path`: `/repo/spike.txt` | `/repo` |
| `edit.json` | `claude-lead-none`, `1792591721236-claude-12246.txt` | `Edit` | `file_path`: `/repo/spike.txt` | `/repo` |
| `notebook-edit.json` | `claude-lead-none`, `1792591718511-claude-12208.txt` | `NotebookEdit` | `notebook_path`: `/repo/spike.ipynb` | `/repo` |
| `monitor.json` | `claude-lead-none`, `1792591728430-claude-12306.txt` | `Monitor` | `command`: `git status` | `/repo` |

The other Claude Code events all have `cwd` `/repo`. Their `Bash` events have `command` `git status`, except three: `ls -la /repo` in `claude-headless-none`, `git -C /repo status` in `claude-subagent-deny`, and the first event of `claude-worktree-none` (below). Their `Write`, `Edit`, `NotebookEdit` and `Monitor` events have the fixtures' `command`, `file_path` and `notebook_path` values, except the worktree write.

### Answers (Step 3)

"Reason appeared" gives the owner's answer to the guide's question: to the agent, to the owner, or nowhere. A quoted Session message is the owner's copy of it, or the headless output.

| Harness | Session | Mode | Call ran | Session showed | Reason appeared | Ask prompt | Owner's answer | `end_ms` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | lead | `deny` | no | nothing else, in the owner's notes | to the owner | n/a | no prompt | yes, exit 0, in `_stray-221502` |
| Claude Code | lead | `ask` | yes | a prompt: "Hook PreToolUse:Bash requires confirmation for this command: spike: ask [settings]", with a line about `settings.json` | to the owner, in the prompt | yes | not recorded; the call ran | yes. A second `ask` event, from a later prompt in the same Session, is in `_stray-221622` |
| Claude Code | lead | `exit1` | invalid: no `exit1` event | the owner's answers describe the `ask` prompt | n/a | n/a | n/a | no event |
| Claude Code | lead | `exit2` | no | Claude said that the hook blocked `git status` and "exited 2 with the message spike: exit 2", and did not retry | to the agent | n/a | no prompt | yes, exit 2, in `_stray-194519` |
| Claude Code | lead | `sleep` | yes | nothing about the hook | nowhere | n/a | no prompt | no: the hook was ended before it finished, as the wiring's 5-second timeout explains. The owner's answer for the wait, 0 seconds, was not measured |
| Claude Code | subagent | `deny` | no | nothing else, in the owner's notes | to the agent | n/a | no prompt | yes. The subagent ran `git -C /repo status` |
| Claude Code | subagent | `ask` | yes | a prompt, with the line about `settings.json` | to the owner | yes | yes | yes |
| Claude Code | subagent | `exit1` | yes | nothing about the hook | nowhere | n/a | no prompt | yes, exit 1 |
| Claude Code | headless | `deny` | no | Exit 0. Claude replied that the call "was denied with the message `spike: deny`", and did not retry | to the agent, in the output | n/a | n/a | yes |
| Claude Code | headless | `ask` | no | Exit 0. Claude replied that the call "came back with `spike: ask`", that nobody could answer the prompt in a non-interactive Session, and that it treated the answer as a denial | to the agent, in the output | no prompt; Claude Code denied the call | n/a | yes |
| Claude Code | lead, `bypassPermissions` | `ask` | yes | a prompt with "spike: ask [settings]". The event's `permission_mode` is `bypassPermissions` | to the owner, in the prompt | yes | yes | yes |
| Codex | lead | `deny` | no | nothing else, in the owner's notes | to the owner | n/a | no prompt | yes |
| Codex | lead | `ask` | yes | nothing about the hook | nowhere | no | no prompt | yes |
| Codex | lead | `exit1` | yes | "hook exited with code 1" | nowhere | n/a | no prompt | yes, exit 1 |
| Codex | lead | `exit2` | no | a block notice. The owner's note reads "Blocked by hook spike: exit 21"; the stand-in writes `spike: exit 2` | to the owner | n/a | no prompt | yes, exit 2 |
| Codex | lead | `sleep` | yes | "Hook failed" and "hook timed out after 5s" | the timeout notice, to the owner | n/a | no prompt | no. The owner's answer for the wait: 5 seconds |
| Codex | subagent | `deny` | no | "The subagent attempted git status, but the PreToolUse hook (spike: deny) blocked it." | to the agent | n/a | no prompt | yes |
| Codex | subagent | `ask` | yes | nothing about the hook | nowhere | no | no prompt | yes |
| Codex | subagent | `exit1` | yes | nothing about the hook | nowhere | n/a | no prompt | yes, exit 1. The subagent ran `git status --short --branch` |
| Codex | headless | `deny` | no | Exit 0. The error line `Command blocked by PreToolUse hook: spike: deny. Command: git status`, then `hook: PreToolUse Blocked`, and the agent's reply that the hook blocked the command | in the output, and to the agent | n/a | n/a | yes |
| Codex | headless | `ask` | yes | Exit 0. `hook: PreToolUse Failed`, then `git status` ran and succeeded | nowhere | no | n/a | yes |
| agy | lead | `deny` | not run | | | n/a | | |
| agy | lead | `ask` | not run | | | | | |
| agy | lead | `exit1` | not run | | | n/a | | |
| agy | lead | `exit2` | not run | | | n/a | | |
| agy | lead | `sleep` | not run | | | n/a | | |
| agy | subagent | `deny` | not run | | | n/a | | |
| agy | subagent | `ask` | not run | | | | | |
| agy | subagent | `exit1` | not run | | | n/a | | |
| agy | headless | `deny` | no: no `spike.txt` | Exit 0. `tool call denied by pre-tool hook: spike: deny`. The hook also answered deny to the agent's next three calls: `run_command` `ls -la` and two `read_file` | in the output, and to the agent | n/a | n/a | yes, four events |
| agy | headless | `ask` | no: no `spike.txt` | Exit 0. agy's notice that the `write_file` permission cannot be prompted for in headless mode, so it was auto-denied | nowhere | no prompt; agy denied the call | n/a | yes |

agy's `ask` rows and its headless `deny` row are runs of the write prompt. agy's lead and subagent rows did not run, so the stand-in's allowance of `invoke_subagent` was not exercised.

Inference, not observed: agy's headless page says that writes inside the workspace are allowed without a prompt. The hook's `ask` is therefore the likely cause of the soft-deny of `write_file` in `agy-headless-ask`, but its output does not name the hook.

The edit inside the linked worktree, in Claude Code (`claude-worktree-none`):

| Event `cwd` | `tool_input.file_path` | `CLAUDE_PROJECT_DIR` | `standin.sh` that ran |
| --- | --- | --- | --- |
| `/repo` | `/repo/.worktrees/wt/spike.txt` | `/repo` | `/repo/standin.sh`, the main checkout's |

A lead Session started in the main checkout wrote `.worktrees/wt/spike.txt` with `Write`. Before the write it ran `ls -la /repo/.worktrees/ /repo/.worktrees/wt/ 2>&1; git -C /repo worktree list 2>&1` with `Bash`, and that event shows the same `cwd`, `CLAUDE_PROJECT_DIR` and `standin.sh`. The hook's `pwd` was `/repo` for both events. Only the edited path names the worktree, so the hook has to judge an edit by the repository that holds its path, as plan 5's Task 3 rules.

### Codex review (Step 4)

- Trust prompt on the first run: the owner chose to require a review, then trusted the spike's hook ("require review. Trusted.", in the owner's words).
- Hooks before review: Codex showed a startup warning about hooks. The guide found no event between the Session's start and the first run, so no hook run before the review was saved.
- `/hooks` review: after the review, `/hooks` listed `PreToolUse` with two hooks, installed and active.
- `codex exec` with the trusted hook: it ran the hook. `codex-headless-none` saved three events, so the run with `--dangerously-bypass-hook-trust` was not needed.
- The changed hook: after the change to `"timeout": 6`, Codex offered to review the hook or trust all ("review hook or trust all", in the owner's words). The changed hook did not run before the owner trusted it, in the owner's answer. `codex-changed-none` then saved one `Bash` event, `git status`, in the scratch repository.
- In the Codex worktrees of Step 3, the trusted hook ran, and the owner recorded no new review.

### Other observations

- The hook's working directory: Claude Code's hook ran with `pwd` and `CLAUDE_PROJECT_DIR` at `/repo` in every run. Codex's hook ran with `pwd` at the Session's `cwd`, the scratch repository or a Codex worktree, and with `CLAUDE_PROJECT_DIR` unset. agy's hook ran with `pwd` at `/repo/.agents`, the folder that holds its `hooks.json`.
- Claude Code's events carry the fields that Setup lists. `effort` is an object, such as `{"level": "max"}`, and the headless events have no `scratchpad_dir`.
- Codex's events carry `session_id`, `turn_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`, `permission_mode`, `tool_name`, `tool_input` and `tool_use_id`. A subagent's events also carry `agent_id` and `agent_type`. The `tool_input.command` of `apply_patch` holds the patch.
- agy's events carry `artifactDirectoryPath`, `conversationId`, `modelName`, `stepIdx`, `toolCall`, `transcriptPath` and `workspacePaths`. Its tools were `run_command` (`args.CommandLine`), `write_file` (`args.Path` and `args.Content`) and `read_file` (`args.Path`). agy's hooks page names the write tool `write_to_file`.
- In Codex, the agent wrote and edited files with shell commands in every Session kind, and used `apply_patch` once, for the notebook. A Codex wiring sees such writes only as shell commands.

## Events

Task 4 copies each block below byte for byte into `tests/devctl/fixtures/hooks/claude/`, named by its heading. Each block is the Claude Code event that [Fixture events](#fixture-events-step-2) names, pretty-printed with two-space indents, with its keys in the order Claude Code sent them.

Step 7 replaced these values, and no others:

- In every event: `session_id`, `prompt_id`, `transcript_path`, `tool_use_id` and `scratchpad_dir` became `"<redacted>"`, and `cwd`, the scratch repository's path, became `/repo`.
- In `bash-subagent.json`: `agent_id` became `"<redacted>"`.
- In `write.json` and `edit.json`: `tool_input.file_path` became `/repo/spike.txt`. In `notebook-edit.json`: `tool_input.notebook_path` became `/repo/spike.ipynb`.

No other value held a home or temporary path. No Claude Code event in the spike names `MultiEdit`, so the record has no `multi-edit.json`.

### bash.json

From the run `claude-lead-none`.

```json
{
  "session_id": "<redacted>",
  "transcript_path": "<redacted>",
  "cwd": "/repo",
  "scratchpad_dir": "<redacted>",
  "prompt_id": "<redacted>",
  "permission_mode": "auto",
  "effort": {
    "level": "max"
  },
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git status",
    "description": "Show working tree status"
  },
  "tool_use_id": "<redacted>"
}
```

### bash-subagent.json

From the run `claude-subagent-none`, whose events the guide moved to `_stray-221151`.

```json
{
  "session_id": "<redacted>",
  "transcript_path": "<redacted>",
  "cwd": "/repo",
  "scratchpad_dir": "<redacted>",
  "prompt_id": "<redacted>",
  "permission_mode": "auto",
  "agent_id": "<redacted>",
  "agent_type": "general-purpose",
  "effort": {
    "level": "max"
  },
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git status",
    "description": "Show working tree status"
  },
  "tool_use_id": "<redacted>"
}
```

### write.json

From the run `claude-lead-none`.

```json
{
  "session_id": "<redacted>",
  "transcript_path": "<redacted>",
  "cwd": "/repo",
  "scratchpad_dir": "<redacted>",
  "prompt_id": "<redacted>",
  "permission_mode": "auto",
  "effort": {
    "level": "max"
  },
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/repo/spike.txt",
    "content": "x"
  },
  "tool_use_id": "<redacted>"
}
```

### edit.json

From the run `claude-lead-none`.

```json
{
  "session_id": "<redacted>",
  "transcript_path": "<redacted>",
  "cwd": "/repo",
  "scratchpad_dir": "<redacted>",
  "prompt_id": "<redacted>",
  "permission_mode": "auto",
  "effort": {
    "level": "max"
  },
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/repo/spike.txt",
    "old_string": "x",
    "new_string": "y",
    "replace_all": false
  },
  "tool_use_id": "<redacted>"
}
```

### notebook-edit.json

From the run `claude-lead-none`.

```json
{
  "session_id": "<redacted>",
  "transcript_path": "<redacted>",
  "cwd": "/repo",
  "scratchpad_dir": "<redacted>",
  "prompt_id": "<redacted>",
  "permission_mode": "auto",
  "effort": {
    "level": "max"
  },
  "hook_event_name": "PreToolUse",
  "tool_name": "NotebookEdit",
  "tool_input": {
    "notebook_path": "/repo/spike.ipynb",
    "cell_id": "cell-0",
    "new_source": "print(1)",
    "edit_mode": "replace"
  },
  "tool_use_id": "<redacted>"
}
```

### monitor.json

From the run `claude-lead-none`. Plan 5 wires `Monitor` after this spike ([Decisions](#what-the-record-changes-in-plan-5)).

```json
{
  "session_id": "<redacted>",
  "transcript_path": "<redacted>",
  "cwd": "/repo",
  "scratchpad_dir": "<redacted>",
  "prompt_id": "<redacted>",
  "permission_mode": "auto",
  "effort": {
    "level": "max"
  },
  "hook_event_name": "PreToolUse",
  "tool_name": "Monitor",
  "tool_input": {
    "description": "git status output after spike.txt and spike.ipynb edits",
    "timeout_ms": 30000,
    "command": "git status"
  },
  "tool_use_id": "<redacted>"
}
```

## Timing

Claude Code's documented default `timeout` for a command hook is 600 seconds ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-10-21). The spike's wiring set 5 seconds, and its `sleep` runs show what a timeout does to the call (Answers).

The owner ran Step 5's block on 2026-10-22, in rapid-ship's main checkout at `0e1d6d0` (`v0.1.0`). The cold run printed `devctl 0.1.0`.

| Measure | Seconds |
| --- | --- |
| Cold run, after `rm -rf tools/devctl/.venv` | 2.39 real (0.49 user, 0.21 sys) |
| Warm median of 20 runs | 0.10 |
| Warm maximum of 20 runs | 0.14 |

The 20 warm times, sorted: twelve of 0.10, six of 0.11, one of 0.12 and one of 0.14.

## Decisions

The owner made these decisions on 2026-10-22, from this record.

### G1 to G4 in the hook

G1 to G4 stay in the hook. A warm `./devctl --version` took 0.10 seconds at the median and 0.14 at most. The one cold run, which rebuilt devctl's environment, took 2.39 seconds. Task 8 times the real `devctl hook`.

### Codex and agy wiring

- Codex: a follow-up wires Codex after plan 5, without G5, because Codex ran the call with no prompt on the hook's ask (backlog item PRO-142).
- agy: no decision yet. The owner decides after agy's interactive runs, a lead Session and a subagent, which this spike did not run (backlog item PRO-143).

### What the record changes in plan 5

Task 1 Step 9 of plan 5 compares the record with what Tasks 3 to 8 assume:

- `Monitor`: Claude Code's `Monitor` tool fired `PreToolUse` with `tool_input.command`, a shell command, in a lead Session, a subagent and a headless Session. Without it in the wiring, an agent could bypass G1 to G3, G7, G8 and the merge guard through `Monitor`. Plan 5 therefore wires `Monitor` and reads its `command` as `Bash`'s.
- `MultiEdit`: no event named it, and Claude Code's permissions page calls it legacy. Plan 5 keeps it in the wiring, which costs nothing and covers versions that still have it.
- `"onFailure": "block"`: the spike's wiring left it unset, and no run exercised it. The seed leaves it unset, and Spec 1 section 11 holds it as an open question.
- The rest held: the event fields, the command and paths that Task 4 expects, the deny and ask answers, exit 1 not blocking, a timed-out hook letting the call through, and the paths of an edit in a linked worktree.

## Limits

- Each run happened once, on one machine, with one version of each Harness (Versions). A model can skip or reorder a requested call, so the event files, not the Session's summary, show what the hook saw.
- The stand-in is not `devctl hook`. It answers by mode, not by rules, and it starts `sh`, not uv and Python. Step 5 times `./devctl --version` instead, which runs no rule; Task 8 times the real hook.
- agy's lead and subagent Sessions did not run. The record has nothing on agy's interactive hooks, its subagents, its exit codes or its timeout, and nothing on agy's `invoke_subagent` or its `accept-edits` mode. agy's own soft-deny of a shell command hid the hook's answer in its headless `none` and `allow` runs.
- Claude Code's lead `exit1` run is invalid. Exit 1 in Claude Code is observed only in a subagent.
- In the interactive `ask` runs, the owner approved Claude Code's prompts, where the Procedure asked to decline the call under test. The spike shows that the prompt appears and that an approved call runs. It does not show a declined ask in an interactive Session. The headless runs show Claude Code denying an ask that nobody can answer.
- Some answers are the owner's own words, quoted as given. The owner did not measure `claude-lead-sleep`'s wait and answered 0 seconds; the event's missing `end_ms` shows that Claude Code ended the hook.
- The stand-in's exit 2 stood in for uv's exit 2. No real uv failure ran.
- No run exercised `"onFailure": "block"`.
- Codex's Step 3 Sessions ran in Codex worktrees, which `spike_reset` did not reach. The shell prompt does not depend on those files.
- Other hooks, plugins and mods on the owner's machine also ran on these events. Conditions under Versions lists those that stayed on.
- The documented behaviour in Setup holds for the pages as read on 2026-10-21. Where a page documents nothing, such as agy's exit codes or Codex's exit 1, only the runs answer the question.
- agy's wiring matches every tool, so its headless `deny` run also saved events for a listing and for reads.
- Desktop apps and IDE extensions are out of scope.
