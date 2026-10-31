# Cloud Shell SSH Access and Read-only MCP Diagnostics

These optional scripts complement the existing `scripts/zcloud-tunnel.sh` lifecycle manager. They do not install or run a second tunnel supervisor and do not replace Cloudflare Access. The Cloud Shell environment is ephemeral and is **not** a production uptime guarantee.

## Preconditions

Use a hostname you own and a named Cloudflare Tunnel already configured on the local machine. In Cloudflare Zero Trust, create a Self-hosted Access Application for the exact SSH hostname and a restrictive Allow policy backed by a trusted identity provider and MFA. Confirm an unauthenticated external request cannot reach SSH. Verify SSH public-key authorization and the origin host key with a trusted fingerprint; never disable host key checking.

## Ingress

```bash
export ZCLOUD_HOSTNAME=ssh.example.org
bash scripts/zwsl-cloudflare.sh preflight
bash scripts/zwsl-cloudflare.sh verify

# ONLY after separately verifying Access policy and authorized keys:
ZCLOUD_ACCESS_POLICY_VERIFIED=YES ZCLOUD_AUTHORIZED_KEYS_VERIFIED=YES \
  bash scripts/zwsl-cloudflare.sh configure

# Restart the existing connector by its established owner/manager.
bash scripts/zwsl-cloudflare.sh verify
```

The opt-in configure operation only updates a very narrow YAML layout: the service line immediately following the exact hostname, initially `http_status:404`. Other layouts fail closed and require manual review. It writes a restricted backup and provides `rollback`. An HTTP 404 is not proof that Access is protecting the endpoint. A modified local config is not proof the live connector loaded it.

## SSH Client

```bash
export ZCLOUD_HOSTNAME=ssh.example.org
export ZCLOUD_IDENTITY_FILE="$HOME/.ssh/id_ed25519"
bash scripts/zwsl-ssh-repair.sh diagnose
bash scripts/zwsl-ssh-repair.sh configure
bash scripts/zwsl-ssh-repair.sh test
```

The client installer preserves other SSH host blocks, backs up the config, rejects ambiguous aliases, requires an existing key with mode 0600, and enables strict host-key checking. `ssh.example.org` is a placeholder. Before running the external test, verify the server fingerprint and authorized public key. Check Cloudflare Access authentication and WebSocket upgrades if the client reports `websocket: bad handshake`.

## Local MCP Diagnostics

```bash
bash scripts/install-zwsl-remote-exec.sh install
bash scripts/install-zwsl-remote-exec.sh check
```

This installs a **stdio-only, read-only** MCP server into the user home directory, not into the repository.
Set `ZWSL_MCP_HOME` to use a different private installation directory.
At installation the generated server records only the current checkout path,
the `ZCLOUD_CONFIG` path, and the discovered `cloudflared` executable in
owner-only `paths.json` (no secrets or `.env` content).
The feature-aware installer detects an existing installation at that same path.
Diagnostics set `GIT_OPTIONAL_LOCKS=0`, cap captured output at 8,000 bytes
while streaming, and enforce a 10-second subprocess deadline. Its tools inspect user/kernel information, repository Git status, listening sockets, and Cloudflare ingress validation. They do not accept arbitrary commands or mutate files. Dependencies require a network connection and the MCP SDK version range stated in the installer. Production installations should pin and audit a concrete tested version.

ChatGPT does not gain remote-shell execution merely by installing a server on Cloud Shell. An authenticated and supported MCP transport plus workspace permissions must be configured separately; do not publish an unauthenticated MCP endpoint or tunnel credentials. A working external SSH test is independent from ChatGPT tool availability.

## Rollback and validation

```bash
bash scripts/zwsl-cloudflare.sh rollback
python3 -m unittest tests.test_cloudshell_access_mcp -v
```

Rollback restores the previous local config. Restarting the already-owned connector remains an explicit operator action. Keep a documented escape path in Cloud Shell before making routing changes.
