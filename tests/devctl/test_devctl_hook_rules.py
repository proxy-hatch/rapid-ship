"""Offline: devctl hook's rules on normalised tool calls, with simulated settings and branches."""

from __future__ import annotations

from pathlib import Path

import pytest

from check_workspace import new_workspace
from devctl.command_line import simple_commands
from devctl.hook import decide, read_settings, work_tree_root
from devctl.hook_protocols import Decision, HookSettings, ToolCall
from devctl.merge_guard import LocalBranches, read_branches

ROOT = Path("/repo")
PROTECTED = ("/.github/", "/.claude/", "/**/AGENTS.md", "/.rapid-ship/")
OFF = HookSettings(
    agent_identity=False, protected=PROTECTED, repository="o/r", reviewer_app_slug=None
)
ON = HookSettings(
    agent_identity=True, protected=PROTECTED, repository="o/r", reviewer_app_slug="o-reviewer"
)
TASK = LocalBranches(frozenset({"main"}), "task")
ON_MAIN = LocalBranches(frozenset({"main"}), "main")


def unread() -> LocalBranches:
    raise AssertionError("local git was read")


def decided(line: str, settings: HookSettings | None = OFF) -> tuple[Decision, str]:
    return decide(ToolCall(line, (), ROOT), ROOT, settings, lambda: TASK)


def edited(path: str, settings: HookSettings | None = OFF) -> tuple[Decision, str]:
    return decide(ToolCall(None, (ROOT / path,), ROOT), ROOT, settings, unread)


SHELL = [  # command line, the rule that denies it with Agent identity off (None: no decision)
    ("git status", None),
    ("git commit -m x --no-verify", "G1"),
    ("git commit -n -m x", "G1"),
    ("git commit -anm x", "G1"),
    ("git commit -mn", None),
    ("git -C sub commit -n -m x", "G1"),
    ("/usr/bin/git commit --no-verify -m x", "G1"),
    ("git push --no-verify origin task", "G1"),
    ("git push --force origin task", "G2"),
    ("git push -uf origin task", "G2"),
    ("git push --force-with-lease=task origin task", "G2"),
    ("git push --force-if-includes origin task", "G2"),
    ("git push origin +task", "G2"),
    ("git push origin task", None),
    ("git push origin main", "G3"),
    ("git push origin HEAD:refs/heads/main", "G3"),
    ("git push origin :main", "G3"),
    ("git push origin --delete main", "G3"),
    ("git push --all origin", "G3"),
    ("git push --mirror origin", "G3"),
    ("gh pr merge 7 --admin --squash", "G3"),
    ("./devctl as worker gh pr merge 7 --admin", "G3"),
    ("gh api -X PUT repos/o/r/pulls/7/merge", "G3"),
    ("gh api -XPUT /repos/{owner}/{repo}/pulls/7/merge", "G3"),
    ("gh api repos/o/r/merges -f base=main -f head=task", "G3"),
    ("gh api https://api.github.com/repos/o/r/git/refs/heads/main -X PATCH -f sha=a", "G3"),
    ("gh api repos/o/r/contents/a.md --method=PUT --input body.json", "G3"),
    ("./devctl as worker gh api -X PUT repos/o/r/pulls/7/merge", "G3"),
    (
        "gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'",
        "G3",
    ),
    ("gh api graphql -F query=@merge.graphql", None),
    ("gh api repos/o/r/git/refs/heads/task -X PATCH -f sha=a", None),
    ("gh api repos/o/r/pulls/7/merge", None),
    ("gh pr merge 7 --squash", None),
    ("echo ok; git push -f origin task", "G2"),
    ("make && git commit -n -m x", "G1"),
    ("false || git push origin main", "G3"),
    ("echo ok\ngit push --force origin task", "G2"),
    ("sleep 1 & git push origin main", "G3"),
    ("(cd sub && git push -f origin task)", "G2"),
    ("GIT_TRACE=1 git push -f origin task", "G2"),
    ("sh -c 'git push --force origin task'", None),
    ("git push origin main >/dev/null", "G3"),
    ("git push -f origin task 2>&1", "G2"),
    ("cd sub  # go there\ngit push -f origin task", "G2"),
    ("echo $(git push -f origin task)", "G2"),
    ("echo `git push -f origin task`", "G2"),
    # The words after a substitution stay in the command that holds it.
    ("git push origin $(git branch --show-current) --force", "G2"),
    ("git push -u origin $(git rev-parse --abbrev-ref HEAD) --force-with-lease", "G2"),
    ("git push origin `git branch --show-current` --force", "G2"),
    ("git commit -F $(mktemp) --no-verify", "G1"),
    ("gh pr merge 7 $(true) --admin", "G3"),
    ("gh pr merge 7 `true` --admin", "G3"),
    ("git push origin $(git rev-parse HEAD):main", "G3"),
    ("cat <<'EOF' > notes.md\ngit push --force origin task\nEOF", None),
    ("git commit -n -F - <<EOF\nIt's done\nEOF", "G1"),
]
IDENTITY = [  # the rule that denies it with Agent identity on; with it off, no decision
    ("git push origin task", "G7"),
    ("git push --dry-run", "G7"),
    ("./devctl as worker push", None),
    ("gh pr create --fill", "G8"),
    ("gh pr merge 7 --squash", "G8"),
    ("gh pr -R o/r comment 7 -b hi", "G8"),
    ("gh pr view 7", None),
    ("gh pr checkout 7", None),
    ("gh issue comment 3 -b hi", "G8"),
    ("gh issue list", None),
    ("gh api repos/o/r/issues -X POST -f title=x", "G8"),
    ("gh api repos/o/r/issues -X GET -f state=open", "G8"),
    ("gh api repos/o/r/pulls/7", None),
    ("./devctl as worker gh pr create --fill", None),
    ("gh release create v1", None),
    ("gh pr create --body-file - <<'EOF'\nIt's done\nEOF", "G8"),
]
EDITS = [
    (".rapid-ship/kit.lock", "deny", "G4"),
    ("AGENTS.md", "ask", "G5"),
    ("src/app/AGENTS.md", "ask", "G5"),
    (".claude/settings.json", "ask", "G5"),
    ("src/app/core.py", None, None),
    # macOS's default file system ignores case, so a case variant writes the same file.
    ("agents.md", "ask", "G5"),
    (".GitHub/workflows/ci.yml", "ask", "G5"),
    (".rapid-ship/KIT.lock", "deny", "G4"),
    (".Rapid-Ship/kit.lock", "deny", "G4"),
]
# The shell runs each of these commands, so Spec 1 section 4 checks it: a comment that holds
# an apostrophe, a reserved word or a brace before a command, process substitution, a
# redirection after a subshell, --branches, git's newer name for --all, a backslash that
# continues the line, a # inside a word, and each heredoc form. Each heredoc body holds an
# apostrophe, so a heredoc the hook misses fails the split, and one it opens wrongly hides
# the push.
GRAMMAR = [
    ("git status  # don't push yet\ngit push -f origin task", "G2"),
    ("if git push origin main; then echo ok; fi", "G3"),
    ("while true; do git push -f origin task; done", "G2"),
    ("! git commit -n -m x", "G1"),
    ("{ git push -f origin task; }", "G2"),
    ("cat <(git push -f origin task)", "G2"),
    ("(git push -f origin task)>log; echo ok", "G2"),
    ("git push --branches origin", "G3"),
    ("gh pr merge 7 \\\n  --admin", "G3"),
    ("git push origin \\\n  main", "G3"),
    ("echo '# not a comment' && git push origin main", "G3"),
    ("git log a#b c'#d' \"#e\" # --no-verify", None),
    ("ls a\\ #b; git push -f origin task", "G2"),
    ("ls a\\\n#b; git push -f origin task", "G2"),
    ("git log \\\n# --no-verify", None),
    ('git commit -F - <<< "it\'s"\ngit push -f origin task', "G2"),
    ("cat <<-EOF\n\tit's\n\tEOF\ngit push -f origin task", "G2"),
    ('cat <<"EOF"\nit\'s\nEOF\ngit push -f origin task', "G2"),
    ("cat <<A <<B\nit's\nA\nit's\nB\ngit push -f origin task", "G2"),
    ("cat << 'EOF'\nit's\nEOF\ngit push -f origin task", "G2"),
    ("cat <<\\EOF\nit's\nEOF\ngit push -f origin task", "G2"),
    # Only an unquoted << opens a heredoc: not one in quotes, a comment or arithmetic, which
    # $(( ... )), (( ... )), a C-style for (( ... )) and the older $[ ... ] hold.
    ("echo '<<EOF'\ngit push -f origin task", "G2"),
    ("cd sub  # copy it with cat <<EOF\ngit push -f origin task", "G2"),
    ("echo $((1<<2))\ngit push -f origin task", "G2"),
    ("(( n = 1 << 2 ))\ngit push -f origin task", "G2"),
    ("if((1<<2)); then :; fi\ngit push -f origin task", "G2"),
    ("for (( i = 0; i < 1 << 2; i++ )); do :; done\ngit push -f origin task", "G2"),
    ("echo $[1<<2]\ngit push -f origin task", "G2"),
    # Arithmetic still runs the substitutions inside it, and ((a) ) is a subshell in a subshell.
    ("(( $(git push -f origin task) ))", "G2"),
    ("echo $[ `git push -f origin task` ]", "G2"),
    ("((git push -f origin task) )", "G2"),
    ("gh pr view 7 --json body -q \"$(cat <<'EOF'\nit's\nEOF\n)\"; git push -f origin task", "G2"),
    # Quotes that shlex alone misreads.
    ("gh pr merge 5 --admin; echo $'it\\'s'", "G3"),
    ('git push --force origin task; y="$(echo \'a"b\')"', "G2"),
    ('echo "$(git push -f origin task)"', "G2"),
    ('echo "`git push -f origin task`"', "G2"),
    ("x=$((git push -f origin task) )", "G2"),
    # A quoted or escaped operator is a word.
    ("git commit -m ';' --no-verify", "G1"),
    ("git commit -m \\; --no-verify", "G1"),
    ("git push origin '>' -f", "G2"),
    ("'if' git push -f origin task", None),
]
G3 = "lands a change on the default branch outside the merge guard; open a pull request and "
MESSAGES = [  # command line, Agent identity on, the whole message
    (
        "git commit -n -m x",
        False,
        "G1: --no-verify and git commit -n skip the pre-commit hook; run the command without "
        "them, and fix what the hook reports",
    ),
    (
        "git push -f origin task",
        False,
        "G2: a force push rewrites published history; push without --force, -f, "
        "--force-with-lease, --force-if-includes or a + refspec, and merge the base branch "
        "instead",
    ),
    (
        "gh pr merge 7 --admin",
        False,
        f"G3: gh pr merge --admin {G3}merge it with gh pr merge <number>, without --admin",
    ),
    (
        "git push origin main",
        False,
        f"G3: a git push to the default branch {G3}merge it with gh pr merge <number>, "
        "without --admin",
    ),
    (
        "gh api -X PUT repos/o/r/pulls/7/merge",
        False,
        f"G3: a gh api write to a merge, ref or contents endpoint {G3}merge it with gh pr merge "
        "<number>, without --admin",
    ),
    (
        "gh api graphql -f query='mutation { mergeBranch }'",
        False,
        f"G3: a GraphQL merge or ref mutation {G3}merge it with gh pr merge <number>, "
        "without --admin",
    ),
    (
        "git push origin task",
        True,
        "G7: Agent identity is on, so the Worker App pushes; run ./devctl as worker push",
    ),
    (
        "gh issue comment 3 -b 'hi there'",
        True,
        "G8: Agent identity is on, so an App makes gh writes; "
        "run ./devctl as <role> gh issue comment 3 -b 'hi there'",
    ),
]


@pytest.mark.parametrize(("line", "rule"), SHELL)
def test_each_shell_rule_denies_its_forms(line: str, rule: str | None) -> None:
    decision, reason = decided(line)
    assert decision == ("deny" if rule else None)
    assert reason.startswith(f"{rule}: ") if rule else reason == ""


@pytest.mark.parametrize(("line", "rule"), IDENTITY)
def test_g7_and_g8_apply_only_with_agent_identity(line: str, rule: str | None) -> None:
    decision, reason = decided(line, ON)
    assert decision == ("deny" if rule else None)
    assert reason.startswith(f"{rule}: ") if rule else reason == ""
    assert decided(line, OFF) == (None, "")
    assert decided(line, None) == (None, "")


@pytest.mark.parametrize(("path", "decision", "rule"), EDITS)
def test_edit_rules(path: str, decision: Decision, rule: str | None) -> None:
    found, reason = edited(path)
    assert found == decision
    assert reason.startswith(f"{rule}: ") if rule else reason == ""


@pytest.mark.parametrize(("line", "rule"), GRAMMAR)
def test_shell_grammar_hides_no_command(line: str, rule: str | None) -> None:
    decision, reason = decided(line)
    assert decision == ("deny" if rule else None)
    assert reason.startswith(f"{rule}: ") if rule else reason == ""


@pytest.mark.parametrize(("line", "identity", "message"), MESSAGES)
def test_each_shell_message_names_the_way_through(line: str, identity: bool, message: str) -> None:
    assert decided(line, ON if identity else OFF) == ("deny", message)


def test_each_edit_message_names_the_file() -> None:
    assert edited(".rapid-ship/kit.lock") == (
        "deny",
        "G4: rapid-ship writes .rapid-ship/kit.lock; change Kit files with rapid-ship sync instead",
    )
    assert edited("src/app/AGENTS.md") == (
        "ask",
        "G5: src/app/AGENTS.md is in the Protected set (CODEOWNERS pattern /**/AGENTS.md); "
        "the owner approves this edit",
    )


def test_a_case_variant_names_the_path_and_the_pattern_as_written() -> None:
    assert edited("Src/App/Agents.MD") == (
        "ask",
        "G5: Src/App/Agents.MD is in the Protected set (CODEOWNERS pattern /**/AGENTS.md); "
        "the owner approves this edit",
    )


def test_a_deny_beats_an_ask() -> None:
    call = ToolCall(None, (ROOT / "AGENTS.md", ROOT / ".rapid-ship/kit.lock"), ROOT)
    assert decide(call, ROOT, OFF, unread)[0] == "deny"


def test_g1_to_g4_apply_and_g5_gives_no_decision_with_unreadable_settings() -> None:
    for line in ("git commit -n -m x", "git push -f origin task", "git push origin main"):
        assert decided(line, None)[0] == "deny"
    assert edited(".rapid-ship/kit.lock", None)[0] == "deny"
    assert edited("AGENTS.md", None) == (None, "")


def test_an_edit_outside_the_repository_gets_no_decision() -> None:
    call = ToolCall(None, (Path("/elsewhere/AGENTS.md"),), ROOT)
    assert decide(call, ROOT, OFF, unread) == (None, "")


@pytest.mark.parametrize(
    ("line", "branches", "rule"),
    [
        ("git push origin master", LocalBranches(frozenset({"main", "master"}), "task"), "G3"),
        ("git push origin master", LocalBranches(frozenset({"trunk"}), "task"), None),
        ("git push origin trunk", LocalBranches(frozenset({"trunk"}), "task"), "G3"),
        ("git push", LocalBranches(frozenset({"main"}), "main"), "G3"),
        ("git push origin HEAD", LocalBranches(frozenset({"main"}), "main"), "G3"),
        ("git push 2>&1", LocalBranches(frozenset({"main"}), "main"), "G3"),
        ("git push", TASK, None),
        ("git push", LocalBranches(frozenset({"main"}), None), None),
        ("git push origin @", ON_MAIN, "G3"),
        ("git push origin @", TASK, None),
        ("git push origin HEAD:heads/main", TASK, "G3"),
        ("git push --delete origin heads/main", TASK, "G3"),
        ("git push origin HEAD:remotes/main", TASK, None),
        ("git push origin :", TASK, "G3"),
        ("git push origin 'refs/heads/*:refs/heads/*'", TASK, "G3"),
        ("git push origin 'refs/*:refs/*'", TASK, "G3"),
        ("git push origin 'refs/heads/ma*:refs/heads/ma*'", TASK, "G3"),
        ("git push origin 'refs/heads/feature/*:refs/heads/feature/*'", TASK, None),
        ("git push origin 'refs/tags/*:refs/tags/*'", TASK, None),
        # The hook cannot read an expansion, so it takes the current branch, wherever an
        # expansion could name a branch.
        ('git push -u origin "$(git branch --show-current)"', ON_MAIN, "G3"),
        ('git push -u origin "$(git branch --show-current)"', TASK, None),
        ("git push -u origin `git branch --show-current`", ON_MAIN, "G3"),
        ("git push origin HEAD:$BRANCH", ON_MAIN, "G3"),
        ('git push origin "HEAD:refs/heads/${BRANCH}"', ON_MAIN, "G3"),
        ("git push origin HEAD:$BRANCH", TASK, None),
        ("git push origin HEAD:release/$VERSION", ON_MAIN, None),
        ("git push origin refs/tags/$TAG", ON_MAIN, None),
    ],
)
def test_a_push_to_the_default_branch(line: str, branches: LocalBranches, rule: str | None) -> None:
    assert decide(ToolCall(line, (), ROOT), ROOT, OFF, lambda: branches)[0] == (
        "deny" if rule else None
    )


def test_local_git_is_read_only_for_a_push_or_a_ref_path() -> None:
    reads: list[str] = []

    def branches() -> LocalBranches:
        reads.append("read")
        return TASK

    for line in ("git status", "gh pr view 7", "gh api -X PUT repos/o/r/pulls/7/merge"):
        decide(ToolCall(line, (), ROOT), ROOT, OFF, branches)
    assert reads == []
    for line in ("git push origin task", "gh api -X PATCH repos/o/r/git/refs/heads/x"):
        decide(ToolCall(line, (), ROOT), ROOT, OFF, branches)
    assert reads == ["read", "read"]


def test_simple_commands_split_with_shell_rules() -> None:
    found = simple_commands("a 'b;c' && d | e; f || g & h\ni")
    assert found[0] == ("a", "b;c")
    assert [words[0] for words in found[1:]] == ["d", "e", "f", "g", "h", "i"]
    with pytest.raises(ValueError, match="closing quotation"):
        simple_commands("git commit -m 'x")


def test_simple_commands_drop_redirections_and_heredoc_bodies() -> None:
    assert simple_commands("git push 2>&1 | tee log") == [("git", "push"), ("tee", "log")]
    assert simple_commands("gh pr merge 7 >/dev/null") == [("gh", "pr", "merge", "7")]
    line = "cat <<'EOF' > notes.md\nIt's done\nEOF\ngit status"
    assert simple_commands(line) == [("cat",), ("git", "status")]


def test_simple_commands_drop_comments_and_reserved_words() -> None:
    assert simple_commands("git status  # it's clean\ngit log") == [
        ("git", "status"),
        ("git", "log"),
    ]
    assert simple_commands("echo '#' a#b \\#c") == [("echo", "#", "a#b", "#c")]
    assert simple_commands("ls a\\ #b c\\\n#d") == [("ls", "a #b", "c#d")]
    assert simple_commands("if git diff; then git log; fi") == [
        ("git", "diff"),
        ("git", "log"),
        ("fi",),
    ]
    assert simple_commands("diff <(git show a) b") == [
        ("git", "show", "a"),
        ("diff", "$(...)", "b"),
    ]
    assert simple_commands("git log \\\n  --oneline") == [("git", "log", "--oneline")]
    assert simple_commands("echo 'a\\\nb'") == [("echo", "a\\\nb")]


def test_a_substitution_gives_its_commands_first_and_stays_one_word_part() -> None:
    assert simple_commands("git push origin $(git rev-parse HEAD):main --force") == [
        ("git", "rev-parse", "HEAD"),
        ("git", "push", "origin", "$(...):main", "--force"),
    ]
    assert simple_commands("a `b $(c)` <(d)x >(e) \"$(f)\" '$(g)'") == [
        ("c",),
        ("b", "$(...)"),
        ("d",),
        ("e",),
        ("f",),
        ("a", "$(...)", "$(...)x", "$(...)", "$(...)", "$(g)"),
    ]
    assert simple_commands("echo $(( $(a) << 2 ))x; b") == [("a",), ("echo", "$(...)x"), ("b",)]
    assert simple_commands("x=$((a; b) )") == [("a",), ("b",), ("x=$(...)",)]
    assert simple_commands("(( $(a) << 2 )); b") == [("a",), ("b",)]
    assert simple_commands('echo $[ $(a) << [2] ]x "$[1]"; b') == [
        ("a",),
        ("echo", "$(...)x", "$(...)"),
        ("b",),
    ]
    assert simple_commands("((a; b) )") == [("a",), ("b",)]
    assert simple_commands("((a; b))") == []  # the shell evaluates it as arithmetic
    for unclosed in ("echo $(a", "echo `a", "echo $((1", "echo <(a", "echo $[1"):
        with pytest.raises(ValueError, match="no closing"):
            simple_commands(unclosed)


def test_simple_commands_read_quotes_and_escapes_as_the_shell_does() -> None:
    assert simple_commands('echo "a\\$(b)\\"c" $"d" $\'e\\\'f\\n\' g\\') == [
        ("echo", 'a$(b)"c', "d", "e'f\n", "g\\")
    ]
    assert simple_commands("cat <<'A' | wc\n$(x)\nA\necho `printf '\\`'`") == [
        ("printf", "`"),
        ("cat",),
        ("wc",),
        ("echo", "$(...)"),
    ]
    with pytest.raises(ValueError, match="heredoc has no WORD"):
        simple_commands("cat <<")


def test_read_branches_from_local_git(tmp_path: Path) -> None:
    workspace = new_workspace(tmp_path / "main")
    workspace.commit()
    assert read_branches(workspace.root) == LocalBranches(frozenset({"main", "master"}), "main")

    workspace.git("update-ref", "refs/remotes/origin/trunk", "HEAD")
    workspace.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert read_branches(workspace.root).default == frozenset({"trunk"})

    workspace.git("checkout", "-q", "--detach")
    assert read_branches(workspace.root).current is None


def test_an_edit_in_a_linked_worktree_belongs_to_that_worktree(tmp_path: Path) -> None:
    main = new_workspace(tmp_path / "main")
    main.commit()
    main.git("worktree", "add", "-q", "-b", "wt", ".worktrees/wt")
    worktree = main.root / ".worktrees/wt"

    assert work_tree_root(worktree / ".rapid-ship/kit.lock") == worktree
    assert work_tree_root(main.root / "src/app.py") == main.root
    assert work_tree_root(Path("/")) is None


def test_unreadable_settings_switch_off_g5_g7_g8_and_say_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n\n[linear]\nteam = "x"\n')

    reason = read_settings(workspace.root)

    assert isinstance(reason, str)
    assert "[linear] was removed" in reason
    [line] = capsys.readouterr().err.splitlines()
    assert line.startswith("devctl hook: ")
    assert reason in line
    assert line.endswith("; G5, G7 and G8 give no decision")

    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n')
    (workspace.root / ".github").mkdir()
    (workspace.root / ".github/CODEOWNERS").write_bytes(b"/.github/ @o\n\xff\xfe\n")
    assert isinstance(read_settings(workspace.root), str)


def test_a_missing_codeowners_is_an_empty_protected_set(tmp_path: Path) -> None:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n')

    assert read_settings(workspace.root) == HookSettings(False, (), None, None)


def test_read_settings_takes_the_reviewer_app_slug_with_agent_identity(tmp_path: Path) -> None:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(
        ".rapid-ship/project.toml",
        'stack = "python"\n\n[github]\nrepository = "o/r"\n'
        'worker_app_id = 1\nworker_app_slug = "o-worker"\n'
        'reviewer_app_id = 2\nreviewer_app_slug = "o-reviewer"\n',
    )
    workspace.write(".github/CODEOWNERS", "* @o\n/.github/ @o\n")

    assert read_settings(workspace.root) == HookSettings(True, ("/.github/",), "o/r", "o-reviewer")
