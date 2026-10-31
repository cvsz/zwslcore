#!/usr/bin/env bash
# Google Cloud Shell: cloud-first AI CLI with optional CPU Ollama.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() {
  cat <<'EOF'
Usage: bash scripts/cloudshell.sh [--allow-non-cloud-shell] [--install-ollama] [--model MODEL]
Cloud-first, CLI-only setup by default; no Docker, PostgreSQL or system packages.
  --install-ollama    Opt in to installing Ollama (requires curl, zstd).
  --model MODEL       Pull a model after installing/verifying Ollama (opt-in).
  --allow-non-cloud-shell  Permit running on a normal Linux workstation.
EOF
}
ALLOW=false
INSTALL=false
MODEL=""
while (($#)); do
  case "$1" in
    --allow-non-cloud-shell) ALLOW=true ;;
    --install-ollama) INSTALL=true ;;
    --model) (($# >= 2)) || { echo "Missing --model value" >&2; exit 2; }; MODEL="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
if [[ -z "${CLOUD_SHELL:-}" && -z "${DEVSHELL_PROJECT_ID:-}" && "$ALLOW" != true ]]; then
  echo "Not Cloud Shell. Use --allow-non-cloud-shell for CLI-only setup." >&2
  exit 2
fi
command -v python3 >/dev/null || { echo "Python 3 required" >&2; exit 1; }
bash -n "$ROOT/scripts/ai.sh"
bash "$ROOT/scripts/ai.sh" selftest

# Load repository .env for AI_API_URL/AI_MODEL credential lookup.
# Reject symlinked .env before any existence check so a dangling symlink
# is never mistaken for an absent file.
if [[ -L "$ROOT/.env" ]]; then
  echo "Refusing symlinked .env" >&2; exit 1
elif [[ -e "$ROOT/.env" ]]; then
  chmod 600 "$ROOT/.env"
  # Source allowlisted AI settings only; never execute shell commands.
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"   # ltrim
    line="${line%"${line##*[![:space:]]}"}"   # rtrim
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    key="${line%%=*}"; value="${line#*=}"
    case "$key" in
      AI_API_URL|AI_MODEL|AI_API_KEY|GEMINI_API_KEY|OPENROUTER_API_KEY|GROQ_API_KEY|PROVIDER_CLIENT_KEY)
        # Strip surrounding quotes.
        value="${value#\"}"; value="${value%\"}"
        value="${value#\'}"; value="${value%\'}"
        export "$key=$value"
        ;;
    esac
  done < "$ROOT/.env"
else
  echo "No .env detected; configure Gemini credentials locally (never commit secrets)."
fi

if [[ -e "$ROOT/.env" && ! -L "$ROOT/.env" ]]; then
  echo "Repository .env loaded (AI settings only)."
fi

if [[ -n "$MODEL" && "$INSTALL" != true ]] && ! command -v ollama >/dev/null 2>&1; then
  echo "--model requires Ollama; use --install-ollama" >&2; exit 2
fi

if [[ "$INSTALL" == true ]]; then
  # Verify required tools before confirming installation is needed.
  command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
  command -v zstd >/dev/null || { echo "zstd missing. Run: sudo apt-get update && sudo apt-get install -y zstd" >&2; echo "Cloud Shell system packages are ephemeral." >&2; exit 1; }
  if ! command -v ollama >/dev/null; then
    echo "Installing Ollama (ephemeral system installation)."
    # Download installer to a temp file, verify it is a shell script, then execute.
    # Never pipe curl directly to sh: inspect before executing.
    installer="$(mktemp)"
    trap 'rm -f "$installer"' EXIT
    curl -fsSL https://ollama.com/install.sh -o "$installer"
    head -1 "$installer" | grep -q '^#!' || { echo "Ollama installer is not a shell script" >&2; exit 1; }
    bash "$installer"
  fi
fi

if [[ "$INSTALL" == true || -n "$MODEL" ]]; then
  command -v ollama >/dev/null || { echo "Ollama binary not found" >&2; exit 1; }
  if ! ollama list >/dev/null 2>&1; then
    echo "Starting Ollama without systemd..."
    nohup ollama serve > "$HOME/ollama.log" 2>&1 < /dev/null &
    ready=false
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      if ollama list >/dev/null 2>&1; then ready=true; break; fi
      sleep 1
    done
    [[ "$ready" == true ]] || { echo "Ollama failed; inspect ~/ollama.log" >&2; exit 1; }
  fi
fi

if [[ -n "$MODEL" ]]; then
  [[ "$MODEL" =~ ^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$ ]] || { echo "Invalid model name" >&2; exit 2; }
  available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  # Check free space where models are stored (~/.ollama/models), not $HOME.
  ollama_dir="$HOME/.ollama"
  free_kib="$(df -Pk "$ollama_dir" 2>/dev/null | awk 'END {print $4}' || df -Pk "$HOME" | awk 'END {print $4}')"
  if [[ "$MODEL" == "qwen2.5-coder:7b" ]] && (( available_kib < 6*1024*1024 || free_kib < 6*1024*1024 )); then
    echo "Insufficient RAM or disk for qwen2.5-coder:7b (requires >=6 GiB available each)." >&2
    echo "Try a smaller model, or use Gemini Cloud." >&2
    exit 1
  fi
  ollama pull "$MODEL"
fi

cat <<'EOF'
Cloud Shell AI CLI profile ready.
  bash scripts/ai.sh doctor
  bash scripts/ai.sh ask "Reply with OK"
  bash scripts/ai.sh chat
Gemini Cloud remains the default when configured in .env.
Ollama is optional; the Cloud Shell VM and system installations are ephemeral.
Never commit API keys. Docker/PostgreSQL/Compose are not installed here.
EOF