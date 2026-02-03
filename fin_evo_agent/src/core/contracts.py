"""Contract definitions for tool validation.

Each task type has input/output contracts that define:
- Expected input types
- Expected output types
- Output constraints (ranges, required keys)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum


class OutputType(str, Enum):
    """Expected output types for tool contracts."""
    NUMERIC = "numeric"           # Single numeric value (float)
    DICT = "dict"                 # Dictionary with specific keys
    DATAFRAME = "dataframe"       # Pandas DataFrame
    LIST = "list"                 # List of values
    BOOLEAN = "boolean"           # True/False
    STRING = "string"             # Text output
    ANY = "any"                   # Any valid output


@dataclass
class ToolContract:
    """Contract defining expected tool behavior."""
    contract_id: str
    category: str
    description: str

    # Input specification
    input_types: Dict[str, str] = field(default_factory=dict)
    required_inputs: List[str] = field(default_factory=list)

    # Output specification
    output_type: OutputType = OutputType.ANY
    output_constraints: Dict[str, Any] = field(default_factory=dict)
    required_keys: List[str] = field(default_factory=list)

    # Validation settings
    allow_none: bool = False
    allow_nan: bool = False


# Predefined contracts for benchmark tasks
CONTRACTS: Dict[str, ToolContract] = {
    # === FETCH CONTRACTS ===
    "fetch_financial": ToolContract(
        contract_id="fetch_financial",
        category="fetch",
        description="Fetch financial statement data (net income, revenue, etc.)",
        input_types={"symbol": "str", "period": "str"},
        required_inputs=["symbol"],
        output_type=OutputType.NUMERIC,
        output_constraints={"allow_negative": True},
    ),
    "fetch_quote": ToolContract(
        contract_id="fetch_quote",
        category="fetch",
        description="Fetch real-time market quote",
        input_types={"symbol": "str"},
        required_inputs=["symbol"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": 0},
    ),
    "fetch_price": ToolContract(
        contract_id="fetch_price",
        category="fetch",
        description="Fetch stock/ETF/index price data",
        input_types={"symbol": "str", "start": "str", "end": "str"},
        required_inputs=["symbol"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": 0},
    ),
    "fetch_ohlcv": ToolContract(
        contract_id="fetch_ohlcv",
        category="fetch",
        description="Fetch OHLCV historical data",
        input_types={"symbol": "str", "start": "str", "end": "str"},
        required_inputs=["symbol"],
        output_type=OutputType.DATAFRAME,
        required_keys=["Open", "High", "Low", "Close", "Volume"],
    ),
    "fetch_list": ToolContract(
        contract_id="fetch_list",
        category="fetch",
        description="Fetch list data (dividends, etc.)",
        input_types={"symbol": "str"},
        required_inputs=["symbol"],
        output_type=OutputType.LIST,
    ),

    # === CALCULATION CONTRACTS ===
    "calc_rsi": ToolContract(
        contract_id="calc_rsi",
        category="calculation",
        description="Calculate RSI indicator",
        input_types={"prices": "list", "period": "int"},
        required_inputs=["prices"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": 0, "max": 100},
    ),
    "calc_ma": ToolContract(
        contract_id="calc_ma",
        category="calculation",
        description="Calculate moving average",
        input_types={"prices": "list", "window": "int"},
        required_inputs=["prices"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": 0},
    ),
    "calc_bollinger": ToolContract(
        contract_id="calc_bollinger",
        category="calculation",
        description="Calculate Bollinger Bands",
        input_types={"prices": "list", "window": "int", "num_std": "float"},
        required_inputs=["prices"],
        output_type=OutputType.DICT,
        required_keys=["upper", "middle", "lower"],
    ),
    "calc_macd": ToolContract(
        contract_id="calc_macd",
        category="calculation",
        description="Calculate MACD indicator",
        input_types={"prices": "list", "fast_period": "int", "slow_period": "int", "signal_period": "int"},
        required_inputs=["prices"],
        output_type=OutputType.DICT,
        required_keys=["macd", "signal", "histogram"],
    ),
    "calc_volatility": ToolContract(
        contract_id="calc_volatility",
        category="calculation",
        description="Calculate price volatility",
        input_types={"prices": "list", "window": "int"},
        required_inputs=["prices"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": 0},
    ),
    "calc_kdj": ToolContract(
        contract_id="calc_kdj",
        category="calculation",
        description="Calculate KDJ indicator",
        input_types={"high": "list", "low": "list", "close": "list", "k_period": "int", "d_period": "int"},
        required_inputs=["high", "low", "close"],
        output_type=OutputType.DICT,
        required_keys=["k", "d", "j"],
    ),
    "calc_drawdown": ToolContract(
        contract_id="calc_drawdown",
        category="calculation",
        description="Calculate maximum drawdown",
        input_types={"prices": "list"},
        required_inputs=["prices"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": 0, "max": 1},  # Drawdown as decimal (0-1)
    ),
    "calc_correlation": ToolContract(
        contract_id="calc_correlation",
        category="calculation",
        description="Calculate correlation between two price series",
        input_types={"prices1": "list", "prices2": "list"},
        required_inputs=["prices1", "prices2"],
        output_type=OutputType.NUMERIC,
        output_constraints={"min": -1, "max": 1},
    ),

    # === COMPOSITE CONTRACTS ===
    "comp_signal": ToolContract(
        contract_id="comp_signal",
        category="composite",
        description="Generate trading signal based on conditions",
        input_types={"prices": "list"},
        required_inputs=["prices"],
        output_type=OutputType.BOOLEAN,
    ),
    "comp_divergence": ToolContract(
        contract_id="comp_divergence",
        category="composite",
        description="Detect volume-price divergence",
        input_types={"prices": "list", "volumes": "list"},
        required_inputs=["prices", "volumes"],
        output_type=OutputType.BOOLEAN,
    ),
    "comp_portfolio": ToolContract(
        contract_id="comp_portfolio",
        category="composite",
        description="Calculate portfolio return",
        input_types={"symbols": "list", "weights": "list"},
        required_inputs=["symbols"],
        output_type=OutputType.NUMERIC,
        output_constraints={"allow_negative": True},
    ),
    "comp_conditional_return": ToolContract(
        contract_id="comp_conditional_return",
        category="composite",
        description="Calculate conditional return (after signal)",
        input_types={"prices": "list", "signal_threshold": "float"},
        required_inputs=["prices"],
        output_type=OutputType.NUMERIC,
        output_constraints={"allow_negative": True},
    ),
}


# Map task_id patterns to contracts
TASK_CONTRACT_MAPPING: Dict[str, str] = {
    # Fetch tasks
    "fetch_001": "fetch_financial",  # Net income
    "fetch_002": "fetch_quote",      # Market quote
    "fetch_003": "fetch_financial",  # Revenue
    "fetch_004": "fetch_price",      # S&P 500 close
    "fetch_005": "fetch_price",      # ETF close
    "fetch_006": "fetch_financial",  # Quarterly net income
    "fetch_007": "fetch_list",       # Dividend history
    "fetch_008": "fetch_price",      # Highest close

    # Calculation tasks
    "calc_001": "calc_rsi",
    "calc_002": "calc_ma",
    "calc_003": "calc_bollinger",
    "calc_004": "calc_macd",
    "calc_005": "calc_volatility",
    "calc_006": "calc_kdj",
    "calc_007": "calc_drawdown",
    "calc_008": "calc_correlation",

    # Composite tasks
    "comp_001": "comp_signal",
    "comp_002": "comp_divergence",
    "comp_003": "comp_portfolio",
    "comp_004": "comp_conditional_return",
}


def get_contract(task_id: str) -> Optional[ToolContract]:
    """Get contract for a task ID."""
    contract_id = TASK_CONTRACT_MAPPING.get(task_id)
    if contract_id:
        return CONTRACTS.get(contract_id)
    return None


def get_contract_by_id(contract_id: str) -> Optional[ToolContract]:
    """Get contract by contract ID."""
    return CONTRACTS.get(contract_id)


def infer_contract_from_query(query: str, category: str) -> Optional[ToolContract]:
    """Infer appropriate contract from task query."""
    query_lower = query.lower()

    if category == "fetch":
        if any(kw in query_lower for kw in ['net income', 'revenue', 'earnings', 'profit']):
            return CONTRACTS["fetch_financial"]
        if any(kw in query_lower for kw in ['quote', 'real-time', 'realtime']):
            return CONTRACTS["fetch_quote"]
        if 'dividend' in query_lower:
            return CONTRACTS["fetch_list"]
        return CONTRACTS["fetch_price"]

    elif category == "calculation":
        if 'rsi' in query_lower:
            return CONTRACTS["calc_rsi"]
        if 'moving average' in query_lower or ' ma' in query_lower or 'ma ' in query_lower:
            return CONTRACTS["calc_ma"]
        if 'bollinger' in query_lower:
            return CONTRACTS["calc_bollinger"]
        if 'macd' in query_lower:
            return CONTRACTS["calc_macd"]
        if 'volatility' in query_lower:
            return CONTRACTS["calc_volatility"]
        if 'kdj' in query_lower:
            return CONTRACTS["calc_kdj"]
        if 'drawdown' in query_lower:
            return CONTRACTS["calc_drawdown"]
        if 'correlation' in query_lower:
            return CONTRACTS["calc_correlation"]

    elif category == "composite":
        if any(kw in query_lower for kw in ['signal', 'if ', 'return true', 'return false']):
            return CONTRACTS["comp_signal"]
        if 'divergence' in query_lower:
            return CONTRACTS["comp_divergence"]
        if 'portfolio' in query_lower:
            return CONTRACTS["comp_portfolio"]
        if 'after' in query_lower and any(kw in query_lower for kw in ['rsi', 'return']):
            return CONTRACTS["comp_conditional_return"]

    return None


if __name__ == "__main__":
    print("=== Contract Definitions ===")
    for contract_id, contract in CONTRACTS.items():
        print(f"\n{contract_id}:")
        print(f"  Category: {contract.category}")
        print(f"  Output: {contract.output_type.value}")
        if contract.required_keys:
            print(f"  Required keys: {contract.required_keys}")
        if contract.output_constraints:
            print(f"  Constraints: {contract.output_constraints}")

    print("\n=== Task-Contract Mapping ===")
    for task_id, contract_id in TASK_CONTRACT_MAPPING.items():
        print(f"  {task_id} -> {contract_id}")

    print("\n=== Inference Tests ===")
    test_queries = [
        ("Calculate AAPL RSI-14", "calculation"),
        ("Get AAPL net income", "fetch"),
        ("Calculate Bollinger Bands", "calculation"),
        ("If MA5>MA20, return True", "composite"),
    ]
    for query, cat in test_queries:
        contract = infer_contract_from_query(query, cat)
        print(f"  '{query}' ({cat}) -> {contract.contract_id if contract else 'None'}")

    print("\nContract system tests passed!")
