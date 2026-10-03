# AI OSS stack sources

zwslcore integrates selected behavior from existing `cvsz/*` repositories instead of copying whole repositories.

| Source | Reused concept |
|---|---|
| `cvsz/zeaz-platform` | local Ollama + LiteLLM + Open WebUI bootstrap and health-check flow |
| `cvsz/qwen-gen` | RAM-aware local model selection and zero-price provider catalog filtering |
| `cvsz/z-prov` | stable provider aliases, local-first routing, provider isolation, loopback-only exposure |
| `cvsz/zai-coder` | small Qwen coder models for CPU-friendly local coding |
| `cvsz/zaiman` | provider registry/free-tier metadata patterns |

## Refactoring decisions

- Do not vendor entire upstream repositories.
- Keep zwslcore as the orchestration and host-integration layer.
- Keep all public service bindings on loopback by default.
- Open WebUI talks to one LiteLLM endpoint.
- Ollama remains local and is never intended for direct Internet exposure.
- Cloud free tiers are opt-in because model availability, quotas, terms, and zero-price status can change.
- Secrets live only in `.env`, which is ignored by Git.
- Model pulling is based on available memory, not only installed memory.

## Runtime aliases

- `zeaz-fast` -> `qwen2.5-coder:3b`
- `zeaz-coder` -> `qwen2.5-coder:7b`
- `zeaz-reasoning` -> `qwen3:8b`
- `zeaz-free` -> OpenRouter free router when explicitly configured

The aliases are intentionally stable so clients do not need to change when backend models are replaced.
