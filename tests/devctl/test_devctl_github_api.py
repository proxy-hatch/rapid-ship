"""Offline: GitHubApi against the simulated GitHub in github_fakes. No network."""

import secrets

import pytest

from devctl.github.api import API_VERSION, GitHubApi, GitHubError
from github_fakes import FakeGitHub


def test_request_sends_bearer_token_version_and_json(github: FakeGitHub) -> None:
    secret = secrets.token_urlsafe(48)
    github.route("POST", "/repos/o/r/things", lambda call, _: (201, {"echo": call.body}))
    api = GitHubApi(secret, base_url=github.url)
    assert api.request("POST", "/repos/o/r/things", {"a": 1}) == {"echo": {"a": 1}}
    headers = github.calls[-1].headers
    assert headers["Authorization"] == f"Bearer {secret}"
    assert headers["X-GitHub-Api-Version"] == API_VERSION
    assert headers["Accept"] == "application/vnd.github+json"


def test_error_carries_status_and_message_but_never_the_token(github: FakeGitHub) -> None:
    secret = secrets.token_urlsafe(48)
    github.route("GET", "/repos/o/r", lambda call, _: (404, {"message": f"Not Found {secret}"}))
    with pytest.raises(GitHubError) as caught:
        GitHubApi(secret, base_url=github.url).request("GET", "/repos/o/r")
    assert caught.value.status == 404
    assert "Not Found" in str(caught.value)
    assert secret not in str(caught.value)


def test_redirects_are_not_followed(github: FakeGitHub) -> None:
    other = FakeGitHub()
    try:
        github.route(
            "GET", "/repos/o/r", lambda call, _: (301, None, {"Location": f"{other.url}/repos/o/r"})
        )
        with pytest.raises(GitHubError) as caught:
            GitHubApi("t", base_url=github.url).request("GET", "/repos/o/r")
        assert caught.value.status == 301
        assert other.calls == []
    finally:
        other.close()


def test_plain_http_is_refused_except_on_loopback() -> None:
    with pytest.raises(ValueError, match="https"):
        GitHubApi("t", base_url="http://api.example.com")


def test_unreachable_server_raises_without_the_token() -> None:
    secret = secrets.token_urlsafe(48)
    with pytest.raises(GitHubError) as caught:
        GitHubApi(secret, base_url="http://127.0.0.1:9").request("GET", "/x")
    assert caught.value.status is None
    assert secret not in str(caught.value)
