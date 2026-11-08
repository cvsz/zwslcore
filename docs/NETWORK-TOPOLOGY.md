# Network Topology — zwslcore Provider Gateway

## Logical architecture

```text
ZCoder (192.168.1.85)
        |
        | authenticated API over restricted LAN (Bearer / X-API-Key)
        v
ZWSLCore Provider Gateway (192.168.1.100:8080, endpoint /v1)
        |
        +---- Ollama (internal Docker network zwslcore-ai, 11434, never published to LAN)
        |
        +---- LiteLLM (internal Docker network zwslcore-ai, 4000, never published to LAN)
        |
        +---- approved provider adapters (ollama, litellm, optional free cloud)

Open WebUI remains an independent UI client (loopback by default, 3000).
```

## Component ownership and boundaries

| Component | Listener | Exposure | Reachable from |
|-----------|----------|----------|----------------|
| Provider Gateway | 8080 (container) | publish controlled by `PROVIDER_BIND_ADDRESS` | local loopback by default; LAN only after firewall rule |
| Ollama | 11434 | `127.0.0.1:11434` only | local host only |
| LiteLLM | 4000 | `127.0.0.1:4000` only | local host only |
| Open WebUI | 3000 | `${OPENWEBUI_BIND_ADDRESS:-127.0.0.1}:3000` | loopback by default |

## Provider Gateway bind address (compose.yaml)

The Provider container binds to `0.0.0.0:8080` inside the container (Dockerfile `ZEAZ_HOST=0.0.0.0`), but Compose publishes only the loopback interface by default:

```yaml
ports:
  - "${PROVIDER_BIND_ADDRESS:-127.0.0.1}:${PROVIDER_PORT:-8080}:8080"
```

Default `PROVIDER_BIND_ADDRESS=127.0.0.1` preserves existing local-client behavior and keeps the Provider off the LAN. This is the secure default.

## Enabling LAN access for ZCoder (operator action)

To allow the ZCoder client at `192.168.1.85` to reach `http://192.168.1.100:8080/v1`:

1. Set `PROVIDER_BIND_ADDRESS=0.0.0.0` in `.env` (or `.env.production`).
2. Recreate the Provider container: `docker compose --env-file .env up -d provider`.
3. Apply the host firewall rule below restricting ingress to `192.168.1.85/32`.
4. Verify: from the ZCoder host, `curl -i http://192.168.1.100:8080/health/live` returns `200`; from any other LAN address the connection is dropped.

Do **not** expose `0.0.0.0:8080` without the firewall rule. Do **not** expose Ollama (11434) or LiteLLM (4000) to the LAN — they remain loopback-only.

## Exact host firewall rule (operator-applied, not applied here)

Firewall access cannot be verified from this build environment, so no firewall change is made in this commit. The operator must apply one of the following on the ZWSLCore host (192.168.1.100):

### nftables (preferred)

```bash
# Allow only the ZCoder client to reach the Provider Gateway on 8080.
nft add rule inet filter input tcp dport 8080 ip saddr 192.168.1.85/32 counter accept
# Drop all other ingress to 8080.
nft add rule inet filter input tcp dport 8080 counter drop
# Save (distribution dependent): nft save
```

### iptables

```bash
iptables -A INPUT -p tcp -s 192.168.1.85/32 --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP
# Save (distribution dependent): iptables-save
```

Verify after applying:

```bash
ss -tlnp | grep 8080            # provider shows 0.0.0.0:8080 after bind change
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.100:8080/health/live   # from 192.168.1.85 -> 200
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.100:8080/health/live   # from another LAN IP -> connection refused/timed out
```

Do not flush or replace Docker-managed firewall rules (`docker`/`kube-`/`ingress` chains). Add rules above Docker's chains in `INPUT`.

## TLS / encryption

The Provider Gateway serves plain HTTP on the LAN. Terminating TLS requires certificate provisioning and renewal that is not part of this repository, so TLS is **not** configured by default.

**LAN trust assumption:** the Provider Gateway and ZCoder client operate within the trusted `192.168.1.0/24` LAN. Bearer credentials are required for every inference route and never leave the LAN. Authentication remains fail-closed (no credentials configured → all inference routes rejected). Do not weaken authentication as a substitute for TLS.

## Open WebUI exposure policy

Open WebUI remains loopback-only by default (`OPENWEBUI_BIND_ADDRESS=127.0.0.1`). Operators may opt into LAN access via `.env`; that policy is unchanged by this document. Provider, LiteLLM, and Ollama are never exposed through the Open WebUI reverse proxy or Cloudflare profile.

## Verification checklist

- [ ] `PROVIDER_BIND_ADDRESS=127.0.0.1` (default) → Provider reachable only on `127.0.0.1:8080`.
- [ ] `PROVIDER_BIND_ADDRESS=0.0.0.0` + firewall rule → Provider reachable on LAN only from `192.168.1.85`.
- [ ] Ollama `127.0.0.1:11434` and LiteLLM `127.0.0.1:4000` loopback-only.
- [ ] Bearer auth required on `/v1/models`, `/v1/chat/completions`, `/v1/messages`, `/v1/responses`.
- [ ] No credentials logged or returned in responses.
