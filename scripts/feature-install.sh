#!/usr/bin/env bash
# Capability-aware zwslcore preflight and installation orchestrator.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${ZWSL_PROFILE:-auto}"
MODE="${1:-preflight}"
INSTALL_WEBUI="${ZWSL_INSTALL_WEBUI:-0}"
INSTALL_MCP="${ZWSL_INSTALL_MCP:-0}"
MODEL_POLICY="${ZWSL_MODEL_POLICY:-reuse}"
STORAGE="${ZWSL_WEBUI_BASE:-/opt/zeaz-storage}"
require() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING: $1" >&2; return 1; }; }
note() { printf '[zwslcore] %s\n' "$*"; }
detect_profile() {
  if [[ "$PROFILE" == auto ]]; then
    if [[ -n "${CLOUD_SHELL:-}" || -n "${DEVSHELL_PROJECT_ID:-}" ]]; then PROFILE=cloudshell
    elif grep -qi microsoft /proc/version 2>/dev/null; then PROFILE=wsl2
    else PROFILE=linux
    fi
  fi
  case "$PROFILE" in cloudshell|wsl2|linux) ;; *) echo "Invalid ZWSL_PROFILE" >&2; exit 2;; esac
}
report() {
  local name="$1" check="$2"
  if eval "$check" >/dev/null 2>&1; then note "PASS: $name"; return 0
  else note "UNAVAILABLE: $name"; return 1; fi
}
preflight() {
  local failed=0
  note "profile=$PROFILE mode=$MODE model_policy=$MODEL_POLICY"
  for name in bash git python3 curl; do require "$name" || failed=1; done
  [[ -f "$ROOT/Makefile" && -f "$ROOT/scripts/cloudshell.sh" ]] || { note "Missing repository files"; failed=1; }
  if command -v git >/dev/null; then
    git -C "$ROOT" status --short --branch || failed=1
  fi
  note "Feature inventory (UNAVAILABLE means an optional feature is not ready):"
  report "AI CLI" "test -f '$ROOT/scripts/ai.sh'" || true
  report "Ollama installed" "command -v ollama" || true
  report "Ollama API responding" "curl -fsS --max-time 3 http://127.0.0.1:11434/api/version" || true
  if command -v ollama >/dev/null; then ollama list || true; fi
  report "Open WebUI installed (native)" "test -x '$STORAGE/venvs/openwebui/bin/open-webui'" || true
  report "Open WebUI health" "curl -fsS --max-time 3 http://127.0.0.1:3000/health" || true
  report "Local MCP server" "test -f '$HOME/.local/share/zwsl-remote-exec/server.py'" || true
  report "Cloudflare CLI" "command -v cloudflared" || true
  report "Cloudflare config" "test -f '$HOME/.cloudflared/config.yml'" || true
  report "SSH listener" "ss -lnt | grep -Eq '[:.]22[[:space:]]'" || true
  report "Docker Compose" "docker compose version" || true
  report "PostgreSQL host listener" "ss -lnt | grep -Eq '[:.]5432[[:space:]]'" || true
  if [[ "$PROFILE" == cloudshell ]]; then
    note "Cloud Shell: Compose, host PostgreSQL, and model downloads are not provisioned."
    if [[ "$INSTALL_WEBUI" == 1 ]]; then
      [[ -d "$STORAGE" && -w "$STORAGE" ]] || { note "WebUI storage must exist and be writable: $STORAGE"; failed=1; }
      python3 -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' || failed=1
      require python3 || failed=1
    fi
  else
    if [[ "$MODE" == install && "$MODEL_POLICY" == reuse ]]; then
      note "Full-stack installer may download models. Refusing to invoke it with MODEL_POLICY=reuse."
      failed=1
    fi
    if [[ "$MODE" == install ]]; then
      require docker || failed=1
      docker compose version >/dev/null 2>&1 || failed=1
    fi
  fi
  return "$failed"
}
verify() {
  bash -n "$ROOT/scripts/cloudshell.sh" "$ROOT/scripts/ai.sh"
  bash "$ROOT/scripts/ai.sh" selftest
  if [[ "$PROFILE" == cloudshell ]]; then
    if [[ "$INSTALL_WEBUI" == 1 ]]; then
      bash "$ROOT/scripts/cloudshell-webui.sh" health
    fi
    if [[ "$INSTALL_MCP" == 1 ]]; then
      bash "$ROOT/scripts/install-zwsl-remote-exec.sh" check
    fi
  else
    make -C "$ROOT" doctor
  fi
}
detect_profile
[[ "$MODEL_POLICY" == reuse || "$MODEL_POLICY" == provision ]] || { echo "Invalid model policy" >&2; exit 2; }
case "$MODE" in
  preflight) preflight ;;
  install)
    preflight
    if [[ "$PROFILE" == cloudshell ]]; then
      make -C "$ROOT" cloudshell
      make -C "$ROOT" ai-test
      if [[ "$INSTALL_MCP" == 1 ]]; then
        [[ -f "$ROOT/scripts/install-zwsl-remote-exec.sh" ]] || { note "Missing optional MCP installer"; exit 1; }
        bash "$ROOT/scripts/install-zwsl-remote-exec.sh" install
      fi
      if [[ "$INSTALL_WEBUI" == 1 ]]; then
        bash "$ROOT/scripts/cloudshell-webui.sh" install
        note "Open WebUI installed but NOT started. First admin registration must remain local and authenticated."
      fi
      note "Cloud Shell installation complete. Existing Ollama models and Tunnel processes were not modified."
    else
      [[ "$MODEL_POLICY" == provision ]] || { note "Use ZWSL_MODEL_POLICY=provision only after reviewing model pulls."; exit 1; }
      make -C "$ROOT" install
    fi
    ;;
  verify) verify ;;
  *) echo "Usage: ZWSL_PROFILE=auto|cloudshell|wsl2|linux ZWSL_MODEL_POLICY=reuse|provision ZWSL_INSTALL_WEBUI=0|1 ZWSL_INSTALL_MCP=0|1 $0 {preflight|install|verify}" >&2; exit 2;;
esac
