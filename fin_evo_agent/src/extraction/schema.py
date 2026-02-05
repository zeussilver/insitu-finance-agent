"""Schema extraction from task descriptions.

Deterministic extraction of:
- Required data inputs (symbols, dates, etc.)
- Expected output format (numeric, dict, dataframe, etc.)
- Category classification (fetch, calculation, composite)
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set


@dataclass
class ExtractedSchema:
    """Schema extracted from a task description."""
    category: str  # 'fetch', 'calculation', 'composite'
    required_inputs: Dict[str, Any] = field(default_factory=dict)
    output_type: str = "unknown"  # 'numeric', 'dict', 'dataframe', 'list', 'boolean'
    symbols: List[str] = field(default_factory=list)
    date_range: Optional[Dict[str, str]] = None
    indicators: List[str] = field(default_factory=list)
    confidence: float = 0.0


# Common stock symbols pattern
SYMBOL_PATTERNS = [
    r'\b([A-Z]{1,5})\b(?:\s+(?:stock|ticker|symbol))?',
    r'(?:ticker|symbol|stock)[:\s]+([A-Z]{1,5})',
    r'\'([A-Z]{1,5})\'',
    r'"([A-Z]{1,5})"',
]

# Index patterns
INDEX_PATTERNS = [
    r'(\^[A-Z]{2,10})',  # ^GSPC, ^DJI, etc.
    r'(?:沪深|上证|深证|标普|道琼斯|纳斯达克)',
]

# Date patterns
DATE_PATTERNS = [
    r'(\d{4}-\d{2}-\d{2})',
    r'(\d{4}/\d{2}/\d{2})',
    r'(?:from|start|begin)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2})',
    r'(?:to|end|until)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2})',
]

# Technical indicators
INDICATOR_KEYWORDS: Dict[str, Set[str]] = {
    'rsi': {'rsi', '相对强弱', '相对强弱指数', 'relative strength'},
    'ma': {'ma', 'moving average', '移动平均', 'sma', '均线'},
    'ema': {'ema', 'exponential moving average', '指数移动平均'},
    'macd': {'macd', '异同移动平均'},
    'bollinger': {'bollinger', 'boll', '布林', '布林带', '布林通道'},
    'kdj': {'kdj', 'stochastic', '随机指标'},
    'volatility': {'volatility', '波动率', '波动性', 'std', 'stdev'},
    'drawdown': {'drawdown', '回撤', '最大回撤', 'max drawdown'},
    'correlation': {'correlation', '相关性', '相关系数', 'corr'},
}

# Fetch keywords
FETCH_KEYWORDS = {
    '获取', '查询', '取得', 'fetch', 'get', 'query', 'retrieve',
    '行情', '报价', '价格', '历史', 'price', 'quote', 'historical',
    '财务', 'financial', 'income', 'balance', 'statement',
}

# Calculation keywords
CALC_KEYWORDS = {
    '计算', '算', 'calculate', 'compute', 'calc', '求',
    '指标', 'indicator', '分析', 'analyze', 'analysis',
}

# Composite keywords
COMPOSITE_KEYWORDS = {
    '组合', '综合', '判断', 'combine', 'composite', 'signal',
    '背离', 'divergence', '条件', 'conditional', '策略', 'strategy',
}


def extract_symbols(text: str) -> List[str]:
    """Extract stock/index symbols from text."""
    symbols = set()

    # Common known symbols
    known_symbols = {'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA'}

    for pattern in SYMBOL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            upper_match = match.upper()
            if upper_match in known_symbols or len(upper_match) <= 5:
                symbols.add(upper_match)

    # Index symbols
    for pattern in INDEX_PATTERNS:
        matches = re.findall(pattern, text)
        symbols.update(matches)

    return list(symbols)


def extract_dates(text: str) -> Optional[Dict[str, str]]:
    """Extract date range from text."""
    dates = []

    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        dates.extend(matches)

    # Normalize date format
    normalized = []
    for date in dates:
        normalized.append(date.replace('/', '-'))

    if len(normalized) >= 2:
        normalized.sort()
        return {"start": normalized[0], "end": normalized[-1]}
    elif len(normalized) == 1:
        return {"start": normalized[0], "end": normalized[0]}

    return None


def extract_indicators_from_text(text: str) -> List[str]:
    """Extract technical indicator names from text."""
    text_lower = text.lower()
    found = []

    for indicator, keywords in INDICATOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if indicator not in found:
                    found.append(indicator)
                break

    return found


def classify_category(text: str) -> str:
    """Classify task into category based on keywords."""
    text_lower = text.lower()

    # Check for composite first (needs multiple criteria)
    composite_score = sum(1 for kw in COMPOSITE_KEYWORDS if kw in text_lower)

    # Check for fetch
    fetch_score = sum(1 for kw in FETCH_KEYWORDS if kw in text_lower)

    # Check for calculation
    calc_score = sum(1 for kw in CALC_KEYWORDS if kw in text_lower)

    # Also check for indicators (implies calculation)
    if extract_indicators_from_text(text):
        calc_score += 2

    # Decision logic
    if composite_score >= 2:
        return "composite"
    if fetch_score > calc_score:
        return "fetch"
    if calc_score > 0:
        return "calculation"
    if fetch_score > 0:
        return "fetch"

    # Default based on content
    if any(kw in text_lower for kw in ['历史', 'historical', '数据', 'data']):
        return "fetch"

    return "calculation"


def infer_output_type(text: str, category: str, indicators: List[str]) -> str:
    """Infer expected output type."""
    text_lower = text.lower()

    # Boolean indicators
    if any(kw in text_lower for kw in ['是否', '判断', 'whether', 'is', 'signal', 'check']):
        return "boolean"

    # List/multiple results
    if any(kw in text_lower for kw in ['列表', 'list', '多个', 'multiple', '所有', 'all']):
        return "list"

    # DataFrame for fetch or complex data
    if category == "fetch" or any(kw in text_lower for kw in ['历史', 'historical', 'dataframe']):
        return "dataframe"

    # Dict for structured results
    if any(kw in text_lower for kw in ['详情', 'details', '信息', 'info', 'quote']):
        return "dict"

    # Single indicator usually returns numeric
    if indicators and len(indicators) == 1:
        return "numeric"

    # Multiple indicators return dict
    if indicators and len(indicators) > 1:
        return "dict"

    return "numeric"


def extract_schema(task_description: str) -> ExtractedSchema:
    """Extract schema from task description.

    Args:
        task_description: Natural language task description

    Returns:
        ExtractedSchema with extracted information
    """
    # Extract components
    symbols = extract_symbols(task_description)
    date_range = extract_dates(task_description)
    indicators = extract_indicators_from_text(task_description)
    category = classify_category(task_description)
    output_type = infer_output_type(task_description, category, indicators)

    # Build required inputs
    required_inputs = {}
    if symbols:
        required_inputs["symbol"] = symbols[0] if len(symbols) == 1 else symbols
    if date_range:
        required_inputs["start"] = date_range["start"]
        required_inputs["end"] = date_range["end"]

    # Calculate confidence
    confidence = 0.0
    if symbols:
        confidence += 0.3
    if date_range:
        confidence += 0.2
    if indicators:
        confidence += 0.3
    if category != "calculation":  # explicit category match
        confidence += 0.2

    return ExtractedSchema(
        category=category,
        required_inputs=required_inputs,
        output_type=output_type,
        symbols=symbols,
        date_range=date_range,
        indicators=indicators,
        confidence=min(confidence, 1.0),
    )


if __name__ == "__main__":
    # Test schema extraction
    test_cases = [
        "获取 AAPL 股票从 2023-01-01 到 2023-01-31 的历史数据",
        "计算 AAPL 股票的 14 日 RSI 指标",
        "Calculate the moving average for MSFT with window 20",
        "判断 AAPL 是否出现 MACD 和 RSI 背离信号",
        "Get TSLA financial information",
        "计算 AAPL 和 MSFT 的相关系数",
    ]

    print("=== Schema Extraction Tests ===\n")
    for task in test_cases:
        schema = extract_schema(task)
        print(f"Task: {task}")
        print(f"  Category: {schema.category}")
        print(f"  Symbols: {schema.symbols}")
        print(f"  Date Range: {schema.date_range}")
        print(f"  Indicators: {schema.indicators}")
        print(f"  Output Type: {schema.output_type}")
        print(f"  Confidence: {schema.confidence:.2f}")
        print()

    print("Schema extraction tests completed!")
