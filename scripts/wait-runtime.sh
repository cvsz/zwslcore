#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
TIMEOUT="${ZW_RUNTIME_WAIT_TIMEOUT:-300}"
STABLE_PASSES="${ZW_RUNTIME_STABLE_PASSES:-3}"
INTERVAL="${ZW_RUNTIME_WAIT_INTERVAL:-5}"

[[ -f "$ENV_FILE" ]] || { echo "missing .env; run scripts/install.sh" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

containers=(
  zwslcore-ollama
  zwslcore-litellm
  zwslcore-provider
  zwslcore-open-webui
)

container_healthy() {
  local name="$1"
  [[ "$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || true)" == "healthy" ]]
}

runtime_ready() {
  local name
  docker info >/dev/null 2>&1 || return 1
  for name in "${containers[@]}"; do
    [[ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || true)" == "true" ]] || return 1
    container_healthy "$name" || return 1
  done
  curl -fsS --max-time 5 "http://127.0.0.1:${OLLAMA_PORT:-11434}/api/tags" >/dev/null || return 1
  curl -fsS --max-time 5 "http://127.0.0.1:${LITELLM_PORT:-4000}/health/readiness" >/dev/null || return 1
  curl -fsS --max-time 5 "http://127.0.0.1:${PROVIDER_PORT:-8080}/health/ready" >/dev/null || return 1
  curl -fsS --max-time 5 "http://127.0.0.1:${OPENWEBUI_PORT:-3000}/health" >/dev/null || return 1
}

printf '[zwslcore] Waiting for runtime readiness (timeout=%ss, stable_passes=%s)\n' "$TIMEOUT" "$STABLE_PASSES"

deadline=$((SECONDS + TIMEOUT))
stable=0

while (( SECONDS < deadline )); do
  if runtime_ready; then
    stable=$((stable + 1))
    printf '[zwslcore] runtime readiness pass %s/%s\n' "$stable" "$STABLE_PASSES"
    if (( stable >= STABLE_PASSES )); then
      printf '[zwslcore] runtime is healthy and stable\n'
      exit 0
    fi
  else
    stable=0
  fi
  sleep "$INTERVAL"
done

printf '[zwslcore] ERROR: runtime did not become stable within %ss\n' "$TIMEOUT" >&2
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" ps >&2 || true
docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" logs --tail=120 >&2 || true
exit 1
