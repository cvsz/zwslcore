import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "chat_ui_contract.py"
SPEC = importlib.util.spec_from_file_location("chat_ui_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class ChatUiContractTests(unittest.TestCase):
    def test_repo_default_contract(self):
        root = SCRIPT.parents[1]
        checks = MODULE.inspect((root / "compose.yaml").read_text(), (root / ".env.example").read_text())
        self.assertTrue(all(checks.values()), checks)

    def test_disallow_direct_ollama(self):
        root = SCRIPT.parents[1]
        compose = (root / "compose.yaml").read_text().replace('ENABLE_OLLAMA_API: "false"', 'ENABLE_OLLAMA_API: "true"')
        checks = MODULE.inspect(compose, (root / ".env.example").read_text())
        self.assertFalse(checks["direct_ollama_disabled"])

    def test_detect_public_signup(self):
        root = SCRIPT.parents[1]
        env = (root / ".env.example").read_text().replace("OPENWEBUI_ENABLE_SIGNUP=false", "OPENWEBUI_ENABLE_SIGNUP=true")
        checks = MODULE.inspect((root / "compose.yaml").read_text(), env)
        self.assertFalse(checks["signup_disabled_by_default"])

if __name__ == "__main__":
    unittest.main()
