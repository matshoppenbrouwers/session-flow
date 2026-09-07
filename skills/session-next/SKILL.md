---
name: session-next
description: Implement the next task from the project's task sequence (backlog). Reads SEQUENCE.md, picks the next open entry that has a linked breakdown, executes it, and marks it done. Use when the user wants to make progress on the backlog without naming a specific task. Triggers on "/session-next" or when user says "implement the next task", "do the next task", "what's next — just do it", or "work the backlog".
---

# Session Next

Pick up and execute the next ready task from the sequence backlog.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Only execute entries with a valid linked breakdown.** An entry marked `(needs breakdown)` or with a dangling link is not ready. Skip it and offer `/session-groom`.
2. **A completion marker covers exactly the entry's owned tasks.** Mark `[x]` in `SEQUENCE.md` once every task ID in the resolved target scope (Step 2) is `[x]` and its aggregate acceptance has passed — never on the first task of several. For a per-task breakdown, also set `**Status**: [x]` in the file. A phase-file anchor has no per-task `**Status**` line: `/session-delegation` marks each task it ran, and you close the entry. Do not batch — a backlog reader must see live state.
3. **Respect order and priority.** Pick the topmost open entry; among equals, prefer lower P-number (P1 before P3). At equal priority, a manual entry outranks one marked `[auto]` — a bot's enqueue never jumps ahead of what the user asked for. Don't cherry-pick the easy one.
4. **Hand off a resolved scope, never a container.** When the link points into a `session-task-planning` phase file, pass `/session-delegation` the resolved target scope — the SEQ identity and the task IDs it owns. A phase file holds tasks belonging to several entries; it is never itself the unit of work.
5. **One task per invocation unless told otherwise.** Finish, report, and suggest the next. Don't silently churn through the whole backlog.

## Path Resolution

1. Read `.session-flow.json` for `paths.sequence`, `paths.tasks`, `paths.todo`. Paths may point outside the repo; resolve them relative to the repo root.
2. If missing, detect `{todo}/SEQUENCE.md` and `{todo}/tasks/`.
3. If no sequence file exists, say so and suggest `/session-add-task` or `/session-gatekeeper` to populate it (or `/session-init` if the project isn't set up).

## Workflow

### Step 1: Select the next entry

Read `SEQUENCE.md`. From top to bottom, find the first entry that is:
- `[ ]` (open), and
- has a link to a breakdown (per-task file or phase-file anchor).

Among otherwise-equal candidates, prefer the lowest P-number; at equal priority, prefer the entry **without** an `[auto]` marker (a bot enqueued the marked one — see Non-Negotiable 3). If the topmost open entries are all `(needs breakdown)`, report that and offer to run `/session-groom` to prepare them.

### Step 2: Resolve the target scope

An entry's link addresses tasks, not a container. Resolve it once into an explicit target scope and carry that same scope through dispatch, acceptance, and close-out:

```
SEQ identity: SEQ-NNN
Breakdown:    <resolved path>
Owned tasks:  <ordered task IDs>
```

- **Per-task file** (`{tasks}/NNNN-slug.md`): the owned task is that file's single breakdown. Read its Files, Instructions, Accept, Test.
- **Phase-file anchor** (`{todo}/<file>.md#TASK-ID`): the owned task is `TASK-ID` and nothing else. The anchor must resolve to exactly one task heading in that file; on zero or several matches, stop, report the anchor and what it matched, and offer `/session-groom`.

Sibling tasks in the same phase file belong to other sequence entries, or to no entry yet. They stay out of scope even when this entry's title names the phase that contains them, and their `[ ]` or `[x]` state says nothing about this entry.

Widen the scope only when the user names the additional task IDs in this invocation. Then list every ID under Owned tasks, echo the resolved scope back in one line before dispatching, and close out against that set as a whole. Never derive extra IDs from the entry title, a phase heading, a `Phase N` label, or the remaining open tasks beside the anchor.

### Step 3: Execute a per-task breakdown

Run the bite-sized prompt directly:
1. Read all referenced files first.
2. Implement the change the breakdown describes.
3. Add the test that pins the acceptance criterion: one focused test, in the existing test module where one exists, covering the decision logic rather than the framework or trivial pass-throughs. Where the project's own CLAUDE.md states a testing rule, that rule wins.
4. Run the breakdown's exact Test command.
5. Commit the change with a descriptive message.

### Step 4: Hand off a multi-task scope

When the owned tasks live in a phase file, invoke `/session-delegation` with the resolved scope: the SEQ identity, the owned task IDs, and the phase file that holds them. Delegation dispatches those IDs plus their permitted prerequisite closure and leaves every other task alone.

Delegation returns two separate results: per-task progress (each dispatched task `[x]` once its own Test passed) and the scope's aggregate acceptance (the scope's Accept criteria plus the project suite). Both are needed to close the entry; per-task progress alone is not completion.

### Step 5: Close out

1. Check the scope: every owned task `[x]`, and delegation's aggregate acceptance passed. If either is short, leave the entry `[ ]`, report the outstanding task IDs and checks, and stop here.
2. Mark the entry `[x]` in `SEQUENCE.md`.
3. Set `**Status**: [x]` in the breakdown file (for per-task files).
4. Report: the SEQ identity and the exact task IDs the marker covers, what was implemented, files changed, test result. When the scope was part of a phase file, name the sibling tasks still `[ ]` so nobody reads the marker as phase completion. If the entry carried `[auto]`, say so — the user is seeing a bot-enqueued item's outcome, and that is worth one clause.
5. Suggest the next entry (or note the backlog is clear / needs grooming).

Chain context: see `references/workflow-overview.md`.
