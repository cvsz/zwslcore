# Comprehensive Enterprise-Grade Implementation Execution Plan

## Objective
Transform zwslcore into a 100% complete, enterprise-grade, production-ready system with:
- Zero linting errors (ruff, shellcheck)
- Zero security findings (bandit)
- Full type safety (mypy strict mode)
- 100% test coverage with all tests passing
- Complete documentation sync
- Final comprehensive report (FINAL-REPORT.md)
- GPG-signed commits, PR creation, review/approve/merge workflow

## Phase Structure

### Phase 1: Linting Fixes (Ruff) - HIGH PRIORITY
**Target**: 213 ruff errors → 0 errors

#### 1.1 Complexity Issues (PLR0912, PLR0915, PLR0913, PLR0911, PLR0917)
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
- `scripts/backup.py:494` - Too many arguments (7>5)
- `scripts/bootstrap.py:88` - Too many arguments (6>5)
- `scripts/capacity.py:142` - TRY004
- `scripts/engineer.py:142` - Too many statements (136>50)
- `scripts/engineer.py:360` - Too many returns (75>6), branches (112>12), statements (348>50)
- `scripts/engineer.py:376` - B007 unused loop variable
- `scripts/engineer.py:606,845,849,859,865,871,874,877,881` - TRY301
- `scripts/engineering-metrics.py:1` - N999 invalid module name
- `scripts/github_admin.py:113` - Too many branches (18>12)
- `scripts/model_manifest.py:38` - PLC0415 import not at top
- `scripts/models-dev.py:1` - N999 invalid module name
- `scripts/models-dev.py:73` - Too many returns (8>6), branches (14>12)
- `scripts/restore.py:84,163,234` - PTH101 os.chmod
- `scripts/restore.py:197,199,201,205,208` - TRY301
- `scripts/restore.py:235` - TRY300 else block
- `scripts/restore.py:236` - TRY203 re-raise
- `scripts/sync-free-models.py:1` - N999 invalid module name
- `services/engineering/agents.py:40,73` - RUF005 iterable unpacking
- `services/engineering/agents.py:93` - Too many branches (19>12), statements (52>50)
- `services/engineering/change_snapshot.py:119,156` - PLW1510 subprocess.check
- `services/engineering/change_snapshot.py:209` - PTH105 Path.replace
- `services/engineering/continuous.py:40` - ARG005 unused lambda
- `services/engineering/continuous.py:60` - PLR2004 magic value 64
- `services/engineering/continuous.py:84,96` - Too many statements
- `services/engineering/delegation.py:47` - SIM108 ternary
- `services/engineering/delegation.py:55` - TRY004
- `services/engineering/delegation.py:91` - Too many args (7>5)
- `services/engineering/evidence.py:175` - PLR1714 merge comparisons
- `services/engineering/evidence.py:233` - PTH105 Path.replace
- `services/engineering/hardware.py:25,33,45,47,62,66,154,156` - PLR2004 magic values
- `services/engineering/hardware.py:108,124,133` - PLW1510 subprocess.check
- `services/engineering/lease.py:50` - Too many args (7>5)
- `services/engineering/lease.py:121` - TRY300 else block
- `services/engineering/ledger.py:80` - PTH105 Path.replace
- `services/engineering/ledger.py:150` - Too many args (7>5)
- `services/engineering/ledger.py:327` - Too many branches (15>12)
- `services/engineering/loop.py:11` - UP042 str+Enum
- `services/engineering/loop.py:58` - Too many args (6>5)
- `services/engineering/loop.py:75` - Too many branches (14>12)
- `services/engineering/mcp.py:52` - Too many branches (13>12)
- `services/engineering/mcp.py:90` - PLR2004 magic value 300
- `services/engineering/mcp.py:171` - TRY301
- `services/engineering/mcp.py:226` - SIM105 contextlib.suppress
- `services/engineering/models.py:10,23,30` - UP042 str+Enum
- `services/engineering/observability.py:115` - Too many args (11>5)
- `services/engineering/prometheus.py:195,213` - TRY004
- `services/engineering/prometheus.py:219` - Too many returns (9>6)
- `services/engineering/prometheus.py:275` - T201 print
- `services/engineering/prometheus.py:276` - SIM105 contextlib.suppress
- `services/engineering/prometheus.py:289` - PLR2004 magic value 65535
- `services/engineering/runtime.py:75` - TRY300 else block
- `services/engineering/runtime.py:82` - PLR2004 magic values 500, 599
- `services/engineering/runtime.py:219` - RUF012 mutable default
- `services/engineering/runtime.py:240` - Too many args (8>5)
- `services/engineering/runtime.py:258` - ARG005 unused lambda
- `services/engineering/runtime.py:295` - Too many args (7>5), branches (23>12), statements (196>50)
- `services/engineering/runtime.py:607,634` - TRY301

#### 1.2 Mutable Default Values (RUF012)
- `services/engineering/runtime.py:220` - EDIT_RESPONSE_SCHEMA class attribute
- `services/engineering/snapshot.py:10,14,17` - EXCLUDED_DIRS, SECRET_NAMES, SECRET_SUFFIXES

#### 1.3 Exception Types (TRY004)
- `services/engineering/prometheus.py:196,214` - Use TypeError instead of ValueError
- `services/engineering/runtime.py:899,902,906,910` - Use TypeError instead of ValueError
- `services/engineering/delegation.py:55` - Use TypeError
- `services/engineering/prometheus.py:195,213` - Use TypeError

#### 1.4 TRY300/TRY301 Issues
- `services/engineering/mcp.py:172` - Abstract raise to inner function
- `services/engineering/runtime.py:609,636,689` - Abstract raises, move to else blocks
- `services/model_catalog/models_dev.py:186` - Move to else block
- `services/engineering/lease.py:121` - Move to else block
- `services/engineering/runtime.py:75` - Move to else block
- `scripts/restore.py:197,199,201,205,208,235,236` - Various TRY300/301

#### 1.5 Magic Values (PLR2004)
- `services/engineering/mcp.py:91` - timeout 300
- `services/engineering/prometheus.py:286` - port 65535
- `services/engineering/runtime.py:83` - HTTP 500, 599
- `services/model_catalog/selector.py:239,243` - RAM thresholds 10, 14
- `services/engineering/continuous.py:60` - magic value 64
- `services/engineering/hardware.py:25,33,45,47,62,66,154,156` - RAM/CPU thresholds
- `services/engineering/prometheus.py:289` - port 65535

#### 1.6 ARG005 Unused Lambda Arguments
- `services/engineering/continuous.py:40` - unused lambda arg
- `services/engineering/runtime.py:258` - unused lambda arg

#### 1.7 PLW1510 subprocess.check=False
- Multiple files in services/engineering, tests/

#### 1.8 PTH105 Path.replace()
- `services/engineering/change_snapshot.py:209` - os.replace → Path.replace
- `services/engineering/evidence.py:233` - os.replace → Path.replace
- `services/engineering/ledger.py:80` - os.replace → Path.replace
- `services/model_catalog/models_dev.py:111` - os.replace → Path.replace

#### 1.9 SIM117 Nested with Statements
- Multiple test files

#### 1.10 E741 Ambiguous Variable Names
- `tests/test_supply_chain_dockerfile.py` - variable `l`

#### 1.11 PLC0415 Top-level Imports
- `tests/test_engineering_metrics.py`, `tests/test_model_inventory.py`
- `scripts/model_manifest.py:38`

#### 1.12 UP042 str+Enum
- `services/engineering/loop.py:11` - WorkKind
- `services/engineering/models.py:10,23,30` - TaskStatus, TaskRisk, PushPolicy
- `services/engineering/loop.py:11` - WorkKind

#### 1.13 N999 Invalid Module Names
- `scripts/engineering-metrics.py` → `engineering_metrics.py`
- `scripts/models-dev.py` → `models_dev.py`
- `scripts/sync-free-models.py` → `sync_free_models.py`

#### 1.14 RUF005 Iterable Unpacking
- `services/engineering/agents.py:40,73`

#### 1.15 RUF012 Mutable Default
- `services/engineering/runtime.py:219` - EDIT_RESPONSE_SCHEMA

#### 1.16 SIM105 contextlib.suppress
- `services/engineering/mcp.py:226`
- `services/engineering/prometheus.py:276`

#### 1.17 SIM108 Ternary Operator
- `services/engineering/delegation.py:47`

#### 1.18 B007 Loop Control Variable
- `scripts/engineer.py:376`

#### 1.19 T201 Print Statement
- `services/engineering/prometheus.py:275`

#### 1.20 PLR1714 Merge Comparisons
- `services/engineering/evidence.py:175`

#### 1.21 PTH101 os.chmod → Path.chmod
- `scripts/restore.py:84,163,234`

### Phase 2: Type Safety (Mypy) - HIGH PRIORITY
**Target**: 0 mypy errors

#### 2.1 Missing Type Annotations
- `services/engineering/mcp.py:178` - Function missing type annotation

#### 2.2 Incompatible Types
- `services/engineering/agents.py:162` - PermissionRule arg type
- `services/engineering/observability.py:159` - Assignment incompatible
- `services/engineering/runtime.py:97` - Incompatible assignment
- `services/engineering/runtime.py:100` - Incompatible assignment
- `services/engineering/runtime.py:174` - sorted type var
- `services/engineering/runtime.py:456` - Union attr None
- `services/engineering/ledger.py:354,361,362,363,364,386,392` - Union attr None
- `services/engineering/ledger.py:484` - Returning Any

#### 2.3 Call Arguments
- `scripts/bootstrap.py:146` - Missing positional args
- `scripts/bootstrap.py:148` - Incompatible arg type
- `scripts/chaos.py:99,102,117,120,329` - Timeout float vs int

#### 2.4 Return Type
- `scripts/backup.py:366,593` - Returning Any, too many args

### Phase 3: Security Fixes (Bandit) - HIGH PRIORITY
**Target**: 0 medium/high security issues

#### 3.1 SQL Injection (B608)
- `scripts/backup.py:105` - f-string in SQL query

#### 3.2 urllib URL Opening (B310)
- `scripts/bootstrap_litellm_admin.py`, `scripts/chaos.py`, `scripts/sync-free-models.py`
- `services/engineering/runtime.py`, `services/model_catalog/models_dev.py`

#### 3.3 Subprocess Issues (B404, B603, B607)
- `scripts/backup.py`, `services/engineering/worktree.py`

#### 3.4 Assert Usage (B101)
- `services/provider/zeaz_provider/resilience.py` (2 locations)

### Phase 4: Shellcheck Fixes - MEDIUM PRIORITY
**Target**: 0 shellcheck issues

#### 4.1 Source File Following
- `scripts/install.sh:354` - source scripts/lib/env.sh
- `scripts/wait-runtime.sh:13` - source scripts/lib/env.sh

### Phase 5: Code Quality Improvements - MEDIUM PRIORITY
- Add missing docstrings
- Improve error messages
- Add comprehensive logging
- Optimize hot paths

### Phase 6: Testing Enhancement - MEDIUM PRIORITY
- Increase coverage to >90%
- Add integration tests
- Add benchmark tests

### Phase 7: Documentation Sync - HIGH PRIORITY
- Update README.md
- Update docs/ architecture.md, development.md, release.md
- Create ADRs (8 ADRs)
- Update CHANGELOG.md
- Update IMPLEMENTATION-SUMMARY.md
- Update AGENTS.md

### Phase 8: Final Report & Git Operations - HIGH PRIORITY
- Generate FINAL-REPORT.md
- GPG-signed commit
- Create PR with gh auth workflow (cvsz → policedbc → cvsz)
- Get review, approval, merge

## Execution Strategy
Each phase will be executed sequentially with verification at each step.
Files within a phase can be parallelized where independent.

## Verification Commands
```bash
# Linting
ruff check .
# Type checking
mypy services/ scripts/
# Security
bandit -r services/ scripts/
# Shellcheck
shellcheck scripts/*.sh
# Tests
pytest tests/ -v
# Coverage
pytest --cov=services --cov=scripts tests/
```

## Dependencies Between Phases
1. Phase 1 must complete before Phase 2 (linting fixes may affect types)
2. Phase 2 must complete before Phase 3 (type fixes may affect security patterns)
3. Phase 3, 4 can run in parallel after Phase 2
4. Phase 5, 6 after Phase 3, 4
5. Phase 7 after Phase 5, 6
6. Phase 8 after Phase 7

## Rollback Strategy
Each phase commits separately with conventional commits. If regression:
1. `git revert <commit>`
2. Fix and re-apply