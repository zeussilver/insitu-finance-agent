def calc_volume_price_divergence(prices: list, volumes: list, period: int = 30) -> bool:
    """Calculate volume-price divergence (price up but volume down) over specified period.

    Args:
        prices: List of closing prices (length >= period + 1)
        volumes: List of trading volumes (same length as prices)
        period: Lookback period in days (default 30)

    Returns:
        True if price increased AND volume decreased over the period, False otherwise
    """
    if len(prices) < period + 1 or len(volumes) < period + 1:
        return False
    
    price_current = prices[-1]
    price_past = prices[-period - 1]
    volume_current = volumes[-1]
    volume_past = volumes[-period - 1]
    
    price_up = price_current > price_past
    volume_down = volume_current < volume_past
    
    return price_up and volume_down

if __name__ == "__main__":
    # Test case 1: Price up (100→105), Volume down (1000→900) → True
    test_prices_1 = [100] * 30 + [105]
    test_volumes_1 = [1000] * 30 + [900]
    assert calc_volume_price_divergence(test_prices_1, test_volumes_1) == True
    
    # Test case 2: Price up (100→105), Volume up (1000→1100) → False
    test_prices_2 = [100] * 30 + [105]
    test_volumes_2 = [1000] * 30 + [1100]
    assert calc_volume_price_divergence(test_prices_2, test_volumes_2) == False