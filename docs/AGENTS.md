# Documentation

Use this directory for user-facing guides and development records.

- [getting-started.md](getting-started.md) is the one controller-era guide left at this level. It describes the controller removed on 2026-10-14 and starts with a "Historical" line. Do not extend it; the documentation site is rewritten once the product works. The tag `archive/controller-2026-10` keeps the other controller-era guides. [credits.md](credits.md) and [branding.md](branding.md) are current pages; update them as needed.
- Put approved specifications and implementation plans in [superpowers](superpowers/AGENTS.md).
- Put observed experiments, failures, limitations, and reproduction evidence in [trials](trials/AGENTS.md).
- Put one decision per file in `adr/`, numbered in order, when it is hard to reverse, surprising without context, and the result of a real trade-off. So far: [0001 this repository's subscription sign-ins](adr/0001-subscription-logins-only.md), [0002 GitHub gates merges; Agent identity is optional](adr/0002-github-gates-merges-reviews-run-locally.md) and [0004 the team-management boundary](adr/0004-team-management-boundary.md). 0003, which deferred rapid-orchestrator, was withdrawn before merge; the [orchestrator note](archive/orchestrator/README.md) links its text.
- Records of dropped work live in [archive](archive/AGENTS.md). They do not describe current behaviour.
- Consult [ARCHITECTURE.md](../ARCHITECTURE.md) for current implementation boundaries and [GLOSSARY.md](../GLOSSARY.md) for shared terms.

Keep implemented behavior, selected future work, and experimental observations distinct.
Update the relevant guide when changing user-visible commands or setup behavior.
The [website](../website/AGENTS.md) builds these Markdown files directly; keep relative links valid for both repository readers and the site.
Add public navigation entries in [sidebars.js](../website/sidebars.js) when a new guide belongs in the sidebar.
Maintainer `AGENTS.md` files are excluded from publication; public pages should link to public documents.
