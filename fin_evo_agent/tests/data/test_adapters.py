"""Tests for data provider adapters."""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import tempfile

import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.interfaces import DataProvider, is_data_provider
from src.data.adapters.mock_adapter import MockAdapter
from src.data.adapters.yfinance_adapter import YFinanceAdapter


class TestDataProviderProtocol:
    """Test DataProvider protocol definition."""

    def test_mock_adapter_satisfies_protocol(self):
        """MockAdapter should satisfy DataProvider protocol."""
        adapter = MockAdapter()
        assert is_data_provider(adapter)

    def test_yfinance_adapter_satisfies_protocol(self):
        """YFinanceAdapter should satisfy DataProvider protocol."""
        adapter = YFinanceAdapter()
        assert is_data_provider(adapter)

    def test_protocol_methods_exist(self):
        """DataProvider should define required methods."""
        # Check that protocol has the expected methods
        assert hasattr(DataProvider, 'get_historical')
        assert hasattr(DataProvider, 'get_quote')
        assert hasattr(DataProvider, 'get_financial_info')
        assert hasattr(DataProvider, 'get_multi_historical')


class TestMockAdapter:
    """Test MockAdapter implementation."""

    @pytest.fixture
    def adapter(self):
        """Create MockAdapter instance."""
        return MockAdapter()

    def test_get_historical_returns_dataframe(self, adapter):
        """get_historical should return a DataFrame."""
        df = adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
        assert isinstance(df, pd.DataFrame)

    def test_get_historical_has_ohlcv_columns(self, adapter):
        """get_historical DataFrame should have OHLCV columns."""
        df = adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
        expected_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
        assert expected_columns.issubset(set(df.columns))

    def test_get_historical_excludes_weekends(self, adapter):
        """get_historical should only include business days."""
        df = adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
        for date in df["Date"]:
            if isinstance(date, datetime):
                assert date.weekday() < 5  # 0-4 are weekdays

    def test_get_quote_returns_dict(self, adapter):
        """get_quote should return a dict."""
        quote = adapter.get_quote("AAPL")
        assert isinstance(quote, dict)

    def test_get_quote_has_required_keys(self, adapter):
        """get_quote dict should have required keys."""
        quote = adapter.get_quote("AAPL")
        assert "symbol" in quote
        assert "price" in quote
        assert "volume" in quote

    def test_get_financial_info_returns_dataframe(self, adapter):
        """get_financial_info should return a DataFrame."""
        df = adapter.get_financial_info("AAPL")
        assert isinstance(df, pd.DataFrame)

    def test_get_multi_historical_returns_dict(self, adapter):
        """get_multi_historical should return dict of DataFrames."""
        result = adapter.get_multi_historical(["AAPL", "MSFT"], "2023-01-01", "2023-01-31")
        assert isinstance(result, dict)
        assert "AAPL" in result
        assert "MSFT" in result
        assert isinstance(result["AAPL"], pd.DataFrame)

    def test_call_log_tracks_calls(self, adapter):
        """Call log should track all method calls."""
        adapter.get_historical("AAPL", "2023-01-01", "2023-01-31")
        adapter.get_quote("MSFT")

        log = adapter.get_call_log()
        assert len(log) == 2
        assert log[0]["method"] == "get_historical"
        assert log[0]["symbol"] == "AAPL"
        assert log[1]["method"] == "get_quote"
        assert log[1]["symbol"] == "MSFT"

    def test_clear_call_log(self, adapter):
        """Clear should reset the call log."""
        adapter.get_quote("AAPL")
        adapter.clear_call_log()
        assert len(adapter.get_call_log()) == 0

    def test_canned_data_override(self):
        """Canned data should override generated data."""
        canned_df = pd.DataFrame({
            "Date": ["2023-01-01"],
            "Open": [100.0],
            "High": [110.0],
            "Low": [95.0],
            "Close": [105.0],
            "Volume": [1000000],
        })

        adapter = MockAdapter(canned_data={"get_historical:TEST": canned_df})
        result = adapter.get_historical("TEST", "2023-01-01", "2023-01-31")

        assert len(result) == 1
        assert result["Close"].iloc[0] == 105.0

    def test_deterministic_generation(self):
        """Generated data should be deterministic for same symbol."""
        adapter1 = MockAdapter()
        adapter2 = MockAdapter()

        df1 = adapter1.get_historical("AAPL", "2023-01-01", "2023-01-31")
        df2 = adapter2.get_historical("AAPL", "2023-01-01", "2023-01-31")

        pd.testing.assert_frame_equal(df1, df2)


class TestYFinanceAdapter:
    """Test YFinanceAdapter implementation (with caching)."""

    @pytest.fixture
    def adapter_with_temp_cache(self):
        """Create YFinanceAdapter with temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = YFinanceAdapter(cache_dir=Path(tmpdir))
            yield adapter

    def test_cache_directory_created(self, adapter_with_temp_cache):
        """Cache directory should exist after initialization."""
        assert adapter_with_temp_cache.cache_dir.exists()

    def test_get_historical_interface(self, adapter_with_temp_cache):
        """get_historical should have correct signature."""
        import inspect
        sig = inspect.signature(adapter_with_temp_cache.get_historical)
        params = list(sig.parameters.keys())
        assert 'symbol' in params
        assert 'start' in params
        assert 'end' in params

    def test_get_quote_interface(self, adapter_with_temp_cache):
        """get_quote should have correct signature."""
        import inspect
        sig = inspect.signature(adapter_with_temp_cache.get_quote)
        params = list(sig.parameters.keys())
        assert 'symbol' in params

    def test_get_financial_info_interface(self, adapter_with_temp_cache):
        """get_financial_info should have correct signature."""
        import inspect
        sig = inspect.signature(adapter_with_temp_cache.get_financial_info)
        params = list(sig.parameters.keys())
        assert 'symbol' in params


class TestAdapterInterchangeability:
    """Test that adapters can be used interchangeably."""

    def test_same_interface_mock_and_yfinance(self):
        """Both adapters should have the same methods."""
        mock = MockAdapter()
        yfinance = YFinanceAdapter()

        mock_methods = {m for m in dir(mock) if not m.startswith('_') and callable(getattr(mock, m))}
        yfinance_methods = {m for m in dir(yfinance) if not m.startswith('_') and callable(getattr(yfinance, m))}

        # Check that common protocol methods exist in both
        protocol_methods = {'get_historical', 'get_quote', 'get_financial_info', 'get_multi_historical'}
        assert protocol_methods.issubset(mock_methods)
        assert protocol_methods.issubset(yfinance_methods)

    def test_function_using_provider_protocol(self):
        """A function accepting DataProvider should work with any adapter."""
        def calculate_average_close(provider: DataProvider, symbol: str) -> float:
            """Example function using DataProvider protocol."""
            df = provider.get_historical(symbol, "2023-01-01", "2023-01-31")
            return float(df["Close"].astype(float).mean())

        # Should work with MockAdapter
        mock = MockAdapter()
        avg = calculate_average_close(mock, "AAPL")
        assert isinstance(avg, float)
        assert avg > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
