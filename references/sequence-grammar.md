# Sequence Grammar

`SEQUENCE.md` is **generated output**. `session-flow.py render` writes it from the work root, and
nothing else writes it. This document describes what the runtime emits, so that a reader — a person,
session-scribe's flows, the ops portfolio script — can parse a line and know which record field it
came from.

It is not an input format. To change an entry, change the work item through the runtime
([work-item-contract.md](work-item-contract.md)); anything typed into the generated file is lost at
the next `render` and was never read in between. Hand-editing is not a supported path, and there is
no second one to fall back to.

## The marker table

The sequence is a flat, priority-ordered list of one-line entries, one per work item:

```
- [ ] SEQ-007 P2: Add rate limiting to the API → work/seq-007/tasks/_index.md
```

| Token | Emitted for |
|-------|-------------|
| `[ ]` | Lifecycle `captured`, `accepted`, `active`, or `blocked` |
| `[x]` | Lifecycle `done` |
| `[DEFERRED]` (in the checkbox slot) | Lifecycle `deferred` or `cancelled` — the identity stays taken |
| `SEQ-NNN` | The record's immutable `seq` |
| `P1`/`P2`/`P3` | Its `priority`; entries sort by `order`, then identity |
| `[auto]` (after the priority) | `provenance.auto` — a skill enqueued it, not the user |
| ` ⇄ <url>` (before the trailing token) | One `annotations` entry: this item and that external item are the same work |
| ` → <link>` (trailing) | `links.breakdown`, plus `#anchor` when the link carries one. Whatever the record holds: the item's own task view, or a historical path preserved by import |
| `(needs breakdown)` (trailing) | `needs_breakdown`, when no breakdown link exists |

Comment lines beneath an entry are the record's `notes`, re-emitted in order.

**The open marker is lossy, deliberately.** `captured`, `accepted`, `active`, and `blocked` all
render `[ ]`, so an open checkbox tells you an item is not finished and nothing more. It is not
eligibility: capture grants no implementation permission, and a breakdown link confers none either.
`select` is what answers whether an item can be worked, and it returns the reasons with the answer.

## One trailing status token

`render` emits at most one trailing token — the ` → <link>` or the `(needs breakdown)` marker, never
both and never a third species.

An external reader parses an entry by stripping exactly one trailing token and reading the ` ⇄ `
annotations from the tail of what remains. A second, unknown tag would block that strip and hide
every annotation behind it. That is why nothing else goes at the end of a line, and why a note is
emitted as a comment line below the entry rather than appended to it.

Position is load-bearing in both directions: an annotation after the link would make the link path
unresolvable, and an annotation after the trailing token would be unfindable. Both resolve to one
rule the renderer follows — annotations go immediately before the trailing token, or at end of line
when the entry has neither.

## The ` ⇄ <url>` source key

` ⇄ <url>` records that this entry and that external item are the same work. Zero or more per line,
each dispatched on its hostname by whoever reads it, never on position.

**Why it is emitted.** A second importer must be able to see the item is already tracked.
session-scribe's `/scribe-pull` imports GitHub issues and excludes any candidate whose URL already
appears as an annotation; without the key it imports the issue a second time under a second
identity, after which the mirror files a third item for the duplicate. Reading the key therefore
comes before capturing: a capture path that knows a URL greps the existing annotations before
allocating identity, and treats a hit as already-captured work. The record keeps the same fact as
`source` and `capture_id`; the view carries it for readers that have only the file.

**Titles are not a fallback.** Capture rewrites a raw issue title into task phrasing, so an entry's
title never matches its source's, and near-matches across unrelated entries do. No URL, no dedup —
which is why a caller that knows the URL must pass it, and why nobody may invent one to fill the
slot.

## The `[auto]` marker

`[auto]`, rendered immediately after the priority, says a skill captured the entry on the user's
behalf rather than the user asking for it:

```
- [ ] SEQ-011 P3 [auto]: Retry failed webhook deliveries → work/seq-011/tasks/_index.md
```

Nothing else about the entry changes. The marker exists so an unattended capture is visible as one:
it is the veto handle that buys propose-don't-execute without asking the user to approve every item
up front. It records provenance and is never authority — an `[auto]` item is as unexecutable as any
other captured item until an authority accepts it.

Consumers: `select` never lets `[auto]` outrank a manual item of the same priority; `/session-groom`
grooms marked items normally but reports them separately; `/session-status` counts them.

## `[DEFERRED]` and identities that are never reused

`[DEFERRED]` retires an item without doing it, and its identity stays taken. Nothing is ever reused,
including the identity of a reservation whose operation crashed.

Allocation does not read this file. The runtime reserves the next `SEQ` under the work-root lock,
against both the retained item directories and the `.state/tombstones` index, and writes the
reservation durably before the record exists. Scanning the sequence view for the highest identity is
not how an id is minted and would miss a reservation that has not rendered yet.

## Coordination: one root, one coordinator

The generated view has no coordination role. It is the work root that is coordinated, and the
contract is this:

- **One authoritative local root, one coordinator at a time.** Several agents may execute
  independent tasks, but every state transition is serialized through the root lock.
- **The lock is a directory,** `.state/lock/`, taken by exclusive creation and owned by a recorded
  host, coordinator, pid, and token. Only the matching token releases it.
- **An expired timestamp never releases a lock.** Recovery inspects owner liveness and the actual
  state before an explicit takeover, and a takeover refuses while prepared operations remain — run
  `reconcile` first.
- **Every mutation is journalled.** A prepared operation records before/after content hashes, the
  records are replaced, the operation is marked applied, the views are regenerated, and the work
  root is committed. Retrying an applied operation returns its prior result; reusing its id with a
  different payload fails. A crash leaves a reconcilable operation, never an instruction to repeat
  its effects.
- **The lock serializes participating local writers only.** It cannot stop another permitted tool,
  or an editor on the Windows side, from writing into the work root — one more reason a hand edit to
  a generated file is not an input. Network or cloud-synchronized roots, editing one root from
  another operating system, and multi-host mutation are unsupported
  ([runtime-integration.md](runtime-integration.md)).

## HTML comments for everything else

Anything that does not fit on the entry line is emitted below it as an HTML comment, from the
record's `notes`:

```
<!-- session-flow: SEQ-NNN escalated to research-design YYYY-MM-DD -->
```

Comment lines are invisible to every `SEQUENCE.md` parser, so a note costs a reader nothing and a
parser nothing. The escalation line above is the format `/session-groom` writes into the record and
reads back from the view: an item carrying that note is waiting on a research-design session and is
skipped by the next groom pass. A comment typed straight into the generated file is not a note — it
disappears at the next `render`.
