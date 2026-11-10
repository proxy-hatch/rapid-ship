# Corrections ledger

A Correction is a change a human, a Reviewer or an incident required of an agent's work. Record a review request the agent acted on, an owner Correction in a Session, or an incident report that names an agent PR or commit as its cause. Questions, suggestions not taken and comments marked optional do not count.

Use one Markdown file per Correction: `<date>-<category>-<n>.md`, with the lowest free `n` from 1 on your branch. If two PRs pick the same name, rename the second file when resolving the merge conflict. Start each entry with YAML front matter between `---` lines; put the explanation in the body.

| Field | Required | Meaning |
| --- | --- | --- |
| `date` | yes | The day the Correction was made, UTC |
| `by` | yes | `reviewer` for a review or comment the Reviewer App posted; `human` for a person's review or comment, or for a Correction the owner gave in a Session; `incident` for an incident record. Without Agent identity, an agent's review comes from a person's account, so it is `human` |
| `source` | yes | The URL of the review, thread, comment or incident record, or `session` for a Correction the owner gave in a Session |
| `pr` | no | The PR whose work was corrected |
| `path` | no | The file the Correction is about |
| `category` | yes | A short kebab-case name shared by repeats of the same mistake |
| `rungs` | yes | One or more distinct rungs from 1 to 4 that would have prevented it. A Correction that needs a safe interface and a check names both |
| `prevention` | yes | One sentence naming the mechanism that would prevent a repeat |
| `status` | yes | One of the statuses below |
| `task` | when `proposed` | The URL of the proposed task in the owner's tracker |
| `prevented_by` | when `implemented` | References that resolve, or repository paths that exist, for the mechanism that now prevents it |
| `reason` | when `rejected` or `closed` | Why the owner chose no prevention, or why none is needed any more |

| Status | Meaning | Who sets it |
| --- | --- | --- |
| `open` | Recorded; nothing decided yet | Whoever adds the entry |
| `proposed` | A task in the tracker proposes a prevention | `rs-garden`, on a new entry or, as a Protected change, on an existing one |
| `implemented` | A mechanism now prevents a repeat | The PR that lands the prevention, signed off by the owner |
| `rejected` | The owner chose no prevention, or judged it no Correction | The owner |
| `closed` | No prevention is needed any more, for example because the code was removed or the entry repeats another | The owner, or a PR the owner signs off |

The four rungs are safe interfaces (1), automated checks (2), judgement (3), and the owner (4). `date` accepts a YAML date or ISO date string without a time. `category` matches `[a-z0-9]+(?:-[a-z0-9]+)*`. `pr` is an integer of at least 1; booleans are not integers. `source` is `session` or starts with `https://`. `task`, `path`, `prevention` and `reason`, when present, are non-empty text. No other fields are allowed.

For `implemented`, each `prevented_by` item must resolve as an existing check reference or a repository path tracked by git. An untracked file on disk does not count. With several stacks, an ambiguous Python reference names the candidate stacks; use `test:<path>::<name>` or a directory-qualified check such as `check:lint (backend)`.

## Writing and approval

When the owner corrects you in a Session, add an `open` entry with `by: human` and `source: session` to the open PR the Correction concerns, or to your next PR when none is open. Gardening writes new `open` or `proposed` entries from review and incident URLs; skip a URL already recorded as a `source`. The PR landing a prevention sets `status: implemented` and `prevented_by`, leaving `source` unchanged. The owner may reject or close an entry.

Adding an entry of any status and updating `last-pass.toml` are unprotected. Editing, renaming or removing an existing entry, including a status change, needs the owner. Every change to this README is Protected through CODEOWNERS. Added entries are agent-reported and unchecked for completeness or sign-off; the format check cannot tell whether an agent missed a Correction.

## Gardening cursor

`last-pass.toml` has exactly `through`, a full 40-character hexadecimal SHA naming a commit in this repository, and `date`, the UTC date of the pass without a time. Gardening writes the default-branch commit its last pass covered. The format check reads the work tree.
