# Agent identity

| Setup | Agent identity | Why |
| --- | --- | --- |
| Solo owner, public repository or a paid plan | Recommended | It is the only way the owner can approve an agent's PR, because GitHub never lets a PR's author approve it, and GitHub then holds agents to CODEOWNERS |
| Solo owner, private repository on GitHub Free | Recommended, for real reviews and metrics | Reviews posted as the Reviewer App become GitHub reviews that the merge guard counts, and agent PRs become countable. There is no ruleset, so the merge guard holds the bar with or without it |
| Team | Optional | Teammates approve agent PRs anyway. The Apps add per-agent metrics, real reviews from the Reviewer App, and agents that CODEOWNERS binds in Flight |

Agent identity lets the owner approve an agent PR; makes Reviewer App reviews real GitHub reviews that the merge guard can count; distinguishes agent PRs for metrics; and binds agents to CODEOWNERS in Flight. It costs two Apps, private keys in macOS Keychain and GitHub writes through `devctl as`.

Without it, agents act as the owner and Walk rests on the merge guard and guardrails. The owner cannot approve a PR their account opened, agent reviews are comments, and per-agent PR metrics report `unknown: needs Agent identity`. In Flight, code-owner review remains required. An agent may merge an unprotected PR when the guard allows it; the guard denies Protected-set merges. A solo owner merges their own Protected PR through GitHub's admin bypass in the web interface; guardrails deny agents an admin merge. The guard cannot require a review from the owner's own account; the root guide and owner instructions carry that requirement.

Each repository owner has one Worker App and one Reviewer App. An organisation admin creates both once. Each developer has a separate private key for each App, stored in their own Keychain; GitHub allows up to 25 keys per App. An organisation admin generates each key and hands it over securely. The developer imports it with `rapid-ship app --import-key` and deletes the downloaded file. For Apps owned by a personal account, the account owner generates keys for collaborators or moves the Apps to an organisation. Separate Apps per developer multiply installations and split reviews.
