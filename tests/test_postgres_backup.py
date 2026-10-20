"""Offline tests for private PostgreSQL backup creation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "postgres_backup.py"


class PostgreSQLBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env_file = self.root / ".env"
        self.env_file.write_text(
            "DATABASE_URL=postgresql://backup-user:p%40ss%3Aword@host.docker.internal:5432/litellm\n"
            "HOST_DOCKER_INTERNAL_IP=172.18.0.1\n",
            encoding="utf-8",
        )
        self.env_file.chmod(0o600)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.argv_log = self.root / "argv.json"
        self.password_seen = self.root / "password-seen"
        self.inherited_secret_seen = self.root / "inherited-secret-seen"
        pg_dump = self.bin / "pg_dump"
        pg_dump.write_text(f"""#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
pathlib.Path({json.dumps(str(self.argv_log))}).write_text(json.dumps(args))
if os.environ.get('PGPASSWORD') == 'p@ss:word': pathlib.Path({json.dumps(str(self.password_seen))}).touch()
if os.environ.get('UNRELATED_SECRET'): pathlib.Path({json.dumps(str(self.inherited_secret_seen))}).touch()
target = pathlib.Path(args[args.index('--file') + 1])
target.write_bytes(b'postgres custom archive fixture')
""", encoding="utf-8")
        pg_dump.chmod(0o700)
        pg_restore = self.bin / "pg_restore"
        pg_restore.write_text(f"""#!/usr/bin/env python3
import os, pathlib, sys
if os.environ.get('UNRELATED_SECRET'): pathlib.Path({json.dumps(str(self.inherited_secret_seen))}).touch()
if sys.argv[1:] == ['--list', sys.argv[-1]]: print('TABLE DATA public messages')
else: raise SystemExit(2)
""", encoding="utf-8")
        pg_restore.chmod(0o700)
        self.env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ.get('PATH', '')}",
            UNRELATED_SECRET="must-not-reach-database-tools",
        )

    def run_backup(self, output: Path):
        return subprocess.run(
            ["python3", str(SCRIPT), "--env-file", str(self.env_file), "--output", str(output)],
            env=self.env, capture_output=True, text=True, timeout=10,
        )

    def test_creates_private_verified_archive_without_cli_password(self):
        output = self.root / "backup.dump"
        result = self.run_backup(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), b"postgres custom archive fixture")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.password_seen.exists())
        self.assertFalse(self.inherited_secret_seen.exists())
        args = json.loads(self.argv_log.read_text(encoding="utf-8"))
        self.assertNotIn("p@ss:word", " ".join(args))
        self.assertIn("127.0.0.1", args)
        self.assertIn("backup-user", args)
        self.assertIn("sha256", result.stdout)

    def test_compose_database_backup_uses_container_pg_dump_without_password_argument(self):
        docker_args = self.root / "docker-argv.json"
        docker = self.bin / "docker"
        docker.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv[1:]
pathlib.Path({json.dumps(str(docker_args))}).write_text(json.dumps(args))
sys.stdout.buffer.write(b'container PostgreSQL archive fixture')
""", encoding="utf-8")
        docker.chmod(0o700)
        self.env_file.write_text(
            "DATABASE_URL=postgresql://backup-user:p%40ss%3Aword@postgres:5432/litellm\n",
            encoding="utf-8",
        )
        self.env_file.chmod(0o600)

        output = self.root / "docker-backup.dump"
        result = self.run_backup(output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), b"container PostgreSQL archive fixture")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        args = json.loads(docker_args.read_text(encoding="utf-8"))
        self.assertIn("postgres", args)
        self.assertIn("pg_dump", args)
        self.assertNotIn("p@ss:word", " ".join(args))

    def test_existing_destination_is_never_overwritten(self):
        output = self.root / "backup.dump"
        output.write_bytes(b"operator data")
        result = self.run_backup(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_bytes(), b"operator data")
        self.assertFalse(self.argv_log.exists())

    def test_symlink_and_open_environment_files_are_rejected(self):
        symlink = self.root / "env-link"
        symlink.symlink_to(self.env_file)
        result = subprocess.run(
            ["python3", str(SCRIPT), "--env-file", str(symlink), "--output", str(self.root / "one.dump")],
            env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("regular non-symlink", result.stderr)

        self.env_file.chmod(0o644)
        result = self.run_backup(self.root / "two.dump")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chmod 600", result.stderr)

    def test_environment_assignments_are_not_executed(self):
        marker = self.root / "executed"
        self.env_file.write_text(
            f"DATABASE_URL=$(touch {marker})\nHOST_DOCKER_INTERNAL_IP=172.18.0.1\n",
            encoding="utf-8",
        )
        self.env_file.chmod(0o600)
        result = self.run_backup(self.root / "backup.dump")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertFalse(self.argv_log.exists())

    def test_invalid_environment_encoding_has_clean_error(self):
        self.env_file.write_bytes(b"DATABASE_URL=\xff\n")
        self.env_file.chmod(0o600)
        result = self.run_backup(self.root / "backup.dump")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("environment file must be UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
