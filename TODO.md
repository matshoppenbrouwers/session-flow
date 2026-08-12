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

## Open

- [ ] **SEQ-008** — fix the nine gatekeeper defects the SEQ-001 trial exposed. Broken down into
  six sequential tasks in `todo/2026-08-12-seq-008-gatekeeper-defects.md`. The two with the most reach:
  the direction-doc fallback never executes when `paths.direction` is misconfigured, and
  nothing in gatekeeper's output distinguishes a grepped claim from an assumed one (source
  refs came back 20/20, test paths 2/10).

- [ ] **Release** — Phase 5 sits under `## Unreleased` in the CHANGELOG. The v5 phase file
  calls for its own 1.4.0 entry rather than an edit to 1.3.0; the version bump across both
  manifests is a `/session-release` decision, not done here.
