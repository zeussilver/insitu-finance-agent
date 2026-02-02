# Phase 1a 技术规格 (spec.md)
> SSOT v1 | 金融自进化 Agent 复现 | 2026-01-29

## 1. 数据模型 (SQLModel)

采用 **"Metadata in DB, Payload on Disk"** 混合存储架构。

### 1.1 枚举定义

```python
from enum import Enum

class ToolStatus(str, Enum):
    PROVISIONAL = "provisional"  # 生成态：仅通过单测，未合并
    VERIFIED    = "verified"     # 稳定态：经过 Batch Merge 或人工 Review
    DEPRECATED  = "deprecated"   # 淘汰态：被更通用工具替代
    FAILED      = "failed"       # 废弃态：修复失败或有安全风险

class Permission(str, Enum):
    CALC_ONLY    = "calc_only"     # 纯计算 (pandas/numpy)
    NETWORK_READ = "network_read"  # 允许 AkShare/Requests GET
    FILE_WRITE   = "file_write"    # 允许写缓存 (极度受限)
```

### 1.2 表结构

#### 1.2.1 ToolArtifact (工具制品表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, auto | 主键 |
| name | str | index | 工具函数名 |
| semantic_version | str | default="0.1.0" | 语义版本号 |
| file_path | str | required | 相对路径，如 `generated/calc_rsi_v1.py` |
| content_hash | str | unique, index | SHA256(代码内容) |
| args_schema | JSON | default={} | 参数 JSON Schema |
| dependencies | JSON | default=[] | 依赖工具 ID 列表 |
| permissions | JSON | default=["calc_only"] | 权限列表 |
| status | ToolStatus | index, default=PROVISIONAL | 状态枚举 |
| parent_tool_ids | JSON | default=[] | Merge 来源 ID |
| test_cases | JSON | default=[] | 固化的回归测试集 |
| created_at | datetime | auto | 创建时间 |

#### 1.2.2 ExecutionTrace (执行轨迹表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| trace_id | str | PK | UUID |
| task_id | str | index | 任务标识 |
| tool_id | int | FK -> tool_artifacts.id | 执行的工具 |
| input_args | JSON | required | 输入参数快照 |
| output_repr | str | required | 结果摘要(截断至 1000 字符) |
| exit_code | int | required | 0=Success, 非0=Error |
| std_out | str | nullable | 标准输出 |
| std_err | str | nullable | 完整 Traceback |
| execution_time_ms | int | required | 执行耗时 |
| llm_config | JSON | required | {model, temperature, thinking_enabled} |
| env_snapshot | JSON | default={} | {akshare_version, pandas_version} |

#### 1.2.3 ErrorReport (错误报告表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, auto | 主键 |
| trace_id | str | FK -> execution_traces.trace_id | 关联执行记录 |
| error_type | str | required | 异常类型全名 |
| root_cause | str | required | LLM 分析后的原因摘要 |
| occurred_at | datetime | auto | 发生时间 |

#### 1.2.4 ToolPatch (修复补丁表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, auto | 主键 |
| error_report_id | int | FK -> error_reports.id | 关联错误报告 |
| base_tool_id | int | FK -> tool_artifacts.id | 基准工具 |
| patch_diff | str | required | Git Diff 或修改说明 |
| rationale | str | required | 思维链摘要 |
| resulting_tool_id | int | FK -> tool_artifacts.id | 新版本工具 |

#### 1.2.5 BatchMergeRecord (批次合并记录)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, auto | 主键 |
| source_tool_ids | JSON | required | 被合并的工具 ID 列表 |
| canonical_tool_id | int | FK -> tool_artifacts.id | 合并后的规范工具 |
| strategy | str | default="generalization" | 合并策略 |
| regression_stats | JSON | required | {passed: int, failed: int} |

## 2. 核心接口规格

### 2.1 LLMAdapter

```python
class LLMAdapter:
    """Qwen3 深度适配器"""
    
    def __init__(self, 
                 model: str = "qwen3-max-thinking",
                 temperature: float = 0.1,
                 enable_thinking: bool = True):
        """
        Args:
            model: 模型标识
            temperature: 采样温度 (0.0-1.0)
            enable_thinking: 是否启用思维链
        """
    
    def _clean_protocol(self, raw_content: str) -> dict:
        """
        协议清洗：剥离思考过程，提取代码载荷
        
        Returns:
            {
                "thought_trace": str,   # <think>...</think> 内容
                "code_payload": str,    # ```python...``` 内容
                "text_response": str    # 清洗后的文本
            }
        """
    
    def generate_tool_code(self, 
                           task: str, 
                           error_context: Optional[str] = None) -> dict:
        """
        生成工具代码
        
        Args:
            task: 任务描述
            error_context: 上次执行的错误信息 (用于修复场景)
        
        Returns:
            {
                "thought_trace": str,
                "code_payload": str,
                "raw_response": str
            }
        """
```

**Prompt 模板要求**：
1. 必须包含 Type Hints
2. 必须包含 Docstring
3. 必须在 `if __name__ == '__main__':` 下提供 2 个 assert 测试
4. 若 `error_context` 存在，追加 "Previous Error: {traceback}. Fix it."

### 2.2 ToolRegistry

```python
class ToolRegistry:
    """工具注册与检索"""
    
    def __init__(self, 
                 db_path: str = "data/evolution.db",
                 artifacts_dir: str = "data/artifacts"):
        pass
    
    def register(self, 
                 name: str,
                 code: str,
                 args_schema: dict,
                 permissions: List[Permission],
                 test_cases: List[dict]) -> ToolArtifact:
        """
        注册新工具
        
        流程:
        1. 计算 content_hash (SHA256)
        2. 检查 hash 是否已存在 (去重)
        3. 写入文件到 artifacts_dir/generated/
        4. 插入 DB 记录
        
        Returns:
            新创建的 ToolArtifact
        """
    
    def retrieve_by_name(self, name: str) -> Optional[ToolArtifact]:
        """按名称检索工具"""
    
    def retrieve_by_hash(self, content_hash: str) -> Optional[ToolArtifact]:
        """按哈希检索工具 (去重用)"""
    
    def search_similar(self, query: str, top_k: int = 5) -> List[ToolArtifact]:
        """
        语义相似检索 (Phase 1a 为 Stub，返回空列表)
        """
        return []
```

### 2.3 ToolExecutor

```python
class ToolExecutor:
    """安全执行器"""
    
    BANNED_MODULES = {'os', 'sys', 'subprocess', 'shutil', 
                      'builtins', 'importlib', 'ctypes', 'socket'}
    
    BANNED_CALLS = {'eval', 'exec', 'compile', '__import__', 
                    'open',  # 需特殊处理：只允许 mode='r'
                    'globals', 'locals', 'vars'}
    
    ALLOWED_MODULES = {'pandas', 'numpy', 'datetime', 'json', 
                       'math', 'decimal', 'collections', 're',
                       'akshare',  # 通过 data_proxy 封装
                       'talib'}    # 技术指标库
    
    def static_check(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        AST 静态检查
        
        Returns:
            (is_safe, error_message)
        """
    
    def run_with_limit(self, 
                       tool_path: str, 
                       args: dict,
                       timeout_sec: int = 30,
                       memory_limit_mb: int = 512) -> ExecutionTrace:
        """
        沙箱执行
        
        使用 subprocess.run:
        - 独立进程
        - 超时控制
        - stdout/stderr 捕获
        """
```

**AST 检查规则**：

| 节点类型 | 检查逻辑 |
|----------|----------|
| Import / ImportFrom | 模块名不在 BANNED_MODULES |
| Call | 函数名不在 BANNED_CALLS |
| Call(open) | 检查 mode 参数，仅允许 'r' |
| Attribute | 禁止 `__dict__`, `__class__` 等魔术属性访问 |

### 2.4 Synthesizer

```python
class Synthesizer:
    """工具合成器：生成 → 验证 → 注册"""
    
    def __init__(self, 
                 llm: LLMAdapter,
                 executor: ToolExecutor,
                 registry: ToolRegistry):
        pass
    
    def synthesize(self, task: str) -> Tuple[Optional[ToolArtifact], ExecutionTrace]:
        """
        合成流程:
        1. 调用 LLM 生成代码
        2. 静态安全检查
        3. 执行内置测试 (if __name__ == '__main__')
        4. 若通过，注册到 Registry
        
        Returns:
            (tool, trace) - tool 可能为 None (生成失败)
        """
```

### 2.5 Refiner

```python
class Refiner:
    """工具修复器：错误分析 → 补丁"""
    
    def __init__(self,
                 llm: LLMAdapter,
                 executor: ToolExecutor,
                 registry: ToolRegistry):
        pass
    
    def refine(self, 
               error_report: ErrorReport,
               max_attempts: int = 3) -> Tuple[Optional[ToolArtifact], List[ExecutionTrace]]:
        """
        修复流程:
        1. 从 error_report 获取失败上下文
        2. 调用 LLM 生成补丁代码
        3. 验证补丁
        4. 创建 ToolPatch 记录
        5. 注册新版本工具
        
        Returns:
            (new_tool, traces) - new_tool 可能为 None (修复失败)
        """
```

## 3. 数据缓存规格

### 3.1 reproducible_akshare 装饰器

```python
def reproducible_akshare(func):
    """
    缓存策略:
    - Key: MD5(func_name + str(args) + str(kwargs))
    - Storage: data/cache/{key}.parquet
    - 优先回放缓存，否则录制
    
    数据清洗:
    - 所有列转为 str 类型 (确保 Parquet 兼容)
    - 时间戳统一为 UTC
    """
```

### 3.2 Bootstrap 工具集

| 工具名 | 功能 | AkShare API |
|--------|------|-------------|
| get_a_share_hist | A股历史行情 | stock_zh_a_hist |
| get_financial_abstract | 财务摘要 | stock_financial_abstract |
| get_realtime_quote | 实时行情 | stock_zh_a_spot_em |
| get_index_daily | 指数日线 | stock_zh_index_daily |
| get_fund_etf_hist | ETF 历史 | fund_etf_hist_em |

## 4. 版本号规则

采用语义化版本 `MAJOR.MINOR.PATCH`：

| 变更类型 | 版本递增 | 示例 |
|----------|----------|------|
| 新工具创建 | MINOR | 0.1.0 → 0.2.0 |
| 修复补丁 | PATCH | 0.1.0 → 0.1.1 |
| Merge 泛化 | MAJOR | 0.1.0 → 1.0.0 |

## 5. 文件命名规范

```
data/artifacts/generated/{tool_name}_v{version}_{hash8}.py

示例:
calc_rsi_v0.1.0_a1b2c3d4.py
calc_bollinger_v0.2.1_e5f6g7h8.py
```

`hash8` = content_hash 前 8 位，用于快速区分同名不同版本。
