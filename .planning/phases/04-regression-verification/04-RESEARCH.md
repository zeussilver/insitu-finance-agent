# Phase 4: Regression Verification - Research

**Researched:** 2026-02-02
**Domain:** Benchmark evaluation infrastructure, test reporting, regression detection
**Confidence:** HIGH

## Summary

This phase implements a verification run of the full benchmark suite to confirm all Phase 1-3 fixes work together. The existing `run_eval.py` provides the evaluation framework, but needs enhancements to meet CONTEXT.md requirements:

1. **Registry clearing** before runs to test fresh tool generation (not reuse)
2. **JSON results storage** with detailed data including generated tool code
3. **Regression detection** by comparing against a baseline of 13 previously-passing tasks
4. **Colored console output** for pass/fail visibility
5. **Per-category reporting** (fetch/calc/composite pass rates)
6. **Graceful interrupt handling** to save partial results on Ctrl+C
7. **Three-state results** (pass, fail, error) distinguishing logic failures from API/timeout errors

The evaluation infrastructure is largely in place. The main work is extending `run_eval.py` with the reporting and baseline comparison features specified in CONTEXT.md.

**Primary recommendation:** Extend `run_eval.py` with JSON output, baseline comparison, and colored console output. Use ANSI escape codes directly (no new dependencies). Store baseline in a dedicated `baseline.json` file tracking the 13 previously-passing tasks.

## Standard Stack

### Core Libraries (Already Present)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| json | stdlib | JSON results storage | Already used in run_eval.py |
| time | stdlib | Timing information | Already used in run_eval.py |
| signal | stdlib | Ctrl+C interrupt handling | Standard pattern for graceful shutdown |
| pathlib | stdlib | File path handling | Already used throughout codebase |

### For Colored Output

| Option | Decision | Rationale |
|--------|----------|-----------|
| ANSI escape codes | USE THIS | No new dependency, works on macOS/Linux where project runs |
| colorama | Not needed | Project runs on macOS, ANSI codes work natively |
| rich | Overkill | Too heavy for simple pass/fail colors |

### No New Dependencies Required

The existing stack (json, time, pathlib, signal) plus raw ANSI escape codes covers all requirements.

## Architecture Patterns

### Pattern 1: Baseline Comparison File

**What:** Store baseline results as JSON for regression detection.
**When to use:** At the start of verification phase, define which tasks were passing.

```python
# File: benchmarks/baseline.json
{
    "version": "2026-02-02",
    "description": "Baseline from run1_v2.csv - 13 passing tasks",
    "passing_tasks": [
        "fetch_001", "fetch_002", "fetch_003", "fetch_004",
        "fetch_005", "fetch_006", "fetch_007", "fetch_008",
        "calc_002", "calc_007",
        "comp_001", "comp_003", "comp_004"
    ],
    "total_tasks": 20,
    "target_pass_rate": 0.80
}
```

**Source:** Analysis of `eval_report_run1_v2.csv` shows these 13 tasks passing.

### Pattern 2: Three-State Result Classification

**What:** Distinguish pass, fail (logic), and error (API/timeout/network).
**When to use:** In result recording to enable separate analysis.

```python
# Recommended pattern from CONTEXT.md
class ResultState:
    PASS = "pass"           # Task completed successfully
    FAIL = "fail"           # Logic failure (AssertionError, wrong output)
    ERROR = "error"         # External error (API, timeout, network)

def classify_result(trace, expected_output):
    """Classify execution result into three states."""
    if trace.exit_code == 0:
        if judge_result(trace.output, expected_output):
            return ResultState.PASS
        return ResultState.FAIL  # Wrong output but no crash

    # Check for API/external errors
    stderr = trace.std_err or ""
    if any(err in stderr for err in ("HTTP Error", "ConnectionError", "TimeoutError", "rate limit")):
        return ResultState.ERROR

    return ResultState.FAIL  # Logic error (TypeError, AssertionError, etc.)
```

### Pattern 3: JSON Results Schema

**What:** Detailed JSON output for each run.
**When to use:** Save after each complete run to `benchmarks/results/{run-id}.json`.

```python
# Recommended schema (Claude's discretion from CONTEXT.md)
{
    "run_id": "run_20260202_143000",
    "timestamp": "2026-02-02T14:30:00",
    "agent_type": "evolving",
    "config": {
        "timeout_per_task": 120,
        "max_refiner_attempts": 3,
        "clear_registry": true
    },
    "summary": {
        "total_tasks": 20,
        "passed": 16,
        "failed": 3,
        "errors": 1,
        "pass_rate": 0.80,
        "target_met": true,
        "total_time_seconds": 1234.5,
        "regressions": []
    },
    "by_category": {
        "fetch": {"passed": 8, "failed": 0, "errors": 0, "total": 8},
        "calculation": {"passed": 6, "failed": 1, "errors": 1, "total": 8},
        "composite": {"passed": 2, "failed": 2, "errors": 0, "total": 4}
    },
    "tasks": [
        {
            "task_id": "calc_001",
            "category": "calculation",
            "query": "Calculate AAPL RSI-14...",
            "state": "pass",
            "tool_source": "created",
            "duration_seconds": 45.2,
            "generated_code": "import pandas as pd\n...",
            "output": "65.23",
            "error_type": null,
            "refiner_attempts": 0,
            "stage_on_timeout": null
        }
    ],
    "security_results": {
        "total": 5,
        "blocked": 5,
        "block_rate": 1.0
    }
}
```

### Pattern 4: ANSI Color Codes for Console

**What:** Simple colored output without dependencies.
**When to use:** For progress display and summary.

```python
# ANSI escape codes for macOS/Linux terminals
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def print_pass(task_id):
    print(f"{Colors.GREEN}[PASS]{Colors.RESET} {task_id}")

def print_fail(task_id, reason):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {task_id}: {reason[:50]}")

def print_error(task_id, reason):
    print(f"{Colors.YELLOW}[ERROR]{Colors.RESET} {task_id}: {reason[:50]}")
```

### Pattern 5: Graceful Interrupt Handling

**What:** Save partial results on Ctrl+C.
**When to use:** Wrap evaluation loop with signal handler.

```python
import signal

class EvalRunner:
    def __init__(self):
        self.results = []
        self.interrupted = False

    def _handle_interrupt(self, signum, frame):
        print(f"\n{Colors.YELLOW}Interrupted! Saving partial results...{Colors.RESET}")
        self.interrupted = True

    def run_all_tasks(self, tasks):
        # Register interrupt handler
        original_handler = signal.signal(signal.SIGINT, self._handle_interrupt)

        try:
            for task in tasks:
                if self.interrupted:
                    break
                result = self.run_task(task)
                self.results.append(result)
        finally:
            signal.signal(signal.SIGINT, original_handler)

        # Save results (complete or partial)
        filename = f"partial_{self.run_id}.json" if self.interrupted else f"{self.run_id}.json"
        self.save_results(filename)
```

### Pattern 6: Registry Clearing for Fresh Runs

**What:** Clear tool registry before benchmark to test generation, not reuse.
**When to use:** At start of verification run per CONTEXT.md decision.

```python
def clear_registry(self):
    """Delete all generated tools from database and disk."""
    from sqlmodel import Session, delete
    from src.core.models import ToolArtifact, get_engine
    from src.config import GENERATED_DIR
    import shutil

    # Clear database
    with Session(get_engine()) as session:
        session.exec(delete(ToolArtifact))
        session.commit()

    # Clear generated files (preserve bootstrap)
    for f in GENERATED_DIR.glob("*.py"):
        f.unlink()

    print("[Setup] Tool registry cleared for fresh generation test")
```

### Anti-Patterns to Avoid

- **Modifying baseline during verification:** Baseline is fixed; never update it based on new results
- **Parallel task execution:** CONTEXT.md specifies sequential execution
- **Automatic retry on failure:** Single attempt per task per CONTEXT.md
- **Mock LLM fallback:** Real API key required per CONTEXT.md
- **Stopping early on failure:** Continue all 20 tasks regardless of failures

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom format | `json.dumps()` with indent=2 | Standard, readable |
| Signal handling | Thread-based | `signal.signal(SIGINT, handler)` | Standard Python pattern |
| Colored output | Full library | Raw ANSI codes | No dependency, simple needs |
| Time formatting | Manual string formatting | `datetime.isoformat()` | ISO 8601 standard |

**Key insight:** The evaluation infrastructure exists. This phase extends it with reporting features, not rebuilds it.

## Common Pitfalls

### Pitfall 1: Confusing Baseline with Current Results

**What goes wrong:** Comparing run results against themselves instead of fixed baseline.
**Why it happens:** No separate baseline storage.
**How to avoid:** Store baseline in `baseline.json`, load at start, never modify during runs.
**Warning signs:** "0 regressions" when clearly some tasks regressed.

### Pitfall 2: Not Clearing Registry Before Fresh Test

**What goes wrong:** High reuse rate masks generation bugs.
**Why it happens:** Forgot to clear registry; old passing tools get reused.
**How to avoid:** Add explicit `--clear-registry` flag or always clear for verification runs.
**Warning signs:** `tool_source: "reused"` for most tasks in a "fresh generation" test.

### Pitfall 3: Treating Timeouts as Logic Failures

**What goes wrong:** Timeout counted as failed task when it's an environmental error.
**Why it happens:** No distinction between ResultState.FAIL and ResultState.ERROR.
**How to avoid:** Check stderr for timeout/network indicators before classifying.
**Warning signs:** Tasks that sometimes pass, sometimes "fail" with timeout messages.

### Pitfall 4: Missing Stage Info in Timeout Errors

**What goes wrong:** Can't tell if timeout occurred in synthesis, verification, or refinement.
**Why it happens:** Timeout error doesn't include context.
**How to avoid:** Wrap each stage with timing/stage tracking. Include `stage_on_timeout` in results.
**Warning signs:** Timeout errors with no indication of which stage was slow.

### Pitfall 5: Interrupt Losing All Results

**What goes wrong:** Ctrl+C loses all progress.
**Why it happens:** No signal handler, no incremental saving.
**How to avoid:** Register SIGINT handler, save partial results before exit.
**Warning signs:** Long runs lost to accidental Ctrl+C.

### Pitfall 6: Colors Not Displaying on Windows

**What goes wrong:** ANSI codes show as gibberish on Windows terminal.
**Why it happens:** Windows cmd doesn't support ANSI by default.
**How to avoid:** Not a concern - CLAUDE.md shows project runs on macOS. If Windows needed, add colorama.
**Warning signs:** Output like `[92m[PASS][0m` instead of green text.

## Code Examples

### Example 1: Baseline File Creation

```python
# Create baseline.json from analysis of eval_report_run1_v2.csv
# These 13 tasks passed: 8 fetch + 2 calc + 3 composite
baseline = {
    "version": "2026-02-02",
    "description": "Baseline from run1_v2.csv before Phase 3 fixes",
    "passing_tasks": [
        "fetch_001", "fetch_002", "fetch_003", "fetch_004",
        "fetch_005", "fetch_006", "fetch_007", "fetch_008",
        "calc_002", "calc_007",
        "comp_001", "comp_003", "comp_004"
    ],
    "total_tasks": 20,
    "target_pass_rate": 0.80
}

# Save to benchmarks/baseline.json
import json
with open("benchmarks/baseline.json", "w") as f:
    json.dump(baseline, f, indent=2)
```

### Example 2: Regression Detection

```python
def detect_regressions(current_results: list, baseline: dict) -> list:
    """
    Find tasks that passed in baseline but fail now.

    Returns list of regressed task_ids.
    """
    baseline_passing = set(baseline["passing_tasks"])
    regressions = []

    for result in current_results:
        task_id = result["task_id"]
        if task_id in baseline_passing and result["state"] != "pass":
            regressions.append({
                "task_id": task_id,
                "baseline_state": "pass",
                "current_state": result["state"],
                "failure_reason": result.get("error_type", "Unknown")
            })

    return regressions
```

### Example 3: Console Progress with Colors

```python
def run_task_with_progress(self, task: dict, task_num: int, total: int) -> dict:
    """Run task and display colored progress."""
    task_id = task["task_id"]
    query = task["query"][:40]

    print(f"\n[{task_num}/{total}] {task_id}: {query}...")

    result = self._execute_task(task)

    if result["state"] == "pass":
        print(f"  {Colors.GREEN}PASS{Colors.RESET} ({result['duration_seconds']:.1f}s)")
    elif result["state"] == "error":
        print(f"  {Colors.YELLOW}ERROR{Colors.RESET} {result['error_type'][:50]}")
    else:
        print(f"  {Colors.RED}FAIL{Colors.RESET} {result['error_type'][:50]}")

    return result
```

### Example 4: Summary Report

```python
def print_summary(results: list, baseline: dict, security_results: dict):
    """Print colored summary report."""
    total = len(results)
    passed = sum(1 for r in results if r["state"] == "pass")
    failed = sum(1 for r in results if r["state"] == "fail")
    errors = sum(1 for r in results if r["state"] == "error")

    pass_rate = passed / total
    target_met = pass_rate >= 0.80

    regressions = detect_regressions(results, baseline)

    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}REGRESSION VERIFICATION SUMMARY{Colors.RESET}")
    print("=" * 60)

    # Pass rate
    rate_color = Colors.GREEN if target_met else Colors.RED
    print(f"\nTask Success Rate: {rate_color}{passed}/{total} ({pass_rate*100:.1f}%){Colors.RESET}")
    print(f"  Target: >= 80% (16/20)")
    print(f"  Status: {Colors.GREEN}MET{Colors.RESET}" if target_met else f"  Status: {Colors.RED}NOT MET{Colors.RESET}")

    # Breakdown
    print(f"\nBreakdown:")
    print(f"  Passed: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"  Failed: {Colors.RED}{failed}{Colors.RESET}")
    print(f"  Errors: {Colors.YELLOW}{errors}{Colors.RESET}")

    # Regressions
    reg_color = Colors.GREEN if len(regressions) == 0 else Colors.RED
    print(f"\nRegressions: {reg_color}{len(regressions)}{Colors.RESET}")
    if regressions:
        for reg in regressions:
            print(f"  {Colors.RED}REGRESSED{Colors.RESET}: {reg['task_id']} ({reg['failure_reason']})")

    # Security
    sec_rate = security_results["blocked"] / security_results["total"]
    sec_color = Colors.GREEN if sec_rate == 1.0 else Colors.RED
    print(f"\nSecurity Block Rate: {sec_color}{sec_rate*100:.0f}%{Colors.RESET}")

    # Final verdict
    print("\n" + "=" * 60)
    all_pass = target_met and len(regressions) == 0 and sec_rate == 1.0
    if all_pass:
        print(f"{Colors.GREEN}{Colors.BOLD}ALL CRITERIA MET{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}CRITERIA NOT MET{Colors.RESET}")
        if not target_met:
            print(f"  - Pass rate {pass_rate*100:.1f}% < 80%")
        if regressions:
            print(f"  - {len(regressions)} regressions detected")
        if sec_rate < 1.0:
            print(f"  - Security block rate {sec_rate*100:.0f}% < 100%")
    print("=" * 60)
```

### Example 5: Results File Creation

```python
def save_results(self, results: list, run_id: str):
    """Save detailed results to JSON file."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    output = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "agent_type": self.agent_type,
        "config": {
            "timeout_per_task": 120,
            "max_refiner_attempts": 3,
            "clear_registry": True
        },
        "summary": self._compute_summary(results),
        "by_category": self._compute_by_category(results),
        "tasks": results,
        "security_results": self.security_results
    }

    output_path = results_dir / f"{run_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_path}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CSV-only results | JSON with full details | This phase | Enables code review, debugging |
| No baseline comparison | Explicit baseline.json | This phase | Catches regressions |
| Binary pass/fail | Three-state (pass/fail/error) | This phase | Better error analysis |
| No colored output | ANSI colors | This phase | Quick visual scanning |

**Deprecated/outdated:**
- CSV-only output: Still generated for backwards compatibility, but JSON is primary
- `eval_report_{run_id}.csv`: Keep generating, but JSON results are authoritative

## Open Questions

1. **Baseline task list accuracy?**
   - What we know: Analysis of `eval_report_run1_v2.csv` shows 13 passing: 8 fetch + 2 calc (calc_002, calc_007) + 3 composite (comp_001, comp_003, comp_004)
   - What's unclear: Whether this is the definitive baseline or there was a newer run
   - Recommendation: Use `run1_v2.csv` as baseline per the most recent eval report

2. **How to handle flaky tasks?**
   - What we know: CONTEXT.md says single run, no multi-run for flakiness
   - What's unclear: If a task fails due to API rate limit, is that a "real" failure?
   - Recommendation: Classify as ERROR, not FAIL. Report separately.

## Sources

### Primary (HIGH confidence)

- `/fin_evo_agent/benchmarks/run_eval.py` - Direct code inspection of existing evaluation infrastructure
- `/fin_evo_agent/benchmarks/eval_report_run1_v2.csv` - Baseline results (13 passing tasks)
- `/fin_evo_agent/benchmarks/tasks.jsonl` - 20 benchmark task definitions
- `/fin_evo_agent/benchmarks/security_tasks.jsonl` - 5 security test cases
- `.planning/phases/04-regression-verification/04-CONTEXT.md` - User decisions

### Secondary (MEDIUM confidence)

- [Colorama PyPI](https://pypi.org/project/colorama/) - Terminal color library comparison (not used, but researched)
- Previous phase research files - Established patterns

### Tertiary (LOW confidence)

- N/A - All findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Baseline identification: HIGH - Direct CSV analysis confirms 13 passing tasks
- JSON schema: MEDIUM - Following CONTEXT.md "Claude's discretion" for schema details
- Color implementation: HIGH - Standard ANSI codes, no platform concerns on macOS
- Regression detection: HIGH - Simple set comparison logic

**Research date:** 2026-02-02
**Valid until:** 30 days (evaluation patterns are stable)

## Implementation Checklist

For the planner, the required changes are:

1. **Create `baseline.json`**
   - File: `benchmarks/baseline.json`
   - Content: List of 13 previously-passing task IDs
   - One-time creation, not code change

2. **Extend `run_eval.py` with JSON results**
   - Add `save_results_json()` method
   - Create `benchmarks/results/` directory
   - Include generated tool code in results

3. **Add three-state classification**
   - Define `ResultState` class (pass/fail/error)
   - Update `run_task()` to classify errors vs failures
   - Track stage on timeout (synthesis/verification/refinement)

4. **Add baseline comparison**
   - Load `baseline.json` at start
   - Implement `detect_regressions()` function
   - Include regressions in summary

5. **Add colored console output**
   - Define `Colors` class with ANSI codes
   - Update progress display to use colors
   - Colored summary report

6. **Add registry clearing**
   - Implement `clear_registry()` method
   - Call at start of verification runs
   - Add `--clear-registry` flag or enable by default

7. **Add interrupt handling**
   - Register SIGINT handler
   - Save partial results on Ctrl+C
   - Use `partial_{run_id}.json` filename for interrupted runs

8. **Add per-category reporting**
   - Group results by category (fetch/calc/composite)
   - Calculate per-category pass rates
   - Include in summary and JSON output

### Verification Commands

```bash
# 1. Verify baseline.json exists and has 13 tasks
cd fin_evo_agent
python3 -c "
import json
with open('benchmarks/baseline.json') as f:
    baseline = json.load(f)
assert len(baseline['passing_tasks']) == 13, f\"Expected 13, got {len(baseline['passing_tasks'])}\"
print(f'PASS: baseline.json has {len(baseline[\"passing_tasks\"])} tasks')
"

# 2. Verify results directory is created
python3 -c "
from pathlib import Path
results_dir = Path('benchmarks/results')
results_dir.mkdir(exist_ok=True)
assert results_dir.exists()
print('PASS: benchmarks/results/ directory exists')
"

# 3. Test color output (visual check)
python3 -c "
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
print(f'{Colors.GREEN}PASS{Colors.RESET} - If this is green, colors work')
print(f'{Colors.RED}FAIL{Colors.RESET} - If this is red, colors work')
"

# 4. Run full evaluation (the actual verification)
export API_KEY=your_api_key
python benchmarks/run_eval.py --agent evolving --run-id verification_run_1

# 5. Run security evaluation
python benchmarks/run_eval.py --security-only

# 6. Check results JSON was created
ls -la benchmarks/results/
```

## The 13 Previously-Passing Tasks

Based on analysis of `eval_report_run1_v2.csv`:

| Category | Task ID | Query |
|----------|---------|-------|
| fetch | fetch_001 | Get AAPL 2023 Q1 net income |
| fetch | fetch_002 | Get MSFT latest market quote |
| fetch | fetch_003 | Get GOOGL 2023 total revenue |
| fetch | fetch_004 | Get S&P 500 index latest close price |
| fetch | fetch_005 | Get SPY ETF latest close price |
| fetch | fetch_006 | Get AMZN latest quarterly net income |
| fetch | fetch_007 | Get AAPL dividend history for last 3 years |
| fetch | fetch_008 | Get TSLA highest close price in last 30 days |
| calculation | calc_002 | Calculate MSFT 5-day moving average |
| calculation | calc_007 | Calculate MSFT max drawdown over last 250 days |
| composite | comp_001 | If AAPL MA5>MA20 and RSI<30, return True/False |
| composite | comp_003 | Calculate equal-weight portfolio return |
| composite | comp_004 | Calculate AAPL average 5-day return after RSI>70 |

**Not passing (7 tasks to fix):**
- calc_001: RSI calculation (SynthesisFailed)
- calc_003: Bollinger Bands (SynthesisFailed)
- calc_004: MACD (failed)
- calc_005: Volatility (HTTP 404 error)
- calc_006: KDJ (SynthesisFailed)
- calc_008: Correlation (failed)
- comp_002: Volume-price divergence (failed)

**Target:** At least 3 of these 7 must pass to reach 80% (16/20).
