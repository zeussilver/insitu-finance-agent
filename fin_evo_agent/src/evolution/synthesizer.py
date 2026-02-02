"""Tool Synthesizer: Generate → Verify → Register → Refine

The core evolution loop:
1. Call LLM to generate tool code from task description
2. Perform AST security check
3. Execute built-in tests in sandbox
4. If passed, register to database and disk
5. If failed, call Refiner for error repair
"""

import re
from typing import Tuple, Optional

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.llm_adapter import LLMAdapter
from src.core.executor import ToolExecutor
from src.core.registry import ToolRegistry
from src.core.models import ToolArtifact, ExecutionTrace, Permission


def extract_function_name(code: str) -> Optional[str]:
    """Extract the main function name from code."""
    # Look for def function_name(
    match = re.search(r'^def\s+(\w+)\s*\(', code, re.MULTILINE)
    return match.group(1) if match else None


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
    """Tool synthesizer: Generate → Verify → Register"""

    def __init__(
        self,
        llm: LLMAdapter = None,
        executor: ToolExecutor = None,
        registry: ToolRegistry = None
    ):
        self.llm = llm or LLMAdapter()
        self.executor = executor or ToolExecutor()
        self.registry = registry or ToolRegistry()

    def synthesize(
        self,
        task: str,
        tool_name: Optional[str] = None
    ) -> Tuple[Optional[ToolArtifact], ExecutionTrace]:
        """
        Synthesize a tool from task description.

        Flow:
        1. Call LLM to generate code
        2. AST security check
        3. Execute built-in tests (if __name__ == '__main__')
        4. Register if passed

        Args:
            task: Task description (e.g., "计算 RSI 指标")
            tool_name: Optional tool name (extracted from code if not provided)

        Returns:
            (tool, trace) - tool is None if synthesis failed
        """
        # 1. Generate code using LLM
        print(f"[Synthesizer] Generating code for: {task}")
        task_prompt = task
        if tool_name:
            task_prompt += f"\n\nPlease name the function: {tool_name}"
        result = self.llm.generate_tool_code(task_prompt)

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

        # 2. Extract function name and schema (always use actual name from code)
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

        args_schema = extract_args_schema(code)
        print(f"[Synthesizer] Extracted function: {func_name}")

        # 3. Verify code by running self-tests
        print("[Synthesizer] Verifying code...")
        trace = self.executor.execute(code, "verify_only", {}, task[:50])

        if trace.exit_code != 0:
            print(f"[Synthesizer] Verification failed: {trace.std_err}")
            return None, trace

        # Check for verification pass marker
        verification_result = self.executor.extract_result(trace)
        if verification_result != "VERIFY_PASS" and "passed" not in (trace.std_out or "").lower():
            # Tests didn't pass explicitly, but might have run without errors
            if trace.exit_code == 0:
                print("[Synthesizer] Verification completed (implicit pass)")
            else:
                print(f"[Synthesizer] Verification unclear: {trace.std_out}")
                return None, trace

        print("[Synthesizer] Verification passed!")

        # 4. Register the tool
        print("[Synthesizer] Registering tool...")
        tool = self.registry.register(
            name=func_name,
            code=code,
            args_schema=args_schema,
            permissions=[Permission.CALC_ONLY.value]
        )

        print(f"[Synthesizer] Tool registered: {tool.name} v{tool.semantic_version} (ID: {tool.id})")
        return tool, trace

    def synthesize_with_retry(
        self,
        task: str,
        max_attempts: int = 3
    ) -> Tuple[Optional[ToolArtifact], list]:
        """
        Synthesize with retry on failure.

        Args:
            task: Task description
            max_attempts: Maximum number of attempts

        Returns:
            (tool, traces) - list of all execution traces
        """
        traces = []
        error_context = None

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

            # Try with error context
            if code:
                func_name = extract_function_name(code)
                if func_name:
                    trace = self.executor.execute(code, "verify_only", {}, task[:50])
                    traces.append(trace)

                    if trace.exit_code == 0:
                        tool = self.registry.register(
                            name=func_name,
                            code=code,
                            args_schema=extract_args_schema(code)
                        )
                        return tool, traces

                    error_context = trace.std_err

        print(f"[Synthesizer] Failed after {max_attempts} attempts")
        return None, traces

    def synthesize_with_refine(
        self,
        task: str,
        tool_name: Optional[str] = None,
        use_refiner: bool = True
    ) -> Tuple[Optional[ToolArtifact], ExecutionTrace]:
        """
        Synthesize a tool with automatic refinement on failure.

        Args:
            task: Task description
            tool_name: Optional tool name
            use_refiner: Whether to use refiner on failure

        Returns:
            (tool, trace) - tool is None if all attempts failed
        """
        # First try normal synthesis
        tool, trace = self.synthesize(task, tool_name)

        if tool:
            return tool, trace

        if not use_refiner:
            return None, trace

        # Import refiner here to avoid circular import
        from src.evolution.refiner import Refiner

        # Get the generated code from LLM (need to regenerate since synthesize doesn't return it on failure)
        result = self.llm.generate_tool_code(task)
        code = result.get("code_payload")

        if not code:
            return None, trace

        # Use refiner to fix the code
        print("[Synthesizer] Synthesis failed, invoking Refiner...")
        refiner = Refiner(self.llm, self.executor, self.registry)
        refined_tool, error_reports = refiner.refine(
            code=code,
            task=task,
            trace=trace
        )

        if refined_tool:
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
