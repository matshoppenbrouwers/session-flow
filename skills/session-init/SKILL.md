---
name: session-init
description: Bootstrap the project documentation structure for session-flow skills. Creates the work root with its namespace, plus research/, plans/, testing/, and architecture/ directories. Run once when adopting session-flow in a new project. Triggers on "/session-init" or when user says "initialize project", "setup docs structure", or "bootstrap project".
---

# Session Init

Bootstrap the documentation structure that all other session-flow skills depend on.

Open with one sentence saying what you are about to do and what it will produce.

## When to Use

- First time adopting session-flow in a project
- Setting up a new repository that will use session-flow skills
- When other session-flow skills fail because they cannot find the docs root

This is **step 0** of the session-flow chain. Run it once, then never again.

## Workflow

### Step 0: Resolve the Runtime

Every record session-flow creates is written by the helper at `<package-root>/scripts/session-flow.py`. Resolve it before creating anything, by the one rule for this host (`references/runtime-integration.md`):

- Native Claude plugin: the plugin root the host supplies in `${CLAUDE_PLUGIN_ROOT}`.
- Codex: the discovered installed skill and package location.
- Standalone copy: the `session-flow-runtime.json` descriptor beside this `SKILL.md`; resolve its `entrypoint` against the descriptor's own directory.

Then confirm it answers, with absolute paths for both the interpreter and the entrypoint:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
```

Read `result.protocol`, `result.record_format`, and `result.runtime`; Step 5a binds the namespace through the same entrypoint. When the interpreter is too old, report `error.detail.install` and stop; when the descriptor, the entrypoint, or a named support file is missing, report what is missing and where it was expected, and stop. Never scan the filesystem for another copy, and never fall back to writing records by hand -- there is no hand-editing path.

### Step 1: Detect Existing Structure

Glob for common documentation directories:

```
_devdocs/
docs/
doc/
documentation/
```

Also check for an existing `.session-flow.json` in the project root. If it exists, read it and report the current configuration -- do not re-initialize. Check the same way for a `namespace.json` under the configured `paths.work`: a work root that already carries a namespace is initialized, so report its namespace and stop.

If legacy sequence/task files exist but the configured work root or namespace is missing, route to `/session-repair`. Repair includes namespace and Git setup in its approved migration plan; the user does not need to run init first. Missing namespaces alongside existing records require restoration, never re-initialization.

### Step 2: Ask User Preference

**If no existing structure found:**
Propose a default root directory. Common choices:
- `_devdocs/` (recommended -- keeps docs out of deployed artifacts)
- `docs/`

Ask the user **one question**: "Where should I create the documentation root? Suggested: `_devdocs/`"

**If existing structure found:**
Report what was found and confirm: "Found `docs/` with existing content. Use this as the session-flow root?"

**Then, once the root is settled:**
Ask: "Does this repo share a work root with a parent folder? If so, give the path to that folder's work root."

When the answer is yes:
- Set `paths.work` and `paths.sequence` in Step 5 to the shared locations, written as `../` paths relative to the repo root. Leave the other keys pointing inside this repo.
- Create no second work root and no second namespace. In Step 5a, bind this repository into the shared root instead: `bind-namespace` adds it under `repositories` and leaves the root's `format` and `namespace` untouched.
- Skip Step 2b: the shared root's owner already answered the visibility question for it.
- Use the shared sequence path when you substitute into the CLAUDE.md block in Step 5b, so the wired instruction names the file that will actually be read.

Do not dump a list of options. One question, one answer.

### Step 2b: Ask the Work-Root Visibility Question -- Once

The work root is a Git repository in every supported configuration: history, backup and restore come from Git rather than from the helper. Ask this once, act on the answer, and never re-ask it per directory. The answer decides a capability, not only privacy.

Find the default before asking:

```bash
gh repo view --json isPrivate --jq .isPrivate
```

| Answer | Setup you run | Consequence you state |
|--------|---------------|-----------------------|
| Repository is private -- the default when the command reports `true` | Track the work root in this repository. If `.gitignore` matches it, remove that line and only that line. | History, backup and restore come from the existing remote, and hosted ops can read the backlog. No extra configuration. |
| Repository is public, work docs stay private | Keep the work root ignored by the outer repository and give it its own private repository, with the setup below. | Hosted ops cannot see this backlog and execution stays local: both ops workflow templates hardcode `OPS_TODO` and `OPS_SEQUENCE`, and a GitHub Actions job can only read committed files. |
| Repository is public, work docs public too | Track it in this repository, as for a private repository. | Same mechanics; the records are published. |

When `gh` is missing, unauthenticated, or the remote is not GitHub, ask with no default and say why there is none.

For the private-work-root answer, offer to run the setup rather than describing it, and run it only once the user agrees:

```bash
git -C "$WORK_ROOT" init -b main
git -C "$WORK_ROOT" add -A && git -C "$WORK_ROOT" commit -m "Initialize work records"
gh repo create "$REPO_NAME-devdocs" --private --source="$WORK_ROOT" --push
```

A Git repository inside an ignored directory is invisible to the outer one, so there is no submodule interaction.

Declining every option is allowed. Leave the work root unversioned and say plainly that backup and restore are unavailable, that applied transitions keep no history and will report there was nothing to commit, and that hosted ops cannot see the backlog. Take that from Step 5c's `doctor` rather than asserting it: `storage.versioned` is false for a root ignored by the enclosing repository, `storage.enclosing_repository` names that repository, and `storage.own_repository` separates a root with its own repository from one the enclosing repository tracks.

### Step 3: Create Subdirectories

Create these directories under the chosen root:

| Directory | Purpose | Used By |
|-----------|---------|---------|
| `research/` | Research and design documents | session-research-design |
| `plans/` | Implementation plans from research | session-research-design |
| `work/` | The work root: one directory per work item, plus `namespace.json` | the runtime, through `paths.work` |
| `testing/` | Manual test plans and test results | session-post-implementation |
| `architecture/` | Architecture documentation | update-architecture |

**Important:** create no `todo/` directory. Work items live in the work root, one directory per item, and the backlog is generated from them. An existing `todo/` in a repository adopting session-flow is history: leave it in place, keep `paths.todo` and `paths.tasks` pointing at it so those files stay findable, and write no new task file there.

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
| `work/` | Work items: one directory per SEQ, `intent.md` and whatever the work needs |
| `SEQUENCE.md` | Generated backlog view -- written by session-flow, never edited by hand |
| `testing/` | Manual test plans and test results |
| `architecture/` | Architecture docs (one per system layer) |

## Quick Navigation

- Task backlog: `SEQUENCE.md` (generated; say "implement the next task")
- Work items: `work/`
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
    "work": "<chosen-root>/work",
    "sequence": "<chosen-root>/SEQUENCE.md",
    "testing": "<chosen-root>/testing",
    "architecture": "<chosen-root>/architecture",
    "direction": "<chosen-root>/PRD.md",
    "conventions": "<chosen-root>/conventions.md",
    "lessons": "<chosen-root>/lessons.md"
  }
}
```

`paths.work` is where the runtime writes records and `paths.sequence` is the generated view of them; every session-flow command resolves both from this file through `--project-root`. Write no `todo` or `tasks` key for a new project -- there is no `todo/` directory. Add them only for a repository that already has those directories, where they address pre-existing historical files and nothing new is written to them.

This config file allows all other session-flow skills to auto-discover the documentation root without hardcoding paths. `paths.direction` points at the product-direction doc used by `/session-gatekeeper` -- it defaults to `<chosen-root>/PRD.md` (inside the docs root), or set it to the user's existing PRD/direction file anywhere in the repo.

`paths.conventions` and `paths.lessons` are optional file paths, defaulting to `<chosen-root>/conventions.md` and `<chosen-root>/lessons.md`. Write them whether or not the files exist yet -- their consumers (`session-research-design`, `session-delegation`, `code-reviewer`) check for the file and say so when it is missing. Point either key at the user's existing file instead if they have one. Drop the key entirely only if the user asks you to.

### Step 5a: Bind the Namespace

The work root carries `namespace.json`: format version, namespace UUID, and repository bindings. It is coordination configuration created with the root, not a second status registry, and every record's identity depends on it. Its contract is `references/work-item-contract.md`.

The runtime writes that file, resolving the work root from the configuration Step 5 just wrote. Run it here, and never hand-write the file:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" bind-namespace
```

`bind-namespace` creates the work root if Step 3 has not, allocates the namespace UUID, and stamps the record format this runtime reads instead of a number that silently becomes `unsupported-format` after an upgrade. Report `result.namespace`. A root that already carries one answers `created: false` and keeps its UUID: the command never reallocates a namespace, because a second one orphans every record already under that root.

When Step 2 configured a shared work root, bind this repository into that root instead of creating a second namespace. Write the binding to a JSON file and pass it:

```json
{"repository": {"name": "<repo name>", "path": "<path to this repo, relative to the work root>"}}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" bind-namespace --input "$BINDING_FILE"
```

Only `repositories` gains an entry; the shared root keeps its `format` and `namespace`. Binding the same name and path twice changes nothing, and a name already bound to another path fails with `invalid-identity` rather than overwriting it.

Create no `SEQUENCE.md` here. The sequence is generated from the work root, in Step 5c.

### Step 5b: Wire the Sequence into CLAUDE.md and AGENTS.md

So agents consult the backlog first, insert an idempotent marked block into the project's `CLAUDE.md` and `AGENTS.md` (create either file if absent). Confirm with the user before writing, per the non-destructive rule.

Use these exact delimiters so re-running updates the block in place instead of duplicating it:

```markdown
<!-- session-flow:sequence -->
## Task Sequence

Before starting unprompted work, consult the backlog at `<sequence path>`. It is generated
output: read it to find work, and never edit it. When asked to "implement the next task",
run `/session-next`, which selects one open item, claims it, and records the outcome against
its identity. Use `/session-add-task` to capture new work, `/session-groom` to fill in missing
breakdowns, and `/session-gatekeeper` to triage incoming issues.
<!-- /session-flow:sequence -->
```

If the block already exists (matched by the `<!-- session-flow:sequence -->` markers), replace its contents; otherwise append it. Substitute `<sequence path>` with the resolved sequence path -- the shared one when a shared work root was configured, so the instruction names the file that will actually be read. Never disturb content outside the marked block.

### Step 5c: Confirm the Root and Generate the Sequence

The runtime resolves `paths.work` and `paths.sequence` from `.session-flow.json`, so run these only after Step 5 has written it:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" render
```

`doctor` must report the namespace from Step 5a under `storage.namespace`; a named error there means the file is malformed, so correct it and re-run rather than proceeding. Report `storage.versioned` and any `storage.limitations` alongside the Step 2b outcome, so the user sees the versioning decision as the runtime now sees it.

`render` writes `paths.sequence` from the work root and reports `items: 0` for a fresh project. That file is generated output: the runtime writes it, no skill appends to it, and a change made only there is lost at the next `render`.

### Step 6: Suggest Next Step

After creation, suggest the logical next step based on the user's intent:

- Starting a new feature: "Run `/session-research-design` to explore and plan."
- Have a plan already: "Run `/session-task-planning` to break it into tasks."
- Just organizing: "Documentation structure is ready. Run any session-flow skill when needed."

## Constraints

- **Non-destructive**: Never overwrite existing files or directories. If a directory already exists, skip it and report that it was preserved.
- **User gate**: Always confirm with the user before creating anything.
- **Minimal INDEX.md**: Under 20 lines of content. Add detail later via update-architecture, not here.
- **Runtime first**: Resolve the helper and get an answer from `doctor` before creating anything. If it cannot answer, report what is missing and stop -- nothing falls back to hand-written records.
- **.gitignore changes only follow the answered question**: Touch `.gitignore` only to act on the Step 2b answer, and only the line matching the work root.
- **`namespace.json` belongs to the runtime**: `bind-namespace` creates it and adds bindings; never hand-write or edit it. A new namespace orphans every record already under that root.
- **The sequence is generated**: Never hand-write or hand-edit `paths.sequence`; `render` writes it from the work root.
- **Config is source of truth**: Other skills read `.session-flow.json` to find paths. If this file is missing, they should suggest running `/session-init`.
- **No local work root beside a shared one**: Never create a local work root or sequence when a shared one is configured, because a stale local copy is what a session finds first.

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
- **Creating a `todo/` directory** -- Work items live in the work root; the backlog is generated, not a directory of task files
- **Hand-writing the sequence** -- `render` produces it; anything typed there is lost at the next render
- **Asking the visibility question twice** -- One question, one answer, acted on; a shared work root inherits the owner's answer
- **Creating sample/template files** -- Only create the structure; content comes from the skills that use each directory
- **Duplicating the CLAUDE.md/AGENTS.md block** -- Match the `<!-- session-flow:sequence -->` markers and replace in place; never append a second copy
- **Forcing a PRD.md or conventions.md** -- Both are optional; offer them, and respect an existing file via `paths.direction` / `paths.conventions`
- **Seeding conventions.md with invented rules** -- The stub carries the format note and nothing else; rules come from the project, not from you

Chain context: see `references/workflow-overview.md`.
