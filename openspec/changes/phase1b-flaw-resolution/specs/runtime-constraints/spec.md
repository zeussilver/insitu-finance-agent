## ADDED Requirements

### Requirement: Single Source of Truth for Constraints
All runtime capability constraints MUST be defined in a single YAML configuration file with Python dataclass wrapper.

#### Scenario: Constraints file exists
- **WHEN** the system starts
- **THEN** `configs/constraints.yaml` is loaded as the authoritative constraint source

#### Scenario: No duplicate constraint definitions
- **WHEN** searching codebase for module allowlists/blocklists
- **THEN** only `configs/constraints.yaml` and its Python wrapper contain these definitions

### Requirement: YAML Configuration Structure
The constraints YAML MUST define execution limits and per-category capability rules.

#### Scenario: Execution constraints are defined
- **WHEN** `configs/constraints.yaml` is parsed
- **THEN** it contains `execution.timeout_sec` and `execution.memory_mb` values

#### Scenario: Category capability rules are defined
- **WHEN** `configs/constraints.yaml` is parsed
- **THEN** it contains `capabilities.<category>.allowed_modules` and `capabilities.<category>.banned_modules` for each tool category

### Requirement: Typed Python Wrapper for Constraints
A Python module MUST provide typed access to YAML constraints.

#### Scenario: Constraints importable as dataclass
- **WHEN** code imports `from src.core.constraints import Constraints`
- **THEN** the import succeeds and provides typed constraint access

#### Scenario: Constraint values are validated at load time
- **WHEN** constraints YAML has invalid values (negative timeout, missing required fields)
- **THEN** the system fails fast with descriptive error at startup

### Requirement: All Modules Use Centralized Constraints
Executor, verifier, and capabilities modules MUST import constraints from the central module.

#### Scenario: Executor uses centralized constraints
- **WHEN** `src/core/executor.py` needs module allowlist
- **THEN** it imports from `src.core.constraints` not inline definitions

#### Scenario: Verifier uses centralized constraints
- **WHEN** `src/core/verifier.py` needs capability rules
- **THEN** it imports from `src.core.constraints` not inline definitions

#### Scenario: Capabilities module uses centralized constraints
- **WHEN** `src/core/capabilities.py` needs module mappings
- **THEN** it imports from `src.core.constraints` not inline definitions
