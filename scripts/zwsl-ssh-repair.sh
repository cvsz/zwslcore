#!/usr/bin/env bash
# Safe Cloudflare SSH client repair and diagnostics for Google Cloud Shell.
set -Eeuo pipefail
umask 077

HOST_ALIAS="${ZCLOUD_ALIAS:-zcloud}"
HOSTNAME="${ZCLOUD_HOSTNAME:-zcloud.example.com}"
SSH_USER="${ZCLOUD_SSH_USER:-$(id -un)}"
TUNNEL="${ZCLOUD_TUNNEL:-zcloud-tunnel}"
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
SSH_DIR="$HOME/.ssh"
SSH_CONFIG="$SSH_DIR/config"
SSH_KEY="$SSH_DIR/google_compute_engine"
ACTION="${1:-diagnose}"

log() { printf '\n==> %s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require() { command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"; }

preflight() {
  require bash; require python3; require ssh; require ssh-keygen
  require cloudflared; require curl
  [[ "$HOST_ALIAS" =~ ^[a-zA-Z0-9_-]+$ ]] || fail 'Invalid alias'
  [[ "$HOSTNAME" =~ ^[a-zA-Z0-9.-]+$ ]] || fail 'Invalid hostname'
  [[ "$SSH_USER" =~ ^[a-zA-Z0-9_.-]+$ ]] || fail 'Invalid SSH username'
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail 'Tunnel config missing or symlinked'
  [[ -f "$SSH_KEY" && ! -L "$SSH_KEY" ]] || fail "SSH private key missing: $SSH_KEY"
  [[ "$(stat -c %a "$SSH_KEY")" == 600 ]] || fail 'Private key must have 0600 permissions'
  ssh-keygen -y -P '' -f "$SSH_KEY" >/dev/null 2>&1 || fail 'Private key cannot be read without passphrase or is invalid; do not replace it blindly'
  cloudflared tunnel ingress validate >/dev/null || fail 'Tunnel configuration failed validation'
}

fix_client() {
  preflight
  mkdir -p "$SSH_DIR"
  chmod 700 "$SSH_DIR"
  [[ ! -L "$SSH_CONFIG" ]] || fail 'SSH config symlink: refusing to edit'
  local backup='none'
  if [[ -f "$SSH_CONFIG" ]]; then
    backup="$SSH_CONFIG.backup.$(date -u +%Y%m%dT%H%M%SZ).$$"
    cp -p -- "$SSH_CONFIG" "$backup"
  fi
  # Atomic rewrite of only the specified host block. Keep unrelated hosts untouched.
  ZCLOUD_ALIAS="$HOST_ALIAS" ZCLOUD_HOSTNAME="$HOSTNAME" ZCLOUD_USER="$SSH_USER" \
  ZCLOUD_KEY="$SSH_KEY" ZCLOUD_SSH_CONFIG="$SSH_CONFIG" python3 - <<'PY_CLIENT'
from pathlib import Path
import os
import re
import tempfile

path = Path(os.environ['ZCLOUD_SSH_CONFIG'])
alias = os.environ['ZCLOUD_ALIAS']
source = path.read_text() if path.exists() else ''
lines = source.splitlines(keepends=True)
# Match a single exact Host block; refuse multi-pattern sections that mention alias.
start = end = None
for index, line in enumerate(lines):
    match = re.match(r'^\s*Host\s+(.+?)\s*(?:#.*)?$', line, re.I)
    if not match:
        continue
    patterns = match.group(1).split()
    if alias in patterns:
        if len(patterns) != 1 or start is not None:
            raise SystemExit('Ambiguous SSH Host block; refusing to modify')
        start = index
        continue
    if start is not None and end is None:
        end = index
    if start is not None and end is not None:
        break
if start is not None and end is None:
    end = len(lines)
block = (f'Host {alias}\n'
         f'    HostName {os.environ["ZCLOUD_HOSTNAME"]}\n'
         f'    User {os.environ["ZCLOUD_USER"]}\n'
         f'    ProxyCommand cloudflared access ssh --hostname %h\n'
         f'    IdentityFile {os.environ["ZCLOUD_KEY"]}\n'
         f'    IdentitiesOnly yes\n'
         f'    StrictHostKeyChecking yes\n'
         f'    BatchMode yes\n')
if start is None:
    result = (source.rstrip('\n') + '\n\n' if source.strip() else '') + block
else:
    result = ''.join(lines[:start]) + block + ''.join(lines[end:])
fd, temporary = tempfile.mkstemp(prefix='.ssh-config-', dir=str(path.parent))
try:
    with os.fdopen(fd, 'w') as out:
        out.write(result)
        out.flush()
        os.fsync(out.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
except BaseException:
    Path(temporary).unlink(missing_ok=True)
    raise
PY_CLIENT
  log "SSH config updated; backup: $backup"
  ssh -G "$HOST_ALIAS" | grep -Ei '^(hostname|user|identityfile|proxycommand|stricthostkeychecking|batchmode) ' || true
}

diagnose() {
  log 'Local SSH listener'
  if timeout 3 bash -c 'exec 3<>/dev/tcp/127.0.0.1/22' 2>/dev/null; then echo 'TCP port 22 reachable'; else echo 'TCP port 22 not reachable'; fi
  log 'Tunnel ingress validation'
  if [[ -f "$CONFIG" ]]; then cloudflared tunnel --config "$CONFIG" ingress validate || true; cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOSTNAME" || true; else echo 'Tunnel config not found'; fi
  log 'Tunnel connectors'
  cloudflared tunnel info "$TUNNEL" || true
  log 'Client SSH configuration (sanitized)'
  ssh -G "$HOST_ALIAS" | grep -Ei '^(hostname|user|identityfile|proxycommand|stricthostkeychecking|batchmode) ' || true
  log 'Private key checks'
  for key in "$SSH_KEY" "$SSH_DIR/id_ed25519"; do
    if [[ -f "$key" ]]; then echo "PRESENT: $key mode=$(stat -c %a "$key")"; else echo "MISSING: $key"; fi
  done
  log 'Cloudflare Access HTTP headers (not proof of policy enforcement)'
  curl -sS -m 10 -o /dev/null -w 'HTTP=%{http_code} REDIRECT=%{redirect_url}\n' "https://$HOSTNAME/cdn-cgi/access/login" || true
  log 'Next checks'
  echo 'If websocket: bad handshake persists, inspect active tunnel logs, DNS route, Access app, WebSockets, binding cookie, and overlapping Workers routes.'
  echo 'Do not infer Access security from an HTTP 404, or disable Access/WAF to make a connection succeed.'
}

test_ssh() {
  log 'Testing external Cloudflare SSH path; Cloudflare Access may require interactive browser login'
  ssh -o ConnectTimeout=15 "$HOST_ALIAS" 'whoami && hostname && pwd'
}

case "$ACTION" in
  diagnose) diagnose ;;
  fix-client) fix_client ;;
  test) test_ssh ;;
  preflight) preflight; echo 'Preflight OK' ;;
  *) printf 'Usage: %s {diagnose|fix-client|test|preflight}\n' "$0"; exit 2 ;;
esac
