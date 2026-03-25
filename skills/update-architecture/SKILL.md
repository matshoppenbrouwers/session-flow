---
name: update-architecture
description: Surgical updates to architecture documentation after code changes. Ensures token-efficient edits and checks if docs need splitting. Called by session-post-implementation step 6. Triggers on "/update-architecture" or when user says "update arch docs", "sync architecture", or "docs are out of date".
---

# Update Architecture Documentation

Surgical updates to architecture docs. Avoid bloat. Keep docs useful.

**Announce:** "Using update-architecture for surgical documentation updates."

## When to Use

- After implementing features that change module behavior
- After refactoring that changes file structure or APIs
- When architecture docs are out of date
- After `/session-post-implementation` or code review reveals doc gaps

## Architecture Doc Discovery

Look for architecture docs in these locations (in order):
1. `.session-flow.json` config (`paths.architecture`)
2. `_devdocs/architecture/` (with `architecture_index.md`)
3. `docs/architecture/`
4. `docs/`
5. Project root (`ARCHITECTURE.md`)

If no architecture docs exist, skip this workflow.

## Update Principles

### 1. Surgical Edits Only

**DO:**
- Update specific line counts when files change significantly
- Update function signatures when APIs change
- Add new entries for new modules/files
- Remove entries for deleted code
- Update status markers

**DON'T:**
- Rewrite entire sections when one line changes
- Add verbose explanations for simple changes
- Duplicate information across docs
- Add "narrative" about what changed

### 2. Token-Efficient Format

```markdown
# Good: Compact, scannable
- `/src/foo.py` (120 LOC) - Brief purpose
  - `function_name(param: type) -> type` - One-line description

# Bad: Verbose, wastes tokens
- `/src/foo.py` - This module provides functionality for handling foo operations.
  It was added in Phase 3 to support the new bar feature.
```

### 3. When to Update What

| Change Type | Update |
|------------|--------|
| New file | Add entry to relevant layer doc + index if new module |
| Delete file | Remove entry from layer doc + index |
| Rename file | Update path in layer doc |
| API change | Update function signature in layer doc |
| New feature | Add bullet point, not paragraph |
| LOC change >20% | Update LOC count |
| New layer/module | Add to index navigation |

## Update Workflow

### Step 1: Identify What Changed

```bash
git diff --stat HEAD~3
```

Map changed files to their architecture doc layer.

### Step 2: Make Surgical Edit

Read only the section that needs updating. Edit only that section.

Example -- adding a new tool:
```markdown
# Before
- **11 Tools**: search, get_tasks, get_recent, ...

# After (surgical -- just update the count and list)
- **12 Tools**: search, get_tasks, get_recent, ..., new_tool
```

### Step 3: Update Index If Needed

Only update the architecture index when:
- New layer doc created
- Layer doc deleted or renamed
- Quick Reference section needs new entry
- Major feature added that needs index visibility

### Step 4: Check Doc Health

After updating, check doc sizes:

| Lines | Action |
|-------|--------|
| <500 | Healthy |
| 500-1000 | Monitor |
| 1000-1500 | Consider splitting |
| >1500 | Split required |

## Splitting Large Docs

When a doc exceeds 1500 lines:

1. Identify natural section boundaries
2. Extract to new doc
3. Add cross-reference in original
4. Update index with new doc

## Anti-Patterns

**Rewriting when editing:**
- BAD: Rewrite the entire "Storage Layer" section because one function changed
- GOOD: Update the single function signature and adjust the line count

**Narrative updates:**
- BAD: "In this release, we added a new caching layer that improves performance..."
- GOOD: Add the cache module entry with its functions and line count

**Ignoring the index:**
- BAD: Add a new layer doc but forget to update the architecture index
- GOOD: Always check if the index needs a new entry

## Workflow Integration

This skill is a supporting skill in the session-flow chain, called by `/session-post-implementation` (Step 6):

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
                                                                                                              │
                                                                                                        /update-architecture (this skill)
```

It can also be invoked standalone at any time when architecture docs need updating.
