#!/usr/bin/env bash
set -Eeuo pipefail

case "$(uname -s)" in
  Linux*) ;;
  *)
    echo "doctor.sh must run inside Linux/WSL. On Windows use scripts/doctor-wsl.ps1." >&2
    exit 2
    ;;
esac

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

container_running() {
  local name="$1"
  [[ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || true)" == "true" ]]
}

container_healthy() {
  local name="$1"
  local status
  status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || true)"
  [[ "$status" == "healthy" ]]
}

check "docker" docker info
check "compose config" docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" config --quiet

for name in zwslcore-ollama zwslcore-litellm zwslcore-provider zwslcore-open-webui; do
  check "$name running" container_running "$name"
  check "$name health" container_healthy "$name"
done

check "ollama api" curl -fsS --max-time 10 "http://127.0.0.1:${OLLAMA_PORT:-11434}/api/tags"
check "litellm readiness" curl -fsS --max-time 10 "http://127.0.0.1:${LITELLM_PORT:-4000}/health/readiness"
check "provider ready" curl -fsS --max-time 10 "http://127.0.0.1:${PROVIDER_PORT:-8080}/health/ready"
check "provider models" curl -fsS --max-time 10 -H "Authorization: Bearer ${PROVIDER_CLIENT_KEY}" "http://127.0.0.1:${PROVIDER_PORT:-8080}/v1/models"

if curl -fsS --max-time 10 "http://127.0.0.1:${OPENWEBUI_PORT:-3000}/health" >/dev/null 2>&1; then
  printf '[PASS] open-webui\n'
else
  printf '[FAIL] open-webui\n' >&2
  fail=1
fi

if (( fail != 0 )); then
  printf '\n[INFO] docker compose ps\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" ps >&2 || true

  printf '\n[INFO] LiteLLM readiness response\n' >&2
  curl -sS -i --max-time 10 "http://127.0.0.1:${LITELLM_PORT:-4000}/health/readiness" >&2 || true

  printf '\n[INFO] Open WebUI health response\n' >&2
  curl -sS -i --max-time 10 "http://127.0.0.1:${OPENWEBUI_PORT:-3000}/health" >&2 || true

  printf '\n[INFO] recent LiteLLM/Open WebUI logs\n' >&2
  docker compose -f "$ROOT/compose.yaml" --env-file "$ENV_FILE" logs --tail=80 litellm open-webui >&2 || true
fi

exit "$fail"
