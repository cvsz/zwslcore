# PR Remediation Tracker

**Repository**: `cvsz/zwslcore`  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)

---

## 1. Remediation Items by PR

| PR | Remediation Item | Owner | Status | Dependencies | Blocker |
|-----|-----------------|-------|--------|--------------|---------|
| #102 | Address policedbc CHANGES_REQUESTED; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #101 | Request policedbc review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #100 | Request policedbc review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #91 | Remove draft; request review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #90 | Request policedbc review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #89 | Request policedbc review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #88 | Resolve conflict; address review feedback; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #87 | Resolve conflict; address review feedback; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #86 | Remove draft; request review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #85 | Address policedbc review feedback; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #84 | Address policedbc review feedback; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #82 | Remove draft; request review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #80 | Address policedbc review feedback; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #79 | Request policedbc review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #78 | New authorization for current SHA; resolve CVE blocker | cvsz | PENDING | CVE fix + new authorization | CVE-2026-115557 |
| #77 | Investigate base branch; add CI checks; resolve conflicts | cvsz | PENDING | None | No CI checks |
| #76 | Request policedbc review; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #73 | Request policedbc review; verify CI; authorize merge | cvsz | READY | None | None |
| #72 | Investigate 3 missing checks (non-main base) | cvsz | PENDING | None | CI check configuration |
| #71 | Address policedbc review feedback; resolve CVE blocker | cvsz | PENDING | CVE fix | CVE-2026-115557 |
| #70 | Request policedbc review | cvsz | PENDING | None | No review |
| #69 | Remove draft; request policedbc review | cvsz | PENDING | None | Draft status |
| #64 | Remove draft; request policedbc review | cvsz | PENDING | None | Draft status |

---

## 2. Items Requiring policedbc Review

| PR | Current Review State | Action Required |
|-----|---------------------|-----------------|
| #78 | APPROVED (on current SHA) | New authorization needed for current SHA |
| #73 | APPROVED | Authorization needed |
| #72 | APPROVED | CI check investigation needed |
| #102 | CHANGES_REQUESTED | Address feedback |
| #85 | CHANGES_REQUESTED | Address feedback |
| #84 | CHANGES_REQUESTED | Address feedback |
| #80 | CHANGES_REQUESTED | Address feedback |
| #71 | CHANGES_REQUESTED | Address feedback |
| #88 | CHANGES_REQUESTED | Address feedback |
| #87 | CHANGES_REQUESTED | Address feedback |
| #101 | REVIEW_REQUIRED | Request review |
| #100 | REVIEW_REQUIRED | Request review |
| #91 | REVIEW_REQUIRED | Request review |
| #86 | REVIEW_REQUIRED | Request review |
| #82 | REVIEW_REQUIRED | Request review |
| #79 | REVIEW_REQUIRED | Request review |
| #76 | REVIEW_REQUIRED | Request review |
| #70 | REVIEW_REQUIRED | Request review |
| #69 | REVIEW_REQUIRED | Request review |
| #64 | REVIEW_REQUIRED | Request review |

---

## 3. Items Requiring CVE Resolution

| PR | Blocker | Required Action |
|-----|---------|-----------------|
| #102 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #101 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #100 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #91 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #90 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #89 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #88 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #87 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #86 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #85 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #84 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #82 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #80 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #79 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #78 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #76 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |
| #71 | build-scan-sbom FAILURE | CVE-2026-115557 fix or risk acceptance |

---
