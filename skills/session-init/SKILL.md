---
name: session-init
description: Bootstrap the project documentation structure for session-flow skills. Creates research/, plans/, todo/, testing/, and architecture/ directories. Run once when adopting session-flow in a new project. Triggers on "/session-init" or when user says "initialize project", "setup docs structure", or "bootstrap project".
---

# Session Init

Bootstrap the documentation structure that all other session-flow skills depend on.

**Announce:** "Using session-init to bootstrap the project documentation structure."

## When to Use

- First time adopting session-flow in a project
- Setting up a new repository that will use session-flow skills
- When other session-flow skills fail because they cannot find the docs root

This is **step 0** of the session-flow chain. Run it once, then never again.

## Workflow

### Step 1: Detect Existing Structure

Glob for common documentation directories:

```
_devdocs/
docs/
doc/
documentation/
```

Also check for an existing `.session-flow.json` in the project root. If it exists, read it and report the current configuration -- do not re-initialize.

### Step 2: Ask User Preference

**If no existing structure found:**
Propose a default root directory. Common choices:
- `_devdocs/` (recommended -- keeps docs out of deployed artifacts)
- `docs/`

Ask the user **one question**: "Where should I create the documentation root? Suggested: `_devdocs/`"

**If existing structure found:**
Report what was found and confirm: "Found `docs/` with existing content. Use this as the session-flow root?"

Do not dump a list of options. One question, one answer.

### Step 3: Create Subdirectories

Create these directories under the chosen root:

| Directory | Purpose | Used By |
|-----------|---------|---------|
| `research/` | Research and design documents | session-research-design |
| `plans/` | Implementation plans from research | session-research-design |
| `todo/` | Task files with dependency tags | session-task-planning |
| `todo/tasks/` | Per-task breakdown files for sequence entries | session-add-task, session-groom |
| `testing/` | Manual test plans and test results | session-post-implementation |
| `architecture/` | Architecture documentation | update-architecture |

**Important:** `todo/` is for task files only -- never put design documents there. Design documents belong in `plans/`.

### Step 3b: Create the Task Sequence

Create `{todo}/SEQUENCE.md` (only if absent) -- the backlog of one-line task entries that `session-next` works through. Use this starter content:

```markdown
# Task Sequence

Backlog of tasks to do, in roughly priority order. Each entry links to a detailed
breakdown. To work the next item, say "implement the next task" (or run /session-next).

**Legend:** `[ ]` open · `[x]` done · `[DEFERRED]` retired, id stays taken · `[auto]` after the priority = enqueued by a bot · ` ⇄ <url>` before the trailing token = same work as that external item · trailing `(needs breakdown)` = awaiting research/breakdown

Add entries with `/session-add-task` or `/session-gatekeeper`. Prepare raw ones with `/session-groom`.

<!-- Example (delete me):
- [ ] SEQ-001 P2: Short one-line task description → todo/tasks/0001-slug.md
-->
```

### Step 3c: Offer a Direction Doc (optional)

`session-gatekeeper` grounds its triage in a product-direction doc. Offer -- do not force -- to scaffold one:

"Want me to create a `PRD.md` stub for product direction in the docs root (`{root}/PRD.md`)? (Used by /session-gatekeeper. You can also point at an existing file instead.)"

- If yes and no file exists: create `{root}/PRD.md` (inside the docs root, e.g. `_devdocs/PRD.md`) with a minimal stub (vision, scope, non-goals headings).
- If the user already has a PRD/direction file: don't create one -- just record its path in `paths.direction` (Step 5).
- If the user declines: skip it; gatekeeper degrades gracefully when no direction doc exists.

### Step 3d: Offer a Conventions File (optional)

`session-research-design` designs against the project's house rules and `code-reviewer` enforces them. Offer -- do not force -- to scaffold one:

"Want me to create a `conventions.md` stub for house rules in the docs root (`{root}/conventions.md`)? (Read by /session-research-design and code-reviewer. You can also point at an existing file instead.)"

- If yes and no file exists: create `{root}/conventions.md` with a heading, a one-line format note, and no invented rules -- the user or a later `codebase-researcher` pass fills it in.
- If the user already has a conventions/house-rules file: don't create one -- just record its path in `paths.conventions` (Step 5).
- If the user declines: skip it; the design and review steps degrade gracefully and say so when no conventions file is configured.

Format for entries, stated in the stub:

```markdown
# Conventions

One rule per line, `rule — reason`, ~140 characters. The reason is mandatory: without it,
design either treats the rule as gospel or ignores it. If a rule needs more than one line,
it is an architecture decision -- record it in `architecture/decisions.md` instead.
```

`lessons.md` (conclusions drawn from past work, same one-line format) uses the same offer only if the user asks for it. Otherwise just leave `paths.lessons` pointing at the default location and let the file appear when there is something to write in it.

### Step 4: Create INDEX.md

Create `{root}/INDEX.md` with a minimal map of the structure:

```markdown
# Documentation Index

Project documentation root for session-flow skills.

## Structure

| Directory | Purpose |
|-----------|---------|
| `research/` | Research documents and design explorations |
| `plans/` | Implementation plans derived from research |
| `todo/` | Session-scoped task files with dependency tags |
| `todo/SEQUENCE.md` | Task backlog: one-line entries linked to breakdowns |
| `todo/tasks/` | Per-task breakdown files |
| `testing/` | Manual test plans and test results |
| `architecture/` | Architecture docs (one per system layer) |

## Quick Navigation

- Task backlog: `todo/SEQUENCE.md` (say "implement the next task")
- Current tasks: `todo/`
- Architecture overview: `architecture/`
- Active research: `research/`
```

Keep it under 20 lines of content. This is a signpost, not a novel.

### Step 5: Write .session-flow.json

Create `.session-flow.json` in the project root:

```json
{
  "root": "<chosen-root>",
  "paths": {
    "research": "<chosen-root>/research",
    "plans": "<chosen-root>/plans",
    "todo": "<chosen-root>/todo",
    "tasks": "<chosen-root>/todo/tasks",
    "sequence": "<chosen-root>/todo/SEQUENCE.md",
    "testing": "<chosen-root>/testing",
    "architecture": "<chosen-root>/architecture",
    "direction": "<chosen-root>/PRD.md",
    "conventions": "<chosen-root>/conventions.md",
    "lessons": "<chosen-root>/lessons.md"
  }
}
```

This config file allows all other session-flow skills to auto-discover the documentation root without hardcoding paths. `paths.direction` points at the product-direction doc used by `/session-gatekeeper` -- it defaults to `<chosen-root>/PRD.md` (inside the docs root), or set it to the user's existing PRD/direction file anywhere in the repo.

`paths.conventions` and `paths.lessons` are optional file paths, defaulting to `<chosen-root>/conventions.md` and `<chosen-root>/lessons.md`. Write them whether or not the files exist yet -- their consumers (`session-research-design`, `session-delegation`, `code-reviewer`) check for the file and say so when it is missing. Point either key at the user's existing file instead if they have one. Drop the key entirely only if the user asks you to.

### Step 5b: Wire the Sequence into CLAUDE.md and AGENTS.md

So agents consult the backlog first, insert an idempotent marked block into the project's `CLAUDE.md` and `AGENTS.md` (create either file if absent). Confirm with the user before writing, per the non-destructive rule.

Use these exact delimiters so re-running updates the block in place instead of duplicating it:

```markdown
<!-- session-flow:sequence -->
## Task Sequence

Before starting unprompted work, consult the backlog at `<sequence path>`. When asked to
"implement the next task", read SEQUENCE.md, pick the next `[ ]` entry that has a linked
breakdown, open it, execute, then mark the entry `[x]`. Use `/session-add-task` to capture
new work, `/session-groom` to fill in missing breakdowns, and `/session-gatekeeper` to triage
incoming issues.
<!-- /session-flow:sequence -->
```

If the block already exists (matched by the `<!-- session-flow:sequence -->` markers), replace its contents; otherwise append it. Substitute `<sequence path>` with the resolved sequence path. Never disturb content outside the marked block.

### Step 6: Suggest Next Step

After creation, suggest the logical next step based on the user's intent:

- Starting a new feature: "Run `/session-research-design` to explore and plan."
- Have a plan already: "Run `/session-task-planning` to break it into tasks."
- Just organizing: "Documentation structure is ready. Run any session-flow skill when needed."

## Constraints

- **Non-destructive**: Never overwrite existing files or directories. If a directory already exists, skip it and report that it was preserved.
- **User gate**: Always confirm with the user before creating anything.
- **Minimal INDEX.md**: Under 20 lines of content. Add detail later via update-architecture, not here.
- **No .gitignore modification**: The user decides what to commit.
- **Config is source of truth**: Other skills read `.session-flow.json` to find paths. If this file is missing, they should suggest running `/session-init`.

## Path Resolution Pattern

All session-flow skills should resolve the docs root using this priority:

1. Read `.session-flow.json` from project root
2. If missing, glob for common directories (`_devdocs/`, `docs/`)
3. If nothing found, suggest running `/session-init`

This skill creates the config that makes step 1 work for all other skills.

## Anti-Patterns

- **Creating directories without asking** -- Always confirm with the user first
- **Overwriting existing content** -- Existing files and directories are preserved unconditionally
- **Bloated INDEX.md** -- This is a signpost, not documentation. Keep it minimal.
- **Hardcoded paths in other skills** -- Other skills must read `.session-flow.json`, not assume `_devdocs/`
- **Running session-init repeatedly** -- If `.session-flow.json` exists, report the current config and stop
- **Putting design docs in todo/** -- `todo/` is for task files only; design docs go in `plans/`
- **Creating sample/template files** -- Only create the structure; content comes from the skills that use each directory
- **Duplicating the CLAUDE.md/AGENTS.md block** -- Match the `<!-- session-flow:sequence -->` markers and replace in place; never append a second copy
- **Forcing a PRD.md or conventions.md** -- Both are optional; offer them, and respect an existing file via `paths.direction` / `paths.conventions`
- **Seeding conventions.md with invented rules** -- The stub carries the format note and nothing else; rules come from the project, not from you

Chain context: see `references/workflow-overview.md`.
