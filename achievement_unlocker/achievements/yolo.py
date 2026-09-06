from __future__ import annotations

from ..github import GitHubClient
from ..models import ActionPlan, ExecutionResult
from ..operations import run_pr_operation
from ..planner import one_shot_plan
from ..state import State


def plan(client: GitHubClient) -> ActionPlan:
    done = any(
        pr.get("merged_at") and pr.get("head", {}).get("ref") == "achievement/yolo/0001"
        for pr in client.list_pull_requests(state="all")
    )
    return one_shot_plan("yolo", done)


def execute(client: GitHubClient, state: State) -> ExecutionResult:
    return run_pr_operation(client, state, achievement="yolo", serial=1)

