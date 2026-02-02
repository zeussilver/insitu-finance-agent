# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Yunjue Agent** - A fully reproducible, zero-start in-situ self-evolving financial agent system.

This project reproduces the core tool evolution loop from the paper "Yunjue Agent: A Fully Reproducible, Zero-Start In-Situ Self-Evolving Agent System" (Li et al., 2026).

### Core Principles

| Principle | Implementation |
|-----------|----------------|
| Auditable | All generated code as `.py` files in `data/artifacts/`, Git trackable |
| Reproducible | Frozen AkShare data via Parquet snapshots; locked dependency versions |
| Secure | AST static analysis + subprocess sandboxing before code execution |

### Architecture

**"Metadata in DB, Payload on Disk"** - SQLite stores tool metadata, actual code files stored on disk.

**JSON-IPC** for sandbox communication - avoids eval(), uses subprocess with JSON file exchange.

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

### Phase 1a MVP - COMPLETED ✅

| Component | File | Status |
|-----------|------|--------|
| Global config | `src/config.py` | ✅ |
| Data models (5 tables) | `src/core/models.py` | ✅ |
| AkShare caching | `src/finance/data_proxy.py` | ✅ |
| LLM adapter | `src/core/llm_adapter.py` | ✅ |
| AST security + sandbox | `src/core/executor.py` | ✅ |
| Tool registry | `src/core/registry.py` | ✅ |
| Tool synthesizer | `src/evolution/synthesizer.py` | ✅ |
| Tool refiner | `src/evolution/refiner.py` | ✅ |
| Bootstrap tools | `src/finance/bootstrap.py` | ✅ |
| Evaluation suite | `benchmarks/run_eval.py` | ✅ |
| Benchmark tasks | `benchmarks/tasks.jsonl` | ✅ |
| Run comparison | `benchmarks/compare_runs.py` | ✅ |
| CLI entry point | `main.py` | ✅ |

### Verified Working

- Database initialization with 5 SQLModel tables
- Security blocking (os, subprocess, eval all blocked; pathlib, hashlib whitelisted)
- Tool synthesis (LLM → verify → register) with Qwen3 API
- Tool refinement (error analysis → patch → re-verify, max 3 attempts)
- Tool reuse (100% reuse rate on second run)
- Data caching (Parquet snapshots)
- Evaluation suite (20 tasks, 3 categories, security tasks)
- Run comparison (consistency rate, reuse improvement)
- LLM timeout protection (60s)

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

# Run security-only evaluation
python benchmarks/run_eval.py --security-only

# Compare two evaluation runs
python benchmarks/compare_runs.py run1 run2
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
│   │   ├── bootstrap/        # Initial AkShare tools
│   │   └── generated/        # Evolved tools (e.g., calc_rsi_v0.1.0_xxx.py)
│   ├── cache/                # [Git Ignore] Parquet snapshots
│   └── logs/                 # thinking_process logs
├── src/
│   ├── config.py             # Global configuration
│   ├── core/
│   │   ├── models.py         # SQLModel definitions (5 tables)
│   │   ├── llm_adapter.py    # Qwen3 protocol cleaning
│   │   ├── registry.py       # Tool registration & retrieval
│   │   └── executor.py       # AST check + sandbox execution
│   ├── evolution/
│   │   ├── synthesizer.py    # Generate → Verify → Register
│   │   └── refiner.py        # Error Analysis → Patch → Re-verify
│   └── finance/
│       ├── data_proxy.py     # AkShare caching decorator
│       └── bootstrap.py      # Initial AkShare tool set (5 tools)
└── benchmarks/
    ├── tasks.jsonl            # 20 benchmark tasks (fetch/calc/composite)
    ├── security_tasks.jsonl   # 5 security test cases
    ├── run_eval.py            # Evaluation runner
    └── compare_runs.py        # Run comparison tool
```

## Data Models (5 SQLModel Tables)

1. **ToolArtifact** - Tool metadata (name, version, hash, permissions, status, test_cases)
2. **ExecutionTrace** - Execution history (inputs, outputs, errors, timing, LLM config)
3. **ErrorReport** - Error analysis (error_type, root_cause from LLM)
4. **ToolPatch** - Repair records (diffs, rationale, resulting_tool)
5. **BatchMergeRecord** - Tool consolidation (source tools, merge strategy)

## Security Model

**AST Static Analysis Blocklist:**
- Modules: `os`, `sys`, `subprocess`, `shutil`, `importlib`, `ctypes`, `socket`, `http`, `urllib`, `pickle`
- Calls: `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `vars`, `getattr`, `setattr`
- Magic attributes: `__dict__`, `__class__`, `__bases__`, `__mro__`

**Allowed Modules:** `pandas`, `numpy`, `datetime`, `json`, `math`, `decimal`, `collections`, `re`, `akshare`, `talib`, `typing`, `hashlib`, `pathlib`

**Sandbox:** subprocess isolation with 30s timeout.

## Tool Evolution Loop

1. **Synthesize**: LLM generates tool code with type hints, docstring, and 2 assert tests
2. **Static Check**: AST analysis blocks dangerous code
3. **Verify**: Execute `if __name__ == '__main__':` tests in sandbox
4. **Register**: If passed, store code on disk and metadata in DB
5. **Refine**: On failure, analyze error and generate patch (max 3 attempts)

## Data Proxy (AkShare Caching)

The `@DataProvider.reproducible` decorator implements record-replay:
- Cache key: MD5(func_name + args + kwargs)
- Storage: `data/cache/{key}.parquet`
- All columns converted to str for Parquet compatibility
- First call: Fetch from network, save to cache
- Subsequent calls: Read from cache (no network)

## File Naming Convention

```
data/artifacts/generated/{tool_name}_v{version}_{hash8}.py
```

Example: `calc_rsi_v0.1.0_f42711fb.py`

## Evaluation (Pending)

20 benchmark tasks in 3 categories:
- **Fetch & Lookup** (8): Data retrieval + field extraction
- **Calculation** (8): Technical indicators (RSI, MACD, Bollinger, etc.)
- **Composite** (4): Multi-tool composition

Target metrics:
- Task Success Rate ≥ 80%
- Tool Reuse Rate ≥ 30% (second run)
- Regression Rate ≈ 0%
- Security Block Rate = 100%



## 每次compact前增量更新CLAUDE.md 至少包含：

-项目目标 & 当前里程碑（1–2 段）

-目录结构简图（只列关键目录/模块）

-约定：代码风格、命名、错误处理、日志、配置

-必跑命令：lint/test/typecheck/e2e（以及成功标准）

-“压缩时必须保留”：修改过的文件列表、未完成 TODO、关键决策、测试命令（官方明确建议可在 CLAUDE.md 里定制 compaction 保留项）

##每完成一个阶段，让 Claude 更新仓库内的：

-plan.md（下一步）

-progress.md（已完成/当前状态/下一步）

-decisions.md（关键决策与理由）

-notes/testing.md（必跑命令与最近一次结果）

这样即使 compaction 发生，也能通过“让它读这些文件”快速恢复完整工作状态，而不是依赖被压缩过的聊天摘要。