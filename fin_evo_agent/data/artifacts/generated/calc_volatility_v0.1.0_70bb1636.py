import pandas as pd
import numpy as np

def calc_volatility(prices: list, period: int = 60) -> float:
    """Calculate annualized volatility over specified period.

    Args:
        prices: List of closing prices
        period: Volatility period in days (default 60)

    Returns:
        Annualized volatility as a decimal (e.g., 0.25 for 25%)
    """
    if len(prices) < period + 1:
        return 0.0  # Return 0 for insufficient data
    
    # Convert to pandas Series for easier calculation
    s = pd.Series(prices)
    
    # Calculate daily log returns
    log_returns = np.log(s / s.shift(1))
    
    # Calculate rolling standard deviation of returns
    rolling_std = log_returns.rolling(window=period).std()
    
    # Annualize volatility (assuming 252 trading days per year)
    annualized_vol = rolling_std * np.sqrt(252)
    
    # Return the most recent volatility value
    return float(annualized_vol.iloc[-1])

if __name__ == "__main__":
    # Test with synthetic price data
    test_prices_1 = [100 + i * 0.1 + np.random.normal(0, 1) for i in range(70)]
    result_1 = calc_volatility(test_prices_1, 60)
    assert isinstance(result_1, float)
    assert result_1 >= 0
    
    # Test with constant prices (should give 0 volatility)
    test_prices_2 = [100] * 61
    result_2 = calc_volatility(test_prices_2, 60)
    assert result_2 == 0.0