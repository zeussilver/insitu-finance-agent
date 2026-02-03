import pandas as pd
import numpy as np

def calc_kdj(high: list, low: list, close: list, k_period: int = 9, k_smoothing: int = 3, d_smoothing: int = 3) -> dict:
    """Calculate KDJ indicator.

    Args:
        high: List of high prices
        low: List of low prices  
        close: List of closing prices
        k_period: Period for calculating RSV (default 9)
        k_smoothing: Smoothing period for %K (default 3)
        d_smoothing: Smoothing period for %D (default 3)

    Returns:
        Dictionary with keys 'k', 'd', 'j' containing the respective indicator values
    """
    # Check if we have enough data
    min_length = max(k_period, k_smoothing + k_period - 1, d_smoothing + k_smoothing + k_period - 2)
    if len(high) < min_length or len(low) < min_length or len(close) < min_length:
        return {'k': 50.0, 'd': 50.0, 'j': 50.0}
    
    # Convert to pandas Series for easier calculation
    high_series = pd.Series(high)
    low_series = pd.Series(low)
    close_series = pd.Series(close)
    
    # Calculate highest high and lowest low over k_period
    highest_high = high_series.rolling(window=k_period).max()
    lowest_low = low_series.rolling(window=k_period).min()
    
    # Calculate RSV (Raw Stochastic Value)
    rsv = (close_series - lowest_low) / (highest_high - lowest_low) * 100
    
    # Handle division by zero
    rsv = rsv.replace([np.inf, -np.inf], 50.0)
    rsv = rsv.fillna(50.0)
    
    # Calculate %K using SMA with initial value of 50
    k_values = [50.0]  # Initial K value
    for i in range(1, len(rsv)):
        if pd.isna(rsv.iloc[i]):
            k_values.append(50.0)
        else:
            k_val = (k_values[-1] * (k_smoothing - 1) + rsv.iloc[i]) / k_smoothing
            k_values.append(k_val)
    
    k_series = pd.Series(k_values)
    
    # Calculate %D using SMA of %K
    d_values = [50.0]  # Initial D value
    for i in range(1, len(k_series)):
        if pd.isna(k_series.iloc[i]):
            d_values.append(50.0)
        else:
            d_val = (d_values[-1] * (d_smoothing - 1) + k_series.iloc[i]) / d_smoothing
            d_values.append(d_val)
    
    d_series = pd.Series(d_values)
    
    # Calculate %J
    j_series = 3 * k_series - 2 * d_series
    
    # Get the latest values
    k_latest = float(k_series.iloc[-1]) if not pd.isna(k_series.iloc[-1]) else 50.0
    d_latest = float(d_series.iloc[-1]) if not pd.isna(d_series.iloc[-1]) else 50.0
    j_latest = float(j_series.iloc[-1]) if not pd.isna(j_series.iloc[-1]) else 50.0
    
    # Clamp values to reasonable range (though J can go outside 0-100)
    k_latest = max(0, min(100, k_latest))
    d_latest = max(0, min(100, d_latest))
    
    return {'k': k_latest, 'd': d_latest, 'j': j_latest}

if __name__ == "__main__":
    # Test with sample data
    test_high = [150, 152, 151, 153, 155, 154, 156, 158, 157, 159, 160, 162, 161, 163]
    test_low = [148, 149, 147, 148, 150, 149, 151, 153, 152, 154, 155, 157, 156, 158]
    test_close = [149, 151, 148, 152, 154, 150, 155, 157, 153, 158, 159, 161, 158, 162]
    
    result1 = calc_kdj(test_high, test_low, test_close)
    assert isinstance(result1['k'], float)
    assert isinstance(result1['d'], float)
    assert isinstance(result1['j'], float)
    
    # Test with insufficient data
    short_high = [150, 152]
    short_low = [148, 149]
    short_close = [149, 151]
    
    result2 = calc_kdj(short_high, short_low, short_close)
    assert result2['k'] == 50.0
    assert result2['d'] == 50.0
    assert result2['j'] == 50.0
    
    print("Tests passed!")