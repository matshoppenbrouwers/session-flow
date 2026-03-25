# Session-Flow Workflow Overview

Reference document connecting all session-flow skills. Load on-demand when you need the full picture.

---

## The Chain

```
session-init ──> research-design ──> task-planning ──> delegation ──> post-impl ──> release
 (one-time)       (optional)                                            │
                                                                  update-architecture
```

**Data flows left to right.** Each stage produces artifacts consumed by the next. Stages can be entered independently if their input artifacts already exist.

---

## Artifact Flow

| Stage | Produces | Consumed By |
|-------|----------|-------------|
| **session-init** | `.session-flow.json`, directory structure (`todo/`, `memory/`, `architecture/`) | All other skills (path resolution) |
| **research-design** | Research report, implementation plan, decision log entries | task-planning |
| **task-planning** | Task file with `[seq]`/`[parallel-after:X]` dependency tags, phase groupings | delegation |
| **delegation** | Completed implementations, updated task file (`[x]` markers), commit history | post-implementation |
| **post-implementation** | Refined code (simplified, reviewed, sanitized), test results, updated arch docs | release |
| **update-architecture** | Updated architecture markdown files reflecting current code state | (consumed by humans and future sessions) |
| **release** | Version-bumped files, changelog entry, tagged commit, verified satellite content | (end of chain) |

---

## Entry Points

Not every workflow starts at `session-init`. Pick your entry based on what already exists:

| You have... | Start at | Why |
|-------------|----------|-----|
| Nothing — new project or feature | `session-init` | Creates config and directory structure |
| A vague idea or complex problem | `research-design` | Explores the problem space collaboratively before planning |
| A clear plan or spec | `task-planning` | Breaks the plan into session-sized executable tasks |
| A task file with items ready | `delegation` | Dispatches agents to execute tasks in parallel |
| Code done, needs polish | `post-implementation` | Simplify, review, sanitize, test, document |
| Code polished, ready to ship | `release` | Version bump, changelog, tag, satellite verification |
| Code changed, docs stale | `update-architecture` | Surgically updates architecture docs to match code |

---

## Skip Patterns

Some stages are optional depending on the scope of work:

| Stage | Skip when... |
|-------|-------------|
| **session-init** | Project already has `.session-flow.json` and directory structure |
| **research-design** | Small feature (< 5 files), well-understood problem, or you already have a spec |
| **task-planning** | Single-task change, or you prefer to work sequentially without a plan |
| **delegation** | You are executing tasks manually in sequence (no parallel dispatch needed) |
| **post-implementation** | Quick fix or hotfix where polish adds more overhead than value |
| **update-architecture** | No architecture docs in the project, or change doesn't affect system design |
| **release** | Not versioning the project, or change doesn't warrant a release |

**Rule of thumb:** Skip a stage only if its output already exists or isn't needed. When in doubt, run it — the overhead is small and the quality gain compounds.

---

## Agent Dependencies

Skills dispatch agents for specialized work. Here is the mapping:

### post-implementation dispatches:
1. **code-simplifier** (Step 1) — Simplifies recently changed code for clarity and maintainability
2. **code-reviewer** (Step 2) — Finds bugs, security issues, and convention violations
3. **code-sanitizer** (Step 4) — Detects dead code, temporary artifacts, and cleanup opportunities

### post-implementation also invokes:
4. **update-architecture** (Step 6) — Surgically updates architecture docs to reflect code changes

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

Every skill needs to find project directories (todo, memory, architecture). They all follow the same resolution order:

### Resolution order:
1. **Config file:** Read `.session-flow.json` in the project root. It contains explicit paths:
   ```json
   {
     "todoDir": "_devdocs/todo",
     "memoryDir": "_devdocs/memory",
     "architectureDir": "_devdocs/architecture"
   }
   ```
2. **Auto-detect:** Look for common directory names at the project root:
   - Todo: `todo/`, `_devdocs/todo/`, `docs/todo/`
   - Memory: `memory/`, `_devdocs/memory/`, `docs/memory/`
   - Architecture: `architecture/`, `_devdocs/architecture/`, `docs/architecture/`
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
session-init       → "Run /session-research-design or /session-task-planning next."
research-design    → "Run /session-task-planning to break this into tasks."
task-planning      → "Run /session-delegation to execute these tasks."
delegation         → "Run /session-post-implementation to polish the code."
post-implementation → "Run /session-release if ready to ship."
```

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
| `/session-research-design` | session-research-design | Explore and plan collaboratively |
| `/session-task-planning` | session-task-planning | Break plan into session-sized tasks |
| `/session-delegation` | session-delegation | Dispatch agents to execute tasks |
| `/session-post-implementation` | session-post-implementation | Simplify, review, sanitize, test |
| `/session-release` | session-release | Version bump, tag, publish |
| `/update-architecture` | update-architecture | Update architecture docs |
| `/session-status` | (command) | Check progress and next steps |
