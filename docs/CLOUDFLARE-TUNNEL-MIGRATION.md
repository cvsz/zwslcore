# Cloudflare Tunnel migration safety

Use this workflow when moving an existing SSH hostname from one Cloudflare Tunnel to another. **No command in this document automatically updates DNS, Access, or running connectors.** Cloud Shell may change instances or egress IPs and should not be considered an always-on production origin.

## Diagnosis and local staging

1. Confirm the running connector and the destination tunnel from the account control plane. A destination tunnel being connected is **not proof** that its connector is on the desired origin machine.
2. Check that SSH listens on loopback port 22. Do not use ephemeral Cloud Shell RFC 1918 addresses as origin endpoints for connectors on unrelated machines.
3. For a **locally managed** destination tunnel, obtain that exact tunnel's credential JSON through an approved secure channel, outside the repository. Never reuse the source tunnel JSON or edit its TunnelID.
4. Run:

   ~~~bash
   export ZCLOUD_HOSTNAME=ssh.example.org
   export ZWSL_TARGET_TUNNEL_ID=REPLACE_WITH_DESTINATION_UUID
   make cloudflare-migration-inspect
   make cloudflare-migration-stage
   ~~~

   Staging requires a private, owned file at ~/.cloudflared/<destination-uuid>.json whose internal TunnelID matches the destination. Override with --target-credentials /secure/path.json when invoking the Python script directly. Staging creates ~/.local/state/zwslcore-tunnel-migration/staged-config.yml (0600) and validates ingress. It **does not modify ~/.cloudflared/config.yml**.

5. For a **remotely managed** destination tunnel, local credential JSON staging is not applicable. Use the dashboard-managed configuration and token-file deployment flow. Never put a token in a CLI argument, commit, transcript, or shared log.

## Cutover gates — all required

- The destination tunnel connector must be on the correct origin host or have a **verified, authorized** network path to it, with SSH tested. If the destination has replicas at unrelated origins, reconcile their routes before adding a replica; requests can otherwise land on the wrong connector.
- Confirm exact-host Cloudflare Access identity/MFA policy, absence of unsafe Bypass policies, SSH authorized keys, DNS ownership, and ingress mapping.
- Record the previous proxied DNS target and connector owner. Update the existing hostname's CNAME to <DESTINATION_UUID>.cfargotunnel.com through the authorized dashboard/API **only after destination readiness**. DNS resolution alone does not prove the service works.
- Test from an **external authorized SSH client** through Cloudflare Access, verifying the host-key fingerprint and destination. Only then retire the source connector through its existing supervisor.
- Roll back by restoring the former DNS route and source connector if SSH connectivity fails. Preserve Access policies and secrets.

## API is a separate origin

An SSH ingress at ssh://127.0.0.1:22 is not an HTTP API. Verify a working HTTP listener and authenticated model inference before introducing an API hostname. Never expose local Provider, Ollama, MCP, or webhook directly without authentication and rate controls.

## Evidence status

The inspect command checks local ingress only. Staging checks secure locally managed credentials, matching tunnel UUID, and a valid alternative ingress config. Neither operation verifies external DNS, Access policy, origin placement of destination replicas, or end-to-end SSH. Record those as NOT VERIFIED or BLOCKED until tested.

References: [Cloudflare Tunnel DNS](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/); [remotely managed token-file](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).
