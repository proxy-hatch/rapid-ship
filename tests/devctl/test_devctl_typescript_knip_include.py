"""Integration test: needs network access, Node.js 24 and npm.

Installs knip 6.43.0 and TypeScript 6.0.3 in a scratch project."""

import json
from pathlib import Path

from devctl import process
from devctl.check.stacks.typescript import KNIP_INCLUDE


def test_which_knip_settings_the_include_option_overrides(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"private": True, "devDependencies": {"knip": "6.43.0", "typescript": "6.0.3"}})
    )
    installed = process.run_process(["npm", "install", "--no-audit", "--no-fund"], tmp_path, 600)
    assert installed.returncode == 0, installed.stderr
    (tmp_path / "src").mkdir()
    (tmp_path / "src/index.ts").write_text('import { a } from "./used.ts"; console.log(a);\n')
    settings: list[dict[str, object]] = [
        {},
        {"rules": {"exports": "off"}},
        {"rules": {"exports": "warn"}},
        {"include": ["files"]},
        {"exclude": ["exports"]},
        {"ignoreExportsUsedInFile": True},
    ]
    hidden: set[str] = set()
    observations = []
    for setting in settings:
        (tmp_path / "src/used.ts").write_text(
            "export const a = 1; export const unused = 2; console.log(unused);\n"
        )
        (tmp_path / "knip.jsonc").write_text(
            json.dumps({"entry": ["src/index.ts"], "project": ["src/**/*.ts"], **setting})
        )
        result = process.run_process(
            [str(tmp_path / "node_modules/.bin/knip"), "--include", KNIP_INCLUDE], tmp_path, 120
        )
        assert result.returncode in (0, 1), result.stderr
        observations.append((setting, result.returncode, result.stdout))
        if not setting:
            assert result.returncode == 1
            assert "unused" in result.stdout
        elif result.returncode == 0:
            hidden.update(setting)
    (tmp_path / "observations.json").write_text(json.dumps(observations, indent=2))
    from devctl.doctor_typescript import KNIP_FLOOR_KEYS

    assert hidden == set(KNIP_FLOOR_KEYS), observations
