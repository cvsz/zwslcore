#!/usr/bin/env bash
# Launch Codex CLI against the local zwslcore Provider gateway.
#
# Reads only PROVIDER_CLIENT_KEY (and PROVIDER_PORT) from the private
# production env file, exports them as OpenAI-compatible client settings,
# verifies the local Provider is reachable, then hands over to codex.
# Model and profile selection follows your own Codex configuration;
# extra arguments are passed through untouched.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ZW_ENV_FILE:-$ROOT/.env.production}"

[[ -f "$ENV_FILE" ]] || { printf 'Missing %s. Copy .env to %s and set production values first.\n' "$ENV_FILE" "$ENV_FILE" >&2; exit 2; }
PROVIDER_CLIENT_KEY="$(sed -n 's/^PROVIDER_CLIENT_KEY=//p' "$ENV_FILE" | tail -n1)"
[[ -n "$PROVIDER_CLIENT_KEY" ]] || { printf 'PROVIDER_CLIENT_KEY is missing from %s.\n' "$ENV_FILE" >&2; exit 2; }
PROVIDER_PORT="$(sed -n 's/^PROVIDER_PORT=//p' "$ENV_FILE" | tail -n1)"
PROVIDER_PORT="${PROVIDER_PORT:-8080}"
command -v codex >/dev/null 2>&1 || { printf 'Codex CLI is not installed in this environment.\n' >&2; exit 2; }

if ! curl -fsS --max-time 10 "http://127.0.0.1:${PROVIDER_PORT}/health/ready" >/dev/null 2>&1; then
  printf 'Local Provider is not ready at 127.0.0.1:%s. Start the stack first.\n' "$PROVIDER_PORT" >&2
  exit 2
fi

export OPENAI_API_KEY="$PROVIDER_CLIENT_KEY"
export OPENAI_BASE_URL="http://127.0.0.1:${PROVIDER_PORT}/v1"
exec codex "$@"
