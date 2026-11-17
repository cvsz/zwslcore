# Production-Grade Implementation Plan

## Objective
Transform zwslcore into a 100% complete, enterprise-grade, production-ready system with:
- Zero linting errors (ruff, shellcheck)
- Zero security findings (bandit)
- Full type safety (mypy)
- 100% test coverage with all tests passing
- Complete documentation sync
- Final comprehensive report

## Current State Assessment

### ✅ Passing
- **Tests**: 226/226 passing
- **Type Checking**: mypy clean (62 source files)
- **Core Functionality**: All engineering control plane, model catalog, provider gateway working

### ❌ Needs Fixing
- **Ruff Linting**: 213 errors (complexity, style, unused args, magic values, mutable defaults)
- **Shellcheck**: 2 informational (sourced files not followed)
- **Bandit Security**: 9 medium severity issues (subprocess, urllib, SQL injection)
- **Documentation**: May be out of sync with latest implementation

---

## Implementation Steps

### Phase 1: Linting Fixes (Ruff) - PRIORITY: HIGH

#### Step 1.1: Fix Complexity Issues (PLR0912, PLR0915, PLR0913, PLR0911, PLR0917)
- **Target Files**:
  - `services/engineering/loop.py` - Too many branches (14>12), too many statements
  - `services/engineering/mcp.py` - Too many branches (13>12)
  - `services/engineering/observability.py` - Too many args (10>5)
  - `services/engineering/prometheus.py` - Too many returns (9>6), magic values
  - `services/engineering/runtime.py` - Too many branches (23>12), statements (197>50), args
  - `services/engineering/snapshot.py` - Too many branches (13>12), returns (7>6), args (6>5)
  - `services/engineering/tui.py` - Too many returns (7>6), branches (14>12), args (7>5), statements (77>50)
  - `services/engineering/worktree.py` - subprocess without check
  - `services/model_catalog/selector.py` - Too many branches (20>12), statements (55>50), magic values
  - `services/provider/zeaz_provider/errors.py` - Too many args (9>5)
  - `services/provider/zeaz_provider/observability.py` - Too many args (8>5)
  - `services/provider/zeaz_provider/resilience.py` - Too many args (7>5)
  - `services/provider/zeaz_provider/streaming.py` - Too many branches/returns/statements

- **Strategy**: Extract helper methods, use dataclasses for parameter groups, add constants for magic values

#### Step 1.2: Fix Mutable Default Values (RUF012)
- **Target Files**:
  - `services/engineering/runtime.py:220` - EDIT_RESPONSE_SCHEMA class attribute
  - `services/engineering/snapshot.py:10,14,17` - EXCLUDED_DIRS, SECRET_NAMES, SECRET_SUFFIXES
- **Strategy**: Use `ClassVar` annotation or initialize in `__init__`

#### Step 1.3: Fix Exception Types (TRY004)
- **Target Files**:
  - `services/engineering/prometheus.py:196,214` - Use TypeError instead of ValueError
  - `services/engineering/runtime.py:899,902,906,910` - Use TypeError instead of ValueError
- **Strategy**: Change exception types to TypeError for invalid type checks

#### Step 1.4: Fix TRY300/TRY301 Issues
- **Target Files**:
  - `services/engineering/mcp.py:172` - Abstract raise to inner function
  - `services/engineering/runtime.py:609,636,689` - Abstract raises, move to else blocks
  - `services/model_catalog/models_dev.py:186` - Move to else block
- **Strategy**: Extract error-raising helpers, restructure control flow

#### Step 1.5: Fix Magic Values (PLR2004)
- **Target Files**:
  - `services/engineering/mcp.py:91` - timeout 300
  - `services/engineering/prometheus.py:286` - port 65535
  - `services/engineering/runtime.py:83` - HTTP 500, 599
  - `services/model_catalog/selector.py:239,243` - RAM thresholds 10, 14
- **Strategy**: Define module-level constants with descriptive names

#### Step 1.6: Fix ARG005 Unused Lambda Arguments
- **Target Files**: Multiple test files
- **Strategy**: Use `_` prefix or remove unused params

#### Step 1.7: Fix PLW1510 subprocess.check=False
- **Target Files**: Multiple files in services/engineering, tests/
- **Strategy**: Add explicit `check=False` to subprocess.run calls

#### Step 1.8: Fix PTH105 Path.replace()
- **Target Files**: `services/model_catalog/models_dev.py:111`
- **Strategy**: Use `Path.replace()` instead of `os.replace()`

#### Step 1.9: Fix SIM117 Nested with Statements
- **Target Files**: Multiple test files
- **Strategy**: Combine nested context managers

#### Step 1.10: Fix E741 Ambiguous Variable Names
- **Target Files**: `tests/test_supply_chain_dockerfile.py` - variable `l`
- **Strategy**: Use descriptive names like `line`

#### Step 1.11: Fix PLC0415 Top-level Imports
- **Target Files**: `tests/test_engineering_metrics.py`, `tests/test_model_inventory.py`
- **Strategy**: Move imports to module top level

#### Step 1.12: Fix PR02004 Magic Values in Tests
- **Target Files**: Test files with hardcoded numbers
- **Strategy**: Use constants or parameters

---

### Phase 2: Security Fixes (Bandit) - PRIORITY: HIGH

#### Step 2.1: Fix SQL Injection in backup.py
- **Location**: `scripts/backup.py:105` - f-string in SQL query
- **Fix**: Use parameterized queries with `?` placeholders

#### Step 2.2: Fix urllib URL Opening (B310)
- **Locations**: Multiple files using `urllib.request.urlopen`
- **Files**: `scripts/bootstrap-litellm-admin.py`, `scripts/chaos.py`, `scripts/sync-free-models.py`, `services/engineering/runtime.py`, `services/model_catalog/models_dev.py`
- **Fix**: Add `# nosec B310` comments with justification, or use allowlist validation

#### Step 2.3: Fix subprocess Issues (B404, B603, B607)
- **Files**: `scripts/backup.py`, `services/engineering/worktree.py`
- **Fix**: Use absolute paths for executables, validate inputs, add `# nosec` where appropriate

#### Step 2.4: Fix Assert Usage (B101)
- **Files**: `services/provider/zeaz_provider/resilience.py` (2 locations)
- **Fix**: Replace asserts with explicit checks and raises

---

### Phase 3: Shellcheck Fixes - PRIORITY: MEDIUM

#### Step 3.1: Source File Following
- **Files**: `scripts/install.sh`, `scripts/wait-runtime.sh`
- **Fix**: Add shellcheck directive or ensure sourced files are available

---

### Phase 4: Code Quality Improvements - PRIORITY: MEDIUM

#### Step 4.1: Add Missing Type Hints
- Review all function signatures for complete type annotations

#### Step 4.2: Improve Error Handling
- Add more specific exception types
- Improve error messages with context

#### Step 4.3: Add Docstrings
- Ensure all public functions/classes have comprehensive docstrings

#### Step 4.4: Optimize Performance
- Review hot paths for optimization opportunities
- Add caching where appropriate

---

### Phase 5: Testing Enhancement - PRIORITY: MEDIUM

#### Step 5.1: Increase Test Coverage
- Target: >90% coverage for all modules
- Add integration tests for critical paths

#### Step 5.2: Add Property-Based Tests
- Use hypothesis for complex logic validation

#### Step 5.3: Add Benchmark Tests
- Performance regression detection

---

### Phase 6: Documentation Sync - PRIORITY: HIGH

#### Step 6.1: Update All Documentation
- README.md - verify all commands work
- docs/ - sync with latest implementation
- AGENTS.md - verify accuracy
- CHANGELOG.md - update with all changes
- IMPLEMENTATION-SUMMARY.md - update

#### Step 6.2: Generate Final Report
- Create comprehensive FINAL-REPORT.md with:
  - System architecture overview
  - All components status
  - Test results summary
  - Security audit results
  - Performance benchmarks
  - Deployment readiness checklist
  - Known limitations
  - Migration guide (if applicable)

---

### Phase 7: Git Operations - PRIORITY: HIGH

#### Step 7.1: Commit All Changes
- Use conventional commits
- GPG sign commits

#### Step 7.2: Create PR
- Use gh auth switch for cvsz → policedbc → cvsz workflow
- Get review and approval
- Merge

---

## Execution Order

```
Phase 1 (Linting) → Phase 2 (Security) → Phase 3 (Shellcheck)
    ↓
Phase 4 (Quality) → Phase 5 (Testing) → Phase 6 (Docs)
    ↓
Phase 7 (Git/PR)
```

## Parallelization Opportunities

Within each phase, individual file fixes can be parallelized:
- Phase 1: Each file fix is independent
- Phase 2: Each security fix is independent
- Phase 4: Type hints, docstrings, error handling can be parallel

## Rollback Strategy

Each phase commits separately. If a phase introduces regressions:
1. Revert that phase's commit
2. Fix and re-apply

## Success Criteria

- [ ] `ruff check .` → 0 errors
- [ ] `shellcheck scripts/*.sh` → 0 errors/warnings
- [ ] `bandit -r services/ scripts/` → 0 medium/high issues
- [ ] `mypy services/ scripts/` → 0 errors
- [ ] `pytest tests/` → 226+ tests passing
- [ ] Coverage > 90%
- [ ] All documentation synced
- [ ] FINAL-REPORT.md created and comprehensive
- [ ] PR created, reviewed, approved, merged