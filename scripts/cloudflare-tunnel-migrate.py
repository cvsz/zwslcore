#!/usr/bin/env python3
"""Fail-closed staging for migrating an existing Cloudflare SSH hostname.

This tool never edits the active config, starts/stops connectors, updates DNS,
or changes Cloudflare Access. Those require independent runtime evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile
import uuid

DEFAULT_CONFIG = Path.home() / ".cloudflared" / "config.yml"
DEFAULT_STATE = Path.home() / ".local" / "state" / "zwslcore-tunnel-migration"
CONFIG_KEY = re.compile(r"^([ \t]*)(tunnel|credentials-file):[ \t]*(.+?)[ \t]*$", re.M)


class MigrationError(Exception):
    """A required safety check failed."""


def private_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise MigrationError(f"Missing or symlinked file: {path}")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise MigrationError(f"File must be owned by current user and private: {path}")


def run_cloudflared(*args: str) -> str:
    try:
        p = subprocess.run(
            ["cloudflared", *args], check=False, capture_output=True, text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MigrationError(f"cloudflared unavailable or timed out: {type(exc).__name__}") from exc
    if p.returncode:
        # The external tool may print sensitive URLs or details; do not echo its output.
        raise MigrationError(f"cloudflared command failed (exit {p.returncode})")
    return p.stdout


def read_config(path: Path) -> tuple[str, str]:
    private_file(path)
    text = path.read_text(encoding="utf-8")
    fields: dict[str, list[str]] = {"tunnel": [], "credentials-file": []}
    for match in CONFIG_KEY.finditer(text):
        if not match.group(1):
            fields[match.group(2)].append(match.group(3).strip().strip("\"'"))
    if len(fields["tunnel"]) != 1 or len(fields["credentials-file"]) != 1:
        raise MigrationError("Expected exactly one top-level tunnel and credentials-file")
    return text, fields["tunnel"][0]


def ssh_ingress_present(config: str, hostname: str) -> bool:
    lines = config.splitlines()
    matches = [i for i, line in enumerate(lines)
               if re.fullmatch(r"[ \t]*-[ \t]*hostname:[ \t]*" +
                               re.escape(hostname) + r"[ \t]*", line)]
    if len(matches) != 1:
        return False
    pos = matches[0]
    # Reject a path rule: SSH must be a hostname-wide service mapping.
    for line in lines[pos + 1:pos + 4]:
        if re.match(r"[ \t]*-[ \t]*(hostname|service):", line):
            break
        if re.match(r"[ \t]*path:", line):
            return False
        if re.fullmatch(r"[ \t]*service:[ \t]*ssh://127\.0\.0\.1:22[ \t]*", line):
            return True
    return False


def ssh_listener_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 22), timeout=2):
            return True
    except OSError:
        return False


def validated_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise MigrationError("Set a valid ZWSL_TARGET_TUNNEL_ID") from exc


def target_credentials_ready(path: Path, target: str) -> None:
    private_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise MigrationError("Destination tunnel credential JSON is invalid") from exc
    if not isinstance(data, dict) or data.get("TunnelID", "").lower() != target:
        raise MigrationError("Credential file belongs to a different tunnel")


def render_staged_config(source: str, target: str, destination_creds: Path) -> str:
    hits = {"tunnel": 0, "credentials-file": 0}

    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(0)
        key = match.group(2)
        hits[key] += 1
        value = target if key == "tunnel" else str(destination_creds)
        return f"{key}: {value}"

    result = CONFIG_KEY.sub(replace, source)
    if hits != {"tunnel": 1, "credentials-file": 1}:
        raise MigrationError("Ambiguous top-level tunnel configuration")
    return result


def stage(config: Path, state: Path, target: str, creds: Path,
          source: str, hostname: str) -> Path:
    target_credentials_ready(creds, target)
    if not ssh_ingress_present(source, hostname):
        raise MigrationError("SSH hostname ingress to 127.0.0.1:22 not found")
    if not ssh_listener_ready():
        raise MigrationError("SSH is not listening on 127.0.0.1:22")
    staged_text = render_staged_config(source, target, creds.resolve())
    if state.is_symlink():
        raise MigrationError("State directory must not be a symlink")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state.stat().st_uid != os.getuid() or stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise MigrationError("State directory must be private")
    staged = state / "staged-config.yml"
    if staged.exists() or staged.is_symlink():
        raise MigrationError("Staged configuration exists; inspect it before replacing")
    fd, temp = tempfile.mkstemp(prefix=".stage-", dir=state)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(staged_text)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp, 0o600)
        run_cloudflared("tunnel", "--config", temp, "ingress", "validate")
        os.replace(temp, staged)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return staged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "stage"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--target-id", default=os.getenv("ZWSL_TARGET_TUNNEL_ID", ""))
    parser.add_argument("--hostname", default=os.getenv("ZCLOUD_HOSTNAME", ""))
    parser.add_argument("--target-credentials", type=Path, default=None)
    args = parser.parse_args()
    try:
        target = validated_uuid(args.target_id)
        if not re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", args.hostname):
            raise MigrationError("Set ZCLOUD_HOSTNAME to the existing authorized SSH hostname")
        source, active = read_config(args.config)
        if active == target:
            raise MigrationError("Active config already names destination; verify connector runtime")
        if not ssh_ingress_present(source, args.hostname):
            raise MigrationError("Expected SSH hostname route to ssh://127.0.0.1:22")
        run_cloudflared("tunnel", "--config", str(args.config), "ingress", "validate")
        print(f"ACTIVE_CONFIG_TUNNEL={active}")
        print(f"DESTINATION_TUNNEL={target}")
        print(f"ORIGIN_SSH_LOOPBACK={'PASS' if ssh_listener_ready() else 'FAIL'}")
        if args.action == "inspect":
            # This is *not* remote Access, DNS, or identity-policy verification.
            print("DNS_ACCESS_REMOTE_CONNECTOR=NOT_VERIFIED")
            print("NO_CHANGES_MADE")
            return 0
        creds = args.target_credentials or (Path.home() / ".cloudflared" / f"{target}.json")
        staged = stage(args.config, args.state, target, creds, source, args.hostname)
        print(f"STAGED_CONFIG={staged}")
        print("ACTIVE_CONFIG_UNCHANGED")
        print("CUTOVER_BLOCKED: verify destination connector placement, Access, DNS, and SSH E2E")
        return 0
    except (MigrationError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
