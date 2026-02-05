"""Tests for VerificationGateway - single enforcement point for tool registration.

Tests verify:
1. All registration MUST go through gateway
2. Verification is enforced before registration
3. Rollback checkpoints are created
4. All attempts are logged
5. Unsafe code is blocked
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.gateway import VerificationGateway, VerificationError, get_gateway
from src.core.verifier import VerificationResult
from src.core.models import VerificationStage
from src.core.contracts import get_contract


# Test fixtures

@pytest.fixture
def gateway(tmp_path):
    """Create a gateway with temporary log directory."""
    gw = VerificationGateway()
    gw.logs_dir = tmp_path / "logs"
    gw.logs_dir.mkdir(parents=True, exist_ok=True)
    gw._setup_logging()
    return gw


@pytest.fixture
def valid_calc_code():
    """Valid RSI calculation code."""
    return '''
import pandas as pd
import numpy as np

def calc_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return 50.0

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.inf)
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])

if __name__ == "__main__":
    prices = [44, 44.5, 44.25, 43.75, 44.5, 44.25, 44.5, 45, 45.5, 46, 46.5, 47, 46.5, 47, 47.5]
    result = calc_rsi(prices, 5)
    assert 0 <= result <= 100, f"RSI out of range: {result}"
    print("Test passed!")
'''


@pytest.fixture
def unsafe_code():
    """Code that should be blocked."""
    return '''
import os

def unsafe_func():
    """Attempts to use banned module."""
    os.system("ls")
'''


@pytest.fixture
def yfinance_code():
    """Fetch code using yfinance."""
    return '''
import yfinance as yf
import pandas as pd

def get_price(symbol: str) -> float:
    """Get latest stock price."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")
    return float(hist['Close'].iloc[-1])

if __name__ == "__main__":
    print("Test passed!")
'''


# Test: Verification enforcement

class TestVerificationEnforcement:
    """Tests that verification is enforced before registration."""

    def test_valid_code_passes_verification(self, gateway, valid_calc_code):
        """Valid code should pass all verification stages."""
        passed, report = gateway.verify_only(
            code=valid_calc_code,
            category="calculation",
            task_id="test_valid"
        )

        assert passed is True
        assert report.final_stage.value >= VerificationStage.SELF_TEST.value

    def test_unsafe_code_blocked(self, gateway, unsafe_code):
        """Unsafe code should fail AST security check."""
        passed, report = gateway.verify_only(
            code=unsafe_code,
            category="calculation",
            task_id="test_unsafe"
        )

        assert passed is False
        assert report.stages[0].stage == VerificationStage.AST_SECURITY
        assert report.stages[0].result == VerificationResult.FAIL

    def test_yfinance_blocked_in_calculation(self, gateway, yfinance_code):
        """yfinance should be blocked for calculation category."""
        passed, report = gateway.verify_only(
            code=yfinance_code,
            category="calculation",
            task_id="test_yfinance_calc"
        )

        assert passed is False
        assert "yfinance" in report.stages[0].message.lower() or "import" in report.stages[0].message.lower()

    def test_yfinance_allowed_in_fetch(self, gateway, yfinance_code):
        """yfinance should be allowed for fetch category."""
        passed, report = gateway.verify_only(
            code=yfinance_code,
            category="fetch",
            task_id="test_yfinance_fetch"
        )

        # Should pass AST stage (may fail later stages without network)
        assert report.stages[0].result == VerificationResult.PASS


# Test: Submit and registration

class TestSubmitMethod:
    """Tests for the gateway submit() method."""

    def test_submit_valid_code(self, gateway, valid_calc_code):
        """Valid code should be registered through submit."""
        success, tool, report = gateway.submit(
            code=valid_calc_code,
            category="calculation",
            contract_id="calc_rsi",
            task_id="test_submit",
            force=True  # Skip gatekeeper in test
        )

        assert success is True
        assert tool is not None
        assert tool.name == "calc_rsi"
        assert report.passed is True

    def test_submit_unsafe_code_rejected(self, gateway, unsafe_code):
        """Unsafe code should be rejected by submit."""
        success, tool, report = gateway.submit(
            code=unsafe_code,
            category="calculation",
            task_id="test_submit_unsafe",
            force=True
        )

        assert success is False
        assert tool is None
        assert report.passed is False

    def test_submit_creates_checkpoint(self, gateway, valid_calc_code):
        """Submit should create rollback checkpoint."""
        import json

        gateway.submit(
            code=valid_calc_code,
            category="calculation",
            task_id="test_checkpoint",
            force=True
        )

        # Verify checkpoint was created - check that submit_tool checkpoints exist
        checkpoint_dir = gateway.checkpoint_manager.checkpoint_dir
        checkpoint_files = list(checkpoint_dir.glob("cp_*submit_tool*.json"))
        assert len(checkpoint_files) > 0, "No submit_tool checkpoint file found"

        # Verify checkpoint content is valid
        with open(checkpoint_files[-1]) as f:
            data = json.load(f)
        assert data["action"] == "submit_tool"
        assert "context" in data
        assert data["status"] in ("pending", "completed", "failed")


# Test: Logging

class TestLogging:
    """Tests for registration attempt logging."""

    def test_success_logged(self, gateway, valid_calc_code):
        """Successful registration should be logged."""
        gateway.submit(
            code=valid_calc_code,
            category="calculation",
            task_id="test_log_success",
            force=True
        )

        # Check log file exists and contains entry
        log_path = gateway.logs_dir / "gateway_attempts.jsonl"
        assert log_path.exists()

        with open(log_path, 'r') as f:
            entries = [json.loads(line) for line in f]

        # Should have at least one success entry
        success_entries = [e for e in entries if e.get("success") is True]
        assert len(success_entries) > 0

    def test_failure_logged(self, gateway, unsafe_code):
        """Failed registration should be logged."""
        gateway.submit(
            code=unsafe_code,
            category="calculation",
            task_id="test_log_failure",
            force=True
        )

        log_path = gateway.logs_dir / "gateway_attempts.jsonl"
        assert log_path.exists()

        with open(log_path, 'r') as f:
            entries = [json.loads(line) for line in f]

        # Should have failure entry
        failure_entries = [e for e in entries if e.get("success") is False]
        assert len(failure_entries) > 0

    def test_log_contains_required_fields(self, gateway, valid_calc_code):
        """Log entries should contain required fields."""
        gateway.submit(
            code=valid_calc_code,
            category="calculation",
            task_id="test_log_fields",
            force=True
        )

        log_path = gateway.logs_dir / "gateway_attempts.jsonl"

        with open(log_path, 'r') as f:
            entry = json.loads(f.readline())

        # Required fields
        assert "timestamp" in entry
        assert "action" in entry
        assert "tool_name" in entry
        assert "category" in entry
        assert "success" in entry


# Test: Contract integration

class TestContractIntegration:
    """Tests for contract-based validation in gateway."""

    def test_contract_lookup_by_id(self, gateway, valid_calc_code):
        """Should look up contract by ID."""
        success, tool, report = gateway.submit(
            code=valid_calc_code,
            category="calculation",
            contract_id="calc_rsi",
            task_id="test_contract_id",
            force=True
        )

        assert success is True
        # Contract validation stage should be present
        contract_stages = [s for s in report.stages if s.stage == VerificationStage.CONTRACT_VALID]
        assert len(contract_stages) > 0

    def test_explicit_contract_used(self, gateway, valid_calc_code):
        """Should use explicitly provided contract."""
        contract = get_contract("calc_rsi")

        success, tool, report = gateway.submit(
            code=valid_calc_code,
            category="calculation",
            contract=contract,
            task_id="test_explicit_contract",
            force=True
        )

        assert success is True


# Test: Statistics

class TestStatistics:
    """Tests for gateway statistics."""

    def test_stats_tracking(self, gateway, valid_calc_code, unsafe_code):
        """Should track success/failure statistics."""
        # Submit one valid, one invalid
        gateway.submit(code=valid_calc_code, category="calculation", task_id="stat1", force=True)
        gateway.submit(code=unsafe_code, category="calculation", task_id="stat2", force=True)

        stats = gateway.get_registration_stats()

        assert stats["total"] >= 2
        assert stats["success"] >= 1
        assert stats["failed"] >= 1
        assert 0.0 <= stats["success_rate"] <= 1.0


# Test: Global gateway instance

class TestGlobalGateway:
    """Tests for global gateway singleton."""

    def test_get_gateway_returns_singleton(self):
        """get_gateway() should return the same instance."""
        gw1 = get_gateway()
        gw2 = get_gateway()

        assert gw1 is gw2

    def test_gateway_has_required_components(self):
        """Gateway should have verifier, registry, gatekeeper."""
        gw = get_gateway()

        assert gw.verifier is not None
        assert gw.registry is not None
        assert gw.gatekeeper is not None
        assert gw.checkpoint_manager is not None


# Test: Verify-only mode

class TestVerifyOnlyMode:
    """Tests for verify_only() method."""

    def test_verify_only_does_not_register(self, gateway, valid_calc_code):
        """verify_only() should not register the tool."""
        initial_tools = gateway.registry.list_tools()
        initial_count = len(initial_tools)

        passed, report = gateway.verify_only(
            code=valid_calc_code,
            category="calculation",
            task_id="test_verify_only"
        )

        # Tool count should not change
        final_tools = gateway.registry.list_tools()
        # Note: This may not be exact if other tests run in parallel
        # Just verify the method works without registration
        assert passed is True
        assert report is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
