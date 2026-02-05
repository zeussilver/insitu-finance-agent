# Technology Stack

**Analysis Date:** 2026-02-05

## Languages

**Primary:**
- Python 3.13.11 - Core application runtime, all modules and scripts

**Secondary:**
- SQL - Database queries and schema management (via SQLModel/SQLAlchemy)
- YAML - Configuration files (`configs/constraints.yaml`, `benchmarks/config_matrix.yaml`)

## Runtime

**Environment:**
- Python 3.13.11 (CPython)

**Package Manager:**
- pip (standard Python package manager)
- Lockfile: `fin_evo_agent/requirements.txt` (present)
- Virtual environment: `.venv` directory (recommended via `python -m venv`)

## Frameworks

**Core:**
- SQLModel 0.0.14 - Database ORM combining SQLAlchemy + Pydantic
- pandas >=2.0.0 - Data manipulation and financial data processing
- numpy >=1.24.0 - Numerical computations for financial indicators

**Testing:**
- pytest (inferred from `.pytest_cache` directory) - Unit and integration testing
- Test suite: `tests/` directory with 102+ tests

**Build/Dev:**
- pyarrow >=14.0.0 - Parquet file format for data caching
- tabulate - CLI table formatting
- PyYAML >=6.0 - YAML configuration parsing

## Key Dependencies

**Critical:**
- yfinance >=0.2.30 - Financial market data fetching (Yahoo Finance API wrapper)
  - Used for: Historical OHLCV data, stock info, market quotes
  - Caching strategy: Parquet snapshots with MD5 hashing
- openai >=1.0.0 - LLM client SDK (OpenAI-compatible interface)
  - Used for: Qwen3 model access via DashScope API
  - Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- sqlalchemy >=2.0.0 - SQL toolkit and ORM foundation
  - Database: SQLite (`data/db/evolution.db`)
  - Tables: 5 core tables (tool_artifacts, execution_traces, error_reports, tool_patches, batch_merge_records)

**Infrastructure:**
- pyarrow >=14.0.0 - Parquet serialization for reproducible data caching
- hashlib (stdlib) - MD5 hashing for cache keys and tool content hashing
- subprocess (stdlib) - Sandboxed code execution with 30s timeout
- ast (stdlib) - Abstract syntax tree analysis for security validation

## Configuration

**Environment:**
- Configuration method: `.env` file in `fin_evo_agent/` directory
- Required variables:
  - `API_KEY` - Qwen3 API key from DashScope (optional, falls back to mock LLM)
- Config loader: Custom parser in `src/config.py` (lines 10-18)

**Runtime Constraints:**
- Primary config: `configs/constraints.yaml` - Centralized runtime constraints
  - Execution limits: 30s timeout, 512MB memory, 3 retries
  - Capability-based module allowlists (calculation, fetch, composite)
  - Security blocklists (banned modules, calls, attributes)

**Build:**
- No build step required (interpreted Python)
- Configuration files:
  - `configs/constraints.yaml` - Runtime constraints and security rules
  - `benchmarks/config_matrix.yaml` - Benchmark execution configuration
  - `.github/workflows/benchmark.yml` - CI/CD pipeline definition

## Platform Requirements

**Development:**
- Python 3.11+ (tested with 3.13.11)
- Virtual environment recommended (`.venv` via `python -m venv`)
- Storage: SQLite database + file system (artifacts in `data/artifacts/`)
- Network: Required for yfinance data fetching (first run), cached thereafter

**Production:**
- Deployment target: Not specified (appears to be research prototype)
- CI/CD: GitHub Actions (`/.github/workflows/benchmark.yml`)
  - Runs on: `ubuntu-latest`
  - Python version: 3.11 (specified in workflow)
  - Caching: yfinance data cached between runs
  - Timeout: 30 minutes per benchmark run

---

*Stack analysis: 2026-02-05*
