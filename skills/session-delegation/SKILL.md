---
name: session-delegation
description: Orchestrate agent execution from a session task plan. Parses dependency tags to dispatch sequential and parallel agents via the Task tool. Use after /session-task-planning produces a todo file. Triggers on "/session-delegation" or when user says "execute the tasks", "run the plan", or "dispatch the agents".
---

# Session Delegation

Orchestrate task execution from a session task plan file.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Never execute without a parsed task plan.** If no `/session-task-planning` output exists, stop and run that first.
2. **Dispatch the named task IDs and nothing else.** Every invocation carries a target scope — a SEQ identity (where one exists) and an explicit list of task IDs. A plan file is a container holding tasks that belong to different scopes; opening it grants no permission to run the tasks the caller did not name.
3. **Respect the dependency graph.** A task with `[parallel-after:X]` where X is still `[ ]` cannot start. No exceptions.
4. **Mark `[x]` in the todo file as soon as a task completes.** Other tasks may be waiting on it. Don't batch updates. A task's `[x]` records that its own Test passed — it is progress, not scope acceptance.
5. **Parallel = one message with multiple Task tool calls.** Not multiple sequential messages. The whole point of parallelism is concurrent execution.
6. **Stop on blocking failure.** If a task fails and other tasks depend on it, pause the dependent branch and report to the user. Do not silently skip and continue.
7. **The acceptance tests are written before the implementers start, by a different agent, and implementers never edit them.** `test-author` writes them from the plan's Accept criteria, so the tests measure the specification rather than the implementation's own opinion of it. This is about who writes the oracle, not about designing through tests: the behaviour was fixed when the plan was approved.

## Prerequisites

- A task plan file produced by `/session-task-planning` with dependency tags
- The plan should have `[seq]`, `[parallel-after:X]`, and status `[ ]` tags
- A target scope: the task IDs to build. `/session-next` supplies the SEQ identity and its owned IDs; a direct invocation must name the IDs, and when the user asks for a plan by name, list its open task IDs and have them confirm the set before Step 1.

**Invoked by session-next:** `/session-next` hands off a resolved scope, not a file. Report the two results separately — per-task progress and the scope's aggregate acceptance — and let `/session-next` close the sequence entry; the entry's marker covers exactly the scope's task IDs.

## Execution Algorithm

### Step 1: Build the graph from the target scope

Read the todo file and locate each task ID the scope names. For each one extract:
- The task heading and its ID (e.g., `1A-1`, `1A-2`)
- Dependency tags (`[seq]`, `[parallel-after:X]`)
- Status (`[ ]`, `[x]`)
- Priority (`P1`, `P2`, `P3`)
- Files — the task's declared write scope

Build nodes for the named IDs and then walk their dependency tags to add the **permitted prerequisite closure**: the tasks the named IDs transitively depend on. A `[seq]` task depends on the preceding task in its own section. Closure members are context, not extra work — a member already `[x]` contributes its result and files to the payload, and nothing else in the file becomes a node.

Stop before dispatching anything and report, when:

- **A named ID is missing or matches more than one heading.** Report the ID and what it matched.
- **A prerequisite is unknown.** `[parallel-after:X]` names an X with no task heading in this file. Report the dangling reference; do not guess which task was meant.
- **The closure contains a cycle.** Report the ID chain that closes on itself.
- **A closure member is still `[ ]`.** The named task is not eligible. Report the unmet prerequisite IDs and offer to add them to the scope, which the caller decides — never pull them in yourself.
- **Two ready tasks declare overlapping write scopes.** See Step 4.

### Step 2: Author the scope's acceptance tests

**Before dispatching any implementer**, dispatch `test-author` **once for the target scope**:

```
Task tool:
  subagent_type: "test-author"
  prompt: |
    Write the acceptance tests for task IDs {scope IDs} of {plan path}, before implementation.

    Design artifact: {absolute path to the plan / design doc}
    Public interface: {signatures, types, and contracts the scope's tasks specify}

    Tasks in the target scope:
    - {TASK-ID}: {title} — Accept: {Accept criterion} — Test: {Test command}
    {repeat per task in scope}

    The code does not exist yet; red is the expected outcome. Report the
    test paths you wrote, keyed by task ID.
```

Record the returned test paths **per task** — they go into each implementer's dispatch payload as its oracle. If a task comes back with no test path, note it and say so when you dispatch that task; do not invent one.

**Expected failures.** These tests fail, and some will not even collect until the tasks they depend on land. That is the expected state before implementation, not a blocking failure — do not treat a red or uncollectable oracle as a reason to pause the scope, and do not ask an implementer to "fix" it. The only failures that stop a scope are the ones the Error Handling section names.

One dispatch per scope, not per task.

**Small tasks routed from `session-next`:** a single-file backlog task keeps that skill's self-written-test rule. Do not dispatch `test-author` for a 20-minute task — the overhead exceeds the benefit. This step applies when a scope holds several tasks.

### Step 3: Execute tasks in dependency order

```
0. Dispatch test-author once (Step 2); record test paths per task
while a named task in the target scope is not [x]:
  1. Find the named tasks whose dependencies are satisfied (all blockers [x])
  2. Group into: sequential (single) vs parallel (multiple ready)
  3. Check the group's write scopes do not overlap (Step 4)
  4. Dispatch accordingly (see below)
  5. On completion, mark [x] in the todo file
  6. Repeat
```

The loop ends when the named IDs are done. Tasks outside the scope keep whatever status they had.

### Step 4: Dispatch patterns

**Sequential task** (one ready task):
```
Task tool:
  subagent_type: "general-purpose"
  prompt: [task instructions from plan, including Files, Instructions, Accept, Test]
```

**Parallel tasks** (multiple ready tasks):
Send a **single message** with multiple Task tool calls:
```
Task tool #1:                          Task tool #2:
  subagent_type: "general-purpose"       subagent_type: "general-purpose"
  prompt: [task 1 instructions]          prompt: [task 2 instructions]
```

This leverages Claude Code's parallel tool execution.

Do not pass a `mode` parameter: subagents inherit the parent session's permission mode (the Task tool's `mode` was deprecated in Claude Code v2.1.212 and is ignored).

**Every dispatch payload carries the task's Files field as an explicit write boundary:**

```
You may only create or modify these paths: {Files}
If the task requires touching anything else, stop and report — do not proceed.
```

This is a prompt-level constraint, not a security boundary — nothing enforces it at the tool layer. Its value is that an agent which wanders now stops and reports instead of writing, and violations become visible. It does **not** make wrongly-parallelised tasks safe: disjoint write sets do not remove semantic dependencies, so the dependency analysis keeps its full weight.

Files entries may be exact paths or directory globs (`src/lib/governor/**`). Pass them through verbatim. Because test paths belong to `test-author` and not to any task's Files field, this also keeps implementers out of the test files for free.

**Overlapping write scopes stop the group.** Before dispatching a parallel group, compare the Files entries of its tasks — an identical path, or a path inside another task's glob, is an overlap. Do not dispatch the group and do not quietly serialise it: report the pair and the shared paths. Concurrent agents editing one file corrupt each other's work, and an overlap inside a parallel group means the plan's dependency analysis is wrong, which is the user's call to fix.

**House rules in the payload.** If `.session-flow.json` sets `paths.conventions` and the file exists, include it in implementer payloads — it is designed to be short. Read `paths.lessons` as a one-line index; load nothing further unless a line bears on the task at hand. When neither key is set, dispatch without them.

### Step 5: Per-task agent workflow

Each dispatched agent should:
1. Read referenced files first
2. Treat the pre-authored tests as the acceptance oracle — never modify a test file, and never write one
3. Implement until those tests pass
4. Run the task's specific test command
5. Report: files changed, test results, any issues

### Step 6: Optional quality gates

For complex tasks (P1, multi-file), optionally run after completion:
- `code-simplifier:code-simplifier` agent for cleanup
- `code-reviewer` agent for review

### Step 7: Progress tracking

Live progress and aggregate acceptance are two separate records. Keep them separate: per-task progress says a task's own Test passed, and only aggregate acceptance says the scope's outcome holds.

After each task completes:
1. Update the todo file: `[ ]` -> `[x]` — this marks that task's own Test as passing, nothing wider
2. Log: task ID, files changed, test result
3. Check if new parallel opportunities are unlocked among the named tasks

When every named task in the target scope is `[x]`:
1. Run the project's full test suite and the scope's own Accept checks
2. Report the aggregate verdict for the scope separately from the per-task marks. On failure, say the scope is integration-failed, name the failing checks, and leave the per-task marks as they are — they are still true
3. Report summary: the scope's task IDs, files changed, any issues, and any task in the same plan file left untouched
4. Suggest running `/session-post-implementation` for refinement

## Agent Prompt Template

When dispatching a task to an agent, use this prompt structure:

```
You are implementing task [TASK-ID] from the session plan.

## Task: [Title]

**Files to modify**: [file list]

You may only create or modify these paths. If the task requires touching
anything else, stop and report — do not proceed.

**Instructions**:
[Copy instructions from plan]

**Acceptance criteria**: [Copy from plan]

**Acceptance oracle**: the tests at [test paths from test-author] were written
for this task before implementation. Make them pass. Never modify a test file.
If a test looks wrong, stop and report it — do not edit around it.

**Test command**: [Copy from plan]

## Workflow
1. Read all referenced files first
2. Read the oracle tests to understand what the task must satisfy
3. Implement the changes
4. Run the test command and verify it passes
5. Report what you changed and the test results
```

## Error Handling

- A named ID that is missing or ambiguous, a dangling `[parallel-after:X]`, a cycle, an unmet prerequisite, or an overlapping write scope in a parallel group: stop before dispatch and report — see Step 1
- Oracle tests failing or not collecting before implementation is not a failure — see **Expected failures** in Step 2
- If an agent fails: log the error, skip the task, continue with independent tasks
- If an implementer reports a test it believes is wrong: stop that task, surface the test and the Accept criterion to the user, and fix the test with `test-author` if the user agrees — never let the implementer edit it
- If a blocking task fails: pause dependent tasks, report to user
- If tests fail after implementation: agent should iterate up to 3 times before reporting failure

Chain context: see `references/workflow-overview.md`.
