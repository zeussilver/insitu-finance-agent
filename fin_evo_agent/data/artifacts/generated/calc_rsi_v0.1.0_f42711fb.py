import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """
    计算 RSI (相对强弱指标)。

    Args:
        prices: 收盘价列表 (float)
        period: 计算周期，默认 14

    Returns:
        RSI 值 (0-100 之间的浮点数)
    """
    if len(prices) < period + 1:
        return 50.0  # 数据不足时返回中性值

    s = pd.Series(prices)
    delta = s.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # 避免除以零
    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


if __name__ == "__main__":
    # Test case 1: Normal data
    prices = [10, 12, 11, 13, 15, 17, 16, 15, 14, 13, 14, 15, 16, 17, 18]
    val = calc_rsi(prices, 5)
    print(f"RSI: {val}")
    assert 0 <= val <= 100, f"RSI should be between 0 and 100, got {val}"

    # Test case 2: Insufficient data
    short_prices = [10, 11, 12]
    val2 = calc_rsi(short_prices, 14)
    assert val2 == 50.0, f"Should return 50.0 for insufficient data, got {val2}"

    print("All tests passed!")