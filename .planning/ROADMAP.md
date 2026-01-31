# Roadmap: Yunjue Agent Benchmark Fix Sprint

## Overview

This sprint fixes 4 root causes preventing the benchmark from reaching 80% task success rate. The work progresses from removing incorrect allowlist entries and fallback behavior, through enhancing LLM prompts for correct tool generation, to fixing the refiner pipeline so failed tools get properly repaired. A final regression verification phase ensures the 13 currently-passing tasks remain intact.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Allowlist Cleanup & Fallback Fix** - Remove talib from the system and stop mock fallback on timeout
- [ ] **Phase 2: Prompt Engineering for Correct Tool Generation** - Guide LLM to produce self-contained tools with correct data patterns
- [ ] **Phase 3: Refiner Pipeline Repair** - Fix error analysis and patch generation so the repair loop works
- [ ] **Phase 4: Regression Verification** - Confirm all fixes work together without breaking existing passes

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
- [ ] 01-01-PLAN.md — Remove talib from ALLOWED_MODULES and SYSTEM_PROMPT
- [ ] 01-02-PLAN.md — Fix mock LLM fallback to only activate without API key

### Phase 2: Prompt Engineering for Correct Tool Generation
**Goal**: The LLM generates self-contained financial tools that accept data as arguments, use only pandas/numpy for calculations, and return correctly typed results
**Depends on**: Phase 1 (talib must be removed before adding pandas/numpy-only guidance)
**Requirements**: PROMPT-03, PROMPT-04, DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. Running a calculation task (e.g., "calc RSI") produces a tool that accepts `prices: list` as a function parameter (not fetching data internally)
  2. Generated tools use only pandas/numpy for technical indicator calculations (no `import talib`, no `import yfinance` inside the tool)
  3. Generated tools return typed results: float for numeric indicators, dict for structured output, bool for boolean checks
  4. The `if __name__ == '__main__'` test block in generated tools uses inline sample data (not API calls)
**Plans**: TBD

Plans:
- [ ] 02-01: Enhance SYSTEM_PROMPT with data pattern and calculation instructions
- [ ] 02-02: Add return type guidance and verify generated tool patterns

### Phase 3: Refiner Pipeline Repair
**Goal**: When a generated tool fails verification, the refiner correctly analyzes the error and produces a working patch
**Depends on**: Phase 2 (prompt improvements reduce error volume; refiner must handle remaining failures)
**Requirements**: REFNR-01, REFNR-02, REFNR-03, REFNR-04
**Success Criteria** (what must be TRUE):
  1. `generate_tool_code()` return dict includes `text_response` key containing the LLM's non-code analysis text
  2. Refiner's `analyze_error()` extracts root cause from `text_response` (not just `thought_trace`) when analyzing errors
  3. Errors of type `ModuleNotFoundError`, `ImportError`, and `AssertionError` are correctly classified (not "UnknownError")
  4. Refiner's patch prompt explicitly instructs the LLM to avoid talib and use pandas/numpy only
**Plans**: TBD

Plans:
- [ ] 03-01: Fix generate_tool_code return value and error analysis extraction
- [ ] 03-02: Add missing error patterns and talib-avoidance instruction to patch prompt

### Phase 4: Regression Verification
**Goal**: The complete fix set achieves >=80% benchmark success rate without breaking any currently-passing tasks
**Depends on**: Phase 3 (all fixes must be in place before verification)
**Requirements**: REGR-01, REGR-02
**Success Criteria** (what must be TRUE):
  1. Running `python benchmarks/run_eval.py --agent evolving` produces a task success rate >= 80% (16/20 or better)
  2. All 13 currently-passing tasks (8 fetch + 5 calc/composite) still pass
  3. Running `python benchmarks/run_eval.py --security-only` produces 100% security block rate
  4. At least 3 of the 7 previously-failing tasks now pass (minimum improvement to reach 80%)
**Plans**: TBD

Plans:
- [ ] 04-01: Run full benchmark and verify targets

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Allowlist Cleanup & Fallback Fix | 0/2 | Planned | - |
| 2. Prompt Engineering for Correct Tool Generation | 0/2 | Not started | - |
| 3. Refiner Pipeline Repair | 0/2 | Not started | - |
| 4. Regression Verification | 0/1 | Not started | - |
