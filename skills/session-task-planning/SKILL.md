---
name: session-task-planning
description: Break an accepted work item into Claude Code-scoped task records with parallelization analysis. Use when breaking down a multi-step implementation into discrete tasks that can each be completed in one Claude Code session. Produces one task record per task under the item's identity, each carrying its dependencies, write boundary, and criteria. Triggers on "/session-task-planning" or when user says "break this into tasks", "plan the tasks", or "create a task list".
---

# Session Task Planning

Convert an accepted work item's plan into session-scoped task records with explicit parallelization opportunities.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Every task is a record under its work item.** One file per task at `{work}/seq-NNN/tasks/<ID>.md`, written through the runtime. Never a phase file in `todo/`, never a task inside `plans/`, and never all tasks in one document.
2. **Every task carries allowed paths, instructions, criteria, and a test.** No exceptions. A task missing any of them is not valid and must be corrected before it is captured.
3. **Criteria must be observable.** "Code is cleaner" is not a criterion. `pytest tests/foo.py::test_bar passes` is.
4. **Action verbs only.** "Create", "Add", "Move", "Extract" — not "Consider", "Look into", "Think about".
5. **Every parallelism claim is tested against the file-modification graph.** Two tasks whose `allowed_paths` overlap cannot run in parallel — and dispatch will stop them, so a wrong claim here costs a run.
6. **Exact paths, not "relevant files".** `src/auth/login.py:45-120` — not "auth files".
7. **Breaking work down grants no permission to do it.** Task records are captured, not accepted. A file existing under `tasks/` is never eligibility.

## Core Principle

Each task must be completable in **one Claude Code session** (~30 min focused work). Tasks too large get split. Tasks too small get merged.

**Predecessor:** Expects an accepted work item whose design is settled — `plan.md` in the item, a linked shared plan, or `intent.md` alone for compact work. If the item is not accepted, or no plan exists, stop and say which is missing: run `/session-research-design` for the design, and let the user accept the outcome before it is broken into tasks.

## Step 0: Resolve the Runtime and the Item

Resolve the helper at `<package-root>/scripts/session-flow.py` by the one rule for this host (`references/runtime-integration.md`): `${CLAUDE_PLUGIN_ROOT}` for a native plugin, the discovered installed package location under Codex, the `session-flow-runtime.json` descriptor beside this `SKILL.md` for a standalone copy. Then read the item you are breaking down:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-042
```

Check three things in that output before planning anything:

- `result.lifecycle` is `accepted` or later. A `captured` item has not been decided on; ask for a decision rather than planning around one.
- `result.metadata.acceptance` applies to the current fingerprint. When it does not, the scope moved after acceptance: settle that first, because tasks cut from a scope nobody accepted inherit nothing.
- `result.metadata.links` and `references` name the design you are planning from. Plan from `spec.md` for behaviour and `plan.md` for order; where they disagree on behaviour, the spec wins.

**Never create a second identity.** A task that grew after investigation keeps its `SEQ` and gains the artifacts its expanded responsibility needs. Independently prioritized or separately delivered work gets its own linked `SEQ`, captured through the runtime.

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

## Task Record Shape

One record per task, captured through the runtime. `--namespace` is the UUID in the work root's `namespace.json`; the task ID is alphanumeric segments joined by hyphens, such as `A1`, giving the full identity `SEQ-042/A1`:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" --namespace "$NAMESPACE" \
  capture --seq SEQ-042 --task A2 --input task-a2.json
```

```json
{"metadata": {"title": "Add crash reconciliation", "parent": "SEQ-042", "priority": "P1", "order": 20,
   "depends_on": ["SEQ-042/A1"],
   "allowed_paths": ["scripts/session_flow/store.py", "tests/test_store.py"],
   "repositories": [{"name": "session-flow", "path": "."}]},
 "scope": "<observable criteria: what proves this task done>",
 "body": "## Instructions\n\n- Read <reference> first\n- Step 1 (action verb)\n\n## Test\n\n`<exact command>`\n"}
```

| Field | What it carries |
|-------|-----------------|
| `parent` | The owning `SEQ`. Every task names it; parent counts and indexes are derived, never typed. |
| `depends_on` | Full task identities this one needs, such as `SEQ-042/A1`. Not titles, not phase names. Omit it when there are none. |
| `allowed_paths` | The write boundary, below. |
| `repositories` | Each `{"name": ..., "path": ...}` binding this task writes in. A cross-repository task names both. |
| `priority`, `order` | `P1`/`P2`/`P3`, then `order` as the tiebreaker within one priority. |
| Scope region | The acceptance-bearing criteria. The runtime fingerprints it, so this is the text that later evidence is judged against. |
| Body | `## Instructions` and `## Test` as ordinary Markdown. Never parsed as fields — write for the agent that will read it. |
| `claim`, `result` | Helper-owned. `claim` records a bounded assignment and `record-result` records the outcome; never type either into the payload. |

**`allowed_paths` entries** may be exact paths (`src/api/routes.py`, `src/api/routes.py:100-200`) or directory globs (`src/lib/governor/**`) when a task legitimately owns a whole subtree. Still never "relevant files" — the entry has to name a footprint.

It is the **dispatch write boundary**: `/session-delegation` injects it into every agent payload as "you may only create or modify these paths", and overlapping boundaries stop dependent dispatch. An incomplete list means an agent stops mid-task and reports instead of doing the work, so list everything the task must touch. It is a prompt-level constraint the runtime checks between tasks, not an enforced sandbox — host permissions are what constrain an agent's actions.

Capture writes each record in `captured`. Creating it grants no execution permission, and neither does listing it under the parent.

### Priority Levels

- **P1**: Critical path, blocks other work
- **P2**: Important but not blocking
- **P3**: Nice to have, can defer

### Preparing Tasks Under an Accepted Parent

Editing the parent while breaking it down is preparation, not a new decision. Send the `preparation` decision with the `revise` payload so the scope check is recorded and acceptance carries across:

```json
{"expected_revision": 4,
 "metadata": {"links": [{"role": "task", "target": "tasks/A1.md"},
                        {"role": "task", "target": "tasks/A2.md"}]},
 "preparation": {"actor": "<who is planning>",
                 "authority": {"source": "<the parent's acceptance>", "revision": "<its commit>"},
                 "scope": "task preparation under the accepted outcome"}}
```

A parent with no applicable acceptance answers `missing-authority`. That is the contract working: get the outcome accepted before breaking it into tasks.

### Accepting the Breakdown

Once the user approves the breakdown, accept each task record so it can be claimed, naming the parent's acceptance as the authority:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" accept --seq SEQ-042 --task A1 --input accept-a1.json
```

A task left `captured` cannot be claimed. That is the right state for one the user has not approved — leave it there and say which tasks are waiting on a decision.

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
A1 --> A2 +---> B1 --> C1 +---> done
       A3 +           C2 +
```

Here A2 + A3 are parallel (both depend on A1), C1 + C2 are parallel (both depend on B1). Two tasks are parallel only when neither needs the other's output **and** their `allowed_paths` are disjoint.

### Step 4: Create parallelization guide

The graph belongs in the item's `plan.md`, where execution order lives. The task records carry `depends_on`, which is what the runtime reads; the diagram is for the person reading the plan, and the two must say the same thing.

```markdown
## Parallelization Guide

```
A1 --> A2 +---> B1 --> C1 +---> done
       A3 +           C2 +
```

**Parallel opportunities:**
- A2 + A3 (after A1 completes)
- C1 + C2 (after B1 completes)
```

Check the diagram against `allowed_paths` before writing it: two tasks shown as parallel whose boundaries overlap will be stopped at dispatch, not silently serialized.

## Where the Breakdown Lives

Everything sits under the one item, resolved from `paths.work` in `.session-flow.json`:

```text
{work}/seq-042/
  intent.md            # identity, accepted scope, links to the rest
  spec.md              # behaviour and design, when the work warranted one
  plan.md              # approach, order, parallelization guide
  tasks/A1.md          # one record per task, loadable on its own
  tasks/A2.md
  tasks/_index.md      # generated task view -- read it, never edit it
```

Each task record is **independently loadable**: an executor opens its own record, the shared design it links, and the results it depends on — not a phase document holding every other task. Link the shared context; never copy it into each task.

Write no phase file in `todo/` and no task in `plans/`. A repository that still has a `todo/` directory keeps it as history; nothing new goes there.

## The Sequence Is Generated

Do not append to `SEQUENCE.md` and do not offer to register anything in it. The runtime renders it from the work root:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" render
```

Every applied transition re-renders both views, so an explicit `render` is only needed after a plain `capture`, `revise`, or `accept`. An entry typed into `SEQUENCE.md` or `tasks/_index.md` is not registration — it is lost at the next render.

For a one-off follow-up that does not warrant breaking an item down, point the user to `/session-add-task` instead.

## Validation Checklist

Before finalizing, verify each task:

- [ ] Has `allowed_paths`, Instructions, a scope region, and a Test
- [ ] Instructions use action verbs ("Create", "Add", "Move", not "Consider")
- [ ] `allowed_paths` are explicit paths or directory globs, not "relevant files"
- [ ] The scope region is observable, not "code is clean"
- [ ] Test command is exact and runnable
- [ ] `depends_on` names full task identities, and no two parallel tasks share a path
- [ ] `parent` names the item, and no second identity was created
- [ ] Can be done in one session without external blockers

## Anti-Patterns

**Missing dependencies:**
- BAD: Tasks that secretly depend on each other, with `depends_on` left empty
- GOOD: If B uses A's output, B carries `"depends_on": ["SEQ-042/B-prerequisite"]`

**One document holding every task:**
- BAD: A phase file an executor must read in full to find its own three paragraphs
- GOOD: One record per task, linking the shared design

**A breakdown read as permission:**
- BAD: Capturing ten task records and dispatching them because the files now exist
- GOOD: Captured until the user approves; accepted before anything is claimed

Chain context: see `references/workflow-overview.md`.
