from __future__ import annotations

from datetime import UTC, datetime

from .github import GitHubClient, GitHubError
from .models import ExecutionResult
from .state import State


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def run_pr_operation(
    client: GitHubClient,
    state: State,
    *,
    achievement: str,
    serial: int,
    coauthor: tuple[str, str] | None = None,
) -> ExecutionResult:
    branch = f"achievement/{achievement}/{serial:04d}"
    title_name = achievement.replace("-", " ").title()
    result = ExecutionResult(achievement=achievement, status="completed")

    if client.create_branch(branch):
        result.created_branches += 1

    progress_path = f".achievement-progress/{achievement}/{serial:04d}.txt"
    message = f"chore(achievement): {achievement} progress {serial}"
    if coauthor:
        message += f"\n\nCo-authored-by: {coauthor[0]} <{coauthor[1]}>"
    content = (
        f"Achievement: {title_name}\n"
        f"Sequence: {serial}\n"
        f"Generated: {datetime.now(UTC).isoformat()}\n"
    )
    if client.create_text_file(progress_path, content, branch, message):
        result.created_commits += 1

    pr = client.find_pull_request(branch)
    if pr is None:
        pr = client.create_pull_request(
            branch,
            f"chore: {title_name} progress {serial}",
            "Controlled achievement-lab operation. No production code is affected.",
        )
        result.created_pull_requests += 1
    number = int(pr["number"])
    result.urls.append(str(pr["html_url"]))
    state.record(
        f"{achievement}:{serial:04d}", branch=branch, pr=number, status="open"
    )

    if not pr.get("merged_at"):
        latest_head = client.get_ref_sha(branch)
        if not latest_head:
            raise GitHubError(f"Branch {branch} disappeared before merge.")
        merged = client.merge_pull_request(number, latest_head)
        if not merged.get("merged"):
            raise GitHubError(f"PR #{number} was not merged: {merged.get('message', 'unknown')}")
        result.merged_pull_requests += 1

    if client.delete_branch(branch):
        result.deleted_branches += 1
    state.record(
        f"{achievement}:{serial:04d}", branch=branch, pr=number, status="merged"
    )
    return result


def run_quickdraw(client: GitHubClient, state: State) -> ExecutionResult:
    marker_prefix = "achievement(quickdraw): controlled close"
    result = ExecutionResult(achievement="quickdraw", status="completed")
    previous = [
        issue
        for issue in client.list_issues(state="all")
        if str(issue.get("title", "")).startswith(marker_prefix)
    ]
    for issue in previous:
        if issue.get("state") != "closed" or not issue.get("closed_at"):
            continue
        elapsed = (_parse_time(issue["closed_at"]) - _parse_time(issue["created_at"])).total_seconds()
        if elapsed <= 300:
            result.status = "already_completed"
            result.detail = f"Issue #{issue['number']} was closed after {elapsed:.1f}s."
            result.urls.append(str(issue["html_url"]))
            return result

    existing = next((issue for issue in previous if issue.get("state") == "open"), None)
    if existing is None:
        suffix = "" if not previous else f" {len(previous) + 1}"
        existing = client.create_issue(
            marker_prefix + suffix,
            "Controlled Quickdraw experiment in the isolated achievement laboratory.",
        )
        result.created_issues += 1
    number = int(existing["number"])
    result.urls.append(str(existing["html_url"]))
    if existing.get("state") != "closed":
        existing = client.close_issue(number)
    created = _parse_time(existing["created_at"])
    closed = _parse_time(existing["closed_at"])
    elapsed = (closed - created).total_seconds()
    if elapsed > 300:
        result.status = "not_eligible"
        result.detail = f"Issue #{number} closed after {elapsed:.1f}s; no duplicate was created."
    else:
        result.detail = f"Issue #{number} closed after {elapsed:.1f}s."
    state.record("quickdraw", issue=number, status=result.status, elapsed_seconds=elapsed)
    return result
