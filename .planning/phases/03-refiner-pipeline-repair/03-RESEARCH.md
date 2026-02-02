# Phase 3: Refiner Pipeline Repair - Research

**Researched:** 2026-02-02
**Domain:** LLM error analysis, code repair pipelines, retry strategies
**Confidence:** HIGH

## Summary

This phase fixes the error analysis and patch generation loop in the refiner so that failed tool syntheses get properly repaired. The current refiner has four specific issues:

1. **Missing `text_response`**: The `generate_tool_code()` method in `llm_adapter.py` already extracts `text_response` in `_clean_protocol()` (line 119, 128) but fails to include it in the return dict (lines 181-185). This is a simple one-line fix.

2. **Incomplete Error Classification**: The refiner's `ERROR_PATTERNS` dict (lines 34-58) only covers `TypeError`, `KeyError`, `IndexError`, `ValueError`, `ZeroDivisionError`, and `AttributeError`. It's missing `ModuleNotFoundError`, `ImportError`, and `AssertionError` which are common failures when LLM generates code with forbidden imports or incorrect logic.

3. **Patch Prompt Missing Talib Guidance**: The current patch prompt (lines 155-175) doesn't include instructions to avoid talib and use pandas/numpy only. Since Phase 2 added this to the synthesis prompt, the patch prompt also needs it to maintain consistency.

4. **No Retry History Tracking**: The refiner doesn't track what patches were attempted previously, leading to potential repeated failures.

**Primary recommendation:** Make surgical edits to `llm_adapter.py` (add `text_response` to return dict) and `refiner.py` (add error patterns, improve patch prompt, add history tracking with exponential backoff).

## Standard Stack

### Core Libraries (No Changes)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlmodel | >=0.0.8 | ErrorReport persistence | Already used for other models |
| time | stdlib | Exponential backoff delays | No external dependency |
| re | stdlib | Error message pattern matching | Already used in refiner |

### No New Dependencies

This phase modifies existing code. No new Python packages needed.

## Architecture Patterns

### Pattern 1: Error Classification with Explicit Fix Instructions

**What:** Map error types to specific fix patterns with example code snippets.
**When to use:** In `_classify_error()` to guide patch generation.

```python
# Recommended pattern based on CONTEXT.md decisions
ERROR_PATTERNS = {
    "ModuleNotFoundError": {
        "pattern": r"ModuleNotFoundError:.*No module named '(\w+)'",
        "strategy": "Replace forbidden module with allowed equivalent. Use pandas/numpy only for calculations.",
        "example_fix": "Replace 'import talib' with pandas implementation: delta.rolling().mean()"
    },
    "ImportError": {
        "pattern": r"ImportError:.*cannot import name '(\w+)'",
        "strategy": "Check import path. Use only: pandas, numpy, datetime, json, math, decimal, collections, re, typing.",
        "example_fix": "from datetime import datetime  # correct path"
    },
    "AssertionError": {
        "pattern": r"AssertionError:?(.*)?",
        "strategy": "Fix calculation logic to match expected output. Do NOT change the test assertions.",
        "example_fix": "Check formula implementation against docstring specification"
    },
    "TypeError": {
        "pattern": r"TypeError:.*",
        "strategy": "Check argument types and add type conversion. Ensure return type matches signature.",
        "example_fix": "return float(result)  # ensure numeric return"
    },
    "ValueError": {
        "pattern": r"ValueError:.*",
        "strategy": "Add input validation. Handle edge cases (empty lists, NaN values).",
        "example_fix": "if len(prices) < period: return 50.0  # neutral value"
    },
    # ... existing patterns preserved ...
}
```

### Pattern 2: History-Aware Patch Prompt

**What:** Include previous patch attempts in retry prompts to avoid repeating failed approaches.
**When to use:** On retry attempts 2 and 3.

```python
# Recommended pattern based on CONTEXT.md decisions
def generate_patch(
    self,
    error_report: ErrorReport,
    original_code: str,
    task: str,
    attempt: int = 1,
    previous_patches: list = None
) -> Optional[str]:
    """Generate patch with history awareness."""

    # Build history section for retries
    history_section = ""
    if previous_patches and attempt > 1:
        history_section = "\n## Previous Attempts (DO NOT REPEAT THESE)\n"
        for i, patch in enumerate(previous_patches, 1):
            history_section += f"\n### Attempt {i} - FAILED\n"
            history_section += f"What was tried: {patch['approach']}\n"
            history_section += f"Why it failed: {patch['failure_reason']}\n"

    # Module guidance based on error type (not full list every time)
    if error_report.error_type in ("ModuleNotFoundError", "ImportError"):
        module_guidance = """
## Module Replacement Guide
- FORBIDDEN: talib, yfinance, akshare, requests, os, sys, subprocess
- USE INSTEAD: pandas, numpy for all calculations
- RSI example: delta.clip(lower=0).rolling(period).mean() instead of talib.RSI()
"""
    else:
        module_guidance = ""

    patch_prompt = f"""修复以下Python代码中的错误。

## 原始任务
{task}

## 原始代码
```python
{original_code}
```

## 错误分析
错误类型: {error_report.error_type}
根本原因: {error_report.root_cause}
{module_guidance}
{history_section}

## 修复要求
1. 首先说明你将要修改什么以及为什么
2. 修复错误，保持原有功能
3. 只使用 pandas 和 numpy 进行计算
4. 保留原有的类型注解和文档字符串
5. 保留 if __name__ == '__main__' 中的测试用例（不要修改测试）
6. 测试定义了期望行为 — 修复应匹配原始测试，不要修改测试

只输出修复后的完整代码，用 ```python ``` 包裹。"""

    return patch_prompt
```

### Pattern 3: Exponential Backoff with Fail-Fast

**What:** Add delays between retry attempts with early exit for unfixable errors.
**When to use:** In `refine()` loop.

```python
# Recommended pattern based on CONTEXT.md decisions
import time

# Unfixable errors - don't retry
UNFIXABLE_ERRORS = {
    "SecurityException",  # AST blocked code
    "TimeoutError",       # External timeout
    "ConnectionError",    # Network failures
    "LLM API Error"       # LLM service failures
}

def refine(self, code, task, trace, base_tool=None, max_attempts=3):
    """Refinement loop with exponential backoff."""

    error_reports = []
    patch_history = []
    current_code = code
    current_trace = trace

    for attempt in range(max_attempts):
        # Check for unfixable errors first
        stderr = current_trace.std_err or ""
        for unfixable in UNFIXABLE_ERRORS:
            if unfixable in stderr:
                print(f"[Refiner] Unfixable error: {unfixable} - aborting")
                return None, error_reports

        # Exponential backoff: 1s, 2s, 4s
        if attempt > 0:
            delay = 2 ** (attempt - 1)  # 1, 2, 4 seconds
            print(f"[Refiner] Waiting {delay}s before attempt {attempt + 1}...")
            time.sleep(delay)

        # ... rest of refinement logic ...
```

### Pattern 4: text_response Extraction Fix

**What:** Include `text_response` in `generate_tool_code()` return dict.
**When to use:** Always - this is a bug fix.

```python
# Source: /fin_evo_agent/src/core/llm_adapter.py
# Current (lines 181-185):
parsed = self._clean_protocol(raw_response)
return {
    "thought_trace": parsed["thought_trace"],
    "code_payload": parsed["code_payload"],
    "raw_response": raw_response
}

# Fixed:
parsed = self._clean_protocol(raw_response)
return {
    "thought_trace": parsed["thought_trace"],
    "code_payload": parsed["code_payload"],
    "text_response": parsed["text_response"],  # <-- ADD THIS
    "raw_response": raw_response
}
```

### Anti-Patterns to Avoid

- **Retrying unfixable errors:** Don't waste attempts on security violations or network errors
- **Modifying tests in patches:** Tests define expected behavior; the fix should match tests, not change them
- **Repeating failed approaches:** History tracking prevents spinning on the same broken fix
- **Full module list every time:** Only include relevant module guidance based on error type

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Delay implementation | Manual loop | `time.sleep()` | Standard library, simple |
| Error pattern matching | Custom parser | `re.search()` with patterns | Already used, reliable |
| History storage | Custom data structure | List of dicts | Simple, sufficient |

**Key insight:** The existing refiner structure is correct. The issues are missing data (`text_response`), incomplete classification (error patterns), and missing guidance (patch prompt). These are surgical fixes, not architectural changes.

## Common Pitfalls

### Pitfall 1: text_response vs thought_trace Confusion

**What goes wrong:** Using `thought_trace` for error analysis when `text_response` has better information.
**Why it happens:** Both contain LLM reasoning, but `text_response` includes everything outside `<think>` tags (the actual explanation), while `thought_trace` is only internal reasoning.
**How to avoid:** Priority: `text_response` first, fall back to `thought_trace` if empty.
**Warning signs:** Root cause extraction returns empty or `<think>` content.

### Pitfall 2: Infinite Retry on Same Error

**What goes wrong:** Refiner keeps trying the same fix approach that already failed.
**Why it happens:** No history tracking between attempts.
**How to avoid:** Store patch attempts with approach description and failure reason. Include in retry prompts.
**Warning signs:** Log shows "Attempt 2" and "Attempt 3" with identical error messages.

### Pitfall 3: ModuleNotFoundError Classified as UnknownError

**What goes wrong:** Refiner returns "UnknownError" for `ModuleNotFoundError: No module named 'talib'`.
**Why it happens:** `ModuleNotFoundError` not in ERROR_PATTERNS dict.
**How to avoid:** Add explicit pattern: `r"ModuleNotFoundError:.*No module named '(\w+)'"`.
**Warning signs:** Error type shows "UnknownError" when stderr clearly shows "ModuleNotFoundError".

### Pitfall 4: Patch Generates Same Forbidden Import

**What goes wrong:** Patch still uses talib even though that's what caused the original error.
**Why it happens:** Patch prompt doesn't explicitly forbid talib or guide to pandas/numpy alternative.
**How to avoid:** Include module replacement guide in patch prompt when error is ModuleNotFoundError/ImportError.
**Warning signs:** All 3 patch attempts fail with same "Unallowed import: talib" error.

### Pitfall 5: Truncating text_response Too Aggressively

**What goes wrong:** Error analysis misses critical information due to length limit.
**Why it happens:** text_response truncated to keep prompts manageable, but cutoff removes key details.
**How to avoid:** Use reasonable limit (2000-4000 chars). Truncate from middle if needed, keeping start and end.
**Warning signs:** Root cause says "..." or "truncated" and misses actual error explanation.

## Code Examples

### Example 1: Adding text_response to Return Dict (THE FIX)

```python
# Source: /fin_evo_agent/src/core/llm_adapter.py lines 180-185
# BEFORE:
parsed = self._clean_protocol(raw_response)
return {
    "thought_trace": parsed["thought_trace"],
    "code_payload": parsed["code_payload"],
    "raw_response": raw_response
}

# AFTER:
parsed = self._clean_protocol(raw_response)
return {
    "thought_trace": parsed["thought_trace"],
    "code_payload": parsed["code_payload"],
    "text_response": parsed["text_response"],  # ADD THIS LINE
    "raw_response": raw_response
}
```

### Example 2: Enhanced Error Patterns

```python
# Source: /fin_evo_agent/src/evolution/refiner.py lines 34-58
# ADD these patterns to ERROR_PATTERNS dict:

"ModuleNotFoundError": {
    "pattern": r"ModuleNotFoundError:.*No module named '(\w+)'",
    "strategy": "Replace forbidden module with pandas/numpy equivalent. See module guide.",
    "unfixable_if": lambda m: m.group(1) in ("os", "sys", "subprocess")  # Security violations
},
"ImportError": {
    "pattern": r"ImportError:.*",
    "strategy": "Check import path and module name. Use only allowed imports."
},
"AssertionError": {
    "pattern": r"AssertionError:?(.*)?",
    "strategy": "Fix the calculation logic. Tests define expected behavior - do not modify tests."
},
```

### Example 3: analyze_error Using text_response

```python
# Source: /fin_evo_agent/src/evolution/refiner.py
# CURRENT (line 121):
root_cause = result.get("thought_trace") or result.get("text_response") or f"{error_type}: {strategy}"

# IMPROVED (priority text_response first):
text_response = result.get("text_response", "")
thought_trace = result.get("thought_trace", "")

# Truncate to reasonable length (recommended: 2000 chars)
MAX_TEXT_LEN = 2000
if len(text_response) > MAX_TEXT_LEN:
    text_response = text_response[:MAX_TEXT_LEN//2] + "\n...[truncated]...\n" + text_response[-MAX_TEXT_LEN//2:]

# Priority: text_response (LLM explanation) > thought_trace (internal reasoning) > default
root_cause = text_response or thought_trace or f"{error_type}: {strategy}"
```

### Example 4: Patch Prompt with Talib Avoidance

```python
# Source: /fin_evo_agent/src/evolution/refiner.py generate_patch()
# The patch prompt MUST include talib avoidance when error is ModuleNotFoundError/ImportError

# Module replacement snippets for common cases:
MODULE_REPLACEMENT_GUIDE = """
## Common Replacements (USE THESE)

### RSI (replace talib.RSI)
```python
delta = prices.diff()
gain = delta.clip(lower=0).rolling(period).mean()
loss = (-delta.clip(upper=0)).rolling(period).mean()
rs = gain / loss.replace(0, np.inf)
rsi = 100 - (100 / (1 + rs))
```

### MACD (replace talib.MACD)
```python
ema_fast = prices.ewm(span=fast, adjust=False).mean()
ema_slow = prices.ewm(span=slow, adjust=False).mean()
macd_line = ema_fast - ema_slow
signal = macd_line.ewm(span=signal_period, adjust=False).mean()
```

### Bollinger Bands (replace talib.BBANDS)
```python
middle = prices.rolling(period).mean()
std = prices.rolling(period).std()
upper = middle + (num_std * std)
lower = middle - (num_std * std)
```
"""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Retry immediately | Exponential backoff (1s, 2s, 4s) | This phase | Reduces API rate limits, gives LLM "breathing room" |
| Generic error messages | Specific fix patterns with examples | This phase | Higher first-attempt success rate |
| No history tracking | Previous attempts in retry prompt | This phase | Avoids repeating failed approaches |

**Deprecated/outdated:**
- Generic "UnknownError" fallback: Now classifies ModuleNotFoundError, ImportError, AssertionError explicitly
- text_response ignored: Now extracted and used for error analysis

## Open Questions

1. **Exact text_response truncation length?**
   - What we know: Must cap to keep prompts manageable (decision from CONTEXT.md)
   - What's unclear: Optimal length that balances information vs. prompt bloat
   - Recommendation: Start with 2000 chars, adjust based on observed behavior. This is in Claude's discretion per CONTEXT.md.

2. **Different retry counts per error type?**
   - What we know: CONTEXT.md mentions this as Claude's discretion
   - What's unclear: Which error types warrant more/fewer retries
   - Recommendation: Keep 3 for all types initially. AssertionError might benefit from more (calculation bugs are fixable), ModuleNotFoundError might need fewer (if LLM keeps using forbidden module, unlikely to change).

3. **When to include pitfalls section vs. when it adds clutter?**
   - What we know: CONTEXT.md mentions this as Claude's discretion
   - What's unclear: Balance between helpful guidance and prompt bloat
   - Recommendation: Include pitfalls only for error types where they're relevant (e.g., module replacement guide only for ModuleNotFoundError).

## Sources

### Primary (HIGH confidence)

- `/fin_evo_agent/src/core/llm_adapter.py` - Direct code inspection, lines 98-185
- `/fin_evo_agent/src/evolution/refiner.py` - Direct code inspection, lines 30-268
- `/fin_evo_agent/src/core/models.py` - ErrorReport model, lines 94-103
- `.planning/phases/03-refiner-pipeline-repair/03-CONTEXT.md` - User decisions

### Secondary (MEDIUM confidence)

- Phase 2 research (02-RESEARCH.md) - Established patterns for talib avoidance
- Phase 1 research (01-RESEARCH.md) - Established error handling patterns

### Tertiary (LOW confidence)

- N/A - All findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- text_response fix: HIGH - Direct code inspection confirms the bug
- Error patterns: HIGH - Direct code inspection shows missing patterns
- Patch prompt improvements: HIGH - Based on Phase 2 established patterns
- Exponential backoff: MEDIUM - Standard practice, specific timing values are discretionary

**Research date:** 2026-02-02
**Valid until:** 60 days (error handling patterns are stable)

## Implementation Checklist

For the planner, the required changes are:

1. **REFNR-01: Add `text_response` to `generate_tool_code()` return dict**
   - File: `src/core/llm_adapter.py`
   - Location: Lines 181-185
   - Change: Add `"text_response": parsed["text_response"],` to return dict

2. **REFNR-02: Update `analyze_error()` to use `text_response` with priority**
   - File: `src/evolution/refiner.py`
   - Location: Line 121
   - Change: Priority should be `text_response` first, then `thought_trace`
   - Also: Add truncation logic (max ~2000 chars)

3. **REFNR-03: Add missing error patterns**
   - File: `src/evolution/refiner.py`
   - Location: Lines 34-58 (ERROR_PATTERNS dict)
   - Add: `ModuleNotFoundError`, `ImportError`, `AssertionError` patterns

4. **REFNR-04: Improve patch prompt with talib avoidance**
   - File: `src/evolution/refiner.py`
   - Location: `generate_patch()` method, lines 138-178
   - Change: Add module replacement guide when error is ModuleNotFoundError/ImportError
   - Change: Add "do not modify tests" instruction

5. **Optional enhancements (Claude's discretion)**:
   - Add exponential backoff in `refine()` loop
   - Add history tracking for retry attempts
   - Add unfixable error detection for fail-fast

### Verification Commands

```bash
# 1. Verify text_response is in return dict
cd fin_evo_agent
python3 -c "
from src.core.llm_adapter import LLMAdapter
a = LLMAdapter()
r = a.generate_tool_code('test')
assert 'text_response' in r, 'text_response missing from return dict'
print('PASS: text_response in return dict')
"

# 2. Verify error patterns include ModuleNotFoundError
python3 -c "
from src.evolution.refiner import Refiner
r = Refiner()
assert 'ModuleNotFoundError' in r.ERROR_PATTERNS, 'ModuleNotFoundError missing'
assert 'ImportError' in r.ERROR_PATTERNS, 'ImportError missing'
assert 'AssertionError' in r.ERROR_PATTERNS, 'AssertionError missing'
print('PASS: All required error patterns present')
"

# 3. Verify error classification
python3 -c "
from src.evolution.refiner import Refiner
r = Refiner()
err_type, strategy = r._classify_error(\"ModuleNotFoundError: No module named 'talib'\")
assert err_type == 'ModuleNotFoundError', f'Expected ModuleNotFoundError, got {err_type}'
print(f'PASS: ModuleNotFoundError classified correctly')
"

# 4. Run a synthesis task that triggers refinement (manual test)
python3 main.py --task "计算布林带" 2>&1 | grep -E "(Refiner|Error type|Root cause)"
```
