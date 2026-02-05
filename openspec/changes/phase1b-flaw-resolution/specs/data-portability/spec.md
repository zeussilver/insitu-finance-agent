## ADDED Requirements

### Requirement: Abstract Data Provider Interface
A Protocol-based interface MUST define the contract for financial data providers.

#### Scenario: DataProvider protocol is importable
- **WHEN** code imports `from src.data.interfaces import DataProvider`
- **THEN** the import succeeds and provides the Protocol definition

#### Scenario: DataProvider defines required methods
- **WHEN** the DataProvider protocol is inspected
- **THEN** it defines: `get_historical()`, `get_quote()`, `get_financial_info()`

### Requirement: yfinance Adapter Implementation
A concrete yfinance adapter MUST implement the DataProvider protocol for production use.

#### Scenario: YFinanceAdapter implements protocol
- **WHEN** `YFinanceAdapter` is instantiated
- **THEN** it satisfies the `DataProvider` protocol

#### Scenario: YFinanceAdapter preserves existing behavior
- **WHEN** `YFinanceAdapter.get_historical("AAPL", "2024-01-01", "2024-01-31")` is called
- **THEN** it returns the same data format as the current `data_proxy.py` implementation

### Requirement: Mock Adapter for Testing
A mock adapter MUST be available for deterministic testing without network calls.

#### Scenario: MockAdapter implements protocol
- **WHEN** `MockAdapter` is instantiated with canned responses
- **THEN** it satisfies the `DataProvider` protocol

#### Scenario: MockAdapter returns canned data
- **WHEN** `MockAdapter.get_historical("AAPL", ...)` is called
- **THEN** it returns predefined test data without network access

### Requirement: Adapter Injection Point
The system MUST support injecting different data adapters at runtime.

#### Scenario: Default adapter is yfinance
- **WHEN** no adapter is explicitly configured
- **THEN** the system uses `YFinanceAdapter` by default

#### Scenario: Test mode uses mock adapter
- **WHEN** `DATA_ADAPTER=mock` environment variable is set
- **THEN** the system uses `MockAdapter` instead of yfinance

#### Scenario: Tools work with any adapter
- **WHEN** a calculation tool requests data
- **THEN** it receives data through the injected adapter regardless of which adapter is active

### Requirement: Bootstrap Tools Use Adapter
Existing bootstrap tools in `data_proxy.py` MUST be refactored to use the adapter interface.

#### Scenario: get_stock_hist uses adapter
- **WHEN** `get_stock_hist()` is called
- **THEN** it delegates to `DataProvider.get_historical()` on the injected adapter

#### Scenario: get_financial_info uses adapter
- **WHEN** `get_financial_info()` is called
- **THEN** it delegates to `DataProvider.get_financial_info()` on the injected adapter
