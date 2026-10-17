#!/usr/bin/env bash
# Opt-in Cloud Shell native Open WebUI installer (no Docker required).
set -Eeuo pipefail
umask 077
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
PYTHON_VERSION="$(python3 -c 'import sys; print(sys.version_info.major * 100 + sys.version_info.minor)')"
if (( PYTHON_VERSION < 311 || PYTHON_VERSION > 312 )); then
  echo "This bootstrap supports Python 3.11/3.12; detected unsupported version." >&2
  exit 1
fi
BASE="${ZWSL_WEBUI_BASE:-/opt/zeaz-storage}"
DATA="${ZWSL_WEBUI_DATA:-$HOME/.local/share/zwslcore-webui}"
VENV="$BASE/venvs/openwebui"
mkdir -p "$DATA"
chmod 700 "$DATA"
if [[ ! -e "$DATA/secret" ]]; then
  python3 -c 'import secrets; print(secrets.token_hex(32))' > "$DATA/secret"
fi
[[ -f "$DATA/secret" && ! -L "$DATA/secret" ]] || { echo "Invalid secret file" >&2; exit 1; }
chmod 600 "$DATA/secret"
if [[ ! -d "$BASE" ]]; then
  echo "Create $BASE as a user-writable temporary storage directory first" >&2
  exit 1
fi
[[ -w "$BASE" ]] || { echo "$BASE is not writable" >&2; exit 1; }
mkdir -p "$BASE/venvs" "$BASE/cache" "$BASE/tmp"
export TMPDIR="$BASE/tmp" XDG_CACHE_HOME="$BASE/cache" PIP_CACHE_DIR="$BASE/cache/pip"
case "${1:-}" in
  install)
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install open-webui
    ;;
  start)
    [[ -x "$VENV/bin/open-webui" ]] || { echo "Run install first" >&2; exit 1; }
    export DATA_DIR="$DATA" WEBUI_SECRET_KEY="$(cat "$DATA/secret")"
    export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
    export ENABLE_SIGNUP="${ENABLE_SIGNUP:-false}"
    export WEBUI_AUTH="${WEBUI_AUTH:-true}"
    exec "$VENV/bin/open-webui" serve --host 127.0.0.1 --port "${ZWSL_WEBUI_PORT:-3000}"
    ;;
  health)
    curl --fail --silent --show-error "http://127.0.0.1:${ZWSL_WEBUI_PORT:-3000}/health"
    ;;
  *)
    echo "Usage: bash scripts/cloudshell-webui.sh {install|start|health}" >&2
    exit 2
    ;;
esac
