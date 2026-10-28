# Trial evidence

This directory records observations and reproduction artifacts, including unsuccessful probes.
The controller-era runtime trials and their frozen bundles are at the tag `archive/controller-2026-10`, starting from the [runtime comparison](https://github.com/proxy-hatch/rapid-ship/blob/archive/controller-2026-10/docs/trials/2026-10-11-runtime-comparison.md).
[2026-10-21-agent-identity.md](2026-10-21-agent-identity.md) records plan 4's live trial of Agent identity, the ruleset and doctor, which led to the ruleset's approval settings.
[2026-10-23-harness-guardrails.md](2026-10-23-harness-guardrails.md) records plan 5's live trial of `devctl hook` and the merge guard in headless Claude Code Sessions, in which every rule gave its expected decision and message.
[2026-10-26-organisation-trial.md](2026-10-26-organisation-trial.md) records plan 4's organisation trial: an admin's `rapid-ship app` on an organisation, `--import-key` and doctor with a team as the code owner, without the App-manager half.

[2026-10-28-agy-hook-outside-repository.md](2026-10-28-agy-hook-outside-repository.md) records the offline launch failure outside Git and the pending T3 runtime capture.

Record the tested versions, conditions, commands, results, and limits for each trial.
Identify deterministic simulations, live provider calls, and later reruns separately.
Preserve the relationship between each report, its saved artifacts, and the revision actually tested.
When replacing an artifact, update its recorded checksum and explain which observations the replacement reproduces.
Check bundles for credentials and private paths before publication; the website publishes these reports.
A spike record keeps its scrubbed event JSON in fenced blocks, and tests copy them as fixtures.
Passing unit tests or one successful probe does not qualify a project for Flight.
