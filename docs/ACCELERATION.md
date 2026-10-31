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

## Runtime settings

The installer manages:

    ZEAZ_ACCELERATOR_MODE=auto
    ZEAZ_QUANTIZATION_PROFILE=Q4_K_M
    ZEAZ_OLLAMA_CONTEXT_LENGTH=4096
    ZEAZ_OLLAMA_FLASH_ATTENTION=false

Ollama receives the context, Flash Attention, and model keep-alive values through Compose. `ZEAZ_OLLAMA_KEEP_ALIVE` defaults to `30m` to reduce repeated cold loads; lower it in `.env` when memory is more constrained.

## vLLM

vLLM is intentionally not installed or started by default. It is best treated as an optional high-throughput backend for supported accelerators.

The hardware profile reports `vllm_candidate=true` only when the host has a sufficiently capable accelerator profile. This flag is advisory; it does not install packages, download models, or change the active backend.

## MiniMax-H3 video generation (GGUF)

MiniMax-H3 is an omni-modal Image-Text-to-Video model (20B parameters) from
Unsloth/MiniMax-H3-GGUF. It generates video (up to 15 seconds at 24 FPS with
32 kHz stereo audio) and is used with stable-diffusion.cpp, **not** with the
zwslcore Provider chat API.

### Components

MiniMax-H3 ships as separate checkpoints. All must be present for generation:

| Component | File | Size | Required |
|-----------|------|------|----------|
| Denoiser (fl2va_pruned) | `minimax_h3_fl2va_pruned-Q4_K.gguf` | ~10.64 GiB | Yes |
| Text encoder | `qwen3vl_32b_minimax_h3-Q4_K_M.gguf` | ~16.97 GiB | Yes |
| Video VAE | `minimax_h3_video_vae_fp16.safetensors` | — | Yes |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | Yes |

VAEs come from Comfy-Org/MiniMax-H3, not from unsloth/MiniMax-H3-GGUF.

### Configuration

In `.env` (untracked):

    ZEAZ_MINIMAX_H3_MODEL_DIR=/home/cvsz/zcoder/models/minimax-h3
    ZEAZ_MINIMAX_H3_DENOISER=minimax_h3_fl2va_pruned-Q4_K.gguf
    ZEAZ_MINIMAX_H3_TEXT_ENCODER=qwen3vl_32b_minimax_h3-Q4_K_M.gguf
    ZEAZ_MINIMAX_H3_VIDEO_VAE=minimax_h3_video_vae_fp16.safetensors
    ZEAZ_MINIMAX_H3_AUDIO_VAE=minimax_h3_audio_vae_fp32.safetensors

The installer downloads these from Hugging Face into `ZEAZ_MINIMAX_H3_MODEL_DIR`.
Modelfile templates live under `models/minimax-h3/`.

### Usage (stable-diffusion.cpp)

```bash
sd-cli --mode vid_gen \
  --diffusion-model minimax_h3_fl2va_pruned-Q4_K.gguf \
  --llm qwen3vl_32b_minimax_h3-Q4_K_M.gguf \
  --vae minimax_h3_video_vae_fp16.safetensors \
  --audio-vae minimax_h3_audio_vae_fp32.safetensors \
  --prompt "<your prompt>" \
  --width 960 --height 544 --video-frames 124 --steps 8 --cfg-scale 1.0 \
  --backend te=cpu --diffusion-fa \
  --output out.webm
```

Three flags are not optional:
1. `--mode vid_gen` — H3 aborts without it
2. `--cfg-scale 1.0` — H3 is cfg-free (default 7.0 aborts above 1.0)
3. `--backend te=cpu` — keeps the 12+ GB text encoder off the GPU

### License

MiniMax H3 Community License Agreement. Defines an Applicable Territory and
excludes some jurisdictions. Read `LICENSE` before use. Not an official
MiniMax product, not endorsed by MiniMax.

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
