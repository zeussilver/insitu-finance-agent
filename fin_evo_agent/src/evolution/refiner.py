"""Tool Refiner: Error Analysis → Patch Generation → Verification

The repair loop:
1. Analyze error from ExecutionTrace
2. Generate ErrorReport with LLM analysis
3. Generate patched code based on error context
4. Verify patch in sandbox
5. If passed, create ToolPatch record and register new version
"""

import re
import uuid
from typing import Tuple, Optional, List
from datetime import datetime

from sqlmodel import Session

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.llm_adapter import LLMAdapter
from src.core.executor import ToolExecutor
from src.core.registry import ToolRegistry
from src.core.models import (
    ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch,
    init_db, get_engine
)
from src.evolution.synthesizer import extract_function_name, extract_args_schema


# Module replacement guide for common talib replacements
MODULE_REPLACEMENT_GUIDE = """
## Module Replacement Guide (USE THESE)
FORBIDDEN: talib, yfinance, akshare, requests, os, sys, subprocess
USE INSTEAD: pandas, numpy for all calculations

### RSI (replace talib.RSI)
```python
delta = prices.diff()
gain = delta.clip(lower=0).rolling(period).mean()
loss = (-delta.clip(upper=0)).rolling(period).mean()
rs = gain / loss.replace(0, np.inf)
rsi = 100 - (100 / (1 + rs))
```

### MACD (replace talib.MACD)
```python
ema_fast = prices.ewm(span=fast, adjust=False).mean()
ema_slow = prices.ewm(span=slow, adjust=False).mean()
macd_line = ema_fast - ema_slow
signal = macd_line.ewm(span=signal_period, adjust=False).mean()
```

### Bollinger Bands (replace talib.BBANDS)
```python
middle = prices.rolling(period).mean()
std = prices.rolling(period).std()
upper = middle + (num_std * std)
lower = middle - (num_std * std)
```
"""


class Refiner:
    """Tool refiner: Error Analysis → Patch → Register"""

    # Common error patterns and fix strategies
    ERROR_PATTERNS = {
        "TypeError": {
            "pattern": r"TypeError:.*",
            "strategy": "Check argument types and add type conversion"
        },
        "KeyError": {
            "pattern": r"KeyError:.*'(\w+)'",
            "strategy": "Check DataFrame column names and use .get() with defaults"
        },
        "IndexError": {
            "pattern": r"IndexError:.*",
            "strategy": "Add length checks before indexing"
        },
        "ValueError": {
            "pattern": r"ValueError:.*",
            "strategy": "Add input validation and handle edge cases"
        },
        "ZeroDivisionError": {
            "pattern": r"ZeroDivisionError.*",
            "strategy": "Add zero-division guards"
        },
        "AttributeError": {
            "pattern": r"AttributeError:.*'(\w+)'.*'(\w+)'",
            "strategy": "Check object type before accessing attribute"
        },
        "ModuleNotFoundError": {
            "pattern": r"ModuleNotFoundError:.*No module named '(\w+)'",
            "strategy": "Replace forbidden module with pandas/numpy equivalent. FORBIDDEN: talib, yfinance, akshare, requests, os, sys, subprocess."
        },
        "ImportError": {
            "pattern": r"ImportError:.*",
            "strategy": "Check import path and module name. Use only: pandas, numpy, datetime, json, math, decimal, collections, re, typing."
        },
        "AssertionError": {
            "pattern": r"AssertionError:?(.*)?",
            "strategy": "Fix the calculation logic to match expected output. Do NOT modify the test assertions."
        }
    }

    def __init__(
        self,
        llm: LLMAdapter = None,
        executor: ToolExecutor = None,
        registry: ToolRegistry = None
    ):
        self.llm = llm or LLMAdapter()
        self.executor = executor or ToolExecutor()
        self.registry = registry or ToolRegistry()
        self.engine = get_engine()

    def _classify_error(self, stderr: str) -> Tuple[str, str]:
        """Classify error type and extract key information."""
        for error_type, info in self.ERROR_PATTERNS.items():
            match = re.search(info["pattern"], stderr)
            if match:
                return error_type, info["strategy"]
        return "UnknownError", "Analyze the error message and fix accordingly"

    def analyze_error(
        self,
        trace: ExecutionTrace,
        code: str
    ) -> ErrorReport:
        """
        Analyze error and create ErrorReport.

        Args:
            trace: Failed execution trace
            code: Source code that failed

        Returns:
            ErrorReport with error classification and root cause
        """
        stderr = trace.std_err or ""
        error_type, strategy = self._classify_error(stderr)

        # Use LLM to analyze root cause
        analysis_prompt = f"""分析以下Python代码执行错误的根本原因。

## 代码
```python
{code}
```

## 错误信息
```
{stderr}
```

## 错误类型
{error_type}

请简洁地说明:
1. 错误发生的具体原因
2. 建议的修复方法

只输出分析结果，不要输出代码。"""

        result = self.llm.generate_tool_code(analysis_prompt)

        # Extract text_response (LLM explanation) and thought_trace (internal reasoning)
        text_response = result.get("text_response", "")
        thought_trace = result.get("thought_trace", "")

        # Truncate to reasonable length to keep prompts manageable
        MAX_TEXT_LEN = 2000
        if len(text_response) > MAX_TEXT_LEN:
            text_response = text_response[:MAX_TEXT_LEN//2] + "\n...[truncated]...\n" + text_response[-MAX_TEXT_LEN//2:]

        # Priority: text_response (explanation) > thought_trace (reasoning) > default
        root_cause = text_response or thought_trace or f"{error_type}: {strategy}"

        # Create ErrorReport
        error_report = ErrorReport(
            trace_id=trace.trace_id,
            error_type=error_type,
            root_cause=root_cause
        )

        # Save to database
        with Session(self.engine) as session:
            session.add(error_report)
            session.commit()
            session.refresh(error_report)

        return error_report

    def generate_patch(
        self,
        error_report: ErrorReport,
        original_code: str,
        task: str
    ) -> Optional[str]:
        """
        Generate patched code based on error analysis.

        Args:
            error_report: Error analysis from analyze_error()
            original_code: Original code that failed
            task: Original task description

        Returns:
            Patched code or None if generation failed
        """
        patch_prompt = f"""修复以下Python代码中的错误。

## 原始任务
{task}

## 原始代码
```python
{original_code}
```

## 错误分析
错误类型: {error_report.error_type}
根本原因: {error_report.root_cause}

## 要求
1. 修复错误，保持原有功能
2. 添加必要的边界检查和错误处理
3. 保留原有的类型注解和文档字符串
4. 在 if __name__ == '__main__' 块中保留测试用例

只输出修复后的完整代码，用 ```python ``` 包裹。"""

        result = self.llm.generate_tool_code(patch_prompt)
        return result.get("code_payload")

    def refine(
        self,
        code: str,
        task: str,
        trace: ExecutionTrace,
        base_tool: Optional[ToolArtifact] = None,
        max_attempts: int = 3
    ) -> Tuple[Optional[ToolArtifact], List[ErrorReport]]:
        """
        Full refinement loop with retry.

        Args:
            code: Failed code to refine
            task: Original task description
            trace: Failed execution trace
            base_tool: Optional base tool (for versioning)
            max_attempts: Maximum refinement attempts

        Returns:
            (refined_tool, error_reports) - tool is None if all attempts failed
        """
        print(f"[Refiner] Starting refinement (max {max_attempts} attempts)")

        error_reports = []
        current_code = code
        current_trace = trace

        for attempt in range(max_attempts):
            print(f"\n[Refiner] Attempt {attempt + 1}/{max_attempts}")

            # 1. Analyze error
            print("[Refiner] Analyzing error...")
            error_report = self.analyze_error(current_trace, current_code)
            error_reports.append(error_report)
            print(f"  > Error type: {error_report.error_type}")
            print(f"  > Root cause: {error_report.root_cause[:100]}...")

            # 2. Generate patch
            print("[Refiner] Generating patch...")
            patched_code = self.generate_patch(error_report, current_code, task)

            if not patched_code:
                print("  > Patch generation failed")
                continue

            # 3. Verify patch
            print("[Refiner] Verifying patch...")
            verify_trace = self.executor.execute(
                patched_code, "verify_only", {}, f"refine_{attempt}"
            )

            if verify_trace.exit_code == 0:
                print("[Refiner] Patch verified successfully!")

                # 4. Register patched tool
                func_name = extract_function_name(patched_code)
                if not func_name:
                    print("  > Could not extract function name")
                    continue

                tool = self.registry.register(
                    name=func_name,
                    code=patched_code,
                    args_schema=extract_args_schema(patched_code)
                )

                # 5. Create ToolPatch record
                if base_tool:
                    patch_record = ToolPatch(
                        error_report_id=error_report.id,
                        base_tool_id=base_tool.id,
                        patch_diff=f"Refined from v{base_tool.semantic_version}",
                        rationale=error_report.root_cause,
                        resulting_tool_id=tool.id
                    )
                    with Session(self.engine) as session:
                        session.add(patch_record)
                        session.commit()

                print(f"[Refiner] Tool refined: {tool.name} v{tool.semantic_version}")
                return tool, error_reports

            else:
                print(f"  > Patch verification failed: {verify_trace.std_err[:100]}...")
                current_code = patched_code
                current_trace = verify_trace

        print(f"[Refiner] Failed after {max_attempts} attempts")
        return None, error_reports


def refine_tool(
    tool: ToolArtifact,
    trace: ExecutionTrace,
    task: str
) -> Optional[ToolArtifact]:
    """
    Convenience function to refine a tool.

    Args:
        tool: Tool that failed
        trace: Failed execution trace
        task: Task description

    Returns:
        Refined tool or None
    """
    refiner = Refiner()
    refined_tool, _ = refiner.refine(
        code=tool.code_content,
        task=task,
        trace=trace,
        base_tool=tool
    )
    return refined_tool


if __name__ == "__main__":
    print("=== Testing Refiner ===\n")

    # Initialize database
    init_db()

    # Create a failing code example
    failing_code = '''
import pandas as pd

def calc_test(prices: list) -> float:
    """Calculate average price."""
    # Bug: division by zero when empty
    return sum(prices) / len(prices)

if __name__ == "__main__":
    # Test with empty list (will fail)
    result = calc_test([])
    print(f"Result: {result}")
'''

    # Create mock trace
    mock_trace = ExecutionTrace(
        trace_id=f"t_{uuid.uuid4().hex[:12]}",
        task_id="test_refine",
        input_args={},
        output_repr="",
        exit_code=1,
        std_out="",
        std_err="ZeroDivisionError: division by zero",
        execution_time_ms=100
    )

    # Test refiner
    refiner = Refiner()
    refined_tool, error_reports = refiner.refine(
        code=failing_code,
        task="计算价格平均值",
        trace=mock_trace
    )

    if refined_tool:
        print(f"\nSuccess! Refined tool: {refined_tool.name} v{refined_tool.semantic_version}")
        print(f"Error reports generated: {len(error_reports)}")
    else:
        print(f"\nFailed after refinement attempts")
        print(f"Error reports: {len(error_reports)}")
