# Requirements: Yunjue Agent Benchmark Fix Sprint

**Defined:** 2026-01-31
**Core Value:** Benchmark task success rate >= 80%

## v1 Requirements

### LLM Prompt & Allowlist

- [x] **PROMPT-01**: Remove `talib` from SYSTEM_PROMPT allowed imports list in `llm_adapter.py`
- [x] **PROMPT-02**: Remove `talib` from ALLOWED_MODULES in `executor.py`
- [ ] **PROMPT-03**: Add explicit instruction in SYSTEM_PROMPT to implement technical indicators using pandas/numpy only (no external indicator libraries)
- [ ] **PROMPT-04**: Add instruction in SYSTEM_PROMPT to accept price data as function arguments rather than fetching internally

### Refiner Pipeline

- [ ] **REFNR-01**: `generate_tool_code` returns `text_response` in its result dict
- [ ] **REFNR-02**: Refiner's `analyze_error` correctly extracts LLM analysis from `text_response`
- [ ] **REFNR-03**: Add `ModuleNotFoundError`, `ImportError`, `AssertionError` to refiner's ERROR_PATTERNS
- [ ] **REFNR-04**: Refiner patch prompt includes instruction to avoid talib and use pandas/numpy

### Mock LLM Fallback

- [x] **MOCK-01**: On LLM timeout, return error result instead of falling back to mock
- [x] **MOCK-02**: Mock LLM only activates when no API key is configured (not on timeout)

### Tool Data Patterns

- [ ] **DATA-01**: SYSTEM_PROMPT instructs LLM to generate functions that accept price data as arguments (list or pd.Series)
- [ ] **DATA-02**: SYSTEM_PROMPT instructs LLM not to call yfinance/akshare inside generated tool functions
- [ ] **DATA-03**: Generated tools return typed results matching expected output formats (float for numeric, dict for structured, bool for boolean)

### Regression Guard

- [ ] **REGR-01**: All 13 currently-passing benchmark tasks still pass after fixes
- [ ] **REGR-02**: Security block rate remains 100%

## v2 Requirements

### Refiner Intelligence

- **REFNR-05**: Refiner detects when the same error repeats across attempts and tries a fundamentally different approach
- **REFNR-06**: Refiner validates that patched tool name matches the requested task

### Tool Quality

- **QUAL-01**: Generated tools include input validation
- **QUAL-02**: Generated tools include proper error messages

## Out of Scope

| Feature | Reason |
|---------|--------|
| Batch merger implementation | Phase 1b feature, not needed for 80% target |
| TA-Lib installation | Removed from allowlist instead |
| New benchmark tasks | Fix existing failures first |
| Eval runner redesign | Current runner works |
| UI/API layer | CLI-only system |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROMPT-01 | Phase 1 | Complete |
| PROMPT-02 | Phase 1 | Complete |
| PROMPT-03 | Phase 2 | Pending |
| PROMPT-04 | Phase 2 | Pending |
| REFNR-01 | Phase 3 | Pending |
| REFNR-02 | Phase 3 | Pending |
| REFNR-03 | Phase 3 | Pending |
| REFNR-04 | Phase 3 | Pending |
| MOCK-01 | Phase 1 | Complete |
| MOCK-02 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| REGR-01 | Phase 4 | Pending |
| REGR-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-01-31*
*Last updated: 2026-01-31 after roadmap creation*
