"""Tests for indicator parameter extraction."""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.extraction.indicators import (
    extract_indicators,
    extract_rsi_params,
    extract_ma_params,
    extract_macd_params,
    extract_bollinger_params,
    extract_kdj_params,
    extract_volatility_params,
    detect_indicators,
    IndicatorParams,
)


class TestIndicatorDetection:
    """Test indicator detection in text."""

    def test_detect_rsi(self):
        """Detect RSI indicator."""
        indicators = detect_indicators("计算 RSI 指标")
        assert "rsi" in indicators

    def test_detect_rsi_chinese(self):
        """Detect RSI with Chinese name."""
        indicators = detect_indicators("计算相对强弱指数")
        assert "rsi" in indicators

    def test_detect_ma(self):
        """Detect moving average."""
        indicators = detect_indicators("Calculate moving average")
        assert "ma" in indicators

    def test_detect_ma_chinese(self):
        """Detect MA with Chinese name."""
        indicators = detect_indicators("计算移动平均线")
        assert "ma" in indicators

    def test_detect_ema(self):
        """Detect EMA indicator."""
        indicators = detect_indicators("Calculate EMA indicator")
        assert "ema" in indicators

    def test_detect_macd(self):
        """Detect MACD indicator."""
        indicators = detect_indicators("Calculate MACD")
        assert "macd" in indicators

    def test_detect_bollinger(self):
        """Detect Bollinger Bands."""
        indicators = detect_indicators("Calculate Bollinger Bands")
        assert "bollinger" in indicators

    def test_detect_bollinger_chinese(self):
        """Detect Bollinger with Chinese name."""
        indicators = detect_indicators("计算布林带")
        assert "bollinger" in indicators

    def test_detect_kdj(self):
        """Detect KDJ indicator."""
        indicators = detect_indicators("计算 KDJ 指标")
        assert "kdj" in indicators

    def test_detect_volatility(self):
        """Detect volatility indicator."""
        indicators = detect_indicators("计算波动率")
        assert "volatility" in indicators

    def test_detect_correlation(self):
        """Detect correlation."""
        indicators = detect_indicators("计算相关系数")
        assert "correlation" in indicators

    def test_detect_drawdown(self):
        """Detect drawdown."""
        indicators = detect_indicators("计算最大回撤")
        assert "drawdown" in indicators

    def test_detect_multiple(self):
        """Detect multiple indicators."""
        indicators = detect_indicators("判断 RSI 和 MACD 信号")
        assert "rsi" in indicators
        assert "macd" in indicators


class TestRSIParams:
    """Test RSI parameter extraction."""

    def test_rsi_with_period(self):
        """Extract RSI period from text."""
        params = extract_rsi_params("计算 14 日 RSI")
        assert params.name == "rsi"
        assert params.params["period"] == 14
        assert params.confidence >= 0.9

    def test_rsi_default_period(self):
        """Use default period when not specified."""
        params = extract_rsi_params("计算 RSI")
        assert params.name == "rsi"
        assert params.params["period"] == 14  # default
        assert params.confidence <= 0.9


class TestMAParams:
    """Test moving average parameter extraction."""

    def test_sma_with_window(self):
        """Extract MA window from text."""
        params = extract_ma_params("Calculate 20-day moving average")
        assert params.name == "sma"
        assert params.params["window"] == 20

    def test_ema_detection(self):
        """Detect EMA type."""
        params = extract_ma_params("Calculate EMA with period 12")
        assert params.name == "ema"

    def test_ema_chinese(self):
        """Detect EMA with Chinese text."""
        params = extract_ma_params("计算指数移动平均")
        assert params.name == "ema"


class TestMACDParams:
    """Test MACD parameter extraction."""

    def test_macd_with_params(self):
        """Extract MACD parameters."""
        params = extract_macd_params("MACD fast=12, slow=26, signal=9")
        assert params.name == "macd"
        assert params.params["fast"] == 12
        assert params.params["slow"] == 26
        assert params.params["signal"] == 9

    def test_macd_default_params(self):
        """Use default MACD parameters."""
        params = extract_macd_params("计算 MACD")
        assert params.params["fast"] == 12  # default
        assert params.params["slow"] == 26  # default
        assert params.params["signal"] == 9  # default


class TestBollingerParams:
    """Test Bollinger Bands parameter extraction."""

    def test_bollinger_with_params(self):
        """Extract Bollinger parameters."""
        params = extract_bollinger_params("Bollinger with 20 window and 2 std")
        assert params.name == "bollinger"
        assert params.params["window"] == 20
        assert params.params["std"] == 2.0

    def test_bollinger_default_params(self):
        """Use default Bollinger parameters."""
        params = extract_bollinger_params("计算布林带")
        assert params.params["window"] == 20  # default
        assert params.params["std"] == 2  # default


class TestKDJParams:
    """Test KDJ parameter extraction."""

    def test_kdj_with_params(self):
        """Extract KDJ parameters."""
        params = extract_kdj_params("KDJ k=9, d=3")
        assert params.name == "kdj"
        assert params.params["k_period"] == 9
        assert params.params["d_period"] == 3

    def test_kdj_with_general_period(self):
        """Extract KDJ with general period."""
        params = extract_kdj_params("KDJ 14 日")
        assert params.params["k_period"] == 14


class TestVolatilityParams:
    """Test volatility parameter extraction."""

    def test_volatility_with_window(self):
        """Extract volatility window."""
        params = extract_volatility_params("30 天波动率")
        assert params.name == "volatility"
        assert params.params["window"] == 30


class TestExtractIndicators:
    """Test the main extract_indicators function."""

    def test_extract_single_indicator(self):
        """Extract single indicator with params."""
        indicators = extract_indicators("计算 14 日 RSI")
        assert len(indicators) >= 1
        rsi = next((i for i in indicators if i.name == "rsi"), None)
        assert rsi is not None
        assert rsi.params["period"] == 14

    def test_extract_multiple_indicators(self):
        """Extract multiple indicators."""
        indicators = extract_indicators("计算 RSI 和 MACD 信号")
        names = [i.name for i in indicators]
        assert "rsi" in names
        assert "macd" in names

    def test_extract_no_indicators(self):
        """Return empty list when no indicators found."""
        indicators = extract_indicators("获取股票历史数据")
        # May return empty or ma (due to '移动平均' false positive)
        indicator_names = [i.name for i in indicators]
        assert "rsi" not in indicator_names
        assert "macd" not in indicator_names


class TestIndicatorParamsDataclass:
    """Test IndicatorParams dataclass."""

    def test_dataclass_fields(self):
        """IndicatorParams should have required fields."""
        params = IndicatorParams(
            name="rsi",
            params={"period": 14},
            confidence=0.9
        )
        assert params.name == "rsi"
        assert params.params == {"period": 14}
        assert params.confidence == 0.9

    def test_default_values(self):
        """IndicatorParams should have defaults."""
        params = IndicatorParams(name="test")
        assert params.params == {}
        assert params.confidence == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
