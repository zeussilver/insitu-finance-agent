# Codebase Concerns

**Analysis Date:** 2026-02-03

## Tech Debt

**Merger Module - Unimplemented Stub:**
- Issue: `src/evolution/merger.py` is documented as "stub for Phase 1b" but file does not exist
- Files: Module missing entirely, referenced in `src/core/models.py` (BatchMergeRecord table)
- Impact: Cannot consolidate similar tools, registry bloat with duplicate tools, no tool generalization
- Fix approach: Implement batch merger with LLM-based consolidation, regression testing against consolidated tools

**Incomplete Multi-Stage Verification Rollout:**
- Issue: Verifier pipeline exists but not all code paths use it consistently
- Files: `src/core/verifier.py` (complete), `src/evolution/synthesizer.py` (uses verifier), `src/evolution/refiner.py` (may bypass stages)
- Impact: Tools may pass through refiner without full contract validation, inconsistent quality guarantees
- Fix approach: Ensure refiner also calls MultiStageVerifier.verify_all_stages() after patching

**Task Executor Symbol Extraction Brittleness:**
- Issue: Symbol extraction uses keyword exclusion list that may miss false positives
- Files: `src/core/task_executor.py` lines 67-73 (SYMBOL_EXCLUSIONS hardcoded list)
- Impact: Common words like "NET" excluded from matching, may break on edge cases like "NET" ticker
- Fix approach: Use NER model or yfinance symbol validation API instead of regex + exclusion list

**Category Inference Heuristics:**
- Issue: Task category inferred from keyword matching, not semantic analysis
- Files: `src/evolution/synthesizer.py` lines 264-275 (_infer_category method), `src/core/llm_adapter.py` lines 325-337
- Impact: Misclassification leads to wrong prompt + wrong capability rules, synthesis failures
- Fix approach: Add explicit category field to benchmark tasks, use LLM classification for user queries

**Database Migration - Manual Column Addition:**
- Issue: Schema evolution uses raw SQL ALTER TABLE instead of proper migration framework
- Files: `src/core/models.py` lines 168-198 (_migrate_tool_artifacts function)
- Impact: No rollback capability, fragile across SQLite versions, risk of data loss on migration errors
- Fix approach: Use Alembic for proper schema migrations with version tracking

## Known Bugs

**Executor Runner Code Injection Risk:**
- Symptoms: Generated runner script uses f-string interpolation of function name and paths
- Files: `src/core/executor.py` lines 245-300 (runner_code template uses eval())
- Trigger: Any function name with special characters or quotes could break sandbox
- Workaround: Static check prevents most dangerous code, but runner itself uses eval() on line 274

**Simple Fetch Fallthrough Ambiguity:**
- Symptoms: Financial queries (net income, revenue) now fall through to tool execution instead of direct handling
- Files: `src/core/task_executor.py` lines 299-302 (changed behavior)
- Trigger: Query "Get AAPL 2023 Q1 net income" returns None, expected to invoke tool
- Workaround: Works as intended after architecture overhaul, but comment indicates previous behavior was ValueError

**Verification Report JSON Serialization:**
- Symptoms: VerificationStage enum values not JSON-serializable in some contexts
- Files: `src/core/verifier.py` line 73 (final_stage.value), line 77 (stage.value)
- Trigger: Saving VerificationReport.to_dict() to ExecutionTrace.std_out fails if trace saved to JSON
- Workaround: Use .value property consistently, but some code paths may miss conversion

## Security Considerations

**Subprocess Runner Uses eval():**
- Risk: Even after AST check passes, runner.py uses eval(func_name) to get function reference
- Files: `src/core/executor.py` lines 274, 280 (eval calls in generated runner)
- Current mitigation: AST check blocks dangerous names, subprocess isolation limits blast radius
- Recommendations: Replace eval() with explicit function lookup via globals() dict traversal, add function name allowlist

**Security Violation Logging - No Alerting:**
- Risk: Security violations logged to file but no real-time alerting or circuit breaker
- Files: `src/core/executor.py` lines 80-93 (_log_security_violation), `fin_evo_agent/data/logs/security_violations.log`
- Current mitigation: Logs to stderr and file, but no monitoring integration
- Recommendations: Add webhook/email alerting for security violations, rate limiting after N violations

**LLM Mock Mode Bypasses Real Security:**
- Risk: Mock LLM responses hardcoded, may not represent real LLM attack patterns
- Files: `src/core/llm_adapter.py` lines 379-525 (_mock_generate method)
- Current mitigation: Only used when API_KEY not set (testing mode)
- Recommendations: Add adversarial LLM test cases to security_tasks.jsonl, test with real LLM

**Cache Poisoning Risk:**
- Risk: Parquet cache keys use MD5 hash without signature validation
- Files: `src/finance/data_proxy.py` lines 88-96 (_get_cache_path using MD5)
- Current mitigation: Cache directory not web-accessible, local filesystem only
- Recommendations: Add cache integrity verification (HMAC signatures), cache expiration policy

## Performance Bottlenecks

**Network Retry - Sequential Blocking:**
- Problem: Network retries use synchronous sleep, blocking entire eval runner
- Files: `src/finance/data_proxy.py` lines 40-81 (with_retry decorator), `src/core/verifier.py` lines 303-324 (integration test retry)
- Cause: time.sleep() blocks thread for exponential backoff (1-10 seconds)
- Improvement path: Use async/await pattern for concurrent task execution, or thread pool for parallel retries

**Verifier Sample Data Generation - Repeated Computation:**
- Problem: Contract test args generated fresh for every verification, same sample data used
- Files: `src/core/verifier.py` lines 352-417 (_generate_test_args method)
- Cause: Hardcoded sample price lists recreated on each call (80 lines of data)
- Improvement path: Cache sample data as module-level constants, reduce redundant list allocations

**Task Executor Data Fetch - No Batch Prefetch:**
- Problem: Each task fetches OHLCV data sequentially, even if symbol + date range identical
- Files: `src/core/task_executor.py` lines 169-208 (fetch_stock_data), `benchmarks/run_eval.py` lines 703-736 (run_all_tasks)
- Cause: No cross-task data sharing, cache helps but initial fetch still sequential
- Improvement path: Prefetch all unique (symbol, start, end) tuples before eval loop, warm cache in parallel

**Large Code Content in Database:**
- Problem: Full source code stored in both DB (code_content TEXT) and disk (file_path)
- Files: `src/core/models.py` line 63 (code_content redundant with file_path), `src/core/registry.py` (reads from both)
- Cause: "Metadata in DB, Payload on Disk" architecture not fully enforced
- Improvement path: Remove code_content column, always read from file_path, reduces DB size from 92KB growth per tool

## Fragile Areas

**LLM Response Protocol Parsing:**
- Files: `src/core/llm_adapter.py` lines 265-296 (_clean_protocol method)
- Why fragile: Regex patterns for `<think>...</think>` and ` ```python...``` ` tags
- Safe modification: Use AST parsing for code extraction instead of regex, validate thinking tags with XML parser
- Test coverage: Only manual test in __main__ block (lines 528-554), no unit tests

**Thinking Process Extraction:**
- Files: `src/core/llm_adapter.py` lines 282-283 (extract thinking), synthesizer uses it for logging
- Why fragile: Thinking tags optional, missing tags cause empty thought_trace but no error
- Safe modification: Add schema validation for LLM responses, warn if thinking tags missing
- Test coverage: No tests for missing thinking tags

**Synthesizer Schema Extraction:**
- Files: `src/evolution/synthesizer.py` lines 69-95 (extract_args_schema using regex)
- Why fragile: Simple regex for function signature, doesn't handle multi-line signatures or complex type hints
- Safe modification: Use ast.parse() to properly extract function arguments and types
- Test coverage: Comment on line 71 says "in production, use ast.parse" but not implemented

**Evaluation Runner Task Classification:**
- Files: `benchmarks/run_eval.py` lines 242-290 (_classify_result method)
- Why fragile: 48 lines of nested if/else to distinguish PASS/FAIL/ERROR from stderr strings
- Safe modification: Refactor into state machine or use explicit result codes from executor
- Test coverage: No unit tests, only tested via full eval runs

## Scaling Limits

**Single-Threaded Evaluation Runner:**
- Current capacity: ~20 tasks sequentially, 2-5 minutes total runtime (based on benchmarks/results/)
- Limit: Cannot scale beyond single process, limited by GIL and sequential execution
- Scaling path: Multiprocessing pool for parallel task execution, shared cache via file system

**SQLite Database Contention:**
- Current capacity: 92KB database handles single-user workflow
- Limit: SQLite write locks prevent concurrent tool synthesis, max ~10k tools before performance degradation
- Scaling path: Migrate to PostgreSQL for multi-user scenarios, add connection pooling

**yfinance Rate Limiting:**
- Current capacity: Retry decorator handles transient failures, cache prevents repeat fetches
- Limit: Yahoo Finance has undocumented rate limits (~2000 requests/hour/IP)
- Scaling path: Add rate limiting client-side (token bucket), rotate API endpoints, cache warming strategy

**Generated Tool File Count:**
- Current capacity: All tools in single directory `data/artifacts/generated/`
- Limit: Filesystem performance degrades with >10k files in single directory (ext4/APFS)
- Scaling path: Shard by hash prefix (e.g., `generated/a/b/calc_rsi_v0.1.0_ab123456.py`), or use content-addressed storage

## Dependencies at Risk

**yfinance - Unofficial API Dependency:**
- Risk: Relies on undocumented Yahoo Finance endpoints, subject to breaking changes
- Impact: All fetch tools break if Yahoo changes API, entire fetch category fails
- Migration plan: Abstract DataProvider interface, add alternative backends (Alpha Vantage, Polygon.io, IEX Cloud)

**Qwen3 Model Deprecation:**
- Risk: Model ID `qwen3-max-2026-01-23` may be deprecated or replaced
- Impact: LLM adapter breaks, no tool synthesis possible, falls back to mock mode
- Migration plan: Add model version config, support multiple model IDs with fallback chain

**SQLModel + SQLAlchemy Version Coupling:**
- Risk: SQLModel 0.x uses SQLAlchemy 2.x, API not stable
- Impact: Migrations break, raw SQL in _migrate_tool_artifacts may fail
- Migration plan: Pin exact versions in requirements.txt (already done), plan migration to Alembic

## Missing Critical Features

**No Refiner Integration in Synthesizer Default Path:**
- Problem: synthesize() method exists but doesn't use refiner, only synthesize_with_refine() does
- Blocks: Most direct API calls bypass error correction, lower success rate
- Priority: Medium (workaround: callers use synthesize_with_refine explicitly)

**No Tool Versioning for Breaking Changes:**
- Problem: semantic_version exists but not incremented on patches, always "0.1.0"
- Blocks: Cannot track tool evolution, no deprecation strategy, breaking changes invisible
- Priority: High (needed for Phase 1b merger, tool consolidation requires version comparison)

**No Contract Validation in Refiner:**
- Problem: Refiner patches code but doesn't re-run contract validation stage
- Blocks: Refined tools may pass self-test but violate output contracts
- Priority: High (affects correctness, refined tools may produce wrong result format)

**No Comprehensive Error Taxonomy:**
- Problem: Error types ad-hoc strings, no standardized classification
- Blocks: Cannot analyze error patterns, refiner can't specialize by error type
- Priority: Medium (needed for intelligent retry strategies, error-specific fixes)

## Test Coverage Gaps

**No Unit Tests for Core Modules:**
- What's not tested: All src/core/*.py modules have __main__ blocks but no pytest tests
- Files: `src/core/verifier.py`, `src/core/executor.py`, `src/core/task_executor.py`, `src/core/llm_adapter.py`
- Risk: Refactoring breaks functionality silently, regression detection depends on full eval runs
- Priority: High (10+ minute eval runs for testing small changes)

**No Integration Tests for Error Paths:**
- What's not tested: Network failures, LLM API timeouts, corrupt cache files
- Files: `src/finance/data_proxy.py` (retry logic), `src/core/verifier.py` (network retry in integration stage)
- Risk: Error handling untested, may crash instead of graceful degradation
- Priority: Medium (production use requires error resilience)

**Security Tasks Coverage - Only 2 Samples:**
- What's not tested: Most attack vectors (command injection, path traversal, code injection via string literals)
- Files: `fin_evo_agent/data/logs/security_violations.log` shows only 2 violations recorded
- Risk: False sense of security, real attackers may find bypasses
- Priority: High (security critical, needs 20+ adversarial test cases)

**No Contract Validation Tests:**
- What's not tested: All 17 contracts in CONTRACTS dict lack dedicated test suites
- Files: `src/core/contracts.py` defines 17 contracts but no tests for constraint validation
- Risk: Contract validation logic may have bugs, tools may pass incorrectly
- Priority: High (contract validation is core verification stage)

---

*Concerns audit: 2026-02-03*
