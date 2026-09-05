---
name: session-delegation
description: Orchestrate agent execution from a session task plan. Parses dependency tags to dispatch sequential and parallel agents via the Task tool. Use after /session-task-planning produces a todo file. Triggers on "/session-delegation" or when user says "execute the tasks", "run the plan", or "dispatch the agents".
---

# Session Delegation

Orchestrate task execution from a session task plan file.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Never execute without a parsed task plan.** If no `/session-task-planning` output exists, stop and run that first.
2. **Respect the dependency graph.** A task with `[parallel-after:X]` where X is still `[ ]` cannot start. No exceptions.
3. **Mark `[x]` in the todo file as soon as a task completes.** Other tasks may be waiting on it. Don't batch updates.
4. **Parallel = one message with multiple Task tool calls.** Not multiple sequential messages. The whole point of parallelism is concurrent execution.
5. **Stop on blocking failure.** If a task fails and other tasks depend on it, pause the dependent branch and report to the user. Do not silently skip and continue.
6. **The acceptance tests are written before the implementers start, by a different agent, and implementers never edit them.** `test-author` writes them from the plan's Accept criteria, so the tests measure the specification rather than the implementation's own opinion of it. This is about who writes the oracle, not about designing through tests: the behaviour was fixed when the plan was approved.

## Prerequisites

- A task plan file produced by `/session-task-planning` with dependency tags
- The plan should have `[seq]`, `[parallel-after:X]`, and status `[ ]` tags

**Invoked by session-next:** When a `SEQUENCE.md` entry links to a multi-task phase file, `/session-next` hands off to this skill. After the linked phase (or anchored task) is fully `[x]`, mark the source sequence entry `[x]` in `SEQUENCE.md` too.

## Execution Algorithm

### Step 1: Parse the task plan

Read the todo file. Extract:
- Task IDs (e.g., `1A-1`, `1A-2`)
- Dependency tags (`[seq]`, `[parallel-after:X]`)
- Status (`[ ]`, `[x]`)
- Priority (`P1`, `P2`, `P3`)

Build an execution graph from the tags.

**Phase exit criterion:** every task in the todo file maps to a node in the graph with dependencies resolved. If a tag is ambiguous (e.g. `[parallel-after:X]` where X doesn't exist), stop and ask the user.

### Step 2: Author the phase's acceptance tests

**Before dispatching any of a phase's implementers**, dispatch `test-author` **once for the phase**:

```
Task tool:
  subagent_type: "test-author"
  prompt: |
    Write the acceptance tests for phase {N} of {plan path}, before implementation.

    Design artifact: {absolute path to the plan / design doc}
    Public interface: {signatures, types, and contracts the phase specifies}

    Tasks in this phase:
    - {TASK-ID}: {title} — Accept: {Accept criterion} — Test: {Test command}
    {repeat per task}

    The code does not exist yet; red is the expected outcome. Report the
    test paths you wrote, keyed by task ID.
```

Record the returned test paths **per task** — they go into each implementer's dispatch payload as its oracle. If a task comes back with no test path, note it and say so when you dispatch that task; do not invent one.

**Expected failures.** These tests fail, and some will not even collect until the tasks they depend on land. That is the expected state before implementation, not a blocking failure — do not treat a red or uncollectable oracle as a reason to pause the phase, and do not ask an implementer to "fix" it. The only failures that stop a phase are the ones the Error Handling section names.

One dispatch per phase, not per task.

**Small tasks routed from `session-next`:** a single-file backlog task keeps that skill's self-written-test rule. Do not dispatch `test-author` for a 20-minute task — the overhead exceeds the benefit. This step applies when a sequence entry links to a multi-task phase file.

### Step 3: Execute tasks in dependency order

```
for each phase:
  0. Dispatch test-author once (Step 2); record test paths per task
  while uncompleted tasks exist in this phase:
    1. Find all tasks whose dependencies are satisfied (all blockers [x])
    2. Group into: sequential (single) vs parallel (multiple ready)
    3. Dispatch accordingly (see below)
    4. On completion, mark [x] in the todo file
    5. Repeat
```

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

After each task completes:
1. Update the todo file: `[ ]` -> `[x]`
2. Log: task ID, files changed, test result
3. Check if new parallel opportunities are unlocked

When every task is `[x]`:
1. Run the project's full test suite
2. Report summary: tasks completed, files changed, any issues
3. Suggest running `/session-post-implementation` for refinement

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

- Oracle tests failing or not collecting before implementation is not a failure — see **Expected failures** in Step 2
- If an agent fails: log the error, skip the task, continue with independent tasks
- If an implementer reports a test it believes is wrong: stop that task, surface the test and the Accept criterion to the user, and fix the test with `test-author` if the user agrees — never let the implementer edit it
- If a blocking task fails: pause dependent tasks, report to user
- If tests fail after implementation: agent should iterate up to 3 times before reporting failure

Chain context: see `references/workflow-overview.md`.
