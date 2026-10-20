from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def service_block(compose: str, service: str) -> str:
    lines = compose.splitlines()
    start = lines.index(f"  {service}:")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("  ") and not lines[i].startswith("    ")), len(lines))
    return "\n".join(lines[start:end])


class ComposePostgreSQLTests(unittest.TestCase):
    def test_postgres_is_pinned_persistent_private_and_health_checked(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        service = service_block(compose, "postgres")
        self.assertIn("postgres:18-alpine@sha256:", service)
        self.assertIn("postgres-data:/var/lib/postgresql", service)
        self.assertIn("./docker/postgres/init:/docker-entrypoint-initdb.d:ro", service)
        self.assertIn("pg_isready", service)
        self.assertNotIn("ports:", service)

    def test_litellm_waits_for_postgres_health_on_internal_service_url(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        service = service_block(compose, "litellm")
        environment = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("postgres:\n        condition: service_healthy", service)
        self.assertIn("@postgres:5432/litellm", environment)
        self.assertNotIn("HOST_DOCKER_INTERNAL_IP", environment)

    def test_init_script_reads_password_from_environment_and_quotes_it_as_sql_data(self):
        init = (ROOT / "docker" / "postgres" / "init" / "10-create-litellm.sql").read_text(encoding="utf-8")
        self.assertIn("\\getenv litellm_password LITELLM_DB_PASSWORD", init)
        self.assertIn("format('CREATE ROLE litellm LOGIN PASSWORD %L'", init)
        self.assertNotIn("LITELLM_DB_PASSWORD='", init)


if __name__ == "__main__":
    unittest.main()
