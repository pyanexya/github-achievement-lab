from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AutomationClass(StrEnum):
    AUTOMATABLE = "AUTOMATABLE"
    PARTIALLY_AUTOMATABLE = "PARTIALLY_AUTOMATABLE"
    MANUAL = "MANUAL"
    EXTERNAL_REQUIREMENT = "EXTERNAL_REQUIREMENT"
    LEGACY_UNOBTAINABLE = "LEGACY_UNOBTAINABLE"
    UNKNOWN = "UNKNOWN"
    BLOCKED_EXTERNAL_REQUIREMENT = "BLOCKED_EXTERNAL_REQUIREMENT"


@dataclass(frozen=True)
class AchievementDefinition:
    slug: str
    name: str
    classification: AutomationClass
    requirements: str
    confidence: str
    thresholds: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionPlan:
    achievement: str
    target: str
    actions: int
    branches: int = 0
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "achievement": self.achievement,
            "target": self.target,
            "actions": self.actions,
            "branches": self.branches,
            "commits": self.commits,
            "pull_requests": self.pull_requests,
            "issues": self.issues,
            "notes": list(self.notes),
        }


@dataclass
class ExecutionResult:
    achievement: str
    status: str
    created_branches: int = 0
    created_commits: int = 0
    created_pull_requests: int = 0
    merged_pull_requests: int = 0
    created_issues: int = 0
    deleted_branches: int = 0
    urls: list[str] = field(default_factory=list)
    detail: str = ""

