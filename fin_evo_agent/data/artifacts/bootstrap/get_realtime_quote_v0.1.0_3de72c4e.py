"""Get real-time market quotes with caching."""
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
