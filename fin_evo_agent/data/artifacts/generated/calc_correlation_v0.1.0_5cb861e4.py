import pandas as pd
import numpy as np

def calc_correlation(prices1: list, prices2: list, period: int = 30) -> float:
    """Calculate correlation coefficient between two price series.

    Args:
        prices1: List of prices for first asset (e.g., S&P 500)
        prices2: List of prices for second asset (e.g., AAPL)
        period: Lookback period in days (default 30)

    Returns:
        Correlation coefficient between -1 and 1
    """
    # Use minimum available data if less than period
    min_len = min(len(prices1), len(prices2))
    if min_len == 0:
        return 0.0
    
    effective_period = min(period, min_len)
    
    # Take last 'effective_period' values
    series1 = pd.Series(prices1[-effective_period:])
    series2 = pd.Series(prices2[-effective_period:])
    
    # Calculate correlation, return 0 if undefined
    correlation = series1.corr(series2)
    return float(correlation) if not pd.isna(correlation) else 0.0

if __name__ == "__main__":
    # Test case 1: Perfect positive correlation
    spx_prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    aapl_prices = [150, 151.5, 153, 154.5, 156, 157.5, 159, 160.5, 162, 163.5]
    result1 = calc_correlation(spx_prices, aapl_prices, period=10)
    assert abs(result1 - 1.0) < 0.001
    
    # Test case 2: Perfect negative correlation
    spx_prices2 = [100, 101, 102, 103, 104]
    aapl_prices2 = [200, 198, 196, 194, 192]
    result2 = calc_correlation(spx_prices2, aapl_prices2, period=5)
    assert abs(result2 + 1.0) < 0.001
    
    print("All tests passed!")