#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

[[ -f "$ENV_FILE" ]] || { echo "missing .env; run scripts/install.sh" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

fail=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf '[PASS] %s\n' "$name"
  else
    printf '[FAIL] %s\n' "$name" >&2
    fail=1
  fi
}

check "docker" docker info
check "compose config" docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" config --quiet
container_running() {
  local name="$1"
  [[ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || true)" == "true" ]]
}

check "ollama container" container_running zwslcore-ollama
check "litellm container" container_running zwslcore-litellm
check "provider container" container_running zwslcore-provider
check "open-webui container" container_running zwslcore-open-webui
check "ollama api" curl -fsS "http://127.0.0.1:${OLLAMA_PORT:-11434}/api/tags"
check "litellm readiness" curl -fsS "http://127.0.0.1:${LITELLM_PORT:-4000}/health/readiness"
check "provider live" curl -fsS "http://127.0.0.1:${PROVIDER_PORT:-8080}/health/live"
check "provider models" curl -fsS -H "Authorization: Bearer ${PROVIDER_CLIENT_KEY}" "http://127.0.0.1:${PROVIDER_PORT:-8080}/v1/models"
if curl -fsS "http://127.0.0.1:${OPENWEBUI_PORT:-3000}/health" >/dev/null 2>&1; then
  printf '[PASS] open-webui\n'
else
  printf '[FAIL] open-webui\n' >&2
  printf '[INFO] open-webui HTTP diagnostics:\n' >&2
  curl -sS -i --max-time 10 "http://127.0.0.1:${OPENWEBUI_PORT:-3000}/health" >&2 || true
  printf '\n[INFO] open-webui container status:\n' >&2
  docker inspect -f 'running={{.State.Running}} status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' zwslcore-open-webui >&2 || true
  printf '[INFO] open-webui recent logs:\n' >&2
  docker logs --tail=80 zwslcore-open-webui >&2 || true
  fail=1
fi

exit "$fail"
