from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stdout

from cli import command_unlock


class DryRunClient:
    class FakeConfig:
        owner = "pyanexya"
        full_name = "pyanexya/github-achievement-lab"
        max_automatic_actions = 20

    config = FakeConfig()

    def __init__(self) -> None:
        self.mutations = 0

    def ensure_identity(self) -> None:
        return None

    def get_repository(self) -> None:
        return None

    def global_public_merged_pr_count(self) -> int:
        return 1

    def ensure_lab(self, *, create: bool) -> None:
        self.mutations += 1


class CliTests(unittest.TestCase):
    def test_dry_run_never_ensures_or_creates_repository(self) -> None:
        client = DryRunClient()
        args = argparse.Namespace(
            achievement="pull-shark",
            target="base",
            count=None,
            dry_run=True,
            allow_high_volume=False,
        )
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(command_unlock(client, args), 0)
        self.assertEqual(client.mutations, 0)
        self.assertIn("no GitHub objects", output.getvalue())


if __name__ == "__main__":
    unittest.main()

