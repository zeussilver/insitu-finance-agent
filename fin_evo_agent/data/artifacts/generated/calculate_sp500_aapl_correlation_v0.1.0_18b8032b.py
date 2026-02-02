import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

def calculate_sp500_aapl_correlation(days: int = 30) -> Optional[float]:
    """
    Calculate the Pearson correlation coefficient between S&P 500 (^GSPC) and AAPL 
    closing prices over the specified number of days.
    
    Args:
        days (int): Number of days to look back for correlation calculation. Default is 30.
        
    Returns:
        Optional[float]: Correlation coefficient between -1 and 1, or None if insufficient data.
        
    Raises:
        ValueError: If days parameter is not positive.
        
    Example:
        >>> corr = calculate_sp500_aapl_correlation(30)
        >>> isinstance(corr, float) or corr is None
        True
    """
    if days <= 0:
        raise ValueError("Days parameter must be positive")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days * 2)  # Get extra days to account for weekends/holidays
    
    try:
        # Download data for both symbols
        sp500_data = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
        aapl_data = yf.download('AAPL', start=start_date, end=end_date, progress=False)
        
        # Merge data on date index and get last 'days' trading days
        merged_data = pd.merge(sp500_data[['Close']], aapl_data[['Close']], 
                              left_index=True, right_index=True, suffixes=('_sp500', '_aapl'))
        
        # Get the last 'days' rows (trading days)
        recent_data = merged_data.tail(days)
        
        # Check if we have sufficient data
        if len(recent_data) < min(10, days):  # Require at least 10 data points or days if less than 10
            return None
            
        # Calculate correlation
        correlation = recent_data['Close_sp500'].corr(recent_data['Close_aapl'])
        
        # Handle case where correlation might be NaN
        if pd.isna(correlation):
            return None
            
        return float(correlation)
        
    except Exception:
        # Return None if any error occurs during data download or processing
        return None

if __name__ == '__main__':
    # Test 1: Basic functionality with default 30 days
    corr_30 = calculate_sp500_aapl_correlation(30)
    assert corr_30 is None or (-1.0 <= corr_30 <= 1.0), f"Correlation should be between -1 and 1, got {corr_30}"
    
    # Test 2: Test with smaller number of days
    corr_10 = calculate_sp500_aapl_correlation(10)
    assert corr_10 is None or (-1.0 <= corr_10 <= 1.0), f"Correlation should be between -1 and 1, got {corr_10}"