# External Integrations

**Analysis Date:** 2026-02-06

## APIs & External Services

**LLM Service:**
- Qwen3-Max (Alibaba DashScope) - Code generation and error analysis
  - SDK/Client: `openai` package (OpenAI-compatible API)
  - Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - Model: `qwen3-max-2026-01-23`
  - Auth: `API_KEY` environment variable
  - Features: Thinking mode enabled (`extra_body={"enable_thinking": True}`)
  - Timeout: 180 seconds (configurable via `LLM_TIMEOUT` env var)
  - Implementation: `fin_evo_agent/src/core/llm_adapter.py`

**Financial Data:**
- Yahoo Finance (yfinance) - Historical stock data, OHLCV, financial statements
  - SDK/Client: `yfinance` package
  - Auth: None (public API)
  - Caching: Record-replay with Parquet snapshots (`fin_evo_agent/data/cache/`)
  - Retry: Exponential backoff (3 attempts, 1-10s delay)
  - Implementation: `fin_evo_agent/src/finance/data_proxy.py`, `fin_evo_agent/src/data/adapters/yfinance_adapter.py`

## Data Storage

**Databases:**
- SQLite
  - Connection: `sqlite:///fin_evo_agent/data/db/evolution.db`
  - Client: SQLModel/SQLAlchemy
  - Tables: `tool_artifacts`, `execution_traces`, `error_reports`, `tool_patches`, `batch_merge_records`
  - Configuration: `fin_evo_agent/src/config.py` (`DB_URL`, `DB_PATH`)

**File Storage:**
- Local filesystem
  - Generated tools: `fin_evo_agent/data/artifacts/generated/` (Python files with naming: `{tool_name}_v{version}_{hash8}.py`)
  - Bootstrap tools: `fin_evo_agent/data/artifacts/bootstrap/` (initial yfinance wrappers)
  - Data cache: `fin_evo_agent/data/cache/` (Parquet files, Git ignored)
  - Logs: `fin_evo_agent/data/logs/` (security violations, gateway attempts, evolution gates)
  - Checkpoints: `fin_evo_agent/data/checkpoints/` (rollback points for verification gateway)

**Caching:**
- Parquet-based record-replay for yfinance API calls
  - Cache key: MD5(function_name + args + kwargs)
  - Storage: `fin_evo_agent/data/cache/{key}.parquet`
  - First call: Fetch from network, save to cache
  - Subsequent calls: Read from cache (no network)

## Authentication & Identity

**Auth Provider:**
- Custom environment variable
  - Implementation: Manual `.env` file loading in `fin_evo_agent/src/config.py`
  - Required variable: `API_KEY` for DashScope LLM access
  - Optional variable: `LLM_TIMEOUT` for timeout override

## Monitoring & Observability

**Error Tracking:**
- Custom error logging system
  - Security violations: `fin_evo_agent/data/logs/security_violations.log`
  - Gateway attempts: `fin_evo_agent/data/logs/gateway_attempts.jsonl` (structured JSONL)
  - Evolution gates: `fin_evo_agent/data/logs/evolution_gates.log`
  - Implementation: `fin_evo_agent/src/core/gateway.py`, `fin_evo_agent/src/core/gates.py`

**Logs:**
- File-based structured logging
  - LLM thinking process: `fin_evo_agent/data/logs/` (when `LLM_ENABLE_THINKING=True`)
  - Execution traces: Stored in SQLite `execution_traces` table
  - Error reports: Stored in SQLite `error_reports` table with LLM-analyzed root causes

## CI/CD & Deployment

**Hosting:**
- GitHub (source code repository)
  - Repo pattern: Git-based codebase with local SQLite database

**CI Pipeline:**
- GitHub Actions
  - Workflow: `.github/workflows/benchmark.yml`
  - Triggers: PR to main branch, manual dispatch
  - Secrets: `API_KEY` (repository secret for DashScope)
  - Artifacts: Benchmark results JSON, downloadable artifacts
  - Caching: yfinance data cache, pip dependencies
  - Timeout: 120 minutes per workflow
  - Python version: 3.11 (ubuntu-latest)

## Environment Configuration

**Required env vars:**
- `API_KEY` - DashScope API key for Qwen3 LLM access (optional, falls back to mock)

**Optional env vars:**
- `LLM_TIMEOUT` - Override default 180s timeout for LLM requests

**Secrets location:**
- Local development: `fin_evo_agent/.env` file (Git ignored)
- GitHub Actions: Repository secrets (Settings → Secrets and variables → Actions)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (yfinance and DashScope APIs use HTTP request-response pattern only)

---

*Integration audit: 2026-02-06*
