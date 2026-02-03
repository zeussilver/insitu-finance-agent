import pandas as pd
import numpy as np

def calc_bollinger(prices: list, period: int = 20, num_std: int = 2) -> dict:
    """Calculate Bollinger Bands.

    Args:
        prices: List of closing prices
        period: Moving average period (default 20)
        num_std: Number of standard deviations (default 2)

    Returns:
        Dictionary with keys 'upper', 'middle', 'lower' representing the Bollinger Bands
    """
    if len(prices) < period:
        # Return None or raise error for insufficient data
        return {'upper': None, 'middle': None, 'lower': None}
    
    s = pd.Series(prices)
    middle = s.rolling(window=period).mean()
    std = s.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    return {
        'upper': float(upper.iloc[-1]),
        'middle': float(middle.iloc[-1]),
        'lower': float(lower.iloc[-1])
    }

if __name__ == "__main__":
    # Test 1: Simple increasing sequence
    test_prices1 = list(range(1, 26))  # 25 data points
    result1 = calc_bollinger(test_prices1)
    assert result1['upper'] is not None
    assert result1['middle'] is not None
    assert result1['lower'] is not None
    
    # Test 2: Constant prices
    test_prices2 = [100] * 25
    result2 = calc_bollinger(test_prices2)
    assert result2['upper'] == 100.0
    assert result2['middle'] == 100.0
    assert result2['lower'] == 100.0
    
    print("All tests passed!")