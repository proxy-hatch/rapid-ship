"""Offline: GitHubApi limits, empty replies and JSON narrowing against the simulated GitHub."""

import secrets

import pytest

import devctl.github.api as api_module
from devctl.github.api import GitHubApi, GitHubError, json_list, json_object
from github_fakes import FakeGitHub


def test_an_empty_reply_is_none(github: FakeGitHub) -> None:
    github.route("DELETE", "/repos/o/r/things/1", lambda call, _: (204, None))
    assert GitHubApi("t", base_url=github.url).request("DELETE", "/repos/o/r/things/1") is None


def test_a_reply_over_the_size_cap_is_refused(
    github: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_module, "MAX_RESPONSE_BYTES", 10)
    github.route("GET", "/big", lambda call, _: (200, ["x" * 50]))
    with pytest.raises(GitHubError, match="response is over 10 bytes") as caught:
        GitHubApi("t", base_url=github.url).request("GET", "/big")
    assert caught.value.status == 200


def test_a_message_that_straddles_the_cut_hides_the_token_before_cutting(
    github: FakeGitHub,
) -> None:
    secret = secrets.token_urlsafe(48)
    github.route("GET", "/x", lambda call, _: (422, {"message": "y" * 290 + secret}))
    with pytest.raises(GitHubError) as caught:
        GitHubApi(secret, base_url=github.url).request("GET", "/x")
    assert str(caught.value).endswith("y[token]")
    assert secret[:6] not in str(caught.value)


def test_the_repr_names_the_host_and_never_the_token() -> None:
    secret = secrets.token_urlsafe(48)
    assert repr(GitHubApi(secret)) == "GitHubApi(api.github.com)"


def test_json_helpers_return_the_value_or_raise_without_a_status() -> None:
    assert json_object({"a": 1}, "the reply") == {"a": 1}
    assert json_list([1], "the reply") == [1]
    with pytest.raises(GitHubError, match="the reply is not a JSON object") as bad_object:
        json_object([], "the reply")
    with pytest.raises(GitHubError, match="the reply is not a JSON list") as bad_list:
        json_list({}, "the reply")
    assert bad_object.value.status is None
    assert bad_list.value.status is None
