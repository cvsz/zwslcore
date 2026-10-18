# Signed Cloud Shell Webhook

This optional integration adds a loopback-only receiver for `/webhook`; it does **not** execute tasks or forward commands into zWorkforce without an explicit, reviewed provider contract.

```bash
cd ~/zwslcore
make webhook-install
make webhook-start    # foreground; separate Cloud Shell terminal
make webhook-health   # second terminal
```

The local receiver binds `127.0.0.1:8765`.
The health endpoint returns a receiver-specific JSON identity
(`status=healthy`, `service=zwslcore-signed-webhook`, `version=1`).
`make webhook-health` and the opt-in route installer verify that identity,
rather than accepting any HTTP 200 from an unrelated service.
Set `ZCLOUD_SSH_PORT` consistently with your existing SSH ingress port
(default `22`); a custom port such as `2222` is supported without changing
the managed SSH origin. It accepts `POST /webhook` with JSON objects up to 64 KiB. The sender must supply:
- `X-ZWSL-Timestamp`: Unix epoch seconds (maximum clock skew 300 seconds)
- `X-ZWSL-Event-ID`: a unique, unguessable event identifier (alphanumeric, underscore or hyphen)
- `X-ZWSL-Signature`: `sha256=` plus hex HMAC-SHA256 of `timestamp + "." + event_id + "." + raw_body`

The secret is generated locally at `~/.config/zwslcore/webhook.key` with mode 0600; it is never committed. Accepted event identifiers are stored as keyed hashes in a private SQLite replay database at `~/.local/state/zwslcore-webhook/replay.sqlite3` (override using `ZWSL_WEBHOOK_REPLAY_DB`). Unique inserts reject concurrent duplicates and persist across receiver process restarts. The state directory must be owner-only (0700) and the database private (0600); an unavailable or insecure store fails closed. The retention window is 600 seconds, longer than the 300-second signature clock skew. Multiple replicas on independent disks, ephemeral home-directory loss and full production durability still require an operator-managed shared deduplication store. Authentication does not mean the event is executed; the current receiver acknowledges valid events with `accepted=true, executed=false`.

## Cloudflare route (separate SSH and HTTP paths)

Keep the existing locally managed tunnel and Access Application. Do not send webhook traffic to SSH port 22.

```bash
export ZCLOUD_HOSTNAME=ssh.example.org
make cloudflare-doctor
# Configure a strict path-specific Access policy before changing routing.
ZWSL_WEBHOOK_ACCESS_VERIFIED=YES make webhook-route
cloudflared tunnel --config ~/.cloudflared/config.yml ingress rule "https://$ZCLOUD_HOSTNAME/webhook"
cloudflared tunnel --config ~/.cloudflared/config.yml ingress rule "https://$ZCLOUD_HOSTNAME/"
```

The route tool backs up the existing ingress YAML and inserts `^/webhook/?$` ahead of the SSH service entry only when its exact layout is recognized; it refuses ambiguous configurations. The existing connector is never stopped or restarted automatically. If anything is wrong:

```bash
make webhook-rollback
```

**Important:** Cloudflare Access policies are managed at the edge, not by this local YAML installer. The operator must verify the matching path-specific Access protection, provider authentication compatibility, and the absence of host-wide Bypass policies. For webhook providers that cannot satisfy an interactive Access login, use an independently authenticated path with provider signature verification and a reviewed network policy; do not enable anonymous forwarding based only on the fact that the receiver has HMAC. Do not reuse CLI OAuth callback query tokens for webhook authentication.

Cloud Shell is ephemeral, and in-process deduplication is lost when restarted. Do not treat this receiver as a durable zWorkforce task ingest service. Production requires a specific signed event schema, persistent idempotency, approval-gated dispatch, and a stable host.
