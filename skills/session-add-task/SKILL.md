---
name: session-add-task
description: Capture a new task into the project's task sequence (backlog) with a detailed breakdown. Use when something surfaces that should be done later — a bug, an optimization, a follow-up — and you want it recorded in SEQUENCE.md with a bite-sized, ready-to-execute breakdown. Produces a one-line sequence entry linked to a per-task breakdown file (or a session-task-planning phase file for multi-task work). Triggers on "/session-add-task" or when user says "add a task", "capture this for later", "put this on the backlog", or "remember to do X".
---

# Session Add Task

Capture a task into the sequence backlog so it can be picked up later with "implement the next task".

**Announce:** "Using session-add-task to capture this into the task sequence."

## Non-Negotiables

1. **Every breakdown has Files, Instructions, Accept, Test.** A linked breakdown missing any field is not valid. The only exception is a deliberate `(needs breakdown)` capture (mode C), which has no breakdown yet by design.
2. **Sequence IDs are unique and monotonic.** Scan existing ids and use the next integer. The entry id is `SEQ-NNN` (zero-padded to 3 digits); the breakdown file uses the same number zero-padded to 4 (`NNNN-slug.md`). Never reuse or duplicate an id.
3. **Never overwrite an existing breakdown file.** If `todo/tasks/NNNN-slug.md` exists, pick a new id/slug. Appending to the sequence is additive only.
4. **One-line entries stay one line.** The sequence is a scannable list. Detail lives in the breakdown file, never inline in SEQUENCE.md.
5. **Action verbs in the breakdown.** "Create", "Add", "Extract" — not "Consider", "Look into".

## Path Resolution

Resolve paths using the standard order:

1. Read `.session-flow.json` for `paths.todo`, `paths.tasks`, `paths.sequence`.
2. If missing, detect `todo/`, `_devdocs/todo/`, `docs/todo/`; the sequence file is `{todo}/SEQUENCE.md` and breakdowns live in `{todo}/tasks/`.
3. If nothing is found, suggest running `/session-init` and stop.

## The Sequence Format

`SEQUENCE.md` is a flat, roughly priority-ordered list of one-line entries:

```
- [ ] SEQ-007 P2: Add rate limiting to the API → todo/tasks/0007-add-rate-limit.md
```

| Marker | Meaning |
|--------|---------|
| `[ ]` | Open |
| `[x]` | Done |
| `(needs breakdown)` (trailing) | Captured but not yet researched/linked |

The link target is **either** a per-task breakdown file (`todo/tasks/NNNN-slug.md`, the default) **or** an anchor into a `session-task-planning` phase file (`todo/2026-06-03-feature.md#NA-1`) for multi-task work.

## Modes

Pick the mode based on the task's size and how ready it is.

### Mode A — Full (default)

The task is well-understood and session-sized (1-5 files). Write a complete breakdown now.

1. Choose the next id (e.g. `SEQ-007`). The breakdown filename reuses that same number padded to 4 digits with a kebab-case slug: `SEQ-007` → `0007-add-rate-limit.md`.
2. Write `{tasks}/NNNN-slug.md` using the breakdown template below.
3. Append a linked entry to `SEQUENCE.md`.

### Mode B — Multi-task

The work spans many files / multiple independent outcomes. Don't cram it into one breakdown.

1. Hand off to `/session-task-planning` to produce a phase file in `todo/` with dependency tags.
2. Append a sequence entry linking to that phase file and the first task anchor (e.g. `→ todo/2026-06-03-feature.md#1A-1`).

### Mode C — Capture

The user just wants it recorded; research/breakdown comes later (via `/session-groom`).

1. Choose the next `SEQ-NNN` id.
2. Append a one-liner with a trailing `(needs breakdown)` and no link:
   `- [ ] SEQ-009 P3: Investigate caching layer (needs breakdown)`

When unsure which mode, ask the user one question: "Quick capture, full breakdown now, or is this big enough to plan as multiple tasks?"

## Breakdown Template

Per-task breakdown files reuse the `session-task-planning` task template, wrapped with a small header. Write it as a self-contained, bite-sized prompt an agent (e.g. Opus) can execute without extra context.

```markdown
# SEQ-NNN: [Title]

**Status**: [ ]
**Priority**: P[1-3]
**Sequence**: SEQUENCE.md
**Plan**: [optional path to plans/... if derived from a plan]
**Research**: [optional path to research/...]

## Task

**Files**: `path/to/file.ext`, `path/to/other.ext:100-200`

**Instructions**:
- Read [reference] first
- Step 1 (action verb)
- Step 2 (action verb)

**Accept**: [Observable outcome that proves completion]

**Test**: `[exact command to verify]`
```

## Workflow

1. Resolve paths (config → detect → suggest init).
2. Determine the next `SEQ-NNN` id by scanning `SEQUENCE.md`.
3. Pick the mode (A/B/C).
4. For A: write the breakdown file; for B: invoke task-planning; for C: skip the breakdown.
5. Append exactly one entry to `SEQUENCE.md`.
6. Report: the new id, the entry line, and the breakdown path (or that it needs grooming).

## Anti-Patterns

**Vague breakdown:**
- BAD: "Improve the API" with no Files/Test
- GOOD: "Add token-bucket middleware to `src/api/middleware.py`; `pytest tests/api/test_rate_limit.py`"

**Cramming a refactor into one breakdown:**
- BAD: "Rewrite the backend" as a single per-task file
- GOOD: Use Mode B → `/session-task-planning`

Chain context: see `references/workflow-overview.md`.
