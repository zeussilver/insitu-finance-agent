"""LLM Adapter for Qwen3-Max-Thinking via DashScope OpenAI-compatible API.

Features:
- Protocol cleaning: Extract thinking trace and code payload
- Code generation with structured prompts
- Support for error context in refinement scenarios
"""

import re
from typing import Optional, TYPE_CHECKING
from openai import OpenAI

if TYPE_CHECKING:
    from src.core.contracts import ToolContract

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_ENABLE_THINKING, LLM_TIMEOUT


# === Category-Specific System Prompts ===

# Default/Calculation prompt - for pure computation tools
CALCULATE_SYSTEM_PROMPT = """You are a financial calculation tool generator. Generate Python functions that:

1. Include complete type hints (e.g., `prices: list`, `period: int = 14`, `-> float`)
2. Include a comprehensive docstring with Args and Returns sections
3. Use ONLY pandas and numpy for calculations - NO talib, NO external indicator libraries
4. Accept price/financial data as function ARGUMENTS (e.g., `prices: list` or `prices: pd.Series`)
5. Return typed results: float for single values, dict for multiple values, bool for conditions
6. Include 2 assert tests in `if __name__ == '__main__':` block using INLINE sample data

Output format:
1. First, explain your reasoning inside <think>...</think> tags
2. Then provide the code inside ```python...``` code block

═══════════════════════════════════════════════════════════════════════════════
CRITICAL CONSTRAINT - READ CAREFULLY - YOUR CODE WILL BE REJECTED IF VIOLATED:
═══════════════════════════════════════════════════════════════════════════════

Calculation tools CANNOT fetch data. You MUST NOT import or use:
  ❌ yfinance (import yfinance, import yfinance as yf, yf.Ticker, etc.)
  ❌ requests, urllib, httpx, aiohttp, akshare
  ❌ Any network library whatsoever

WHY: Calculation tools perform PURE COMPUTATIONS on data PASSED IN as arguments.
Data fetching is done by separate "fetch" tools BEFORE your function is called.

Your function will receive data like this:
  calc_rsi(prices=[100, 101, 102, ...], period=14)

NOT like this (WRONG - will be BLOCKED):
  calc_rsi(symbol="AAPL", period=14)  # Then fetches data internally - WRONG!

═══════════════════════════════════════════════════════════════════════════════

IMPORTANT - Parameter Naming Convention (MUST follow exactly):
- For single price series: use `prices` (list of floats)
- For OHLCV data: use `high`, `low`, `close`, `volume` (each a list of floats)
- For correlation: use `prices1` and `prices2` (both lists of floats)
- For period/window parameters: use `period` or `window` (int)
- Do NOT use custom names like `aapl_prices`, `stock_prices`, `data`, etc.

For dict outputs (like KDJ, Bollinger, MACD), use lowercase keys:
- KDJ: {'k': ..., 'd': ..., 'j': ...} NOT {'K': ..., 'D': ..., 'J': ...}
- Bollinger: {'upper': ..., 'middle': ..., 'lower': ...}
- MACD: {'macd': ..., 'signal': ..., 'histogram': ...}

ALLOWED IMPORTS (only these):
- pandas, numpy, datetime, json, math, decimal, collections, re, typing

FORBIDDEN IMPORTS (code will be BLOCKED):
- yfinance, akshare, talib, requests, urllib, httpx, aiohttp
- os, sys, subprocess, shutil, socket, ctypes, pickle

Function names should be GENERIC (e.g., `calc_rsi`, not `calc_aapl_rsi`)
Test data must be INLINE hardcoded lists, NOT fetched from APIs

SECURITY REQUIREMENTS (violations will be BLOCKED and task will FAIL):
- NEVER use: os, sys, subprocess, shutil, builtins, socket, ctypes, pickle
- NEVER call: eval, exec, compile, __import__, getattr, setattr, delattr, open, hasattr
- NEVER access: __class__, __bases__, __subclasses__, __dict__, __globals__, __builtins__
- Code with these patterns will be automatically rejected

EXAMPLE of correct calculation pattern:
```python
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    \"\"\"Calculate RSI indicator.

    Args:
        prices: List of closing prices
        period: RSI period (default 14)

    Returns:
        RSI value between 0 and 100
    \"\"\"
    if len(prices) < period + 1:
        return 50.0  # Return neutral value for insufficient data

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

if __name__ == "__main__":
    test_prices = [44, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45, 45.5, 46]
    result = calc_rsi(test_prices, 5)
    assert 0 <= result <= 100
    print("Test passed!")
```
"""


# Fetch prompt - for tools that fetch data from yfinance
FETCH_SYSTEM_PROMPT = """You are a financial data fetcher tool generator. Generate Python functions that:

1. Use yfinance to fetch real market data
2. Include complete type hints and comprehensive docstring
3. Handle errors gracefully (network issues, invalid symbols)
4. Include 2 assert tests in `if __name__ == '__main__':` block

Output format:
1. First, explain your reasoning inside <think>...</think> tags
2. Then provide the code inside ```python...``` code block

═══════════════════════════════════════════════════════════════════════════════
CRITICAL - RETURN TYPE MUST MATCH THE TASK:
═══════════════════════════════════════════════════════════════════════════════

Different tasks require different return types. Match your return type to the task:

| Task Type                    | Return Type    | Example                          |
|------------------------------|----------------|----------------------------------|
| "获取市值/revenue/财务数据"   | float          | return 2500000000000.0           |
| "获取股价/close price/quote" | float          | return 185.50                    |
| "获取历史OHLCV数据"          | pd.DataFrame   | return df[['Date','Close',...]]  |
| "获取公司信息/简介"          | dict           | return {'name': ..., 'sector':..}|

WRONG (will fail contract validation):
  Task: "获取AAPL的市值"
  Return: DataFrame with all historical data  # ❌ Should return float!

CORRECT:
  Task: "获取AAPL的市值"
  Return: float(ticker.info.get('marketCap', 0))  # ✅ Returns numeric value

═══════════════════════════════════════════════════════════════════════════════

IMPORTANT:
- Allowed imports: pandas, numpy, datetime, json, yfinance, hashlib, typing, warnings
- FORBIDDEN: os, sys, subprocess, shutil, eval, exec, compile, urllib3, requests, aiohttp, httpx
- For warning suppression (e.g., yfinance SSL warnings), use: import warnings; warnings.filterwarnings('ignore')
- Handle edge cases: invalid symbols, empty data, network timeouts
- Return clear error indicators (None, 0.0, empty DataFrame) rather than raising exceptions

SECURITY REQUIREMENTS (violations will be BLOCKED and task will FAIL):
- NEVER use: os, sys, subprocess, shutil, builtins, socket, ctypes, pickle
- NEVER call: eval, exec, compile, __import__, getattr, setattr, delattr, open, hasattr
- NEVER access: __class__, __bases__, __subclasses__, __dict__, __globals__, __builtins__
- Code with these patterns will be automatically rejected

EXAMPLE 1 - Fetching a SINGLE VALUE (market cap, price, etc.):
```python
import yfinance as yf
from typing import Optional

def get_market_cap(symbol: str) -> float:
    \"\"\"Fetch stock market capitalization.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Market cap as a float, or 0.0 if unavailable
    \"\"\"
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return float(info.get('marketCap', 0))
    except Exception:
        return 0.0

if __name__ == "__main__":
    cap = get_market_cap('AAPL')
    assert isinstance(cap, float), "Should return float"
    assert cap > 0, "AAPL should have positive market cap"
    print("Test passed!")
```

EXAMPLE 2 - Fetching HISTORICAL DATA (OHLCV DataFrame):
```python
import yfinance as yf
import pandas as pd
from typing import Optional

def get_stock_hist(symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
    \"\"\"Fetch stock historical OHLCV data.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format

    Returns:
        DataFrame with Date, Open, High, Low, Close, Volume columns
        None if fetch fails
    \"\"\"
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end)
        if df.empty:
            return None
        df = df.reset_index()
        return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception:
        return None

if __name__ == "__main__":
    df = get_stock_hist('AAPL', '2023-01-01', '2023-01-10')
    assert df is not None, "Should return data for valid symbol"
    assert 'Close' in df.columns, "Should have Close column"
    print("Test passed!")
```
"""


# Composite prompt - for tools combining multiple operations
COMPOSITE_SYSTEM_PROMPT = """You are a financial composite tool generator. Generate Python functions that:

1. Combine multiple calculations or conditions
2. Accept all necessary data as function ARGUMENTS (prices, volumes, etc.)
3. Return clear results: bool for conditions, float/dict for calculations
4. Include type hints and comprehensive docstring
5. Include 2 assert tests in `if __name__ == '__main__':` block

Output format:
1. First, explain your reasoning inside <think>...</think> tags
2. Then provide the code inside ```python...``` code block

═══════════════════════════════════════════════════════════════════════════════
CRITICAL CONSTRAINT - READ CAREFULLY - YOUR CODE WILL BE REJECTED IF VIOLATED:
═══════════════════════════════════════════════════════════════════════════════

Composite tools CANNOT fetch data. You MUST NOT import or use:
  ❌ yfinance (import yfinance, import yfinance as yf, yf.Ticker, etc.)
  ❌ requests, urllib, httpx, aiohttp, akshare
  ❌ Any network library whatsoever

WHY: Composite tools COMPOSE calculations on data that is PASSED IN as arguments.
Data fetching is done by separate "fetch" tools BEFORE your function is called.

Your function will receive data like this:
  my_composite_tool(prices=[100, 101, 102, ...], volumes=[1000, 1200, ...])

NOT like this (WRONG - will be BLOCKED):
  my_composite_tool(symbol="AAPL")  # Then fetches data internally - WRONG!

═══════════════════════════════════════════════════════════════════════════════

IMPORTANT - Parameter Naming Convention (MUST follow exactly):
- For price data: use `prices` (list of floats)
- For volume data: use `volumes` (list of floats) - note the 's'
- For multiple price series: use `prices1`, `prices2`, `prices3` etc.
- For portfolio tasks: accept a dict parameter `symbol_prices` mapping symbol to price list
- Do NOT use symbol-specific names like `aapl_prices`, `msft_prices`

For dict outputs, use lowercase keys:
- Example: {'k': ..., 'd': ..., 'j': ...} NOT {'K': ..., 'D': ..., 'J': ...}

ALLOWED IMPORTS (only these):
- pandas, numpy, datetime, json, math, decimal, collections, re, typing

FORBIDDEN IMPORTS (code will be BLOCKED):
- yfinance, akshare, talib, requests, urllib, httpx, aiohttp
- os, sys, subprocess, shutil, socket, ctypes, pickle

SECURITY REQUIREMENTS (violations will be BLOCKED and task will FAIL):
- NEVER use: os, sys, subprocess, shutil, builtins, socket, ctypes, pickle
- NEVER call: eval, exec, compile, __import__, getattr, setattr, delattr, open, hasattr
- NEVER access: __class__, __bases__, __subclasses__, __dict__, __globals__, __builtins__

EXAMPLE of correct composite pattern:
```python
import pandas as pd
import numpy as np

def check_ma_crossover_with_rsi(
    prices: list,
    short_window: int = 5,
    long_window: int = 20,
    rsi_period: int = 14,
    rsi_threshold: float = 30
) -> bool:
    \"\"\"Check if MA5>MA20 and RSI<threshold (buy signal).

    Args:
        prices: List of closing prices (PASSED IN, not fetched)
        short_window: Short MA period (default 5)
        long_window: Long MA period (default 20)
        rsi_period: RSI calculation period (default 14)
        rsi_threshold: RSI threshold for oversold (default 30)

    Returns:
        True if MA5>MA20 and RSI<threshold, False otherwise
    \"\"\"
    if len(prices) < max(long_window, rsi_period + 1):
        return False

    s = pd.Series(prices)

    # Calculate MAs
    ma_short = s.rolling(window=short_window).mean().iloc[-1]
    ma_long = s.rolling(window=long_window).mean().iloc[-1]

    # Calculate RSI
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_period).mean().iloc[-1]
    avg_loss = loss.rolling(window=rsi_period).mean().iloc[-1]
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    return ma_short > ma_long and rsi < rsi_threshold

if __name__ == "__main__":
    # Test case 1: Uptrend with low RSI - uses INLINE data, no API calls
    prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 85, 88, 91]
    result = check_ma_crossover_with_rsi(prices, 5, 20, 14, 30)
    assert isinstance(result, bool), "Should return boolean"
    print("Test passed!")
```
"""


# Mapping from category to prompt
PROMPT_BY_CATEGORY = {
    'fetch': FETCH_SYSTEM_PROMPT,
    'calculation': CALCULATE_SYSTEM_PROMPT,
    'composite': COMPOSITE_SYSTEM_PROMPT,
}

# Default system prompt (for backward compatibility)
SYSTEM_PROMPT = CALCULATE_SYSTEM_PROMPT


class LLMAdapter:
    """Qwen3 adapter with protocol cleaning."""

    def __init__(
        self,
        model: str = LLM_MODEL,
        temperature: float = LLM_TEMPERATURE,
        enable_thinking: bool = LLM_ENABLE_THINKING
    ):
        self.model = model
        self.temperature = temperature
        self.enable_thinking = enable_thinking

        if LLM_API_KEY:
            self.client = OpenAI(
                api_key=LLM_API_KEY,
                base_url=LLM_BASE_URL,
                timeout=float(LLM_TIMEOUT),
            )
        else:
            self.client = None

    def _clean_protocol(self, raw_content: str) -> dict:
        """
        Clean LLM response protocol.

        Extracts:
        - thought_trace: Content inside <think>...</think>
        - code_payload: Content inside ```python...```
        - text_response: Cleaned text without thinking tags

        Returns:
            {
                "thought_trace": str,
                "code_payload": str,
                "text_response": str
            }
        """
        # Extract thinking trace
        think_match = re.search(r"<think>(.*?)</think>", raw_content, re.DOTALL)
        thought_trace = think_match.group(1).strip() if think_match else ""

        # Remove thinking tags for clean text
        text_response = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()

        # Extract Python code block
        code_match = re.search(r"```python(.*?)```", text_response, re.DOTALL)
        code_payload = code_match.group(1).strip() if code_match else None

        return {
            "thought_trace": thought_trace,
            "code_payload": code_payload,
            "text_response": text_response
        }

    def generate_tool_code(
        self,
        task: str,
        error_context: Optional[str] = None,
        category: Optional[str] = None,
        contract: Optional['ToolContract'] = None
    ) -> dict:
        """
        Generate tool code using Qwen3.

        Args:
            task: Task description (e.g., "计算 RSI 指标")
            error_context: Previous error traceback for refinement
            category: Tool category ('fetch', 'calculation', 'composite')
                      Used to select appropriate system prompt
            contract: Optional contract defining expected output type

        Returns:
            {
                "thought_trace": str,
                "code_payload": str,
                "raw_response": str,
                "category": str
            }
        """
        # Select appropriate system prompt based on category
        if category and category in PROMPT_BY_CATEGORY:
            system_prompt = PROMPT_BY_CATEGORY[category]
        else:
            # Infer category from task keywords
            task_lower = task.lower()
            if any(kw in task_lower for kw in ['fetch', 'get', '获取', '查询', 'price', 'quote']):
                if any(kw in task_lower for kw in ['calculate', 'calc', '计算', 'rsi', 'macd', 'bollinger']):
                    # Calculation task that needs data - use calculation prompt
                    category = 'calculation'
                else:
                    category = 'fetch'
            elif any(kw in task_lower for kw in ['if ', 'return true', 'return false', 'signal', 'divergence', 'portfolio']):
                category = 'composite'
            else:
                category = 'calculation'
            system_prompt = PROMPT_BY_CATEGORY.get(category, SYSTEM_PROMPT)

        # Build user prompt
        user_prompt = f"Task: {task}"

        # Add contract constraint (H-6 fix: stronger binding with enforcement framing)
        if contract:
            constraint = self._format_output_constraint(contract)
            if constraint:
                user_prompt += (
                    f"\n\n═══ MANDATORY OUTPUT CONTRACT ═══\n"
                    f"{constraint}\n"
                    f"Your code WILL BE REJECTED if the return type does not match this contract.\n"
                    f"═════════════════════════════════"
                )

        if error_context:
            user_prompt += f"\n\nPrevious Error:\n{error_context}\n\nFix the issue."

        if self.client is None:
            # Mock only when no API key configured (testing mode)
            raw_response = self._mock_generate(task, category)
        else:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    extra_body={"enable_thinking": self.enable_thinking}
                )
                raw_response = completion.choices[0].message.content
            except Exception as e:
                # API error or timeout - return error result, don't mask with mock
                print(f"[LLM Error] {e}")
                return {
                    "thought_trace": "",
                    "code_payload": None,
                    "text_response": f"LLM API Error: {e}",
                    "raw_response": f"LLM API Error: {e}",
                    "category": category
                }

        parsed = self._clean_protocol(raw_response)
        return {
            "thought_trace": parsed["thought_trace"],
            "code_payload": parsed["code_payload"],
            "text_response": parsed["text_response"],
            "raw_response": raw_response,
            "category": category
        }

    def _format_output_constraint(self, contract: 'ToolContract') -> str:
        """Format contract as ultra-minimal output constraint for LLM."""
        output_type = contract.output_type.value if hasattr(contract.output_type, 'value') else str(contract.output_type)

        if output_type == "numeric":
            return "Return a single float. Do NOT return dict/DataFrame/list."
        elif output_type == "dict":
            keys = getattr(contract, 'required_keys', None) or []
            if keys:
                return f"Return a dict with keys: {keys}. Do NOT return DataFrame/list."
            return "Return a dict. Do NOT return DataFrame/list."
        elif output_type == "boolean":
            return "Return True or False. Do NOT return 0/1 or string."
        elif output_type == "dataframe":
            keys = getattr(contract, 'required_keys', None) or []
            if keys:
                return f"Return a DataFrame with columns: {keys}."
            return "Return a DataFrame."
        elif output_type == "list":
            return "Return a list. Do NOT return dict/DataFrame."
        return ""

    def _mock_generate(self, task: str, category: str = None) -> str:
        """Mock LLM response for testing without API key."""
        task_lower = task.lower()

        # Mock for fetch tasks
        if category == 'fetch' or any(kw in task_lower for kw in ['fetch', 'get stock', 'get etf', 'get index', 'close price']):
            return '''<think>
用户需要获取股票数据。我将使用 yfinance 来获取历史数据。
需要处理网络错误和空数据情况。
</think>

好的，这是获取股票数据的工具。

```python
import yfinance as yf
import pandas as pd
from typing import Optional

def get_stock_hist(symbol: str, start: str = "2023-01-01", end: str = "2023-12-31") -> Optional[pd.DataFrame]:
    """
    获取股票历史 OHLCV 数据。

    Args:
        symbol: 股票代码 (e.g., 'AAPL')
        start: 开始日期 YYYY-MM-DD
        end: 结束日期 YYYY-MM-DD

    Returns:
        DataFrame with Date, Open, High, Low, Close, Volume
        None if fetch fails
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end)
        if df.empty:
            return None
        df = df.reset_index()
        return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception:
        return None


if __name__ == "__main__":
    # Mock test - just verify function exists and runs
    print("Test passed!")
```'''

        # Mock for composite/condition tasks
        if category == 'composite' or any(kw in task_lower for kw in ['if ', 'return true', 'signal', 'divergence']):
            return '''<think>
用户需要一个组合条件判断工具。
需要计算多个指标并返回布尔值。
</think>

好的，这是组合条件判断工具。

```python
import pandas as pd
import numpy as np

def check_trading_signal(prices: list, volume: list = None) -> bool:
    """
    检查交易信号条件。

    Args:
        prices: 收盘价列表
        volume: 成交量列表 (可选)

    Returns:
        True if signal condition met, False otherwise
    """
    if len(prices) < 20:
        return False

    s = pd.Series(prices)
    ma5 = s.rolling(5).mean().iloc[-1]
    ma20 = s.rolling(20).mean().iloc[-1]

    return ma5 > ma20


if __name__ == "__main__":
    prices = list(range(100, 125))
    result = check_trading_signal(prices)
    assert isinstance(result, bool)
    print("Test passed!")
```'''

        # Default mock for calculation tasks
        return '''<think>
用户想要计算 RSI (相对强弱指标)。
公式: RSI = 100 - 100 / (1 + RS)
其中 RS = 平均涨幅 / 平均跌幅
需要处理 Pandas Series，使用滚动窗口计算。
我将编写一个 calc_rsi 函数，并包含测试用例。
</think>

好的，这是为您生成的 RSI 计算工具。

```python
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """
    计算 RSI (相对强弱指标)。

    Args:
        prices: 收盘价列表 (float)
        period: 计算周期，默认 14

    Returns:
        RSI 值 (0-100 之间的浮点数)
    """
    if len(prices) < period + 1:
        return 50.0  # 数据不足时返回中性值

    s = pd.Series(prices)
    delta = s.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # 避免除以零
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


if __name__ == "__main__":
    # Test case 1: Normal data
    prices = [10, 12, 11, 13, 15, 17, 16, 15, 14, 13, 14, 15, 16, 17, 18]
    val = calc_rsi(prices, 5)
    print(f"RSI: {val}")
    assert 0 <= val <= 100, f"RSI should be between 0 and 100, got {val}"

    # Test case 2: Insufficient data
    short_prices = [10, 11, 12]
    val2 = calc_rsi(short_prices, 14)
    assert val2 == 50.0, f"Should return 50.0 for insufficient data, got {val2}"

    print("All tests passed!")
```'''


if __name__ == "__main__":
    # Test the adapter
    adapter = LLMAdapter()

    # Test protocol cleaning
    test_input = '''<think>
我需要计算 RSI 指标...
步骤1: 获取价格数据
步骤2: 计算涨跌幅
</think>

```python
def calc_rsi(prices, period=14):
    pass
```
'''

    result = adapter._clean_protocol(test_input)
    print(f"thought_trace: {bool(result['thought_trace'])}")
    print(f"code_payload: {bool(result['code_payload'])}")
    print(f"text_response contains <think>: {'<think>' in result['text_response']}")

    # Test code generation (mock)
    print("\nTesting code generation (mock)...")
    gen_result = adapter.generate_tool_code("计算 RSI 指标")
    print(f"Generated code length: {len(gen_result['code_payload'] or '')}")
