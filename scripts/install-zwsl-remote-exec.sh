#!/usr/bin/env bash
# Install a local stdio MCP diagnostics server; it never exposes a network listener.
set -Eeuo pipefail
umask 077
BASE="${ZWSL_MCP_HOME:-$HOME/.local/share/zwsl-remote-exec}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLOUD_CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
CLOUDFLARED="$(command -v cloudflared || true)"
case "${1:-help}" in
  install)
    command -v python3 >/dev/null || exit 1
    mkdir -p "$BASE"; chmod 700 "$BASE"
    python3 -m venv "$BASE/.venv"
    "$BASE/.venv/bin/python" -m pip install --disable-pip-version-check 'mcp>=1.12,<2'
    # Persist only validated location metadata. The MCP server has no need for
    # .env files, tunnel credentials or runtime shell interpolation.
    ZWSL_MCP_REPO_ROOT="$ROOT" ZWSL_MCP_CLOUD_CONFIG="$CLOUD_CONFIG" \
    ZWSL_MCP_CLOUDFLARED="$CLOUDFLARED" python3 - "$BASE/paths.json" <<'PYPATHS'
import json
import os
from pathlib import Path
import sys

target = Path(sys.argv[1])
paths = {
    "repository": str(Path(os.environ["ZWSL_MCP_REPO_ROOT"]).absolute()),
    "cloudflared_config": str(Path(os.environ["ZWSL_MCP_CLOUD_CONFIG"]).expanduser().absolute()),
    "cloudflared_bin": os.environ["ZWSL_MCP_CLOUDFLARED"],
}
target.write_text(json.dumps(paths, sort_keys=True) + "\n")
target.chmod(0o600)
PYPATHS
    cat > "$BASE/server.py" <<'PYMCP'
"""Read-only, stdio-only MCP diagnostics. Never expose arbitrary shell execution."""
from __future__ import annotations
import json
import os
from pathlib import Path
import selectors
import subprocess
import time
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ZWSL Cloud Shell Diagnostics")
HOME = Path.home()
PATHS = json.loads(Path(__file__).with_name("paths.json").read_text())
REPO = Path(PATHS["repository"])
CLOUD_CONFIG = Path(PATHS["cloudflared_config"])
CLOUDFLARED = PATHS["cloudflared_bin"]

def run_fixed(argv: list[str]) -> str:
    """Stream fixed-command output with an 8 KiB hard cap and 10s deadline."""
    env = {"HOME": str(HOME), "PATH": "/usr/local/bin:/usr/bin:/bin",
           "LANG": "C.UTF-8", "GIT_OPTIONAL_LOCKS": "0"}
    proc = None
    try:
        proc = subprocess.Popen(argv, cwd=HOME, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env=env)
        captured = bytearray()
        truncated = False
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 10
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise subprocess.TimeoutExpired(argv, 10)
                chunk = os.read(proc.stdout.fileno(), min(4096, 8001 - len(captured)))
                if not chunk:
                    break
                captured.extend(chunk)
                if len(captured) > 8000:
                    truncated = True
                    break
        if truncated:
            proc.kill()
        exit_code = proc.wait(timeout=2)
        message = captured[:8000].decode("utf-8", errors="replace")
        if truncated:
            message += "\n[TRUNCATED at 8000 bytes]"
        return f"exit_code={exit_code}\n" + message
    except (OSError, subprocess.TimeoutExpired) as exc:
        return type(exc).__name__
    finally:
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if proc.stdout:
                proc.stdout.close()

@mcp.tool()
def system_identity() -> str:
    """Report local account and kernel metadata."""
    return run_fixed(["/usr/bin/id", "-un"]) + run_fixed(["/usr/bin/uname", "-a"])

@mcp.tool()
def repository_status() -> str:
    """Read git status for the expected repository only."""
    if not (REPO / ".git").exists():
        return "repository_missing"
    return run_fixed(["/usr/bin/git", "-C", str(REPO), "status", "--short", "--branch"])

@mcp.tool()
def ssh_listener() -> str:
    """Report listening sockets without opening or altering ports."""
    return run_fixed(["/usr/bin/ss", "-lnt"])

@mcp.tool()
def cloudflare_ingress() -> str:
    """Validate tunnel config without printing credentials or opening traffic."""
    if not CLOUD_CONFIG.is_file() or CLOUD_CONFIG.is_symlink():
        return "config_missing_or_symlink"
    if not CLOUDFLARED or not Path(CLOUDFLARED).is_file():
        return "cloudflared_binary_missing"
    return run_fixed([CLOUDFLARED, "tunnel", "--config",
                      str(CLOUD_CONFIG), "ingress", "validate"])

if __name__ == "__main__":
    mcp.run(transport="stdio")
PYMCP
    chmod 600 "$BASE/server.py"
    "$BASE/.venv/bin/python" -m py_compile "$BASE/server.py"
    echo "Installed local read-only MCP server: $BASE/server.py"
    echo "External ChatGPT connectivity requires a separately configured authenticated MCP transport."
    ;;
  check)
    [[ -f "$BASE/server.py" && -f "$BASE/paths.json" && -x "$BASE/.venv/bin/python" ]] || exit 1
    "$BASE/.venv/bin/python" -m py_compile "$BASE/server.py"
    echo "Syntax OK. This does not prove remote connectivity."
    ;;
  *) echo "Usage: $0 {install|check}" ;;
esac
