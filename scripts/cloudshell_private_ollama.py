#!/usr/bin/env python3
"""Fail-closed Cloud Shell Ollama/WARP private route checks (no .env or secrets)."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request

IPV4_PRIVATE = tuple(ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
INTERFACE = re.compile(r"^[A-Za-z0-9_.-]+$")
DEFAULT_CONFIG = Path.home() / ".cloudflared" / "config.yml"


class Failed(RuntimeError):
    pass


def run(*argv: str, timeout: int = 15) -> str:
    try:
        result = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise Failed(f"{argv[0]}: {type(exc).__name__}") from exc
    if result.returncode:
        # CLI errors can include sensitive URLs; do not dump raw stderr.
        raise Failed(f"{argv[0]} {argv[1] if len(argv)>1 else ''}: exit {result.returncode}")
    return result.stdout


def private_ip(interface: str) -> str:
    if not INTERFACE.fullmatch(interface):
        raise Failed("Invalid interface name")
    text = run("ip", "-o", "-4", "addr", "show", "dev", interface, "scope", "global")
    matches = re.findall(r"\binet\s+(\d+\.\d+\.\d+\.\d+)/\d+", text)
    allowed = [ip for ip in matches if any(ipaddress.ip_address(ip) in n for n in IPV4_PRIVATE)]
    if len(allowed) != 1:
        raise Failed(f"Expected one RFC1918 address on {interface}, found {len(allowed)}")
    return allowed[0]


def tunnel_id(config: Path) -> str:
    if config.is_symlink() or not config.is_file():
        raise Failed("Tunnel config missing or symlinked")
    # Read only the config identifier; never print raw config, tokens or credentials.
    found = re.findall(r"^tunnel:\s*([\w-]+)\s*$", config.read_text(), flags=re.M)
    if len(found) != 1 or not UUID.fullmatch(found[0]):
        raise Failed("Expected one UUID tunnel in locally managed config")
    return found[0].lower()


def fetch_json(url: str, timeout: int = 10) -> dict:
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # Limit response size, no secrets in response are printed.
            raw = response.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise Failed("Origin JSON body too large")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise Failed("Invalid JSON object from Ollama")
        return data
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise Failed(f"Ollama HTTP verification failed: {type(exc).__name__}") from exc


def check_model(ip: str, model: str) -> None:
    data = fetch_json(f"http://{ip}:11434/api/tags")
    names = {x.get("name") for x in data.get("models", []) if isinstance(x, dict)}
    if model not in names:
        raise Failed(f"Ollama reachable, but requested model is not available: {model}")
    print(f"OLLAMA_MODEL=PASS model={model}")


def route_lines(text: str, cidr: str) -> list[str]:
    # `cloudflared tunnel route ip show` is table-based. Only match exact CIDR column.
    return [line for line in text.splitlines() if cidr in line.split()]


def local_status(args: argparse.Namespace) -> tuple[str, str]:
    ip = private_ip(args.interface)
    tid = tunnel_id(Path(args.config))
    print(f"CLOUDSHELL_PRIVATE_IP={ip}")
    print(f"CLOUDSHELL_INTERFACE={args.interface}")
    print(f"LOCAL_TUNNEL_ID={tid}")
    check_model(ip, args.model)
    rules = run("cloudflared", "tunnel", "route", "ip", "show", timeout=20)
    match = route_lines(rules, f"{ip}/32")
    print("PRIVATE_ROUTE=" + ("PRESENT" if match else "MISSING"))
    if match:
        # Only print CIDR; show command's comments may be user-sensitive.
        print(f"PRIVATE_ROUTE_CIDR={ip}/32")
    return ip, tid


def local_connector_running(tunnel: str) -> bool:
    """Verify this host, not just Cloudflare control plane, runs the tunnel."""
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            args = (item / "cmdline").read_bytes().split(b"\\0")
            values = [arg.decode("utf-8", errors="replace") for arg in args if arg]
        except (OSError, PermissionError):
            continue
        if values and Path(values[0]).name == "cloudflared" and "run" in values and tunnel in values:
            return True
    return False


def sync_route(args: argparse.Namespace) -> None:
    # A route must terminate at the running Cloud Shell connector, not an unrelated tunnel.
    ip, tid = local_status(args)
    if not args.vnet or not UUID.fullmatch(args.vnet):
        raise Failed("Pass --vnet-id <existing virtual network UUID>; no default inferred")
    if args.tunnel_id and args.tunnel_id.lower() != tid:
        raise Failed("Requested tunnel differs from locally running Cloud Shell tunnel")
    cidr = f"{ip}/32"
    routes = run("cloudflared", "tunnel", "route", "ip", "show", timeout=20)
    existing = route_lines(routes, cidr)
    if existing:
        if len(existing) != 1 or tid not in existing[0].split() or args.vnet not in existing[0].split():
            raise Failed("Existing exact route is not verifiably owned by requested tunnel and virtual network")
        print("ROUTE_SYNC=SKIPPED_VERIFIED_EXISTING")
        return
    if not args.apply:
        print(f"ROUTE_SYNC=DRY_RUN cidr={cidr} tunnel={tid} vnet={args.vnet}")
        print("Re-run with --apply to register the route; previous routes are preserved")
        return
    if not local_connector_running(tid):
        raise Failed("Destination tunnel connector is not running on this Cloud Shell host")
    info = run("cloudflared", "tunnel", "info", tid, timeout=20)
    if "CONNECTOR ID" not in info:
        raise Failed("Cannot verify active Cloud Shell tunnel connector from Cloudflare")
    # CLI args list prevents shell interpolation/injection; no key material is used.
    run("cloudflared", "tunnel", "route", "ip", "add", "--vnet", args.vnet,
        "--comment", "CloudShell Ollama private endpoint", cidr, tid, timeout=30)
    actual = run("cloudflared", "tunnel", "route", "ip", "show", timeout=20)
    verified = route_lines(actual, cidr)
    if len(verified) != 1 or tid not in verified[0].split() or args.vnet not in verified[0].split():
        raise Failed("Route add succeeded but ownership could not be verified by read-back")
    print(f"ROUTE_SYNC=PASS cidr={cidr} tunnel={tid}")
    print("External WARP client connectivity remains NOT VERIFIED; do not delete previous routes yet")


def infer(ip: str, model: str) -> None:
    """Test OpenAI-compatible inference through private network with bounded response."""
    payload = json.dumps({"model": model,
                          "messages": [{"role": "user", "content": "Reply with OK"}],
                          "stream": False, "max_tokens": 16}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{ip}:11434/v1/chat/completions", data=payload, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise Failed("Inference response too large")
        response_data = json.loads(raw)
        choices = response_data.get("choices") or []
        if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
            raise Failed("No message returned from inference")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise Failed(f"OpenAI-compatible inference failed: {type(exc).__name__}") from exc
    print("OPENAI_COMPATIBLE_INFERENCE=PASS")


def client_check(args: argparse.Namespace) -> None:
    ip = str(ipaddress.ip_address(args.ip))
    if not any(ipaddress.ip_address(ip) in n for n in IPV4_PRIVATE):
        raise Failed("Client target must be an RFC1918 private IPv4 address")
    print(f"CLIENT_PRIVATE_TARGET={ip}:11434")
    check_model(ip, args.model)
    if args.infer:
        infer(ip, args.model)
    print("CLIENT_PRIVATE_CONNECTIVITY=PASS (HTTP API and model inventory reachable from this client)")
    print("ZWORKFORCE_PROVIDER_BASE_URL=http://" + ip + ":11434/v1")
    print("ZWORKFORCE_MODEL_LUNA=" + args.model)
    print("ZWORKFORCE_MODEL_TERRA=" + args.model)
    print("ZWORKFORCE_MODEL_SOL=" + args.model)
    print("NOTE=Provider config must be applied on zWorkforce host; credentials are not read or modified")
    print("NOTE=Ollama has no built-in API authentication: enforce WARP device/network policies")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("status", "sync-route", "client-check"):
        sp = sub.add_parser(name)
        sp.add_argument("--model", default="qwen2.5-coder:7b")
        if name in ("status", "sync-route"):
            sp.add_argument("--interface", default="eth0")
            sp.add_argument("--config", default=str(DEFAULT_CONFIG))
        if name == "sync-route":
            sp.add_argument("--vnet-id", dest="vnet", required=True)
            sp.add_argument("--tunnel-id", default=None)
            sp.add_argument("--apply", action="store_true", help="Register new /32 route, never remove existing routes")
        if name == "client-check":
            sp.add_argument("--ip", required=True, help="Private IP discovered on Cloud Shell")
            sp.add_argument("--infer", action="store_true", help="Run live OpenAI-compatible inference")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "status":
            local_status(args)
        elif args.action == "sync-route":
            sync_route(args)
        else:
            client_check(args)
    except (Failed, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())