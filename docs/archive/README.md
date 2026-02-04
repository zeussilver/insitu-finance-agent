# Archived Documentation

> **Warning**: The documents in this directory are **archived and no longer maintained**.
>
> They were created during early development when the project used different technologies
> (akshare for Chinese A-shares instead of yfinance for US stocks).

## Why These Documents Are Archived

During January 2026, the project underwent a significant migration:

| Before | After |
|--------|-------|
| akshare (Chinese A-shares) | yfinance (US stocks) |
| Chinese stock codes (600519, 000001) | US tickers (AAPL, MSFT, SPY) |
| 10% benchmark pass rate | **85% benchmark pass rate** |

The documents in this directory reflect the pre-migration state and contain outdated:
- API references (akshare instead of yfinance)
- Stock codes (Chinese A-share codes instead of US tickers)
- File paths and module names
- Performance metrics

## Current Documentation

For up-to-date documentation, see:

- **[README.md](../../README.md)** - Project overview and quick start
- **[CLAUDE.md](../../CLAUDE.md)** - Authoritative technical reference (for AI assistants)
- **[docs/index.md](../index.md)** - Documentation hub

## Archived Documents

| File | Original Name | Topic |
|------|---------------|-------|
| [plan_akshare.md](plan_akshare.md) | plan.md | Phase 1a planning (akshare-based) |
| [spec_akshare.md](spec_akshare.md) | spec.md | Technical specification (akshare-based) |
| [check_akshare.md](check_akshare.md) | check.md | Acceptance checklist (akshare-based) |
| [eval_akshare.md](eval_akshare.md) | eval.md | Evaluation specification (akshare-based) |
| [guide_chinese.md](guide_chinese.md) | 金融智能体底座构建指南.md | Chinese implementation guide |
| [handoff_jan31.md](handoff_jan31.md) | .continue-here.md | Work handoff document |
| [problem.md](problem.md) | problem.md | Root cause analysis |
| [output_jan30.md](output_jan30.md) | fin_evo_agent/output.md | Early evaluation report (10% pass rate) |

---

*Archived on: 2026-02-04*
