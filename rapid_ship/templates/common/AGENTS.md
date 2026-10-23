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

- Mark every suppression with `rs-exception: EX-<n>` and list it in `.rapid-ship/exceptions.toml`. enforced by: check:exceptions
- Declare each removed test under `Removed tests:` in the PR body, with a reason. enforced by: check:diff
- Keep each change inside its task's paths. advisory
- Editing or deleting a Kit-managed file (`kind = "managed"` in `.rapid-ship/kit.lock`) makes it this project's own and stops its Kit updates. To change behaviour and keep updates, use `tools/devctl/devctl_project/` or the settings in `.rapid-ship/`. To own a Kit file outright, list it under `[kit] exclude`. To give one back to the Kit, run `rapid-ship sync --revert <path>`. advisory

## Shared language and decisions

- Terms are in `GLOSSARY.md`, and decisions in `docs/adr/`.
- Follow the `rs-writing` skill for prose and the `rs-ponytail` skill for building only what is needed.
