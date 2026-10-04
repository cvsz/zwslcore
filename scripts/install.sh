#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

log() { printf '\n[zwslcore] %s\n' "$*"; }
die() { printf '[zwslcore] ERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Linux" ]] || die "Linux is required."
grep -qi microsoft /proc/version || log "Warning: WSL2 was not detected; continuing on Linux."
command -v docker >/dev/null 2>&1 || die "Docker Engine is required."
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is required."
command -v python3 >/dev/null 2>&1 || die "Python 3 is required."
command -v curl >/dev/null 2>&1 || die "curl is required."

if [[ ! -f "$ENV_FILE" ]]; then
  log "Creating .env from .env.example"
  cp "$ROOT/.env.example" "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"

log "Migrating managed defaults and generating local secrets"
python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import secrets
import sys

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()

managed_defaults = {
    "OLLAMA_IMAGE": ("ollama/ollama:0.35.1", {"", "ollama/ollama:latest"}),
    "LITELLM_IMAGE": (
        "ghcr.io/berriai/litellm:v1.104.0",
        {"", "docker.litellm.ai/berriai/litellm:latest", "ghcr.io/berriai/litellm:latest"},
    ),
    "OPENWEBUI_IMAGE": (
        "ghcr.io/open-webui/open-webui:v0.11.4",
        {"", "ghcr.io/open-webui/open-webui:main", "ghcr.io/open-webui/open-webui:latest"},
    ),
}

values = {}
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        values[key] = value

replacements = {
    "REPLACE_ME_WEBUI_SECRET": secrets.token_hex(32),
    "REPLACE_ME_LITELLM_MASTER_KEY": "sk-" + secrets.token_hex(32),
    "REPLACE_ME_PROVIDER_CLIENT_KEY": "zw-" + secrets.token_hex(32),
}
text = "\n".join(lines) + "\n"
for old, new in replacements.items():
    text = text.replace(old, new)

lines = text.splitlines()
seen = set()
out = []
for line in lines:
    if "=" not in line or line.lstrip().startswith("#"):
        out.append(line)
        continue
    key, value = line.split("=", 1)
    seen.add(key)
    if key in managed_defaults:
        target, old_values = managed_defaults[key]
        if value in old_values:
            value = target
    out.append(f"{key}={value}")

for key, (target, _) in managed_defaults.items():
    if key not in seen:
        out.append(f"{key}={target}")
if "OPENWEBUI_CORS_ALLOW_ORIGIN" not in seen:
    out.append("OPENWEBUI_CORS_ALLOW_ORIGIN=http://localhost:3000;http://127.0.0.1:3000")
if "ZEAZ_COST_POLICY" not in seen:
    out.append("ZEAZ_COST_POLICY=ZERO_COST_ONLY")

path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY

if grep -Eq 'REPLACE_ME_(WEBUI_SECRET|LITELLM_MASTER_KEY|PROVIDER_CLIENT_KEY)' "$ENV_FILE"; then
  die "Secret placeholders remain in .env."
fi

log "Validating Compose configuration"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" config --quiet

log "Pulling pinned runtime images"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" pull ollama litellm open-webui

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

ACCELERATOR_MODE="cpu"
QUANTIZATION_PROFILE="Q4_K_M"
OLLAMA_CONTEXT_LENGTH="4096"
OLLAMA_FLASH_ATTENTION="false"
VLLM_CANDIDATE="false"

if command -v nvidia-smi >/dev/null 2>&1; then
  NVIDIA_MEM_MIB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -d ' ' || true)"
  if [[ "$NVIDIA_MEM_MIB" =~ ^[0-9]+$ ]]; then
    ACCELERATOR_MODE="nvidia"
    OLLAMA_FLASH_ATTENTION="true"
    if (( NVIDIA_MEM_MIB >= 16384 )); then
      OLLAMA_CONTEXT_LENGTH="16384"
      VLLM_CANDIDATE="true"
    elif (( NVIDIA_MEM_MIB >= 8192 )); then
      OLLAMA_CONTEXT_LENGTH="8192"
      VLLM_CANDIDATE="true"
    fi
  fi
elif command -v rocminfo >/dev/null 2>&1 && rocminfo >/dev/null 2>&1; then
  ACCELERATOR_MODE="rocm"
  OLLAMA_FLASH_ATTENTION="true"
fi

log "Accelerator profile: mode=$ACCELERATOR_MODE quantization=$QUANTIZATION_PROFILE context=$OLLAMA_CONTEXT_LENGTH flash_attention=$OLLAMA_FLASH_ATTENTION vllm_candidate=$VLLM_CANDIDATE"

FAST_MODEL="qwen2.5-coder:3b"
CODER_MODEL="$FAST_MODEL"
REASONING_MODEL="$FAST_MODEL"
LOCAL_MODEL="$FAST_MODEL"

if (( AVAILABLE_GB >= 10 )); then
  CODER_MODEL="qwen2.5-coder:7b"
  REASONING_MODEL="$CODER_MODEL"
  LOCAL_MODEL="$CODER_MODEL"
fi
if (( AVAILABLE_GB >= 14 )); then
  REASONING_MODEL="qwen3:8b"
  LOCAL_MODEL="$REASONING_MODEL"
fi

log "Runtime model selection: fast=$FAST_MODEL coder=$CODER_MODEL reasoning=$REASONING_MODEL default=$LOCAL_MODEL"

python3 - "$ENV_FILE" "$FAST_MODEL" "$CODER_MODEL" "$REASONING_MODEL" "$LOCAL_MODEL" "$ACCELERATOR_MODE" "$QUANTIZATION_PROFILE" "$OLLAMA_CONTEXT_LENGTH" "$OLLAMA_FLASH_ATTENTION" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
fast, coder, reasoning, local = sys.argv[2:6]
accelerator, quantization, context_length, flash_attention = sys.argv[6:10]
engineering = "auto"
updates = {
    "ZEAZ_FAST_MODEL": fast,
    "ZEAZ_CODER_MODEL": coder,
    "ZEAZ_REASONING_MODEL": reasoning,
    "ZEAZ_LOCAL_MODEL": local,
    "ZEAZ_LITELLM_FAST_MODEL": f"ollama/{fast}",
    "ZEAZ_LITELLM_CODER_MODEL": f"ollama/{coder}",
    "ZEAZ_LITELLM_REASONING_MODEL": f"ollama/{reasoning}",
    "ZEAZ_ACCELERATOR_MODE": accelerator,
    "ZEAZ_QUANTIZATION_PROFILE": quantization,
    "ZEAZ_OLLAMA_CONTEXT_LENGTH": context_length,
    "ZEAZ_OLLAMA_FLASH_ATTENTION": flash_attention,
}

lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
out = []
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        if key == "ZEAZ_ENGINEERING_MODEL":
            if value in {"", "zeaz-local"}:
                value = engineering
            out.append(f"{key}={value}")
            seen.add(key)
            continue
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
            continue
    out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")
if "ZEAZ_ENGINEERING_MODEL" not in seen:
    out.append(f"ZEAZ_ENGINEERING_MODEL={engineering}")
path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY
chmod 600 "$ENV_FILE"

mapfile -t SELECTED < <(printf '%s\n' "$FAST_MODEL" "$CODER_MODEL" "$REASONING_MODEL" | awk '!seen[$0]++')
for model in "${SELECTED[@]}"; do
  if ! docker exec zwslcore-ollama ollama list | awk 'NR>1 {print $1}' | grep -qx "$model"; then
    log "Pulling $model"
    docker exec zwslcore-ollama ollama pull "$model"
  fi
done

log "Re-validating runtime configuration"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" config --quiet

log "Building the in-repo provider gateway"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" build --pull provider

log "Starting LiteLLM, zwslcore Provider, and Open WebUI"
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" up -d --remove-orphans

log "Waiting for the full AI stack to become healthy and stable"
if ! bash "$ROOT/scripts/wait-runtime.sh"; then
  printf '\n[zwslcore] Runtime stability wait failed. Current container state:\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" ps >&2 || true
  printf '\n[zwslcore] Recent service logs:\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" logs --tail=120 >&2 || true
  die "AI stack did not become stable within the readiness timeout."
fi

log "Running health checks"
if ! bash "$ROOT/scripts/doctor.sh"; then
  printf '\n[zwslcore] Stack health check failed. Current container state:\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" ps >&2 || true
  printf '\n[zwslcore] Recent service logs:\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" logs --tail=120 >&2 || true
  die "AI stack did not become healthy within 300 seconds."
fi

log "Running end-to-end smoke test"
if ! bash "$ROOT/scripts/smoke.sh"; then
  printf '\n[zwslcore] End-to-end smoke test failed. Current container state:\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" ps >&2 || true
  printf '\n[zwslcore] Recent service logs:\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" logs --tail=120 >&2 || true
  die "AI stack is healthy but inference validation failed."
fi

# shellcheck source=scripts/lib/env.sh
source "$ROOT/scripts/lib/env.sh"
OPENWEBUI_PORT="$(dotenv_get "$ENV_FILE" OPENWEBUI_PORT 3000)"
PROVIDER_PORT="$(dotenv_get "$ENV_FILE" PROVIDER_PORT 8080)"
LITELLM_PORT="$(dotenv_get "$ENV_FILE" LITELLM_PORT 4000)"
OLLAMA_PORT="$(dotenv_get "$ENV_FILE" OLLAMA_PORT 11434)"
ZEAZ_LOCAL_MODEL="$(dotenv_get "$ENV_FILE" ZEAZ_LOCAL_MODEL unknown)"

cat <<EOF

zwslcore AI stack is running and inference-tested.

Open WebUI : http://localhost:${OPENWEBUI_PORT:-3000}
Provider   : http://localhost:${PROVIDER_PORT:-8080}
LiteLLM    : http://localhost:${LITELLM_PORT:-4000}
Ollama     : http://localhost:${OLLAMA_PORT:-11434}
Default    : ${ZEAZ_LOCAL_MODEL}

Cloud provider fallback remains disabled until you explicitly enable it and configure provider keys.
EOF
