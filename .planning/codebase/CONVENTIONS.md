# Coding Conventions

**Analysis Date:** 2026-02-03

## Naming Patterns

**Files:**
- Snake_case for modules: `llm_adapter.py`, `task_executor.py`, `data_proxy.py`
- No file extensions except `.py`
- Main entry point: `main.py`
- Bootstrap code in `bootstrap.py`, generated code in `generated/`

**Functions:**
- Snake_case: `get_stock_hist()`, `calc_rsi()`, `extract_function_name()`
- Prefix conventions:
  - `get_` for data fetching: `get_stock_hist()`, `get_financial_info()`
  - `calc_` for calculations: `calc_rsi()`, `calc_ma()`, `calc_bollinger()`
  - `check_` for boolean conditions: `check_trading_signal()`
  - `extract_` for parsing: `extract_function_name()`, `extract_indicator()`
  - `_validate_` for validation helpers: `_validate_numeric()`, `_validate_dict()`
  - Private methods with single underscore: `_clean_protocol()`, `_infer_category()`

**Variables:**
- Snake_case: `tool_name`, `func_name`, `exit_code`, `std_err`
- Constants in UPPERCASE: `BANNED_MODULES`, `ALLOWED_MODULES`, `RETRY_MAX_ATTEMPTS`
- Boolean flags with `is_`/`has_` prefix: `is_safe`, `has_error`

**Classes:**
- PascalCase: `ToolExecutor`, `LLMAdapter`, `Synthesizer`, `MultiStageVerifier`
- Descriptive noun phrases: `ToolArtifact`, `ExecutionTrace`, `ErrorReport`
- Enums also use PascalCase: `ToolStatus`, `Permission`, `VerificationStage`

**Types:**
- Enums inherit from `str, Enum` pattern for JSON serialization
- Example: `class ToolStatus(str, Enum):`
- TypeVar usage: `T = TypeVar('T')`

## Code Style

**Formatting:**
- No automated formatter detected (no `.prettierrc`, `.black`, or `pyproject.toml`)
- Manual style conventions observed:
  - 4-space indentation
  - Maximum line length ~100-120 characters (not enforced)
  - Blank line between class methods
  - Two blank lines between top-level definitions

**Linting:**
- No linter configuration files detected (no `.pylintrc`, `.flake8`, `pyproject.toml`)
- Style enforced through code review

**Docstrings:**
- Google-style docstrings used consistently
- Triple-quoted strings with `"""`
- Format:
  ```python
  def function_name(arg1: type, arg2: type) -> return_type:
      """Brief description.

      Args:
          arg1: Description
          arg2: Description

      Returns:
          Description of return value
      """
  ```
- Module-level docstrings in all files
- Class docstrings describe purpose and responsibilities

## Import Organization

**Order:**
1. Standard library imports (grouped)
2. Third-party imports (pandas, numpy, yfinance, sqlmodel)
3. Local imports with sys.path manipulation
4. Example from `src/core/executor.py`:
   ```python
   import ast
   import json
   import subprocess
   import sys
   import tempfile

   import sys as _sys
   _sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
   from src.config import EXECUTION_TIMEOUT_SEC
   from src.core.models import ExecutionTrace
   ```

**Path Aliases:**
- No path aliases configured
- Uses dynamic path insertion: `sys.path.insert(0, str(__file__).rsplit("/", 3)[0])`
- All imports use absolute paths from project root: `from src.config import ...`

**Import Style:**
- Explicit imports preferred: `from src.core.models import ToolArtifact, ExecutionTrace`
- Module imports when many symbols: `import pandas as pd`, `import numpy as np`
- Avoid wildcard imports (no `from module import *` observed)

## Error Handling

**Patterns:**
- Try-except blocks with specific exception types
- Return values over exceptions for expected failures:
  - `None` for data not found
  - Empty DataFrame for failed queries
  - Tuple of `(is_safe, error_message)` for validation
- Custom exceptions for security: `class SecurityException(Exception):`
- Execution results use structured traces rather than raising exceptions

**Example pattern from `src/core/executor.py`:**
```python
def static_check(self, code: str) -> Tuple[bool, Optional[str]]:
    """Returns (is_safe, error_message) instead of raising"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    # ... validation logic ...
    return True, None
```

**Example from `src/finance/data_proxy.py`:**
```python
try:
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end)
    if df.empty:
        return None  # Expected failure returns None
    return df
except Exception:
    return None  # Network errors also return None
```

## Logging

**Framework:** `print()` statements (no logging framework)

**Patterns:**
- Structured prefixes: `[Step 1]`, `[Synthesizer]`, `[Retry]`, `[SECURITY]`
- Progress indicators: `print(f"[Synthesizer] Generating code for: {task}")`
- Error logging to stderr: `print(f"[SECURITY] {violation}", file=sys.stderr)`
- File-based security logs: `data/logs/security_violations.log`
- Thinking process logs: `data/logs/thinking_process/`

**Security Violation Logging Pattern:**
```python
def _log_security_violation(self, violation: str, task_id: str = "unknown"):
    # Log to stderr
    print(f"[SECURITY] {violation}", file=sys.stderr)
    # Log to file
    log_path = logs_dir / "security_violations.log"
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().isoformat()} | {task_id} | {violation}\n")
```

## Comments

**When to Comment:**
- Complex algorithms: RSI calculation logic
- Security-critical sections: AST validation rules
- Non-obvious design decisions: "Metadata in DB, Payload on Disk"
- TODO markers: Not observed in current codebase

**JSDoc/Pydoc:**
- Comprehensive function docstrings (Google style)
- Type hints provide inline documentation
- Module-level docstrings explain architecture
- Example from `src/evolution/synthesizer.py`:
  ```python
  """Tool Synthesizer: Generate → Verify → Register → Refine

  The core evolution loop:
  1. Call LLM to generate tool code from task description
  2. Multi-stage verification (AST, self-test, contract, integration)
  3. If passed all stages, register to database and disk
  4. If failed, call Refiner for error repair
  """
  ```

## Function Design

**Size:**
- Functions typically 20-50 lines
- Helper methods extracted for readability
- Example: `_validate_numeric()`, `_validate_dict()` separated from `_validate_output()`

**Parameters:**
- Type hints required: `def calc_rsi(prices: list, period: int = 14) -> float:`
- Default values for optional params: `period: int = 14`
- Keyword arguments preferred for clarity
- Dict/JSON for complex inputs: `args: dict`, `config: Dict[str, Any]`

**Return Values:**
- Explicit type hints: `-> float`, `-> Tuple[bool, Optional[str]]`, `-> ExecutionTrace`
- Tuples for multiple values: `(is_safe, error_message)`
- None for failure cases rather than exceptions
- Structured objects for complex returns: `ExecutionTrace`, `VerificationReport`

## Module Design

**Exports:**
- No explicit `__all__` declarations
- Public API through classes and top-level functions
- Private helpers prefixed with underscore

**Barrel Files:**
- Not used
- Each module imported directly: `from src.core.executor import ToolExecutor`

**Module Structure Pattern:**
```python
# Docstring
"""Module purpose and architecture notes."""

# Imports (standard, third-party, local)
import sys
from typing import ...

# Constants
CONSTANT_NAME = value

# Classes
class ClassName:
    pass

# Functions
def helper_function():
    pass

# Main execution
if __name__ == "__main__":
    # Test code or CLI entry point
```

## Type Annotations

**Usage:**
- Comprehensive type hints throughout codebase
- Function signatures: `def func(arg: type) -> return_type:`
- Complex types from `typing`: `Optional`, `Tuple`, `Dict`, `List`, `Set`
- Forward references avoided by proper import order
- SQLModel fields use `Field()` with metadata:
  ```python
  name: str = Field(index=True)
  content_hash: str = Field(index=True, unique=True)
  ```

## Security Conventions

**Critical Rules:**
- Always use AST validation before executing generated code
- Never use `eval()`, `exec()`, `__import__()` in generated tools
- Subprocess sandboxing for all code execution
- Banned modules/calls/attributes defined in constants
- Capability-based permissions per tool category

**Pattern from `src/core/executor.py`:**
```python
BANNED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'builtins',
    'importlib', 'ctypes', 'socket', 'http', 'urllib',
    # ... more
}

BANNED_CALLS = {
    'eval', 'exec', 'compile', '__import__',
    # ... more
}
```

---

*Convention analysis: 2026-02-03*
