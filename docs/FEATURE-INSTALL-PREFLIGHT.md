# Feature-Aware Installation and Preflight

Run the preflight **before** any installation. The script discovers the active profile and reports available optional services without changing the system. It never deletes Ollama models, resets volumes, restarts the existing Cloudflare tunnel, or exposes a public endpoint.

## Selective install and Cloudflare configuration validation

Run the following checks before installing or changing services:

```bash
ZWSL_PROFILE=cloudshell ZWSL_CHECK_CLOUDFLARE=1 \
  ZCLOUD_HOSTNAME=ssh.example.org bash scripts/feature-install.sh preflight

# Install the missing optional components only, without starting them:
ZWSL_PROFILE=cloudshell ZWSL_INSTALL_MCP=1 ZWSL_INSTALL_WEBUI=1 \
  bash scripts/feature-install.sh install
```

The Cloudflare check validates the existing YAML and local SSH listener without updating DNS, creating or modifying Access policies, restarting the existing connector, or changing ingress routes. The real hostname is supplied at runtime, never committed. A successful local preflight is not evidence of Cloudflare Access enforcement or authenticated SSH end-to-end. Existing native Open WebUI and MCP installs are skipped (MCP syntax is rechecked). For Open WebUI install, prepare a writable data/storage directory and meet the Python version requirement.

## Google Cloud Shell (reuse installed models)

```bash
cd ~/zwslcore
bash scripts/feature-install.sh preflight
bash scripts/feature-install.sh install
bash scripts/feature-install.sh verify
```

The default Cloud Shell installation runs the supported CLI-only bootstrap and `ai-test`. It does not install Docker, host PostgreSQL, LiteLLM, Provider Gateway, or a new Ollama instance. `ollama list` identifies existing models without downloading them. API credentials and upstream model endpoints remain user-managed.

The following optional features require separate prerequisites:

```bash
# Native Open WebUI: writable storage and Python 3.11/3.12 are required.
ZWSL_INSTALL_WEBUI=1 bash scripts/feature-install.sh preflight
ZWSL_INSTALL_WEBUI=1 bash scripts/feature-install.sh install

# Read-only local stdio MCP diagnostics:
ZWSL_INSTALL_MCP=1 bash scripts/feature-install.sh install
ZWSL_INSTALL_MCP=1 bash scripts/feature-install.sh verify
```

Open WebUI installation does **not** start the service or expose the port. The first administrator must be registered via a trusted local access path, with `WEBUI_AUTH=true`. Cloudflare Access SSH and ChatGPT MCP remote connectivity are **separate** and are not automatically configured or validated by this installer.

## Full Linux / WSL2

```bash
ZWSL_PROFILE=wsl2 bash scripts/feature-install.sh preflight
```

For the full Compose stack, read the PostgreSQL prerequisites and model installation behavior in the README. Unlike the Cloud Shell mode, `scripts/install.sh` currently pulls pinned images and may download Ollama models. To prevent accidental model downloads, the feature-aware installer refuses that path by default. Only opt in after reviewing storage, database and model retention:

```bash
ZWSL_PROFILE=wsl2 ZWSL_MODEL_POLICY=provision \
  bash scripts/feature-install.sh install
ZWSL_PROFILE=wsl2 bash scripts/feature-install.sh verify
```

This command is not equivalent to proof of production readiness. Review `make doctor`, `make smoke`, backups, host PostgreSQL, port ownership, authentication, runtime health, and Cloudflare Access independently.

## CI / validation

```bash
bash -n scripts/feature-install.sh
python3 -m unittest tests.test_feature_install tests.test_cloudshell_access_mcp -v
make ai-test
```

Protect any API credentials, never commit `.env`, and never disable SSH host key validation. Cloud Shell sessions and /opt storage are ephemeral.
