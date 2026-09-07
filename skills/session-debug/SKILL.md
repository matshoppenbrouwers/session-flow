---
name: session-debug
description: Use when the user reports a bug, a failing test, or unexpected behaviour and wants it diagnosed before it is fixed. Finds the root cause, tests one hypothesis at a time, and stops to question the design after three failed fixes.
---

# Session Debug

Find the cause before changing anything. A change that addresses a symptom is not a fix.

Open with one sentence saying what you are about to do and what it will produce.

## Rules

1. **No fix before the cause is known.** Finish the investigation before proposing a change,
   however obvious the change looks. Simple bugs have causes too, and rushing produces rework.
2. **One hypothesis, one change, one result.** State the hypothesis, make the smallest change
   that tests it, and read the result before doing anything else. Do not stack changes.
3. **Three failed fixes means the design is in question.** Stop, say so, and discuss the
   architecture with the user before a fourth attempt.
4. **Say what you do not know.** "I do not understand X yet" is a valid state; guessing is not.
5. **No fix before the work item exists.** A confirmed cause becomes a captured work item before
   Phase 4 changes anything. Capture is not permission: the item lands in `captured`, and the
   user's report of the bug is what authorizes fixing it — not the record. Investigation itself
   needs no work item; a change to the codebase does.

## Phase 1: Investigate

- Read the error completely: message, stack trace, line numbers, codes. The answer is often in
  it.
- Reproduce it. If it does not reproduce reliably, gather more data before forming a hypothesis.
- Check what changed: recent commits, dependencies, configuration, environment.
- In a system with several components, instrument the boundaries before guessing where it
  breaks: log what enters and leaves each component, run once, and let the evidence point at the
  failing one. Then investigate that component.
- When the error is deep in a call stack, trace the bad value backwards to where it originates and
  fix it there. `references/root-cause-tracing.md` describes the technique.

## Phase 2: Compare

- Find working code that does something similar in the same codebase.
- If the broken code follows a reference pattern, read the reference fully before judging the
  deviation.
- List every difference between working and broken, however small.
- Note the dependencies and assumptions the broken path relies on.

## Phase 3: Hypothesis

- Write the hypothesis down: "X is the cause because Y."
- Test it with the smallest possible change. One variable at a time.
- Confirmed: go to Phase 4. Not confirmed: form a new hypothesis, and do not leave the failed
  change in place.

## Phase 4: Fix

- **Capture the work item first.** Hand `/session-add-task` the confirmed cause, in Mode A: the
  reporter's words verbatim as `original_request`, the root cause you established as the
  interpreted intent, the corrected behaviour as the scope, and the reproduction as the `Test`.
  It allocates the identity and writes the record with the runtime. Report the `SEQ-NNN` before
  you change a line, so the fix, its evidence, and its cause share one home. A bug filed as an
  issue carries its URL into `source` and `annotations`; one reported in conversation carries
  neither, and no URL is invented for it.
- Reproduce the bug in the smallest form you can: an automated test where the project has a
  framework, otherwise a one-off script.
- Make the one change that addresses the cause. No unrelated improvements, no bundled
  refactoring.
- Run the reproduction and the surrounding tests. Report what you ran and what it printed.
- Keep the regression test where the project keeps tests for this kind of change; drop the
  scratch script.
- Record the outcome against the captured identity: what the cause was, what the fix was, and what
  the test printed. The record is where the next session reads this, not the transcript.
- If the fix does not hold, count the attempts. Fewer than three: return to Phase 1 with what you
  learned. Three: rule 3 applies.

## When there is no root cause

Sometimes a completed investigation shows the issue is environmental, timing-dependent, or
external. Then document what was checked in the captured item — the investigation is the outcome
even when no cause was found — add the handling that fits (a retry, a timeout, a clearer error)
and the logging that would catch the next occurrence. Most "no root cause" conclusions are
incomplete investigations; make sure this one is not.

## Signals you have left the process

- "Quick fix now, investigate later."
- "Let me just try changing X."
- Several changes before a single test run.
- Proposing fixes before tracing the data flow.
- A second fix that reveals a new problem somewhere else.

Any of these means: return to Phase 1.

Derived from the `systematic-debugging` skill in superpowers by Jesse Vincent (MIT); see
`THIRD_PARTY_NOTICES.md`. Chain context: `references/workflow-overview.md`.
