# TODO

Remaining session-flow work. The canonical backlog is `todo/SEQUENCE.md`; the v5
breakdowns live in `todo/2026-08-09-v5-implementation.md`.

## Done 2026-08-12

Everything this file previously tracked has landed. Kept as a short record of what closed,
since the gate blocked the other two items for a while.

- [x] **SEQ-001** — `/session-gatekeeper` ran against 14 real intake items over two runs, with
  four independent review passes over the first. Verdicts, findings, and disposition:
  `todo/2026-08-12-seq-001-gatekeeper-trial.md`. Gate released.

- [x] **SEQ-006 / 5A-1 + 5A-2** — the `[auto]` provenance marker. add-task takes an optional
  auto-provenance flag (off by default); gatekeeper sets it when enqueuing; groom, next, and
  session-status read it. The session-scribe parser caveat is documented in both writers.

- [x] **Gatekeeper inbox sweep** — the one pinned paragraph added to
  `skills/session-gatekeeper/SKILL.md` **Inputs**, verbatim from ops spec §11. No other
  gatekeeper behaviour moved; escalation formatting stayed in the ops workflow prompts.

- [x] **SEQ-008** — the nine gatekeeper defects the SEQ-001 trial exposed, fixed across six
  sequential tasks (`todo/2026-08-12-seq-008-gatekeeper-defects.md`). The two with the most
  reach: the direction-doc chain now runs when `paths.direction` is misconfigured and reports
  the dead path, and every claim is marked verified (`file:line`) or assumed while every cited
  path is existence-checked before a breakdown is written.

- [x] **Release** — 1.4.0. Phase 5 and the SEQ-008 fixes ship together; version bumped across
  both manifests and `CITATION.cff`, satellite surfaces scanned.

## Open

Nothing tracked here. New work goes to `todo/SEQUENCE.md` via `/session-add-task` or
`/session-gatekeeper`.
