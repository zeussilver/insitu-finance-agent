# Architecture

**Analysis Date:** 2026-01-31

## Pattern Overview

**Overall:** Tool Evolution Loop with Secure Sandbox Execution

**Key Characteristics:**
- **Metadata in DB, Payload on Disk** - SQLite stores tool metadata; actual code stored as .py files on disk
- **Generate → Verify → Register → Refine** - Self-evolving tool pipeline with LLM feedback loop
- **AST Static Analysis + Subprocess Sandboxing** - Two-layer security preventing dangerous operations before execution
- **Record-Replay Caching** - Frozen data snapshots for reproducible analysis
- **JSON-IPC for Sandbox Communication** - Subprocess isolation avoids eval() and string interpolation exploits

## Layers

**LLM Layer:**
- Purpose: Generate tool code from natural language task descriptions
- Location: `src/core/llm_adapter.py`
- Contains: Qwen3-Max API client, protocol cleaning (extract thinking traces and code payloads), system prompts for tool generation
- Depends on: OpenAI client library, configuration from `src/config.py`
- Used by: `src/evolution/synthesizer.py`, `src/evolution/refiner.py`

**Security Layer:**
- Purpose: Prevent execution of dangerous code through static and runtime checks
- Location: `src/core/executor.py`
- Contains: AST static analysis (banned imports, functions, magic attributes), subprocess sandbox with timeout/memory limits
- Depends on: Python's ast module, subprocess module
- Used by: `src/evolution/synthesizer.py`, `src/evolution/refiner.py`, `main.py` (CLI security verification)

**Registry Layer:**
- Purpose: Manage tool lifecycle - storage, retrieval, versioning, deduplication
- Location: `src/core/registry.py`
- Contains: Tool registration, content-hash based deduplication, version tracking, file path generation
- Depends on: SQLModel ORM, `src/core/models.py`
- Used by: `src/evolution/synthesizer.py`, `src/evolution/refiner.py`, `main.py`

**Evolution Layer:**
- Purpose: Implement the synthesis and refinement loops for tool generation
- Location: `src/evolution/synthesizer.py`, `src/evolution/refiner.py`
- Contains:
  - Synthesizer: LLM generation → AST check → sandbox test → registration
  - Refiner: Error classification → LLM patch generation → re-verification (max 3 attempts)
- Depends on: LLMAdapter, ToolExecutor, ToolRegistry
- Used by: `main.py` task command

**Finance Layer:**
- Purpose: Provide financial data access and bootstrap tools
- Location: `src/finance/data_proxy.py`, `src/finance/bootstrap.py`
- Contains:
  - DataProvider: yfinance wrapper with MD5-keyed Parquet caching
  - Bootstrap tools: 5 initial tools (stock history, financial info, real-time quotes, index data, ETF data)
- Depends on: yfinance, pandas
- Used by: Bootstrap initialization, task data preparation in `main.py`

**Data Model Layer:**
- Purpose: Define SQLModel schemas for persistent tool artifact tracking
- Location: `src/core/models.py`
- Contains: 5 tables (ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord)
- Depends on: SQLModel, SQLAlchemy
- Used by: Registry, Executor, Synthesizer, Refiner

**CLI Layer:**
- Purpose: Entry point for user interactions
- Location: `main.py`
- Contains: Command handlers (init, bootstrap, task, list, security-check)
- Depends on: All above layers
- Used by: End user via command line

## Data Flow

**Task Execution Flow (primary flow):**

1. User invokes `main.py --task "计算 RSI"`
2. Registry attempts lookup by inferred tool name (e.g., "calc_rsi")
3. If tool not found, Synthesizer generates:
   - LLMAdapter generates code via Qwen3-Max with thinking mode
   - Protocol cleaned (extract ```python...``` code block)
   - ToolExecutor static check (AST analysis)
   - ToolExecutor runs `if __name__ == '__main__':` tests in subprocess sandbox
   - If pass: Registry stores code file + metadata, returns ToolArtifact
   - If fail: Refiner attempts repair (up to 3 iterations)
4. ToolExecutor executes tool with provided arguments in sandbox
5. ExecutionTrace captures input/output/timing/errors
6. Result extracted and returned to user

**Tool Synthesis Loop (with refinement):**

```
Task Description
       ↓
LLMAdapter.generate_tool_code()
       ↓
ToolExecutor.static_check() [AST analysis]
       ↓
ToolExecutor.execute() [Sandbox with test block]
       ↓
    Pass?
    ↙   ↘
  Yes    No (exit_code ≠ 0)
  ↓      ↓
  ↓     Refiner.refine()
  ↓      ↓
  ↓     _classify_error() [regex patterns]
  ↓      ↓
  ↓     LLMAdapter.refine_tool_code() [with error context]
  ↓      ↓
  ↓     ErrorReport created
  ↓      ↓
  ↓     ToolExecutor.static_check() [new code]
  ↓      ↓
  ↓     ToolExecutor.execute() [re-test]
  ↓      ↓
  ↓     Max 3 attempts?
  ↓      ↓
  ↓     if max attempts: ToolArtifact.status = FAILED
  ↓      ↓
  └──────┘
        ↓
ToolRegistry.register()
        ↓
Code file written to data/artifacts/generated/{name}_v{ver}_{hash8}.py
Metadata inserted to tool_artifacts table
```

**Data Caching (Record-Replay):**

1. Task calls `get_a_share_hist("000001", "20230101", "20230201")`
2. DataProvider.reproducible decorator creates cache key: MD5(func_name + args + kwargs)
3. Cache hit: Read from `data/cache/{hash}.parquet`
4. Cache miss: Call yfinance, convert all columns to str, save to Parquet
5. Subsequent runs: Always read from cache (deterministic)

**State Management:**

- **Tool State**: Persisted in SQLite `tool_artifacts` table (status: PROVISIONAL, VERIFIED, DEPRECATED, FAILED)
- **Execution History**: Stored in `execution_traces` table for debugging and refinement context
- **Error Analysis**: `error_reports` table links trace errors to LLM-generated root cause analysis
- **Repair Records**: `tool_patches` table tracks error → patch → resulting_tool relationships
- **Tool Code**: Stored as .py files on disk, indexed by content hash (deduplication)
- **Cache Data**: Parquet snapshots in `data/cache/` for reproducible data access

## Key Abstractions

**ToolArtifact:**
- Purpose: Represents a registered tool (metadata + code content)
- Examples: `ToolArtifact(name="calc_rsi", semantic_version="0.1.0", code_content="...", status=PROVISIONAL)`
- Pattern: SQLModel table with denormalized code_content (convenience) and file_path pointer (separation of concerns)

**ExecutionTrace:**
- Purpose: Records a single tool execution (inputs, outputs, errors, timing)
- Examples: `ExecutionTrace(trace_id="task_calc_rsi_abc123", tool_id=5, input_args={...}, exit_code=0, std_out="RSI: 45.2")`
- Pattern: Foreign key to tool_artifacts, timestamped, includes full stderr for error analysis

**Security Abstraction (ToolExecutor):**
- Purpose: Enforce security guarantees without runtime overhead
- Pattern:
  - BANNED_MODULES = {os, sys, subprocess, ...} - strict allowlist approach
  - BANNED_CALLS = {eval, exec, compile, ...}
  - ALLOWED_MODULES = {pandas, numpy, math, ...}
  - Static check via AST walk before execution
  - Runtime: subprocess isolation with JSON file exchange (no eval)

**Tool Evolution Abstraction (Synthesizer + Refiner):**
- Purpose: Encapsulate the generate-verify-register-refine loop
- Pattern:
  - Synthesizer: Stateless generator, delegates to LLM → Executor → Registry
  - Refiner: Stateful error handler, analyzes execution traces and generates patches
  - Error classification via regex patterns (ERROR_PATTERNS dict)
  - Deterministic retry logic (max 3 attempts)

## Entry Points

**CLI Entry Point:**
- Location: `main.py`
- Triggers: `python main.py --task "..."`, `--init`, `--bootstrap`, `--list`, `--security-check`
- Responsibilities:
  - Initialize database and tables
  - Register bootstrap tools (5 initial yfinance tools)
  - Handle task execution with tool synthesis/retrieval
  - List registered tools
  - Verify security mechanisms

**Programmatic Entry Points:**
- `ToolRegistry.register()`: Register a new tool artifact
- `Synthesizer.synthesize()`: Generate and verify a tool from task description
- `Refiner.refine()`: Attempt to fix a failed tool via error analysis
- `ToolExecutor.execute()`: Run tool code in secure sandbox

## Error Handling

**Strategy:** Layered error detection with LLM-assisted analysis and automatic retry

**Patterns:**

1. **Security Errors** (ToolExecutor.static_check):
   - AST analysis finds banned imports/calls
   - Raises SecurityException (synthesis fails immediately)
   - No retry (security issues are fatal)

2. **Syntax Errors** (ToolExecutor.static_check):
   - ast.parse() fails
   - Synthesis fails with error message in ExecutionTrace.std_err
   - Refiner attempts patch based on SyntaxError message

3. **Execution Errors** (ToolExecutor.execute):
   - Subprocess exits with non-zero code
   - ExecutionTrace captures stderr
   - ErrorReport created with LLM-analyzed root_cause
   - Refiner.ERROR_PATTERNS classifies (TypeError, KeyError, etc.)
   - Refiner generates patched code and retries (max 3 attempts)

4. **Timeout Errors** (ToolExecutor.execute):
   - Subprocess exceeds EXECUTION_TIMEOUT_SEC (30s)
   - ExecutionTrace.exit_code = -9 (SIGKILL)
   - Treated as execution error, routed to Refiner

5. **LLM Errors** (LLMAdapter):
   - API timeout (60s per request)
   - Falls back to mock response if API_KEY not set
   - Result includes code_payload="" on failure
   - Synthesizer checks `if not result["code_payload"]:` and fails gracefully

## Cross-Cutting Concerns

**Logging:**
- Approach: Print statements to stdout (no structured logging framework)
- Patterns:
  - `print("[Step N] ...")` in main.py task flow
  - `print("[Synthesizer] ...")` in synthesizer.py
  - `print(f"[Network] Fetching {func_name}...")` in data_proxy.py
  - No log rotation or levels

**Validation:**
- Approach: Explicit checks in each component
- Patterns:
  - ToolExecutor.static_check(): Validate imports and function calls via AST
  - Refiner.ERROR_PATTERNS: Validate error classification via regex
  - ToolArtifact schema validation via SQLModel (type hints)
  - Input args validation in bootstrap tool templates

**Authentication:**
- Approach: API key from environment variable
- Patterns:
  - LLM: `API_KEY` env var → OpenAI client initialization
  - yfinance: No auth required (public market data)
  - Database: SQLite (file-based, no auth)

**Permissions Model:**
- Approach: Declarative permission list on ToolArtifact
- Patterns:
  - Permission enum: CALC_ONLY, NETWORK_READ, FILE_WRITE
  - Default: [CALC_ONLY] for all tools
  - Bootstrap tools marked: [NETWORK_READ, FILE_WRITE] for caching
  - Stored in permissions JSON field
  - Not currently enforced at runtime (Phase 1a)

---

*Architecture analysis: 2026-01-31*
