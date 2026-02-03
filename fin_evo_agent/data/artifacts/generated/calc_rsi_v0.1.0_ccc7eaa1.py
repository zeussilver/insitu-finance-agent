import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI indicator.

    Args:
        prices: List of closing prices
        period: RSI period (default 14)

    Returns:
        RSI value between 0 and 100
    """
    if len(prices) < period + 1:
        return 50.0  # Return neutral value for insufficient data

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

if __name__ == "__main__":
    # Test with sample price data (simulating last 30 days of AAPL-like prices)
    test_prices_30d = [170.0, 171.5, 169.8, 172.3, 173.1, 171.9, 174.2, 175.6, 174.8, 176.2,
                       177.5, 176.9, 178.3, 179.1, 178.7, 180.2, 181.5, 180.8, 182.3, 183.7,
                       182.9, 184.1, 185.6, 184.8, 186.2, 187.5, 186.9, 188.3, 189.1, 188.7]
    result = calc_rsi(test_prices_30d, 14)
    assert 0 <= result <= 100
    print(f"RSI-14: {result:.2f}")
    
    # Test with smaller dataset
    test_prices_small = [44, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45, 45.5, 46, 45.8, 46.2, 46.5, 47.0, 46.8]
    result2 = calc_rsi(test_prices_small, 14)
    assert 0 <= result2 <= 100
    print("All tests passed!")