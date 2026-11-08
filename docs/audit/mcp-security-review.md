# MCP Security Review — cvsz/zwslcore

**Generated:** 2026-11-08  
**Scope:** Local stdio MCP client (`services/engineering/mcp.py`)  
**Status:** VERIFIED

---

## 1. Transport Security

| Control | Implementation | Status |
|---------|---------------|--------|
| stdio transport only | `subprocess.Popen` with `shell=False` | VERIFIED |
| No HTTP/SSE/OAuth | Remote transports intentionally deferred | VERIFIED |
| No automatic tool execution | Autonomous agents do not receive MCP tool execution | VERIFIED |
| Explicit invocation only | `mcp-call` command requires explicit tool and arguments | VERIFIED |

---

## 2. Process Management

| Control | Implementation | Status |
|---------|---------------|--------|
| `shell=False` | No shell interpolation; direct argv execution | VERIFIED |
| Process termination | `terminate()` → `kill()` with timeout; all streams closed in `finally` | VERIFIED (PR #79) |
| Stderr draining | Dedicated thread with selector timeout prevents pipe block | VERIFIED (PR #79) |
| Bounded messages | `MAX_MESSAGE_BYTES = 2 * 1024 * 1024` | VERIFIED |
| Request timeouts | Socket connect/read timeouts configured | VERIFIED |

---

## 3. Environment Isolation

| Control | Implementation | Status |
|---------|---------------|--------|
| Environment allowlist | Only allowlisted environment variables passed to MCP process | VERIFIED |
| No secret leakage | Environment variables filtered; secrets not passed | VERIFIED |
| Process isolation | Separate process per MCP server | VERIFIED |

---

## 4. Input/Output Validation

| Control | Implementation | Status |
|---------|---------------|--------|
| Tool registration | Servers configured in `~/.zwslcore/mcp/servers.json` | VERIFIED |
| Input validation | JSON-RPC 2.0 message validation | VERIFIED |
| Output validation | Response schema validation | VERIFIED |
| Error propagation | Errors propagated without secret disclosure | VERIFIED |
| Message size limits | 2 MiB max message size | VERIFIED |

---

## 5. PR #79 MCP Hardening

**Changes in PR #79 (OPEN):**
- Added `threading` import for stderr drainer
- Added `STDERR_TAIL_BYTES = 4096` and `READ_CHUNK_BYTES = 64 * 1024` constants
- Added `_drain_stderr()` method with selector-based timeout
- Improved `close()` with `finally` block closing all streams (stdin, stdout, stderr)
- Removed unused `contextmanager` and `Iterator` imports

**Assessment:** These changes improve process lifecycle safety and prevent stderr pipe deadlock. The stderr drainer is important because a chatty MCP server could block on a full pipe, causing the parent process to hang.

---

## 6. Residual Risks

| Risk | Likelihood | Impact | Control |
|------|-----------|--------|---------|
| Malicious MCP server configuration | Low | High | Servers configured manually in `servers.json`; no auto-discovery |
| MCP server path traversal | Low | Medium | Server commands are configured, not user-supplied at runtime |
| Secret disclosure via MCP | Low | High | Environment allowlist; no secrets in MCP config |
