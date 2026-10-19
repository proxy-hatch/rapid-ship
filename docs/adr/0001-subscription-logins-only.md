---
status: accepted
---

# This repository's agents use subscription sign-ins only

*This ADR records this repository's own rule, not product behaviour.* rapid-ship the product states no sign-in rule; the last considered option below says why.

Agents that work on this repository sign in with each Provider's subscription, through the vendor's own unmodified Harness and sign-in flow, once per Provider. They use no API key. No model gateway or proxy sits between a Harness and its Provider, such as LiteLLM, OmniRoute or a proxy that rewrites credentials. This repository's root AGENTS.md states the rule.

The rule has two reasons:

1. The subscriptions' quotas pay for this repository's agent work, and API billing would give them up.
2. Providers have suspended accounts for using a third-party client or gateway that presents a subscription sign-in.

## Considered options

- **API keys for this repository's unattended work.** Rejected: they give up the subscription quotas, which are the first reason for the rule.
- **A credential proxy that keeps tokens outside the sandbox** (Docker Sandboxes, AstraBox with LiteLLM). Rejected: it terminates TLS and rewrites the authorization header on Provider traffic, which is the intermediary that the second reason excludes.
- **Subscription sign-ins as a rule of rapid-ship the product.** Rejected on 2026-10-16. Which Provider a Harness uses is each owner's choice, and rapid-ship starts no Session, so it could not enforce the rule ([ADR 0004](0004-team-management-boundary.md)). The product works with a subscription, an API key or a gateway, such as pi running a GLM model through OpenRouter. Nothing it ships needs an API key, and its CI needs no model sign-in.

## Consequences

- Tools that accept only API keys are unavailable to this repository, including OpenAI's Codex GitHub Action.
- When this repository's Lead runs `claude -p` from another Harness's shell, it never passes `--bare`: bare mode skips the subscription sign-in and needs an API key.
- Google's consumer terms say that wrapping `agy` inside third-party applications is not supported. For this repository, the owner accepted that risk on 2026-10-13, and again on 2026-10-15 when agy ran from inside a Codex CLI session. The acceptance covers `devctl doctor`'s agy probes and Roster routes that run `agy -p` from another Harness's shell. Other owners make their own choice: `rs-lead` warns them about these terms, in the form recorded here, when it offers such a route.
- Backlog item PRO-107, API billing support, is closed as unneeded, because the product already works with any Provider.
