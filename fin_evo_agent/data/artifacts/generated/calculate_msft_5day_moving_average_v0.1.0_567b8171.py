import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

def calculate_msft_5day_moving_average() -> pd.Series:
    """
    Calculate the 5-day simple moving average (SMA) for Microsoft (MSFT) stock
    over the last 20 trading days.
    
    This function downloads MSFT stock price data, calculates the 5-day SMA,
    and returns the most recent 20 days of SMA values.
    
    Returns:
        pd.Series: A pandas Series containing the 5-day moving average values
                   for the last 20 trading days, indexed by date.
                   
    Raises:
        ValueError: If insufficient data is available to calculate the moving average
    """
    # Calculate date range - get extra days to ensure we have enough for 5-day SMA
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=40)  # Get ~40 calendar days to ensure 25+ trading days
    
    try:
        # Download MSFT stock data
        msft = yf.Ticker("MSFT")
        hist = msft.history(start=start_date.strftime('%Y-%m-%d'), 
                            end=(end_date + timedelta(days=1)).strftime('%Y-%m-%d'))
    except Exception as e:
        raise ValueError(f"Failed to download MSFT historical data: {str(e)}")
    
    if hist.empty:
        raise ValueError("No historical data available for MSFT")
    
    # Ensure we have enough data points
    if len(hist) < 5:
        raise ValueError("Insufficient data points to calculate 5-day moving average")
    
    # Calculate 5-day simple moving average on closing prices
    hist['SMA_5'] = hist['Close'].rolling(window=5).mean()
    
    # Get the last 20 days of SMA values (excluding NaN values from the beginning)
    sma_series = hist['SMA_5'].dropna().tail(20)
    
    if len(sma_series) == 0:
        raise ValueError("No valid moving average values calculated")
    
    return sma_series

if __name__ == '__main__':
    # Test 1: Verify the function returns a pandas Series
    result = calculate_msft_5day_moving_average()
    assert isinstance(result, pd.Series), "Result should be a pandas Series"
    
    # Test 2: Verify we get approximately 20 data points (allowing for market holidays)
    assert len(result) >= 15, "Should return at least 15 data points (accounting for weekends/holidays)"