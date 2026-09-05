---
name: session-groom
description: Groom the task sequence (backlog) by researching un-broken-down entries and attaching ready-to-execute breakdowns. Use to keep SEQUENCE.md healthy — every entry researched, verified, and linked to a breakdown — especially for items added as raw one-liners. Safe to run periodically via /loop. Triggers on "/session-groom" or when user says "groom the backlog", "prepare the sequence", "fill in the task breakdowns", or "tidy up SEQUENCE.md".
---

# Session Groom

Keep the sequence backlog ready: research each un-prepared entry, verify it, and attach a breakdown.

Open with one sentence saying what you are about to do and what it will produce.

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

Skip entries that are `[x]` done or already linked to an existing breakdown. Also skip entries with an escalation comment on the line below (`<!-- session-flow: SEQ-NNN escalated to research-design … -->`) — they are waiting on a `/session-research-design` session, and re-researching them each pass breaks idempotence (Non-Negotiable 1).

An entry may carry `[auto]` after its priority (`- [ ] SEQ-011 P3 [auto]: …`), meaning a bot enqueued it — `/session-gatekeeper` triage, typically. It is a normal groom target: same research, same verification bar, same escalation rules. Note which entries were marked so Step 5 can report them; entries without the marker are unaffected.

### Step 2: Research and verify each entry

For each un-prepared entry:
1. Read the relevant code to confirm what the task touches and whether it's feasible.
2. Judge the scope:
   - **Session-sized & clear** → proceed to write a breakdown (Step 3).
   - **Significant / divergent / unclear** → escalate (Step 4).

### Step 3: Write the breakdown

Reuse the `session-add-task` / `session-task-planning` breakdown template (header + Files / Instructions / Accept / Test). Files entries may be exact paths or directory globs (`src/lib/governor/**`), and the field doubles as the **dispatch write boundary** delegation injects into agent payloads — list everything the task must touch. Write it to `{tasks}/NNNN-slug.md`, where `NNNN` is the entry's existing `SEQ-NNN` number (zero-padded) so the file and entry stay aligned. Never overwrite an existing file. Then update the sequence entry to drop `(needs breakdown)` and add the `→` link.

**Preserve any ` ⇄ <url>` annotations on the line, in place.** They sit immediately before the trailing status token, so swapping `(needs breakdown)` for the `→` link leaves them exactly where they belong — but you are rewriting that region of the line, and dropping one is silent. Why the annotation matters and what it costs to lose: `references/sequence-grammar.md`.

### Step 4: Escalate when needed

If the entry is too big or diverges from the app's direction, do not break it down. Instead:
- **Leave the entry line untouched.** Do not append a `(needs research-design)` tag to it: an entry carries exactly one trailing status token, and a second, unknown tag hides the ` ⇄ ` annotations behind it (`references/sequence-grammar.md`).
- Record the escalation on its own line **immediately below** the entry, as an HTML comment:
  `<!-- session-flow: SEQ-NNN escalated to research-design YYYY-MM-DD -->`
- Recommend `/session-research-design` for a cowork session with the user.

### Step 5: Report

Summarize: entries groomed (with new breakdown paths), entries escalated, entries skipped (already healthy).

Call out provenance: state how many of the groomed entries were `[auto]`, and name them. An unattended intake feed is exactly the thing that accumulates unnoticed, so a groom pass is the natural place for the user to see what a bot added since they last looked.

## Running Periodically with /loop

Groom is designed to run unattended on an interval:

```
/loop 30m /session-groom
```

Each tick scans for new raw one-liners (e.g. ones a user pasted in) and prepares them. Because anything significant is escalated rather than auto-actioned, periodic grooming is safe — it never silently commits to a large change.

Chain context: see `references/workflow-overview.md`.
