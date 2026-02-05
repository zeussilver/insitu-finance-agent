# External Integrations

**Analysis Date:** 2026-02-05

## APIs & External Services

**LLM Services:**
- Qwen3 (Alibaba Cloud DashScope) - Code generation and error analysis
  - SDK/Client: `openai` package (OpenAI-compatible API)
  - Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - Model: `qwen3-max` (configurable in `src/config.py:38`)
  - Auth: `API_KEY` environment variable
  - Features: Thinking mode enabled (`extra_body={"enable_thinking": True}`)
  - Timeout: 180 seconds
  - Fallback: Mock LLM responses when `API_KEY` not set (`src/core/llm_adapter.py:491-637`)

**Financial Data:**
- Yahoo Finance (via yfinance) - Market data provider
  - SDK/Client: `yfinance >=0.2.30`
  - Auth: None required (public API)
  - Data types: Stock OHLCV, financial info, market quotes, index data, ETF data
  - Retry mechanism: 3 attempts with exponential backoff (1-10s delays)
  - Implementation: `src/finance/data_proxy.py` and `src/data/adapters/yfinance_adapter.py`

## Data Storage

**Databases:**
- SQLite
  - Connection: `sqlite:///data/db/evolution.db` (file-based)
  - Client: SQLModel 0.0.14 (SQLAlchemy 2.0+ backend)
  - Schema: 5 tables
    - `tool_artifacts` - Tool metadata (name, version, hash, code_content, capabilities, verification_stage)
    - `execution_traces` - Execution history (inputs, outputs, errors, timing)
    - `error_reports` - LLM-analyzed error root causes
    - `tool_patches` - Error-to-fix repair records
    - `batch_merge_records` - Tool consolidation records
  - Initialization: `src/core/models.py:201-208` (`init_db()`)

**File Storage:**
- Local filesystem
  - Tool artifacts: `data/artifacts/` (bootstrap/, generated/)
  - Data cache: `data/cache/` (.parquet files, gitignored)
  - Logs: `data/logs/` (gateway.log, security_violations.log, gateway_attempts.jsonl)
  - Checkpoints: `data/checkpoints/` (rollback points before tool registration)

**Caching:**
- Parquet-based reproducible caching
  - Strategy: MD5(function_name + args + kwargs) as cache key
  - Format: `.parquet` files in `data/cache/`
  - Behavior: First call fetches from network, subsequent calls replay from cache
  - Implementation: `@DataProvider.reproducible` decorator in `src/finance/data_proxy.py:113-138`
  - Adapters: `src/data/adapters/yfinance_adapter.py` (production), `src/data/adapters/mock_adapter.py` (testing)

## Authentication & Identity

**Auth Provider:**
- None (no user authentication)
  - System operates as single-user research prototype
  - API key for LLM access stored in `.env` file

## Monitoring & Observability

**Error Tracking:**
- Custom logging system
  - Security violations: `data/logs/security_violations.log`
  - Gateway attempts: `data/logs/gateway_attempts.jsonl` (structured JSON Lines)
  - Gateway general log: `data/logs/gateway.log`
  - Database records: `error_reports` and `tool_patches` tables

**Logs:**
- File-based logging
  - Location: `data/logs/` directory
  - Thinking traces: Captured in execution flow (LLM `<think>...</think>` blocks)
  - Execution traces: Stored in `execution_traces` table with stdout/stderr snapshots

## CI/CD & Deployment

**Hosting:**
- Not deployed (local development/research environment)

**CI Pipeline:**
- GitHub Actions
  - Workflow: `.github/workflows/benchmark.yml`
  - Triggers: Pull requests to main branch, manual dispatch
  - Environment: Ubuntu Latest, Python 3.11
  - Secrets: `API_KEY` (Qwen3 DashScope API key)
  - Artifacts: Benchmark results JSON, security violation logs (30-day retention)
  - Caching: yfinance data, pip dependencies
  - Gates: Fails on regressions, warns on <80% pass rate
  - PR comments: Posts benchmark results to pull requests

## Environment Configuration

**Required env vars:**
- `API_KEY` - Qwen3 DashScope API key (optional, mock LLM used if absent)

**Secrets location:**
- Development: `.env` file in `fin_evo_agent/` directory (gitignored)
- CI/CD: GitHub Actions secrets (`secrets.API_KEY`)

**Config hierarchy:**
1. `fin_evo_agent/.env` - Environment variables (API keys)
2. `fin_evo_agent/src/config.py` - Global configuration constants
3. `fin_evo_agent/configs/constraints.yaml` - Runtime constraints and security rules
4. `fin_evo_agent/benchmarks/config_matrix.yaml` - Benchmark execution settings

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## Network Resilience

**Retry Strategy:**
- Decorator: `@with_retry` in `src/finance/data_proxy.py:54-95`
- Parameters:
  - Max attempts: 3
  - Base delay: 1.0 seconds
  - Max delay: 10.0 seconds
  - Backoff factor: 2.0 (exponential)
- Applied to: All yfinance data fetching operations
- Logging: Console output on retry attempts

**Sandbox Execution:**
- Method: Subprocess isolation
- Implementation: `src/core/executor.py` (AST security check + subprocess execution)
- Limits:
  - Timeout: 30 seconds (configurable via `configs/constraints.yaml`)
  - Memory: 512MB
  - No network access for generated calculation/composite tools
  - Network allowed only for fetch-category tools with yfinance

---

*Integration audit: 2026-02-05*
