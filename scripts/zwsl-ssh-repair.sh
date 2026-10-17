#!/usr/bin/env bash
# Configure an explicit SSH client alias without weakening host-key checks.
set -Eeuo pipefail
umask 077
ALIAS="${ZCLOUD_ALIAS:-zcloud}"
HOST="${ZCLOUD_HOSTNAME:-ssh.example.com}"
USER_NAME="${ZCLOUD_SSH_USER:-$(id -un)}"
KEY="${ZCLOUD_IDENTITY_FILE:-$HOME/.ssh/id_ed25519}"
CONFIG="$HOME/.ssh/config"
case "${1:-help}" in
  diagnose)
    ssh -G "$ALIAS" | grep -E '^(hostname|user|identityfile|proxycommand|stricthostkeychecking) ' || true
    for f in "$KEY" "$HOME/.ssh/google_compute_engine"; do
      if [[ -f "$f" && ! -L "$f" ]]; then echo "PRESENT: $f"; else echo "MISSING: $f"; fi
    done
    echo "Access check (HTTP response does not prove authorization):"
    if [[ "$HOST" != ssh.example.com ]]; then
      curl --max-time 10 -sS -o /dev/null -w 'HTTP=%{http_code}\n' "https://$HOST/cdn-cgi/access/login" || true
    fi
    ;;
  configure)
    [[ "$ALIAS" =~ ^[a-zA-Z0-9_-]+$ && "$HOST" =~ ^[a-zA-Z0-9.-]+$ && "$HOST" != ssh.example.com && "$USER_NAME" =~ ^[a-zA-Z0-9_.-]+$ ]] || exit 1
    [[ -f "$KEY" && ! -L "$KEY" ]] || { echo "Missing private key; do not generate or copy one automatically." >&2; exit 1; }
    [[ "$(stat -c %a "$KEY")" == 600 ]] || { echo "Private key must be mode 600" >&2; exit 1; }
    mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
    [[ ! -L "$CONFIG" ]] || exit 1
    ZCLOUD_ALIAS="$ALIAS" ZCLOUD_HOSTNAME="$HOST" ZCLOUD_USER="$USER_NAME" ZCLOUD_KEY="$KEY" ZCLOUD_CLIENT_CONFIG="$CONFIG" python3 - <<'PYSSH'
from pathlib import Path
import os, re, tempfile, shutil, time
p = Path(os.environ["ZCLOUD_CLIENT_CONFIG"])
lines = p.read_text().splitlines(keepends=True) if p.exists() else []
alias = os.environ["ZCLOUD_ALIAS"]
heads = [(i, m.group(1).split()) for i, line in enumerate(lines)
         if (m := re.match(r"^\s*Host\s+([^#]+)", line, re.I))]
exact = [i for i, names in heads if alias in names]
if len(exact) > 1 or any(len(names) != 1 for i, names in heads if alias in names):
    raise SystemExit("Ambiguous host block")
block = ("Host " + alias + "\n"
         + "    HostName " + os.environ["ZCLOUD_HOSTNAME"] + "\n"
         + "    User " + os.environ["ZCLOUD_USER"] + "\n"
         + "    ProxyCommand cloudflared access ssh --hostname %h\n"
         + "    IdentityFile " + os.environ["ZCLOUD_KEY"] + "\n"
         + "    IdentitiesOnly yes\n"
         + "    StrictHostKeyChecking yes\n")
if exact:
    begin = exact[0]
    end = min([i for i, _ in heads if i > begin] + [len(lines)])
    lines[begin:end] = [block]
else:
    lines.append("\n" + block)
if p.exists():
    shutil.copy2(p, p.with_name("config.bak." + str(time.time_ns())))
fd, tmp = tempfile.mkstemp(prefix=".config.", dir=p.parent)
try:
    with os.fdopen(fd, "w") as f:
        f.writelines(lines)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)
except BaseException:
    Path(tmp).unlink(missing_ok=True)
    raise
PYSSH
    ssh -G "$ALIAS" | grep -E '^(hostname|user|identityfile|proxycommand|stricthostkeychecking) '
    ;;
  test)
    echo "SSH verification requires verified Cloudflare Access and a trusted host key."
    ssh -o BatchMode=yes -o ConnectTimeout=15 "$ALIAS" 'id -un && hostname'
    ;;
  *) echo "Usage: $0 {diagnose|configure|test}" ;;
esac
