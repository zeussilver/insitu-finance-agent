# Yunjue Agent Documentation

This is the documentation table of contents for the Yunjue Agent project - a fully reproducible, zero-start in-situ self-evolving financial agent system.

---

## Getting Started

- [Quick Start](../README.md#quick-start) - Get up and running in minutes
- [Environment Setup](../CLAUDE.md#environment-setup) - Virtual environment and dependencies

---

## Technical Reference

- [CLAUDE.md](../CLAUDE.md) - The authoritative technical guide
  - Architecture overview and core principles
  - Security model (capability-based AST analysis, sandbox execution)
  - CLI commands reference
  - Project file structure
  - Data models (5 SQLModel tables)
  - Tool evolution loop
  - Contract system

---

## Development

- [PROJECT.md](../.planning/PROJECT.md) - Project overview and goals
- [STATE.md](../.planning/STATE.md) - Current state tracking and progress
- [phases/](../.planning/phases/) - Development history and phase documentation

---

## Benchmarks

The evaluation suite consists of 20 benchmark tasks across 3 categories:

| Category | Tasks | Description |
|----------|-------|-------------|
| Fetch & Lookup | 8 | Data retrieval and field extraction |
| Calculation | 8 | Technical indicators (RSI, MACD, Bollinger, etc.) |
| Composite | 4 | Multi-tool composition |

- [tasks.jsonl](../benchmarks/tasks.jsonl) - Full benchmark task definitions with contract IDs

**Current Status**: 85% pass rate achieved (17/20 tasks passing) - Target of 80% met.

---

## Archive

- [Archive README](archive/README.md) - Historical documentation index

Contains documentation from the pre-yfinance era, preserved for reference.
