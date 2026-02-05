# OpenSpec and Spec-Driven Development for Agent System Improvement Plans

The most effective approach for your Phase 1b improvement plan combines the **OpenSpec methodology** (a concrete framework by Fission-AI) with the **Yunjue Agent's In-Situ Self-Evolving paradigm** and industry-standard **benchmark-driven development patterns**. This synthesis provides a structure where each PR addresses specific fatal flaws with verifiable gates, while the specification evolves dynamically as implementation progresses.

## OpenSpec provides the structural foundation for PR-by-PR iteration

**OpenSpec** is not merely a methodology concept—it's a specific, well-supported framework (9k+ GitHub stars, MIT license) designed for modifying existing codebases through spec-driven development. Its core innovation is a **two-folder model** that physically separates current truth from proposed changes:

```
openspec/
├── specs/           # Source of truth (current state)
│   └── financial_agent/
│       └── spec.md
└── changes/         # Proposed updates per PR
    └── phase1b-flaw-1/
        ├── proposal.md    # Why and what changes
        ├── tasks.md       # Implementation checklist (maps to PR)
        ├── design.md      # Technical decisions
        └── specs/
            └── financial_agent/
                └── spec.md   # Delta showing additions/modifications
```

The **four-phase workflow** enforces an irreversible lifecycle: Proposal → Review/Align → Apply → Archive. Each change captures a "spec delta" that shows exactly how requirements evolve, creating an auditable trail. For your **7 ordered PRs**, each maps to a separate `changes/` directory with explicit task breakdowns, file-level modifications, and acceptance criteria.

## The Yunjue paradigm reveals why tool evolution gates matter most

The **Yunjue Agent's In-Situ Self-Evolving paradigm** (arXiv 2601.18226, achieving 2nd place on HLE leaderboard) offers critical insights for your financial agent architecture. The paradigm treats tool evolution as the primary driver of capability expansion because tools provide **binary feedback signals**—execution either succeeds or fails, enabling verification without ground-truth labels.

This directly addresses several of your fatal flaws. The **executor running `__main__` self-tests** violates separation of concerns; Yunjue's architecture uses a four-role separation (Manager → Tool Developer → Executor → Integrator) where each role has distinct responsibilities. The **refiner bypassing verification gateway** contradicts the core principle that "every mutation requires a checkpoint with rollback always possible." Your **broken schema/indicator extraction** maps to Yunjue's observation that tool correctness is immediately detectable through code execution—failures are objective and verifiable.

Yunjue's **convergence monitoring metric** is particularly relevant for your benchmark configuration: track tool creation rate vs. query count as an analog to training loss. In their experiments, tool creation showed diminishing marginal returns—**128 tools** stabilized after ~4000 questions—demonstrating when capability expansion reaches equilibrium.

## Structuring the Phase 1b specification with file-level PR mapping

For your **5 fatal flaws addressed through 7 ordered PRs**, the OpenSpec `tasks.md` format provides the clearest structure. Each task specifies exact file/function/modification points:

```markdown
# Phase 1b: Fatal Flaw Resolution

## PR-1: Isolate Executor from Self-Test Contamination
**Flaw addressed**: Executor running __main__ self-tests
**Files modified**:
- [ ] `src/executor/main.py` - REMOVE self-test invocation from __main__ block
- [ ] `src/executor/runner.py` - EXTRACT test harness to separate module
- [ ] `tests/executor_tests.py` - MOVE self-tests to dedicated test suite
**Gate**: All existing tests pass, no __main__ execution in executor module

## PR-2: Restore Verification Gateway Enforcement
**Flaw addressed**: Refiner bypassing verification gateway
**Files modified**:
- [ ] `src/refiner/pipeline.py` - ADD mandatory gateway call before output
- [ ] `src/verification/gateway.py` - ENFORCE checkpoint creation
- [ ] `src/refiner/config.py` - REMOVE bypass flags
**Gate**: Gateway coverage = 100% of refiner outputs

## PR-3: Fix Schema Extraction Pipeline
**Flaw addressed**: Broken schema/indicator extraction
**Files modified**:
- [ ] `src/extraction/schema.py` - REWRITE extraction logic
- [ ] `src/extraction/indicators.py` - FIX parsing for edge cases
- [ ] `tests/extraction_golden.json` - ADD golden test cases
**Gate**: Schema extraction accuracy ≥ 95% on golden set

## PR-4: Unify Runtime Capability Constraints
**Flaw addressed**: Inconsistent runtime capability constraints
**Files modified**:
- [ ] `src/runtime/capabilities.py` - CONSOLIDATE constraint definitions
- [ ] `src/config/constraints.yaml` - CENTRALIZE all limits
- [ ] `src/agents/*.py` - REFERENCE central constraints
**Gate**: Single source of truth for all capability limits

## PR-5: Implement Data Layer Abstraction
**Flaw addressed**: Poor data layer portability
**Files modified**:
- [ ] `src/data/interfaces.py` - DEFINE abstract data layer interface
- [ ] `src/data/adapters/*.py` - CREATE adapter implementations
- [ ] `src/agents/base.py` - INJECT data layer dependency
**Gate**: Agents work with mock data adapter in tests

## PR-6: Add Evolution Gates Infrastructure
**Prerequisite**: PRs 1-5
**Files modified**:
- [ ] `src/evolution/gates.py` - CREATE evolution gate framework
- [ ] `src/verification/metrics.py` - ADD convergence tracking
- [ ] `configs/gates.yaml` - DEFINE gate thresholds
**Gate**: Gate infrastructure passes self-verification

## PR-7: Benchmark Integration and Validation
**Prerequisite**: PR-6
**Files modified**:
- [ ] `benchmarks/config_matrix.yaml` - DEFINE benchmark configurations
- [ ] `benchmarks/runner.py` - IMPLEMENT benchmark execution
- [ ] `ci/benchmark_gates.yaml` - CONFIGURE CI/CD integration
**Gate**: All 7 PRs verified against benchmark suite
```

## Benchmark configuration matrix for cold-start vs warm-start

The distinction between cold-start and warm-start testing is critical for your financial agent. **Cold-start** (no cached state, fresh model context) establishes true baseline performance, while **warm-start** (accumulated tool library, cached context) measures operational efficiency.

```yaml
benchmark_matrix:
  name: "Phase 1b Verification Suite"
  version: "1.0.0"
  
  conditions:
    cold_start:
      description: "Fresh initialization, no cached state"
      requirements:
        - Empty tool library
        - No cached SEC filings or financial data
        - Fresh model context per session
        - Wait 2-3 minutes between runs (cache clearance)
      use_cases:
        - Baseline establishment
        - Regression testing in CI/CD
        - Production deployment validation
        
    warm_start:
      description: "Accumulated state from prior execution"
      requirements:
        - Pre-populated tool library (from previous sessions)
        - Cached common financial data sources
        - Persistent model context within session
      use_cases:
        - Multi-turn conversation testing
        - Portfolio-level analysis
        - Incremental improvement validation
        
  task_categories:
    schema_extraction:
      weight: 0.25
      cold_start_threshold: 0.90
      warm_start_threshold: 0.95
      tests:
        - golden_schemas.json
        - edge_case_schemas.json
        
    indicator_parsing:
      weight: 0.20
      cold_start_threshold: 0.85
      warm_start_threshold: 0.92
      tests:
        - standard_indicators.json
        - complex_indicators.json
        
    verification_gateway:
      weight: 0.25
      cold_start_threshold: 1.00  # Must be 100%
      warm_start_threshold: 1.00
      tests:
        - gateway_coverage.json
        
    runtime_constraints:
      weight: 0.15
      cold_start_threshold: 1.00
      warm_start_threshold: 1.00
      tests:
        - constraint_enforcement.json
        
    data_portability:
      weight: 0.15
      cold_start_threshold: 0.95
      warm_start_threshold: 0.98
      tests:
        - adapter_compatibility.json

  gates:
    pr_merge:
      blocking:
        - metric: "accuracy_regression"
          threshold: -0.02  # Block if >2% regression
        - metric: "gateway_coverage"
          threshold: 1.00   # Must be 100%
        - metric: "behavioral_tests"
          threshold: 1.00   # All must pass
      warning:
        - metric: "latency_increase"
          threshold: 1.20   # Warn if >20% slower
          
    pre_production:
      blocking:
        - metric: "cold_start_baseline"
          threshold: 0.90
        - metric: "warm_start_improvement"
          threshold: 1.10   # Must be ≥10% better than cold
```

## Tool evolution gates follow the three-tier boundary model

The most effective specs use a **three-tier boundary system** combined with the **Agent Capability Standard's 36 atomic capabilities** across 9 cognitive layers. For your financial agent's evolution gates:

**Level 1 - Always Execute (Low Risk)**
- Retrieve financial data from cached sources
- Search public SEC EDGAR filings
- Execute read-only calculations
- Generate intermediate summaries

**Level 2 - Checkpoint Required (Moderate Risk)**
- Create new analytical tools during inference
- Modify workflow configurations
- Update cached financial data
- Execute multi-step reasoning chains

**Level 3 - Human Approval Required (High Risk)**
- Persist changes to tool library (permanent evolution)
- Modify verification gateway rules
- Change runtime capability constraints
- Deploy to production

The verification pipeline follows Anthropic's **continuous evaluation framework**: Pre-launch evals in CI/CD → Shadow deployment → Production monitoring → Transcript review. Each PR should include conformance criteria: "Must pass all cases in `conformance/pr-N-tests.yaml`."

## Dynamic specification updating as PRs complete

The spec document itself should evolve through OpenSpec's archive mechanism. When each PR completes:

1. **PR Merge Trigger**: Move completed change from `changes/phase1b-flaw-N/` to `archive/`
2. **Spec Update**: Merge approved delta into `specs/financial_agent/spec.md`
3. **Gate Recalibration**: Update baseline metrics for subsequent PRs
4. **Dependency Unlock**: Enable dependent PRs (e.g., PR-6 unlocks after PRs 1-5)

```markdown
# Spec Change Log (Living Document)

## Current State: PR-3 Complete, PR-4 In Progress

| PR | Status | Completion Date | Gate Result |
|----|--------|-----------------|-------------|
| PR-1 | ✅ Merged | 2026-02-10 | All gates passed |
| PR-2 | ✅ Merged | 2026-02-14 | All gates passed |
| PR-3 | ✅ Merged | 2026-02-18 | Schema accuracy: 96.2% |
| PR-4 | 🔄 In Review | - | Awaiting gate verification |
| PR-5 | ⏳ Blocked | - | Depends on PR-4 |
| PR-6 | ⏳ Blocked | - | Depends on PRs 1-5 |
| PR-7 | ⏳ Blocked | - | Depends on PR-6 |

## Updated Baselines (Post-PR-3)
- Schema extraction: 96.2% (was 78.4%)
- Indicator parsing: 91.3% (was 82.1%)
- Next target: Runtime constraint unification
```

## Practical template for Phase 1b specification document

Combining all patterns, your Phase 1b document should follow this structure:

```markdown
# Phase 1b Improvement Plan: Financial Agent System
**Paradigm**: Yunjue Agent In-Situ Self-Evolving
**Methodology**: OpenSpec Spec-Driven Development
**Version**: 1.0.0 | **Status**: Active | **Last Updated**: [Auto-updated]

## Executive Summary
[BLUF: What this phase accomplishes in 2-3 sentences]

## Fatal Flaws Addressed
| ID | Flaw | Severity | PR | Root Cause |
|----|------|----------|----|-----------| 
| F1 | Executor running __main__ self-tests | Critical | PR-1 | [cause] |
| F2 | Refiner bypassing verification gateway | Critical | PR-2 | [cause] |
| F3 | Broken schema/indicator extraction | High | PR-3 | [cause] |
| F4 | Inconsistent runtime capability constraints | High | PR-4 | [cause] |
| F5 | Poor data layer portability | Medium | PR-5 | [cause] |

## PR Dependency Graph
PR-1 → PR-2 → PR-3 → PR-4 → PR-5 → PR-6 → PR-7
         └──────────────────────────┘
         (PR-6 depends on all 1-5)

## Detailed PR Specifications
[Per-PR sections with file/function/modification points]

## Benchmark Configuration Matrix
[Cold-start vs warm-start configurations]

## Evolution Gates
[Three-tier boundary definitions]

## Verification Pipeline
[Per-PR gate criteria and conformance suites]

## Living Document Protocol
- Update frequency: After each PR merge
- Baseline recalibration: Automatic on merge
- Archive location: `openspec/changes/archive/phase1b/`
```

## Key sources informing this synthesis

The research draws from several authoritative sources: **OpenSpec** (github.com/Fission-AI/OpenSpec) for the spec-driven development framework; the **Yunjue Agent paper** (arXiv 2601.18226) for the In-Situ Self-Evolving paradigm and tool-first evolution principles; the **Agent Capability Standard** (github.com/synaptiai/agent-capability-standard) for the 36 atomic capabilities and verification patterns; **Anthropic's agent evaluation guidelines** for verification pipeline staging; **MLCommons/MLPerf** for benchmark-driven development standards; and the **Finance Agent Benchmark** for domain-specific evaluation patterns relevant to financial agent systems.