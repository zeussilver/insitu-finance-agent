"""Tool Synthesizer: Generate → Verify → Register → Refine

The core evolution loop:
1. Call LLM to generate tool code from task description
2. Submit to VerificationGateway (enforces multi-stage verification)
3. Gateway registers if all stages pass
4. If failed, call Refiner for error repair

Architecture: All tool registration MUST go through VerificationGateway.
Direct registry.register() calls are prohibited.
"""

import re
from typing import Tuple, Optional, List

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.llm_adapter import LLMAdapter
from src.core.executor import ToolExecutor
from src.core.registry import ToolRegistry
from src.core.models import ToolArtifact, ExecutionTrace, Permission, VerificationStage
from src.core.verifier import MultiStageVerifier, VerificationReport
from src.core.contracts import get_contract, infer_contract_from_query, ToolContract
from src.core.capabilities import get_category_capabilities, ToolCapability
from src.core.gateway import VerificationGateway, get_gateway
from src.core.gates import EvolutionGatekeeper


def extract_function_name(code: str) -> Optional[str]:
    """Extract the main function name from code."""
    # Look for def function_name(
    match = re.search(r'^def\s+(\w+)\s*\(', code, re.MULTILINE)
    return match.group(1) if match else None


# Indicator keywords for schema extraction
INDICATOR_KEYWORDS = {
    'rsi': ['rsi', '相对强弱', 'relative strength'],
    'macd': ['macd', '指数平滑异同'],
    'bollinger': ['bollinger', '布林', 'boll'],
    'kdj': ['kdj', '随机指标'],
    'ma': ['moving average', 'ma', '移动平均'],
    'volatility': ['volatility', '波动率'],
    'drawdown': ['drawdown', '回撤', 'max_drawdown'],
    'correlation': ['correlation', '相关系数', '相关性'],
    'volume_price': ['volume price', '量价', 'divergence'],
    'portfolio': ['portfolio', '组合', 'weight'],
}


def extract_indicator(task: str, code: str) -> Optional[str]:
    """Extract indicator type from task description or code."""
    text = (task + ' ' + code).lower()
    for indicator, keywords in INDICATOR_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return indicator
    return None


def extract_data_type(task: str, args_schema: dict) -> str:
    """Infer data type from task and function arguments."""
    task_lower = task.lower()
    if any(kw in task_lower for kw in ['financial', '财务', 'net income', '净利润', 'revenue', 'roe']):
        return 'financial'
    if any(kw in task_lower for kw in ['volume', '成交量', '量']):
        return 'volume'
    if 'ohlcv' in str(args_schema).lower() or all(k in str(args_schema).lower() for k in ['open', 'high', 'low', 'close']):
        return 'ohlcv'
    return 'price'  # default


def extract_args_schema(code: str) -> dict:
    """Extract simple args schema from function signature."""
    # Simple extraction - in production, use ast.parse
    match = re.search(r'def\s+\w+\s*\((.*?)\)', code, re.DOTALL)
    if not match:
        return {}

    args_str = match.group(1)
    schema = {}

    # Parse each argument
    for arg in args_str.split(','):
        arg = arg.strip()
        if not arg or arg == 'self':
            continue

        # Handle type hints: name: type = default
        if ':' in arg:
            name = arg.split(':')[0].strip()
            type_hint = arg.split(':')[1].split('=')[0].strip()
            schema[name] = type_hint
        elif '=' in arg:
            name = arg.split('=')[0].strip()
            schema[name] = "any"
        else:
            schema[arg] = "any"

    return schema


class Synthesizer:
    """Tool synthesizer: Generate → Gateway Submit → Refine

    All tool registration goes through VerificationGateway exclusively.
    Direct registry.register() calls are prohibited.
    """

    def __init__(
        self,
        llm: LLMAdapter = None,
        executor: ToolExecutor = None,
        registry: ToolRegistry = None,
        verifier: MultiStageVerifier = None,
        gateway: VerificationGateway = None,
        gatekeeper: EvolutionGatekeeper = None,
    ):
        self.llm = llm or LLMAdapter()
        self.executor = executor or ToolExecutor()
        self.registry = registry or ToolRegistry()
        self.verifier = verifier or MultiStageVerifier(self.executor, self.registry)
        self.gateway = gateway or get_gateway()
        self.gatekeeper = gatekeeper or EvolutionGatekeeper()

    def synthesize(
        self,
        task: str,
        tool_name: Optional[str] = None,
        category: Optional[str] = None,
        contract: Optional[ToolContract] = None
    ) -> Tuple[Optional[ToolArtifact], ExecutionTrace]:
        """
        Synthesize a tool from task description.

        Flow:
        1. Call LLM to generate code (with category-specific prompt)
        2. Submit to VerificationGateway (verifies + registers atomically)
        3. Gateway handles verification, checkpoint, and registration

        Args:
            task: Task description (e.g., "计算 RSI 指标")
            tool_name: Optional tool name (extracted from code if not provided)
            category: Tool category ('fetch', 'calculation', 'composite')
            contract: Optional contract for output validation

        Returns:
            (tool, trace) - tool is None if synthesis failed
        """
        # Infer category if not provided
        if not category:
            category = self._infer_category(task)

        # Try to get contract if not provided
        if not contract:
            contract = infer_contract_from_query(task, category)

        # 1. Generate code using LLM with category-specific prompt
        print(f"[Synthesizer] Generating code for: {task}")
        print(f"[Synthesizer] Category: {category}")
        task_prompt = task
        if tool_name:
            task_prompt += f"\n\nPlease name the function: {tool_name}"
        result = self.llm.generate_tool_code(task_prompt, category=category)

        if not result["code_payload"]:
            # Failed to generate code
            trace = ExecutionTrace(
                trace_id="gen_failed",
                task_id=task[:50],
                input_args={"task": task},
                output_repr="",
                exit_code=1,
                std_out="",
                std_err="LLM failed to generate valid code",
                execution_time_ms=0
            )
            return None, trace

        code = result["code_payload"]

        # Log thinking process
        if result["thought_trace"]:
            print(f"[Thinking] {result['thought_trace'][:100]}...")

        # 2. Extract function name for logging
        func_name = extract_function_name(code) or tool_name
        if not func_name:
            trace = ExecutionTrace(
                trace_id="no_func",
                task_id=task[:50],
                input_args={"task": task},
                output_repr="",
                exit_code=1,
                std_out="",
                std_err="Could not extract function name from generated code",
                execution_time_ms=0
            )
            return None, trace

        print(f"[Synthesizer] Extracted function: {func_name}")

        # 3. Submit to VerificationGateway (handles verification + registration)
        print("[Synthesizer] Submitting to VerificationGateway...")
        success, tool, report = self.gateway.submit(
            code=code,
            category=category,
            contract=contract,
            task=task,
            task_id=task[:50],
            force=False,  # Respect gatekeeper approval
        )

        # Create trace from verification report
        trace = self._create_trace_from_report(task, report)

        if not success:
            print(f"[Synthesizer] Gateway rejected: {report.final_stage.name}")
            for stage in report.stages:
                if stage.result.value == 'fail':
                    print(f"  - {stage.stage.name}: {stage.message}")
            return None, trace

        print(f"[Synthesizer] Gateway approved! Final stage: {report.final_stage.name}")

        # Extract schema metadata for update
        args_schema = extract_args_schema(code)
        indicator = extract_indicator(task, code)
        data_type = extract_data_type(task, args_schema)

        # Get capabilities for this category
        capabilities = [cap.value for cap in get_category_capabilities(category)]

        # Update schema fields after registration
        if tool:
            self.registry.update_schema(
                tool.id,
                category=category,
                indicator=indicator,
                data_type=data_type,
                input_requirements=list(args_schema.keys()) if args_schema else []
            )

        print(f"[Synthesizer] Tool registered: {tool.name} v{tool.semantic_version} (ID: {tool.id})")
        print(f"[Synthesizer] Schema: category={category}, indicator={indicator}, data_type={data_type}")
        print(f"[Synthesizer] Capabilities: {capabilities}")
        return tool, trace

    def _infer_category(self, task: str) -> str:
        """Infer tool category from task description."""
        task_lower = task.lower()
        if any(kw in task_lower for kw in ['获取', 'fetch', 'get', '查询', '历史', 'price', 'quote']):
            # Check if it's actually a calculation task that mentions data
            if any(kw in task_lower for kw in ['calculate', 'calc', '计算', 'rsi', 'macd', 'bollinger', 'volatility', 'correlation']):
                return 'calculation'
            return 'fetch'
        elif any(kw in task_lower for kw in ['if ', 'return true', 'return false', 'signal', 'divergence', 'portfolio', 'after']):
            return 'composite'
        else:
            return 'calculation'

    def _create_trace_from_report(
        self,
        task: str,
        report: VerificationReport
    ) -> ExecutionTrace:
        """Create ExecutionTrace from VerificationReport."""
        # Collect error info from failed stages
        errors = []
        for stage in report.stages:
            if stage.result.value == 'fail':
                errors.append(f"{stage.stage.name}: {stage.message}")

        return ExecutionTrace(
            trace_id=f"verify_{report.tool_name}",
            task_id=task[:50],
            input_args={"task": task, "category": report.category},
            output_repr=f"final_stage={report.final_stage.name}",
            exit_code=0 if report.passed else 1,
            std_out=str(report.to_dict()),
            std_err="; ".join(errors) if errors else "",
            execution_time_ms=0
        )

    def _update_tool_verification_fields(
        self,
        tool_id: int,
        capabilities: List[str],
        contract_id: Optional[str],
        verification_stage: int
    ):
        """Update tool with verification-related fields."""
        from sqlmodel import Session
        from src.core.models import get_engine, ToolArtifact

        engine = get_engine()
        with Session(engine) as session:
            tool = session.get(ToolArtifact, tool_id)
            if tool:
                tool.capabilities = capabilities
                tool.contract_id = contract_id
                tool.verification_stage = verification_stage
                session.add(tool)
                session.commit()

    def synthesize_with_retry(
        self,
        task: str,
        max_attempts: int = 3
    ) -> Tuple[Optional[ToolArtifact], list]:
        """
        Synthesize with retry on failure.

        All registration goes through VerificationGateway.

        Args:
            task: Task description
            max_attempts: Maximum number of attempts

        Returns:
            (tool, traces) - list of all execution traces
        """
        traces = []
        error_context = None
        category = self._infer_category(task)
        contract = infer_contract_from_query(task, category)

        for attempt in range(max_attempts):
            print(f"\n[Synthesizer] Attempt {attempt + 1}/{max_attempts}")

            if error_context:
                # Include error context for refinement
                result = self.llm.generate_tool_code(task, error_context)
                code = result.get("code_payload")
            else:
                tool, trace = self.synthesize(task)
                traces.append(trace)

                if tool:
                    return tool, traces

                error_context = trace.std_err

                continue

            # Try with error context - submit through gateway
            if code:
                func_name = extract_function_name(code)
                if func_name:
                    # Use gateway for verification and registration
                    success, tool, report = self.gateway.submit(
                        code=code,
                        category=category,
                        contract=contract,
                        task=task,
                        task_id=task[:50],
                        force=False,
                    )

                    trace = self._create_trace_from_report(task, report)
                    traces.append(trace)

                    if success and tool:
                        return tool, traces

                    error_context = trace.std_err

        print(f"[Synthesizer] Failed after {max_attempts} attempts")
        return None, traces

    def synthesize_with_refine(
        self,
        task: str,
        tool_name: Optional[str] = None,
        use_refiner: bool = True,
        category: Optional[str] = None,
        contract: Optional[ToolContract] = None
    ) -> Tuple[Optional[ToolArtifact], ExecutionTrace]:
        """
        Synthesize a tool with automatic refinement on failure.

        All registration goes through VerificationGateway.

        Args:
            task: Task description
            tool_name: Optional tool name
            use_refiner: Whether to use refiner on failure
            category: Tool category ('fetch', 'calculation', 'composite')
            contract: Optional contract for output validation

        Returns:
            (tool, trace) - tool is None if all attempts failed
        """
        # First try normal synthesis with category and contract
        tool, trace = self.synthesize(task, tool_name, category=category, contract=contract)

        if tool:
            return tool, trace

        if not use_refiner:
            return None, trace

        # Import refiner here to avoid circular import
        from src.evolution.refiner import Refiner

        # Get the generated code from LLM (need to regenerate since synthesize doesn't return it on failure)
        result = self.llm.generate_tool_code(task, category=category)
        code = result.get("code_payload")

        if not code:
            return None, trace

        # Use refiner to fix the code (refiner now uses gateway)
        print("[Synthesizer] Synthesis failed, invoking Refiner...")
        refiner = Refiner(
            llm=self.llm,
            executor=self.executor,
            registry=self.registry,
            gateway=self.gateway,
        )

        if not category:
            category = self._infer_category(task)

        refined_tool, error_reports = refiner.refine(
            code=code,
            task=task,
            trace=trace,
            category=category,
            contract=contract,
        )

        if refined_tool:
            # Update schema fields for refined tool
            self.registry.update_schema(
                refined_tool.id,
                category=category,
                indicator=extract_indicator(task, refined_tool.code_content),
                data_type=extract_data_type(task, extract_args_schema(refined_tool.code_content)),
                input_requirements=list(extract_args_schema(refined_tool.code_content).keys())
            )

            # Create a success trace
            success_trace = ExecutionTrace(
                trace_id=f"refined_{trace.trace_id}",
                task_id=task[:50],
                input_args={"task": task},
                output_repr="",
                exit_code=0,
                std_out="Refined successfully",
                std_err="",
                execution_time_ms=trace.execution_time_ms
            )
            return refined_tool, success_trace

        return None, trace


if __name__ == "__main__":
    from src.core.models import init_db

    print("Initializing database...")
    init_db()

    print("\n=== Testing Synthesizer ===\n")
    synthesizer = Synthesizer()

    # Test synthesis (will use mock LLM if no API key)
    tool, trace = synthesizer.synthesize("计算 RSI 指标")

    if tool:
        print(f"\nSuccess! Tool: {tool.name} v{tool.semantic_version}")
        print(f"File: {tool.file_path}")
    else:
        print(f"\nFailed: {trace.std_err}")
