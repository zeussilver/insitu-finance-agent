import pandas as pd
import numpy as np

def calc_bollinger(prices: list, period: int = 20, std_multiplier: float = 2.0) -> dict:
    """Calculate Bollinger Bands indicator.

    Args:
        prices: List of closing prices
        period: Moving average period (default 20)
        std_multiplier: Standard deviation multiplier (default 2.0)

    Returns:
        Dictionary containing 'upper', 'middle', and 'lower' band values
    """
    if len(prices) < period:
        return {'upper': np.nan, 'middle': np.nan, 'lower': np.nan}
    
    s = pd.Series(prices)
    middle = s.rolling(window=period).mean()
    std = s.rolling(window=period).std()
    upper = middle + (std * std_multiplier)
    lower = middle - (std * std_multiplier)
    
    return {
        'upper': float(upper.iloc[-1]),
        'middle': float(middle.iloc[-1]),
        'lower': float(lower.iloc[-1])
    }

if __name__ == "__main__":
    # Test 1: Basic functionality with sufficient data
    test_prices1 = [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 
                    51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
    result1 = calc_bollinger(test_prices1, period=10)
    assert isinstance(result1['upper'], float)
    assert result1['upper'] > result1['middle'] > result1['lower']
    
    # Test 2: With default parameters
    test_prices2 = list(range(1, 26))  # 25 data points
    result2 = calc_bollinger(test_prices2)
    assert all(isinstance(val, float) for val in result2.values())
    assert result2['upper'] > result2['middle'] > result2['lower']