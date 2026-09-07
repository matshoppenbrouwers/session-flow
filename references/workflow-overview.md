# Session-Flow Workflow Overview

Reference document connecting all session-flow skills. Load on-demand when you need the full picture.

---

## The Chain

```
session-init ──> gatekeeper ──> brainstorm ──> research-design ──> task-planning ──> delegation ──> post-impl ──> verify ──> release
 (one-time)      (triage)       (an idea)      (optional)                                │                       (optional,
                                                                                 update-architecture                heavy)

       work layer:  gatekeeper / add-task / brainstorm / debug ──> captured work item ──> accepted ──> groom / task-planning ──> next / delegation

       side entry:  debug ──> the cause of a bug or failing test, found and fixed
```

**Data flows left to right.** Each stage produces artifacts consumed by the next. Stages can be entered independently if their input artifacts already exist. The **work layer** runs alongside the chain: every entry path captures a work item under an identity, and `SEQUENCE.md` is the generated view of those items — read it to find work, never to change it.

## The Lifecycle Contract

Four rules hold across every skill below. They are the reason the chain is not simply "a file exists, therefore do it".

- **Capture allocates identity.** Every entry path records a work item through the runtime, in `captured`, with its own `SEQ-NNN`. Nothing downstream refers to work by filename or by date.
- **Acceptance is separate from capture.** `captured` is not executable. An authority accepts a named scope revision, and the acceptance names that revision's fingerprint. A linked breakdown file confers no eligibility, and `[auto]` is provenance, never authority.
- **Dispatch is bounded by task ID.** Delegation receives explicit task identities plus their permitted prerequisite closure. An unknown prerequisite, a cycle, an overlapping write scope, a stale claim, or changed accepted scope stops dependent dispatch.
- **Completion requires applicable evidence.** A task can pass while the parent still needs integration or delivery. The parent reaches `done` only on evidence that applies to the accepted scope; premature closure is reopened under the same identity with a correction record.

---

## Artifact Flow

| Stage | Produces | Consumed By |
|-------|----------|-------------|
| **session-init** | `.session-flow.json`, the work root and its `namespace.json`, `architecture/`, the generated `SEQUENCE.md`, CLAUDE.md/AGENTS.md sequence block | All other skills (path resolution) |
| **gatekeeper** | Triage verdicts; captured work items, or an escalation to research-design | add-task / research-design |
| **research-design** | Research report; `spec.md` and `plan.md` on the work item when the work warrants them | task-planning |
| **task-planning** | Task records under `work/seq-NNN/tasks/`, each with dependency IDs, allowed paths, and scope fingerprint | delegation |
| **add-task** | A captured work item with its original request and interpreted intent | next / groom |
| **groom** | Breakdowns attached to items still marked `(needs breakdown)`; escalations for big items | next |
| **next** | One selected and claimed item worked, its result recorded against that identity | post-implementation |
| **delegation** | Implementations for the dispatched task IDs, results recorded per task | post-implementation |
| **post-implementation** | Refined code (simplified, reviewed), test results, updated arch docs | verify (optional) or release |
| **session-verify** | Evidence against the accepted scope — criteria, code revision, environment, result, limitations — plus probes under `_verification/probes/` | release (pre-flight gate) |
| **update-architecture** | Updated architecture markdown files reflecting current code state | (consumed by humans and future sessions) |
| **release** | Version-bumped files, changelog entry, tagged commit, verified satellite content | (end of chain) |

---

## Entry Points

Not every workflow starts at `session-init`. Pick your entry based on what already exists:

| You have... | Start at | Why |
|-------------|----------|-----|
| Nothing — new project or feature | `session-init` | Creates config and directory structure |
| Incoming issues or ideas to triage | `gatekeeper` | Routes each to the sequence or a design session, grounded in direction |
| A running backlog with accepted items | `session-next` | Selects one eligible item, claims it, and works it |
| An idea, not yet a task | `session-brainstorm` | Shapes it into a short design you approve before anything is built |
| A vague idea or complex problem | `research-design` | Explores the problem space collaboratively before planning |
| A clear plan or spec | `task-planning` | Breaks the plan into session-sized executable tasks |
| Task records ready to execute | `delegation` | Dispatches the named task IDs and their permitted prerequisites |
| Code done, needs polish | `post-implementation` | Simplify, review, test, document |
| Feature/plan done, needs evidence it works | `session-verify` | Falsification-based proof artifact against design spec |
| Code polished, ready to ship | `release` | Version bump, changelog, tag, satellite verification |
| Code changed, docs stale | `update-architecture` | Surgically updates architecture docs to match code |
| A bug or failing test | `session-debug` | Finds the cause before anything is changed |

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
| **session-verify** | Bugfix, single-file change, no separate spec exists, or polish without user-facing behavior. Not skippable when the item's completion depends on evidence that a check must produce |
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

Every skill needs to find the work root and the project's documentation directories (sequence, architecture, direction). They all follow the same resolution order:

### Resolution order:
1. **Config file:** Read `.session-flow.json` in the project root. It contains explicit paths under a nested `paths` object:
   ```json
   {
     "root": "_devdocs",
     "paths": {
       "work": "_devdocs/work",
       "sequence": "_devdocs/SEQUENCE.md",
       "architecture": "_devdocs/architecture",
       "direction": "_devdocs/PRD.md"
     }
   }
   ```

   `paths.work` is the work root the runtime writes records into; `paths.sequence` is the generated
   view of it. Both may point outside the repo, for example `"work": "../work"`, when several repos
   in one parent folder share one root — resolve them relative to the repo root. Keep
   `architecture`, `direction`, `plans` and `research` inside the repo unless they are shared too.
   `todo` and `tasks` appear only in a repository that predates the work root, where they address
   historical files and nothing new is written to them.
2. **Auto-detect:** Look for common directory names at the project root:
   - Architecture: `architecture/`, `_devdocs/architecture/`, `docs/architecture/`
   - Direction: `PRD.md` / `DIRECTION.md` / `VISION.md` in the docs root, then the repo root
   - The work root and the sequence are not auto-detected by scanning: they fall back to
     `_devdocs/work` and `_devdocs/SEQUENCE.md`, so configure both when the docs root differs.
3. **Suggest init:** If neither config nor a work root exists, suggest running `/session-init` to bootstrap the project structure.

### Why this matters:
- Skills never hardcode paths — they adapt to any project layout.
- `session-init` writes `.session-flow.json` once; every subsequent skill reads it, and the runtime
  resolves the same file through `--project-root`.
- Work is addressed by `SEQ-NNN` within a namespace, so a moved or renamed file never changes which
  item a skill is talking about.

---

## Skill Interaction Patterns

### Handoff pattern
Each skill ends by suggesting the next skill in the chain. This creates a guided workflow without forcing automation:

```
session-init       → "Run /session-gatekeeper to triage issues, or /session-research-design / /session-task-planning."
brainstorm         → "Spike answered / bounded change captured / run /session-research-design."
gatekeeper         → "Trivial → captured as a work item. Significant → run /session-research-design together."
research-design    → "Run /session-task-planning to break this into tasks."
task-planning      → "Run /session-delegation with the task IDs to execute."
add-task           → "Accept it and run /session-next to implement it, or keep capturing."
groom              → "Run /session-next to work the now-ready items."
next               → "Run /session-post-implementation to polish, or /session-next again."
delegation         → "Run /session-post-implementation to polish the code."
post-implementation → "Run /session-verify (if plan/feature complete) or /session-release if ready to ship."
session-verify     → "Run /session-release if the evidence applies and passes, otherwise fix findings first."
debug              → "Cause found and fixed; run /session-post-implementation if the fix is more than a line."
```

### Work layer
Every entry path captures a work item under its own identity. The generated `SEQUENCE.md` is the view of those items:

```
gatekeeper / add-task / brainstorm / debug ──> captured ──> accepted ──> groom (prepare) ──> next / delegation (execute)
```

`/session-groom` keeps items ready (great under `/loop`), `/session-next` selects and claims one, and `/session-delegation` runs named task IDs. "Implement the next task" is wired into CLAUDE.md/AGENTS.md by `/session-init`. `/session-status` reports from the generated views, keyed by identity — never by which file is newest.

Nothing in this layer writes `SEQUENCE.md`. Skills change work items through the runtime, which regenerates the view; a hand edit there is lost at the next render.

### User gates and standing authority
An explicit request or a standing policy authorizes the actions it covers without repeated confirmation, and skills re-resolve that authority before dispatch and before consequential effects. What is escalated is an actual unknown decision, with the evidence for it — not routine reapproval. Revocation blocks new dependent actions; effects already applied stay recorded, and rolling one back needs its own authority.

Skills still pause where the decision is the user's to make:
- **research-design:** After presenting the plan, before finalizing
- **delegation:** Before dispatching, showing the task IDs and the prerequisite closure that will run
- **release:** Before the build, before satellite content updates, and on the verification reuse-or-rerun decision. Push, tag, and publish are printed as instructions, not executed

Two skills decide up front instead of pausing mid-run:
- **task-planning:** No save gate. Task records are written once every task passes the validation checklist
- **post-implementation:** Scope and add-ons are chosen in one configuration block before Step 1, so the steps then run without pausing between agents

Investigate, implement, create PR, merge, deploy, rollback, and external posting are separate permissions throughout. None of them follows from an item being accepted.

### Parallel execution
`delegation` and `research-design` both dispatch multiple agents concurrently. Delegation groups the requested task IDs by their recorded dependency IDs; each batch runs in parallel, batches run sequentially, and a request naming one task stays one task. Research-design sends its researcher dispatches in a single message.

---

## Quick Reference: Slash Commands

| Command | Skill | Purpose |
|---------|-------|---------|
| `/session-init` | session-init | Bootstrap project structure |
| `/session-gatekeeper` | session-gatekeeper | Triage incoming issues/ideas; route to sequence or design |
| `/session-research-design` | session-research-design | Explore and plan collaboratively |
| `/session-task-planning` | session-task-planning | Break plan into session-sized tasks |
| `/session-add-task` | session-add-task | Capture a work item into the backlog |
| `/session-groom` | session-groom | Research and attach breakdowns to backlog entries |
| `/session-next` | session-next | Select, claim, and work the next eligible item |
| `/session-delegation` | session-delegation | Dispatch agents against named task IDs |
| `/session-post-implementation` | session-post-implementation | Simplify, review, test |
| `/session-verify` | session-verify | Evidence-based verification against design spec |
| `/session-release` | session-release | Version bump, tag, publish |
| `/update-architecture` | update-architecture | Update architecture docs |
| `/session-status` | (command) | Report the active work item, its tasks, and the backlog |
