# Roadmap: Yunjue Agent Benchmark Fix Sprint

## Overview

This sprint fixes 4 root causes preventing the benchmark from reaching 80% task success rate. The work progresses from removing incorrect allowlist entries and fallback behavior, through enhancing LLM prompts for correct tool generation, to fixing the refiner pipeline so failed tools get properly repaired. A final regression verification phase ensures the 13 currently-passing tasks remain intact.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Allowlist Cleanup & Fallback Fix** - Remove talib from the system and stop mock fallback on timeout
- [x] **Phase 2: Prompt Engineering for Correct Tool Generation** - Guide LLM to produce self-contained tools with correct data patterns
- [x] **Phase 3: Refiner Pipeline Repair** - Fix error analysis and patch generation so the repair loop works
- [x] **Phase 4: Regression Verification** - Confirm all fixes work together without breaking existing passes (ISSUES FOUND)
- [ ] **Phase 5: Verification Gap Closure** - Fix security blocking, fetch task pattern, and tool matching issues identified in Phase 4

## Phase Details

### Phase 1: Allowlist Cleanup & Fallback Fix
**Goal**: The system no longer references talib anywhere, and LLM timeouts produce honest failures instead of silently returning wrong tools
**Depends on**: Nothing (first phase)
**Requirements**: PROMPT-01, PROMPT-02, MOCK-01, MOCK-02
**Success Criteria** (what must be TRUE):
  1. Running `python main.py --security-check` shows `talib` is NOT in ALLOWED_MODULES
  2. SYSTEM_PROMPT in `llm_adapter.py` does not mention `talib` in the allowed imports list
  3. When the LLM API times out, the system returns an error result (not mock-generated RSI code)
  4. Mock LLM only activates when `API_KEY` environment variable is unset, not on API errors or timeouts
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Remove talib from ALLOWED_MODULES and SYSTEM_PROMPT
- [x] 01-02-PLAN.md — Fix mock LLM fallback to only activate without API key

### Phase 2: Prompt Engineering for Correct Tool Generation
**Goal**: The LLM generates self-contained financial tools that accept data as arguments, use only pandas/numpy for calculations, and return correctly typed results
**Depends on**: Phase 1 (talib must be removed before adding pandas/numpy-only guidance)
**Requirements**: PROMPT-03, PROMPT-04, DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. Running a calculation task (e.g., "calc RSI") produces a tool that accepts `prices: list` as a function parameter (not fetching data internally)
  2. Generated tools use only pandas/numpy for technical indicator calculations (no `import talib`, no `import yfinance` inside the tool)
  3. Generated tools return typed results: float for numeric indicators, dict for structured output, bool for boolean checks
  4. The `if __name__ == '__main__'` test block in generated tools uses inline sample data (not API calls)
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Enhance SYSTEM_PROMPT with pure function pattern (data-as-arguments, pandas/numpy-only, return types, inline test data)

### Phase 3: Refiner Pipeline Repair
**Goal**: When a generated tool fails verification, the refiner correctly analyzes the error and produces a working patch
**Depends on**: Phase 2 (prompt improvements reduce error volume; refiner must handle remaining failures)
**Requirements**: REFNR-01, REFNR-02, REFNR-03, REFNR-04
**Success Criteria** (what must be TRUE):
  1. `generate_tool_code()` return dict includes `text_response` key containing the LLM's non-code analysis text
  2. Refiner's `analyze_error()` extracts root cause from `text_response` (not just `thought_trace`) when analyzing errors
  3. Errors of type `ModuleNotFoundError`, `ImportError`, and `AssertionError` are correctly classified (not "UnknownError")
  4. Refiner's patch prompt explicitly instructs the LLM to avoid talib and use pandas/numpy only
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Fix generate_tool_code return value and error analysis extraction
- [x] 03-02-PLAN.md — Add missing error patterns and talib-avoidance instruction to patch prompt

### Phase 4: Regression Verification
**Goal**: The complete fix set achieves >=80% benchmark success rate without breaking any currently-passing tasks
**Depends on**: Phase 3 (all fixes must be in place before verification)
**Requirements**: REGR-01, REGR-02
**Success Criteria** (what must be TRUE):
  1. Running `python benchmarks/run_eval.py --agent evolving` produces a task success rate >= 80% (16/20 or better)
  2. All 13 currently-passing tasks (8 fetch + 5 calc/composite) still pass
  3. Running `python benchmarks/run_eval.py --security-only` produces 100% security block rate
  4. At least 3 of the 7 previously-failing tasks now pass (minimum improvement to reach 80%)
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Enhance run_eval.py with JSON output, colors, baseline comparison, registry clearing
- [x] 04-02-PLAN.md — Run full benchmark verification and confirm targets

**Verification Results (2026-02-03):**
- Pass Rate: 60% (12/20) — TARGET NOT MET (need 80%)
- Regressions: 5 — TARGET NOT MET (need 0)
- Security Block: 20% (1/5) — TARGET NOT MET (need 100%)

Issues identified and documented for Phase 5.

### Phase 5: Verification Gap Closure
**Goal**: Fix the three root causes identified in Phase 4 verification to achieve 80% pass rate with proper security blocking
**Depends on**: Phase 4 (issues must be diagnosed before fixing)
**Requirements**: REGR-01, REGR-02 (still pending), plus new requirements for fixes
**Success Criteria** (what must be TRUE):
  1. Security AST check blocks all 5 security test cases (currently 1/5)
  2. Fetch tasks use yfinance to actually retrieve data (not pure functions expecting data as arguments)
  3. Tool matching uses structured schema matching, not just keyword matching
  4. Pass rate >= 80% (16/20)
  5. Zero regressions on baseline tasks
  6. CI pipeline catches regressions automatically
**Plans**: 12 plans (6 original + 3 round 1 gap closure + 3 round 2 gap closure)

Plans:
- [x] 05-01-PLAN.md — Expand AST security blocklists (block introspection chains, getattr, encoding bypasses)
- [x] 05-02-PLAN.md — Add schema fields to ToolArtifact model (category, indicator, data_type, input_requirements)
- [x] 05-03-PLAN.md — Implement schema-based tool matching in registry and synthesizer
- [x] 05-04-PLAN.md — Create TaskExecutor for bootstrap tool chaining (fetch + calc pattern)
- [x] 05-05-PLAN.md — Update run_eval.py to use TaskExecutor and schema matching
- [x] 05-06-PLAN.md — Create GitHub Actions CI workflow for regression testing
- [x] 05-07-PLAN.md — Fix extract_symbol() to not match "GET" as ticker symbol
- [x] 05-08-PLAN.md — Add simple fetch query handling directly from OHLCV data
- [x] 05-09-PLAN.md — Add security logging to eval and run verification benchmark
- [ ] 05-10-PLAN.md — Fix UNSUPPORTED_FETCH_PATTERNS ValueError (return None instead of raise)
- [ ] 05-11-PLAN.md — Fix symbol extraction "DOW" in "drawdown" bug (word boundary matching)
- [ ] 05-12-PLAN.md — Add yfinance retry mechanism with exponential backoff

**Issues to Address (Original):**
1. **Security**: LLM generates dangerous code that passes AST check (4/5 attacks bypass)
2. **Fetch Pattern**: Pure function pattern conflicts with tasks that need to fetch data via yfinance
3. **Tool Matching**: Keyword-based `_infer_tool_name()` matches wrong tools to similar-sounding tasks
4. **CI**: No automated regression protection

**Post-Verification Gaps (from 05-VERIFICATION.md):**
1. **Symbol Extraction Bug**: extract_symbol() matches "GET" as ticker, causing fetch_004/005 regressions
2. **Argument Mismatch**: Generated tools expect different arg formats than TaskExecutor provides
3. **Security Logging**: Violations not logged during security-only evaluation
4. **Pass Rate Regression**: Phase 5 made pass rate worse (55% vs 60% in Phase 4)

**Re-Verification Gaps (from 05-RE-VERIFICATION.md - Round 2):**
1. **UNSUPPORTED_FETCH_PATTERNS ValueError**: _handle_simple_fetch() raises ValueError, breaking task execution
2. **"DOW" in "drawdown"**: INDEX_SYMBOL_MAPPING matches "DOW" substring, causing calc_007 to fetch ^DJI instead of MSFT
3. **yfinance Network Resilience**: No retry mechanism when yfinance returns no data

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Allowlist Cleanup & Fallback Fix | 2/2 | Complete | 2026-02-02 |
| 2. Prompt Engineering for Correct Tool Generation | 1/1 | Complete | 2026-02-02 |
| 3. Refiner Pipeline Repair | 2/2 | Complete | 2026-02-02 |
| 4. Regression Verification | 2/2 | Complete (Issues Found) | 2026-02-03 |
| 5. Verification Gap Closure | 9/12 | Gap Closure Round 2 | - |
