## ADDED Requirements

### Requirement: Executor __main__ Block is Test-Free
The executor module (`src/core/executor.py`) SHALL NOT contain any self-test invocations in its `__main__` block. All test logic MUST be extracted to dedicated test modules under `tests/`.

#### Scenario: Executor module import has no side effects
- **WHEN** the executor module is imported
- **THEN** no test code is executed and no output is produced

#### Scenario: Executor __main__ provides CLI or is empty
- **WHEN** `python src/core/executor.py` is run directly
- **THEN** no self-tests execute (either empty block or CLI-only entrypoint)

### Requirement: Test Extraction to pytest Modules
All executor self-tests MUST be moved to `tests/core/test_executor.py` and run via pytest.

#### Scenario: Extracted tests are discoverable by pytest
- **WHEN** `pytest tests/core/test_executor.py` is executed
- **THEN** all previously-inlined executor tests run and pass

#### Scenario: Tests cover safe code execution
- **WHEN** a safe code snippet is submitted for execution
- **THEN** the test verifies successful execution without security violations

#### Scenario: Tests cover dangerous code blocking
- **WHEN** a dangerous code snippet (using banned modules/calls) is submitted
- **THEN** the test verifies the code is blocked with appropriate error

### Requirement: Verify-Only Mode Remains Available
The executor MUST retain `verify_only` execution mode for tool self-validation, which is distinct from module-level tests.

#### Scenario: Verify-only mode validates without full execution
- **WHEN** `ToolExecutor.execute(code, verify_only=True)` is called
- **THEN** static analysis runs but subprocess execution is skipped

#### Scenario: Verify-only returns validation result
- **WHEN** verify-only mode completes
- **THEN** a structured result indicates whether the code passed static checks
