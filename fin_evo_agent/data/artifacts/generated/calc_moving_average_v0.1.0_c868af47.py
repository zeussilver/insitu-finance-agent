import pandas as pd
import numpy as np

def calc_moving_average(prices: list, period: int = 5) -> float:
    """Calculate simple moving average for given price series.

    Args:
        prices: List of closing prices
        period: Moving average period (default 5)

    Returns:
        Most recent moving average value
    """
    if len(prices) < period:
        raise ValueError(f"Need at least {period} prices to calculate {period}-day moving average")
    
    s = pd.Series(prices)
    ma = s.rolling(window=period).mean()
    return float(ma.iloc[-1])

if __name__ == "__main__":
    # Test with 20 days of sample price data
    test_prices_20days = [280.0, 282.5, 281.0, 283.5, 285.0, 284.0, 286.5, 287.0, 285.5, 288.0,
                         289.5, 290.0, 288.5, 291.0, 292.5, 291.5, 293.0, 294.5, 295.0, 296.0]
    result = calc_moving_average(test_prices_20days, 5)
    assert isinstance(result, float)
    assert result > 0
    print(f"5-day MA: {result:.2f}")