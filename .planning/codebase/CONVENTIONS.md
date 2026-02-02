# Coding Conventions

**Analysis Date:** 2026-01-31

## Naming Patterns

**Files:**
- Modules use lowercase with underscores: `llm_adapter.py`, `data_proxy.py`, `synthesizer.py`
- Bootstrap/config files: `bootstrap.py`, `config.py`
- Package modules follow PEP 8: `src/core/`, `src/evolution/`, `src/finance/`

**Functions:**
- Lowercase with underscores for regular functions: `calc_rsi()`, `extract_function_name()`, `get_a_share_hist()`
- Private functions prefixed with underscore: `_clean_protocol()`, `_compute_hash()`, `_classify_error()`
- Utility functions descriptive: `extract_args_schema()`, `init_db()`, `get_engine()`

**Variables:**
- Lowercase snake_case for local variables: `start_ts`, `content_hash`, `trace_id`
- Module-level constants in UPPERCASE: `BANNED_MODULES`, `ALLOWED_MODULES`, `SYSTEM_PROMPT`, `LLM_API_KEY`
- Configuration variables uppercase: `ROOT_DIR`, `DB_PATH`, `ARTIFACTS_DIR`, `EXECUTION_TIMEOUT_SEC`

**Types:**
- Class names use PascalCase: `ToolArtifact`, `ExecutionTrace`, `ErrorReport`, `ToolExecutor`, `Synthesizer`, `Refiner`
- Enum members uppercase: `ToolStatus.PROVISIONAL`, `Permission.CALC_ONLY`, `Permission.NETWORK_READ`
- Type hints on function signatures: `def execute(self, code: str, func_name: str, args: dict, task_id: str) -> ExecutionTrace:`

## Code Style

**Formatting:**
- No explicit formatter configured (no `.pylintrc`, `.flake8`, or `pyproject.toml` detected)
- Follows implicit PEP 8 style throughout
- Line lengths vary but generally respect 100-120 character limits
- Indentation: 4 spaces consistently

**Linting:**
- No linting configuration file present
- Code assumes implicit adherence to PEP 8

## Import Organization

**Order:**
1. Standard library imports: `import os`, `import sys`, `import json`, `import subprocess`, `import ast`
2. Third-party packages: `import pandas as pd`, `import numpy as np`, `from sqlmodel import SQLModel`
3. OpenAI/LLM SDK: `from openai import OpenAI`
4. Local project imports: `from src.config import ...`, `from src.core.models import ...`

**Path Aliases:**
- Project root path insertion at module entry points:
  ```python
  import sys
  sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
  from src.config import ...
  ```
- Consistent in `config.py`, `models.py`, `executor.py`, `registry.py`, `synthesizer.py`, `refiner.py`

## Error Handling

**Patterns:**

1. **Custom Exception Classes:**
   - `SecurityException` raised in `src/core/executor.py` for AST static analysis failures
   - Used when dangerous imports/calls detected: `raise SecurityException("Banned import: {module}")`

2. **Try-Except with Logging:**
   - `try/except Exception` with print statements for visibility
   - `src/core/executor.py` catches `subprocess.TimeoutExpired` separately
   - `src/core/llm_adapter.py` catches API errors and falls back to mock: `except Exception as e: print(f"[LLM Error] {e}"); raw_response = self._mock_generate(task)`

3. **Return vs Raise:**
   - Functions return `(Optional[T], ExecutionTrace)` tuples for result + error context
   - `Synthesizer.synthesize()` returns `(None, trace)` on failure, not exception
   - `ExecutionTrace` objects carry `exit_code`, `std_err`, `std_out` for detailed error context

4. **Defensive Checks:**
   - Database operations use `if Session.exec(...).first()` pattern
   - File operations use `Path.exists()` checks before read/write
   - Type validation: `if not isinstance(df, pd.DataFrame):`

## Logging

**Framework:** `print()` statements only (no logging module)

**Patterns:**
- Prefixed with component brackets: `[Synthesizer]`, `[Refiner]`, `[System]`, `[LLM Error]`, `[Task]`
- Three-tier detail:
  ```python
  print(f"[Synthesizer] Generating code for: {task}")  # High level
  print(f"  > Loaded {len(prices)} price records")     # Detail with indent
  print(f"  > Error type: {error_report.error_type}")  # Sub-detail
  ```
- Success indicators: `print(f"[Synthesizer] Verification passed!")`
- Progress: `print(f"\n[Synthesizer] Attempt {attempt + 1}/{max_attempts}")`

## Comments

**When to Comment:**
- Strategic comments above significant logic blocks: See `src/core/executor.py` line 161 "# 2. Create temporary directory for sandboxed execution"
- Comments in docstrings preferred over inline comments
- Used in error patterns dict to explain mapping: `"pattern": r"TypeError:.*"` (self-documenting)

**JSDoc/TSDoc:**
- Uses Python docstrings following Google/NumPy style:
  ```python
  def execute(self, code: str, func_name: str, args: dict, task_id: str, timeout_sec: int = EXECUTION_TIMEOUT_SEC) -> ExecutionTrace:
      """
      Execute code in a sandboxed subprocess.

      Args:
          code: Python source code
          func_name: Function to call (or 'verify_only' for self-tests)
          args: Arguments to pass to the function
          task_id: Task identifier for tracing

      Returns:
          ExecutionTrace with results
      """
  ```

## Function Design

**Size:** Functions range 10-100 lines, typically 30-50 lines for core logic
- Small utility functions: `extract_function_name()` - 6 lines
- Medium handlers: `execute()` - 120+ lines (complex but single responsibility)
- Large coordination functions: `refine()` - 80+ lines with clear sections

**Parameters:**
- Required positional args first: `code: str, task: str`
- Optional kwargs with defaults: `tool_name: Optional[str] = None`, `max_attempts: int = 3`
- Type hints on all parameters
- Methods use `self` as first parameter, no default values for self

**Return Values:**
- Simple types: `bool`, `str`, `Optional[ToolArtifact]`
- Tuple returns for multi-value results: `Tuple[Optional[ToolArtifact], ExecutionTrace]`
- Dictionaries for structured returns: `{"thought_trace": str, "code_payload": str, "text_response": str}`
- Database entities returned directly: `ToolArtifact`, `ExecutionTrace`

## Module Design

**Exports:**
- Modules export classes and utility functions, no `__all__` definitions
- Main classes at module top: `class ToolExecutor:`, `class Synthesizer:`
- Utility functions before classes: `def extract_function_name():`, `def extract_args_schema():`
- Test blocks at bottom: `if __name__ == "__main__":` in every module

**Barrel Files:**
- `src/__init__.py` empty
- `src/core/__init__.py` empty
- `src/evolution/__init__.py` empty
- `src/finance/__init__.py` empty
- No re-exports; direct imports used throughout

**Module Responsibilities (Single Responsibility):**
- `src/config.py` - Environment and path configuration only
- `src/core/models.py` - Database schema definitions (5 SQLModel tables)
- `src/core/executor.py` - Code execution and security (AST + sandbox)
- `src/core/registry.py` - Tool storage and retrieval (DB + disk)
- `src/core/llm_adapter.py` - LLM communication and response parsing
- `src/evolution/synthesizer.py` - Tool generation workflow (Generate → Verify → Register)
- `src/evolution/refiner.py` - Tool repair workflow (Analyze Error → Generate Patch → Verify)
- `src/finance/bootstrap.py` - Initial tool registration
- `src/finance/data_proxy.py` - Data caching and reproducibility

---

*Convention analysis: 2026-01-31*
