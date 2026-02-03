import yfinance as yf
import pandas as pd
from typing import Optional
import warnings
warnings.filterwarnings('ignore')

def get_etf_hist() -> Optional[float]:
    """Fetch the latest closing price for SPY ETF.

    This function retrieves the most recent closing price for the SPY ETF
    (SPDR S&P 500 ETF Trust) using Yahoo Finance data.

    Returns:
        float: The latest closing price of SPY ETF
        None: If the data fetch fails, returns None (e.g., due to network issues,
              invalid symbol, or no available data)

    Note:
        - SPY is one of the most liquid ETFs tracking the S&P 500 index
        - The function fetches the last 5 days of data to ensure at least one
          valid trading day is captured
        - Returns None rather than raising exceptions for robust error handling
    """
    try:
        ticker = yf.Ticker("SPY")
        # Fetch last 5 days to ensure we get at least one trading day
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return None
            
        # Get the most recent closing price
        latest_close = hist['Close'].iloc[-1]
        return float(latest_close)
        
    except Exception:
        return None

if __name__ == "__main__":
    # Test 1: Should return a positive float value
    price = get_etf_hist()
    assert price is not None, "Should return a price value for SPY"
    assert isinstance(price, float) and price > 0, "Price should be a positive float"
    
    # Test 2: Verify it's a reasonable SPY price range (above $100 typically)
    assert price > 100.0, "SPY price should be above $100"
    print(f"Latest SPY close price: ${price:.2f}")