from __future__ import annotations

import html
import re
from dataclasses import dataclass

import requests

ACHIEVEMENT_LINK = re.compile(r"[?&]achievement=([a-z0-9-]+)", re.IGNORECASE)


@dataclass(frozen=True)
class ProfileAchievements:
    slugs: frozenset[str]
    visibility_uncertain: bool


def inspect_public_profile(owner: str, *, timeout: int = 20) -> ProfileAchievements:
    response = requests.get(
        f"https://github.com/{owner}",
        headers={"User-Agent": "safe-github-achievement-unlocker/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    page = html.unescape(response.text)
    slugs = frozenset(match.casefold() for match in ACHIEVEMENT_LINK.findall(page))
    # An empty public section means either no achievements or user-hidden achievements.
    return ProfileAchievements(slugs=slugs, visibility_uncertain=not slugs)

