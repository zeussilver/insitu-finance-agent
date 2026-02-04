> ⚠️ **ARCHIVED - NOT MAINTAINED**
> This document reflects the pre-yfinance implementation (akshare-based).
> For current documentation, see [CLAUDE.md](../../CLAUDE.md).
> Archived on: 2026-02-04

---

# Phase 1a 验收清单 (check.md)
> SSOT v1 | 金融自进化 Agent 复现 | 2026-01-29

## 验收流程

按顺序执行以下检查点，每个 `[ ]` 需手动确认并打 `[x]`。

---

## Step 1: 环境与依赖

### 1.1 Python 环境

```bash
python --version  # 期望: Python 3.10+
```

- [ ] Python 版本 ≥ 3.10

### 1.2 依赖安装

```bash
pip install -r requirements.txt
pip list | grep -E "akshare|sqlmodel|pandas|pyarrow"
```

- [ ] akshare==1.13.50 已安装
- [ ] sqlmodel==0.0.14 已安装
- [ ] pandas==2.1.4 已安装
- [ ] pyarrow==14.0.2 已安装

---

## Step 2: 基础建设

### 2.1 数据库初始化

```bash
python main.py --init
```

**验收项**：

- [ ] `data/evolution.db` 文件已生成
- [ ] SQLite 中存在 5 张表：

```bash
sqlite3 data/evolution.db ".tables"
# 期望输出: batch_merge_records  error_reports  execution_traces  tool_artifacts  tool_patches
```

- [ ] 表结构正确（抽查 tool_artifacts）：

```bash
sqlite3 data/evolution.db ".schema tool_artifacts"
# 验证: id, name, semantic_version, file_path, content_hash, args_schema, dependencies, permissions, status, parent_tool_ids, test_cases, created_at
```

### 2.2 Bootstrap 工具初始化

```bash
python src/finance/bootstrap.py
```

**验收项**：

- [ ] `data/cache/` 目录下生成 Parquet 文件
- [ ] 再次运行速度极快（< 1 秒，命中缓存）

```bash
time python src/finance/bootstrap.py
# 二次运行期望: real < 1s
```

- [ ] `data/artifacts/bootstrap/` 目录下存在 3-5 个 `.py` 文件

```bash
ls data/artifacts/bootstrap/
# 期望: get_a_share_hist.py, get_financial_abstract.py, ...
```

---

## Step 3: LLM 适配器

### 3.1 协议清洗测试

```bash
python -c "
from src.core.llm_adapter import LLMAdapter

test_input = '''
<think>
我需要计算 RSI 指标...
步骤1: 获取价格数据
步骤2: 计算涨跌幅
</think>

\`\`\`python
def calc_rsi(prices, period=14):
    pass
\`\`\`
'''

adapter = LLMAdapter()
result = adapter._clean_protocol(test_input)
print('thought_trace:', bool(result['thought_trace']))
print('code_payload:', bool(result['code_payload']))
"
```

**验收项**：

- [ ] `thought_trace` 成功提取（非空）
- [ ] `code_payload` 成功提取（非空）
- [ ] 清洗后的 `text_response` 不含 `<think>` 标签

---

## Step 4: 安全执行器

### 4.1 AST 静态检查 - 安全代码

```bash
python -c "
from src.core.executor import ToolExecutor

safe_code = '''
import pandas as pd
def calc_ma(prices, window=5):
    return pd.Series(prices).rolling(window).mean()
'''

executor = ToolExecutor()
is_safe, error = executor.static_check(safe_code)
print(f'Safe code check: is_safe={is_safe}, error={error}')
"
```

- [ ] 输出 `is_safe=True, error=None`

### 4.2 AST 静态检查 - 危险代码

```bash
python -c "
from src.core.executor import ToolExecutor

dangerous_codes = [
    'import os; os.system(\"rm -rf /\")',
    'import subprocess; subprocess.run([\"ls\"])',
    'eval(\"1+1\")',
    'exec(\"print(1)\")',
    '__import__(\"sys\")',
]

executor = ToolExecutor()
for code in dangerous_codes:
    is_safe, error = executor.static_check(code)
    print(f'{code[:30]}... -> blocked={not is_safe}')
"
```

**验收项**：

- [ ] 所有 5 段危险代码均被拦截（`blocked=True`）

### 4.3 沙箱执行测试

```bash
python main.py --task "执行 rm -rf /"
```

- [ ] 日志显示 `SecurityException` 或类似安全拦截信息
- [ ] 系统无任何文件被删除

---

## Step 5: 工具合成流程

### 5.1 基础合成测试

```bash
python main.py --task "计算 000001 的布林带"
```

**验收项**：

- [ ] 日志显示 `<think>` 过程被提取（或存入 `data/logs/`）
- [ ] `data/artifacts/generated/` 下生成 `.py` 文件

```bash
ls data/artifacts/generated/
# 期望: 至少一个 calc_bollinger*.py 或类似文件
```

- [ ] DB `tool_artifacts` 表新增记录：

```bash
sqlite3 data/evolution.db "SELECT name, status, file_path FROM tool_artifacts WHERE status='provisional' LIMIT 5"
```

- [ ] 新记录 `status='provisional'`

### 5.2 Content Hash 去重

```bash
# 执行两次相同任务
python main.py --task "计算 000001 的布林带"
python main.py --task "计算 000001 的布林带"

# 检查是否去重
sqlite3 data/evolution.db "SELECT COUNT(*) FROM tool_artifacts WHERE name LIKE '%bollinger%'"
```

- [ ] 相同代码内容只注册一次（hash 去重生效）

---

## Step 6: 工具修复流程

### 6.1 触发修复场景

```bash
# 构造一个会失败的任务（如数据格式不匹配）
python main.py --task "计算不存在股票代码 999999 的 RSI"
```

**验收项**：

- [ ] `error_reports` 表新增记录
- [ ] 系统尝试调用 Refiner（日志可见）
- [ ] 若修复成功，`tool_patches` 表有记录

```bash
sqlite3 data/evolution.db "SELECT COUNT(*) FROM error_reports"
sqlite3 data/evolution.db "SELECT COUNT(*) FROM tool_patches"
```

---

## Step 7: 评测执行

### 7.1 首次评测

```bash
python benchmarks/run_eval.py --agent evolving --run-id run1
```

**验收项**：

- [ ] 生成 `benchmarks/eval_report_run1.csv`
- [ ] CSV 包含必需列: `task_id, category, agent_type, success, tool_source, execution_time_ms`
- [ ] 输出汇总统计（Task Success Rate, Tool Creation Count 等）

### 7.2 二次评测（验证 Reuse）

```bash
python benchmarks/run_eval.py --agent evolving --run-id run2
```

**验收项**：

- [ ] run2 的 `tool_source` 列中 `reused` 数量 > run1
- [ ] run2 的平均 `execution_time_ms` < run1（复用更快）

### 7.3 对照组评测

```bash
python benchmarks/run_eval.py --agent static --run-id static1
```

- [ ] Static Agent 的 Task Success Rate < Evolving Agent

---

## Step 8: 可复现性验证

### 8.1 缓存命中

```bash
# 在断网环境下运行（或 mock AkShare）
python benchmarks/run_eval.py --agent evolving --offline-mode
```

- [ ] 所有任务正常完成（100% 缓存命中）
- [ ] 无网络请求错误

### 8.2 结果一致性

```bash
python benchmarks/compare_runs.py run1 run2
```

- [ ] 输出一致率 ≥ 95%（允许 LLM 非确定性导致的微小差异）

---

## Step 9: 最终指标验收

| 指标 | 目标 | 实际 | Pass |
|------|------|------|------|
| Task Success Rate (Evolving) | ≥ 80% | ___% | [ ] |
| Tool Reuse Rate (run2) | ≥ 30% | ___% | [ ] |
| Regression Rate | ≈ 0% | ___% | [ ] |
| Security Block Rate | 100% | ___% | [ ] |
| Bootstrap 工具数 | 3-5 个 | ___ 个 | [ ] |
| 表结构完整性 | 5 张表 | ___ 张 | [ ] |

---

## 签字确认

- [ ] **Step 1-9 全部通过**
- [ ] 评审人签字: ____________
- [ ] 日期: ____________

---

## 附录: 快速验收命令汇总

```bash
# 一键验收脚本 (可选实现)
#!/bin/bash
set -e

echo "=== Step 1: Environment ==="
python --version
pip list | grep -E "akshare|sqlmodel"

echo "=== Step 2: Init ==="
python main.py --init
sqlite3 data/evolution.db ".tables"

echo "=== Step 3: Bootstrap ==="
python src/finance/bootstrap.py
ls data/cache/
ls data/artifacts/bootstrap/

echo "=== Step 4: Security ==="
python main.py --task "执行 rm -rf /"

echo "=== Step 5: Synthesis ==="
python main.py --task "计算 000001 的布林带"
ls data/artifacts/generated/

echo "=== Step 6: Eval ==="
python benchmarks/run_eval.py --agent evolving --run-id quick_test

echo "=== All checks passed! ==="
```
