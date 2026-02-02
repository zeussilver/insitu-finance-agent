#!/usr/bin/env python3
"""
Yunjue Agent - Self-Evolving Financial Agent System
====================================================

CLI entry point for the Phase 1a MVP.

Commands:
    python main.py --init              Initialize database
    python main.py --bootstrap         Create bootstrap tools
    python main.py --task "计算 RSI"    Run a task
    python main.py --list              List registered tools
    python main.py --security-check    Verify security mechanisms
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import DB_PATH, GENERATED_DIR, CACHE_DIR
from src.core.models import init_db
from src.core.registry import ToolRegistry
from src.core.executor import ToolExecutor
from src.core.llm_adapter import LLMAdapter
from src.evolution.synthesizer import Synthesizer
from src.finance.data_proxy import get_stock_hist
from src.finance.bootstrap import create_bootstrap_tools


def cmd_init():
    """Initialize the database."""
    print("=== Initializing Database ===")
    init_db()
    print(f"Database created at: {DB_PATH}")
    print("Tables: tool_artifacts, execution_traces, error_reports, tool_patches, batch_merge_records")
    print("[Done] Database initialized successfully.")


def cmd_bootstrap():
    """Create and register bootstrap tools."""
    create_bootstrap_tools()


def cmd_list():
    """List all registered tools."""
    print("=== Registered Tools ===\n")
    registry = ToolRegistry()
    tools = registry.list_tools()

    if not tools:
        print("No tools registered yet.")
        return

    for tool in tools:
        print(f"  [{tool.id}] {tool.name} v{tool.semantic_version}")
        print(f"      Status: {tool.status.value}")
        print(f"      File: {tool.file_path}")
        print()


def cmd_task(task: str):
    """Execute a task (synthesize or retrieve tool, then execute)."""
    print(f"=== FinEvo Agent Phase 1a MVP ===")
    print(f"Task: {task}\n")

    # Initialize components
    registry = ToolRegistry()
    executor = ToolExecutor()
    llm = LLMAdapter()
    synthesizer = Synthesizer(llm, executor, registry)

    # Step 1: Try to get context data
    print("[Step 1] Preparing context data...")
    try:
        df = get_stock_hist("AAPL", "2023-01-01", "2023-02-01")
        prices = df['Close'].astype(float).tolist()
        print(f"  > Loaded {len(prices)} price records")
    except Exception as e:
        print(f"  > Data fetch skipped: {e}")
        prices = [10, 12, 11, 13, 15, 17, 16, 15, 14, 13, 14, 15, 16, 17, 18]
        print(f"  > Using sample data: {len(prices)} records")

    # Step 2: Synthesize or retrieve tool
    # Try to infer tool name from task
    tool_name = None
    if "rsi" in task.lower():
        tool_name = "calc_rsi"
    elif "ma" in task.lower() or "均线" in task:
        tool_name = "calc_ma"
    elif "布林" in task.lower() or "bollinger" in task.lower():
        tool_name = "calc_bollinger"
    elif "macd" in task.lower():
        tool_name = "calc_macd"

    tool = None
    if tool_name:
        tool = registry.get_by_name(tool_name)
        if tool:
            print(f"\n[Step 2] Tool '{tool_name}' found in registry.")
            print(f"  > Version: {tool.semantic_version}")
            print(f"  > Status: {tool.status.value}")

    if not tool:
        print(f"\n[Step 2] Synthesizing new tool...")
        tool, trace = synthesizer.synthesize(task, tool_name)

        if not tool:
            print(f"  > Synthesis failed: {trace.std_err}")
            return

        print(f"  > Tool registered: {tool.name} v{tool.semantic_version}")

    # Step 3: Execute the tool
    print(f"\n[Step 3] Executing tool...")

    # Prepare arguments based on tool name
    args = {}
    if "rsi" in tool.name.lower():
        args = {"prices": prices[:20], "period": 14}
    elif "ma" in tool.name.lower():
        args = {"prices": prices[:20], "window": 5}
    elif "bollinger" in tool.name.lower():
        args = {"prices": prices[:20], "window": 20, "num_std": 2}
    elif "macd" in tool.name.lower():
        args = {"prices": prices[:26]}
    else:
        # Generic args - just pass prices
        args = {"prices": prices[:20]}

    exec_trace = executor.execute(
        tool.code_content,
        tool.name,
        args,
        f"task_{tool.name}"
    )

    if exec_trace.exit_code == 0:
        result = executor.extract_result(exec_trace)
        print(f"  > Success!")
        print(f"  > Result: {result}")
        print(f"  > Execution time: {exec_trace.execution_time_ms}ms")
    else:
        print(f"  > Execution failed:")
        print(f"  > Error: {exec_trace.std_err}")


def cmd_verify_security():
    """Verify security mechanisms work."""
    print("=== Security Verification ===\n")
    executor = ToolExecutor()

    dangerous_tasks = [
        ("执行 rm -rf /", "import os; os.system('rm -rf /')"),
        ("读取系统文件", "import subprocess; subprocess.run(['cat', '/etc/passwd'])"),
        ("执行任意代码", "eval('__import__(\"os\").system(\"ls\")')"),
    ]

    all_blocked = True
    for task, code in dangerous_tasks:
        is_safe, error = executor.static_check(code)
        status = "BLOCKED" if not is_safe else "ALLOWED (FAIL!)"
        print(f"  {task}: {status}")
        if is_safe:
            all_blocked = False

    print()
    if all_blocked:
        print("[Pass] All dangerous operations blocked!")
    else:
        print("[FAIL] Some dangerous operations were not blocked!")


def main():
    parser = argparse.ArgumentParser(
        description="Yunjue Agent - Self-Evolving Financial Agent System"
    )
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--bootstrap", action="store_true", help="Create bootstrap tools")
    parser.add_argument("--task", type=str, help="Task description")
    parser.add_argument("--list", action="store_true", help="List registered tools")
    parser.add_argument("--security-check", action="store_true", help="Verify security mechanisms")

    args = parser.parse_args()

    if args.init:
        cmd_init()
    elif args.bootstrap:
        cmd_bootstrap()
    elif args.list:
        cmd_list()
    elif args.security_check:
        cmd_verify_security()
    elif args.task:
        cmd_task(args.task)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
