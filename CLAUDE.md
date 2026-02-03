# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Yunjue Agent** - A fully reproducible, zero-start in-situ self-evolving financial agent system.

This project reproduces the core tool evolution loop from the paper "Yunjue Agent: A Fully Reproducible, Zero-Start In-Situ Self-Evolving Agent System" (Li et al., 2026).

### Current Milestone

**Architecture Overhaul (Option C)** - Completed. Achieved **85% pass rate** (17/20) with capability-based, contract-validated architecture.

### Core Principles

| Principle | Implementation |
|-----------|----------------|
| Auditable | All generated code as `.py` files in `data/artifacts/`, Git trackable |
| Reproducible | Frozen yfinance data via Parquet snapshots; locked dependency versions |
| Secure | Capability-based AST analysis + subprocess sandboxing before code execution |

### Architecture

**"Metadata in DB, Payload on Disk"** - SQLite stores tool metadata, actual code files stored on disk.

**Capability-Based Verification** - Different tool categories have different allowed modules:
- `calculation`: pandas, numpy, datetime, json, math, decimal, collections, re, typing
- `fetch`: Same as calculation + yfinance, hashlib, pathlib
- `composite`: Same as calculation

**Multi-Stage Verification Pipeline**:
1. AST_SECURITY - Capability-specific import/call rules
2. SELF_TEST - Built-in assert tests pass
3. CONTRACT_VALID - Output matches contract constraints
4. INTEGRATION - Real data test (fetch tools only)

## Quick Start

```bash
# 1. Activate virtual environment
cd fin_evo_agent
source .venv/bin/activate

# 2. Initialize database
python main.py --init

# 3. Run a task (uses mock LLM if no API key)
python main.py --task "计算 RSI"

# 4. List registered tools
python main.py --list

# 5. Verify security mechanisms
python main.py --security-check
```

## Environment Setup

```bash
# Create and activate virtual environment
cd fin_evo_agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set Qwen3 API key (optional - uses mock LLM if not set)
export API_KEY=your_dashscope_api_key
```

## Qwen3 API Configuration

The LLM adapter uses Qwen3 via DashScope's OpenAI-compatible API:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    model="qwen3-max-2026-01-23",
    messages=[{'role': 'user', 'content': '...'}],
    extra_body={"enable_thinking": True}
)
```

- **Environment variable**: `API_KEY`
- **Model**: `qwen3-max-2026-01-23`
- **Thinking mode**: Enabled via `extra_body={"enable_thinking": True}`
- **Fallback**: If no API key, uses mock responses for testing

## Implementation Status

### Architecture Overhaul - COMPLETED ✅

| Component | File | Status |
|-----------|------|--------|
| Capability system | `src/core/capabilities.py` | ✅ NEW |
| Contract definitions | `src/core/contracts.py` | ✅ NEW |
| Multi-stage verifier | `src/core/verifier.py` | ✅ NEW |
| Category-specific prompts | `src/core/llm_adapter.py` | ✅ Updated |
| Capability-based AST check | `src/core/executor.py` | ✅ Updated |
| Verifier integration | `src/evolution/synthesizer.py` | ✅ Updated |
| Network retry | `src/finance/data_proxy.py` | ✅ Updated |
| Contract IDs in tasks | `benchmarks/tasks.jsonl` | ✅ Updated |

### Phase 1a MVP - COMPLETED ✅

| Component | File | Status |
|-----------|------|--------|
| Global config | `src/config.py` | ✅ |
| Data models (5 tables) | `src/core/models.py` | ✅ |
| yfinance caching | `src/finance/data_proxy.py` | ✅ |
| LLM adapter | `src/core/llm_adapter.py` | ✅ |
| AST security + sandbox | `src/core/executor.py` | ✅ |
| Tool registry | `src/core/registry.py` | ✅ |
| Tool synthesizer | `src/evolution/synthesizer.py` | ✅ |
| Tool refiner | `src/evolution/refiner.py` | ✅ |
| Bootstrap tools (yfinance) | `src/finance/bootstrap.py` | ✅ |
| Evaluation suite | `benchmarks/run_eval.py` | ✅ |
| Benchmark tasks | `benchmarks/tasks.jsonl` | ✅ |
| Run comparison | `benchmarks/compare_runs.py` | ✅ |
| CLI entry point | `main.py` | ✅ |

### Pending Implementation

| Component | File | Status |
|-----------|------|--------|
| Batch merger | `src/evolution/merger.py` | ⏳ Stub (Phase 1b) |

## Commands

```bash
# Initialize database (creates 5 SQLModel tables)
python main.py --init

# Run a task (synthesize + verify + execute)
python main.py --task "计算 RSI"

# List registered tools
python main.py --list

# Verify security mechanisms
python main.py --security-check

# Run evaluation suite
python benchmarks/run_eval.py --agent evolving --run-id run1

# Run with fresh registry (clear all tools first)
python benchmarks/run_eval.py --clear-registry --run-id fresh_run

# Run security-only evaluation
python benchmarks/run_eval.py --security-only

# Compare two evaluation runs
python benchmarks/compare_runs.py run1 run2

# Test individual components
python src/core/capabilities.py    # Capability system
python src/core/contracts.py       # Contract definitions
python src/core/verifier.py        # Multi-stage verifier
python src/core/executor.py        # AST security check
python src/core/task_executor.py   # Task execution
```

## Project Structure

```
fin_evo_agent/
├── .venv/                    # Virtual environment
├── requirements.txt          # Locked dependencies
├── main.py                   # CLI entry point
├── data/
│   ├── db/evolution.db       # SQLite database
│   ├── artifacts/
│   │   ├── bootstrap/        # Initial yfinance tools
│   │   └── generated/        # Evolved tools (e.g., calc_rsi_v0.1.0_xxx.py)
│   ├── cache/                # [Git Ignore] Parquet snapshots
│   └── logs/                 # thinking_process logs, security_violations.log
├── src/
│   ├── config.py             # Global configuration
│   ├── core/
│   │   ├── models.py         # SQLModel definitions (5 tables + VerificationStage)
│   │   ├── llm_adapter.py    # Qwen3 + category-specific prompts
│   │   ├── registry.py       # Tool registration & retrieval
│   │   ├── executor.py       # AST check + sandbox execution
│   │   ├── task_executor.py  # Task orchestration
│   │   ├── capabilities.py   # ✅ NEW: Capability enums & module mappings
│   │   ├── contracts.py      # ✅ NEW: Contract definitions for 20 tasks
│   │   └── verifier.py       # ✅ NEW: Multi-stage verification pipeline
│   ├── evolution/
│   │   ├── synthesizer.py    # Generate → Verify → Register (with verifier)
│   │   └── refiner.py        # Error Analysis → Patch → Re-verify
│   └── finance/
│       ├── data_proxy.py     # yfinance caching + retry decorator
│       └── bootstrap.py      # Initial yfinance tool set (5 tools)
└── benchmarks/
    ├── tasks.jsonl            # 20 benchmark tasks with contract_id
    ├── security_tasks.jsonl   # 5 security test cases
    ├── run_eval.py            # Evaluation runner
    └── compare_runs.py        # Run comparison tool
```

## Data Models (5 SQLModel Tables)

1. **ToolArtifact** - Tool metadata (name, version, hash, permissions, status, test_cases)
   - NEW: `capabilities`, `contract_id`, `verification_stage` fields
2. **ExecutionTrace** - Execution history (inputs, outputs, errors, timing, LLM config)
3. **ErrorReport** - Error analysis (error_type, root_cause from LLM)
4. **ToolPatch** - Repair records (diffs, rationale, resulting_tool)
5. **BatchMergeRecord** - Tool consolidation (source tools, merge strategy)

## Security Model

**Capability-Based AST Analysis:**
- Each tool category has specific allowed modules
- `calculation` tools CANNOT import yfinance (blocked)
- `fetch` tools CAN import yfinance

**Always Banned Modules:** `os`, `sys`, `subprocess`, `shutil`, `importlib`, `ctypes`, `socket`, `http`, `urllib`, `pickle`

**Always Banned Calls:** `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `vars`, `getattr`, `setattr`

**Always Banned Attributes:** `__dict__`, `__class__`, `__bases__`, `__mro__`, `__globals__`

**Sandbox:** subprocess isolation with 30s timeout.

## Tool Evolution Loop (Updated)

1. **Synthesize**: LLM generates tool code with category-specific prompt
2. **Multi-Stage Verify**:
   - Stage 1: AST security check (capability-based)
   - Stage 2: Self-test execution
   - Stage 3: Contract validation (output constraints)
   - Stage 4: Integration test (fetch tools only)
3. **Register**: If ALL stages pass, store code on disk and metadata in DB
4. **Refine**: On failure, analyze error and generate patch (max 3 attempts)

## Contract System

17 predefined contracts for all task types:
- **Fetch**: `fetch_financial`, `fetch_quote`, `fetch_price`, `fetch_ohlcv`, `fetch_list`
- **Calc**: `calc_rsi`, `calc_ma`, `calc_bollinger`, `calc_macd`, `calc_volatility`, `calc_kdj`, `calc_drawdown`, `calc_correlation`
- **Composite**: `comp_signal`, `comp_divergence`, `comp_portfolio`, `comp_conditional_return`

Each contract defines:
- Input types and required inputs
- Output type (numeric, dict, boolean, list, dataframe)
- Output constraints (min/max ranges, required keys)

## Data Proxy (yfinance Caching)

The `@DataProvider.reproducible` decorator implements record-replay with retry:
- Cache key: MD5(func_name + args + kwargs)
- Storage: `data/cache/{key}.parquet`
- Retry: 3 attempts with exponential backoff (1-10s)
- First call: Fetch from network, save to cache
- Subsequent calls: Read from cache (no network)

## File Naming Convention

```
data/artifacts/generated/{tool_name}_v{version}_{hash8}.py
```

Example: `calc_rsi_v0.1.0_f42711fb.py`

## Evaluation

20 benchmark tasks in 3 categories:
- **Fetch & Lookup** (8): Data retrieval + field extraction
- **Calculation** (8): Technical indicators (RSI, MACD, Bollinger, etc.)
- **Composite** (4): Multi-tool composition

Target metrics:
- Task Success Rate ≥ 80% ✅ **Achieved: 85% (17/20)**
- Tool Reuse Rate ≥ 30% (second run)
- Regression Rate ≈ 0%
- Security Block Rate = 100%

## Key Decisions (Architecture Overhaul)

1. **Capability-based permissions**: Different tool categories have different allowed modules
2. **Contract-based validation**: Each task type has input/output contracts
3. **Multi-stage verification**: Tools only promoted if ALL stages pass (eliminates implicit pass)
4. **Network resilience**: Retry with exponential backoff for data fetching
5. **Category-specific LLM prompts**: FETCH_SYSTEM_PROMPT, CALCULATE_SYSTEM_PROMPT, COMPOSITE_SYSTEM_PROMPT

## Recent Changes (Architecture Overhaul)

### New Files
- `src/core/capabilities.py` - ToolCapability enum, module mappings
- `src/core/contracts.py` - ToolContract dataclass, 17 contracts
- `src/core/verifier.py` - MultiStageVerifier class

### Modified Files
- `src/core/models.py` - Added VerificationStage enum, new fields
- `src/core/executor.py` - Added static_check_with_rules()
- `src/core/llm_adapter.py` - Category-specific prompts
- `src/evolution/synthesizer.py` - Integrated MultiStageVerifier
- `src/core/task_executor.py` - Financial queries now fall through
- `src/finance/data_proxy.py` - with_retry decorator
- `benchmarks/tasks.jsonl` - Added contract_id field
- `benchmarks/run_eval.py` - Integrated contracts/verifier

---

## Benchmark Results (2026-02-03)

### Latest Benchmark Result ✅
- **Pass Rate**: **85% (17/20)** - Target 80% **MET**
- **Run ID**: `post_round3_fix`
- **Results**: `benchmarks/results/post_round3_fix.json`

### By Category
| Category | Pass Rate | Status |
|----------|-----------|--------|
| Fetch | 75% (6/8) | Good |
| Calculation | 88% (7/8) | Good |
| Composite | **100% (4/4)** | ✅ Perfect |

### Fixes Applied (Round 3)

| Fix | File | Change |
|-----|------|--------|
| 1. Allow warnings | `src/core/executor.py` | Added `'warnings'` to ALLOWED_MODULES |
| 2. Allow urllib3 | `src/core/executor.py` | Added `'urllib3'` to ALLOWED_MODULES (yfinance dependency) |
| 3. Boolean parsing | `benchmarks/run_eval.py` | Handle Python boolean strings (`True`/`False`) |
| 4. Multi-asset fetch | `src/core/task_executor.py` | Added multi-symbol data fetching |
| 5. Param standardization | `src/core/llm_adapter.py` | Added param naming requirements to prompts |

### Key Files Modified
- `src/core/executor.py:64-69` - ALLOWED_MODULES includes `warnings`, `urllib3`
- `src/core/task_executor.py:163-318` - Multi-asset support methods
- `src/core/llm_adapter.py:35-45,175-183` - Parameter naming conventions in prompts
- `benchmarks/run_eval.py:259-264` - Python boolean string parsing

---

## Compaction Preservation

When context is compacted, preserve:
- Modified files list above
- Key decisions documented
- Test commands: `python src/core/verifier.py`, `python benchmarks/run_eval.py --clear-registry`
- **Current status**: 85% pass rate achieved, target 80% met
- Verification command: `python benchmarks/run_eval.py --clear-registry --run-id verify`
