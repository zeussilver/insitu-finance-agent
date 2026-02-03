import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

def get_stock_hist(symbol: str = "TSLA", days: int = 30) -> Optional[float]:
    """Get the highest closing price of a stock in the last N days.

    Args:
        symbol: Stock ticker symbol (default: 'TSLA')
        days: Number of days to look back (default: 30)

    Returns:
        Highest closing price in the specified period as float
        None if fetch fails or no data available
    """
    try:
        # Calculate date range
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Fetch stock data
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            return None
            
        # Get maximum close price
        max_close = df['Close'].max()
        return float(max_close)
        
    except Exception:
        return None

if __name__ == "__main__":
    # Test with TSLA (should return a float value)
    result = get_stock_hist("TSLA", 30)
    assert result is not None, "Should return highest close price for TSLA"
    assert isinstance(result, float), "Result should be a float"
    print(f"TSLA highest close in last 30 days: ${result:.2f}")
    
    # Test with invalid symbol (should return None)
    result_invalid = get_stock_hist("INVALID_SYMBOL", 30)
    assert result_invalid is None, "Should return None for invalid symbol"
    print("Test passed!")