# SEQ-010: Make the SEQUENCE.md grammar one written contract

**Status**: [x]
**Priority**: P3
**Sequence**: SEQUENCE.md
**Research**: ../session-scribe/_devdocs/research/2026-08-14-three-plugin-alignment.md (§2 C2, §3.5, §3.6 C5)

## Context

Three plugins parse `SEQUENCE.md` (session-flow's skills, session-scribe's three flows,
session-ops' `ops-portfolio.py`), and the grammar has drifted into pieces: `[DEFERRED]`
id-counting is promised in `README.md:266` and implemented by scribe's `/scribe` skill but
instructed by no session-flow skill; `session-init`'s starter legend omits `[auto]`, ` ⇄ `, and
`[DEFERRED]`; `session-groom` writes a `(needs research-design)` tag that appears in no marker
table and collides with the "exactly one trailing status token" rule scribe parses by; the
gatekeeper's enqueue priority is unspecified; and the id-allocation concurrency discipline (one
scheduled writer per repo, pull before local edits) is written down only in session-ops' spec.

## Task

**Files**: `skills/session-add-task/SKILL.md`, `skills/session-init/SKILL.md`,
`skills/session-groom/SKILL.md`, `README.md`

**Instructions**:
- Add `[DEFERRED]` to add-task's marker table and extend Non-Negotiable 2's id rule to "scan
  every line carrying a SEQ id, including `[x]` and `[DEFERRED]`" (matching README:266 and
  scribe's implementation).
- Extend init's starter SEQUENCE.md legend to list `[auto]`, ` ⇄ <url>`, and `[DEFERRED]` so a
  new project's in-file legend covers the grammar siblings parse.
- Settle `(needs research-design)`: either add it to the marker table as a trailing tag with an
  explicit position rule compatible with the one-trailing-token grammar, or change groom to
  record escalation somewhere other than the entry line. Verify the choice against scribe's
  parse rule (strip exactly one trailing status token) before writing it down.
- Add the concurrency discipline to add-task's Provenance section: ids are allocated
  highest-plus-one with no locking; safety comes from one scheduled writer per repo and pulling
  before local edits.
- Specify the P-value gatekeeper assigns on enqueue (default P3, same rationale as scribe's
  intake doors: an untriaged-against-the-roadmap item cannot claim higher).

**Accept**: add-task's marker table lists every token any shipped writer emits; init's legend
matches it; groom's escalation tag has a defined grammar status; gatekeeper has a priority rule.

**Test**: `grep -c 'DEFERRED' skills/session-add-task/SKILL.md` — expect ≥1 — and `grep -c 'auto' skills/session-init/SKILL.md` — expect ≥1.
