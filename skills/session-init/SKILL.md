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
| `testing/` | Manual test plans and test results | session-post-implementation |
| `architecture/` | Architecture documentation | update-architecture |

**Important:** `todo/` is for task files only -- never put design documents there. Design documents belong in `plans/`.

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
| `testing/` | Manual test plans and test results |
| `architecture/` | Architecture docs (one per system layer) |

## Quick Navigation

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
    "testing": "<chosen-root>/testing",
    "architecture": "<chosen-root>/architecture"
  }
}
```

This config file allows all other session-flow skills to auto-discover the documentation root without hardcoding paths.

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

## Workflow Integration

```
session-init (step 0)
    |
    v
session-research-design --> plans/
    |
    v
session-task-planning --> todo/
    |
    v
session-delegation --> executes tasks
    |
    v
session-post-implementation --> testing/
    |
    v
update-architecture --> architecture/
    |
    v
session-release
```

This skill is the prerequisite for all others. It creates the directory structure and config file that the entire chain depends on. After running once, it is not needed again unless the project is restructured.
