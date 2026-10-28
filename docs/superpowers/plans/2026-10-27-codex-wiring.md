# Codex wiring implementation plan

**Goal:** Wire Codex to the Kit's guardrails, without G5 (PRO-142).

**Architecture:** Reuse the per-Harness protocol and doctor boundaries built for agy. Parse Codex patches into every written path before the existing rules decide. Seed `.codex/hooks.json`; resolve devctl from the current git top level, including linked worktrees. No service or agent orchestration is added.

**Requirements:** [Spec 1](../specs/2026-10-14-kit-and-setup-design.md), sections 4, 6, 8, 10 and 11; the [hook spike](../../trials/2026-10-21-hook-spike.md), Codex CLI 0.163.0. The approved failure choice is exit 1, one stderr diagnostic and no stdout for internal errors, malformed events and known-Codex usage errors. Codex lets those calls through. The hook never exits 2; a recognized merge catches its own failures and denies. Exit 2 before devctl starts can still block; timeouts can let calls through.

**Constraints:** Tests first, offline simulations clearly labelled. Keep Claude Code and agy behavior. Change devctl templates, stage new templates, then sync managed copies and the lock. Preserve existing seeded files. Stay below 1,500 counted lines against `3a4fc85fa33328d05c7cb498b0eaf0ba31354bd1`. No heavy checks or publication in this Worker turn. No live hook-trust change.

## Tasks and exact files

- [x] Commit this plan and one Codex follow-up entry in `2026-10-14-kit-and-setup.md`.
- [x] Protocol, tests first: `rapid_ship/templates/common/tools/devctl/devctl/hook_protocols.py` and `hook.py`; `tests/devctl/test_devctl_hook_codex.py`, `test_devctl_hook_patch.py`, `test_devctl_hook_protocol.py`. Read Bash commands and all Add, Update, Delete and Move paths, including later operations, spaces, CRLF and lexical `..`. Reject malformed patches. Test every deny rule through the CLI, no decision, G5 absence, invalid settings and failure outputs.
- [x] Recover four events from original kept captures into `tests/devctl/fixtures/hooks/codex/{bash,bash-subagent,bash-headless,apply-patch}.json`. Append scrubbed blocks and source run/filename provenance to `docs/trials/2026-10-21-hook-spike.md`; preserve existing evidence. Fixtures equal blocks byte for byte. No recorded subagent patch exists.
- [x] Seed and doctor, tests first: `rapid_ship/templates/common/.codex/hooks.json`, `rapid_ship/templates/kit.toml`, both `rapid_ship/templates/{common,python}/.github/CODEOWNERS`, project-owned `.github/CODEOWNERS`; devctl templates `doctor_wiring.py`, `doctor.py`, `doctor_local.py`, `doctor_rules.py`. Validate tracked wiring, safe command, matcher coverage and synchronous timeout of at least 360 seconds (default 600). Probe only recognized commands; require exit 0 and G2 deny. Report missing versus unknown, and name `/hooks` trust and user-config limits.
- [x] Doctor and Kit tests: `tests/devctl/test_devctl_doctor_wiring_codex.py`, `test_devctl_doctor_settings.py`, `test_devctl_doctor_local_limits.py`, `test_devctl_doctor_github.py`, and `tests/test_kit_contents.py`. Include stand-in shim integration and linked-worktree command resolution.
- [x] Sync-only copies: `.codex/hooks.json`, `tools/devctl/devctl/{hook_protocols,hook,doctor_wiring,doctor,doctor_local,doctor_rules}.py`, `.rapid-ship/kit.lock`.
- [x] Current behavior and navigation: `.codex/AGENTS.md`, `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `rapid_ship/templates/AGENTS.md`, Spec 1. Correct only Codex-unwired claims in `2026-10-14-rapid-ship-design.md` and the guardrails line in `2026-10-16-metrics-and-gardening-design.md`; preserve Spec 3 status and unrelated text.
- [x] Verify focused new/affected pytest modules, Claude/agy hook and probe regressions, affected Kit contents tests, `./devctl check --tier fast`, `uv run rapid-ship status --strict`, and `./devctl doctor --settings`. Calculate the fixed-base diff with `devctl.check.diff.counted_lines`. Scan added text, commit messages and branch against the private identifier list without printing matches. Commit all changes; return clean status and evidence. The lead runs heavy checks and independent review afterward.

## Pending Owner steps

- [ ] After merge, Shawn reviews and trusts the exact new definition in Codex `/hooks`, with the project trusted. A changed hook requires another review. Doctor validates local wiring and a subprocess probe; it cannot establish persisted trust or user-level settings.
- [ ] After trust, Shawn runs a live guardrail trial in lead, subagent and headless Sessions, excluding G5, in a disposable repository with no live remote. Try `git commit -n -m trial` (G1), `git push --force` (G2), `git push origin HEAD:main` (G3), patch Add/Update/Delete/Move involving `.rapid-ship/kit.lock` (G4), `git push origin trial` with Agent identity on (G7), `gh pr create --fill` with Agent identity on (G8), and `gh pr merge 1` in Walk (merge denial). `git status` gets no hook decision; a Protected-file patch gets no G5 ask. Record version, tested commit, Session kind, event/tool, decision/reason, whether the tool ran, current worktree and trust review. Do not run a denied operation by another route.

After merge and Shawn's trust, Codex Sessions in rapid-ship checkouts, Feature leads included, run devctl hook. This implementation's Sessions are not claimed to have run under that hook. The recovered events are historical evidence; offline tests and doctor's subprocess probe do not complete the live trial.


## Verification, 2026-10-28

The first command, `./devctl doctor --settings`, passed with 4 ok, 0 missing, 0 unknown. HEAD matched the fixed review base and the worktree was clean.

Failing-first evidence:

- `uv run pytest -q tests/devctl/test_devctl_hook_codex.py`: 33 failed, 1 passed before Codex dispatch existed.
- `uv run pytest -q tests/devctl/test_devctl_hook_patch.py`: 29 failed before Codex patch parsing existed.
- `uv run pytest -q --tb=short tests/devctl/test_devctl_doctor_wiring_codex.py tests/devctl/test_devctl_doctor_settings.py tests/test_kit_contents.py`: two collection errors for the missing Codex doctor entry points.
- The first doctor/Kit regression run after implementation: 6 failed, 352 passed. Existing expectations needed the new doctor item and Protected path; the checks were preserved.
- `uv run pytest -q --tb=short tests/devctl/test_devctl_doctor_wiring_codex.py -k invalid_handlers`: 1 failed, 25 passed before rejecting an infinite timeout. Codex now rejects non-finite timeouts without changing agy’s validation.
- Fast-tier failures identified formatting, long lines and excessive patch-parser complexity. Small parsing helpers resolved these without suppressions.

The focused regression command passed **763 tests**:

```sh
uv run pytest -q --tb=short \
  tests/devctl/test_devctl_hook_codex.py \
  tests/devctl/test_devctl_hook_patch.py \
  tests/devctl/test_devctl_hook_protocol.py \
  tests/devctl/test_devctl_hook_agy.py \
  tests/devctl/test_devctl_hook_rules.py \
  tests/devctl/test_devctl_merge_guard.py \
  tests/devctl/test_devctl_doctor_wiring_codex.py \
  tests/devctl/test_devctl_doctor_wiring.py \
  tests/devctl/test_devctl_doctor_wiring_agy.py \
  tests/devctl/test_devctl_doctor_settings.py \
  tests/devctl/test_devctl_doctor_local_limits.py \
  tests/devctl/test_devctl_doctor_github.py \
  tests/test_kit_contents.py
```

`uv run pytest -q --tb=short tests/test_kit_contents.py -k codex` also passed: 10 passed, 36 deselected. Both stacks create the seed during init and sync and preserve existing project-owned definitions.

`./devctl check --tier fast` passed format, lint, map, exceptions, file-size, kit and vendored. `uv run rapid-ship status --strict` passed with 45 managed files unchanged. The real `./devctl doctor --settings` passed with 5 ok, 0 missing, 0 unknown, and 26 Protected paths. Its agy subprocess probe passed here; this does not verify agy execution under T3 Sessions or resolve PRO-172.

`devctl.check.diff.counted_lines` reports **1,034** lines against the fixed review base. The added diff lines, commit messages and branch name had no matches against the private identifier expressions. The original spike record remains an exact prefix of the updated record; all four recovered fixtures equal the appended blocks.

All tests above are offline. Doctor runs subprocess probes, not Codex Sessions. No owner trust or live guardrail trial was performed. No full check, full pytest suite, devctl-wide suite or documentation build ran. Heavy checks and independent review belong to the lead. Removed tests: none; the existing unknown-Harness parameter now uses `unwired`, because `codex` is supported.
