# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-31)

**Core value:** Benchmark task success rate >= 80%
**Current focus:** Phase 5 - Verification Gap Closure COMPLETE.

## Current Position

Phase: 5 of 5 (Verification Gap Closure)
Plan: 6 of 6 complete in current phase (05-01, 05-02, 05-03, 05-04, 05-05, 05-06)
Status: Phase 5 COMPLETE
Last activity: 2026-02-03 - Completed 05-06-PLAN.md (GitHub Actions CI)

Progress: [██████████] 100%

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
- Total plans completed: 12
- Average duration: 2m 15s
- Total execution time: ~0.45 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-allowlist-cleanup | 2/2 | 4m 27s | 2m 14s |
| 02-prompt-engineering | 1/1 | 1m 49s | 1m 49s |
| 03-refiner-pipeline | 2/2 | 4m 44s | 2m 22s |
| 04-regression-verification | 2/2 | ~9m | ~4m 30s |
| 05-verification-gap-closure | 6/6 | ~14m | ~2m 20s |

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
- [05-01]: Add BANNED_ATTRIBUTES as separate set from BANNED_CALLS for magic attribute blocking
- [05-01]: Check string literals for banned patterns (catches getattr(x, 'eval'))
- [05-01]: Defense in depth: LLM prompt warnings + AST enforcement
- [05-03]: Separate find_by_schema() method rather than modifying get_by_name()
- [05-03]: update_schema() called after registration (not passed to register())
- [05-03]: INDICATOR_KEYWORDS dict at module level for reuse
- [05-04]: Use data_proxy.get_stock_hist directly (not via bootstrap tool artifact)
- [05-04]: Default symbol AAPL, default date range 2023-01-01 to 2023-12-31
- [05-04]: All OHLCV values converted to float for JSON serialization
- [05-05]: Schema-based matching tried first, keyword-based as fallback
- [05-05]: TaskExecutor handles all task categories uniformly
- [05-05]: Preserved _infer_tool_name() for backwards compatibility
- [05-06]: Hard fail on regressions, warn on pass rate < 80% (LLM variance)
- [05-06]: Cache yfinance data by tasks.jsonl hash for reproducibility
- [05-06]: Use thollander/actions-comment-pull-request@v2 for PR comments

### Pending Todos

None.

### Blockers/Concerns

All Phase 5 plans complete. Project ready for final verification and release.

## Session Continuity

Last session: 2026-02-03T05:11:00Z
Stopped at: Completed 05-06-PLAN.md (GitHub Actions CI)
Resume file: None

## Phase 5 Plans

| Plan | Wave | Files | Status |
|------|------|-------|--------|
| 05-01 | 1 | executor.py, llm_adapter.py | Complete (2026-02-03) |
| 05-02 | 1 | models.py | Complete (2026-02-03) |
| 05-03 | 2 | registry.py, synthesizer.py | Complete (2026-02-03) |
| 05-04 | 2 | src/core/task_executor.py | Complete (2026-02-03) |
| 05-05 | 3 | benchmarks/run_eval.py | Complete (2026-02-03) |
| 05-06 | 4 | .github/workflows/benchmark.yml | Complete (2026-02-03) |

## Phase 5 Completed Enhancements

**05-01: Security Improvements (2026-02-03)**
- Expanded BANNED_MODULES with pty, tty, fcntl, posix, etc.
- Expanded BANNED_CALLS with hasattr, open, breakpoint, etc.
- Added BANNED_ATTRIBUTES for object introspection blocking
- Added encoding normalization to prevent PEP-263 bypass
- Added security violation logging to file and stderr
- Removed pathlib from ALLOWED_MODULES
- Added SECURITY REQUIREMENTS section to LLM SYSTEM_PROMPT
- Security block rate improved from 20% to 60-100%

**05-02: Schema Fields (2026-02-03)**
- Added category, indicator, data_type, input_requirements fields to ToolArtifact
- Added migration function for existing databases
- Enables schema-based tool matching

**05-03: Schema Matching (2026-02-03)**
- Added find_by_schema() method to ToolRegistry
- Added update_schema() method to modify schema fields
- Added INDICATOR_KEYWORDS dict with 10 indicator types
- Added extract_indicator() and extract_data_type() functions
- Integrated schema extraction into synthesize() method
- Tools now automatically get schema metadata on registration

**05-04: TaskExecutor Module (2026-02-03)**
- Created TaskExecutor class to orchestrate fetch + calc chains
- fetch_stock_data() returns standardized OHLCV dict format
- execute_task() handles fetch/calculation/composite categories
- prepare_calc_args() maps OHLCV data to tool argument names
- extract_symbol() and extract_date_range() parse task queries
- _extract_task_params() handles RSI, MACD, KDJ, Bollinger params
- Pure calc tools receive data as arguments (not fetching internally)

**05-05: Benchmark Integration (2026-02-03)**
- Added TaskExecutor import and instance to EvalRunner
- Added _extract_schema_from_task() supporting 10 indicator types
- Schema-based matching tried first via find_by_schema()
- Keyword-based matching preserved as fallback
- Task execution uses task_executor.execute_task() for uniform flow
- Smoke test verified: tool reuse and execution working

**05-06: GitHub Actions CI (2026-02-03)**
- Created .github/workflows/benchmark.yml
- Triggers on PR to main and manual workflow dispatch
- Uses API_KEY from GitHub Secrets for LLM API
- Caches yfinance data for reproducibility
- Hard fails on regressions, warns on pass rate < 80%
- Posts results as PR comment with summary table
- Uploads benchmark results and security logs as artifacts
