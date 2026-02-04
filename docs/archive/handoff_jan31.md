> ⚠️ **ARCHIVED - NOT MAINTAINED**
> This document reflects the pre-yfinance implementation (akshare-based).
> For current documentation, see [CLAUDE.md](../../CLAUDE.md).
> Archived on: 2026-02-04

---

# Work Handoff — Yunjue Agent (fin_evo_agent)

**Last updated:** 2026-01-31
**Status:** In progress — akshare→yfinance migration mostly done, eval suite needs final run

---

## What Was Done This Session

### 1. Data Source Migration (akshare → yfinance) — COMPLETE
All source code under `src/` fully migrated:

| File | Change |
|------|--------|
| `src/finance/data_proxy.py` | Rewritten for yfinance (already done before this session) |
| `src/finance/bootstrap.py` | Rewritten for yfinance (already done before this session) |
| `src/core/executor.py` | `yfinance` in ALLOWED_MODULES (was done), **NEW: added `inspect.signature` arg filtering to runner** |
| `src/core/llm_adapter.py` | System prompt references yfinance (was done) |
| `src/core/models.py` | Updated NETWORK_READ comment from AkShare to yfinance |
| `main.py` | **FIXED:** import `get_stock_hist` (was broken: `get_a_share_hist`), updated to AAPL + English columns |
| `benchmarks/run_eval.py` | **FIXED:** import, sample data, tool name inference, arg mapping, result judging |
| `benchmarks/tasks.jsonl` | **REWRITTEN:** All 20 tasks converted from Chinese A-share codes to US tickers (AAPL, MSFT, etc.) |
| `requirements.txt` | Already had yfinance (was done before) |

### 2. Stale Artifacts Cleaned
- Removed all old akshare bootstrap files from `data/artifacts/bootstrap/`
- Removed all old akshare generated files from `data/artifacts/generated/`
- Deleted old database, re-initialized fresh
- Cleared old Parquet cache
- Re-registered 5 new yfinance bootstrap tools

### 3. Python/SSL Compatibility — NO ISSUE
- System Python: 3.9.6 + LibreSSL 2.8.3 (problematic)
- **Venv Python: 3.13.11 + OpenSSL 3.0.18** (no issues)
- yfinance 1.1.0 installed in venv

### 4. Bug Fix: Synthesizer Function Name Mismatch
- **Problem:** `synthesizer.py` used `tool_name` hint to override the actual function name from LLM-generated code, causing executor to fail with "Function not found"
- **Fix:** Changed `func_name = tool_name or extract_function_name(code)` → `func_name = extract_function_name(code) or tool_name`
- **Also:** Added function name hint in LLM prompt when `tool_name` is provided

### 5. Bug Fix: Executor Argument Filtering
- **Problem:** Hardcoded args in main.py/run_eval.py didn't match LLM-generated function signatures (`period` vs `window`, etc.)
- **Fix:** Updated executor runner to use `inspect.signature()` to filter args to only those the function accepts

### 6. Evaluation Improvements
- `run_eval.py`: Comprehensive arg dict (passes all possible args, executor filters)
- `run_eval.py`: More lenient judging — extracts numbers from Series/DataFrame output, checks required keys in string output

---

## What Remains

### Must Do: Run Clean Evaluation
The evaluation was started (`run1_v2`) but interrupted. Need to:

1. **Clean generated tools** (some stale from interrupted run1):
   ```bash
   sqlite3 data/db/evolution.db "DELETE FROM tool_artifacts WHERE id > 5"
   rm -f data/artifacts/generated/*.py
   ```

2. **Run fresh eval**:
   ```bash
   source .venv/bin/activate
   python benchmarks/run_eval.py --agent evolving --run-id run1_final
   ```

3. **Run second eval** (test tool reuse):
   ```bash
   python benchmarks/run_eval.py --agent evolving --run-id run2_final
   ```

4. **Compare runs**:
   ```bash
   python benchmarks/compare_runs.py run1_final run2_final
   ```

5. **Run security eval**:
   ```bash
   python benchmarks/run_eval.py --security-only
   ```

### Known Issues to Watch

1. **Security eval**: Only 40% block rate when LLM is involved (LLM generates "safe" code using allowed modules like pathlib to accomplish dangerous tasks). Direct AST check works 100%. This is a design limitation of blocklist-based security.

2. **Bootstrap tool execution**: Bootstrap tools (get_financial_info, get_index_daily, etc.) may fail in eval because the runner passes generic args — the `inspect.signature` fix should help, but the bootstrap tools are self-contained scripts that fetch their own data.

3. **LLM-generated tools**: The Qwen3 LLM generates self-contained tools that fetch data via yfinance internally. The eval framework's approach of passing price data externally doesn't match this pattern well. The arg filtering fix mitigates but may not fully resolve.

4. **Result format mismatch**: LLM tools often return DataFrames/Series instead of simple floats/dicts. The lenient judging helps but isn't perfect.

### Nice to Have

- Update `check.md` to reflect yfinance migration (currently references akshare)
- Update `plan.md` and `CLAUDE.md` to reflect current state
- Update `progress.md` with session results

---

## Current Registered Tools (DB)

| ID | Name | Status |
|----|------|--------|
| 1 | get_stock_hist | PROVISIONAL |
| 2 | get_financial_info | PROVISIONAL |
| 3 | get_realtime_quote | PROVISIONAL |
| 4 | get_index_daily | PROVISIONAL |
| 5 | get_etf_hist | PROVISIONAL |
| 6-9 | (stale from interrupted eval) | PROVISIONAL |

Clean IDs 6+ before next eval run.

---

## Files Modified This Session

- `fin_evo_agent/main.py` — fixed import, stock codes, column names
- `fin_evo_agent/src/core/executor.py` — added inspect.signature arg filtering
- `fin_evo_agent/src/core/models.py` — updated comment
- `fin_evo_agent/src/evolution/synthesizer.py` — fixed function name extraction, added LLM hint
- `fin_evo_agent/benchmarks/run_eval.py` — fixed import, args, judging, added `re` import
- `fin_evo_agent/benchmarks/tasks.jsonl` — rewritten for US tickers

---

## Resume Command

```bash
cd "/Users/liuzhenqian/Desktop/personal project/2026-1-week3/Insitu finance agent/fin_evo_agent"
source .venv/bin/activate

# Clean stale tools
sqlite3 data/db/evolution.db "DELETE FROM tool_artifacts WHERE id > 5"
rm -f data/artifacts/generated/*.py

# Run eval
python benchmarks/run_eval.py --agent evolving --run-id run1_final
```
