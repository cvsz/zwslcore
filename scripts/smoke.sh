#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

[[ -f "$ENV_FILE" ]] || { echo "missing .env; run scripts/install.sh" >&2; exit 1; }

# shellcheck source=scripts/lib/env.sh
source "$ROOT/scripts/lib/env.sh"
LITELLM_PORT="$(dotenv_get "$ENV_FILE" LITELLM_PORT 4000)"
PROVIDER_PORT="$(dotenv_get "$ENV_FILE" PROVIDER_PORT 8080)"
PROVIDER_CLIENT_KEY="$(dotenv_get "$ENV_FILE" PROVIDER_CLIENT_KEY)"
LITELLM_MASTER_KEY="$(dotenv_get "$ENV_FILE" LITELLM_MASTER_KEY)"
AUTH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zwslcore-smoke.XXXXXX")"
chmod 700 "$AUTH_DIR"
trap 'rm -rf -- "$AUTH_DIR"' EXIT
LITELLM_AUTH_FILE="$AUTH_DIR/litellm.header"
PROVIDER_AUTH_FILE="$AUTH_DIR/provider.header"
write_curl_auth_header "$LITELLM_AUTH_FILE" "$LITELLM_MASTER_KEY"
write_curl_auth_header "$PROVIDER_AUTH_FILE" "$PROVIDER_CLIENT_KEY"

if ! models_json="$(curl -fsS --max-time 20 \
  -H "@$LITELLM_AUTH_FILE" \
  "http://127.0.0.1:${LITELLM_PORT:-4000}/v1/models")"; then
  echo "[FAIL] LiteLLM model catalog unavailable; check PostgreSQL connectivity with make doctor." >&2
  exit 1
fi
printf '%s\n' "$models_json" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, UnicodeDecodeError):
    raise SystemExit("[FAIL] LiteLLM returned an invalid model catalog.")
if not isinstance(data, dict) or not isinstance(data.get("data"), list):
    raise SystemExit("[FAIL] LiteLLM model catalog has an invalid response shape.")
if not any(isinstance(model, dict) and model.get("id") == "zeaz-coder" for model in data["data"]):
    raise SystemExit("[FAIL] LiteLLM model catalog is missing zeaz-coder.")
print("[PASS] LiteLLM model catalog")
'

litellm_payload='{"model":"zeaz-coder","messages":[{"role":"user","content":"Reply exactly OK"}],"temperature":0,"max_tokens":8}'
litellm_response="$(
  curl -fsS --max-time 180 \
    -H "@$LITELLM_AUTH_FILE" \
    -H "Content-Type: application/json" \
    -d "$litellm_payload" \
    "http://127.0.0.1:${LITELLM_PORT:-4000}/v1/chat/completions"
)"
python3 - "$litellm_response" <<'PY'
import json
import sys

value = json.loads(sys.argv[1])
choices = value.get("choices")
if not isinstance(choices, list) or not choices:
    raise SystemExit("LiteLLM returned no choices")
print("[PASS] litellm inference")
PY

payload='{"model":"zeaz-fast","messages":[{"role":"user","content":"Reply exactly OK"}],"temperature":0,"max_tokens":32}'
response="$(
  curl -fsS --max-time 180 -H "@$PROVIDER_AUTH_FILE" -H "Content-Type: application/json" -d "$payload" "http://127.0.0.1:${PROVIDER_PORT:-8080}/v1/chat/completions"
)"

python3 - "$response" <<'PY'
import json
import sys

value = json.loads(sys.argv[1])
choices = value.get("choices")
if not isinstance(choices, list) or not choices:
    raise SystemExit("provider returned no choices")
message = choices[0].get("message", {})
content = message.get("content")
if not isinstance(content, str) or not content.strip():
    raise SystemExit("provider returned an empty completion")
print("[PASS] provider inference")
PY


structured_payload='{"model":"zeaz-fast","messages":[{"role":"user","content":"Return a JSON object with status exactly OK."}],"temperature":0,"max_tokens":64,"response_format":{"type":"json_schema","json_schema":{"name":"status_response","strict":true,"schema":{"type":"object","additionalProperties":false,"required":["status"],"properties":{"status":{"type":"string","enum":["OK"]}}}}}}'
structured_response="$(
  curl -fsS --max-time 180 \
    -H "@$PROVIDER_AUTH_FILE" \
    -H "Content-Type: application/json" \
    -d "$structured_payload" \
    "http://127.0.0.1:${PROVIDER_PORT:-8080}/v1/chat/completions"
)"

python3 - "$structured_response" <<'PY'
import json
import sys

value = json.loads(sys.argv[1])
choices = value.get("choices")
if not isinstance(choices, list) or not choices:
    raise SystemExit("provider structured output returned no choices")
content = choices[0].get("message", {}).get("content")
if not isinstance(content, str) or not content.strip():
    raise SystemExit("provider structured output returned empty content")
parsed = json.loads(content)
if parsed != {"status": "OK"}:
    raise SystemExit(f"provider structured output violated schema: {parsed!r}")
print("[PASS] provider structured inference")
PY
