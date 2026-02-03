# Phase 5: Verification Gap Closure - Research

**Researched:** 2026-02-03
**Domain:** Security AST analysis, task orchestration, tool matching, CI/CD
**Confidence:** MEDIUM-HIGH (verified against current codebase + official sources)

## Summary

Phase 5 addresses three root causes identified in Phase 4 verification:
1. **Security AST bypass** (4/5 security tasks passed LLM-generated dangerous code)
2. **Fetch task pattern mismatch** (pure function pattern conflicts with data retrieval needs)
3. **Keyword-based tool matching** (wrong tools selected for similar queries)

Additionally, the phase implements CI pipeline for regression protection via GitHub Actions.

The research confirms that the **current executor.py AST checker has gaps** that allow LLM-generated code to bypass security. The checker correctly blocks direct `import os` but does not catch object introspection chains (`__class__.__bases__.__subclasses__()`), indirect attribute access via `getattr()`, and encoding-based bypasses. The solution requires expanding the blocklist to cover these patterns while keeping the existing architecture.

**Primary recommendation:** Implement defense-in-depth by (1) expanding AST blocklist to catch introspection/getattr patterns, (2) adding security warnings to LLM prompts, (3) creating a task executor that chains bootstrap fetch tools with pure calc tools, and (4) replacing keyword matching with structured schema matching stored in ToolArtifact.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ast (stdlib) | Python 3.9+ | Static code analysis | Official Python module, already in use |
| SQLModel | 0.0.14+ | DB schema extension for tool metadata | Already in project, follows "metadata in DB" |
| GitHub Actions | v4/v5 | CI/CD automation | Official GitHub CI, widely adopted |
| gh CLI | 2.x | PR comments, workflow control | Pre-installed on GitHub runners |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| actions/checkout | v5 | Git checkout in CI | Every workflow |
| actions/setup-python | v5 | Python environment in CI | Python testing |
| actions/upload-artifact | v4 | Save benchmark results | After test runs |
| thollander/actions-comment-pull-request | v3 | PR comments | Post benchmark summary |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| thollander/actions-comment-pull-request | gh pr comment CLI | CLI requires manual formatting, action supports upsert via comment-tag |
| Expand blocklist | Strict allowlist only | Allowlist more secure but breaks legitimate pandas/numpy code patterns |

**Installation:**
No new dependencies needed. All use stdlib (ast) or GitHub-hosted runner pre-installed tools.

## Architecture Patterns

### Recommended Project Structure
```
fin_evo_agent/
├── src/
│   ├── core/
│   │   ├── executor.py          # MODIFY: Expand AST blocklist
│   │   ├── models.py            # MODIFY: Add schema fields to ToolArtifact
│   │   ├── task_executor.py     # NEW: Task orchestration (fetch + calc chaining)
│   │   └── ...
│   ├── evolution/
│   │   └── synthesizer.py       # MODIFY: Add security warnings to prompt
│   └── ...
├── benchmarks/
│   └── run_eval.py              # MODIFY: Use task_executor, structured matching
└── .github/
    └── workflows/
        └── benchmark.yml        # NEW: CI pipeline
```

### Pattern 1: Defense-in-Depth Security
**What:** Multiple layers of security checking (prompt warnings + AST analysis + logging)
**When to use:** Whenever executing LLM-generated code
**Example:**
```python
# Layer 1: Prompt warning (in llm_adapter.py SYSTEM_PROMPT)
"""
SECURITY REQUIREMENTS:
- NEVER use: os, sys, subprocess, eval, exec, __import__, getattr, setattr
- NEVER access: __class__, __bases__, __subclasses__, __builtins__, __dict__
- Violations will be BLOCKED and the task will FAIL
"""

# Layer 2: Expanded AST check (in executor.py)
BANNED_ATTRIBUTES = {
    '__class__', '__bases__', '__subclasses__', '__mro__',
    '__dict__', '__globals__', '__code__', '__builtins__',
    '__getattribute__', '__reduce__', '__reduce_ex__'
}

BANNED_CALLS = {
    'eval', 'exec', 'compile', '__import__',
    'globals', 'locals', 'vars', 'dir',
    'getattr', 'setattr', 'delattr', 'hasattr',
    'open',  # Block all open() calls
}

# Layer 3: Logging violations (both file and DB)
def log_security_violation(code: str, violation: str, task_id: str):
    # File log
    with open(LOGS_DIR / "security_violations.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} | {task_id} | {violation}\n")
    # DB log via ErrorReport
    error_report = ErrorReport(
        trace_id=f"sec_{uuid.uuid4().hex[:8]}",
        error_type="SecurityViolation",
        root_cause=violation
    )
```

### Pattern 2: Task Executor with Bootstrap Tool Chaining
**What:** System-level orchestration that fetches data via bootstrap tools, then passes to calc tools
**When to use:** All fetch-category and composite-category tasks
**Example:**
```python
# src/core/task_executor.py
class TaskExecutor:
    """Orchestrates task execution: fetch data -> pass to tool -> return result"""

    def __init__(self, registry: ToolRegistry, executor: ToolExecutor):
        self.registry = registry
        self.executor = executor
        self.bootstrap_tools = self._load_bootstrap_tools()

    def execute_task(self, task: dict, tool: ToolArtifact) -> ExecutionTrace:
        category = task.get("category")

        if category == "fetch":
            # Fetch tasks: bootstrap tool provides data, generated tool processes it
            data = self._fetch_data_for_task(task)
            return self._execute_with_data(tool, data, task)

        elif category == "calculation":
            # Calc tasks: need price data from bootstrap tool
            data = self._fetch_price_data(task)
            return self._execute_with_data(tool, data, task)

        elif category == "composite":
            # Composite: may need multiple data sources
            data = self._fetch_all_required_data(task)
            return self._execute_with_data(tool, data, task)

    def _fetch_data_for_task(self, task: dict) -> dict:
        """Use bootstrap tools to fetch required data."""
        symbol = self._extract_symbol(task["query"])
        # Call bootstrap get_stock_hist tool
        return {
            "symbol": symbol,
            "dates": [...],
            "open": [...],
            "high": [...],
            "low": [...],
            "close": [...],
            "volume": [...]
        }
```

### Pattern 3: Structured Schema Matching
**What:** Match tools by structured metadata fields, not keyword patterns
**When to use:** Tool retrieval/reuse decisions
**Example:**
```python
# Extended ToolArtifact schema (models.py)
class ToolArtifact(SQLModel, table=True):
    # ... existing fields ...

    # NEW: Structured matching fields
    category: Optional[str] = Field(default=None, index=True)  # "fetch", "calculation", "composite"
    indicator: Optional[str] = Field(default=None, index=True)  # "rsi", "macd", "bollinger", etc.
    data_type: Optional[str] = Field(default=None)  # "price", "financial", "volume"
    input_requirements: List[str] = Field(default=[], sa_column=Column(JSON))  # ["prices", "period"]

# Tool matching (registry.py)
def find_tool_by_schema(
    self,
    category: str = None,
    indicator: str = None,
    data_type: str = None
) -> Optional[ToolArtifact]:
    """Find tool by structured schema fields."""
    with Session(self.engine) as session:
        query = select(ToolArtifact).where(
            ToolArtifact.status == ToolStatus.PROVISIONAL
        )
        if category:
            query = query.where(ToolArtifact.category == category)
        if indicator:
            query = query.where(ToolArtifact.indicator == indicator)
        # ... additional filters
        return session.exec(query).first()
```

### Anti-Patterns to Avoid
- **String-based import blocking only:** `import os` is blocked but `__import__('os')` or `getattr(__builtins__, '__import__')('os')` bypass it
- **Keyword matching for tools:** `_infer_tool_name()` using substring matching picks wrong tools
- **Pure functions expecting API calls:** Tools that declare `def get_stock_hist(symbol)` but expect the caller to provide data somehow

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Security AST analysis | Custom regex patterns | Expand ast.walk() with proper node type handling | AST handles syntax edge cases (comments, strings) |
| GitHub PR comments | Manual API calls | `thollander/actions-comment-pull-request` action | Handles upsert, fork permissions, formatting |
| Python version matrix | Multiple workflow files | `strategy.matrix` in single workflow | DRY, maintainable |
| Artifact caching in CI | Manual upload/download | `actions/cache` with hash key | Handles invalidation, concurrent access |
| Retry with backoff for fetch | Simple sleep loop | Use existing `@DataProvider.reproducible` decorator | Already has caching built-in |

**Key insight:** The existing bootstrap tools and DataProvider decorator already solve fetch + caching. The gap is in orchestration (chaining bootstrap output to calc tools), not in data fetching itself.

## Common Pitfalls

### Pitfall 1: AST Check Position Sensitivity
**What goes wrong:** Checking `isinstance(node.func, ast.Name)` misses calls like `module.func()` or `getattr(obj, 'func')()`
**Why it happens:** ast.Call can have `func` as Name, Attribute, Subscript, or Call
**How to avoid:** Check all func types:
```python
if isinstance(node, ast.Call):
    func = node.func
    if isinstance(func, ast.Name):
        if func.id in BANNED_CALLS:
            return False, f"Banned call: {func.id}"
    elif isinstance(func, ast.Attribute):
        if func.attr in BANNED_CALLS:
            return False, f"Banned method call: {func.attr}"
```
**Warning signs:** Security tests pass code containing `getattr(...)` or `obj.banned_method()`

### Pitfall 2: Object Introspection Chains
**What goes wrong:** Code like `''.__class__.__bases__[0].__subclasses__()` bypasses import checks
**Why it happens:** These are attribute accesses, not imports
**How to avoid:** Block dunder attributes in ast.Attribute checks:
```python
BANNED_ATTRIBUTES = {
    '__class__', '__bases__', '__subclasses__', '__mro__',
    '__dict__', '__globals__', '__code__', '__builtins__',
    '__getattribute__', '__reduce__', '__reduce_ex__'
}

if isinstance(node, ast.Attribute):
    if node.attr in BANNED_ATTRIBUTES:
        return False, f"Banned attribute: {node.attr}"
```
**Warning signs:** LLM generates code with `.__class__` or `.__subclasses__()` chains

### Pitfall 3: Encoding Bypass (PEP-263)
**What goes wrong:** `# coding: utf-7` allows obfuscated code that decodes to dangerous operations
**Why it happens:** Python interpreter processes encoding declaration before AST parsing
**How to avoid:** Strip/normalize encoding declarations before parsing, or reject non-UTF-8:
```python
def normalize_encoding(code: str) -> str:
    """Remove encoding declarations, enforce UTF-8."""
    lines = code.split('\n')
    clean_lines = []
    for i, line in enumerate(lines):
        if i < 2 and line.strip().startswith('#') and 'coding' in line:
            continue  # Skip encoding declaration
        clean_lines.append(line)
    return '\n'.join(clean_lines)
```
**Warning signs:** Code starts with `# coding:` or `# -*- coding:`

### Pitfall 4: GitHub Actions Fork PR Permissions
**What goes wrong:** PR from fork has only read permission, comment action fails
**Why it happens:** `pull_request` event from forks has restricted permissions
**How to avoid:** Use `pull_request_target` for comment-only operations, or skip comments for fork PRs
**Warning signs:** "Resource not accessible by integration" error in workflow logs

### Pitfall 5: Tool Schema Extraction Timing
**What goes wrong:** Schema fields (category, indicator) not populated when tool is registered
**Why it happens:** `synthesize()` creates tool before schema extraction happens
**How to avoid:** Use hybrid extraction: task provides category, LLM/heuristics determine indicator:
```python
def register_with_schema(self, name, code, task_category, task_query):
    # Extract indicator from query using pattern matching
    indicator = self._extract_indicator(task_query)  # "rsi", "macd", etc.

    tool = self.register(name=name, code=code)
    # Update schema fields
    tool.category = task_category
    tool.indicator = indicator
    self._update_tool(tool)
```
**Warning signs:** Tools registered with null category/indicator, matching always fails

## Code Examples

Verified patterns from official sources and codebase analysis:

### Expanded AST Security Check
```python
# Source: Codebase analysis + HackTricks bypass research
class ToolExecutor:
    # Expanded blocklists based on known bypass techniques
    BANNED_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'builtins',
        'importlib', 'ctypes', 'socket', 'http', 'urllib',
        'pickle', 'shelve', 'multiprocessing', 'threading',
        'pty', 'tty', 'fcntl', 'posix', 'nt', 'msvcrt',
        'code', 'codeop', 'commands', 'popen2', 'signal'
    }

    BANNED_CALLS = {
        'eval', 'exec', 'compile', '__import__',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'open', 'file', 'input', 'raw_input',
        'execfile', 'reload', 'breakpoint',
    }

    BANNED_ATTRIBUTES = {
        '__class__', '__bases__', '__subclasses__', '__mro__',
        '__dict__', '__globals__', '__code__', '__builtins__',
        '__getattribute__', '__setattr__', '__delattr__',
        '__reduce__', '__reduce_ex__', '__getstate__', '__setstate__',
        '__init_subclass__', '__class_getitem__',
        'func_globals', 'func_code',  # Python 2 compat
    }

    def static_check(self, code: str) -> Tuple[bool, Optional[str]]:
        # Normalize encoding first
        code = self._normalize_encoding(code)

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.BANNED_MODULES:
                        return False, f"Banned import: {module}"
                    if module not in self.ALLOWED_MODULES:
                        return False, f"Unallowed import: {module}"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.BANNED_MODULES:
                        return False, f"Banned import from: {module}"
                    if module not in self.ALLOWED_MODULES:
                        return False, f"Unallowed import from: {module}"

            # Check ALL function calls (Name, Attribute, or nested)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    if func.id in self.BANNED_CALLS:
                        return False, f"Banned call: {func.id}"
                elif isinstance(func, ast.Attribute):
                    if func.attr in self.BANNED_CALLS:
                        return False, f"Banned method call: {func.attr}"

            # Check attribute access (catches __class__, __subclasses__, etc.)
            elif isinstance(node, ast.Attribute):
                if node.attr in self.BANNED_ATTRIBUTES:
                    return False, f"Banned attribute access: {node.attr}"

            # Check string literals for banned keywords (catches getattr('eval'))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for banned in self.BANNED_CALLS | self.BANNED_MODULES:
                    if banned in node.value and len(node.value) < 50:
                        return False, f"Suspicious string literal containing: {banned}"

        return True, None

    def _normalize_encoding(self, code: str) -> str:
        """Strip encoding declarations to prevent PEP-263 bypass."""
        lines = code.split('\n')
        clean = []
        for i, line in enumerate(lines):
            if i < 2 and 'coding' in line.lower() and line.strip().startswith('#'):
                continue
            clean.append(line)
        return '\n'.join(clean)
```

### GitHub Actions Workflow
```yaml
# Source: GitHub Docs - Building and testing Python
# .github/workflows/benchmark.yml
name: Benchmark Evaluation

on:
  pull_request:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        working-directory: fin_evo_agent
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Restore yfinance cache
        uses: actions/cache@v4
        with:
          path: fin_evo_agent/data/cache
          key: yfinance-cache-${{ hashFiles('fin_evo_agent/benchmarks/tasks.jsonl') }}
          restore-keys: yfinance-cache-

      - name: Initialize database
        working-directory: fin_evo_agent
        run: python main.py --init

      - name: Run benchmark
        working-directory: fin_evo_agent
        env:
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          python benchmarks/run_eval.py \
            --agent evolving \
            --run-id ci-${{ github.run_number }} \
            --clear-registry

      - name: Check for regressions
        working-directory: fin_evo_agent
        run: |
          # Parse results and check for regressions
          python -c "
          import json
          import sys
          with open('benchmarks/results/ci-${{ github.run_number }}.json') as f:
              results = json.load(f)

          regressions = results['summary'].get('regressions', [])
          pass_rate = results['summary']['pass_rate']

          if regressions:
              print(f'FAIL: {len(regressions)} regressions detected')
              for r in regressions:
                  print(f'  - {r[\"task_id\"]}: {r[\"failure_reason\"][:50]}')
              sys.exit(1)

          if pass_rate < 0.80:
              print(f'WARNING: Pass rate {pass_rate*100:.1f}% < 80% target')
              # Warning only, no hard fail for pass rate (LLM variance)

          print(f'OK: {pass_rate*100:.1f}% pass rate, no regressions')
          "

      - name: Upload results artifact
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results-${{ github.run_number }}
          path: fin_evo_agent/benchmarks/results/ci-${{ github.run_number }}.json
        if: always()

      - name: Comment on PR
        uses: thollander/actions-comment-pull-request@v3
        if: github.event_name == 'pull_request'
        with:
          comment-tag: benchmark-results
          message: |
            ## Benchmark Results

            | Metric | Value |
            |--------|-------|
            | Pass Rate | ${{ env.PASS_RATE }} |
            | Regressions | ${{ env.REGRESSION_COUNT }} |

            [Full results artifact](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})
```

### Task Executor Pattern
```python
# Source: Codebase analysis of bootstrap.py + run_eval.py
# src/core/task_executor.py

from typing import Dict, Any, Optional
from pathlib import Path

class TaskExecutor:
    """
    Orchestrates task execution by chaining bootstrap fetch tools with generated calc tools.

    Pattern: System fetches data via bootstrap tools, passes to pure function tools.
    This keeps generated tools pure (data-as-arguments) while supporting fetch tasks.
    """

    OHLCV_COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

    def __init__(self, registry, executor):
        self.registry = registry
        self.executor = executor
        self._bootstrap_cache = {}

    def get_bootstrap_tool(self, tool_name: str):
        """Get a bootstrap tool by name."""
        if tool_name not in self._bootstrap_cache:
            tool = self.registry.get_by_name(tool_name)
            if tool and 'bootstrap' in tool.file_path:
                self._bootstrap_cache[tool_name] = tool
        return self._bootstrap_cache.get(tool_name)

    def fetch_stock_data(self, symbol: str, start: str, end: str) -> Dict[str, Any]:
        """
        Fetch OHLCV data using bootstrap get_stock_hist tool.
        Returns standardized data format.
        """
        tool = self.get_bootstrap_tool('get_stock_hist')
        if not tool:
            raise ValueError("Bootstrap tool get_stock_hist not found")

        # Execute bootstrap tool to get data
        trace = self.executor.execute(
            tool.code_content,
            'get_stock_hist',
            {'symbol': symbol, 'start': start, 'end': end},
            f"fetch_{symbol}"
        )

        if trace.exit_code != 0:
            raise RuntimeError(f"Failed to fetch data: {trace.std_err}")

        # Parse DataFrame output into standardized dict
        # (In practice, the tool returns DataFrame which we convert)
        return self._parse_ohlcv_output(trace.std_out)

    def execute_calc_task(
        self,
        task: Dict,
        tool: Any,
        data: Dict[str, Any]
    ):
        """
        Execute a calculation task with pre-fetched data.
        Maps standardized OHLCV data to tool's expected arguments.
        """
        # Build args dict from data + task params
        args = {
            'prices': data.get('close', []),
            'symbol': data.get('symbol'),
            # Add OHLCV columns as separate args for tools that need them
            'high': data.get('high', []),
            'low': data.get('low', []),
            'close': data.get('close', []),
            'volume': data.get('volume', []),
            'dates': data.get('dates', []),
        }

        # Add any task-specific parameters
        args.update(self._extract_task_params(task))

        return self.executor.execute(
            tool.code_content,
            tool.name,
            args,
            task['task_id']
        )

    def _extract_task_params(self, task: Dict) -> Dict:
        """Extract parameters from task query (period, window, etc.)."""
        import re
        query = task.get('query', '')
        params = {}

        # Extract common parameters
        if match := re.search(r'(\d+)-?day', query.lower()):
            params['period'] = int(match.group(1))
        if match := re.search(r'RSI-?(\d+)', query, re.I):
            params['period'] = int(match.group(1))
        if match := re.search(r'MACD\((\d+),(\d+),(\d+)\)', query, re.I):
            params['fast_period'] = int(match.group(1))
            params['slow_period'] = int(match.group(2))
            params['signal_period'] = int(match.group(3))

        return params
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Blocklist import names only | Blocklist imports + calls + attributes | 2025+ (post-sandbox-escape CVEs) | Catches introspection chains |
| Keyword tool matching | Structured schema matching | Current phase | Eliminates wrong tool selection |
| Pure functions with no data | Orchestrator fetches, tools compute | Current phase | Enables fetch tasks |
| Manual PR testing | GitHub Actions CI | Current phase | Catches regressions automatically |

**Deprecated/outdated:**
- `getattr()` as safe function - now recognized as security risk in sandbox contexts
- String keyword matching for tool retrieval - unreliable for similar-sounding queries

## Open Questions

Things that couldn't be fully resolved:

1. **LLM Regeneration on Security Violation**
   - What we know: Decision is to regenerate once with explanation of what was blocked
   - What's unclear: Exact prompt wording for regeneration request
   - Recommendation: Include blocked pattern and ask for alternative approach

2. **Fetch Error Handling Strategy**
   - What we know: User deferred to Claude's discretion
   - Options: (a) Fail immediately with clear error, (b) Retry once with backoff
   - Recommendation: Fail immediately - bootstrap tools have caching, so retries unlikely to help

3. **Encoding Bypass Completeness**
   - What we know: UTF-7 and unicode_escape are known bypass vectors
   - What's unclear: Full list of potentially dangerous encodings
   - Recommendation: Conservative approach - strip ALL encoding declarations, enforce UTF-8

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `executor.py`, `run_eval.py`, `synthesizer.py`, `models.py`, `bootstrap.py`
- [GitHub Docs - Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) - CI workflow patterns
- [GitHub CLI Manual - gh pr comment](https://cli.github.com/manual/gh_pr_comment) - PR comment automation

### Secondary (MEDIUM confidence)
- [Two Six Technologies - Hijacking the AST](https://twosixtech.com/blog/hijacking-the-ast-to-safely-handle-untrusted-python/) - AST security patterns
- [Snyk - Code injection in Python](https://snyk.io/blog/code-injection-python-prevention-examples/) - Security best practices
- [JFrog Security Research - n8n Sandbox Escape](https://research.jfrog.com/post/achieving-remote-code-execution-on-n8n-via-sandbox-escape/) - CVE-2026 bypass techniques
- [Blacksmith - GitHub Actions Secrets Best Practices](https://www.blacksmith.sh/blog/best-practices-for-managing-secrets-in-github-actions) - CI security

### Tertiary (LOW confidence)
- WebSearch results for Python sandbox escape techniques - verified against codebase patterns
- Community discussions on HackTricks regarding `__class__.__subclasses__()` bypass

## Metadata

**Confidence breakdown:**
- Security AST expansion: HIGH - verified against known CVEs and codebase gaps
- Task executor pattern: HIGH - follows existing architecture, uses existing tools
- Structured matching: MEDIUM - schema fields straightforward, extraction heuristics need testing
- CI pipeline: HIGH - based on official GitHub documentation

**Research date:** 2026-02-03
**Valid until:** 30 days (security patterns stable, CI tooling stable)
