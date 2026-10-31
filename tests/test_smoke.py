from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SMOKE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "smoke.sh"
ENV_LOADER = Path(__file__).resolve().parents[1] / "scripts" / "lib" / "env.sh"


class SmokeScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts" / "lib").mkdir(parents=True)
        shutil.copy2(SMOKE_SCRIPT, self.root / "scripts" / "smoke.sh")
        shutil.copy2(ENV_LOADER, self.root / "scripts" / "lib" / "env.sh")
        (self.root / ".env").write_text(
            "LITELLM_MASTER_KEY=test-secret\n", encoding="utf-8"
        )
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        curl = fake_bin / "curl"
        curl.write_text(
            "#!/bin/sh\n"
            'for arg in "$@"; do case "$arg" in *test-secret*) echo "secret-in-argv" >&2; exit 98;; esac; done\n'
            'if [ "${SMOKE_CURL_FAIL:-0}" = 1 ]; then echo "connection refused" >&2; exit 7; fi\n'
            'printf "%s" "${SMOKE_CURL_BODY:-}"\n',
            encoding="utf-8",
        )
        curl.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "SMOKE_CURL_BODY": "",
        }

    def run_smoke(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.root / "scripts" / "smoke.sh")],
            cwd=self.root,
            env=self.env,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def test_unavailable_litellm_has_actionable_error_without_json_traceback(self) -> None:
        self.env["SMOKE_CURL_FAIL"] = "1"
        result = self.run_smoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("check PostgreSQL connectivity with make doctor", result.stderr)
        self.assertNotIn("JSONDecodeError", result.stderr)
        self.assertNotIn("test-secret", result.stderr)

    def test_invalid_model_catalog_has_clean_error(self) -> None:
        self.env["SMOKE_CURL_BODY"] = "not-json"
        result = self.run_smoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid model catalog", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_model_catalog_must_include_coder_alias(self) -> None:
        self.env["SMOKE_CURL_BODY"] = '{"data":[]}'
        result = self.run_smoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing zeaz-coder", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
