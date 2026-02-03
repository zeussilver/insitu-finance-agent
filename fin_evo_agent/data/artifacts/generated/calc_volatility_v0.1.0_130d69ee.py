import pandas as pd
import numpy as np

def calc_volatility(prices: list, period: int = 60) -> float:
    """Calculate annualized volatility over a given period.

    Args:
        prices: List of closing prices
        period: Number of days for volatility calculation (default 60)

    Returns:
        Annualized volatility as a percentage (e.g., 0.25 for 25%)
    """
    if len(prices) < period + 1:
        return 0.0  # Not enough data to calculate
    
    # Convert to pandas Series for easier calculation
    s = pd.Series(prices)
    
    # Calculate daily log returns
    log_returns = np.log(s / s.shift(1))
    
    # Calculate rolling standard deviation of returns
    volatility = log_returns.rolling(window=period).std()
    
    # Annualize volatility (252 trading days per year)
    annualized_volatility = volatility * np.sqrt(252)
    
    return float(annualized_volatility.iloc[-1])

if __name__ == "__main__":
    # Test with synthetic price data
    test_prices1 = [100 + i*0.1 + (i%10)*0.5 for i in range(70)]
    result1 = calc_volatility(test_prices1, 60)
    assert result1 >= 0
    
    test_prices2 = [100] * 61  # Flat prices should give zero volatility
    result2 = calc_volatility(test_prices2, 60)
    assert abs(result2) < 1e-10
    
    print("Tests passed!")