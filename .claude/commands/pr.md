---
name: "PR"
description: Create a PR from an OpenSpec change with structured body linking to spec files
category: Workflow
tags: [workflow, pr, openspec, git]
---

Create a pull request from an OpenSpec change with gate criteria and spec links.

**Input**: The argument after `/pr` is the change name (kebab-case), e.g., `/pr my-feature`

**Prerequisites**:
- Change must exist at `openspec/changes/<name>/`
- All implementation tasks should be complete (check `tasks.md`)

**Steps**

1. **Validate the change exists**

   Check that `openspec/changes/<name>/` exists. If not, show available changes:
   ```bash
   ls -d openspec/changes/*/
   ```
   And suggest running `/opsx:new <name>` first.

2. **Check or create the branch**

   Check if already on the correct branch:
   ```bash
   git branch --show-current
   ```

   If on `main`, create and switch to the feature branch:
   ```bash
   git checkout -b openspec/<name>
   ```

   If already on `openspec/<name>`, continue.

   If on a different branch, ask the user if they want to switch.

3. **Gather change context**

   Read these files to build the PR description:
   - `openspec/changes/<name>/proposal.md` - Summary and rationale
   - `openspec/changes/<name>/tasks.md` - Implementation checklist
   - `fin_evo_agent/benchmarks/config_matrix.yaml` - Gate thresholds

4. **Stage and commit any uncommitted work**

   Check for uncommitted changes:
   ```bash
   git status --porcelain
   ```

   If there are changes, commit them with a conventional commit message:
   ```bash
   git add -A
   git commit -m "feat(<name>): implement <brief description>

   OpenSpec change: openspec/changes/<name>/

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
   ```

5. **Push the branch**

   ```bash
   git push -u origin openspec/<name>
   ```

6. **Create the PR with structured body**

   Use `gh pr create` with a HEREDOC body:
   ```bash
   gh pr create --title "feat(<name>): <title from proposal.md>" --body "$(cat <<'EOF'
   ## Summary
   <1-3 bullets from proposal.md>

   ## OpenSpec Change
   - Change: `openspec/changes/<name>/`
   - Proposal: [proposal.md](openspec/changes/<name>/proposal.md)
   - Design: [design.md](openspec/changes/<name>/design.md)
   - Tasks: [tasks.md](openspec/changes/<name>/tasks.md)

   ## Gate Criteria
   From `fin_evo_agent/benchmarks/config_matrix.yaml`:
   - [ ] Accuracy regression ≤ 2%
   - [ ] Gateway coverage = 100%
   - [ ] Security block rate = 100%

   ## Test Plan
   - [ ] Benchmark passes: `python benchmarks/run_eval.py --config cold_start`
   - [ ] All tasks in tasks.md marked complete

   ---
   🤖 Generated with [Claude Code](https://claude.ai/code)
   EOF
   )"
   ```

7. **Output the PR URL**

   Show the user the created PR URL and next steps:
   - Wait for CI checks
   - Request review if needed
   - After merge, run `/opsx:archive <name>`

**Guardrails**
- Do NOT force push or rebase unless explicitly asked
- Do NOT create a PR if there are uncommitted changes without committing first
- If the remote branch already exists, push to it (don't create a new one)
- If a PR already exists for this branch, show its URL instead of creating a new one

**Examples**

```bash
# Create PR for an existing change
/pr phase1b-flaw-resolution

# Will:
# 1. Create branch openspec/phase1b-flaw-resolution (if not exists)
# 2. Commit any uncommitted work
# 3. Push to remote
# 4. Create PR with structured body
```
