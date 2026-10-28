# MiniMax-H3 GGUF Models

MiniMax-H3 is an omni-modal generative system for **video generation** (up to
15 seconds at 24 FPS with 32 kHz stereo audio). It is an Image-Text-to-Video
model with 20B parameters, quantized to GGUF format by Unsloth.

## Source

- Hugging Face: https://huggingface.co/unsloth/MiniMax-H3-GGUF
- Base model: https://huggingface.co/MiniMaxAI/MiniMax-H3
- Usage reference (stable-diffusion.cpp):
  https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/minimax_h3.md
  https://github.com/Comfy-Org/docs/blob/main/tutorials/video/minimax/minimax-h3.mdx

## Components

MiniMax-H3 ships as separate checkpoints. You must download the denoiser,
the text encoder, and the VAEs:

### Denoisers (pick one)

| File | Size | Description |
|------|------|-------------|
| `minimax_h3_fl2va_pruned-Q4_K.gguf` | ~10.64 GiB | First-and-last-frame denoiser (text + 0-2 frames) |
| `minimax_h3_ref2va_pruned-Q4_K.gguf` | ~10.60 GiB | Reference denoiser (text + reference media) |

### Text encoder (shared, required)

| File | Size |
|------|------|
| `qwen3vl_32b_minimax_h3-Q4_K_M.gguf` | ~16.97 GiB |

### VAEs (from Comfy-Org/MiniMax-H3)

| File | Description |
|------|-------------|
| `minimax_h3_video_vae_fp16.safetensors` | Video VAE |
| `minimax_h3_audio_vae_fp32.safetensors` | Audio VAE |

## Usage with stable-diffusion.cpp

```bash
sd-cli --mode vid_gen \
  --diffusion-model minimax_h3_fl2va_pruned-Q4_K.gguf \
  --llm qwen3vl_32b_minimax_h3-Q4_K_M.gguf \
  --vae minimax_h3_video_vae_fp16.safetensors \
  --audio-vae minimax_h3_audio_vae_fp32.safetensors \
  --prompt "a red panda stepping along a mossy log in a misty forest, cinematic" \
  --width 960 --height 544 --video-frames 124 --steps 8 --cfg-scale 1.0 \
  --backend te=cpu --diffusion-fa \
  --output out.webm
```

Three flags are not optional:
1. `--mode vid_gen` — H3 aborts without it
2. `--cfg-scale 1.0` — H3 is cfg-free (default 7.0 aborts above 1.0)
3. `--backend te=cpu` — keeps the 12+ GB text encoder off the GPU

## License

**MiniMax H3 Community License Agreement.** Read `LICENSE` before use. It
defines an Applicable Territory and excludes some jurisdictions. These files
are Model Derivatives (quantized), not a plain copy — see `NOTICE` for
attribution. Not an official MiniMax product, not endorsed by MiniMax.

## Integration with zwslcore

GGUF files are downloaded into `ZEAZ_MINIMAX_H3_MODEL_DIR` and registered
with Ollama aliases via `scripts/install.sh` and
`scripts/create-local-models.sh`. Note that MiniMax-H3 is a video generation
model; it is used with stable-diffusion.cpp, not with the zwslcore Provider
chat API.
