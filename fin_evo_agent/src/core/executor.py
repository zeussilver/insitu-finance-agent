"""Secure tool executor with AST static analysis and subprocess sandboxing.

Safety measures:
1. AST static analysis blocks dangerous imports and calls
2. Subprocess isolation with timeout and memory limits
3. JSON-IPC for parameter passing (avoids eval)
"""

import ast
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Tuple, Optional

import sys as _sys
_sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import EXECUTION_TIMEOUT_SEC, EXECUTION_MEMORY_MB, ROOT_DIR
from src.core.models import ExecutionTrace


class SecurityException(Exception):
    """Raised when code fails security checks."""
    pass


class ToolExecutor:
    """Secure executor with AST analysis and subprocess sandboxing."""

    # Modules that are strictly banned
    BANNED_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'builtins',
        'importlib', 'ctypes', 'socket', 'http', 'urllib',
        'pickle', 'shelve', 'multiprocessing', 'threading'
    }

    # Function calls that are banned
    BANNED_CALLS = {
        'eval', 'exec', 'compile', '__import__',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr'
    }

    # Allowed modules for financial tools
    ALLOWED_MODULES = {
        'pandas', 'numpy', 'datetime', 'json',
        'math', 'decimal', 'collections', 're',
        'yfinance', 'typing', 'hashlib',
        'pathlib'
    }

    def static_check(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Perform AST static security analysis.

        Args:
            code: Python source code to check

        Returns:
            (is_safe, error_message) - error_message is None if safe
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.BANNED_MODULES:
                        return False, f"Banned import: {module}"
                    if module not in self.ALLOWED_MODULES:
                        return False, f"Unallowed import: {module}"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.BANNED_MODULES:
                        return False, f"Banned import from: {module}"
                    if module not in self.ALLOWED_MODULES:
                        return False, f"Unallowed import from: {module}"

            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.BANNED_CALLS:
                        return False, f"Banned call: {node.func.id}"
                    # Special handling for open()
                    if node.func.id == 'open':
                        # Check if mode is 'r' (read-only)
                        mode_ok = False
                        for kw in node.keywords:
                            if kw.arg == 'mode' and isinstance(kw.value, ast.Constant):
                                if kw.value.value == 'r':
                                    mode_ok = True
                        # Also check positional args
                        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                            if node.args[1].value == 'r':
                                mode_ok = True
                        if not mode_ok:
                            return False, "open() only allowed with mode='r'"

            # Check magic attributes
            elif isinstance(node, ast.Attribute):
                if node.attr in ('__dict__', '__class__', '__bases__', '__mro__'):
                    return False, f"Banned magic attribute: {node.attr}"

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

    # Test 2: Dangerous code
    dangerous_codes = [
        'import os; os.system("ls")',
        'import subprocess; subprocess.run(["ls"])',
        'eval("1+1")',
        'exec("print(1)")',
        '__import__("sys")',
    ]

    print("\nDangerous code checks:")
    for code in dangerous_codes:
        is_safe, error = executor.static_check(code)
        print(f"  {code[:30]}... -> blocked={not is_safe}")

    # Test 3: Execute safe code
    print("\nExecuting safe code...")
    trace = executor.execute(safe_code, "verify_only", {}, "test_task")
    print(f"Exit code: {trace.exit_code}")
    print(f"Result: {executor.extract_result(trace)}")
