#!/usr/bin/env python3
"""Validate and preflight the PostgreSQL endpoint configured for Compose."""

from __future__ import annotations

import socket
import sys
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_DOCKER_GATEWAY = "172.18.0.1"


def read_env(path: str | Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            values[key.strip()] = value
    return values


def database_target(values: dict[str, str]) -> tuple[str, int]:
    url = urlsplit(values.get("DATABASE_URL", ""))
    if url.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must use the PostgreSQL scheme")
    host = url.hostname
    if not host:
        raise ValueError("DATABASE_URL must include a hostname")
    if host == "host.docker.internal":
        host = values.get("HOST_DOCKER_INTERNAL_IP", DEFAULT_DOCKER_GATEWAY)
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError("HOST_DOCKER_INTERNAL_IP must be an IP address") from exc
    try:
        parsed_port = url.port
    except ValueError as exc:
        raise ValueError("DATABASE_URL has an invalid port") from exc
    port = 5432 if parsed_port is None else parsed_port
    if not 1 <= port <= 65535:
        raise ValueError("DATABASE_URL port must be between 1 and 65535")
    return host, port


def check(path: str | Path) -> bool:
    try:
        host, port = database_target(read_env(path))
    except (OSError, ValueError) as exc:
        print(f"Invalid PostgreSQL configuration: {exc}")
        return False
    if host == "postgres":
        print("PostgreSQL uses the internal Compose service; runtime health is checked after startup.")
        return True
    try:
        socket.create_connection((host, port), timeout=3).close()
    except OSError as exc:
        print(f"PostgreSQL unreachable at {host}:{port}: {exc}")
        return False
    print(f"PostgreSQL reachable at {host}:{port}")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: postgres_preflight.py ENV_FILE")
    raise SystemExit(0 if check(sys.argv[1]) else 1)
