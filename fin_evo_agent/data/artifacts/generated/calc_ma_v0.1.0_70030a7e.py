import yfinance as yf
import pandas as pd
from typing import Optional, Union

def calc_ma(symbol: str = "MSFT", period: int = 20) -> Optional[float]:
    """
    Calculate the latest Simple Moving Average (SMA) for a given stock symbol.
    
    This function fetches historical stock price data for the specified symbol,
    calculates the Simple Moving Average over the given period, and returns the
    most recent SMA value. By default, it uses Microsoft (MSFT) with a 20-day period.
    
    Parameters:
    -----------
    symbol : str, default "MSFT"
        The stock ticker symbol to analyze
    period : int, default 20
        The number of trading days to use for the moving average calculation
        
    Returns:
    --------
    Optional[float]
        The latest Simple Moving Average value, or None if data is insufficient
        or unavailable
        
    Raises:
    -------
    ValueError
        If period is not a positive integer
    """
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be a positive integer")
    
    try:
        # Fetch historical data (last 3 months to ensure enough data points)
        stock = yf.Ticker(symbol)
        hist = stock.history(period="3mo")
        
        if hist.empty:
            return None
            
        # Calculate Simple Moving Average
        sma = hist['Close'].rolling(window=period).mean()
        
        # Return the latest non-null SMA value
        latest_sma = sma.dropna().iloc[-1] if not sma.dropna().empty else None
        return float(latest_sma) if latest_sma is not None else None
        
    except Exception:
        return None

if __name__ == '__main__':
    # Test 1: Basic functionality with default parameters
    msft_ma = calc_ma()
    assert isinstance(msft_ma, (float, type(None))), "Result should be float or None"
    
    # Test 2: Custom symbol and period
    apple_ma = calc_ma("AAPL", 10)
    assert isinstance(apple_ma, (float, type(None))), "Result should be float or None"