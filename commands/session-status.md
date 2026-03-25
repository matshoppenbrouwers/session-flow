---
name: session-status
description: Check session-flow workflow progress. Shows completed/remaining tasks, current phase, and suggests the next skill to run. Triggers on "/session-status" or when user says "where are we", "what's next", or "session progress".
allowed-tools: Read, Glob, Grep
---

# Session Status

Check the current state of the session-flow workflow and recommend the next action.

## Step 1: Find the Task File

Locate the project's task directory using this resolution order:

1. Read `.session-flow.json` in the project root for a configured `todoDir` path.
2. If no config, detect from common locations: `todo/`, `_devdocs/todo/`, `docs/todo/`.
3. If no directory found, skip to Step 4.

Within the task directory, find the most recent task file by checking:
- Filenames with date prefixes (`YYYY-MM-DD-*.md`) — pick the latest date.
- If no date prefix, pick the most recently modified `.md` file.

## Step 2: Parse Task Status

Read the task file and count status markers:

| Marker | Meaning |
|--------|---------|
| `[x]` or `[done]` | Completed |
| `[ ]` | Remaining |
| `[plan]` | Still in planning |
| `[blocked]` | Blocked by dependency |

Also detect the current phase from `### [PHASE-TASK]` headers (e.g., `SETUP`, `CORE`, `TEST`, `DOCS`).

Identify parallel opportunities: tasks tagged `[parallel-after:X]` where task X is already `[x]`.

## Step 3: Report Status

Output this summary (adjust fields based on what's available):

```
## Session Status

**Task file:** {relative path to task file}
**Progress:** {completed}/{total} tasks ({percent}%)
**Current phase:** {phase name from latest incomplete task}
**Blocked:** {count of blocked tasks, or "none"}
**Parallel opportunities:** {list of tasks that can run concurrently, or "none"}

**Next:** {recommended action — see Step 4}
```

## Step 4: Recommend Next Action

Based on the state, suggest the appropriate skill:

| State | Recommendation |
|-------|---------------|
| No task directory or task file found | "Run `/session-research-design` to explore the problem space, or `/session-task-planning` if you already have a plan." |
| Task file exists but all items are `[plan]` | "Run `/session-task-planning` to break these into executable tasks." |
| Tasks exist with `[ ]` remaining | "Continue with `/session-delegation` to execute the next batch." |
| All tasks `[x]` (100% complete) | "Run `/session-post-implementation` to simplify, review, and test." |
| Mix of `[x]` and `[blocked]` | "Unblock dependencies first. Check blocked tasks for missing prerequisites." |
