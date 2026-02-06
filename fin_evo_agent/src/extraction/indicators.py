"""Technical indicator parameter extraction from task descriptions.

Extracts indicator-specific parameters like:
- RSI period
- Moving average window
- Bollinger band parameters
- MACD settings
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class IndicatorParams:
    """Extracted parameters for a technical indicator."""
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


# Default parameters for indicators
DEFAULT_PARAMS: Dict[str, Dict[str, Any]] = {
    "rsi": {"period": 14},
    "ma": {"window": 20},
    "sma": {"window": 20},
    "ema": {"window": 12},
    "macd": {"fast": 12, "slow": 26, "signal": 9},
    "bollinger": {"window": 20, "std": 2},
    "kdj": {"k_period": 9, "d_period": 3},
    "volatility": {"window": 20},
    "drawdown": {},
    "correlation": {},
}

# Parameter extraction patterns
PERIOD_PATTERNS = [
    r'(\d+)\s*(?:日|天|period|day|bar)',
    r'(?:period|周期|窗口|window)[:\s=]*(\d+)',
    r'(\d+)\s*(?:期|周期)',
]

WINDOW_PATTERNS = [
    r'(\d+)\s*(?:日|天|window|day)',
    r'(?:window|窗口)[:\s=]*(\d+)',
    r'(?:ma|均线)\s*(\d+)',
]

STD_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*(?:倍|x|times)?\s*(?:std|标准差|σ)',
    r'(?:std|标准差)[:\s=]*(\d+(?:\.\d+)?)',
]


def extract_period(text: str) -> Optional[int]:
    """Extract period/window parameter from text."""
    for pattern in PERIOD_PATTERNS + WINDOW_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def extract_std_multiplier(text: str) -> Optional[float]:
    """Extract standard deviation multiplier from text."""
    for pattern in STD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def extract_rsi_params(text: str) -> IndicatorParams:
    """Extract RSI parameters."""
    period = extract_period(text) or DEFAULT_PARAMS["rsi"]["period"]

    return IndicatorParams(
        name="rsi",
        params={"period": period},
        confidence=0.9 if extract_period(text) else 0.7,
    )


def extract_ma_params(text: str) -> IndicatorParams:
    """Extract moving average parameters."""
    window = extract_period(text) or DEFAULT_PARAMS["ma"]["window"]

    # Detect MA type
    text_lower = text.lower()
    if 'ema' in text_lower or '指数' in text:
        name = "ema"
    else:
        name = "sma"

    return IndicatorParams(
        name=name,
        params={"window": window},
        confidence=0.9 if extract_period(text) else 0.7,
    )


def extract_macd_params(text: str) -> IndicatorParams:
    """Extract MACD parameters."""
    # MACD typically uses standard parameters unless specified
    params = DEFAULT_PARAMS["macd"].copy()

    # Try to extract custom parameters
    fast_match = re.search(r'(?:fast|快线)[:\s=]*(\d+)', text, re.IGNORECASE)
    slow_match = re.search(r'(?:slow|慢线)[:\s=]*(\d+)', text, re.IGNORECASE)
    signal_match = re.search(r'(?:signal|信号)[:\s=]*(\d+)', text, re.IGNORECASE)

    if fast_match:
        params["fast"] = int(fast_match.group(1))
    if slow_match:
        params["slow"] = int(slow_match.group(1))
    if signal_match:
        params["signal"] = int(signal_match.group(1))

    confidence = 0.9 if (fast_match or slow_match or signal_match) else 0.8

    return IndicatorParams(
        name="macd",
        params=params,
        confidence=confidence,
    )


def extract_bollinger_params(text: str) -> IndicatorParams:
    """Extract Bollinger Bands parameters."""
    window = extract_period(text) or DEFAULT_PARAMS["bollinger"]["window"]
    std = extract_std_multiplier(text) or DEFAULT_PARAMS["bollinger"]["std"]

    confidence = 0.9
    if not extract_period(text):
        confidence -= 0.1
    if not extract_std_multiplier(text):
        confidence -= 0.1

    return IndicatorParams(
        name="bollinger",
        params={"window": window, "std": std},
        confidence=confidence,
    )


def extract_kdj_params(text: str) -> IndicatorParams:
    """Extract KDJ parameters."""
    params = DEFAULT_PARAMS["kdj"].copy()

    k_match = re.search(r'k[:\s=]*(\d+)', text, re.IGNORECASE)
    d_match = re.search(r'd[:\s=]*(\d+)', text, re.IGNORECASE)

    if k_match:
        params["k_period"] = int(k_match.group(1))
    if d_match:
        params["d_period"] = int(d_match.group(1))

    # Also try general period extraction
    if not k_match:
        period = extract_period(text)
        if period:
            params["k_period"] = period

    return IndicatorParams(
        name="kdj",
        params=params,
        confidence=0.8,
    )


def extract_volatility_params(text: str) -> IndicatorParams:
    """Extract volatility parameters."""
    window = extract_period(text) or DEFAULT_PARAMS["volatility"]["window"]

    return IndicatorParams(
        name="volatility",
        params={"window": window},
        confidence=0.9 if extract_period(text) else 0.7,
    )


def extract_correlation_params(text: str) -> IndicatorParams:
    """Extract correlation parameters."""
    # Correlation mainly needs symbols, which are extracted separately
    return IndicatorParams(
        name="correlation",
        params={},
        confidence=0.8,
    )


def extract_drawdown_params(text: str) -> IndicatorParams:
    """Extract drawdown parameters."""
    return IndicatorParams(
        name="drawdown",
        params={},
        confidence=0.9,
    )


# Indicator extractors mapping
INDICATOR_EXTRACTORS = {
    "rsi": extract_rsi_params,
    "ma": extract_ma_params,
    "sma": extract_ma_params,
    "ema": extract_ma_params,
    "macd": extract_macd_params,
    "bollinger": extract_bollinger_params,
    "boll": extract_bollinger_params,
    "kdj": extract_kdj_params,
    "volatility": extract_volatility_params,
    "correlation": extract_correlation_params,
    "drawdown": extract_drawdown_params,
}

# Indicator keywords for detection
INDICATOR_KEYWORDS = {
    "rsi": ["rsi", "相对强弱", "relative strength"],
    "ma": ["moving average", "移动平均", "均线", "ma"],
    "ema": ["ema", "指数移动平均", "exponential"],
    "macd": ["macd", "异同移动平均"],
    "bollinger": ["bollinger", "boll", "布林"],
    "kdj": ["kdj", "stochastic", "随机指标"],
    "volatility": ["volatility", "波动率", "波动性"],
    "correlation": ["correlation", "相关", "corr"],
    "drawdown": ["drawdown", "回撤"],
}


def detect_indicators(text: str) -> List[str]:
    """Detect which indicators are mentioned in text."""
    text_lower = text.lower()
    found = []

    for indicator, keywords in INDICATOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if indicator not in found:
                    found.append(indicator)
                break

    return found


def extract_indicators(text: str) -> List[IndicatorParams]:
    """Extract all indicator parameters from text.

    Args:
        text: Task description text

    Returns:
        List of IndicatorParams for each detected indicator
    """
    indicators = detect_indicators(text)
    results = []

    for indicator in indicators:
        extractor = INDICATOR_EXTRACTORS.get(indicator)
        if extractor:
            params = extractor(text)
            results.append(params)

    return results


if __name__ == "__main__":
    # Test indicator extraction
    test_cases = [
        "计算 AAPL 股票的 14 日 RSI 指标",
        "Calculate 20-day moving average for MSFT",
        "计算 MACD 指标 (fast=12, slow=26, signal=9)",
        "Calculate Bollinger Bands with 20 window and 2 std",
        "计算 AAPL 的 KDJ 随机指标 (k=9, d=3)",
        "计算过去 30 天的波动率",
        "计算最大回撤",
        "计算 AAPL 和 MSFT 的相关系数",
    ]

    print("=== Indicator Extraction Tests ===\n")
    for task in test_cases:
        indicators = extract_indicators(task)
        print(f"Task: {task}")
        for ind in indicators:
            print(f"  {ind.name}: {ind.params} (confidence: {ind.confidence:.2f})")
        if not indicators:
            print("  No indicators detected")
        print()

    print("Indicator extraction tests completed!")
