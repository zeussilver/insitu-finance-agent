# Architecture

**Analysis Date:** 2026-02-03

## Pattern Overview

**Overall:** Self-Evolving Tool System with Multi-Stage Verification Pipeline

**Key Characteristics:**
- LLM-driven code generation with capability-based security validation
- "Metadata in DB, Payload on Disk" separation for auditability
- Contract-based output validation with progressive verification stages
- Record-replay caching for reproducible data access

## Layers

**Presentation Layer (CLI):**
- Purpose: User interface and command orchestration
- Location: `fin_evo_agent/main.py`
- Contains: Argument parsing, command handlers (init, bootstrap, task, list, security-check)
- Depends on: Core layer, Evolution layer, Finance layer
- Used by: End users, benchmark scripts

**Core Layer:**
- Purpose: System primitives for tool lifecycle management
- Location: `fin_evo_agent/src/core/`
- Contains: Data models, registry, executor, verifier, contracts, capabilities
- Depends on: Config, SQLModel, AST analysis
- Used by: Evolution layer, Task execution layer

**Evolution Layer:**
- Purpose: Tool generation and refinement loop
- Location: `fin_evo_agent/src/evolution/`
- Contains: Synthesizer (generate → verify → register), Refiner (error analysis → patch)
- Depends on: Core layer (LLM adapter, executor, registry, verifier)
- Used by: Task executor, evaluation suite

**Finance Layer:**
- Purpose: Domain-specific data access with reproducibility
- Location: `fin_evo_agent/src/finance/`
- Contains: Data proxy (yfinance caching), bootstrap tools (atomic fetch functions)
- Depends on: yfinance, pandas, config (CACHE_DIR)
- Used by: Task executor, bootstrap initialization

**Data Layer:**
- Purpose: Persistent storage for tools and execution history
- Location: `fin_evo_agent/data/`
- Contains: SQLite database (metadata), artifact files (.py code), cache (parquet), logs
- Depends on: SQLModel, filesystem
- Used by: Registry, executor, data proxy

## Data Flow

**Tool Synthesis Flow:**

1. User provides task description → `Synthesizer.synthesize()`
2. LLM generates Python code (category-specific prompt) → `LLMAdapter.generate_tool_code()`
3. Multi-stage verification pipeline:
   - Stage 1: AST security check (capability-based) → `MultiStageVerifier._verify_ast_security()`
   - Stage 2: Self-test execution (built-in asserts) → `MultiStageVerifier._verify_self_test()`
   - Stage 3: Contract validation (output constraints) → `MultiStageVerifier._verify_contract()`
   - Stage 4: Integration test (real data for fetch tools) → `MultiStageVerifier._verify_integration()`
4. If all stages pass: Write code to disk → `ToolRegistry.register()`
5. If any stage fails: Invoke refiner with error context → `Refiner.refine()`

**Task Execution Flow:**

1. User provides task query → `TaskExecutor.execute_task()`
2. Extract symbol and date range from query → `TaskExecutor.extract_symbol()`, `TaskExecutor.extract_date_range()`
3. Fetch OHLCV data via cached proxy → `get_stock_hist()` (with retry)
4. Check if simple fetch pattern (latest/highest/lowest close) → `TaskExecutor._handle_simple_fetch()`
5. If simple: Return direct result, skip tool execution
6. If complex: Prepare args from data → `TaskExecutor.prepare_calc_args()`
7. Execute tool in sandbox → `ToolExecutor.execute()` (subprocess isolation)
8. Return execution trace with result/error

**State Management:**
- Tool metadata: SQLite database (5 tables: ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
- Tool code: Filesystem (`data/artifacts/generated/{name}_v{version}_{hash8}.py`)
- Data cache: Parquet files (`data/cache/{md5}.parquet`)
- Execution state: Stateless (each task execution creates new trace)

## Key Abstractions

**ToolArtifact:**
- Purpose: Represents a registered tool with metadata
- Examples: `data/artifacts/generated/calc_rsi_v0.1.0_a5a0e879.py`, `data/artifacts/bootstrap/get_stock_hist_v0.1.0_*.py`
- Pattern: SQLModel with file pointer (code_content redundant for convenience)
- Fields: name, version, content_hash, file_path, permissions, status, category, capabilities, contract_id, verification_stage

**ToolContract:**
- Purpose: Defines input/output constraints for task validation
- Examples: `calc_rsi` (output: 0-100), `fetch_price` (output: numeric ≥ 0), `calc_bollinger` (output: dict with upper/middle/lower)
- Pattern: Dataclass with input types, output type, constraints
- Used by: MultiStageVerifier for contract validation stage

**ToolCapability:**
- Purpose: Defines what operations a tool category can perform
- Examples: CALCULATE (pandas/numpy only), FETCH (yfinance allowed), NETWORK_READ (yfinance allowed)
- Pattern: Enum with module mappings
- Used by: AST security checker to enforce capability-based import rules

**ExecutionTrace:**
- Purpose: Records execution context for debugging and refinement
- Examples: Trace for successful RSI calculation, trace for failed MACD with error
- Pattern: SQLModel with input snapshot, output, stdout/stderr, timing
- Used by: Refiner for error analysis, evaluation suite for metrics

**MultiStageVerifier:**
- Purpose: Progressive verification pipeline ensuring tool quality
- Examples: Verification report showing tool passed AST+self-test but failed contract
- Pattern: Strategy pattern with stage results (PASS/FAIL/SKIP)
- Used by: Synthesizer during tool registration

## Entry Points

**CLI Entry Point:**
- Location: `fin_evo_agent/main.py`
- Triggers: Command-line invocation (`python main.py --task "..."`)
- Responsibilities: Parse args, dispatch to command handlers, display results

**Evaluation Entry Point:**
- Location: `fin_evo_agent/benchmarks/run_eval.py`
- Triggers: Benchmark execution (`python benchmarks/run_eval.py --agent evolving`)
- Responsibilities: Load tasks.jsonl, execute each task, compute metrics, save results

**Database Initialization:**
- Location: `src/core/models.py::init_db()`
- Triggers: `python main.py --init` or first import
- Responsibilities: Create 5 SQLModel tables, run migrations for new schema fields

**Bootstrap Tool Creation:**
- Location: `src/finance/bootstrap.py::create_bootstrap_tools()`
- Triggers: `python main.py --bootstrap`
- Responsibilities: Register 5 atomic yfinance tools (get_stock_hist, get_financial_info, get_spot_price, get_index_daily, get_etf_hist)

## Error Handling

**Strategy:** Multi-level with progressive refinement

**Patterns:**
- **AST Security Check:** Fails immediately with SecurityException if banned modules/calls detected → logged to `data/logs/security_violations.log`
- **Execution Sandbox:** Subprocess timeout (30s) returns non-zero exit code → captured in ExecutionTrace.std_err
- **Verification Failure:** Returns VerificationReport with failed stage → triggers Refiner if enabled
- **Network Failure:** Retry with exponential backoff (3 attempts, 1-10s delay) → raises RuntimeError after exhaustion
- **LLM Failure:** Returns empty code_payload → synthesis returns (None, error_trace)

## Cross-Cutting Concerns

**Logging:**
- Thinking process logs: `data/logs/thinking_process_{timestamp}.txt` (from LLM adapter)
- Security violations: `data/logs/security_violations.log` (from executor)
- Network retry: Printed to stdout (from data_proxy)

**Validation:**
- Input validation: AST security check with capability-based rules
- Output validation: Contract-based constraints (type, range, required keys)
- Data validation: Type coercion for cached parquet data

**Authentication:**
- Not applicable (single-user local system)
- LLM API key: Environment variable `API_KEY` loaded from `.env`

---

*Architecture analysis: 2026-02-03*
