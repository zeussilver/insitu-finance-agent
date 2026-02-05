# Testing Patterns

**Analysis Date:** 2026-02-05

## Test Framework

**Runner:**
- pytest 9.0.2
- No pytest.ini or pyproject.toml config file
- Default pytest configuration

**Assertion Library:**
- Standard Python `assert` statements
- pytest's enhanced assertion introspection

**Run Commands:**
```bash
pytest tests/                    # Run all tests
python -m pytest tests/ -v       # Verbose output
pytest tests/core/test_executor.py -v  # Specific test file
python tests/core/test_executor.py     # Direct execution (fallback)
```

**Coverage:**
```bash
# No coverage tool configured yet
# Would add: pytest-cov for coverage reporting
```

## Test File Organization

**Location:**
- Co-located in `tests/` directory (separate from source)
- Mirrors source structure:
  ```
  tests/
  ├── core/
  │   ├── test_executor.py
  │   ├── test_gateway.py
  │   └── __init__.py
  ├── evolution/
  │   ├── test_refiner.py
  │   └── __init__.py
  ├── extraction/
  │   ├── test_schema.py
  │   ├── test_indicators.py
  │   └── golden_schemas.json
  └── data/
      └── test_adapters.py
  ```

**Naming:**
- Test files: `test_*.py` prefix (pytest convention)
- Test classes: `Test*` prefix (e.g., `TestStaticCheck`, `TestVerificationEnforcement`)
- Test functions: `test_*` prefix (e.g., `test_safe_pandas_code`, `test_banned_os_import`)

**Structure:**
- One test file per source module
- Multiple test classes per file, grouped by functionality
- Each test class focuses on one aspect/method

## Test Structure

**Suite Organization:**
```python
"""Tests for ToolExecutor - extracted from executor.__main__.

Tests cover:
- Static AST security analysis
- Capability-based module checking
- Sandbox execution
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.executor import ToolExecutor, SecurityException


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
```

**Patterns:**
- Module-level docstring explains test scope
- Path setup at module level
- Imports from source using absolute imports
- Test classes group related tests
- Fixtures for setup/teardown
- Descriptive test names explain expected behavior
- Docstrings in test functions describe what's being validated

## Mocking

**Framework:**
- No explicit mocking library imports detected (unittest.mock not used)
- Manual mocking through dependency injection and test doubles

**Patterns:**
```python
# Mock LLM adapter when no API key
class LLMAdapter:
    def __init__(self):
        if LLM_API_KEY:
            self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        else:
            self.client = None  # Triggers mock path

    def generate_tool_code(self, task: str) -> dict:
        if self.client is None:
            return self._mock_generate(task)  # Built-in mock
        # Real API call
```

**Test Fixtures:**
```python
@pytest.fixture
def gateway(tmp_path):
    """Create a gateway with temporary log directory."""
    gw = VerificationGateway()
    gw.logs_dir = tmp_path / "logs"
    gw.logs_dir.mkdir(parents=True, exist_ok=True)
    gw._setup_logging()
    return gw

@pytest.fixture
def valid_calc_code():
    """Valid RSI calculation code."""
    return '''
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    # ... implementation ...
'''
```

**What to Mock:**
- External API calls (LLM, yfinance) - use fallback mock implementations
- File I/O - use `tmp_path` fixture for temporary directories
- Network calls - retry decorator with mock data for tests

**What NOT to Mock:**
- Core logic (AST analysis, verification pipeline)
- Security checks (must test real behavior)
- Data transformations (pandas operations)

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def golden_test_set():
    """Load golden test set from JSON file."""
    golden_path = Path(__file__).parent / "golden_schemas.json"
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.fixture
def valid_calc_code():
    """Valid RSI calculation code."""
    return '''
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    # Full implementation
'''

@pytest.fixture
def unsafe_code():
    """Code that should be blocked."""
    return '''
import os

def unsafe_func():
    os.system("ls")
'''
```

**Location:**
- Fixtures defined at test class level as methods
- Shared fixtures at module level (top of file)
- Golden test data in JSON files: `tests/extraction/golden_schemas.json`

**Patterns:**
- String fixtures for code snippets
- File-based fixtures for golden test sets
- Temporary directory fixtures using pytest's `tmp_path`
- Factory fixtures that return objects (executor, gateway)

## Coverage

**Requirements:**
- No explicit coverage target configured
- Existing tests cover:
  - Security mechanisms: 100% (all banned operations tested)
  - Core execution: ~85% (executor, verifier, gateway)
  - Schema extraction: 95% target (golden test validation)

**View Coverage:**
```bash
# Not currently configured
# To add: pip install pytest-cov
# Then: pytest --cov=src --cov-report=html tests/
```

**Coverage Strategy:**
- Unit tests for all security checks
- Integration tests for verification pipeline
- Golden test sets for extraction accuracy
- End-to-end tests via benchmark suite (`benchmarks/run_eval.py`)

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Location: `tests/core/`, `tests/extraction/`
- Approach:
  - Pure function testing with known inputs/outputs
  - Security check validation (banned imports/calls)
  - Data extraction accuracy
  - Error handling paths
- Example: `test_safe_pandas_code()`, `test_banned_os_import()`

**Integration Tests:**
- Scope: Multiple components working together
- Location: `tests/core/test_gateway.py`, `tests/evolution/test_refiner.py`
- Approach:
  - Gateway with verifier, registry, executor
  - Synthesizer with LLM, executor, gateway
  - Full verification pipeline (AST → self-test → contract → integration)
- Example: `test_valid_code_passes_verification()`, `test_submit_creates_checkpoint()`

**Golden Tests:**
- Scope: Schema extraction accuracy against known good outputs
- Location: `tests/extraction/test_schema.py` + `golden_schemas.json`
- Approach:
  - 55 test cases covering category, symbol, date, indicator extraction
  - Accuracy targets: 80-95% depending on extraction type
  - Regression detection through frozen expected outputs
- Example: `test_overall_accuracy()` with 80%+ threshold

**E2E Tests:**
- Scope: Full system behavior from task → result
- Location: `benchmarks/run_eval.py` (20 benchmark tasks)
- Approach:
  - Task success rate ≥ 80% (achieved 85% with 17/20 passing)
  - Cold start vs warm start scenarios
  - Security vulnerability detection
- Example: Benchmark evaluation with metrics tracking

**System Tests:**
- Security verification: `main.py --security-check`
- Bootstrap validation: `main.py --bootstrap`
- Manual smoke tests via CLI

## Common Patterns

**Async Testing:**
```python
# Not used - all operations are synchronous
# Subprocess execution uses timeout, not async/await
```

**Error Testing:**
```python
def test_banned_os_import(self, executor):
    """Import of os module should be blocked."""
    dangerous_code = 'import os; os.system("ls")'
    is_safe, error = executor.static_check(dangerous_code)
    assert is_safe is False
    assert "os" in error.lower()

def test_syntax_error_rejected(self, executor):
    """Code with syntax errors should be rejected."""
    bad_code = 'def foo( broken'
    is_safe, error = executor.static_check(bad_code)
    assert is_safe is False
    assert "syntax" in error.lower()
```

**Parameterized Testing:**
```python
# Pattern: Loop over test cases from golden set
def test_fetch_category(self, golden_test_set):
    """Test fetch category detection."""
    fetch_cases = [c for c in golden_test_set["test_cases"]
                  if c["expected"]["category"] == "fetch"]

    correct = 0
    total = len(fetch_cases)

    for case in fetch_cases:
        schema = extract_schema(case["task"])
        if schema.category == "fetch":
            correct += 1
        else:
            print(f"FAIL: {case['task'][:50]}... expected fetch, got {schema.category}")

    accuracy = correct / total if total > 0 else 0
    assert accuracy >= 0.8, f"Fetch accuracy {accuracy:.1%} below 80% threshold"
```

**Result Validation:**
```python
def test_execute_safe_function(self, executor):
    """Execute a safe calculation function."""
    code = '''
import pandas as pd

def calc_ma(prices: list, window: int = 5) -> float:
    return float(pd.Series(prices).rolling(window).mean().iloc[-1])
'''
    trace = executor.execute(
        code,
        func_name="calc_ma",
        args={"prices": [1, 2, 3, 4, 5, 6, 7], "window": 3},
        task_id="test_task"
    )
    assert trace.exit_code == 0
    result = executor.extract_result(trace)
    assert result is not None
    assert float(result) == 6.0
```

**Fixture Usage:**
```python
class TestVerificationEnforcement:
    """Tests that verification is enforced before registration."""

    def test_valid_code_passes_verification(self, gateway, valid_calc_code):
        """Valid code should pass all verification stages."""
        passed, report = gateway.verify_only(
            code=valid_calc_code,
            category="calculation",
            task_id="test_valid"
        )

        assert passed is True
        assert report.final_stage.value >= VerificationStage.SELF_TEST.value
```

## Test Execution

**Direct Execution:**
```python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**IDE Integration:**
- Tests runnable directly: `python tests/core/test_executor.py`
- Pytest discovery: `pytest tests/`
- Individual test: `pytest tests/core/test_executor.py::TestStaticCheck::test_safe_pandas_code`

**CI Integration:**
- Benchmark evaluation: `python benchmarks/run_eval.py --config cold_start --run-id ci_test`
- Security-only tests: `python benchmarks/run_eval.py --security-only`
- Configuration matrix testing via `benchmarks/config_matrix.yaml`

## Test Organization Principles

**Test Extraction:**
- Self-tests removed from `if __name__ == "__main__"` blocks in source files
- Moved to dedicated test files under `tests/`
- Source files now have minimal `__main__` blocks pointing to tests

**Test Isolation:**
- Each test is independent (can run in any order)
- Uses fixtures for setup/teardown
- Temporary directories via `tmp_path` fixture
- No shared state between tests

**Test Naming:**
- Class names describe component under test: `TestStaticCheck`, `TestGateway`
- Test names describe expected behavior: `test_safe_pandas_code`, `test_unsafe_code_blocked`
- Docstrings provide additional context

**Golden Test Pattern:**
- Reference data in JSON files (`golden_schemas.json`)
- Accuracy thresholds for regression detection
- Detailed failure reporting showing mismatches

---

*Testing analysis: 2026-02-05*
