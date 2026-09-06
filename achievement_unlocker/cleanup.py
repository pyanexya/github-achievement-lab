from __future__ import annotations

from dataclasses import dataclass

from .github import GitHubClient
from .state import State


@dataclass
class CleanupResult:
    closed_pull_requests: int = 0
    closed_issues: int = 0
    deleted_branches: int = 0


def cleanup(client: GitHubClient, state: State) -> CleanupResult:
    result = CleanupResult()
    for pr in client.list_pull_requests(state="open"):
        branch = str(pr.get("head", {}).get("ref", ""))
        if not branch.startswith("achievement/"):
            continue
        client.update_pull_request(int(pr["number"]), state="closed")
        result.closed_pull_requests += 1

    for issue in client.list_issues(state="open"):
        if not str(issue.get("title", "")).startswith("achievement("):
            continue
        client.close_issue(int(issue["number"]))
        result.closed_issues += 1

    for pr in client.list_pull_requests(state="all"):
        branch = str(pr.get("head", {}).get("ref", ""))
        if branch.startswith("achievement/") and client.delete_branch(branch):
            result.deleted_branches += 1

    state.clear()
    return result

