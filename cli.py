from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable

import requests

from achievement_unlocker.achievements import (
    pair_extraordinaire,
    pull_shark,
    quickdraw,
    yolo,
)
from achievement_unlocker.catalog import ACHIEVEMENTS, BY_SLUG
from achievement_unlocker.cleanup import cleanup
from achievement_unlocker.config import Config, ConfigurationError, resolve_token
from achievement_unlocker.github import GitHubClient, GitHubError
from achievement_unlocker.models import ActionPlan, ExecutionResult
from achievement_unlocker.planner import (
    PlanningError,
    enforce_volume,
    one_shot_plan,
    pull_shark_plan,
)
from achievement_unlocker.profile import ProfileAchievements, inspect_public_profile
from achievement_unlocker.state import State


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safe, bounded automation for GitHub achievement experiments."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status", help="Inspect current visible achievements and progress.")
    subcommands.add_parser("init", help="Create the isolated public laboratory repository.")
    subcommands.add_parser("cleanup", help="Close unfinished lab activity and remove temp branches.")

    unlock = subcommands.add_parser("unlock", help="Plan or execute an achievement operation.")
    unlock.add_argument(
        "achievement",
        choices=("quickdraw", "yolo", "pull-shark", "pair-extraordinaire", "all"),
    )
    unlock.add_argument(
        "--target", choices=("base", "bronze", "silver", "gold"), default="base"
    )
    unlock.add_argument("--count", type=int, help="Exact Pull Shark PR count to create.")
    unlock.add_argument("--dry-run", action="store_true", help="Print a plan without mutations.")
    unlock.add_argument(
        "--allow-high-volume",
        action="store_true",
        help="Allow a reviewed plan to exceed the default safety cap.",
    )
    return parser


def make_client() -> GitHubClient:
    config = Config.from_env()
    config.validate_target()
    return GitHubClient(config, resolve_token())


def safe_profile(owner: str) -> ProfileAchievements:
    try:
        return inspect_public_profile(owner)
    except requests.RequestException as exc:
        print(f"[!] Public profile inspection unavailable: {exc}")
        return ProfileAchievements(frozenset(), True)


def print_plan(plan: ActionPlan) -> None:
    print(f"\n{BY_SLUG[plan.achievement].name} -> {plan.target}")
    print(f"  actions: {plan.actions}")
    print(f"  branches: {plan.branches}")
    print(f"  commits: {plan.commits}")
    print(f"  pull requests: {plan.pull_requests}")
    print(f"  issues: {plan.issues}")
    for note in plan.notes:
        print(f"  note: {note}")


def print_results(results: Iterable[ExecutionResult]) -> None:
    totals = ExecutionResult(achievement="summary", status="completed")
    print("\nExecution summary")
    for result in results:
        name = BY_SLUG[result.achievement].name
        print(f"[✓] {name}: {result.status}{' — ' + result.detail if result.detail else ''}")
        for url in result.urls:
            print(f"    {url}")
        totals.created_branches += result.created_branches
        totals.created_commits += result.created_commits
        totals.created_pull_requests += result.created_pull_requests
        totals.merged_pull_requests += result.merged_pull_requests
        totals.created_issues += result.created_issues
        totals.deleted_branches += result.deleted_branches
    print(
        "Totals: "
        f"branches created={totals.created_branches}, "
        f"commits={totals.created_commits}, "
        f"PRs created={totals.created_pull_requests}, "
        f"PRs merged={totals.merged_pull_requests}, "
        f"issues created={totals.created_issues}, "
        f"branches deleted={totals.deleted_branches}"
    )


def command_status(client: GitHubClient) -> int:
    client.ensure_identity()
    repo = client.get_repository()
    profile = safe_profile(client.config.owner)
    public_prs = client.global_public_merged_pr_count()
    max_stars = client.max_owned_repository_stars()

    print("GitHub Achievement Unlocker")
    print(f"Account: {client.config.owner}")
    print(f"Repository: {client.config.full_name} ({'missing' if repo is None else repo.visibility})")
    print(f"Profile visibility uncertain: {'yes' if profile.visibility_uncertain else 'no'}")
    for item in ACHIEVEMENTS:
        unlocked = item.slug in profile.slugs
        progress = "unknown"
        next_threshold = "n/a"
        if item.slug == "pull-shark":
            progress = str(public_prs)
            next_threshold = next(
                (f"{tier}:{value}" for tier, value in item.thresholds.items() if value > public_prs),
                "gold complete",
            )
        elif item.slug == "starstruck":
            progress = f"max repo stars={max_stars}"
            next_threshold = next(
                (f"{tier}:{value}" for tier, value in item.thresholds.items() if value > max_stars),
                "gold complete",
            )
        elif unlocked:
            progress = "badge visible"
        marker = "✓" if unlocked else "-"
        print(
            f"[{marker}] {item.name:<27} {item.classification.value:<30} "
            f"progress={progress}; next={next_threshold}"
        )
    if profile.visibility_uncertain:
        print("\nNote: no badges are public; they may be absent or hidden in profile settings.")
    return 0


def command_init(client: GitHubClient) -> int:
    repo = client.ensure_lab(create=True)
    print(f"Initialized: https://github.com/{repo.full_name}")
    print(f"Visibility: {repo.visibility}; default branch: {repo.default_branch}")
    return 0


def _single_plan(client: GitHubClient, args: argparse.Namespace) -> ActionPlan:
    repo_exists = client.get_repository() is not None
    if args.achievement == "quickdraw":
        return quickdraw.plan(client) if repo_exists else one_shot_plan("quickdraw", False)
    if args.achievement == "yolo":
        return yolo.plan(client) if repo_exists else one_shot_plan("yolo", False)
    if args.achievement == "pull-shark":
        if args.count is not None and args.target != "base":
            raise PlanningError("Use either --count or --target, not both.")
        current = client.global_public_merged_pr_count()
        return pull_shark_plan(current, target=args.target, count=args.count)
    if args.achievement == "pair-extraordinaire":
        if args.count is not None:
            raise PlanningError("--count is supported only for pull-shark.")
        if repo_exists:
            return pair_extraordinaire.plan(client, target=args.target)
        pair_extraordinaire.coauthor_from_env()
        from achievement_unlocker.planner import pair_plan

        return pair_plan(0, target=args.target)
    raise PlanningError(f"Unsupported achievement: {args.achievement}")


def _plan_all(client: GitHubClient) -> tuple[list[ActionPlan], str | None]:
    repo_exists = client.get_repository() is not None
    profile = safe_profile(client.config.owner)
    quick_plan = (
        one_shot_plan("quickdraw", "quickdraw" in profile.slugs)
        if not repo_exists
        else quickdraw.plan(client)
    )
    yolo_plan = (
        one_shot_plan("yolo", "yolo" in profile.slugs)
        if not repo_exists
        else yolo.plan(client)
    )
    current_public = client.global_public_merged_pr_count()
    projected_public = current_public + yolo_plan.pull_requests
    shark_plan = pull_shark_plan(projected_public, target="base")
    plans = [quick_plan, yolo_plan, shark_plan]
    blocker = None
    try:
        if repo_exists:
            plans.append(pair_extraordinaire.plan(client, target="base"))
        else:
            pair_extraordinaire.coauthor_from_env()
            from achievement_unlocker.planner import pair_plan

            plans.append(pair_plan(0, target="base"))
    except pair_extraordinaire.MissingCoauthor as exc:
        blocker = str(exc)
    return plans, blocker


def command_unlock(client: GitHubClient, args: argparse.Namespace) -> int:
    client.ensure_identity()
    if args.achievement == "all":
        if args.count is not None or args.target != "base":
            raise PlanningError("unlock all always targets only the minimal/base tier.")
        plans, pair_blocker = _plan_all(client)
    else:
        plans = [_single_plan(client, args)]
        pair_blocker = None

    for plan in plans:
        enforce_volume(
            plan,
            maximum=client.config.max_automatic_actions,
            allow_high_volume=args.allow_high_volume,
        )
        print_plan(plan)
    if pair_blocker:
        print(f"\n[!] Pair Extraordinaire: BLOCKED_EXTERNAL_REQUIREMENT — {pair_blocker}")
    if args.dry_run:
        print("\nDry-run complete: no GitHub objects were created or changed.")
        return 0

    client.ensure_lab(create=False)
    state = State.load()
    results: list[ExecutionResult] = []
    if args.achievement == "all":
        if plans[0].actions:
            results.append(quickdraw.execute(client, state))
        if plans[1].actions:
            results.append(yolo.execute(client, state))
        # Recalculate because the YOLO merge also contributes to Pull Shark.
        refreshed = pull_shark.plan(client, target="base")
        enforce_volume(
            refreshed,
            maximum=client.config.max_automatic_actions,
            allow_high_volume=args.allow_high_volume,
        )
        results.extend(pull_shark.execute(client, state, refreshed))
        if len(plans) == 4 and plans[3].actions:
            results.extend(pair_extraordinaire.execute(client, state, plans[3]))
    else:
        plan = plans[0]
        if not plan.actions:
            print("\nTarget already satisfied; no changes were made.")
            return 0
        if args.achievement == "quickdraw":
            results.append(quickdraw.execute(client, state))
        elif args.achievement == "yolo":
            results.append(yolo.execute(client, state))
        elif args.achievement == "pull-shark":
            results.extend(pull_shark.execute(client, state, plan))
        elif args.achievement == "pair-extraordinaire":
            results.extend(pair_extraordinaire.execute(client, state, plan))
    print_results(results)
    return 0


def command_cleanup(client: GitHubClient) -> int:
    client.ensure_identity()
    client.ensure_lab(create=False)
    result = cleanup(client, State.load())
    print(
        "Cleanup complete: "
        f"closed PRs={result.closed_pull_requests}, "
        f"closed issues={result.closed_issues}, "
        f"deleted branches={result.deleted_branches}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = make_client()
        if args.command == "status":
            return command_status(client)
        if args.command == "init":
            return command_init(client)
        if args.command == "cleanup":
            return command_cleanup(client)
        if args.command == "unlock":
            return command_unlock(client, args)
        raise AssertionError(args.command)
    except (ConfigurationError, GitHubError, PlanningError, pair_extraordinaire.MissingCoauthor) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
