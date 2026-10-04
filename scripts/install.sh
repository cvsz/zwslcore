#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
MODELS=(qwen2.5-coder:3b qwen2.5-coder:7b qwen3:8b)

log() { printf '\n[zwslcore] %s\n' "$*"; }
die() { printf '[zwslcore] ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Linux" ]] || die "Linux is required."
grep -qi microsoft /proc/version || log "Warning: WSL2 was not detected; continuing on Linux."
command -v docker >/dev/null 2>&1 || die "Docker Engine is required."
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is required."

if [[ ! -f "$ENV_FILE" ]]; then
  log "Creating .env from .env.example"
  cp "$ROOT/.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import secrets
import sys

path = Path(sys.argv[1])
text = path.read_text()
replacements = {
    "REPLACE_ME_WEBUI_SECRET": secrets.token_hex(32),
    "REPLACE_ME_LITELLM_MASTER_KEY": "sk-" + secrets.token_hex(32),
    "REPLACE_ME_PROVIDER_CLIENT_KEY": "zw-" + secrets.token_hex(32),
}
for old, new in replacements.items():
    text = text.replace(old, new)
path.write_text(text)
PY

log "Validating Compose configuration"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" config --quiet

log "Starting Ollama"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" up -d ollama

log "Waiting for Ollama"
for _ in $(seq 1 60); do
  if docker exec zwslcore-ollama ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec zwslcore-ollama ollama list >/dev/null 2>&1 || die "Ollama did not become ready."

AVAILABLE_KB=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))
log "Available RAM: ${AVAILABLE_GB} GiB"

SELECTED=("${MODELS[0]}")
if (( AVAILABLE_GB >= 10 )); then SELECTED+=("${MODELS[1]}"); fi
if (( AVAILABLE_GB >= 14 )); then SELECTED+=("${MODELS[2]}"); fi

for model in "${SELECTED[@]}"; do
  if ! docker exec zwslcore-ollama ollama list | awk 'NR>1 {print $1}' | grep -qx "$model"; then
    log "Pulling $model"
    docker exec zwslcore-ollama ollama pull "$model"
  fi
done

log "Starting LiteLLM, zwslcore Provider, and Open WebUI"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" up -d

log "Running health checks"
bash "$ROOT/scripts/doctor.sh"

cat <<EOF

zwslcore AI stack is running.

Open WebUI : http://localhost:${OPENWEBUI_PORT:-3000}
Provider   : http://localhost:${PROVIDER_PORT:-8080}
LiteLLM    : http://localhost:${LITELLM_PORT:-4000}
Ollama     : http://localhost:${OLLAMA_PORT:-11434}

Cloud provider fallback remains disabled until you explicitly set provider keys.
EOF
