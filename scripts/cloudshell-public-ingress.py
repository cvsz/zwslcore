#!/usr/bin/env python3
"""Stage and verify protected public API ingress without interrupting existing SSH.

A DNS write needs explicit Cloudflare API credentials and compare-and-swap
approval. The script never restarts a connector or changes Cloudflare Access.
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
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "zwslcore-public-ingress"
CONFIG_DEFAULT = Path.home() / ".cloudflared" / "config.yml"
API_ORIGIN = "http://127.0.0.1:8080"
CF_API = "https://api.cloudflare.com/client/v4"
TUNNEL_PATTERN = re.compile(r"^tunnel:\s*([0-9a-fA-F-]{36})\s*$", re.M)
HOST_PATTERN = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
HEX32_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


class Blocked(RuntimeError):
    pass


def private_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Blocked("Tunnel config is missing or symlinked")
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise Blocked("Tunnel config must be owned by current user and private")
    return path.read_text(encoding="utf-8")


def tunnel_id(source: str) -> str:
    values = TUNNEL_PATTERN.findall(source)
    if len(values) != 1:
        raise Blocked("Expected exactly one top-level tunnel UUID")
    try:
        return str(uuid.UUID(values[0]))
    except ValueError as exc:
        raise Blocked("Invalid locally managed tunnel UUID") from exc


def local_ssh() -> None:
    try:
        with socket.create_connection(("127.0.0.1", 22), timeout=2):
            pass
    except OSError as exc:
        raise Blocked("SSH loopback port 22 is unavailable") from exc


def preserve_ssh(source: str, host: str) -> None:
    matches = re.findall(r"(?m)^[ \t]*-[ \t]*hostname:[ \t]*" + re.escape(host) + r"[ \t]*$", source)
    if len(matches) != 1:
        raise Blocked("Existing SSH ingress hostname missing or ambiguous")
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if re.fullmatch(r"[ \t]*-[ \t]*hostname:[ \t]*" + re.escape(host) + r"[ \t]*", line):
            after = lines[i + 1:i + 4]
            if any(re.fullmatch(r"[ \t]*service:[ \t]*ssh://127\.0\.0\.1:22[ \t]*", a) for a in after):
                return
    raise Blocked("Existing SSH ingress does not point to loopback port 22")


def render(source: str, api_host: str, ssh_host: str) -> str:
    if not HOST_PATTERN.fullmatch(api_host) or not HOST_PATTERN.fullmatch(ssh_host) or api_host == ssh_host:
        raise Blocked("Specify distinct valid DNS hostnames")
    preserve_ssh(source, ssh_host)
    lines = source.splitlines(keepends=True)
    api_hits = [i for i, x in enumerate(lines) if x.strip() == "- hostname: " + api_host]
    if api_hits:
        if len(api_hits) != 1:
            raise Blocked("Multiple API hostname ingress rules")
        i = api_hits[0]
        if i + 1 < len(lines) and lines[i + 1].strip() == "service: " + API_ORIGIN:
            return source
        raise Blocked("Existing API ingress has another origin; refuse overwrite")
    fallback = [i for i, x in enumerate(lines) if x.strip() == "- service: http_status:404"]
    if len(fallback) != 1 or fallback[0] != len(lines) - 1:
        raise Blocked("Expected exactly one final fallback ingress")
    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    i = fallback[0]
    indent = lines[i].split("-", 1)[0]
    lines[i:i] = [indent + "- hostname: " + api_host + "\n",
                  indent + "  service: " + API_ORIGIN + "\n"]
    result = "".join(lines)
    preserve_ssh(result, ssh_host)
    return result


def run_cloudflared(config: Path) -> None:
    try:
        result = subprocess.run(["cloudflared", "tunnel", "--config", str(config), "ingress", "validate"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=20, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise Blocked("cloudflared ingress validation unavailable") from exc
    if result.returncode:
        raise Blocked("cloudflared ingress validation failed")


def origin_auth_verified() -> None:
    # Use the existing Provider, not an unauthenticated Ollama listener.
    import importlib.util
    module_path = ROOT / "scripts" / "cloudshell-provider-runtime.py"
    spec = importlib.util.spec_from_file_location("zwsl_provider_runtime", module_path)
    if not spec or not spec.loader:
        raise Blocked("Provider runtime checker missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify()


def stage(config: Path, ssh_host: str, api_host: str) -> tuple[Path, str]:
    source = private_file(config)
    tid = tunnel_id(source)
    local_ssh()
    origin_auth_verified()
    changed = render(source, api_host, ssh_host)
    if STATE.is_symlink():
        raise Blocked("State directory cannot be symlinked")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if STATE.stat().st_uid != os.getuid() or stat.S_IMODE(STATE.stat().st_mode) & 0o077:
        raise Blocked("State directory must be owner-only")
    staged = STATE / "candidate.yml"
    if staged.is_symlink():
        raise Blocked("Candidate configuration cannot be symlinked")
    if staged.exists() and private_file(staged) != changed:
        raise Blocked("Existing staged candidate differs; review before replacing")
    if not staged.exists():
        fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(changed)
    run_cloudflared(staged)
    return staged, tid


def apply_ingress(config: Path, ssh_host: str, api_host: str) -> None:
    if os.getenv("ZWSL_API_ACCESS_VERIFIED") != "YES":
        raise Blocked("Cloudflare Access policy must be separately verified before apply")
    source = private_file(config)
    candidate, tid = stage(config, ssh_host, api_host)
    replacement = private_file(candidate)
    if source == replacement:
        print("INGRESS=ALREADY_CONFIGURED")
        return
    # Refuse overwriting changes by another operator since staging began.
    if private_file(config) != source:
        raise Blocked("Tunnel config changed concurrently")
    backup = STATE / ("backup-" + str(time.time_ns()) + ".yml")
    fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(source)
        output.flush()
        os.fsync(output.fileno())
    fd, temp = tempfile.mkstemp(prefix=".api-ingress-", dir=config.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(replacement)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, config)
    finally:
        Path(temp).unlink(missing_ok=True)
    (STATE / "last-backup").write_text(str(backup) + "\n")
    (STATE / "last-backup").chmod(0o600)
    print("INGRESS=APPLIED tunnel=" + tid)
    print("CONNECTOR_RELOAD=REQUIRED: restart via existing supervisor after SSH/Access maintenance plan")
    print("DNS=UNCHANGED")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise Blocked("Cloudflare API unexpectedly redirected")


def cf_request(method: str, path: str, payload: dict | None = None) -> dict:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not token:
        raise Blocked("CLOUDFLARE_API_TOKEN required in process environment")
    url = CF_API + path
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "Accept": "application/json",
    })
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=12) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise Blocked("Cloudflare API response exceeds limit")
        data = json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        if isinstance(exc, Blocked):
            raise
        code = getattr(exc, "code", None)
        raise Blocked("Cloudflare API request failed" + (f" HTTP {code}" if code else "")) from exc
    if not isinstance(data, dict) or data.get("success") is not True:
        raise Blocked("Cloudflare API rejected or returned malformed response")
    return data


def dns_records(zone_id: str, host: str) -> list[dict]:
    params = urllib.parse.urlencode({"name": host, "per_page": "100"})
    data = cf_request("GET", f"/zones/{zone_id}/dns_records?{params}")
    items = data.get("result")
    if not isinstance(items, list) or len(items) > 1:
        raise Blocked("DNS record count is ambiguous; manual review required")
    return items


def dns(args: argparse.Namespace, commit: bool) -> None:
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "")
    if not HEX32_PATTERN.fullmatch(zone_id):
        raise Blocked("Set an exact CLOUDFLARE_ZONE_ID")
    if not HOST_PATTERN.fullmatch(args.zone) or not args.api_host.endswith("." + args.zone):
        raise Blocked("API hostname must be in the specified Cloudflare zone")
    config = Path(args.config)
    source = private_file(config)
    expected_target = tunnel_id(source) + ".cfargotunnel.com"
    if commit:
        if os.getenv("ZWSL_API_ACCESS_VERIFIED") != "YES":
            raise Blocked("Cloudflare Access verification is required for DNS writes")
        if "- hostname: " + args.api_host not in source:
            raise Blocked("Active local ingress must be configured before DNS write")
        origin_auth_verified()
    zone = cf_request("GET", f"/zones/{zone_id}").get("result", {})
    if zone.get("name") != args.zone:
        raise Blocked("Zone ID and expected DNS zone name do not match")
    items = dns_records(zone_id, args.api_host)
    current = items[0] if items else None
    if current and current.get("type") != "CNAME":
        raise Blocked("Existing API record is not a CNAME; refuse destructive replacement")
    if current and current.get("content", "").rstrip(".").lower() == expected_target.lower() and current.get("proxied") is True:
        print("DNS=ALREADY_CORRECT")
        return
    print("DNS_EXPECTED_CNAME=" + expected_target)
    print("DNS_CURRENT=" + (str(current.get("content", "")) if current else "MISSING"))
    if not commit:
        print("DNS_WRITE=DRY_RUN")
        return
    if current and (not args.expect_cname or current.get("content", "").rstrip(".").lower() != args.expect_cname.rstrip(".").lower()):
        raise Blocked("Existing CNAME mismatch; supply exact --expect-cname for approved cutover")
    backup = STATE / ("dns-before-" + str(time.time_ns()) + ".json")
    if not STATE.exists() or STATE.is_symlink():
        raise Blocked("Run ingress stage first; secure state directory required")
    fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump({"api_host": args.api_host, "previous": current}, output)
        output.flush()
        os.fsync(output.fileno())
    spec = {"type": "CNAME", "name": args.api_host, "content": expected_target, "proxied": True}
    if current:
        if not isinstance(current.get("id"), str) or not HEX32_PATTERN.fullmatch(current["id"]):
            raise Blocked("Existing DNS record ID invalid")
        cf_request("PUT", f"/zones/{zone_id}/dns_records/{current['id']}", spec)
    else:
        cf_request("POST", f"/zones/{zone_id}/dns_records", spec)
    after = dns_records(zone_id, args.api_host)
    if len(after) != 1 or after[0].get("content", "").rstrip(".").lower() != expected_target or after[0].get("proxied") is not True:
        raise Blocked("DNS updated but read-back did not confirm expected CNAME and proxy")
    print("DNS=APPLIED_AND_READBACK_VERIFIED")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "stage", "apply-ingress", "dns-plan", "dns-apply", "rollback"))
    parser.add_argument("--config", default=str(CONFIG_DEFAULT))
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--api-host", required=True)
    parser.add_argument("--zone", required=True)
    parser.add_argument("--expect-cname", default="")
    args = parser.parse_args(argv)
    try:
        config = Path(args.config)
        if args.action == "inspect":
            source = private_file(config)
            print("TUNNEL_ID=" + tunnel_id(source))
            print("SSH_ROUTE=PRESERVED" if preserve_ssh(source, args.ssh_host) is None else "SSH_ROUTE=FAIL")
            print("API_ROUTE=CONFIGURED" if "- hostname: " + args.api_host in source else "API_ROUTE=MISSING")
        elif args.action == "stage":
            _, tid = stage(config, args.ssh_host, args.api_host)
            print("INGRESS=STAGED tunnel=" + tid + " (no live changes)")
        elif args.action == "apply-ingress":
            apply_ingress(config, args.ssh_host, args.api_host)
        elif args.action in ("dns-plan", "dns-apply"):
            dns(args, args.action == "dns-apply")
        elif args.action == "rollback":
            last = STATE / "last-backup"
            backup = Path(private_file(last).strip())
            if backup.parent != STATE:
                raise Blocked("Invalid rollback backup location")
            old = private_file(backup)
            preserve_ssh(old, args.ssh_host)
            run_cloudflared(backup)
            current = private_file(config)
            # Do not overwrite changes since our route was applied.
            if "- hostname: " + args.api_host not in current:
                raise Blocked("Current API route not owned by this rollback")
            fd, temp = tempfile.mkstemp(prefix=".rollback-", dir=config.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    file.write(old)
                    file.flush()
                    os.fsync(file.fileno())
                os.chmod(temp, 0o600)
                os.replace(temp, config)
            finally:
                Path(temp).unlink(missing_ok=True)
            print("INGRESS=ROLLED_BACK; connector reload required; DNS unchanged")
        return 0
    except (Blocked, OSError, ValueError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
