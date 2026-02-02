"""Get financial summary for a stock with caching."""
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
