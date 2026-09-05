# Sequence Grammar

The entry-line grammar of `SEQUENCE.md`, and the reasoning behind it. The rules themselves stay in
the skills that write the file — `/session-add-task`, `/session-gatekeeper`, `/session-groom` — so
each can state a rule in a line and point here for why it holds and what breaks without it.

## The marker table

`SEQUENCE.md` is a flat, roughly priority-ordered list of one-line entries:

```
- [ ] SEQ-007 P2: Add rate limiting to the API → todo/tasks/0007-add-rate-limit.md
```

| Marker | Meaning |
|--------|---------|
| `[ ]` | Open |
| `[x]` | Done |
| `[DEFERRED]` (in the checkbox slot) | Retired without being done — the id stays taken, and the id-allocation scan must count it |
| `[auto]` (after the priority) | Enqueued by a bot, not by the user |
| ` ⇄ <url>` (before the trailing status token) | This entry and that external item are the same work |
| `(needs breakdown)` (trailing) | Captured but not yet researched/linked |

The link target is **either** a per-task breakdown file (`todo/tasks/NNNN-slug.md`, the default)
**or** an anchor into a `session-task-planning` phase file (`todo/2026-06-03-feature.md#NA-1`) for
multi-task work.

This table is the whole entry-line grammar — every token any shipped writer (`/session-add-task`,
`/session-gatekeeper`, `/session-groom`, session-scribe's three flows) puts on an entry line.

## One trailing status token

An entry ends in exactly one trailing status token — the ` → <link>` or the `(needs breakdown)`
marker, never both, never a third species.

External readers parse an entry by stripping exactly one trailing token and reading the ` ⇄ `
annotations from the tail of what remains. A second, unknown tag blocks that strip and hides every
annotation behind it, which is how a `(needs research-design)` tag appended to a line silently
disables the dedup key described below. This is why an escalation or any other note goes on a
comment line beneath the entry rather than at the end of it.

## The ` ⇄ <url>` source key

` ⇄ <url>` records that this entry and that external item are the same work. Zero or more per line,
each dispatched on its hostname by whoever reads it, never on position.

**Why record it.** A second importer must be able to see the item is already in the file.
session-scribe's `/scribe-pull` imports GitHub issues into `SEQUENCE.md` and dedups by excluding any
candidate whose URL already appears as a ` ⇄ ` annotation. If `/session-gatekeeper` enqueues an
issue in CI and writes no annotation, that issue is invisible to the check and gets imported a
second time under a second `SEQ-NNN` — after which the mirror files a third item for the duplicate.
The same key stops the mirror from re-filing an entry whose issue already exists. Reading the key
therefore comes before writing it: a writer that knows a URL greps for it among the existing
annotations before allocating an id, and treats a hit as an already-enqueued item.

**Titles are not a fallback.** The capture skills rewrite a raw issue title into task phrasing, so
an entry's title never matches its source's, and near-matches across unrelated entries do. No URL,
no dedup — which is why a caller that knows the URL must pass it, and why nobody may invent one to
fill the slot.

**Position is load-bearing, in both directions.** `/session-status`, `/session-groom` and
`/session-next` all read the breakdown link as *the text after the last ` → `* and open it as a
path, so an annotation appended after the link makes that path
`todo/tasks/0011-retry-webhooks.md ⇄ https://…`, which resolves to nothing — a fully-groomed entry
then reads as dangling and gets re-groomed or skipped. And a reader looking for the annotation scans
the tail of the line once the trailing token is stripped, so an annotation placed after the token is
unfindable. Both constraints resolve to one rule: the annotation goes immediately before the entry's
trailing status token, or at end of line when the entry has neither token.

## The `[auto]` marker

`[auto]`, rendered immediately after the priority, says a skill enqueued the entry on the user's
behalf rather than the user asking for it:

```
- [ ] SEQ-011 P3 [auto]: Retry failed webhook deliveries → todo/tasks/0011-retry-webhooks.md
```

Nothing else about the entry changes — same id rules, same breakdown, same link. The marker exists
so an unattended enqueue is visible as one: it is the veto handle that buys propose-don't-execute
without asking the user to approve every item up front, since marked entries sit in the sequence and
can be struck on sight.

Consumers: `/session-groom` grooms marked entries normally but reports them separately;
`/session-next` never lets `[auto]` outrank a manual entry of the same priority; `/session-status`
counts them.

session-scribe parses `SEQUENCE.md` by file-format convention rather than shared code, so both
markers change the line format it reads. `[auto]` is verified against that parser, and the ` ⇄ `
convention is written down as a shared contract in its `scribe-tasks` skill, which is what makes it
safe to write either one from here.

## `[DEFERRED]` and the highest id ever

`[DEFERRED]` in the checkbox slot retires an entry without doing it, and its id stays taken. The
id-allocation scan reads every line carrying a `SEQ` id — open, done and deferred alike — because
the highest id ever used is the floor, not the highest open one: an active-only scan misses a
retired id and mints a collision.

## Id allocation is lock-free

Four writers append to the same file (`/session-add-task`, `/session-gatekeeper` in CI, and
session-scribe's `/scribe-pull` and `/scribe code`), and all allocate ids the same way: highest
existing id plus one, with no locking. Nothing in the format stops a concurrent CI enqueue and a
local import from minting the same id. What makes the scheme safe is operating discipline, not
mechanism: at most one scheduled writer per repo, and pull before any local edit to the sequence.
Both halves are load-bearing — enrolling a second bot writer on the same repo, or appending to a
stale local copy, reintroduces the collision no code will catch.

## HTML comments for everything else

Anything that does not fit on the entry line goes below it as an HTML comment:

```
<!-- session-flow: SEQ-NNN escalated to research-design YYYY-MM-DD -->
```

Comment lines are invisible to all three `SEQUENCE.md` parsers (this plugin's skills,
session-scribe's flows, the ops portfolio script), so a note costs a reader nothing and a parser
nothing. Both `/scribe-pull` (divergence markers) and `/session-groom` (escalation markers) already
write them, and the escalation line above is the format `/session-groom` writes and reads: an entry
with that comment on the line below it is waiting on a research-design session and is skipped by the
next groom pass.
