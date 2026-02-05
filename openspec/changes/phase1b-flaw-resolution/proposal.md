## Why

The Yunjue Agent financial system has achieved 85% pass rate but contains 5 fatal architectural flaws that prevent production deployment: executor contamination from self-tests, verification gateway bypasses, broken schema extraction, inconsistent runtime constraints, and poor data layer portability. These flaws undermine the core "auditable + reproducible + secure" principles and must be resolved before the system can safely evolve tools in production.

## What Changes

- **BREAKING**: Remove self-test execution from executor's `__main__` block - tests will no longer auto-run during tool execution
- **BREAKING**: Enforce mandatory verification gateway for all refiner outputs - no bypass paths allowed
- Rewrite schema/indicator extraction pipeline with golden test coverage
- Consolidate runtime capability constraints into single source of truth
- Introduce abstract data layer interface with adapter pattern for portability
- Add evolution gates infrastructure with three-tier boundary model (auto/checkpoint/human-approval)
- Create benchmark integration with cold-start vs warm-start configuration matrix

## Capabilities

### New Capabilities

- `executor-isolation`: Separation of tool execution from self-test contamination, ensuring clean sandbox boundaries
- `verification-gateway`: Mandatory checkpoint enforcement for all tool mutations with rollback support
- `schema-extraction`: Reliable extraction of financial schemas and indicators with ≥95% accuracy on golden sets
- `runtime-constraints`: Centralized capability constraint definitions with single source of truth
- `data-portability`: Abstract data layer interface with pluggable adapters for different data sources
- `evolution-gates`: Three-tier boundary system (Level 1: auto-execute, Level 2: checkpoint, Level 3: human approval) for tool evolution control
- `benchmark-matrix`: Cold-start and warm-start benchmark configurations with PR merge gates

### Modified Capabilities

_(No existing specs to modify)_

## Impact

**Code Changes:**
- `src/core/executor.py` - Remove `__main__` self-test invocation, extract test harness
- `src/evolution/refiner.py` - Add mandatory gateway calls, remove bypass flags
- `src/evolution/synthesizer.py` - Integrate verification checkpoints
- `src/finance/data_proxy.py` - Implement abstract interface
- New files: `src/core/gates.py`, `src/data/interfaces.py`, `src/data/adapters/`

**APIs:**
- Executor API changes to remove implicit test execution
- New data adapter interface for financial data sources
- New evolution gate API for tier-based approval

**Dependencies:**
- No new external dependencies
- Internal module restructuring for cleaner separation of concerns

**Systems:**
- CI/CD pipeline updates for benchmark gates
- Pre-production deployment validation requirements
