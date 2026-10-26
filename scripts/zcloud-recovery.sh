#!/usr/bin/env bash
# Recover the Cloud Shell zcloud connector after a VM reset.
#
# Cloud Shell wipes the base image (including /usr) between sessions; only
# $HOME persists. This script restores the pieces that live outside $HOME:
#   1. installs the pinned cloudflared binary into a persistent home directory
#   2. validates the tunnel config, credentials, tunnel ID, and SSH ingress
#   3. verifies the local sshd listener required by the SSH ingress rule
#   4. delegates lifecycle to scripts/zcloud-tunnel.sh through Bash
#
# Run on the Cloud Shell VM. Idempotent: safe to re-run after every VM reset.
# Does not create credentials or change DNS records by default.
set -Eeuo pipefail
umask 077

BIN_DIR="${ZCLOUD_BIN_DIR:-$HOME/bin}"
CLOUDFLARED="${ZCLOUD_CLOUDFLARED:-$BIN_DIR/cloudflared}"
URL="${ZCLOUD_CLOUDFLARED_URL:-https://github.com/cloudflare/cloudflared/releases/download/2026.10.1/cloudflared-linux-amd64}"
# cloudflared 2026.10.1 linux-amd64; override URL and SHA together when upgrading.
SHA256="${ZCLOUD_CLOUDFLARED_SHA256:-3bfc539f45d2620c71debb7a86be0efa737ed5ccbad9eb85c787116900e5c586}"
TUNNEL_SCRIPT="${ZCLOUD_TUNNEL_SCRIPT:-$HOME/zwslcore/scripts/zcloud-tunnel.sh}"
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
# These are operator-owned runtime settings, not template defaults.
TUNNEL_ID="${ZCLOUD_TUNNEL_ID:-}"
HOSTNAME_VALUE="${ZCLOUD_HOSTNAME:-}"
LOGFILE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-cloudflared/connector.log"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_tunnel_identity() {
  [[ "$TUNNEL_ID" =~ ^[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}$ ]] ||
    fail "Set ZCLOUD_TUNNEL_ID to the intended tunnel UUID."
  [[ "$HOSTNAME_VALUE" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]] ||
    fail "Set ZCLOUD_HOSTNAME to the intended fully qualified hostname."
}

install_binary() {
  [[ "$CLOUDFLARED" == /* ]] || fail "ZCLOUD_CLOUDFLARED must be an absolute path"
  [[ ! -L "$CLOUDFLARED" ]] || fail "Refusing symlinked cloudflared path: $CLOUDFLARED"
  [[ ! -e "$CLOUDFLARED" || -f "$CLOUDFLARED" ]] || fail "cloudflared target is not a regular file: $CLOUDFLARED"

  if [[ -f "$CLOUDFLARED" ]] &&
     printf '%s  %s\n' "$SHA256" "$CLOUDFLARED" | sha256sum -c - >/dev/null 2>&1; then
    [[ -x "$CLOUDFLARED" ]] || chmod 700 "$CLOUDFLARED"
    echo "cloudflared binary verified: $CLOUDFLARED"
    return 0
  fi

  echo "cloudflared binary missing or checksum mismatch; downloading pinned release"
  local target_dir
  target_dir="$(dirname "$CLOUDFLARED")"
  if [[ "$target_dir" == "$BIN_DIR" ]]; then
    mkdir -p "$BIN_DIR"
    chmod 700 "$BIN_DIR"
  else
    [[ -d "$target_dir" && ! -L "$target_dir" ]] ||
      fail "Custom cloudflared target directory must exist and must not be a symlink: $target_dir"
  fi

  local tmp
  tmp="$(mktemp "$target_dir/.cloudflared-XXXXXXXX")"
  if ! curl --fail --silent --show-error --location --max-time 120 "$URL" --output "$tmp"; then
    rm -f -- "$tmp"
    fail "cloudflared download failed"
  fi
  chmod 700 "$tmp"
  if ! printf '%s  %s\n' "$SHA256" "$tmp" | sha256sum -c - >/dev/null; then
    rm -f -- "$tmp"
    fail "checksum mismatch for downloaded cloudflared"
  fi
  mv -f -- "$tmp" "$CLOUDFLARED"
  echo "cloudflared binary installed: $CLOUDFLARED"
}

check_credentials_file() {
  local line credentials credential_dir file_perms dir_perms uid
  line="$(grep -E '^[[:space:]]*credentials-file:[[:space:]]*' "$CONFIG" | head -n 1 || true)"
  credentials="${line#*:}"
  credentials="${credentials#"${credentials%%[![:space:]]*}"}"
  credentials="${credentials%"${credentials##*[![:space:]]}"}"
  credentials="${credentials%\"}"
  credentials="${credentials#\"}"
  credentials="${credentials%\'}"
  credentials="${credentials#\'}"
  [[ -n "$credentials" ]] || fail "Config must declare credentials-file"
  [[ "$credentials" != *$'\n'* && "$credentials" != *$'\r'* ]] || fail "Invalid credentials-file path"
  if [[ "$credentials" != /* ]]; then
    credentials="$(dirname "$CONFIG")/$credentials"
  fi
  [[ -f "$credentials" && ! -L "$credentials" ]] ||
    fail "Tunnel credentials must be an existing regular file, not a symlink"
  credential_dir="$(dirname "$credentials")"
  [[ -d "$credential_dir" && ! -L "$credential_dir" ]] ||
    fail "Tunnel credentials directory must exist and must not be a symlink"
  uid="$(id -u)"
  [[ "$(stat -c %u "$credentials")" == "$uid" ]] ||
    fail "Tunnel credentials file must be owned by the current user"
  [[ "$(stat -c %u "$credential_dir")" == "$uid" ]] ||
    fail "Tunnel credentials directory must be owned by the current user"
  file_perms="$(stat -c %a "$credentials")"
  dir_perms="$(stat -c %a "$credential_dir")"
  if (( (8#$file_perms & 8#077) != 0 )); then
    fail "Tunnel credentials are group/world accessible; require mode 0600"
  fi
  if (( (8#$dir_perms & 8#077) != 0 )); then
    fail "Tunnel credentials directory is group/world accessible; require mode 0700"
  fi
}

config_checks() {
  require_tunnel_identity
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail "Config missing or symlinked: $CONFIG"
  local perms name route_output
  perms="$(stat -c %a "$CONFIG")"
  if (( (8#$perms & 8#077) != 0 )); then
    fail "Config permissions expose credentials; require mode 0600 ($CONFIG)"
  fi
  [[ "$(stat -c %u "$CONFIG")" == "$(id -u)" ]] ||
    fail "Config must be owned by the current user"
  check_credentials_file
  name="$(sed -n 's/^[[:space:]]*tunnel:[[:space:]]*//p' "$CONFIG" | head -n 1)"
  name="${name%\"}"
  name="${name#\"}"
  name="${name%\'}"
  name="${name#\'}"
  [[ "$name" == "$TUNNEL_ID" ]] || fail "Config tunnel ID does not match ZCLOUD_TUNNEL_ID"
  [[ -x "$CLOUDFLARED" && ! -L "$CLOUDFLARED" ]] || fail "Verified cloudflared binary is not executable"
  "$CLOUDFLARED" tunnel --config "$CONFIG" ingress validate >/dev/null ||
    fail "ingress validation failed"
  route_output="@@("$CLOUDFLARED" tunnel --config "$CONFIG" ingress rule "https://$HOSTNAME_VALUE" 2>&1)" ||
    fail "Unable to determine the ingress rule for ZCLOUD_HOSTNAME"
  grep -Fq 'ssh://127.0.0.1:22' <<< "$route_output" ||
    fail "ZCLOUD_HOSTNAME does not route to ssh://127.0.0.1:22"
  echo "Config, credentials, and SSH ingress validated"
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
  local binary_dir
  binary_dir="$(dirname "$CLOUDFLARED")"
  case ":$PATH:" in
    *":$binary_dir:"*) : ;;
    *) export PATH="$binary_dir:$PATH" ;;
  esac
}

recover() {
  install_binary
  config_checks
  check_sshd
  [[ -r "$TUNNEL_SCRIPT" && ! -L "$TUNNEL_SCRIPT" ]] ||
    fail "Connector lifecycle script is unreadable or symlinked: $TUNNEL_SCRIPT"
  ZCLOUD_CLOUDFLARED="$CLOUDFLARED" bash "$TUNNEL_SCRIPT" start
}

verify() {
  require_tunnel_identity
  config_checks
  check_sshd
  local code
  if ! code="$(curl --silent --show-error --max-time 12 --output /dev/null --write-out '%{http_code}' "https://$HOSTNAME_VALUE")"; then
    fail "HTTP verification request failed for ZCLOUD_HOSTNAME"
  fi
  [[ "$code" =~ ^[1-5][0-9]{2}$ ]] || fail "Invalid HTTP status returned by verification request"
  [[ "$code" != "530" ]] || fail "ZCLOUD_HOSTNAME returned HTTP 530 (connector down or unreachable edge)"
  echo "ZCLOUD_HOSTNAME returned HTTP $code (not a dead-tunnel 530)"
  if [[ -f "$LOGFILE" ]] && tail -n 2 "$LOGFILE" | grep -E 'Registered tunnel connection|Metrics server'; then
    return 0
  fi
  fail "Connector registration log not found; inspect $LOGFILE"
}

repair_dns() {
  require_tunnel_identity
  read -r -p "Rewrite DNS record for $HOSTNAME_VALUE to tunnel $TUNNEL_ID? Type 'yes': " answer
  [[ "$answer" == "yes" ]] || fail "Refused by operator"
  "$CLOUDFLARED" tunnel route dns --overwrite-dns "$TUNNEL_ID" "$HOSTNAME_VALUE" >/dev/null
  echo "DNS record repaired for the explicitly configured hostname and tunnel"
}

case "${1:-help}" in
  recover)    recover ;;
  verify)     verify ;;
  repair-dns) install_binary >/dev/null; ensure_path; repair_dns ;;
  install)    install_binary ;;
  *) echo "Usage: $0 {recover|verify|repair-dns|install}"; exit 2 ;;
esac
