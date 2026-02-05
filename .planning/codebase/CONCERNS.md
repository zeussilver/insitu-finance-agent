# Codebase Concerns

**Analysis Date:** 2026-02-05

## Tech Debt

**LLM Synthesis Failures (High Priority):**
- Issue: 3 of 20 benchmark tasks fail with SynthesisFailed after 120+ second timeout
- Files: `fin_evo_agent/src/evolution/synthesizer.py`, `fin_evo_agent/benchmarks/results/post_round3_fix.json`
- Impact: 15% task failure rate (fetch_001, fetch_002, calc_007) - LLM generates non-compliant code repeatedly
- Fix approach: Implement prompt caching, add example code snippets to prompts, reduce LLM timeout to fail faster and retry with different strategies

**Bare Exception Handlers:**
- Issue: Multiple bare `except:` blocks swallow all exceptions without logging
- Files: `fin_evo_agent/src/core/gateway.py:357`, `fin_evo_agent/src/core/gateway.py:406`
- Impact: Silent failures during checkpoint operations make debugging impossible
- Fix approach: Replace with specific exception types (`except (IOError, OSError)`) and add logging

**Broad Exception Catching:**
- Issue: 20+ instances of `except Exception as e` catch all non-system exceptions
- Files: `fin_evo_agent/src/finance/data_proxy.py:80`, `fin_evo_agent/src/core/executor.py:319`, `fin_evo_agent/src/core/task_executor.py:267`
- Impact: Masks programming errors (TypeError, AttributeError) that should fail fast
- Fix approach: Catch specific exceptions for expected failure modes, let others propagate

**Hardcoded API Key in .env File:**
- Issue: API key committed in plaintext `.env` file
- Files: `fin_evo_agent/.env:3` (`API_KEY=sk-5e03ae33722843c3a9e803541c168f08`)
- Impact: Security vulnerability - API key exposed in repository
- Fix approach: Add `.env` to `.gitignore`, use environment variables or secret management, rotate exposed key

**Stub Implementation:**
- Issue: Merger module is completely unimplemented (Phase 1b requirement)
- Files: `fin_evo_agent/src/evolution/merger.py` (file does not exist)
- Impact: Cannot consolidate redundant tools, registry grows unbounded
- Fix approach: Implement semantic similarity detection and code merging logic

**Missing Tests for Evolution Modules:**
- Issue: No unit tests for Synthesizer and Refiner classes
- Files: `fin_evo_agent/src/evolution/synthesizer.py` (474 lines), `fin_evo_agent/src/evolution/refiner.py` (527 lines)
- Impact: No test coverage for critical evolution loop - refactoring risk is high
- Fix approach: Add unit tests with mocked LLM responses and verification pipeline

## Known Bugs

**Gateway Log Shows 100% Failure Rate:**
- Symptoms: All logged attempts show FAILED status in `gateway.log`
- Files: `fin_evo_agent/data/logs/gateway.log` (50/50 entries are FAILED)
- Trigger: Every `gateway.submit()` call during test runs
- Workaround: Tests still pass, suggests logging captures pre-retry failures not final state

**Network Retry Prints to stdout:**
- Symptoms: Retry messages clutter console output during evaluation
- Files: `fin_evo_agent/src/finance/data_proxy.py:84-85` (print statements in decorator)
- Trigger: Any network error during yfinance fetch
- Workaround: None - output noise interferes with benchmark results display

**Boolean String Parsing Fragility:**
- Symptoms: Task outputs like "True" (string) fail validation expecting `True` (boolean)
- Files: `fin_evo_agent/benchmarks/run_eval.py:259-264` (workaround added)
- Trigger: Composite tasks returning boolean values from LLM-generated code
- Workaround: Added Python boolean string parsing, but root cause is string-based output extraction

## Security Considerations

**Subprocess Timeout Bypass:**
- Risk: Code can spawn background processes that outlive timeout
- Files: `fin_evo_agent/src/core/executor.py:305-319`
- Current mitigation: 30-second subprocess timeout
- Recommendations: Use process groups with `os.setpgrp()` and kill entire group on timeout

**AST Security vs Runtime Security:**
- Risk: AST checks only catch static patterns - dynamic code execution patterns may bypass
- Files: `fin_evo_agent/src/core/executor.py:64-108` (ALLOWED_MODULES, BANNED_CALLS)
- Current mitigation: Static AST analysis before execution
- Recommendations: Add runtime sandboxing with restricted builtins (replace `__builtins__` dict)

**Generated Code Stored as Executable Files:**
- Risk: Generated `.py` files could be accidentally imported or executed outside sandbox
- Files: `fin_evo_agent/data/artifacts/generated/` (all generated tools)
- Current mitigation: Code loaded via AST parsing before execution
- Recommendations: Store generated code in database as text only, generate temp files on execution

**Module Allowlist Drift:**
- Risk: New dependency (e.g., urllib3) added reactively after security block
- Files: `fin_evo_agent/src/core/executor.py:64-69` (warnings, urllib3 added in Round 3)
- Current mitigation: Centralized constraints in `configs/constraints.yaml`
- Recommendations: Audit all allowed modules quarterly, document why each is needed

**No Rate Limiting on LLM Calls:**
- Risk: Infinite loop in synthesis/refinement could exhaust API quota
- Files: `fin_evo_agent/src/core/llm_adapter.py` (no rate limiting)
- Current mitigation: Max 3 refiner attempts per task
- Recommendations: Add per-hour request counter with circuit breaker

## Performance Bottlenecks

**LLM Synthesis Timeout (120s per task):**
- Problem: Slow LLM responses block benchmark evaluation
- Files: `fin_evo_agent/benchmarks/results/post_round3_fix.json` (tasks take 107-147s to fail)
- Cause: Sequential retries with full prompt context on each attempt
- Improvement path: Reduce timeout to 30s, implement prompt caching, parallelize independent tasks

**No Database Connection Pooling:**
- Problem: Each operation opens new SQLite connection
- Files: `fin_evo_agent/src/core/registry.py:40` (creates engine per method call)
- Cause: SQLModel defaults without pool configuration
- Improvement path: Configure SQLAlchemy pool with max connections and overflow

**Subprocess Launch Overhead:**
- Problem: Every tool execution spawns new Python process
- Files: `fin_evo_agent/src/core/executor.py:305-319` (subprocess.run per execution)
- Cause: Security isolation requires subprocess
- Improvement path: Reuse worker processes with multiprocessing.Pool for batch execution

**Gateway Creates Checkpoint on Every Submit:**
- Problem: Disk I/O bottleneck when registering multiple tools
- Files: `fin_evo_agent/src/core/gateway.py`, `fin_evo_agent/data/checkpoints/` (26 files from test runs)
- Cause: Checkpoint created before verification even if likely to fail
- Improvement path: Only create checkpoint after AST security passes (skip for certain failures)

## Fragile Areas

**TaskExecutor Pattern Matching (672 lines):**
- Files: `fin_evo_agent/src/core/task_executor.py`
- Why fragile: Regex-based query parsing with 25+ hardcoded patterns - brittle to query variations
- Safe modification: Add new patterns at end of lists (order matters), test with fuzzy query variations
- Test coverage: No unit tests for pattern matching logic

**LLM Adapter Prompt Engineering (665 lines):**
- Files: `fin_evo_agent/src/core/llm_adapter.py`
- Why fragile: 3 large prompt templates (100+ lines each) - small changes break contract adherence
- Safe modification: Version prompts with timestamps, A/B test changes on subset of tasks
- Test coverage: No prompt regression tests

**Verifier Contract Validation (652 lines):**
- Files: `fin_evo_agent/src/core/verifier.py`
- Why fragile: Complex constraint checking with edge cases (empty DataFrames, None values, NaN)
- Safe modification: Add defensive checks for new constraint types, run full benchmark before merging
- Test coverage: Gateway tests cover happy path only

**Symbol Extraction with Exclusions:**
- Files: `fin_evo_agent/src/core/task_executor.py:66-88` (SYMBOL_EXCLUSIONS set)
- Why fragile: 40+ English words hardcoded to prevent false ticker matches
- Safe modification: Use NLP library for part-of-speech tagging instead of exclusion list
- Test coverage: No tests for edge cases (e.g., "NOW" stock ticker vs "NOW" word)

## Scaling Limits

**SQLite Write Contention:**
- Current capacity: Single writer, sequential tool registration
- Limit: ~100 concurrent evaluation runs would cause lock timeouts
- Scaling path: Migrate to PostgreSQL for concurrent writes, or use tool registration queue

**Checkpoint Directory Growth:**
- Current capacity: 26 checkpoints from test runs = ~10KB
- Limit: 100K tool registrations = ~4GB checkpoint data
- Scaling path: Implement checkpoint rotation (keep last N), compress with gzip

**Generated Artifact Storage:**
- Current capacity: 5 bootstrap tools only
- Limit: 10K evolved tools × 10KB average = 100MB code storage
- Scaling path: Implement tool deduplication and compression, archive deprecated tools

**Cache Directory Size:**
- Current capacity: 240KB for cached yfinance data
- Limit: 1 year of daily data for 100 symbols = ~50MB
- Scaling path: Implement cache eviction policy (LRU), set max cache size

## Dependencies at Risk

**yfinance>=0.2.30:**
- Risk: Frequent breaking changes in yfinance API (e.g., 0.2.x → 0.3.x changed column names)
- Impact: All fetch tools break, need regeneration
- Migration plan: Pin exact version (not >=), test upgrades in isolated environment

**SQLModel==0.0.14:**
- Risk: Version 0.0.x indicates pre-stable API (no semantic versioning guarantees)
- Impact: Schema migrations may break on minor updates
- Migration plan: Prepare SQLAlchemy-based migration scripts, test on copy of DB

**openai>=1.0.0:**
- Risk: OpenAI SDK changes could break Qwen3 compatibility layer
- Impact: LLM adapter fails, entire system unusable
- Migration plan: Fork SDK for stability, or use direct HTTP client

## Missing Critical Features

**No Rollback Mechanism:**
- Problem: Checkpoints created but never used for recovery
- Blocks: Cannot undo bad tool registrations or revert to known-good state
- Priority: Medium

**No Tool Versioning Beyond Semantic Version:**
- Problem: Cannot track tool lineage or compare versions
- Blocks: Cannot analyze which refinement attempts improved performance
- Priority: Low

**No Observability Dashboard:**
- Problem: Must manually parse logs and JSON files to understand system state
- Blocks: Cannot monitor production system health in real-time
- Priority: Medium

**No Distributed Execution:**
- Problem: Single-threaded task execution
- Blocks: Cannot parallelize benchmark evaluation or production workloads
- Priority: Low

## Test Coverage Gaps

**TaskExecutor Query Parsing:**
- What's not tested: Pattern matching for 25+ query patterns
- Files: `fin_evo_agent/src/core/task_executor.py:23-57`
- Risk: Query variations silently fall through to wrong tool
- Priority: High

**LLM Adapter Prompt Variants:**
- What's not tested: Prompt variations across categories (fetch/calc/composite)
- Files: `fin_evo_agent/src/core/llm_adapter.py:18-250`
- Risk: Prompt changes break specific task types
- Priority: High

**Gateway Rollback Logic:**
- What's not tested: Checkpoint restoration after failed registration
- Files: `fin_evo_agent/src/core/gateway.py:358-407`
- Risk: Rollback fails silently, registry becomes inconsistent
- Priority: High

**Refiner Error Pattern Matching:**
- What's not tested: Error pattern extraction and fix strategy selection
- Files: `fin_evo_agent/src/evolution/refiner.py:88-115`
- Risk: Certain error types enter infinite refinement loop
- Priority: Medium

**Contract Constraint Edge Cases:**
- What's not tested: NaN values, empty DataFrames, infinity in numeric outputs
- Files: `fin_evo_agent/src/core/contracts.py:241-290`
- Risk: Edge case outputs incorrectly pass/fail validation
- Priority: Medium

**Network Retry Exhaustion:**
- What's not tested: Behavior after all retry attempts fail
- Files: `fin_evo_agent/src/finance/data_proxy.py:60-95`
- Risk: Unclear whether exception propagates or returns None
- Priority: Low

---

*Concerns audit: 2026-02-05*
