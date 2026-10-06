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
  printf 'Created %s from the example. Set the real public hostname there.\n' "$PROFILE_FILE"
fi

# Keep long-lived port overrides in the ignored profile so every compose
# invocation that loads the overlay agrees; backfill older copies.
for entry in PROVIDER_PORT=18086 OPENWEBUI_PORT=18087; do
  if ! grep -q "^${entry%%=*}=" "$PROFILE_FILE"; then
    printf '%s\n' "$entry" >> "$PROFILE_FILE"
  fi
done

# shellcheck disable=SC1090
set -a; source "$PROFILE_FILE"; set +a

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

printf 'Provider loopback:   http://127.0.0.1:%s\n' "$PROVIDER_PORT"
printf 'Open WebUI loopback: http://127.0.0.1:%s\n' "$OPENWEBUI_PORT"
printf 'Health commands read .env defaults; reload this profile overlay to probe these ports.\n'
