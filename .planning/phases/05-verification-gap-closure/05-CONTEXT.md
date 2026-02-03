# Phase 5: Verification Gap Closure - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three root causes identified in Phase 4 verification to achieve 80% pass rate:
1. Security AST check not blocking LLM-generated dangerous code (4/5 bypass)
2. Pure function pattern conflicts with fetch tasks that need yfinance data
3. Keyword-based tool matching selects wrong tools for similar-sounding tasks

Plus: Add CI pipeline for regression protection.

</domain>

<decisions>
## Implementation Decisions

### Security Blocking
- Expand blocklist approach (not strict allowlist)
- Analyze the 5 security test cases first to identify exactly what bypasses current check
- If security violation detected: regenerate once (tell LLM what was blocked, ask for safe version)
- Log violations to both file (`data/logs/security_violations.log`) AND database (ErrorReport table)
- Defense in depth: add security constraints to prompt AND check output
- Prompt warnings should be consequence-focused (explain violations will be blocked + task will fail)
- Environment variable access is allowed (no secrets in sandbox)
- Keep pathlib in allowed modules

### Fetch Task Pattern
- Wrapper approach: system fetches data, tools stay pure functions
- Use existing bootstrap yfinance tools for data fetching
- LLM decides which bootstrap tool to use for each fetch task
- Validate first: check if bootstrap tool output matches what calc tool expects
- System chains: orchestrator calls bootstrap tool → passes data → calls generated tool
- New module `src/core/task_executor.py` for chaining logic
- Task metadata (category field in tasks.jsonl) determines if task needs fetch + calc vs just calc
- If no bootstrap tool matches: fail the task with clear error (don't generate fetch tools)
- Use existing `@DataProvider.reproducible` cache (already built)
- Standardized data format: Full OHLCV `{symbol, dates, open, high, low, close, volume}`

### Tool Matching
- Structured matching on schema fields (not keyword matching, not semantic similarity)
- Full schema: `category`, `indicator`, `data_type`, `input_requirements`
- Schema fields stored in ToolArtifact model (SQLModel DB) — follows "metadata in DB" principle
- If no tool matches structured query: generate new tool via synthesizer
- Hybrid schema extraction: task provides category, LLM determines indicator and requirements

### Testing Strategy
- CI integration via GitHub Actions
- Trigger: Hybrid (PR to main + manual workflow_dispatch)
- API key via GitHub Secrets (repository secret `API_KEY`)
- CI failure behavior:
  - Hard fail on regressions (baseline tasks that were passing now fail)
  - Warning on pass rate < 80% without regressions (accounts for LLM variance)
- Save benchmark results as JSON artifacts + post summary as PR comment
- Cache `data/cache/` (yfinance Parquet snapshots) for reproducibility and speed

### Claude's Discretion
- Fetch error handling (retry with backoff vs fail immediately)
- Specific dangerous patterns to add to AST blocklist (after analyzing security test cases)
- Exact format of PR comment summary

</decisions>

<specifics>
## Specific Ideas

- User wants step-by-step CI setup instructions included in the plan
- Full OHLCV format matches yfinance DataFrame columns directly — no transformation needed
- Task executor should be importable by both main.py and run_eval.py

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-verification-gap-closure*
*Context gathered: 2026-02-03*
