from __future__ import annotations

import random
import time
from collections.abc import Iterable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, ClassVar
from urllib.parse import quote

import requests

from .config import Config


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class RepositoryState:
    full_name: str
    visibility: str
    default_branch: str


class GitHubClient:
    RETRYABLE: ClassVar[frozenset[int]] = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        config: Config,
        token: str,
        *,
        session: requests.Session | None = None,
        sleeper=time.sleep,
    ) -> None:
        config.validate_target()
        self.config = config
        self._token = token
        self._session = session or requests.Session()
        self._sleep = sleeper
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "safe-github-achievement-unlocker/1.0",
            }
        )

    def _safe_body(self, response: requests.Response) -> str:
        body = response.text[:2000]
        if self._token:
            body = body.replace(self._token, "[REDACTED]")
        return body

    @staticmethod
    def _retry_delay(response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(retry_after)
                    return max(0.0, parsed.timestamp() - time.time())
                except (TypeError, ValueError):
                    pass
        if response.headers.get("X-RateLimit-Remaining") == "0":
            reset = response.headers.get("X-RateLimit-Reset")
            if reset and reset.isdigit():
                return max(0.0, float(reset) - time.time()) + 1.0
        return min(30.0, (2**attempt) + random.random())

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: Iterable[int] = (200,),
        **kwargs: Any,
    ) -> requests.Response:
        url = path if path.startswith("http") else f"{self.config.api_url}{path}"
        expected_set = set(expected)
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._session.request(
                    method, url, timeout=self.config.timeout_seconds, **kwargs
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                self._sleep(min(30.0, 2**attempt))
                continue

            if response.status_code in expected_set:
                return response

            secondary_limit = (
                response.status_code == 403
                and "secondary rate limit" in response.text.casefold()
            )
            exhausted = (
                response.status_code == 403
                and response.headers.get("X-RateLimit-Remaining") == "0"
            )
            if (
                response.status_code in self.RETRYABLE or secondary_limit or exhausted
            ) and attempt < self.config.max_retries:
                self._sleep(self._retry_delay(response, attempt))
                continue

            raise GitHubError(
                f"GitHub API {method} {path} failed with HTTP {response.status_code}: "
                f"{self._safe_body(response)}",
                status=response.status_code,
            )

        raise GitHubError(
            f"GitHub API {method} {path} failed after "
            f"{self.config.max_retries + 1} attempts: {last_error}"
        )

    def json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.request(method, path, **kwargs)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def authenticated_login(self) -> str:
        return str(self.json("GET", "/user")["login"])

    def ensure_identity(self) -> None:
        login = self.authenticated_login()
        if login.casefold() != self.config.owner.casefold():
            raise GitHubError(
                f"Authenticated as {login!r}, expected {self.config.owner!r}."
            )

    def get_repository(self) -> RepositoryState | None:
        response = self.request(
            "GET",
            f"/repos/{self.config.full_name}",
            expected=(200, 404),
        )
        if response.status_code == 404:
            return None
        data = response.json()
        return RepositoryState(
            full_name=data["full_name"],
            visibility=data.get("visibility", "private" if data.get("private") else "public"),
            default_branch=data["default_branch"],
        )

    def ensure_lab(self, *, create: bool) -> RepositoryState:
        self.ensure_identity()
        repo = self.get_repository()
        if repo is None:
            if not create:
                raise GitHubError(
                    f"Repository {self.config.full_name} does not exist. Run `python cli.py init`."
                )
            data = self.json(
                "POST",
                "/user/repos",
                expected=(201,),
                json={
                    "name": self.config.repository,
                    "description": "Isolated lab for bounded GitHub achievement experiments.",
                    "private": False,
                    "auto_init": True,
                    "has_issues": True,
                },
            )
            repo = RepositoryState(
                full_name=data["full_name"],
                visibility=data.get("visibility", "public"),
                default_branch=data["default_branch"],
            )
        if repo.visibility != "public":
            raise GitHubError(f"Repository {repo.full_name} must be public.")
        if repo.full_name.casefold() != self.config.full_name.casefold():
            raise GitHubError(f"Unexpected repository returned: {repo.full_name}")
        if repo.default_branch != self.config.base_branch:
            raise GitHubError(
                f"Expected default branch {self.config.base_branch!r}, got {repo.default_branch!r}."
            )
        return repo

    def get_ref_sha(self, branch: str) -> str | None:
        encoded = quote(branch, safe="")
        try:
            data = self.json("GET", f"/repos/{self.config.full_name}/git/ref/heads/{encoded}")
        except GitHubError as exc:
            if exc.status == 404:
                return None
            raise
        return str(data["object"]["sha"])

    def create_branch(self, branch: str, from_branch: str | None = None) -> bool:
        if self.get_ref_sha(branch):
            return False
        base = from_branch or self.config.base_branch
        base_sha = self.get_ref_sha(base)
        if not base_sha:
            raise GitHubError(f"Base branch {base!r} does not exist.")
        self.json(
            "POST",
            f"/repos/{self.config.full_name}/git/refs",
            expected=(201,),
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        return True

    def delete_branch(self, branch: str) -> bool:
        if not self.get_ref_sha(branch):
            return False
        encoded = quote(branch, safe="")
        self.request(
            "DELETE",
            f"/repos/{self.config.full_name}/git/refs/heads/{encoded}",
            expected=(204,),
        )
        return True

    def get_content(self, path: str, ref: str) -> dict[str, Any] | None:
        encoded_path = quote(path, safe="/")
        try:
            return self.json(
                "GET",
                f"/repos/{self.config.full_name}/contents/{encoded_path}",
                params={"ref": ref},
            )
        except GitHubError as exc:
            if exc.status == 404:
                return None
            raise

    def create_text_file(
        self, path: str, content: str, branch: str, message: str
    ) -> bool:
        if self.get_content(path, branch) is not None:
            return False
        import base64

        encoded_path = quote(path, safe="/")
        self.json(
            "PUT",
            f"/repos/{self.config.full_name}/contents/{encoded_path}",
            expected=(201,),
            json={
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            },
        )
        return True

    def list_pull_requests(self, *, state: str = "all") -> list[dict[str, Any]]:
        data = self.json(
            "GET",
            f"/repos/{self.config.full_name}/pulls",
            params={"state": state, "per_page": 100, "sort": "created", "direction": "asc"},
        )
        return list(data)

    def find_pull_request(self, branch: str) -> dict[str, Any] | None:
        for pr in self.list_pull_requests(state="all"):
            if pr.get("head", {}).get("ref") == branch:
                return pr
        return None

    def create_pull_request(self, branch: str, title: str, body: str) -> dict[str, Any]:
        return self.json(
            "POST",
            f"/repos/{self.config.full_name}/pulls",
            expected=(201,),
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": self.config.base_branch,
            },
        )

    def merge_pull_request(self, number: int, head_sha: str) -> dict[str, Any]:
        return self.json(
            "PUT",
            f"/repos/{self.config.full_name}/pulls/{number}/merge",
            json={"sha": head_sha, "merge_method": "merge"},
        )

    def update_pull_request(self, number: int, *, state: str) -> dict[str, Any]:
        return self.json(
            "PATCH",
            f"/repos/{self.config.full_name}/pulls/{number}",
            json={"state": state},
        )

    def list_issues(self, *, state: str = "all") -> list[dict[str, Any]]:
        data = self.json(
            "GET",
            f"/repos/{self.config.full_name}/issues",
            params={"state": state, "per_page": 100, "sort": "created", "direction": "asc"},
        )
        return [item for item in data if "pull_request" not in item]

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        return self.json(
            "POST",
            f"/repos/{self.config.full_name}/issues",
            expected=(201,),
            json={"title": title, "body": body},
        )

    def close_issue(self, number: int) -> dict[str, Any]:
        return self.json(
            "PATCH",
            f"/repos/{self.config.full_name}/issues/{number}",
            json={"state": "closed", "state_reason": "completed"},
        )

    def merged_pr_count(self) -> int:
        return sum(1 for pr in self.list_pull_requests(state="closed") if pr.get("merged_at"))

    def global_public_merged_pr_count(self) -> int:
        data = self.json(
            "GET",
            "/search/issues",
            params={
                "q": f"author:{self.config.owner} is:pr is:merged is:public",
                "per_page": 1,
            },
        )
        return int(data.get("total_count", 0))

    def max_owned_repository_stars(self) -> int:
        page = 1
        maximum = 0
        while page <= 10:
            items = self.json(
                "GET",
                f"/users/{self.config.owner}/repos",
                params={"type": "owner", "per_page": 100, "page": page},
            )
            if not items:
                break
            maximum = max(maximum, *(int(item.get("stargazers_count", 0)) for item in items))
            if len(items) < 100:
                break
            page += 1
        return maximum

    def get_user(self, login: str) -> dict[str, Any]:
        return self.json("GET", f"/users/{quote(login, safe='')}")
