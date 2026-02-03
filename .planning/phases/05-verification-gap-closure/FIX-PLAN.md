# Benchmark Failure Fix Plan (Round 2)

## Benchmark Results Summary
- **Previous Run**: 60% (12/20)
- **Current Run**: 75% (15/20) - Target: 80%+
- **Improvement**: +15% (calculation tasks now at 100%)
- **Remaining Failures**: 5 tasks (3 fetch, 2 composite)

---

## Root Cause Analysis (Updated 2026-02-03)

### Issue 1: Financial Parameter Extraction Missing
**Affected Tasks**: fetch_001, fetch_003

**Problem**: TaskExecutor's `_extract_task_params()` method only extracts calculation-specific parameters (RSI period, MACD params, etc.) but NOT financial query parameters.

**Evidence**:
- fetch_001: "Get AAPL 2023 Q1 net income"
  - Tool expects: `get_net_income(symbol: str, year: int, quarter: int)`
  - TaskExecutor provides: `{'symbol': 'AAPL', 'prices': [...], ...}` - NO `year` or `quarter`

- fetch_003: "Get GOOGL 2023 total revenue"
  - Tool expects: `get_total_revenue(symbol: str, year: int)`
  - TaskExecutor provides: `{'symbol': 'GOOGL', 'prices': [...], ...}` - NO `year`

**Root Cause Location**: `src/core/task_executor.py:380-418` (`_extract_task_params` method)

**Fix**:
```python
# Add to _extract_task_params():

# Extract year from query (e.g., "2023", "2024")
year_match = re.search(r'\b(20\d{2})\b', query)
if year_match:
    params['year'] = int(year_match.group(1))

# Extract quarter from query (e.g., "Q1", "Q2", "1st quarter")
quarter_match = re.search(r'Q(\d)|(\d)(?:st|nd|rd|th)?\s*quarter', query, re.IGNORECASE)
if quarter_match:
    params['quarter'] = int(quarter_match.group(1) or quarter_match.group(2))
```

---

### Issue 2: urllib3 Import in LLM-Generated Code
**Affected Task**: fetch_007

**Problem**: LLM generates code with `import urllib3` to suppress yfinance SSL warnings, but `urllib3` is blocked by security policy.

**Evidence**:
- Security log: `[SECURITY] Unallowed import from: urllib3`
- Refiner aborts immediately (Unallowed import is in UNFIXABLE_ERRORS)

**Root Cause**: LLM prompt doesn't explicitly forbid urllib3 or suggest using `warnings` module instead.

**Fix Location**: `src/core/llm_adapter.py` (FETCH_SYSTEM_PROMPT)

**Fix**:
```python
# Add to FETCH_SYSTEM_PROMPT:
"- FORBIDDEN: urllib3, requests, aiohttp, httpx (yfinance handles all network I/O)"
"- For warning suppression, use: import warnings; warnings.filterwarnings('ignore')"
```

---

### Issue 3: Volume Parameter Name Mismatch
**Affected Task**: comp_002

**Problem**: TaskExecutor passes `volume` (singular) but tool expects `volumes` (plural).

**Evidence**:
- Contract `comp_divergence` requires: `{"prices": "list", "volumes": "list"}`
- Tool signature: `calculate_volume_price_divergence(prices: list, volumes: list, period: int)`
- TaskExecutor provides: `{'prices': [...], 'volume': [...]}` - singular `volume`!

**Root Cause Location**: `src/core/task_executor.py:358-373` (`prepare_calc_args` standard case)

**Fix**:
```python
# Add special case before standard args preparation:
if 'divergence' in query:
    args = {
        'prices': data.get('close', []),
        'volumes': data.get('volume', []),  # Map singular to plural
    }
    args.update(self._extract_task_params(task))
    return args
```

---

### Issue 4: Portfolio Parameter Name Mismatch
**Affected Task**: comp_003

**Problem**: TaskExecutor passes symbol names as keys (`AAPL`, `GOOGL`, `AMZN`) but tool expects numbered params (`prices1`, `prices2`, `prices3`).

**Evidence**:
- Tool signature: `calculate_equal_weight_portfolio_return(prices1: list, prices2: list, prices3: list, period: int)`
- TaskExecutor provides: `{'AAPL': [...], 'GOOGL': [...], 'AMZN': [...]}`
- COMPOSITE_SYSTEM_PROMPT says: "use prices1, prices2, prices3" but TaskExecutor doesn't comply

**Root Cause Location**: `src/core/task_executor.py:308-320` (portfolio branch in `prepare_calc_args`)

**Fix**:
```python
# Replace portfolio branch:
elif 'portfolio' in query:
    args = {}
    price_index = 1
    for key, value in data.items():
        if isinstance(value, list) and key not in ('symbols', 'dates'):
            args[f'prices{price_index}'] = value  # Convert to prices1, prices2, prices3
            price_index += 1
    args.update(self._extract_task_params(task))
    return args
```

---

## Fix Implementation Plan

### Window 1: Financial Parameter Extraction
**File**: `src/core/task_executor.py`
**Method**: `_extract_task_params()`
- Add regex patterns for `year` extraction
- Add regex patterns for `quarter` extraction
- **Fixes**: fetch_001, fetch_003

### Window 2: LLM Prompt Update (urllib3)
**File**: `src/core/llm_adapter.py`
**Section**: FETCH_SYSTEM_PROMPT
- Add explicit urllib3/requests/aiohttp ban
- Add guidance to use `warnings` module instead
- **Fixes**: fetch_007

### Window 3: Divergence Task Parameter Mapping
**File**: `src/core/task_executor.py`
**Method**: `prepare_calc_args()`
- Add special case for divergence tasks
- Map `volume` → `volumes` (singular to plural)
- **Fixes**: comp_002

### Window 4: Portfolio Task Parameter Mapping
**File**: `src/core/task_executor.py`
**Method**: `prepare_calc_args()`
- Fix portfolio branch to use numbered parameters
- Map symbol keys to `prices1`, `prices2`, `prices3`
- **Fixes**: comp_003

---

## Expected Impact

| Issue | Tasks Fixed | New Pass Count |
|-------|-------------|----------------|
| Financial params | fetch_001, fetch_003 | +2 |
| urllib3 ban | fetch_007 | +1 |
| Volume plural | comp_002 | +1 |
| Portfolio params | comp_003 | +1 |

**Current**: 15/20 (75%)
**Projected**: 20/20 (100%) or 19/20 (95%)

---

## Verification Steps

1. Apply all 4 fixes
2. Clear registry and run benchmark:
   ```bash
   python benchmarks/run_eval.py --clear-registry --run-id round2_fix_verification
   ```
3. Expected: ≥80% pass rate (16/20), 0 regressions
4. Target: 95-100% pass rate

---

## Key Code Locations Summary

| File | Line | Method/Section | Issue |
|------|------|----------------|-------|
| `task_executor.py` | 380-418 | `_extract_task_params()` | Missing year/quarter extraction |
| `task_executor.py` | 358-373 | `prepare_calc_args()` standard | volume → volumes mapping |
| `task_executor.py` | 308-320 | `prepare_calc_args()` portfolio | Symbol keys → numbered params |
| `llm_adapter.py` | 98-158 | `FETCH_SYSTEM_PROMPT` | Missing urllib3 ban |

---

## Compaction Preservation

When context is compacted, preserve:
- 5 failures: fetch_001, fetch_003, fetch_007, comp_002, comp_003
- 4 fixes needed: financial params, urllib3 ban, volume plural, portfolio params
- Target: 80%+ pass rate
- Command: `python benchmarks/run_eval.py --clear-registry --run-id round2_fix_verification`
