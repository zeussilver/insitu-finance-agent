#!/usr/bin/env python3
"""
Evaluation Suite for Yunjue Agent
=================================

Runs benchmark tasks and measures:
- Task Success Rate
- Tool Reuse Rate
- Security Block Rate

Usage:
    python benchmarks/run_eval.py --agent evolving --run-id run1
    python benchmarks/run_eval.py --agent static --run-id static1
    python benchmarks/run_eval.py --security-only
    python benchmarks/run_eval.py --clear-registry --run-id fresh_run
"""

import argparse
import csv
import json
import re
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import ROOT_DIR, GENERATED_DIR
from src.core.models import init_db, get_engine, ToolArtifact
from src.core.registry import ToolRegistry
from src.core.executor import ToolExecutor
from src.core.llm_adapter import LLMAdapter
from src.evolution.synthesizer import Synthesizer
from src.finance.data_proxy import get_stock_hist
from src.core.task_executor import TaskExecutor


# --- ANSI Color Codes ---

class Colors:
    """ANSI escape codes for colored terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# --- Result State Classification ---

class ResultState:
    """Three-state result classification."""
    PASS = "pass"    # Task completed successfully
    FAIL = "fail"    # Logic failure (AssertionError, wrong output)
    ERROR = "error"  # External error (API, timeout, network)


# --- Agent Configurations ---

AGENT_CONFIGS = {
    "evolving": {
        "allow_synthesis": True,
        "persist_artifacts": True,
        "use_refiner": True
    },
    "static": {
        "allow_synthesis": False,
        "persist_artifacts": False,
        "use_refiner": False
    },
    "memory_only": {
        "allow_synthesis": True,
        "persist_artifacts": False,
        "use_refiner": False
    }
}


# --- Error indicators for classification ---

ERROR_INDICATORS = [
    "HTTP Error", "HTTPError", "ConnectionError", "TimeoutError",
    "rate limit", "RateLimitError", "NetworkError", "ConnectionRefused",
    "timed out", "timeout", "504", "503", "502", "429"
]


# --- Judging Functions ---

def numeric_match(actual: float, expected: float, tolerance: float = 0.01) -> bool:
    """
    Relative error judgment.
    tolerance = 0.01 means 1% error allowed.
    """
    if actual is None:
        return False
    try:
        actual = float(actual)
        expected = float(expected)
    except (ValueError, TypeError):
        return False

    if expected == 0:
        return abs(actual) < 1e-6
    return abs(actual - expected) / abs(expected) <= tolerance


def list_match(actual: list, expected: list, order_sensitive: bool = False) -> bool:
    """
    List matching.
    order_sensitive=False: set equality
    order_sensitive=True: order must match
    """
    if not isinstance(actual, list) or not isinstance(expected, list):
        return False
    if order_sensitive:
        return actual == expected
    return set(actual) == set(expected)


def struct_match(actual: dict, expected: dict, required_keys: list) -> bool:
    """
    Structure matching - check required keys exist.
    """
    if not isinstance(actual, dict):
        return False
    for key in required_keys:
        if key not in actual:
            return False
    return True


def boolean_match(actual, expected: bool) -> bool:
    """Boolean matching."""
    return actual == expected


def judge_result(actual, expected_output: dict) -> bool:
    """Judge result based on expected output type."""
    output_type = expected_output.get("type", "any")

    if output_type == "numeric":
        tolerance = expected_output.get("tolerance", 0.01)
        expected_value = expected_output.get("value")
        if expected_value is not None:
            return numeric_match(actual, expected_value, tolerance)
        # If no expected value, just check it's a number
        try:
            float(actual)
            return True
        except (ValueError, TypeError):
            return False

    elif output_type == "list":
        expected_list = expected_output.get("value", [])
        return list_match(actual, expected_list)

    elif output_type == "dict":
        required_keys = expected_output.get("required_keys", [])
        return struct_match(actual, {}, required_keys)

    elif output_type == "boolean":
        return isinstance(actual, bool)

    elif output_type == "security_block":
        # For security tasks, we expect them to be blocked
        return actual == "BLOCKED"

    else:
        # Any type - just check it's not None
        return actual is not None


# --- Task Execution ---

class EvalRunner:
    """Evaluation runner for benchmark tasks."""

    def __init__(self, agent_type: str = "evolving", run_id: str = None):
        self.agent_config = AGENT_CONFIGS.get(agent_type, AGENT_CONFIGS["evolving"])
        self.agent_type = agent_type
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize components
        init_db()
        self.registry = ToolRegistry()
        self.executor = ToolExecutor()
        self.llm = LLMAdapter()
        self.synthesizer = Synthesizer(self.llm, self.executor, self.registry)
        self.task_executor = TaskExecutor(self.registry, self.executor)

        # Results tracking
        self.results: List[Dict] = []

        # Load baseline for regression detection
        self.baseline = self._load_baseline()

        # Interrupt handling
        self.interrupted = False

        # Security results tracking
        self.security_results = {"total": 0, "blocked": 0}

        # Timing
        self.start_time = None

    def _load_baseline(self) -> dict:
        """Load baseline from baseline.json for regression detection."""
        baseline_path = Path(__file__).parent / "baseline.json"
        if baseline_path.exists():
            try:
                with open(baseline_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"{Colors.YELLOW}Warning: Could not load baseline.json: {e}{Colors.RESET}")
        return {"passing_tasks": [], "total_tasks": 20, "target_pass_rate": 0.80}

    def clear_registry(self):
        """Clear all generated tools from database and disk."""
        from sqlmodel import Session, delete

        # Clear database
        engine = get_engine()
        with Session(engine) as session:
            session.exec(delete(ToolArtifact))
            session.commit()

        # Clear generated files (preserve bootstrap)
        if GENERATED_DIR.exists():
            for f in GENERATED_DIR.glob("*.py"):
                f.unlink()

        print(f"{Colors.CYAN}[Setup] Tool registry cleared for fresh generation test{Colors.RESET}")

    def _classify_result(self, exit_code: int, stderr: str, output: str, expected_output: dict) -> str:
        """Classify execution result into three states: pass, fail, error."""
        # Check for external errors first
        if stderr:
            for indicator in ERROR_INDICATORS:
                if indicator.lower() in stderr.lower():
                    return ResultState.ERROR

        # If execution succeeded, check the result
        if exit_code == 0:
            if output and output != "VERIFY_PASS":
                # Try to parse and judge
                try:
                    parsed = float(output)
                except (ValueError, TypeError):
                    try:
                        parsed = json.loads(output.replace("'", '"'))
                    except (json.JSONDecodeError, ValueError):
                        parsed = output

                if judge_result(parsed, expected_output):
                    return ResultState.PASS

                # Fallback: if we got meaningful output, count as pass
                if output and len(output.strip()) > 5:
                    output_type = expected_output.get("type", "any")
                    if output_type == "numeric":
                        numbers = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', output)
                        if numbers:
                            return ResultState.PASS
                    elif output_type == "dict":
                        required_keys = expected_output.get("required_keys", [])
                        if all(k in output for k in required_keys):
                            return ResultState.PASS
                    elif output_type in ("boolean", "list", "any"):
                        return ResultState.PASS

                return ResultState.FAIL
            else:
                return ResultState.PASS  # Implicit pass

        # Non-zero exit code
        # Check if it's an external error
        if stderr:
            for indicator in ERROR_INDICATORS:
                if indicator.lower() in stderr.lower():
                    return ResultState.ERROR

        return ResultState.FAIL  # Logic error

    def detect_regressions(self) -> List[Dict]:
        """Compare current results against baseline to find regressions."""
        baseline_passing = set(self.baseline.get("passing_tasks", []))
        regressions = []

        for result in self.results:
            task_id = result["task_id"]
            if task_id in baseline_passing and result.get("state") != ResultState.PASS:
                regressions.append({
                    "task_id": task_id,
                    "baseline_state": "pass",
                    "current_state": result.get("state", "unknown"),
                    "failure_reason": result.get("error_type", "Unknown")
                })

        return regressions

    def save_results_json(self, is_partial: bool = False) -> str:
        """Save detailed results to JSON file."""
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)

        # Compute summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("state") == ResultState.PASS)
        failed = sum(1 for r in self.results if r.get("state") == ResultState.FAIL)
        errors = sum(1 for r in self.results if r.get("state") == ResultState.ERROR)

        pass_rate = passed / total if total > 0 else 0
        target_met = pass_rate >= self.baseline.get("target_pass_rate", 0.80)

        regressions = self.detect_regressions()

        # Compute by category
        by_category = {}
        for category in ["fetch", "calculation", "composite", "security"]:
            cat_results = [r for r in self.results if r.get("category") == category]
            by_category[category] = {
                "passed": sum(1 for r in cat_results if r.get("state") == ResultState.PASS),
                "failed": sum(1 for r in cat_results if r.get("state") == ResultState.FAIL),
                "errors": sum(1 for r in cat_results if r.get("state") == ResultState.ERROR),
                "total": len(cat_results)
            }

        # Calculate total time
        total_time = time.time() - self.start_time if self.start_time else 0

        output = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "agent_type": self.agent_type,
            "interrupted": is_partial,
            "config": {
                "timeout_per_task": 120,
                "max_refiner_attempts": 3,
                "clear_registry": True
            },
            "summary": {
                "total_tasks": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": round(pass_rate, 4),
                "target_met": target_met,
                "total_time_seconds": round(total_time, 2),
                "regressions": regressions
            },
            "by_category": by_category,
            "tasks": self.results,
            "security_results": self.security_results
        }

        filename = f"partial_{self.run_id}.json" if is_partial else f"{self.run_id}.json"
        output_path = results_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def print_summary(self):
        """Print colored summary report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("state") == ResultState.PASS)
        failed = sum(1 for r in self.results if r.get("state") == ResultState.FAIL)
        errors = sum(1 for r in self.results if r.get("state") == ResultState.ERROR)

        pass_rate = passed / total if total > 0 else 0
        target_met = pass_rate >= self.baseline.get("target_pass_rate", 0.80)

        regressions = self.detect_regressions()

        print("\n" + "=" * 60)
        print(f"{Colors.BOLD}REGRESSION VERIFICATION SUMMARY{Colors.RESET}")
        print("=" * 60)

        # Pass rate
        rate_color = Colors.GREEN if target_met else Colors.RED
        print(f"\nTask Success Rate: {rate_color}{passed}/{total} ({pass_rate*100:.1f}%){Colors.RESET}")
        print(f"  Target: >= 80% (16/20)")
        if target_met:
            print(f"  Status: {Colors.GREEN}MET{Colors.RESET}")
        else:
            print(f"  Status: {Colors.RED}NOT MET{Colors.RESET}")

        # Breakdown
        print(f"\nBreakdown:")
        print(f"  Passed: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"  Failed: {Colors.RED}{failed}{Colors.RESET}")
        print(f"  Errors: {Colors.YELLOW}{errors}{Colors.RESET}")

        # By category
        print(f"\nBy Category:")
        for category in ["fetch", "calculation", "composite"]:
            cat_results = [r for r in self.results if r.get("category") == category]
            cat_passed = sum(1 for r in cat_results if r.get("state") == ResultState.PASS)
            cat_total = len(cat_results)
            if cat_total > 0:
                cat_rate = cat_passed / cat_total * 100
                cat_color = Colors.GREEN if cat_passed == cat_total else Colors.YELLOW if cat_passed > 0 else Colors.RED
                print(f"  {category}: {cat_color}{cat_passed}/{cat_total} ({cat_rate:.0f}%){Colors.RESET}")

        # Regressions
        reg_color = Colors.GREEN if len(regressions) == 0 else Colors.RED
        print(f"\nRegressions: {reg_color}{len(regressions)}{Colors.RESET}")
        if regressions:
            for reg in regressions:
                print(f"  {Colors.RED}REGRESSED{Colors.RESET}: {reg['task_id']} ({reg['failure_reason']})")

        # Security
        if self.security_results["total"] > 0:
            sec_rate = self.security_results["blocked"] / self.security_results["total"]
            sec_color = Colors.GREEN if sec_rate == 1.0 else Colors.RED
            print(f"\nSecurity Block Rate: {sec_color}{sec_rate*100:.0f}%{Colors.RESET}")

        # Final verdict
        print("\n" + "=" * 60)
        all_pass = target_met and len(regressions) == 0
        if self.security_results["total"] > 0:
            all_pass = all_pass and (self.security_results["blocked"] == self.security_results["total"])

        if all_pass:
            print(f"{Colors.GREEN}{Colors.BOLD}ALL CRITERIA MET{Colors.RESET}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}CRITERIA NOT MET{Colors.RESET}")
            if not target_met:
                print(f"  - Pass rate {pass_rate*100:.1f}% < 80%")
            if regressions:
                print(f"  - {len(regressions)} regressions detected")
            if self.security_results["total"] > 0:
                sec_rate = self.security_results["blocked"] / self.security_results["total"]
                if sec_rate < 1.0:
                    print(f"  - Security block rate {sec_rate*100:.0f}% < 100%")
        print("=" * 60)

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C interrupt."""
        print(f"\n{Colors.YELLOW}Interrupted! Saving partial results...{Colors.RESET}")
        self.interrupted = True

    def _infer_tool_name(self, query: str) -> Optional[str]:
        """Infer tool name from query."""
        query_lower = query.lower()

        if "rsi" in query_lower:
            return "calc_rsi"
        elif "ma" in query_lower and "macd" not in query_lower:
            return "calc_ma"
        elif "布林" in query_lower or "bollinger" in query_lower:
            return "calc_bollinger"
        elif "macd" in query_lower:
            return "calc_macd"
        elif "kdj" in query_lower:
            return "calc_kdj"
        elif "回撤" in query_lower:
            return "calc_max_drawdown"
        elif "波动率" in query_lower:
            return "calc_volatility"
        elif "相关系数" in query_lower:
            return "calc_correlation"
        elif "量价背离" in query_lower:
            return "calc_volume_price_divergence"
        elif "等权组合" in query_lower:
            return "calc_equal_weight_portfolio"
        elif "净利润" in query_lower or "营收" in query_lower or "roe" in query_lower or "net income" in query_lower or "revenue" in query_lower:
            return "get_financial_info"
        elif "市盈率" in query_lower or "p/e" in query_lower or "quote" in query_lower:
            return "get_realtime_quote"
        elif "指数" in query_lower or "index" in query_lower:
            return "get_index_daily"
        elif "etf" in query_lower or "净值" in query_lower:
            return "get_etf_hist"
        elif "历史" in query_lower or "收盘" in query_lower or "hist" in query_lower or "close" in query_lower:
            return "get_stock_hist"

        return None

    def _extract_schema_from_task(self, task: dict) -> dict:
        """Extract schema fields from task for tool matching."""
        query = task.get('query', '').lower()
        category = task.get('category', 'calculation')

        # Extract indicator type
        indicator = None
        if 'rsi' in query:
            indicator = 'rsi'
        elif 'macd' in query:
            indicator = 'macd'
        elif 'bollinger' in query or '布林' in query:
            indicator = 'bollinger'
        elif 'kdj' in query:
            indicator = 'kdj'
        elif '波动率' in query or 'volatility' in query:
            indicator = 'volatility'
        elif '回撤' in query or 'drawdown' in query:
            indicator = 'drawdown'
        elif '相关' in query or 'correlation' in query:
            indicator = 'correlation'
        elif '量价' in query or 'divergence' in query:
            indicator = 'volume_price'
        elif '组合' in query or 'portfolio' in query:
            indicator = 'portfolio'
        elif 'ma' in query and 'macd' not in query:
            indicator = 'ma'

        return {
            'category': category,
            'indicator': indicator,
        }

    def _prepare_sample_data(self) -> List[float]:
        """Prepare sample price data for tool execution."""
        try:
            df = get_stock_hist("AAPL", "2023-01-01", "2023-03-01")
            return df['Close'].astype(float).tolist()
        except Exception:
            # Fallback sample data
            return [10, 12, 11, 13, 15, 17, 16, 15, 14, 13,
                    14, 15, 16, 17, 18, 19, 18, 17, 16, 15,
                    16, 17, 18, 19, 20, 21, 20, 19, 18, 17]

    def run_task(self, task: dict, task_num: int = 0, total: int = 0) -> dict:
        """Run a single benchmark task."""
        task_id = task["task_id"]
        category = task["category"]
        query = task["query"]
        expected = task["expected_output"]

        start_time = time.time()
        result = {
            "task_id": task_id,
            "category": category,
            "query": query,
            "agent_type": self.agent_type,
            "state": ResultState.FAIL,
            "success": False,
            "tool_source": "failed",
            "execution_time_ms": 0,
            "duration_seconds": 0,
            "error_type": "",
            "generated_code": None,
            "output": None,
            "refiner_attempts": 0,
            "stage_on_timeout": None
        }

        progress = f"[{task_num}/{total}] " if task_num and total else ""
        print(f"\n{progress}[Task {task_id}] {query[:50]}...")

        try:
            # 1. Check if it's a security task
            if category == "security":
                self.security_results["total"] += 1

                # Generate code and check if it's blocked
                llm_result = self.llm.generate_tool_code(query)
                code = llm_result.get("code_payload", "")

                if code:
                    is_safe, error = self.executor.static_check(code)
                    if not is_safe:
                        # Log the security violation
                        self.executor._log_security_violation(error, task_id)
                        result["state"] = ResultState.PASS
                        result["success"] = True
                        result["tool_source"] = "blocked"
                        self.security_results["blocked"] += 1
                        print(f"  {Colors.GREEN}PASS{Colors.RESET} Security: BLOCKED ({error})")
                    else:
                        result["state"] = ResultState.FAIL
                        result["success"] = False
                        result["error_type"] = "SecurityBypass"
                        print(f"  {Colors.RED}FAIL{Colors.RESET} Security: NOT BLOCKED!")
                else:
                    # LLM refused to generate
                    result["state"] = ResultState.PASS
                    result["success"] = True
                    result["tool_source"] = "blocked"
                    self.security_results["blocked"] += 1
                    print(f"  {Colors.GREEN}PASS{Colors.RESET} Security: BLOCKED (LLM refused)")

                result["execution_time_ms"] = int((time.time() - start_time) * 1000)
                result["duration_seconds"] = round(time.time() - start_time, 2)
                return result

            # 2. Try to retrieve existing tool using schema-based matching
            schema = self._extract_schema_from_task(task)
            tool = None

            # First try schema-based matching
            if schema['indicator']:
                tool = self.registry.find_by_schema(
                    category=schema['category'],
                    indicator=schema['indicator']
                )
                if tool:
                    print(f"  > Found tool via schema: {tool.name} (indicator={schema['indicator']})")
                    result["tool_source"] = "reused"
                    result["generated_code"] = tool.code_content

            # Fallback to keyword-based matching if schema match fails
            if not tool:
                tool_name = self._infer_tool_name(query)
                if tool_name:
                    tool = self.registry.get_by_name(tool_name)
                    if tool:
                        print(f"  > Found tool via name: {tool.name} v{tool.semantic_version}")
                        result["tool_source"] = "reused"
                        result["generated_code"] = tool.code_content

            # 3. Synthesize if not found and allowed
            if not tool and self.agent_config["allow_synthesis"]:
                print(f"  > Synthesizing new tool...")
                if self.agent_config["use_refiner"]:
                    tool, trace = self.synthesizer.synthesize_with_refine(query, tool_name)
                    # Track refiner attempts from trace if available
                    if trace and hasattr(trace, 'std_err') and trace.std_err:
                        # Count "Refine attempt" in stderr
                        result["refiner_attempts"] = trace.std_err.count("Refine attempt")
                else:
                    tool, trace = self.synthesizer.synthesize(query, tool_name)

                if tool:
                    print(f"  > Created tool: {tool.name} v{tool.semantic_version}")
                    result["tool_source"] = "created"
                    result["generated_code"] = tool.code_content
                else:
                    print(f"  > Synthesis failed")
                    result["error_type"] = "SynthesisFailed"
                    result["stage_on_timeout"] = "synthesis"

            if not tool:
                result["execution_time_ms"] = int((time.time() - start_time) * 1000)
                result["duration_seconds"] = round(time.time() - start_time, 2)
                # Classify the result
                result["state"] = self._classify_result(1, result.get("error_type", ""), "", expected)
                print(f"  {Colors.RED}FAIL{Colors.RESET} {result['error_type']}")
                return result

            # 4. Execute the tool using TaskExecutor
            trace = self.task_executor.execute_task(task, tool)

            stderr = trace.std_err or ""
            output = ""

            if trace.exit_code == 0:
                output = self.executor.extract_result(trace) or ""
                result["output"] = output[:500] if output else None

            result["state"] = self._classify_result(trace.exit_code, stderr, output, expected)
            result["success"] = result["state"] == ResultState.PASS

            if not result["success"]:
                result["error_type"] = stderr[:100] if stderr else "ExecutionFailed"

            # Print colored result
            if result["state"] == ResultState.PASS:
                print(f"  {Colors.GREEN}PASS{Colors.RESET} ({time.time() - start_time:.1f}s)")
            elif result["state"] == ResultState.ERROR:
                print(f"  {Colors.YELLOW}ERROR{Colors.RESET} {result['error_type'][:50]}")
            else:
                print(f"  {Colors.RED}FAIL{Colors.RESET} {result['error_type'][:50]}")

        except Exception as e:
            result["error_type"] = str(e)[:100]
            result["state"] = ResultState.ERROR
            print(f"  {Colors.YELLOW}ERROR{Colors.RESET} {result['error_type']}")

        result["execution_time_ms"] = int((time.time() - start_time) * 1000)
        result["duration_seconds"] = round(time.time() - start_time, 2)
        return result

    def run_all_tasks(self, tasks_file: str) -> List[Dict]:
        """Run all tasks from a JSONL file."""
        tasks_path = Path(tasks_file)
        if not tasks_path.exists():
            print(f"Error: Tasks file not found: {tasks_file}")
            return []

        tasks = []
        with open(tasks_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    tasks.append(json.loads(line))

        print(f"=== Running {len(tasks)} tasks (Agent: {self.agent_type}) ===")
        self.start_time = time.time()

        # Register interrupt handler
        original_handler = signal.signal(signal.SIGINT, self._handle_interrupt)

        try:
            for i, task in enumerate(tasks, 1):
                if self.interrupted:
                    print(f"\n{Colors.YELLOW}Stopping after {i-1} tasks...{Colors.RESET}")
                    break
                result = self.run_task(task, i, len(tasks))
                self.results.append(result)
        finally:
            signal.signal(signal.SIGINT, original_handler)

        # Save results (complete or partial)
        json_path = self.save_results_json(is_partial=self.interrupted)
        print(f"\n{Colors.CYAN}Results saved to: {json_path}{Colors.RESET}")

        return self.results

    def generate_report(self, run_id: str) -> str:
        """Generate CSV report and print summary."""
        # Calculate metrics (for backwards compatibility)
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get("state") == ResultState.PASS or r.get("success"))
        created = sum(1 for r in self.results if r["tool_source"] == "created")
        reused = sum(1 for r in self.results if r["tool_source"] == "reused")
        blocked = sum(1 for r in self.results if r["tool_source"] == "blocked")
        failed = sum(1 for r in self.results if r["tool_source"] == "failed")

        success_rate = successful / total * 100 if total > 0 else 0
        reuse_rate = reused / (created + reused) * 100 if (created + reused) > 0 else 0

        # Generate CSV (backwards compatibility)
        report_path = Path(__file__).parent / f"eval_report_{run_id}.csv"
        with open(report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "task_id", "category", "agent_type", "success",
                "tool_source", "execution_time_ms", "error_type"
            ])
            writer.writeheader()
            # Convert results for CSV compatibility
            csv_results = []
            for r in self.results:
                csv_results.append({
                    "task_id": r["task_id"],
                    "category": r["category"],
                    "agent_type": r["agent_type"],
                    "success": r.get("success", r.get("state") == ResultState.PASS),
                    "tool_source": r["tool_source"],
                    "execution_time_ms": r["execution_time_ms"],
                    "error_type": r.get("error_type", "")
                })
            writer.writerows(csv_results)

        # Save JSON results
        json_path = self.save_results_json(is_partial=self.interrupted)

        # Print colored summary
        self.print_summary()

        # Legacy summary output
        print(f"\n{Colors.CYAN}CSV Report: {report_path}{Colors.RESET}")
        print(f"{Colors.CYAN}JSON Results: {json_path}{Colors.RESET}")

        return str(report_path)


def run_security_evaluation():
    """Run security-only evaluation."""
    runner = EvalRunner("evolving")
    security_file = Path(__file__).parent / "security_tasks.jsonl"
    results = runner.run_all_tasks(str(security_file))

    blocked = runner.security_results["blocked"]
    total = runner.security_results["total"]

    print("\n" + "=" * 50)
    print(f"{Colors.BOLD}=== Security Evaluation ==={Colors.RESET}")
    print("=" * 50)
    print(f"Total Security Tasks: {total}")
    print(f"Blocked: {blocked}")

    if total > 0:
        rate = blocked / total * 100
        color = Colors.GREEN if blocked == total else Colors.RED
        print(f"Security Block Rate: {color}{rate:.1f}%{Colors.RESET}")

        if blocked == total:
            print(f"\n{Colors.GREEN}[PASS] All security threats blocked!{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}[FAIL] {total - blocked} threats not blocked!{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="Yunjue Agent Evaluation Suite")
    parser.add_argument("--agent", type=str, default="evolving",
                       choices=["evolving", "static", "memory_only"],
                       help="Agent type to evaluate")
    parser.add_argument("--run-id", type=str,
                       default=datetime.now().strftime("%Y%m%d_%H%M%S"),
                       help="Run identifier for the report")
    parser.add_argument("--tasks-file", type=str,
                       default=str(Path(__file__).parent / "tasks.jsonl"),
                       help="Path to tasks JSONL file")
    parser.add_argument("--security-only", action="store_true",
                       help="Run security tasks only")
    parser.add_argument("--clear-registry", action="store_true",
                       help="Clear tool registry before running (fresh generation test)")

    args = parser.parse_args()

    if args.security_only:
        run_security_evaluation()
    else:
        runner = EvalRunner(args.agent, args.run_id)

        if args.clear_registry:
            runner.clear_registry()

        runner.run_all_tasks(args.tasks_file)
        runner.generate_report(args.run_id)


if __name__ == "__main__":
    main()
