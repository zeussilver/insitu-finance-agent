# External Integrations

**Analysis Date:** 2026-01-31

## APIs & External Services

**LLM - Code Generation & Refinement:**
- Service: Qwen3 via DashScope (Alibaba Cloud)
- SDK/Client: `openai` package (OpenAI-compatible API)
- Endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Model: `qwen3-max` (or `qwen3-max-2026-01-23` with thinking mode)
- Auth: Environment variable `API_KEY`
- Implementation file: `src/core/llm_adapter.py`
- Features:
  - Protocol cleaning: Extracts `<think>...</think>` traces and ````python...```code blocks
  - Support for extended thinking via `extra_body={"enable_thinking": True}`
  - Fallback to mock LLM if API_KEY not set (for testing)
  - Timeout: 60 seconds per request

**Financial Data - Stock/Index/ETF:**
- Service: Yahoo Finance (via yfinance wrapper)
- SDK/Client: `yfinance` 0.2.30+
- Auth: None required (public API)
- Implementation file: `src/finance/data_proxy.py`
- Bootstrap tools: `src/finance/bootstrap.py`
- Features:
  - Record-Replay caching: First call fetches from network, subsequent calls read from cache
  - Supports: Stock OHLCV, index data, ETF data, financial statements, real-time quotes
  - Cache key: MD5 hash of (function_name + args + kwargs)
  - Cache storage: Parquet format in `data/cache/{md5}.parquet`

## Data Storage

**Databases:**
- SQLite (single file)
  - Location: `data/db/evolution.db`
  - Connection: `sqlite:///data/db/evolution.db` (via `src/config.DB_URL`)
  - Client: SQLModel (ORM) + SQLAlchemy (engine)

**File Storage:**
- Local filesystem only
  - Code artifacts: `data/artifacts/bootstrap/*.py` (5 bootstrap tools)
  - Code artifacts: `data/artifacts/generated/*.py` (evolved tools, named `{tool_name}_v{version}_{hash8}.py`)
  - Data cache: `data/cache/{md5_hash}.parquet` (frozen AkShare snapshots)
  - Logs: `data/logs/` (thinking process JSON from LLM)

**Caching:**
- Parquet-based record-replay mechanism (reproducibility)
  - All DataFrame columns converted to string for Parquet compatibility
  - Cache hit check: File existence before network call
  - Cache miss: Network fetch → convert to string → save to Parquet

## Authentication & Identity

**Auth Provider:**
- Custom (LLM token-based)
- Implementation: Direct environment variable (`API_KEY`) → OpenAI client initialization
  - If no API_KEY: Mock LLM responses for testing
  - Location: `src/core/llm_adapter.py` (LLMAdapter.__init__)

## Monitoring & Observability

**Error Tracking:**
- None (application-level only)
- Error details stored in SQLite tables:
  - `error_reports` table: error_type, root_cause (from LLM analysis)
  - `execution_traces` table: std_err, std_out, exit_code
  - Location: `src/core/models.py` (ErrorReport, ExecutionTrace)

**Logs:**
- Application logs: stdout/stderr (no dedicated logging framework)
- Thinking process logs: JSON output from LLM stored in `data/logs/`
- CLI output: Formatted via `tabulate` package
- Location for capture: `src/evolution/synthesizer.py`, `src/evolution/refiner.py`

## CI/CD & Deployment

**Hosting:**
- Local development or any Python 3.9+ environment (no cloud deployment in current phase)
- Target platforms: macOS, Linux, Windows

**CI Pipeline:**
- None (Phase 1a MVP, no automated CI configured)

**Evaluation:**
- Manual evaluation via `benchmarks/run_eval.py`
- Benchmark tasks: 20 tasks in `benchmarks/tasks.jsonl` (fetch, calc, composite)
- Security tasks: 5 tasks in `benchmarks/security_tasks.jsonl`

## Environment Configuration

**Required env vars:**
- `API_KEY` - Qwen3 DashScope API key (optional; uses mock if not provided)

**Optional configs:**
- None (all other configs hardcoded in `src/config.py`)

**Secrets location:**
- `.env` file in project root (`fin_evo_agent/.env`)
- WARNING: API key currently committed in `.env` (should use proper secrets management in production)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Data Flow - Record-Replay Cache

**Mechanism: `@DataProvider.reproducible` decorator** (located in `src/finance/data_proxy.py`)

1. **Cache Key Generation:**
   - Inputs: function name, args tuple, kwargs dict
   - Process: JSON serialize → MD5 hash
   - Output: `{cache_dir}/{hash}.parquet`

2. **Replay Mode (Cache Hit):**
   - Check if cache file exists
   - If yes: Return `pd.read_parquet(cache_path)` (no network)
   - Used for: Reproducibility and speed on subsequent runs

3. **Record Mode (Cache Miss):**
   - Call underlying function (e.g., yfinance.download)
   - Convert all columns to string (Parquet compatibility)
   - Save to cache as Parquet
   - Return DataFrame

4. **Bootstrap Tools Using Cache:**
   - `get_stock_hist()` - Historical stock OHLCV
   - `get_financial_info()` - Financial statements
   - `get_realtime_quote()` - Current market quotes
   - `get_index_daily()` - Index historical data
   - `get_etf_hist()` - ETF historical data

## Tool Artifact Storage

**File Naming Convention:**
- Format: `data/artifacts/generated/{tool_name}_v{semantic_version}_{content_hash8}.py`
- Example: `calc_rsi_v0.1.0_f42711fb.py`

**Metadata Storage:**
- Database: `tool_artifacts` table in SQLite
  - Fields: name, semantic_version, file_path, content_hash, code_content, args_schema, permissions, status
  - Hash: MD5 of code content (ensures uniqueness)
  - Status: provisional, verified, deprecated, failed

---

*Integration audit: 2026-01-31*
