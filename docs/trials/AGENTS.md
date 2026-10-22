# Trial evidence

This directory records observations and reproduction artifacts, including unsuccessful probes.
The controller-era runtime trials and their frozen bundles are at the tag `archive/controller-2026-10`, starting from the [runtime comparison](https://github.com/proxy-hatch/rapid-ship/blob/archive/controller-2026-10/docs/trials/2026-10-11-runtime-comparison.md).
[2026-10-21-agent-identity.md](2026-10-21-agent-identity.md) records plan 4's live trial of Agent identity, the ruleset and doctor, which led to the ruleset's approval settings.

Record the tested versions, conditions, commands, results, and limits for each trial.
Identify deterministic simulations, live provider calls, and later reruns separately.
Preserve the relationship between each report, its saved artifacts, and the revision actually tested.
When replacing an artifact, update its recorded checksum and explain which observations the replacement reproduces.
Check bundles for credentials and private paths before publication; the website publishes these reports.
Passing unit tests or one successful probe does not qualify a project for Flight.
