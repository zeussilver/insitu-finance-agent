# Architecture

**Analysis Date:** 2026-02-05

## Pattern Overview

**Overall:** Self-Evolving Agent with Capability-Based Tool Synthesis

**Key Characteristics:**
- LLM generates Python tools dynamically from natural language task descriptions
- Multi-stage verification pipeline (AST security → self-tests → contract validation → integration)
- Centralized enforcement gateway prevents verification bypass
- Metadata-in-database, payload-on-disk pattern for tool storage
- Reproducible data layer with parquet-based caching

## Layers

**CLI & Orchestration:**
- Purpose: User-facing interface and task coordination
- Location: `fin_evo_agent/main.py`, `fin_evo_agent/src/core/task_executor.py`
- Contains: Argument parsing, task workflow orchestration, bootstrap setup
- Depends on: Core layer, Evolution layer, Finance layer
- Used by: End users, Benchmark suite

**Core (Registry & Execution):**
- Purpose: Tool storage, retrieval, and sandboxed execution
- Location: `fin_evo_agent/src/core/`
- Contains:
  - `models.py` - SQLModel schemas (5 tables: ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
  - `registry.py` - Tool CRUD operations, schema-based matching
  - `executor.py` - AST security analysis, subprocess sandbox with 30s timeout
  - `gateway.py` - Single enforcement point for all tool registration
  - `verifier.py` - Multi-stage verification pipeline
  - `contracts.py` - 17 predefined contracts for input/output validation
  - `capabilities.py` - Category-specific module allowlists
  - `constraints.py` - Centralized runtime constraints loader (YAML-based)
  - `gates.py` - Three-tier evolution gate system (AUTO/CHECKPOINT/APPROVAL)
- Depends on: Config, Data models
- Used by: Evolution layer, CLI layer

**Evolution (Synthesis & Refinement):**
- Purpose: LLM-driven tool generation and error repair
- Location: `fin_evo_agent/src/evolution/`
- Contains:
  - `synthesizer.py` - Generate → Gateway Submit → Refine loop
  - `refiner.py` - Error analysis and patch generation (max 3 attempts)
- Depends on: Core layer, LLM adapter
- Used by: CLI layer, Benchmark suite

**Finance (Data Access):**
- Purpose: Bootstrap tools and data proxy
- Location: `fin_evo_agent/src/finance/`
- Contains:
  - `bootstrap.py` - 5 initial yfinance tools (get_stock_hist, get_financial_info, get_realtime_quote, get_index_daily, get_etf_hist)
  - `data_proxy.py` - Reproducible data layer with @with_retry decorator, parquet caching
- Depends on: yfinance SDK, Core models
- Used by: Task executor, Bootstrap tools

**Data Abstraction:**
- Purpose: Pluggable data provider interface
- Location: `fin_evo_agent/src/data/`
- Contains:
  - `interfaces.py` - DataProvider Protocol for structural typing
  - `adapters/yfinance_adapter.py` - Production adapter
  - `adapters/mock_adapter.py` - Testing adapter
- Depends on: None (Protocol-based)
- Used by: Finance layer, Future providers

**Extraction (Schema Intelligence):**
- Purpose: Task schema and technical indicator extraction
- Location: `fin_evo_agent/src/extraction/`
- Contains:
  - `schema.py` - Extract task category/params from NL queries
  - `indicators.py` - Identify technical indicator types
- Depends on: Core models
- Used by: Evolution layer for schema-based tool matching

**Configuration:**
- Purpose: Global settings and constraint definitions
- Location: `fin_evo_agent/src/config.py`, `fin_evo_agent/configs/constraints.yaml`
- Contains: Database paths, LLM config, execution limits, capability rules
- Depends on: None
- Used by: All layers

## Data Flow

**Tool Synthesis Flow:**

1. User submits task via CLI (`main.py --task "计算 RSI"`)
2. TaskExecutor infers category and fetches data if needed (via bootstrap tools)
3. Synthesizer generates code using LLM with category-specific prompt
4. VerificationGateway runs multi-stage verification:
   - Stage 1: AST security check (capability-based module rules)
   - Stage 2: Self-test execution (built-in assertions)
   - Stage 3: Contract validation (output constraints)
   - Stage 4: Integration test (real data, fetch tools only)
5. If all stages pass, Gateway registers tool to SQLite + disk
6. If any stage fails, Refiner analyzes error and generates patch (max 3 attempts)
7. Tool executes with sandboxed subprocess (30s timeout)

**Tool Execution Flow:**

1. TaskExecutor extracts symbol/date range from query
2. Fetches OHLCV data via bootstrap tools (cached in parquet)
3. Prepares arguments from fetched data (maps Close → prices, etc.)
4. Executor runs tool code in subprocess sandbox
5. Extracts result from stdout and validates against contract
6. Returns ExecutionTrace with result/error

**State Management:**
- SQLite stores tool metadata (name, version, hash, permissions, verification_stage)
- Disk stores actual Python code files (`data/artifacts/generated/{name}_v{version}_{hash}.py`)
- Parquet cache stores network responses (`data/cache/{md5}.parquet`)
- JSONL logs store gateway attempts (`data/logs/gateway_attempts.jsonl`)

## Key Abstractions

**VerificationGateway:**
- Purpose: Single enforcement point for all tool registration
- Examples: `fin_evo_agent/src/core/gateway.py`
- Pattern: Gateway pattern with checkpoint rollback
- All evolution modules MUST use `gateway.submit()` - direct `registry.register()` is prohibited

**ToolContract:**
- Purpose: Input/output validation rules for tool categories
- Examples: `fin_evo_agent/src/core/contracts.py`
- Pattern: Dataclass-based specification with 17 predefined contracts
- Each contract defines input_types, required_inputs, output_type, output_constraints

**ToolCapability:**
- Purpose: Category-specific module allowlists
- Examples: `fin_evo_agent/src/core/capabilities.py`
- Pattern: Enum-based capabilities with get_allowed_modules() mapping
- Different categories have different allowed modules (fetch can import yfinance, calculation cannot)

**DataProvider Protocol:**
- Purpose: Abstract financial data access
- Examples: `fin_evo_agent/src/data/interfaces.py`
- Pattern: Structural typing (Protocol) for pluggable adapters
- No inheritance required - duck typing for get_historical(), get_quote(), etc.

**ExecutionTrace:**
- Purpose: Complete record of tool execution for debugging and refinement
- Examples: `fin_evo_agent/src/core/models.py`
- Pattern: Immutable execution log with input_args, output_repr, std_out, std_err, execution_time_ms

## Entry Points

**CLI (main.py):**
- Location: `fin_evo_agent/main.py`
- Triggers: Direct invocation (`python main.py --task "..."`)
- Responsibilities: Command routing (--init, --bootstrap, --task, --list, --security-check)

**Benchmark Runner:**
- Location: `fin_evo_agent/benchmarks/run_eval.py`
- Triggers: Evaluation suite invocation
- Responsibilities: Run 20 benchmark tasks, measure success rate, tool reuse, security blocking

**Bootstrap Registration:**
- Location: `fin_evo_agent/src/finance/bootstrap.py`
- Triggers: First run or explicit --bootstrap command
- Responsibilities: Register 5 initial yfinance tools via VerificationGateway

## Error Handling

**Strategy:** Multi-level error recovery with automatic refinement

**Patterns:**
- AST security violations block immediately at Stage 1 (no execution)
- Self-test failures trigger Refiner with error context
- Contract validation failures provide constraint details for repair
- Network errors retry with exponential backoff (3 attempts, 1-10s)
- Subprocess timeouts terminate after 30s with SIGKILL
- All registration attempts logged to JSONL for audit trail

## Cross-Cutting Concerns

**Logging:** Structured logging to `data/logs/` (gateway.log for registration, gateway_attempts.jsonl for structured audit)

**Validation:**
- Multi-stage verification via VerificationGateway
- Contract-based output validation
- AST-based security analysis (banned modules: os, sys, subprocess, shutil, socket, pickle)

**Authentication:**
- LLM API key via environment variable (API_KEY)
- yfinance uses public API (no authentication)

**Caching:**
- Data layer: MD5-keyed parquet files in `data/cache/`
- Network retry: @with_retry decorator with exponential backoff

**Checkpointing:**
- Gateway creates rollback checkpoints before registration
- CheckpointManager stores context in `data/checkpoints/`
- Failed operations can be audited and rolled back

---

*Architecture analysis: 2026-02-05*
