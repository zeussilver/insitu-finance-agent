---
phase: 03-refiner-pipeline-repair
plan: 02
subsystem: evolution
tags: [refiner, error-handling, backoff, talib-avoidance, patch-history]

# Dependency graph
requires:
  - phase: 03-01
    provides: text_response extraction, error patterns with talib guidance
provides:
  - MODULE_REPLACEMENT_GUIDE constant with pandas/numpy examples
  - UNFIXABLE_ERRORS set for fail-fast detection
  - Enhanced generate_patch() with history and module guidance
  - Enhanced refine() with exponential backoff and fail-fast
affects: [04-evaluation, benchmarks]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module replacement guide pattern for import error handling"
    - "Patch history tracking to avoid repeating failed approaches"
    - "Exponential backoff (1s, 2s, 4s) for rate limit protection"
    - "Fail-fast pattern for unfixable errors"

key-files:
  created: []
  modified:
    - fin_evo_agent/src/evolution/refiner.py

key-decisions:
  - "MODULE_REPLACEMENT_GUIDE at module level for reuse across methods"
  - "UNFIXABLE_ERRORS includes security violations and external failures"
  - "Exponential backoff starts at 1s (2^0) after first failure"
  - "Patch history tracks both approach and failure_reason for context"

patterns-established:
  - "Module guidance: Include replacement examples for forbidden imports"
  - "History tracking: Pass failed attempts to LLM to avoid repetition"
  - "Fail-fast: Check unfixable errors before expensive operations"

# Metrics
duration: 3min
completed: 2026-02-02
---

# Phase 3 Plan 02: Refiner Enhancement Summary

**Enhanced refiner with talib avoidance guide, patch history tracking, exponential backoff, and fail-fast for unfixable errors**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-02T10:00:00Z
- **Completed:** 2026-02-02T10:03:00Z
- **Tasks:** 5
- **Files modified:** 1

## Accomplishments
- Added MODULE_REPLACEMENT_GUIDE with pandas/numpy implementations for RSI, MACD, Bollinger Bands
- Added UNFIXABLE_ERRORS set (7 patterns) for security violations, timeouts, API errors
- Enhanced generate_patch() with attempt/previous_patches parameters and "do not modify tests" instruction
- Enhanced refine() with exponential backoff (1s, 2s, 4s) between retries
- Implemented fail-fast logic that aborts immediately on unfixable errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add MODULE_REPLACEMENT_GUIDE constant** - `2ece95e` (feat)
2. **Task 2: Add UNFIXABLE_ERRORS constant** - `358b5e9` (feat)
3. **Task 3: Add time import** - `2a218aa` (chore)
4. **Task 4: Enhance generate_patch() with module guide and history** - `92ad0b0` (feat)
5. **Task 5: Enhance refine() with backoff, history, and fail-fast** - `b74ea50` (feat)

## Files Created/Modified
- `fin_evo_agent/src/evolution/refiner.py` - Enhanced with MODULE_REPLACEMENT_GUIDE, UNFIXABLE_ERRORS, improved generate_patch() and refine() methods

## Decisions Made
- MODULE_REPLACEMENT_GUIDE placed at module level (not inside class) for potential reuse
- UNFIXABLE_ERRORS includes both specific patterns ("SecurityException") and message substrings ("Unallowed import")
- Exponential backoff formula: 2^(attempt-1) gives 1s, 2s, 4s delays
- Patch history stored as list of dicts with 'approach' and 'failure_reason' keys

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Initial MODULE_REPLACEMENT_GUIDE placement caused IndentationError (constant was added inside class but `__init__` retained class indentation) - fixed by moving constant to module level before class definition

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 3 complete: Refiner pipeline now has proper error guidance, backoff, and fail-fast
- Ready for Phase 4: Evaluation suite can now test refined error handling
- All success criteria met:
  - [x] MODULE_REPLACEMENT_GUIDE with talib avoidance
  - [x] UNFIXABLE_ERRORS for fail-fast
  - [x] generate_patch() with attempt/previous_patches params
  - [x] "do not modify tests" instruction in patch prompt
  - [x] Exponential backoff in refine()
  - [x] Patch history tracking

---
*Phase: 03-refiner-pipeline-repair*
*Completed: 2026-02-02*
