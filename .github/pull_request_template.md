## Summary

<!-- Brief description of what this PR does (1-3 bullets) -->

-

## OpenSpec Change

<!-- Link to the OpenSpec change if this PR is spec-driven -->

- [ ] Linked to: `openspec/changes/<name>/`
- Proposal: <!-- link to proposal.md -->
- Design: <!-- link to design.md -->
- Tasks: <!-- link to tasks.md -->

## Gate Criteria

From `fin_evo_agent/benchmarks/config_matrix.yaml`:

- [ ] Accuracy regression ≤ 2% (baseline: 85% / 17 of 20)
- [ ] Gateway coverage = 100%
- [ ] Security block rate = 100%
- [ ] Schema extraction accuracy ≥ 95%

## Changes

<!-- List key files/modules changed -->

### Added
-

### Modified
-

### Removed
-

## Test Plan

- [ ] Benchmark passes: `python benchmarks/run_eval.py --config cold_start`
- [ ] Unit tests pass: `pytest tests/`
- [ ] Security tests pass: `python benchmarks/run_eval.py --security-only`

## Verification

<!-- How did you verify this change works? -->

- [ ] All tasks in `tasks.md` marked complete
- [ ] Manual testing performed
- [ ] CI checks pass

---
🤖 Generated with [Claude Code](https://claude.ai/code)
