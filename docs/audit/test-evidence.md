# Test Evidence — cvsz/zwslcore

**Generated:** 2026-11-08  
**Branch:** `feat/zwslcore-enterprise-hardening`  
**SHA:** Working tree with Dockerfile update + new tests

## 1. Test Suite Results

### Full Test Suite

```
Command: python3 -m unittest discover -s tests -v
Result:  200 tests, 0 failures, 0 errors — OK
Duration: ~6.5 seconds
Test files: 30 (29 original + 1 new)
```

## 2. Supply-Chain Test Details

| Test | Purpose | Result |
|------|---------|--------|
| test_base_image_uses_immutable_digest_not_latest_tag | Every FROM uses @sha256: digest | PASS |
| test_no_unpinned_from_lines | No FROM without digest pin | PASS |
| test_pip_install_uses_require_hashes | --require-hashes present | PASS |
| test_pip_install_uses_binary_only_policy | --only-binary=:all: present | PASS |
| test_pyyaml_source_build_exception_is_documented | --no-binary pyyaml exception present | PASS |
| test_container_runs_as_non_root | Container uses non-root USER | PASS |
| test_read_only_rootfs_in_compose | Compose has read_only: true | PASS |
| test_no_latest_tag_in_compose_images | No :latest/:main in compose images | PASS |

## 3. Shell Syntax Checks

| Script | Command | Result |
|--------|---------|--------|
| scripts/install.sh | bash -n | PASS |
| scripts/doctor.sh | bash -n | PASS |
| scripts/smoke.sh | bash -n | PASS |
| scripts/wait-runtime.sh | bash -n | PASS |
| scripts/backup.sh | bash -n | PASS |
| scripts/restore.sh | bash -n | PASS |
| scripts/chaos.sh | bash -n | PASS |
| scripts/bootstrap-wsl.sh | bash -n | PASS |
| scripts/lib/env.sh | bash -n | PASS |

## 4. Python Compilation

| Target | Command | Result |
|--------|---------|--------|
| services/provider/zeaz_provider | python3 -m compileall -q | PASS |
| services/engineering | python3 -m compileall -q | PASS |
| scripts/engineer.py | python3 -m py_compile | PASS |
| scripts/sync-free-models.py | python3 -m py_compile | PASS |
| scripts/models-dev.py | python3 -m py_compile | PASS |
| services/model_catalog/* | python3 -m py_compile | PASS |

## 5. Docker Image Scan

```
Command: grype local/zwslcore-provider:ci -o json --fail-on high
Result: exit 2 (2 High-severity without fixes remain)
Total vulnerabilities: 4 (0 Critical, 2 High, 1 Medium, 1 Low)

Critical: NONE
High (no fix available):
  - CVE-2026-119586: sqlite-libs 3.54.1-r0
  - CVE-2026-84243: glibc-2.44 2.44-r14
```

## 6. SBOM

```
Command: syft local/zwslcore-provider:ci -o spdx-json
Result: 97 packages, SPDX-2.3
Output: /tmp/opencode/provider-image.spdx.json
```

## 7. Docker Build

```
Command: docker build --pull --tag local/zwslcore-provider:ci -f services/provider/Dockerfile services/provider
Result: SUCCESS
```

## 8. Provider Runtime

```
Command: docker run --rm local/zwslcore-provider:ci --version
Result: zwslcore-provider 0.1.0 (PASS)
```

## 9. Evidence State Classification

| Claim | Evidence | State |
|-------|----------|-------|
| All 200 tests pass | Test suite output | VERIFIED |
| Docker image builds | Build output | VERIFIED |
| Image scan has 0 Critical | Grype output | VERIFIED |
| Image scan has 2 accepted-risk High | Grype output | VERIFIED |
| SBOM generated with 97 packages | Syft output | VERIFIED |
| Provider runs and reports version | Docker run output | VERIFIED |
| Windows/WSL2 tested | No Windows host available | BLOCKED |
| Isolated backup/restore drill | Not executed | NOT_ADDED |
