# Phase 1: Allowlist Cleanup & Fallback Fix - Research

**Researched:** 2026-01-31
**Domain:** Python module allowlisting, LLM error handling, mock fallback behavior
**Confidence:** HIGH

## Summary

This phase addresses two distinct but related issues in the Yunjue Agent system:

1. **Talib Removal**: The `talib` library is referenced in both the SYSTEM_PROMPT (llm_adapter.py line 23) and ALLOWED_MODULES (executor.py line 51), but the library is not installed. This causes generated tools that import talib to fail at runtime. The fix is straightforward: remove talib from both locations.

2. **Mock LLM Fallback Fix**: The current LLMAdapter falls back to mock responses on ANY exception (line 131-133), including API timeouts. This masks real failures by returning hardcoded RSI code regardless of the actual task. The fix requires distinguishing between "no API key configured" (use mock) and "API error/timeout" (return error).

**Primary recommendation:** Make surgical edits to two files - remove talib references and restructure the exception handling in `generate_tool_code()` to only use mock when `self.client is None`.

## Standard Stack

This phase does not introduce new libraries. It modifies existing Python code.

### Core Files to Modify

| File | Location | Change Type |
|------|----------|-------------|
| `src/core/llm_adapter.py` | Line 23, Lines 116-133 | Remove talib, fix exception handling |
| `src/core/executor.py` | Line 51 | Remove talib from ALLOWED_MODULES |

### No New Dependencies

This phase removes a dependency reference (talib) rather than adding one.

## Architecture Patterns

### Pattern 1: Module Allowlist (Existing)

**What:** The executor uses a set-based allowlist to validate imports via AST analysis.
**Current implementation:**
```python
# Source: /workspace/fin_evo_agent/src/core/executor.py lines 48-53
ALLOWED_MODULES = {
    'pandas', 'numpy', 'datetime', 'json',
    'math', 'decimal', 'collections', 're',
    'yfinance', 'talib', 'typing', 'hashlib',  # <-- talib here
    'pathlib'
}
```

**Fix:** Remove `'talib'` from this set.

### Pattern 2: LLM Prompt Allowlist (Existing)

**What:** The SYSTEM_PROMPT tells the LLM which imports are allowed.
**Current implementation:**
```python
# Source: /workspace/fin_evo_agent/src/core/llm_adapter.py line 23
# "3. Use only allowed imports: pandas, numpy, datetime, json, math, decimal, collections, re, yfinance, talib, pathlib"
```

**Fix:** Remove `talib` from this list.

### Pattern 3: Mock Fallback (Current - Problematic)

**What:** The current code falls back to mock on any exception.
**Current implementation:**
```python
# Source: /workspace/fin_evo_agent/src/core/llm_adapter.py lines 116-133
if self.client is None:
    # Fallback to mock response if no API key
    raw_response = self._mock_generate(task)
else:
    try:
        completion = self.client.chat.completions.create(...)
        raw_response = completion.choices[0].message.content
    except Exception as e:
        print(f"[LLM Error] {e}, falling back to mock")
        raw_response = self._mock_generate(task)  # <-- PROBLEM: masks errors
```

**Fix:** Remove the exception handler's mock fallback. Let errors propagate or return an error result.

### Pattern 4: Mock Fallback (Corrected)

**What:** Mock should ONLY activate when no API key is configured.
**Correct pattern:**
```python
# Recommended fix pattern
if self.client is None:
    # No API key configured - use mock for testing
    raw_response = self._mock_generate(task)
else:
    try:
        completion = self.client.chat.completions.create(...)
        raw_response = completion.choices[0].message.content
    except Exception as e:
        # API error or timeout - return error, don't mask with mock
        return {
            "thought_trace": "",
            "code_payload": None,
            "raw_response": f"LLM Error: {e}"
        }
```

### Anti-Patterns to Avoid

- **Silent fallback on errors:** Never mask API failures with mock data. This produces incorrect tools that appear to succeed.
- **Catch-all exception handling:** The current `except Exception` catches timeouts, rate limits, and network errors - all of which should be reported, not hidden.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Module validation | Custom string parsing | AST-based allowlist (already exists) | AST handles edge cases like `from x import y` |
| Error classification | Manual string matching | Exception type checking | Python's exception hierarchy is reliable |

**Key insight:** The existing patterns are correct. The issue is configuration (talib in allowlist) and control flow (mock fallback), not architecture.

## Common Pitfalls

### Pitfall 1: Incomplete Talib Removal

**What goes wrong:** Removing talib from one location but not the other.
**Why it happens:** Two separate files contain the reference.
**How to avoid:** Verify BOTH locations after changes:
  1. `executor.py` ALLOWED_MODULES set
  2. `llm_adapter.py` SYSTEM_PROMPT string
**Warning signs:** Generated tools still try to import talib; security check still shows talib as allowed.

### Pitfall 2: Breaking Mock Testing Mode

**What goes wrong:** Removing mock fallback entirely breaks local testing without API key.
**Why it happens:** Over-correction - removing mock from error path AND from no-API-key path.
**How to avoid:** Keep the `if self.client is None` mock path. Only remove the `except Exception` mock fallback.
**Warning signs:** Running without API_KEY produces errors instead of mock responses.

### Pitfall 3: Returning Wrong Error Format

**What goes wrong:** Error return doesn't match expected dict structure.
**Why it happens:** `generate_tool_code()` returns a dict with specific keys; error path must match.
**How to avoid:** Error return must include: `thought_trace`, `code_payload`, `raw_response` keys.
**Warning signs:** Downstream code crashes on KeyError when accessing result dict.

### Pitfall 4: Not Testing Both Paths

**What goes wrong:** Fix works for one scenario but breaks another.
**Why it happens:** Only testing with API key set, or only testing without.
**How to avoid:** Test matrix:
  - No API_KEY set -> mock response (should work)
  - API_KEY set, API works -> real response (should work)
  - API_KEY set, API times out -> error result (should NOT return mock)
**Warning signs:** Benchmark passes locally but fails in CI, or vice versa.

## Code Examples

### Example 1: Removing Talib from ALLOWED_MODULES

```python
# Source: /workspace/fin_evo_agent/src/core/executor.py
# BEFORE (line 48-53):
ALLOWED_MODULES = {
    'pandas', 'numpy', 'datetime', 'json',
    'math', 'decimal', 'collections', 're',
    'yfinance', 'talib', 'typing', 'hashlib',
    'pathlib'
}

# AFTER:
ALLOWED_MODULES = {
    'pandas', 'numpy', 'datetime', 'json',
    'math', 'decimal', 'collections', 're',
    'yfinance', 'typing', 'hashlib',
    'pathlib'
}
```

### Example 2: Removing Talib from SYSTEM_PROMPT

```python
# Source: /workspace/fin_evo_agent/src/core/llm_adapter.py
# BEFORE (line 23):
# "3. Use only allowed imports: pandas, numpy, datetime, json, math, decimal, collections, re, yfinance, talib, pathlib"

# AFTER:
# "3. Use only allowed imports: pandas, numpy, datetime, json, math, decimal, collections, re, yfinance, pathlib"
```

### Example 3: Fixing Mock Fallback Behavior

```python
# Source: /workspace/fin_evo_agent/src/core/llm_adapter.py
# BEFORE (lines 116-133):
if self.client is None:
    raw_response = self._mock_generate(task)
else:
    try:
        completion = self.client.chat.completions.create(...)
        raw_response = completion.choices[0].message.content
    except Exception as e:
        print(f"[LLM Error] {e}, falling back to mock")
        raw_response = self._mock_generate(task)

# AFTER:
if self.client is None:
    # Mock only when no API key configured (testing mode)
    raw_response = self._mock_generate(task)
else:
    try:
        completion = self.client.chat.completions.create(...)
        raw_response = completion.choices[0].message.content
    except Exception as e:
        # API error - return error result, don't mask with mock
        print(f"[LLM Error] {e}")
        return {
            "thought_trace": "",
            "code_payload": None,
            "raw_response": f"LLM API Error: {e}"
        }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Use talib for indicators | Use pandas/numpy | This sprint | Removes C library dependency |
| Mock on any error | Mock only when no API key | This sprint | Honest error reporting |

**Deprecated/outdated:**
- `talib` reference: Being removed because the C library is not installed and won't be installed (per project decision)

## Open Questions

None for this phase. The requirements are clear and the implementation is straightforward.

## Verification Commands

After implementation, verify success with:

```bash
# 1. Verify talib removed from ALLOWED_MODULES
cd /workspace/fin_evo_agent
python3 -c "from src.core.executor import ToolExecutor; assert 'talib' not in ToolExecutor.ALLOWED_MODULES, 'talib still in ALLOWED_MODULES'"

# 2. Verify talib removed from SYSTEM_PROMPT
python3 -c "from src.core.llm_adapter import SYSTEM_PROMPT; assert 'talib' not in SYSTEM_PROMPT, 'talib still in SYSTEM_PROMPT'"

# 3. Run security check (should not mention talib)
python3 main.py --security-check

# 4. Test mock behavior without API key
unset API_KEY
python3 -c "from src.core.llm_adapter import LLMAdapter; a = LLMAdapter(); r = a.generate_tool_code('test'); print('Mock works:', r['code_payload'] is not None)"
```

## Sources

### Primary (HIGH confidence)

- `/workspace/fin_evo_agent/src/core/llm_adapter.py` - Direct code inspection
- `/workspace/fin_evo_agent/src/core/executor.py` - Direct code inspection
- `/workspace/.planning/REQUIREMENTS.md` - Requirements PROMPT-01, PROMPT-02, MOCK-01, MOCK-02

### Secondary (MEDIUM confidence)

- `/workspace/CLAUDE.md` - Project documentation confirming talib is in allowlist

## Metadata

**Confidence breakdown:**
- Talib removal locations: HIGH - Direct code inspection confirms exact lines
- Mock fallback fix: HIGH - Direct code inspection confirms control flow
- Error return format: HIGH - Verified by reading downstream consumers (synthesizer.py)

**Research date:** 2026-01-31
**Valid until:** N/A - This is a one-time fix, not a library version concern

## Implementation Checklist

For the planner, the tasks are:

1. **Task 01-01: Remove talib from allowlist and prompt**
   - Edit `executor.py` line 51: remove `'talib'` from ALLOWED_MODULES set
   - Edit `llm_adapter.py` line 23: remove `talib` from SYSTEM_PROMPT imports list
   - Verify with security-check command

2. **Task 01-02: Fix mock LLM fallback behavior**
   - Edit `llm_adapter.py` lines 131-133: replace mock fallback with error return
   - Ensure error return matches expected dict format
   - Test both paths: no API key (mock works) and API error (returns error)
