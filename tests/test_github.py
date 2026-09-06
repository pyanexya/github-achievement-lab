from __future__ import annotations

import json
import unittest

import requests

from achievement_unlocker.config import Config
from achievement_unlocker.github import GitHubClient, GitHubError


def response(status: int, body: dict[str, object], headers: dict[str, str] | None = None) -> requests.Response:
    item = requests.Response()
    item.status_code = status
    item._content = json.dumps(body).encode("utf-8")
    item.headers.update(headers or {})
    item.url = "https://api.github.com/test"
    return item


class FakeSession:
    def __init__(self, responses: list[requests.Response]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.calls = 0

    def request(self, *_args: object, **_kwargs: object) -> requests.Response:
        item = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return item


class GitHubClientTests(unittest.TestCase):
    def test_retries_are_bounded(self) -> None:
        session = FakeSession([response(500, {"message": "temporary"})])
        client = GitHubClient(
            Config(max_retries=2), "token", session=session, sleeper=lambda _delay: None
        )
        with self.assertRaises(GitHubError):
            client.request("GET", "/test")
        self.assertEqual(session.calls, 3)

    def test_token_is_redacted_from_errors(self) -> None:
        secret = "sensitive-test-token"
        session = FakeSession([response(400, {"message": secret})])
        client = GitHubClient(Config(), secret, session=session)
        with self.assertRaises(GitHubError) as raised:
            client.request("GET", "/test")
        self.assertNotIn(secret, str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
