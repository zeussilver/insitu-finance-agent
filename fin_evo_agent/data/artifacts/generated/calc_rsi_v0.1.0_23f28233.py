import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index) indicator.

    Args:
        prices: List of closing prices (float values)
        period: RSI period for calculation (default 14)

    Returns:
        RSI value as float between 0 and 100
    """
    if len(prices) < period + 1:
        return 50.0  # Return neutral value when insufficient data
    
    # Convert to pandas Series for easier calculation
    s = pd.Series(prices)
    
    # Calculate price differences
    delta = s.diff()
    
    # Separate gains and losses
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Calculate average gains and losses using rolling window
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Calculate RS (Relative Strength)
    rs = avg_gain / avg_loss.replace(0, np.inf)  # Avoid division by zero
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    
    # Return the last RSI value as float
    return float(rsi.iloc[-1])

if __name__ == "__main__":
    # Test case 1: Basic functionality
    test_prices_1 = [44.0, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45.0, 45.5, 46.0, 
                     46.5, 47.0, 46.8, 47.2, 47.5, 48.0, 47.8, 48.2, 48.5, 49.0]
    result_1 = calc_rsi(test_prices_1, 14)
    assert 0 <= result_1 <= 100, f"RSI should be between 0 and 100, got {result_1}"
    
    # Test case 2: Insufficient data handling
    test_prices_2 = [100.0, 101.0, 102.0]
    result_2 = calc_rsi(test_prices_2, 14)
    assert result_2 == 50.0, f"Should return 50.0 for insufficient data, got {result_2}"