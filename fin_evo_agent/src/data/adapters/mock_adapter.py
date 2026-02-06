"""Mock implementation of DataProvider protocol for testing.

Provides deterministic test data without network calls.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class MockAdapter:
    """Mock DataProvider for deterministic testing."""

    def __init__(self, canned_data: Optional[dict] = None):
        """Initialize with optional canned responses.

        Args:
            canned_data: Dict mapping method calls to predefined responses.
                        Keys format: "{method}:{symbol}" or "{method}"
        """
        self.canned_data = canned_data or {}
        self._call_log = []

    def _log_call(self, method: str, **kwargs) -> None:
        """Record method call for verification."""
        self._call_log.append({"method": method, **kwargs})

    def get_call_log(self) -> list:
        """Get record of all method calls."""
        return self._call_log

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log = []

    def _generate_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        base_price: float = 100.0
    ) -> pd.DataFrame:
        """Generate synthetic OHLCV data."""
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")

        dates = []
        current = start_dt
        while current <= end_dt:
            if current.weekday() < 5:  # Skip weekends
                dates.append(current)
            current += timedelta(days=1)

        if not dates:
            return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

        # Generate synthetic prices with random walk
        np.random.seed(hash(symbol) % (2**32))
        n = len(dates)
        returns = np.random.normal(0.001, 0.02, n)
        prices = base_price * np.exp(np.cumsum(returns))

        data = {
            "Date": dates,
            "Open": prices * (1 + np.random.uniform(-0.01, 0.01, n)),
            "High": prices * (1 + np.random.uniform(0, 0.02, n)),
            "Low": prices * (1 - np.random.uniform(0, 0.02, n)),
            "Close": prices,
            "Volume": np.random.randint(1000000, 10000000, n),
        }

        return pd.DataFrame(data)

    def get_historical(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol."""
        self._log_call("get_historical", symbol=symbol, start=start, end=end, interval=interval)

        # Check for canned response
        key = f"get_historical:{symbol}"
        if key in self.canned_data:
            return self.canned_data[key]

        # Generate synthetic data
        return self._generate_ohlcv(symbol, start, end)

    def get_quote(self, symbol: str) -> dict:
        """Get current quote/price data for a symbol."""
        self._log_call("get_quote", symbol=symbol)

        # Check for canned response
        key = f"get_quote:{symbol}"
        if key in self.canned_data:
            return self.canned_data[key]

        # Generate synthetic quote
        np.random.seed(hash(symbol) % (2**32))
        price = 100 + np.random.uniform(-20, 80)

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "volume": int(np.random.randint(1000000, 10000000)),
            "market_cap": int(price * np.random.randint(1e8, 1e10)),
            "previous_close": round(price * (1 + np.random.uniform(-0.02, 0.02)), 2),
        }

    def get_financial_info(self, symbol: str) -> pd.DataFrame:
        """Get financial statement data for a symbol."""
        self._log_call("get_financial_info", symbol=symbol)

        # Check for canned response
        key = f"get_financial_info:{symbol}"
        if key in self.canned_data:
            return self.canned_data[key]

        # Generate synthetic financial data
        np.random.seed(hash(symbol) % (2**32))
        periods = ["2023-12-31", "2022-12-31", "2021-12-31"]
        revenue_base = np.random.uniform(1e9, 1e11)

        data = {
            "Period": periods,
            "Total Revenue": [revenue_base * (1.1 ** i) for i in range(3)],
            "Net Income": [revenue_base * 0.1 * (1.1 ** i) for i in range(3)],
            "Operating Income": [revenue_base * 0.15 * (1.1 ** i) for i in range(3)],
        }

        return pd.DataFrame(data)

    def get_multi_historical(
        self,
        symbols: list[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols."""
        self._log_call("get_multi_historical", symbols=symbols, start=start, end=end, interval=interval)

        result = {}
        for symbol in symbols:
            result[symbol] = self.get_historical(symbol, start, end, interval)
        return result


if __name__ == "__main__":
    # Test the mock adapter
    print("Testing MockAdapter...")

    # Test with generated data
    adapter = MockAdapter()

    df = adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
    print(f"Historical data: {len(df)} rows")
    print(f"Columns: {list(df.columns)}")

    quote = adapter.get_quote("AAPL")
    print(f"Quote: {quote}")

    # Test with canned data
    canned = {
        "get_historical:TEST": pd.DataFrame({
            "Date": ["2023-01-01"],
            "Open": [100.0],
            "High": [105.0],
            "Low": [95.0],
            "Close": [102.0],
            "Volume": [1000000],
        })
    }
    adapter2 = MockAdapter(canned_data=canned)
    df_canned = adapter2.get_historical("TEST", "2023-01-01", "2023-01-31")
    print(f"Canned data: {len(df_canned)} rows")

    # Verify call log
    print(f"Call log: {adapter2.get_call_log()}")

    print("\nMockAdapter tests passed!")
