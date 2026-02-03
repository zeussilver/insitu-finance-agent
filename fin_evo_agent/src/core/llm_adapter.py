"""LLM Adapter for Qwen3-Max-Thinking via DashScope OpenAI-compatible API.

Features:
- Protocol cleaning: Extract thinking trace and code payload
- Code generation with structured prompts
- Support for error context in refinement scenarios
"""

import re
from typing import Optional
from openai import OpenAI

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_ENABLE_THINKING


# System prompt for tool generation
SYSTEM_PROMPT = """You are a financial tool generator. Generate Python functions that:

1. Include complete type hints (e.g., `prices: list`, `period: int = 14`, `-> float`)
2. Include a comprehensive docstring with Args and Returns sections
3. Use ONLY pandas and numpy for calculations - NO talib, NO external indicator libraries
4. Accept price/financial data as function ARGUMENTS (e.g., `prices: list` or `prices: pd.Series`)
5. Do NOT call yfinance, akshare, or any data API inside the function - data is passed IN
6. Return typed results: float for single values, dict for multiple values, bool for conditions
7. Include 2 assert tests in `if __name__ == '__main__':` block using INLINE sample data

Output format:
1. First, explain your reasoning inside <think>...</think> tags
2. Then provide the code inside ```python...``` code block

IMPORTANT:
- Allowed imports: pandas, numpy, datetime, json, math, decimal, collections, re, typing
- FORBIDDEN inside generated tools: yfinance, akshare, talib, requests, urllib
- Never use: os, sys, subprocess, shutil, eval, exec, compile
- Function names should be GENERIC (e.g., `calc_rsi`, not `calc_aapl_rsi`)
- Test data must be INLINE hardcoded lists, NOT fetched from APIs

SECURITY REQUIREMENTS (violations will be BLOCKED and task will FAIL):
- NEVER use: os, sys, subprocess, shutil, builtins, socket, ctypes, pickle
- NEVER call: eval, exec, compile, __import__, getattr, setattr, delattr, open, hasattr
- NEVER access: __class__, __bases__, __subclasses__, __dict__, __globals__, __builtins__
- NEVER use object introspection chains like obj.__class__.__bases__
- NEVER use encoding tricks or obfuscation to bypass security checks
- Code with these patterns will be automatically rejected and the task will fail

EXAMPLE of correct pattern:
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
```
"""


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
                timeout=60.0,
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
        error_context: Optional[str] = None
    ) -> dict:
        """
        Generate tool code using Qwen3.

        Args:
            task: Task description (e.g., "计算 RSI 指标")
            error_context: Previous error traceback for refinement

        Returns:
            {
                "thought_trace": str,
                "code_payload": str,
                "raw_response": str
            }
        """
        # Build user prompt
        user_prompt = f"Task: {task}"
        if error_context:
            user_prompt += f"\n\nPrevious Error:\n{error_context}\n\nFix the issue."

        if self.client is None:
            # Mock only when no API key configured (testing mode)
            raw_response = self._mock_generate(task)
        else:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
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
                    "raw_response": f"LLM API Error: {e}"
                }

        parsed = self._clean_protocol(raw_response)
        return {
            "thought_trace": parsed["thought_trace"],
            "code_payload": parsed["code_payload"],
            "text_response": parsed["text_response"],
            "raw_response": raw_response
        }

    def _mock_generate(self, task: str) -> str:
        """Mock LLM response for testing without API key."""
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
