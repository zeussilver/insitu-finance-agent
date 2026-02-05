"""yfinance implementation of DataProvider protocol.

Production adapter using yfinance for real market data.
Includes caching via Parquet files for reproducibility.
"""

import hashlib
import json
import time
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, Optional

import yfinance as yf
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.config import CACHE_DIR


# Network retry configuration
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 10.0
RETRY_BACKOFF_FACTOR = 2.0


T = TypeVar('T')


def with_retry(
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR
) -> Callable:
    """Decorator for retry with exponential backoff."""
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
                        print(f"[Retry] Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        print(f"[Retry] Waiting {delay:.1f}s before retry...")
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        print(f"[Retry] All {max_attempts} attempts failed")

            raise last_exception

        return wrapper
    return decorator


class YFinanceAdapter:
    """yfinance implementation of DataProvider protocol with caching."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize adapter with optional custom cache directory."""
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, method_name: str, *args, **kwargs) -> Path:
        """Generate unique cache path from method signature."""
        key = json.dumps({
            "m": method_name,
            "a": [str(a) for a in args],
            "k": {k: str(v) for k, v in sorted(kwargs.items())}
        }, sort_keys=True)
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.parquet"

    def _cache_result(self, cache_path: Path, df: pd.DataFrame) -> None:
        """Cache DataFrame as Parquet."""
        if isinstance(df, pd.DataFrame) and not df.empty:
            df.astype(str).to_parquet(cache_path)

    def _load_cache(self, cache_path: Path) -> Optional[pd.DataFrame]:
        """Load cached DataFrame if exists."""
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        return None

    def get_historical(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol."""
        cache_path = self._get_cache_path("get_historical", symbol, start, end, interval=interval)

        # Check cache first
        cached = self._load_cache(cache_path)
        if cached is not None:
            return cached

        # Fetch with retry
        @with_retry()
        def fetch():
            print(f"[Network] Fetching historical data for {symbol}...")
            df = yf.download(symbol, start=start, end=end, interval=interval,
                            auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            return df

        df = fetch()
        self._cache_result(cache_path, df)
        return df

    def get_quote(self, symbol: str) -> dict:
        """Get current quote/price data for a symbol."""
        # Note: Quotes are real-time, not cached
        @with_retry()
        def fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return {
                "symbol": symbol,
                "price": getattr(info, "last_price", None),
                "volume": getattr(info, "last_volume", None),
                "market_cap": getattr(info, "market_cap", None),
                "previous_close": getattr(info, "previous_close", None),
            }

        return fetch()

    def get_financial_info(self, symbol: str) -> pd.DataFrame:
        """Get financial statement data for a symbol."""
        cache_path = self._get_cache_path("get_financial_info", symbol)

        # Check cache
        cached = self._load_cache(cache_path)
        if cached is not None:
            return cached

        @with_retry()
        def fetch():
            print(f"[Network] Fetching financial info for {symbol}...")
            ticker = yf.Ticker(symbol)
            df = ticker.income_stmt
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.T
                df = df.reset_index()
                df = df.rename(columns={"index": "Period"})
            return df

        df = fetch()
        self._cache_result(cache_path, df)
        return df

    def get_multi_historical(
        self,
        symbols: list[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols."""
        result = {}
        for symbol in symbols:
            result[symbol] = self.get_historical(symbol, start, end, interval)
        return result


if __name__ == "__main__":
    # Test the adapter
    print("Testing YFinanceAdapter...")
    adapter = YFinanceAdapter()

    # Test historical data
    df = adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
    print(f"Historical data: {len(df)} rows")

    # Test again (should hit cache)
    df = adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
    print(f"Historical data (cached): {len(df)} rows")

    print("\nYFinanceAdapter tests passed!")
