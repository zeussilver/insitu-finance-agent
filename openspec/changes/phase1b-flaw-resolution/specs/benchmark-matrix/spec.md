## ADDED Requirements

### Requirement: YAML Configuration Matrix
Benchmark configurations MUST be defined in a YAML matrix configuration file.

#### Scenario: Matrix config file exists
- **WHEN** benchmarks are run
- **THEN** `benchmarks/config_matrix.yaml` is read for configuration

#### Scenario: Matrix defines named configurations
- **WHEN** the matrix config is parsed
- **THEN** it contains named configurations (at minimum: `cold_start`, `warm_start`)

### Requirement: Cold-Start Benchmark Configuration
The cold-start configuration MUST clear all state for baseline testing.

#### Scenario: Cold-start clears registry
- **WHEN** benchmark runs with `cold_start` configuration
- **THEN** the tool registry is cleared before test execution

#### Scenario: Cold-start clears cache
- **WHEN** benchmark runs with `cold_start` configuration
- **THEN** the data cache is cleared before test execution

#### Scenario: Cold-start measures fresh performance
- **WHEN** cold-start benchmark completes
- **THEN** results reflect performance without any accumulated state

### Requirement: Warm-Start Benchmark Configuration
The warm-start configuration MUST preserve state for operational validation.

#### Scenario: Warm-start preserves registry
- **WHEN** benchmark runs with `warm_start` configuration
- **THEN** the tool registry is NOT cleared before test execution

#### Scenario: Warm-start preserves cache
- **WHEN** benchmark runs with `warm_start` configuration
- **THEN** the data cache is NOT cleared before test execution

#### Scenario: Warm-start measures operational performance
- **WHEN** warm-start benchmark completes
- **THEN** results reflect performance with accumulated tool library

### Requirement: PR Merge Gates in Configuration
The configuration MUST define quality gates that block PR merges on regression.

#### Scenario: Accuracy regression gate is defined
- **WHEN** the matrix config is parsed
- **THEN** it contains `gates.pr_merge.accuracy_regression` threshold

#### Scenario: Accuracy regression blocks merge
- **WHEN** benchmark accuracy drops by more than the threshold (e.g., >2%)
- **THEN** the CI pipeline fails and blocks merge

### Requirement: run_eval.py Reads Matrix Configuration
The benchmark runner MUST read and apply matrix configurations.

#### Scenario: Run with named configuration
- **WHEN** `python benchmarks/run_eval.py --config cold_start` is executed
- **THEN** the `cold_start` configuration from the matrix is applied

#### Scenario: Default configuration is cold_start
- **WHEN** `python benchmarks/run_eval.py` is executed without `--config`
- **THEN** the `cold_start` configuration is used as default

### Requirement: Benchmark Results Include Configuration Metadata
Benchmark results MUST record which configuration was used.

#### Scenario: Results include config name
- **WHEN** benchmark results are saved
- **THEN** the JSON includes `"config": "cold_start"` or similar metadata

#### Scenario: Results are comparable by config
- **WHEN** comparing two benchmark runs
- **THEN** configuration differences are highlighted if configs don't match
