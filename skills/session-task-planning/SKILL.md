---
name: session-task-planning
description: Create Claude Code-scoped tasks with parallelization analysis. Use when breaking down a multi-step implementation into discrete tasks that can each be completed in one Claude Code session. Produces task files with dependency tags ([seq], [parallel-after:X]) and session-fit validation. Triggers on "/session-task-planning" or when user says "break this into tasks", "plan the tasks", or "create a task list".
---

# Session Task Planning

Convert implementation plans into session-scoped tasks with explicit parallelization opportunities.

**Announce:** "Using session-task-planning to break this into Claude Code session-sized tasks."

## Non-Negotiables

1. **Task files go to `todo/`, never `plans/`.** Design documents and task files are separate artifacts with separate directories.
2. **Every task has Files, Instructions, Accept, Test.** No exceptions. A task missing any field is not valid and must be revised before saving.
3. **Accept criteria must be observable.** "Code is cleaner" is not acceptance. `pytest tests/foo.py::test_bar passes` is.
4. **Action verbs only.** "Create", "Add", "Move", "Extract" — not "Consider", "Look into", "Think about".
5. **Every parallelism claim is tested against the file-modification graph.** If two tasks touch the same file, they cannot be `[parallel-after:X]` — they must be `[seq]`.
6. **Exact paths, not "relevant files".** `src/auth/login.py:45-120` — not "auth files".

## Core Principle

Each task must be completable in **one Claude Code session** (~30 min focused work). Tasks too large get split. Tasks too small get merged.

**Predecessor:** Expects an implementation plan from `/session-research-design` or equivalent. If no plan exists, ask the user for one before proceeding.

## Task Sizing Rules

**Right-sized task:**
- Modifies 1-5 files
- Has clear acceptance criteria
- Can be tested independently
- Produces a commit

**Too large (split it):**
- Touches >5 files across domains
- Has multiple independent outcomes
- Requires context switches (backend -> frontend -> docs)
- "Do X, Y, and Z" where X, Y, Z are independent

**Too small (merge it):**
- Single-line change
- Pure formatting/linting
- No testable outcome

## Task Template

```markdown
### [PHASE-TASK] [dependency-tag] [status] P[priority]: Title
**Files**: `path/to/file.py`, `path/to/other.py:100-200`

**Instructions**:
- Read [reference] first
- Step 1 (action verb)
- Step 2 (action verb)
- Step 3 (action verb)

**Accept**: [Observable outcome that proves completion]

**Test**: `[exact command to verify]`

---
```

**Files entries** may be exact paths (`src/api/routes.py`, `src/api/routes.py:100-200`) or directory globs (`src/lib/governor/**`) when a task legitimately owns a whole subtree. Still never "relevant files" — the entry has to name a footprint.

Files doubles as the **dispatch write boundary**: `/session-delegation` injects it into every agent payload as "you may only create or modify these paths". An incomplete Files field means an agent stops mid-task and reports instead of doing the work, so list everything the task must touch.

### Tag Reference

| Tag | Meaning |
|-----|---------|
| `[seq]` | Must complete before next task starts |
| `[parallel-after:X]` | Can run parallel with siblings after task X |
| `[x]` | Completed |
| `[plan]` | Planning phase (design not code) |
| `[ ]` | Not started |

### Priority Levels

- **P1**: Critical path, blocks other work
- **P2**: Important but not blocking
- **P3**: Nice to have, can defer

## Dependency Analysis

### Step 1: List all tasks

Write out all tasks without dependencies first.

### Step 2: Build dependency graph

For each task pair, ask:
- Does Task B need Task A's code/output?
- Do they modify the same files?
- Does Task B's test require Task A's implementation?

If any "yes" -> B depends on A.

### Step 3: Identify parallel opportunities

Tasks with same dependency can run parallel:
```
A-1 --> A-2 +---> B-1 --> C-1 +---> done
       A-3 +              C-2 +
```

Here A-2 + A-3 are parallel (both depend on A-1), C-1 + C-2 are parallel (both depend on B-1).

### Step 4: Create parallelization guide

Add ASCII diagram at top of task file:

```markdown
## Parallelization Guide

```
1A-1 --> 1A-2 +---> 1B-1 --> 1C-1 +---> done
         1A-3 +              1C-2 +
```

**Parallel opportunities:**
- 1A-2 + 1A-3 (after 1A-1 completes)
- 1C-1 + 1C-2 (after 1B-1 completes)
```

## File Structure

Save the task file to the project's **todo** directory (read path from `.session-flow.json` config, or detect `todo/`, `_devdocs/todo/`, `docs/todo/`). If not found, suggest running `/session-init`. **Never** save task files to `plans/` -- that directory is for implementation plans from `/session-research-design`.

```markdown
# Phase N: [Phase Name]

**Design Doc**: `[path to design doc]`
**Goal**: [One sentence]

Each task references the design doc -- read it first for full context.

---

## Parallelization Guide

[ASCII diagram]

[Tag legend table]

**Parallel opportunities:**
- [List explicit parallel pairs]

---

## Phase NA: [Subphase Name]

### [NA-1] [seq] [ ] P1: First task
...

### [NA-2] [parallel-after:NA-1] [ ] P1: Second task
...

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| [Criterion 1] | [How to verify] |
| [Criterion 2] | [How to verify] |
```

## Sequence Integration

After writing a phase file, optionally surface it on the task backlog so it can be picked up with "implement the next task":

- Offer to register the phase's top-level tasks as entries in `SEQUENCE.md`, each linked to its task anchor (e.g. `→ todo/2026-06-03-feature.md#1A-1`).
- For one-off follow-ups that don't warrant a full phase, point the user to `/session-add-task` instead.
- This is additive only. Keep the `todo/` vs `plans/` separation intact -- phase files and breakdowns live under `todo/`, design docs stay in `plans/`.

## Validation Checklist

Before finalizing, verify each task:

- [ ] Has all required fields (Files, Instructions, Accept, Test)
- [ ] Instructions use action verbs ("Create", "Add", "Move", not "Consider")
- [ ] Files are explicit paths or directory globs, not "relevant files"
- [ ] Accept criteria is observable, not "code is clean"
- [ ] Test command is exact and runnable
- [ ] Dependency tag is correct
- [ ] Can be done in one session without external blockers

## Anti-Patterns

**Missing dependencies:**
- BAD: Tasks that secretly depend on each other marked as parallel
- GOOD: If B uses A's output, B has `[parallel-after:A]` or `[seq]` after A

Chain context: see `references/workflow-overview.md`.
