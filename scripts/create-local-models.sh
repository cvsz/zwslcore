#!/usr/bin/env bash
set -Eeuo pipefail

CONTAINER="${OLLAMA_CONTAINER:-zwslcore-ollama}"
WORKDIR="${TMPDIR:-/tmp}/zwslcore-models"
mkdir -p "$WORKDIR"

cat >"$WORKDIR/Modelfile.fast" <<'EOF'
FROM qwen2.5-coder:3b
PARAMETER temperature 0.05
PARAMETER top_p 0.8
PARAMETER repeat_penalty 1.15
PARAMETER num_ctx 4096
SYSTEM """
You are zwslcore-fast, a local coding assistant.
Inspect before editing. Prefer minimal patches. Never expose secrets.
Always provide validation commands for proposed repository changes.
"""
EOF

cat >"$WORKDIR/Modelfile.coder" <<'EOF'
FROM qwen2.5-coder:7b
PARAMETER temperature 0.05
PARAMETER top_p 0.8
PARAMETER repeat_penalty 1.12
PARAMETER num_ctx 8192
SYSTEM """
You are zwslcore-coder, a local coding and review assistant.
Inspect before editing. Prefer minimal safe changes. Never expose secrets.
Consider tests, security, rollback, and operational impact.
"""
EOF

docker exec "$CONTAINER" ollama pull qwen2.5-coder:3b
docker cp "$WORKDIR/Modelfile.fast" "$CONTAINER:/tmp/Modelfile.fast"
docker exec "$CONTAINER" ollama create zwslcore-fast -f /tmp/Modelfile.fast

docker exec "$CONTAINER" ollama pull qwen2.5-coder:7b
docker cp "$WORKDIR/Modelfile.coder" "$CONTAINER:/tmp/Modelfile.coder"
docker exec "$CONTAINER" ollama create zwslcore-coder -f /tmp/Modelfile.coder

docker exec "$CONTAINER" ollama list
