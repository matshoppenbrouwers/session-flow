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
3. **Claim before executing, and execute only what the claim names.** The claim carries the identity, the expected revision, and the allowed paths. It records a bounded assignment and moves an `accepted` record to `active`; it does not run that assignment and does not schedule it.
4. **Record results through `record-result` against the claimed identity.** A `passed` result also closes a task; there is no separate `transition`. Never write completion into the sequence view or a task view — both are derived, and the next `render` discards anything typed there.
5. **A passing task is not a delivered outcome.** A task result never moves its parent to `done`, and `record-result` on an item never changes the item's lifecycle. Parent completion needs applicable evidence for the accepted outcome, which is `/session-verify`'s judgement, not this skill's.
6. **One bounded unit per invocation.** Finish it, report, and name the next candidate without starting it. Continuation over several units needs its own scoped invocation, or the standing policy **Continuation Over Several Units** defines — capacity, scope, and stop conditions, re-resolved before every dispatch.
7. **One mutation per record at a time.** Never send two mutating runtime calls for the same record at once. Wait for each call's result and re-read the record before the next, because every write moves `revision` and the second call would fail as `stale-revision` or overwrite the first.

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

### A Direct Instruction for a `captured` Item

When the user directly instructs you to implement a named item that is still `captured`, their message is the authority. Record acceptance first, quoting the message as the authority source and giving the decision scope as a list of strings, then run `select --seq` again and continue:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" accept --seq SEQ-042 --input accept.json
```

This is the one payload example in this skill. For `claim`, `record-result` and the other payloads, run `session-flow.py schema <command>`: it prints the required and optional fields and an example.

```json
{"expect_revision": 2, "actor": "<this session>",
 "authority": {"source": "user message: \"implement SEQ-042\"", "revision": "<approval timestamp>"},
 "scope": ["implement", "verify"]}
```

Quote only what the user said, and list only the actions it covers. A merge, deployment, or external post is not covered unless the message names it. Without a direct instruction, a `captured` item stays ineligible.

## Step 2: Resolve One Bounded Unit

The candidate is a work item, not permission to run everything under it.

- **Compact item** (`task_counts.total` is 0): the unit is the item itself. `intent.md` is the whole record — scope, approach, and result all live there.
- **Expanded item**: the unit is exactly one task — the first whose lifecycle is `accepted` and whose `depends_on` entries are all `done`. Read it with `show --seq SEQ-NNN --task A1`.

Widen the unit only when the user names the additional task IDs in this invocation. Then echo the resolved set back in one line before claiming. Never derive extra IDs from a title, a heading, a phase label, or the tasks sitting beside the one you resolved.

Write the resolved unit down before going on: SEQ identity, task ID where there is one, the record's current `revision`, and its `allowed_paths`.

## Step 3: Claim the Resolved Identity

Build the payload as a file — no option accepts free text — and claim exactly the identity Step 2 resolved. The payload carries `coordinator`, `actor`, `seq`, `task` (for a task), `expect_revision` and `allowed_paths`. Run `session-flow.py schema claim` for the required and optional fields and an example.

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" claim --seq SEQ-042 --task A1 --input "$PAYLOAD"
```

A successful `claim` on an `accepted` record also moves it to `active`. Do not send a `transition` to start the work.

- `missing-authority`: another actor holds the claim. Report the holder and stop. Reassign only when the user says to, with `takeover_claim` and the authority that reassigns it.
- `stale-revision`: the record moved since Step 2. Re-read it and rebuild the payload; never retry with the old revision.
- The payload needs no `operation`: the runtime generates one and returns it under `operation`. If you may need to retry after an interruption, send your own `operation` id in the first call; then re-sending the same payload with that id returns the prior result with `replayed: true` and the bounded assignment stands. Otherwise run `show` (and `reconcile` if the runtime reports a pending operation) before re-sending, because `expect_revision` makes a blind retry fail with `stale-revision`. A different payload under that id is refused.

## Step 4: Execute the Claimed Unit

1. Read the record's scope region and every file it names before changing anything.
2. Implement inside `allowed_paths` only. If the work needs a path outside them, stop and report: the scope is wrong, and widening it is a decision, not a detail. When the user approves the widening, follow the widening sequence in `/session-delegation`: `revise` changes `allowed_paths` with the approval quoted in its `correction` field, then the same actor re-claims with the full new list, because a claim replaces the previous claim's paths.
3. Add the regression test that pins the accepted criterion — one focused test, in the existing test module where one exists, covering the decision logic rather than the framework. Where the project's own CLAUDE.md states a testing rule, that rule wins.
4. Run the record's named Test command and keep its output; Step 5 records it.

When the user widened the unit to several task IDs, hand them to `/session-delegation` instead of running them here: pass the SEQ identity and the explicit task IDs. Delegation dispatches those IDs and their permitted prerequisite closure, and nothing else in the item.

## Step 5: Record the Result

The close-out is two calls: `claim` (Step 3), then `record-result`. Build the result payload as a file; run `session-flow.py schema record-result` for the fields.

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" record-result --seq SEQ-042 --task A1 --input "$PAYLOAD"
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" render
```

`outcome` is one of `passed`, `failed`, `blocked`, `unknown`, and it says what actually happened. A check that could not run is `unknown`, never `passed`. Only the claiming actor may record the result. Put the criterion, environment, code revision and limitations in `result.evidence`.

On a task, the outcome decides the lifecycle:

- `passed` closes the task, when it is `active`: the runtime records the result, adds an evidence entry built from the result's evidence at the task's current fingerprint, and moves the task to `done` when the completion gate passes.
- `result.not_closed` in the response: the result and evidence are recorded, but the gate refused to close the task and it stays `active`. The value gives the reason. Fix the cause: re-accept with `"lifecycle": "active"` in the accept payload (a bare `accept` fails on an active task), or record a same-meaning decision (the `same_meaning` key in a `revise` payload) when the meaning did not change, or add the missing evidence; then record the result again. Report it; do not treat the task as finished.
- `blocked`: the task moves to `blocked`. To resume it, the claim holder sends a `transition` to `active`, then records the result again.
- A task that is not `active`: the result is recorded without an evidence entry and without a lifecycle move, and a `passed` result returns `not_closed` saying so. The remedy depends on the lifecycle. `accepted`: claim it, then record the result again. `blocked`: the claim holder transitions it to `active`, then records again. `done`: it is already closed and nothing needs to happen. `captured`, `deferred` and `cancelled`: it needs acceptance, or a reopening with a correction, before a result can close it.
- `failed` or `unknown`: the result is recorded and the task stays `active`.

`result.evidence` is optional, but on a `passed` result for an `active` task its `criteria`, when evidence is present, must be a non-empty string; otherwise the call is refused and nothing is recorded. Other outcomes and tasks that are not `active` store `result.evidence` as sent. Leaving `evidence` out closes the task only when an applicable evidence entry is already recorded on it; otherwise the result is recorded and the task stays `active`. The runtime marks the entry `source: "record-result"`: it is your own report, not independent verification. `claim`, `result` and `corrections` are written only by `claim`, `record-result` and the `correction` key, and a `revise` or `transition` that changes them is refused. `claim` needs a record that is `accepted`, `active` or `blocked` and whose acceptance names the record's current fingerprint, and is refused as `missing-authority` otherwise.

On a compact item, `record-result` records the result and never changes the item's lifecycle. Completion stays with `/session-verify`.

## Step 6: Report

1. The SEQ identity, the task ID where there is one, and the outcome the result records.
2. The checks behind that outcome, with their output.
3. What the parent still needs: the tasks not yet `done`, and the `delivery` target the accepted scope requires. Say plainly that a passing task is progress, and that `/session-verify` decides whether the outcome is delivered.
4. The next candidate from a fresh `select` — named, not started.

## When the user asks to commit, push or deploy

Delivery is a separate action from the unit's result, and it gets its own receipt. Delivery authority exists only where the user granted it: a passing task, an accepted item or a standing continuation policy does not grant it. Do each step in order and stop at the first one that fails.

1. **Find the runbook.** Use `paths.runbook` in `.session-flow.json`. When it is absent, look for the runbook in the project's CLAUDE.md or AGENTS.md. When neither names one, ask the user, and offer to record the answer in `paths.runbook` so the next delivery does not ask.
2. **Commit only the item's paths.** Stage by name the item's files and the tests written for the item, which sit outside `allowed_paths` on purpose. For an item with tasks, the item's files are the union of its tasks' `allowed_paths`, because `allowed_paths` lives on task records. For a compact item, they are its own `allowed_paths` or claim paths. Leave unrelated changes in the working tree alone.
3. **Check the hooks.** Confirm the repository's hooks are present and executable before pushing. A hook that is missing or not executable is a failure to report, not something to skip.
4. **Push** to the branch and remote the runbook names.
5. **Check the deployed revision and its health.** Confirm the target runs the revision you pushed, then run the runbook's health check against it. Report a mismatch or a failing check as it is.
6. **Record `delivery.receipt`** on the item through `revise`, with the revision, the target and the health result. A `revise` patch replaces the whole `delivery` object, so resend the stored `required`, `target` and `repository` keys unchanged and add the receipt; dropping them changes the fingerprint and makes acceptance stale. Set `delivered_at` inside `delivery`, the key the completion gate reads, only when the push and the health check both succeeded. When a step failed, stop, record `delivery.receipt` with what you observed, leave out `delivered_at`, and report. A receipt records what the checks showed: a failed health check is recorded as failed, and it is not a delivery.

Verification the user already authorized continues as separate work and is never cancelled silently. If delivery would change what that verification tests, say so and ask. `/session-verify` points here for how delivery is done.

## Continuation Over Several Units

Continuation is off unless something outside this run authorizes it: an invocation that names the further units, or a `continuation` policy in `.session-flow.json`. Without one, Step 6 ends the run — name the next candidate and stop.

The `continuation` object in `.session-flow.json` has four keys:

- `"authority"`: `source` (for example `maintainer-standing-policy`) and `revision` (a timestamp).
- `"capacity"`: `units`, how many units the run may complete.
- `"scope"`: `seq`, the identities it covers, and `actions`, such as `implement`.
- `"stop_conditions"`: a list such as `["result-not-passed", "delivery-outstanding"]`.

All four keys are required, `authority.source` is a trusted source and never `auto`, and `stop_conditions` holds only the two tokens defined here. A block missing a key, or naming a condition this skill does not define, authorizes nothing: run one unit and stop. `result-not-passed` stops on the first recorded outcome that is not `passed`. `delivery-outstanding` stops when the finished unit's parent still owes the `delivery` target its accepted scope names.

Each round, before claiming anything:

1. Re-read the policy from `.session-flow.json`. Authority is re-resolved every round, never carried over from the round before.
2. Run `select` and check the candidate against the policy: `scope.seq` must name its identity, and `scope.actions` the action this unit performs.
3. Check the stops below. The first one that holds ends the run there.

Then claim, execute, and record as Steps 3 to 5 do, and count one unit against `capacity`. A unit already claimed finishes: its result is recorded even when the policy is withdrawn while it runs. Revocation blocks the next dispatch; it does not erase an effect that already happened.

| Continuation stop | Reported as | What to report |
|-------------------|-------------|----------------|
| The policy's capacity is spent | `capacity-exhausted` | The units run, the capacity, and the next candidate — named, not started |
| A configured stop condition holds | `stop-condition-met` | The token that held and the record that met it |
| The policy is gone, its `revision` changed, or `scope` no longer covers the next unit | `missing-authority` | The authority the run started under and what stands now |
| The next unit is claimed by another actor | `missing-authority` | The holding actor. Never take a claim over to keep continuing |
| Acceptance no longer names the record's current fingerprint | `missing-authority` | Both fingerprints, and that re-acceptance is a decision, not a detail |
| `select` returns no candidate | `no-candidate` | Every considered item with its reasons verbatim |

Report the stop with the run: how many units ran, which identities, and the reason it stopped.

### A Bounded Request From Ops

Ops produces requests, not assignments. A request names the `seq` it concerns, the action it asks for, and the capture identity it came from; everything else it carries is provenance. Treat it as a candidate: run `select --seq` for that identity and apply the policy above. Local execution does the work, under the policy or under a scoped invocation — the request itself confers nothing. With no standing policy covering that identity, the request starts nothing: report `missing-authority`, name the request, and leave it for the user. A request naming its own `authority` is refused the same way.

Chain context: see `references/workflow-overview.md`.
