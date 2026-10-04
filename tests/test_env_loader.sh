#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/env.sh
source "$ROOT/scripts/lib/env.sh"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

cat >"$tmp" <<'EOF'
PORT=8080
OPENWEBUI_CORS_ALLOW_ORIGIN=http://localhost:3000;http://127.0.0.1:3000
SPACED=value with spaces
DANGEROUS=$(touch /tmp/zwslcore-dotenv-should-not-exist)
QUOTED="hello world"
EOF

rm -f /tmp/zwslcore-dotenv-should-not-exist

[[ "$(dotenv_get "$tmp" PORT 1)" == "8080" ]]
[[ "$(dotenv_get "$tmp" OPENWEBUI_CORS_ALLOW_ORIGIN)" == "http://localhost:3000;http://127.0.0.1:3000" ]]
[[ "$(dotenv_get "$tmp" SPACED)" == "value with spaces" ]]
[[ "$(dotenv_get "$tmp" DANGEROUS)" == '$(touch /tmp/zwslcore-dotenv-should-not-exist)' ]]
[[ "$(dotenv_get "$tmp" QUOTED)" == "hello world" ]]
[[ "$(dotenv_get "$tmp" MISSING fallback)" == "fallback" ]]
[[ ! -e /tmp/zwslcore-dotenv-should-not-exist ]]

printf '[PASS] safe dotenv parsing\n'
