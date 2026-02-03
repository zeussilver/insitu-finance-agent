import pandas as pd
import numpy as np

def calc_kdj(high: list, low: list, close: list, n: int = 9, m1: int = 3, m2: int = 3) -> dict:
    """Calculate KDJ indicator (Stochastic Oscillator variant).

    Args:
        high: List of high prices
        low: List of low prices  
        close: List of closing prices
        n: Period for RSV calculation (default 9)
        m1: Smoothing period for K line (default 3)
        m2: Smoothing period for D line (default 3)

    Returns:
        Dictionary containing latest K, D, J values
    """
    if len(high) != len(low) or len(low) != len(close):
        raise ValueError("Price lists must have equal length")
    
    if len(close) < n:
        # Return neutral values if insufficient data
        return {"K": 50.0, "D": 50.0, "J": 50.0}
    
    df = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close
    })
    
    # Calculate RSV (Raw Stochastic Value)
    df['lowest_low'] = df['low'].rolling(window=n).min()
    df['highest_high'] = df['high'].rolling(window=n).max()
    df['rsv'] = (df['close'] - df['lowest_low']) / (df['highest_high'] - df['lowest_low']) * 100
    
    # Handle division by zero
    df['rsv'] = df['rsv'].replace([np.inf, -np.inf], 0)
    df['rsv'] = df['rsv'].fillna(0)
    
    # Initialize K and D arrays
    k_values = [50.0]  # Start with neutral value
    d_values = [50.0]  # Start with neutral value
    
    # Calculate K and D iteratively
    for i in range(1, len(df)):
        if pd.isna(df['rsv'].iloc[i]):
            k_values.append(k_values[-1])
            d_values.append(d_values[-1])
        else:
            k_new = (m1 - 1) / m1 * k_values[-1] + 1 / m1 * df['rsv'].iloc[i]
            d_new = (m2 - 1) / m2 * d_values[-1] + 1 / m2 * k_new
            k_values.append(k_new)
            d_values.append(d_new)
    
    df['K'] = k_values
    df['D'] = d_values
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    # Return the latest values
    return {
        "K": float(df['K'].iloc[-1]),
        "D": float(df['D'].iloc[-1]),
        "J": float(df['J'].iloc[-1])
    }

if __name__ == "__main__":
    # Test with sample data
    test_high = [150, 152, 151, 153, 155, 154, 156, 158, 157, 159, 160, 162, 161, 163]
    test_low = [148, 149, 147, 148, 150, 149, 151, 152, 150, 151, 152, 153, 151, 152]
    test_close = [149, 151, 148, 152, 154, 150, 155, 157, 151, 153, 154, 156, 152, 155]
    
    result = calc_kdj(test_high, test_low, test_close)
    assert 0 <= result["K"] <= 100
    assert 0 <= result["D"] <= 100
    
    # Test with insufficient data
    short_high = [150, 152]
    short_low = [148, 149] 
    short_close = [149, 151]
    result2 = calc_kdj(short_high, short_low, short_close)
    assert result2 == {"K": 50.0, "D": 50.0, "J": 50.0}