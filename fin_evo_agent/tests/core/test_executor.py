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
    """Calculate moving average."""
    return float(pd.Series(prices).rolling(window).mean().iloc[-1])
'''
        is_safe, error = executor.static_check(safe_code)
        assert is_safe is True
        assert error is None

    def test_safe_numpy_code(self, executor):
        """Safe code using numpy should pass."""
        safe_code = '''
import numpy as np

def calc_std(prices: list) -> float:
    """Calculate standard deviation."""
    return float(np.std(prices))
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

    def test_banned_subprocess_import(self, executor):
        """Import of subprocess module should be blocked."""
        dangerous_code = 'import subprocess; subprocess.run(["ls"])'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "subprocess" in error.lower()

    def test_banned_eval_call(self, executor):
        """Call to eval() should be blocked."""
        dangerous_code = 'eval("1+1")'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "eval" in error.lower()

    def test_banned_exec_call(self, executor):
        """Call to exec() should be blocked."""
        dangerous_code = 'exec("print(1)")'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "exec" in error.lower()

    def test_banned_import_call(self, executor):
        """Call to __import__() should be blocked."""
        dangerous_code = '__import__("sys")'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "__import__" in error.lower()

    def test_banned_magic_attribute(self, executor):
        """Access to __dict__ should be blocked."""
        dangerous_code = 'x = {}; print(x.__dict__)'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "__dict__" in error.lower()

    def test_banned_globals_attribute(self, executor):
        """Access to __globals__ should be blocked."""
        dangerous_code = 'f = lambda: None; f.__globals__'
        is_safe, error = executor.static_check(dangerous_code)
        assert is_safe is False
        assert "__globals__" in error.lower()


class TestStaticCheckWithRules:
    """Test static check with custom capability rules."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    def test_calculation_cannot_use_yfinance(self, executor):
        """Calculation tools should not be able to import yfinance."""
        code = '''
import yfinance as yf

def fetch_price(symbol: str) -> float:
    return yf.Ticker(symbol).fast_info.last_price
'''
        # Default allowed modules don't include yfinance restriction
        # but we can test with custom rules
        allowed_modules = {'pandas', 'numpy', 'datetime', 'json', 'math', 'typing'}

        is_safe, error = executor.static_check_with_rules(
            code,
            allowed_modules=allowed_modules,
        )
        assert is_safe is False
        assert "yfinance" in error.lower()

    def test_fetch_can_use_yfinance(self, executor):
        """Fetch tools should be able to import yfinance."""
        code = '''
import yfinance as yf

def fetch_price(symbol: str) -> float:
    return yf.Ticker(symbol).fast_info.last_price
'''
        allowed_modules = {
            'pandas', 'numpy', 'datetime', 'json', 'math',
            'yfinance', 'hashlib', 'typing', 'warnings'
        }

        is_safe, error = executor.static_check_with_rules(
            code,
            allowed_modules=allowed_modules,
        )
        assert is_safe is True
        assert error is None

    def test_syntax_error_rejected(self, executor):
        """Code with syntax errors should be rejected."""
        bad_code = 'def foo( broken'
        is_safe, error = executor.static_check(bad_code)
        assert is_safe is False
        assert "syntax" in error.lower()


class TestExecute:
    """Test sandbox execution."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    def test_execute_safe_function(self, executor):
        """Execute a safe calculation function."""
        code = '''
import pandas as pd

def calc_ma(prices: list, window: int = 5) -> float:
    """Calculate moving average."""
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

    def test_execute_dangerous_code_blocked(self, executor):
        """Dangerous code should be blocked before execution."""
        dangerous_code = 'import os; os.system("ls")'
        trace = executor.execute(
            dangerous_code,
            func_name="dangerous",
            args={},
            task_id="test_task"
        )
        assert trace.exit_code == 1
        assert "SecurityException" in trace.std_err

    def test_execute_verify_only(self, executor):
        """Test verify_only execution mode."""
        code = '''
import pandas as pd

def calc_ma(prices: list, window: int = 5) -> float:
    return float(pd.Series(prices).rolling(window).mean().iloc[-1])

if __name__ == "__main__":
    result = calc_ma([1, 2, 3, 4, 5, 6, 7], 3)
    assert result == 6.0, f"Expected 6.0, got {result}"
'''
        trace = executor.execute(
            code,
            func_name="verify_only",
            args={},
            task_id="test_verify"
        )
        assert trace.exit_code == 0
        result = executor.extract_result(trace)
        assert result == "VERIFY_PASS"

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


class TestExtractResult:
    """Test result extraction from execution traces."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    def test_extract_numeric_result(self, executor):
        """Extract numeric result from trace."""
        from src.core.models import ExecutionTrace
        trace = ExecutionTrace(
            trace_id="test",
            task_id="test",
            input_args={},
            output_repr="",
            exit_code=0,
            std_out="<<RESULT_START>>\n42.5\n<<RESULT_END>>",
            std_err="",
            execution_time_ms=100
        )
        result = executor.extract_result(trace)
        assert result == "42.5"

    def test_extract_verify_pass(self, executor):
        """Extract VERIFY_PASS from trace."""
        from src.core.models import ExecutionTrace
        trace = ExecutionTrace(
            trace_id="test",
            task_id="test",
            input_args={},
            output_repr="",
            exit_code=0,
            std_out="<<VERIFY_PASS>>",
            std_err="",
            execution_time_ms=100
        )
        result = executor.extract_result(trace)
        assert result == "VERIFY_PASS"

    def test_extract_failed_result(self, executor):
        """Failed execution returns None."""
        from src.core.models import ExecutionTrace
        trace = ExecutionTrace(
            trace_id="test",
            task_id="test",
            input_args={},
            output_repr="",
            exit_code=1,
            std_out="",
            std_err="Error occurred",
            execution_time_ms=100
        )
        result = executor.extract_result(trace)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
