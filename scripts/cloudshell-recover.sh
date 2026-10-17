#!/usr/bin/env bash
# Restore missing Cloud Shell tools without changing DNS, Access, or model data.
set -Eeuo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-cloudshell-recovery"
CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
MODEL_DIR="${ZWSL_OLLAMA_MODELS:-${OLLAMA_MODELS:-/opt/zeaz-storage/models}}"
MODEL_PIDFILE="$STATE/ollama.pid"
ACTION="${1:-status}"

note() { printf '[cloudshell-recover] %s\n' "$*"; }
fail() { printf '[cloudshell-recover] BLOCKED: %s\n' "$*" >&2; exit 2; }
exists() { command -v "$1" >/dev/null 2>&1; }
ollama_healthy() {
  exists curl && curl --noproxy '*' --fail --silent --max-time 3 \
    http://127.0.0.1:11434/api/version >/dev/null
}
managed_ollama_pid() {
  local pid args
  [[ -f "$MODEL_PIDFILE" && ! -L "$MODEL_PIDFILE" ]] || return 1
  read -r pid < "$MODEL_PIDFILE" || return 1
  [[ "$pid" =~ ^[1-9][0-9]*$ && -r "/proc/$pid/cmdline" ]] || return 1
  [[ "$(stat -c %u "/proc/$pid" 2>/dev/null)" == "$(id -u)" ]] || return 1
  args="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
  [[ "$args" == *"ollama serve"* ]] || return 1
  printf '%s\n' "$pid"
}

ollama_uses_model_store() {
  local pid
  pid="$(managed_ollama_pid)" || return 1
  tr '\0' '\n' < "/proc/$pid/environ" |
    grep -Fxq -- "OLLAMA_MODELS=$MODEL_DIR"
}

validate_model_dir() {
  exists realpath || fail "realpath is required for path safety"
  [[ "$MODEL_DIR" == /* && "$MODEL_DIR" != "/" && "$MODEL_DIR" != "/opt" ]] ||
    fail "ZWSL_OLLAMA_MODELS must be a dedicated absolute directory"
  [[ "$(realpath -m -- "$MODEL_DIR")" == "$MODEL_DIR" ]] ||
    fail "Model storage path is non-canonical or contains a symlink"
  [[ ! -e "$MODEL_DIR" || -d "$MODEL_DIR" ]] ||
    fail "Model storage path exists but is not a directory"
  [[ ! -e "$MODEL_DIR" || ( -O "$MODEL_DIR" && -w "$MODEL_DIR" ) ]] ||
    fail "Existing model storage must be owned and writable by the current user"
}

prepare_model_dir() {
  validate_model_dir
  if [[ ! -d "$MODEL_DIR" ]]; then
    if [[ "$MODEL_DIR" == "/opt/zeaz-storage/models" ]]; then
      exists sudo || fail "sudo required to create default /opt model storage"
      sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 0700 "$MODEL_DIR"
    else
      local parent
      parent="$(dirname -- "$MODEL_DIR")"
      [[ -d "$parent" && -w "$parent" ]] ||
        fail "Custom model storage parent must already exist and be writable"
      install -d -m 0700 "$MODEL_DIR"
    fi
    note "ollama_storage=CREATED path=$MODEL_DIR"
  else
    note "ollama_storage=REUSED path=$MODEL_DIR"
  fi
  validate_model_dir
}

model_storage_status() {
  note "ollama_storage_path=$MODEL_DIR"
  if [[ -L "$MODEL_DIR" ]]; then
    note "ollama_storage=INVALID_SYMLINK"
  elif [[ -d "$MODEL_DIR" ]]; then
    local kib
    kib="$(du -sk -- "$MODEL_DIR" 2>/dev/null | awk '{print $1}')" || kib=""
    note "ollama_storage=PRESENT size_kib=${kib:-UNKNOWN}"
  else
    note "ollama_storage=MISSING"
  fi
}

status() {
  if exists cloudflared; then note "cloudflared=INSTALLED"; else note "cloudflared=MISSING"; fi
  if exists ollama; then note "ollama=INSTALLED"; else note "ollama=MISSING"; fi
  if exists zstd; then note "ollama_dependency_zstd=INSTALLED"; else note "ollama_dependency_zstd=MISSING"; fi
  model_storage_status
  if ollama_healthy; then
    if ollama_uses_model_store; then
      note "ollama_storage_binding=PASS"
    else
      note "ollama_storage_binding=NOT_VERIFIED_OR_MISMATCH"
    fi
    note "ollama_api=PASS origin=127.0.0.1:11434"
    curl --noproxy '*' --fail --silent --max-time 3 http://127.0.0.1:11434/api/tags |
      python3 -c 'import json,sys; data=json.load(sys.stdin); print("[cloudshell-recover] ollama_models="+str(len(data.get("models",[]))))' ||
      note "ollama_models=NOT_VERIFIED"
  else
    note "ollama_api=NOT_RUNNING"
  fi
  if [[ -f "$CONFIG" && ! -L "$CONFIG" ]]; then
    note "tunnel_config=PRESENT"
  else
    note "tunnel_config=MISSING_OR_INVALID"
  fi
  if exists pgrep && pgrep -u "$(id -u)" -x cloudflared >/dev/null 2>&1; then
    note "cloudflared_process=PRESENT"
  else
    note "cloudflared_process=NOT_RUNNING"
  fi
  if exists ss && ss -lnt | grep -Eq '[:.]22[[:space:]]'; then
    note "ssh_listener=PASS"
  else
    note "ssh_listener=NOT_VERIFIED"
  fi
  note "external_access_and_model_inference=NOT_VERIFIED"
}
require_cloudshell() {
  if [[ -z "${CLOUD_SHELL:-}" && -z "${DEVSHELL_PROJECT_ID:-}" &&
        ! -d /google/devshell && "${ZWSL_ALLOW_NON_CLOUDSHELL:-0}" != 1 ]]; then
    fail "Mutation is Cloud Shell only (override with ZWSL_ALLOW_NON_CLOUDSHELL=1)"
  fi
}
install_cloudflared() {
  if exists cloudflared; then note "SKIP: cloudflared installed"; return; fi
  for exe in curl sudo apt-get install grep; do exists "$exe" || fail "$exe is required"; done
  local source='deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main'
  local list='/etc/apt/sources.list.d/cloudflared.list'
  if [[ -e "$list" ]] && ! grep -Fxq "$source" "$list"; then
    fail "Existing Cloudflare APT source differs; manual review required"
  fi
  local tmp
  tmp="$(mktemp)"
  if ! curl --fail --silent --show-error --location --retry 2 --max-time 40 \
       https://pkg.cloudflare.com/cloudflare-main.gpg -o "$tmp"; then
    rm -f "$tmp"; fail "Could not retrieve Cloudflare APT signing key"
  fi
  if [[ ! -s "$tmp" ]]; then rm -f "$tmp"; fail "Empty Cloudflare signing key"; fi
  sudo install -d -m 0755 /usr/share/keyrings
  if [[ -e /usr/share/keyrings/cloudflare-main.gpg ]]; then
    note "SKIP: existing Cloudflare keyring"
  else
    sudo install -m 0644 "$tmp" /usr/share/keyrings/cloudflare-main.gpg
  fi
  rm -f "$tmp"
  if [[ ! -e "$list" ]]; then
    printf '%s\n' "$source" | sudo tee "$list" >/dev/null
  fi
  sudo apt-get update -qq
  sudo apt-get install -y cloudflared
  exists cloudflared || fail "cloudflared install did not expose an executable"
  note "cloudflared=INSTALLED_FROM_SIGNED_APT"
}
ensure_ollama_prerequisites() {
  # The upstream Ollama installer requires zstd to unpack its Linux archive.
  # Cloud Shell images may not include it; install only when unavailable.
  if exists zstd; then
    note "SKIP: zstd already installed"
    return
  fi
  for exe in sudo apt-get; do exists "$exe" || fail "$exe is required to install zstd"; done
  note "Installing missing Ollama archive dependency: zstd"
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends zstd
  exists zstd || fail "zstd remains unavailable after apt installation"
}

install_ollama() {
  if exists ollama; then note "SKIP: Ollama installed"; return; fi
  for exe in curl sh mktemp; do exists "$exe" || fail "$exe is required"; done
  ensure_ollama_prerequisites
  local tmp
  tmp="$(mktemp -d)"
  if ! curl --fail --silent --show-error --location --retry 2 --max-time 60 \
       https://ollama.com/install.sh -o "$tmp/install.sh"; then
    rm -rf -- "$tmp"; fail "Could not retrieve Ollama upstream installer"
  fi
  [[ -s "$tmp/install.sh" ]] || { rm -rf -- "$tmp"; fail "Empty Ollama installer"; }
  sh -n "$tmp/install.sh" || { rm -rf -- "$tmp"; fail "Invalid Ollama installer"; }
  # Explicit repair action only; upstream installer may require sudo.
  if ! sh "$tmp/install.sh"; then rm -rf -- "$tmp"; fail "Ollama installer failed"; fi
  rm -rf -- "$tmp"
  exists ollama || fail "Ollama installer did not expose an executable"
  note "ollama=INSTALLED_NO_MODELS_PULLED"
}
start_ollama() {
  if ollama_healthy; then
    ollama_uses_model_store || fail "Existing Ollama model store differs or process ownership unverified; will not restart it"
    note "SKIP: Ollama already responding with expected model storage"
    return
  fi
  exists ollama || fail "Ollama not installed"
  exists ss || fail "ss is required to check port 11434"
  if ss -lnt | grep -Eq '[:.]11434[[:space:]]'; then
    fail "port 11434 occupied but Ollama health failed; refusing second server"
  fi
  [[ ! -L "$STATE" ]] || fail "State directory is a symlink"
  mkdir -p "$STATE"; chmod 700 "$STATE"
  note "Starting native Ollama on 127.0.0.1:11434"
  nohup env OLLAMA_MODELS="$MODEL_DIR" OLLAMA_HOST=127.0.0.1:11434 ollama serve \
    </dev/null >>"$STATE/ollama.log" 2>&1 &
  printf '%s\n' "$!" >"$MODEL_PIDFILE"
  chmod 600 "$STATE/ollama.log" "$MODEL_PIDFILE"
  for _ in $(seq 1 25); do
    if ollama_healthy; then note "ollama_api=PASS"; return; fi
    sleep 1
  done
  fail "Ollama startup did not pass health; inspect private runtime log"
}
restore_model() {
  # Explicit opt-in: never download model weights during routine repair/status.
  [[ "${ZWSL_ALLOW_MODEL_DOWNLOAD:-0}" == 1 ]] ||
    fail "Set ZWSL_ALLOW_MODEL_DOWNLOAD=1 to authorize the network/model download"
  local model="${ZWSL_RECOVERY_MODEL:-}"
  [[ -n "$model" && "$model" =~ ^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$ ]] ||
    fail "Set a valid explicit ZWSL_RECOVERY_MODEL (example: qwen2.5-coder:7b)"
  [[ -d "$MODEL_DIR" ]] || fail "Run make cloudshell-recover to prepare model storage first"
  validate_model_dir
  ollama_healthy || fail "Ollama API not running; run make cloudshell-recover"
  ollama_uses_model_store || fail "Ollama process does not match expected model storage"
  if ollama list | awk 'NR>1 {print $1}' | grep -Fxq -- "$model"; then
    note "SKIP: model already installed: $model"
    return
  fi
  note "Explicit model download approved: $model"
  ollama pull "$model"
  ollama list | awk 'NR>1 {print $1}' | grep -Fxq -- "$model" ||
    fail "Model pull returned but model is absent from Ollama inventory"
  note "model_restore=PASS model=$model"
}

check_tunnel_credentials() {
  exists cloudflared || fail "cloudflared not installed"
  exists python3 || fail "python3 missing"
  python3 - "$CONFIG" <<'PY'
import json, os, re, stat, sys, uuid
from pathlib import Path

def private_file(path):
    if path.is_symlink() or not path.is_file():
        raise SystemExit("BLOCKED: tunnel file missing or symlinked")
    meta = path.stat()
    if meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) & 0o077:
        raise SystemExit("BLOCKED: tunnel file permissions or owner invalid")

config = Path(sys.argv[1])
private_file(config)
body = config.read_text()
ids = re.findall(r"^tunnel:[ \t]*(\S+)[ \t]*$", body, re.M)
creds = re.findall(r"^credentials-file:[ \t]*(.+?)[ \t]*$", body, re.M)
if len(ids) != 1 or len(creds) != 1:
    raise SystemExit("BLOCKED: ambiguous tunnel or credential config")
try:
    tid = str(uuid.UUID(ids[0]))
except ValueError:
    raise SystemExit("BLOCKED: invalid tunnel UUID")
path = Path(creds[0].strip().strip("'\"")).expanduser()
if not path.is_absolute():
    raise SystemExit("BLOCKED: credential path must be absolute")
private_file(path)
try:
    credential = json.loads(path.read_text())
except (ValueError, UnicodeError):
    raise SystemExit("BLOCKED: invalid credential JSON")
if not isinstance(credential, dict) or str(credential.get("TunnelID", "")).lower() != tid:
    raise SystemExit("BLOCKED: credential TunnelID mismatch")
host = os.environ.get("ZCLOUD_HOSTNAME", "")
lines = body.splitlines()
routes = [index for index, line in enumerate(lines)
          if line.strip() == f"- hostname: {host}"]
if len(routes) != 1:
    raise SystemExit("BLOCKED: expected one exact SSH hostname ingress")
services = []
for line in lines[routes[0] + 1:]:
    stripped = line.strip()
    if stripped.startswith("- hostname:") or stripped.startswith("- service:"):
        break
    if stripped.startswith("path:"):
        raise SystemExit("BLOCKED: SSH ingress must not be path scoped")
    if stripped.startswith("service:"):
        services.append(stripped.split(":", 1)[1].strip())
if services != ["ssh://127.0.0.1:22"]:
    raise SystemExit("BLOCKED: SSH hostname is not mapped to local port 22")
print("[cloudshell-recover] tunnel_credentials_and_ssh_ingress=PASS (existing only)")
PY
  cloudflared tunnel --config "$CONFIG" ingress validate >/dev/null
}
start_tunnel() {
  [[ -n "${ZCLOUD_HOSTNAME:-}" ]] || fail "Set ZCLOUD_HOSTNAME to authorized hostname"
  check_tunnel_credentials
  bash "$ROOT/scripts/zcloud-tunnel.sh" start
  bash "$ROOT/scripts/zcloud-tunnel.sh" status
  note "External Cloudflare Access and authenticated SSH remain NOT_VERIFIED"
}
case "$ACTION" in
  status) status ;;
  repair)
    require_cloudshell
    prepare_model_dir
    install_cloudflared
    install_ollama
    start_ollama
    status
    ;;
  model-restore)
    require_cloudshell
    restore_model
    ;;
  tunnel-start)
    require_cloudshell
    start_tunnel
    ;;
  *) fail "Usage: $0 {status|repair|model-restore|tunnel-start}" ;;
esac
