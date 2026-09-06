from __future__ import annotations

from .models import AchievementDefinition, AutomationClass

ACHIEVEMENTS: tuple[AchievementDefinition, ...] = (
    AchievementDefinition(
        "quickdraw", "Quickdraw", AutomationClass.AUTOMATABLE,
        "Close an issue or pull request within five minutes of opening it.", "high"
    ),
    AchievementDefinition(
        "yolo", "YOLO", AutomationClass.AUTOMATABLE,
        "Merge a pull request without an approving review.", "medium"
    ),
    AchievementDefinition(
        "pull-shark", "Pull Shark", AutomationClass.AUTOMATABLE,
        "Have pull requests opened by the account merged.", "high",
        {"base": 2, "bronze": 16, "silver": 128, "gold": 1024},
    ),
    AchievementDefinition(
        "pair-extraordinaire", "Pair Extraordinaire",
        AutomationClass.BLOCKED_EXTERNAL_REQUIREMENT,
        "Co-author a commit in a merged pull request with a real GitHub user.", "medium",
        {"base": 1, "bronze": 10, "silver": 24, "gold": 48},
    ),
    AchievementDefinition(
        "starstruck", "Starstruck", AutomationClass.EXTERNAL_REQUIREMENT,
        "Own a repository with at least 16 genuine stars.", "high",
        {"base": 16, "bronze": 128, "silver": 512, "gold": 4096},
    ),
    AchievementDefinition(
        "galaxy-brain", "Galaxy Brain", AutomationClass.EXTERNAL_REQUIREMENT,
        "Have answers accepted in GitHub Discussions.", "medium",
        {"base": 2, "bronze": 8, "silver": 16, "gold": 32},
    ),
    AchievementDefinition(
        "public-sponsor", "Public Sponsor", AutomationClass.MANUAL,
        "Publicly sponsor open-source work through GitHub Sponsors.", "high"
    ),
    AchievementDefinition(
        "heart-on-your-sleeve", "Heart On Your Sleeve",
        AutomationClass.LEGACY_UNOBTAINABLE,
        "Unreleased/test achievement; currently not earnable.", "medium"
    ),
    AchievementDefinition(
        "open-sourcerer", "Open Sourcerer", AutomationClass.LEGACY_UNOBTAINABLE,
        "Unreleased/test achievement; currently not earnable.", "medium"
    ),
    AchievementDefinition(
        "arctic-code-vault-contributor", "Arctic Code Vault Contributor",
        AutomationClass.LEGACY_UNOBTAINABLE,
        "Contributed to a repository included in the 2020 Archive Program snapshot.", "high"
    ),
    AchievementDefinition(
        "mars-2020-contributor", "Mars 2020 Contributor",
        AutomationClass.LEGACY_UNOBTAINABLE,
        "Contributed code used by the Mars 2020 helicopter mission.", "high"
    ),
)


BY_SLUG = {item.slug: item for item in ACHIEVEMENTS}

