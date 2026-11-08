# Local GGUF Models

This directory contains GGUF-format model files imported from SERVER_CORE
(`ssh -p 2223 cvsz@192.168.1.85:/home/cvsz/zcoder/models/`).

| File | Size | Purpose |
|------|------|---------|
| `qwen-1.5b-q4km.gguf` | ~1.1 GB | Fast model (`zwslcore-qwen-1.5b-q4km`) |
| `qwen-7b-q4km.gguf` | ~4.4 GB | Coder/reasoning model (`zwslcore-qwen-7b-q4km`) |

## Usage with Ollama

GGUF models are imported into Ollama via Modelfile:

```bash
docker cp models/qwen-1.5b-q4km.gguf zwslcore-ollama:/tmp/qwen-1.5b-q4km.gguf
docker cp models/Modelfile.gguf-fast zwslcore-ollama:/tmp/Modelfile.gguf-fast
docker exec zwslcore-ollama ollama create zwslcore-qwen-1.5b-q4km -f /tmp/Modelfile.gguf-fast
```

The installer (`scripts/install.sh`) handles GGUF import automatically when
`ZEAZ_GGUF_MODEL_DIR` points to a directory containing the `.gguf` files.

## Model Mapping

| GGUF Model | Ollama Alias | Env Var |
|------------|-------------|---------|
| `qwen-1.5b-q4km.gguf` | `zwslcore-qwen-1.5b-q4km` | `ZEAZ_FAST_MODEL` |
| `qwen-7b-q4km.gguf` | `zwslcore-qwen-7b-q4km` | `ZEAZ_CODER_MODEL`, `ZEAZ_REASONING_MODEL`, `ZEAZ_LOCAL_MODEL` |
