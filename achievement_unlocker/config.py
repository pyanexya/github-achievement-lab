from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    pass


def _token_from_gh() -> str | None:
    if not shutil.which("gh"):
        return None
    completed = subprocess.run(
        ["gh", "auth", "token"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return completed.stdout.strip()
    return None


def resolve_token() -> str:
    """Resolve credentials without ever logging or persisting the secret."""
    token = _token_from_gh() or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ConfigurationError(
            "No GitHub credential found. Authenticate gh, or set GH_TOKEN/GITHUB_TOKEN."
        )
    return token


@dataclass(frozen=True)
class Config:
    owner: str = "pyanexya"
    repository: str = "github-achievement-lab"
    base_branch: str = "main"
    api_url: str = "https://api.github.com"
    timeout_seconds: int = 30
    max_retries: int = 4
    max_automatic_actions: int = 20

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            owner=os.getenv("GITHUB_OWNER", "pyanexya"),
            repository=os.getenv("GITHUB_REPOSITORY", "github-achievement-lab"),
            base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
            api_url=os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/"),
            timeout_seconds=int(os.getenv("GITHUB_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("GITHUB_MAX_RETRIES", "4")),
            max_automatic_actions=int(os.getenv("GITHUB_MAX_AUTOMATIC_ACTIONS", "20")),
        )

    def validate_target(self) -> None:
        expected = "pyanexya/github-achievement-lab"
        if self.full_name.casefold() != expected.casefold():
            raise ConfigurationError(
                f"Refusing repository {self.full_name!r}; the only allowed target is {expected}."
            )

