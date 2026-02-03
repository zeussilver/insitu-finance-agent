import pandas as pd
from typing import Union

def get_etf_hist(prices: Union[list, pd.Series]) -> float:
    """Get the latest closing price from historical price data.

    Args:
        prices: List or pandas Series of historical closing prices

    Returns:
        Latest (most recent) closing price as a float
    """
    if isinstance(prices, list):
        if not prices:
            raise ValueError("Price list cannot be empty")
        return float(prices[-1])
    elif isinstance(prices, pd.Series):
        if prices.empty:
            raise ValueError("Price series cannot be empty")
        return float(prices.iloc[-1])
    else:
        raise TypeError("Prices must be a list or pandas Series")

if __name__ == "__main__":
    # Test with list input
    test_prices_list = [400.5, 401.2, 402.8, 403.1, 402.9]
    result1 = get_etf_hist(test_prices_list)
    assert result1 == 402.9
    
    # Test with pandas Series input
    test_prices_series = pd.Series([150.25, 151.30, 152.10, 151.85])
    result2 = get_etf_hist(test_prices_series)
    assert result2 == 151.85