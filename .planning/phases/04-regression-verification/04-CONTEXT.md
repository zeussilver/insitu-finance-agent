# Phase 4: Regression Verification - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Run the full evaluation suite to confirm all fixes work together: achieve >=80% task success rate (16/20), maintain 0 regressions on the 13 previously-passing tasks, and verify 100% security block rate. This is a verification phase, not a fix phase.

</domain>

<decisions>
## Implementation Decisions

### Test execution
- Run full 20-task benchmark (not subset)
- Single run (no multi-run for flakiness)
- Security tests run separately via `--security-only` flag
- Clear tool registry before running (fresh start, test generation not reuse)
- 120 seconds timeout per task
- Real API key required (no mock LLM fallback)
- Log LLM thinking traces only on failure (to data/logs/)
- Run tasks sequentially (not parallel)

### Results reporting
- Console shows progress + summary (task names as they run, summary at end)
- Save detailed results to JSON file: `benchmarks/results/{run-id}.json`
- Summary lists both passed and failed tasks with failure reasons
- Compare against baseline: show regressions (tasks that used to pass but now fail)
- Include generated tool code in JSON results
- Track timing information (per-task duration, total time)
- Categorize results by task type (fetch/calc/composite) with per-category pass rate
- Use colors in console output (green=pass, red=fail)

### Failure handling
- Continue running all 20 tasks regardless of failures (no early stop)
- No automatic retry on failure (single attempt per task)
- API errors (rate limits, network) marked separately from logic failures
- If 80% target missed, report results and let user decide next steps
- Security block rate tracked as separate metric (not part of 80%)
- Track which tasks exhausted refiner attempts (max 3)
- Timeout errors include which stage (synthesis/verification/refinement)
- On Ctrl+C, save partial results before exiting

### Success criteria
- 80% (16/20) is a hard requirement
- 0 regressions (13 previously-passing must still pass) is a hard requirement
- 100% security block rate is a hard requirement
- On success: print summary and exit, user decides next steps

### Claude's Discretion
- Exact JSON result schema structure
- Console progress format details
- Color scheme selection
- Partial results filename on interrupt

</decisions>

<specifics>
## Specific Ideas

- Distinguish three result states: pass, fail (logic), error (API/timeout)
- Track refiner exhaustion separately for debugging tool generation issues
- Include stage information in timeout errors for pinpointing bottlenecks

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-regression-verification*
*Context gathered: 2026-02-02*
