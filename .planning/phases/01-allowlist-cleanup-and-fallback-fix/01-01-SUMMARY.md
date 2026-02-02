---
phase: 01-allowlist-cleanup-and-fallback-fix
plan: 01
status: complete
subsystem: security
tags: [allowlist, talib, ast-security, llm-prompt]
dependency-graph:
  requires: []
  provides: [talib-free-allowlist, consistent-allowed-modules]
  affects: [01-02, phase-02]
tech-stack:
  added: []
  patterns: [allowlist-consistency-between-executor-and-prompt]
key-files:
  created: []
  modified:
    - fin_evo_agent/src/core/llm_adapter.py
decisions:
  - id: D-0101-01
    description: "talib already absent from executor.py ALLOWED_MODULES; only llm_adapter.py SYSTEM_PROMPT needed editing"
metrics:
  duration: 2m 22s
  completed: 2026-02-02
---

# Phase 01 Plan 01: Remove talib from Allowlists Summary

Removed all references to `talib` from the LLM system prompt so the allowed-imports list in `llm_adapter.py` matches the `ALLOWED_MODULES` set in `executor.py`. This prevents the LLM from generating tools that import talib (which is not installed), eliminating runtime `ModuleNotFoundError` failures.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Remove talib from ALLOWED_MODULES in executor.py | (no-op, already absent) | fin_evo_agent/src/core/executor.py |
| 2 | Remove talib from SYSTEM_PROMPT in llm_adapter.py | 358b7cd | fin_evo_agent/src/core/llm_adapter.py |
| 3 | Verify security check output | (verification only) | - |

## Deliverables

- `fin_evo_agent/src/core/llm_adapter.py` -- SYSTEM_PROMPT line 23 no longer lists `talib` as an allowed import
- `fin_evo_agent/src/core/executor.py` -- ALLOWED_MODULES confirmed talib-free (was already correct)
- Both files now agree on the same allowed module set: pandas, numpy, datetime, json, math, decimal, collections, re, yfinance, pathlib (plus typing, hashlib in executor only)

## Verification Results

- `python3 -c "from src.core.executor import ToolExecutor; assert 'talib' not in ToolExecutor.ALLOWED_MODULES"` -- PASS
- `python3 -c "from src.core.llm_adapter import SYSTEM_PROMPT; assert 'talib' not in SYSTEM_PROMPT"` -- PASS
- `python3 main.py --security-check` -- PASS, no talib in output
- AST security check blocks `import talib` with "Unallowed import: talib" -- PASS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Recreated virtual environment**

- **Found during:** Task 3
- **Issue:** The `.venv` had stale paths from a previous project location (referenced `/week3/` instead of `/2026-1-week3/`). `pip` and `python3` shims pointed to nonexistent paths.
- **Fix:** Deleted and recreated the venv with `python3 -m venv .venv && pip install -r requirements.txt`
- **Files modified:** `.venv/` (not tracked in git)

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-0101-01 | Task 1 was a no-op (talib already removed from executor.py) | The ALLOWED_MODULES set in executor.py had already been updated in a prior session; only the SYSTEM_PROMPT in llm_adapter.py still contained talib |

## Issues

- None. Plan executed cleanly.

## Next Phase Readiness

Plan 01-02 (fallback fix for mock LLM) can proceed. No blockers introduced by this plan.
