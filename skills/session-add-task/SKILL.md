---
name: session-add-task
description: Capture a new work item into the project's work root with its original request, interpretation and provenance. Use when something surfaces that should be done later — a bug, an optimization, a follow-up — and you want it recorded so it can be accepted and picked up. Produces a work item in the captured state, identity allocated by the runtime, and the regenerated sequence entry that shows it. Triggers on "/session-add-task" or when user says "add a task", "capture this for later", "put this on the backlog", or "remember to do X".
---

# Session Add Task

Capture work into the work root so it can be accepted later and picked up with "implement the next task".

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Capture grants no implementation permission.** A captured item is not executable, and neither a linked breakdown nor a written `Files` field makes it so. `select` refuses a `captured` item by name; only an acceptance naming the current scope fingerprint makes it eligible. Never implement what you have just captured because you also happen to know how.
2. **The runtime allocates identity.** Never pick a `SEQ-NNN` yourself and never scan the sequence for the next free number. `transition` reserves the identity under the root lock against retained homes and tombstones, so a retired id stays taken and two concurrent captures cannot collide.
3. **The originator's words are preserved verbatim, separately from your reading of them.** `original_request` holds what was actually asked, unedited; the interpretation goes in the body under its own heading. A later session must be able to see that you misread the request.
4. **Every capture carries provenance.** Who asked, when, whether a skill enqueued it, and — when the work came from somewhere addressable — the source URL and the capture id that deduplicate it.
5. **The sequence is generated output.** Never append to it, never edit it, never read it as the authority for what exists. `render` writes it from the work root, and a line typed there is lost at the next render.
6. **Keep it compact.** A small clear item is `intent.md` and nothing else. No `spec.md`, no `plan.md`, no `tasks/` directory, no empty optional section.
7. **Action verbs, and never cite a path that does not exist.** "Create", "Add", "Extract" — not "Consider", "Look into". Existence-check every path you write into `Files` or `Test` (`test -f`, or `test -d` for a glob's root) before capturing it. The one exception is a path the item's own instructions create — say so inline (`new file`).

## Path Resolution

1. Resolve the runtime entrypoint by the one rule for this host — `${CLAUDE_PLUGIN_ROOT}` natively, the discovered installed location under Codex, the `session-flow-runtime.json` descriptor beside this `SKILL.md` for a standalone copy (`references/runtime-integration.md`). Use absolute paths for both the interpreter and the entrypoint.
2. Read `.session-flow.json` for `paths.work` and `paths.sequence`. The runtime resolves both itself from `--project-root`; you read them to find the records.
3. Confirm the root answers before writing anything:

   ```bash
   python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
   ```

   A named error, a missing work root, or a missing `namespace.json` means stop and report it. There is no hand-editing path: mutation fails closed.

## The Generated Sequence

`render` writes one line per work item into `paths.sequence`, from the record's own fields:

```
- [ ] SEQ-007 P2: Add rate limiting to the API ⇄ https://github.com/owner/repo/issues/42 (needs breakdown)
```

| Token | Rendered from |
|-------|---------------|
| `[ ]` open · `[x]` done · `[DEFERRED]` retired | `lifecycle` |
| `SEQ-NNN` | `seq`, allocated at capture |
| `P1`/`P2`/`P3` | `priority` |
| `[auto]` after the priority | `provenance.auto` |
| ` ⇄ <url>` before the trailing token | each entry of `annotations` |
| trailing ` → <link>` | `links.breakdown`, plus `links.anchor` |
| trailing `(needs breakdown)` | `needs_breakdown` |
| an `<!-- … -->` line below the entry | each entry of `notes` |

An entry ends in **exactly one trailing status token** — the link or the `(needs breakdown)` marker, never both — because external parsers strip exactly one, and an unknown trailing tag hides the annotations behind it. Anything that does not fit goes below the line as a `notes` comment. Full grammar and cross-writer contract: `references/sequence-grammar.md`. Record fields and lifecycle: `references/work-item-contract.md`.

## Provenance

`provenance.auto` renders as `[auto]` and says a skill enqueued the entry on the user's behalf. It is off by default — a user invoking `/session-add-task` produces an unmarked entry — and set only when the caller is a skill enqueuing without the user having seen the item, `/session-gatekeeper` triage being the one shipped caller. `[auto]` records **provenance and is the veto handle**: a marked entry sits in the sequence and can be struck on sight. It is never authority, and it never makes an item eligible.

`annotations` renders as ` ⇄ <url>` and says this item and that external item are the same work. Never invent one: it is the only key another writer can dedup on, because this skill rewrites raw issue titles into task phrasing and the titles never match. Store the same URL in `source` and a stable key in `capture_id` (`github:owner/repo#42`, `notion:<page-id>`), so a second importer can match on the record rather than on a rendered line.

## Modes

Pick the mode based on the item's size and how ready it is.

### Mode A — Compact (default)

The work is well-understood and session-sized (1-5 files). One record carries all of it: the request, your reading of it, and the instructions an agent will execute. The body carries `Files`, `Instructions`, `Accept` and `Test`; the scope region carries the acceptance-bearing behaviour. Set no `needs_breakdown`.

### Mode B — Multi-task

The work spans many files or several independent outcomes. Capture the item here, then hand off to `/session-task-planning`, which attaches the expanded artifacts to this same identity. Do not cram it into one record and do not allocate a second one.

### Mode C — Capture only

The user just wants it recorded; research comes later, via `/session-groom`. Capture the request and the provenance, set `"needs_breakdown": true`, and write no instructions you have not verified.

When unsure which mode, ask the user one question: "Quick capture, full instructions now, or is this big enough to plan as multiple tasks?"

## The Capture Payload

Write the payload to a file and pass it with `--input`. No option accepts free text, and nothing in it is executed.

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" transition --input "$PAYLOAD"
```

```json
{
  "operation": "add-task-<unique-token>",
  "coordinator": "session-add-task",
  "changes": [
    {
      "new": true,
      "scope": "The behaviour that would make this done, in the requester's terms.",
      "body": "## Original request\n\n> verbatim\n\n## Interpreted intent\n\nWhat you understood.\n\n**Files**: `path/to/file.ext`\n\n**Instructions**:\n- Step 1 (action verb)\n\n**Accept**: observable outcome\n\n**Test**: `exact command`\n",
      "metadata": {
        "title": "One line, task phrasing",
        "lifecycle": "captured",
        "priority": "P3",
        "original_request": "verbatim, unedited",
        "source": "https://github.com/owner/repo/issues/42",
        "capture_id": "github:owner/repo#42",
        "annotations": ["https://github.com/owner/repo/issues/42"],
        "provenance": {"origin": "user", "actor": "<who asked>", "captured_at": "<ISO-8601 UTC>", "auto": false},
        "needs_breakdown": true
      }
    }
  ]
}
```

`operation` is unique per capture: re-sending the same id with the same payload returns the first result instead of capturing twice, and re-sending it with a different payload is refused. Omit `source`, `capture_id` and `annotations` for something surfaced in conversation rather than filed anywhere — never invent a URL to fill the slot. Omit `needs_breakdown` in Mode A. Set `"auto": true` only when a skill is enqueuing on the user's behalf.

`Files` doubles as the **dispatch write boundary** — `/session-delegation` injects it as "you may only create or modify these paths" — so an incomplete field stalls the agent rather than widening its lane. It is a prompt-level constraint, not an enforced one.

## Workflow

1. Resolve the runtime and the paths; run `doctor`.
2. **If the item has a source URL, check it before capturing.** Grep the work root's `intent.md` files for the URL and the capture id — `grep -rl "<url>" "$WORK_ROOT"` — not only the generated sequence, because records are the authority. On a hit, stop: report the existing item's `SEQ-NNN` and capture nothing. This is the same exclusion session-scribe's `/scribe-pull` runs in the other direction, and the two checks together make the key symmetric between writers.
3. Pick the mode (A/B/C) and write the payload to a file.
4. Run `transition`. Read `result.reserved` for the allocated identity and `result.records[0].path` for the record.
5. For Mode B, hand the allocated identity to `/session-task-planning`.
6. Report: the allocated `SEQ-NNN`, the record path, the item's state (`captured`), and that acceptance is a separate decision the item does not yet have.

## Anti-Patterns

**Treating capture as approval:**
- BAD: "I've added SEQ-011 and started on it"
- GOOD: "Captured as SEQ-011. It is `captured`, not accepted — `select` will refuse it until someone accepts the scope."

**Choosing the id yourself:**
- BAD: scanning `SEQUENCE.md` for the highest number and adding one
- GOOD: let `transition` reserve it; the sequence is a rendering and a retired id it no longer shows is still taken

**Editing the sequence:**
- BAD: appending the new entry to `SEQUENCE.md` so it shows up immediately
- GOOD: `transition` re-renders it; a line typed there is lost at the next render

**Paraphrasing the request into the record:**
- BAD: `original_request: "user wants rate limiting"`
- GOOD: `original_request: "can we stop people hammering the API"`, with your reading of it under **Interpreted intent** — the gap between the two is the thing a later session needs to see

**Deduping by title instead of URL:**
- BAD: skipping the source check because "no existing item has this title"
- GOOD: grep the work root for the URL. This skill rewrites raw issue titles into task phrasing, so an item's title never matches its source's — and near-matches across unrelated items do. The URL is the only key.

Chain context: see `references/workflow-overview.md`.
