# Codebase Concerns

**Analysis Date:** 2026-02-06

## Tech Debt

**Contract Information Loss in LLM Generation**
- Issue: Contract requirements (output types, constraints) are not passed to LLM during tool code generation, causing LLM to generate wrong output types (e.g., DataFrame when numeric expected)
- Files: `fin_evo_agent/src/core/llm_adapter.py:321-455`, `fin_evo_agent/src/evolution/synthesizer.py:155`
- Impact: 15% failure rate (3/20 tasks) from CONTRACT_VALID stage failures; LLM generates code returning DataFrame/dict when contract expects single numeric value
- Fix approach: Add `contract` parameter to `generate_tool_code()` and inject contract requirements into LLM user prompt (lines documented in `problem_analyse.md:192-232`)

**Contract-Blind Refiner Loop**
- Issue: Refiner's `generate_patch()` method doesn't receive contract information, so it cannot guide LLM to fix output type mismatches
- Files: `fin_evo_agent/src/evolution/refiner.py:220-282`
- Impact: Refiner exhausts max attempts (2-3) without fixing root cause; LLM "fixes" by changing test assertions instead of fixing return type
- Fix approach: Add `contract` parameter to `generate_patch()` and inject contract requirements into refinement prompt (lines documented in `problem_analyse.md:234-309`)

**Missing Contract-Aware Self-Tests**
- Issue: Generated self-tests use arbitrary assertions (e.g., `assert ni_aapl > 0`) that don't validate contract requirements like output type
- Files: Generated code in `fin_evo_agent/data/artifacts/generated/*.py`, system prompts in `fin_evo_agent/src/core/llm_adapter.py:24-229`
- Impact: Tools pass SELF_TEST stage but fail CONTRACT_VALID stage; smoke tests don't catch type mismatches
- Fix approach: Add contract-specific test guidance to system prompts (e.g., "For NUMERIC outputs: assert isinstance(result, float)")

**Stub Implementation: Batch Merger**
- Issue: `fin_evo_agent/src/evolution/merger.py` is a stub placeholder (Phase 1b feature deferred)
- Files: `fin_evo_agent/src/evolution/merger.py`
- Impact: Cannot consolidate similar tools into optimized versions; tool library grows without deduplication
- Fix approach: Implement semantic similarity detection + LLM-guided merging (per Yunjue paper Section 3.4)

## Known Bugs

**API Connection Timeouts in CI/Local Divergence**
- Symptoms: Local benchmarks achieve 85% (17/20) pass rate, but CI shows 35% (7/20) with 12 TaskTimeout errors
- Files: `fin_evo_agent/benchmarks/results/post_contract_fix2.json` (CI), `fin_evo_agent/benchmarks/results/post_round3_fix.json` (local)
- Trigger: DashScope API connection errors in CI environment; timeout_per_task_sec=300 not sufficient for LLM thinking mode with retries
- Workaround: Increase CI timeout to 120 minutes (`.github/workflows/benchmark.yml:38`), set LLM_TIMEOUT=90 env var

**SELF_TEST Failures from urllib3 Warning**
- Symptoms: Self-tests fail with truncated error message containing urllib3 OpenSSL warning; actual test logic never runs
- Files: `fin_evo_agent/data/logs/gateway_attempts.jsonl:28,36,44,48` show repeated pattern
- Trigger: urllib3 v2 emits NotOpenSSLWarning when compiled with LibreSSL; warning text truncated in error message at 100 chars
- Workaround: Allow `warnings` module in fetch tools (already fixed in `fin_evo_agent/configs/constraints.yaml:42`)

**Security Check Blocking Reflection Calls**
- Symptoms: LLM-generated code uses `getattr`, `hasattr` for dynamic attribute access; AST security check blocks these as banned calls
- Files: `fin_evo_agent/data/logs/gateway_attempts.jsonl:6,12,38`, `fin_evo_agent/src/core/executor.py:51-57`
- Trigger: LLM generates code like `getattr(ticker, 'info', {})` for defensive programming; banned_calls set includes getattr/hasattr
- Workaround: None currently; refiner cannot fix AST_SECURITY failures (unfixable error class)

## Security Considerations

**Evolution Gate Default Mode: Dev (Permissive)**
- Risk: Evolution gates run in `dev` mode which auto-approves APPROVAL-tier actions without human review
- Files: `fin_evo_agent/configs/constraints.yaml:144`, `fin_evo_agent/src/core/gates.py:239`
- Current mitigation: Warning logged to console when auto-approving APPROVAL actions
- Recommendations: Switch to `prod` mode before production deployment; implement webhook notification for APPROVAL-tier requests

**Capability-Based Security Depends on LLM Compliance**
- Risk: Security model assumes LLM will not intentionally generate malicious code; AST analysis blocks after generation
- Files: `fin_evo_agent/src/core/executor.py:93-183`, `fin_evo_agent/configs/constraints.yaml:66-136`
- Current mitigation: Multi-layer defense: (1) LLM system prompts forbid banned modules, (2) AST static analysis blocks violations, (3) subprocess sandbox isolates execution
- Recommendations: Add input validation for task queries (reject queries containing "os.system", "subprocess", etc.)

**Subprocess Execution Uses Temp Files**
- Risk: Generated code executed via subprocess with tempfile.NamedTemporaryFile; potential race condition if attacker can predict temp file path
- Files: `fin_evo_agent/src/core/executor.py:234-293`
- Current mitigation: Python's tempfile uses secure random naming; 30-second timeout limits exposure window
- Recommendations: Use `delete=True` parameter (already implemented); consider switching to in-memory execution via RestrictedPython

## Performance Bottlenecks

**Sequential LLM Calls in Refiner Loop**
- Problem: Refiner makes up to 2-3 sequential LLM calls per failed tool (analyze_error removed in recent optimization, but patch generation still synchronous)
- Files: `fin_evo_agent/src/evolution/refiner.py:284-432`
- Cause: Each refinement attempt waits for LLM response (2-10 seconds per call) before next attempt
- Improvement path: Batch multiple refinement attempts into single LLM call with ranked alternatives; parallel execution if using multiple fallback LLMs

**Contract Validation Re-Executes Code**
- Problem: Multi-stage verifier executes tool code twice: once for SELF_TEST, again for CONTRACT_VALID with same test data
- Files: `fin_evo_agent/src/core/verifier.py:122-150`
- Cause: Stages are independent; output from SELF_TEST not cached for CONTRACT_VALID reuse
- Improvement path: Cache execution result from SELF_TEST stage and reuse for contract validation

**yfinance Network Calls Without Circuit Breaker**
- Problem: Bootstrap tools make yfinance API calls with retry (3 attempts, exponential backoff) but no circuit breaker
- Files: `fin_evo_agent/src/finance/data_proxy.py:71-95`, retry decorator at lines 46-68
- Cause: If yfinance API is down, every tool waits for 1+2+4=7 seconds before failing
- Improvement path: Implement circuit breaker pattern (after N consecutive failures, skip retries for X seconds)

## Fragile Areas

**Symbol Extraction from Natural Language Queries**
- Files: `fin_evo_agent/src/core/task_executor.py:123-169`
- Why fragile: Heuristic-based extraction using regex + exclusion lists; ambiguous queries like "NET profit" could extract "NET" as symbol
- Safe modification: Add new symbols to US_TICKERS (line 117) or INDEX_SYMBOL_MAPPING (line 76); do NOT modify SYMBOL_EXCLUSIONS without testing
- Test coverage: No unit tests for extract_symbol(); failures only caught in integration tests

**Multi-Stage Verifier Stage Dependencies**
- Files: `fin_evo_agent/src/core/verifier.py:97-167`
- Why fragile: Verification stages run sequentially with early termination; adding new stage requires careful ordering
- Safe modification: New stages must be inserted at correct position (e.g., security must run before execution); update VerificationStage enum values carefully
- Test coverage: Unit tests in `tests/core/test_verifier.py` cover happy path; edge cases (skip logic) not fully tested

**Contract Inference from Query Text**
- Files: `fin_evo_agent/src/core/contracts.py:233-296`
- Why fragile: Keyword matching on query text (e.g., "RSI" → calc_rsi contract); ambiguous queries may infer wrong contract
- Safe modification: Add new keywords to existing contract patterns; avoid overlapping keywords between contracts
- Test coverage: Golden test coverage in `tests/extraction/test_schema.py`; 95% accuracy gate enforced

## Scaling Limits

**SQLite Database Concurrent Writes**
- Current capacity: Single-writer model; SQLite handles ~1000 writes/sec but blocks on concurrent writes
- Limit: Multi-process tool synthesis would hit write lock contention
- Scaling path: Migrate to PostgreSQL for concurrent tool registration; or implement write queue with background worker

**Tool Registry Linear Search by Name**
- Current capacity: Registry queries use `SELECT * FROM tool_artifacts WHERE name = ?` without index on name field
- Limit: With 1000+ tools, lookup becomes O(n); currently ~10 tools so negligible
- Scaling path: Add database index on (name, status) columns; or implement in-memory LRU cache for hot tools

**LLM API Rate Limits**
- Current capacity: DashScope Qwen3-max has rate limits (exact limits not documented in codebase)
- Limit: Benchmark run generates 20-60 LLM calls (1 per task, 2-3 refinements); hitting rate limit causes cascading failures
- Scaling path: Implement exponential backoff on 429 errors; distribute across multiple API keys; or add local LLM fallback

## Dependencies at Risk

**yfinance Unofficial Library**
- Risk: yfinance is community-maintained, not official Yahoo API; breaking changes or deprecation possible
- Impact: All fetch tools and bootstrap tools depend on yfinance; breakage would fail 40% of tasks (8/20 fetch tasks)
- Migration plan: Abstract data source behind DataProvider protocol (already implemented in `fin_evo_agent/src/data/interfaces.py`); swap to Alpha Vantage or Polygon.io adapters

**OpenAI Client for DashScope API**
- Risk: Using OpenAI Python client for DashScope OpenAI-compatible endpoint; API compatibility not guaranteed
- Impact: LLM calls would fail completely; system falls back to mock LLM (returns placeholder code)
- Migration plan: Switch to DashScope native SDK; or implement LLM adapter abstraction with multiple backends

**Python 3.9 Compatibility**
- Risk: Codebase uses Python 3.9 features (dict merge `|`, type hints); some dependencies require >=3.10
- Impact: CI uses Python 3.11 (`.github/workflows/benchmark.yml:47`); local dev may use 3.9; version skew possible
- Migration plan: Pin minimum Python version to 3.10 in `requirements.txt`; update CI matrix to test 3.10-3.12

## Missing Critical Features

**No Rollback Mechanism for Failed Registrations**
- Problem: VerificationGateway creates checkpoints but doesn't expose rollback UI/API
- Blocks: Cannot recover from bad tool registrations; database grows with failed attempts (12% failure rate)
- Priority: Medium - manual SQLite query can delete failed tools

**No Tool Versioning or Deprecation**
- Problem: Tools use semantic versioning (v0.1.0) but no upgrade/deprecation mechanism
- Blocks: Cannot mark old tool versions as obsolete; registry accumulates duplicate tools with different versions
- Priority: Low - Phase 1 focuses on generation, not maintenance

**No Human-in-the-Loop for APPROVAL Gate**
- Problem: APPROVAL-tier actions (persist to library, modify rules) should require human approval but currently auto-approved in dev mode
- Blocks: Cannot safely enable tool library persistence without risk of polluting shared library
- Priority: High - required for production deployment

## Test Coverage Gaps

**Integration Test Coverage: 0%**
- What's not tested: End-to-end task execution flow (synthesizer → gateway → verifier → executor → refiner)
- Files: No integration tests exist; only unit tests in `tests/core/`, `tests/evolution/`
- Risk: Regressions in multi-component interactions not caught until benchmark run (expensive)
- Priority: High - add smoke test that runs one fetch task + one calc task

**Error Path Coverage: ~30%**
- What's not tested: Refiner error classification edge cases (lines 111-177 in `refiner.py`); contract validation with missing/malformed output
- Files: `tests/evolution/test_refiner.py` only tests happy path; `tests/core/test_gateway.py` missing error scenarios
- Risk: Uncaught exceptions in error handling paths could crash synthesizer loop
- Priority: Medium - add negative test cases for each error type

**Security Violation Handling: Partial Coverage**
- What's not tested: AST security check with nested banned calls (e.g., `lambda: eval()`); attribute access chains (e.g., `obj.__class__.__bases__`)
- Files: `tests/core/test_executor.py` has basic security tests; advanced evasion techniques not tested
- Risk: Sophisticated LLM-generated exploits might bypass AST analysis
- Priority: Low - current coverage blocks obvious violations; advanced evasion unlikely from unmalicious LLM

---

*Concerns audit: 2026-02-06*
