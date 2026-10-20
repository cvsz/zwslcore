#!/usr/bin/env python3
"""Safely migrate the local LiteLLM database into the private Compose PostgreSQL service."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from env_file import write_private_file
from postgres_backup import _connection, _private_env, create_backup

TARGET_DATABASE = "litellm_migrated"
LOCAL_SOURCE_HOSTS = {"host.docker.internal", "localhost", "127.0.0.1", "::1"}
QUERY = (
    "SELECT count(*) FROM pg_tables "
    "WHERE schemaname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')"
)


def _safe_environment() -> dict[str, str]:
    names = (
        "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "DOCKER_CONFIG",
        "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH",
        "SSH_AUTH_SOCK",
    )
    return {name: os.environ[name] for name in names if name in os.environ}


def _url_for_docker(raw_url: str) -> str:
    url = urlsplit(raw_url)
    if url.scheme not in {"postgres", "postgresql"} or url.hostname not in LOCAL_SOURCE_HOSTS:
        raise ValueError("only a local host PostgreSQL source can be migrated")
    if not url.username or not url.password or not url.path.strip("/"):
        raise ValueError("DATABASE_URL must include username, password, and database")
    if url.query and any(item.partition("=")[0] not in {"sslmode", "application_name"} for item in url.query.split("&")):
        raise ValueError("DATABASE_URL has unsupported query options")
    userinfo = url.netloc.rsplit("@", 1)[0]
    return urlunsplit((url.scheme, f"{userinfo}@postgres:5432", f"/{TARGET_DATABASE}", url.query, ""))


def _compose(env_file: Path, *args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    command = [
        "docker", "compose", "--project-directory", str(ROOT),
        "--file", str(ROOT / "compose.yaml"), "--env-file", str(env_file), *args,
    ]
    return subprocess.run(
        command,
        cwd=ROOT,
        env=_safe_environment(),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=1800,
    )


def _source_table_count(values: dict[str, str]) -> int:
    host, port, user, password, database = _connection(values)
    psql = shutil.which("psql")
    if not psql:
        raise RuntimeError("psql is required to verify the source table count")
    child_env = _safe_environment() | {"PGPASSWORD": password}
    result = subprocess.run(
        [psql, "--no-password", "--no-psqlrc", "--tuples-only", "--no-align",
         "--set", "ON_ERROR_STOP=1", "--host", host, "--port", str(port),
         "--username", user, "--dbname", database, "--command", QUERY],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError("could not verify source PostgreSQL table count")
    try:
        return int(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("source PostgreSQL returned an invalid table count") from exc


def _container_table_count(env_file: Path) -> int:
    result = _compose(
        env_file, "exec", "--no-TTY", "postgres", "psql", "--username", "postgres",
        "--dbname", TARGET_DATABASE, "--tuples-only", "--no-align", "--command", QUERY,
    )
    if result.returncode:
        raise RuntimeError("could not verify migrated PostgreSQL table count")
    try:
        return int(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Docker PostgreSQL returned an invalid table count") from exc


def _require_new_migration_target(exists: bool) -> None:
    if exists:
        raise RuntimeError(
            f"target database {TARGET_DATABASE!r} already exists; "
            "refusing to reuse it because matching table counts do not verify its contents"
        )


def _ensure_superuser_password(env_file: Path, values: dict[str, str]) -> tuple[str, dict[str, str]]:
    if values.get("POSTGRES_SUPERUSER_PASSWORD"):
        return env_file.read_text(encoding="utf-8"), values
    original = env_file.read_text(encoding="utf-8")
    password = secrets.token_hex(32)
    lines = original.splitlines()
    lines.append(f"POSTGRES_SUPERUSER_PASSWORD={password}")
    write_private_file(env_file, "\n".join(lines).rstrip() + "\n")
    values["POSTGRES_SUPERUSER_PASSWORD"] = password
    # Keep generated administrative credentials across a failed URL cutover.
    return env_file.read_text(encoding="utf-8"), values


def _replace_database_url(content: str, new_url: str) -> str:
    output: list[str] = []
    found = False
    for line in content.splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            output.append(line)
            continue
        key, _ = line.split("=", 1)
        if key.strip() == "DATABASE_URL":
            output.append(f"DATABASE_URL={new_url}")
            found = True
        else:
            output.append(line)
    if not found:
        output.append(f"DATABASE_URL={new_url}")
    return "\n".join(output).rstrip() + "\n"


def migrate(env_file: Path) -> tuple[Path, str, int]:
    env_file = env_file.expanduser()
    if not env_file.is_absolute():
        env_file = Path.cwd() / env_file
    values = _private_env(env_file)
    raw_url = values.get("DATABASE_URL", "")
    parsed = urlsplit(raw_url)
    if parsed.hostname == "postgres":
        raise ValueError("DATABASE_URL already targets the Docker PostgreSQL service")
    target_url = _url_for_docker(raw_url)
    if unquote(parsed.password or "") != values.get("LITELLM_DB_PASSWORD"):
        raise ValueError("DATABASE_URL password must match LITELLM_DB_PASSWORD")

    original_env, values = _ensure_superuser_password(env_file, values)
    source_tables = _source_table_count(values)
    if source_tables == 0:
        raise RuntimeError("source PostgreSQL has no user tables; refusing an empty migration")

    backup_path, digest, size = create_backup(env_file, None)

    result = _compose(env_file, "up", "-d", "postgres")
    if result.returncode:
        raise RuntimeError("could not start the Docker PostgreSQL service")
    for _ in range(60):
        health = subprocess.run(
            ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{end}}", "zwslcore-postgres"],
            env=_safe_environment(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=10,
        )
        if health.returncode == 0 and health.stdout.strip() == b"healthy":
            break
        time.sleep(2)
    else:
        raise RuntimeError("Docker PostgreSQL did not become healthy; source database remains unchanged")

    exists = _compose(
        env_file, "exec", "--no-TTY", "postgres", "psql", "--username", "postgres",
        "--dbname", "postgres", "--tuples-only", "--no-align", "--command",
        f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DATABASE}'",
    )
    if exists.returncode:
        raise RuntimeError("could not inspect the Docker PostgreSQL target")
    _require_new_migration_target(bool(exists.stdout.strip()))

    created = _compose(
        env_file, "exec", "--no-TTY", "postgres", "createdb", "--username", "postgres",
        "--owner", "litellm", TARGET_DATABASE,
    )
    if created.returncode:
        raise RuntimeError("could not create the isolated migration database")
    restore = _compose(
        env_file, "exec", "--no-TTY", "postgres", "pg_restore", "--no-owner", "--no-acl",
        "--exit-on-error", "--username", "litellm", "--dbname", TARGET_DATABASE,
        input_bytes=backup_path.read_bytes(),
    )
    if restore.returncode:
        raise RuntimeError(
            f"restore failed; the isolated target database {TARGET_DATABASE!r} is retained for review"
        )
    target_tables = _container_table_count(env_file)
    if target_tables != source_tables:
        raise RuntimeError(
            f"table-count verification failed (source={source_tables}, target={target_tables}); "
            "the source remains unchanged and the isolated target is retained"
        )

    new_content = _replace_database_url(original_env, target_url)
    write_private_file(env_file, new_content)
    cutover = _compose(env_file, "up", "-d", "litellm")
    for _ in range(60):
        health = subprocess.run(
            ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{end}}", "zwslcore-litellm"],
            env=_safe_environment(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=10,
        )
        if cutover.returncode == 0 and health.returncode == 0 and health.stdout.strip() == b"healthy":
            return backup_path, digest, source_tables
        if cutover.returncode != 0:
            break
        time.sleep(2)

    write_private_file(env_file, original_env)
    _compose(env_file, "up", "-d", "litellm")
    raise RuntimeError(
        "LiteLLM did not become healthy on Docker PostgreSQL; .env was restored to its original URL, "
        "and both PostgreSQL copies were retained"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("Usage: postgres_migrate_docker.py [ENV_FILE]", file=sys.stderr)
        return 2
    env_file = Path(args[0]) if args else Path(".env")
    try:
        backup, digest, table_count = migrate(env_file)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"PostgreSQL Docker migration failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"PostgreSQL Docker migration verified: {table_count} tables; "
        f"backup {backup} ({backup.stat().st_size} bytes, sha256 {digest})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
