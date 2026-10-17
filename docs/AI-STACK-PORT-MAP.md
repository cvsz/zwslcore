# AI Stack Port Map and Cloudflare Hostname Routing

## Source of truth

The declarative inventory is `config/ai-stack-port-map.json`. The
read-only inspector is `scripts/ai-stack-port-map.py`. These describe the
existing `compose.yaml` and native Cloud Shell bootstrap; they are not
a deployment manifest and they never modify DNS, Access or local tunnel
configuration. Host ports can be overridden by an operator at runtime;
inspect the actual listening sockets before cutover.

| Service | Cloud Shell host | Compose host → container | Exposure |
| --- | ---: | ---: | --- |
| SSH | TCP 22 | Separate host SSH :22 | Cloudflare Access SSH hostname |
| zwslcore Provider | TCP 8080 | 8080 → 8080 | Authenticated HTTPS API hostname |
| Open WebUI | TCP 3000 | 3000 → 8080 | Optional distinct Access-protected hostname |
| Ollama | TCP 11434 | 11434 → 11434 | Private, never publish directly |
| LiteLLM | Not installed by native profile | 4000 → 4000 | Private, never publish directly |
| Signed Webhook | TCP 8765 (optional) | Not in Compose | Private by default; path-scoped only with provider authentication |

The zWorkforce control-plane/MCP listener (default port 9569) is on the
**zWorkforce host**, not necessarily the same origin as zwslcore.
Keep the existing authorized MCP endpoint and provider pool unchanged.

Cloudflare's public entrypoint uses HTTPS port 443 and a hostname mapped
to a tunnel. It forwards to the configured **origin host port**. It does
not expose 8080, 3000 or 11434 on the public DNS address by default.

## Non-mutating inspection

```bash
python3 scripts/ai-stack-port-map.py map --profile cloudshell \
  --ssh-host ssh.example.net --api-host api.example.net

python3 scripts/ai-stack-port-map.py verify-local --profile cloudshell

python3 scripts/ai-stack-port-map.py ingress-preview --profile cloudshell \
  --ssh-host ssh.example.net --api-host api.example.net
```

For the WSL2/Compose profile, use `--profile compose`. Add
`--webui-host ui.example.net` only after confirming that hostname's
Access policy and the WebUI's session/authentication configuration. WebUI
must not reuse the SSH hostname.

The local verifier tests TCP 22, Ollama `/api/version`, Provider
`/health/live`, and Provider's **401/403 on unauthenticated
`/v1/models`**. It checks optional WebUI/Webhook only if running and
reports required port failures. Results are host-local observations;
a PASS does not verify public DNS or Cloudflare Access policies.

## Safe ingress target

The minimal intended Cloudflare hostname map is:

```yaml
ingress:
  - hostname: ssh.example.net
    service: ssh://127.0.0.1:22
  - hostname: api.example.net
    service: http://127.0.0.1:8080
  - service: http_status:404
```

This is an **illustration, not a replacement config**. It omits the
tunnel UUID, credentials, existing webhook rules, WARP routes, and
unrelated hostnames. Keep all existing entries. If the SSH hostname
already has a path-scoped `/webhook` route, keep it **before** the
unscoped SSH rule. The existing
`scripts/cloudshell-public-ingress.py stage` and
`apply-ingress` preserve that SSH mapping and check the authenticated
Provider on port 8080. Use `cloudflared tunnel ingress validate` and
`cloudflared tunnel ingress rule` before reloading the known connector.

For an optional WebUI hostname, add a separate rule that points to
`http://127.0.0.1:3000` only after enabling Cloudflare Access.
Use the existing `scripts/cloudflare-stack.sh` preparation and rollback
flow. Do not publish Ollama, LiteLLM, Redis, databases or metrics directly.

## Public readiness and DNS

1. Verify that the SSH hostname's existing Cloudflare CNAME still targets
   the **Cloud Shell connector owner**; do not migrate it to an unrelated
   WSL2 tunnel simply because the new tunnel has live connections.
2. Verify that API DNS is a proxied CNAME to the tunnel running on the
   **machine that actually listens on port 8080**. Stage the correct
   ingress first; the DNS change must be independently authorized.
3. Verify Cloudflare Access policy and MFA for SSH, and Service Auth
   policy for the API. The Provider's bearer authentication is a
   separate mandatory layer. Do not use Access Bypass.
4. Test external SSH login with host-key checking and external API
   `/v1/models` and `/v1/chat/completions` with both Access and
   Provider credentials. A DNS resolution or HTTPS 404 alone is not proof.
5. Keep the pre-cutover DNS and ingress backups, validate rollback and
   re-check SSH after every connector reload.

If the Cloud Shell is recycled, tunnel connectors and listeners may
stop. A 24/7 public service requires a persistent host and supervised
service lifecycle. No GitHub CI pass proves a public service is live.

Run tests with
`python3 -m unittest tests.test_ai_stack_port_map
tests.test_cloudshell_public_domains -v`.
