## 1. Infrastructure Setup (Non-Breaking)

- [x] 1.1 Create `configs/constraints.yaml` with execution limits and capability rules
- [x] 1.2 Create `src/core/constraints.py` dataclass wrapper with YAML loading and validation
- [x] 1.3 Create `src/data/interfaces.py` with DataProvider Protocol definition
- [x] 1.4 Create `src/data/adapters/` directory structure
- [x] 1.5 Create `src/data/adapters/yfinance_adapter.py` implementing DataProvider
- [x] 1.6 Create `src/data/adapters/mock_adapter.py` implementing DataProvider
- [x] 1.7 Create `src/core/gates.py` with EvolutionGate enum and EvolutionGatekeeper class
- [x] 1.8 Create `src/extraction/` module directory structure
- [x] 1.9 Create `src/extraction/schema.py` with extract_schema function
- [x] 1.10 Create `src/extraction/indicators.py` with extract_indicators function

## 2. Test Infrastructure

- [x] 2.1 Create `tests/core/test_executor.py` with tests extracted from executor.__main__
- [x] 2.2 Create `tests/evolution/test_refiner.py` with tests extracted from refiner.__main__
- [x] 2.3 Create `tests/extraction/golden_schemas.json` with 50+ golden test cases
- [x] 2.4 Create `tests/extraction/test_schema.py` validating against golden test set
- [x] 2.5 Create `tests/extraction/test_indicators.py` for indicator parameter extraction
- [x] 2.6 Create `tests/data/test_adapters.py` verifying adapter implementations

## 3. Verification Gateway

- [x] 3.1 Create `src/core/gateway.py` with VerificationGateway class
- [x] 3.2 Implement `VerificationGateway.submit()` method with verification enforcement
- [x] 3.3 Add rollback checkpoint creation in gateway
- [x] 3.4 Add logging for all registration attempts (success/failure)
- [x] 3.5 Create `tests/core/test_gateway.py` with gateway verification tests

## 4. Module Migration (Gradual Enforcement)

- [x] 4.1 Update `src/core/executor.py` to import constraints from centralized module
- [x] 4.2 Update `src/core/verifier.py` to import constraints from centralized module
- [x] 4.3 Update `src/core/capabilities.py` to import constraints from centralized module
- [x] 4.4 Remove duplicate constraint definitions from executor, verifier, capabilities
- [x] 4.5 Update `src/finance/data_proxy.py` to use DataProvider adapter
- [x] 4.6 Update `src/finance/bootstrap.py` to use DataProvider adapter

## 5. Evolution Integration

- [x] 5.1 Modify `src/evolution/synthesizer.py` to use VerificationGateway exclusively
- [x] 5.2 Modify `src/evolution/refiner.py` to use VerificationGateway exclusively
- [x] 5.3 Remove direct `registry.register()` calls from evolution modules
- [x] 5.4 Integrate EvolutionGatekeeper into synthesizer flow
- [x] 5.5 Integrate EvolutionGatekeeper into refiner flow

## 6. Executor Cleanup (Test Isolation)

- [x] 6.1 Remove self-test invocation from `src/core/executor.py` __main__ block
- [x] 6.2 Remove self-test invocation from `src/finance/data_proxy.py` __main__ block
- [x] 6.3 Verify `verify_only` mode still functions correctly
- [x] 6.4 Run pytest to confirm extracted tests pass

## 7. Benchmark Matrix

- [x] 7.1 Create `benchmarks/config_matrix.yaml` with cold_start and warm_start configurations
- [x] 7.2 Update `benchmarks/run_eval.py` to read matrix configuration
- [x] 7.3 Add `--config` CLI argument to run_eval.py
- [x] 7.4 Add configuration metadata to benchmark result output
- [x] 7.5 Define PR merge gates (accuracy_regression threshold) in config

## 8. Validation & Cleanup

- [x] 8.1 Run full benchmark suite with cold_start configuration
- [x] 8.2 Verify 85% pass rate is maintained (no regression)
- [x] 8.3 Verify schema extraction achieves ≥95% accuracy on golden set
- [x] 8.4 Remove any legacy code paths and feature flags
- [x] 8.5 Update CLAUDE.md with new architecture documentation
