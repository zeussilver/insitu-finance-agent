import yfinance as yf

def get_index_daily() -> float:
    """
    Get the latest closing price of the S&P 500 index (^GSPC).
    
    Returns:
        float: The latest closing price of the S&P 500 index.
    """
    sp500 = yf.Ticker("^GSPC")
    hist = sp500.history(period="1d")
    if not hist.empty:
        return float(hist['Close'].iloc[-1])
    else:
        raise ValueError("Failed to retrieve S&P 500 data")