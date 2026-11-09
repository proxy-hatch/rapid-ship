"""Map rule 9: validate the tracked Corrections ledger in the work tree."""

from collections.abc import Sequence

from devctl.check.references import path_problem, resolve
from devctl.check.steps import CheckContext
from devctl.check.tracked import TrackedFiles
from devctl.codeowners import ledger_entry
from devctl.ledger import LAST_PASS, Entry, LastPass, read_entry, read_last_pass
from devctl.repo import RepoError


def ledger_errors(context: CheckContext, files: Sequence[str]) -> list[str]:
    tracked = TrackedFiles.read(context.repo)
    errors: list[str] = []
    for file in files:
        if not (ledger_entry(file) or file == LAST_PASS):
            continue
        path = context.repo.root / file
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{file}: format: cannot read UTF-8 text: {error}")
            continue
        result = read_last_pass(text) if file == LAST_PASS else read_entry(file, text)
        if isinstance(result, list):
            errors.extend(result)
        elif isinstance(result, LastPass):
            try:
                context.repo.git("cat-file", "-e", f"{result.through}^{{commit}}")
            except RepoError:
                errors.append(
                    f"{file}: through: through names no commit in this repository; "
                    "use a full commit SHA"
                )
        else:
            errors.extend(_prevention_errors(context, tracked, result))
    return errors


def _prevention_errors(context: CheckContext, tracked: TrackedFiles, entry: Entry) -> list[str]:
    errors: list[str] = []
    if entry.status != "implemented":
        return errors
    for item in entry.prevented_by:
        reason = resolve(item, context, tracked, entry.file)
        if reason is not None and (problem := path_problem(item, tracked)) is not None:
            errors.append(
                f"{entry.file}: prevented_by: {reason}; or a repository path that exists "
                f"(tracked by git); missing tracked repository path {item}: {problem}"
            )
    return errors
