from __future__ import annotations

from ..github import GitHubClient
from ..models import ActionPlan, ExecutionResult
from ..operations import run_pr_operation
from ..planner import pull_shark_plan
from ..state import State


def plan(
    client: GitHubClient, *, target: str = "base", count: int | None = None
) -> ActionPlan:
    return pull_shark_plan(client.global_public_merged_pr_count(), target=target, count=count)


def execute(client: GitHubClient, state: State, action_plan: ActionPlan) -> list[ExecutionResult]:
    current = client.merged_pr_count()
    return [
        run_pr_operation(
            client,
            state,
            achievement="pull-shark",
            serial=current + offset,
        )
        for offset in range(1, action_plan.actions + 1)
    ]
