---
name: session-groom
description: Groom the task sequence (backlog) by researching un-broken-down entries and attaching ready-to-execute breakdowns. Use to keep SEQUENCE.md healthy — every entry researched, verified, and linked to a breakdown — especially for items added as raw one-liners. Safe to run periodically via /loop. Triggers on "/session-groom" or when user says "groom the backlog", "prepare the sequence", "fill in the task breakdowns", or "tidy up SEQUENCE.md".
---

# Session Groom

Keep the sequence backlog ready: research each un-prepared entry, verify it, and attach a breakdown.

**Announce:** "Using session-groom to research and break down the open sequence entries."

## Non-Negotiables

1. **Idempotent.** Running groom twice over a healthy sequence changes nothing. Only act on entries that are `(needs breakdown)`, have a dangling/missing link, or are explicitly flagged for re-research.
2. **Verify before linking.** A breakdown is only attached after the task is confirmed feasible and grounded in the actual code (files exist, the approach is sound). Don't fabricate paths or tests.
3. **Gate the big ones.** If an entry turns out to be a significant or architecture-touching change, do not auto-break-it-down — escalate to a cowork `/session-research-design` session and leave a note on the entry.
4. **Never start implementation.** Groom prepares breakdowns; it does not write app code. Execution is `/session-next`'s job.
5. **Report a summary.** After a pass, list what was groomed, what was escalated, and what was skipped.

## Path Resolution

1. Read `.session-flow.json` for `paths.sequence`, `paths.tasks`, `paths.todo`.
2. If missing, detect `{todo}/SEQUENCE.md` and `{todo}/tasks/`.
3. If no sequence file exists, report nothing to groom and suggest `/session-add-task` or `/session-init`.

## Workflow

### Step 1: Scan for un-prepared entries

Read `SEQUENCE.md`. Collect entries that need work:
- Trailing `(needs breakdown)`.
- A link whose target file is missing (dangling).
- No link at all on an open `[ ]` entry.

Skip entries that are `[x]` done or already linked to an existing breakdown.

### Step 2: Research and verify each entry

For each un-prepared entry:
1. Read the relevant code to confirm what the task touches and whether it's feasible.
2. Judge the scope:
   - **Session-sized & clear** → proceed to write a breakdown (Step 3).
   - **Significant / divergent / unclear** → escalate (Step 4).

### Step 3: Write the breakdown

Reuse the `session-add-task` / `session-task-planning` breakdown template (header + Files / Instructions / Accept / Test). Write it to `{tasks}/NNNN-slug.md`, where `NNNN` is the entry's existing `SEQ-NNN` number (zero-padded) so the file and entry stay aligned. Never overwrite an existing file. Then update the sequence entry to drop `(needs breakdown)` and add the `→` link.

### Step 4: Escalate when needed

If the entry is too big or diverges from the app's direction, do not break it down. Instead:
- Leave the entry as-is and annotate it (e.g. `(needs research-design)`).
- Recommend `/session-research-design` for a cowork session with the user.

### Step 5: Report

Summarize: entries groomed (with new breakdown paths), entries escalated, entries skipped (already healthy).

## Running Periodically with /loop

Groom is designed to run unattended on an interval:

```
/loop 30m /session-groom
```

Each tick scans for new raw one-liners (e.g. ones a user pasted in) and prepares them. Because anything significant is escalated rather than auto-actioned, periodic grooming is safe — it never silently commits to a large change.

## Anti-Patterns

**Re-grooming healthy entries:**
- BAD: Rewriting existing breakdowns on every pass
- GOOD: Touch only `(needs breakdown)` / dangling / unlinked entries

**Fabricated breakdowns:**
- BAD: Inventing file paths and a test command without reading the code
- GOOD: Verify files exist and the approach is real before linking

**Auto-planning a refactor:**
- BAD: Quietly breaking a "rewrite the data layer" one-liner into tasks
- GOOD: Escalate to `/session-research-design`

**Implementing during groom:**
- BAD: Starting to write the fix while grooming
- GOOD: Prepare the breakdown; let `/session-next` execute it

Chain context: see `references/workflow-overview.md`.
