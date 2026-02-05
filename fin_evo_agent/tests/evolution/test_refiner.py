"""Tests for Refiner - extracted from refiner.__main__.

Tests cover:
- Error classification
- Error analysis
- Patch generation
- Refinement loop
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.evolution.refiner import Refiner, UNFIXABLE_ERRORS
from src.core.models import ExecutionTrace, ErrorReport, init_db


class TestErrorClassification:
    """Test error type classification."""

    @pytest.fixture
    def refiner(self):
        return Refiner.__new__(Refiner)  # Create without __init__

    def test_classify_type_error(self, refiner):
        """TypeError should be classified correctly."""
        stderr = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "TypeError"
        assert "type" in strategy.lower()

    def test_classify_key_error(self, refiner):
        """KeyError should be classified correctly."""
        stderr = "KeyError: 'missing_column'"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "KeyError"
        assert "column" in strategy.lower() or "get" in strategy.lower()

    def test_classify_index_error(self, refiner):
        """IndexError should be classified correctly."""
        stderr = "IndexError: list index out of range"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "IndexError"
        assert "length" in strategy.lower() or "check" in strategy.lower()

    def test_classify_value_error(self, refiner):
        """ValueError should be classified correctly."""
        stderr = "ValueError: invalid literal for int()"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "ValueError"
        assert "validation" in strategy.lower() or "edge" in strategy.lower()

    def test_classify_zero_division(self, refiner):
        """ZeroDivisionError should be classified correctly."""
        stderr = "ZeroDivisionError: division by zero"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "ZeroDivisionError"
        assert "zero" in strategy.lower() or "guard" in strategy.lower()

    def test_classify_attribute_error(self, refiner):
        """AttributeError should be classified correctly."""
        stderr = "AttributeError: 'NoneType' object has no attribute 'value'"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "AttributeError"
        assert "type" in strategy.lower() or "attribute" in strategy.lower()

    def test_classify_module_not_found(self, refiner):
        """ModuleNotFoundError should be classified correctly."""
        stderr = "ModuleNotFoundError: No module named 'talib'"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "ModuleNotFoundError"
        assert "forbidden" in strategy.lower() or "pandas" in strategy.lower()

    def test_classify_assertion_error(self, refiner):
        """AssertionError should be classified correctly."""
        stderr = "AssertionError: Expected 5, got 3"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "AssertionError"
        assert "logic" in strategy.lower() or "test" in strategy.lower()

    def test_classify_unknown_error(self, refiner):
        """Unknown errors should return UnknownError."""
        stderr = "SomeCustomException: weird stuff happened"
        error_type, strategy = refiner._classify_error(stderr)
        assert error_type == "UnknownError"
        assert "analyze" in strategy.lower()


class TestUnfixableErrors:
    """Test detection of unfixable errors."""

    def test_security_exception_is_unfixable(self):
        """SecurityException should be unfixable."""
        assert "SecurityException" in UNFIXABLE_ERRORS

    def test_unallowed_import_is_unfixable(self):
        """Unallowed import should be unfixable."""
        assert "Unallowed import" in UNFIXABLE_ERRORS

    def test_timeout_is_unfixable(self):
        """TimeoutError should be unfixable."""
        assert "TimeoutError" in UNFIXABLE_ERRORS

    def test_connection_error_is_unfixable(self):
        """ConnectionError should be unfixable."""
        assert "ConnectionError" in UNFIXABLE_ERRORS


class TestRefinerIntegration:
    """Integration tests for the refiner (with mocked LLM)."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM adapter."""
        llm = MagicMock()
        # Mock generate_tool_code to return fixed analysis
        llm.generate_tool_code.return_value = {
            "text_response": "Division by zero when list is empty",
            "thought_trace": "",
            "code_payload": '''
import pandas as pd

def calc_test(prices: list) -> float:
    """Calculate average price."""
    if not prices:
        return 0.0
    return sum(prices) / len(prices)

if __name__ == "__main__":
    result = calc_test([])
    assert result == 0.0
    print(f"Result: {result}")
'''
        }
        return llm

    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor."""
        executor = MagicMock()
        # First call fails (original), second succeeds (patched)
        executor.execute.side_effect = [
            ExecutionTrace(
                trace_id="t_test1",
                task_id="test",
                input_args={},
                output_repr="",
                exit_code=0,
                std_out="<<VERIFY_PASS>>",
                std_err="",
                execution_time_ms=100
            )
        ]
        return executor

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry."""
        registry = MagicMock()
        from src.core.models import ToolArtifact
        registry.register.return_value = ToolArtifact(
            id=1,
            name="calc_test",
            semantic_version="0.1.1",
            source_hash="abc123",
            code_path="/tmp/test.py",
            permissions="read_only",
            status="active",
            test_cases={}
        )
        return registry

    def test_analyze_error_creates_report(self, mock_llm):
        """analyze_error should create an ErrorReport."""
        # Skip database operations for this test
        with patch('src.evolution.refiner.get_engine'), \
             patch('src.evolution.refiner.Session'):
            refiner = Refiner(llm=mock_llm)

            trace = ExecutionTrace(
                trace_id="t_test",
                task_id="test",
                input_args={},
                output_repr="",
                exit_code=1,
                std_out="",
                std_err="ZeroDivisionError: division by zero",
                execution_time_ms=100
            )

            error_report = refiner.analyze_error(trace, "def test(): pass")
            assert error_report.error_type == "ZeroDivisionError"

    def test_generate_patch_uses_llm(self, mock_llm):
        """generate_patch should call LLM with error context."""
        with patch('src.evolution.refiner.get_engine'), \
             patch('src.evolution.refiner.Session'):
            refiner = Refiner(llm=mock_llm)

            error_report = ErrorReport(
                trace_id="t_test",
                error_type="ZeroDivisionError",
                root_cause="Division by zero when list is empty"
            )

            patched_code = refiner.generate_patch(
                error_report,
                "def calc_test(prices): return sum(prices)/len(prices)",
                "计算平均值"
            )

            assert patched_code is not None
            assert "if not prices" in patched_code

    def test_refine_aborts_on_security_exception(self, mock_llm, mock_executor, mock_registry):
        """refine should abort immediately on security exceptions."""
        with patch('src.evolution.refiner.get_engine'), \
             patch('src.evolution.refiner.Session'):
            refiner = Refiner(
                llm=mock_llm,
                executor=mock_executor,
                registry=mock_registry
            )

            trace = ExecutionTrace(
                trace_id="t_test",
                task_id="test",
                input_args={},
                output_repr="",
                exit_code=1,
                std_out="",
                std_err="SecurityException: Banned import: os",
                execution_time_ms=100
            )

            result, error_reports = refiner.refine(
                code="import os",
                task="test",
                trace=trace,
                max_attempts=3
            )

            assert result is None
            assert len(error_reports) == 0  # Should abort before analysis


class TestRefinerFailingCode:
    """Test refiner with actual failing code examples."""

    @pytest.fixture
    def failing_code_division_by_zero(self):
        """Code that fails with division by zero."""
        return '''
import pandas as pd

def calc_test(prices: list) -> float:
    """Calculate average price."""
    return sum(prices) / len(prices)

if __name__ == "__main__":
    result = calc_test([])
    print(f"Result: {result}")
'''

    @pytest.fixture
    def failing_trace(self):
        """Trace for failed execution."""
        return ExecutionTrace(
            trace_id="t_test",
            task_id="test",
            input_args={},
            output_repr="",
            exit_code=1,
            std_out="",
            std_err="ZeroDivisionError: division by zero",
            execution_time_ms=100
        )

    def test_error_classification_from_trace(self, failing_code_division_by_zero, failing_trace):
        """Error should be correctly classified from trace."""
        refiner = Refiner.__new__(Refiner)
        error_type, strategy = refiner._classify_error(failing_trace.std_err)
        assert error_type == "ZeroDivisionError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
