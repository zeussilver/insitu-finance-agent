import pandas as pd

def get_stock_hist(prices: list) -> float:
    """Get the highest closing price from provided price history.

    Args:
        prices: List of closing prices (assumed to be last 30 days)

    Returns:
        Highest closing price in the provided list
    """
    if not prices:
        return 0.0
    
    return float(pd.Series(prices).max())

if __name__ == "__main__":
    # Simulated TSLA closing prices for last 30 days
    tsla_prices = [250.1, 255.3, 248.7, 260.2, 257.8, 262.4, 259.9, 265.1, 
                   263.5, 268.2, 270.0, 267.3, 272.8, 275.4, 273.1, 278.9,
                   280.5, 277.2, 282.6, 285.0, 283.7, 288.4, 290.1, 287.9,
                   292.3, 295.8, 293.2, 298.7, 300.5, 297.6]
    
    result = get_stock_hist(tsla_prices)
    assert result == 300.5
    assert isinstance(result, float)