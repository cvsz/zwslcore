#!/usr/bin/env python3
"""Audit the existing AI stack port map without changing Cloudflare or reading .env."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import socket
import sys
import urllib.error
import urllib.request

MANIFEST = Path(__file__).resolve().parents[1] / "config" / "ai-stack-port-map.json"
HOSTNAME = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
PUBLIC_ROLES = frozenset({"ssh", "api", "webui"})
INTERNAL_ONLY = frozenset({"ollama", "litellm", "signed-webhook"})


class PortMapError(ValueError):
    """An unsafe or invalid AI stack public mapping."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_profile(profile: str) -> list[dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or profile not in data.get("profiles", {}):
        raise PortMapError("Unknown or incompatible AI stack profile")
    rows = data["profiles"][profile]
    if not isinstance(rows, list) or not rows:
        raise PortMapError("Port map requires a non-empty list")
    seen_names: set[str] = set()
    seen_ports: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PortMapError("Invalid service entry")
        name, port, role = row.get("name"), row.get("host_port"), row.get("hostname_role")
        if not isinstance(name, str) or name in seen_names:
            raise PortMapError("Duplicate or invalid service")
        if type(port) is not int or not 1 <= port <= 65535 or port in seen_ports:
            raise PortMapError("Duplicate or invalid host port")
        if role is not None and role not in PUBLIC_ROLES:
            raise PortMapError("Unknown public role")
        if name in INTERNAL_ONLY and (role is not None or row.get("exposure") != "private"):
            raise PortMapError("Internal AI service cannot be publicly routed")
        if role is None and row.get("exposure") != "private":
            raise PortMapError("Unrouted service must be private")
        if row.get("protocol") not in ("ssh", "http"):
            raise PortMapError("Unsupported protocol")
        if type(row.get("service_port")) is not int or not 1 <= row["service_port"] <= 65535:
            raise PortMapError("Invalid container port")
        seen_names.add(name)
        seen_ports.add(port)
    return rows


def domains(ssh: str, api: str, webui: str) -> dict[str, str]:
    mapped = {"ssh": ssh, "api": api}
    if webui:
        mapped["webui"] = webui
    if not all(HOSTNAME.fullmatch(value or "") for value in mapped.values()):
        raise PortMapError("Explicit valid public hostnames are required")
    if len(set(value.lower() for value in mapped.values())) != len(mapped):
        raise PortMapError("SSH, API and WebUI must use distinct hostnames")
    return mapped


def ingress_preview(rows: list[dict], hosts: dict[str, str]) -> str:
    """Print a non-mutating preview, never replace a running tunnel config."""
    lines = [
        "# NON-APPLYING PREVIEW ONLY. Keep existing tunnel ID, SSH and webhook ingress.",
        "# Do not overwrite ~/.cloudflared/config.yml with this snippet.",
        "ingress:",
    ]
    assigned: set[str] = set()
    for row in rows:
        role = row["hostname_role"]
        if role is None or role not in hosts:
            continue
        assigned.add(role)
        port = row["host_port"]
        scheme = "ssh" if role == "ssh" else "http"
        lines.extend([f"  - hostname: {hosts[role]}", f"    service: {scheme}://127.0.0.1:{port}"])
    if not {"ssh", "api"}.issubset(assigned):
        raise PortMapError("Selected profile lacks required SSH or Provider entry")
    lines.append("  - service: http_status:404")
    return "\n".join(lines) + "\n"


def _request_code(port: int, path: str) -> int:
    url = f"http://127.0.0.1:{port}{path}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=3) as response:
            response.read(1)
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (OSError, TimeoutError, ValueError, urllib.error.URLError):
        return 0


def _tcp_up(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def probe(row: dict) -> bool:
    """Health is origin-only. Public DNS, Access and remote clients are separate."""
    port = row["host_port"]
    endpoint = row["check"]
    if endpoint == "tcp":
        return _tcp_up(port)
    if endpoint == "provider":
        return (_request_code(port, "/health/live") == 200
                and _request_code(port, "/v1/models") in (401, 403))
    return _request_code(port, endpoint) == 200


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("map", "ingress-preview", "verify-local"))
    parser.add_argument("--profile", choices=("cloudshell", "compose"), default="cloudshell")
    parser.add_argument("--ssh-host", default="")
    parser.add_argument("--api-host", default="")
    parser.add_argument("--webui-host", default="")
    args = parser.parse_args(argv)
    try:
        rows = load_profile(args.profile)
        if args.action == "ingress-preview":
            print(ingress_preview(rows, domains(args.ssh_host, args.api_host, args.webui_host)), end="")
        elif args.action == "map":
            hosts = (domains(args.ssh_host, args.api_host, args.webui_host)
                     if args.ssh_host or args.api_host or args.webui_host else {})
            print("SERVICE\tHOST:PORT\tCONTAINER:PORT\tPUBLIC HOST\tEXPOSURE")
            for row in rows:
                role = row["hostname_role"]
                public = hosts.get(role, "OPTIONAL" if role == "webui" else "PRIVATE")
                print(f"{row['name']}\t127.0.0.1:{row['host_port']}\t"
                      f"{row['service_port']}\t{public}\t{row['exposure']}")
        else:
            missing = False
            for row in rows:
                ok = probe(row)
                if row["required"] and not ok:
                    missing = True
                status = "PASS" if ok else "NOT_RUNNING_OR_UNVERIFIED"
                print(f"{row['name']}={status} required={row['required']}")
            print("PUBLIC_DNS_ACCESS_AND_EXTERNAL_E2E=NOT_VERIFIED")
            return 1 if missing else 0
        return 0
    except (PortMapError, OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
