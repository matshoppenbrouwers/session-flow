---
name: session-delegation
description: Orchestrate agent execution from a session task plan. Parses dependency tags to dispatch sequential and parallel agents via the Task tool. Use after /session-task-planning produces a todo file. Triggers on "/session-delegation" or when user says "execute the tasks", "run the plan", or "dispatch the agents".
---

# Session Delegation

Orchestrate task execution from a session task plan file.

**Announce:** "Using session-delegation to orchestrate task execution from the plan."

## Prerequisites

- A task plan file produced by `/session-task-planning` with dependency tags
- The plan should have `[seq]`, `[parallel-after:X]`, and status `[ ]` tags

## Execution Algorithm

### Step 1: Parse the task plan

Read the todo file. Extract:
- Task IDs (e.g., `1A-1`, `1A-2`)
- Dependency tags (`[seq]`, `[parallel-after:X]`)
- Status (`[ ]`, `[x]`)
- Priority (`P1`, `P2`, `P3`)

Build an execution graph from the tags.

### Step 2: Execute tasks in dependency order

```
while uncompleted tasks exist:
  1. Find all tasks whose dependencies are satisfied (all blockers [x])
  2. Group into: sequential (single) vs parallel (multiple ready)
  3. Dispatch accordingly (see below)
  4. On completion, mark [x] in the todo file
  5. Repeat
```

### Step 3: Dispatch patterns

**Sequential task** (one ready task):
```
Task tool:
  subagent_type: "general-purpose"
  mode: "bypassPermissions"
  prompt: [task instructions from plan, including Files, Instructions, Accept, Test]
```

**Parallel tasks** (multiple ready tasks):
Send a **single message** with multiple Task tool calls:
```
Task tool #1:                          Task tool #2:
  subagent_type: "general-purpose"       subagent_type: "general-purpose"
  mode: "bypassPermissions"              mode: "bypassPermissions"
  prompt: [task 1 instructions]          prompt: [task 2 instructions]
```

This leverages Claude Code's parallel tool execution.

Note: `bypassPermissions` mode may not be available to all users. If not available, use `default` mode -- the user will be prompted to approve tool calls.

### Step 4: Per-task agent workflow

Each dispatched agent should:
1. Read referenced files first
2. Write tests for the acceptance criteria (TDD)
3. Implement until tests pass
4. Run the task's specific test command
5. Report: files changed, test results, any issues

### Step 5: Optional quality gates

For complex tasks (P1, multi-file), optionally run after completion:
- `code-simplifier:code-simplifier` agent for cleanup
- `code-reviewer` agent for review

### Step 6: Progress tracking

After each task completes:
1. Update the todo file: `[ ]` -> `[x]`
2. Log: task ID, files changed, test result
3. Check if new parallel opportunities are unlocked

## Agent Prompt Template

When dispatching a task to an agent, use this prompt structure:

```
You are implementing task [TASK-ID] from the session plan.

## Task: [Title]

**Files to modify**: [file list]

**Instructions**:
[Copy instructions from plan]

**Acceptance criteria**: [Copy from plan]

**Test command**: [Copy from plan]

## Workflow
1. Read all referenced files first
2. Write a test that validates the acceptance criteria
3. Implement the changes
4. Run the test command and verify it passes
5. Report what you changed and the test results
```

## Error Handling

- If an agent fails: log the error, skip the task, continue with independent tasks
- If a blocking task fails: pause dependent tasks, report to user
- If tests fail after implementation: agent should iterate up to 3 times before reporting failure

## Anti-Patterns

**Dispatching without a plan:**
- BAD: Start executing tasks without a parsed task plan file
- GOOD: Always have a `/session-task-planning` output with dependency tags before dispatching

**Not tracking progress:**
- BAD: Fire-and-forget agents without updating the todo file
- GOOD: Mark `[ ]` -> `[x]` after each task and check for newly unlocked parallel opportunities

**Ignoring parallel opportunities:**
- BAD: Run all tasks sequentially when some are independent
- GOOD: Check dependency graph -- tasks with satisfied dependencies can run in a single multi-tool message

## Workflow Integration

This skill is part of the session workflow chain:

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
  (bootstrap)       (research & design)             (break into tasks)          (this skill)              (refine and test)                  (package & ship)
```

When all tasks are `[x]`:
1. Run the project's full test suite
2. Report summary: tasks completed, files changed, any issues
3. Suggest running `/session-post-implementation` for refinement
