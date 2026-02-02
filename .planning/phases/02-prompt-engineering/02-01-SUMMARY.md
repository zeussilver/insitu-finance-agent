---
phase: 02-prompt-engineering
plan: 01
subsystem: llm
tags: [prompt-engineering, system-prompt, pure-function, pandas, numpy]

# Dependency graph
requires:
  - phase: 01-allowlist-cleanup
    provides: talib removed from ALLOWED_MODULES in executor.py
provides:
  - Enhanced SYSTEM_PROMPT with pure function pattern
  - Data-as-arguments instruction for generated tools
  - FORBIDDEN imports list (yfinance, akshare, talib, requests, urllib)
  - Return type guidance (float/dict/bool)
  - Example pattern for LLM to follow
affects: [phase-02-plan-02, benchmark-evaluation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure function pattern: accept data as arguments, not fetch internally"
    - "Return type conventions: float for single values, dict for multiple, bool for conditions"
    - "FORBIDDEN imports enforcement via prompt (not just executor)"

key-files:
  created: []
  modified:
    - fin_evo_agent/src/core/llm_adapter.py

key-decisions:
  - "Added explicit FORBIDDEN list in SYSTEM_PROMPT (defense in depth with executor ALLOWED_MODULES)"
  - "Included complete example in SYSTEM_PROMPT to guide LLM by demonstration"
  - "Removed pathlib from allowed imports (not needed for pure calculation tools)"

patterns-established:
  - "Data-as-arguments: prices: list parameter signature"
  - "Return types: float for scalars, dict for multi-value, bool for conditions"
  - "Inline test data: hardcoded lists in if __name__ == '__main__' block"

# Metrics
duration: 2min
completed: 2026-02-02
---

# Phase 2 Plan 01: Enhance SYSTEM_PROMPT Summary

**Enhanced SYSTEM_PROMPT with pure function pattern: data as arguments, pandas/numpy-only calculations, typed returns, and complete example**

## Performance

- **Duration:** 1m 49s
- **Started:** 2026-02-02T08:43:37Z
- **Completed:** 2026-02-02T08:45:26Z
- **Tasks:** 2 (1 implementation, 1 verification)
- **Files modified:** 1

## Accomplishments
- SYSTEM_PROMPT now enforces pure function pattern with explicit data-as-arguments instruction
- FORBIDDEN imports list added: yfinance, akshare, talib, requests, urllib
- Return type guidance added: float for single values, dict for multiple values, bool for conditions
- Complete example of correct pattern included to guide LLM by demonstration
- All 6 verification checks passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance SYSTEM_PROMPT with pure function pattern instructions** - `3f0b6b0` (feat)
2. **Task 2: Verify generated tool patterns (mock mode)** - No commit (verification only)

## Files Created/Modified
- `fin_evo_agent/src/core/llm_adapter.py` - Enhanced SYSTEM_PROMPT from 16 lines to 55 lines with pure function pattern instructions and example

## Decisions Made
- Added explicit FORBIDDEN list in SYSTEM_PROMPT as defense in depth (executor ALLOWED_MODULES is the hard block, prompt is soft guidance for LLM)
- Included complete working example in SYSTEM_PROMPT to guide LLM by demonstration rather than just rules
- Removed pathlib from allowed imports list (not needed for pure calculation tools)
- Kept yfinance in executor ALLOWED_MODULES for bootstrap tools, but added to FORBIDDEN in SYSTEM_PROMPT for generated tools

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None - verification commands initially failed due to missing venv activation, resolved by activating virtual environment.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SYSTEM_PROMPT enhancement complete
- Ready for real LLM testing (requires API_KEY)
- Benchmark evaluation will validate the prompt changes improve tool generation quality

---
*Phase: 02-prompt-engineering*
*Completed: 2026-02-02*
