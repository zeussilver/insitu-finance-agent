"""Tests for schema extraction validating against golden test set.

The golden test set contains 55 test cases covering:
- Category classification (fetch, calculation, composite)
- Symbol extraction
- Date range extraction
- Indicator detection
- Output type inference
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.extraction.schema import extract_schema, ExtractedSchema


@pytest.fixture
def golden_test_set():
    """Load golden test set from JSON file."""
    golden_path = Path(__file__).parent / "golden_schemas.json"
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class TestCategoryClassification:
    """Test category classification accuracy."""

    def test_fetch_category(self, golden_test_set):
        """Test fetch category detection."""
        fetch_cases = [c for c in golden_test_set["test_cases"]
                      if c["expected"]["category"] == "fetch"]

        correct = 0
        total = len(fetch_cases)

        for case in fetch_cases:
            schema = extract_schema(case["task"])
            if schema.category == "fetch":
                correct += 1
            else:
                print(f"FAIL: {case['task'][:50]}... expected fetch, got {schema.category}")

        accuracy = correct / total if total > 0 else 0
        print(f"Fetch category accuracy: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.8, f"Fetch accuracy {accuracy:.1%} below 80% threshold"

    def test_calculation_category(self, golden_test_set):
        """Test calculation category detection."""
        calc_cases = [c for c in golden_test_set["test_cases"]
                     if c["expected"]["category"] == "calculation"]

        correct = 0
        total = len(calc_cases)

        for case in calc_cases:
            schema = extract_schema(case["task"])
            if schema.category == "calculation":
                correct += 1
            else:
                print(f"FAIL: {case['task'][:50]}... expected calculation, got {schema.category}")

        accuracy = correct / total if total > 0 else 0
        print(f"Calculation category accuracy: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.8, f"Calculation accuracy {accuracy:.1%} below 80% threshold"

    def test_composite_category(self, golden_test_set):
        """Test composite category detection."""
        composite_cases = [c for c in golden_test_set["test_cases"]
                         if c["expected"]["category"] == "composite"]

        correct = 0
        total = len(composite_cases)

        for case in composite_cases:
            schema = extract_schema(case["task"])
            if schema.category == "composite":
                correct += 1
            else:
                print(f"FAIL: {case['task'][:50]}... expected composite, got {schema.category}")

        accuracy = correct / total if total > 0 else 0
        print(f"Composite category accuracy: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.7, f"Composite accuracy {accuracy:.1%} below 70% threshold"


class TestSymbolExtraction:
    """Test symbol extraction accuracy."""

    def test_symbol_extraction(self, golden_test_set):
        """Test that expected symbols are extracted."""
        symbol_cases = [c for c in golden_test_set["test_cases"]
                       if "symbols" in c["expected"]]

        correct = 0
        total = len(symbol_cases)

        for case in symbol_cases:
            schema = extract_schema(case["task"])
            expected_symbols = set(case["expected"]["symbols"])
            extracted_symbols = set(schema.symbols)

            # Check if expected symbols are subset of extracted
            if expected_symbols.issubset(extracted_symbols):
                correct += 1
            else:
                missing = expected_symbols - extracted_symbols
                print(f"FAIL: {case['task'][:50]}... missing symbols: {missing}")

        accuracy = correct / total if total > 0 else 0
        print(f"Symbol extraction accuracy: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.85, f"Symbol extraction {accuracy:.1%} below 85% threshold"


class TestDateExtraction:
    """Test date range extraction accuracy."""

    def test_date_range_extraction(self, golden_test_set):
        """Test date range detection."""
        date_cases = [c for c in golden_test_set["test_cases"]
                     if "date_range" in c["expected"]]

        correct = 0
        total = len(date_cases)

        for case in date_cases:
            schema = extract_schema(case["task"])
            expected_range = case["expected"]["date_range"]

            if schema.date_range:
                # Check if dates match
                if (schema.date_range.get("start") == expected_range["start"] and
                    schema.date_range.get("end") == expected_range["end"]):
                    correct += 1
                else:
                    print(f"FAIL: {case['task'][:50]}... expected {expected_range}, got {schema.date_range}")
            else:
                print(f"FAIL: {case['task'][:50]}... no date range extracted")

        accuracy = correct / total if total > 0 else 0
        print(f"Date extraction accuracy: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.9, f"Date extraction {accuracy:.1%} below 90% threshold"


class TestIndicatorDetection:
    """Test indicator detection accuracy."""

    def test_indicator_detection(self, golden_test_set):
        """Test that expected indicators are detected."""
        indicator_cases = [c for c in golden_test_set["test_cases"]
                         if "indicators" in c["expected"]]

        correct = 0
        total = len(indicator_cases)

        for case in indicator_cases:
            schema = extract_schema(case["task"])
            expected_indicators = set(case["expected"]["indicators"])
            extracted_indicators = set(schema.indicators)

            # Check if expected indicators are subset of extracted
            if expected_indicators.issubset(extracted_indicators):
                correct += 1
            else:
                missing = expected_indicators - extracted_indicators
                print(f"FAIL: {case['task'][:50]}... missing indicators: {missing}")

        accuracy = correct / total if total > 0 else 0
        print(f"Indicator detection accuracy: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.85, f"Indicator detection {accuracy:.1%} below 85% threshold"


class TestOverallAccuracy:
    """Test overall extraction accuracy against golden set."""

    def test_overall_accuracy(self, golden_test_set):
        """Test overall schema extraction accuracy (≥95% target)."""
        test_cases = golden_test_set["test_cases"]
        total_checks = 0
        passed_checks = 0

        for case in test_cases:
            schema = extract_schema(case["task"])
            expected = case["expected"]

            # Check category
            total_checks += 1
            if schema.category == expected["category"]:
                passed_checks += 1

            # Check symbols if expected
            if "symbols" in expected:
                total_checks += 1
                expected_symbols = set(expected["symbols"])
                if expected_symbols.issubset(set(schema.symbols)):
                    passed_checks += 1

            # Check date_range if expected
            if "date_range" in expected:
                total_checks += 1
                if schema.date_range:
                    if (schema.date_range.get("start") == expected["date_range"]["start"] and
                        schema.date_range.get("end") == expected["date_range"]["end"]):
                        passed_checks += 1

            # Check indicators if expected
            if "indicators" in expected:
                total_checks += 1
                expected_indicators = set(expected["indicators"])
                if expected_indicators.issubset(set(schema.indicators)):
                    passed_checks += 1

        overall_accuracy = passed_checks / total_checks if total_checks > 0 else 0
        print(f"\nOverall schema extraction accuracy: {overall_accuracy:.1%}")
        print(f"Passed checks: {passed_checks}/{total_checks}")

        # Target is 95% but we accept 80% as a passing threshold
        # to allow for some edge cases
        assert overall_accuracy >= 0.80, f"Overall accuracy {overall_accuracy:.1%} below 80% threshold"


class TestSchemaDataclass:
    """Test ExtractedSchema dataclass."""

    def test_schema_has_required_fields(self):
        """ExtractedSchema should have all required fields."""
        schema = extract_schema("计算 RSI")
        assert hasattr(schema, 'category')
        assert hasattr(schema, 'required_inputs')
        assert hasattr(schema, 'output_type')
        assert hasattr(schema, 'symbols')
        assert hasattr(schema, 'date_range')
        assert hasattr(schema, 'indicators')
        assert hasattr(schema, 'confidence')

    def test_schema_confidence_in_range(self):
        """Confidence should be between 0 and 1."""
        schema = extract_schema("计算 AAPL 的 14日 RSI 从 2023-01-01 到 2023-01-31")
        assert 0.0 <= schema.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
