# Coding Conventions

**Analysis Date:** 2026-02-06

## Naming Patterns

**Files:**
- snake_case for all Python files: `llm_adapter.py`, `task_executor.py`, `data_proxy.py`
- Test files prefixed with `test_`: `test_executor.py`, `test_gateway.py`, `test_schema.py`
- `__init__.py` in every package directory for explicit imports
- UPPERCASE for markdown docs in root: `CLAUDE.md`, `README.md`

**Functions:**
- snake_case for all functions: `extract_function_name()`, `static_check()`, `get_constraints()`
- Private functions prefixed with underscore: `_normalize_encoding()`, `_log_security_violation()`, `_parse()`
- Verbs for actions: `extract_`, `get_`, `load_`, `create_`, `validate_`

**Variables:**
- snake_case for local variables: `task_id`, `func_name`, `code_content`
- SCREAMING_SNAKE_CASE for module-level constants: `BANNED_MODULES`, `ALLOWED_MODULES`, `LLM_TIMEOUT`
- Descriptive names over abbreviations: `verification_stage` not `ver_stage`

**Classes:**
- PascalCase for class names: `ToolArtifact`, `VerificationGateway`, `ExecutionTrace`
- Noun-based names describing entities: `Synthesizer`, `Refiner`, `ToolExecutor`
- Exception suffix for custom exceptions: `SecurityException`, `VerificationError`

**Types:**
- PascalCase for Enums: `ToolStatus`, `Permission`, `VerificationStage`
- SCREAMING_SNAKE_CASE for enum values: `CALC_ONLY`, `NETWORK_READ`, `AST_SECURITY`

## Code Style

**Formatting:**
- No explicit formatter configured (no .prettierrc, .black, etc.)
- Manual PEP 8 compliance observed
- 4-space indentation consistently used
- Line length: Generally kept under 100 characters, docstrings under 80

**Linting:**
- No linter config files detected (.pylintrc, .flake8, pyproject.toml absent)
- Code shows manual adherence to PEP 8 standards
- Type hints used extensively throughout

## Import Organization

**Order:**
1. Standard library imports (grouped, no blank line between)
2. Blank line
3. Third-party imports (openai, sqlmodel, pandas, etc.)
4. Blank line
5. Local imports with conditional TYPE_CHECKING for circular dependency avoidance
6. Path manipulation via `sys.path.insert(0, ...)` for project root

**Example pattern from `src/core/gateway.py`:**
```python
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.verifier import MultiStageVerifier
from src.core.registry import ToolRegistry
from src.core.models import ToolArtifact
```

**Path Aliases:**
- No path aliases configured
- All imports use explicit `src.` prefix: `from src.core.models import ...`
- Relative imports avoided in favor of absolute imports from project root

## Type Hints

**Usage:**
- Comprehensive type hints on all public functions
- Function signatures include parameter types and return types
- Example: `def submit(code: str, category: str, contract: Optional[ToolContract] = None) -> Tuple[bool, Optional[ToolArtifact], VerificationReport]`
- `TYPE_CHECKING` conditional imports to avoid circular dependencies
- Protocol types used for interfaces: `class DataProvider(Protocol):`

**Collections:**
- `List[str]`, `Dict[str, Any]`, `Set[str]`, `Tuple[bool, str]` from typing module
- `Optional[T]` for nullable types, never bare `None`

## Error Handling

**Patterns:**
- Custom exceptions for domain errors: `SecurityException`, `VerificationError`
- Exception classes include optional context data: `VerificationError.__init__(message, report)`
- Try-except blocks with specific exception types, not bare `except:`
- Graceful degradation: functions return `(success: bool, result, error)` tuples instead of raising

**Example from `src/core/gateway.py`:**
```python
try:
    passed, report = self.verifier.verify_all_stages(...)
    if not passed:
        return False, None, report
    # ... register tool
    return True, tool, report
except Exception as e:
    self.checkpoint_manager.mark_failed(checkpoint_id, str(e))
    raise
```

**Validation:**
- Input validation at function entry: `if len(prices) < period + 1: return 50.0`
- Constraint validation in centralized config loader: `if execution.timeout_sec <= 0: raise ValueError(...)`

## Logging

**Framework:** Python standard library `logging`

**Patterns:**
- Module-level loggers: `self.logger = logging.getLogger("VerificationGateway")`
- File handlers for persistent logs: `logs_dir / "gateway.log"`
- Structured JSONL logs for machine-readable data: `gateway_attempts.jsonl`
- Log levels: INFO for normal operations, ERROR for failures
- Format: `'%(asctime)s | %(levelname)s | %(message)s'`

**When to log:**
- All gateway submissions (success and failure) in `src/core/gateway.py`
- Security violations to `data/logs/security_violations.log`
- Evolution attempts logged with thinking traces in `data/logs/`

**Example from `src/core/gateway.py`:**
```python
self._log_attempt(
    "REGISTERED",
    func_name,
    category,
    success=True,
    details={"tool_id": tool.id, "version": tool.semantic_version}
)
```

## Comments

**When to Comment:**
- Module-level docstrings explaining file purpose and architecture
- Class docstrings describing responsibilities
- Function docstrings with Args/Returns sections for all public functions
- Inline comments for non-obvious logic or constraints

**Docstring Style:**
- Google-style docstrings with Args, Returns, Raises sections
- Example:
  ```python
  def submit(code: str, category: str) -> Tuple[bool, Optional[ToolArtifact], VerificationReport]:
      """Submit a tool for verification and registration.

      Args:
          code: Python source code for the tool
          category: Tool category ('fetch', 'calculation', 'composite')

      Returns:
          (success, tool, report) - tool is None if verification failed

      Raises:
          VerificationError: If verification fails
      """
  ```

**Section headers in files:**
- ASCII art separators for major sections: `# === Category-Specific System Prompts ===`
- Numbered sections in docstrings: `1. All tools pass verification`, `2. Rollback checkpoints`

**TODOs:**
- No TODO/FIXME pattern observed in codebase - issues tracked externally

## Function Design

**Size:**
- Public functions: Generally 20-50 lines
- Private helper functions: 5-20 lines
- Main orchestration functions (like `gateway.submit()`): Can extend to 100+ lines with clear section comments

**Parameters:**
- Keyword arguments preferred for clarity: `submit(code=..., category=..., force=True)`
- Default values for optional parameters: `period: int = 14`, `force: bool = False`
- Explicit parameter names over positional: `extract_schema(task)` not `extract_schema(t)`

**Return Values:**
- Tuple returns for multiple values: `(success: bool, tool: Optional[ToolArtifact], report: VerificationReport)`
- Dataclasses for complex return types: `ExtractedSchema`, `VerificationReport`
- `None` for failure cases when using `Optional[T]`

## Module Design

**Exports:**
- Explicit `__all__` not used
- Public API defined through `__init__.py` re-exports
- Example from `src/data/__init__.py`:
  ```python
  from src.data.interfaces import DataProvider
  ```

**Barrel Files:**
- `__init__.py` files used as barrel exports for clean imports
- Package structure: `src/core/`, `src/evolution/`, `src/finance/`, `src/extraction/`

## Configuration Management

**Centralized config:**
- `src/config.py` for global settings: paths, LLM settings, execution limits
- `configs/constraints.yaml` for runtime constraints loaded via `src/core/constraints.py`
- Environment variables via manual .env parsing in `src/config.py`

**Pattern:**
```python
# Global config
from src.config import LLM_MODEL, EXECUTION_TIMEOUT_SEC

# Constraint config
from src.core.constraints import get_constraints
constraints = get_constraints()
allowed_modules = constraints.get_allowed_modules('calculation')
```

## Architectural Patterns

**Gateway Pattern:**
- All tool registration MUST go through `VerificationGateway.submit()`
- Direct `registry.register()` calls prohibited
- Centralized enforcement point documented in file headers

**Protocol-Based Interfaces:**
- `DataProvider` Protocol defines interface for data adapters
- Runtime protocol checking with `@runtime_checkable`

**Singleton Pattern:**
- Global instances via getter functions: `get_gateway()`, `get_constraints()`
- Lazy initialization with module-level `_instance` variables

**Dataclasses:**
- Used for configuration: `ExecutionConstraints`, `CategoryConstraints`
- Used for structured data: `ExtractedSchema`, `ToolContract`

## Security Conventions

**AST Analysis:**
- All code passes through `ToolExecutor.static_check()` before execution
- Capability-based module checking: different rules for 'calculation' vs 'fetch'
- Centralized banned lists in `configs/constraints.yaml`

**Subprocess Isolation:**
- All tool execution via subprocess with timeout
- JSON IPC for parameter passing, avoiding `eval()`
- Memory and timeout limits from centralized config

**No Trust in Generated Code:**
- Multi-stage verification before registration
- Rollback checkpoints via `CheckpointManager`
- All attempts logged for audit trail

## Database Conventions

**ORM:**
- SQLModel for SQLite database access
- Table names in snake_case: `tool_artifacts`, `execution_traces`
- Migrations via manual `ALTER TABLE` in `_migrate_tool_artifacts()`

**Schema Evolution:**
- Migration functions: `_migrate_tool_artifacts()`, `_migrate_execution_traces()`
- Check existing columns before adding: `if col_name not in existing_columns`
- Backwards-compatible migrations only

## File Organization

**Generated Files:**
- Tool code stored in `data/artifacts/generated/` with naming: `{tool_name}_v{version}_{hash8}.py`
- Logs in `data/logs/`: `gateway.log`, `security_violations.log`, `gateway_attempts.jsonl`
- Database at `data/db/evolution.db`

**Source Files:**
- Core logic in `src/core/`: models, executor, verifier, gateway
- Evolution logic in `src/evolution/`: synthesizer, refiner
- Domain logic in `src/finance/`: data_proxy, bootstrap
- Tests mirror source structure: `tests/core/`, `tests/extraction/`

---

*Convention analysis: 2026-02-06*
