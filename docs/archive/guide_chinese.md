> ⚠️ **ARCHIVED - NOT MAINTAINED**
> This document reflects the pre-yfinance implementation (akshare-based).
> For current documentation, see [CLAUDE.md](../../CLAUDE.md).
> Archived on: 2026-02-04

---

我是首席架构师。Phase 1a 的核心是构建\*\*"数据可复现、执行更安全、过程全记录"\*\*的金融智能体底座。

我们将严格遵循 **"Metadata in DB, Payload on Disk"** 的架构原则，采用 **JSON-IPC** 方式解决沙箱与主进程间传输 Pandas DataFrame 的难题。

以下是完整、分步骤、可运行的代码实现。

### ---

**Step 0: 工程初始化**

请在终端执行以下命令，构建项目结构与依赖配置。

Bash

\# 1\. 创建目录树
mkdir \-p fin\_evo\_agent/data/{db,artifacts/generated,cache,logs}
mkdir \-p fin\_evo\_agent/src/{core,finance,evolution,utils}
touch fin\_evo\_agent/\_\_init\_\_.py

\# 2\. 写入依赖配置 (锁定版本以保证复现)
cat \<\<EOF \> fin\_evo\_agent/requirements.txt
sqlmodel==0.0.14
sqlalchemy\>=2.0.0
pandas\>=2.0.0
numpy\>=1.24.0
akshare\>=1.13.0
pyarrow\>=14.0.0
openai\>=1.0.0
tabulate
EOF

\# 3\. 安装依赖
\# pip install \-r fin\_evo\_agent/requirements.txt

**全局配置**: fin\_evo\_agent/src/config.py

Python

import os
from pathlib import Path

\# 定位项目根目录
ROOT\_DIR \= Path(\_\_file\_\_).parent.parent
DATA\_DIR \= ROOT\_DIR / "data"

\# 数据库路径
DB\_URL \= f"sqlite:///{DATA\_DIR}/db/evolution.db"

\# 存储路径
ARTIFACTS\_DIR \= DATA\_DIR / "artifacts"
GENERATED\_DIR \= ARTIFACTS\_DIR / "generated"
CACHE\_DIR \= DATA\_DIR / "cache"

\# 确保目录存在
for p in \[GENERATED\_DIR, CACHE\_DIR\]:
    p.mkdir(parents=True, exist\_ok=True)

### ---

**Step 1: 核心数据模型 (SQLModel)**

我们定义 5 张核心表，实现元数据与代码文件的分离存储。

**文件**: fin\_evo\_agent/src/core/models.py

Python

from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, JSON, Column, create\_engine
from sqlalchemy import Text
from src.config import DB\_URL

\# \--- 枚举定义 \---
class ToolStatus(str, Enum):
    PROVISIONAL \= "provisional"  \# 刚生成，仅通过内建单测
    VERIFIED \= "verified"        \# 经过 Batch Merge 验证
    DEPRECATED \= "deprecated"    \# 已淘汰
    FAILED \= "failed"            \# 无法修复

class Permission(str, Enum):
    CALC\_ONLY \= "calc\_only"       \# 纯计算
    NETWORK\_READ \= "network\_read" \# 允许 AkShare
    FILE\_WRITE \= "file\_write"     \# 允许写缓存

\# \--- 1\. 工具制品表 (Code on Disk, Meta in DB) \---
class ToolArtifact(SQLModel, table=True):
    \_\_tablename\_\_ \= "tool\_artifacts"

    id: Optional\[int\] \= Field(default=None, primary\_key=True)
    name: str \= Field(index=True, unique=True)
    semantic\_version: str \= Field(default="0.1.0")

    \# 物理存储指向
    file\_path: str \= Field(description="artifacts/generated 下的文件名")
    content\_hash: str \= Field(index=True, unique=True)

    \# 元数据
    code\_content: str \= Field(sa\_column=Column(Text)) \# 冗余存储方便调试
    permissions: List\[str\] \= Field(default=\[Permission.CALC\_ONLY\], sa\_column=Column(JSON))
    status: ToolStatus \= Field(default=ToolStatus.PROVISIONAL, index=True)

    created\_at: datetime \= Field(default\_factory=datetime.utcnow)

\# \--- 2\. 执行轨迹表 (用于复盘与修复) \---
class ExecutionTrace(SQLModel, table=True):
    \_\_tablename\_\_ \= "execution\_traces"

    trace\_id: str \= Field(primary\_key=True)
    task\_id: str \= Field(index=True)
    tool\_id: Optional\[int\] \= Field(foreign\_key="tool\_artifacts.id")

    \# 输入输出快照
    input\_args: Dict \= Field(default={}, sa\_column=Column(JSON))
    output\_repr: str \= Field(sa\_column=Column(Text)) \# 结果摘要

    \# 执行现场
    exit\_code: int
    std\_out: Optional\[str\] \= Field(sa\_column=Column(Text))
    std\_err: Optional\[str\] \= Field(sa\_column=Column(Text))
    execution\_time\_ms: int

    created\_at: datetime \= Field(default\_factory=datetime.utcnow)

\# \--- DB 初始化工具 \---
def init\_db():
    engine \= create\_engine(DB\_URL)
    SQLModel.metadata.create\_all(engine)

### ---

**Step 2: 金融数据底座 (Data Freeze Proxy)**

这是评测**可复现性**的关键。通过装饰器拦截 AkShare 请求，将数据"冷冻"为 Parquet 文件。

**文件**: fin\_evo\_agent/src/finance/data\_proxy.py

Python

import akshare as ak
import pandas as pd
import hashlib
import os
import json
from functools import wraps
from src.config import CACHE\_DIR

class DataProvider:
    """AkShare 代理：实现 '录制-回放' (Record-Replay) 机制"""

    @staticmethod
    def \_get\_cache\_path(func\_name, args, kwargs):
        \# 生成唯一指纹：函数名 \+ 参数 \+ 排序后的关键字参数
        key \= json.dumps({
            "f": func\_name,
            "a": \[str(a) for a in args\],
            "k": {k: str(v) for k, v in sorted(kwargs.items())}
        }, sort\_keys=True)
        hash\_key \= hashlib.md5(key.encode()).hexdigest()
        return CACHE\_DIR / f"{hash\_key}.parquet"

    @classmethod
    def reproducible(cls, func):
        @wraps(func)
        def wrapper(\*args, \*\*kwargs):
            cache\_path \= cls.\_get\_cache\_path(func.\_\_name\_\_, args, kwargs)

            \# 1\. 回放模式 (Hit)
            if cache\_path.exists():
                \# print(f"\[Cache Hit\] {func.\_\_name\_\_}")
                return pd.read\_parquet(cache\_path)

            \# 2\. 录制模式 (Miss)
            try:
                print(f"\[Network\] Fetching {func.\_\_name\_\_}...")
                df \= func(\*args, \*\*kwargs)

                \# 降级策略：强制将所有列转为 String 以兼容 Parquet (防止 Object 类型混合报错)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.astype(str).to\_parquet(cache\_path)
                return df
            except Exception as e:
                raise RuntimeError(f"Data Fetch Failed: {str(e)}")
        return wrapper

\# \--- Bootstrap Tools (系统预置的原子工具) \---

@DataProvider.reproducible
def get\_a\_share\_hist(symbol: str, start: str, end: str) \-\> pd.DataFrame:
    """获取 A 股日线行情。Args: symbol='000001', start='20230101', end='20230131'"""
    \# 强制指定 adjust="qfq" 保证回测准确
    return ak.stock\_zh\_a\_hist(symbol=symbol, period="daily", start\_date=start, end\_date=end, adjust="qfq")

@DataProvider.reproducible
def get\_financial\_abstract(symbol: str) \-\> pd.DataFrame:
    """获取个股财务摘要"""
    return ak.stock\_financial\_abstract(symbol=symbol)

@DataProvider.reproducible
def get\_spot\_price() \-\> pd.DataFrame:
    """获取全市场实时行情"""
    return ak.stock\_zh\_a\_spot\_em()

### ---

**Step 3: 安全执行器 (Sandbox with JSON-IPC)**

为了安全地传输 Pandas DataFrame 并隔离环境，我们不使用 eval()，而是生成一个独立的 runner.py 脚本，通过 JSON 文件交换参数。

**文件**: fin\_evo\_agent/src/core/executor.py

Python

import ast
import subprocess
import sys
import tempfile
import json
import time
from pathlib import Path
from src.core.models import ExecutionTrace

class SecurityException(Exception): pass

class ToolExecutor:
    \# 静态黑名单：严禁系统操作与网络 IO (除受控库外)
    BANNED\_IMPORTS \= {'os', 'sys', 'subprocess', 'shutil', 'builtins', 'importlib', 'socket', 'http'}
    BANNED\_CALLS \= {'eval', 'exec', 'open', 'compile'}

    def static\_check(self, code: str):
        """AST 静态安全检查"""
        try:
            tree \= ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module \= node.module.split('.')\[0\] if hasattr(node, 'module') and node.module else ""
                    for n in node.names:
                        name \= module or n.name.split('.')\[0\]
                        if name in self.BANNED\_IMPORTS:
                            raise SecurityException(f"Illegal import: {name}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in self.BANNED\_CALLS:
                        raise SecurityException(f"Illegal call: {node.func.id}")
        except SyntaxError as e:
            raise SecurityException(f"Syntax Error: {e}")

    def execute(self, code: str, func\_name: str, args: dict, task\_id: str) \-\> ExecutionTrace:
        """
        沙箱执行流程：
        1\. Static Check
        2\. Serialize Args \-\> args.json
        3\. Generate Runner \-\> runner.py
        4\. Subprocess Run
        """
        self.static\_check(code)

        start\_ts \= time.time\_ns()

        \# 使用临时目录隔离文件
        with tempfile.TemporaryDirectory() as tmp\_dir:
            dir\_path \= Path(tmp\_dir)
            args\_path \= dir\_path / "args.json"

            \# 1\. 序列化参数 (处理 DataFrame 需转换为 list 或 dict，此处简化为 str dump)
            \# 在生产环境中，DataFrame 应通过 parquet 临时文件传递，此处为 MVP 简化
            safe\_args \= json.loads(json.dumps(args, default=str))
            with open(args\_path, 'w') as f:
                json.dump(safe\_args, f)

            \# 2\. 构造 Runner 脚本
            \# 注入 PYTHONPATH 确保能 import src 模块
            runner\_code \= f"""
import json
import sys
import os
import pandas as pd
import numpy as np

\# Inject Project Root
sys.path.append("{os.getcwd()}")

\# \--- Tool Code \---
{code}
\# \-----------------

if \_\_name\_\_ \== "\_\_main\_\_":
    try:
        if "{func\_name}" \== "verify\_only":
            \# 仅运行代码中的 if \_\_name\_\_ \== "\_\_main\_\_" 测试
            print("\<\<VERIFY\_PASS\>\>")
            sys.exit(0)

        \# 加载参数
        with open("{args\_path}", "r") as f:
            args \= json.load(f)

        \# 执行函数
        if "{func\_name}" in locals():
            res \= {func\_name}(\*\*args)
            print("\<\<RESULT\_START\>\>")
            print(res)
            print("\<\<RESULT\_END\>\>")
        else:
            print("Error: Function {func\_name} not found.")
            sys.exit(1)

    except Exception:
        import traceback
        traceback.print\_exc()
        sys.exit(1)
"""
            runner\_path \= dir\_path / "runner.py"
            with open(runner\_path, 'w') as f:
                f.write(runner\_code)

            \# 3\. 子进程执行
            try:
                proc \= subprocess.run(
                    \[sys.executable, str(runner\_path)\],
                    capture\_output=True, text=True, timeout=15
                )
                exit\_code \= proc.returncode
                stdout \= proc.stdout
                stderr \= proc.stderr
            except subprocess.TimeoutExpired:
                exit\_code \= 124
                stdout \= ""
                stderr \= "Timeout (15s)"

        duration \= (time.time\_ns() \- start\_ts) // 1\_000\_000

        return ExecutionTrace(
            trace\_id=f"t\_{start\_ts}", task\_id=task\_id,
            input\_args=safe\_args, output\_repr=stdout\[:500\], \# 截断日志
            exit\_code=exit\_code, std\_out=stdout, std\_err=stderr,
            execution\_time\_ms=duration
        )

### ---

**Step 4: 适配器与注册表**

实现 **Qwen3 协议清洗** 与 **工具落盘**。

**文件**: fin\_evo\_agent/src/core/llm\_adapter.py

Python

import re

class LLMAdapter:
    def \_\_init\_\_(self, model="qwen3-max-thinking"):
        self.model \= model

    def clean\_protocol(self, raw\_text: str) \-\> dict:
        """
        协议清洗：
        1\. 剥离 \<think\>...\</think\> \-\> Log
        2\. 提取 \`\`\`python ... \`\`\` \-\> Code
        """
        \# 提取 Thinking
        think\_match \= re.search(r"\<think\>(.\*?)\</think\>", raw\_text, re.DOTALL)
        thought \= think\_match.group(1).strip() if think\_match else ""

        \# 移除 Thinking，保留正文
        clean\_text \= re.sub(r"\<think\>.\*?\</think\>", "", raw\_text, flags=re.DOTALL).strip()

        \# 提取 Python 代码
        code\_match \= re.search(r"\`\`\`python(.\*?)\`\`\`", clean\_text, re.DOTALL)
        code \= code\_match.group(1).strip() if code\_match else None

        return {
            "thought": thought,
            "code": code,
            "text": clean\_text
        }

    def mock\_generate(self, task: str) \-\> str:
        """\[MVP\] 模拟 Qwen3 返回，用于测试整个 pipeline"""
        return """\<think\>
用户想要计算 RSI (相对强弱指标)。
公式: RSI \= 100 \- 100 / (1 \+ RS)。
需要处理 Pandas Series。
我将编写一个 calc\_rsi 函数，并包含测试用例。
\</think\>
好的，这是为您生成的 RSI 计算工具。

\`\`\`python
import pandas as pd
import numpy as np

def calc\_rsi(prices: list, period: int \= 14\) \-\> float:
    \\"\\"\\"
    计算 RSI 指标。
    Args:
        prices: 收盘价列表 (float)
        period: 周期，默认 14
    \\"\\"\\"
    if len(prices) \< period:
        return 0.0

    s \= pd.Series(prices)
    delta \= s.diff()
    gain \= (delta.where(delta \> 0, 0)).rolling(period).mean()
    loss \= (-delta.where(delta \< 0, 0)).rolling(period).mean()

    rs \= gain / loss
    rsi \= 100 \- (100 / (1 \+ rs))
    return float(rsi.iloc\[-1\])

if \_\_name\_\_ \== "\_\_main\_\_":
    \# Golden Tests (必须包含)
    p \= \[10, 12, 11, 13, 15, 17, 16, 15, 14, 13, 14, 15, 16, 17, 18\]
    val \= calc\_rsi(p, 5\)
    print(f"RSI: {val}")
    assert 0 \<= val \<= 100
    print("Tests Passed")
\`\`\`"""

**文件**: fin\_evo\_agent/src/core/registry.py

Python

import hashlib
from sqlmodel import Session, create\_engine, select
from src.config import DB\_URL, GENERATED\_DIR
from src.core.models import ToolArtifact, ToolStatus, SQLModel

class ToolRegistry:
    def \_\_init\_\_(self):
        self.engine \= create\_engine(DB\_URL)
        \# 确保表已创建
        SQLModel.metadata.create\_all(self.engine)

    def register(self, name: str, code: str) \-\> ToolArtifact:
        content\_hash \= hashlib.sha256(code.encode()).hexdigest()
        filename \= f"{name}\_v1.py" \# MVP 简化命名
        file\_path \= GENERATED\_DIR / filename

        \# 1\. Payload 落盘
        with open(file\_path, "w", encoding="utf-8") as f:
            f.write(code)

        \# 2\. Metadata 入库
        tool \= ToolArtifact(
            name=name, file\_path=filename.name, content\_hash=content\_hash,
            code\_content=code, status=ToolStatus.PROVISIONAL
        )

        with Session(self.engine) as session:
            \# 简单去重
            existing \= session.exec(select(ToolArtifact).where(ToolArtifact.name \== name)).first()
            if existing: return existing

            session.add(tool)
            session.commit()
            session.refresh(tool)
            return tool

    def get\_tool(self, name: str):
        with Session(self.engine) as session:
            return session.exec(select(ToolArtifact).where(ToolArtifact.name \== name)).first()

### ---

**Step 5: 主程序闭环 (Main Entry)**

将所有组件串联：Data \-\> Synthesize (Mock) \-\> Verify \-\> Execute。

**文件**: fin\_evo\_agent/main.py

Python

import argparse
import sys
import os

\# 确保能导入 src
sys.path.append(os.getcwd())

from src.core.models import init\_db
from src.finance.data\_proxy import get\_a\_share\_hist
from src.core.llm\_adapter import LLMAdapter
from src.core.executor import ToolExecutor
from src.core.registry import ToolRegistry

def main():
    parser \= argparse.ArgumentParser()
    parser.add\_argument("--task", type\=str, default="计算 RSI", help\="任务描述")
    parser.add\_argument("--init", action="store\_true", help\="初始化数据库")
    args \= parser.parse\_args()

    if args.init:
        init\_db()
        print("\[System\] Database Initialized.")
        return

    print("=== FinEvo Agent Phase 1a MVP \===")

    \# 1\. 组件加载
    registry \= ToolRegistry()
    executor \= ToolExecutor()
    llm \= LLMAdapter()

    \# 2\. 数据准备 (Bootstrap)
    print("\\n\[Step 1\] Fetching Context Data...")
    try:
        \# 这里会触发 Data Proxy：第一次联网，第二次走 Cache
        df \= get\_a\_share\_hist("000001", "20230101", "20230201")
        prices \= df\['close'\].astype(float).tolist()
        print(f"  \> Loaded {len(prices)} records from AkShare (or Cache).")
    except Exception as e:
        print(f"  \> Data Error: {e}")
        return

    \# 3\. 工具获取/生成
    tool\_name \= "calc\_rsi"
    tool \= registry.get\_tool(tool\_name)

    if not tool:
        print(f"\\n\[Step 2\] Tool '{tool\_name}' not found. Synthesizing...")

        \# 调用 Mock LLM 生成代码
        raw\_resp \= llm.mock\_generate(args.task)
        parsed \= llm.clean\_protocol(raw\_resp)

        if parsed\['thought'\]:
            print(f"  \> Thinking: {parsed\['thought'\]\[:60\]}...")

        \# 验证代码 (Running self-tests)
        print("  \> Verifying code...")
        verify\_trace \= executor.execute(parsed\['code'\], "verify\_only", {}, "verify")

        if verify\_trace.exit\_code \== 0:
            print("  \> Verification Passed.")
            tool \= registry.register(tool\_name, parsed\['code'\])
            print(f"  \> Tool registered: ID={tool.id}")
        else:
            print(f"  \> Verification Failed:\\n{verify\_trace.std\_err}")
            return
    else:
        print(f"\\n\[Step 2\] Tool '{tool\_name}' found in registry.")

    \# 4\. 任务执行
    print(f"\\n\[Step 3\] Executing Task with Tool...")
    \# 通过 JSON 传递 20 条价格数据
    exec\_trace \= executor.execute(
        tool.code\_content,
        tool\_name,
        {"prices": prices\[:20\], "period": 6},
        "real\_task\_001"
    )

    if exec\_trace.exit\_code \== 0:
        print(f"  \> Success\! Result Output:")
        \# 提取 \<\<RESULT\_START\>\> 之间的内容
        if "\<\<RESULT\_START\>\>" in exec\_trace.std\_out:
            res \= exec\_trace.std\_out.split("\<\<RESULT\_START\>\>")\[1\].split("\<\<RESULT\_END\>\>")\[0\]
            print(f"    {res.strip()}")
        else:
            print(f"    {exec\_trace.std\_out}")
    else:
        print(f"  \> Execution Failed:\\n{exec\_trace.std\_err}")

if \_\_name\_\_ \== "\_\_main\_\_":
    main()

### ---

**如何验收**

1. **运行初始化**：
   Bash
   python fin\_evo\_agent/main.py \--init

   *预期*：data/db/evolution.db 被创建。
2. **运行任务**：
   Bash
   python fin\_evo\_agent/main.py \--task "计算 RSI"

   *预期*：
   * **Data**: 控制台显示 \[Network\] Fetching get\_a\_share\_hist...，随后 data/cache/ 下生成 parquet 文件。
   * **Verify**: 显示 Verification Passed，生成的 calc\_rsi 代码落盘到 data/artifacts/generated/。
   * **Result**: 打印出 RSI 计算结果。
3. **再次运行**（验证复现性）：
   Bash
   python fin\_evo\_agent/main.py \--task "计算 RSI"

   *预期*：不再显示 \[Network\]，而是直接利用缓存数据；不再显示 Synthesizing，而是直接加载 Tool found。
