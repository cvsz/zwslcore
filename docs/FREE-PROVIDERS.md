# Optional Free-Tier Provider Expansion

This is an **opt-in** gateway extension, not an unlimited-free guarantee.

## Existing behavior

`zeaz-free` remains the default alias, with local Ollama as primary.
Existing `zeaz-fast`, `zeaz-coder`, `zeaz-reasoning`, `zeaz-local`, `zeaz-auto`, and cloud aliases are unchanged.
`FREE_CLOUD_FALLBACK_ENABLED=false` remains the default for existing remote gateways.

## Additional optional gateways

| Provider | Enable | API Key | Alias |
|---|---|---|---|
| Cerebras | `CEREBRAS_FREE_ENABLED=true` | `CEREBRAS_API_KEY` | `zeaz-cloud-cerebras` |
| SambaNova | `SAMBANOVA_FREE_ENABLED=true` | `SAMBANOVA_API_KEY` | `zeaz-cloud-sambanova` |
| Cloudflare Workers AI | `CLOUDFLARE_FREE_ENABLED=true` | `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` | `zeaz-cloud-cloudflare` |

These endpoints use OpenAI-compatible chat APIs. Model IDs and eligibility change.
Verify that the configured model is currently accessible, supports chat, and is covered by
the account's free quota. **Set up provider-side spending limits and alerts first.**
The gateway's `FREE_REMOTE` cost class is a policy label, not real-time billing verification.
Do not enable an optional provider without checking current plan terms and quotas.

`zeaz-cloud-auto` adds a new opt-in-capable route: local fast model first,
then available remote fallbacks in configured order. Its name does not imply
latency-aware routing; the existing router uses fallback-on-error, not live p95
selection. Do not send private repository code to cloud providers without
company approval and an acceptable data-processing policy.

## Benchmark

Read `PROVIDER_CLIENT_KEY` from the private runtime environment, never store
it in committed files or benchmark reports. For local-only comparison:

```bash
python3 scripts/benchmark-free-coding.py --model zeaz-fast --model zeaz-coder --iterations 3 --output benchmark-local.json
```

Only after explicit free-tier validation and consent to remote code processing:

```bash
python3 scripts/benchmark-free-coding.py --model zeaz-cloud-cerebras --iterations 3 --allow-remote
```

The benchmark measures end-to-end latency and reported output tokens/s; it does
**not** measure correctness or use statistically representative workloads. Its
requests are bounded, non-streaming and do not log secrets or model output.
If no provider returns token usage, throughput is null. A failure returns non-zero.

## Verification and rollback

```bash
python3 -m unittest discover -s tests -v
make config
make ci
```

Before a live remote smoke test, verify account limits and configure valid keys.
Rollback by setting all three `*_FREE_ENABLED=false`, then restarting Provider,
or reverting the PR. Existing provider configuration remains available.
