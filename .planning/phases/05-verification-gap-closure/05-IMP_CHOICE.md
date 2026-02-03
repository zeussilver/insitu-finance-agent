# Phase 5: Implementation Choice Analysis

**Created:** 2026-02-03

This document captures the option analysis for each implementation decision in Phase 5. Use this as reference for understanding why certain approaches were chosen.

---

## Security Blocking

### Decision 1: Blocking approach

| Option | Description | Chosen |
|--------|-------------|--------|
| Expand blocklist | Add more patterns to AST check | ✅ |
| Allowlist only | Only permit specific AST patterns | |

**Analysis:** Expand blocklist is more practical — we can target specific dangerous patterns identified in the 5 security test cases rather than restricting to a narrow allowlist.

---

### Decision 2: What patterns to block

| Option | Description | Chosen |
|--------|-------------|--------|
| File operations | Block open(), pathlib file ops | |
| All dangerous calls | File ops + compile() + type() abuse | |
| Analyze attacks first | Read 5 security test cases, identify exact bypasses | ✅ |

**Analysis:** Analyze attacks first ensures we block exactly what's bypassing, not guessing at patterns.

---

### Decision 3: Security violation handling

| Option | Description | Chosen |
|--------|-------------|--------|
| Fail immediately | Security violation = hard stop | |
| Regenerate once | Tell LLM what was blocked, ask for safe version (1 attempt) | ✅ |

**Analysis:** Regenerate once gives a chance to fix without opening infinite retry loops.

---

### Decision 4: Security logging

| Option | Description | Chosen |
|--------|-------------|--------|
| Log to file | data/logs/security_violations.log | |
| DB only | ErrorReport table | |
| Both | Log file + DB | ✅ |

**Analysis:** Both provides audit trail (file) + programmatic access (DB).

---

### Decision 5: Defense in depth

| Option | Description | Chosen |
|--------|-------------|--------|
| After only | Check generated code before execution | |
| Prompt + after | Security constraints in prompt AND check output | ✅ |

**Analysis:** Defense in depth — prompt guides LLM away from dangerous patterns, AST check catches violations.

---

### Decision 6: Prompt warning style

| Option | Description | Chosen |
|--------|-------------|--------|
| Minimal | Just list forbidden modules/calls | |
| With examples | Show what NOT to do (risky) | |
| Consequence-focused | Explain violations will be blocked + task fails | ✅ |

**Analysis:** Consequence-focused warns without teaching evasion patterns.

---

## Fetch Task Pattern

### Decision 7: How fetch tools work

| Aspect | Allow yfinance in fetch tools | Separate tool types | Wrapper approach |
|--------|------------------------------|---------------------|------------------|
| LLM complexity | Medium | High — must identify task type | ✅ Low — tools stay pure |
| Consistency | Inconsistent patterns | Two patterns | ✅ One pattern |
| Reliability | Depends on LLM | Depends on LLM | ✅ System-controlled |

**Chosen:** Wrapper approach — system fetches data, tools stay pure functions. Doesn't rely on LLM following prompts.

---

### Decision 8: Where data fetching logic lives

| Aspect | main.py | synthesizer.py | Bootstrap fetch tools |
|--------|---------|----------------|----------------------|
| Single responsibility | ❌ CLI + orchestration | ❌ Generates, shouldn't execute | ✅ Composition |
| Existing infrastructure | New logic | New logic | ✅ 5 bootstrap tools exist |
| Paper alignment | Neutral | Neutral | ✅ Tool composition is core |

**Chosen:** Bootstrap fetch tools — leverages existing infrastructure, clean architecture.

---

### Decision 9: How to chain fetch → calc

| Aspect | System chains (orchestrator) | Tool calls tool (direct import) |
|--------|------------------------------|--------------------------------|
| Tool independence | ✅ Decoupled, reusable | ❌ Tight coupling |
| Pure function pattern | ✅ Maintained | ❌ Violated |
| Security | ✅ Bootstrap trusted, generated sandboxed | ⚠️ Generated imports other code |

**Chosen:** System chains — orchestrator controls fetch → calc flow, tools stay pure.

---

### Decision 10: Where chaining logic lives

| Aspect | main.py | New module (task_executor.py) | run_eval.py |
|--------|---------|------------------------------|-------------|
| Single responsibility | ❌ CLI grows | ✅ Dedicated orchestration | ❌ Benchmark code |
| Reusability | ❌ CLI only | ✅ Importable anywhere | ❌ Tied to benchmarks |
| Code organization | ❌ main.py bloated | ✅ Follows src/core/ pattern | ❌ Wrong place |

**Chosen:** New module `src/core/task_executor.py` — clean separation, reusable.

---

### Decision 11: How to determine task type

| Option | Description | Chosen |
|--------|-------------|--------|
| Task metadata | tasks.jsonl has 'category' field | ✅ |
| LLM classifies | Ask LLM to classify | |
| Try pure first | Retry with fetch if fails | |

**Analysis:** Task metadata is efficient and doesn't rely on LLM.

---

### Decision 12: Missing bootstrap tool handling

| Aspect | Fail the task | Generate fetch tool |
|--------|---------------|---------------------|
| Security | ✅ Only trusted bootstrap calls APIs | ⚠️ LLM-generated calls APIs |
| Consistency | ✅ All fetch via bootstrap | ❌ Mixed sources |
| Maintainability | ✅ Add bootstrap tools explicitly | ❌ Generated may be inconsistent |

**Chosen:** Fail the task — gaps fixed by adding bootstrap tools, not generating risky fetch code.

---

### Decision 13: Data caching

| Option | Description | Chosen |
|--------|-------------|--------|
| No caching | Fetch fresh each time | |
| Use existing DataProvider cache | @DataProvider.reproducible already built | ✅ |

**Analysis:** Already implemented, aligns with reproducibility principle, zero extra work.

---

### Decision 14: Standardized data format

| Aspect | Minimal {symbol, prices, dates} | Full OHLCV |
|--------|--------------------------------|------------|
| Indicator coverage | ❌ Limited | ✅ All indicators |
| yfinance alignment | ❌ Needs transformation | ✅ Direct mapping |
| Future-proofing | ❌ Expand later | ✅ Covers all cases |

**Chosen:** Full OHLCV `{symbol, dates, open, high, low, close, volume}` — industry standard, maps to yfinance.

---

## Tool Matching

### Decision 15: Matching approach

| Aspect | Semantic similarity | LLM selection | Structured matching |
|--------|---------------------|---------------|---------------------|
| Dependencies | ❌ Need embedding model | ✅ Have Qwen3 | ✅ None |
| Speed | ⚠️ API call | ❌ Slow | ✅ Fast |
| Reliability | ✅ Deterministic | ⚠️ LLM varies | ✅ Deterministic |
| Cost | ⚠️ Embedding API | ❌ LLM per match | ✅ Free |

**Chosen:** Structured matching — fast, deterministic, no extra dependencies.

---

### Decision 16: Schema fields

| Aspect | Category + indicator | Full schema |
|--------|---------------------|-------------|
| Precision | ✅ Good for most | ✅ Better for edge cases |
| Future-proofing | ⚠️ May expand | ✅ Covers variations |

**Chosen:** Full schema `{category, indicator, data_type, input_requirements}` — more precise matching.

---

### Decision 17: Where to store schema

| Aspect | ToolArtifact model (DB) | Separate file | Tool docstring |
|--------|------------------------|---------------|----------------|
| Single source of truth | ✅ DB authoritative | ⚠️ Sync issues | ⚠️ Parse needed |
| Query capability | ✅ SQL queries | ❌ Load + filter | ❌ Read all files |
| Project alignment | ✅ "Metadata in DB" | ❌ Breaks pattern | ⚠️ Mixed |

**Chosen:** ToolArtifact model — follows "metadata in DB" principle, enables SQL queries.

---

### Decision 18: No match behavior

| Option | Description | Chosen |
|--------|-------------|--------|
| Generate new tool | Synthesize for this task | ✅ |
| Fail with suggestion | Suggest closest matches | |

**Analysis:** Generate new tool — synthesizer already handles this, extends tool library.

---

### Decision 19: Schema extraction

| Option | Description | Chosen |
|--------|-------------|--------|
| From task metadata | All fields from tasks.jsonl | |
| LLM extracts | LLM determines all fields | |
| Hybrid | Task provides category, LLM determines rest | ✅ |

**Analysis:** Hybrid balances reliability (category is known) with flexibility (LLM infers indicator/requirements).

---

## Testing Strategy

### Decision 20: Verification approach

| Aspect | Run full benchmark | Incremental testing | CI integration |
|--------|-------------------|---------------------|----------------|
| Regression detection | ✅ Immediate | ⚠️ Delayed | ✅ Automatic |
| Setup effort | ✅ Exists | ✅ Minimal | ⚠️ Need config |

**Chosen:** CI integration — automatic protection, industry standard.

---

### Decision 21: CI platform

| Option | Description | Chosen |
|--------|-------------|--------|
| GitHub Actions | Built into GitHub, free for public repos | ✅ |
| GitLab CI | Built into GitLab | |
| Local only | Git hooks | |

**Analysis:** GitHub Actions — integrated, well-documented, free tier sufficient.

---

### Decision 22: CI trigger

| Aspect | On every push | PR only | Manual | Hybrid |
|--------|---------------|---------|--------|--------|
| Protection | ✅ Max | ✅ Good | ⚠️ Min | ✅ Good |
| Cost | ❌ High | ⚠️ Moderate | ✅ Low | ⚠️ Moderate |
| Friction | ❌ High | ✅ Low | ✅ None | ✅ Low |

**Chosen:** Hybrid (PR + Manual) — automatic on PR, manual for ad-hoc testing.

---

### Decision 23: API key handling

| Option | Description | Chosen |
|--------|-------------|--------|
| GitHub Secrets | Store in repository secrets | ✅ |
| Mock LLM in CI | No real API calls | |
| Skip generation tests | Only test execution | |

**Analysis:** GitHub Secrets — enables full benchmark with real LLM.

---

### Decision 24: CI failure behavior

| Aspect | Fail the workflow | Warning only | Hybrid |
|--------|-------------------|--------------|--------|
| Protection | ✅ Strong | ⚠️ Weak | ✅ Balanced |
| LLM variance | ❌ Flaky failures | ✅ Tolerant | ✅ Tolerant |

**Chosen:** Hybrid — hard fail on regressions, warning on pass rate < 80%.

---

### Decision 25: CI artifacts

| Aspect | Save JSON only | Save + PR comment | No artifacts |
|--------|---------------|-------------------|--------------|
| Visibility | ⚠️ Download needed | ✅ In PR directly | ❌ None |
| Debugging | ✅ Can analyze | ✅ Same | ❌ Re-run needed |

**Chosen:** Save + PR comment — best visibility for reviewers.

---

### Decision 26: Data caching in CI

| Aspect | Cache data/cache/ | No caching |
|--------|------------------|------------|
| Reproducibility | ✅ Same data every run | ❌ May vary |
| Speed | ✅ Fast | ❌ Slow |
| Project alignment | ✅ Matches principle | ❌ Violates |

**Chosen:** Cache data/cache/ — reproducibility, speed, aligned with project principles.

---

*Phase: 05-verification-gap-closure*
*Analysis documented: 2026-02-03*
