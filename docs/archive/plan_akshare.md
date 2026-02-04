> ⚠️ **ARCHIVED - NOT MAINTAINED**
> This document reflects the pre-yfinance implementation (akshare-based).
> For current documentation, see [CLAUDE.md](../../CLAUDE.md).
> Archived on: 2026-02-04

---

# Phase 1a 项目规划 (plan.md)
> SSOT v1 | 金融自进化 Agent 复现 | 2026-01-29

## 1. 项目目标

复现论文 "Yunjue Agent: A Fully Reproducible, Zero-Start In-Situ Self-Evolving Agent System" (Li et al., 2026) 的工具进化核心循环，聚焦于：

| 目标 | 验收标准 |
|------|----------|
| 可审计 (Artifacts on Disk) | 所有生成代码以 `.py` 文件形式落盘，Git 可追踪 |
| 可复现 (AkShare Freeze) | 相同输入在任意时间点产生相同输出 |
| 安全可控 (AST Blocking) | 危险代码在执行前被静态拦截 |

## 2. 范围边界

### 2.1 Phase 1a 包含

- 核心数据模型 (5 张 SQLModel 表)
- LLM 适配器 (Qwen3 协议清洗)
- 工具注册与检索 (Registry)
- 安全执行器 (AST 检查 + 沙箱)
- AkShare 离线缓存 (Parquet 快照)
- 工具合成器 (Synthesizer: 生成 → 验证 → 注册)
- 工具修复器 (Refiner: 错误分析 → 补丁)
- 离线评测基座 (20 个任务)

### 2.2 Phase 1a 排除 (Stub/Placeholder)

- Batch Merge 逻辑 (仅预留接口)
- 向量检索 (ChromaDB 占位)
- 多轮对话管理
- 前端可视化

## 3. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 数据库 | SQLite + SQLModel | 轻量、单文件、ORM 友好 |
| 缓存格式 | Parquet | 列存高效、Schema 自描述 |
| LLM | Qwen3-Max-Thinking | 原生思维链、中文金融优化 |
| 数据源 | AkShare 1.13.50 | A 股数据覆盖全、API 稳定 |
| 沙箱 | subprocess + AST | 进程隔离、静态分析 |

## 4. 里程碑计划

```
Week 1: 基础建设
├── Day 1-2: 数据模型 + DB 初始化
├── Day 3-4: AkShare 缓存层 + Bootstrap 工具
└── Day 5: LLM 适配器 (协议清洗)

Week 2: 进化循环
├── Day 1-2: ToolExecutor (AST + 沙箱)
├── Day 3-4: Synthesizer (生成→验证→注册)
└── Day 5: Refiner (错误分析→补丁)

Week 3: 评测与验收
├── Day 1-2: 评测任务集 (20 个) ✅
├── Day 3: 评测脚本 + 指标计算 ✅ (run_eval.py + compare_runs.py)
├── Day 4: 对照组实验 ✅ (evolving run1/run2 + security)
└── Day 5: 文档收尾 ✅
```

## 5. 仓库结构

```
fin_evo_agent/
├── data/
│   ├── evolution.db          # SQLite 数据库
│   ├── artifacts/            # [Git Tracked]
│   │   ├── bootstrap/        # 初始 AkShare 工具 (3-5 个)
│   │   └── generated/        # 进化出的工具
│   ├── cache/                # [Git Ignore] Parquet 快照
│   └── logs/                 # thinking_process 日志
├── src/
│   ├── core/
│   │   ├── models.py         # SQLModel 定义
│   │   ├── llm_adapter.py    # Qwen3 协议清洗
│   │   ├── registry.py       # 工具落盘与检索
│   │   └── executor.py       # AST 检查 + 沙箱
│   ├── evolution/
│   │   ├── synthesizer.py    # 生成 → 验证 → 注册
│   │   ├── refiner.py        # 错误分析 → 补丁
│   │   └── merger.py         # (Stub) Batch 合并
│   ├── finance/
│   │   ├── bootstrap.py      # AkShare 初始工具集
│   │   └── data_proxy.py     # 缓存装饰器
│   └── utils/
│       └── file_ops.py       # Hash 与文件读写
├── benchmarks/
│   ├── tasks.jsonl           # 离线评测集 (20 个任务)
│   ├── security_tasks.jsonl  # 安全评测集 (5 个任务)
│   ├── run_eval.py           # 评测脚本
│   └── compare_runs.py       # 两次运行结果对比
├── main.py                   # CLI 入口
├── requirements.txt
└── README.md
```

## 6. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Qwen3 API 不稳定 | 进化循环中断 | 本地缓存 + 重试机制 + **60s 超时** ✅ |
| AkShare 接口变更 | 数据获取失败 | 锁定版本 + Parquet 快照 |
| 生成代码执行危险操作 | 系统安全风险 | AST 白名单 + 进程沙箱 (**pathlib/hashlib 已加白**) ✅ |
| 工具库膨胀 | 检索效率下降 | Merge 机制 (Phase 1b) |
| Python 3.9 + LibreSSL 兼容性 | AkShare 网络调用 SSL 错误 | 需升级到 Python 3.10+ 或安装 OpenSSL 1.1.1+ |

## 7. 依赖锁定

```
# requirements.txt (精确版本)
akshare==1.13.50
sqlmodel==0.0.14
pandas==2.1.4
pyarrow==14.0.2
dashscope>=1.14.0  # Qwen3 SDK
```
