#!/usr/bin/env bash
# Cloud Shell profile: CLI only, no Docker/PostgreSQL/system packages.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -n "${CLOUD_SHELL:-}" || -n "${DEVSHELL_PROJECT_ID:-}" || "${1:-}" == "--allow-non-cloud-shell" ]] || {
  echo "Not Cloud Shell. Use --allow-non-cloud-shell for CLI-only setup." >&2; exit 2;
}
command -v python3 >/dev/null || { echo "Python 3 required" >&2; exit 1; }
bash -n "$ROOT/scripts/ai.sh"
bash "$ROOT/scripts/ai.sh" selftest
cat <<'EOF'
Cloud Shell CLI profile is ready (no background services started).
Configure a remote HTTPS OpenAI-compatible endpoint:
  export AI_API_URL='https://YOUR_PROVIDER/v1/chat/completions'
  export AI_MODEL='YOUR_MODEL'
  read -rsp 'API key: ' AI_API_KEY; echo; export AI_API_KEY
  bash scripts/ai.sh doctor
  bash scripts/ai.sh chat

Notes:
- Google Cloud project selection does not grant third-party LLM API access.
- Avoid saving API keys in shell history or committing them to Git.
- Docker, Ollama, PostgreSQL and the full Compose stack are intentionally skipped.
- Cloud Shell VM is ephemeral; use persistent hosting for always-on services.
EOF
