## ADDED Requirements

### Requirement: Dedicated Schema Extraction Module
Schema and indicator extraction logic MUST be implemented in a dedicated `src/extraction/` module, not embedded in task_executor.

#### Scenario: Schema extraction is importable from dedicated module
- **WHEN** code imports `from src.extraction.schema import extract_schema`
- **THEN** the import succeeds and provides schema extraction functionality

#### Scenario: Indicator extraction is importable from dedicated module
- **WHEN** code imports `from src.extraction.indicators import extract_indicators`
- **THEN** the import succeeds and provides indicator parameter extraction functionality

### Requirement: Schema Extraction Accuracy Gate
Schema extraction MUST achieve ≥95% accuracy on the golden test set before merge.

#### Scenario: Golden test suite validates extraction
- **WHEN** `pytest tests/extraction/test_schema.py` runs against golden test cases
- **THEN** at least 95% of test cases pass

#### Scenario: CI blocks merge on accuracy regression
- **WHEN** schema extraction accuracy drops below 95%
- **THEN** the CI pipeline fails and blocks merge

### Requirement: Golden Test Set for Schema Extraction
A golden test set with ≥50 cases MUST exist for validating schema extraction.

#### Scenario: Golden test file exists with sufficient cases
- **WHEN** `tests/extraction/golden_schemas.json` is loaded
- **THEN** it contains at least 50 test cases with input/expected output pairs

#### Scenario: Golden tests cover edge cases
- **WHEN** the golden test set is reviewed
- **THEN** it includes: empty inputs, multi-field schemas, nested structures, Chinese text, special characters

### Requirement: Indicator Parameter Extraction
The extraction module MUST reliably extract technical indicator parameters from task descriptions.

#### Scenario: RSI parameter extraction
- **WHEN** task description is "Calculate 14-day RSI for AAPL"
- **THEN** extraction returns `{"indicator": "RSI", "period": 14, "symbol": "AAPL"}`

#### Scenario: MACD parameter extraction
- **WHEN** task description is "Calculate MACD (12, 26, 9) for MSFT"
- **THEN** extraction returns `{"indicator": "MACD", "fast": 12, "slow": 26, "signal": 9, "symbol": "MSFT"}`

#### Scenario: Bollinger parameter extraction
- **WHEN** task description is "Calculate 20-day Bollinger Bands with 2 std for GOOG"
- **THEN** extraction returns `{"indicator": "Bollinger", "period": 20, "std_dev": 2, "symbol": "GOOG"}`
