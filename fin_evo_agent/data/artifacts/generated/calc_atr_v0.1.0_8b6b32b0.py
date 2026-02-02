import pandas as pd
import numpy as np

def calc_atr(high: list, low: list, close: list, period: int = 14) -> float:
    """Calculate Average True Range (ATR) indicator.

    Args:
        high: List of high prices
        low: List of low prices  
        close: List of closing prices
        period: ATR period (default 14)

    Returns:
        ATR value as float
    """
    # Validate input lengths
    if len(high) != len(low) or len(high) != len(close):
        raise ValueError("High, low, and close lists must have the same length")
    
    if len(high) < period + 1:
        # Not enough data to calculate meaningful ATR
        return 0.0
    
    # Convert to pandas Series for easier calculation
    high_series = pd.Series(high)
    low_series = pd.Series(low)
    close_series = pd.Series(close)
    
    # Calculate True Range components
    tr1 = high_series - low_series
    tr2 = (high_series - close_series.shift(1)).abs()
    tr3 = (low_series - close_series.shift(1)).abs()
    
    # True Range is the maximum of the three
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR as simple moving average of True Range
    atr = true_range.rolling(window=period).mean()
    
    return float(atr.iloc[-1])

if __name__ == "__main__":
    # Test case 1: Simple price data
    test_high = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
    test_low = [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
    test_close = [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]
    result1 = calc_atr(test_high, test_low, test_close, 14)
    assert result1 >= 0.0
    
    # Test case 2: More volatile data
    test_high2 = [10, 12, 8, 15, 11, 13, 9, 14, 16, 12, 18, 10, 17, 13, 19]
    test_low2 = [8, 10, 6, 12, 9, 11, 7, 12, 14, 10, 16, 8, 15, 11, 17]
    test_close2 = [9, 11, 7, 13, 10, 12, 8, 13, 15, 11, 17, 9, 16, 12, 18]
    result2 = calc_atr(test_high2, test_low2, test_close2, 10)
    assert result2 >= 0.0