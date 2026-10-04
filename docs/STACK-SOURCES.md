# Integrated components

zwslcore is self-contained. The code and configuration required for runtime are stored in this repository and no external ZEAZ repository is cloned, imported, mounted, or required by the installer.

## In-repository components

| Component | Location | Responsibility |
|---|---|---|
| Provider gateway | `services/provider/` | OpenAI/Anthropic-compatible API, model aliases, fallback routing, auth, limits and metrics |
| Model catalog | `services/model_catalog/` | zero-price/chat-capable model filtering and route generation |
| Ollama model pack | `scripts/create-local-models.sh` | local coder aliases and Modelfiles |
| LiteLLM routing | `config/litellm.yaml` | local and optional provider routing |
| Open WebUI orchestration | `compose.yaml` | browser UI wired through the in-repo provider gateway |
| Installer/doctor | `scripts/install.sh`, `scripts/doctor.sh` | bootstrap, secret generation and health validation |

## Refactoring provenance

The implementation was consolidated from patterns and code previously maintained across ZEAZ projects including provider gateway, model discovery, Ollama tuning, and Open WebUI/LiteLLM bootstrap work. Those repositories are historical provenance only; they are not runtime dependencies.

The consolidated implementation is intentionally owned by zwslcore now:

- configuration paths are zwslcore-local;
- provider package and Docker build context live under `services/provider/`;
- model catalog logic lives under `services/model_catalog/`;
- stable public aliases are controlled here;
- health checks, credentials and lifecycle commands are controlled here.

## Runtime flow

```text
Open WebUI
    |
    v
zwslcore Provider Gateway
    |------------------|
    v                  v
 Ollama             LiteLLM
 local models       optional routes
    |
    +--> optional cloud fallback only when explicitly enabled
```

All host-published ports remain loopback-only by default.
