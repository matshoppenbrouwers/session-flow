---
name: session-next
description: Implement the next task from the project's task sequence (backlog). Reads SEQUENCE.md, picks the next open entry that has a linked breakdown, executes it, and marks it done. Use when the user wants to make progress on the backlog without naming a specific task. Triggers on "/session-next" or when user says "implement the next task", "do the next task", "what's next — just do it", or "work the backlog".
---

# Session Next

Pick up and execute the next ready task from the sequence backlog.

**Announce:** "Using session-next to implement the next task from the sequence."

## Non-Negotiables

1. **Only execute entries with a valid linked breakdown.** An entry marked `(needs breakdown)` or with a dangling link is not ready. Skip it and offer `/session-groom`.
2. **Mark `[x]` on completion.** Always update the entry in `SEQUENCE.md`. For a per-task breakdown, also set `**Status**: [x]` in the file. (A phase-file anchor has no per-task `**Status**` line — `/session-delegation` marks the phase tasks `[x]`; you just close the entry.) Do not batch — a backlog reader must see live state.
3. **Respect order and priority.** Pick the topmost open entry; among equals, prefer lower P-number (P1 before P3). Don't cherry-pick the easy one.
4. **Hand off multi-task breakdowns.** If the link points to a `session-task-planning` phase file, dispatch via `/session-delegation` — do not try to do a whole phase as one task.
5. **One task per invocation unless told otherwise.** Finish, report, and suggest the next. Don't silently churn through the whole backlog.

## Path Resolution

1. Read `.session-flow.json` for `paths.sequence`, `paths.tasks`, `paths.todo`.
2. If missing, detect `{todo}/SEQUENCE.md` and `{todo}/tasks/`.
3. If no sequence file exists, say so and suggest `/session-add-task` or `/session-gatekeeper` to populate it (or `/session-init` if the project isn't set up).

## Workflow

### Step 1: Select the next entry

Read `SEQUENCE.md`. From top to bottom, find the first entry that is:
- `[ ]` (open), and
- has a link to a breakdown (per-task file or phase-file anchor).

Among otherwise-equal candidates, prefer the lowest P-number. If the topmost open entries are all `(needs breakdown)`, report that and offer to run `/session-groom` to prepare them.

### Step 2: Open the breakdown

- **Per-task file** (`todo/tasks/NNNN-slug.md`): read it. It contains Files, Instructions, Accept, Test.
- **Phase-file anchor** (`todo/...#TASK-ID`): this is multi-task work → go to Step 4.

### Step 3: Execute a per-task breakdown

Run the bite-sized prompt directly:
1. Read all referenced files first.
2. Write the test(s) the acceptance criterion needs — no more. Prefer extending an existing test module over forking a new one. Cover the pure/decision layer; don't test the framework, mocks, or trivial pass-throughs. (Defer to the project's root `CLAUDE.md` "Test with altitude" principle, which wins where present.)
3. Implement until the test passes.
4. Run the breakdown's exact Test command.
5. Commit the change with a descriptive message.

### Step 4: Hand off multi-task work

If the entry links to a phase file, invoke `/session-delegation` against that file. Delegation runs the dependency graph and marks each task `[x]`. The sequence entry is done only when the linked phase (or anchored task) is complete.

### Step 5: Close out

1. Mark the entry `[x]` in `SEQUENCE.md`.
2. Set `**Status**: [x]` in the breakdown file (for per-task files).
3. Report: what was implemented, files changed, test result.
4. Suggest the next entry (or note the backlog is clear / needs grooming).

Chain context: see `references/workflow-overview.md`.
