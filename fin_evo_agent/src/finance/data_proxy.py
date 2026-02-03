"""yfinance data proxy with Record-Replay caching mechanism.

Implements reproducible data access:
- First call: Fetch from yfinance, cache as Parquet
- Subsequent calls: Replay from cache (no network)

Features:
- Retry with exponential backoff for network resilience
- Parquet caching for reproducibility

Cache key: MD5(func_name + args + kwargs)
Storage: data/cache/{key}.parquet
"""

import hashlib
import json
import time
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

import yfinance as yf
import pandas as pd

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import CACHE_DIR


# Network retry configuration
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0  # seconds
RETRY_MAX_DELAY = 10.0  # seconds
RETRY_BACKOFF_FACTOR = 2.0


T = TypeVar('T')


def with_retry(
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR
) -> Callable:
    """Decorator for retry with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        backoff_factor: Multiplier for exponential backoff

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = base_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        # Log retry attempt
                        print(f"[Retry] Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        print(f"[Retry] Waiting {delay:.1f}s before retry...")
                        time.sleep(delay)
                        # Exponential backoff
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        print(f"[Retry] All {max_attempts} attempts failed")

            raise last_exception

        return wrapper
    return decorator


class DataProvider:
    """yfinance proxy implementing 'Record-Replay' mechanism for reproducibility."""

    @staticmethod
    def _get_cache_path(func_name: str, args: tuple, kwargs: dict) -> Path:
        """Generate unique cache path from function signature."""
        key = json.dumps({
            "f": func_name,
            "a": [str(a) for a in args],
            "k": {k: str(v) for k, v in sorted(kwargs.items())}
        }, sort_keys=True)
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return CACHE_DIR / f"{hash_key}.parquet"

    @classmethod
    def reproducible(cls, func):
        """Decorator for reproducible data access with Parquet caching and retry."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_path = cls._get_cache_path(func.__name__, args, kwargs)

            # 1. Replay mode (cache hit)
            if cache_path.exists():
                return pd.read_parquet(cache_path)

            # 2. Record mode (cache miss) with retry
            @with_retry(max_attempts=RETRY_MAX_ATTEMPTS)
            def fetch_with_retry():
                print(f"[Network] Fetching {func.__name__}...")
                return func(*args, **kwargs)

            try:
                df = fetch_with_retry()

                # Save to Parquet (convert all columns to str for compatibility)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.astype(str).to_parquet(cache_path)
                return df
            except Exception as e:
                raise RuntimeError(f"Data Fetch Failed after {RETRY_MAX_ATTEMPTS} attempts: {str(e)}")
        return wrapper


# --- Bootstrap Tools (Pre-built atomic tools using yfinance) ---

@DataProvider.reproducible
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
    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    return df


@DataProvider.reproducible
def get_financial_info(symbol: str) -> pd.DataFrame:
    """
    Get financial summary for a stock.

    Args:
        symbol: Ticker symbol, e.g., 'AAPL'

    Returns:
        DataFrame with key financial metrics (income statement)
    """
    ticker = yf.Ticker(symbol)
    df = ticker.income_stmt
    if isinstance(df, pd.DataFrame) and not df.empty:
        df = df.T  # Transpose: rows = periods, columns = metrics
        df = df.reset_index()
        df = df.rename(columns={"index": "Period"})
    return df


@DataProvider.reproducible
def get_spot_price(symbols: str = "AAPL,MSFT,GOOGL") -> pd.DataFrame:
    """
    Get latest market quotes for given tickers.

    Args:
        symbols: Comma-separated ticker symbols, e.g., 'AAPL,MSFT,GOOGL'

    Returns:
        DataFrame with current prices and trading data
    """
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
    return pd.DataFrame(rows)


@DataProvider.reproducible
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
    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    return df


@DataProvider.reproducible
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
    df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    return df


if __name__ == "__main__":
    # Test bootstrap tools
    print("Testing bootstrap tools...")

    # Test stock history
    df = get_stock_hist("AAPL", "2023-01-01", "2023-01-31")
    print(f"Stock hist: {len(df)} rows")

    # Test again (should hit cache)
    df = get_stock_hist("AAPL", "2023-01-01", "2023-01-31")
    print(f"Stock hist (cached): {len(df)} rows")

    print("Bootstrap tools test completed.")
