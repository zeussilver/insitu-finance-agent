import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def calculate_volume_price_divergence(ticker: str = "MSFT", days: int = 30) -> int:
    """
    Calculate the number of days in the specified period where price increased 
    but volume decreased compared to the previous day (volume-price divergence).
    
    Args:
        ticker (str): Stock ticker symbol (default: "MSFT")
        days (int): Number of days to analyze (default: 30)
    
    Returns:
        int: Count of divergence days in the specified period
    
    Raises:
        ValueError: If insufficient data is available for the requested period
    """
    # Fetch more data than needed to ensure we have enough for comparisons
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 60)  # Extra buffer for weekends/holidays
    
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date)
    except Exception as e:
        raise ValueError(f"Failed to download data for {ticker}: {str(e)}")
    
    if len(stock_data) < days + 1:
        raise ValueError(f"Insufficient data available for {ticker}. Need at least {days + 1} days, got {len(stock_data)}")
    
    # Calculate price and volume changes
    stock_data['price_change'] = stock_data['Close'].diff()
    stock_data['volume_change'] = stock_data['Volume'].diff()
    
    # Identify divergence: price up (positive change) AND volume down (negative change)
    divergence_condition = (stock_data['price_change'] > 0) & (stock_data['volume_change'] < 0)
    
    # Get the last 'days' number of trading days and count divergences
    recent_data = stock_data.tail(days)
    divergence_count = divergence_condition.loc[recent_data.index].sum()
    
    return int(divergence_count)

if __name__ == '__main__':
    # Test with MSFT and 30 days
    msft_divergence = calculate_volume_price_divergence("MSFT", 30)
    assert isinstance(msft_divergence, int)
    assert msft_divergence >= 0
    
    # Test with different ticker
    aapl_divergence = calculate_volume_price_divergence("AAPL", 10)
    assert isinstance(aapl_divergence, int)
    assert aapl_divergence >= 0