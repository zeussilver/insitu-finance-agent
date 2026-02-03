import pandas as pd
import numpy as np

def calc_equal_weight_portfolio_return(price_series_list: list, period_days: int = 30) -> float:
    """Calculate equal-weight portfolio return over specified period.

    Args:
        price_series_list: List of price series (each as list or pd.Series) for each asset
        period_days: Number of days to calculate return over (default 30)

    Returns:
        Portfolio return as a decimal (e.g., 0.05 for 5% return)
    """
    if not price_series_list:
        return 0.0
    
    num_assets = len(price_series_list)
    weights = 1.0 / num_assets
    total_return = 0.0
    
    for prices in price_series_list:
        if isinstance(prices, pd.Series):
            price_list = prices.tolist()
        else:
            price_list = list(prices)
            
        if len(price_list) < period_days + 1:
            # Not enough data, assume 0 return for this asset
            asset_return = 0.0
        else:
            start_price = price_list[-period_days - 1]
            end_price = price_list[-1]
            if start_price == 0:
                asset_return = 0.0
            else:
                asset_return = (end_price - start_price) / start_price
        
        total_return += weights * asset_return
    
    return total_return

if __name__ == "__main__":
    # Sample price data for 3 assets over 35 days (more than 30 needed)
    aapl_prices = [150 + i*0.5 for i in range(35)]  # Steadily increasing
    googl_prices = [2800 - i*2 for i in range(35)]  # Steadily decreasing
    amzn_prices = [3200 + i*1.5 for i in range(35)]  # Increasing
    
    portfolio_return = calc_equal_weight_portfolio_return(
        [aapl_prices, googl_prices, amzn_prices], 
        period_days=30
    )
    
    # Verify it's a float and within reasonable bounds
    assert isinstance(portfolio_return, float)
    assert -1.0 <= portfolio_return <= 1.0  # Should be between -100% and +100%