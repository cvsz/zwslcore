#!/usr/bin/env bash
# Safely prepare a signed webhook receiver and opt-in Cloudflare path ingress.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${ZCLOUD_HOSTNAME:-}"
PORT="${ZWSL_WEBHOOK_PORT:-8765}"
SSH_PORT="${ZCLOUD_SSH_PORT:-22}"
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-webhook"
KEY="${ZWSL_WEBHOOK_SECRET_FILE:-$HOME/.config/zwslcore/webhook.key}"
[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT < 65536 )) || { echo "Invalid port" >&2; exit 2; }
[[ "$SSH_PORT" =~ ^[0-9]+$ ]] && (( SSH_PORT >= 1 && SSH_PORT < 65536 )) || { echo "Invalid SSH port" >&2; exit 2; }
receiver_health() {
  # Do not route a signed webhook to an arbitrary service that happens to
  # answer 200 at /health. Validate the exact receiver identity instead.
  ZWSL_WEBHOOK_PORT="$PORT" python3 - <<'PYHEALTH'
import json
import os
import urllib.error
import urllib.request

url = "http://127.0.0.1:" + os.environ["ZWSL_WEBHOOK_PORT"] + "/health"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(url, timeout=5) as response:
        if response.status != 200:
            raise ValueError("unexpected health status")
        payload = json.loads(response.read(4097))
        if payload != {"status": "healthy", "service": "zwslcore-signed-webhook", "version": 1}:
            raise ValueError("unexpected webhook receiver identity")
except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
    raise SystemExit("Webhook receiver identity validation failed")
print("Webhook receiver identity verified")
PYHEALTH
}
case "${1:-help}" in
  install)
    mkdir -p "$(dirname "$KEY")" "$STATE"
    chmod 700 "$(dirname "$KEY")" "$STATE"
    [[ ! -L "$KEY" ]] || exit 1
    if [[ ! -f "$KEY" ]]; then
      python3 - "$KEY" <<'PYKEY'
from pathlib import Path
import secrets, sys, os
path = Path(sys.argv[1])
fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(secrets.token_hex(32) + "\n")
PYKEY
    fi
    [[ "$(stat -c %a "$KEY")" == 600 ]] || { echo "Key permissions must be 600" >&2; exit 1; }
    python3 -m py_compile "$ROOT/scripts/cloudshell-webhook.py"
    echo "Installed webhook receiver. Start locally via: make webhook-start"
    ;;
  start)
    [[ -f "$KEY" && ! -L "$KEY" ]] || { echo "Run install first" >&2; exit 1; }
    exec python3 "$ROOT/scripts/cloudshell-webhook.py"
    ;;
  health)
    receiver_health
    ;;
  configure)
    [[ "$HOST" =~ ^[a-zA-Z0-9.-]+$ && "$HOST" == *.* ]] || { echo "Set ZCLOUD_HOSTNAME" >&2; exit 2; }
    [[ -f "$CONFIG" && ! -L "$CONFIG" && "$(stat -c %a "$CONFIG")" == 600 ]] || { echo "Secure existing tunnel config required" >&2; exit 1; }
    command -v cloudflared >/dev/null
    cloudflared tunnel --config "$CONFIG" ingress validate
    # This does not alter the Access policy. A path-specific authentication
    # policy must be configured separately before exposing a public webhook.
    [[ "${ZWSL_WEBHOOK_ACCESS_VERIFIED:-}" == YES ]] || { echo "Verify path-specific Access and provider authentication before routing" >&2; exit 1; }
    [[ -f "$KEY" && ! -L "$KEY" && "$(stat -c %a "$KEY")" == 600 ]] || { echo "Install a private webhook secret first" >&2; exit 1; }
    receiver_health >/dev/null || { echo "Webhook receiver health failed" >&2; exit 1; }
    mkdir -p "$STATE"; chmod 700 "$STATE"
    ZCLOUD_HOSTNAME="$HOST" ZWSL_WEBHOOK_PORT="$PORT" ZCLOUD_SSH_PORT="$SSH_PORT" ZCLOUD_CONFIG="$CONFIG" ZWSL_WEBHOOK_STATE="$STATE" python3 - <<'PYROUTE'
from pathlib import Path
import os, shutil, tempfile, time
path = Path(os.environ["ZCLOUD_CONFIG"])
host = os.environ["ZCLOUD_HOSTNAME"]
port = os.environ["ZWSL_WEBHOOK_PORT"]
ssh_port = os.environ["ZCLOUD_SSH_PORT"]
state = Path(os.environ["ZWSL_WEBHOOK_STATE"])
lines = path.read_text().splitlines(keepends=True)
needle = "    - hostname: " + host + "\n"
# Support the existing four-space and two-space YAML ingress indentation.
indices = [i for i, v in enumerate(lines) if v.strip() == "- hostname: " + host]
if len(indices) not in (1, 2):
    raise SystemExit("Expected an existing SSH hostname rule; refusing ambiguous ingress")
ssh_rules = [i for i in indices if i + 1 < len(lines) and lines[i+1].strip() == f"service: ssh://127.0.0.1:{ssh_port}"]
if len(ssh_rules) != 1:
    raise SystemExit("SSH rule not found in expected layout")
idx = ssh_rules[0]
indent = lines[idx].split("-",1)[0]
path_rule = indent + "- hostname: " + host + "\n"
path_regex = indent + "  path: ^/webhook/?$\n"
path_service = indent + "  service: http://127.0.0.1:" + port + "\n"
already = any(i + 2 < len(lines) and lines[i+1] == path_regex and lines[i+2] == path_service for i in indices)
if already:
    print("Webhook route already configured")
    raise SystemExit(0)
if len(indices) != 1:
    raise SystemExit("Existing extra rule for host requires manual review")
backup = state / ("config." + str(time.time_ns()) + ".yml")
shutil.copy2(path, backup)
lines[idx:idx] = [path_rule, path_regex, path_service]
fd, temp = tempfile.mkstemp(prefix=".config.", dir=path.parent)
try:
    with os.fdopen(fd,"w") as f:
        f.writelines(lines)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(temp,0o600)
    os.replace(temp,path)
    (state / "last-backup").write_text(str(backup))
except BaseException:
    Path(temp).unlink(missing_ok=True)
    raise
print("Backup:",backup)
PYROUTE
    cloudflared tunnel --config "$CONFIG" ingress validate
    cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOST/webhook"
    cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOST/"
    echo "Restart existing managed connector explicitly after Access policy verification."
    ;;
  rollback)
    [[ -f "$STATE/last-backup" && ! -L "$CONFIG" ]] || exit 1
    backup="$(cat "$STATE/last-backup")"
    [[ "$backup" == "$STATE/"* && -f "$backup" && ! -L "$backup" ]] || exit 1
    cp -p "$backup" "$CONFIG"
    cloudflared tunnel --config "$CONFIG" ingress validate
    ;;
  *) echo "Usage: $0 {install|start|health|configure|rollback}" ;;
esac
