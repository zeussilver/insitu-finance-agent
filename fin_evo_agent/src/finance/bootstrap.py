"""Bootstrap Tools Registration

Registers 5 initial yfinance tools as ToolArtifacts:
1. get_stock_hist - Stock historical OHLCV data
2. get_financial_info - Financial summary (income statement)
3. get_realtime_quote - Real-time market quotes
4. get_index_daily - Index daily data
5. get_etf_hist - ETF historical data

Each tool is registered with:
- Standalone code that uses DataProvider.reproducible for caching
- Type hints and docstrings
- Built-in test cases in if __name__ == '__main__' block

Note: Bootstrap tools use inline caching for portability. For new code,
prefer using the DataProvider adapter from src.data.adapters.
"""

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.core.registry import ToolRegistry
from src.core.models import Permission, init_db


# --- Bootstrap Tool Code Templates ---

GET_STOCK_HIST_CODE = '''"""Get stock daily historical data with caching."""
import pandas as pd
import yfinance as yf
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(func_name: str, args: tuple, kwargs: dict) -> Path:
    key = json.dumps({"f": func_name, "a": list(args), "k": kwargs}, sort_keys=True)
    return CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.parquet"

def get_stock_hist(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Get stock daily historical data.

    Args:
        symbol: Ticker symbol, e.g., 'AAPL'
        start: Start date, e.g., '2023-01-01'
        end: End date, e.g., '2023-01-31'

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
    """
    cache_path = _get_cache_path("get_stock_hist", (symbol, start, end), {})
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    if isinstance(df, pd.DataFrame) and not df.empty:
        df.astype(str).to_parquet(cache_path)
    return df

if __name__ == "__main__":
    # Test case 1: Fetch data
    df = get_stock_hist("AAPL", "2023-01-01", "2023-01-10")
    assert len(df) > 0, "Should return non-empty DataFrame"
    assert "Close" in df.columns, "Should have 'Close' column"

    # Test case 2: Cache hit
    df2 = get_stock_hist("AAPL", "2023-01-01", "2023-01-10")
    assert len(df) == len(df2), "Cache should return same data"

    print("All tests passed!")
'''

GET_FINANCIAL_INFO_CODE = '''"""Get financial summary for a stock with caching."""
import pandas as pd
import yfinance as yf
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(func_name: str, args: tuple, kwargs: dict) -> Path:
    key = json.dumps({"f": func_name, "a": list(args), "k": kwargs}, sort_keys=True)
    return CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.parquet"

def get_financial_info(symbol: str) -> pd.DataFrame:
    """
    Get financial summary for a stock (income statement).

    Args:
        symbol: Ticker symbol, e.g., 'AAPL'

    Returns:
        DataFrame with key financial metrics (Net Income, Revenue, etc.)
    """
    cache_path = _get_cache_path("get_financial_info", (symbol,), {})
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    ticker = yf.Ticker(symbol)
    df = ticker.income_stmt
    if isinstance(df, pd.DataFrame) and not df.empty:
        df = df.T
        df = df.reset_index()
        df = df.rename(columns={"index": "Period"})
        df.astype(str).to_parquet(cache_path)
    return df

if __name__ == "__main__":
    # Test case 1: Fetch data
    df = get_financial_info("AAPL")
    assert len(df) > 0, "Should return non-empty DataFrame"

    print("All tests passed!")
'''

GET_REALTIME_QUOTE_CODE = '''"""Get real-time market quotes with caching."""
import pandas as pd
import yfinance as yf
import hashlib
import json
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(func_name: str, args: tuple, kwargs: dict) -> Path:
    key = json.dumps({"f": func_name, "a": list(args), "k": kwargs}, sort_keys=True)
    return CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.parquet"

def get_realtime_quote(symbol: str = None) -> pd.DataFrame:
    """
    Get real-time market quotes.

    Args:
        symbol: Ticker symbol (optional). If specified, returns data for that symbol only.
                If None, returns data for major tickers: AAPL, MSFT, GOOGL.

    Returns:
        DataFrame with columns: symbol, price, market_cap, volume
    """
    date_key = datetime.now().strftime("%Y%m%d")
    symbols = symbol if symbol else "AAPL,MSFT,GOOGL"
    cache_path = _get_cache_path("get_realtime_quote", (date_key, symbols), {})

    if cache_path.exists():
        df = pd.read_parquet(cache_path)
    else:
        symbol_list = [s.strip() for s in symbols.split(",")]
        rows = []
        for sym in symbol_list:
            ticker = yf.Ticker(sym)
            info = ticker.fast_info
            rows.append({
                "symbol": sym,
                "price": getattr(info, "last_price", None),
                "market_cap": getattr(info, "market_cap", None),
                "volume": getattr(info, "last_volume", None),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df.astype(str).to_parquet(cache_path)

    if symbol and not df.empty:
        df = df[df["symbol"] == symbol]

    return df

if __name__ == "__main__":
    # Test case 1: Fetch all data
    df = get_realtime_quote()
    assert len(df) > 0, "Should return non-empty DataFrame"
    assert "symbol" in df.columns, "Should have 'symbol' column"

    # Test case 2: Fetch specific stock
    df_single = get_realtime_quote("AAPL")
    assert len(df_single) <= 1, "Should return at most one row for specific symbol"

    print("All tests passed!")
'''

GET_INDEX_DAILY_CODE = '''"""Get index daily historical data with caching."""
import pandas as pd
import yfinance as yf
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(func_name: str, args: tuple, kwargs: dict) -> Path:
    key = json.dumps({"f": func_name, "a": list(args), "k": kwargs}, sort_keys=True)
    return CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.parquet"

def get_index_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Get index daily data.

    Args:
        symbol: Index ticker, e.g., '^GSPC' for S&P 500, '^DJI' for Dow Jones
        start: Start date, e.g., '2023-01-01'
        end: End date, e.g., '2023-01-31'

    Returns:
        DataFrame with index OHLCV data
    """
    cache_path = _get_cache_path("get_index_daily", (symbol, start, end), {})
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()

    if isinstance(df, pd.DataFrame) and not df.empty:
        df.astype(str).to_parquet(cache_path)

    return df

if __name__ == "__main__":
    # Test case 1: Fetch S&P 500 index
    df = get_index_daily("^GSPC", "2023-01-01", "2023-01-31")
    assert isinstance(df, pd.DataFrame), "Should return DataFrame"

    print("All tests passed!")
'''

GET_ETF_HIST_CODE = '''"""Get ETF historical data with caching."""
import pandas as pd
import yfinance as yf
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(func_name: str, args: tuple, kwargs: dict) -> Path:
    key = json.dumps({"f": func_name, "a": list(args), "k": kwargs}, sort_keys=True)
    return CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.parquet"

def get_etf_hist(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Get ETF historical data.

    Args:
        symbol: ETF ticker, e.g., 'SPY' for SPDR S&P 500
        start: Start date, e.g., '2023-01-01'
        end: End date, e.g., '2023-01-31'

    Returns:
        DataFrame with ETF OHLCV data
    """
    cache_path = _get_cache_path("get_etf_hist", (symbol, start, end), {})
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()

    if isinstance(df, pd.DataFrame) and not df.empty:
        df.astype(str).to_parquet(cache_path)
    return df

if __name__ == "__main__":
    # Test case 1: Fetch ETF data
    df = get_etf_hist("SPY", "2023-01-01", "2023-01-31")
    assert isinstance(df, pd.DataFrame), "Should return DataFrame"

    print("All tests passed!")
'''


# --- Tool Registration ---

BOOTSTRAP_TOOLS = [
    {
        "name": "get_stock_hist",
        "code": GET_STOCK_HIST_CODE,
        "args_schema": {
            "symbol": "str",
            "start": "str",
            "end": "str"
        },
        "permissions": [Permission.NETWORK_READ.value, Permission.CALC_ONLY.value]
    },
    {
        "name": "get_financial_info",
        "code": GET_FINANCIAL_INFO_CODE,
        "args_schema": {
            "symbol": "str"
        },
        "permissions": [Permission.NETWORK_READ.value, Permission.CALC_ONLY.value]
    },
    {
        "name": "get_realtime_quote",
        "code": GET_REALTIME_QUOTE_CODE,
        "args_schema": {
            "symbol": "str"
        },
        "permissions": [Permission.NETWORK_READ.value, Permission.CALC_ONLY.value]
    },
    {
        "name": "get_index_daily",
        "code": GET_INDEX_DAILY_CODE,
        "args_schema": {
            "symbol": "str",
            "start": "str",
            "end": "str"
        },
        "permissions": [Permission.NETWORK_READ.value, Permission.CALC_ONLY.value]
    },
    {
        "name": "get_etf_hist",
        "code": GET_ETF_HIST_CODE,
        "args_schema": {
            "symbol": "str",
            "start": "str",
            "end": "str"
        },
        "permissions": [Permission.NETWORK_READ.value, Permission.CALC_ONLY.value]
    }
]


def create_bootstrap_tools():
    """Register all bootstrap tools to the database and disk."""
    print("=== Registering Bootstrap Tools ===\n")

    # Ensure DB exists
    init_db()

    registry = ToolRegistry()
    registered = []

    for tool_def in BOOTSTRAP_TOOLS:
        print(f"Registering: {tool_def['name']}...")

        tool = registry.register(
            name=tool_def["name"],
            code=tool_def["code"],
            args_schema=tool_def["args_schema"],
            permissions=tool_def["permissions"],
            is_bootstrap=True
        )

        print(f"  > Version: {tool.semantic_version}")
        print(f"  > File: {tool.file_path}")
        print(f"  > Hash: {tool.content_hash[:8]}")
        print()

        registered.append(tool)

    print(f"[Done] Registered {len(registered)} bootstrap tools.")
    return registered


def list_bootstrap_tools():
    """List all registered bootstrap tools."""
    registry = ToolRegistry()
    tools = registry.list_tools()

    bootstrap_tools = [t for t in tools if "bootstrap" in t.file_path]

    print(f"\n=== Bootstrap Tools ({len(bootstrap_tools)}) ===\n")
    for tool in bootstrap_tools:
        print(f"  [{tool.id}] {tool.name} v{tool.semantic_version}")
        print(f"      Status: {tool.status.value}")
        print(f"      File: {tool.file_path}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bootstrap Tools Management")
    parser.add_argument("--create", action="store_true", help="Create/register bootstrap tools")
    parser.add_argument("--list", action="store_true", help="List bootstrap tools")

    args = parser.parse_args()

    if args.create:
        create_bootstrap_tools()
    elif args.list:
        list_bootstrap_tools()
    else:
        # Default: create tools
        create_bootstrap_tools()
