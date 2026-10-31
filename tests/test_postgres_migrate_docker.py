from __future__ import annotations

import unittest

from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.postgres_migrate_docker import (
    _ensure_superuser_password,
    _require_new_migration_target,
    _replace_database_url,
    _url_for_docker,
)


class PostgreSQLDockerMigrationTests(unittest.TestCase):
    def test_local_host_url_moves_to_internal_service_and_preserves_encoded_credentials(self):
        result = _url_for_docker(
            "postgresql://db-user:p%40ss%3Aword@host.docker.internal:5432/litellm?sslmode=disable"
        )
        self.assertEqual(
            result,
            "postgresql://db-user:p%40ss%3Aword@postgres:5432/litellm_migrated?sslmode=disable",
        )

    def test_external_database_is_never_silently_redirected(self):
        with self.assertRaisesRegex(ValueError, "local host PostgreSQL"):
            _url_for_docker("postgresql://user:password@db.example.net/litellm")

    def test_database_url_replacement_updates_all_active_duplicates_only(self):
        original = (
            "# DATABASE_URL=leave-this-comment\n"
            "DATABASE_URL=postgresql://old-a\n"
            "OTHER_SETTING=preserve\n"
            "DATABASE_URL=postgresql://old-b\n"
        )
        result = _replace_database_url(original, "postgresql://litellm@postgres/litellm_migrated")
        self.assertEqual(result.count("DATABASE_URL=postgresql://litellm@postgres/litellm_migrated"), 2)
        self.assertIn("# DATABASE_URL=leave-this-comment", result)
        self.assertIn("OTHER_SETTING=preserve", result)

    def test_generated_superuser_credential_is_preserved_for_rollback(self):
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("DATABASE_URL=postgresql://user:pass@localhost/db\n")
            rollback_content, values = _ensure_superuser_password(env_file, {})
            self.assertIn("POSTGRES_SUPERUSER_PASSWORD=", rollback_content)
            self.assertEqual(values["POSTGRES_SUPERUSER_PASSWORD"], rollback_content.split("POSTGRES_SUPERUSER_PASSWORD=", 1)[1].strip())

    def test_existing_target_is_rejected_even_when_table_count_could_match(self):
        with self.assertRaisesRegex(RuntimeError, "matching table counts do not verify its contents"):
            _require_new_migration_target(True)

    def test_absent_target_can_be_created_for_restore(self):
        _require_new_migration_target(False)


if __name__ == "__main__":
    unittest.main()
