---
phase: 01-allowlist-cleanup-and-fallback-fix
plan: 02
status: complete
subsystem: core-llm
tags: [error-handling, mock-fallback, llm-adapter]
dependency-graph:
  requires: [01-01]
  provides: [correct-error-handling, text-response-key]
  affects: [02-phase-synthesizer, 02-phase-refiner]
tech-stack:
  added: []
  patterns: [error-dict-return, early-return-on-error]
key-files:
  created: []
  modified: [fin_evo_agent/src/core/llm_adapter.py]
decisions:
  - id: MOCK-01
    description: "API errors return error dict instead of falling back to mock"
  - id: MOCK-02
    description: "Mock only activates when API_KEY env var is unset"
metrics:
  duration: 2m 5s
  completed: 2026-02-02
---

# Phase 01 Plan 02: Fix Mock LLM Fallback Behavior Summary

Fixed generate_tool_code() to return error dict on API failures instead of masking them with mock RSI responses; mock now only activates when no API key is configured.

## Summary

The `generate_tool_code()` method in `LLMAdapter` previously caught all exceptions (including API timeouts) and fell back to the mock LLM, which always returns hardcoded RSI code. This masked real API failures by silently producing irrelevant tool code regardless of the actual task.

After this fix:
- **API errors/timeouts**: Return an error dict with `code_payload=None` and a descriptive `text_response` containing the error message
- **No API key**: Mock mode still works as before for local testing
- **Forward compatibility**: Error dict includes `text_response` key used by the refiner's `analyze_error()` method

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix exception handler in generate_tool_code | d88cb3e | fin_evo_agent/src/core/llm_adapter.py |
| 2 | Verify mock still works without API key | (verification only) | - |
| 3 | Verify error return format and downstream compatibility | (verification only) | - |

## Deliverables

- Modified `generate_tool_code()` exception handler to return error dict instead of calling `_mock_generate()`
- Error dict structure: `{thought_trace: "", code_payload: None, text_response: "LLM API Error: ...", raw_response: "LLM API Error: ..."}`
- Mock comment updated from "Fallback to mock response if no API key" to "Mock only when no API key configured (testing mode)"

## Verification Results

All 6 verification checks passed:
1. Exception handler returns error dict (not calling mock)
2. Error return includes `text_response` key for refiner compatibility
3. Mock mode works without API key (code_payload is not None)
4. Error return has all 4 required keys (thought_trace, code_payload, text_response, raw_response)
5. Synthesizer handles `code_payload=None` without KeyError (line 100: `if not result["code_payload"]`)
6. Refiner can access `text_response` from error return dict (line 121: `result.get("text_response")`)

## Success Criteria

- [x] MOCK-01: On LLM timeout, return error result instead of falling back to mock
- [x] MOCK-02: Mock LLM only activates when no API key is configured
- [x] Error return format includes all 4 keys - no KeyError downstream
- [x] text_response key present for forward compatibility with refiner (REFNR-02)
- [x] Mock testing mode still works for local development
- [x] Synthesizer handles code_payload=None gracefully

## Deviations from Plan

None - plan executed exactly as written.

## Issues

None.

## Next Phase Readiness

Phase 1 is now complete (both plans 01-01 and 01-02 executed). The codebase is ready for Phase 2 work:
- Allowlist is clean (talib removed in 01-01)
- Error handling is correct (mock fallback fixed in 01-02)
- No blockers identified
