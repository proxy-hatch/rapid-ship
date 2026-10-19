# rapid-orchestrator: dropped

**Status: dropped.** [ADR 0004](../../adr/0004-team-management-boundary.md) says that rapid-ship never orchestrates: the owner's Harness starts, watches and resumes agent Sessions. Nothing here is planned, and nothing here describes current behaviour.

## What it was meant to be

rapid-orchestrator was to be a separate project that starts, resumes and cancels agent Sessions for every project on one machine, each in a Linux container, under caps per project, per Provider and per machine. rapid-ship would have driven it through its CLI, and it would have committed each Session's work itself.

## What the evidence showed

- **Sign-in trial, 2026-10-13.** One subscription sign-in per Provider served several Docker containers at once for Claude Code, Codex CLI and agy on one Mac, and the host's own sign-ins kept working. Claude Code took a `claude setup-token` token passed by variable name, the Codex containers shared one live `auth.json`, and agy needed only its token file. The trial lasted about an hour, so no token refresh was observed, and 5 of 18 agy turns failed at Google's eligibility check with HTTP 502 or 503.
- **Landscape survey, 2026-10-13.** Desk research over more than forty projects, fourteen of them read at source level, found none to adopt or fork as rapid-orchestrator. The closest ran interactive terminal sessions, let the agent commit and push, or preferred API keys. Several held pieces worth copying, such as Scion's agy container setup and the admission and reconciliation rules of OpenAI's Symphony.
- **Flight without an orchestrator, 2026-10-13.** Four desk-research reads concluded that Flight driven by a prompt alone is unsound: a hosted Worker can act as the owner, and a pull request can edit the CI that judges it. Eight small deterministic pieces would make it sound, as GitHub settings, Actions workflows and stateless devctl commands, with no daemon or state store. Nothing was run, and ADR 0004 later rejected pieces 1, 2 and 5, Flight's credential safeguards.

## Where the full records live

- The controller-era documents and the 2026-10-11 runtime trials are at the tag [`archive/controller-2026-10`](https://github.com/proxy-hatch/rapid-ship/tree/archive/controller-2026-10/docs).
- These records were deleted after commit `401b57d` and stay readable there:
  - [ADR 0003](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/adr/0003-walk-on-bare-sessions-orchestrator-deferred.md), which deferred rapid-orchestrator and was withdrawn before merge;
  - the [sign-in trial](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/trials/2026-10-13-login-carry.md), and its [Dockerfiles and check scripts](https://github.com/proxy-hatch/rapid-ship/tree/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/archive/orchestrator/login-carry-spike);
  - the [landscape survey](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/trials/2026-10-13-orchestrator-landscape.md);
  - the [Flight research note](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/trials/2026-10-13-flight-without-orchestrator.md);
  - the [earlier version of this note](https://github.com/proxy-hatch/rapid-ship/blob/401b57ddfba495efebb6fbbc647293bbc4cf2542/docs/archive/orchestrator/README.md), with the three Harnesses' headless contracts and the sources a builder would have copied from.
