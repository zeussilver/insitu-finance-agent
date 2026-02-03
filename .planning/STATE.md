# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-31)

**Core value:** Benchmark task success rate >= 80%
**Current focus:** Phase 5 - Verification Gap Closure in progress.

## Current Position

Phase: 5 of 5 (Verification Gap Closure)
Plan: 2 of 4 in current phase
Status: In progress - 05-02 complete (schema fields for tool matching)
Last activity: 2026-02-03 - Completed 05-02-PLAN.md (schema fields)

Progress: [████████░░] 82%

## Phase 4 Verification Results

**Benchmark Run:** verification_phase4.json (2026-02-03)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Pass Rate | >= 80% | 60% (12/20) | NOT MET |
| Regressions | 0 | 5 | NOT MET |
| Security Block | 100% | 20% (1/5) | NOT MET |

**Root Causes Identified:**
1. **Security**: LLM generates dangerous code that passes AST check (4/5 attacks bypass)
2. **Fetch Pattern**: Pure function pattern conflicts with fetch tasks that need yfinance
3. **Tool Matching**: Keyword-based matching reuses wrong tools for similar-sounding tasks

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 2m 20s
- Total execution time: ~0.35 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-allowlist-cleanup | 2/2 | 4m 27s | 2m 14s |
| 02-prompt-engineering | 1/1 | 1m 49s | 1m 49s |
| 03-refiner-pipeline | 2/2 | 4m 44s | 2m 22s |
| 04-regression-verification | 2/2 | ~9m | ~4m 30s |
| 05-verification-gap-closure | 2/4 | ~4m | ~2m |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Remove talib from allowlist instead of installing C library
- [Init]: Fix mock LLM to fail on timeout instead of producing wrong tools
- [Init]: Guide LLM to use pandas/numpy only for technical indicators
- [01-01]: talib was already absent from executor.py ALLOWED_MODULES; only SYSTEM_PROMPT in llm_adapter.py needed editing
- [01-02]: API errors return error dict (code_payload=None, text_response with error msg) instead of falling back to mock
- [01-02]: Mock only activates when API_KEY env var is unset, not on API errors/timeouts
- [02-01]: Added explicit FORBIDDEN list in SYSTEM_PROMPT (defense in depth with executor ALLOWED_MODULES)
- [02-01]: Included complete example in SYSTEM_PROMPT to guide LLM by demonstration
- [02-01]: Removed pathlib from allowed imports (not needed for pure calculation tools)
- [03-01]: Prioritize text_response over thought_trace in analyze_error() for more actionable error analysis
- [03-01]: Truncate text_response at 2000 chars to prevent prompt bloat in repair loop
- [03-02]: MODULE_REPLACEMENT_GUIDE at module level for reuse across methods
- [03-02]: UNFIXABLE_ERRORS includes security violations and external failures
- [03-02]: Exponential backoff starts at 1s (2^0) after first failure
- [03-02]: Patch history tracks both approach and failure_reason for context
- [04-01]: Use raw ANSI codes for colors (no colorama dependency)
- [04-01]: Three-state result classification (pass/fail/error) to distinguish API errors
- [04-01]: Static baseline.json file with 13 task IDs for regression detection
- [04-02]: **DATA SOURCE CHANGE**: Project now uses yfinance instead of akshare
- [04-02]: CLAUDE.md updated to reflect yfinance as the data source
- [05-02]: Use ALTER TABLE for SQLite migration (create_all doesn't add columns to existing tables)
- [05-02]: Store input_requirements as JSON TEXT column for SQLite compatibility
- [05-02]: Indexes on category/indicator only created on fresh databases (SQLite limitation)

### Pending Todos

None.

### Blockers/Concerns

**Phase 5 progress:**
1. [DONE - 05-01] Security AST check improvements
2. [IN PROGRESS] Fetch task pattern (allow yfinance calls in generated tools for fetch tasks)
3. [DONE - 05-02] Tool matching schema fields added
4. [PENDING] Tool matching query logic in run_eval.py
5. [DONE - 05-01] pathlib removed from ALLOWED_MODULES

## Session Continuity

Last session: 2026-02-03T04:52:52Z
Stopped at: Completed 05-02-PLAN.md (schema fields for tool matching)
Resume file: None

## Phase 5 Plans

| Plan | Wave | Files | Status |
|------|------|-------|--------|
| 05-01 | 1 | executor.py, llm_adapter.py | Complete |
| 05-02 | 1 | models.py | Complete |
| 05-03 | 2 | synthesizer.py | Pending |
| 05-04 | 2 | run_eval.py | Pending |

## Phase 5 Completed Enhancements

**05-01: Security Improvements**
- Expanded BANNED_MODULES with pty, tty, fcntl, posix, etc.
- Expanded BANNED_CALLS with hasattr, open, breakpoint, etc.
- Added BANNED_ATTRIBUTES for object introspection blocking
- Added encoding normalization to prevent PEP-263 bypass
- Added security violation logging
- Removed pathlib from ALLOWED_MODULES
- Added security warnings to LLM SYSTEM_PROMPT

**05-02: Schema Fields for Tool Matching**
- Added category field (indexed) for task type classification
- Added indicator field (indexed) for technical indicator type
- Added data_type field for data requirements
- Added input_requirements field (JSON) for required parameters
- Database migration preserves existing tools
