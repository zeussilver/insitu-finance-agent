"""Multi-stage verification pipeline for tool validation.

Verification stages:
1. AST_SECURITY - Capability-specific import/call rules
2. SELF_TEST - Built-in assert tests pass
3. CONTRACT_VALID - Output matches contract constraints
4. INTEGRATION - Real data test (fetch tools only)

Tools are only promoted if ALL stages pass.

Constraints are loaded from the centralized constraints module.
"""

import re
import json
import math
from typing import Tuple, Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from src.core.executor import ToolExecutor
from src.core.registry import ToolRegistry
from src.core.models import ExecutionTrace, VerificationStage
from src.core.constraints import get_constraints
from src.core.contracts import (
    ToolContract, OutputType, get_contract, infer_contract_from_query
)


class VerificationResult(str, Enum):
    """Result of a verification stage."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"  # Stage not applicable


@dataclass
class StageResult:
    """Result of a single verification stage."""
    stage: VerificationStage
    result: VerificationResult
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationReport:
    """Complete verification report for a tool."""
    tool_name: str
    category: str
    stages: List[StageResult] = field(default_factory=list)
    final_stage: VerificationStage = VerificationStage.NONE
    passed: bool = False

    def add_stage(self, result: StageResult):
        """Add a stage result and update final stage if passed."""
        self.stages.append(result)
        if result.result == VerificationResult.PASS:
            if result.stage.value > self.final_stage.value:
                self.final_stage = result.stage
        elif result.result == VerificationResult.FAIL:
            self.passed = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "tool_name": self.tool_name,
            "category": self.category,
            "final_stage": self.final_stage.value,
            "passed": self.passed,
            "stages": [
                {
                    "stage": s.stage.value,
                    "result": s.result.value,
                    "message": s.message,
                    "details": s.details
                }
                for s in self.stages
            ]
        }


class MultiStageVerifier:
    """Multi-stage verification pipeline for tools."""

    def __init__(
        self,
        executor: ToolExecutor = None,
        registry: ToolRegistry = None
    ):
        self.executor = executor or ToolExecutor()
        self.registry = registry or ToolRegistry()

    def verify_all_stages(
        self,
        code: str,
        category: str,
        task_id: str = "unknown",
        contract: ToolContract = None,
        real_data: Dict[str, Any] = None
    ) -> Tuple[bool, VerificationReport]:
        """
        Run all verification stages on the code.

        Args:
            code: Python source code to verify
            category: Tool category ('fetch', 'calculation', 'composite')
            task_id: Task identifier for tracing
            contract: Optional contract for output validation
            real_data: Optional real data for integration testing

        Returns:
            (passed, report) - passed is True only if all applicable stages pass
        """
        # Extract function name for report
        func_name = self._extract_function_name(code) or "unknown"
        report = VerificationReport(tool_name=func_name, category=category)
        report.passed = True  # Assume pass until failure

        # Stage 1: AST Security Check
        stage1 = self._verify_ast_security(code, category, task_id)
        report.add_stage(stage1)
        if stage1.result == VerificationResult.FAIL:
            return False, report

        # Stage 2: Self-Test Execution
        stage2 = self._verify_self_test(code, task_id)
        report.add_stage(stage2)
        if stage2.result == VerificationResult.FAIL:
            return False, report

        # Stage 3: Contract Validation (if contract provided)
        if contract:
            stage3 = self._verify_contract(code, contract, task_id)
            report.add_stage(stage3)
            if stage3.result == VerificationResult.FAIL:
                return False, report
        else:
            report.add_stage(StageResult(
                stage=VerificationStage.CONTRACT_VALID,
                result=VerificationResult.SKIP,
                message="No contract provided"
            ))

        # Stage 4: Integration Test (only for fetch tools with real data)
        if category == 'fetch' and real_data:
            stage4 = self._verify_integration(code, func_name, real_data, task_id)
            report.add_stage(stage4)
            if stage4.result == VerificationResult.FAIL:
                return False, report
        else:
            report.add_stage(StageResult(
                stage=VerificationStage.INTEGRATION,
                result=VerificationResult.SKIP,
                message="Integration test not applicable"
            ))

        return True, report

    def _extract_function_name(self, code: str) -> Optional[str]:
        """Extract the main function name from code."""
        match = re.search(r'^def\s+(\w+)\s*\(', code, re.MULTILINE)
        return match.group(1) if match else None

    def _verify_ast_security(
        self,
        code: str,
        category: str,
        task_id: str
    ) -> StageResult:
        """Stage 1: Verify code passes AST security check with capability rules."""
        # Get constraints from centralized config
        constraints = get_constraints()

        # Get allowed modules for this category from centralized config
        allowed_modules = constraints.get_allowed_modules(category)

        # Get banned modules for this category (always banned + category-specific)
        banned_modules = constraints.get_banned_modules(category)

        is_safe, error = self.executor.static_check_with_rules(
            code,
            allowed_modules=allowed_modules,
            banned_modules=banned_modules,
            banned_calls=constraints.get_always_banned_calls(),
            banned_attributes=constraints.get_always_banned_attributes()
        )

        if is_safe:
            return StageResult(
                stage=VerificationStage.AST_SECURITY,
                result=VerificationResult.PASS,
                message="AST security check passed",
                details={"allowed_modules": sorted(allowed_modules)}
            )
        else:
            return StageResult(
                stage=VerificationStage.AST_SECURITY,
                result=VerificationResult.FAIL,
                message=f"AST security check failed: {error}",
                details={"error": error}
            )

    def _verify_self_test(self, code: str, task_id: str) -> StageResult:
        """Stage 2: Verify built-in tests pass."""
        trace = self.executor.execute(code, "verify_only", {}, task_id)

        if trace.exit_code != 0:
            return StageResult(
                stage=VerificationStage.SELF_TEST,
                result=VerificationResult.FAIL,
                message=f"Self-test failed: {trace.std_err[:200]}",
                details={
                    "exit_code": trace.exit_code,
                    "stderr": trace.std_err[:500] if trace.std_err else "",
                    "stdout": trace.std_out[:500] if trace.std_out else ""
                }
            )

        # Check for explicit verification markers
        result = self.executor.extract_result(trace)
        stdout = trace.std_out or ""

        if result == "VERIFY_PASS" or "passed" in stdout.lower() or "pass" in stdout.lower():
            return StageResult(
                stage=VerificationStage.SELF_TEST,
                result=VerificationResult.PASS,
                message="Self-test passed",
                details={"output": stdout[:200]}
            )

        # Exit code 0 without explicit pass - still considered pass
        return StageResult(
            stage=VerificationStage.SELF_TEST,
            result=VerificationResult.PASS,
            message="Self-test completed (exit code 0)",
            details={"output": stdout[:200]}
        )

    def _verify_contract(
        self,
        code: str,
        contract: ToolContract,
        task_id: str
    ) -> StageResult:
        """Stage 3: Verify output matches contract constraints."""
        func_name = self._extract_function_name(code)
        if not func_name:
            return StageResult(
                stage=VerificationStage.CONTRACT_VALID,
                result=VerificationResult.FAIL,
                message="Could not extract function name"
            )

        # Generate test args from contract
        test_args = self._generate_test_args(contract)

        # Execute with test args
        trace = self.executor.execute(code, func_name, test_args, task_id)

        if trace.exit_code != 0:
            return StageResult(
                stage=VerificationStage.CONTRACT_VALID,
                result=VerificationResult.FAIL,
                message=f"Contract test execution failed: {trace.std_err[:200]}",
                details={"exit_code": trace.exit_code, "stderr": trace.std_err[:500]}
            )

        # Extract and validate output
        output = self.executor.extract_result(trace)
        valid, validation_msg = self._validate_output(output, contract)

        if valid:
            return StageResult(
                stage=VerificationStage.CONTRACT_VALID,
                result=VerificationResult.PASS,
                message="Contract validation passed",
                details={"output": output[:200] if output else "", "contract": contract.contract_id}
            )
        else:
            return StageResult(
                stage=VerificationStage.CONTRACT_VALID,
                result=VerificationResult.FAIL,
                message=f"Contract validation failed: {validation_msg}",
                details={"output": output[:200] if output else "", "validation_error": validation_msg}
            )

    def _verify_integration(
        self,
        code: str,
        func_name: str,
        real_data: Dict[str, Any],
        task_id: str,
        max_retries: int = 2
    ) -> StageResult:
        """Stage 4: Verify with real data (fetch tools only).

        Includes retry logic for network resilience.
        """
        last_error = None

        for attempt in range(max_retries + 1):
            trace = self.executor.execute(code, func_name, real_data, task_id)

            if trace.exit_code != 0:
                last_error = trace.std_err
                # Check if it's a network error worth retrying
                network_errors = ['timeout', 'connection', 'network', 'rate limit', '503', '504', '429']
                stderr_lower = (trace.std_err or "").lower()
                is_network_error = any(err in stderr_lower for err in network_errors)

                if is_network_error and attempt < max_retries:
                    print(f"[Verifier] Integration test retry {attempt + 1}/{max_retries}")
                    import time
                    time.sleep(1.0 * (attempt + 1))  # Simple backoff
                    continue
                else:
                    return StageResult(
                        stage=VerificationStage.INTEGRATION,
                        result=VerificationResult.FAIL,
                        message=f"Integration test failed: {trace.std_err[:200]}",
                        details={"exit_code": trace.exit_code, "stderr": trace.std_err[:500], "attempts": attempt + 1}
                    )

            output = self.executor.extract_result(trace)

            # Basic output validation for integration
            if output and output != "None" and output.strip():
                return StageResult(
                    stage=VerificationStage.INTEGRATION,
                    result=VerificationResult.PASS,
                    message="Integration test passed",
                    details={"output_preview": output[:200], "attempts": attempt + 1}
                )
            else:
                return StageResult(
                    stage=VerificationStage.INTEGRATION,
                    result=VerificationResult.FAIL,
                    message="Integration test returned empty/None output",
                    details={"output": output, "attempts": attempt + 1}
                )

        # Should not reach here, but just in case
        return StageResult(
            stage=VerificationStage.INTEGRATION,
            result=VerificationResult.FAIL,
            message=f"Integration test failed after {max_retries + 1} attempts",
            details={"last_error": last_error}
        )

    def _generate_test_args(self, contract: ToolContract) -> Dict[str, Any]:
        """Generate test arguments based on contract input types."""
        args = {}

        # Sample data for common input types
        sample_prices = [100.0, 101.5, 99.8, 102.3, 101.0, 103.5, 102.8, 104.0, 103.2, 105.0,
                        104.5, 106.0, 105.2, 107.0, 106.5, 108.0, 107.2, 109.0, 108.5, 110.0]
        sample_high = [101.0, 102.5, 100.8, 103.3, 102.0, 104.5, 103.8, 105.0, 104.2, 106.0,
                      105.5, 107.0, 106.2, 108.0, 107.5, 109.0, 108.2, 110.0, 109.5, 111.0]
        sample_low = [99.0, 100.5, 98.8, 101.3, 100.0, 102.5, 101.8, 103.0, 102.2, 104.0,
                     103.5, 105.0, 104.2, 106.0, 105.5, 107.0, 106.2, 108.0, 107.5, 109.0]
        sample_volumes = [1000000, 1100000, 950000, 1200000, 1050000, 1150000, 1000000, 1250000,
                         1100000, 1300000, 1050000, 1200000, 980000, 1150000, 1020000, 1180000,
                         1050000, 1220000, 1000000, 1280000]

        for input_name, input_type in contract.input_types.items():
            if input_name in ('prices', 'close'):
                args[input_name] = sample_prices
            elif input_name == 'high':
                args[input_name] = sample_high
            elif input_name == 'low':
                args[input_name] = sample_low
            elif input_name in ('volume', 'volumes'):
                args[input_name] = sample_volumes
            elif input_name in ('prices1', 'prices2'):
                # For correlation, use slightly different data
                args[input_name] = sample_prices if input_name == 'prices1' else sample_high
            elif input_name == 'symbol':
                args[input_name] = 'AAPL'
            elif input_name in ('start', 'start_date'):
                args[input_name] = '2023-01-01'
            elif input_name in ('end', 'end_date'):
                args[input_name] = '2023-12-31'
            elif input_name == 'period':
                args[input_name] = 14
            elif input_name == 'window':
                args[input_name] = 20
            elif input_name in ('fast_period', 'short_period'):
                args[input_name] = 12
            elif input_name in ('slow_period', 'long_period'):
                args[input_name] = 26
            elif input_name == 'signal_period':
                args[input_name] = 9
            elif input_name == 'k_period':
                args[input_name] = 9
            elif input_name == 'd_period':
                args[input_name] = 3
            elif input_name == 'num_std':
                args[input_name] = 2.0
            elif input_name in ('weights', 'weight'):
                args[input_name] = [0.33, 0.33, 0.34]
            elif input_name == 'symbols':
                args[input_name] = ['AAPL', 'MSFT', 'GOOGL']
            elif input_name == 'signal_threshold':
                args[input_name] = 70.0
            elif input_type == 'int':
                args[input_name] = 14
            elif input_type == 'float':
                args[input_name] = 2.0
            elif input_type == 'str':
                args[input_name] = 'default'
            elif input_type == 'list':
                args[input_name] = sample_prices
            elif input_type == 'bool':
                args[input_name] = True

        return args

    def _validate_output(
        self,
        output: Optional[str],
        contract: ToolContract
    ) -> Tuple[bool, str]:
        """
        Validate output matches contract constraints.

        Returns:
            (valid, message) - message explains validation result
        """
        if output is None or output == "None":
            if contract.allow_none:
                return True, "None output allowed by contract"
            return False, "Output is None but contract doesn't allow None"

        output = output.strip()

        # Handle different output types
        if contract.output_type == OutputType.NUMERIC:
            return self._validate_numeric(output, contract)
        elif contract.output_type == OutputType.DICT:
            return self._validate_dict(output, contract)
        elif contract.output_type == OutputType.BOOLEAN:
            return self._validate_boolean(output)
        elif contract.output_type == OutputType.LIST:
            return self._validate_list(output)
        elif contract.output_type == OutputType.DATAFRAME:
            return self._validate_dataframe(output, contract)
        elif contract.output_type == OutputType.ANY:
            return True, "Any output accepted"

        return False, f"Unknown output type: {contract.output_type}"

    def _validate_numeric(
        self,
        output: str,
        contract: ToolContract
    ) -> Tuple[bool, str]:
        """Validate numeric output."""
        try:
            value = float(output)

            # Check for NaN
            if math.isnan(value):
                if contract.allow_nan:
                    return True, "NaN output allowed"
                return False, "Output is NaN"

            # Check constraints
            constraints = contract.output_constraints
            if 'min' in constraints and value < constraints['min']:
                return False, f"Value {value} below min {constraints['min']}"
            if 'max' in constraints and value > constraints['max']:
                return False, f"Value {value} above max {constraints['max']}"

            return True, f"Numeric value {value} within constraints"

        except (ValueError, TypeError) as e:
            return False, f"Could not parse numeric output: {output[:50]}"

    def _validate_dict(
        self,
        output: str,
        contract: ToolContract
    ) -> Tuple[bool, str]:
        """Validate dict output."""
        try:
            # Handle Python dict representation
            output_clean = output.replace("'", '"')
            data = json.loads(output_clean)

            if not isinstance(data, dict):
                return False, f"Expected dict, got {type(data).__name__}"

            # Check required keys
            for key in contract.required_keys:
                # Check case-insensitive
                found = any(k.lower() == key.lower() for k in data.keys())
                if not found:
                    return False, f"Missing required key: {key}"

            return True, f"Dict contains required keys: {contract.required_keys}"

        except json.JSONDecodeError:
            # Try to check keys from string representation
            output_lower = output.lower()
            missing = []
            for key in contract.required_keys:
                if key.lower() not in output_lower:
                    missing.append(key)
            if missing:
                return False, f"Missing required keys: {missing}"
            return True, "Required keys found in output string"

    def _validate_boolean(self, output: str) -> Tuple[bool, str]:
        """Validate boolean output."""
        output_lower = output.lower().strip()
        if output_lower in ('true', 'false', '1', '0', 'yes', 'no'):
            return True, f"Boolean value: {output_lower}"
        return False, f"Not a boolean: {output}"

    def _validate_list(self, output: str) -> Tuple[bool, str]:
        """Validate list output."""
        if output.startswith('[') and output.endswith(']'):
            return True, "List output format validated"
        if ',' in output or '\n' in output:
            return True, "List-like output detected"
        return False, f"Not a list: {output[:50]}"

    def _validate_dataframe(
        self,
        output: str,
        contract: ToolContract
    ) -> Tuple[bool, str]:
        """Validate DataFrame output."""
        # Check for required columns in string representation
        output_lower = output.lower()

        for key in contract.required_keys:
            if key.lower() not in output_lower:
                return False, f"DataFrame missing column: {key}"

        return True, f"DataFrame contains required columns: {contract.required_keys}"


if __name__ == "__main__":
    # Test the verifier
    print("=== Multi-Stage Verifier Test ===\n")

    verifier = MultiStageVerifier()

    # Test code - RSI calculation
    test_code = '''
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return 50.0

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])

if __name__ == "__main__":
    prices = [44, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45, 45.5, 46, 46.5, 47, 46.5, 47, 47.5]
    result = calc_rsi(prices, 5)
    assert 0 <= result <= 100, f"RSI out of range: {result}"
    print("Test passed!")
'''

    # Test with contract
    from src.core.contracts import CONTRACTS
    contract = CONTRACTS["calc_rsi"]

    passed, report = verifier.verify_all_stages(
        code=test_code,
        category="calculation",
        task_id="test_001",
        contract=contract
    )

    print(f"Verification result: {'PASS' if passed else 'FAIL'}")
    print(f"Final stage: {report.final_stage.name}")
    print("\nStage details:")
    for stage in report.stages:
        print(f"  {stage.stage.name}: {stage.result.value} - {stage.message}")

    # Test with unsafe code
    print("\n=== Testing Unsafe Code ===\n")
    unsafe_code = '''
import os
def unsafe_func():
    os.system("ls")
'''
    passed, report = verifier.verify_all_stages(
        code=unsafe_code,
        category="calculation",
        task_id="test_unsafe"
    )
    print(f"Unsafe code: {'PASS' if passed else 'FAIL (expected)'}")
    print(f"Failure reason: {report.stages[0].message}")

    # Test fetch code with yfinance allowed
    print("\n=== Testing Fetch Code ===\n")
    fetch_code = '''
import yfinance as yf
import pandas as pd

def get_stock_price(symbol: str) -> float:
    """Get latest stock price."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")
    return float(hist['Close'].iloc[-1])

if __name__ == "__main__":
    # Mock test
    print("Test passed!")
'''
    passed, report = verifier.verify_all_stages(
        code=fetch_code,
        category="fetch",
        task_id="test_fetch"
    )
    print(f"Fetch code with yfinance: {'PASS' if passed else 'FAIL'}")
    if report.stages:
        print(f"AST stage: {report.stages[0].result.value}")

    # Same code should fail for calculation category
    print("\n=== Testing yfinance in Calculation Category ===\n")
    passed, report = verifier.verify_all_stages(
        code=fetch_code,
        category="calculation",
        task_id="test_fetch_as_calc"
    )
    print(f"Fetch code as calculation: {'PASS' if passed else 'FAIL (expected)'}")
    if report.stages and report.stages[0].result == VerificationResult.FAIL:
        print(f"Correctly blocked: {report.stages[0].message}")

    print("\nAll verifier tests complete!")
