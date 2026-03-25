---
name: session-task-planning
description: Create Claude Code-scoped tasks with parallelization analysis. Use when breaking down a multi-step implementation into discrete tasks that can each be completed in one Claude Code session. Produces task files with dependency tags ([seq], [parallel-after:X]) and session-fit validation. Triggers on "/session-task-planning" or when user says "break this into tasks", "plan the tasks", or "create a task list".
---

# Session Task Planning

Convert implementation plans into session-scoped tasks with explicit parallelization opportunities.

**Announce:** "Using session-task-planning to break this into Claude Code session-sized tasks."

## Core Principle

Each task must be completable in **one Claude Code session** (~30 min focused work). Tasks too large get split. Tasks too small get merged.

## Task Sizing Rules

**Right-sized task:**
- Modifies 1-5 files
- Has clear acceptance criteria
- Can be tested independently
- Produces a commit

**Too large (split it):**
- Touches >5 files across domains
- Has multiple independent outcomes
- Requires context switches (backend -> frontend -> docs)
- "Do X, Y, and Z" where X, Y, Z are independent

**Too small (merge it):**
- Single-line change
- Pure formatting/linting
- No testable outcome

## Task Template

```markdown
### [PHASE-TASK] [dependency-tag] [status] P[priority]: Title
**Files**: `path/to/file.py`, `path/to/other.py:100-200`

**Instructions**:
- Read [reference] first
- Step 1 (action verb)
- Step 2 (action verb)
- Step 3 (action verb)

**Accept**: [Observable outcome that proves completion]

**Test**: `[exact command to verify]`

---
```

### Tag Reference

| Tag | Meaning |
|-----|---------|
| `[seq]` | Must complete before next task starts |
| `[parallel-after:X]` | Can run parallel with siblings after task X |
| `[x]` | Completed |
| `[plan]` | Planning phase (design not code) |
| `[ ]` | Not started |

### Priority Levels

- **P1**: Critical path, blocks other work
- **P2**: Important but not blocking
- **P3**: Nice to have, can defer

## Dependency Analysis

### Step 1: List all tasks

Write out all tasks without dependencies first.

### Step 2: Build dependency graph

For each task pair, ask:
- Does Task B need Task A's code/output?
- Do they modify the same files?
- Does Task B's test require Task A's implementation?

If any "yes" -> B depends on A.

### Step 3: Identify parallel opportunities

Tasks with same dependency can run parallel:
```
A-1 --> A-2 +---> B-1 --> C-1 +---> done
       A-3 +              C-2 +
```

Here A-2 + A-3 are parallel (both depend on A-1), C-1 + C-2 are parallel (both depend on B-1).

### Step 4: Create parallelization guide

Add ASCII diagram at top of task file:

```markdown
## Parallelization Guide

```
1A-1 --> 1A-2 +---> 1B-1 --> 1C-1 +---> done
         1A-3 +              1C-2 +
```

**Parallel opportunities:**
- 1A-2 + 1A-3 (after 1A-1 completes)
- 1C-1 + 1C-2 (after 1B-1 completes)
```

## File Structure

Save the task file to the project's **todo** directory (read path from `.session-flow.json` config, or detect `todo/`, `_devdocs/todo/`, `docs/todo/`). If not found, suggest running `/session-init`. **Never** save task files to `plans/` -- that directory is for implementation plans from `/session-research-design`.

```markdown
# Phase N: [Phase Name]

**Design Doc**: `[path to design doc]`
**Goal**: [One sentence]

Each task references the design doc -- read it first for full context.

---

## Parallelization Guide

[ASCII diagram]

[Tag legend table]

**Parallel opportunities:**
- [List explicit parallel pairs]

---

## Phase NA: [Subphase Name]

### [NA-1] [seq] [ ] P1: First task
...

### [NA-2] [parallel-after:NA-1] [ ] P1: Second task
...

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| [Criterion 1] | [How to verify] |
| [Criterion 2] | [How to verify] |
```

## Validation Checklist

Before finalizing, verify each task:

- [ ] Has all required fields (Files, Instructions, Accept, Test)
- [ ] Instructions use action verbs ("Create", "Add", "Move", not "Consider")
- [ ] Files are explicit paths, not "relevant files"
- [ ] Accept criteria is observable, not "code is clean"
- [ ] Test command is exact and runnable
- [ ] Dependency tag is correct
- [ ] Can be done in one session without external blockers

## Anti-Patterns

**Vague instructions:**
- BAD: "Improve the code structure"
- GOOD: "Extract `_convert_messages()` from server.py:200-250 into providers/openai.py"

**Unclear acceptance:**
- BAD: "Code is cleaner"
- GOOD: "`provider_type='openai'` works end-to-end via new module"

**Missing dependencies:**
- BAD: Tasks that secretly depend on each other marked as parallel
- GOOD: If B uses A's output, B has `[parallel-after:A]` or `[seq]` after A

**Too ambitious:**
- BAD: "Refactor entire backend" as one task
- GOOD: Split into focused extraction tasks

**Saving task files to plans/:**
- BAD: Task files mixed with design docs in plans/
- GOOD: Task files always go to todo/, design docs always go to plans/

## Workflow Integration

This skill is the second step in the session workflow chain:

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
  (setup project)       (research & design)          (this skill)              (execute tasks)           (refine and test)                  (version & publish)
```

**Predecessor:** Expects an implementation plan from `/session-research-design` or equivalent. If no plan exists, ask the user for one before proceeding.

**This skill produces task files.** To execute them:

1. **Sequential execution**: Work through `[seq]` tasks in order
2. **Parallel execution**: Use `/session-delegation` for parallel pairs
3. **Progress tracking**: Update `[ ]` -> `[x]` as tasks complete
4. **Intermezzo**: Run full test suite between phases
