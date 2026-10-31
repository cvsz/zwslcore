import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zeaz_provider.config import load_settings

VALID_CONFIG = """
default_model: test-route
providers:
  ollama:
    api: openai
    base_url: http://127.0.0.1:11434/v1
    cost_class: FREE_LOCAL
models:
  test-route:
    provider: ollama
    model: qwen2.5-coder:3b
    cost_policy: LOCAL_ONLY
    fallbacks: []
"""


class ConfigPathResolutionTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "ZEAZ_RATE_LIMIT_BACKEND": "memory",
                "ZEAZ_CLIENT_KEYS": "",
                "ZEAZ_CLIENT_KEY_HASHES": "",
                "ZEAZ_CONFIG": "",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_config(self, directory: str, filename: str) -> Path:
        path = Path(directory) / filename
        path.write_text(VALID_CONFIG, encoding="utf-8")
        return path

    def test_default_config_is_independent_of_working_directory(self):
        repository_config = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "providers.yaml"
        )

        with tempfile.TemporaryDirectory() as directory:
            previous_cwd = Path.cwd()
            try:
                os.chdir(directory)
                settings = load_settings()
            finally:
                os.chdir(previous_cwd)

        self.assertTrue(repository_config.is_file())
        self.assertIn("zeaz-claude", settings.models)

    def test_environment_config_overrides_package_default(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory, "custom.yaml")
            os.environ["ZEAZ_CONFIG"] = str(config_path)

            settings = load_settings()

        self.assertEqual(settings.default_model, "test-route")

    def test_explicit_path_overrides_environment_config(self):
        with tempfile.TemporaryDirectory() as directory:
            explicit_path = self.write_config(directory, "explicit.yaml")
            environment_path = Path(directory) / "environment.yaml"
            environment_path.write_text(
                VALID_CONFIG.replace("test-route", "environment-route"),
                encoding="utf-8",
            )

            os.environ["ZEAZ_CONFIG"] = str(environment_path)

            settings = load_settings(explicit_path)

        self.assertEqual(settings.default_model, "test-route")

    def test_missing_config_reports_resolved_path(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "missing.yaml"

            with self.assertRaisesRegex(
                RuntimeError,
                str(missing_path.resolve()),
            ):
                load_settings(missing_path)


if __name__ == "__main__":
    unittest.main()
