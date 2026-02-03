import pandas as pd
import numpy as np

def calc_macd(prices: list, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> dict:
    """Calculate MACD indicator.

    Args:
        prices: List of closing prices
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line EMA period (default 9)

    Returns:
        Dictionary with 'macd', 'signal', and 'histogram' values
    """
    if len(prices) < max(slow_period, fast_period) + signal_period:
        return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    s = pd.Series(prices)
    
    # Calculate EMAs
    fast_ema = s.ewm(span=fast_period, adjust=False).mean()
    slow_ema = s.ewm(span=slow_period, adjust=False).mean()
    
    # Calculate MACD line
    macd_line = fast_ema - slow_ema
    
    # Calculate signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return {
        'macd': float(macd_line.iloc[-1]),
        'signal': float(signal_line.iloc[-1]),
        'histogram': float(histogram.iloc[-1])
    }

if __name__ == "__main__":
    # Test 1: Simple increasing prices
    test_prices1 = [100 + i for i in range(50)]
    result1 = calc_macd(test_prices1)
    assert isinstance(result1['macd'], float)
    assert isinstance(result1['signal'], float)
    assert isinstance(result1['histogram'], float)
    
    # Test 2: Constant prices
    test_prices2 = [150.0] * 30
    result2 = calc_macd(test_prices2)
    assert result2['macd'] == 0.0
    assert result2['signal'] == 0.0
    assert result2['histogram'] == 0.0
    
    print("All tests passed!")