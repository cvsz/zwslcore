from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


INSTALL_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.sh"


class InstallerEnvironmentSafetyTests(unittest.TestCase):
    def run_installer(self, env_path: Path) -> subprocess.CompletedProcess[str]:
        root = env_path.parent
        scripts = root / "scripts"
        library = scripts / "lib"
        library.mkdir(parents=True, exist_ok=True)
        installer = scripts / "install.sh"
        shutil.copy2(INSTALL_SCRIPT, installer)
        shutil.copy2(INSTALL_SCRIPT.parent / "postgres_preflight.py", scripts / "postgres_preflight.py")
        shutil.copy2(INSTALL_SCRIPT.parents[1] / "scripts" / "lib" / "env_file.py", library / "env_file.py")
        example = INSTALL_SCRIPT.parents[1] / ".env.example"
        shutil.copy2(example, root / ".env.example")
        # Force a closed, deterministic preflight failure after environment
        # migration so installer safety can be verified without Docker access.
        sample = (root / ".env.example").read_text(encoding="utf-8")
        sample = sample.replace(
            "postgresql://litellm:REPLACE_ME_DATABASE_PASSWORD@postgres:5432/litellm",
            "postgresql://litellm:REPLACE_ME_DATABASE_PASSWORD@127.0.0.1:1/litellm",
        )
        (root / ".env.example").write_text(sample, encoding="utf-8")
        binaries = root / "bin"
        binaries.mkdir()
        docker = binaries / "docker"
        docker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        docker.chmod(0o700)
        return subprocess.run(
            ["bash", str(installer)],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": f"{binaries}:/usr/bin:/bin"},
        )

    def test_symlinked_env_is_rejected_before_runtime_checks_or_target_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "outside.env"
            target.write_text("KEEP=this value\n", encoding="utf-8")
            target.chmod(0o644)
            env_file = root / "checkout" / ".env"
            env_file.parent.mkdir()
            env_file.symlink_to(target)

            result = self.run_installer(env_file)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("regular, non-symlink", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "KEEP=this value\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_non_file_env_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "checkout" / ".env"
            env_file.mkdir(parents=True)

            result = self.run_installer(env_file)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("regular, non-symlink", result.stderr)

    def test_new_environment_is_private_and_recoverable_when_preflight_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "checkout" / ".env"
            env_file.parent.mkdir()

            result = self.run_installer(env_file)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PostgreSQL unreachable", result.stdout + result.stderr)
            self.assertTrue(env_file.is_file())
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("REPLACE_ME_", env_file.read_text(encoding="utf-8"))

    def test_upgrade_adds_missing_postgres_superuser_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "checkout" / ".env"
            env_file.parent.mkdir()
            env_file.write_text(
                "LITELLM_DB_PASSWORD=existing-db-password\n"
                "LITELLM_SALT_KEY=existing-salt\n"
                "DATABASE_URL=postgresql://litellm:existing-db-password@127.0.0.1:1/litellm\n",
                encoding="utf-8",
            )
            env_file.chmod(0o600)

            result = self.run_installer(env_file)

            content = env_file.read_text(encoding="utf-8")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PostgreSQL unreachable", result.stdout + result.stderr)
            self.assertRegex(content, r"(?m)^POSTGRES_SUPERUSER_PASSWORD=.+$")
            self.assertNotIn("REPLACE_ME_", content)
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
