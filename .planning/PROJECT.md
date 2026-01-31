# Yunjue Agent — Benchmark Fix Sprint

## What This Is

A targeted fix sprint on the Yunjue Agent (self-evolving financial agent system) to push benchmark task success rate from 65% to >=80%. The system already has a working tool evolution loop (synthesize -> verify -> register -> refine), but 7 of 20 benchmark tasks fail due to 4 identifiable root causes in the synthesizer prompt, refiner pipeline, LLM fallback, and generated tool data patterns.

## Core Value

The benchmark must pass at >=80% task success rate — meaning the tool evolution loop reliably produces working financial tools from natural language task descriptions.

## Requirements

### Validated

- ✓ Tool synthesis loop (LLM -> AST check -> sandbox verify -> register) — existing
- ✓ Tool refinement loop (error analysis -> patch -> re-verify, max 3 attempts) — existing
- ✓ AST security model (banned modules/calls/attributes) — existing
- ✓ Subprocess sandboxing with 30s timeout — existing
- ✓ Tool registry with metadata in SQLite, code on disk — existing
- ✓ AkShare data caching via Parquet snapshots — existing
- ✓ Benchmark evaluation suite (20 tasks, 3 categories) — existing
- ✓ Bootstrap tools (5 AkShare wrappers) — existing
- ✓ Fetch tasks pass 100% (8/8) — existing
- ✓ Tool reuse rate >=30% (currently 58.8%) — existing

### Active

- [ ] Remove `talib` from allowed modules and SYSTEM_PROMPT; guide LLM to use pandas/numpy only
- [ ] Fix refiner root cause extraction: return `text_response` from `generate_tool_code`, add missing error patterns (ModuleNotFoundError, ImportError, AssertionError)
- [ ] Fix mock LLM fallback: return failure on timeout instead of hardcoded RSI code
- [ ] Fix generated tool data patterns: guide LLM to accept data as function args instead of fetching internally via yfinance

### Out of Scope

- Batch merger (Phase 1b stub) — not needed for 80% target
- Installing TA-Lib C library — removed from allowlist instead
- Fixing #4 (missing error patterns) as separate item — partially covered by refiner extraction fix
- New benchmark tasks or categories — fix existing failures first
- UI or API layer — CLI-only system

## Context

- Benchmark run `run1_v2` shows 65% success (13/20), target is >=80% (16/20)
- All 8 fetch tasks pass; failures are concentrated in calculation (5/8 fail) and composite (2/4 fail)
- Specific failed tasks: calc_001 (RSI/talib), calc_003 (Bollinger/talib), calc_004 (MACD/timeout->mock), calc_005 (volatility/HTTP 404), calc_006 (KDJ/talib), calc_008 (correlation/None), comp_002 (volume-price divergence/wrong return type)
- LLM is Qwen3-Max via DashScope API with 60s timeout
- Refiner's `_classify_error` returns "UnknownError" for ModuleNotFoundError because it's not in ERROR_PATTERNS
- `generate_tool_code` returns {thought_trace, code_payload, raw_response} but refiner expects `text_response` key

## Constraints

- **Tech stack**: Python 3.9+, SQLModel, Qwen3-Max API — no changes
- **Security**: Must maintain AST blocklist and sandbox isolation
- **Compatibility**: Fixes must not break the 13 currently-passing tasks
- **Dependencies**: No new Python packages (removing talib, not adding)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Remove talib instead of installing | Avoids C dependency complexity; pandas/numpy sufficient for indicators | — Pending |
| Fix top 4 root causes, skip #4 | #4 (missing error patterns) is partially covered by #2 (refiner extraction fix) | — Pending |
| Keep mock LLM but make it fail on timeout | Mock is useful for testing without API key, but shouldn't silently produce wrong tools | — Pending |

---
*Last updated: 2026-01-31 after initialization*
