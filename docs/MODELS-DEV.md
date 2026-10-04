# Models.dev integration

zwslcore treats Models.dev as an optional metadata source, not a runtime dependency.

## Source endpoints

The default sync endpoint is:

    https://models.dev/catalog.json?type=all

The combined catalog contains:

- `providers`: provider records keyed by provider ID, including their model offerings;
- `models`: provider-agnostic canonical model metadata keyed by lab/model ID.

Models.dev publishes provider costs in USD per million tokens. zwslcore preserves those values as source metadata and does not use them to override the Provider's local `ZEAZ_COST_POLICY`.

## Commands

    python3 scripts/models-dev.py sync
    python3 scripts/models-dev.py stats
    python3 scripts/models-dev.py providers
    python3 scripts/models-dev.py lookup <MODEL_ID>

Equivalent Make targets:

    make models-dev-sync
    make models-dev-stats

## Cache and failure policy

The cache path defaults to:

    ~/.zwslcore/cache/models.dev.catalog.json

The cache envelope records its source URL and fetch timestamp. Writes use fsync + atomic replace. A network refresh has a 16 MiB response cap and a bounded HTTP timeout.

Lookup uses fresh cache first. If refresh fails and a previous cache exists, zwslcore can use the stale cache. If neither network nor cache is available, the command fails instead of inventing model metadata.

## Trust boundary

Models.dev metadata is advisory:

- it does not make a model executable locally;
- it does not automatically enable a cloud provider;
- it does not add or expose provider credentials;
- it does not bypass `ZERO_COST_ONLY` routing policy;
- local Ollama inventory and zwslcore Provider routes remain the execution authority.

This separation lets zwslcore use current model context, capability, pricing and provider metadata while preserving local-first/offline-safe behavior.


## Explainable recommendation engine

Rank candidates:

    python3 scripts/models-dev.py recommend --structured-output --min-context 4096

Optional filters:

    --tool-call
    --reasoning
    --min-context N
    --include-remote
    --permit-paid
    --top N

Ranking is deterministic and returns score, eligibility, reasons and blockers.

Hard eligibility rules are evaluated before score:

- disabled providers are ineligible;
- `ZERO_COST_ONLY` rejects offerings with non-zero published input/output price;
- required structured output, tool calling, reasoning and context must be satisfied.

Local Provider aliases receive the strongest preference. Remote Models.dev offerings are considered only when `--include-remote` is supplied; if `FREE_CLOUD_FALLBACK_ENABLED=false`, those candidates remain disabled and therefore ineligible.

For autonomous engineering, `ZEAZ_ENGINEERING_MODEL=auto` ranks only configured local Provider aliases. It does not dynamically enable or call cloud models. An explicit alias in `.env` overrides automatic selection.
