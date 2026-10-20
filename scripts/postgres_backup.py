#!/usr/bin/env python3
"""Create a private, verified PostgreSQL custom-format backup."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from postgres_preflight import database_target
from services.engineering.secure_storage import ensure_private_directory, reject_symlink_components


def _private_env(path: Path) -> dict[str, str]:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise ValueError("environment file must be a readable regular non-symlink file") from exc
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("environment file must be a regular file")
            if info.st_size > 1_000_000:
                raise ValueError("environment file is too large")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("environment file permissions are too open; run chmod 600")
            values: dict[str, str] = {}
            for raw_line in stream:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                        value = value[1:-1]
                    values[key.strip()] = value
            return values
    except UnicodeError as exc:
        raise ValueError("environment file must be UTF-8") from exc


def _connection(values: dict[str, str]) -> tuple[str, int, str, str, str]:
    raw_url = values.get("DATABASE_URL", "")
    url = urlsplit(raw_url)
    if url.scheme not in ("postgres", "postgresql") or not url.hostname:
        raise ValueError("DATABASE_URL must be a PostgreSQL URL with a host")
    host, port = database_target(values)
    # Compose resolves host.docker.internal to the bridge gateway. Backup runs
    # on the host, where that same PostgreSQL instance is reachable on loopback.
    if url.hostname == "host.docker.internal":
        host = "127.0.0.1"
    user = unquote(url.username or "")
    password = unquote(url.password or "")
    database = unquote(url.path.lstrip("/"))
    if not user or not password or not database:
        raise ValueError("DATABASE_URL must include username, password, and database")
    return host, port, user, password, database


def _destination(path: Path | None) -> Path:
    if path is None:
        try:
            directory = ensure_private_directory(Path.home() / ".zwslcore" / "backups" / "postgres")
        except PermissionError as exc:
            raise ValueError("PostgreSQL backup directory must be private and contain no symlinks") from exc
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = directory / f"litellm-{stamp}-{secrets.token_hex(3)}.dump"
    else:
        path = Path(os.path.abspath(path.expanduser()))
        try:
            reject_symlink_components(path)
        except PermissionError as exc:
            raise ValueError("backup destination must not contain symlink path components") from exc
    if path.exists() or path.is_symlink():
        raise FileExistsError("refusing to overwrite an existing backup destination")
    if not path.parent.is_dir():
        raise ValueError("backup destination parent directory must already exist")
    return path


def create_backup(env_file: Path, destination: Path | None) -> tuple[Path, str, int]:
    values = _private_env(env_file)
    host, port, user, password, database = _connection(values)
    database_url = urlsplit(values["DATABASE_URL"])
    output = _destination(destination)
    pg_dump = shutil.which("pg_dump")
    pg_restore = shutil.which("pg_restore")
    docker = shutil.which("docker") if database_url.hostname == "postgres" else None
    if (database_url.hostname == "postgres" and not docker) or not pg_restore:
        raise RuntimeError("docker and pg_restore are required for the Compose PostgreSQL service")
    if database_url.hostname != "postgres" and not pg_dump:
        raise RuntimeError("pg_dump and pg_restore are required")

    fd, temporary_name = tempfile.mkstemp(prefix=".zwslcore-postgres-", suffix=".dump", dir=output.parent)
    temporary = Path(temporary_name)
    os.fchmod(fd, 0o600)
    os.close(fd)
    child_env = {
        key: os.environ[key]
        for key in (
            "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "DOCKER_CONFIG",
            "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH",
            "SSH_AUTH_SOCK",
        )
        if key in os.environ
    }
    dump_env = child_env | ({"PGPASSWORD": password} if database_url.hostname != "postgres" else {})
    sslmode = database_url.query
    if sslmode:
        # Pass only libpq connection options, never the original credential-bearing URL.
        for item in sslmode.split("&"):
            key, separator, value = item.partition("=")
            if separator and key == "sslmode":
                dump_env["PGSSLMODE"] = value
    if database_url.hostname == "postgres":
        root = Path(__file__).resolve().parents[1]
        command = [
            docker, "compose", "--project-directory", str(root),
            "--file", str(root / "compose.yaml"), "--env-file", str(env_file),
            "exec", "--no-TTY", "postgres", "pg_dump", "--format=custom",
            "--no-owner", "--no-acl", "--username", user, "--dbname", database,
        ]
    else:
        command = [
            pg_dump, "--no-password", "--format=custom", "--no-owner", "--no-acl",
            "--host", host, "--port", str(port), "--username", user,
            "--dbname", database, "--file", str(temporary),
        ]
    try:
        if database_url.hostname == "postgres":
            with temporary.open("wb") as archive:
                result = subprocess.run(command, env=dump_env, stdout=archive,
                                        stderr=subprocess.PIPE, check=False, timeout=1800)
        else:
            result = subprocess.run(command, env=dump_env, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, check=False, timeout=1800)
        if result.returncode:
            raise RuntimeError(f"pg_dump failed with exit status {result.returncode}")
        checked = subprocess.run(
            [pg_restore, "--list", str(temporary)], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=60, env=child_env,
        )
        if checked.returncode or not checked.stdout.strip():
            raise RuntimeError("pg_restore could not read the generated archive")
        with temporary.open("rb") as archive:
            os.fsync(archive.fileno())
        os.link(temporary, output)
        temporary.unlink()
        with output.open("rb") as archive:
            digest = hashlib.file_digest(archive, "sha256").hexdigest()
        directory_fd = os.open(output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return output, digest, output.stat().st_size
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, help="new backup file; default is an owner-only local backup directory")
    args = parser.parse_args(argv)
    try:
        path, digest, size = create_backup(args.env_file, args.output)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"PostgreSQL backup failed: {exc}", file=sys.stderr)
        return 1
    print(f"PostgreSQL backup verified: {path} ({size} bytes, sha256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
