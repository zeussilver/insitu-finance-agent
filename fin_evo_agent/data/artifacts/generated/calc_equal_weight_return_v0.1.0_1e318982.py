def calc_equal_weight_return(
    prices1: list,
    prices2: list,
    prices3: list,
    period: int = 30
) -> float:
    """Calculate equal-weight portfolio return for three stocks over specified period.

    Args:
        prices1: List of closing prices for first stock (e.g., AAPL)
        prices2: List of closing prices for second stock (e.g., GOOGL)  
        prices3: List of closing prices for third stock (e.g., AMZN)
        period: Number of days to calculate return over (default 30)

    Returns:
        Float representing the equal-weight portfolio return over the period
        (e.g., 0.05 for 5% return)

    Raises:
        ValueError: If any price list has insufficient data points
    """
    # Validate input lengths
    min_required = period
    if len(prices1) < min_required or len(prices2) < min_required or len(prices3) < min_required:
        raise ValueError(f"All price lists must have at least {min_required} data points")
    
    # Calculate individual stock returns over the period
    def calculate_return(prices):
        start_price = prices[-period]
        end_price = prices[-1]
        return (end_price - start_price) / start_price if start_price != 0 else 0.0
    
    return1 = calculate_return(prices1)
    return2 = calculate_return(prices2)
    return3 = calculate_return(prices3)
    
    # Equal weight (1/3 each)
    portfolio_return = (return1 + return2 + return3) / 3.0
    
    return portfolio_return

if __name__ == "__main__":
    # Test case 1: All stocks up 10% over 30 days
    prices1 = [100 * (1 + 0.1 * i / 29) for i in range(30)]  # From 100 to 110
    prices2 = [200 * (1 + 0.1 * i / 29) for i in range(30)]  # From 200 to 220
    prices3 = [300 * (1 + 0.1 * i / 29) for i in range(30)]  # From 300 to 330
    result = calc_equal_weight_return(prices1, prices2, prices3)
    expected = 0.1  # All have ~10% return, average is 10%
    assert abs(result - expected) < 0.01, f"Expected ~0.1, got {result}"
    
    # Test case 2: Mixed returns
    prices1 = [100] * 29 + [110]  # +10%
    prices2 = [200] * 29 + [180]  # -10%  
    prices3 = [300] * 29 + [300]  # 0%
    result = calc_equal_weight_return(prices1, prices2, prices3)
    expected = (0.1 - 0.1 + 0.0) / 3.0  # 0%
    assert abs(result - expected) < 0.001, f"Expected ~0.0, got {result}"
    
    print("All tests passed!")