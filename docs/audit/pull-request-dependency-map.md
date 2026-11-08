# Pull Request Dependency Map — cvsz/zwslcore

**Generated:** 2026-11-08  
**Purpose:** Map dependencies between PRs to determine safe merge order and identify blocking relationships.

---

## Dependency Chains

### Cloud Shell Chain
```
#71 (Cloud Shell Ollama install) 
  └─► #72 (multi-node Ollama pool) — depends on #71 being merged first
  └─► #76 (MCP diagnostics + SSH access) — depends on #71, #73
      └─► #77 (webhook body timeout) — depends on #76
  └─► #80 (zcloud recovery) — standalone, depends on Cloud Shell context
```

**Merge order:** #71 → #73 → #76 → #77, with #80 independent

### Engineering Control Plane Chain
```
#8 (engineering control plane)
  └─► #11 (hardware profiling, cost policy)
  └─► #23 (evidence bundles)
  └─► #24 (resumable cursor)
  └─► #33 (queue reconciliation)
  └─► #48 (durable queue recovery)
  └─► #102 (worktree hardening) — depends on all above
```

**All already merged.** #102 is open DRAFT and would be the next in this chain.

### Supply Chain Chain
```
#22 (Python 3.14 runtime)
  └─► #21 (dependency refresh)
  └─► #92 (Provider supply chain remediation)
  └─► Issue #108 (current remediation — Dockerfile digest fix committed on feat/zwslcore-enterprise-hardening)
  └─► #87 (certifi lock update) — superseded by issue #108 fix
  └─► #88 (digestabot automation) — could be re-proposed after issue #108 fix
```

### CodeQL Chain
```
#66 (CodeQL analyze bump) — superseded by #85
#67 (CodeQL init bump) — superseded by #84
#84 (CodeQL init v4.39.1) — merge ready
#85 (CodeQL analyze v4.39.1) — merge ready
#86 (CodeQL + Dependabot grouping sync) — DRAFT, depends on #84/#85
```

**Merge order:** #84 → #85 → #86

### FastAPI Chain
```
#65 (FastAPI update) — superseded by #101
#83 (FastAPI update) — superseded by #101
#101 (FastAPI <0.163) — merge ready, requires lockfile regeneration
```

### TruffleHog Chain
```
#100 (trufflehog 3.86.1→3.99.7) — superseded by #107
#107 (trufflehog 3.99.7→3.99.8) — merge ready
```

---

## Cross-PR Conflicts

| Conflicting PRs | Overlapping Files | Resolution |
|-----------------|-------------------|------------|
| #87 vs #88 | Both touch services/provider/requirements.lock and Dockerfile | #88 is DRAFT and non-buildable; #87 is insufficient alone. Both superseded by direct Dockerfile fix on feat/zwslcore-enterprise-hardening |
| #81 vs #82 | Both move LiteLLM PostgreSQL into Docker | #81 (policedbc) closed; #82 (cvsz) open DRAFT |
| #94 vs #95 vs #96 vs #97 | All add make release pre-flight target | #97 merged; others closed as superseded |
| #64 vs #90 | Both modify .env.example with model variables | #64 adds optional free providers; #90 changes default Ollama models to GGUF. Can coexist if #90 keeps GGUF as opt-in |

---

## PRs That Block Other Work

| Blocking PR | Blocked Work | Reason |
|-------------|-------------|--------|
| #71 | #72, #76 | Cloud Shell Ollama install is prerequisite for multi-node pool and MCP diagnostics |
| #76 | #77 | Webhook timeout fix builds on webhook infrastructure from #76 |
| #84, #85 | #86 | CodeQL v4.39.1 sync requires both init and analyze bumps |
| None | Issue #108 remediation | Issue #108 fix (Dockerfile digest) is already committed on feat/zwslcore-enterprise-hardening |

---

## PRs With No Dependencies (Safe to Merge Independently)

- #70 (dotenv config)
- #73 (Open WebUI contract)
- #80 (zcloud recovery)
- #84 (CodeQL init)
- #85 (CodeQL analyze)
- #90 (GGUF model support — review default model changes)
- #101 (FastAPI <0.163)
- #107 (TruffleHog bump)

---

## Merge Priority

| Priority | PRs | Rationale |
|----------|-----|-----------|
| P0 | #87, #88 | Superseded — close; issue #108 fix already committed |
| P1 | #84, #85, #101, #107 | Dependabot updates; low risk, merge ready |
| P1 | #70, #73 | Security/testing improvements; low risk |
| P2 | #80, #90 | Feature additions; need review |
| P2 | #79 | Security hardening; needs independent review |
| P3 | #71, #72, #76, #77 | Cloud Shell features; chain dependency |
| P3 | #64, #69, #82, #86, #91, #102 | DRAFT; keep until complete |
