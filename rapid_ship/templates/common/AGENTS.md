# {{project_name}}

{{project_name}} is this repository's product. Replace this paragraph with one that says what it does and who uses it.

## Commands

- Run `./devctl doctor --settings` first in each Session, unless the Session runs the full `./devctl doctor`; it checks the settings files and asks GitHub nothing.
- `./devctl check` runs every check CI requires. Add `--tier fast` for the quick subset.
- `./devctl doctor` reports missing tools, settings and GitHub configuration.
- `./devctl --help` lists the project's own verbs.

## Find the change

| Work | Start here |
| --- | --- |
| What the project does, and how to run and check it | [README](README.md) |
| The system's parts and how data moves between them | [Architecture](ARCHITECTURE.md) |
| What a feature does, where it starts and how to reproduce it | [Feature map](docs/features/README.md) |
| The one supported way to do a recurring task | [Patterns](docs/patterns/README.md) |
| Where feature and Pattern files live | [Documentation](docs/AGENTS.md) |
| This project's devctl verbs and check steps | [Tools](tools/AGENTS.md) |

Add a row for each directory guide.

## Rules

- Keep each change inside the scope you were asked to change. advisory
- Prefer clear names, types, and simple control flow. advisory
- Add comments only when they convey a contract, rationale, invariant, or external constraint that the code does not adequately express. advisory
- Delete commented-out code. advisory
- Keep local explanations beside the relevant code and broader design reasoning in linked documentation. advisory
- Do not cite the document, plan or decision behind the code in a comment; documentation points to code, not the reverse. advisory
- A comment does not make a workaround acceptable. Fix the root cause within scope, or explicitly report the limitation. advisory
- A necessary workaround must have a verified reason, appropriate validation, and a tracked removal condition when temporary. advisory
- Give each TODO its author and the issue that tracks it. advisory
- Mark every suppression with `rs-exception: EX-<n>` and list it in `.rapid-ship/exceptions.toml`, with its reason and removal condition. enforced by: check:exceptions
- Do not invent explanations, weaken tests, or suppress correctness checks to make a change appear complete. advisory
- Declare each removed test under `Removed tests:` in the PR body, with a reason. enforced by: check:diff
- Update comments with behaviour changes, and investigate existing constraint comments before removing them. advisory
- Do not introduce unnecessary abstractions or broaden a refactor just to eliminate a useful comment. advisory
- Editing or deleting a Kit-managed file (`kind = "managed"` in `.rapid-ship/kit.lock`) makes it this project's own and stops its Kit updates. To change behaviour and keep updates, use `tools/devctl/devctl_project/` or the settings in `.rapid-ship/`. To own a Kit file outright, list it under `[kit] exclude`. To give one back to the Kit, run `rapid-ship sync --revert <path>`. advisory

## Pull requests

- Run `./devctl check` and fix what it reports before you open a pull request.
- With Agent identity on, push with `./devctl as worker push` and open the pull request with `./devctl as worker gh pr create`.
- Review a change from a Session that did not write it. With Agent identity on, approve with `./devctl as reviewer gh pr review <number> --approve`, or request changes with `./devctl as reviewer gh pr review <number> --request-changes --body <findings>`. Never approve a change you wrote.
- Merge with `gh pr merge <number> --squash --match-head-commit <sha>`; the merge guard checks the pull request first. In Walk, the owner merges every pull request.
- Declare `Over the diff cap:` in the pull request body only after the owner accepted the overage.
- Undo a merged change only with `git revert`.

## Shared language and decisions

- Terms are in `GLOSSARY.md`, and decisions in `docs/adr/`.
- Follow the `rs-writing` skill for prose and the `rs-ponytail` skill for building only what is needed.
