# Testing Patterns

**Analysis Date:** 2026-01-31

## Test Framework

**Runner:**
- No formal test framework configured (pytest, unittest, vitest not present)
- Testing is manual and embedded

**Assertion Library:**
- Python built-in `assert` statements only
- No external assertion library (no pytest, unittest, or nose)

**Run Commands:**
```bash
# Run module self-tests (each module has if __name__ == "__main__" block)
python src/core/executor.py       # Test AST checking and execution
python src/core/registry.py       # Test tool registration and retrieval
python src/core/llm_adapter.py    # Test LLM protocol cleaning
python src/evolution/synthesizer.py  # Test tool synthesis workflow
python src/evolution/refiner.py   # Test error analysis and refinement

# Run evaluation benchmark suite
python benchmarks/run_eval.py --agent evolving --run-id run1
python benchmarks/run_eval.py --security-only

# Run CLI entry point for quick validation
python main.py --init             # Initialize database
python main.py --task "计算 RSI"   # End-to-end tool synthesis + execution
python main.py --security-check   # Verify security mechanisms
```

## Test File Organization

**Location:**
- Tests embedded in each source module's `if __name__ == "__main__":` block
- No separate `test/` directory
- Benchmark tasks in `benchmarks/tasks.jsonl` and `benchmarks/security_tasks.jsonl`

**Naming:**
- Test blocks use `if __name__ == "__main__":` pattern
- Test code commented as "Test case 1:", "Test case 2:"

**Structure:**
```
src/
├── core/
│   ├── executor.py          # Tests: safe_code, dangerous_codes list, execute sample
│   ├── registry.py          # Tests: registration, retrieval, deduplication
│   ├── llm_adapter.py       # Tests: protocol cleaning, code generation
│   └── models.py            # (No tests)
├── evolution/
│   ├── synthesizer.py       # Tests: synthesize() call with task
│   └── refiner.py           # Tests: refine() with failing code example
└── finance/
    └── bootstrap.py         # Tests: create_bootstrap_tools()
```

## Test Structure

**Suite Organization:**

Each module follows this pattern:
```python
if __name__ == "__main__":
    print("=== Testing [Component] ===\n")

    # Initialize if needed
    init_db()
    component = SomeClass()

    # Test case 1
    result = component.method(...)
    assert condition, f"Expected X, got {result}"
    print("Test 1 passed!")

    # Test case 2
    result2 = component.method(...)
    assert condition2, f"Expected Y, got {result2}"
    print("Test 2 passed!")
```

**Example from `src/core/executor.py` (lines 252-289):**
```python
if __name__ == "__main__":
    executor = ToolExecutor()

    # Test 1: Safe code
    safe_code = '''
import pandas as pd

def calc_ma(prices: list, window: int = 5) -> float:
    """Calculate moving average."""
    return float(pd.Series(prices).rolling(window).mean().iloc[-1])

if __name__ == "__main__":
    result = calc_ma([1, 2, 3, 4, 5, 6, 7], 3)
    assert result == 6.0, f"Expected 6.0, got {result}"
    print("Test passed!")
'''
    is_safe, error = executor.static_check(safe_code)
    print(f"Safe code check: is_safe={is_safe}, error={error}")

    # Test 2: Dangerous code list
    dangerous_codes = [
        'import os; os.system("ls")',
        'import subprocess; subprocess.run(["ls"])',
        'eval("1+1")',
    ]
    print("\nDangerous code checks:")
    for code in dangerous_codes:
        is_safe, error = executor.static_check(code)
        print(f"  {code[:30]}... -> blocked={not is_safe}")
```

## Mocking

**Framework:** None - uses actual components in tests

**Patterns:**

1. **Mock LLM Response:**
   - `src/core/llm_adapter.py` provides `_mock_generate()` method (lines 142-201)
   - Returns hardcoded RSI tool code when no API key present
   - Used fallback: `raw_response = self._mock_generate(task)` (line 118)

2. **Mock ExecutionTrace:**
   ```python
   from src.core.models import ExecutionTrace

   mock_trace = ExecutionTrace(
       trace_id=f"t_{uuid.uuid4().hex[:12]}",
       task_id="test_refine",
       input_args={},
       output_repr="",
       exit_code=1,
       std_out="",
       std_err="ZeroDivisionError: division by zero",
       execution_time_ms=100
   )
   ```
   Example: `src/evolution/refiner.py` lines 318-328

3. **Sample Data:**
   - `benchmarks/run_eval.py` uses fallback data: `[10, 12, 11, 13, 15, 17, ...]` (line 207-209)
   - Used when network unavailable: `get_a_share_hist()` falls back to sample list

**What to Mock:**
- LLM API responses (when no API_KEY env var)
- Network calls to AkShare/yfinance (use sample data or cached Parquet)
- External data sources in benchmarks

**What NOT to Mock:**
- File system operations (create directories, write tool code)
- Database operations (SQLModel/SQLite - use real in-memory or file DB)
- AST parsing and security checks (must test real code)
- Subprocess execution (must test real sandbox behavior)

## Fixtures and Factories

**Test Data:**

1. **Code Fixtures:**
   - Safe code example in `src/core/executor.py` (lines 256-267)
   - Dangerous code list in `src/core/executor.py` (lines 272-278)
   - Bootstrap tool code templates in `src/finance/bootstrap.py` (lines 24-279)

2. **Tool Fixtures:**
   - Registry test creates tool with: `test_code`, `args_schema`, `permissions` (lines 180-198 in registry.py)
   - Tool artifacts used directly from database

3. **Benchmark Tasks:**
   - Location: `benchmarks/tasks.jsonl` (20 tasks) and `benchmarks/security_tasks.jsonl` (5 tasks)
   - Format: JSON lines with `task_id`, `category`, `query`, `expected_output`
   - Example task:
     ```json
     {
       "task_id": "fetch_001",
       "category": "fetch",
       "query": "Get stock price history for AAPL",
       "expected_output": {"type": "numeric", "value": null}
     }
     ```

**Location:**
- Code fixtures inline in each test block
- Tool code templates as module-level strings in `src/finance/bootstrap.py`
- Benchmark tasks in `benchmarks/` directory

## Coverage

**Requirements:** No coverage tracking or enforcement

**View Coverage:**
- Not applicable (no coverage tools configured)
- Coverage can be estimated by running benchmarks: `benchmarks/run_eval.py`

## Test Types

**Unit Tests:**
- Scope: Individual class methods and utility functions
- Approach: Direct instantiation and method calls
- Examples:
  - `ToolExecutor.static_check()` - AST analysis for single code snippets
  - `LLMAdapter._clean_protocol()` - Response parsing
  - `ToolRegistry.register()` - Tool registration
  - `Synthesizer.extract_function_name()` - Code analysis

**Integration Tests:**
- Scope: Multi-component workflows
- Approach: Full end-to-end task execution
- Examples:
  - `Synthesizer.synthesize()` - LLM generate → AST check → verify → register
  - `Refiner.refine()` - Error analysis → patch generation → verify
  - `main.py --task` - Complete workflow from task to result

**E2E Tests:**
- Framework: `benchmarks/run_eval.py`
- 25 total tasks across 3 categories:
  - **Fetch & Lookup** (8 tasks): Data retrieval + field extraction
  - **Calculation** (8 tasks): Technical indicators (RSI, MACD, etc.)
  - **Composite** (4 tasks): Multi-tool composition
- **Security** (5 tasks): Verify dangerous operations are blocked
- Metrics measured:
  - Task Success Rate (% tasks passing)
  - Tool Reuse Rate (% reused vs created on second run)
  - Security Block Rate (% malicious code blocked)
  - Regression Rate (consistency across runs)

## Common Patterns

**Async Testing:**
- Not applicable (no async code in project)

**Error Testing:**
- Test error classification: `Refiner._classify_error()` pattern matching (lines 72-78)
- Test error recovery: `Refiner.refine()` with `max_attempts=3` (line 186)
- Test security blocking:
  ```python
  dangerous_code = 'import os; os.system("ls")'
  is_safe, error = executor.static_check(dangerous_code)
  assert not is_safe, "Should block OS imports"
  ```

**Boundary Tests:**
- Empty input handling: `calc_rsi()` with insufficient data (line 198 in llm_adapter.py)
- DataFrame operations: Check for empty DataFrames before processing (line 58 in bootstrap.py)
- Timeout testing: `subprocess.TimeoutExpired` catch in executor.py (line 218)

**Regression Tests:**
- Benchmark suite tracks tool reuse across runs
- Compare consecutive runs with `benchmarks/compare_runs.py`
- Security baseline: All 5 security tasks must be blocked in every run

---

*Testing analysis: 2026-01-31*
