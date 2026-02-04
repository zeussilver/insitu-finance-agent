# Documentation Verification Checklist

After the documentation cleanup, verify:

## Link Verification
- [x] README.md Quick Start commands work: `python main.py --init`, `python main.py --list`
- [x] README.md links to CLAUDE.md exist
- [x] README.md links to docs/index.md exist
- [x] docs/index.md links all resolve correctly
- [x] All archived docs have "Archived / Not maintained" banner

## Content Verification
- [x] requirements.txt lists yfinance (not akshare)
- [x] .planning/STATE.md shows 85% pass rate
- [x] No orphaned docs (all reachable from README or docs/index.md)

## Archive Verification
- [x] docs/archive/README.md exists with archive index
- [x] 8 archived documents present in docs/archive/
- [x] Original files removed from project root

## Files Created (5 total)
- [x] README.md (new)
- [x] docs/index.md (new)
- [x] docs/docs_audit.md (new)
- [x] docs/docs_checklist.md (this file)
- [x] docs/archive/README.md (new)

## Files Archived (8 total)
- [x] plan.md → docs/archive/plan_akshare.md
- [x] spec.md → docs/archive/spec_akshare.md
- [x] check.md → docs/archive/check_akshare.md
- [x] eval.md → docs/archive/eval_akshare.md
- [x] 金融智能体底座构建指南.md → docs/archive/guide_chinese.md
- [x] .continue-here.md → docs/archive/handoff_jan31.md
- [x] problem.md → docs/archive/problem.md
- [x] fin_evo_agent/output.md → docs/archive/output_jan30.md

## Files Updated (1 total)
- [x] .planning/STATE.md - Fixed 75% → 85% pass rate

## Files Deleted (1 total)
- [x] 2026-01-31-local-command-caveatcaveat-the-messages-below-w.txt

---
*Checklist verified: 2026-02-04*
