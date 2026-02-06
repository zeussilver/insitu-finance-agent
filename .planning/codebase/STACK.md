# Technology Stack

**Analysis Date:** 2026-02-06

## Languages

**Primary:**
- Python 3.9.6 - All application code, financial tools, evolution system

## Runtime

**Environment:**
- Python 3.9.6

**Package Manager:**
- pip (Python package manager)
- Lockfile: `fin_evo_agent/requirements.txt` with pinned versions

## Frameworks

**Core:**
- SQLModel 0.0.14 - ORM for tool metadata storage
- SQLAlchemy >=2.0.0 - Database engine underneath SQLModel
- pandas >=2.0.0 - Data manipulation for financial calculations
- numpy >=1.24.0 - Numerical computations

**Testing:**
- pytest - Unit testing framework (referenced in `tests/` directory and CI workflows)

**Build/Dev:**
- venv - Virtual environment isolation (`.venv/` directory)
- GitHub Actions - CI/CD pipeline (`.github/workflows/benchmark.yml`)

## Key Dependencies

**Critical:**
- `yfinance` >=0.2.30 - Financial data fetching from Yahoo Finance API
- `openai` >=1.0.0 - LLM SDK for Qwen3 via DashScope OpenAI-compatible API
- `sqlmodel` 0.0.14 - Data persistence layer for tool artifacts and execution traces

**Infrastructure:**
- `pyarrow` >=14.0.0 - Parquet serialization for reproducible data caching
- `PyYAML` >=6.0 - Configuration file parsing (`configs/constraints.yaml`, `benchmarks/config_matrix.yaml`)
- `tabulate` - CLI table formatting for tool listings and benchmarks

## Configuration

**Environment:**
- Environment variables loaded from `fin_evo_agent/.env` (file present but not read per security policy)
- Key environment variable: `API_KEY` for Qwen3 LLM access via DashScope
- Fallback: Mock LLM responses if `API_KEY` not set
- Configuration centralized in `fin_evo_agent/src/config.py`

**Build:**
- `fin_evo_agent/requirements.txt` - Locked dependency versions
- `fin_evo_agent/configs/constraints.yaml` - Centralized runtime constraints
- `fin_evo_agent/benchmarks/config_matrix.yaml` - Benchmark configuration matrix
- `.github/workflows/benchmark.yml` - CI pipeline configuration

## Platform Requirements

**Development:**
- Python 3.9+ (tested with 3.9.6, CI uses 3.11)
- Virtual environment recommended: `python -m venv .venv`
- Installation: `pip install -r fin_evo_agent/requirements.txt`
- Optional: DashScope API key for LLM functionality

**Production:**
- GitHub Actions (ubuntu-latest runners)
- Deployment target: SQLite file-based database, local filesystem for generated tools
- No external hosting - self-contained system

---

*Stack analysis: 2026-02-06*
