# SEQ-009: Gatekeeper and add-task consult existing ` ⇄ ` annotations before enqueueing

**Status**: [x]
**Priority**: P2
**Sequence**: SEQUENCE.md
**Research**: ../session-scribe/_devdocs/research/2026-08-14-three-plugin-alignment.md (§2 conflict C1, §3.4)

## Context

The ` ⇄ <url>` annotation is the only dedup key between the four writers of `SEQUENCE.md`.
session-scribe reads it before writing (its `/scribe-pull` excludes any candidate whose URL
already appears); session-flow's gatekeeper and add-task **write** the key but neither skill
checks existing annotations before appending an entry. Two concrete double-intake paths result:
a reopened, previously-imported issue re-triages in CI (ops-triage skips only `scribe:mirror`
and `ops-dashboard`) and is enqueued a second time under a second `SEQ-NNN`; and an issue
labelled `scribe:ready` that triage *escalates* stays a `/scribe-pull` candidate, so the later
dashboard box-tick enqueues work the import already filed.

## Task

**Files**: `skills/session-gatekeeper/SKILL.md`, `skills/session-add-task/SKILL.md`

**Instructions**:
- Read the alignment review section cited above first.
- In `session-add-task`'s workflow: when the caller passes a source URL, scan `SEQUENCE.md` for
  that URL among existing ` ⇄ ` annotations **before** allocating an id. On a hit, stop, report
  the existing entry's `SEQ-NNN`, and append nothing. State that this is the same exclusion
  `/scribe-pull` runs in the other direction, and that together they make the key symmetric.
- In `session-gatekeeper`'s enqueue path: check the issue URL against existing annotations before
  routing to add-task; treat a hit as already-enqueued (name the entry in the run record, skip).
  Name the two double-intake paths above as the reason.
- Add an anti-pattern to both: falling back to title matching (titles are rewritten into task
  phrasing; the URL is the only key).

**Accept**: gatekeeper triaging an issue whose URL already appears as a ` ⇄ ` annotation produces
no new `SEQUENCE.md` entry; add-task invoked with a source URL already present refuses and names
the existing id.

**Test**: `grep -l 'already appears' skills/session-gatekeeper/SKILL.md skills/session-add-task/SKILL.md | wc -l` — expect `2`, with the exclusion instruction present in both workflow sections.
