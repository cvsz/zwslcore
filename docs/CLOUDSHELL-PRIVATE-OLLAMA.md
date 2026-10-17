# Cloud Shell private Ollama route verification

This optional diagnostic detects a changed Cloud Shell RFC1918 interface
address and checks the existing `cloudflared` private-network /32 route.
It neither assigns a static IP to Cloud Shell nor creates a new Tunnel.
No `.env` or credentials are read and no existing route is removed.

## On Cloud Shell

```bash
python3 scripts/cloudshell_private_ollama.py status --interface eth0 --model YOUR_INSTALLED_MODEL
python3 scripts/cloudshell_private_ollama.py sync-route --vnet-id EXISTING_VNET_UUID --model YOUR_INSTALLED_MODEL
```

The second command is dry-run by default. For an authorized **locally
managed** connector running on the same Cloud Shell host, a new /32 route can
be registered only with an explicit `--apply` flag. Before applying, verify
that the existing Cloudflare Tunnel, VNet and Access/WARP policies are correct.

```bash
python3 scripts/cloudshell_private_ollama.py sync-route \
  --vnet-id EXISTING_VNET_UUID --model YOUR_INSTALLED_MODEL --apply
```

The script rejects pre-existing routes when their Tunnel/VNet ownership
cannot be verified in the CLI listing, checks the connector on this specific
host before registration and validates read-back. A successful route update
still does not prove WARP client connectivity. Never route an entire LAN or
default subnet just to reach a single Cloud Shell model.

## On the zWorkforce host

The actual zWorkforce host needs an authorized WARP/device connection to the
correct Cloudflare One Virtual Network and an explicit route to the Cloud
Shell private address. Obtain the current IP from the Cloud Shell status
check and use:

```bash
python3 scripts/cloudshell_private_ollama.py client-check \
  --ip CURRENT_CLOUDSHELL_PRIVATE_IP --model YOUR_INSTALLED_MODEL --infer
```

An HTTP model inventory and an opt-in OpenAI-compatible inference response
prove client reachability only when executed from that actual zWorkforce
host. This is not a cloud SLA. Cloud Shell addresses and VMs are ephemeral.

**Security:** Ollama's default listener has no bearer-token authentication.
Never publish port 11434 to the public Internet. Private routing alone does
not replace Cloudflare One device/network authorization or an authenticated
proxy. Provider credentials and the existing zWorkforce model router remain
unchanged.

Rollback: stop using the optional script. It makes no filesystem, DNS or
runtime changes during status/normal dry-run. An explicitly added /32 route
must be reverted separately using reviewed Cloudflare change procedures
and verified route ownership, never by blanket route deletion.

Tests: `python3 -m unittest tests.test_cloudshell_private_ollama -v`.
