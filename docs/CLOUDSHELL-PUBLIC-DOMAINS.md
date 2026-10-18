# Cloud Shell public SSH and authenticated API hostnames

This runbook publishes two **separate** hostnames through an already-owned
Cloudflare Tunnel, without duplicating the existing model router or exposing
unauthenticated Ollama. It does **not** claim that Cloud Shell is a permanent
24/7 production host. Cloud Shell instances, internal IPs, and running
processes may be recycled. Persistent deployment requires an operator-owned
VM or equivalent always-on host.

The existing SSH hostname MUST continue routing to `ssh://127.0.0.1:22`.
The API hostname MUST route to the already-implemented, authenticated
zwslcore Provider at `http://127.0.0.1:8080`. Do **not** point the public
API at `http://127.0.0.1:11434`, which is an unauthenticated Ollama origin.

## Operator preparation

Use a reviewed commit in your checked-out repository on the actual
Cloud Shell origin, not from a different WSL host. Do not read or copy
`.env` or private Cloudflare credentials into logs, tickets or Git.

```bash
cd ~/zwslcore
python3 scripts/cloudshell-provider-runtime.py inspect
python3 scripts/cloudshell-provider-runtime.py start
python3 scripts/cloudshell-provider-runtime.py verify --infer
```

This runtime wrapper:
- Reuses an existing local Ollama model and the existing zwslcore FastAPI
  Provider code (no new Model Router, no Docker model download).
- Generates a random API token at
  `~/.local/state/zwslcore-public-provider/provider.key` with mode 0600,
  stores a local-only YAML profile in the same private state directory,
  and configures the existing Provider's SHA-256 API key digests.
- Disables unauthenticated Provider requests; binds Provider to loopback
  port 8080. It never publishes port 11434.
- Starts only when no unknown process owns port 8080. A healthy existing
  Provider is preserved; an incompatible one is not overwritten.
- Requires existing Python Provider dependencies; it does not silently
  install packages over the user's Python environment.

For client applications, obtain the API token by approved, secret-safe
operator distribution, not by copying it into source or environment logs.
The token is not printed by the installer.

## Prepare the ingress without changing the SSH route

Replace the examples below with your two actual authorized hostnames and
your actual Cloudflare zone. Set them through process environment or
command arguments; do not commit real domain ownership into the template.

```bash
export ZCLOUD_HOSTNAME=ssh.example.com
export ZWSL_API_HOSTNAME=api.example.com
export ZWSL_DNS_ZONE=example.com

python3 scripts/cloudshell-public-ingress.py inspect \
  --ssh-host "$ZCLOUD_HOSTNAME" --api-host "$ZWSL_API_HOSTNAME" \
  --zone "$ZWSL_DNS_ZONE"

python3 scripts/cloudshell-public-ingress.py stage \
  --ssh-host "$ZCLOUD_HOSTNAME" --api-host "$ZWSL_API_HOSTNAME" \
  --zone "$ZWSL_DNS_ZONE"
```

`stage` validates a private alternative ingress file and checks local SSH
and authenticated Provider. It does not alter the active connector, DNS or
Cloudflare Access. The API ingress is inserted before the existing catch-all
404 rule and never replaces the SSH hostname entry. A conflicting API
hostname origin causes a fail-closed refusal.

Do not migrate the SSH hostname to another tunnel just because that
tunnel has an active connector. Its connector could be at a different
origin; verify its location, Access policy and authorized SSH login first.

## Access, ingress apply and DNS compare-and-swap

Before public cutover, independently verify restrictive Cloudflare Access
policies for both hosts, authorized SSH login, Provider bearer rejection and
TLS. Never add Bypass. The `ZWSL_API_ACCESS_VERIFIED=YES` setting is an
**operator attestation**, not an automatic policy verification.

```bash
export ZWSL_API_ACCESS_VERIFIED=YES

python3 scripts/cloudshell-public-ingress.py apply-ingress \
  --ssh-host "$ZCLOUD_HOSTNAME" --api-host "$ZWSL_API_HOSTNAME" \
  --zone "$ZWSL_DNS_ZONE"
```

This keeps a private backup and checks that an existing SSH route is
unchanged. The active connector must be **reloaded by its existing
process supervisor** afterward. Do not kill the source tunnel blindly or
start a duplicate connector without verifying ownership and origin
placement. Recheck local SSH and Provider readiness after reload.

For DNS, use a Cloudflare API token and Zone ID with only the required
permissions. The commands below do **not** require copying secrets to
GitHub or reading `.env`.

```bash
python3 scripts/cloudshell-public-ingress.py dns-plan \
  --ssh-host "$ZCLOUD_HOSTNAME" --api-host "$ZWSL_API_HOSTNAME" \
  --zone "$ZWSL_DNS_ZONE"
```

`dns-plan` reads the authoritative Cloudflare record. It requires
`CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN` in the command
environment and checks that the Zone ID corresponds to the expected
zone name. If the record is missing, `dns-apply` can create the CNAME.
If the record already has another target, `dns-apply` requires its
**exact current target** through `--expect-cname` and refuses an A,
AAAA or ambiguous result. It backs up the prior record before changing
it and reads the record back after writing.

```bash
python3 scripts/cloudshell-public-ingress.py dns-apply \
  --ssh-host "$ZCLOUD_HOSTNAME" --api-host "$ZWSL_API_HOSTNAME" \
  --zone "$ZWSL_DNS_ZONE" --expect-cname CURRENT_VERIFIED_CNAME
```

The desired DNS CNAME target is based on the locally managed tunnel
UUID from the active Cloud Shell config, not on a guessed external tunnel
connector. The existing SSH hostname DNS remains untouched. Cloudflare
public DNS often resolves to Cloudflare edge IPs and cannot by itself
prove which tunnel is serving the hostname.

## External authenticated acceptance

From an **independent, authorized** external client, verify HTTPS/TLS,
invalid-bearer rejection, a valid bearer `/v1/models` response, and
a real `POST /v1/chat/completions`. A Cloudflare Access-protected API
may require the additional `CF-Access-Client-Id` and
`CF-Access-Client-Secret` headers or an interactive Access session.

The following demonstrates API authentication (substitute secure runtime
token provisioning rather than hardcoding an actual secret):

```bash
curl --fail-with-body https://api.example.com/v1/models \
  -H "Authorization: Bearer $ZWSLCORE_PROVIDER_TOKEN"
```

For SSH, configure the authorized client's Cloudflare SSH ProxyCommand
and verify the actual server host-key fingerprint and logged-in identity.
A `404` or `302` from the SSH hostname using ordinary HTTPS is **not**
proof that SSH login works. Preserve `StrictHostKeyChecking=yes`.

## Rollback / incident constraints

```bash
python3 scripts/cloudshell-public-ingress.py rollback \
  --ssh-host "$ZCLOUD_HOSTNAME" --api-host "$ZWSL_API_HOSTNAME" \
  --zone "$ZWSL_DNS_ZONE"
```

Rollback restores the previous locally managed ingress only when the
current config hash matches the last applied snapshot; it refuses to
overwrite concurrent operator changes. It does not touch DNS or running
connectors. Restore DNS separately using the private DNS backup and
the approved Cloudflare change process, and reload the known connector
through its supervisor before concluding recovery.

## Verification boundaries

Passing repository tests does not prove that either hostname is live.
To claim public readiness, attach operator evidence of:
- Current Cloudflare DNS CNAME target and zone ownership for both hosts.
- Actual cloudflared connector located at the intended origin.
- Effective Access policy for each host, with no unsafe Bypass.
- Authenticated SSH login and stable host-key validation from an external client.
- Provider on loopback port 8080, unauthorized 401/403, authorized models
  and model inference from an external HTTPS client.
- Restart/rollback evidence and non-ephemeral hosting plan.
