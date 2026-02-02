import yfinance as yf
import pandas as pd
from typing import List, Optional

def calculate_equal_weight_portfolio_return() -> float:
    """
    Calculate the equal-weight portfolio return for AAPL, GOOGL, and AMZN over the last 30 trading days.
    
    This function:
    1. Fetches historical closing prices for AAPL, GOOGL, and AMZN
    2. Calculates individual stock returns over the last 30 trading days
    3. Computes the equal-weight portfolio return (each stock has 1/3 weight)
    
    Returns:
        float: The portfolio return as a decimal (e.g., 0.05 for 5% return)
        
    Raises:
        ValueError: If insufficient data is available for any of the tickers
        Exception: If there are issues fetching data from Yahoo Finance
    """
    tickers = ['AAPL', 'GOOGL', 'AMZN']
    weights = [1/3, 1/3, 1/3]
    
    # Fetch data for the last 35 days to ensure we have at least 30 trading days
    # (accounting for weekends and holidays)
    try:
        data = yf.download(tickers, period='35d', interval='1d', group_by='ticker')
    except Exception as e:
        raise Exception(f"Failed to fetch data from Yahoo Finance: {e}")
    
    individual_returns = []
    
    for i, ticker in enumerate(tickers):
        try:
            if len(tickers) == 1:
                # Handle single ticker case (though not applicable here)
                ticker_data = data
            else:
                ticker_data = data[ticker]
            
            # Drop rows with missing closing prices
            close_prices = ticker_data['Close'].dropna()
            
            if len(close_prices) < 2:
                raise ValueError(f"Insufficient data for {ticker}: need at least 2 data points")
            
            # Get the last 30 trading days worth of data (or all available if less than 30)
            recent_prices = close_prices.tail(min(31, len(close_prices)))
            
            if len(recent_prices) < 2:
                raise ValueError(f"Insufficient recent data for {ticker}")
            
            # Calculate return: (final_price - initial_price) / initial_price
            initial_price = recent_prices.iloc[0]
            final_price = recent_prices.iloc[-1]
            stock_return = (final_price - initial_price) / initial_price
            
            individual_returns.append(stock_return)
            
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Error processing data for {ticker}: {e}")
    
    # Calculate weighted portfolio return
    portfolio_return = sum(weight * ret for weight, ret in zip(weights, individual_returns))
    
    return float(portfolio_return)

if __name__ == '__main__':
    # Test 1: Function should return a float
    result = calculate_equal_weight_portfolio_return()
    assert isinstance(result, float), "Return value should be a float"
    
    # Test 2: Return value should be a reasonable number (not extremely large)
    # Portfolio returns over 30 days are typically within -1.0 to 1.0 range
    assert -1.0 <= result <= 1.0, f"Return {result} seems unreasonably large for 30-day period"