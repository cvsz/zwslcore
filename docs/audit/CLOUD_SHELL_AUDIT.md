# Google Cloud Shell Audit — cvsz/zwslcore

**Date:** 2026-11-09  
**Repository:** cvsz/zwslcore  
**Status:** VERIFIED (CLI-only profile; ephemeral filesystem)

## 1. Scope

This document audits the Google Cloud Shell integration for zwslcore, which provides a CLI-only AI chat profile without the full WSL2/Docker/PostgreSQL stack.

## 2. Cloud Shell Profile Findings

| Area | Finding | Severity | Status |
|------|---------|----------|--------|
| Stack footprint | No PostgreSQL, no Docker, no Ollama models pulled | Low | VERIFIED |
| Entry point | `make cloudshell` → `scripts/cloudshell.sh` | Low | VERIFIED |
| AI CLI | `make ai-test` → `bash -n scripts/ai.sh` + `scripts/ai.sh selftest` | Low | VERIFIED |
| Endpoint | Default `http://127.0.0.1:8080/v1/chat/completions` (loopback only) | Low | VERIFIED |
| Credentials | API key read via `read -rsp` (not stored in config) | Low | VERIFIED |
| Ephemeral storage | Documented as ephemeral; unsuitable for always-on production | Low | VERIFIED |
| `make install` restriction | Documented warning not to use in Cloud Shell without full stack | Low | VERIFIED |

## 3. Security Findings

| Area | Finding | Severity | Status |
|------|---------|----------|--------|
| Loopback-only exposure | Cloud Shell profile does not publish services beyond `127.0.0.1` | Low | VERIFIED |
| No unauthenticated Ollama | Ollama not installed/run in Cloud Shell profile | Low | VERIFIED |
| API key handling | Key prompted interactively; not written to disk by default | Low | VERIFIED |
| Secret leakage | No secrets committed; `.env` gitignored | Low | VERIFIED |

## 4. Residual Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ephemeral filesystem | Data lost on session end | Documented; not suitable for production |
| No persistent storage | Model inventory not retained across sessions | Documented |
| Loopback dependency | Requires local Provider running on port 8080 | Documented |

## 5. Conclusion

Cloud Shell CLI-only profile is VERIFIED as a secure, loopback-only, ephemeral AI chat entry point. Not suitable for production hosting; documented limitations are appropriate.
