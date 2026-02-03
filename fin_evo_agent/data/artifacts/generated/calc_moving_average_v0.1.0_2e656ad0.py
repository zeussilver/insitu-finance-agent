import pandas as pd
import numpy as np

def calc_moving_average(prices: list, period: int = 5) -> float:
    """Calculate simple moving average (SMA) for given price data.

    Args:
        prices: List of closing prices
        period: Moving average period (default 5)

    Returns:
        Latest moving average value as float
    """
    if len(prices) < period:
        raise ValueError(f"Insufficient data: need at least {period} prices")
    
    s = pd.Series(prices)
    sma = s.rolling(window=period).mean()
    return float(sma.iloc[-1])

if __name__ == "__main__":
    # Sample MSFT-like price data for 20 days
    msft_prices_20d = [
        335.2, 336.8, 334.1, 337.5, 338.2,
        339.0, 340.5, 341.2, 339.8, 342.1,
        343.5, 344.0, 342.8, 345.2, 346.7,
        347.3, 348.1, 349.5, 350.2, 351.8
    ]
    
    result = calc_moving_average(msft_prices_20d, 5)
    assert isinstance(result, float)
    assert 345.0 <= result <= 355.0  # Reasonable range for last 5 days