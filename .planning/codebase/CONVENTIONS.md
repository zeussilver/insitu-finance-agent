# Coding Conventions

**Analysis Date:** 2026-02-05

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `llm_adapter.py`, `task_executor.py`)
- Test modules: `test_*.py` prefix (e.g., `test_executor.py`, `test_gateway.py`)
- Config files: `lowercase.yaml` (e.g., `constraints.yaml`)
- Main entry point: `main.py` at project root
- Init files: `__init__.py` in every package (mostly empty for namespace declaration)

**Functions:**
- Snake case with descriptive verbs: `extract_function_name()`, `static_check_with_rules()`, `get_category_modules()`
- Private functions: Leading underscore `_clean_protocol()`, `_mock_generate()`, `_log_security_violation()`
- Module-level getters: `get_*` prefix (`get_gateway()`, `get_engine()`, `get_constraints()`)
- Boolean checks: `is_*` prefix (`is_data_provider()`, `is_safe`)
- Decorators: `with_*` or `@*` pattern (`with_retry()`, `@DataProvider.reproducible`)

**Variables:**
- Snake case: `tool_name`, `exit_code`, `allowed_modules`, `std_err`
- Constants: `UPPERCASE_SNAKE` (e.g., `ALLOWED_MODULES`, `EXECUTION_TIMEOUT_SEC`, `SYSTEM_PROMPT`)
- Private attributes: Leading underscore `_constraints`, `_setup_logging()`
- Paths: `*_DIR` or `*_PATH` suffix (`ROOT_DIR`, `DB_PATH`, `CACHE_DIR`)

**Classes:**
- PascalCase: `ToolExecutor`, `LLMAdapter`, `VerificationGateway`, `MultiStageVerifier`
- Exception classes: Suffix `Exception` (`SecurityException`, `VerificationError`)
- Enum classes: PascalCase with UPPERCASE values
  ```python
  class ToolStatus(str, Enum):
      PROVISIONAL = "provisional"
      VERIFIED = "verified"
  ```

**Types:**
- Type hints use standard library and typing module
- SQLModel classes use PascalCase with `table=True`
- Dataclasses use PascalCase with `@dataclass` decorator

## Code Style

**Formatting:**
- Tool: No explicit formatter configured (follows PEP 8 manually)
- Indentation: 4 spaces (consistent throughout)
- Line length: No strict limit, but most lines under 100 chars
- String quotes: Double quotes `"` preferred, single quotes `'` for keys/internal strings
- Trailing commas: Used in multi-line collections

**Docstrings:**
- Triple double-quotes `"""..."""`
- Module-level docstrings at file top explaining purpose
- Function docstrings with Args/Returns sections:
  ```python
  def calc_rsi(prices: list, period: int = 14) -> float:
      """Calculate RSI indicator.

      Args:
          prices: List of closing prices
          period: RSI period (default 14)

      Returns:
          RSI value between 0 and 100
      """
  ```
- Class docstrings describe purpose and key methods

**Linting:**
- No explicit linter config file (`.eslintrc`, `.flake8`) detected
- Code follows PEP 8 conventions manually
- Type hints used extensively for function signatures

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports (sqlmodel, pandas, openai)
3. Local imports with path manipulation
4. Blank line between groups

**Pattern observed:**
```python
# Standard library
import re
import json
from typing import Optional, List
from pathlib import Path

# Third-party
import pandas as pd
from openai import OpenAI
from sqlmodel import SQLModel, Field

# Local (with path setup)
import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.models import ToolArtifact
from src.config import DB_URL
```

**Path Aliases:**
- No path aliases (tsconfig paths) used
- Absolute imports from `src.*` after path manipulation
- Path setup: `sys.path.insert(0, str(__file__).rsplit("/", 3)[0])` or `sys.path.insert(0, str(Path(__file__).parent.parent.parent))`

**Import Style:**
- Explicit imports: `from src.core.executor import ToolExecutor, SecurityException`
- Avoid wildcard imports `from module import *`
- Relative imports not used - always absolute after path setup

## Error Handling

**Patterns:**
- Try-except with specific error handling:
  ```python
  try:
      completion = self.client.chat.completions.create(...)
      raw_response = completion.choices[0].message.content
  except Exception as e:
      print(f"[LLM Error] {e}")
      return {"code_payload": None, "error": str(e)}
  ```
- Return sentinel values rather than raising exceptions:
  - `None` for missing data
  - `0.0` for failed numeric operations
  - Empty string `""` for failed string operations
  - Exit codes: `0` = success, `1` = error, `124` = timeout

**Custom Exceptions:**
- `SecurityException` for AST security violations
- `VerificationError` for gateway failures
- Raised explicitly: `raise SecurityException("Banned import: os")`

**Validation:**
- Early returns for invalid input:
  ```python
  if len(prices) < period + 1:
      return 50.0  # Return neutral value
  ```
- Assertion in tests: `assert result > 0, "AAPL should have positive market cap"`

## Logging

**Framework:** Print statements (no structured logging framework detected)

**Patterns:**
- Prefixed log messages: `[Component] Message`
- Examples:
  - `print(f"[Synthesizer] Generating code for: {task}")`
  - `print(f"[SECURITY] {violation}", file=sys.stderr)`
  - `print("[Step 1] Preparing context data...")`
- File logging for security violations: `data/logs/security_violations.log`
- Structured JSONL for gateway attempts: `data/logs/gateway_attempts.jsonl`

**Log Levels:**
- Info: `[Component] Action`
- Error: `print(..., file=sys.stderr)`
- Security: `[SECURITY] Violation details`

**When to Log:**
- Component entry/exit points
- Key state transitions (synthesis, verification, registration)
- Errors and security violations
- Test pass/fail results

## Comments

**When to Comment:**
- Critical security constraints with visual separators:
  ```python
  # ═══════════════════════════════════════════
  # CRITICAL CONSTRAINT - READ CAREFULLY
  # ═══════════════════════════════════════════
  ```
- Complex algorithms explaining logic:
  ```python
  # Calculate RSI: RS = avg_gain / avg_loss
  # RSI = 100 - 100 / (1 + RS)
  ```
- TODO/FIXME markers (avoided in this codebase - implementation complete)
- Section dividers in long files:
  ```python
  # --- Table 1: ToolArtifact ---
  # --- Multi-Stage Verification ---
  ```

**Comment Style:**
- Full sentences with proper capitalization
- Inline comments: `#` followed by space
- Block comments above code, not at end of line
- No commented-out code (clean implementation)

**JSDoc/TSDoc:**
- Python equivalent: Docstrings (not JSDoc)
- Used for all public functions, classes, and modules
- Args, Returns, Raises sections where applicable

## Function Design

**Size:**
- Small focused functions: 10-50 lines typical
- Large system functions: 100-200 lines for complex logic (e.g., `synthesize()`, `execute()`)
- Self-tests moved out of `__main__` blocks into separate test files

**Parameters:**
- Type hints required: `prices: list`, `period: int = 14`, `-> float`
- Default values for optional params: `def calc_rsi(prices: list, period: int = 14)`
- Dictionary for complex args: `args: dict`, `config: Dict`
- Named parameters preferred over positional

**Return Values:**
- Explicit type hints: `-> Optional[str]`, `-> Tuple[bool, Optional[str]]`
- Tuple unpacking for multiple returns: `success, tool, report = gateway.submit(...)`
- None for failure cases: `return None, trace`
- Typed returns match function signature

**Patterns:**
- Validation at function start with early returns
- Single responsibility per function
- Pure functions for calculations (no side effects)
- Builder pattern for complex objects (`Synthesizer`, `Verifier`)

## Module Design

**Exports:**
- All public classes/functions defined in module
- No explicit `__all__` declarations
- Module-level functions and classes directly importable

**Structure:**
- Module docstring at top
- Imports
- Constants/Enums
- Classes
- Functions
- `if __name__ == "__main__":` block (often just a message pointing to tests)

**Barrel Files:**
- `__init__.py` files are mostly empty (used for namespace only)
- No re-exports or index files
- Direct imports: `from src.core.executor import ToolExecutor`

**Organization:**
- One primary class per file: `executor.py` contains `ToolExecutor`
- Related functions grouped in same module: `schema.py` has `extract_symbols()`, `extract_dates()`, etc.
- Utility modules: `constraints.py` for centralized config loading

## Architecture Patterns

**Dependency Injection:**
- Components accept dependencies in `__init__`:
  ```python
  def __init__(self, llm=None, executor=None, registry=None):
      self.llm = llm or LLMAdapter()
      self.executor = executor or ToolExecutor()
  ```

**Singleton Pattern:**
- Global gateway instance: `get_gateway()` returns singleton
- Database engine: `get_engine()` creates on demand

**Protocol Pattern:**
- `DataProvider` protocol for pluggable adapters
- Type checking: `is_data_provider(obj)` validates protocol compliance

**Decorator Pattern:**
- `@with_retry` for network resilience
- `@DataProvider.reproducible` for caching
- Custom decorators with retry logic and exponential backoff

**Enum Pattern:**
- String enums for status values: `class ToolStatus(str, Enum)`
- Integer enums for stages: `class VerificationStage(int, Enum)`

## Security Conventions

**AST Analysis:**
- All code passes through `static_check()` before execution
- Capability-based rules loaded from `configs/constraints.yaml`
- Banned modules/calls/attributes enforced at parse time

**Subprocess Isolation:**
- All tool execution in subprocess with timeout
- JSON IPC for parameter passing (avoids eval)
- Temp directories for sandboxing

**No Dynamic Execution:**
- Never use `eval()` or `exec()` in production code
- Runner script uses `eval()` only in isolated subprocess
- All parameters validated before passing to subprocess

---

*Convention analysis: 2026-02-05*
