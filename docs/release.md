# Release

## Scope

This template provides release guidance and release-note configuration. It does **not** provide a generic artifact-publishing workflow because publishing credentials, registries, signing, environments, and approval policy are project-specific.

The in-repository Provider has a scoped supply-chain workflow. It builds the Provider image, fails on HIGH or CRITICAL findings, and stores the local image archive, image and source SPDX SBOMs, scan report, and a machine-readable manifest as immutable GitHub workflow artifacts for 30 days. Pushes to `main` and version tags also create and verify keyless GitHub provenance and an image SBOM attestation. The workflow does not publish to a container registry or deploy. Its manifest records the local image ID and archive checksum; `registry_digest` and `rollback_target` remain `null` until a project-specific registry release and known-good rollback target exist.

The Provider lock at `services/provider/requirements.lock` is generated from its `pyproject.toml` for Python 3.14 with exact versions and package hashes. Run `make provider-lock` with Python 3.14 and pip-tools 7.6.1 for an intentional dependency refresh; CI runs `make provider-lock-check` to detect lock drift. The Provider image installs only hash-verified wheels from this lock, then installs the local package without resolving dependencies again.

To verify an attested workflow artifact after a trusted push, download the `provider-supply-chain-<source-sha>` workflow artifact and run `gh attestation verify artifacts/provider-image.tar.gz --repo OWNER/REPOSITORY`. GitHub attestation verification checks the artifact against its workflow identity and recorded provenance; it does not establish that the artifact was deployed or is a known-good rollback target.

## Versioning

Use an explicit versioning policy. Semantic Versioning is recommended for reusable software unless the project defines a better scheme.

## Release checklist

1. Confirm the release commit is the intended exact head.
2. Ensure required CI/security checks pass on that exact head.
3. Confirm protected-branch/admin controls are effective.
4. Update `CHANGELOG.md` and compatibility/migration notes.
5. Verify deployment and rollback procedures.
6. Verify migrations and data rollback/forward strategy when applicable.
7. Verify required backup/restore evidence for stateful systems.
8. Create/push the release tag according to project policy.
9. Publish artifacts only from trusted workflows/environments.
10. Generate provenance/signing/attestation where required.
11. Verify the published artifact and deployed environment.
12. Record release evidence and remaining known risk separately.

## Production readiness

Release authorization and production readiness are distinct.

A maintainer may authorize a release with accepted risk, but accepted risk does not convert `PARTIALLY VERIFIED`, `UNVERIFIED`, or `BLOCKED` readiness gates into `VERIFIED`.

Use the canonical evidence definitions in `../ZEAZ-INTRODUCTION.md`.

## Rollback

Document and test, as appropriate:

- last known-good artifact/build
- application rollback
- safe database/data migration handling
- configuration rollback
- credential/artifact invalidation after compromise
- traffic/routing rollback
- operator and stakeholder communication

A rollback document without environment-appropriate execution evidence is not proof that recovery will work.
