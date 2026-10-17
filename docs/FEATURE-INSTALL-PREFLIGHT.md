# Feature-Aware Installation and Preflight

Run the preflight **before** any installation. The script discovers the active profile and reports available optional services without changing the system. It never deletes Ollama models, resets volumes, restarts the existing Cloudflare tunnel, or exposes a public endpoint.

## Cloudflare SSH failure remediation

The installer now includes a token-safe Cloudflare SSH doctor. Run it on the origin Cloud Shell when a remote client reports `websocket: bad handshake` or the Access CLI callback returns HTTP 404:

```bash
ZCLOUD_HOSTNAME=ssh.example.org make cloudflare-doctor
ZWSL_CHECK_CLOUDFLARE=1 ZCLOUD_HOSTNAME=ssh.example.org make feature-preflight
```

It inspects active connector processes, validates the ingress target and SSH listener, and explicitly identifies that an existing connector might not have reloaded a changed config. It does **not** print Access JWTs/callback tokens, make an unauthenticated command-execution endpoint, or kill/restart an unknown supervisor.

A complete Access fix also requires a real Cloudflare Zero Trust Self-hosted Application and a verified identity-bound Allow/MFA policy, plus successful client-side CLI and SSH tests. The installer cannot safely manufacture a verified policy from a local YAML file, and does not impersonate the administrator. After verifying policy, restart **only** the existing connector through its original manager, then test externally. A 404 at the root of an SSH-only hostname is not itself proof of failed Access authorization.

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

## Cloud Shell session recovery

A new Cloud Shell VM may have SSH available but no cloudflared binary, native
Ollama process, or Compose containers. That is not an instruction to run the
WSL2/production installer or to manufacture a new Tunnel credential.

Use the following opt-in recovery path from this branch after reviewing the
repository checkout (do not reset or discard local changes):

```bash
cd ~/zwslcore
make cloudshell-recover-status  # Non-mutating capability inventory
make cloudshell-recover         # Explicit: install only missing tools; start Ollama on loopback
make models                     # Uses existing Docker container or native Ollama
```

`cloudshell-recover` installs missing cloudflared from Cloudflare's stable
signed APT repository and missing Ollama using its official Linux installer.
If the Google Cloud Shell image lacks `zstd`, recovery installs this archive
extraction dependency from the system APT repositories before invoking the
Ollama installer; if `zstd` exists it is reused. Recovery does not start
Docker or provision models.
It reuses installed tools and an already healthy Ollama instance. Ollama is
started locally at `127.0.0.1:11434` when needed, without pulling a model.
Installing Ollama may require sudo and uses disk/network resources. The
command does not create `.env.production`, install PostgreSQL, start Compose,
or publish Open WebUI/Provider/Ollama.

Starting the existing locally managed Tunnel is a **separate operation**.
Only after the prior Cloudflare Access policy, SSH authorized keys, source
Tunnel ID, and external client authentication have been verified, run:

```bash
ZCLOUD_HOSTNAME=ssh.example.com make cloudshell-tunnel-start
```

This validates the private existing `~/.cloudflared/config.yml` and matching
credential JSON, exact SSH hostname mapped to `ssh://127.0.0.1:22`, then
reuses the existing managed tunnel lifecycle. It does not regenerate a
credential, switch Tunnel IDs, modify DNS/Access, or forcibly restart an
unknown connector. A separate destination Tunnel on a different origin is
not interchangeable with the locally configured Tunnel.

**Failure interpretation:**
- `This version requires zstd for extraction` — older recovery script versions
  need `sudo apt-get update -qq && sudo apt-get install -y --no-install-recommends zstd`
  before retrying; current recovery installs missing `zstd` automatically.
- `MISSING: cloudflared` — restore CLI with `make cloudshell-recover`.
- Native Ollama missing or port 11434 not responding — recover runtime, then
  check `make models`. If no model is installed, provisioning is a separate
  deliberate operator action; never silently pull multi-gigabyte models.
- `make production-up` reports missing `.env.production` — expected release
  gate, not a Cloud Shell recovery issue.
- Absent `zwslcore-ollama` Docker container is normal for this native
  recovery path.
- Missing/private credential mismatch prevents starting a connector;
  restore the original file through an authorized secret-management channel.
- Cloud Shell VM and private IP are ephemeral; external WARP/SSH/Access and
  model inference remain unverified until independently tested.

Rollback: `bash scripts/zcloud-tunnel.sh stop` stops only its own managed
supervisor. Stop only the `ollama.pid` instance owned by this recovery
session after verifying process identity. Do not delete model files or tunnel
credentials to roll back a tool installation. Existing live services are not
restarted by routine status checks.
