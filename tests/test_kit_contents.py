"""Offline: the packaged Kit's templates and the files they render."""

import json
import re
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from devctl.codeowners import codeowners_match
from devctl.process import run_process
from devctl.settings import load_project
from rapid_ship.kit.init import init_repository
from rapid_ship.kit.sync import sync_repository
from rapid_ship.kit.templates import (
    STACKS,
    Stack,
    Template,
    load_manifest,
    packaged_templates,
    render_files,
)
from test_devctl_doctor_wiring import SEED as CLAUDE_WIRING
from test_devctl_doctor_wiring_agy import SEED as AGY_WIRING
from test_devctl_doctor_wiring_codex import SEED as CODEX_WIRING

VARIABLES = {
    "project_name": "demo-app",
    "package": "demo_app",
    "owner": "octo",
    "repository": "octo/demo-app",
}
CODE_OWNER_COMMENT = (
    "# The code owner that CODEOWNERS names, written as CODEOWNERS writes it: "
    '"@login" or "@organisation/team".'
)
SEEDED = {
    ".agents/hooks.json",
    ".claude/settings.json",
    ".codex/hooks.json",
    ".github/CODEOWNERS",
    ".rapid-ship/exceptions.toml",
    ".rapid-ship/project.toml",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CLAUDE.md",
    "README.md",
    "docs/AGENTS.md",
    "docs/features/README.md",
    "docs/patterns/README.md",
    "tools/AGENTS.md",
}


def rendered(stack: Stack = "python", **variables: str) -> dict[str, Template]:
    return {t.path: t for t in render_files(stack, {**VARIABLES, **variables}, ())}


def text(stack: Stack, path: str, **variables: str) -> str:
    return content(rendered(stack, **variables)[path]).decode()


def content(template: Template) -> bytes:
    assert template.content is not None, f"{template.path} is a symlink"
    return template.content


def test_every_manifest_path_exists_in_a_layer() -> None:
    manifest = load_manifest()
    root = packaged_templates()
    for path in manifest.seeded | manifest.new_project | manifest.executable:
        assert any((root / layer / path).is_file() for layer in ("common", *STACKS)), path


@pytest.mark.parametrize("stack", STACKS)
def test_every_stack_seeds_the_shared_files(stack: Stack) -> None:
    kinds = {path: t.kind for path, t in rendered(stack).items()}
    assert {path for path in SEEDED if kinds.get(path) == "seeded"} == SEEDED


@pytest.mark.parametrize("stack", STACKS)
def test_the_claude_code_wiring_seed_holds_only_the_pre_tool_hook(stack: Stack) -> None:
    # The seed's PreToolUse hook sets no timeout: the merge guard's 300-second budget relies on
    # Claude Code's default of 600 seconds.
    assert json.loads(text(stack, ".claude/settings.json")) == CLAUDE_WIRING


@pytest.mark.parametrize("stack", STACKS)
def test_the_agy_wiring_seed_holds_only_the_devctl_hook(stack: Stack) -> None:
    assert json.loads(text(stack, ".agents/hooks.json")) == AGY_WIRING


def test_python_new_project_seeds() -> None:
    kinds = {path: t.kind for path, t in rendered().items()}
    paths = (
        ".gitignore",
        "pyproject.toml",
        "src/AGENTS.md",
        "src/demo_app/__init__.py",
        "tests/AGENTS.md",
        "tests/test_import.py",
        *STARTER_PYTHON_FILES,
    )
    assert {kinds[p] for p in paths} == {"seeded"}
    assert text("python", ".gitignore") == "__pycache__/\n*.py[cod]\n.venv/\ndist/\n"


@pytest.mark.parametrize(("stack", "roots"), [("python", ["src/demo_app"]), ("agnostic", [])])
def test_project_settings_seed_has_the_kit_defaults(stack: Stack, roots: list[str]) -> None:
    settings = tomllib.loads(text(stack, ".rapid-ship/project.toml"))
    assert settings == {
        "stack": stack,
        "github": {
            "repository": "octo/demo-app",
            "code_owner": "@octo",
            "worker_app_id": 0,
            "worker_app_slug": "",
            "reviewer_app_id": 0,
            "reviewer_app_slug": "",
        },
        "escalation": {
            "every_pr": True,
            "kinds": [
                "a pull request that removes a behavioural test",
                "a pull request that declares Over the diff cap:",
            ],
            "revision_rounds": 3,
        },
        "kit": {"optional": [], "exclude": []},
        "map": {"source_roots": roots, "unguided": [], "exclude": []},
        "tests": {"unit": ["tests/unit/**"]},
    }
    assert "github" in tomllib.loads(text(stack, ".rapid-ship/project.toml", repository=""))
    assert (
        "repository"
        not in tomllib.loads(text(stack, ".rapid-ship/project.toml", repository=""))["github"]
    )


@pytest.mark.parametrize("stack", STACKS)
def test_without_an_owner_the_code_owner_seed_is_empty_not_a_placeholder(stack: Stack) -> None:
    lines = text(stack, ".rapid-ship/project.toml", owner="").splitlines()

    # devctl reads "" as unset; a placeholder there would fail every later devctl command.
    assert 'code_owner = ""' in lines
    assert not any("<owner>" in line or "<code_owner>" in line for line in lines)
    comment = lines.index('code_owner = ""') - 1
    assert lines[comment] == CODE_OWNER_COMMENT
    assert lines[comment - 1] == 'repository = "octo/demo-app"'


@pytest.mark.parametrize("stack", STACKS)
def test_the_settings_seed_names_no_roster_and_still_loads(stack: Stack, tmp_path: Path) -> None:
    seed = text(stack, ".rapid-ship/project.toml")

    # rapid-ship does not run agents across several Providers, so the seed names none.
    assert "roster" not in seed.lower()
    assert "Provider" not in seed
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship/project.toml").write_text(seed)
    assert load_project(tmp_path).stack == stack


def test_the_kit_no_longer_seeds_gate_toml() -> None:
    assert ".rapid-ship/gate.toml" not in rendered("python")
    assert ".rapid-ship/gate.toml" not in load_manifest().seeded


def test_exceptions_seed_lists_none() -> None:
    assert tomllib.loads(text("agnostic", ".rapid-ship/exceptions.toml")) == {}


def active(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() and not line.startswith("#")]


# devctl doctor requires these in Flight: PROTECTED_PATHS, plus PYTHON_PROTECTED_PATHS for Python.
PROTECTED = (
    "/.github/",
    "/.githooks/",
    "/devctl",
    "/tools/devctl/",
    "/.agents/",
    "/.claude/",
    "/.codex/",
    "/**/AGENTS.md",
    "/**/CLAUDE.md",
    "/.rapid-ship/",
    # A settings file can switch its check off, so the secrets and workflows tools' are listed.
    "/.gitleaks.toml",
    "/.gitleaksignore",
    "/zizmor.yml",
    "/zizmor.yaml",
)
# Every file the Python tools read their settings from. Ruff uses the nearest ruff.toml or
# .ruff.toml, so those match at any depth; mypy, pytest and import-linter read the root only.
PYTHON_PROTECTED = (
    "/pyproject.toml",
    "/**/ruff.toml",
    "/**/.ruff.toml",
    "/mypy.ini",
    "/.mypy.ini",
    "/pytest.ini",
    "/.pytest.ini",
    "/pytest.toml",
    "/.pytest.toml",
    "/setup.cfg",
    "/tox.ini",
    "/.importlinter",
)
# A new Python project's starter Patterns: CODEOWNERS lists each existing Pattern file.
STARTER_PATTERNS = tuple(
    f"/docs/patterns/python-{name}.md"
    for name in ("error-handling", "configuration", "input-validation", "performance")
)
PYTHON_SET = (*PROTECTED[:10], *STARTER_PATTERNS, *PROTECTED[10:], *PYTHON_PROTECTED)
# The new-project seeds that come with them: each Pattern's reference module and its tests.
STARTER_MODULES = ("errors", "inputs", "settings", "profiling")
STARTER_PYTHON_FILES = (
    *(path.removeprefix("/") for path in STARTER_PATTERNS),
    *(f"src/demo_app/{name}.py" for name in STARTER_MODULES),
    *(f"tests/test_{name}.py" for name in STARTER_MODULES),
)


@pytest.mark.parametrize(("stack", "expected"), [("python", PYTHON_SET), ("agnostic", PROTECTED)])
def test_codeowners_has_the_walk_line_and_the_stack_protected_set(
    stack: Stack, expected: tuple[str, ...]
) -> None:
    lines = text(stack, ".github/CODEOWNERS").splitlines()
    assert active(lines) == ["* @octo"]
    protected = [line for line in lines if re.fullmatch(r"# /\S+ @octo", line)]
    assert protected == [f"# {path} @octo" for path in expected]


@pytest.mark.parametrize("stack", STACKS)
def test_the_flight_set_protects_every_agent_instruction(stack: Stack) -> None:
    lines = text(stack, ".github/CODEOWNERS").splitlines()
    patterns = [line.split()[1] for line in lines if re.fullmatch(r"# /\S+ @octo", line)]
    instructions = (
        "AGENTS.md",
        "src/demo_app/AGENTS.md",
        "CLAUDE.md",
        "docs/CLAUDE.md",
        ".claude/settings.json",
        ".codex/hooks.json",
        ".claude/skills/rs-tdd",
        ".agents/hooks.json",
        ".agents/skills/rs-tdd/SKILL.md",
    )
    for path in instructions:
        assert any(codeowners_match(pattern, path) for pattern in patterns), path
    assert not any(codeowners_match(pattern, "src/demo_app/app.py") for pattern in patterns)


def test_the_python_codeowners_only_adds_the_python_settings() -> None:
    python = text("python", ".github/CODEOWNERS").splitlines()
    agnostic = text("agnostic", ".github/CODEOWNERS").splitlines()
    split = agnostic.index("# /.rapid-ship/ @octo") + 1
    patterns = [f"# {path} @octo" for path in STARTER_PATTERNS]
    added = [f"# {path} @octo" for path in PYTHON_PROTECTED]
    assert python == [*agnostic[:split], *patterns, *agnostic[split:], *added]


@pytest.mark.parametrize("stack", ["python", "agnostic"])
def test_codeowners_has_no_placeholder_for_harness_settings(stack: Stack) -> None:
    assert "Harness settings" not in text(stack, ".github/CODEOWNERS")


def test_codeowners_without_an_owner_leaves_the_owner_to_rs_setup() -> None:
    lines = text("agnostic", ".github/CODEOWNERS", owner="").splitlines()
    assert active(lines) == []
    assert "# * @<owner>" in lines
    assert "# /devctl @<owner>" in lines


def test_python_seed_has_the_guardrail_settings() -> None:
    data = tomllib.loads(text("python", "pyproject.toml"))
    lint = data["tool"]["ruff"]["lint"]
    assert set(lint["select"]) == {
        "E",
        "W",
        "F",
        "I",
        "B",
        "UP",
        "SIM",
        "C4",
        "RUF",
        "PGH",
        "ERA",
        "T20",
        "S",
        "TID",
        "PT",
        "PTH",
        "DTZ",
        "C90",
        "TD",
        "BLE",
        "ANN401",
    }
    assert lint["external"] == ["V"]
    assert lint["mccabe"]["max-complexity"] == 10
    tidy = lint["flake8-tidy-imports"]
    assert tidy["ban-relative-imports"] == "all"
    # The configuration Pattern's bans; its settings module is the one file exempt from them.
    assert set(tidy["banned-api"]) == {"os.environ", "os.getenv"}
    for entry in tidy["banned-api"].values():
        assert "docs/patterns/python-configuration.md" in entry["msg"]
    assert lint["per-file-ignores"] == {
        "tests/**": ["S101"],
        "src/demo_app/settings.py": ["TID251"],
    }
    assert data["tool"]["ruff"]["extend-exclude"] == ["tools/devctl"]
    mypy = data["tool"]["mypy"]
    assert mypy["strict"] is True
    assert mypy["warn_unreachable"] is True
    assert set(mypy["enable_error_code"]) == {
        "ignore-without-code",
        "redundant-expr",
        "truthy-bool",
    }
    assert mypy["files"] == ["src", "tests"]
    pytest_options = data["tool"]["pytest"]["ini_options"]
    assert pytest_options["addopts"] == ["--strict-markers", "--strict-config"]
    assert pytest_options["xfail_strict"] is True
    assert pytest_options["filterwarnings"] == ["error"]
    assert [c["type"] for c in data["tool"]["importlinter"]["contracts"]] == ["layers", "forbidden"]
    names = {re.split(r"[<>=]", requirement)[0] for requirement in data["dependency-groups"]["dev"]}
    assert names == {"deptry", "import-linter", "mypy", "pytest", "ruff", "vulture"}
    assert data["tool"]["vulture"] == {"paths": ["src", "tests"]}
    assert data["tool"]["deptry"] == {
        "extend_exclude": ["tools/devctl"],
        "known_first_party": ["demo_app"],
    }
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/demo_app"]


def test_python_seeds_are_valid_python() -> None:
    modules = [path for path in STARTER_PYTHON_FILES if path.endswith(".py")]
    for path in ("src/demo_app/__init__.py", "tests/test_import.py", *modules):
        compile(text("python", path), path, "exec")
    assert 'importlib.import_module("demo_app")' in text("python", "tests/test_import.py")


ROOT_GUIDE_LINKS = [
    "README.md",
    "ARCHITECTURE.md",
    "docs/features/README.md",
    "docs/patterns/README.md",
    "docs/AGENTS.md",
    "tools/AGENTS.md",
]
SETTINGS_FIRST = (
    "- Run `./devctl doctor --settings` first in each Session, unless the Session runs the full "
    "`./devctl doctor`; it checks the settings files and asks GitHub nothing."
)
# The root guide's Rules on comments, workarounds, suppressions and removed tests, in order.
COMMENT_RULES = (
    "Prefer clear names, types, and simple control flow.",
    "Add comments only when they convey a contract, rationale, invariant, or external constraint "
    "that the code does not adequately express.",
    "Delete commented-out code.",
    "Keep local explanations beside the relevant code and broader design reasoning in linked "
    "documentation.",
    "Do not cite the document, plan or decision behind the code in a comment; documentation points "
    "to code, not the reverse.",
    "A comment does not make a workaround acceptable. Fix the root cause within scope, or "
    "explicitly report the limitation.",
    "A necessary workaround must have a verified reason, appropriate validation, and a tracked "
    "removal condition when temporary.",
    "Give each TODO its author and the issue that tracks it.",
    "Mark every suppression with `rs-exception: EX-<n>` and list it in "
    "`.rapid-ship/exceptions.toml`, with its reason and removal condition.",
    "Do not invent explanations, weaken tests, or suppress correctness checks to make a change "
    "appear complete.",
    "Declare each removed test under `Removed tests:` in the PR body, with a reason.",
    "Update comments with behaviour changes, and investigate existing constraint comments before "
    "removing them.",
    "Do not introduce unnecessary abstractions or broaden a refactor just to eliminate a useful "
    "comment.",
)
POINTERS = (
    "`GLOSSARY.md`",
    "`docs/adr/`",
    "`rs-writing`",
    "`rs-ponytail`",
    "`./devctl check`",
    "`./devctl doctor`",
    "`./devctl doctor --settings`",
)


@pytest.mark.parametrize(
    ("stack", "links"),
    [
        ("agnostic", ROOT_GUIDE_LINKS),
        ("python", [*ROOT_GUIDE_LINKS, "src/AGENTS.md", "tests/AGENTS.md"]),
    ],
)
def test_root_guide_skeleton_has_its_headings_rules_links_and_pointers(
    stack: Stack, links: list[str]
) -> None:
    guide = text(stack, "AGENTS.md")
    headings = re.findall(r"^#+ .*$", guide, flags=re.MULTILINE)
    assert headings == [
        "# demo-app",
        "## Commands",
        "## Find the change",
        "## Rules",
        "## Shared language and decisions",
    ]
    rules = guide.split("## Rules")[1].split("##")[0]
    bullets = [line for line in rules.splitlines() if line.startswith("- ")]
    assert bullets
    assert all(re.search(r"(enforced by: \S+|advisory)$", line) for line in bullets)
    statements = [re.sub(r" (enforced by: \S+|advisory)$", "", line[2:]) for line in bullets]
    assert [s for s in statements if s in COMMENT_RULES] == list(COMMENT_RULES)
    # The guide says how a Kit file becomes the project's own, how to keep updates instead,
    # and how to give a file back.
    owned = next(line for line in bullets if "Kit-managed file" in line)
    for words in (
        "makes it this project's own and stops its Kit updates",
        "`tools/devctl/devctl_project/`",
        "`[kit] exclude`",
        "To give one back to the Kit, run `rapid-ship sync --revert <path>`.",
    ):
        assert words in owned
    assert re.findall(r"\]\(([^)]+)\)", guide) == links
    assert all(pointer in guide for pointer in POINTERS)
    commands = guide.split("## Commands")[1].split("##")[0]
    assert commands.strip().splitlines()[0] == SETTINGS_FIRST


def test_the_python_root_guide_adds_its_rows_and_rules() -> None:
    python = text("python", "AGENTS.md").splitlines()
    (dead_code,) = [line for line in python if "`dead-code` false positive" in line]
    python.remove(dead_code)
    # The dead-code Rule names the forms that devctl reads, and those that only review catches.
    for words in ("noqa: V<code>", "deptry: ignore[<code>]", "`ignore_names`", "whitelist"):
        assert words in dead_code
    rows = [line for line in python if "](src/AGENTS.md)" in line or "](tests/AGENTS.md)" in line]
    lint = [
        line.removeprefix("- ").removesuffix(" enforced by: check:lint")
        for line in python
        if line.endswith(" enforced by: check:lint")
    ]

    assert len(rows) == 2
    # Ruff's ERA001, TD002 and TD003 carry these two Rules, and no other.
    assert lint == [
        "Delete commented-out code.",
        "Give each TODO its author and the issue that tracks it.",
    ]
    # The agnostic stack has no lint step, so its guide marks the same two Rules advisory.
    agnostic = [
        line.replace(" enforced by: check:lint", " advisory") for line in python if line not in rows
    ]
    assert agnostic == text("agnostic", "AGENTS.md").splitlines()


def test_the_readme_and_architecture_seeds_render_their_skeleton() -> None:
    readme = text("agnostic", "README.md")
    assert "./devctl check" in readme
    assert "](AGENTS.md)" in readme
    architecture = text("agnostic", "ARCHITECTURE.md")
    assert "| Part | Where | What it does |" in architecture
    assert "`docs/adr/`" in architecture
    for seed in (readme, architecture):
        assert "demo-app" in seed
        assert "{{" not in seed


def test_claude_md_imports_the_guide() -> None:
    assert text("agnostic", "CLAUDE.md") == "@AGENTS.md\n"


def test_feature_and_pattern_formats_name_every_key() -> None:
    features = text("agnostic", "docs/features/README.md")
    for key in ("purpose", "entry_points", "data", "observe", "reproduce"):
        assert f"`{key}`" in features
    # devctl's map check requires at least one entry point.
    assert "| Paths where the feature is entered | A non-empty list; each path exists |" in features
    patterns = text("agnostic", "docs/patterns/README.md")
    for key in (
        "`task`",
        "`reference`",
        "`enforced_by`",
        "## Lessons",
        "`check:",
        "`test:",
        "`ruff:",
        "`banned:",
        "`contract:",
        "`type:",
    ):
        assert key in patterns


def test_the_devctl_shim_is_managed_executable_and_valid_sh(tmp_path: Path) -> None:
    shim = rendered("agnostic")["devctl"]
    assert shim.kind == "managed"
    assert "devctl" in load_manifest().executable
    assert b'exec uv run --project "$root/tools/devctl" --frozen --quiet devctl "$@"' in content(
        shim
    )
    (tmp_path / "devctl").write_bytes(content(shim))
    result = run_process(["sh", "-n", str(tmp_path / "devctl")], tmp_path, 30)
    assert result.returncode == 0, result.stderr


def test_devctl_is_its_own_uv_workspace_and_its_versions_agree() -> None:
    files = rendered("agnostic")
    project = tomllib.loads(content(files["tools/devctl/pyproject.toml"]).decode())
    assert project["tool"]["uv"]["workspace"] == {"members": []}
    assert project["project"]["scripts"] == {"devctl": "devctl.cli:main"}
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "devctl",
        "devctl_project",
    ]
    version = project["project"]["version"]
    lock = tomllib.loads(content(files["tools/devctl/uv.lock"]).decode())
    locked = {p["name"]: p.get("version") for p in lock["package"]}
    assert locked["devctl"] == version
    # uv.lock records each dependency under its normalized name.
    declared = {
        re.sub(r"[-_.]+", "-", re.split(r"[\[<>=!~;\s]", requirement, maxsplit=1)[0]).lower()
        for requirement in project["project"]["dependencies"]
    }
    assert declared <= locked.keys()
    assert (
        f'__version__ = "{version}"' in content(files["tools/devctl/devctl/__init__.py"]).decode()
    )


def test_devctl_project_is_seeded_and_the_environment_is_ignored() -> None:
    files = rendered("agnostic")
    assert files["tools/devctl/devctl_project/__init__.py"].kind == "seeded"
    assert files["tools/devctl/.gitignore"].content == b"/.venv/\n__pycache__/\n"


def test_askpass_is_written_executable() -> None:
    # init and sync set the executable bit only for paths kit.toml lists.
    assert "tools/devctl/devctl/github/askpass.py" in load_manifest().executable


@pytest.mark.parametrize("stack", STACKS)
def test_codex_seed_matches_the_protocol(stack: Stack) -> None:
    assert json.loads(text(stack, ".codex/hooks.json")) == CODEX_WIRING


@pytest.mark.parametrize("stack", STACKS)
@pytest.mark.parametrize("existing", [False, True])
def test_codex_seed_init_and_sync_preserve_project_ownership(
    stack: Stack,
    existing: bool,
    git_repo: Path,
    commit_all: Callable[..., None],
) -> None:
    path = git_repo / ".codex/hooks.json"
    if existing:
        path.parent.mkdir()
        path.write_text('{"hooks": {}}\n')
        commit_all(git_repo)
    init_repository(git_repo, stack=stack, variables=VARIABLES)
    expected = '{"hooks": {}}\n' if existing else text(stack, ".codex/hooks.json")
    assert path.read_text() == expected
    path.write_text('{"hooks": {}, "project_owned": true}\n')
    commit_all(git_repo)
    sync_repository(git_repo, in_place=True)
    assert path.read_text() == '{"hooks": {}, "project_owned": true}\n'


@pytest.mark.parametrize("stack", STACKS)
@pytest.mark.parametrize("existing", [False, True])
def test_sync_adds_codex_wiring_without_overwriting_an_existing_definition(
    stack: Stack,
    existing: bool,
    git_repo: Path,
    make_templates: Callable[..., Path],
    commit_all: Callable[..., None],
) -> None:
    old = make_templates("before-codex")
    init_repository(git_repo, stack=stack, variables=VARIABLES, templates_root=old)
    path = git_repo / ".codex/hooks.json"
    if existing:
        path.parent.mkdir()
        path.write_text('{"hooks": {}}\n')
        commit_all(git_repo)
    manifest = (
        (old / "kit.toml").read_text().replace("seeded = [", 'seeded = [".codex/hooks.json", ')
    )
    seed = text(stack, ".codex/hooks.json")
    new = make_templates("with-codex", {"kit.toml": manifest, "common/.codex/hooks.json": seed})
    sync_repository(git_repo, in_place=True, templates_root=new)
    assert path.read_text() == ('{"hooks": {}}\n' if existing else seed)
