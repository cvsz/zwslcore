# zwslcore

WSL2-first local AI orchestration stack for Ubuntu 26.04. It integrates selected, reusable behavior from the existing ZEAZ AI repositories without vendoring whole projects.

## Runtime

```text
Windows 11
└── WSL2 Ubuntu 26.04
    └── zwslcore
        ├── Ollama
        │   ├── qwen2.5-coder:3b
        │   ├── qwen2.5-coder:7b
        │   └── qwen3:8b
        ├── LiteLLM
        │   ├── zeaz-fast
        │   ├── zeaz-coder
        │   ├── zeaz-reasoning
        │   └── zeaz-free (optional cloud route)
        └── Open WebUI
```

All published ports bind to `127.0.0.1` by default.

## Install

Prerequisites:

- WSL2 Ubuntu 26.04 or compatible Linux
- Docker Engine
- Docker Compose plugin
- Python 3
- curl

From the repository:

```bash
cd ~/zwslcore
git pull
make install
```

The installer:

1. creates a private `.env` when missing;
2. generates Open WebUI and LiteLLM secrets locally;
3. validates Compose;
4. starts Ollama;
5. detects currently available memory;
6. pulls CPU-friendly models appropriate to available RAM;
7. starts LiteLLM and Open WebUI;
8. runs runtime diagnostics.

Open:

```text
Open WebUI  http://localhost:3000
LiteLLM     http://localhost:4000
Ollama      http://localhost:11434
```

## Operations

```bash
make doctor
make models
make logs
make restart
make down
make up
```

Validate configuration and repository checks:

```bash
make config
make ci
```

## Free model discovery

Local Ollama models are the default and require no provider API key.

To inspect currently declared zero-price OpenRouter text models:

```bash
python3 scripts/sync-free-models.py
```

Optionally export `OPENROUTER_API_KEY` before discovery or configure it only in the untracked `.env`. External free tiers and quotas can change and are not treated as permanently free.

## Security defaults

- Open WebUI, LiteLLM, and Ollama publish only to loopback.
- Open WebUI sign-up is disabled by default.
- Provider credentials are not committed.
- `.env` remains ignored.
- Cloud provider fallback is opt-in.
- Ollama is not intended to be exposed directly through Cloudflare or the public Internet.
- Existing repository governance, CodeQL, dependency review, and branch-protection tooling remain in place.

## Integrated source inventory

See [AI OSS stack sources](docs/STACK-SOURCES.md).

The current integration reuses design/behavior from:

- `cvsz/zeaz-platform` — Ollama/LiteLLM/Open WebUI bootstrap
- `cvsz/qwen-gen` — RAM-aware model selection and free-model filtering
- `cvsz/z-prov` — local-first provider gateway patterns and stable aliases
- `cvsz/zai-coder` — CPU-friendly Qwen coding models
- `cvsz/zaiman` — provider/free-tier registry patterns

zwslcore is the orchestration layer; it does not duplicate the complete source trees of those projects.

## Repository engineering controls

The repository retains its ZEAZ engineering baseline including:

- CI repository validation
- CodeQL
- Dependency Review
- Dependabot
- CODEOWNERS and PR governance
- secret-file checks
- repository administration verification tooling

A green repository CI run validates only the checks that ran. Production readiness still requires runtime, recovery, security, observability, and deployment evidence for the target environment.

## License

MIT. See `LICENSE`.
