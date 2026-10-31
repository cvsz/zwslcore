#!/usr/bin/env bash
# Diagnose a locally managed Cloudflare SSH tunnel without exposing credentials.
set -Eeuo pipefail
umask 077
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
HOST="${ZCLOUD_HOSTNAME:-}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-cloudflare"
mkdir -p "$STATE"; chmod 700 "$STATE"
[[ "$HOST" =~ ^[a-zA-Z0-9.-]+$ && "$HOST" == *.* ]] || { echo "Set ZCLOUD_HOSTNAME to the configured SSH hostname" >&2; exit 2; }
[[ -f "$CONFIG" && ! -L "$CONFIG" ]] || { echo "Missing or symlinked tunnel config" >&2; exit 1; }
for exe in cloudflared python3 curl ss; do command -v "$exe" >/dev/null || { echo "Missing: $exe" >&2; exit 1; }; done
case "${1:-doctor}" in
  doctor)
    cloudflared tunnel --config "$CONFIG" ingress validate
    cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOST"
    echo "=== Origin SSH listener ==="
    ss -lnt | grep -E '[:.]22[[:space:]]' || echo "NOT LISTENING: port 22"
    echo "=== Active connector processes ==="
    pgrep -af '[c]loudflared.*tunnel.*run' || echo "NO CONNECTOR"
    echo "=== Config freshness compared with connector start ==="
    ZCLOUD_CONFIG="$CONFIG" python3 - <<'PY'
import os
from pathlib import Path
config = Path(os.environ["ZCLOUD_CONFIG"])
fresh = config.stat().st_mtime
found = False
for proc in Path("/proc").iterdir():
    if not proc.name.isdigit():
        continue
    try:
        args = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if "cloudflared" not in args or " tunnel " not in args or " run" not in args:
            continue
        found = True
        # The start time is intentionally not guessed from PID or logs.
        print(f"connector_pid={proc.name}; config_mtime={int(fresh)}; confirm connector was restarted after last config change")
    except (OSError, PermissionError):
        pass
if not found:
    print("No visible connector process; start through its existing owner/manager")
PY
    echo "=== Unauthenticated HTTP endpoint status (404 is not SSH proof) ==="
    curl -sS --max-time 10 -o /dev/null -w 'status=%{http_code}\n' "https://$HOST/" || true
    echo "=== Action ==="
    echo "Check exact-host Cloudflare Access Allow policy and absence of Bypass; check WebSocket/Worker routes."
    echo "Validate CLI login from client; NEVER paste Access callback URLs or tokens."
    echo "Do not start a second tunnel connector. Reload via the existing owner after policy verification."
    ;;
  *) echo "Usage: ZCLOUD_HOSTNAME=ssh.example.org $0 doctor" >&2; exit 2 ;;
esac
