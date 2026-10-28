# ADR 0001: zwslcore Runtime and Video Factory Boundary

- Status: Proposed
- Date: 2026-10-29
- Owners: @cvsz

## Context

The repository contains a working WSL2-oriented model-serving runtime and local engineering control plane, while parts of the inherited repository documentation still describe a language-agnostic template. The ZEAZDEV Video Factory specification also defines a separate control plane, inference plane, media plane, and artifact plane.

Without an explicit boundary, future changes could accidentally couple video inference to the LLM gateway, treat an LLM as a video-generation runtime, share internal databases, or introduce automatic external inference when local capacity is unavailable.

## Proposed decision

1. Treat zwslcore as the local-first LLM/model-serving gateway and local engineering runtime. Keep the inherited governance/bootstrap utilities subordinate to that application scope.
2. Preserve the Provider's supported HTTP API as the integration boundary for LLM capabilities. Do not require ZCoder or ZWorkforce to import zwslcore internals.
3. Keep Video Factory generation, MiniMax H3 weights/runtime, media processing, QA, artifacts, and publication approval in the separate Video Factory system and its qualified workers.
4. Allow ZCoder to use zwslcore for prompt planning and other LLM tasks through the supported API. Allow ZWorkforce to orchestrate Video Factory jobs only through an approved versioned API or authenticated webhook contract.
5. If CMe is approved for identity or shared metadata, integrate through its documented API; do not read or write its internal tables directly.
6. Fail closed when no compatible local provider/model is available. Do not silently route to a paid or external inference provider.

## Alternatives considered

- **Move H3 inference into zwslcore:** rejected because it mixes LLM serving with a distinct video inference/runtime and media-processing lifecycle, undermining worker qualification and resource isolation.
- **Treat the LLM endpoint as the video engine:** rejected because prompt/storyboard generation does not perform video inference.
- **Share internal database tables across services:** rejected because it creates schema coupling and circular deployment dependencies.
- **Automatically fall back to hosted inference:** rejected because it violates the local-first, fail-closed cost and privacy policy.

## Consequences

- zwslcore remains independently operable for LLM serving even when no video worker is available.
- Video Factory can add or replace H3 workers without requiring a zwslcore deployment change, provided the public integration contract remains compatible.
- Cross-service integration requires least-privilege credentials, idempotent job submission, authenticated/replay-protected webhooks, and explicit ownership of state.
- This ADR does not implement those integrations or establish production readiness. The status remains Proposed until reviewed and accepted.

## Validation

Before accepting this ADR or claiming integration readiness:

- Verify the Compose stack contains no H3/video inference runtime or model weights.
- Verify local-provider exhaustion returns a clear failure rather than a paid/external fallback.
- Add contract tests for any implemented API/webhook integration.
- Verify authentication, idempotency, replay protection, observability, and failure isolation.
- Require exact-head CI/security checks and independent review for changes that cross these boundaries.
