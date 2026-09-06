from __future__ import annotations

from .catalog import BY_SLUG
from .models import ActionPlan


class PlanningError(RuntimeError):
    pass


def threshold_for(achievement: str, target: str) -> int:
    definition = BY_SLUG[achievement]
    try:
        return definition.thresholds[target]
    except KeyError as exc:
        valid = ", ".join(definition.thresholds) or "base"
        raise PlanningError(
            f"Unsupported target {target!r} for {achievement}; choose {valid}."
        ) from exc


def pull_shark_plan(
    current: int,
    *,
    target: str = "base",
    count: int | None = None,
) -> ActionPlan:
    if count is not None:
        if count < 0:
            raise PlanningError("--count cannot be negative.")
        needed = count
        target_label = f"count:{count}"
    else:
        goal = threshold_for("pull-shark", target)
        needed = max(0, goal - current)
        target_label = f"{target} ({goal})"
    return ActionPlan(
        achievement="pull-shark",
        target=target_label,
        actions=needed,
        branches=needed,
        commits=needed,
        pull_requests=needed,
        notes=(f"Current laboratory merged PR count: {current}",),
    )


def pair_plan(current: int, *, target: str = "base") -> ActionPlan:
    goal = threshold_for("pair-extraordinaire", target)
    needed = max(0, goal - current)
    return ActionPlan(
        achievement="pair-extraordinaire",
        target=f"{target} ({goal})",
        actions=needed,
        branches=needed,
        commits=needed,
        pull_requests=needed,
        notes=(f"Known laboratory co-authored merged PR count: {current}",),
    )


def one_shot_plan(achievement: str, already_done: bool) -> ActionPlan:
    needed = 0 if already_done else 1
    return ActionPlan(
        achievement=achievement,
        target="base",
        actions=needed,
        branches=needed if achievement == "yolo" else 0,
        commits=needed if achievement == "yolo" else 0,
        pull_requests=needed if achievement == "yolo" else 0,
        issues=needed if achievement == "quickdraw" else 0,
    )


def enforce_volume(plan: ActionPlan, *, maximum: int, allow_high_volume: bool) -> None:
    if plan.actions > maximum and not allow_high_volume:
        raise PlanningError(
            f"Plan requires {plan.actions} actions, exceeding the safety limit {maximum}. "
            "Use --allow-high-volume only after reviewing --dry-run."
        )

