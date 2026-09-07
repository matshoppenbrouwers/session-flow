---
name: session-next
description: Implement the next work item from the project's backlog. Asks the runtime to select one accepted item, claims it, executes one bounded unit, and records the result against that identity. Use when the user wants to make progress on the backlog without naming a specific item. Triggers on "/session-next" or when user says "implement the next task", "do the next task", "what's next — just do it", or "work the backlog".
---

# Session Next

Select, claim, and execute one bounded unit of accepted work.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Selection comes from `select`, never from a file.** The sequence at `paths.sequence` is generated output: read it to see the backlog, never to pick from it, and never edit it. `select` returns one candidate and the eligibility reasons for everything it considered, and it starts nothing.
2. **Only accepted work is eligible.** `captured` work, work whose acceptance no longer names the current scope fingerprint, and work still marked `(needs breakdown)` are refused by `select` with a reason. A linked breakdown file confers no eligibility, and neither does an existing record.
3. **Claim before executing, and execute only what the claim names.** The claim carries the identity, the expected revision, and the allowed paths. It records a bounded assignment; it does not run that assignment and does not schedule it.
4. **Record results through `record-result` against the claimed identity.** Never write completion into the sequence view or a task view — both are derived, and the next `render` discards anything typed there.
5. **A passing task is not a delivered outcome.** A task result never moves its parent to `done`. Parent completion needs applicable evidence for the accepted outcome, which is `/session-verify`'s judgement, not this skill's.
6. **One bounded unit per invocation.** Finish it, report, and name the next candidate without starting it. Continuation over several units needs its own scoped invocation, or a standing policy that names capacity and stop conditions.

## Step 0: Resolve the Runtime

Every record read or written here goes through the helper at `<package-root>/scripts/session-flow.py`. Resolve it by the one rule for this host (`references/runtime-integration.md`): the plugin root in `${CLAUDE_PLUGIN_ROOT}` for a native plugin, the discovered installed package for Codex, or the `session-flow-runtime.json` descriptor beside this `SKILL.md` for a standalone copy. Then confirm it answers, with absolute paths for the interpreter and the entrypoint:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
```

`storage.work_root` and `storage.sequence_path` come from `.session-flow.json`, so a wrong root shows up here rather than three steps later. When the runtime cannot answer, report what is missing and where it was expected, and stop. There is no hand-editing path.

## Step 1: Select One Candidate

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" select
```

Read `result.candidate` and `result.considered`. The candidate is one work item, ordered by priority, then provenance — a manual item outranks an `[auto]` one at equal priority — then order, then identity.

- **`candidate` is `null`**: nothing is eligible. Report each considered item with its reasons verbatim, and offer `/session-groom` for items needing a breakdown, `/session-gatekeeper` for untriaged intake, or acceptance for items still `captured`. Do not pick an ineligible item anyway.
- **The user named an item**: pass `--seq SEQ-NNN`. The answer is then that item or its reasons for being ineligible — never a different item.

## Step 2: Resolve One Bounded Unit

The candidate is a work item, not permission to run everything under it.

- **Compact item** (`task_counts.total` is 0): the unit is the item itself. `intent.md` is the whole record — scope, approach, and result all live there.
- **Expanded item**: the unit is exactly one task — the first whose lifecycle is `accepted` and whose `depends_on` entries are all `done`. Read it with `show --seq SEQ-NNN --task A1`.

Widen the unit only when the user names the additional task IDs in this invocation. Then echo the resolved set back in one line before claiming. Never derive extra IDs from a title, a heading, a phase label, or the tasks sitting beside the one you resolved.

Write the resolved unit down before going on: SEQ identity, task ID where there is one, the record's current `revision`, and its `allowed_paths`.

## Step 3: Claim the Resolved Identity

Build the payload as a file — no option accepts free text — and claim exactly the identity Step 2 resolved:

```json
{
  "operation": "next-<short unique id>",
  "coordinator": "session-next",
  "actor": "<this session>",
  "seq": "SEQ-042",
  "task": "A1",
  "expect_revision": 3,
  "allowed_paths": ["scripts/session_flow/store.py", "tests/test_store.py"]
}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" claim --seq SEQ-042 --task A1 --input "$PAYLOAD"
```

- `missing-authority`: another actor holds the claim. Report the holder and stop. Reassign only when the user says to, with `takeover_claim` and the authority that reassigns it.
- `stale-revision`: the record moved since Step 2. Re-read it and rebuild the payload; never retry with the old revision.
- An interrupted run resumes by re-sending the **same** `operation` id with the same payload: the runtime returns the prior result with `replayed: true` and the bounded assignment stands. A different payload under that id is refused — issue a new operation id instead.

## Step 4: Execute the Claimed Unit

1. Read the record's scope region and every file it names before changing anything.
2. Implement inside `allowed_paths` only. If the work needs a path outside them, stop and report: the scope is wrong, and widening it is a decision, not a detail.
3. Add the regression test that pins the accepted criterion — one focused test, in the existing test module where one exists, covering the decision logic rather than the framework. Where the project's own CLAUDE.md states a testing rule, that rule wins.
4. Run the record's named Test command and keep its output; Step 5 records it.

When the user widened the unit to several task IDs, hand them to `/session-delegation` instead of running them here: pass the SEQ identity and the explicit task IDs. Delegation dispatches those IDs and their permitted prerequisite closure, and nothing else in the item.

## Step 5: Record the Result

```json
{
  "operation": "result-<short unique id>",
  "coordinator": "session-next",
  "actor": "<the actor that claimed it>",
  "seq": "SEQ-042",
  "task": "A1",
  "expect_revision": 4,
  "result": {
    "outcome": "passed",
    "checks": [{"command": "python3 -B -m unittest -v tests.test_store", "observed": "ok"}],
    "evidence": {"criteria": "<the criterion this proves>", "environment": "<where it ran>",
                 "revision": "<code revision>", "limitations": ["<what it does not cover>"]}
  }
}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" record-result --seq SEQ-042 --task A1 --input "$PAYLOAD"
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" render
```

`outcome` is one of `passed`, `failed`, `blocked`, `unknown`, and it says what actually happened. A check that could not run is `unknown`, never `passed`. Only the claiming actor may record the result.

## Step 6: Report

1. The SEQ identity, the task ID where there is one, and the outcome the result records.
2. The checks behind that outcome, with their output.
3. What the parent still needs: the tasks not yet `done`, and the `delivery` target the accepted scope requires. Say plainly that a passing task is progress, and that `/session-verify` decides whether the outcome is delivered.
4. The next candidate from a fresh `select` — named, not started.

Chain context: see `references/workflow-overview.md`.
