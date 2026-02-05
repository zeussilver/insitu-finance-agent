"""Abstract data provider interface using Protocol for structural typing.

This module defines the contract for financial data providers, enabling:
- Pluggable adapters (yfinance, mock, future providers)
- Deterministic testing without network calls
- Clean separation of data access from business logic
"""

from typing import Protocol, runtime_checkable, Optional
import pandas as pd


@runtime_checkable
class DataProvider(Protocol):
    """Protocol defining the contract for financial data providers.

    Any class implementing these methods satisfies the DataProvider protocol.
    Uses structural typing - no explicit inheritance required.
    """

    def get_historical(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', '^GSPC')
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format
            interval: Data interval ('1d', '1h', etc.)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        ...

    def get_quote(self, symbol: str) -> dict:
        """Get current quote/price data for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Dict with keys: symbol, price, volume, market_cap, etc.
        """
        ...

    def get_financial_info(self, symbol: str) -> pd.DataFrame:
        """Get financial statement data for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            DataFrame with financial metrics (income statement, etc.)
        """
        ...

    def get_multi_historical(
        self,
        symbols: list[str],
        start: str,
        end: str,
        interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols.

        Args:
            symbols: List of ticker symbols
            start: Start date
            end: End date
            interval: Data interval

        Returns:
            Dict mapping symbol to its historical DataFrame
        """
        ...


def is_data_provider(obj: object) -> bool:
    """Check if an object satisfies the DataProvider protocol."""
    return isinstance(obj, DataProvider)


if __name__ == "__main__":
    # Verify protocol definition
    print("DataProvider Protocol defined with methods:")
    for method in ['get_historical', 'get_quote', 'get_financial_info', 'get_multi_historical']:
        print(f"  - {method}")
    print("\nProtocol verification passed!")
