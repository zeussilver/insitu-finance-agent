## Context

The Yunjue Agent financial system currently achieves 85% pass rate (17/20 benchmarks) but has architectural flaws that prevent production deployment. The system follows "Metadata in DB, Payload on Disk" pattern with capability-based verification.

**Current State:**
- `src/core/executor.py` contains self-tests in `__main__` block that pollute execution
- `src/evolution/refiner.py` can bypass verification via direct tool registration
- Schema extraction embedded in task_executor without golden test coverage
- Runtime constraints scattered across multiple files (executor, verifier, capabilities)
- Data layer tightly coupled to yfinance via `DataProvider` class
- No evolution gates - all tool mutations auto-execute

**Stakeholders:**
- Financial analysts using evolved tools for market analysis
- DevOps engineers managing production deployment
- Security team auditing tool evolution

## Goals / Non-Goals

**Goals:**
- Eliminate all 5 fatal flaws blocking production deployment
- Maintain backward compatibility with existing 85% pass rate
- Enable auditable tool evolution with human-in-the-loop for high-risk changes
- Support cold-start and warm-start benchmark configurations
- Single source of truth for all capability constraints

**Non-Goals:**
- Changing the "Metadata in DB, Payload on Disk" architecture pattern
- Migrating away from SQLModel/SQLite
- Adding new financial data sources (beyond yfinance abstraction)
- Implementing distributed execution or multi-agent coordination
- UI/dashboard for evolution monitoring (CLI-only scope)

## Decisions

### D1: Test Isolation Architecture

**Decision:** Extract all self-tests from `__main__` blocks into dedicated test modules under `tests/`.

**Alternatives Considered:**
- A) Keep tests in `__main__` but add execution flag → Rejected: Still pollutes tool code
- B) Move tests to `if __name__ == "__main__"` with `--test` CLI flag → Rejected: Complicates execution
- C) **Extract to `tests/` directory with pytest** → Selected: Clean separation, standard practice

**Rationale:** Following Yunjue paradigm's four-role separation (Manager → Tool Developer → Executor → Integrator). The executor role must be isolated from test execution concerns.

**Implementation:**
- New `tests/core/test_executor.py` for executor tests
- New `tests/evolution/test_refiner.py` for refiner tests
- Remove `if __name__ == "__main__"` test blocks from source files
- Retain `verify_only` execution mode for tool self-validation (distinct from module tests)

### D2: Verification Gateway Enforcement

**Decision:** Add mandatory `VerificationGateway` class that wraps all tool registration paths.

**Alternatives Considered:**
- A) Add validation in `ToolRegistry.register()` → Rejected: Can be bypassed by direct DB access
- B) **Create gateway that decorates/wraps registration** → Selected: Single enforcement point
- C) Database trigger for validation → Rejected: Harder to debug, less portable

**Rationale:** Yunjue principle: "every mutation requires a checkpoint with rollback always possible."

**Implementation:**
```python
class VerificationGateway:
    def __init__(self, verifier: MultiStageVerifier, registry: ToolRegistry):
        self.verifier = verifier
        self.registry = registry

    def submit(self, code: str, category: str, contract: ToolContract) -> Tuple[bool, ToolArtifact]:
        """All tool registration MUST go through this method."""
        passed, report = self.verifier.verify_all_stages(code, category, contract=contract)
        if not passed:
            raise VerificationError(report)
        return self.registry.register(...)
```

- Modify `synthesizer.py` to use gateway exclusively
- Modify `refiner.py` to use gateway exclusively
- Remove direct `registry.register()` calls from evolution modules

### D3: Schema Extraction Pipeline

**Decision:** Create dedicated `src/extraction/` module with golden test suite.

**Alternatives Considered:**
- A) Inline extraction logic in task_executor → Rejected: Current state, lacks testability
- B) **Dedicated extraction module with 95%+ accuracy gate** → Selected: Testable, measurable
- C) LLM-based extraction only → Rejected: Non-deterministic, expensive

**Rationale:** Schema extraction failures cause downstream task failures. Need deterministic, tested extraction.

**Implementation:**
- `src/extraction/schema.py` - Schema extraction from task descriptions
- `src/extraction/indicators.py` - Technical indicator parameter extraction
- `tests/extraction/golden_schemas.json` - 50+ golden test cases
- Gate: Must pass 95% of golden tests before merge

### D4: Centralized Runtime Constraints

**Decision:** Single `src/core/constraints.py` module with YAML configuration.

**Alternatives Considered:**
- A) Keep constraints scattered → Rejected: Current pain point
- B) Environment variables only → Rejected: Not structured enough
- C) **YAML config + Python dataclass** → Selected: Readable, typed, centralized

**Implementation:**
```yaml
# configs/constraints.yaml
execution:
  timeout_sec: 30
  memory_mb: 512

capabilities:
  calculation:
    allowed_modules: [pandas, numpy, datetime, json, math, decimal, collections, re, typing]
    banned_modules: [yfinance, os, sys, subprocess]
  fetch:
    allowed_modules: [pandas, numpy, datetime, json, math, yfinance, hashlib, pathlib]
    banned_modules: [os, sys, subprocess]

verification:
  max_retries: 3
  retry_delay_sec: 1.0
```

- All modules import constraints from `src/core/constraints.py`
- Remove duplicate constraint definitions from executor, verifier, capabilities

### D5: Data Layer Abstraction

**Decision:** Abstract interface pattern with pluggable adapters.

**Alternatives Considered:**
- A) Keep yfinance coupling → Rejected: Blocks testing/portability
- B) Dependency injection framework → Rejected: Over-engineering
- C) **Protocol/ABC interface with adapters** → Selected: Simple, testable

**Implementation:**
```python
# src/data/interfaces.py
from typing import Protocol
import pandas as pd

class DataProvider(Protocol):
    def get_historical(self, symbol: str, start: str, end: str) -> pd.DataFrame: ...
    def get_quote(self, symbol: str) -> dict: ...
    def get_financial_info(self, symbol: str) -> pd.DataFrame: ...

# src/data/adapters/yfinance_adapter.py
class YFinanceAdapter(DataProvider):
    """Production adapter using yfinance."""
    ...

# src/data/adapters/mock_adapter.py
class MockAdapter(DataProvider):
    """Test adapter with canned responses."""
    ...
```

- Existing tools continue to work via default yfinance adapter
- Tests can inject mock adapter for deterministic behavior
- Future: Add other data sources (Alpha Vantage, Bloomberg) via new adapters

### D6: Three-Tier Evolution Gates

**Decision:** Implement boundary-based approval system for tool mutations.

**Alternatives Considered:**
- A) All changes auto-execute → Rejected: Current state, unsafe for production
- B) All changes require human approval → Rejected: Too slow for development
- C) **Three-tier model based on risk** → Selected: Balances safety and velocity

**Implementation:**
```python
# src/core/gates.py
class EvolutionGate(Enum):
    AUTO = 1      # Level 1: Execute immediately
    CHECKPOINT = 2  # Level 2: Log + rollback point
    APPROVAL = 3    # Level 3: Require human approval

class EvolutionGatekeeper:
    def classify(self, action: str, context: dict) -> EvolutionGate:
        """Classify action into gate tier."""
        ...

    def request_approval(self, action: str, context: dict) -> bool:
        """Block until human approval (or timeout)."""
        ...
```

**Gate Classification:**
| Action | Gate Level |
|--------|------------|
| Read cached data | AUTO |
| Execute read-only calculation | AUTO |
| Create new tool (fetch category) | CHECKPOINT |
| Modify existing tool | CHECKPOINT |
| Persist tool to library | APPROVAL |
| Modify verification rules | APPROVAL |

### D7: Benchmark Matrix Architecture

**Decision:** YAML-based configuration matrix for cold/warm start benchmarks.

**Implementation:**
```yaml
# benchmarks/config_matrix.yaml
benchmark_matrix:
  cold_start:
    clear_registry: true
    clear_cache: true
    description: "Fresh initialization, no cached state"

  warm_start:
    clear_registry: false
    clear_cache: false
    description: "Use accumulated tool library"

  gates:
    pr_merge:
      accuracy_regression: -0.02  # Block if >2% regression
      gateway_coverage: 1.00
```

- `benchmarks/run_eval.py` reads matrix configuration
- CI/CD uses cold_start for regression testing
- Convergence tracking via tool creation rate metric

## Risks / Trade-offs

**R1: Test Extraction May Break Existing Workflows**
→ Mitigation: Phase rollout - keep old tests during transition, remove after green CI

**R2: Verification Gateway Adds Latency**
→ Mitigation: Gateway is lightweight (<10ms overhead); verification stages already exist

**R3: Schema Extraction Golden Set Maintenance**
→ Mitigation: Add new golden cases as edge cases discovered; automate validation

**R4: YAML Config Drift from Code**
→ Mitigation: Startup validation that config matches code expectations

**R5: Evolution Gates Block Development Velocity**
→ Mitigation: Development mode with relaxed gates; production mode enforces strictly

**R6: Data Abstraction Hides yfinance Behaviors**
→ Mitigation: Adapter tests verify yfinance-specific behaviors are preserved

## Migration Plan

### Phase 1: Non-Breaking Infrastructure (PRs 1-3)
1. Add new files without modifying existing code paths
2. Create test infrastructure alongside existing tests
3. Implement gateway without enforcing

### Phase 2: Gradual Enforcement (PRs 4-5)
1. Route new registrations through gateway
2. Migrate constraints to YAML
3. Add data abstraction layer

### Phase 3: Full Enforcement (PRs 6-7)
1. Enable gate enforcement
2. Remove legacy code paths
3. Benchmark validation

### Rollback Strategy
- Each PR is independently revertable
- Feature flags for gateway enforcement: `ENFORCE_GATEWAY=true/false`
- Benchmark baseline captured before each PR merge

## Open Questions

1. **Q: Should evolution gates integrate with external approval systems (Slack, email)?**
   - Current decision: CLI-only for Phase 1b; external integration deferred

2. **Q: How to handle tool evolution during offline/disconnected mode?**
   - Current decision: Queue APPROVAL-tier actions; process on reconnect

3. **Q: Should warm-start benchmarks include time-based cache invalidation?**
   - Current decision: No TTL for Phase 1b; all cached tools persist
