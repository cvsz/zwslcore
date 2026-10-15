# Reusable Architecture Review Prompt

Focused slice of `master-think-drill.md` for architecture decisions. Apply the
master workflow with emphasis on DIVE DEEPER; produce a decision, not a
redesign for aesthetics alone.

## Evaluate

1. Map system boundaries, contracts, data ownership, and trust boundaries from
   current source and configuration, not from documentation alone.
2. Assess scalability, availability, failure modes, observability, deployment,
   recovery, security, cost, and maintainability against the actual objective.
3. Compare major alternatives (including doing nothing) by benefit, risk,
   complexity, cost, migration impact, and operational burden.
4. Verify both sides of every touched contract: callers, schemas, migrations,
   feature flags, and rollback cost.

## Decide

Record the decision as an ADR-style entry: context, options considered,
chosen option with file/line evidence, consequences, migration and rollback
plan, and validation that proves the claim. Classify evidence per
`../../../ZEAZ-INTRODUCTION.md`; an unvalidated architecture remains
`UNVERIFIED` regardless of review consensus.
