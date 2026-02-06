# Architecture

**Analysis Date:** 2026-02-06

## Pattern Overview

**Overall:** Self-Evolving Agent with Capability-Based Verification Gateway

**Key Characteristics:**
- LLM-driven tool synthesis and repair loop with multi-stage verification
- Capability-based security model preventing dangerous code execution
- "Metadata in DB, Payload on Disk" storage pattern for auditable evolution
- Contract-validated tool registration with rollback checkpoints
- Pluggable data adapters for reproducible testing

## Layers

**Presentation Layer (CLI):**
- Purpose: User interaction and command dispatch
- Location: `fin_evo_agent/main.py`
- Contains: Argument parsing, command handlers (init, bootstrap, task, list, security-check)
- Depends on: Core layer (registry, executor, models), Evolution layer (synthesizer)
- Used by: End users, CI/CD pipeline

**Core Layer:**
- Purpose: Tool lifecycle management and security enforcement
- Location: `fin_evo_agent/src/core/`
- Contains: Database models, registry, executor, verifier, gateway, capabilities, contracts
- Depends on: Data layer (for fetch operations), Config module
- Used by: Evolution layer, Task executor, Bootstrap tools

**Evolution Layer:**
- Purpose: Tool generation, verification, and refinement
- Location: `fin_evo_agent/src/evolution/`
- Contains: Synthesizer (LLM → code → gateway), Refiner (error → patch → gateway)
- Depends on: Core layer (gateway, verifier, executor, registry), LLM adapter
- Used by: Task executor (via synthesizer), Self-repair loop (via refiner)

**Data Layer:**
- Purpose: External data access with caching and reproducibility
- Location: `fin_evo_agent/src/data/`, `fin_evo_agent/src/finance/`
- Contains: DataProvider protocol, yfinance adapter, mock adapter, caching proxy
- Depends on: External APIs (yfinance), Parquet cache storage
- Used by: Task executor, Fetch tools, Integration tests

**Configuration Layer:**
- Purpose: Centralized runtime constraints and settings
- Location: `fin_evo_agent/src/config.py`, `fin_evo_agent/configs/constraints.yaml`
- Contains: Global paths, LLM config, execution limits, capability rules
- Depends on: Nothing (root dependency)
- Used by: All layers

## Data Flow

**Tool Synthesis Flow:**

1. User submits task via CLI (`main.py --task "计算 RSI"`)
2. Synthesizer extracts category and contract from task description
3. LLM generates Python code using category-specific prompts
4. Synthesizer submits code to VerificationGateway
5. Gateway creates rollback checkpoint and runs multi-stage verification
6. Verification passes: Registry stores metadata in DB, code on disk
7. Verification fails: Refiner analyzes error and generates patch
8. Patched code re-submitted to gateway (max 3 attempts)

**Task Execution Flow:**

1. TaskExecutor receives task with query and category
2. Executor extracts stock symbol and date range from query
3. DataProxy fetches OHLCV data from yfinance (cached)
4. For simple queries (latest/highest/lowest close), return directly
5. For complex queries, prepare args from fetched data
6. ToolExecutor runs tool code in subprocess sandbox (30s timeout)
7. ExecutionTrace logged with inputs, outputs, errors, timing
8. If error occurs, ErrorReport generated and Refiner invoked

**Verification Pipeline Flow:**

1. AST Security Check: Parse code, validate imports/calls against capability whitelist
2. Self-Test Execution: Run built-in assertions in sandboxed subprocess
3. Contract Validation: Check output type and constraints (min/max, required keys)
4. Integration Test: Fetch tools run against real data (cached yfinance)
5. ALL stages must pass for tool registration (no implicit pass)

**State Management:**
- Database state: SQLite with 5 tables (ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
- File state: Tool code stored as `.py` files in `data/artifacts/generated/`
- Cache state: Parquet snapshots in `data/cache/` for reproducible yfinance data
- Checkpoint state: Gateway creates rollback points before each registration

## Key Abstractions

**VerificationGateway:**
- Purpose: Single enforcement point for all tool registration
- Examples: `fin_evo_agent/src/core/gateway.py`
- Pattern: Facade pattern wrapping verifier, registry, gatekeeper, checkpoint manager
- Key methods: `submit()` (verify + register atomically), `verify_only()` (dry-run)
- Logging: All registration attempts logged to `data/logs/gateway_attempts.jsonl`

**ToolContract:**
- Purpose: Defines input/output contracts for task types
- Examples: `fin_evo_agent/src/core/contracts.py`
- Pattern: 17 predefined contracts (calc_rsi, fetch_price, comp_signal, etc.)
- Fields: category, input_types, required_inputs, output_type, output_constraints
- Usage: LLM prompt generation, multi-stage verification, error analysis

**MultiStageVerifier:**
- Purpose: Runs 4-stage verification pipeline (AST → self-test → contract → integration)
- Examples: `fin_evo_agent/src/core/verifier.py`
- Pattern: Chain of responsibility with VerificationReport accumulation
- Stages: VerificationStage enum (NONE=0, AST_SECURITY=1, SELF_TEST=2, CONTRACT_VALID=3, INTEGRATION=4)
- Result: (passed: bool, report: VerificationReport)

**ToolCapability:**
- Purpose: Capability-based permission system for tool execution
- Examples: `fin_evo_agent/src/core/capabilities.py`, `fin_evo_agent/configs/constraints.yaml`
- Pattern: FETCH tools can import yfinance, CALCULATE tools cannot
- Constraints: Delegates to centralized YAML for allowed/banned modules
- Enforcement: AST static analysis in `ToolExecutor.static_check_with_rules()`

**DataProvider Protocol:**
- Purpose: Abstract interface for pluggable financial data sources
- Examples: `fin_evo_agent/src/data/interfaces.py`, `fin_evo_agent/src/data/adapters/yfinance_adapter.py`
- Pattern: Protocol-based structural typing (no inheritance required)
- Methods: `get_historical()`, `get_quote()`, `get_financial_info()`, `get_multi_historical()`
- Implementations: YFinanceAdapter (production), MockAdapter (testing)

**LLMAdapter:**
- Purpose: Qwen3 API integration with category-specific prompts
- Examples: `fin_evo_agent/src/core/llm_adapter.py`
- Pattern: OpenAI-compatible API with thinking mode enabled
- Prompts: FETCH_SYSTEM_PROMPT (yfinance+caching), CALCULATE_SYSTEM_PROMPT (pandas/numpy), COMPOSITE_SYSTEM_PROMPT (tool chaining)
- Fallback: Mock responses if API_KEY not set

## Entry Points

**CLI Entry Point:**
- Location: `fin_evo_agent/main.py`
- Triggers: Command-line arguments (--init, --bootstrap, --task, --list, --security-check)
- Responsibilities: Parse args, dispatch to appropriate command handler, initialize components

**Benchmark Entry Point:**
- Location: `fin_evo_agent/benchmarks/run_eval.py`
- Triggers: CI/CD pipeline, manual evaluation runs
- Responsibilities: Load tasks from `benchmarks/tasks.jsonl`, run agent in cold_start or warm_start mode, collect metrics, save results

**Database Initialization:**
- Location: `fin_evo_agent/src/core/models.py:init_db()`
- Triggers: `main.py --init`, automatic on first import
- Responsibilities: Create 5 SQLModel tables, run migrations for new columns, ensure data directory structure

**Bootstrap Tool Creation:**
- Location: `fin_evo_agent/src/finance/bootstrap.py`
- Triggers: `main.py --bootstrap`
- Responsibilities: Register 5 initial yfinance tools (get_stock_hist, get_financial_info, get_realtime_quote, get_index_daily, get_etf_hist)

## Error Handling

**Strategy:** Multi-layer error handling with LLM-driven repair

**Patterns:**
- AST security violations: Fail immediately with SecurityException (unfixable)
- Import errors: Refiner suggests module replacements (talib → pandas/numpy)
- Type errors: Refiner adds type conversion and validation
- Key errors: Refiner uses `.get()` with defaults instead of direct indexing
- Execution timeouts: Fail fast (30s subprocess timeout)
- Network errors: Retry with exponential backoff (3 attempts, 1-10s delay)
- Contract violations: Refiner adjusts output format to match contract

**Repair Loop:**
1. ExecutionTrace captures error (exit_code != 0, std_err)
2. Refiner creates ErrorReport with LLM-analyzed root cause
3. Refiner generates patched code based on error context
4. Patch submitted to VerificationGateway (max 3 attempts)
5. If all attempts fail, tool marked as FAILED status

## Cross-Cutting Concerns

**Logging:**
- Gateway: `data/logs/gateway.log` (standard logger), `data/logs/gateway_attempts.jsonl` (structured attempts)
- Evolution: `data/logs/evolution_gates.log` (gatekeeper decisions)
- Security: `data/logs/security_violations.log` (AST check failures)
- LLM: `data/logs/thinking_process.log` (Qwen3 thinking chains)

**Validation:**
- AST-level: Static analysis in `ToolExecutor.static_check_with_rules()` (module/call/attribute whitelist)
- Runtime: Subprocess sandbox with 30s timeout and 512MB memory limit
- Contract: Output type and constraint validation in `MultiStageVerifier.verify_stage_contract()`
- Integration: Real data test against cached yfinance snapshots

**Authentication:**
- LLM API: Qwen3 via DashScope with API_KEY environment variable
- Data API: yfinance (no auth required, public data only)
- No user authentication (single-user CLI application)

**Checkpointing:**
- Gateway creates rollback checkpoints before each tool registration
- Checkpoint format: JSON files in `data/checkpoints/` with timestamp and context
- Checkpoint states: pending → complete/failed
- Recovery: Manual rollback via checkpoint files (automated recovery not yet implemented)

---

*Architecture analysis: 2026-02-06*
