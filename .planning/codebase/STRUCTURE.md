# Codebase Structure

**Analysis Date:** 2026-02-06

## Directory Layout

```
fin_evo_agent/
├── main.py                        # CLI entry point
├── requirements.txt               # Python dependencies (locked versions)
├── .env                           # Environment variables (API_KEY)
├── configs/                       # Centralized configuration
│   └── constraints.yaml           # Runtime constraints (capabilities, security rules)
├── src/                           # Source code
│   ├── config.py                  # Global configuration loader
│   ├── core/                      # Core infrastructure
│   ├── evolution/                 # Tool synthesis and refinement
│   ├── finance/                   # Bootstrap tools and data proxy
│   ├── data/                      # Data abstraction layer
│   ├── extraction/                # Schema and indicator extraction
│   └── utils/                     # Shared utilities
├── data/                          # Runtime data (gitignored)
│   ├── db/evolution.db            # SQLite database (5 tables)
│   ├── artifacts/                 # Tool code storage
│   │   ├── bootstrap/             # Initial yfinance tools
│   │   └── generated/             # Evolved tools (calc_rsi_v0.1.0_xxx.py)
│   ├── cache/                     # Parquet snapshots (yfinance data)
│   ├── checkpoints/               # Rollback checkpoints
│   └── logs/                      # Structured logs (gateway, security, LLM)
├── tests/                         # Test suite (102+ tests)
│   ├── core/                      # Core module tests
│   ├── evolution/                 # Evolution module tests
│   ├── data/                      # Data adapter tests
│   └── extraction/                # Schema extraction tests
└── benchmarks/                    # Evaluation framework
    ├── tasks.jsonl                # 20 benchmark tasks
    ├── security_tasks.jsonl       # 5 security test cases
    ├── config_matrix.yaml         # Benchmark configurations
    ├── run_eval.py                # Evaluation runner
    ├── compare_runs.py            # Run comparison tool
    ├── results/                   # Evaluation results (JSON)
    └── baselines/                 # Baseline comparison data
```

## Directory Purposes

**configs/**
- Purpose: Centralized runtime configuration
- Contains: YAML files defining constraints, capabilities, security rules
- Key files: `constraints.yaml` (single source of truth for all rules)

**src/core/**
- Purpose: Core infrastructure for tool lifecycle management
- Contains: Database models, registry, executor, verifier, gateway, capabilities, contracts
- Key files:
  - `models.py`: 5 SQLModel tables (ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
  - `gateway.py`: VerificationGateway single enforcement point
  - `verifier.py`: MultiStageVerifier (4-stage pipeline)
  - `executor.py`: ToolExecutor (AST security + subprocess sandbox)
  - `registry.py`: ToolRegistry (CRUD operations on ToolArtifact)
  - `capabilities.py`: Capability-based permission system
  - `contracts.py`: 17 predefined contracts for task types
  - `constraints.py`: Centralized constraints loader
  - `gates.py`: EvolutionGate enum and Gatekeeper
  - `llm_adapter.py`: Qwen3 API integration
  - `task_executor.py`: Task orchestration (data fetch + tool execution)

**src/evolution/**
- Purpose: Tool generation, verification, and refinement
- Contains: LLM-driven code synthesis and error-based repair
- Key files:
  - `synthesizer.py`: Generate code from task → submit to gateway
  - `refiner.py`: Analyze error → generate patch → submit to gateway
  - `merger.py`: Batch tool consolidation (stub for Phase 1b)

**src/finance/**
- Purpose: Bootstrap tools and financial data access
- Contains: Initial yfinance tools and caching proxy
- Key files:
  - `bootstrap.py`: Create 5 initial yfinance tools
  - `data_proxy.py`: `@reproducible` decorator for yfinance caching

**src/data/**
- Purpose: Abstract data layer for pluggable providers
- Contains: DataProvider protocol and adapter implementations
- Key files:
  - `interfaces.py`: DataProvider protocol definition
  - `adapters/yfinance_adapter.py`: Production yfinance adapter
  - `adapters/mock_adapter.py`: Testing mock adapter

**src/extraction/**
- Purpose: Schema and technical indicator extraction from tasks
- Contains: Task schema extraction logic
- Key files:
  - `schema.py`: Extract category, inputs, outputs from task queries
  - `indicators.py`: Extract technical indicator types (RSI, MACD, etc.)

**data/db/**
- Purpose: SQLite database storage
- Contains: Single `evolution.db` file with 5 tables
- Committed: No (gitignored)

**data/artifacts/bootstrap/**
- Purpose: Initial yfinance tools for cold-start
- Contains: 5 manually created tools (get_stock_hist, get_financial_info, etc.)
- Committed: Yes (checked into git)

**data/artifacts/generated/**
- Purpose: Evolved tools created by Synthesizer
- Contains: Auto-generated `.py` files with versioned naming
- Committed: No (gitignored, only metadata in DB is committed)

**data/cache/**
- Purpose: Parquet snapshots of yfinance data for reproducibility
- Contains: `.parquet` files keyed by MD5 hash of (function + args)
- Committed: No (gitignored)

**data/checkpoints/**
- Purpose: Rollback points created by VerificationGateway
- Contains: JSON files with checkpoint state (pending/complete/failed)
- Committed: No (gitignored)

**data/logs/**
- Purpose: Structured logging for debugging and audit
- Contains: Log files and JSONL entries
- Committed: No (gitignored)

**tests/**
- Purpose: Test suite covering core modules
- Contains: pytest-based tests (102+ tests)
- Committed: Yes

**benchmarks/**
- Purpose: Evaluation framework for agent performance
- Contains: Task definitions, evaluation runner, results
- Committed: Yes (tasks and config), No (results)

## Key File Locations

**Entry Points:**
- `fin_evo_agent/main.py`: CLI entry point for all commands
- `fin_evo_agent/benchmarks/run_eval.py`: Benchmark evaluation runner

**Configuration:**
- `fin_evo_agent/src/config.py`: Global paths, LLM config, execution limits
- `fin_evo_agent/configs/constraints.yaml`: Centralized runtime constraints
- `fin_evo_agent/.env`: Environment variables (API_KEY, LLM_TIMEOUT)

**Core Logic:**
- `fin_evo_agent/src/core/gateway.py`: Single enforcement point for tool registration
- `fin_evo_agent/src/core/verifier.py`: Multi-stage verification pipeline
- `fin_evo_agent/src/core/executor.py`: AST security check + subprocess execution
- `fin_evo_agent/src/evolution/synthesizer.py`: LLM code generation
- `fin_evo_agent/src/evolution/refiner.py`: Error analysis and code patching

**Testing:**
- `fin_evo_agent/tests/core/test_gateway.py`: Gateway integration tests
- `fin_evo_agent/tests/core/test_executor.py`: Executor security tests
- `fin_evo_agent/tests/evolution/test_refiner.py`: Refiner patch tests
- `fin_evo_agent/tests/extraction/test_schema.py`: Schema extraction golden tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `llm_adapter.py`, `task_executor.py`)
- Generated tools: `{tool_name}_v{version}_{hash8}.py` (e.g., `calc_rsi_v0.1.0_f42711fb.py`)
- Config files: `lowercase.yaml` (e.g., `constraints.yaml`, `config_matrix.yaml`)
- Data files: `{prefix}_{timestamp}.{ext}` (e.g., `cp_20260205_202906_submit_tool.json`)

**Directories:**
- Source code: `lowercase` (e.g., `core`, `evolution`, `finance`)
- Data storage: `lowercase` (e.g., `artifacts`, `cache`, `checkpoints`)

**Functions:**
- Public functions: `snake_case` (e.g., `execute_task`, `verify_all_stages`)
- Private functions: `_snake_case` (e.g., `_extract_args_schema`, `_handle_simple_fetch`)
- Tool functions: `{action}_{indicator}` (e.g., `calc_rsi`, `get_stock_hist`, `check_divergence`)

**Classes:**
- Class names: `PascalCase` (e.g., `ToolRegistry`, `MultiStageVerifier`, `VerificationGateway`)
- Enum classes: `PascalCase` with UPPER_CASE values (e.g., `ToolStatus.PROVISIONAL`, `VerificationStage.SELF_TEST`)

**Variables:**
- Local variables: `snake_case` (e.g., `tool_name`, `exec_trace`, `contract_id`)
- Constants: `UPPER_CASE` (e.g., `ALLOWED_MODULES`, `EXECUTION_TIMEOUT_SEC`)
- Class attributes: `snake_case` (e.g., `self.registry`, `self.executor`)

## Where to Add New Code

**New Feature:**
- Primary code: `fin_evo_agent/src/core/{feature_name}.py` (if core infrastructure) or `fin_evo_agent/src/evolution/{feature_name}.py` (if evolution-related)
- Tests: `fin_evo_agent/tests/core/test_{feature_name}.py` or `fin_evo_agent/tests/evolution/test_{feature_name}.py`
- Configuration: Add to `fin_evo_agent/configs/constraints.yaml` if adding new constraints

**New Tool Contract:**
- Implementation: Add to `CONTRACTS` dict in `fin_evo_agent/src/core/contracts.py`
- Format: `ToolContract(contract_id=..., category=..., description=..., input_types=..., output_type=..., output_constraints=...)`
- Tests: Add to `fin_evo_agent/tests/core/test_contracts.py` (if exists) or update benchmark tasks

**New Capability Category:**
- Constraints: Add to `capabilities` section in `fin_evo_agent/configs/constraints.yaml`
- Enum: Add to `ToolCategory` in `fin_evo_agent/src/core/capabilities.py`
- Mapping: Update `CATEGORY_CAPABILITIES` dict in `fin_evo_agent/src/core/capabilities.py`

**New Data Provider:**
- Implementation: `fin_evo_agent/src/data/adapters/{provider_name}_adapter.py`
- Must implement: `DataProvider` protocol from `fin_evo_agent/src/data/interfaces.py`
- Registration: Update imports in `fin_evo_agent/src/data/__init__.py`
- Tests: `fin_evo_agent/tests/data/test_{provider_name}_adapter.py`

**New Verification Stage:**
- Enum: Add to `VerificationStage` in `fin_evo_agent/src/core/models.py`
- Logic: Add `verify_stage_{stage_name}()` method in `fin_evo_agent/src/core/verifier.py`
- Pipeline: Update `verify_all_stages()` in `fin_evo_agent/src/core/verifier.py`

**New Bootstrap Tool:**
- Implementation: Add function in `fin_evo_agent/src/finance/bootstrap.py`
- Registration: Call in `create_bootstrap_tools()` function
- Storage: Will be written to `fin_evo_agent/data/artifacts/bootstrap/{tool_name}.py`

**Utilities:**
- Shared helpers: `fin_evo_agent/src/utils/{module_name}.py`
- String parsing: Add to existing modules (e.g., `src/core/task_executor.py` for symbol extraction)
- Data transformation: `fin_evo_agent/src/data/adapters/` (adapter-specific) or `fin_evo_agent/src/utils/data.py` (generic)

## Special Directories

**data/cache/**
- Purpose: Parquet cache for yfinance data (reproducibility)
- Generated: Yes (by `@reproducible` decorator)
- Committed: No (gitignored, regenerated from network on first run)

**data/artifacts/generated/**
- Purpose: Auto-generated tool code from Synthesizer
- Generated: Yes (by `Synthesizer.synthesize()` and `Refiner.refine()`)
- Committed: No (gitignored, tool metadata stored in DB)

**data/checkpoints/**
- Purpose: Rollback points for gateway operations
- Generated: Yes (by `CheckpointManager.create_checkpoint()`)
- Committed: No (gitignored, used for runtime recovery only)

**data/logs/**
- Purpose: Structured logs and audit trails
- Generated: Yes (by logging handlers)
- Committed: No (gitignored, rotated periodically)

**.venv/**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv .venv`)
- Committed: No (gitignored)

**__pycache__/**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (gitignored)

**benchmarks/results/**
- Purpose: Evaluation run results
- Generated: Yes (by `run_eval.py`)
- Committed: No (gitignored, saved for analysis but not version controlled)

---

*Structure analysis: 2026-02-06*
