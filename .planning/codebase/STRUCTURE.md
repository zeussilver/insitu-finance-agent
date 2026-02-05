# Codebase Structure

**Analysis Date:** 2026-02-05

## Directory Layout

```
fin_evo_agent/
├── main.py                    # CLI entry point
├── requirements.txt           # Locked dependencies
├── .env                       # API key configuration
├── configs/                   # Configuration files
│   └── constraints.yaml       # Centralized runtime constraints
├── data/                      # Runtime data storage
│   ├── db/                    # SQLite database
│   ├── artifacts/             # Generated tool code files
│   ├── cache/                 # Parquet data cache [Git Ignore]
│   ├── logs/                  # Structured logs
│   └── checkpoints/           # Rollback checkpoints
├── src/                       # Core source code
│   ├── config.py              # Global configuration
│   ├── core/                  # Registry, execution, verification
│   ├── evolution/             # Tool synthesis and refinement
│   ├── finance/               # Bootstrap tools and data proxy
│   ├── data/                  # Data provider abstraction
│   ├── extraction/            # Schema and indicator extraction
│   └── utils/                 # Shared utilities
├── tests/                     # Isolated test suite
│   ├── core/                  # Core module tests
│   ├── evolution/             # Evolution module tests
│   ├── data/                  # Data adapter tests
│   └── extraction/            # Extraction module tests
└── benchmarks/                # Evaluation suite
    ├── run_eval.py            # Main evaluation runner
    ├── compare_runs.py        # Run comparison tool
    ├── tasks.jsonl            # 20 benchmark tasks
    ├── security_tasks.jsonl   # 5 security test cases
    ├── config_matrix.yaml     # Benchmark configuration matrix
    ├── results/               # Evaluation results
    └── baselines/             # Baseline comparison data
```

## Directory Purposes

**fin_evo_agent/ (root):**
- Purpose: Project root with entry point and configuration
- Contains: `main.py`, `requirements.txt`, `.env`, `.gitignore`
- Key files:
  - `main.py` - CLI commands (--init, --bootstrap, --task, --list, --security-check)
  - `requirements.txt` - Locked dependencies (yfinance, openai, sqlmodel, pandas, pyyaml)
  - `.env` - API_KEY for Qwen3 LLM

**configs/**
- Purpose: Centralized configuration management
- Contains: YAML configuration files
- Key files:
  - `constraints.yaml` - Runtime constraints (execution limits, capability rules, security allowlists)

**data/**
- Purpose: Runtime data storage (not version controlled except structure)
- Contains: Database, artifacts, cache, logs, checkpoints
- Key files:
  - `db/evolution.db` - SQLite database with 5 tables
  - `artifacts/bootstrap/*.py` - Initial yfinance tools (5 files)
  - `artifacts/generated/*.py` - LLM-generated tools (format: `{name}_v{version}_{hash}.py`)
  - `cache/*.parquet` - MD5-keyed data snapshots [Git Ignore]
  - `logs/gateway.log` - Registration log
  - `logs/gateway_attempts.jsonl` - Structured audit trail
  - `checkpoints/*.json` - Rollback checkpoints

**src/core/**
- Purpose: Core engine for tool registry, execution, and verification
- Contains: 13 Python modules
- Key files:
  - `models.py` - SQLModel schemas (ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
  - `registry.py` - Tool CRUD (register, get_by_name, get_by_id, list_tools, update_schema)
  - `executor.py` - AST security check + subprocess sandbox
  - `gateway.py` - VerificationGateway (single enforcement point)
  - `verifier.py` - MultiStageVerifier (4 stages: AST → self-test → contract → integration)
  - `contracts.py` - 17 ToolContract definitions
  - `capabilities.py` - ToolCapability enum with module allowlists
  - `constraints.py` - Load constraints from YAML
  - `gates.py` - EvolutionGate enum, EvolutionGatekeeper, CheckpointManager
  - `task_executor.py` - Task orchestration (extract symbol/dates, fetch data, execute tool)
  - `llm_adapter.py` - Qwen3 API client with category-specific prompts

**src/evolution/**
- Purpose: LLM-driven tool generation and repair
- Contains: 2 Python modules
- Key files:
  - `synthesizer.py` - Generate → Gateway Submit → Refine loop
  - `refiner.py` - Error analysis and patch generation (max 3 attempts)

**src/finance/**
- Purpose: Financial data access with bootstrap tools
- Contains: 2 Python modules
- Key files:
  - `bootstrap.py` - 5 bootstrap tool templates (get_stock_hist, get_financial_info, etc.)
  - `data_proxy.py` - @with_retry decorator, parquet caching, get_stock_hist()

**src/data/**
- Purpose: Data provider abstraction layer
- Contains: `interfaces.py` and `adapters/` subdirectory
- Key files:
  - `interfaces.py` - DataProvider Protocol
  - `adapters/yfinance_adapter.py` - Production adapter
  - `adapters/mock_adapter.py` - Testing adapter

**src/extraction/**
- Purpose: Schema and indicator extraction from natural language
- Contains: 2 Python modules
- Key files:
  - `schema.py` - Extract task category, params from queries
  - `indicators.py` - Identify technical indicator types (rsi, macd, bollinger, etc.)

**tests/**
- Purpose: Isolated test suite (102+ tests)
- Contains: Test modules mirroring src structure
- Key files:
  - `core/test_gateway.py` - Gateway enforcement tests
  - `core/test_executor.py` - Security and sandbox tests
  - `evolution/test_refiner.py` - Refinement loop tests
  - `data/test_adapters.py` - Data provider protocol tests
  - `extraction/test_schema.py` - Schema extraction tests (with golden_schemas.json)
  - `extraction/test_indicators.py` - Indicator detection tests

**benchmarks/**
- Purpose: Evaluation suite for reproducibility
- Contains: Evaluation runners, task definitions, results
- Key files:
  - `run_eval.py` - Main evaluation runner (supports --config, --clear-registry, --security-only)
  - `compare_runs.py` - Compare two evaluation runs
  - `tasks.jsonl` - 20 benchmark tasks (8 fetch, 8 calculation, 4 composite)
  - `security_tasks.jsonl` - 5 security violation test cases
  - `config_matrix.yaml` - cold_start vs warm_start configurations
  - `results/*.json` - Evaluation results with timestamps
  - `baselines/*.json` - Baseline results for regression testing

## Key File Locations

**Entry Points:**
- `fin_evo_agent/main.py` - CLI entry point
- `fin_evo_agent/benchmarks/run_eval.py` - Evaluation entry point
- `fin_evo_agent/src/finance/bootstrap.py` - Bootstrap registration entry point

**Configuration:**
- `fin_evo_agent/src/config.py` - Global config (DB paths, LLM config, timeouts)
- `fin_evo_agent/configs/constraints.yaml` - Centralized runtime constraints
- `fin_evo_agent/.env` - API key (not committed to Git)
- `fin_evo_agent/benchmarks/config_matrix.yaml` - Benchmark configurations

**Core Logic:**
- `fin_evo_agent/src/core/gateway.py` - Single enforcement point
- `fin_evo_agent/src/core/verifier.py` - Multi-stage verification
- `fin_evo_agent/src/evolution/synthesizer.py` - Tool generation
- `fin_evo_agent/src/core/task_executor.py` - Task orchestration

**Testing:**
- `fin_evo_agent/tests/` - Isolated test suite (pytest-based)
- `fin_evo_agent/benchmarks/run_eval.py` - End-to-end evaluation

## Naming Conventions

**Files:**
- Module files: `snake_case.py` (e.g., `task_executor.py`, `llm_adapter.py`)
- Config files: `snake_case.yaml` or `UPPERCASE.md` for docs
- Generated tools: `{function_name}_v{semver}_{hash8}.py` (e.g., `calc_rsi_v0.1.0_f42711fb.py`)

**Directories:**
- Package directories: `snake_case/` (e.g., `src/core/`, `src/evolution/`)
- Data directories: `lowercase/` (e.g., `data/cache/`, `data/logs/`)

**Functions:**
- Public functions: `snake_case` (e.g., `get_stock_hist`, `execute_task`)
- Private functions: `_snake_case` (e.g., `_extract_args_schema`, `_handle_simple_fetch`)

**Classes:**
- PascalCase (e.g., `VerificationGateway`, `MultiStageVerifier`, `ToolExecutor`)

**Constants:**
- UPPER_SNAKE_CASE (e.g., `DB_PATH`, `EXECUTION_TIMEOUT_SEC`, `LLM_MODEL`)

## Where to Add New Code

**New Feature:**
- Primary code: Determine layer (core/evolution/finance/data/extraction)
- If adding verification stage: `src/core/verifier.py`
- If adding tool capability: `configs/constraints.yaml` and `src/core/capabilities.py`
- If adding contract: `src/core/contracts.py`
- If adding LLM prompt: `src/core/llm_adapter.py`
- Tests: `tests/{layer}/test_{module}.py`

**New Component/Module:**
- Implementation: `src/{layer}/{module}.py`
- Tests: `tests/{layer}/test_{module}.py`
- Add to `__init__.py` if package-level import needed

**New Tool (Generated):**
- Implementation: Auto-generated to `data/artifacts/generated/`
- Metadata: Auto-stored in SQLite `tool_artifacts` table
- Never manually edit generated tools - use Refiner for repairs

**New Bootstrap Tool:**
- Implementation: Add code template to `src/finance/bootstrap.py`
- Registration: Call via `create_bootstrap_tools()` function
- Must include self-tests in `if __name__ == '__main__'` block

**New Data Provider:**
- Implementation: `src/data/adapters/{provider}_adapter.py`
- Must satisfy DataProvider Protocol (get_historical, get_quote, get_financial_info, get_multi_historical)
- Tests: `tests/data/test_adapters.py`

**Utilities:**
- Shared helpers: `src/utils/` (currently minimal - prefer layer-specific utilities)
- Cross-cutting concerns: Consider adding to appropriate core module

**New Benchmark Task:**
- Task definition: Add to `benchmarks/tasks.jsonl` (format: `{"task_id": "...", "category": "...", "query": "...", "contract_id": "..."}`)
- Contract: Add to `src/core/contracts.py` if new contract type
- Expected output: Add to comparison baseline if regression testing

## Special Directories

**data/cache/**
- Purpose: Parquet snapshots for reproducible data
- Generated: Yes (by @with_retry decorator)
- Committed: No (Git Ignore)
- Naming: MD5 hash of function call (e.g., `a3f2b8c9d1e0f7a6b5c4d3e2f1a0b9c8.parquet`)

**data/artifacts/generated/**
- Purpose: LLM-generated tool code
- Generated: Yes (by Synthesizer via Gateway)
- Committed: Yes (for auditability)
- Naming: `{function_name}_v{version}_{hash8}.py`

**data/artifacts/bootstrap/**
- Purpose: Initial yfinance tools
- Generated: Yes (by bootstrap.py)
- Committed: Yes (foundational tools)
- Naming: Same as generated tools

**data/db/**
- Purpose: SQLite database storage
- Generated: Yes (by init_db())
- Committed: No (Git Ignore - only schema in code)
- Naming: `evolution.db`

**data/logs/**
- Purpose: Structured logging and audit trails
- Generated: Yes (by Gateway, Executor)
- Committed: No (Git Ignore)
- Naming: `gateway.log`, `gateway_attempts.jsonl`, `thinking_process.log`, `security_violations.log`

**data/checkpoints/**
- Purpose: Rollback checkpoints for failed operations
- Generated: Yes (by CheckpointManager)
- Committed: No (Git Ignore)
- Naming: JSON files with checkpoint metadata

**benchmarks/results/**
- Purpose: Evaluation run results
- Generated: Yes (by run_eval.py)
- Committed: Yes (for tracking progress)
- Naming: `{run_id}.json` (e.g., `post_round3_fix.json`)

**benchmarks/baselines/**
- Purpose: Baseline results for regression testing
- Generated: Manually curated
- Committed: Yes
- Naming: `{baseline_name}.json`

**tests/**
- Purpose: Isolated test suite (pytest-based)
- Generated: No (manually written)
- Committed: Yes
- Naming: `test_{module}.py` (e.g., `test_gateway.py`, `test_executor.py`)

---

*Structure analysis: 2026-02-05*
