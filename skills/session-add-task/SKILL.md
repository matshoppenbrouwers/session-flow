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
6. **Never cite a path that does not exist.** Existence-check every path in `Files` and `Test` (`test -f`, or `test -d` for a glob's root) before writing the breakdown. The one exception is a path the task's own Instructions create — say so inline (`new file`). A test path inferred from a naming convention the project has abandoned costs the implementer a failed collection run, not a minute of grepping.

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
| `[auto]` (after the priority) | Enqueued by a bot, not by the user — see Provenance below |
| ` ⇄ <url>` (before the trailing link) | This entry and that external item are the same work — see Provenance below |
| `(needs breakdown)` (trailing) | Captured but not yet researched/linked |

The link target is **either** a per-task breakdown file (`todo/tasks/NNNN-slug.md`, the default) **or** an anchor into a `session-task-planning` phase file (`todo/2026-06-03-feature.md#NA-1`) for multi-task work.

## Provenance

Two independent markers, answering two different questions. `[auto]` says **who** put the entry in the
file; ` ⇄ <url>` says **where the work came from**. An entry may carry either, both, or neither — a
gatekeeper enqueue from a GitHub issue carries both.

### Who added it — the `[auto]` marker

Add-task takes an optional **auto-provenance flag**. It is off by default: a user invoking `/session-add-task` produces an unmarked entry. Set it only when the caller is a skill enqueuing on the user's behalf without the user having seen the item — `/session-gatekeeper` triage is the one shipped caller.

When set, the marker renders immediately after the priority:

```
- [ ] SEQ-011 P3 [auto]: Retry failed webhook deliveries → todo/tasks/0011-retry-webhooks.md
```

Nothing else about the entry changes — same id rules, same breakdown, same link. The marker exists so an unattended enqueue is visible as one, and so the user can veto it on sight instead of approving every item up front.

Consumers: `/session-groom` grooms marked entries normally but reports them separately; `/session-next` never lets `[auto]` outrank a manual entry of the same priority; `/session-status` counts them.

**Before relying on this with session-scribe:** scribe parses `SEQUENCE.md` by file-format convention, not shared code. `[auto]` changes the line format it reads. Verify scribe's parser against a marked line before trusting the Notion mirror.

### Where it came from — the ` ⇄ <url>` source key

Add-task also takes an optional **source URL**: the external item this task was captured from — a GitHub issue, a Notion task, a tracker ticket. When the caller passes one, render it as ` ⇄ <url>` **immediately before the trailing ` → <breakdown-link>`**:

```
- [ ] SEQ-011 P3 [auto]: Retry failed webhook deliveries ⇄ https://github.com/owner/repo/issues/42 → todo/tasks/0011-retry-webhooks.md
```

Zero or more per line, each dispatched on its hostname by whoever reads it, never on position. Presence means one thing: **this line and that URL are the same work.**

**Why record it.** A second importer must be able to see the item is already in the file. session-scribe's `/scribe-pull` imports GitHub issues into `SEQUENCE.md`, and it dedups by excluding any candidate whose URL already appears as a ` ⇄ ` annotation. If the gatekeeper enqueues an issue in CI and writes no annotation, that issue is invisible to the check and gets imported a second time under a second `SEQ-NNN` — after which scribe's mirror files a *third* item for the duplicate. The same key also stops the mirror from re-filing an entry whose issue already exists.

**It is the only key between writers.** Do not fall back to matching on title text: this skill rewrites a raw issue title into task phrasing, so the two never match, and near-matches across unrelated entries do. No URL, no dedup — which is why a caller that knows the URL must pass it.

**Position is load-bearing, in both directions.** `/session-status`, `/session-groom` and `/session-next` all read the breakdown link as *the text after the last ` → `* and open it as a path. An annotation appended after the link makes that path `todo/tasks/0011-retry-webhooks.md ⇄ https://…`, which resolves to nothing — so a fully-groomed entry reads as dangling and gets re-groomed or skipped. And a reader looking for the annotation scans the tail of the line once that trailing token is stripped, so an annotation placed after the token is unfindable.

Both constraints resolve to one rule: **the annotation goes immediately before the entry's trailing status token** — the ` → <breakdown-link>` on a groomed entry, or the `(needs breakdown)` marker on an ungroomed one (mode C), or end-of-line if it has neither. An entry has one such token or the other, never both.

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
   With a source URL, the annotation goes before the marker:
   `- [ ] SEQ-009 P3: Investigate caching layer ⇄ https://github.com/owner/repo/issues/42 (needs breakdown)`

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

**Files entries** may be exact paths (`src/api/routes.py:100-200`) or directory globs (`src/lib/governor/**`) when the task owns a whole subtree. Files also doubles as the **dispatch write boundary** — `/session-delegation` injects it as "you may only create or modify these paths" — so an incomplete field stalls the agent rather than widening its lane.

## Workflow

1. Resolve paths (config → detect → suggest init).
2. Determine the next `SEQ-NNN` id by scanning `SEQUENCE.md`.
3. Pick the mode (A/B/C).
4. For A: write the breakdown file; for B: invoke task-planning; for C: skip the breakdown.
5. Append exactly one entry to `SEQUENCE.md`, rendering `[auto]` after the priority if the caller set the auto-provenance flag, and ` ⇄ <url>` before the trailing status token if the caller passed a source URL.
6. Report: the new id, the entry line, and the breakdown path (or that it needs grooming).

## Anti-Patterns

**Vague breakdown:**
- BAD: "Improve the API" with no Files/Test
- GOOD: "Add token-bucket middleware to `src/api/middleware.py`; `pytest tests/api/test_rate_limit.py`"

**Cramming a refactor into one breakdown:**
- BAD: "Rewrite the backend" as a single per-task file
- GOOD: Use Mode B → `/session-task-planning`

**Dropping the source URL because the title says where it came from:**
- BAD: `- [ ] SEQ-011 P3 [auto]: Retry failed webhook deliveries (from issue #42) → todo/tasks/0011-retry-webhooks.md`
- GOOD: `- [ ] SEQ-011 P3 [auto]: Retry failed webhook deliveries ⇄ https://github.com/owner/repo/issues/42 → todo/tasks/0011-retry-webhooks.md` — a second importer greps for the URL, not for prose. `(from issue #42)` is readable by a human and invisible to the one check that prevents the item being enqueued twice

Chain context: see `references/workflow-overview.md`.
