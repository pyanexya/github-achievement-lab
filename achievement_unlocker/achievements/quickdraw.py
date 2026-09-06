from __future__ import annotations

from ..github import GitHubClient
from ..models import ActionPlan, ExecutionResult
from ..operations import run_quickdraw
from ..planner import one_shot_plan
from ..state import State


def plan(client: GitHubClient) -> ActionPlan:
    from ..operations import _parse_time

    done = False
    for issue in client.list_issues(state="all"):
        if not str(issue.get("title", "")).startswith(
            "achievement(quickdraw): controlled close"
        ):
            continue
        if issue.get("state") == "closed" and issue.get("closed_at"):
            elapsed = (
                _parse_time(issue["closed_at"]) - _parse_time(issue["created_at"])
            ).total_seconds()
            done = done or elapsed <= 300
    return one_shot_plan("quickdraw", done)


def execute(client: GitHubClient, state: State) -> ExecutionResult:
    return run_quickdraw(client, state)
