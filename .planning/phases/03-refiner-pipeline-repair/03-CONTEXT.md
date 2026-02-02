# Phase 3: Refiner Pipeline Repair - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the error analysis and patch generation loop so failed tool syntheses get properly repaired. This includes:
- Adding `text_response` to `generate_tool_code()` return dict
- Making `analyze_error()` extract root cause from `text_response`
- Correctly classifying known error types
- Improving patch prompts with talib-avoidance instructions

</domain>

<decisions>
## Implementation Decisions

### Error Classification
- Unknown errors: Ask LLM to classify first, then apply appropriate fix pattern
- Known error types with explicit fix patterns:
  - `ModuleNotFoundError` — replace forbidden module with allowed equivalent
  - `ImportError` — similar handling, check import paths
  - `AssertionError` — fix the logic/calculation to match expected output
  - `TypeError/ValueError` — fix function signatures or data handling
- Fix instructions: Very specific, with example code snippets for common fixes
- Multiple errors: Fix first error only, re-run, then handle next if any
- Track history: Remember what was tried in previous attempts to avoid repetition
- Unfixable errors (fail fast, no retry):
  - Security violations (AST blocked code)
  - Network/API errors (external service failures)

### Patch Prompt Strategy
- Include original task description alongside broken code
- Module guidance: Only mention relevant modules based on error type (not full list every time)
- Include history: Show previous patches and why they failed on retries 2 and 3
- Output format: Diff/patch format (shows changes clearly)
- Include common pitfalls warnings relevant to the error type
- Verbosity: Detailed and explicit step-by-step instructions
- Require explanation: LLM states what it will change and why before the diff
- Test preservation: Tests define expected behavior — fix should match original tests, not change them

### text_response Extraction
- Extraction scope: Everything outside code blocks (all text not in ```python...```)
- Storage: Store thought_trace and text_response separately as distinct fields
- Priority for error analysis: text_response first, fall back to thought_trace if empty
- Length limit: Yes, cap at reasonable length to keep prompts manageable
- Persistence: Store in database (ErrorReport table) for debugging

### Retry Behavior
- Max retries: Keep at 3 (current limit is reasonable)
- Delay: Exponential backoff between attempts (1s, 2s, 4s)
- Final failure: Return failure with history of all 3 patch attempts for debugging
- Vary by error type: Different retry strategies for different error types

### Claude's Discretion
- Exact max length for text_response truncation
- Specific retry count variations per error type
- Exact exponential backoff timing values
- When to add warnings vs. when pitfalls section adds clutter

</decisions>

<specifics>
## Specific Ideas

- Fix patterns should include working code snippets (e.g., RSI calculation in pandas as template)
- Each patch attempt should have the best chance of success since max retries is limited
- History tracking prevents spinning on the same failed fix approach

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-refiner-pipeline-repair*
*Context gathered: 2026-02-02*
