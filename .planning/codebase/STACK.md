# Technology Stack

**Analysis Date:** 2026-01-31

## Languages

**Primary:**
- Python 3.9.6 - All core application logic, LLM integration, tool synthesis and execution

## Runtime

**Environment:**
- Python 3.9.6

**Package Manager:**
- pip (via virtual environment `.venv`)
- Lockfile: `requirements.txt` (explicit version pinning for reproducibility)

## Frameworks

**Core:**
- SQLModel 0.0.14 - ORM for database models and table definitions
- SQLAlchemy 2.0.0+ - Database engine and SQL operations

**LLM & API:**
- OpenAI SDK 1.0.0+ - OpenAI-compatible client for Qwen3 API integration via DashScope

**Data Processing:**
- pandas 2.0.0+ - DataFrame operations and data transformation
- numpy 1.24.0+ - Numerical computations for financial indicators
- pyarrow 14.0.0+ - Parquet file I/O for data caching

**Finance Data:**
- yfinance 0.2.30+ - Yahoo Finance API wrapper for stock, index, and ETF data

**CLI & Output:**
- tabulate - Formatted table output for CLI commands

## Key Dependencies

**Critical:**
- sqlmodel 0.0.14 - Defines 5 core tables: ToolArtifact, ExecutionTrace, ErrorReport, ToolPatch, BatchMergeRecord
- openai 1.0.0+ - Enables Qwen3 API communication for tool code generation and refinement
- yfinance 0.2.30+ - Provides bootstrap tools for stock/index/ETF data retrieval
- pandas 2.0.0+ - Required for all data manipulation in tools and evaluation
- pyarrow 14.0.0+ - Enables Parquet-based caching for reproducible data replay

**Infrastructure:**
- sqlalchemy 2.0.0+ - Database abstraction layer for SQLite operations

## Configuration

**Environment:**
- `.env` file for API credentials (read at startup in `src/config.py`)
- Key configuration in `src/config.py` (hardcoded paths, LLM settings, execution limits)

**Environment Variables:**
- `API_KEY` - Qwen3 API key for DashScope (optional; uses mock LLM if not provided)

**Build:**
- No build system required (pure Python, no compilation)
- Virtual environment management via standard Python venv

## Platform Requirements

**Development:**
- macOS 10.15+ / Linux / Windows (tested on macOS 12.6)
- Python 3.9.6+
- ~500MB disk space (code + cache)

**Production:**
- Any platform with Python 3.9+
- SQLite3 (bundled with Python)
- 512MB memory minimum (EXECUTION_MEMORY_MB = 512)

## Database

**Type:** SQLite
- Location: `data/db/evolution.db`
- URL: `sqlite:///data/db/evolution.db`

**Tables (5 core models):**
1. `tool_artifacts` - Tool metadata, code content, version, permissions
2. `execution_traces` - Execution history, I/O snapshots, timing, LLM config
3. `error_reports` - Error analysis from LLM (error_type, root_cause)
4. `tool_patches` - Repair records (patch diffs, rationale, resulting tool)
5. `batch_merge_records` - Tool consolidation (source tools, merge strategy)

## Execution Environment

**Sandbox:**
- Subprocess isolation via Python's `subprocess` module
- Timeout: 30 seconds (`EXECUTION_TIMEOUT_SEC = 30`)
- Memory: 512MB limit (`EXECUTION_MEMORY_MB = 512`)
- Security: AST static analysis before execution

**Storage:**
- Code artifacts: `data/artifacts/{bootstrap|generated}/*.py`
- Data cache: `data/cache/{md5_hash}.parquet` (Parquet format)
- Logs: `data/logs/` (thinking process traces from LLM)

---

*Stack analysis: 2026-01-31*
