from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from achievement_unlocker.config import Config, ConfigurationError, resolve_token


class ConfigTests(unittest.TestCase):
    def test_only_lab_repository_is_allowed(self) -> None:
        Config().validate_target()
        with self.assertRaises(ConfigurationError):
            Config(repository="ympatcher").validate_target()

    @patch("achievement_unlocker.config._token_from_gh", return_value=None)
    def test_token_comes_from_environment(self, _mock_gh: object) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "secret"}, clear=True):
            self.assertEqual(resolve_token(), "secret")

    @patch("achievement_unlocker.config._token_from_gh", return_value=None)
    def test_missing_token_is_explicit(self, _mock_gh: object) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaises(ConfigurationError),
        ):
            resolve_token()


if __name__ == "__main__":
    unittest.main()
