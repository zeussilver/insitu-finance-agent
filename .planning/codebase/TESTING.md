# Testing Patterns

**Analysis Date:** 2026-02-06

## Test Framework

**Runner:**
- pytest (version unspecified in requirements.txt, installed implicitly)
- Config: No explicit `pytest.ini` or `pyproject.toml` config detected
- `.pytest_cache/` directory present, confirming pytest usage

**Assertion Library:**
- pytest built-in assertions
- Standard Python `assert` statements throughout

**Run Commands:**
```bash
python -m pytest tests/                    # Run all tests
python -m pytest tests/core/               # Run core module tests
python -m pytest tests/ -v                 # Verbose mode
python -m pytest tests/extraction/ -v      # Specific module with details
python main.py --security-check            # Manual security verification (not pytest)
```

**Test Organization:**
- 59 tests collected across 11 test files (3 import errors observed)
- Test modules: `test_executor.py`, `test_gateway.py`, `test_refiner.py`, `test_adapters.py`, `test_schema.py`, `test_indicators.py`

## Test File Organization

**Location:**
- Separate `tests/` directory mirroring `src/` structure
- Pattern: `tests/core/`, `tests/extraction/`, `tests/data/`, `tests/evolution/`

**Naming:**
- Test files: `test_{module}.py` format
- Example: `tests/core/test_executor.py` tests `src/core/executor.py`

**Structure:**
```
tests/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── test_executor.py      # Tests ToolExecutor AST security
│   └── test_gateway.py        # Tests VerificationGateway
├── extraction/
│   ├── __init__.py
│   ├── test_schema.py         # Schema extraction tests
│   ├── test_indicators.py     # Indicator detection tests
│   └── golden_schemas.json    # Golden test data (55 test cases)
├── evolution/
│   ├── __init__.py
│   └── test_refiner.py        # Tool refinement tests
└── data/
    ├── __init__.py
    └── test_adapters.py       # DataProvider protocol tests
```

## Test Structure

**Suite Organization:**
```python
class TestStaticCheck:
    """Test static AST security analysis."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    def test_safe_pandas_code(self, executor):
        """Safe code using pandas should pass."""
        safe_code = '''
import pandas as pd
def calc_ma(prices: list, window: int = 5) -> float:
    return float(pd.Series(prices).rolling(window).mean().iloc[-1])
'''
        is_safe, error = executor.static_check(safe_code)
        assert is_safe is True
        assert error is None

    def test_banned_os_import(self, executor):
        """Import of os module should be blocked."""
        dangerous_code = 'import os; os.system("ls")'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "os" in error.lower()
```

**Patterns:**
- Class-based test organization: `class TestStaticCheck`, `class TestExecute`
- Descriptive class names indicating test focus area
- One class per major feature or behavior group
- `@pytest.fixture` for test dependencies and setup

**Naming:**
- Test methods: `test_{what_is_being_tested}`
- Descriptive names: `test_safe_pandas_code`, `test_banned_os_import`, `test_yfinance_blocked_in_calculation`
- Negative tests clearly named: `test_unsafe_code_blocked`, `test_failure_logged`

## Fixtures

**Setup Pattern:**
```python
@pytest.fixture
def executor(self):
    return ToolExecutor()

@pytest.fixture
def gateway(tmp_path):
    """Create a gateway with temporary log directory."""
    gw = VerificationGateway()
    gw.logs_dir = tmp_path / "logs"
    gw.logs_dir.mkdir(parents=True, exist_ok=True)
    gw._setup_logging()
    return gw
```

**Fixture Scope:**
- Function-scoped fixtures (default): `executor()`, `gateway()`
- No module or session-scoped fixtures observed

**Data Fixtures:**
```python
@pytest.fixture
def valid_calc_code():
    """Valid RSI calculation code."""
    return '''
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    # ... implementation
'''

@pytest.fixture
def golden_test_set():
    """Load golden test set from JSON file."""
    golden_path = Path(__file__).parent / "golden_schemas.json"
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)
```

**Teardown:**
- No explicit teardown observed
- Relies on pytest's automatic cleanup and `tmp_path` fixture

## Mocking

**Framework:** No explicit mocking library detected (unittest.mock, pytest-mock not in requirements)

**Patterns:**
- Real objects used for most tests (integration-style)
- Temporary directories via `tmp_path` fixture for isolation
- Example: `gateway.logs_dir = tmp_path / "logs"` to avoid polluting real logs

**Test Doubles:**
- Mock data adapter: `src/data/adapters/mock_adapter.py` (not a test mock, production fallback)
- Golden test data: `tests/extraction/golden_schemas.json` (55 test cases)

**What to Mock:**
- File system operations via `tmp_path` fixture
- LLM calls implicitly avoided in most tests (test pure logic)

**What NOT to Mock:**
- Core business logic: `ToolExecutor`, `VerificationGateway` used directly
- Database operations: Tests use real SQLModel/SQLite (likely in-memory or temp)
- Security checks: Real AST analysis executed to ensure correctness

## Fixtures and Factories

**Test Data:**
```python
# Inline test data in fixtures
@pytest.fixture
def valid_calc_code():
    return '''
import pandas as pd
def calc_rsi(prices: list, period: int = 14) -> float:
    # Full implementation with test assertions
'''

# External golden data
@pytest.fixture
def golden_test_set():
    golden_path = Path(__file__).parent / "golden_schemas.json"
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)
```

**Location:**
- Golden test data: `tests/extraction/golden_schemas.json`
- Inline fixtures within test files
- No separate `conftest.py` for shared fixtures observed

**Factory Pattern:**
- Not explicitly used
- Fixtures return fresh instances each time: `return ToolExecutor()`

## Coverage

**Requirements:** No coverage target enforced

**View Coverage:**
- No coverage configuration detected (.coveragerc absent)
- No coverage requirements in CI/CD

**Gaps:**
- 3 test modules have import errors (likely due to circular dependencies or missing setup)
- No integration tests for full end-to-end workflows detected

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Pattern: Test one function with various inputs
- Example: `test_safe_pandas_code()` tests `executor.static_check()` with safe code
- Coverage: Core security checks, AST analysis, contract validation

**Integration Tests:**
- Scope: Multiple components working together
- Pattern: Real VerificationGateway with real Verifier and Executor
- Example: `test_submit_valid_code()` exercises gateway → verifier → executor → registry
- No mocking of internal components

**Validation Tests:**
- Golden test sets for schema extraction
- 55 test cases in `golden_schemas.json`
- Accuracy thresholds: `assert accuracy >= 0.8` for category classification
- Example from `test_schema.py`:
  ```python
  def test_overall_accuracy(self, golden_test_set):
      """Test overall schema extraction accuracy (≥95% target)."""
      # ... run all golden tests
      assert overall_accuracy >= 0.80
  ```

**E2E Tests:**
- Not detected in test suite
- Manual E2E via `python main.py --task "..."` and benchmark suite
- Benchmark runner at `benchmarks/run_eval.py` (not pytest)

## Common Patterns

**Async Testing:**
- Not applicable - no async code detected in codebase

**Error Testing:**
```python
def test_banned_os_import(self, executor):
    """Import of os module should be blocked."""
    dangerous_code = 'import os; os.system("ls")'
    is_safe, error = executor.static_check(dangerous_code)
    assert is_safe is False
    assert "os" in error.lower()

def test_execute_dangerous_code_blocked(self, executor):
    """Dangerous code should be blocked before execution."""
    dangerous_code = 'import os; os.system("ls")'
    trace = executor.execute(dangerous_code, func_name="dangerous", args={}, task_id="test")
    assert trace.exit_code == 1
    assert "SecurityException" in trace.std_err
```

**Pattern:**
- Test both detection (static check) and prevention (execution)
- Assert on error messages for specificity
- Negative tests are first-class citizens

**Protocol Testing:**
```python
def test_mock_adapter_satisfies_protocol(self):
    """MockAdapter should satisfy DataProvider protocol."""
    adapter = MockAdapter()
    assert isinstance(adapter, DataProvider)

def test_same_interface_mock_and_yfinance(self):
    """Mock and real adapter should have identical interfaces."""
    mock_methods = set(dir(MockAdapter))
    yf_methods = set(dir(YFinanceAdapter))
    protocol_methods = {'get_historical', 'get_quote', 'get_financial_info'}
    # Assert both implement protocol methods
```

**Subprocess Testing:**
```python
def test_execute_with_timeout(self, executor):
    """Test that long-running code times out."""
    slow_code = '''
import time
def slow_func():
    time.sleep(10)
    return "done"
'''
    trace = executor.execute(
        slow_code,
        func_name="slow_func",
        args={},
        task_id="test_timeout",
        timeout_sec=1
    )
    assert trace.exit_code == 124  # timeout exit code
    assert "timeout" in trace.std_err.lower()
```

## Parametrized Tests

**Pattern:**
- Not explicitly using `@pytest.mark.parametrize`
- Instead, iterate over golden test data within test functions:
  ```python
  def test_fetch_category(self, golden_test_set):
      fetch_cases = [c for c in golden_test_set["test_cases"]
                    if c["expected"]["category"] == "fetch"]
      for case in fetch_cases:
          schema = extract_schema(case["task"])
          if schema.category != "fetch":
              print(f"FAIL: {case['task'][:50]}...")
      # Assert overall accuracy
  ```

## Test Execution

**Path Setup:**
- Every test file includes:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent.parent.parent))
  ```
- Ensures imports work from any directory

**Running Standalone:**
```python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```
- Each test file can run independently

**CI Integration:**
- Benchmark workflow in `.github/workflows/benchmark.yml`
- Runs `benchmarks/run_eval.py --config cold_start`
- No pytest in CI detected (uses custom benchmark runner)

## Assertion Patterns

**Positive Assertions:**
```python
assert is_safe is True
assert error is None
assert tool is not None
assert tool.name == "calc_rsi"
```

**Negative Assertions:**
```python
assert is_safe is False
assert "os" in error.lower()
assert tool is None
```

**Range Assertions:**
```python
assert 0 <= result <= 100, f"RSI out of range: {result}"
assert 0.0 <= schema.confidence <= 1.0
assert overall_accuracy >= 0.80
```

**Collection Assertions:**
```python
assert len(checkpoint_files) > 0
assert expected_symbols.issubset(extracted_symbols)
assert "timestamp" in entry
```

## Test Documentation

**Docstrings:**
- Every test method has a docstring explaining what it tests
- Pattern: `"""What should happen under what conditions."""`
- Examples:
  - `"""Safe code using pandas should pass."""`
  - `"""Import of os module should be blocked."""`
  - `"""MockAdapter should satisfy DataProvider protocol."""`

**Test Organization Comments:**
```python
# Test: Verification enforcement
class TestVerificationEnforcement:
    """Tests that verification is enforced before registration."""

# Test: Submit and registration
class TestSubmitMethod:
    """Tests for the gateway submit() method."""
```

## Golden Testing Pattern

**Approach:**
- 55 golden test cases in `tests/extraction/golden_schemas.json`
- Each case has `task` input and `expected` output
- Tests validate accuracy across all cases

**Example:**
```python
def test_overall_accuracy(self, golden_test_set):
    """Test overall schema extraction accuracy (≥95% target)."""
    total_checks = 0
    passed_checks = 0

    for case in test_cases:
        schema = extract_schema(case["task"])
        expected = case["expected"]

        # Check category
        total_checks += 1
        if schema.category == expected["category"]:
            passed_checks += 1

        # Check symbols if expected
        if "symbols" in expected:
            total_checks += 1
            if expected_symbols.issubset(set(schema.symbols)):
                passed_checks += 1

    overall_accuracy = passed_checks / total_checks
    assert overall_accuracy >= 0.80
```

**Thresholds:**
- Category accuracy: ≥80%
- Symbol extraction: ≥85%
- Date extraction: ≥90%
- Indicator detection: ≥85%
- Overall accuracy: ≥80% (target 95%)

## Security Testing

**AST Security Tests:**
- Test suite: `tests/core/test_executor.py::TestStaticCheck`
- Tests banned modules: `os`, `sys`, `subprocess`
- Tests banned calls: `eval`, `exec`, `__import__`
- Tests banned attributes: `__dict__`, `__globals__`

**Capability-Based Tests:**
```python
def test_calculation_cannot_use_yfinance(self, executor):
    """Calculation tools should not be able to import yfinance."""
    code = '''import yfinance as yf'''
    allowed_modules = {'pandas', 'numpy', 'datetime', 'json', 'math'}
    is_safe, error = executor.static_check_with_rules(
        code, allowed_modules=allowed_modules
    )
    assert is_safe is False
    assert "yfinance" in error.lower()

def test_fetch_can_use_yfinance(self, executor):
    """Fetch tools should be able to import yfinance."""
    code = '''import yfinance as yf'''
    allowed_modules = {'pandas', 'numpy', 'yfinance', 'hashlib'}
    is_safe, error = executor.static_check_with_rules(
        code, allowed_modules=allowed_modules
    )
    assert is_safe is True
```

**Benchmark Security Tests:**
- Separate security task set: `benchmarks/security_tasks.jsonl`
- 5 security test cases for malicious code detection
- Run via: `python benchmarks/run_eval.py --security-only`

---

*Testing analysis: 2026-02-06*
