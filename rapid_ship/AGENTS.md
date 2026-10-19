# rapid_ship package

This root-level directory is the importable `rapid_ship` package behind the `rapid-ship` command. [pyproject.toml](../pyproject.toml) defines wheel selection and the `rapid-ship` entry point. The [plan index](../docs/superpowers/plans/2026-10-14-kit-and-setup.md) fixes the modules that later plans add here.

- [cli.py](cli.py) parses arguments and runs `init`, `status`, `sync` and `app`. It exits 1 on a `KitRefusal` and 2 on a `KitError`. `app` also runs outside a work tree; inside one, it passes on the Apps that `.rapid-ship/project.toml` records. [__main__.py](__main__.py) and the entry point call the same `main`.
- [github_app.py](github_app.py) runs `rapid-ship app`. For each role it uses the App that `.rapid-ship/project.toml` records for the repository. Otherwise it uses an App of the repository's owner whose key the Keychain holds, which `GET /apps/<slug>` with the owner's `gh` confirms, and otherwise it creates one. It reads everything before it changes anything. A recorded App with no key on this machine stops the command with exit 1 and names `rapid-ship app --import-key <role>`. A key kept under plan 4's item name, `rapid-ship/<role>-app`, is re-stored under the new name, and the old item stays. The command prints each App's ID, slug and install URL.
- [app_flow.py](app_flow.py) runs GitHub's manifest flow for one App. A server on `127.0.0.1` posts the manifest, takes GitHub's one-time code and exchanges it for the App and its key.
- [app_keychain.py](app_keychain.py) keeps each key in the macOS Keychain with `security`, from stdin, in an item named `rapid-ship/<role>-app/<App ID>`. It lists a role's items from `security dump-keychain` without `-d`, which prints attributes only. It also holds `AppSetupError` and the process runner (EX-11).

`rapid_ship` cannot import devctl, so `app_keychain.keychain_service` and `app_flow.APP_PERMISSIONS` repeat devctl's; a test in `tests/devctl/test_devctl_github_app.py` keeps them equal. An import-linter contract in `pyproject.toml` keeps the order of imports: `github_app`, then `app_flow`, then `app_keychain`.
- [kit](kit/AGENTS.md) holds the Kit commands: templates, lock, `init`, `status`, `sync` and their git calls.
- [templates](templates/AGENTS.md) holds the Kit's files: the template tree and `kit.toml`. The wheel ships it, and this repository vendors it.
- [files.py](files.py) writes files for the Kit. `atomic_replace` replaces a file atomically, `create_file` creates one and never overwrites it, and `safe_path` and `relative_parts` refuse a path that leaves the repository or passes through a symlink. Writers validate the path with `safe_path`, create the parent directory and own serialization.
- [skills](skills/AGENTS.md) holds the engineering skill used while working on this repository.

Import modules directly; `__init__.py` is a marker, not an alternate interface. Keep resources under this package: `importlib.resources.files("rapid_ship")` is the lookup root in an installed wheel. After packaging changes, run the root checks and the [distribution smoke](../scripts/AGENTS.md).
