"""Offline: which gh api calls the hook denies as writes while Agent identity is on, judged on
normalised tool calls with simulated settings. A call to a GraphQL endpoint reads only when it
sends one inline document that holds queries alone and no placeholder that gh fills; a call to
any other endpoint reads exactly when its method is GET."""

from __future__ import annotations

import shlex

import pytest

from devctl.command_line import ApiCall, parse_api
from devctl.hook_protocols import HookSettings
from test_devctl_hook_rules import OFF, ON, decided

MUTATION = "mutation { addComment(input: {}) { clientMutationId } }"


def graphql(document: str, *options: str, endpoint: str = "graphql", field: str = "-f") -> str:
    """The gh api command line that sends the document inline, in a raw field unless field says
    otherwise."""
    return shlex.join(["gh", "api", *options, endpoint, field, f"query={document}"])


def denial(line: str, settings: HookSettings | None = ON) -> str | None:
    """The reason that denies the line, or None when no rule decides."""
    decision, reason = decided(line, settings)
    assert decision in (None, "deny")
    return reason if decision else None


QUERIES = {  # documents that hold queries alone, whatever else they hold
    "anonymous": "{ viewer { login } }",
    "query keyword": "query { viewer { login } }",
    "variables, a default and a directive": (
        "query Threads($first: Int = 50, $skip: Boolean = false) @cached(ttl: 60) "
        "{ viewer { login @skip(if: $skip) } }"
    ),
    "list and object variables": (
        "query($ids: [ID!]!, $f: Filter = {a: 1, b: [1, 2]}) "
        "{ nodes(ids: $ids, filter: $f) { id } }"
    ),
    "a fragment after the query": (
        "query($teams: Boolean!) { viewer { ...Info } } "
        "fragment Info on User { login organizations(first: 5) @include(if: $teams) "
        "{ totalCount } }"
    ),
    "a fragment before the query": "fragment Info on User { login } query { viewer { ...Info } }",
    "a fragment with a directive": "query { a } fragment F on User @d(a: 1) @e { id }",
    "an inline fragment": "{ node(id: 1) { ... on Issue { title } ... @skip(if: false) { id } } }",
    "two queries": "query A { a } query B { b }",
    "a comment that holds a brace and a mutation": "query { a # } mutation { b }\n}",
    "a trailing comment": "{ a } # mutation { b }",
    "a string that holds a brace and a mutation": '{ a(x: "} mutation {") }',
    "an empty string": '{ search(query: "", type: ISSUE, first: 1) { issueCount } }',
    "a string with escapes": r'{ a(x: "say \"mutation {\" \\ \u00e9 \/") }',
    "a block string that holds an escaped triple quote": (
        r'{ a(x: """ \""" mutation { b } "quoted" """) }'
    ),
    "a block string beside a string": '{ a(x: """one""", y: "two") }',
    "keywords as names": "query mutation { mutation { subscription fragment query on } }",
    "numbers, lists and objects": (
        "query { search(first: 10, ratio: -1.5e3, ids: [1, 2], f: {on: true, n: null}) { a } }"
    ),
    "underscore names": "{ __typename _x { __schema } }",
    "a $ in a string inside parentheses": '{ search(query: "cost:$5") { issueCount } }',
    "a $ in a comment inside parentheses": "query($a: Int # $a counts\n) { x(a: $a) }",
    "an object value that holds a variable": "query($id: ID!) { node(input: {id: $id}) { id } }",
    "a list value that holds a variable": "query($a: ID!) { nodes(ids: [$a]) { id } }",
    "commas, a leading byte order mark and CRLF": "\ufeffquery,A\r\n{\r\n  a,\r\n  b\r\n}\r\n",
    "names that only start like a placeholder": (
        '{ a(x: ":repository", y: ":branches", z: "{ownership}") { b } }'
    ),
    "placeholder names with a capital or spaces": '{ a(x: ":Owner", y: "{ repo }") { owner } }',
    "names that go on after a placeholder name": '{ a(x: ":repo_", y: ":repoe") { b } }',
}
OTHER_DOCUMENTS = {  # documents that hold more than queries, or that the hook cannot read
    "a mutation": MUTATION,
    "an anonymous mutation after a query": f"{{ a }} {MUTATION}",
    "a query after a mutation": f"{MUTATION} query {{ a }}",
    "a mutation after a fragment": f"fragment F on User {{ login }} {MUTATION}",
    "a named mutation with variables and a directive": (
        "mutation Add($body: String!) @x { addComment(input: {body: $body}) { clientMutationId } }"
    ),
    "a subscription": "subscription { x }",
    "a subscription beside a query": "{ a } subscription S { x }",
    "a variable outside every pair of parentheses": "{ viewer { login $x } }",
    "a variable after the last definition": "{ a } $x",
    "a variable after the parentheses close": "query($a: Int) { x(a: $a) y $b }",
    "a variable in a comment after a query": "{ a } # $X",
    "a variable in a comment before a query": "# $X\n{ a }",
    "a variable in a comment after the parentheses close": "query($a: Int) { x(a: $a) } # $a",
    "a variable in a string in a selection set": '{ a "$X" }',
    "a variable in a block string in a selection set": '{ a """$X""" }',
    "an unclosed brace": "{ viewer { login }",
    "an extra closing brace": "{ viewer { login } } }",
    "pairs that do not match": "{ viewer ( login } )",
    "an unclosed parenthesis": "query($a: Int { a }",
    "an unterminated string": '{ search(query: "abc, type: ISSUE) { issueCount } }',
    "an unterminated block string": '{ search(query: """abc, type: ISSUE) { issueCount } }',
    "an escaped triple quote that leaves a block string open": r'{ a(x: """ \""" ) }',
    "four quotes, which open a block string that never ends": '{ a(x: """") }',
    "a fragment named on": "{ a } fragment on on T { b }",
    "a string with a raw line break": '{ a(x: "one\ntwo") }',
    "a string with an unknown escape": r'{ a(x: "\q") }',
    "a comment that ends at a carriage return": "{ a } # note\rmutation { b }",
    "a keyword with a capital letter": "Query { viewer { login } }",
    "a fragment only": "fragment F on User { login }",
    "an empty document": "",
    "only whitespace and a comment": "  # nothing here\n",
    "a stray top-level name": "viewer { login }",
    "a stray token after a query": "{ a } b",
    "a stray number": "{ a } 5",
    "a string before a query": '"""Describes the query""" { a }',
    "an operation with no selection set": "query Foo($a: Int)",
    "a keyword after the operation name": "query q mutation { a }",
    "a type definition": "type A { b: Int }",
    "a schema definition": "schema { query: Q }",
    "an invalid character": "{ a % }",
    "a single dot": "{ a . b }",
    "two dots": "{ a .. b }",
    "a name with an accent": "{ vi\xe9wer { login } }",
    "a byte order mark after the start": "{ a }\ufeff{ b }",
}
# What gh's -F fills in a value, from the repository, GH_REPO or the current branch.
PLACEHOLDERS = ["{owner}", "{repo}", "{branch}", ":owner", ":repo", ":branch"]
PLACES = {  # a document of queries alone, with <name> where a placeholder can stand
    "a string": '{ repository(name: "<name>") { id } }',
    "a block string": '{ repository(name: """<name>""") { id } }',
    "a comment": "# <name>\n{ viewer { login } }",
    "a selection set": "{ viewer { login } } { a(x: <name>) { b } }",
}
# The places where a letter outside ASCII is valid GraphQL: a selection set takes none.
TEXT_PLACES = {name: place for name, place in PLACES.items() if name != "a selection set"}
# gh's matcher is a Go regexp, whose word boundary reads ASCII only, so a name that one of these
# follows at once is a placeholder. Python's word boundary counts them as word characters.
LETTERS_OUTSIDE_ASCII = {
    "e with an acute accent": chr(0xE9),
    "n with a tilde": chr(0xF1),
    "u with a diaeresis": chr(0xFC),
    "a CJK character": chr(0x4E2D),
}
# GH_REPO names a repository whose name closes the block string that the hook reads in the document
# below. What gh sends once it has put that name in place of {repo} holds a mutation beside queries.
CLOSING_REPOSITORY = 'x/"""){__typename}}'
FILLED_DOCUMENT = (
    'query Q { node(id: """{repo} mutation M { addComment(input: {subjectId: "S", body: "B"}) '
    '{ clientMutationId } } query R { node(id: {repo}""") { __typename } }'
)
FILLED_LINE = (
    f"GH_REPO='{CLOSING_REPOSITORY}' gh api graphql -F 'query={FILLED_DOCUMENT}' -f operationName=M"
)
REST_READS = [
    "gh api repos/o/r/issues -X GET -f state=open",
    "gh api repos/o/r/issues -X GET -F per_page=50",
    "gh api repos/o/r/issues --method=GET --raw-field q=x",
    "gh api repos/o/r/issues --method GET --field per_page=50",
    "gh api repos/o/r/issues -X get -f q=x",
    "gh api repos/o/r/issues -XGET -f q=x",
    "gh api repos/o/r/issues -X GET --input q.json",
    "gh api repos/o/r/issues -X GET --input=q.json -f q=x",
    "gh api -X GET advisories -f ecosystem=npm -f affects=minimatch",
    "gh api -X GET /search/issues -f 'q=repo:o/r is:open' --paginate -H 'Accept: x' --jq .items",
    # A REST path that ends in graphql is no GraphQL endpoint.
    "gh api -X GET repos/o/r/contents/graphql -f ref=main",
    "gh api -X GET https://ghe.example.com/api/v3/repos/o/r/contents/graphql -f ref=main",
    "env GH_DEBUG=1 gh api -X GET repos/o/r/issues -f state=open",
    # The last method given decides, as gh reads it.
    "gh api repos/o/r/issues -X POST -X GET -f q=x",
    "gh api repos/o/r/issues -f q=x --method=get",
    "gh api repos/o/r/issues -X GET",
    "gh api repos/o/r/issues",
    # A placeholder in the path or in a field changes no method.
    "gh api -X GET repos/{owner}/{repo}/issues -f state=open",
    "gh api -X GET repos/:owner/:repo/issues -F ref=:branch",
    "gh api repos/{owner}/{repo}/pulls/1",
]
REST_WRITES = [
    # Fields or --input without a method send a POST.
    "gh api repos/o/r/issues -f title=x",
    "gh api repos/o/r/issues -F n=1",
    "gh api repos/o/r/issues --field n=1",
    "gh api repos/o/r/issues --raw-field q=x",
    "gh api repos/o/r/issues --input body.json",
    "gh api repos/o/r/issues/1 -X DELETE",
    "gh api repos/o/r/issues -X GET -X POST -f q=x",
    "gh api repos/o/r/issues --method=GET --method=PATCH",
    "env GH_DEBUG=1 gh api -X POST repos/o/r/issues -f title=x",
]
GRAPHQL_READS = [
    "gh api graphql -f query='{ viewer { login } }'",
    "gh api graphql -F query='{ viewer { login } }'",
    "gh api graphql --raw-field query='{ viewer { login } }'",
    "gh api graphql --field query='{ viewer { login } }'",
    "gh api graphql --raw-field=query='{ viewer { login } }'",
    "gh api graphql -fquery='{ viewer { login } }'",
    "gh api /graphql -f query='{ viewer { login } }'",
    "gh api https://api.github.com/graphql -f query='{ viewer { login } }'",
    "gh api graphql?x=1 -f query='{ viewer { login } }'",
    "gh api -X GET graphql -f query='{ viewer { login } }'",
    "gh api -X POST graphql -f query='{ viewer { login } }'",
    "gh api graphql --method=DELETE -f query='{ viewer { login } }'",
    "env GH_DEBUG=1 gh api graphql -f query='{ viewer { login } }'",
    # Other fields, such as variables and operationName, and the other options change nothing.
    "gh api graphql -f query='{ viewer { login } }' -F owner=o -f operationName=x",
    "gh api graphql --paginate -H 'Accept: x' -f query='{ a }' --cache 1h -q .data",
    # An escaped \$ in double quotes reaches gh as a variable of the document.
    r'gh api graphql -f query="query(\$a: Int) { x(a: \$a) }"',
    # The two real calls that the hook once denied as writes.
    "gh api -X GET advisories -f ecosystem=npm -f affects=minimatch",
    (
        "gh api graphql -f query='query($owner: String!, $repo: String!, $pr: Int!) "
        "{ repository(owner: $owner, name: $repo) { pullRequest(number: $pr) "
        "{ reviewThreads(first: 50) { nodes { isResolved } } } } }' "
        "-F owner=o -F repo=r -F pr=7"
    ),
    # Placeholders in the variable fields: the document holds none, so gh sends it as written.
    (
        "gh api graphql -F owner='{owner}' -F name='{repo}' -f query='query($name: String!, "
        "$owner: String!) { repository(owner: $owner, name: $name) { releases(last: 3) "
        "{ nodes { tagName } } } }'"
    ),
    (
        "gh api graphql -F owner=:owner -F name=:repo -F ref=:branch -f query='query($owner: "
        "String!, $name: String!, $ref: String!) { repository(owner: $owner, name: $name) "
        "{ ref(qualifiedName: $ref) { name } } }'"
    ),
]
GRAPHQL_WRITES = [
    # A document in a file or on stdin is out of reach.
    "gh api graphql -F query=@q.graphql",
    "gh api graphql -f query=@q",
    "gh api graphql --field query=@-",
    "gh api graphql --raw-field=query=@q.graphql",
    # So is a request body in a file or on stdin, whatever else is given.
    "gh api graphql --input req.json",
    "gh api graphql --input=req.json",
    "gh api graphql --input -",
    "gh api graphql -f query='{ viewer { login } }' --input req.json",
    "gh api graphql -X GET -f query='{ viewer { login } }' --input=req.json",
    "gh api https://ghe.example.com/api/graphql --input mutation.json",
    "gh api -X GET https://ghe.example.com/api/graphql --input mutation.json",
    # No query field, or more than one.
    "gh api graphql",
    "gh api graphql -F owner=o -F repo=r",
    "gh api graphql -f Query='{ a }'",
    "gh api graphql -f 'query[a]={ a }'",
    "gh api graphql -f query",
    "gh api graphql -f query=",
    "gh api graphql -f query='{ a }' -f query='{ b }'",
    "gh api graphql -f query='{ a }' -F query='{ b }'",
    "gh api graphql --raw-field=query='{ a }' --field query='{ b }'",
    # The hook cannot know what a substitution prints.
    'gh api graphql -f query="$(cat q.graphql)"',
    'gh api graphql -f query="`cat q.graphql`"',
    'gh api graphql -f query="query { a(x: $(id)) }"',
    'gh api graphql -f query="query { a(x: `id`) }"',
    'gh api graphql -f "query={ $(echo a) }"',
    "gh api graphql -F query=$(cat q.graphql)",
    # A method that sends fields as parameters does not make a mutation a read.
    f"gh api -X GET graphql -f query='{MUTATION}'",
    f"env GH_DEBUG=1 gh api graphql -f query='{MUTATION}'",
    # A $ outside every pair of parentheses in a double-quoted document, as a token, in a
    # comment or in a string.
    'gh api graphql -f query="{ viewer { login $x } }"',
    'gh api graphql -f query="{ a } # $X"',
    'gh api graphql -f query="# $X\n{ a }"',
    'gh api graphql -f query="{ a \\"$X\\" }"',
    # A newline in $X ends the comment, so the mutation that $X holds and the visible selection set
    # make one mutation that gh sends, though the visible text alone is a query.
    (
        'X=$\'\\nmutation { mergePullRequest(input: {pullRequestId: "P"}) { ...F } } '
        "fragment F on MergePullRequestPayload'; "
        'gh api graphql -f query="# $X\n{ clientMutationId }"'
    ),
    # gh fills a placeholder in a -F value, so the document that it sends can differ from the one
    # that the hook reads. The hook keeps no record of which option gave a field, so a -f
    # document that holds a placeholder counts too.
    FILLED_LINE,
    graphql('{ repository(name: "{branch}") { id } }', field="-F"),
    graphql('{ repository(name: ":repo") { id } }', field="-F"),
    graphql('{ repository(name: "{owner}") { id } }'),
]
LINES = [
    *REST_READS,
    *REST_WRITES,
    *GRAPHQL_READS,
    *GRAPHQL_WRITES,
    *(graphql(document) for document in QUERIES.values()),
    *(graphql(document) for document in OTHER_DOCUMENTS.values()),
]
METHODS = ["POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS", "post", "Delete"]
FIELDS = ["", " -f title=x", " -F n=1", " --raw-field q=x", " --field q=x", " --input body.json"]
ENDPOINTS = [
    "graphql",
    "/graphql",
    "https://api.github.com/graphql",
    "graphql?x=1",
    "https://api.github.com/graphql?x=1",
    "/graphql/",
    "https://ghe.example.com/api/graphql",
    "https://ghe.example.com/graphql",
    "HTTPS://API.GITHUB.COM/graphql",
]
MUTATIONS = [
    "mergePullRequest",
    "enablePullRequestAutoMerge",
    "enqueuePullRequest",
    "mergeBranch",
    "updateRef",
    "updateRefs",
    "createCommitOnBranch",
]
GRAPHQL_MERGE = "G3: a GraphQL merge or ref mutation lands a change on the default branch"


@pytest.mark.parametrize("line", [*REST_READS, *GRAPHQL_READS])
def test_a_get_or_a_query_gives_no_decision_with_agent_identity_on(line: str) -> None:
    assert decided(line, ON) == (None, "")


@pytest.mark.parametrize("line", [*REST_WRITES, *GRAPHQL_WRITES])
def test_every_other_gh_api_call_is_denied_as_a_write(line: str) -> None:
    reason = denial(line)
    assert reason is not None
    assert reason.startswith("G8: ")


@pytest.mark.parametrize("fields", FIELDS)
@pytest.mark.parametrize("method", METHODS)
def test_a_method_other_than_get_writes_with_or_without_fields(method: str, fields: str) -> None:
    for option in (f"-X {method}", f"--method={method}", f"-X{method}"):
        reason = denial(f"gh api repos/o/r/issues {option}{fields}")
        assert reason is not None
        assert reason.startswith("G8: ")


@pytest.mark.parametrize("document", QUERIES.values(), ids=list(QUERIES))
def test_a_document_of_queries_alone_is_a_read(document: str) -> None:
    assert decided(graphql(document), ON) == (None, "")


@pytest.mark.parametrize("document", OTHER_DOCUMENTS.values(), ids=list(OTHER_DOCUMENTS))
def test_a_document_with_anything_else_is_a_write(document: str) -> None:
    reason = denial(graphql(document))
    assert reason is not None
    assert reason.startswith("G8: ")


@pytest.mark.parametrize("field", ["-F", "-f"])
@pytest.mark.parametrize("name", PLACEHOLDERS)
@pytest.mark.parametrize("place", PLACES.values(), ids=list(PLACES))
def test_a_document_that_holds_a_placeholder_that_gh_fills_is_a_write(
    place: str, name: str, field: str
) -> None:
    reason = denial(graphql(place.replace("<name>", name), field=field))
    assert reason is not None
    assert reason.startswith("G8: ")


@pytest.mark.parametrize("field", ["-F", "-f"])
@pytest.mark.parametrize("letter", LETTERS_OUTSIDE_ASCII.values(), ids=list(LETTERS_OUTSIDE_ASCII))
@pytest.mark.parametrize("name", [":owner", ":repo", ":branch"])
@pytest.mark.parametrize("place", TEXT_PLACES.values(), ids=list(TEXT_PLACES))
def test_a_placeholder_that_a_letter_outside_ascii_follows_at_once_is_a_write(
    place: str, name: str, letter: str, field: str
) -> None:
    reason = denial(graphql(place.replace("<name>", f"{name}{letter}"), field=field))
    assert reason is not None
    assert reason.startswith("G8: ")


@pytest.mark.parametrize("letter", LETTERS_OUTSIDE_ASCII.values(), ids=list(LETTERS_OUTSIDE_ASCII))
@pytest.mark.parametrize("place", TEXT_PLACES.values(), ids=list(TEXT_PLACES))
def test_a_letter_outside_ascii_after_a_name_that_holds_no_colon_is_a_read(
    place: str, letter: str
) -> None:
    assert decided(graphql(place.replace("<name>", f"repo{letter}")), ON) == (None, "")


def test_filling_a_placeholder_can_turn_a_document_of_queries_into_a_write() -> None:
    plain = FILLED_DOCUMENT.replace("{repo}", "r")
    sent = FILLED_DOCUMENT.replace("{repo}", CLOSING_REPOSITORY.partition("/")[2])
    assert decided(graphql(plain), ON) == (None, "")
    reason = denial(graphql(sent))
    assert reason is not None
    assert reason.startswith("G8: ")


@pytest.mark.parametrize("method", ["", "-X GET", "-X POST", "--method=PUT", "-X delete"])
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_the_endpoint_spelling_and_the_method_leave_the_document_to_decide(
    endpoint: str, method: str
) -> None:
    options = method.split()
    assert decided(graphql(QUERIES["anonymous"], *options, endpoint=endpoint), ON) == (None, "")
    reason = denial(graphql(MUTATION, *options, endpoint=endpoint))
    assert reason is not None
    assert reason.startswith("G8: ")


@pytest.mark.parametrize("settings", [OFF, ON], ids=["identity-off", "identity-on"])
@pytest.mark.parametrize(
    "document",
    [
        "mutation { <name>(input: {}) { clientMutationId } }",
        "query { a } mutation { <name> }",
        "query { <name> }",
    ],
    ids=["a mutation", "a mutation beside a query", "a query that only names it"],
)
@pytest.mark.parametrize("name", MUTATIONS)
def test_a_document_that_names_a_merge_or_ref_mutation_is_still_denied_as_a_merge_first(
    name: str, document: str, settings: HookSettings
) -> None:
    reason = denial(graphql(document.replace("<name>", name)), settings)
    assert reason is not None
    assert reason.startswith(GRAPHQL_MERGE)


@pytest.mark.parametrize("line", LINES)
def test_without_agent_identity_or_settings_no_gh_api_call_gets_a_decision(line: str) -> None:
    assert decided(line, OFF) == (None, "")
    assert decided(line, None) == (None, "")


@pytest.mark.parametrize("line", [graphql(MUTATION), "gh api repos/o/r/issues -X POST -f x=y"])
@pytest.mark.parametrize("role", ["worker", "reviewer"])
def test_a_gh_api_write_through_devctl_as_is_not_denied(role: str, line: str) -> None:
    assert decided(f"./devctl as {role} {line}", ON) == (None, "")


def test_the_denial_of_a_graphql_write_names_the_way_through() -> None:
    assert decided(graphql(MUTATION), ON) == (
        "deny",
        "G8: Agent identity is on, so an App makes gh writes; run ./devctl as <role> gh api "
        "graphql -f 'query=mutation { addComment(input: {}) { clientMutationId } }'",
    )


@pytest.mark.parametrize(
    ("words", "call"),
    [
        (["repos/o/r"], ApiCall("GET", "repos/o/r", (), False)),
        (["repos/o/r", "-f", "a=b"], ApiCall("POST", "repos/o/r", ("a=b",), False)),
        (["repos/o/r", "--input", "x.json"], ApiCall("POST", "repos/o/r", (), True)),
        (["repos/o/r", "--input=x.json"], ApiCall("POST", "repos/o/r", (), True)),
        (
            ["repos/o/r", "-X", "get", "-F", "a=b", "--input=x.json"],
            ApiCall("GET", "repos/o/r", ("a=b",), True),
        ),
        (["-X", "POST", "-XPATCH", "repos/o/r"], ApiCall("PATCH", "repos/o/r", (), False)),
        (["--method=GET", "-X", "put", "r", "-f", "a"], ApiCall("PUT", "r", ("a",), False)),
        (["https://api.github.com/graphql?x=1"], ApiCall("GET", "graphql", (), False)),
        (["/graphql/", "-f", "query=a=b"], ApiCall("POST", "graphql", ("query=a=b",), False)),
    ],
)
def test_parse_api_reads_the_method_the_fields_and_whether_input_was_given(
    words: list[str], call: ApiCall
) -> None:
    assert parse_api(words) == call
