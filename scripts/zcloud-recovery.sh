#!/usr/bin/env bash
# Recover the Cloud Shell zcloud connector after a VM reset.
#
# Cloud Shell wipes the base image (including /usr) between sessions; only
# $HOME persists. This script restores the pieces that live outside $HOME:
#   1. install the pinned cloudflared binary into $HOME/bin (persistent)
#   2. validate the tunnel config (mode 0600, no symlink, ingress, tunnel ID)
#   3. verify the local sshd listener required by the SSH ingress rule
#   4. delegate the connector lifecycle to scripts/zcloud-tunnel.sh
#      (single supervised cloudflared; this script never starts a second one)
#
# Run on the Cloud Shell VM. Idempotent: safe to re-run after every VM reset.
# Does not create credentials and does not change DNS records by default;
# use the opt-in `repair-dns` action only when the hostname record is stale.
set -Eeuo pipefail
umask 077

BIN_DIR="${ZCLOUD_BIN_DIR:-$HOME/bin}"
CLOUDFLARED="${ZCLOUD_CLOUDFLARED:-$BIN_DIR/cloudflared}"
URL="${ZCLOUD_CLOUDFLARED_URL:-https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64}"
# cloudflared 2026.10.1 linux-amd64; override ZCLOUD_CLOUDFLARED_SHA256 when upgrading.
SHA256="${ZCLOUD_CLOUDFLARED_SHA256:-3bfc539f45d2620c71debb7a86be0efa737ed5ccbad9eb85c787116900e5c586}"
TUNNEL_SCRIPT="${ZCLOUD_TUNNEL_SCRIPT:-$HOME/zwslcore/scripts/zcloud-tunnel.sh}"
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
TUNNEL_ID="${ZCLOUD_TUNNEL_ID:-09f176a3-8ebe-4e08-aae7-c56e4b8d7314}"
HOSTNAME_VALUE="${ZCLOUD_HOSTNAME:-zcloud.zeaz.dev}"
LOGFILE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-cloudflared/connector.log"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

install_binary() {
  [[ -f "$CLOUDFLARED" && ! -L "$CLOUDFLARED" ]] || { echo "cloudflared binary missing at $CLOUDFLARED"; return 1; }
  if printf '%s  %s\n' "$SHA256" "$CLOUDFLARED" | sha256sum -c - >/dev/null 2>&1; then
    echo "cloudflared binary verified: $CLOUDFLARED"
    return 0
  fi
  echo "cloudflared binary missing or checksum mismatch; downloading pinned release"
  mkdir -p "$BIN_DIR" && chmod 700 "$BIN_DIR"
  local tmp
  tmp="$(mktemp -p "$BIN_DIR" .cloudflared-XXXXXXXX)"
  curl --silent --show-error --location --max-time 120 "$URL" --output "$tmp" || {
    rm -f "$tmp"; fail "download failed: $URL"
  }
  chmod 700 "$tmp"
  printf '%s  %s\n' "$SHA256" "$tmp" | sha256sum -c - >/dev/null || {
    rm -f "$tmp"; fail "checksum mismatch for downloaded cloudflared"
  }
  mv -f "$tmp" "$CLOUDFLARED"
  echo "cloudflared binary installed: $CLOUDFLARED"
}

config_checks() {
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail "Config missing or symlinked: $CONFIG"
  local perms
  perms="$(stat -c %a "$CONFIG")"
  if (( (8#$perms & 8#077) != 0 )); then
    fail "Config permissions expose credentials; require mode 0600 ($CONFIG)"
  fi
  local name
  name="$(sed -n 's/^[[:space:]]*tunnel:[[:space:]]*//p' "$CONFIG" | head -1)"
  [[ "$name" == "$TUNNEL_ID" ]] || fail "Config tunnel ID ($name) != expected ($TUNNEL_ID)"
  "$CLOUDFLARED" tunnel --config "$CONFIG" ingress validate >/dev/null || fail "ingress validation failed"
  echo "Config validated: $CONFIG"
}

check_sshd() {
  python3 - "$HOSTNAME_VALUE" <<'PY'
import socket, sys
try:
    with socket.create_connection(('127.0.0.1', 22), timeout=3):
        print('sshd reachable on 127.0.0.1:22')
except OSError as exc:
    sys.exit(f'ERROR: sshd unavailable on 127.0.0.1:22 ({exc}); Cannot serve {sys.argv[1]} SSH ingress')
PY
}

ensure_path() {
  case ":$PATH:" in
    *":$BIN_DIR:"*) : ;;
    *) export PATH="$BIN_DIR:$PATH" ;;
  esac
}

recover() {
  install_binary
  ensure_path
  config_checks
  check_sshd
  [[ -x "$TUNNEL_SCRIPT" ]] || fail "Connector lifecycle script missing: $TUNNEL_SCRIPT (clone the repo first)"
  "$TUNNEL_SCRIPT" start
}

verify() {
  local code
  code="$(curl --silent --show-error --max-time 12 --output /dev/null --write-out '%{http_code}' "https://$HOSTNAME_VALUE")" || true
  if [[ "$code" == "530" || "$code" == "000" ]]; then
    fail "https://$HOSTNAME_VALUE returned HTTP $code (connector down or unreachable edge)"
  fi
  echo "https://$HOSTNAME_VALUE responded with HTTP $code (not a dead-tunnel 530)"
  [[ -f "$LOGFILE" ]] && tail -n 2 "$LOGFILE" | grep -E 'Registered tunnel connection|Metrics server' && return 0
  echo "Connector registration log not found; inspect $LOGFILE"
}

repair_dns() {
  # Explicit, opt-in, and visible: rewrites the hostname CNAME to this tunnel.
  read -r -p "Rewrite DNS record for $HOSTNAME_VALUE to tunnel $TUNNEL_ID? Type 'yes': " answer
  [[ "$answer" == "yes" ]] || fail "Refused by operator"
  "$CLOUDFLARED" tunnel route dns --overwrite-dns "$TUNNEL_ID" "$HOSTNAME_VALUE" >/dev/null
  echo "DNS record repaired for $HOSTNAME_VALUE -> tunnel $TUNNEL_ID"
}

case "${1:-help}" in
  recover)    recover ;;
  verify)     verify ;;
  repair-dns) install_binary >/dev/null; ensure_path; repair_dns ;;
  install)    install_binary ;;
  *) echo "Usage: $0 {recover|verify|repair-dns|install}"; exit 2 ;;
esac
