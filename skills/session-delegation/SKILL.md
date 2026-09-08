---
name: session-delegation
description: Dispatch named tasks of one work item to agents. Loads each task record through the runtime, resolves the permitted prerequisite closure, and records each result against its claimed identity. Use after /session-task-planning has written task records. Triggers on "/session-delegation" or when user says "execute the tasks", "run the plan", or "dispatch the agents".
---

# Session Delegation

Dispatch the named tasks of one work item, and nothing else.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **An invocation carries explicit task IDs.** Every dispatch names a SEQ identity and the task IDs it may run. A work item holds tasks belonging to different decisions; being able to read one grants no permission to run it.
2. **The task set never grows during a run.** The named IDs plus their permitted prerequisite closure are the whole set. A prerequisite already `done` contributes its result and its files as context, not as work to redo, and nothing else joins the run.
3. **Claim each task before dispatching it, and dispatch only within its `allowed_paths`.** The claim is the bounded assignment: identity, expected revision, allowed paths. It runs nothing by itself.
4. **Record each task's outcome through `record-result` against the claimed identity.** Progress never goes into the sequence view or a task index; both are generated, and the next `render` discards anything typed there.
5. **Parallel means one message with several Task tool calls.** Not several sequential messages.
6. **A task result is a task result.** Reaching `passed` on every named task does not complete the parent: that needs applicable evidence for the accepted outcome, which is `/session-verify`'s judgement.
7. **The acceptance tests are written before the implementers start, by a different agent, and implementers never edit them.** `test-author` writes them from each task's accepted scope, so the tests measure the specification rather than the implementation's opinion of it. This is about who writes the oracle, not about designing through tests: the behaviour was fixed when the scope was accepted.

## Prerequisites

- Task records under `<work root>/seq-NNN/tasks/`, written by `/session-task-planning`.
- A resolved runtime. Resolve it as `references/runtime-integration.md` describes and confirm it with `doctor` before reading any record; when it cannot answer, report what is missing and stop.
- An explicit target scope: the SEQ identity and the task IDs to run. `/session-next` supplies both. A direct invocation must name the IDs; when the user asks for an item by name, list its `accepted` task IDs and have them confirm the set before Step 1.

**Invoked by session-next:** report the two results separately — each task's own result, and the item's aggregate acceptance — and leave the parent's completion to `/session-verify`.

## Execution Algorithm

### Step 1: Load the Named Tasks and Their Permitted Closure

Read each named task record, then walk its `depends_on` entries to add the permitted prerequisite closure — the tasks the named IDs transitively depend on:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-042 --task A2
```

From each record take `task`, `depends_on`, `allowed_paths`, `lifecycle`, `revision`, `claim`, `result`, and the scope region. Read the item's `intent.md` once for the accepted outcome and the shared requirements it links — `spec.md`, `plan.md`, prerequisite results — and load those links rather than copying their content into a payload.

Closure members are context. A member already `done` contributes its result and its `allowed_paths`; it is never re-dispatched.

**Stop before dispatching anything**, report the condition with the named error below, and let the caller decide:

| Stop condition | Named error | What to report |
|----------------|-------------|----------------|
| An unknown prerequisite: a `depends_on` entry names a record that does not exist | `invalid-identity` | The naming task, the dangling identity, and the runtime's own message. Never guess which task was meant |
| A cycle in the permitted closure | `invalid-identity` | The identity chain that closes on itself, in order |
| An overlapping write scope: two tasks ready in the same group share an `allowed_paths` entry, or one lies inside another's glob | `invalid-request` | The pair and the shared paths. Do not quietly serialize them — the dependency analysis is wrong, and that is the caller's to fix |
| A stale claim: the record is claimed by another actor | `missing-authority` | The holding actor and when it claimed. Reassign only on the user's word, with `takeover_claim` |
| Changed accepted scope: acceptance no longer names the record's current fingerprint | `missing-authority` | Both fingerprints, and that re-acceptance or a same-meaning decision is needed before this task can run |

Two further conditions stop the run the same way: a named ID with no record, and a prerequisite that is still `accepted` rather than `done`. For the second, report the unmet IDs and offer to add them to the scope — the caller decides, and you never pull them in yourself.

### Step 2: Author the Scope's Acceptance Tests

**Before dispatching any implementer**, dispatch `test-author` **once for the whole named set**:

```
Task tool:
  subagent_type: "test-author"
  prompt: |
    Write the acceptance tests for {SEQ-NNN} tasks {task IDs}, before implementation.

    Accepted outcome: {absolute path to the item's intent.md, and spec.md when it exists}
    Public interface: {signatures, types, and contracts the tasks specify}

    Tasks:
    - {SEQ-NNN}/{task ID}: {title} — Accepted scope: {the task's scope region} — Test: {test command}
    {repeat per task}

    The code does not exist yet; red is the expected outcome. Report the
    test paths you wrote, keyed by task ID.
```

Record the returned test paths per task — they go into each implementer's payload as its oracle. If a task comes back with no test path, say so when you dispatch it; do not invent one.

**Expected failures.** These tests fail, and some will not collect until the tasks they depend on land. That is the expected state before implementation, not a blocking failure — do not treat a red oracle as a reason to pause, and do not ask an implementer to "fix" it. The only failures that stop the run are the ones Step 1 and Error Handling name.

**Small units routed from `/session-next`:** a single-record backlog item keeps that skill's self-written-test rule. Do not dispatch `test-author` for a 20-minute change; this step applies when several tasks are named.

### Step 3: Execute in Dependency Order

```
0. Dispatch test-author once (Step 2); record test paths per task
while a named task is not done:
  1. Take the named tasks whose depends_on entries are all done
  2. Group into: sequential (one ready) vs parallel (several ready)
  3. Check the group's allowed_paths do not overlap (Step 1's table)
  4. Claim each task in the group, then dispatch it (Step 4)
  5. On completion, record-result against the claimed identity (Step 5)
  6. Repeat
```

The loop ends when the named IDs have results. Tasks outside the named set keep the state they had.

### Step 4: Claim, Then Dispatch

Claim first. One payload per task, sent as a file:

```json
{"operation": "dispatch-<short unique id>", "coordinator": "session-delegation",
 "actor": "agent:<task ID>", "seq": "SEQ-042", "task": "A2", "expect_revision": 2,
 "allowed_paths": ["scripts/session_flow/views.py"]}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" claim --seq SEQ-042 --task A2 --input "$PAYLOAD"
```

A `missing-authority` answer means someone already holds that assignment: stop that task and report the holder. A `stale-revision` answer means the record moved — re-read it and rebuild. After an interruption, re-send the identical payload under the same `operation` id: the runtime returns the prior result with `replayed: true`, and the claim it recorded still stands. Never reuse that id for a different payload.

**Sequential task** (one ready):
```
Task tool:
  subagent_type: "general-purpose"
  prompt: [the task record's scope, instructions, allowed paths, oracle, test command]
```

**Parallel tasks** (several ready): send a **single message** with several Task tool calls. Do not pass a `mode` parameter — subagents inherit the parent session's permission mode, and the Task tool's `mode` was deprecated in Claude Code v2.1.212 and is ignored.

**Every payload carries the task's `allowed_paths` as an explicit write boundary:**

```
You may only create or modify these paths: {allowed_paths}
If the task requires touching anything else, stop and report — do not proceed.
```

This is a prompt-level constraint, not a security boundary — nothing enforces it at the tool layer. Its value is that an agent which wanders stops and reports instead of writing, and violations become visible. It does **not** make wrongly parallelized tasks safe: disjoint write sets do not remove semantic dependencies, so the dependency analysis keeps its full weight.

Entries may be exact paths or directory globs (`src/lib/governor/**`). Pass them through verbatim. Because test paths belong to `test-author` and to no task's `allowed_paths`, this also keeps implementers out of the test files.

**House rules in the payload.** If `.session-flow.json` sets `paths.conventions` and the file exists, include it — it is designed to be short. Read `paths.lessons` as a one-line index; load nothing further unless a line bears on the task at hand. When neither key is set, dispatch without them.

### Step 5: Record Each Result

As each task returns, record its outcome against the identity that was claimed, then refresh the views:

```json
{"operation": "result-<short unique id>", "coordinator": "session-delegation",
 "actor": "agent:<task ID>", "seq": "SEQ-042", "task": "A2", "expect_revision": 3,
 "result": {"outcome": "passed", "checks": [{"command": "...", "observed": "ok"}],
            "evidence": {"criteria": "...", "environment": "...", "revision": "...",
                         "limitations": ["..."]}}}
```

`outcome` is `passed`, `failed`, `blocked`, or `unknown`, and it says what happened: a check that could not run is `unknown`, never `passed`. Only the actor that claimed the task records its result. Then run `render` — never write progress into a generated view.

Recording a result unblocks dependents, so do it as each task returns rather than in a batch.

### Step 6: Optional Quality Gates

For consequential tasks (P1, several files), optionally run after completion:
- `code-simplifier:code-simplifier` agent for cleanup
- `code-reviewer` agent for review

### Step 7: Report

Two records, kept apart. A task's result says its own checks passed. The item's aggregate acceptance says the accepted outcome holds, and only `/session-verify` establishes that.

When every named task has a result:
1. Run the project's full test suite and the accepted scope's own checks.
2. Report the aggregate verdict separately from the per-task results. On failure, say the item is integration-failed, name the failing checks, and leave the task results as they are — they are still true.
3. Report: the SEQ identity, the task IDs run, files changed, and any task of the same item left untouched.
4. Say what the parent still needs — the tasks without results and the `delivery` target the accepted scope requires — and suggest `/session-post-implementation` for refinement, then `/session-verify` for the outcome.

### Invocation and Continuation

One invocation runs one named set and stops. Running the next set is a new invocation with its own named IDs, or the `continuation` policy `/session-next` defines — capacity, scope, and stop conditions in `.session-flow.json`. This skill never grants itself the next set, and finishing one set is not authority to start another.

Under such a policy, re-resolve the authority before each dispatch and before each consequential effect: re-read the policy, confirm it still covers this SEQ identity and this action, and re-run Step 1's checks for the set about to run. A withdrawn or changed policy stops the next dispatch and is reported as `missing-authority`; tasks already dispatched finish, and their results are recorded. Spent capacity stops the run the same way, reported as `capacity-exhausted`.

A bounded request from ops is a candidate for a named set, never the set itself. It carries no authority of its own — the work runs locally, under the policy or under an invocation that names the IDs — and without one it starts nothing.

## Agent Prompt Template

```
You are implementing task {SEQ-NNN}/{TASK-ID}.

## Task: [Title]

**Work item**: {SEQ-NNN} — accepted outcome at {absolute path to intent.md}
**Allowed paths**: [allowed_paths]

You may only create or modify these paths. If the task requires touching
anything else, stop and report — do not proceed.

**Accepted scope**: [the task record's scope region, verbatim]

**Instructions**:
[the task record's instructions]

**Acceptance oracle**: the tests at [test paths from test-author] were written
for this task before implementation. Make them pass. Never modify a test file.
If a test looks wrong, stop and report it — do not edit around it.

**Test command**: [the task's test command]

## Workflow
1. Read all referenced files first
2. Read the oracle tests to understand what the task must satisfy
3. Implement the changes
4. Run the test command and verify it passes
5. Report against {SEQ-NNN}/{TASK-ID}: files changed, test results, issues.
   Do not mark the task complete — the coordinator records its result.
```

## Error Handling

- Any condition in Step 1's table: stop before dispatch and report it with the named error
- Oracle tests failing or not collecting before implementation is not a failure — see **Expected failures** in Step 2
- If an agent fails: record `failed` against its identity with the checks that failed, and continue with independent tasks
- If an implementer reports a test it believes is wrong: stop that task, surface the test and the accepted criterion to the user, and fix the test with `test-author` if the user agrees — never let the implementer edit it
- If a task other tasks depend on fails: pause the dependent branch and report; do not dispatch on a failed prerequisite
- If tests fail after implementation: the agent iterates up to 3 times before reporting failure
- If the runtime answers `root-busy`: another coordinator holds the work root, or a prepared operation needs recovery. Report it and run `reconcile` before retrying — do not write records around it

Chain context: see `references/workflow-overview.md`.
