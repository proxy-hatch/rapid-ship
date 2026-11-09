# Shared audit

Run each item over the whole repository for a health audit. For a gardening pass, apply each item to files changed in the range and inspect their related settings, Patterns and references. Cite file:line or command output for every finding.

## Rung 1

Find recurring tasks done several ways; propose a Pattern, reference implementation and enforcing check. Find missing safe interfaces and the bypasses they would ban. Compare code with every existing Pattern, including starter Patterns for error handling, typed and validated configuration, and typed input validation. Cite each Pattern's Lessons in its finding.

Apply the base rule to changed code: fail fast and gracefully, and never hide or obscure an error. Find dropped or broad catches that continue, failures turned into defaults or success, retries or fallbacks hiding persistent failure, and messages losing causes or useful fixes.

## Rung 2

Find missing checks and test tiers, doctor gaps, each stack's floor items replaced by project rules, advisory Rules that a check could enforce, and missing non-stylistic tool rules. Find exceptions whose removal condition holds and settings entries matching nothing, including kit exclusions, unguided directories, unit-test patterns and CODEOWNERS paths. Include Setup entries marked for removal when code next changes.

## Rung 3

Find golden paths in `docs/golden-paths/` that no longer match merged code. At adoption, propose first golden paths for suitable merged examples. Find README.md, ARCHITECTURE.md and directory guide statements, commands, paths and links that no longer match code, and missing directory guides. Find dead code that checks cannot see: code reached only by tests, unimported modules, definitions kept alive by a same-name use or bare test reference, unreachable check steps, settings or branches, unused development dependencies, and dead code marked at Setup. A gardening pass may fix document-only drift; propose tasks for other findings.

## Rung 4 and reviews

Find gaps in the Protected set, CODEOWNERS and the ruleset. Across recent reviews, find repeated comments a rung could prevent; in a range inspect reviews of the relevant pull requests.

Do not repeat what `devctl check` already fails on: broken guide links, exception entries matching no suppression, unresolved Pattern references, and unused code or declared dependencies its checks detect.
