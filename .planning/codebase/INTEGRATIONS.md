# External Integrations

**Analysis Date:** 2026-02-03

## APIs & External Services

**Financial Data:**
- yfinance (Yahoo Finance) - Stock/ETF/index historical data
  - SDK/Client: `yfinance >=0.2.30`
  - Auth: None required (public API)
  - Usage: `fin_evo_agent/src/finance/data_proxy.py`
  - Caching: Parquet snapshots in `fin_evo_agent/data/cache/` (MD5-keyed)
  - Retry: 3 attempts with exponential backoff (1-10s delay)

**LLM Provider:**
- Qwen3 via DashScope - Tool code generation, error analysis
  - SDK/Client: `openai >=1.0.0` (OpenAI-compatible API)
  - Auth: `API_KEY` environment variable
  - Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - Model: `qwen3-max-2026-01-23`
  - Thinking mode: Enabled via `extra_body={"enable_thinking": True}`
  - Fallback: Mock LLM responses if no API key
  - Usage: `fin_evo_agent/src/core/llm_adapter.py`

## Data Storage

**Databases:**
- SQLite
  - Connection: `sqlite:///fin_evo_agent/data/db/evolution.db`
  - Client: SQLModel 0.0.14 (SQLAlchemy 2.0+ backend)
  - Tables: `tool_artifacts`, `execution_traces`, `error_reports`, `tool_patches`, `batch_merge_records`
  - Schema: `fin_evo_agent/src/core/models.py`

**File Storage:**
- Local filesystem only
  - Artifacts: `fin_evo_agent/data/artifacts/generated/*.py` - Generated tool code
  - Bootstrap: `fin_evo_agent/data/artifacts/bootstrap/*.py` - Initial yfinance tools
  - Cache: `fin_evo_agent/data/cache/*.parquet` - Parquet snapshots (Git ignored)
  - Logs: `fin_evo_agent/data/logs/` - Thinking traces, security violations

**Caching:**
- Custom Parquet-based caching (`@DataProvider.reproducible` decorator)
  - Key: MD5(function_name + args + kwargs)
  - Storage: `fin_evo_agent/data/cache/{hash}.parquet`
  - Implementation: `fin_evo_agent/src/finance/data_proxy.py`

## Authentication & Identity

**Auth Provider:**
- None (no user authentication)
  - Single-user system
  - API key stored in `.env` file

## Monitoring & Observability

**Error Tracking:**
- Custom logging to files
  - Security violations: `fin_evo_agent/data/logs/security_violations.log`
  - LLM thinking: `fin_evo_agent/data/logs/thinking_process/`
  - ExecutionTrace model stores errors in SQLite

**Logs:**
- File-based logging (no external service)
- ANSI-colored terminal output for evaluation runs
- No structured logging framework (Sentry, Datadog)

## CI/CD & Deployment

**Hosting:**
- Local development/execution only
  - No deployment infrastructure detected

**CI Pipeline:**
- GitHub repository detected (`.git/`, `.github/`)
  - No workflow files observed in exploration
  - Manual evaluation via `python benchmarks/run_eval.py`

## Environment Configuration

**Required env vars:**
- `API_KEY` - Qwen3 API key (DashScope)

**Optional env vars:**
- None detected

**Secrets location:**
- `.env` file in `fin_evo_agent/.env`
- ⚠️ WARNING: `.env` file contains plaintext API key (should not be committed)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Security Mechanisms

**Sandbox Execution:**
- subprocess isolation with 30s timeout
  - Implementation: `fin_evo_agent/src/core/executor.py`
  - Method: `subprocess.run()` with timeout
  - Memory limit: 512MB (configured, not enforced)

**AST Security Analysis:**
- Capability-based module whitelisting
  - Capability definitions: `fin_evo_agent/src/core/capabilities.py`
  - Always banned modules: `os`, `sys`, `subprocess`, `shutil`, `socket`, `pickle`
  - Always banned calls: `eval`, `exec`, `compile`, `__import__`
  - Category-specific rules:
    - `fetch` tools: Can import yfinance, hashlib, pathlib
    - `calculation` tools: Cannot import yfinance (blocked)
    - `composite` tools: Calculation capabilities only

**Network Isolation:**
- yfinance access only (no raw HTTP/socket libraries)
- Retry decorator handles network failures transparently

---

*Integration audit: 2026-02-03*
