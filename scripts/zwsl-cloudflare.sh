#!/usr/bin/env bash
# Opt-in Cloudflare SSH ingress setup; does not create or bypass Access policies.
set -Eeuo pipefail
umask 077
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
HOSTNAME="${ZCLOUD_HOSTNAME:-ssh.example.com}"
PORT="${ZCLOUD_SSH_PORT:-22}"
STATE="${ZCLOUD_BACKUP_DIR:-$HOME/.local/state/zwslcore-access}"
require() { command -v "$1" >/dev/null || { echo "Missing: $1" >&2; exit 1; }; }
preflight() {
  require python3; require cloudflared; require ssh; require ss
  [[ "$HOSTNAME" =~ ^[a-zA-Z0-9.-]+$ && "$HOSTNAME" != "ssh.example.com" ]] || { echo "Set ZCLOUD_HOSTNAME to your authorized hostname" >&2; exit 1; }
  [[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT > 0 && PORT < 65536 )) || exit 1
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || { echo "Missing or symlink config" >&2; exit 1; }
  local mode; mode="$(stat -c %a "$CONFIG")"
  (( (8#$mode & 8#077) == 0 )) || { echo "Config permissions too broad" >&2; exit 1; }
  cloudflared tunnel --config "$CONFIG" ingress validate
  ss -lnt | grep -Eq "[:.]$PORT[[:space:]]" || { echo "SSH TCP listener not found" >&2; exit 1; }
}
case "${1:-help}" in
  preflight) preflight ;;
  verify)
    preflight
    cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOSTNAME"
    echo "Local ingress verified. External Access authorization and SSH authentication are not verified."
    ;;
  configure)
    preflight
    [[ "${ZCLOUD_ACCESS_POLICY_VERIFIED:-}" == YES && "${ZCLOUD_AUTHORIZED_KEYS_VERIFIED:-}" == YES ]] || {
      echo "Verify Cloudflare Access identity/MFA policy and SSH authorized keys first." >&2; exit 1;
    }
    mkdir -p "$STATE"; chmod 700 "$STATE"
    ZCLOUD_CONFIG="$CONFIG" ZCLOUD_HOSTNAME="$HOSTNAME" ZCLOUD_SSH_PORT="$PORT" ZCLOUD_STATE="$STATE" python3 - <<'PYCFG'
from pathlib import Path
import os, shutil, tempfile, time
config = Path(os.environ["ZCLOUD_CONFIG"])
hostname = os.environ["ZCLOUD_HOSTNAME"]
port = os.environ["ZCLOUD_SSH_PORT"]
state = Path(os.environ["ZCLOUD_STATE"])
lines = config.read_text().splitlines(keepends=True)
matching = [i for i, line in enumerate(lines) if line.strip() == f"hostname: {hostname}"]
if len(matching) != 1:
    raise SystemExit("Expected exactly one matching hostname entry")
index = matching[0]
if index + 1 >= len(lines) or lines[index+1].strip() not in ("service: http_status:404", f"service: ssh://127.0.0.1:{port}"):
    raise SystemExit("Unexpected ingress layout; refusing automatic edit")
if lines[index+1].strip() == f"service: ssh://127.0.0.1:{port}":
    print("SSH ingress already configured")
    raise SystemExit(0)
backup = state / ("config." + str(time.time_ns()) + ".yml")
shutil.copy2(config, backup)
lines[index+1] = lines[index+1].split("service:")[0] + f"service: ssh://127.0.0.1:{port}\n"
fd, target = tempfile.mkstemp(prefix=".config.", dir=str(config.parent))
try:
    with os.fdopen(fd, "w") as handle:
        handle.writelines(lines)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(target, 0o600)
    os.replace(target, config)
    (state / "last-backup").write_text(str(backup))
except BaseException:
    Path(target).unlink(missing_ok=True)
    raise
print(f"Backup: {backup}")
PYCFG
    if ! cloudflared tunnel --config "$CONFIG" ingress validate; then echo "Validation failed; run rollback before restarting any connector" >&2; exit 1; fi
    echo "Config updated; restart ONLY your existing tunnel supervisor after verifying Access enforcement."
    ;;
  rollback)
    [[ -f "$STATE/last-backup" && ! -L "$CONFIG" ]] || { echo "Backup pointer or destination missing" >&2; exit 1; }
    backup="$(cat "$STATE/last-backup")"
    [[ "$backup" == "$STATE/"* && -f "$backup" && ! -L "$backup" ]] || exit 1
    cp -p -- "$backup" "$CONFIG"
    cloudflared tunnel --config "$CONFIG" ingress validate
    echo "Config restored; restart existing connector explicitly."
    ;;
  *) echo "Usage: ZCLOUD_HOSTNAME=ssh.example.org $0 {preflight|configure|verify|rollback}" ;;
esac
