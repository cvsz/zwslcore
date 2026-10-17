# Google Cloud Shell: Cloudflare Tunnel and SSH access (opt-in)

This runbook covers an existing **locally managed** Cloudflare Named Tunnel. It does not create a Cloudflare account, set DNS, create an Access application, provision SSH keys, or give ChatGPT access to terminal commands. Cloud Shell is ephemeral and **not** 24/7 hosting. Use a persistent VM for continuous connectors.

## Observed during the 2026-10-17 Cloud Shell session

Operator-reported evidence (not independently executed by repository CI): cloudflared 2026.10.1 installed; systemd reported `offline`; an SSH daemon listened on TCP 22; a new named tunnel registered four QUIC edge connections; DNS HTTPS returned intentional `404` for `http_status:404`. A later managed connector also registered four edge connections. This does **not** prove Cloudflare Access was configured, SSH login succeeded, boot-time auto-start worked, or remote command execution is possible from this chat.

## Prerequisites and safe preparation

Create the Named Tunnel using `cloudflared tunnel login` and `cloudflared tunnel create YOUR_TUNNEL` **only if a suitable tunnel does not already exist**. Never commit `~/.cloudflared/cert.pem`, `*.json` credentials, tokens, `.env`, SSH private keys, session cookies or logs. The host and tunnel UUID are runtime configuration, not repository constants.

A safe ingress for initial connectivity testing is:

```yaml
tunnel: YOUR_TUNNEL_UUID
credentials-file: /home/YOUR_USER/.cloudflared/YOUR_TUNNEL_UUID.json
ingress:
  - hostname: tunnel.example.com
    service: http_status:404
  - service: http_status:404
```

Store the file at `~/.cloudflared/config.yml` with mode 0600, credentials mode 0600 and its directory mode 0700. Check with:

```bash
cloudflared tunnel --config "$HOME/.cloudflared/config.yml" ingress validate
cloudflared tunnel ingress rule https://tunnel.example.com
cloudflared tunnel info YOUR_TUNNEL_UUID
curl -I https://tunnel.example.com
```

The expected `404` verifies the safe HTTP ingress, **not** an SSH endpoint or application health.

## Connector lifecycle without systemd

From the repository root:

```bash
bash scripts/zcloud-tunnel.sh preflight
bash scripts/zcloud-tunnel.sh start
bash scripts/zcloud-tunnel.sh status
bash scripts/zcloud-tunnel.sh logs
bash scripts/zcloud-tunnel.sh stop
```

If another cloudflared process is already present, `start` refuses to compete: first inspect and stop only the connector you own. The manager uses flock to prevent concurrent supervisors; `stop` signals only its supervised process. Logs stay under `~/.local/state/zwslcore-cloudflared` (do not share raw logs without review). To opt in to interactive Bash startup:

```bash
bash scripts/zcloud-tunnel.sh install-autostart
```

The hook assumes the repository is at `~/zwslcore`; changing the checkout location requires adjusting the hook. Bash startup is not Google Cloud Shell VM boot startup, and a crash of the VM cannot be recovered by this script.

## SSH security gates

1. Create a Cloudflare Access self-hosted application for the exact hostname, with an explicit identity allowlist and no `Everyone` bypass. Verify unauthorized access is denied. A tunnel being online does not prove an Access policy exists.
2. Confirm host-side SSH key authorization and verify the SSH host-key fingerprint out of band. Do not modify Cloud Shell's existing `sshd` configurations blindly.
3. **Only after Access has been independently tested**, back up `config.yml`, change the hostname rule to `service: ssh://127.0.0.1:22`, validate ingress, restart the connector, and test through a Cloudflare-aware SSH client. Keep catch-all `http_status:404`.
4. Client example, with properly provisioned authorized keys:

```sshconfig
Host example-cloud-shell
  HostName tunnel.example.com
  User YOUR_USER
  ProxyCommand cloudflared access ssh --hostname %h
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking yes
```

Rollback: restore the backed-up safe configuration, validate and restart; do not delete the tunnel, DNS, credentials, or SSH keys as a shortcut.

## Git and AI CLI follow-up

Use `git status --short`, `git fetch origin --prune`, then `git pull --ff-only` only if the checkout can safely fast-forward. No force reset. Check `bash scripts/ai.sh doctor`, `bash scripts/ai.sh selftest`, and the tests relevant to provider routing. On `main`, `ai.sh` defaults to a loopback provider and does not load a repository `.env` automatically; coordinate with the existing `.env` and Cloud Shell/Ollama PRs before changing that behavior. Never `source` an untrusted `.env`.

Cloudflare Access and SSH access alone do not grant ChatGPT-in-Chat an SSH execution tool. An explicitly authorized execution connector is still required.

## Verification matrix

- `bash -n scripts/zcloud-tunnel.sh`: script syntax
- `bash scripts/zcloud-tunnel.sh status`: supervisor status only
- `cloudflared tunnel info`: active connector confirmation
- `curl -I`: expected safe ingress HTTP status
- Access denied for unauthorized identity; authorized Cloudflare login works
- SSH host-key and public-key authentication succeed from a trusted client
- Stop/restart/rollback tested on the target; no production claim without these results
