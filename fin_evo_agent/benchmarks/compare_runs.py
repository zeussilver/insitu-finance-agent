#!/usr/bin/env python3
"""
Compare two evaluation runs for consistency and improvement.

Implements eval.md Section 6.2 (regression_test) and check.md Step 8.2.

Usage:
    python benchmarks/compare_runs.py run1 run2

Metrics:
    - Consistency Rate: % of tasks with same success result (target >= 95%)
    - Tool Reuse Improvement: run2 should have more reused tools
    - Execution Time Comparison: run2 should be faster on average
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List


def load_report(run_id: str) -> Dict[str, dict]:
    """Load evaluation report CSV into a dict keyed by task_id."""
    report_path = Path(__file__).parent / f"eval_report_{run_id}.csv"
    if not report_path.exists():
        print(f"Error: Report not found: {report_path}")
        sys.exit(1)

    results = {}
    with open(report_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results[row["task_id"]] = row
    return results


def compare_runs(run1_id: str, run2_id: str) -> bool:
    """
    Compare two runs and print detailed report.

    Returns:
        True if consistency rate >= 95%, False otherwise
    """
    run1 = load_report(run1_id)
    run2 = load_report(run2_id)

    # Align by task_id
    all_tasks = sorted(set(run1.keys()) | set(run2.keys()))

    if not all_tasks:
        print("Error: No tasks found in reports")
        return False

    # --- Per-task comparison ---
    consistent = 0
    total = len(all_tasks)
    rows = []

    for task_id in all_tasks:
        r1 = run1.get(task_id, {})
        r2 = run2.get(task_id, {})

        s1 = r1.get("success", "N/A")
        s2 = r2.get("success", "N/A")
        src1 = r1.get("tool_source", "N/A")
        src2 = r2.get("tool_source", "N/A")
        t1 = r1.get("execution_time_ms", "N/A")
        t2 = r2.get("execution_time_ms", "N/A")

        match = s1 == s2
        if match:
            consistent += 1

        rows.append({
            "task_id": task_id,
            "run1_success": s1,
            "run2_success": s2,
            "run1_source": src1,
            "run2_source": src2,
            "run1_time": t1,
            "run2_time": t2,
            "match": "YES" if match else "NO"
        })

    consistency_rate = consistent / total * 100 if total > 0 else 0

    # --- Tool source distribution ---
    def count_sources(run_data: Dict[str, dict]) -> dict:
        counts = {"created": 0, "reused": 0, "blocked": 0, "failed": 0}
        for r in run_data.values():
            src = r.get("tool_source", "failed")
            if src in counts:
                counts[src] += 1
        return counts

    src1_counts = count_sources(run1)
    src2_counts = count_sources(run2)

    # --- Execution time ---
    def avg_time(run_data: Dict[str, dict]) -> float:
        times = []
        for r in run_data.values():
            try:
                times.append(int(r.get("execution_time_ms", 0)))
            except (ValueError, TypeError):
                pass
        return sum(times) / len(times) if times else 0

    avg_t1 = avg_time(run1)
    avg_t2 = avg_time(run2)

    # --- Success rates ---
    def success_rate(run_data: Dict[str, dict]) -> float:
        total_r = len(run_data)
        passed = sum(1 for r in run_data.values() if r.get("success") == "True")
        return passed / total_r * 100 if total_r > 0 else 0

    sr1 = success_rate(run1)
    sr2 = success_rate(run2)

    # --- Print Report ---
    print("=" * 70)
    print(f"  Run Comparison: {run1_id} vs {run2_id}")
    print("=" * 70)

    # Summary
    print(f"\n--- Summary ---")
    print(f"  Total tasks compared:  {total}")
    print(f"  Consistent results:    {consistent}/{total}")
    print(f"  Consistency Rate:      {consistency_rate:.1f}% (target >= 95%)")
    print(f"  Run1 Success Rate:     {sr1:.1f}%")
    print(f"  Run2 Success Rate:     {sr2:.1f}%")

    # Tool source comparison
    print(f"\n--- Tool Source Distribution ---")
    print(f"  {'Source':<12} {'Run1':>6} {'Run2':>6} {'Change':>8}")
    print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*8}")
    for src in ["created", "reused", "blocked", "failed"]:
        c1 = src1_counts[src]
        c2 = src2_counts[src]
        diff = c2 - c1
        sign = "+" if diff > 0 else ""
        print(f"  {src:<12} {c1:>6} {c2:>6} {sign}{diff:>7}")

    reuse_improved = src2_counts["reused"] >= src1_counts["reused"]
    print(f"\n  Reuse improved: {'YES' if reuse_improved else 'NO'}")

    # Execution time
    print(f"\n--- Execution Time ---")
    print(f"  Run1 avg: {avg_t1:.0f} ms")
    print(f"  Run2 avg: {avg_t2:.0f} ms")
    time_improved = avg_t2 <= avg_t1
    print(f"  Time improved: {'YES' if time_improved else 'NO'}")

    # Per-task table
    print(f"\n--- Per-Task Comparison ---")
    print(f"  {'Task ID':<12} {'R1 Success':>10} {'R2 Success':>10} {'R1 Source':>10} {'R2 Source':>10} {'Match':>6}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*6}")
    for row in rows:
        print(f"  {row['task_id']:<12} {row['run1_success']:>10} {row['run2_success']:>10} "
              f"{row['run1_source']:>10} {row['run2_source']:>10} {row['match']:>6}")

    # Final verdict
    print(f"\n{'=' * 70}")
    passed = consistency_rate >= 95.0
    if passed:
        print(f"  [PASS] Consistency Rate {consistency_rate:.1f}% >= 95%")
    else:
        print(f"  [FAIL] Consistency Rate {consistency_rate:.1f}% < 95%")
    print(f"{'=' * 70}")

    return passed


def main():
    parser = argparse.ArgumentParser(
        description="Compare two evaluation runs for consistency"
    )
    parser.add_argument("run1", help="First run ID (e.g., run1)")
    parser.add_argument("run2", help="Second run ID (e.g., run2)")
    args = parser.parse_args()

    passed = compare_runs(args.run1, args.run2)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
