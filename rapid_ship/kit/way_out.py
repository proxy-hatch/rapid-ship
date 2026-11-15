"""The guided errors init raises before it writes anything: a package that is no Python package
name, a pyproject.toml it cannot read, and an existing stack with no package directory or source
root. Each names its cause (where the package came from, the file init could not read, or the
directories it looked in) and a next step that works as written. init.py keeps the lookup."""

from collections.abc import Sequence

from rapid_ship.kit.stacks import ProjectStack, under
from rapid_ship.kit.templates import KitError


def option_not_a_package_name(package: str) -> KitError:
    """A --package value that is no Python package name."""
    return KitError(
        f"package {package!r} is not a Python package name; --package takes the package "
        "directory's name, not a path."
    )


def default_not_a_package_name(package: str, declared: str | None, project_name: str) -> KitError:
    """The package that init derived is no Python package name. It comes from the root
    pyproject.toml's [project] name, declared, else from the project name."""
    origin = (
        f"the [project] name {declared!r} in pyproject.toml"
        if declared
        else f"the project name {project_name!r}"
    )
    return KitError(
        f"package {package!r} is not a Python package name. It comes from {origin}; pass "
        "--package to override it."
    )


def unreadable_root(error: Exception) -> KitError:
    """The root pyproject.toml, which init reads for the package before it looks at any stack,
    so the error names the file and no stack's directory."""
    return KitError(
        f"init wrote nothing: cannot read pyproject.toml ({error}). Fix pyproject.toml and "
        "commit the fix, then run init again, or pass --package with the package directory's "
        "name, not its path, so that init does not read the file."
    )


def leave_out(stack: ProjectStack, stacks: Sequence[ProjectStack]) -> str:
    """The way out for a stack whose directory holds no product code. With no other stack to
    keep, leaving its option out would make init print its proposal again."""
    where, option = "the root", f"--stack {stack.name}"
    if stack.directory != ".":
        where, option = stack.directory, f"--stack {stack.name}={stack.directory}"
    if len(stacks) > 1:
        return f"If {where} holds no product code, run init without {option}."
    return (
        f"If {where} holds no product code, replace {option} with a --stack option for each "
        "stack that has product code, or with --stack agnostic when none has."
    )


def unreadable_stack(
    stack: ProjectStack, stacks: Sequence[ProjectStack], error: Exception
) -> KitError:
    """A stack's own pyproject.toml, which init reads for its package. The error names no
    package directory, because init could not read the name."""
    settings = under(stack.directory, "pyproject.toml")
    return KitError(
        f"init wrote nothing: cannot read {settings} ({error}). Fix {settings} and commit the "
        f"fix, then run init again. {leave_out(stack, stacks)}"
    )


def no_project_name(stack: ProjectStack, stacks: Sequence[ProjectStack]) -> KitError:
    """A Python stack whose pyproject.toml has no [project] name, so init cannot tell where its
    package directory is."""
    settings = under(stack.directory, "pyproject.toml")
    package = under(stack.directory, "src/<name>")
    return KitError(
        f"init wrote nothing: the python stack in {stack.directory} has no package directory: "
        f"{settings} has no [project] name, so init could not tell where to look. Add a "
        f"[project] name to {settings}, create {package}/__init__.py, where <name> is that name "
        "in lowercase with each run of - _ or . replaced by _, move the product code into "
        f"{package}/ and commit them, then run init again. {leave_out(stack, stacks)}"
    )


def no_source_root(
    stack: ProjectStack, stacks: Sequence[ProjectStack], looked: Sequence[str]
) -> KitError:
    """A stack with no tracked file in any directory of looked. The first names the directory
    to create or move the product code into."""
    first = looked[0]
    noun = "source root"
    steps = f"Move the product code into {first}/ and commit it, then run init again."
    if stack.name == "python":
        noun = "package directory"
        steps = (
            f"Create {first}/__init__.py, move the product code into {first}/ and commit them, "
            "then run init again."
        )
        if stack.directory == ".":
            steps += (
                " If the product code is already in a package directory with another name, "
                "pass --package with that directory's name, not its path."
            )
    return KitError(
        f"init wrote nothing: the {stack.name} stack in {stack.directory} has no {noun}: init "
        f"looked in {' or '.join(looked)} and found no tracked file. {steps} "
        f"{leave_out(stack, stacks)}"
    )
