import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_60d_volatility(ticker: str, period: str = "6mo") -> float:
    """
    Calculate the 60-day annualized volatility for a given stock ticker.
    
    Volatility is calculated as the annualized standard deviation of daily log returns
    over a rolling 60-day window. The most recent volatility value is returned.
    
    Parameters:
    ticker (str): Stock ticker symbol (e.g., 'TSLA')
    period (str): Data period to fetch (default: '6mo' for 6 months)
    
    Returns:
    float: Annualized 60-day volatility as a decimal (e.g., 0.35 for 35%)
           Returns NaN if insufficient data is available
    
    Example:
    >>> vol = calculate_60d_volatility('TSLA')
    >>> isinstance(vol, float)
    True
    """
    # Fetch historical data
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
    except Exception:
        return np.nan
    
    if len(hist) < 60:
        return np.nan
    
    # Calculate daily log returns
    hist['log_returns'] = np.log(hist['Close'] / hist['Close'].shift(1))
    
    # Calculate rolling 60-day volatility (annualized)
    hist['volatility'] = hist['log_returns'].rolling(window=60).std() * np.sqrt(252)
    
    # Return the most recent volatility value
    return hist['volatility'].iloc[-1]

if __name__ == '__main__':
    # Test 1: Valid ticker should return positive volatility
    tsla_vol = calculate_60d_volatility('TSLA')
    assert isinstance(tsla_vol, float) and not np.isnan(tsla_vol) and tsla_vol > 0
    
    # Test 2: Invalid ticker should return NaN
    invalid_vol = calculate_60d_volatility('INVALID_TICKER_123')
    assert np.isnan(invalid_vol)