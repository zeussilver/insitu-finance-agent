"""Get stock daily historical data with caching."""
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
