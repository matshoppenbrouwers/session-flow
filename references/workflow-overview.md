# Session-Flow Workflow Overview

Reference document connecting all session-flow skills. Load on-demand when you need the full picture.

---

## The Chain

```
session-init ──> gatekeeper ──> research-design ──> task-planning ──> delegation ──> post-impl ──> verify ──> release
 (one-time)      (triage)        (optional)                            │             (optional,
                                                                 update-architecture   heavy)

       sequence layer:  gatekeeper / add-task / task-planning ──> SEQUENCE.md ──> groom ──> next
```

**Data flows left to right.** Each stage produces artifacts consumed by the next. Stages can be entered independently if their input artifacts already exist. The **sequence layer** runs alongside the chain: a standing backlog (`todo/SEQUENCE.md`) that gatekeeper/add-task fill, groom prepares, and next executes.

---

## Artifact Flow

| Stage | Produces | Consumed By |
|-------|----------|-------------|
| **session-init** | `.session-flow.json`, directory structure (`todo/`, `todo/tasks/`, `architecture/`), `SEQUENCE.md`, CLAUDE.md/AGENTS.md sequence block | All other skills (path resolution) |
| **gatekeeper** | Triage verdicts; routes items to the sequence (via add-task) or to research-design | add-task / research-design |
| **research-design** | Research report, implementation plan | task-planning |
| **task-planning** | Task file with `[seq]`/`[parallel-after:X]` dependency tags, phase groupings | delegation / sequence |
| **add-task** | A `SEQUENCE.md` entry + per-task breakdown in `todo/tasks/` | next / groom |
| **groom** | Breakdowns attached to raw `(needs breakdown)` entries; escalations for big items | next |
| **next** | The next ready backlog task implemented, entry marked `[x]` | post-implementation |
| **delegation** | Completed implementations, updated task file (`[x]` markers), commit history | post-implementation |
| **post-implementation** | Refined code (simplified, reviewed), test results, updated arch docs | verify (optional) or release |
| **session-verify** | Evidence artifact `_verification/YYYY-MM-DD-{label}-verification.md` + probes under `_verification/probes/` | release (pre-flight gate) |
| **update-architecture** | Updated architecture markdown files reflecting current code state | (consumed by humans and future sessions) |
| **release** | Version-bumped files, changelog entry, tagged commit, verified satellite content | (end of chain) |

---

## Entry Points

Not every workflow starts at `session-init`. Pick your entry based on what already exists:

| You have... | Start at | Why |
|-------------|----------|-----|
| Nothing — new project or feature | `session-init` | Creates config and directory structure |
| Incoming issues or ideas to triage | `gatekeeper` | Routes each to the sequence or a design session, grounded in direction |
| A running backlog with ready items | `session-next` | Implements the next ready task from `SEQUENCE.md` |
| A vague idea or complex problem | `research-design` | Explores the problem space collaboratively before planning |
| A clear plan or spec | `task-planning` | Breaks the plan into session-sized executable tasks |
| A task file with items ready | `delegation` | Dispatches agents to execute tasks in parallel |
| Code done, needs polish | `post-implementation` | Simplify, review, test, document |
| Feature/plan done, needs evidence it works | `session-verify` | Falsification-based proof artifact against design spec |
| Code polished, ready to ship | `release` | Version bump, changelog, tag, satellite verification |
| Code changed, docs stale | `update-architecture` | Surgically updates architecture docs to match code |

---

## Skip Patterns

Some stages are optional depending on the scope of work:

| Stage | Skip when... |
|-------|-------------|
| **session-init** | Project already has `.session-flow.json` and directory structure |
| **gatekeeper** | You already know the work is in scope and aligned — capture it directly with `add-task` |
| **research-design** | Small feature (< 5 files), well-understood problem, or you already have a spec |
| **task-planning** | Single-task change, or you prefer to work sequentially without a plan |
| **delegation** | You are executing tasks manually in sequence (no parallel dispatch needed) |
| **post-implementation** | Quick fix or hotfix where polish adds more overhead than value |
| **session-verify** | Bugfix, single-file change, no design doc exists, or polish without user-facing behavior |
| **update-architecture** | No architecture docs in the project, or change doesn't affect system design |
| **release** | Not versioning the project, or change doesn't warrant a release |

**Rule of thumb:** Skip a stage when its output already exists or the change is too small to
need it. The table above says what "too small" means for each stage.

---

## Agent Dependencies

Skills dispatch agents for specialized work. Here is the mapping:

### post-implementation dispatches:
1. **code-simplifier** (Simplify step) — Simplifies recently changed code for clarity and maintainability, and removes what the implementation left behind
2. **code-reviewer** (Review step) — Finds bugs, security issues, and convention violations

### post-implementation also invokes:
3. **update-architecture** (Update Architecture Docs step) — Surgically updates architecture docs to reflect code changes

### delegation dispatches:
- **General-purpose agents** for task execution (one agent per independent task or parallel group)

### Agent override precedence:
1. Project-level agents (`.claude/agents/`) — highest priority
2. User-level agents (`~/.claude/agents/`)
3. Marketplace plugins (e.g., `code-simplifier:code-simplifier`)
4. Package-bundled agents (`session-flow/agents/`) — lowest priority

If you have a custom `code-reviewer.md` in your project's `.claude/agents/`, post-implementation uses it instead of the bundled one.

---

## Path Resolution

Every skill needs to find project directories (todo, tasks, sequence, architecture, direction). They all follow the same resolution order:

### Resolution order:
1. **Config file:** Read `.session-flow.json` in the project root. It contains explicit paths under a nested `paths` object:
   ```json
   {
     "root": "_devdocs",
     "paths": {
       "todo": "_devdocs/todo",
       "tasks": "_devdocs/todo/tasks",
       "sequence": "_devdocs/todo/SEQUENCE.md",
       "architecture": "_devdocs/architecture",
       "direction": "_devdocs/PRD.md"
     }
   }
   ```
2. **Auto-detect:** Look for common directory names at the project root:
   - Todo: `todo/`, `_devdocs/todo/`, `docs/todo/`
   - Tasks/sequence: `{todo}/tasks/`, `{todo}/SEQUENCE.md`
   - Architecture: `architecture/`, `_devdocs/architecture/`, `docs/architecture/`
   - Direction: `PRD.md` / `DIRECTION.md` / `VISION.md` in the docs root, then the repo root
3. **Suggest init:** If neither config nor directories exist, suggest running `/session-init` to bootstrap the project structure.

### Why this matters:
- Skills never hardcode paths — they adapt to any project layout.
- `session-init` writes `.session-flow.json` once; every subsequent skill reads it.
- Users who already have directories can skip init entirely.

---

## Skill Interaction Patterns

### Handoff pattern
Each skill ends by suggesting the next skill in the chain. This creates a guided workflow without forcing automation:

```
session-init       → "Run /session-gatekeeper to triage issues, or /session-research-design / /session-task-planning."
gatekeeper         → "Trivial → added to the sequence. Significant → run /session-research-design together."
research-design    → "Run /session-task-planning to break this into tasks."
task-planning      → "Run /session-delegation to execute, or register tasks in the sequence."
add-task           → "Run /session-next to implement it, or keep capturing."
groom              → "Run /session-next to work the now-ready entries."
next               → "Run /session-post-implementation to polish, or /session-next again."
delegation         → "Run /session-post-implementation to polish the code."
post-implementation → "Run /session-verify (if plan/feature complete) or /session-release if ready to ship."
session-verify     → "Run /session-release if verdict is PASS, otherwise fix findings first."
```

### Sequence (backlog) layer
The sequence is a standing list of one-line tasks (`todo/SEQUENCE.md`), each linked to a breakdown in `todo/tasks/`. It runs alongside the linear chain:

```
gatekeeper / add-task / task-planning ──> SEQUENCE.md ──> groom (prepare) ──> next (execute)
```

`/session-gatekeeper` and `/session-add-task` fill it, `/session-groom` keeps it ready (great under `/loop`), and `/session-next` works it down. "Implement the next task" is wired into CLAUDE.md/AGENTS.md by `/session-init`.

### User gates
Every skill pauses for user approval at critical decision points:
- **research-design:** After presenting the plan, before finalizing
- **task-planning:** After showing the task breakdown, before writing the file
- **delegation:** Before dispatching agents, showing what will run in parallel
- **post-implementation:** After each agent completes, before proceeding to the next step
- **release:** Before version bump, before tagging, before any publish step

### Parallel execution
`delegation` is the only skill that dispatches multiple agents concurrently. It reads `[parallel-after:X]` tags from the task file and groups independent tasks into batches. Each batch runs in parallel; batches run sequentially.

---

## Quick Reference: Slash Commands

| Command | Skill | Purpose |
|---------|-------|---------|
| `/session-init` | session-init | Bootstrap project structure |
| `/session-gatekeeper` | session-gatekeeper | Triage incoming issues/ideas; route to sequence or design |
| `/session-research-design` | session-research-design | Explore and plan collaboratively |
| `/session-task-planning` | session-task-planning | Break plan into session-sized tasks |
| `/session-add-task` | session-add-task | Capture a task into the sequence backlog |
| `/session-groom` | session-groom | Research and attach breakdowns to backlog entries |
| `/session-next` | session-next | Implement the next ready task from the backlog |
| `/session-delegation` | session-delegation | Dispatch agents to execute tasks |
| `/session-post-implementation` | session-post-implementation | Simplify, review, test |
| `/session-verify` | session-verify | Evidence-based verification against design spec |
| `/session-release` | session-release | Version bump, tag, publish |
| `/update-architecture` | update-architecture | Update architecture docs |
| `/session-status` | (command) | Check progress and next steps |
