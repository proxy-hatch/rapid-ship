# rapid_ship package

This root-level directory is the importable `rapid_ship` package behind the `rapid-ship` command. [pyproject.toml](../pyproject.toml) defines wheel selection and the `rapid-ship` entry point. The [plan index](../docs/superpowers/plans/2026-10-14-kit-and-setup.md) fixes the modules that later plans add here.

- [cli.py](cli.py) parses arguments and runs `init`, `status`, `sync` and `app`. It exits 1 on a `KitRefusal` and 2 on a `KitError`. `app` reads no Kit file, so it runs outside a work tree. [__main__.py](__main__.py) and the entry point call the same `main`.
- [github_app.py](github_app.py) runs `rapid-ship app`. GitHub's manifest flow, through a server on `127.0.0.1`, creates the Worker App and the Reviewer App on the owner's account. `security` stores each key in the macOS Keychain from stdin, and the command prints each App's ID, slug and install URL. `rapid_ship` cannot import devctl, so this module has its own process runner (EX-11) and repeats devctl's Keychain services and App permissions; a test in `tests/devctl/test_devctl_github_app.py` keeps them equal.
- [kit](kit/AGENTS.md) holds the Kit commands: templates, lock, `init`, `status`, `sync` and their git calls.
- [templates](templates/AGENTS.md) holds the Kit's files: the template tree and `kit.toml`. The wheel ships it, and this repository vendors it.
- [files.py](files.py) writes files for the Kit. `atomic_replace` replaces a file atomically, `create_file` creates one and never overwrites it, and `safe_path` and `relative_parts` refuse a path that leaves the repository or passes through a symlink. Writers validate the path with `safe_path`, create the parent directory and own serialization.
- [skills](skills/AGENTS.md) holds the engineering skill used while working on this repository.

Import modules directly; `__init__.py` is a marker, not an alternate interface. Keep resources under this package: `importlib.resources.files("rapid_ship")` is the lookup root in an installed wheel. After packaging changes, run the root checks and the [distribution smoke](../scripts/AGENTS.md).
