---
name: session-status
description: Check session-flow workflow progress. Shows completed/remaining tasks, current phase, and suggests the next skill to run. Triggers on "/session-status" or when user says "where are we", "what's next", or "session progress".
allowed-tools: Read, Glob, Grep
---

# Session Status

Check the current state of the session-flow workflow and recommend the next action.

## Step 1: Find the Task File

Locate the project's task directory using this resolution order:

1. Read `.session-flow.json` in the project root for the configured `paths.todo` path.
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

## Step 2b: Parse the Task Sequence

Find the backlog file via `.session-flow.json` `paths.sequence`, or detect `{todo}/SEQUENCE.md`. If present, count its one-line entries:

| Category | How to count |
|----------|--------------|
| Total | All `- [ ]` / `- [x]` entries |
| Done | `[x]` entries |
| Ready | `[ ]` entries with a `→` link to an existing breakdown |
| Needs breakdown | `[ ]` entries with trailing `(needs breakdown)` or a missing/dangling link |
| Auto | `[ ]` entries carrying an `[auto]` marker after the priority (`SEQ-011 P3 [auto]:`) |

`Auto` overlaps the other categories rather than partitioning them — a marked entry is also counted as ready or needs-breakdown. It reports how much of the open backlog arrived via unattended intake (`/session-gatekeeper`). Count 0 when nothing is marked.

If there is no sequence file, treat all counts as 0.

Keep the path you read, written as it is configured, and report it in Step 3 -- a shared backlog resolves outside the repo, so naming the file is what makes a wrong resolution visible.

## Step 3: Report Status

Output exactly this structure. Fixed fields, no substitutions.

```
## Session Status

**Task file:** {relative path to task file}
**Progress:** {completed}/{total} tasks ({percent}%)
**Current phase:** {phase name from latest incomplete task, or "n/a"}
**Blocked:** {count of blocked tasks, or "none"}
**Parallel opportunities:** {list of task IDs that can run concurrently, or "none"}
**Recent activity:** {last completed task ID and title, or "no completions yet"}
**Sequence file:** {path read, as configured, or "none found"}
**Sequence backlog:** {done}/{total} done · {ready} ready · {needs_breakdown} need breakdown · {auto} auto (or "no sequence")

**Next:** {recommended action — see Step 4}
```

Every field is required. If a field has no data, use "none", "n/a", or "0" — do not omit the field.

## Step 4: Recommend Next Action

Based on the state, suggest the appropriate skill:

Check the sequence backlog first, then the active task file:

| State | Recommendation |
|-------|---------------|
| Sequence has `ready` entries | "Run `/session-next` to implement the next task from the backlog." |
| Sequence has only `needs breakdown` entries | "Run `/session-groom` to research and break down the open entries." |
| No task directory or task file found | "Run `/session-research-design` to explore the problem space, or `/session-task-planning` if you already have a plan." |
| Task file exists but all items are `[plan]` | "Run `/session-task-planning` to break these into executable tasks." |
| Tasks exist with `[ ]` remaining | "Continue with `/session-delegation` to execute the next batch." |
| All tasks `[x]` (100% complete) | "Run `/session-post-implementation` to simplify, review, and test." |
| Mix of `[x]` and `[blocked]` | "Unblock dependencies first. Check blocked tasks for missing prerequisites." |
