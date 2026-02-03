# Technology Stack

**Analysis Date:** 2026-02-03

## Languages

**Primary:**
- Python 3.9+ - All application code, generated tools, bootstrapping, evaluation

**Secondary:**
- None

## Runtime

**Environment:**
- Python 3.13.11 (local development)
- Python 3.9+ minimum required

**Package Manager:**
- pip (Python package installer)
- Lockfile: `fin_evo_agent/requirements.txt` (13 lines, locked versions)

## Frameworks

**Core:**
- SQLModel 0.0.14 - ORM for database models (5 tables)
- SQLAlchemy >=2.0.0 - Database engine (SQLite)
- pandas >=2.0.0 - Data manipulation for financial calculations
- numpy >=1.24.0 - Numerical computations

**Testing:**
- Built-in assert statements in generated tool code
- Custom evaluation framework in `fin_evo_agent/benchmarks/run_eval.py`
- No external test runner (pytest, unittest)

**Build/Dev:**
- venv - Virtual environment isolation (`fin_evo_agent/.venv/`)
- No build tools (pure Python, no compilation)

## Key Dependencies

**Critical:**
- yfinance >=0.2.30 - Financial data fetching (Yahoo Finance API)
- openai >=1.0.0 - LLM SDK for Qwen3 API (OpenAI-compatible interface)
- pyarrow >=14.0.0 - Parquet serialization for data caching

**Infrastructure:**
- tabulate - CLI output formatting

## Configuration

**Environment:**
- Environment variables loaded from `fin_evo_agent/.env`
- Key variable: `API_KEY` - Qwen3 API key via DashScope
- Config module: `fin_evo_agent/src/config.py`

**Build:**
- No build configuration (interpreted Python)
- Virtual environment managed via `python -m venv .venv`

## Platform Requirements

**Development:**
- Python 3.9+ runtime
- Virtual environment: `fin_evo_agent/.venv/`
- SQLite 3.x (included with Python)
- Network access for yfinance API (first run only)
- DashScope API access (optional - falls back to mock LLM)

**Production:**
- Deployment target: Local/self-hosted
- No containerization detected (Docker, Kubernetes)
- No cloud platform dependencies
- Designed for reproducibility: Parquet cache enables offline execution

---

*Stack analysis: 2026-02-03*
