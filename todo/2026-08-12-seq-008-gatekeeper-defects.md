# Phase file: SEQ-008 — gatekeeper defect fixes

**Findings source**: `todo/2026-08-12-seq-001-gatekeeper-trial.md` §3
**Goal**: Close the nine defects the SEQ-001 trial exposed in `/session-gatekeeper`. Each task
cites its finding number — read that finding before starting; it carries the evidence the fix
is answering.

Groomed from the raw SEQ-008 one-liner. No new design work: the trial record already pairs every
defect with a concrete fix, so this is a breakdown of recorded conclusions, not a research pass.

**Scope note.** Eight of nine fixes are edits to `skills/session-gatekeeper/SKILL.md`. Finding 2
is the exception: gatekeeper hands trivial items to `/session-add-task`, which is what actually
writes the `Files` and `Test` fields, so the cited-path problem belongs to both skills. 8A-3 owns
that boundary and is the only task that touches a second skill file.

**Sequencing.** Nearly every task edits the same file, so the chain is `[seq]` throughout —
there is no real parallel opportunity here. 8A-6 (CHANGELOG) is last because it describes the
five that precede it.

---

## Parallelization Guide

```
8A-1 ─> 8A-2 ─> 8A-3 ─> 8A-4 ─> 8A-5 ─> 8A-6
```

| Tag | Meaning |
|-----|---------|
| `[seq]` | Must complete before next task starts |
| `[x]` | Completed |
| `[ ]` | Not started |

**Parallel opportunities:** none. Single-file contention.

**Findings coverage:** 8A-1 → 1 · 8A-2 → 5, 6, 7 · 8A-3 → 2, 3 · 8A-4 → 4 · 8A-5 → 8, 9.

---

## Phase 8A: Gatekeeper defect fixes

### [8A-1] [seq] [x] P1: Make the direction-doc fallback actually execute
**Files**: `skills/session-gatekeeper/SKILL.md:20-28`

**Instructions**:
- Read trial finding 1 first
- Rewrite step 2 of **Path & Context Resolution** so `paths.direction` is a hint, not a terminus:
  run the detection chain when the key is unset **or** when it points at a file that does not
  exist. Today the fallback is written as `If unset, detect …` — the misconfigured case falls
  through it
- Extend the chain past the two locations it currently names. Order: `paths.direction` →
  `PRD.md` / `DIRECTION.md` / `VISION.md` in the docs root → the same three at the repo root →
  the same three one directory below the docs root → a `## Direction` section in a top-level doc.
  The trial's PRD sat one directory down and was never reached
- Add this sentence to the step, verbatim: `A paths.direction that resolves to no file is itself
  a finding` — and require Step 4's report to name both the dead path and the file actually used
- Amend step 5 so "no direction doc exists" means the **whole chain** came up empty. A configured
  path that missed is not the same as an absent direction doc, and only the former should force
  alignment to "unknown"

**Accept**: With `paths.direction` pointing at a nonexistent file and a `PRD.md` one directory
below the docs root, the written chain reaches that PRD, and the misconfiguration is reported
rather than swallowed.

**Test**: `grep -q "resolves to no file is itself a finding" skills/session-gatekeeper/SKILL.md && ! grep -q "If unset, detect" skills/session-gatekeeper/SKILL.md`

---

### [8A-2] [seq] [x] P1: Close the three classification holes — questions, unknown alignment, "trivial"
**Files**: `skills/session-gatekeeper/SKILL.md:43-69`

**Instructions**:
- Read trial findings 5, 6 and 7 first
- **(finding 5)** Insert a step between Classify and Route: if an item is a question answerable
  from the code, answer it — grep, cite `file:line` — and route on the answer. Two of the trial's
  14 items were questions, and both answers changed the routing. State that guessing at an
  answerable question is a defect, and that all three rows of the routing table are live
  branches: a run that only ever adds or escalates has not used the third
- **(finding 6)** Make `Alignment: unknown` a hard escalate in the routing table itself, not just
  in the prose at resolution step 5. Run 1 declared alignment unknowable and then auto-added six
  items; the table has to make that combination unrepresentable
- **(finding 7)** Add an explicit bar to the Scope axis, above the trivial/feature/architectural
  values: anything touching database schema or a spine/canonical status field returns to the user
  regardless of size. This is the run-2 rule that moved three items out of the sequence
- Keep the table format; do not expand the axes into prose

**Accept**: The routing table cannot produce "auto-add" for an item whose alignment is unknown or
which touches schema or a spine status field; answerable questions get answered before routing.

**Test**: `grep -q "spine" skills/session-gatekeeper/SKILL.md && grep -qi "unknown alignment" skills/session-gatekeeper/SKILL.md && grep -qi "answerable from the code" skills/session-gatekeeper/SKILL.md`

---

### [8A-3] [seq] [x] P1: Separate verified claims from assumed ones, and check cited paths exist
**Files**: `skills/session-gatekeeper/SKILL.md:53-73`, `skills/session-add-task/SKILL.md`

**Instructions**:
- Read trial findings 2 and 3 first. The numbers are the argument: 20/20 grepped source refs
  landed, 2/10 inferred test paths did, same run and same stated confidence
- In gatekeeper, add a rule before the hand-off to add-task: every path cited in a breakdown's
  `Files` or `Test` field must be existence-checked before the breakdown is written — a `test -f`
  (or `test -d` for globs) over each one. A path that fails the check is either corrected or
  dropped; it is never cited on the strength of a naming convention
- Require every substantive claim in a verdict or breakdown to be marked as **verified** (with the
  `file:line` it was grepped from) or **assumed**. Unmarked claims are not permitted. Finding 3
  records twelve claim errors that survived into breakdowns, several inverted rather than merely
  wrong — the marking is what makes an inverted claim visible as a guess
- In `session-add-task`, add a matching Non-Negotiable: a breakdown may not cite a path that does
  not exist unless the task's own Instructions create it, in which case say so inline
- Do not add a verification step to `session-groom` or `session-task-planning` in this task —
  they are out of SEQ-008's scope and get their own entry if wanted

**Accept**: Neither skill permits an unchecked path in a breakdown, and a reader of a gatekeeper
verdict can tell which claims were grepped and which were inferred.

**Test**: `grep -q "test -f" skills/session-gatekeeper/SKILL.md && grep -qi "verified" skills/session-gatekeeper/SKILL.md && grep -qi "does not exist" skills/session-add-task/SKILL.md`

---

### [8A-4] [seq] [x] P1: Make escalation an act, not a tag
**Files**: `skills/session-gatekeeper/SKILL.md:12-18`, `:53-73`

**Instructions**:
- Read trial finding 4 first
- Define what escalation means in the Route row for significant/divergent/unclear items: name the
  specific question the research-design session has to answer, name the items it covers (merging
  near-duplicates, as run 2 did with three overlapping requests), and **propose the session to the
  user in the run's output**. Appending `(needs research-design)` to seven lines is what run 1 did;
  it duplicated the section preamble, discriminated nothing, and proposed nothing
- State plainly that a tag written into a file nobody re-reads does not satisfy Non-Negotiables 2
  and 5. Those two say escalation happens *with the user*
- The annotation may stay as a marker, but only alongside the proposal — never as the whole of it

**Accept**: An escalated batch produces a named, scoped session proposal addressed to the user; a
run that only annotates lines fails the skill's own bar.

**Test**: `grep -qi "propose" skills/session-gatekeeper/SKILL.md && grep -qi "not escalation" skills/session-gatekeeper/SKILL.md`

---

### [8A-5] [seq] [x] P1: Persist findings; leave raw capture unmutated
**Files**: `skills/session-gatekeeper/SKILL.md:30-35`, `:71-73`

**Instructions**:
- Read trial findings 8 and 9 first
- **(finding 8)** Require Step 4's report to be written to a file, not only to chat. A code
  inventory and two question answers lived only in the trial's transcript, and routing was then
  done off the tag rather than the answer. Write the per-item verdict table plus any answers and
  inventories to `{paths.todo}/YYYY-MM-DD-gatekeeper-run.md` (repo file-naming convention), and
  link it from anything the run escalates or enqueues
- **(finding 9)** Add a rule to **Inputs**: inbox items are raw user capture. The gatekeeper reads
  them, routes them, and `git rm`s a routed one — it does not edit headings, reword items, or fold
  one item into another. Run 1 deleted a heading and merged two items with no trace left. If two
  items should be merged, that is a routing decision recorded in the report, not an edit to the
  capture
- Keep the existing `git rm`-on-routing sentence; this extends it rather than replacing it

**Accept**: Every run leaves a durable record on disk, and an inbox file is either untouched or
removed — never rewritten.

**Test**: `grep -q "gatekeeper-run" skills/session-gatekeeper/SKILL.md && grep -qi "raw user capture" skills/session-gatekeeper/SKILL.md && grep -q "git rm" skills/session-gatekeeper/SKILL.md`

---

### [8A-6] [seq] [x] P2: CHANGELOG entry for the gatekeeper fixes
**Files**: `CHANGELOG.md`

**Instructions**:
- Add a **Fixed** subsection under `## Unreleased` describing the five tasks above as one change
  set, framed by what the trial measured rather than by task ids
- Update the existing `### Notes` bullet that currently reads "They are tracked as SEQ-008 and are
  **not** addressed here" — that sentence goes stale the moment 8A-1 lands
- Cite `todo/2026-08-12-seq-001-gatekeeper-trial.md` as the evidence, as the Unreleased preamble
  already does

**Accept**: `## Unreleased` describes the gatekeeper fixes, and no bullet still claims the nine
findings are unaddressed.

**Test**: `! grep -q "not addressed here" CHANGELOG.md && grep -q "SEQ-008" CHANGELOG.md`

---

## Success Criteria

- All nine trial findings have a landed fix; §3 of the trial record can be read top to bottom
  against the skill file with no open item.
- `/session-gatekeeper` reaches a direction doc that exists anywhere in its chain, and says so
  when the configured path is wrong.
- No breakdown the gatekeeper produces cites a path that does not exist.
- Escalation produces a proposal to the user; every run leaves a file behind.

## Open question for the user

Finding 5 is recorded as "the third routing branch went unused", but its supporting evidence is
about unanswered questions rather than the off-direction branch. 8A-2 covers both readings — it
adds the answer-first step *and* states that all three branches are live. If only one was meant,
say which and 8A-2 narrows.
