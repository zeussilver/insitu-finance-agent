# Yunjue Agent

**A fully reproducible, zero-start in-situ self-evolving financial agent system.**

This project reproduces the core tool evolution loop from the paper "Yunjue Agent: A Fully Reproducible, Zero-Start In-Situ Self-Evolving Agent System" (Li et al., 2026).

## Current Status

| Metric | Value | Target |
|--------|-------|--------|
| Pass Rate | **85% (17/20)** | 80% MET |
| Data Source | yfinance (US stocks) | - |
| Security Block Rate | **100%** | 100% |

## Quick Start

```bash
cd fin_evo_agent
source .venv/bin/activate
python main.py --init
python main.py --task "计算 RSI"
python main.py --list
```

## Core Principles

| Principle | Implementation |
|-----------|----------------|
| Auditable | All generated code as `.py` files in `data/artifacts/`, Git trackable |
| Reproducible | Frozen yfinance data via Parquet snapshots |
| Secure | Capability-based AST analysis + subprocess sandboxing |

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Technical reference (for AI assistants) |
| [docs/index.md](docs/index.md) | Documentation hub |
| [docs/archive/](docs/archive/) | Historical documentation |

## Benchmark Results

**Overall: 85% (17/20)**

| Category | Pass Rate | Details |
|----------|-----------|---------|
| Fetch | 75% | 6/8 |
| Calculation | 88% | 7/8 |
| Composite | **100%** | 4/4 |

## License

See LICENSE file for details.
