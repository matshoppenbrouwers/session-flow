---
name: update-architecture
description: Surgical updates and current-state initialization for the project's architecture documentation root. Ensures token-efficient edits, current data-flow and system-structure notes, architecture index hygiene, and doc splitting checks. Called by session-post-implementation when architecture docs are in scope. Triggers on "/update-architecture" or when user says "update arch docs", "sync architecture", "map current architecture", "initialize architecture docs", or "docs are out of date".
---

# Update Architecture Documentation

Maintain the project's architecture docs, wherever they live. Keep updates surgical, compact, and useful.

Throughout this skill, `{architecture}` means the resolved architecture documentation root (see below) — never a hardcoded directory.

**Announce:** "Using update-architecture for session-flow architecture documentation updates."

## Modes

Use one of two modes:

1. **Maintenance mode** — architecture docs already exist and code changed. Make surgical updates only.
2. **Current-state mode** — user explicitly asks to establish, initialize, map, or review current architecture. Create or refresh a compact architecture baseline.

When invoked by `/session-post-implementation`, default to maintenance mode.

## Architecture Doc Discovery

Resolve `{architecture}` before doing anything else, using the same order every other session-flow skill uses:

1. Read `.session-flow.json` and use `paths.architecture` if set.
2. Otherwise detect, in order: `architecture/`, `_devdocs/architecture/`, `docs/architecture/`.
3. Use whichever resolved first as `{architecture}` for the rest of the session, and state the resolved path in your first message.

Once resolved, treat `{architecture}` as the single architecture documentation location for this project — do not scatter architecture docs across other roots, and do not migrate an existing root to a different one without asking.

If `.session-flow.json` is missing and no candidate directory exists, suggest running `/session-init`.

If `{architecture}` does not exist:

- if running from `/session-post-implementation`, skip and report that architecture docs are not initialized;
- if the user explicitly asked to establish, create, map, or initialize architecture documentation, create `{architecture}` (defaulting to the configured root, else `architecture/`) and the minimal current-state architecture structure.

## Preferred Architecture Structure

Use this structure for normal projects:

```text
{architecture}/
  architecture_index.md
  system_context.md
  containers.md
  data_flows.md
  data_lineage.md
  runtime_deployment.md
  operational_processes.md
  risks_and_controls.md
  decisions.md
```

For small projects, this reduced structure is acceptable:

```text
{architecture}/
  architecture_index.md
  overview.md
  data_flows.md
  decisions.md
```

For larger projects, split by layer, domain, or flow:

```text
{architecture}/
  architecture_index.md
  frontend.md
  backend.md
  data_layer.md
  integrations.md
  background_jobs.md
  data_flows/
    import_flow.md
    sync_flow.md
    reporting_flow.md
  decisions/
    ADR-0001-source-of-truth.md
```

Prefer small focused files over one large architecture document.

## Current-State Mode Workflow

Use this when the user asks to establish, initialize, map, or review current architecture.

### Step 1: Inspect the Repository

Identify:

- major apps, packages, modules, scripts, and services;
- config files and environment variable usage;
- data stores, local storage, generated files, and external integrations;
- background jobs, scheduled jobs, CLIs, and automation entry points;
- user-facing surfaces and system-facing APIs.

Do not expose secret values. Mention only variable names and where they are used.

### Step 2: Create or Update the Architecture Index

Ensure `{architecture}/architecture_index.md` exists.

Keep it compact:

```markdown
# Architecture index

Last reviewed:
Reviewed by:
Confidence:

## System map

| Area | File | Purpose |
|---|---|---|
| System context | `system_context.md` | Users, boundaries, external systems |
| Containers | `containers.md` | Major apps, services, scripts, data stores |
| Data flows | `data_flows.md` | Important system data movement |
| Data lineage | `data_lineage.md` | Source and transformation of key outputs |
| Runtime/deployment | `runtime_deployment.md` | Hosting, jobs, config, logs, backups |
| Risks and controls | `risks_and_controls.md` | Fragile dependencies and mitigations |
| Decisions | `decisions.md` | Architecture decision records |

## Current known gaps

- ...
```

### Step 3: Document Core Views

Create or update only the views that can be supported by repository evidence.

Required current-state views:

- `system_context.md` — users, system boundary, external dependencies;
- `containers.md` — major separately maintained or separately running parts;
- `data_flows.md` — important data movement and transformation flows;
- `runtime_deployment.md` — where the system runs, configuration, jobs, logs, backups;
- `risks_and_controls.md` — fragile dependencies, failure modes, mitigation ideas;
- `decisions.md` — ADRs only where decisions are visible from code or explicitly provided by the user.

Optional views:

- `data_lineage.md` — required when the system has dashboards, reports, metrics, or derived outputs;
- `operational_processes.md` — required when human handoffs or manual steps are part of the system.

### Step 4: Mark Confidence and Gaps

Each file should include:

```text
Last reviewed:
Reviewed by:
Confidence: high / medium / low
Known gaps:
```

Use low confidence when docs are inferred from partial code inspection or when runtime/deployment details are not verifiable from the repo.

## Maintenance Mode Workflow

Use this after code changes when architecture docs already exist.

### Step 1: Identify What Changed

Use recent diffs and changed files. Prefer a small window unless the user gives a specific range.

```bash
git diff --stat HEAD~3
```

Map changed files to architecture docs and architecture views.

### Step 2: Decide Whether Architecture Docs Need Updates

Update docs when changes affect:

- system boundaries;
- external dependencies;
- data flows;
- data sources or destinations;
- business logic or calculation rules;
- authentication or authorization;
- deployment, scheduled jobs, storage, logging, monitoring, backup, or recovery;
- manual processes or operational handoffs.

If none apply, report: `Architecture docs reviewed. No architecture documentation updates required.`

### Step 3: Make Surgical Edits

Read only the section that needs updating. Edit only that section.

**DO:**

- update specific line counts when files change significantly;
- update function signatures when APIs change;
- add new entries for new modules/files;
- remove entries for deleted code;
- update status markers;
- add concise data-flow, risk, or dependency notes when behavior changes.

**DON'T:**

- rewrite entire sections when one line changes;
- add verbose explanations for simple changes;
- duplicate information across docs;
- add release-note style narrative.

Example -- adding a new tool:

```markdown
# Before
- **11 Tools**: search, get_tasks, get_recent, ...

# After
- **12 Tools**: search, get_tasks, get_recent, ..., new_tool
```

### Step 4: Update Index If Needed

Only update `architecture_index.md` when:

- a new architecture file is created;
- an architecture file is deleted or renamed;
- a quick reference section needs a new entry;
- a major feature or subsystem needs index visibility;
- known gaps materially change.

### Step 5: Check Doc Health

After updating, check architecture doc sizes:

| Lines | Action |
|-------|--------|
| <500 | Healthy |
| 500-1000 | Monitor |
| 1000-1500 | Consider splitting |
| >1500 | Split required |

## View-Specific Guidance

### System Context

Show the system boundary, users, and external dependencies. Keep this high level. Do not include internal functions.

### Containers

Document major separately maintained or separately running parts:

- frontend apps;
- backend services;
- server functions;
- scripts;
- scheduled jobs;
- databases;
- local data stores;
- file stores;
- API integrations;
- dashboards;
- report/export processes.

For each container, capture purpose, technology, location, inputs, outputs, dependencies, failure mode, and recovery path where known.

### Data Flows

Create separate flow sections or files for important processes. Label every arrow with a meaningful data object or trigger. Avoid arrows labeled only as "data".

For important flows, capture source, destination, data object, format, trigger, frequency, validation, transformation, failure mode, recovery, and owner where known.

### Data Lineage

Use when outputs, reports, dashboards, or metrics are derived from other data.

For each important output, capture business definition, source fields, transformation logic, filters, refresh frequency, validation checks, caveats, and owner where known.

### Runtime and Deployment

Capture hosting, runtime, deployment method, environment variables, secrets location without values, authentication, scheduled jobs, background tasks, file storage, logs, alerts, backups, manual deployment steps, and rollback steps where known.

### Risks and Controls

Maintain a compact risk register. Prioritize risks involving silent data corruption, incorrect outputs, broken dashboards, failed imports, unauthorized access, unrecoverable data loss, inconsistent sources of truth, fragile dependencies, and undocumented manual steps.

### Decisions

Use lightweight ADRs. Add or update ADRs when changing source-of-truth ownership, storage, deployment, authentication, external integrations, background job strategy, calculation logic, file naming/versioning, API boundaries, or frontend/backend responsibility split.

## Splitting Large Docs

When a doc exceeds 1500 lines:

1. Identify natural section boundaries.
2. Extract sections to focused files.
3. Add cross-references in the original file.
4. Update `architecture_index.md`.
5. Preserve useful content.
6. Remove duplication.

## Output Contract

At the end of an update session, produce exactly this summary. No freeform prose.

```markdown
## Architecture Doc Updates

| Doc | Before | After | Lines Δ | Change |
|-----|--------|-------|---------|--------|
| `{architecture}/containers.md` | 420 | 438 | +18 | Added background job container and dependency notes |
| `{architecture}/data_flows.md` | 287 | 292 | +5 | Updated import validation flow |
| `{architecture}/architecture_index.md` | 140 | 140 | 0 | Reviewed; no index update needed |

**Docs split:** 0
**Docs approaching threshold:** 1 (`containers.md` at 438, monitor)
**Cross-references added:** 0
**Known gaps:** 2
```

Every scanned architecture doc must be included. If no change was needed in a scanned doc, include it with `Lines Δ: 0` as evidence it was reviewed.

## Anti-Patterns

**Hardcoding the documentation root:**
- BAD: Assume a fixed root and reject a project that keeps its docs elsewhere.
- GOOD: Resolve `paths.architecture` from config (falling back to detection), then keep every doc under that one resolved root.

**Rewriting when editing:**
- BAD: Rewrite the entire "Storage Layer" section because one function changed.
- GOOD: Update the single function signature and adjust the line count.

**Narrative updates:**
- BAD: "In this release, we added a new caching layer that improves performance..."
- GOOD: Add the cache module entry with its functions, dependencies, and failure mode if relevant.

**Ignoring the index:**
- BAD: Add a new architecture file but forget to update `architecture_index.md`.
- GOOD: Always check if the index needs a new entry.

**Over-documenting implementation details:**
- BAD: Document every helper function.
- GOOD: Document system structure, data movement, important dependencies, runtime behavior, and risks.

## Workflow Integration

This skill is a supporting skill in the session-flow chain, called by `/session-post-implementation` Step 7 when architecture docs are included in the selected scope:

```text
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
                                                                                                              |
                                                                                                        /update-architecture (this skill)
```

It can also be invoked standalone when architecture docs need updating or when the user wants to establish a current-state architecture baseline.
