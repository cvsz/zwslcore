#!/usr/bin/env bash
# Configure a protected WebUI route in an existing locally managed Cloudflare tunnel.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
WEBUI_HOST="${ZWSL_WEBUI_HOSTNAME:-}"
SSH_HOST="${ZCLOUD_HOSTNAME:-}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-cloudflare-stack"
PORT="${ZWSL_WEBUI_PORT:-3000}"
check() {
  [[ "$WEBUI_HOST" =~ ^[A-Za-z0-9.-]+$ && "$WEBUI_HOST" == *.* ]] || { echo "Set ZWSL_WEBUI_HOSTNAME" >&2; exit 2; }
  [[ "$WEBUI_HOST" != "$SSH_HOST" ]] || { echo "WebUI and SSH must use separate hostnames" >&2; exit 2; }
  [[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || exit 2
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || exit 1
  local perms; perms="$(stat -c %a "$CONFIG")"
  (( (8#$perms & 8#077) == 0 )) || { echo "Tunnel config permissions must be private" >&2; exit 1; }
  command -v cloudflared >/dev/null
  cloudflared tunnel --config "$CONFIG" ingress validate
}
case "${1:-help}" in
  preflight)
    check
    curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" >/dev/null || { echo "Open WebUI not healthy on loopback:$PORT" >&2; exit 1; }
    echo "WebUI healthy; Cloudflare Access policy and DNS ownership must be verified independently."
    ;;
  configure)
    check
    [[ "${ZWSL_WEBUI_ACCESS_VERIFIED:-}" == YES ]] || { echo "Verify restrictive Access identity/MFA Allow policy for WebUI hostname first" >&2; exit 1; }
    curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" >/dev/null || { echo "WebUI health failed" >&2; exit 1; }
    mkdir -p "$STATE"; chmod 700 "$STATE"
    ZWSL_CF_CONFIG="$CONFIG" ZWSL_CF_HOST="$WEBUI_HOST" ZWSL_CF_PORT="$PORT" ZWSL_CF_STATE="$STATE" python3 - <<'PY'
from pathlib import Path
import os, tempfile, shutil, time
p=Path(os.environ["ZWSL_CF_CONFIG"]); host=os.environ["ZWSL_CF_HOST"]
port=os.environ["ZWSL_CF_PORT"]; state=Path(os.environ["ZWSL_CF_STATE"])
lines=p.read_text().splitlines(keepends=True)
if any(v.strip()==f"- hostname: {host}" for v in lines):
    raise SystemExit("Hostname already has an ingress rule; refusing overwrite")
idx=[i for i,v in enumerate(lines) if v.strip()=="- service: http_status:404"]
if len(idx)!=1: raise SystemExit("Expected exactly one final fallback rule")
i=idx[0]
if i!=len(lines)-1: raise SystemExit("Fallback must be final rule")
indent=lines[i].split("-",1)[0]
backup=state/("config."+str(time.time_ns())+".yml")
shutil.copy2(p,backup)
lines[i:i]=[indent+f"- hostname: {host}\n",indent+f"  service: http://127.0.0.1:{port}\n"]
fd,tmp=tempfile.mkstemp(prefix=".config.",dir=p.parent)
try:
    with os.fdopen(fd,"w") as f:
        f.writelines(lines);f.flush();os.fsync(f.fileno())
    os.chmod(tmp,0o600);os.replace(tmp,p)
    (state/"last-backup").write_text(str(backup))
except BaseException:
    Path(tmp).unlink(missing_ok=True);raise
print("Backup:",backup)
PY
    cloudflared tunnel --config "$CONFIG" ingress validate
    cloudflared tunnel --config "$CONFIG" ingress rule "https://$WEBUI_HOST/"
    echo "Route configured locally. DNS mapping, Access policy verification and existing connector reload remain required."
    ;;
  rollback)
    [[ -f "$STATE/last-backup" && ! -L "$CONFIG" ]] || exit 1
    backup="$(cat "$STATE/last-backup")"
    [[ "$backup" == "$STATE/"* && -f "$backup" && ! -L "$backup" ]] || exit 1
    cp -p "$backup" "$CONFIG"
    cloudflared tunnel --config "$CONFIG" ingress validate
    ;;
  *) echo "Usage: ZWSL_WEBUI_HOSTNAME=webui.example.org $0 {preflight|configure|rollback}" >&2;exit 2;;
esac
