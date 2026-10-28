# Acceleration and quantization policy

zwslcore keeps Ollama as the default local inference backend and chooses a safe runtime profile from detected hardware.

## Current host behavior

On CPU-only or unsupported-GPU hosts:

- backend: Ollama
- quantization policy: Q4_K_M
- context length: 4096
- Flash Attention: disabled
- vLLM: not selected

This is the expected profile for the current Ryzen 5 3400G WSL host when no supported compute GPU is visible inside WSL.

## NVIDIA profile

When `nvidia-smi` is available:

- 8-15 GiB VRAM: context 8192, Flash Attention enabled
- 16+ GiB VRAM: context 16384, Flash Attention enabled
- vLLM becomes a candidate at 8+ GiB VRAM

Ollama remains the default backend unless the operator explicitly chooses another runtime.

## ROCm profile

When `rocminfo` succeeds:

- backend remains Ollama
- Flash Attention is enabled
- context defaults conservatively to 4096 unless reliable VRAM information is available
- vLLM is only considered when a suitable GPU memory budget is known

## Quantization

`ZEAZ_QUANTIZATION_PROFILE=Q4_K_M` is the default policy for local consumer hardware. It describes the preferred weight quantization class; the exact model artifact is still determined by the configured Ollama model tag.

To use another quantized artifact, override the model variables in the untracked `.env`, for example:

    ZEAZ_FAST_MODEL=<your-valid-ollama-model-tag>
    ZEAZ_CODER_MODEL=<your-valid-ollama-model-tag>

Do not invent model tags. Confirm that a tag exists in the model registry before changing it.

## GGUF local models

zwslcore can import GGUF-format model files directly into Ollama instead of pulling from the Ollama registry. GGUF models are useful when running quantized models that are not published as Ollama tags, or when models are transferred between air-gapped systems.

### Configuration

In `.env` (untracked):

    ZEAZ_GGUF_MODEL_DIR=/home/cvsz/zcoder/models
    ZEAZ_GGUF_FAST_MODEL=qwen-1.5b-q4km.gguf
    ZEAZ_GGUF_CODER_MODEL=qwen-7b-q4km.gguf

The installer imports each `.gguf` file as an Ollama model named `zwslcore-<filename-without-extension>` using a `Modelfile` from `models/`. The resulting Ollama aliases are referenced by:

    ZEAZ_FAST_MODEL=zwslcore-qwen-1.5b-q4km
    ZEAZ_CODER_MODEL=zwslcore-qwen-7b-q4km
    ZEAZ_REASONING_MODEL=zwslcore-qwen-7b-q4km
    ZEAZ_LOCAL_MODEL=zwslcore-qwen-7b-q4km

GGUF import happens in `scripts/install.sh` after Ollama pulls complete, and can also be triggered manually with `scripts/create-local-models.sh`.

### Obtaining GGUF models

Copy `.gguf` files from SERVER_CORE:

    ssh -p 2223 cvsz@192.168.1.85:/home/cvsz/zcoder/models/

### Runtime settings

The installer manages:

    ZEAZ_ACCELERATOR_MODE=auto
    ZEAZ_QUANTIZATION_PROFILE=Q4_K_M
    ZEAZ_OLLAMA_CONTEXT_LENGTH=4096
    ZEAZ_OLLAMA_FLASH_ATTENTION=false

Ollama receives the context, Flash Attention, and model keep-alive values through Compose. `ZEAZ_OLLAMA_KEEP_ALIVE` defaults to `30m` to reduce repeated cold loads; lower it in `.env` when memory is more constrained.

## vLLM

vLLM is intentionally not installed or started by default. It is best treated as an optional high-throughput backend for supported accelerators.

The hardware profile reports `vllm_candidate=true` only when the host has a sufficiently capable accelerator profile. This flag is advisory; it does not install packages, download models, or change the active backend.

## Operator verification

From Windows PowerShell:

    .\scripts\engineer-wsl.ps1 profile

Then confirm runtime health:

    .\scripts\doctor-wsl.ps1 -Smoke

The profile output includes:

- accelerator backend
- detected GPU and memory when available
- recommended quantization policy
- recommended context length
- Flash Attention recommendation
- whether vLLM is a candidate
