"""Tool Refiner: Error Analysis → Patch Generation → Gateway Submit

The repair loop:
1. Analyze error from ExecutionTrace
2. Generate ErrorReport with LLM analysis
3. Generate patched code based on error context
4. Submit to VerificationGateway (verifies + registers atomically)
5. If passed, create ToolPatch record

Architecture: All tool registration MUST go through VerificationGateway.
Direct registry.register() calls are prohibited.
"""

import re
import time
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
from src.core.gateway import VerificationGateway, get_gateway
from src.core.gates import EvolutionGatekeeper
from src.core.contracts import ToolContract
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

# Errors that should not be retried (fail fast)
UNFIXABLE_ERRORS = {
    "SecurityException",      # AST blocked code
    "Unallowed import",       # Security violation
    "Unallowed call",         # Security violation
    "Unallowed attribute",    # Security violation
    "TimeoutError",           # External timeout
    "ConnectionError",        # Network failures
    "LLM API Error",          # LLM service failures
}


class Refiner:
    """Tool refiner: Error Analysis → Patch → Gateway Submit

    All tool registration goes through VerificationGateway exclusively.
    Direct registry.register() calls are prohibited.
    """

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
        registry: ToolRegistry = None,
        gateway: VerificationGateway = None,
        gatekeeper: EvolutionGatekeeper = None,
    ):
        self.llm = llm or LLMAdapter()
        self.executor = executor or ToolExecutor()
        self.registry = registry or ToolRegistry()
        self.gateway = gateway or get_gateway()
        self.gatekeeper = gatekeeper or EvolutionGatekeeper()
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
        task: str,
        attempt: int = 1,
        previous_patches: Optional[List[dict]] = None
    ) -> Optional[str]:
        """
        Generate patched code based on error analysis.

        Args:
            error_report: Error analysis from analyze_error()
            original_code: Original code that failed
            task: Original task description
            attempt: Current attempt number (1-3)
            previous_patches: List of previous patch attempts with failure reasons

        Returns:
            Patched code or None if generation failed
        """
        # Build history section for retries
        history_section = ""
        if previous_patches and attempt > 1:
            history_section = "\n## Previous Attempts (DO NOT REPEAT THESE APPROACHES)\n"
            for i, patch in enumerate(previous_patches, 1):
                history_section += f"\n### Attempt {i} - FAILED\n"
                history_section += f"What was tried: {patch.get('approach', 'Unknown')}\n"
                history_section += f"Why it failed: {patch.get('failure_reason', 'Unknown')}\n"

        # Module guidance for import errors
        module_guidance = ""
        if error_report.error_type in ("ModuleNotFoundError", "ImportError"):
            module_guidance = MODULE_REPLACEMENT_GUIDE

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
{module_guidance}
{history_section}

## 修复要求
1. 首先简要说明你将要修改什么以及为什么
2. 修复错误，保持原有功能
3. 只使用 pandas 和 numpy 进行计算 (不要使用 talib 或其他外部库)
4. 保留原有的类型注解和文档字符串
5. 保留 if __name__ == '__main__' 中的测试用例
6. 重要：不要修改测试断言 - 测试定义了期望行为，修复应使代码通过原始测试

只输出修复后的完整代码，用 ```python ``` 包裹。"""

        result = self.llm.generate_tool_code(patch_prompt)
        return result.get("code_payload")

    def refine(
        self,
        code: str,
        task: str,
        trace: ExecutionTrace,
        base_tool: Optional[ToolArtifact] = None,
        max_attempts: int = 3,
        category: Optional[str] = None,
        contract: Optional[ToolContract] = None,
    ) -> Tuple[Optional[ToolArtifact], List[ErrorReport]]:
        """
        Full refinement loop with retry, backoff, and history tracking.

        All registration goes through VerificationGateway.

        Args:
            code: Failed code to refine
            task: Original task description
            trace: Failed execution trace
            base_tool: Optional base tool (for versioning)
            max_attempts: Maximum refinement attempts
            category: Tool category for verification
            contract: Optional contract for validation

        Returns:
            (refined_tool, error_reports) - tool is None if all attempts failed
        """
        print(f"[Refiner] Starting refinement (max {max_attempts} attempts)")

        # Infer category if not provided
        if not category:
            category = self._infer_category(task)

        error_reports = []
        patch_history = []
        current_code = code
        current_trace = trace

        for attempt in range(max_attempts):
            # Check for unfixable errors first (fail-fast)
            stderr = current_trace.std_err or ""
            for unfixable in UNFIXABLE_ERRORS:
                if unfixable in stderr:
                    print(f"[Refiner] Unfixable error detected: {unfixable} - aborting")
                    return None, error_reports

            # Exponential backoff: 1s, 2s, 4s (skip on first attempt)
            if attempt > 0:
                delay = 2 ** (attempt - 1)  # 1, 2, 4 seconds
                print(f"[Refiner] Waiting {delay}s before attempt {attempt + 1}...")
                time.sleep(delay)

            print(f"\n[Refiner] Attempt {attempt + 1}/{max_attempts}")

            # 1. Analyze error
            print("[Refiner] Analyzing error...")
            error_report = self.analyze_error(current_trace, current_code)
            error_reports.append(error_report)
            print(f"  > Error type: {error_report.error_type}")
            print(f"  > Root cause: {error_report.root_cause[:100]}...")

            # 2. Generate patch with history
            print("[Refiner] Generating patch...")
            patched_code = self.generate_patch(
                error_report,
                current_code,
                task,
                attempt=attempt + 1,
                previous_patches=patch_history if patch_history else None
            )

            if not patched_code:
                print("  > Patch generation failed")
                patch_history.append({
                    "approach": "LLM failed to generate code",
                    "failure_reason": "No code payload returned"
                })
                continue

            # 3. Extract function name for logging
            func_name = extract_function_name(patched_code)
            if not func_name:
                print("  > Could not extract function name")
                patch_history.append({
                    "approach": "Patch generated but function name extraction failed",
                    "failure_reason": "No function definition found in patched code"
                })
                continue

            # 4. Submit to VerificationGateway (handles verification + registration)
            print("[Refiner] Submitting to VerificationGateway...")
            success, tool, report = self.gateway.submit(
                code=patched_code,
                category=category,
                contract=contract,
                task=task,
                task_id=f"refine_{attempt}",
                force=False,
            )

            if success and tool:
                print("[Refiner] Gateway approved! Patch registered.")

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
                failure_snippet = ""
                for stage in report.stages:
                    if stage.result.value == 'fail':
                        failure_snippet = stage.message[:200]
                        break

                print(f"  > Gateway rejected: {failure_snippet[:100]}...")

                # Track this failed attempt
                patch_history.append({
                    "approach": f"Fixed {error_report.error_type}: {error_report.root_cause[:100]}",
                    "failure_reason": failure_snippet or "Gateway verification failed"
                })

                current_code = patched_code
                # Create a trace from the report for next iteration
                current_trace = ExecutionTrace(
                    trace_id=f"t_{uuid.uuid4().hex[:12]}",
                    task_id=f"refine_{attempt}",
                    input_args={},
                    output_repr="",
                    exit_code=1,
                    std_out="",
                    std_err=failure_snippet,
                    execution_time_ms=0
                )

        print(f"[Refiner] Failed after {max_attempts} attempts")
        return None, error_reports

    def _infer_category(self, task: str) -> str:
        """Infer tool category from task description."""
        task_lower = task.lower()
        if any(kw in task_lower for kw in ['获取', 'fetch', 'get', '查询', '历史', 'price', 'quote']):
            if any(kw in task_lower for kw in ['calculate', 'calc', '计算', 'rsi', 'macd', 'bollinger']):
                return 'calculation'
            return 'fetch'
        elif any(kw in task_lower for kw in ['if ', 'return true', 'return false', 'signal', 'divergence', 'portfolio']):
            return 'composite'
        else:
            return 'calculation'


def refine_tool(
    tool: ToolArtifact,
    trace: ExecutionTrace,
    task: str,
    category: Optional[str] = None,
    contract: Optional[ToolContract] = None,
) -> Optional[ToolArtifact]:
    """
    Convenience function to refine a tool.

    All registration goes through VerificationGateway.

    Args:
        tool: Tool that failed
        trace: Failed execution trace
        task: Task description
        category: Optional tool category
        contract: Optional contract for validation

    Returns:
        Refined tool or None
    """
    refiner = Refiner()
    refined_tool, _ = refiner.refine(
        code=tool.code_content,
        task=task,
        trace=trace,
        base_tool=tool,
        category=category,
        contract=contract,
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
