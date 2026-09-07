---
name: session-groom
description: Groom the backlog by researching captured work items that carry no verified breakdown and recording one against each. Use to keep the work root healthy — every item researched, verified, and ready to be accepted — especially for items captured as raw one-liners. Safe to run periodically via /loop. Triggers on "/session-groom" or when user says "groom the backlog", "prepare the sequence", "fill in the task breakdowns", or "tidy up SEQUENCE.md".
---

# Session Groom

Keep the backlog ready: research each unprepared work item, verify it, and record the breakdown on it.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Idempotent.** Running groom twice over a healthy backlog changes nothing. Only act on items marked `needs_breakdown`, items whose body carries no verified instructions, and items explicitly flagged for re-research.
2. **Verify before recording.** A breakdown goes on the record only after the work is confirmed feasible and grounded in the actual code — files exist, the approach is sound. Don't fabricate paths or tests.
3. **Grooming is not acceptance.** Clearing `needs_breakdown` prepares an item; it does not make it executable. `select` still refuses a `captured` item by name, and a verified breakdown confers no eligibility — acceptance is a separate decision by someone with the authority to make it. Never treat "I researched it and it's fine" as that decision.
4. **Never rewrite the scope region.** Instructions, files and tests go in the body, which is outside the fingerprint, so recording them leaves an existing acceptance intact. If the research shows the accepted scope itself is wrong, that is an escalation (Step 4), not a reword.
5. **Gate the big ones.** If an item turns out to be a significant or architecture-touching change, do not record a breakdown for it — escalate to a cowork `/session-research-design` session and leave a note on the record.
6. **Never start implementation.** Groom prepares; it does not write app code. Execution is `/session-next`'s job.
7. **The sequence is generated.** Never edit `paths.sequence`. Change the record and let the runtime re-render; a line typed there is lost at the next render.
8. **Report a summary.** After a pass, list what was groomed, what was escalated, and what was skipped.

## Path Resolution

1. Resolve the runtime entrypoint by the one rule for this host — `${CLAUDE_PLUGIN_ROOT}` natively, the discovered installed location under Codex, the `session-flow-runtime.json` descriptor beside this `SKILL.md` for a standalone copy (`references/runtime-integration.md`).
2. Read `.session-flow.json` for `paths.work`; the records live one directory per item beneath it.
3. Confirm the root answers before changing anything:

   ```bash
   python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
   ```

   A named error, a missing work root, or a missing `namespace.json` means report it and stop. There is no hand-editing path.

## Workflow

### Step 1: Find the unprepared items

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" select
```

`select` returns every item it considered with its lifecycle and the reasons it is or is not eligible. The groom targets are the items whose reasons include `the item is still marked (needs breakdown)`. Read each one's record for the rest:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-NNN
```

Skip `done`, `deferred` and `cancelled` items, items whose body already carries verified `Files` / `Instructions` / `Accept` / `Test`, and items carrying an escalation note (`notes` holding `<!-- session-flow: SEQ-NNN escalated to research-design … -->`) — those are waiting on a `/session-research-design` session, and re-researching them each pass breaks idempotence.

An item may carry `provenance.auto`, rendering as `[auto]`, meaning a skill enqueued it — `/session-gatekeeper` triage, typically. It is a normal groom target: same research, same verification bar, same escalation rules. Note which items were marked so Step 5 can report them.

### Step 2: Research and verify each item

For each unprepared item:

1. Read `original_request` and the interpreted intent before the code. The gap between them is where a groom pass finds the real work, and neither is yours to rewrite.
2. Read the relevant code to confirm what the item touches and whether it is feasible. Existence-check every path you are about to write (`test -f`, `test -d` for a glob's root).
3. Judge the scope:
   - **Session-sized and clear** → record the breakdown (Step 3).
   - **Significant, divergent, or unclear** → escalate (Step 4).

### Step 3: Record the breakdown

One compact record holds it: the breakdown goes in the item's own body, not in a companion file. Write the payload and apply it.

```json
{
  "operation": "groom-<unique-token>",
  "coordinator": "session-groom",
  "changes": [
    {
      "seq": "SEQ-NNN",
      "expect_revision": 3,
      "metadata": {"needs_breakdown": null},
      "body": "## Original request\n\n> unchanged, verbatim\n\n## Interpreted intent\n\nunchanged\n\n**Files**: `src/api/middleware.py`\n\n**Instructions**:\n- Step 1 (action verb)\n\n**Accept**: observable outcome\n\n**Test**: `exact command`\n"
    }
  ]
}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" transition --input "$PAYLOAD"
```

`expect_revision` is the revision `show` just reported; a mismatch is refused as `stale-revision`, which is the pass finding that someone else edited the record while you were researching. Re-read it and rebuild the change. `"needs_breakdown": null` removes the field, so the rendered entry drops its `(needs breakdown)` token; carry the whole body forward, because `body` replaces rather than appends. The transition re-renders the sequence and commits the work root itself — run nothing else afterwards.

The ` ⇄ <url>` annotations and the `[auto]` marker are rendered from `annotations` and `provenance.auto`, which this payload does not touch, so they survive the rewrite by construction. Do not restate them in the payload. Why they matter and what it costs to lose one: `references/sequence-grammar.md`.

Work that spans several files or independent outcomes does not become a longer body. Escalate it, or hand the identity to `/session-task-planning`, which attaches expanded artifacts to that same `SEQ-NNN`.

### Step 4: Escalate when needed

If the item is too big or diverges from the app's direction, do not record a breakdown. Instead:

- **Leave `needs_breakdown` set.** The item is not prepared, and the rendered entry should keep saying so.
- Add the escalation to the record's `notes`, which renders as its own comment line below the entry:
  `{"metadata": {"notes": ["<!-- session-flow: SEQ-NNN escalated to research-design YYYY-MM-DD -->"]}}`
  The patch replaces the list, so carry any note already on the record forward with it.
- Recommend `/session-research-design` for a cowork session with the user.

### Step 5: Report

Summarize: items groomed, items escalated, items skipped (already prepared).

Call out provenance: state how many of the groomed items were `[auto]`, and name them. An unattended intake feed is exactly the thing that accumulates unnoticed, so a groom pass is the natural place for the user to see what a bot added since they last looked. State also that none of the groomed items became eligible: they are prepared, not accepted.

## Running Periodically with /loop

Groom is designed to run unattended on an interval:

```
/loop 30m /session-groom
```

Each tick prepares whatever was captured since the last one. Because grooming never accepts an item and anything significant is escalated rather than auto-actioned, periodic grooming is safe — it never silently commits to a large change, and it cannot make one executable.

Chain context: see `references/workflow-overview.md`.
