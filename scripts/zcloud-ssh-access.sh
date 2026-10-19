#!/usr/bin/env bash
# Manage Cloudflare Tunnel SSH ingress on Google Cloud Shell.
set -Eeuo pipefail
umask 077

CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
HOSTNAME="${ZCLOUD_HOSTNAME:-zcloud.example.com}"
SSH_PORT="${ZCLOUD_SSH_PORT:-22}"
STATE_DIR="${ZCLOUD_STATE_DIR:-$HOME/.local/state/zcloud-ssh-access}"
ACTION="${1:-help}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require() { command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"; }
validate_inputs() {
  require python3
  require cloudflared
  [[ "$SSH_PORT" =~ ^[0-9]+$ ]] && (( 10#$SSH_PORT > 0 && 10#$SSH_PORT < 65536 )) || fail 'Invalid SSH port'
  [[ "$HOSTNAME" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ && "$HOSTNAME" == *.* && "$HOSTNAME" != *..* ]] || fail 'Invalid hostname'
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail "Config missing or symlinked: $CONFIG"
  python3 - "$CONFIG" "$STATE_DIR" <<'PY'
import os, stat, sys
from pathlib import Path
cfg, state = (Path(x) for x in sys.argv[1:])
s = cfg.stat()
if s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077:
    sys.exit('ERROR: Config must be owned by the current user and mode 0600/0400')
if cfg.parent.is_symlink() or state.is_symlink():
    sys.exit('ERROR: Symlinked configuration or state directory is not supported')
PY
}
validate_config() { cloudflared tunnel --config "$CONFIG" ingress validate; }
check_sshd() {
  require python3
  python3 - "$SSH_PORT" <<'PY'
import socket, sys
port = int(sys.argv[1])
try:
    with socket.create_connection(('127.0.0.1', port), timeout=2):
        print('SSH TCP listener: reachable on 127.0.0.1:%d' % port)
except OSError as exc:
    sys.exit('ERROR: SSH TCP listener unavailable: %s' % exc)
PY
}
preflight() {
  validate_inputs
  validate_config
  check_sshd
  cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOSTNAME"
}
verify() {
  preflight
  printf '\nExternal Cloudflare endpoint (HTTP status is not SSH authentication):\n'
  curl --silent --show-error --max-time 12 --output /dev/null --write-out 'HTTP status: %{http_code}\n' "https://$HOSTNAME" || true
  printf 'Verify Cloudflare Access enforcement and SSH host key from an authorized external client.\n'
}
configure() {
  validate_inputs
  [[ "${ZCLOUD_ACCESS_POLICY_VERIFIED:-}" == YES ]] || fail 'Confirm Cloudflare Access identity + MFA policy; set ZCLOUD_ACCESS_POLICY_VERIFIED=YES'
  [[ "${ZCLOUD_AUTHORIZED_KEYS_VERIFIED:-}" == YES ]] || fail 'Confirm SSH key authentication and host-key verification; set ZCLOUD_AUTHORIZED_KEYS_VERIFIED=YES'
  check_sshd
  require flock
  mkdir -p "$STATE_DIR" && chmod 700 "$STATE_DIR"
  [[ ! -L "$STATE_DIR" ]] || fail 'State directory must not be a symlink'
  exec 9>"$STATE_DIR/change.lock"
  flock -n 9 || fail 'Another operation is running'
  python3 - "$CONFIG" "$HOSTNAME" "$SSH_PORT" "$STATE_DIR" <<'PY'
import os, re, shutil, sys, tempfile, time
from pathlib import Path
cfg, host, port, state = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
original = cfg.read_text()
lines = original.splitlines(keepends=True)
# Restrict modifications to the conventional top-level `ingress:` block.
ingress = [i for i, line in enumerate(lines) if re.fullmatch(r'ingress:\s*(?:#.*)?\n?', line)]
if len(ingress) != 1:
    sys.exit('ERROR: Expected one top-level ingress: block')
start = ingress[0] + 1
end = next((i for i in range(start, len(lines)) if re.match(r'^[^\s#][^:]*:', lines[i])), len(lines))
section = lines[start:end]
entries = [(j, re.match(r'^(\s*)-\s*(hostname|service):\s*(.*?)\s*(?:#.*)?$', line.rstrip('\n')))
           for j, line in enumerate(section)]
entries = [(j, m) for j, m in entries if m]
if not entries:
    sys.exit('ERROR: No recognizable ingress rules')
# Each rule must begin with a YAML sequence marker. Reject complex layouts rather than guessing.
starts = [(j, m) for j, m in entries]
blocks = []
for k, (j, m) in enumerate(starts):
    nxt = starts[k + 1][0] if k + 1 < len(starts) else len(section)
    blocks.append((j, nxt, m.group(2), m.group(3).strip().strip('"\''), m.group(1)))
if not blocks or any(kind not in ('hostname', 'service') for _, _, kind, _, _ in blocks):
    sys.exit('ERROR: Unsupported ingress structure')
# Service lines are nested; only top-level sequence markers appear in blocks.
matching = [(j, nxt, indent) for j, nxt, kind, value, indent in blocks if kind == 'hostname' and value == host]
if len(matching) > 1:
    sys.exit('ERROR: Duplicate hostname rules')
if matching:
    j, nxt, indent = matching[0]
    body = section[j + 1:nxt]
    service_idx = [n for n, line in enumerate(body) if re.match(r'^\s+service:\s*', line)]
    if len(service_idx) != 1:
        sys.exit('ERROR: Expected exactly one nested service')
    pos = j + 1 + service_idx[0]
    old = section[pos].strip().split('#', 1)[0].strip()
    target = f'service: ssh://127.0.0.1:{port}'
    if old != target and old != 'service: http_status:404':
        sys.exit('ERROR: Existing service is not SSH or the expected placeholder; refusing overwrite')
    section[pos] = re.match(r'^(\s*)', section[pos]).group(1) + target + '\n'
else:
    # Insert before the catch-all, which must remain the final ingress rule.
    catchall = [(j, kind, value, indent) for j, _, kind, value, indent in blocks if kind == 'service' and value.startswith('http_status:404')]
    if len(catchall) != 1:
        sys.exit('ERROR: Expected one explicit catch-all service: http_status:404')
    j, _, _, indent = catchall[0]
    section[j:j] = [f'{indent}- hostname: {host}\n', f'{indent}  service: ssh://127.0.0.1:{port}\n']
new = ''.join(lines[:start] + section + lines[end:])
if new == original:
    print('Already configured; no changes made')
    sys.exit(0)
backup = state / f'config-{time.time_ns()}-{os.getpid()}.yml'
shutil.copy2(cfg, backup)
os.chmod(backup, 0o600)
fd, tmp = tempfile.mkstemp(prefix='.zcloud-', dir=cfg.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(new)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, cfg)
except BaseException:
    try: os.unlink(tmp)
    except FileNotFoundError: pass
    raise
pointer = state / 'last-backup'
pointer.write_text(str(backup.resolve()) + '\n')
os.chmod(pointer, 0o600)
print('Backup:', backup)
print(f'Configured: {host} -> ssh://127.0.0.1:{port}')
PY
  if ! validate_config; then
    printf 'Validation failed: restoring previous configuration\n' >&2
    rollback_locked
    fail 'New ingress config rejected'
  fi
  cloudflared tunnel --config "$CONFIG" ingress rule "https://$HOSTNAME"
  printf '\nRestart your existing tunnel manager: ~/zcloud-tunnel restart\n'
  printf 'Then run: %s verify\n' "$0"
}
rollback_locked() {
  python3 - "$CONFIG" "$STATE_DIR" <<'PY'
import os, sys, tempfile
from pathlib import Path
cfg, state = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
pointer = state / 'last-backup'
if pointer.is_symlink() or not pointer.is_file():
    sys.exit('ERROR: Missing or symlinked backup pointer')
backup = Path(pointer.read_text().strip()).resolve()
if backup.parent != state or not backup.is_file() or not backup.name.startswith('config-'):
    sys.exit('ERROR: Invalid backup path')
fd, tmp = tempfile.mkstemp(prefix='.zcloud-rollback-', dir=cfg.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(backup.read_bytes())
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, cfg)
except BaseException:
    try: os.unlink(tmp)
    except FileNotFoundError: pass
    raise
print('Restored:', backup)
PY
}
rollback() {
  validate_inputs
  require flock
  [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || fail 'State directory missing or symlinked'
  exec 9>"$STATE_DIR/change.lock"
  flock -n 9 || fail 'Another operation is running'
  rollback_locked
  validate_config
  printf 'Restart your existing tunnel manager: ~/zcloud-tunnel restart\n'
}
case "$ACTION" in
  preflight) preflight ;;
  verify) require curl; verify ;;
  configure) configure ;;
  rollback) rollback ;;
  help|-h|--help)
    cat <<HELP
Usage: $0 {preflight|configure|verify|rollback}

Configuration defaults:
  ZCLOUD_CONFIG=$CONFIG
  ZCLOUD_HOSTNAME=$HOSTNAME
  ZCLOUD_SSH_PORT=$SSH_PORT

Before configure, verify Cloudflare Access identity/MFA restrictions and SSH
public-key authentication, then run:
  ZCLOUD_ACCESS_POLICY_VERIFIED=YES ZCLOUD_AUTHORIZED_KEYS_VERIFIED=YES $0 configure
  ~/zcloud-tunnel restart
  $0 verify

External SSH client example (~/.ssh/config):
  Host zcloud
    HostName $HOSTNAME
    User YOUR_CLOUD_SHELL_USERNAME
    ProxyCommand cloudflared access ssh --hostname %h
    StrictHostKeyChecking yes

Keep your existing tunnel supervisor; do not start a second one.
Cloud Shell instances and processes are ephemeral.
HELP
    ;;
  *) fail "Unknown action: $ACTION" ;;
esac
