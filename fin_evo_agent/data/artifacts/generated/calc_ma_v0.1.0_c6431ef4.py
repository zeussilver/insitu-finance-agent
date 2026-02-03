import pandas as pd
import numpy as np

def calc_ma(prices: list, period: int = 20, ma_type: str = "sma") -> float:
    """Calculate moving average indicator.

    Args:
        prices: List of closing prices
        period: Moving average period (default 20)
        ma_type: Type of moving average - "sma" for simple, "ema" for exponential (default "sma")

    Returns:
        Latest moving average value
    """
    if len(prices) < period:
        raise ValueError(f"At least {period} price points required")
    
    s = pd.Series(prices)
    
    if ma_type.lower() == "sma":
        ma = s.rolling(window=period).mean()
    elif ma_type.lower() == "ema":
        ma = s.ewm(span=period, adjust=False).mean()
    else:
        raise ValueError("ma_type must be 'sma' or 'ema'")
    
    return float(ma.iloc[-1])

if __name__ == "__main__":
    # Test with sample price data
    test_prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 
                   110, 112, 111, 113, 115, 114, 116, 118, 117, 119]
    
    # Test SMA
    sma_result = calc_ma(test_prices, period=5, ma_type="sma")
    assert isinstance(sma_result, float)
    assert sma_result > 0
    
    # Test EMA
    ema_result = calc_ma(test_prices, period=5, ma_type="ema")
    assert isinstance(ema_result, float)
    assert ema_result > 0