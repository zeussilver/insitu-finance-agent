# Documentation Audit Report

**Audit Date**: 2026-02-04
**Auditor**: Claude Code
**Project**: Yunjue Agent (Insitu Finance Agent)

---

## 1. Executive Summary

This audit documents the documentation cleanup performed on 2026-02-04. The project migrated from akshare (Chinese A-shares) to yfinance (US stocks) during development, but most documentation was not updated to reflect this change. CLAUDE.md was the only up-to-date document.

### Migration Impact

| Before | After |
|--------|-------|
| akshare (Chinese A-shares) | yfinance (US stocks) |
| Chinese stock codes (600519, 000001) | US tickers (AAPL, MSFT, SPY) |
| 10% benchmark pass rate | **85% benchmark pass rate** |

---

## 2. Documentation Asset Inventory

| Path | Topic | Last Git Update | Linked from Entry? | Status | Evidence |
|------|-------|-----------------|-------------------|--------|----------|
| `CLAUDE.md` | Main project guide | 2026-02-03 | Entry point | **Keep** | Current (yfinance, 85% pass rate) |
| `plan.md` | Phase 1a planning | 2026-02-02 (initial) | No | **Archived** | References akshare, A-shares (000001, 600519) |
| `spec.md` | Technical specification | 2026-02-02 (initial) | No | **Archived** | References akshare API, wrong ALLOWED_MODULES |
| `check.md` | Acceptance checklist | 2026-02-02 (initial) | No | **Archived** | References akshare, A-share codes, wrong paths |
| `eval.md` | Evaluation spec | 2026-02-02 (initial) | No | **Archived** | Chinese stock codes, akshare API |
| `金融智能体底座构建指南.md` | Chinese implementation guide | 2026-02-02 (initial) | No | **Archived** | Entire doc is akshare-based |
| `.continue-here.md` | Work handoff doc | 2026-02-02 (initial) | No | **Archived** | References akshare→yfinance migration as in-progress |
| `problem.md` | Root cause analysis | 2026-02-02 (initial) | No | **Archived** | Analysis of pre-migration issues |
| `fin_evo_agent/output.md` | Evaluation report | N/A | No | **Archived** | Shows 10% pass rate (now 85%) |
| `.planning/PROJECT.md` | Project overview | 2026-01-31 | No | **Keep** | Mix of old/new references (historical) |
| `.planning/STATE.md` | Current state | 2026-02-04 | No | **Updated** | Now shows 85% pass rate |
| `.planning/phases/*` | Development history | Various | No | **Keep** | Historical reference |
| `.planning/codebase/*` | Architecture docs | Various | No | **Keep** | Still relevant |

---

## 3. Consistency Checks

### 3.1 Data Source Mismatch (akshare → yfinance)

| Document | Line(s) | Issue |
|----------|---------|-------|
| `plan.md` | 22, 36, 41, 49, 71-73, 113-119 | References "AkShare", "akshare==1.13.50", A-share API |
| `spec.md` | 21-22, 205-206, 293-319 | Lists AkShare as data source, bootstrap tools |
| `check.md` | 24-30, 68-80 | Tests akshare installation, A-share data |
| `eval.md` | 28-68 | All tasks use Chinese stock codes (600519, 000001) |
| `金融智能体底座构建指南.md` | Throughout | Entire implementation based on akshare |
| `.continue-here.md` | 10-28 | Documents migration status (incomplete) |

**Actual**: `requirements.txt` shows `yfinance>=0.2.30`, `openai>=1.0.0`

### 3.2 Stock Code Mismatch

| Document | References | Actual (tasks.jsonl) |
|----------|-----------|---------------------|
| `check.md` | 000001, 000858, 600519 | AAPL, MSFT, SPY |
| `eval.md` | 600519, 000001, 沪深300 | AAPL, TSLA, ^GSPC |

### 3.3 Path/Structure Mismatch

| Document | Claims | Actual |
|----------|--------|--------|
| `plan.md:69` | `data/evolution.db` | `data/db/evolution.db` |
| `plan.md:72` | `artifacts/bootstrap/get_a_share_hist.py` | `get_stock_hist_v0.1.0_*.py` |
| `spec.md:205` | `ALLOWED_MODULES` includes `akshare`, `talib` | Includes `yfinance`, no `talib` |

### 3.4 Pass Rate Mismatch

| Document | Claims | Actual |
|----------|--------|--------|
| `output.md` | 10% pass rate | 85% (per latest benchmark) |
| `.planning/STATE.md` | ~~75%~~ 85% pass rate | 85% (fixed) |

---

## 4. Archived Documents

The following 8 documents have been archived to `docs/archive/`:

| Original Location | Archive Location | Reason for Archival |
|------------------|------------------|---------------------|
| `plan.md` | `docs/archive/plan_akshare.md` | References akshare, A-shares API |
| `spec.md` | `docs/archive/spec_akshare.md` | akshare-based technical specification |
| `check.md` | `docs/archive/check_akshare.md` | Tests akshare installation, A-share codes |
| `eval.md` | `docs/archive/eval_akshare.md` | Chinese stock codes in all tasks |
| `金融智能体底座构建指南.md` | `docs/archive/guide_chinese.md` | Entire implementation is akshare-based |
| `.continue-here.md` | `docs/archive/handoff_jan31.md` | Documents incomplete migration |
| `problem.md` | `docs/archive/problem.md` | Analysis of pre-migration issues |
| `fin_evo_agent/output.md` | `docs/archive/output_jan30.md` | Shows outdated 10% pass rate |

Each archived file has been prefixed with a banner:
```markdown
> ⚠️ **ARCHIVED - NOT MAINTAINED**
> This document reflects the pre-yfinance implementation (akshare-based).
> For current documentation, see [CLAUDE.md](../../CLAUDE.md).
> Archived on: 2026-02-04
```

---

## 5. Files Deleted

| File | Reason |
|------|--------|
| `2026-01-31-local-command-caveatcaveat-the-messages-below-w.txt` | Claude Code session log, not documentation |

---

## 6. Current Documentation Structure

```
Insitu finance agent/
├── README.md                     # User-facing entry point (NEW)
├── CLAUDE.md                     # Authoritative technical reference
├── docs/
│   ├── index.md                  # Documentation hub (NEW)
│   ├── docs_audit.md             # This audit report (NEW)
│   ├── docs_checklist.md         # Verification checklist (NEW)
│   └── archive/                  # Archived documents
│       ├── README.md             # Archive index with disclaimer (NEW)
│       ├── plan_akshare.md       # (was plan.md)
│       ├── spec_akshare.md       # (was spec.md)
│       ├── check_akshare.md      # (was check.md)
│       ├── eval_akshare.md       # (was eval.md)
│       ├── guide_chinese.md      # (was 金融智能体底座构建指南.md)
│       ├── handoff_jan31.md      # (was .continue-here.md)
│       ├── problem.md            # (was problem.md)
│       └── output_jan30.md       # (was fin_evo_agent/output.md)
└── .planning/
    ├── PROJECT.md                # Project overview
    ├── STATE.md                  # Current state (85% pass rate)
    ├── phases/                   # Development history
    └── codebase/                 # Architecture documentation
```

### Documentation Hierarchy

1. **`README.md`** - User entry point with:
   - Project overview
   - Quick start commands
   - Links to detailed documentation

2. **`CLAUDE.md`** - Authoritative technical reference for:
   - Architecture and core principles
   - Implementation status
   - CLI commands
   - Security model
   - Benchmark results

3. **`docs/index.md`** - Documentation table of contents

4. **`docs/archive/*`** - Historical reference only (8 files)

---

## 7. Recommendations

1. **Maintain CLAUDE.md as primary technical documentation** - All current project information is consolidated there
2. **Use README.md for new users** - Simple entry point with quick start
3. **Do not update archived documents** - They serve as historical record only
4. **Preserve archive for audit trail** - Documents the akshare→yfinance migration history

---

*End of Documentation Audit Report*
