# Codebase Structure

**Analysis Date:** 2026-02-03

## Directory Layout

```
fin_evo_agent/
├── .venv/                      # Python virtual environment (gitignored)
├── .env                        # API key configuration
├── .gitignore                  # Git exclusions (cache/, logs/, .venv/)
├── main.py                     # CLI entry point
├── requirements.txt            # Locked dependencies
├── benchmarks/                 # Evaluation suite
│   ├── tasks.jsonl            # 20 benchmark tasks with contracts
│   ├── security_tasks.jsonl   # 5 security test cases
│   ├── run_eval.py            # Evaluation runner
│   ├── compare_runs.py        # Run comparison tool
│   └── results/               # JSON result files (timestamped)
├── data/                       # Persistent storage
│   ├── db/                    # SQLite database
│   │   └── evolution.db       # 5 tables (tool_artifacts, execution_traces, etc.)
│   ├── artifacts/             # Tool code files (.py)
│   │   ├── bootstrap/         # Initial atomic tools (5 yfinance wrappers)
│   │   └── generated/         # Evolved tools (e.g., calc_rsi_v0.1.0_a5a0e879.py)
│   ├── cache/                 # [Gitignored] Parquet data snapshots
│   └── logs/                  # [Gitignored] Thinking process, security violations
└── src/                        # Source code
    ├── config.py              # Global configuration (paths, LLM settings)
    ├── core/                  # System primitives
    │   ├── models.py          # SQLModel definitions (5 tables + enums)
    │   ├── registry.py        # Tool registration & retrieval
    │   ├── executor.py        # AST security + subprocess sandbox
    │   ├── task_executor.py   # Task orchestration (fetch + execute)
    │   ├── llm_adapter.py     # Qwen3 API client + category prompts
    │   ├── capabilities.py    # Capability enums & module mappings
    │   ├── contracts.py       # Contract definitions (17 contracts)
    │   └── verifier.py        # Multi-stage verification pipeline
    ├── evolution/             # Tool generation & refinement
    │   ├── synthesizer.py     # Generate → Verify → Register
    │   └── refiner.py         # Error analysis → Patch → Re-verify
    ├── finance/               # Domain-specific tools
    │   ├── data_proxy.py      # yfinance caching with retry
    │   └── bootstrap.py       # Initial tool creation
    └── utils/                 # (Empty - reserved for helpers)
```

## Directory Purposes

**`benchmarks/`:**
- Purpose: Evaluation and testing infrastructure
- Contains: Task definitions (JSONL), evaluation runner, comparison tools, result archives
- Key files: `tasks.jsonl` (20 tasks with contract_id), `run_eval.py` (main evaluation script)

**`data/db/`:**
- Purpose: SQLite database storage
- Contains: `evolution.db` (5 tables: ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
- Key files: `evolution.db`

**`data/artifacts/bootstrap/`:**
- Purpose: Initial atomic tools (not evolved)
- Contains: 5 pre-built yfinance wrappers
- Key files: `get_stock_hist_v0.1.0_*.py`, `get_financial_info_v0.1.0_*.py`, `get_spot_price_v0.1.0_*.py`, `get_index_daily_v0.1.0_*.py`, `get_etf_hist_v0.1.0_*.py`

**`data/artifacts/generated/`:**
- Purpose: LLM-generated evolved tools
- Contains: Tool code files with naming pattern `{name}_v{version}_{hash8}.py`
- Key files: `calc_rsi_v0.1.0_*.py`, `calc_macd_v0.1.0_*.py`, `calc_bollinger_v0.1.0_*.py`

**`data/cache/`:**
- Purpose: Reproducible data access (Parquet snapshots)
- Contains: Cached yfinance responses (MD5-keyed parquet files)
- Key files: `{md5_hash}.parquet` (auto-generated, gitignored)

**`data/logs/`:**
- Purpose: Debug and audit logs
- Contains: LLM thinking process logs, security violation logs
- Key files: `thinking_process_{timestamp}.txt`, `security_violations.log`

**`src/core/`:**
- Purpose: Core system components
- Contains: Data models, registry, executor, verifier, contracts, capabilities
- Key files: `models.py` (SQLModel tables), `verifier.py` (multi-stage pipeline), `executor.py` (sandbox)

**`src/evolution/`:**
- Purpose: Tool lifecycle management
- Contains: Synthesizer (generate + verify + register), Refiner (error analysis + patch)
- Key files: `synthesizer.py`, `refiner.py`

**`src/finance/`:**
- Purpose: Financial domain logic
- Contains: Data proxy (yfinance caching), bootstrap tools (atomic fetchers)
- Key files: `data_proxy.py`, `bootstrap.py`

## Key File Locations

**Entry Points:**
- `fin_evo_agent/main.py`: CLI commands (init, bootstrap, task, list, security-check)
- `fin_evo_agent/benchmarks/run_eval.py`: Evaluation runner

**Configuration:**
- `fin_evo_agent/src/config.py`: Global paths, LLM settings, execution limits
- `fin_evo_agent/.env`: API key (gitignored)
- `fin_evo_agent/requirements.txt`: Dependency versions

**Core Logic:**
- `fin_evo_agent/src/core/models.py`: 5 SQLModel tables + VerificationStage enum
- `fin_evo_agent/src/core/verifier.py`: Multi-stage verification (AST → self-test → contract → integration)
- `fin_evo_agent/src/core/executor.py`: AST security check + subprocess sandbox
- `fin_evo_agent/src/evolution/synthesizer.py`: LLM code generation + verification + registration

**Testing:**
- `fin_evo_agent/benchmarks/tasks.jsonl`: 20 benchmark tasks
- `fin_evo_agent/benchmarks/security_tasks.jsonl`: 5 security test cases

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `task_executor.py`, `llm_adapter.py`)
- Generated tools: `{function_name}_v{version}_{hash8}.py` (e.g., `calc_rsi_v0.1.0_a5a0e879.py`)
- Test files: `run_eval.py`, `compare_runs.py` (not using `.test.py` suffix)

**Directories:**
- All lowercase: `core/`, `evolution/`, `finance/`, `benchmarks/`
- Plural for collections: `artifacts/`, `logs/`, `results/`

**Functions:**
- snake_case: `extract_function_name()`, `verify_all_stages()`, `get_stock_hist()`

**Classes:**
- PascalCase: `ToolArtifact`, `MultiStageVerifier`, `TaskExecutor`, `Synthesizer`

**Constants:**
- UPPER_SNAKE_CASE: `BANNED_MODULES`, `RETRY_MAX_ATTEMPTS`, `CONTRACTS`

## Where to Add New Code

**New Feature:**
- Primary code: `fin_evo_agent/src/core/` for system-level features
- Tests: Add to `fin_evo_agent/benchmarks/tasks.jsonl` with contract_id

**New Component/Module:**
- Implementation: `fin_evo_agent/src/{domain}/` (e.g., `src/analysis/` for new analysis tools)

**Utilities:**
- Shared helpers: `fin_evo_agent/src/utils/` (currently empty - reserved)

**New Verification Stage:**
- Add stage to `VerificationStage` enum in `src/core/models.py`
- Implement `_verify_{stage}()` method in `src/core/verifier.py::MultiStageVerifier`
- Update `verify_all_stages()` to include new stage

**New Tool Category:**
- Add to `ToolCategory` enum in `src/core/capabilities.py`
- Define allowed modules in `CATEGORY_CAPABILITIES` mapping
- Add category-specific prompt in `src/core/llm_adapter.py`

**New Contract:**
- Add to `CONTRACTS` dict in `src/core/contracts.py`
- Define contract_id, input types, output type, constraints
- Reference contract_id in benchmark task (tasks.jsonl)

**New Bootstrap Tool:**
- Implement in `src/finance/data_proxy.py` with `@DataProvider.reproducible` decorator
- Register in `src/finance/bootstrap.py::create_bootstrap_tools()`

## Special Directories

**`data/cache/`:**
- Purpose: Reproducible data snapshots (Parquet files)
- Generated: Yes (auto-created by data_proxy on first fetch)
- Committed: No (gitignored for reproducibility - each dev has own cache)

**`data/logs/`:**
- Purpose: Debug and audit logs
- Generated: Yes (auto-created by executor and llm_adapter)
- Committed: No (gitignored - too large and environment-specific)

**`data/artifacts/generated/`:**
- Purpose: LLM-generated tool code
- Generated: Yes (created by Synthesizer during tool registration)
- Committed: Yes (essential for tracking tool evolution history)

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (manual: `python -m venv .venv`)
- Committed: No (gitignored - environment-specific)

**`benchmarks/results/`:**
- Purpose: Evaluation run results (JSON files with timestamps)
- Generated: Yes (created by run_eval.py)
- Committed: Partial (important milestones committed, others gitignored)

## Import Path Patterns

**Standard pattern for all modules:**
```python
import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import DB_PATH
from src.core.models import ToolArtifact
```

**Reason:** Ensures imports work regardless of working directory

## File Naming Patterns

**Tool artifacts:**
- Pattern: `{function_name}_v{version}_{hash8}.py`
- Example: `calc_rsi_v0.1.0_a5a0e879.py`
- Location: `data/artifacts/generated/` or `data/artifacts/bootstrap/`

**Cache files:**
- Pattern: `{md5_hash}.parquet`
- Example: `3f2a8c9d1e0b4a5c6d7e8f9a0b1c2d3e.parquet`
- Location: `data/cache/`

**Result files:**
- Pattern: `{timestamp}.json` or `{run_id}.json`
- Example: `20260203_134254.json`, `phase5_verification.json`
- Location: `benchmarks/results/`

**Log files:**
- Pattern: `{log_type}_{timestamp}.txt` or `{log_type}.log`
- Example: `thinking_process_20260203_134254.txt`, `security_violations.log`
- Location: `data/logs/`

## Architecture Decision Records

**"Metadata in DB, Payload on Disk":**
- SQLite stores tool metadata (name, version, hash, status)
- Filesystem stores actual code files (.py)
- Rationale: Git-trackable code, queryable metadata

**Capability-Based Security:**
- Different tool categories have different allowed modules
- CALCULATE tools CANNOT import yfinance (blocked)
- FETCH tools CAN import yfinance
- Rationale: Prevent privilege escalation, enforce separation of concerns

**Multi-Stage Verification:**
- Tools must pass ALL stages to be promoted
- Stages: AST security → self-test → contract → integration
- Rationale: Eliminate implicit pass, ensure tool quality

**Record-Replay Caching:**
- First yfinance call: fetch from network, save to parquet
- Subsequent calls: read from cache (no network)
- Rationale: Reproducibility, offline development

---

*Structure analysis: 2026-02-03*
