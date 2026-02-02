# Codebase Structure

**Analysis Date:** 2026-01-31

## Directory Layout

```
fin_evo_agent/
├── main.py                       # CLI entry point (commands: --init, --task, --list, --security-check, --bootstrap)
├── requirements.txt              # Locked dependencies (pandas, numpy, openai, yfinance, sqlmodel, etc.)
├── .env                          # Environment config (API_KEY, other settings)
├── .gitignore                    # Git ignore patterns
│
├── src/                          # Main source code
│   ├── __init__.py
│   ├── config.py                 # Global configuration (paths, DB URL, LLM settings, execution limits)
│   │
│   ├── core/                     # Core infrastructure (execution, registry, models, LLM)
│   │   ├── __init__.py
│   │   ├── models.py             # SQLModel definitions (5 tables: ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
│   │   ├── executor.py           # ToolExecutor (AST static analysis + subprocess sandbox with JSON-IPC)
│   │   ├── registry.py           # ToolRegistry (store/retrieve tools, content-hash deduplication, versioning)
│   │   └── llm_adapter.py        # LLMAdapter (Qwen3-Max protocol, thinking mode, code extraction)
│   │
│   ├── evolution/                # Tool generation and refinement
│   │   ├── __init__.py
│   │   ├── synthesizer.py        # Synthesizer (LLM → static check → sandbox test → register)
│   │   └── refiner.py            # Refiner (error analysis → patch generation → re-verify, max 3 attempts)
│   │
│   ├── finance/                  # Financial data and bootstrap tools
│   │   ├── __init__.py
│   │   ├── data_proxy.py         # DataProvider (yfinance wrapper with record-replay Parquet caching)
│   │   └── bootstrap.py          # Bootstrap tools (5 initial yfinance tools with self-tests)
│   │
│   └── utils/                    # Utilities (currently empty)
│       └── __init__.py
│
├── data/                         # Data storage (metadata in DB, payload on disk)
│   ├── db/
│   │   └── evolution.db          # SQLite database (5 tables, creates on first init)
│   │
│   ├── artifacts/                # Tool code files (Git-tracked)
│   │   ├── bootstrap/            # Initial tools (5 bootstrap tools)
│   │   │   ├── get_a_share_hist_v0.1.0_f4811dba.py
│   │   │   ├── get_financial_abstract_v0.1.0_4d51f391.py
│   │   │   ├── get_fund_etf_hist_v0.1.0_01392fd7.py
│   │   │   ├── get_index_daily_v0.1.0_47332a8c.py
│   │   │   └── get_realtime_quote_v0.1.0_ceaf2218.py
│   │   │
│   │   └── generated/            # Evolved tools (Git-tracked)
│   │       ├── calc_bollinger_v0.1.0_ee864087.py
│   │       ├── calc_correlation_v0.1.0_6c4fbbc7.py
│   │       ├── calc_kdj_v0.1.0_34602bc2.py
│   │       ├── calc_max_drawdown_v0.1.0_6f2134c7.py
│   │       ├── calc_rsi_v0.1.0_f42711fb.py
│   │       ├── calc_rsi_v0.1.1_58e0c3b5.py
│   │       ├── calc_volatility_v0.1.0_a9870622.py
│   │       ├── calc_volume_price_divergence_v0.1.0_927520c3.py
│   │       ├── calculate_ma5_recent_v0.1.0_1517b317.py
│   │       ├── get_recent_dividends_v0.1.0_c20f38c9.py
│   │       └── get_stock_dividend_history_v0.1.0_9f8649f2.py
│   │
│   ├── cache/                    # Parquet snapshots (Git-ignored, auto-generated on first run)
│   │   └── *.parquet             # MD5-keyed snapshots from yfinance (record-replay)
│   │
│   └── logs/                     # Thinking process logs (Git-ignored, future use)
│
└── benchmarks/                   # Evaluation suite
    ├── run_eval.py               # Evaluation runner (task simulation, metrics: success rate, reuse rate, security blocks)
    ├── compare_runs.py           # Run comparison tool (cross-run analysis)
    ├── tasks.jsonl               # 20 benchmark tasks (fetch, calculation, composite categories)
    ├── security_tasks.jsonl      # 5 security test cases (banned operations)
    │
    └── eval_report_*.csv         # Evaluation results (generated)
        ├── eval_report_run1.csv
        └── eval_report_run2.csv
```

## Directory Purposes

**src/:**
- Purpose: All application source code
- Contains: Core infrastructure, evolution engine, financial data access
- Key files:
  - `config.py`: Centralized configuration (all paths, LLM settings, execution limits)
  - `core/models.py`: Database schema definitions (5 SQLModel tables)

**src/core/:**
- Purpose: Core infrastructure - execution, registry, LLM communication
- Contains:
  - `executor.py`: Secure sandbox execution (AST checks, subprocess isolation)
  - `registry.py`: Tool lifecycle management (store, retrieve, deduplicate, version)
  - `llm_adapter.py`: Qwen3-Max integration (protocol cleaning, code extraction)
  - `models.py`: SQLModel schema definitions

**src/evolution/:**
- Purpose: Tool generation and improvement loop
- Contains:
  - `synthesizer.py`: Generate → Verify → Register (LLM-driven tool synthesis)
  - `refiner.py`: Error Analysis → Patch → Re-verify (automatic error recovery, max 3 retries)

**src/finance/:**
- Purpose: Financial data access and bootstrap
- Contains:
  - `data_proxy.py`: yfinance wrapper with MD5-keyed Parquet caching for reproducibility
  - `bootstrap.py`: 5 initial tools (stock history, financial info, quotes, index, ETF data)

**data/db/:**
- Purpose: SQLite database (persistent metadata store)
- Contents:
  - `evolution.db`: 5 tables - ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord

**data/artifacts/bootstrap/:**
- Purpose: Initial tool set (5 yfinance wrappers)
- Contents:
  - 5 .py files: get_a_share_hist, get_financial_abstract, get_fund_etf_hist, get_index_daily, get_realtime_quote
  - Pattern: `{name}_v{version}_{hash8}.py`
  - Each includes data caching logic and self-tests in `if __name__ == '__main__':` block

**data/artifacts/generated/:**
- Purpose: Evolved tools created via synthesis
- Contents:
  - 11+ .py files (as of 2026-01-31): RSI, KDJ, Bollinger, MACD, correlation, volatility, etc.
  - Pattern: `{name}_v{version}_{hash8}.py` (hash8 = first 8 chars of SHA256(code))
  - Naming example: `calc_rsi_v0.1.0_f42711fb.py`

**data/cache/:**
- Purpose: Parquet snapshots for record-replay caching
- Contents:
  - MD5-hashed .parquet files (one per unique data query)
  - Auto-generated on first execution
  - Git-ignored (not committed)

**benchmarks/:**
- Purpose: Evaluation suite for measuring agent performance
- Contains:
  - `run_eval.py`: Main evaluation runner (supports --agent and --run-id)
  - `compare_runs.py`: Cross-run comparison tool
  - `tasks.jsonl`: 20 benchmark tasks (8 fetch, 8 calculation, 4 composite)
  - `security_tasks.jsonl`: 5 security test cases

## Key File Locations

**Entry Points:**
- `main.py`: CLI entry point (init database, bootstrap, run task, list tools, security check)
- `benchmarks/run_eval.py`: Evaluation suite entry point

**Configuration:**
- `src/config.py`: Global settings (DB path, LLM API key, execution timeout, directories)
- `.env`: Environment file (API_KEY, local overrides)
- `requirements.txt`: Locked dependency versions

**Core Logic:**
- `src/core/executor.py`: Secure execution with AST analysis (banned imports, sandboxing)
- `src/core/registry.py`: Tool persistence and retrieval (SQL operations)
- `src/core/llm_adapter.py`: LLM protocol handling (code extraction from responses)
- `src/evolution/synthesizer.py`: Tool generation loop (LLM → verify → register)
- `src/evolution/refiner.py`: Error recovery loop (classify → patch → retry)

**Data Definitions:**
- `src/core/models.py`: SQLModel table definitions (ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
- `benchmarks/tasks.jsonl`: Benchmark task definitions (task_id, category, query, expected_output)

**Bootstrap and Caching:**
- `src/finance/bootstrap.py`: 5 initial tool templates (inline code strings)
- `src/finance/data_proxy.py`: yfinance wrapper with record-replay decorator

## Naming Conventions

**Files:**
- Tool code files: `{function_name}_v{semantic_version}_{content_hash8}.py`
  - Examples: `calc_rsi_v0.1.0_f42711fb.py`, `get_a_share_hist_v0.1.0_f4811dba.py`
  - Hash8 = first 8 characters of SHA256(code content) for deduplication
- Module files: `snake_case.py` (e.g., `data_proxy.py`, `llm_adapter.py`)
- Python packages: `snake_case/` directories with `__init__.py`

**Directories:**
- Modules: `snake_case` (e.g., `src/core/`, `src/evolution/`, `benchmarks/`)
- Data storage: lowercase with underscores (e.g., `artifacts/`, `bootstrap/`, `generated/`, `cache/`)

**Classes:**
- PascalCase (e.g., `ToolArtifact`, `ExecutionTrace`, `ToolRegistry`, `ToolExecutor`)

**Functions:**
- snake_case (e.g., `init_db()`, `static_check()`, `synthesize()`, `refine()`)
- Private functions: leading underscore (e.g., `_clean_protocol()`, `_classify_error()`)

**Variables and Constants:**
- Global constants: UPPER_SNAKE_CASE (e.g., `BANNED_MODULES`, `ALLOWED_MODULES`, `DB_PATH`)
- Local variables: snake_case (e.g., `code_content`, `tool_name`, `exit_code`)

## Where to Add New Code

**New Calculation Tool (e.g., MACD indicator):**
- Primary code: `data/artifacts/generated/{tool_name}_v0.1.0_{hash8}.py`
  - File is auto-generated by Synthesizer, but structure follows pattern in `data/artifacts/generated/calc_rsi_v0.1.0_f42711fb.py`
  - Must include docstring, type hints, and `if __name__ == '__main__':` test block
- Test cases: Embedded in the tool's `if __name__ == '__main__':` block (2 assert statements)
- Registration: Automatic via `ToolRegistry.register()` when synthesis succeeds

**New Data Access Tool (e.g., crypto price API):**
- Implementation: `src/finance/data_proxy.py` (add new decorator method or wrapper function)
- Bootstrap: If initial tool, add template to `src/finance/bootstrap.py` (inline code string)
- Pattern: Use `@DataProvider.reproducible` decorator for record-replay caching
- Registration: Bootstrap tools registered via `create_bootstrap_tools()` in `main.py`

**New Error Handling Pattern:**
- Location: `src/evolution/refiner.py` in the `ERROR_PATTERNS` dictionary
- Format:
  ```python
  "MyErrorType": {
      "pattern": r"MyErrorType: ...",  # Regex to match error
      "strategy": "How to fix this error..."  # Fix guidance for LLM
  }
  ```
- The Refiner uses these patterns to classify errors and generate patch prompts

**New Security Rule:**
- Location: `src/core/executor.py`
- Banned imports: Add to `BANNED_MODULES` set
- Banned functions: Add to `BANNED_CALLS` set
- Allowed imports: Add to `ALLOWED_MODULES` set only if needed
- Pattern: Conservative allowlist (whitelist) approach - default deny

**New Evaluation Benchmark:**
- Task definition: Add JSON line to `benchmarks/tasks.jsonl`
- Format:
  ```json
  {"task_id": "type_nnn", "category": "fetch|calculation|composite", "query": "...", "expected_output": {...}, "required_tools": [...], "difficulty": "easy|medium|hard"}
  ```
- Runner: Handled automatically by `benchmarks/run_eval.py`

**Utility Helpers:**
- Location: `src/utils/` (currently empty, add modules here for shared utilities)
- Imports: Import from `src.utils.{module}` following existing project structure

## Special Directories

**data/artifacts/:**
- Purpose: Persist tool code on disk (Git-tracked for reproducibility)
- Generated: No (files created by Synthesizer.synthesize() and Refiner.refine())
- Committed: Yes (essential for reproducibility)
- Subdirs:
  - `bootstrap/`: Initial 5 tools (never change)
  - `generated/`: Evolved tools (append-only, versions increase)

**data/cache/:**
- Purpose: Parquet snapshots for deterministic data access
- Generated: Yes (auto-generated on first `get_a_share_hist()` call)
- Committed: No (ignored in `.gitignore`)
- Cleanup: Can safely delete to force data refresh from yfinance

**data/logs/:**
- Purpose: LLM thinking process logs (for transparency)
- Generated: Yes (created by refiner/synthesizer if logging enabled)
- Committed: No (ignored in `.gitignore`)

**data/db/:**
- Purpose: SQLite database (persistent metadata store)
- Generated: Yes (created on `python main.py --init`)
- Committed: No (ignored in `.gitignore`, should be re-initialized in clean environments)

---

*Structure analysis: 2026-01-31*
