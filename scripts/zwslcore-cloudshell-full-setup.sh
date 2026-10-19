#!/usr/bin/env bash
# Install and validate the supported zwslcore Cloud Shell profile.
set -Eeuo pipefail
umask 077
ROOT="${ZWSL_ROOT:-$HOME/zwslcore}"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-setup"
mkdir -p "$LOG_DIR" && chmod 700 "$LOG_DIR"
LOG="$LOG_DIR/setup-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$LOG") 2>&1
trap 'printf "FAIL at line %s (exit %s); log: %s\n" "$LINENO" "$?" "$LOG" >&2' ERR
step() { printf '\n=== %s ===\n' "$1"; }
step 'Prerequisites'
for cmd in git python3 bash make; do command -v "$cmd" >/dev/null || { echo "Missing: $cmd" >&2; exit 1; }; done
[[ -d "$ROOT/.git" ]] || { echo "Repository missing at $ROOT; clone it first." >&2; exit 1; }
cd "$ROOT"
step 'Git state (non-destructive)'
git status --short --branch
git remote -v | sed -E 's#(https?://)[^/@]+@#\1[REDACTED]@#g'
if [[ "${ZWSL_SYNC_MAIN:-0}" == 1 ]]; then
  [[ -z "$(git status --porcelain)" ]] || { echo 'Dirty checkout; cannot sync automatically' >&2; exit 1; }
  [[ "$(git branch --show-current)" == main ]] || { echo 'Switch to main manually before sync' >&2; exit 1; }
  git pull --ff-only origin main
fi
step 'Cloud Shell bootstrap'
make cloudshell
step 'AI CLI self-test'
make ai-test
step 'AI configuration diagnostics'
bash scripts/ai.sh doctor
step 'Optional Cloudflare diagnostics'
if command -v cloudflared >/dev/null 2>&1; then
  cloudflared --version
  if [[ -f "$HOME/.cloudflared/config.yml" ]]; then
    cloudflared tunnel --config "$HOME/.cloudflared/config.yml" ingress validate
  fi
else
  echo 'cloudflared not installed (optional)'
fi
for f in scripts/zwsl-cloudflare.sh scripts/zwsl-ssh-repair.sh scripts/zcloud-tunnel.sh scripts/install-zwsl-remote-exec.sh; do
  if [[ -f "$f" ]]; then bash -n "$f" && echo "syntax OK: $f"; else echo "not present on checked-out revision: $f"; fi
done
step 'Optional local MCP diagnostics'
if [[ "${ZWSL_INSTALL_MCP:-0}" == 1 ]]; then
  [[ -f scripts/install-zwsl-remote-exec.sh ]] || { echo 'MCP installer not present in checkout' >&2; exit 1; }
  bash scripts/install-zwsl-remote-exec.sh install
  bash scripts/install-zwsl-remote-exec.sh check
else
  echo 'MCP skipped; set ZWSL_INSTALL_MCP=1 only after reviewing the installer.'
fi
step 'Optional native Open WebUI'
if [[ "${ZWSL_INSTALL_WEBUI:-0}" == 1 ]]; then
  [[ -f scripts/cloudshell-webui.sh ]] || { echo 'Missing WebUI installer' >&2; exit 1; }
  bash scripts/cloudshell-webui.sh install
  echo 'WebUI installed but not started; configure authentication and trusted local access before startup.'
else
  echo 'Open WebUI skipped. Explicit opt-in: ZWSL_INSTALL_WEBUI=1.'
fi
step 'Result'
echo 'Cloud Shell profile checks completed.'
echo "Report: $LOG"
echo 'Not verified by this script: paid/free provider authorization, live chat inference, WebUI HTTP health, Cloudflare Access policy, SSH E2E, ChatGPT remote connector.'
