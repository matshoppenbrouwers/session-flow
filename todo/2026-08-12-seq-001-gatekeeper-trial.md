# SEQ-001 — gatekeeper trial run, recorded verdicts

**Date**: 2026-08-12
**Gate**: SEQ-001, which blocked SEQ-006 (`[auto]` marker) and the ops-spec §11 inbox sweep.
**Status**: satisfied — gate released.

Run against a real private project (an internal ops app), not a fixture. Details below are
de-identified: session-flow is public and the trial repo is not. What is recorded here is what
SEQ-001 existed to establish — whether `/session-gatekeeper` produces trustworthy verdicts on real
input — plus the defects the run exposed in the skill.

---

## 1. Scope of the trial

- **Items triaged**: 14 raw inbox one-liners (SEQ-001 required ≥3).
- **Runs**: two. Run 1 unsteered; run 2 after full rollback, with four routing decisions taken by the
  user up front.
- **Review**: four read-only subagents against run 1's output — skill compliance, claim falsification,
  routing critique, repo-convention audit.

The item mix was representative rather than convenient: two questions, three schema-touching features,
three architecture-scale asks, one confirmed defect, and several ambiguous middles.

## 2. Verdicts

Run 2's per-item table, three-axis (scope / alignment / clarity) as Step 4 requires:

| Item class | Count | Route |
|---|---|---|
| Trivial, aligned, clear — pure code or copy | 3 | Added to sequence |
| Feature touching schema or spine business rules | 3 | User decision |
| Question answerable from code | 2 | Answered, then user decision on the follow-up |
| Architectural / needs research | 5 | Research-design (three near-duplicates merged into one) |
| Divergent — built a rule on a deprecated value | 1 | User decision, flagged divergent |

Run 1, by contrast, auto-added 6 and escalated 7 by appending a tag. Run 2 shipped 3.

## 3. Findings — defects in the skill, not the project

These are the trial's real output. Each is a concrete gatekeeper failure with a concrete fix.

1. **The direction-doc fallback never ran.** Config pointed `paths.direction` at the wrong file. The
   skill's own resolution chain says to then search `PRD.md` / `DIRECTION.md` / `VISION.md` in the docs
   root and repo root. Run 1 stopped at the misconfiguration, declared direction unknown, and proceeded.
   A correctly-named PRD existed one directory down and was never read. The fallback must actually
   execute, and a misconfigured `paths.direction` is itself a finding to report.

2. **Verified and assumed claims were indistinguishable in the output.** Source references were
   grepped: 20 spot-checked, 20 landed. Test paths were inferred from a convention the project had
   abandoned: 8 of 10 cited files did not exist, so every `Test` command would have failed at
   collection. Same run, same confidence, 100% vs 20% accuracy. Nothing in the output marked which was
   which. A `test -f` loop over every cited path would have caught all 8.

3. **Twelve substantive claim errors survived into breakdowns**, several inverted rather than merely
   wrong — "nothing calls this for rootless rows" when its only caller fires exclusively for rootless
   rows; "two doors onto this transition" when both converge on one documented path. Depth cuts both
   ways: detailed breakdowns are more useful when right and send implementers further down dead ends
   when wrong.

4. **Escalation was a no-op.** Appending `(needs research-design)` to seven lines duplicated what the
   section preamble already said, discriminated nothing, and proposed no session. Non-Negotiables 2
   and 5 require escalation *with the user*. A tag in a file nobody re-reads is not escalation.

5. **The third routing branch went unused.** Two of the 14 items were questions answerable in a few
   greps, and both answers changed the routing. Answering is the gatekeeper's job; guessing is not.

6. **Self-contradiction on the alignment axis.** Run 1 declared alignment unknowable, then auto-added
   six items — where the skill's own routing table makes "unknown" a hard escalate.

7. **"Trivial" silently absorbed schema and business-rule changes.** Two schema columns and two
   changes to the canonical single-writer surface were classified trivial. An explicit bar in run 2
   ("anything touching schema or spine status fields returns to the user regardless of size") moved
   three items out of the sequence.

8. **Findings were reported in chat and then lost.** A code inventory and two answers lived only in the
   transcript, and routing was done on the tag rather than on the answer.

9. **Raw user capture was mutated.** Run 1 deleted a heading and folded one item into another without
   leaving a trace. The inbox is described in-file as raw capture.

## 4. What the run got right

The grounding pass was real and changed the answer — three of six run-1 items turned out to be
substantially built already, which a text-only triage would have missed. The reuse-grounds escalation of
three overlapping ledger requests was correct in both runs. Id and priority hygiene were clean
throughout.

## 5. Disposition

SEQ-001 is satisfied: the gatekeeper ran against real items and the verdicts are recorded. The gate on
SEQ-006 and the ops §11 inbox sweep is released, and both shipped alongside this record.

The nine findings above are **not** fixed by SEQ-006 — they are gatekeeper-quality work in its own
right, and are queued separately rather than folded into the intake feature.
