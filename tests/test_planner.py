from __future__ import annotations

import unittest

from achievement_unlocker.planner import PlanningError, enforce_volume, pull_shark_plan


class PlannerTests(unittest.TestCase):
    def test_pull_shark_creates_exact_missing_count(self) -> None:
        plan = pull_shark_plan(1, target="base")
        self.assertEqual(plan.actions, 1)
        self.assertEqual(plan.pull_requests, 1)

    def test_satisfied_target_is_noop(self) -> None:
        self.assertEqual(pull_shark_plan(20, target="bronze").actions, 0)

    def test_explicit_count(self) -> None:
        self.assertEqual(pull_shark_plan(900, count=2).actions, 2)

    def test_volume_guard(self) -> None:
        plan = pull_shark_plan(0, target="silver")
        with self.assertRaises(PlanningError):
            enforce_volume(plan, maximum=20, allow_high_volume=False)
        enforce_volume(plan, maximum=20, allow_high_volume=True)


if __name__ == "__main__":
    unittest.main()

