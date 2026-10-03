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
check "ollama container" docker inspect -f '{{.State.Running}}' zwslcore-ollama
check "litellm container" docker inspect -f '{{.State.Running}}' zwslcore-litellm
check "open-webui container" docker inspect -f '{{.State.Running}}' zwslcore-open-webui
check "ollama api" curl -fsS "http://127.0.0.1:${OLLAMA_PORT:-11434}/api/tags"
check "litellm models" curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" "http://127.0.0.1:${LITELLM_PORT:-4000}/v1/models"
check "open-webui" curl -fsS "http://127.0.0.1:${OPENWEBUI_PORT:-3000}/health"

exit "$fail"
