def calculate_volume_price_divergence(
    prices: list,
    volumes: list,
    period: int = 30
) -> bool:
    """Calculate if there's volume-price divergence (price up but volume down) over specified period.

    Args:
        prices: List of closing prices (latest price last)
        volumes: List of trading volumes (latest volume last)
        period: Number of days to look back (default 30)

    Returns:
        True if price increased but volume decreased over the period, False otherwise
    """
    # Check if we have enough data
    if len(prices) < period + 1 or len(volumes) < period + 1:
        return False
    
    # Get current and historical values
    current_price = prices[-1]
    historical_price = prices[-(period + 1)]
    
    current_volume = volumes[-1]
    historical_volume = volumes[-(period + 1)]
    
    # Check for divergence: price up but volume down
    price_up = current_price > historical_price
    volume_down = current_volume < historical_volume
    
    return price_up and volume_down

if __name__ == "__main__":
    # Test case 1: Price up, volume down (divergence exists)
    prices_test1 = [100 + i * 0.5 for i in range(31)]  # Price increasing from 100 to 115
    volumes_test1 = [1000000 - i * 10000 for i in range(31)]  # Volume decreasing from 1M to 700K
    result1 = calculate_volume_price_divergence(prices_test1, volumes_test1, 30)
    assert result1 == True, "Should detect divergence when price up and volume down"
    
    # Test case 2: Price up, volume up (no divergence)
    prices_test2 = [100 + i * 0.5 for i in range(31)]  # Price increasing
    volumes_test2 = [1000000 + i * 10000 for i in range(31)]  # Volume increasing
    result2 = calculate_volume_price_divergence(prices_test2, volumes_test2, 30)
    assert result2 == False, "Should not detect divergence when both price and volume up"
    
    print("All tests passed!")