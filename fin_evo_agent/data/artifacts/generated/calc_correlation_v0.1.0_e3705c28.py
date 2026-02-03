import pandas as pd
import numpy as np

def calc_correlation(series1: list, series2: list, period: int = 30) -> float:
    """Calculate correlation coefficient between two price series.

    Args:
        series1: List of prices for first asset (e.g., S&P 500)
        series2: List of prices for second asset (e.g., AAPL)
        period: Number of days to calculate correlation over (default 30)

    Returns:
        Correlation coefficient between -1 and 1
    """
    # Ensure we have enough data points
    min_length = min(len(series1), len(series2))
    if min_length < period:
        # If insufficient data, use all available points
        if min_length < 2:
            return 0.0  # Not enough data for correlation
    
    # Use the most recent 'period' data points
    end_idx = min_length
    start_idx = max(0, end_idx - period)
    
    s1 = pd.Series(series1[start_idx:end_idx])
    s2 = pd.Series(series2[start_idx:end_idx])
    
    # Calculate correlation
    correlation = s1.corr(s2)
    
    # Handle NaN case (when all values are the same in one series)
    if pd.isna(correlation):
        return 0.0
        
    return float(correlation)

if __name__ == "__main__":
    # Test case 1: Perfect positive correlation
    sp500_test = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    aapl_test = [150, 151.5, 153, 154.5, 156, 157.5, 159, 160.5, 162, 163.5]
    result1 = calc_correlation(sp500_test, aapl_test, period=10)
    assert abs(result1 - 1.0) < 0.001  # Should be nearly perfect correlation
    
    # Test case 2: Perfect negative correlation
    sp500_test2 = [100, 101, 102, 103, 104]
    aapl_test2 = [200, 198, 196, 194, 192]
    result2 = calc_correlation(sp500_test2, aapl_test2, period=5)
    assert abs(result2 + 1.0) < 0.001  # Should be nearly perfect negative correlation