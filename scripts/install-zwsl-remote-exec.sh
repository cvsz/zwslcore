#!/usr/bin/env bash
# Install a local stdio MCP diagnostics server; it never exposes a network listener.
set -Eeuo pipefail
umask 077
BASE="${ZWSL_MCP_HOME:-$HOME/.local/share/zwsl-remote-exec}"
case "${1:-help}" in
  install)
    command -v python3 >/dev/null || exit 1
    mkdir -p "$BASE"; chmod 700 "$BASE"
    python3 -m venv "$BASE/.venv"
    "$BASE/.venv/bin/python" -m pip install --disable-pip-version-check 'mcp>=1.12,<2'
    cat > "$BASE/server.py" <<'PYMCP'
"""Read-only, stdio-only MCP diagnostics. Never expose arbitrary shell execution."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ZWSL Cloud Shell Diagnostics")
HOME = Path.home()
REPO = (HOME / "zwslcore").resolve()

def run_fixed(argv: list[str]) -> str:
    """Run a fixed allowlisted command, with bounded output and timeout."""
    try:
        p = subprocess.run(argv, cwd=HOME, capture_output=True,
                           text=True, timeout=10, check=False,
                           env={"HOME": str(HOME), "PATH": "/usr/local/bin:/usr/bin:/bin",
                                "LANG": "C.UTF-8"})
        return f"exit_code={p.returncode}\n" + (p.stdout + p.stderr)[:8000]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return type(exc).__name__

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
    config = HOME / ".cloudflared/config.yml"
    if not config.is_file() or config.is_symlink():
        return "config_missing_or_symlink"
    return run_fixed(["/usr/local/bin/cloudflared", "tunnel", "--config",
                      str(config), "ingress", "validate"])

if __name__ == "__main__":
    mcp.run(transport="stdio")
PYMCP
    chmod 600 "$BASE/server.py"
    "$BASE/.venv/bin/python" -m py_compile "$BASE/server.py"
    echo "Installed local read-only MCP server: $BASE/server.py"
    echo "External ChatGPT connectivity requires a separately configured authenticated MCP transport."
    ;;
  check)
    [[ -f "$BASE/server.py" && -x "$BASE/.venv/bin/python" ]] || exit 1
    "$BASE/.venv/bin/python" -m py_compile "$BASE/server.py"
    echo "Syntax OK. This does not prove remote connectivity."
    ;;
  *) echo "Usage: $0 {install|check}" ;;
esac
