#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
PROFILE_FILE="$ROOT/.env.cloudflare"
COMPOSE_FILE="$ROOT/compose.yaml"

if [[ ! -f "$ENV_FILE" ]]; then
  printf 'Missing %s. Run make install first.\n' "$ENV_FILE" >&2
  exit 2
fi

if [[ ! -f "$PROFILE_FILE" ]]; then
  install -m 0600 "$ROOT/.env.cloudflare.example" "$PROFILE_FILE"
  printf 'Created %s with the reviewed zwsl.zeaz.dev settings.\n' "$PROFILE_FILE"
fi

export PROVIDER_PORT=18086
export OPENWEBUI_PORT=18087

docker compose \
  --project-directory "$ROOT" \
  --file "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  --env-file "$PROFILE_FILE" \
  config --quiet

docker compose \
  --project-directory "$ROOT" \
  --file "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  --env-file "$PROFILE_FILE" \
  up --detach provider open-webui

printf 'Provider loopback:   http://127.0.0.1:18086\n'
printf 'Open WebUI loopback: http://127.0.0.1:18087\n'
