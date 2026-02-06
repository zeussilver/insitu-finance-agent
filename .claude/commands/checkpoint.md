---
name: Checkpoint
description: "Save current work state and prepare for fresh window continuation"
category: Workflow
tags: [workflow, checkpoint, context, handoff]
---

# Checkpoint Command

Create a checkpoint of current work state so the user can continue in a fresh Claude Code window with full context.

## What To Do

1. **Identify Current Work Context**
   - Check for active OpenSpec changes: `ls openspec/changes/` if exists
   - Check task lists if any
   - Review recent file modifications from git status
   - Note any in-progress work mentioned in conversation

2. **Create Checkpoint File**

   Create a timestamped checkpoint at `.claude/checkpoints/CHECKPOINT_<timestamp>.md` with:

   ```markdown
   # Checkpoint - <timestamp>

   ## Active Work
   [What was being worked on]

   ## Current Status
   [Where things stand - what's done, what's in progress]

   ## Next Steps
   [Clear, actionable items to continue]

   ## Key Files
   [Important files to review when resuming]

   ## Context
   [Any important decisions, blockers, or notes]
   ```

3. **Display Resume Instructions**

   After creating the checkpoint, display:

   ```
   ## Checkpoint Saved

   File: .claude/checkpoints/CHECKPOINT_<timestamp>.md

   ## To Resume in Fresh Window

   Open a new Claude Code session and say:

   > Resume from checkpoint: .claude/checkpoints/CHECKPOINT_<timestamp>.md

   Or simply:

   > /resume
   ```

## Checkpoint Content Guidelines

- Be concise but complete
- Include specific file paths and line numbers where relevant
- Note any uncommitted changes
- Capture decisions made but not yet documented
- Include any error states or blockers
- Reference OpenSpec change names if applicable

## Example Checkpoint

```markdown
# Checkpoint - 2026-02-04T20:45:00

## Active Work
Phase 1B Flaw Resolution (OpenSpec change: phase1b-flaw-resolution)

## Current Status
- Tasks 1.1-1.10 complete (Infrastructure Setup)
- Tasks 2.1-2.6 complete (Test Infrastructure)
- Tasks 3.1-3.5 complete (Verification Gateway)
- Task 4.1 complete (Executor migration to centralized constraints)
- Currently on: Task 4.2 (Verifier migration)

## Next Steps
1. Complete Task 4.2: Update verifier.py to use centralized constraints
2. Complete Task 4.3: Update capabilities.py to use centralized constraints
3. Run test suite to verify migrations work

## Key Files
- `openspec/changes/phase1b-flaw-resolution/tasks.md` - Full task list
- `fin_evo_agent/src/core/constraints.py` - Centralized config
- `fin_evo_agent/src/core/verifier.py` - Next to modify

## Context
- Using singleton pattern for constraints loading
- Properties replace class constants for backward compatibility
- All security rules now in configs/constraints.yaml
```

## Important

- Always create the checkpoint file BEFORE displaying instructions
- Use ISO 8601 timestamp format
- Keep the checkpoint focused - it's a resume point, not full documentation
