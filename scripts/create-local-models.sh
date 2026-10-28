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

# --- Import MiniMax-H3 GGUF models into Ollama ---
MINIMAX_H3_DIR="${ZEAZ_MINIMAX_H3_MODEL_DIR:-/home/cvsz/zcoder/models/minimax-h3}"
if [[ -d "$MINIMAX_H3_DIR" ]]; then
  docker exec "$CONTAINER" mkdir -p /tmp/zwslcore-gguf/minimax-h3
  for gguf in "$MINIMAX_H3_DIR"/*.gguf; do
    [[ -f "$gguf" ]] || continue
    name="$(basename "$gguf" .gguf)"
    alias="zwslcore-$name"
    docker cp "$gguf" "$CONTAINER:/tmp/zwslcore-gguf/minimax-h3/$(basename "$gguf")"
    cat >"$WORKDIR/Modelfile.minimax-$name" <<EOF
FROM /tmp/zwslcore-gguf/minimax-h3/$(basename "$gguf")
PARAMETER temperature 0.0
PARAMETER top_p 1.0
PARAMETER repeat_penalty 1.0
PARAMETER num_ctx 4096
SYSTEM """
You are $alias, a MiniMax-H3 video generation model (GGUF quantization).
This is an Image-Text-to-Video model, NOT a text chat model. Use with
stable-diffusion.cpp, not with Ollama chat.
"""
EOF
    docker cp "$WORKDIR/Modelfile.minimax-$name" "$CONTAINER:/tmp/Modelfile.minimax-$name"
    if ! docker exec "$CONTAINER" ollama list | awk 'NR>1 {print $1}' | grep -qx "$alias"; then
      echo "Importing GGUF model $(basename "$gguf") as $alias"
      docker exec "$CONTAINER" ollama create "$alias" -f "/tmp/Modelfile.minimax-$name"
    else
      echo "GGUF model $alias already present in Ollama"
    fi
  done
else
  echo "MiniMax-H3 directory $MINIMAX_H3_DIR not found; skipping GGUF import."
fi

docker exec "$CONTAINER" ollama list
