import pandas as pd
import numpy as np

def calc_bollinger(prices: list, window: int = 20, num_std: int = 2) -> dict:
    """Calculate Bollinger Bands.

    Args:
        prices: List of closing prices
        window: Moving average window (default 20)
        num_std: Number of standard deviations (default 2)

    Returns:
        Dictionary containing 'upper', 'middle', and 'lower' band values
    """
    if len(prices) < window:
        raise ValueError(f"At least {window} price points required")
    
    s = pd.Series(prices)
    sma = s.rolling(window=window).mean()
    std = s.rolling(window=window).std()
    
    upper_band = sma + (num_std * std)
    lower_band = sma - (num_std * std)
    
    return {
        'upper': float(upper_band.iloc[-1]),
        'middle': float(sma.iloc[-1]),
        'lower': float(lower_band.iloc[-1])
    }

if __name__ == "__main__":
    # Test with synthetic data
    test_prices1 = list(range(1, 26))  # 25 consecutive numbers
    result1 = calc_bollinger(test_prices1)
    assert all(key in result1 for key in ['upper', 'middle', 'lower'])
    assert result1['upper'] > result1['middle'] > result1['lower']
    
    # Test with more volatile data
    test_prices2 = [100 + i%10 + (i%3)*5 for i in range(25)]
    result2 = calc_bollinger(test_prices2)
    assert isinstance(result2['upper'], float)