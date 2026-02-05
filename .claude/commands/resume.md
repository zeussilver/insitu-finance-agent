---
name: Resume
description: "Resume work from a checkpoint in a fresh window"
category: Workflow
tags: [workflow, checkpoint, context, resume]
---

# Resume Command

Resume work from a saved checkpoint file.

## Input

The argument after `/resume` can be:
- A specific checkpoint path: `/resume .claude/checkpoints/CHECKPOINT_2026-02-04T20:45:00.md`
- Empty (use most recent): `/resume`

## What To Do

1. **Find Checkpoint**

   If no path provided, find the most recent checkpoint:
   ```bash
   ls -t .claude/checkpoints/CHECKPOINT_*.md | head -1
   ```

2. **Read and Display Checkpoint**

   Read the checkpoint file and display its contents to establish context.

3. **Load Additional Context**

   Based on the checkpoint, load relevant context:
   - If OpenSpec change mentioned: Read `openspec/changes/<name>/tasks.md`
   - Read key files mentioned in checkpoint
   - Check git status for any changes since checkpoint

4. **Confirm Ready to Continue**

   Display:
   ```
   ## Context Restored

   <checkpoint summary>

   ### Changes Since Checkpoint
   <git diff summary if any>

   Ready to continue. What would you like to work on?
   ```

## Example Flow

```
User: /resume

Claude: [finds most recent checkpoint]
        [reads checkpoint file]
        [reads referenced key files]
        [checks git status]

        ## Context Restored

        **Active Work**: Phase 1B Flaw Resolution
        **Last Task Completed**: Task 4.1 (Executor migration)
        **Next Task**: Task 4.2 (Verifier migration)

        ### Key Context
        - Centralized constraints in configs/constraints.yaml
        - Using singleton pattern with get_constraints()
        - Properties replace class constants

        ### Changes Since Checkpoint
        No uncommitted changes.

        Ready to continue. What would you like to work on?

User: Continue with Task 4.2
```

## Important

- Always read the full checkpoint before proceeding
- Load enough context to be productive immediately
- Don't assume - if checkpoint references files, read them
- If checkpoint is stale (lots of changes since), warn the user
