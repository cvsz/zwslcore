from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.postgres_preflight import check, database_target, read_env


class PostgresPreflightTests(unittest.TestCase):
    def test_compose_service_defers_socket_check_to_container_health(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("DATABASE_URL=postgresql://litellm:secret@postgres:5432/litellm\n")
            output = io.StringIO()
            with patch("scripts.postgres_preflight.socket.create_connection") as connect:
                with contextlib.redirect_stdout(output):
                    self.assertTrue(check(path))
                connect.assert_not_called()
            self.assertIn("internal Compose service", output.getvalue())

    def test_docker_host_resolves_to_configured_bridge_gateway(self) -> None:
        self.assertEqual(
            database_target(
                {
                    "DATABASE_URL": "postgresql://litellm:secret@host.docker.internal:5432/litellm",
                    "HOST_DOCKER_INTERNAL_IP": "172.20.0.1",
                }
            ),
            ("172.20.0.1", 5432),
        )

    def test_docker_host_uses_default_bridge_gateway(self) -> None:
        self.assertEqual(
            database_target(
                {"DATABASE_URL": "postgresql://litellm:secret@host.docker.internal/litellm"}
            ),
            ("172.18.0.1", 5432),
        )

    def test_explicit_database_host_is_preserved(self) -> None:
        self.assertEqual(
            database_target({"DATABASE_URL": "postgresql://litellm:secret@db.internal:5544/litellm"}),
            ("db.internal", 5544),
        )

    def test_quoted_database_url_and_gateway_are_parsed_as_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                'DATABASE_URL="postgresql://litellm:secret@host.docker.internal:5433/litellm"\n'
                "HOST_DOCKER_INTERNAL_IP='172.21.0.1'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                database_target(read_env(path)),
                ("172.21.0.1", 5433),
            )

    def test_non_postgresql_database_url_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "PostgreSQL scheme"):
            database_target({"DATABASE_URL": "sqlite:///tmp/litellm.db"})

    def test_invalid_docker_gateway_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "HOST_DOCKER_INTERNAL_IP"):
            database_target(
                {
                    "DATABASE_URL": "postgresql://litellm:secret@host.docker.internal/litellm",
                    "HOST_DOCKER_INTERNAL_IP": "",
                }
            )

    def test_explicit_zero_port_is_rejected_instead_of_defaulting(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
            database_target({"DATABASE_URL": "postgresql://litellm@host.docker.internal:0/litellm"})

    def test_malformed_ipv6_url_has_a_clean_configuration_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid IPv6 URL"):
            database_target({"DATABASE_URL": "postgresql://[broken/litellm"})

    def test_env_file_reads_values_without_printing_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("# comment\nHOST_DOCKER_INTERNAL_IP=172.20.0.1\n", encoding="utf-8")
            self.assertEqual(read_env(path), {"HOST_DOCKER_INTERNAL_IP": "172.20.0.1"})

    def test_connection_failure_reports_only_host_and_port(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "DATABASE_URL=postgresql://user:do-not-print@host.docker.internal/db\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with patch("scripts.postgres_preflight.socket.create_connection", side_effect=OSError("refused")):
                with contextlib.redirect_stdout(output):
                    self.assertFalse(check(path))
            self.assertIn("172.18.0.1:5432", output.getvalue())
            self.assertNotIn("do-not-print", output.getvalue())


if __name__ == "__main__":
    unittest.main()
