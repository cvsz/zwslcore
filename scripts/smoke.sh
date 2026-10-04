#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

[[ -f "$ENV_FILE" ]] || { echo "missing .env; run scripts/install.sh" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

curl -fsS --max-time 20   -H "Authorization: Bearer ${LITELLM_MASTER_KEY}"   "http://127.0.0.1:${LITELLM_PORT:-4000}/v1/models"   | python3 -c 'import json,sys; data=json.load(sys.stdin); assert any(m.get("id") == "zeaz-coder" for m in data.get("data", []))'

litellm_payload='{"model":"zeaz-coder","messages":[{"role":"user","content":"Reply exactly OK"}],"temperature":0,"max_tokens":8}'
litellm_response="$(
  curl -fsS --max-time 180 \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
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

payload='{"model":"zeaz-local","messages":[{"role":"user","content":"Reply exactly OK"}],"temperature":0,"max_tokens":8}'
response="$(
  curl -fsS --max-time 180     -H "Authorization: Bearer ${PROVIDER_CLIENT_KEY}"     -H "Content-Type: application/json"     -d "$payload"     "http://127.0.0.1:${PROVIDER_PORT:-8080}/v1/chat/completions"
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
