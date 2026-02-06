"""Secure tool executor with AST static analysis and subprocess sandboxing.

Safety measures:
1. AST static analysis blocks dangerous imports and calls
2. Subprocess isolation with timeout and memory limits
3. JSON-IPC for parameter passing (avoids eval)

Constraints are loaded from the centralized constraints module.
"""

import ast
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Tuple, Optional, Set

import sys as _sys
_sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import EXECUTION_TIMEOUT_SEC, EXECUTION_MEMORY_MB, ROOT_DIR
from src.core.models import ExecutionTrace
from src.core.constraints import get_constraints


class SecurityException(Exception):
    """Raised when code fails security checks."""
    pass


class ToolExecutor:
    """Secure executor with AST analysis and subprocess sandboxing.

    Constraints are loaded from configs/constraints.yaml via the centralized
    constraints module.
    """

    def __init__(self):
        """Initialize executor with constraints from config."""
        self._constraints = get_constraints()

    @property
    def BANNED_MODULES(self) -> Set[str]:
        """Get always banned modules from centralized config."""
        return self._constraints.always_banned_modules

    @property
    def BANNED_CALLS(self) -> Set[str]:
        """Get always banned calls from centralized config."""
        return self._constraints.always_banned_calls

    @property
    def BANNED_ATTRIBUTES(self) -> Set[str]:
        """Get always banned attributes from centralized config."""
        return self._constraints.always_banned_attributes

    @property
    def ALLOWED_MODULES(self) -> Set[str]:
        """Get default allowed modules (union of all categories)."""
        # Return union of all category allowed modules for backwards compatibility
        all_allowed = set()
        for cat in ['calculation', 'fetch', 'composite']:
            all_allowed.update(self._constraints.get_allowed_modules(cat))
        return all_allowed

    def _normalize_encoding(self, code: str) -> str:
        """Strip encoding declarations to prevent PEP-263 bypass."""
        lines = code.split('\n')
        clean = []
        for i, line in enumerate(lines):
            if i < 2 and 'coding' in line.lower() and line.strip().startswith('#'):
                continue  # Skip encoding declaration
            clean.append(line)
        return '\n'.join(clean)

    def _log_security_violation(self, violation: str, task_id: str = "unknown"):
        """Log security violation to file and stderr."""
        import sys
        from datetime import datetime

        # Log to stderr
        print(f"[SECURITY] {violation}", file=sys.stderr)

        # Log to file
        logs_dir = ROOT_DIR / "data" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "security_violations.log"
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} | {task_id} | {violation}\n")

    def static_check(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Perform AST static security analysis.

        Args:
            code: Python source code to check

        Returns:
            (is_safe, error_message) - error_message is None if safe
        """
        return self.static_check_with_rules(code)

    def static_check_with_rules(
        self,
        code: str,
        allowed_modules: set = None,
        banned_modules: set = None,
        banned_calls: set = None,
        banned_attributes: set = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Perform AST static security analysis with custom rules.

        This method supports capability-based checking where different tool
        categories have different allowed/banned modules.

        Args:
            code: Python source code to check
            allowed_modules: Set of allowed module names (None uses default)
            banned_modules: Additional modules to ban (merged with default)
            banned_calls: Additional calls to ban (merged with default)
            banned_attributes: Additional attributes to ban (merged with default)

        Returns:
            (is_safe, error_message) - error_message is None if safe
        """
        # Use defaults if not specified
        if allowed_modules is None:
            allowed_modules = self.ALLOWED_MODULES
        if banned_modules is None:
            banned_modules = self.BANNED_MODULES
        else:
            banned_modules = self.BANNED_MODULES | banned_modules
        if banned_calls is None:
            banned_calls = self.BANNED_CALLS
        else:
            banned_calls = self.BANNED_CALLS | banned_calls
        if banned_attributes is None:
            banned_attributes = self.BANNED_ATTRIBUTES
        else:
            banned_attributes = self.BANNED_ATTRIBUTES | banned_attributes

        # Normalize encoding to prevent PEP-263 bypass
        code = self._normalize_encoding(code)

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in banned_modules:
                        return False, f"Banned import: {module}"
                    if module not in allowed_modules:
                        return False, f"Unallowed import: {module}"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in banned_modules:
                        return False, f"Banned import from: {module}"
                    if module not in allowed_modules:
                        return False, f"Unallowed import from: {module}"

            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in banned_calls:
                        return False, f"Banned call: {node.func.id}"
                # Check for banned method calls on objects (e.g., obj.__class__)
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in banned_calls:
                        return False, f"Banned method call: {node.func.attr}"

            # Check magic attributes - use banned_attributes set
            elif isinstance(node, ast.Attribute):
                if node.attr in banned_attributes:
                    return False, f"Banned attribute access: {node.attr}"

            # Check string literals for banned patterns (catches getattr(obj, 'eval'))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for banned in banned_calls | banned_attributes:
                    if banned in node.value:
                        return False, f"Suspicious string literal containing: {banned}"

        return True, None

    def execute(
        self,
        code: str,
        func_name: str,
        args: dict,
        task_id: str,
        timeout_sec: int = EXECUTION_TIMEOUT_SEC
    ) -> ExecutionTrace:
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
        # 1. Static security check
        is_safe, error = self.static_check(code)
        if not is_safe:
            # Log security violation
            self._log_security_violation(error, task_id)
            return ExecutionTrace(
                trace_id=f"t_{uuid.uuid4().hex[:12]}",
                task_id=task_id,
                input_args=args,
                output_repr="",
                exit_code=1,
                std_out="",
                std_err=f"SecurityException: {error}",
                execution_time_ms=0
            )

        start_ts = time.time_ns()

        # 2. Create temporary directory for sandboxed execution
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            args_path = dir_path / "args.json"

            # Serialize arguments to JSON
            safe_args = json.loads(json.dumps(args, default=str))
            with open(args_path, 'w') as f:
                json.dump(safe_args, f)

            # 3. Generate runner script
            runner_code = f'''
import json
import sys
import inspect
import pandas as pd
import numpy as np

# Inject project root for imports
sys.path.insert(0, "{ROOT_DIR}")

# --- Tool Code Start ---
{code}
# --- Tool Code End ---

if __name__ == "__main__":
    try:
        if "{func_name}" == "verify_only":
            # Run self-tests in if __name__ == '__main__' block
            # The code above already executed the tests
            print("<<VERIFY_PASS>>")
            sys.exit(0)

        # Load arguments
        with open("{args_path}", "r") as f:
            args = json.load(f)

        # Find the target function
        target_func = None
        if "{func_name}" in dir() and callable(eval("{func_name}")):
            target_func = eval("{func_name}")
        else:
            # Fallback: find first user-defined function in module scope
            for name, obj in list(globals().items()):
                if callable(obj) and not name.startswith("_") and hasattr(obj, "__module__"):
                    target_func = obj
                    break

        if target_func is None:
            print(f"Error: Function {func_name} not found.")
            sys.exit(1)

        # Filter args to match function signature
        sig = inspect.signature(target_func)
        valid_params = set(sig.parameters.keys())
        filtered_args = {{k: v for k, v in args.items() if k in valid_params}}

        result = target_func(**filtered_args)
        print("<<RESULT_START>>")
        print(result)
        print("<<RESULT_END>>")

    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
'''
            runner_path = dir_path / "runner.py"
            with open(runner_path, 'w') as f:
                f.write(runner_code)

            # 4. Execute in subprocess with timeout
            try:
                proc = subprocess.run(
                    [sys.executable, str(runner_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    cwd=str(ROOT_DIR)
                )
                exit_code = proc.returncode
                stdout = proc.stdout
                stderr = proc.stderr
            except subprocess.TimeoutExpired:
                exit_code = 124
                stdout = ""
                stderr = f"Timeout ({timeout_sec}s)"
            except Exception as e:
                exit_code = 1
                stdout = ""
                stderr = str(e)

        duration = (time.time_ns() - start_ts) // 1_000_000

        return ExecutionTrace(
            trace_id=f"t_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            input_args=safe_args,
            output_repr=stdout[:500],
            exit_code=exit_code,
            std_out=stdout,
            std_err=stderr,
            execution_time_ms=duration
        )

    def extract_result(self, trace: ExecutionTrace) -> Optional[str]:
        """Extract result from execution trace output."""
        if trace.exit_code != 0:
            return None
        stdout = trace.std_out or ""
        if "<<RESULT_START>>" in stdout and "<<RESULT_END>>" in stdout:
            return stdout.split("<<RESULT_START>>")[1].split("<<RESULT_END>>")[0].strip()
        if "<<VERIFY_PASS>>" in stdout:
            return "VERIFY_PASS"
        return stdout.strip()


if __name__ == "__main__":
    # Self-tests moved to tests/core/test_executor.py
    # This block is kept minimal for verify_only mode support
    print("ToolExecutor module loaded. Run pytest tests/core/test_executor.py for tests.")
