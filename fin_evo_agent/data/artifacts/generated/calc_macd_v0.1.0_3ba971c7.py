import pandas as pd
import numpy as np

def calc_macd(prices: list, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> dict:
    """Calculate MACD indicator components.

    Args:
        prices: List of closing prices
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line EMA period (default 9)

    Returns:
        Dictionary containing 'macd', 'signal', and 'histogram' values
    """
    if len(prices) < max(slow_period, fast_period) + signal_period:
        return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    s = pd.Series(prices)
    
    # Calculate EMAs
    fast_ema = s.ewm(span=fast_period, adjust=False).mean()
    slow_ema = s.ewm(span=slow_period, adjust=False).mean()
    
    # MACD line
    macd_line = fast_ema - slow_ema
    
    # Signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Histogram
    histogram = macd_line - signal_line
    
    return {
        'macd': float(macd_line.iloc[-1]),
        'signal': float(signal_line.iloc[-1]),
        'histogram': float(histogram.iloc[-1])
    }

if __name__ == "__main__":
    # Test with sample price data
    test_prices1 = [3000, 3050, 3025, 3075, 3100, 3080, 3120, 3150, 3130, 3180, 
                    3200, 3190, 3220, 3250, 3230, 3270, 3300, 3280, 3320, 3350,
                    3330, 3370, 3400, 3380, 3420, 3450, 3430, 3470, 3500]
    result1 = calc_macd(test_prices1)
    assert isinstance(result1['macd'], float)
    assert isinstance(result1['signal'], float)
    assert isinstance(result1['histogram'], float)
    
    # Test with minimal data
    test_prices2 = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    result2 = calc_macd(test_prices2)
    assert all(isinstance(v, float) for v in result2.values())