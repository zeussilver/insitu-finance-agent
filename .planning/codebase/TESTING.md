# Testing Patterns

**Analysis Date:** 2026-02-03

## Test Framework

**Runner:**
- No formal test framework detected (no pytest, unittest configuration)
- Manual testing through:
  - `if __name__ == "__main__":` blocks in modules
  - `benchmarks/run_eval.py` evaluation suite
  - `main.py --security-check` command

**Assertion Library:**
- Built-in `assert` statements
- No external assertion library (pytest, unittest.mock)

**Run Commands:**
```bash
python main.py --security-check     # Verify security mechanisms
python benchmarks/run_eval.py       # Run benchmark evaluation
python src/core/executor.py         # Test executor module
python src/core/verifier.py         # Test verifier module
python src/core/capabilities.py     # Test capability system
```

## Test File Organization

**Location:**
- Inline tests in `if __name__ == "__main__":` blocks within source files
- Evaluation suite: `benchmarks/run_eval.py`, `benchmarks/compare_runs.py`
- Task definitions: `benchmarks/tasks.jsonl`
- No separate `tests/` directory

**Naming:**
- No dedicated test files (`test_*.py` or `*_test.py`)
- Test data in JSONL: `benchmarks/tasks.jsonl`, `benchmarks/security_tasks.jsonl`
- Results stored: `benchmarks/results/*.json`

**Structure:**
```
fin_evo_agent/
├── src/
│   └── core/
│       └── executor.py          # Contains tests in __main__
├── benchmarks/
│   ├── run_eval.py              # Evaluation suite
│   ├── compare_runs.py          # Result comparison
│   ├── tasks.jsonl              # 20 benchmark tasks
│   └── results/                 # Test results
```

## Test Structure

**Suite Organization:**
```python
if __name__ == "__main__":
    # Test 1: Safe code
    safe_code = '''...'''
    is_safe, error = executor.static_check(safe_code)
    print(f"Safe code check: is_safe={is_safe}")

    # Test 2: Dangerous code
    dangerous_codes = [...]
    for code in dangerous_codes:
        is_safe, error = executor.static_check(code)
        print(f"  {code[:30]}... -> blocked={not is_safe}")

    # Test 3: Execute safe code
    trace = executor.execute(safe_code, "verify_only", {}, "test_task")
    print(f"Exit code: {trace.exit_code}")
```

**Patterns:**
- Multiple test cases in sequence
- Print-based output verification
- Manual inspection of results
- Example from `src/core/verifier.py`:
  ```python
  # Test with contract
  passed, report = verifier.verify_all_stages(
      code=test_code,
      category="calculation",
      task_id="test_001",
      contract=contract
  )

  print(f"Verification result: {'PASS' if passed else 'FAIL'}")
  for stage in report.stages:
      print(f"  {stage.stage.name}: {stage.result.value}")
  ```

## Mocking

**Framework:** No mocking framework

**Patterns:**
- Conditional mock responses when API key not present
- Mock LLM responses in `src/core/llm_adapter.py`:
  ```python
  def generate_tool_code(self, task: str, error_context: Optional[str] = None) -> dict:
      if self.client is None:
          # Mock only when no API key configured
          raw_response = self._mock_generate(task, category)
      else:
          # Real API call
          completion = self.client.chat.completions.create(...)
  ```
- Sample data generation for testing:
  ```python
  sample_prices = [10, 12, 11, 13, 15, 17, 16, 15, 14, 13, 14, 15, 16, 17, 18]
  test_args = {"prices": sample_prices, "period": 14}
  ```

**What to Mock:**
- LLM API calls when no API key configured
- Network requests (implicitly via cache)
- Test runs default to mock mode

**What NOT to Mock:**
- AST security validation (always real)
- Subprocess execution (always sandboxed)
- Core logic and algorithms

## Fixtures and Factories

**Test Data:**
```python
# From benchmarks/tasks.jsonl - structured test cases
{
    "task_id": "calc_rsi",
    "query": "计算 RSI 相对强弱指标",
    "category": "calculation",
    "contract_id": "calc_rsi",
    "expected_output": {
        "type": "numeric",
        "value": 65.0,
        "tolerance": 0.1
    }
}

# Inline sample data in verifier
sample_prices = [100.0, 101.5, 99.8, 102.3, 101.0, ...]
sample_volumes = [1000000, 1100000, 950000, ...]
```

**Location:**
- JSONL files: `benchmarks/tasks.jsonl`
- Inline in test functions: `src/core/verifier.py:_generate_test_args()`
- No centralized fixture repository

## Coverage

**Requirements:** No coverage tracking configured

**View Coverage:**
- Not available
- Manual inspection through evaluation results
- Success rate metrics in `benchmarks/run_eval.py`

**Current Metrics (from Architecture Overhaul):**
- Target: 90%+ task success rate
- Security Block Rate: 100% (verified)
- Tool Reuse Rate: ≥30% target

## Test Types

**Unit Tests:**
- Inline module tests in `if __name__ == "__main__":`
- Scope: Individual functions and classes
- Example from `src/core/executor.py`:
  ```python
  if __name__ == "__main__":
      executor = ToolExecutor()

      # Test 1: Safe code
      safe_code = '''...'''
      is_safe, error = executor.static_check(safe_code)

      # Test 2: Dangerous code
      dangerous_codes = [...]
      for code in dangerous_codes:
          is_safe, error = executor.static_check(code)
  ```

**Integration Tests:**
- Multi-stage verification pipeline tests tool integration
- Stage 4 (INTEGRATION) in `src/core/verifier.py`:
  ```python
  def _verify_integration(self, code: str, func_name: str, real_data: Dict[str, Any], task_id: str):
      """Stage 4: Verify with real data (fetch tools only)."""
      trace = self.executor.execute(code, func_name, real_data, task_id)
      # Validate against real yfinance data
  ```

**E2E Tests:**
- Evaluation suite: `benchmarks/run_eval.py`
- Full workflow: task → synthesis → verification → execution → judgment
- 20 benchmark tasks covering fetch, calculation, and composite categories
- Result tracking: `benchmarks/results/*.json`

**Security Tests:**
- Dedicated security verification: `main.py --security-check`
- Dangerous code patterns: `benchmarks/security_tasks.jsonl`
- AST-level validation tests in `src/core/executor.py`

## Common Patterns

**Self-Test Pattern (Generated Tools):**
```python
def calc_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI indicator."""
    # ... implementation ...
    return float(rsi.iloc[-1])

if __name__ == "__main__":
    # Test case 1: Normal data
    test_prices = [44, 44.5, 44.25, 43.75, 44.5, ...]
    result = calc_rsi(test_prices, 5)
    assert 0 <= result <= 100

    # Test case 2: Edge case
    short_prices = [10, 11]
    result2 = calc_rsi(short_prices, 14)
    assert result2 == 50.0

    print("Tests passed!")
```

**Verification Pipeline Pattern:**
```python
# From src/core/verifier.py
passed, report = verifier.verify_all_stages(
    code=code,
    category=category,
    task_id=task_id,
    contract=contract
)

for stage in report.stages:
    if stage.result == VerificationResult.FAIL:
        print(f"Failed at {stage.stage.name}: {stage.message}")
```

**Async Testing:**
- Not used (no async/await patterns in codebase)

**Error Testing:**
```python
# Security violation testing
dangerous_codes = [
    'import os; os.system("ls")',
    'import subprocess; subprocess.run(["ls"])',
    'eval("1+1")',
]

all_blocked = True
for code in dangerous_codes:
    is_safe, error = executor.static_check(code)
    if is_safe:
        all_blocked = False

if all_blocked:
    print("[Pass] All dangerous operations blocked!")
```

**Contract Validation Testing:**
```python
# From src/core/verifier.py
def _validate_output(self, output: Optional[str], contract: ToolContract) -> Tuple[bool, str]:
    """Validate output matches contract constraints."""
    if contract.output_type == OutputType.NUMERIC:
        return self._validate_numeric(output, contract)
    elif contract.output_type == OutputType.DICT:
        return self._validate_dict(output, contract)
    # ... more output types
```

**Retry Testing Pattern:**
```python
# From src/core/verifier.py - integration test with retry
for attempt in range(max_retries + 1):
    trace = self.executor.execute(code, func_name, real_data, task_id)
    if trace.exit_code != 0:
        network_errors = ['timeout', 'connection', 'network', '503', '504']
        is_network_error = any(err in stderr_lower for err in network_errors)
        if is_network_error and attempt < max_retries:
            time.sleep(1.0 * (attempt + 1))
            continue
    # ... success path
```

## Evaluation Framework

**Benchmark Structure:**
- Tasks defined in JSONL: `benchmarks/tasks.jsonl`
- Three-state results: PASS, FAIL, ERROR
- Judging functions: `numeric_match()`, `list_match()`, `struct_match()`, `boolean_match()`

**Metrics Tracked:**
```python
# From benchmarks/run_eval.py
{
    "task_success_rate": pass_count / total,
    "tool_reuse_rate": reuse_count / total,
    "security_block_rate": 1.0,
    "pass_count": pass_count,
    "fail_count": fail_count,
    "error_count": error_count
}
```

**Result Classification:**
```python
class ResultState:
    PASS = "pass"    # Task completed successfully
    FAIL = "fail"    # Logic failure (wrong output)
    ERROR = "error"  # External error (API, timeout, network)
```

**Test Execution:**
```bash
# Run evaluation with fresh registry
python benchmarks/run_eval.py --clear-registry --run-id fresh_run

# Compare two runs
python benchmarks/compare_runs.py run1 run2

# Security-only evaluation
python benchmarks/run_eval.py --security-only
```

---

*Testing analysis: 2026-02-03*
