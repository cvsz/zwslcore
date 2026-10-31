from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OpenWebUICustomCSSTests(unittest.TestCase):
    def test_mobile_login_override_is_read_only_mounted_and_scoped(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        service = compose.split("  open-webui:\n", 1)[1].split("\nnetworks:\n", 1)[0]
        css = (ROOT / "webui" / "custom.css").read_text(encoding="utf-8")

        self.assertIn("./webui/custom.css:/app/build/static/custom.css:ro", service)
        self.assertIn("@media (max-width: 480px)", css)
        self.assertIn("#auth-page", css)
        self.assertIn("#auth-container", css)
        self.assertIn("#auth-login-card", css)
        self.assertNotIn("body {", css)


if __name__ == "__main__":
    unittest.main()
