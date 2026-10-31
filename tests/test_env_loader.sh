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
DUPLICATE=first
DUPLICATE=last
EOF

rm -f /tmp/zwslcore-dotenv-should-not-exist

[[ "$(dotenv_get "$tmp" PORT 1)" == "8080" ]]
[[ "$(dotenv_get "$tmp" OPENWEBUI_CORS_ALLOW_ORIGIN)" == "http://localhost:3000;http://127.0.0.1:3000" ]]
[[ "$(dotenv_get "$tmp" SPACED)" == "value with spaces" ]]
# Keep the command substitution literal: executing it would invalidate this test.
# shellcheck disable=SC2016
[[ "$(dotenv_get "$tmp" DANGEROUS)" == '$(touch /tmp/zwslcore-dotenv-should-not-exist)' ]]
[[ "$(dotenv_get "$tmp" QUOTED)" == "hello world" ]]
[[ "$(dotenv_get "$tmp" DUPLICATE)" == "last" ]]
[[ "$(dotenv_get "$tmp" MISSING fallback)" == "fallback" ]]
[[ ! -e /tmp/zwslcore-dotenv-should-not-exist ]]

auth_file="${tmp}.auth"
write_curl_auth_header "$auth_file" 'test-secret'
[[ "$(stat -c '%a' "$auth_file")" == "600" ]]
[[ "$(cat "$auth_file")" == "Authorization: Bearer test-secret" ]]
if write_curl_auth_header "${tmp}.bad-auth" $'bad\nheader' >/dev/null 2>&1; then
  printf 'write_curl_auth_header accepted a line break in a key\n' >&2
  exit 1
fi
rm -f "$auth_file" "${tmp}.bad-auth"

link="${tmp}.link"
ln -s "$tmp" "$link"
if dotenv_get "$link" PORT >/dev/null 2>&1; then
  printf 'dotenv_get unexpectedly followed a symlink\n' >&2
  exit 1
fi
rm -f "$link"

printf '[PASS] safe dotenv parsing\n'
