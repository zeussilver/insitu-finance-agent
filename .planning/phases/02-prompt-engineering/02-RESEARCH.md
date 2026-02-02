# Phase 2: Prompt Engineering for Correct Tool Generation - Research

**Researched:** 2026-02-02
**Domain:** LLM prompt engineering for self-contained financial tool code generation
**Confidence:** HIGH

## Summary

This phase focuses on improving the SYSTEM_PROMPT in `llm_adapter.py` to guide the LLM to generate tools that follow a "separation of concerns" pattern: tools accept price data as arguments (not fetch it internally), use only pandas/numpy for calculations (no talib, no yfinance calls inside tools), and return properly typed results.

The current problem is clearly demonstrated by examining existing generated tools:
- `calculate_msft_5day_moving_average_v0.1.0_567b8171.py` - Uses `yf.Ticker("MSFT")` inside the function (BAD)
- `calculate_sp500_aapl_correlation_v0.1.0_18b8032b.py` - Uses `yf.download()` inside the function (BAD)
- `calc_rsi_v0.1.0_f42711fb.py` - Accepts `prices: list` as argument (GOOD - this is the mock LLM output)

The mock LLM already generates the correct pattern. The real LLM needs prompt guidance to follow the same pattern.

**Primary recommendation:** Add explicit instructions to SYSTEM_PROMPT that enforce the "pure function" pattern: accept data as arguments, use only pandas/numpy for calculations, return typed results, and use inline sample data in tests.

## Standard Stack

### Core Libraries for Generated Tools

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.0 | DataFrame operations, rolling windows | Industry standard for time series |
| numpy | >=1.24 | Numerical operations, NaN handling | Foundation for pandas calculations |

### Libraries NOT to Use Inside Generated Tools

| Library | Reason | Alternative |
|---------|--------|-------------|
| yfinance | Data fetching belongs to orchestrator | Accept prices as function argument |
| akshare | Same as yfinance | Accept data as function argument |
| talib | C library dependency | Implement using pandas/numpy |
| requests | No external API calls in tools | Not needed for calculations |

### Allowed in SYSTEM_PROMPT (for type hints/utilities)

| Library | Purpose | Notes |
|---------|---------|-------|
| datetime | Date type hints | Standard library |
| typing | Type annotations | Standard library |
| json | Return dict serialization | Standard library |
| math | Basic math operations | Standard library |
| decimal | Precision for financial values | Standard library |

**Installation:** These are already installed in the project. No new dependencies needed.

## Architecture Patterns

### Pattern 1: Pure Calculation Function (THE PATTERN TO ENFORCE)

**What:** Functions that accept data as arguments and return calculated results without side effects.
**When to use:** ALWAYS for generated financial tools.

```python
# Source: Existing mock LLM output (calc_rsi_v0.1.0_f42711fb.py) - CORRECT PATTERN
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """
    Calculate RSI (Relative Strength Index).

    Args:
        prices: List of closing prices (float)
        period: Calculation period, default 14

    Returns:
        RSI value (float between 0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # Return neutral value for insufficient data

    s = pd.Series(prices)
    delta = s.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


if __name__ == "__main__":
    # INLINE sample data - no API calls
    prices = [10, 12, 11, 13, 15, 17, 16, 15, 14, 13, 14, 15, 16, 17, 18]
    val = calc_rsi(prices, 5)
    assert 0 <= val <= 100
```

### Pattern 2: Return Type Conventions

**What:** Consistent return types based on output type.
**When to use:** All generated tools.

```python
# Source: Project requirements DATA-03

# Single numeric indicator -> float
def calc_rsi(prices: list, period: int = 14) -> float:
    ...
    return float(result)

# Multiple related values -> dict
def calc_macd(prices: list) -> dict:
    ...
    return {
        "macd": float(macd_line),
        "signal": float(signal_line),
        "histogram": float(histogram)
    }

# Boolean condition -> bool
def check_golden_cross(prices: list) -> bool:
    ...
    return bool(ma5 > ma20)
```

### Pattern 3: Pandas/NumPy Technical Indicator Implementations

**What:** Pure pandas/numpy implementations of common indicators.

**RSI (Relative Strength Index):**
```python
# Source: https://www.alpharithms.com/relative-strength-index-rsi-in-python-470209/
def calc_rsi(prices: list, period: int = 14) -> float:
    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])
```

**MACD (Moving Average Convergence Divergence):**
```python
# Source: https://aleksandarhaber.com/macd-moving-average-convergence-divergence-of-stock-price-time-series-in-pandas-and-python/
def calc_macd(prices: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    s = pd.Series(prices)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": float(macd_line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "histogram": float(histogram.iloc[-1])
    }
```

**Bollinger Bands:**
```python
# Source: https://www.askpython.com/python/examples/bollinger-bands-python
def calc_bollinger_bands(prices: list, period: int = 20, num_std: int = 2) -> dict:
    s = pd.Series(prices)
    middle = s.rolling(window=period).mean()
    std = s.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    return {
        "upper": float(upper.iloc[-1]),
        "middle": float(middle.iloc[-1]),
        "lower": float(lower.iloc[-1])
    }
```

### Anti-Patterns to Avoid

- **Data fetching inside tool:** `yf.download()` or `yf.Ticker().history()` inside the function
- **Hardcoded tickers:** `def calc_msft_rsi()` instead of `def calc_rsi(prices: list)`
- **API calls in tests:** `if __name__ == '__main__': data = yf.download(...)`
- **Returning pandas objects:** Return `float(value)` not `pd.Series`
- **Missing type hints:** Always include `: list`, `-> float`, etc.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Moving Average | Custom loop | `pd.Series.rolling().mean()` | Handles edge cases, NaN |
| EMA | Manual calculation | `pd.Series.ewm().mean()` | Correct smoothing factor |
| Standard Deviation | numpy loop | `pd.Series.rolling().std()` | Handles degrees of freedom |
| Price Changes | Manual diff | `pd.Series.diff()` | Handles NaN at start |
| Positive/Negative filtering | if-else loops | `pd.Series.clip()` or `.where()` | Vectorized, faster |

**Key insight:** pandas has built-in methods for all common financial calculations. The SYSTEM_PROMPT should guide the LLM to use these rather than manual implementations.

## Common Pitfalls

### Pitfall 1: LLM Generates Data-Fetching Code Inside Tools

**What goes wrong:** LLM generates `yf.Ticker("AAPL").history(...)` inside the function body.
**Why it happens:** LLM sees the task "Calculate AAPL RSI" and assumes it needs to fetch AAPL data.
**How to avoid:** SYSTEM_PROMPT must explicitly say "Accept price data as a function argument. Do NOT call yfinance, akshare, or any data API inside the function."
**Warning signs:** Generated code contains `import yfinance` or `yf.download()`.

### Pitfall 2: LLM Uses talib Even When Told Not To

**What goes wrong:** LLM generates `from talib import RSI` despite instructions.
**Why it happens:** LLM's training data heavily features talib for technical indicators.
**How to avoid:**
1. SYSTEM_PROMPT explicitly says "Use pandas/numpy ONLY. Do NOT use talib."
2. The ALLOWED_MODULES list in executor.py excludes talib (already done in Phase 1).
**Warning signs:** AST check fails with "Unallowed import: talib".

### Pitfall 3: Tests Make API Calls

**What goes wrong:** `if __name__ == '__main__'` block calls `yf.download()`.
**Why it happens:** LLM thinks it needs real data for realistic tests.
**How to avoid:** SYSTEM_PROMPT must explicitly say "In the test block, use inline sample data (hardcoded lists). Do NOT make API calls."
**Warning signs:** Tests fail due to network errors or rate limits in sandbox.

### Pitfall 4: Incorrect Return Types

**What goes wrong:** Function returns `pd.Series` instead of `float`, or returns `None` instead of a neutral value.
**Why it happens:** LLM doesn't consider downstream usage.
**How to avoid:** SYSTEM_PROMPT specifies return type conventions:
- Numeric indicators -> `float`
- Structured output -> `dict` with typed values
- Boolean checks -> `bool`
**Warning signs:** Downstream code fails with type errors.

### Pitfall 5: Hardcoded Ticker Symbols in Function Name

**What goes wrong:** LLM generates `def calculate_msft_5day_moving_average()` instead of `def calc_ma(prices, period)`.
**Why it happens:** LLM interprets task literally.
**How to avoid:** SYSTEM_PROMPT should say "Generate reusable tools with generic function names. Accept the data source as a parameter."
**Warning signs:** Generated tool is not reusable for other tickers.

## Code Examples

### Example 1: Current SYSTEM_PROMPT (Needs Improvement)

```python
# Source: /fin_evo_agent/src/core/llm_adapter.py (current)
SYSTEM_PROMPT = """You are a financial tool generator. Generate Python functions that:

1. Include complete type hints
2. Include a comprehensive docstring
3. Use only allowed imports: pandas, numpy, datetime, json, math, decimal, collections, re, yfinance, pathlib
4. Include 2 assert tests in `if __name__ == '__main__':` block

Output format:
1. First, explain your reasoning inside <think>...</think> tags
2. Then provide the code inside ```python...``` code block

IMPORTANT:
- Never use: os, sys, subprocess, shutil, eval, exec, compile, open (except mode='r')
- Keep functions focused and single-purpose
- Handle edge cases gracefully
"""
```

### Example 2: Improved SYSTEM_PROMPT (RECOMMENDATION)

```python
# Source: Research recommendation based on requirements PROMPT-03, PROMPT-04, DATA-01, DATA-02, DATA-03
SYSTEM_PROMPT = """You are a financial tool generator. Generate Python functions that:

1. Include complete type hints (e.g., `prices: list`, `period: int = 14`, `-> float`)
2. Include a comprehensive docstring with Args and Returns sections
3. Use ONLY pandas and numpy for calculations - NO talib, NO external indicator libraries
4. Accept price/financial data as function ARGUMENTS (e.g., `prices: list` or `prices: pd.Series`)
5. Do NOT call yfinance, akshare, or any data API inside the function - data is passed IN
6. Return typed results: float for single values, dict for multiple values, bool for conditions
7. Include 2 assert tests in `if __name__ == '__main__':` block using INLINE sample data

Output format:
1. First, explain your reasoning inside <think>...</think> tags
2. Then provide the code inside ```python...``` code block

IMPORTANT:
- Allowed imports: pandas, numpy, datetime, json, math, decimal, collections, re, typing
- FORBIDDEN inside generated tools: yfinance, akshare, talib, requests, urllib
- Never use: os, sys, subprocess, shutil, eval, exec, compile
- Function names should be GENERIC (e.g., `calc_rsi`, not `calc_aapl_rsi`)
- Test data must be INLINE hardcoded lists, NOT fetched from APIs

EXAMPLE of correct pattern:
```python
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    \"\"\"Calculate RSI indicator.

    Args:
        prices: List of closing prices
        period: RSI period (default 14)

    Returns:
        RSI value between 0 and 100
    \"\"\"
    # Implementation using pandas only...
    return float(result)

if __name__ == "__main__":
    test_prices = [44, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45, 45.5, 46]
    result = calc_rsi(test_prices, 5)
    assert 0 <= result <= 100
```
"""
```

### Example 3: Technical Indicator Formulas for Reference

```python
# These formulas should be included in SYSTEM_PROMPT or a supplementary reference
# Source: Financial analysis standards

# RSI Formula:
# 1. Calculate price changes: delta = prices.diff()
# 2. Separate gains and losses: gain = delta.clip(lower=0), loss = -delta.clip(upper=0)
# 3. Calculate averages: avg_gain = gain.rolling(period).mean()
# 4. RS = avg_gain / avg_loss
# 5. RSI = 100 - (100 / (1 + RS))

# MACD Formula:
# 1. Fast EMA (12): prices.ewm(span=12, adjust=False).mean()
# 2. Slow EMA (26): prices.ewm(span=26, adjust=False).mean()
# 3. MACD Line = Fast EMA - Slow EMA
# 4. Signal Line = MACD.ewm(span=9, adjust=False).mean()
# 5. Histogram = MACD Line - Signal Line

# Bollinger Bands Formula:
# 1. Middle Band = prices.rolling(20).mean()
# 2. Std Dev = prices.rolling(20).std()
# 3. Upper Band = Middle + (2 * Std Dev)
# 4. Lower Band = Middle - (2 * Std Dev)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Use talib for indicators | Use pandas/numpy only | This sprint | Removes C library dependency |
| Fetch data inside tools | Accept data as arguments | This sprint | Enables reusability, testability |
| Return pandas objects | Return Python primitives | This sprint | Cleaner API, JSON-serializable |

**Deprecated/outdated:**
- `import talib`: Removed from allowlist in Phase 1
- Data fetching in generated tools: To be prohibited by SYSTEM_PROMPT

## Open Questions

1. **Should SYSTEM_PROMPT include formula references?**
   - What we know: Including formulas as comments might help LLM generate correct implementations
   - What's unclear: Whether this bloats the prompt too much
   - Recommendation: Start without formulas; add if generated code has calculation errors

2. **Should yfinance stay in ALLOWED_MODULES?**
   - What we know: yfinance is currently in ALLOWED_MODULES for bootstrap tools
   - What's unclear: Whether to remove it from generated tools only via prompt, or remove from ALLOWED_MODULES entirely
   - Recommendation: Keep in ALLOWED_MODULES for bootstrap tools, use SYSTEM_PROMPT to prohibit in generated tools. The AST check won't block it, but the LLM will be instructed not to use it.

## Sources

### Primary (HIGH confidence)
- `/fin_evo_agent/src/core/llm_adapter.py` - Current SYSTEM_PROMPT, line 19-34
- `/fin_evo_agent/src/core/executor.py` - ALLOWED_MODULES, line 48-53
- `/fin_evo_agent/data/artifacts/generated/*.py` - Existing generated tools showing current patterns
- Project requirements PROMPT-03, PROMPT-04, DATA-01, DATA-02, DATA-03

### Secondary (MEDIUM confidence)
- [LLMs for Code Generation - Prompt Engineering Guide](https://www.promptingguide.ai/prompts/coding) - Prompt structuring best practices
- [Crafting Prompt Templates for Code Generation](https://dev.to/stephenc222/crafting-prompt-templates-for-code-generation-l6d) - Template structure recommendations
- [Addy Osmani's LLM Coding Workflow 2026](https://addyosmani.com/blog/ai-coding-workflow/) - Modern code generation practices

### Tertiary (LOW confidence - formulas verified against multiple sources)
- [RSI Implementation in Python](https://www.alpharithms.com/relative-strength-index-rsi-in-python-470209/) - RSI formula reference
- [MACD Implementation](https://aleksandarhaber.com/macd-moving-average-convergence-divergence-of-stock-price-time-series-in-pandas-and-python/) - MACD formula reference
- [Bollinger Bands Implementation](https://www.askpython.com/python/examples/bollinger-bands-python) - Bollinger Bands formula reference

## Metadata

**Confidence breakdown:**
- Standard stack (pandas/numpy): HIGH - Standard tools, well-documented
- Architecture patterns: HIGH - Based on existing working mock LLM output
- Pitfalls: HIGH - Based on direct analysis of existing generated tools
- Indicator formulas: MEDIUM - Multiple sources agree, but formulas may have variations

**Research date:** 2026-02-02
**Valid until:** 60 days (prompt engineering patterns are stable)

## Implementation Checklist

For the planner, the required changes are:

1. **Edit SYSTEM_PROMPT** in `src/core/llm_adapter.py`:
   - Add instruction: "Accept price data as function arguments (list or pd.Series)"
   - Add instruction: "Do NOT call yfinance, akshare, or any data API inside the function"
   - Add instruction: "Use pandas/numpy ONLY for calculations - NO talib"
   - Add instruction: "Return typed results: float for numeric, dict for structured, bool for boolean"
   - Add instruction: "Test block must use inline sample data, not API calls"
   - Add example of correct pattern
   - Remove yfinance from allowed imports list in prompt (keep in ALLOWED_MODULES for bootstrap)

2. **Verification tests**:
   - Run `python main.py --task "Calculate RSI"` and verify generated code:
     - Has `prices: list` parameter
     - Does NOT contain `import yfinance` or `yf.`
     - Does NOT contain `import talib`
     - Returns `float`
     - Test block uses inline data
