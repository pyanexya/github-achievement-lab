from __future__ import annotations

import os

from ..github import GitHubClient
from ..models import ActionPlan, ExecutionResult
from ..operations import run_pr_operation
from ..planner import pair_plan
from ..state import State


class MissingCoauthor(RuntimeError):
    pass


def coauthor_from_env() -> tuple[str, str]:
    name = os.getenv("GITHUB_COAUTHOR_NAME", "").strip()
    email = os.getenv("GITHUB_COAUTHOR_EMAIL", "").strip()
    if not name or not email:
        raise MissingCoauthor(
            "Set both GITHUB_COAUTHOR_NAME and GITHUB_COAUTHOR_EMAIL for a real GitHub user."
        )
    return name, email


def validate_coauthor(client: GitHubClient, coauthor: tuple[str, str]) -> str:
    name, email = coauthor
    if name.casefold() == client.config.owner.casefold():
        raise MissingCoauthor("The co-author must be a different real GitHub user.")
    user = client.get_user(name)
    public_email = (user.get("email") or "").casefold()
    supplied = email.casefold()
    if public_email:
        if public_email != supplied:
            raise MissingCoauthor(
                f"The supplied email does not match {name}'s public GitHub email."
            )
        return "verified-public-email"
    if supplied.endswith("@users.noreply.github.com") and name.casefold() in supplied:
        return "plausible-noreply-email"
    return "unverifiable-private-email"


def _known_merged(client: GitHubClient) -> int:
    return sum(
        1
        for pr in client.list_pull_requests(state="closed")
        if pr.get("merged_at")
        and str(pr.get("head", {}).get("ref", "")).startswith(
            "achievement/pair-extraordinaire/"
        )
    )


def plan(client: GitHubClient, *, target: str = "base") -> ActionPlan:
    coauthor_from_env()
    return pair_plan(_known_merged(client), target=target)


def execute(
    client: GitHubClient, state: State, action_plan: ActionPlan
) -> list[ExecutionResult]:
    coauthor = coauthor_from_env()
    verification = validate_coauthor(client, coauthor)
    current = _known_merged(client)
    results = [
        run_pr_operation(
            client,
            state,
            achievement="pair-extraordinaire",
            serial=current + offset,
            coauthor=coauthor,
        )
        for offset in range(1, action_plan.actions + 1)
    ]
    for result in results:
        result.detail = f"Co-author validation: {verification}."
    return results

