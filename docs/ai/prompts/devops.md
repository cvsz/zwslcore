# Reusable DevOps / SRE Prompt

Focused slice of `master-think-drill.md` for delivery and operations. Prefer
idempotent, auditable, reversible, environment-aware automation. Do not mutate
production without explicit authorization.

## Assess

- CI/CD: required checks, hermetic tests, exact-head verification;
- reproducible builds: pinned images/digests, hashed lockfiles, SBOMs;
- artifacts: immutable identity, provenance, signing, rollback target;
- containers and IaC: least privilege, read-only surfaces, drift detection;
- deployment and rollback: rehearsed paths with preserved user state;
- secrets: rotation, recovery, and absence from logs/evidence/Git;
- observability: structured logs, metrics, traces, actionable alerts;
- backup, restore, DR, capacity, and SLO/SLI where applicable.

## Deliver

Record baseline, change, validation evidence, and rollback per
`../../../ZEAZ-INTRODUCTION.md`. A green build alone never proves production
readiness; every applicable gate must be `VERIFIED` with direct evidence, and
accepted risk must be recorded separately without upgrading gate states.
