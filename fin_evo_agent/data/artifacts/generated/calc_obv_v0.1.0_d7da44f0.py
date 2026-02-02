import pandas as pd
import numpy as np

def calc_obv(prices: list, volumes: list) -> float:
    """Calculate On Balance Volume (OBV) indicator.

    OBV is a technical analysis indicator that uses volume flow to predict 
    changes in stock price. It adds volume on up days and subtracts volume on down days.

    Args:
        prices: List of closing prices
        volumes: List of trading volumes corresponding to each price

    Returns:
        Final OBV value as a float
    """
    if len(prices) != len(volumes):
        raise ValueError("Prices and volumes must have the same length")
    
    if len(prices) == 0:
        return 0.0
    
    if len(prices) == 1:
        return float(volumes[0])
    
    price_series = pd.Series(prices)
    volume_series = pd.Series(volumes)
    
    # Calculate price changes
    price_diff = price_series.diff()
    
    # Create OBV direction: +1 for up, -1 for down, 0 for no change
    obv_direction = np.where(price_diff > 0, 1, np.where(price_diff < 0, -1, 0))
    
    # Calculate OBV values
    obv_values = volume_series * obv_direction
    obv_values.iloc[0] = volume_series.iloc[0]  # First OBV value is first volume
    
    # Cumulative sum to get OBV
    obv_cumulative = obv_values.cumsum()
    
    return float(obv_cumulative.iloc[-1])

if __name__ == "__main__":
    # Test case 1: Simple up and down movements
    test_prices1 = [10, 11, 10, 12, 11]
    test_volumes1 = [100, 150, 200, 180, 120]
    result1 = calc_obv(test_prices1, test_volumes1)
    expected1 = 100 + 150 - 200 + 180 - 120  # 110
    assert result1 == expected1
    
    # Test case 2: All prices increasing
    test_prices2 = [5, 6, 7, 8]
    test_volumes2 = [50, 60, 70, 80]
    result2 = calc_obv(test_prices2, test_volumes2)
    expected2 = 50 + 60 + 70 + 80  # 260
    assert result2 == expected2