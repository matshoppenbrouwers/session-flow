# Phase file: session-flow v5 implementation

**Design Doc**: `plans/2026-08-09-session-flow-v5-spec.md`
**Goal**: Implement the v5 spec — defect fixes, prescriptiveness trim, three new agents with rewiring, Files-as-boundary, conventions/lessons config, `[auto]` intake marker, docs and release.

Each task references the design doc — read the relevant section first for full context.

**User gate:** SEQ-001 (a real `/session-gatekeeper` trial run) gates Phase 5 only. The v5 migration list runs it first for everything; the file-dependency graph says only the intake tasks (5A-1, 5A-2) actually consume its outcome, so the rest may proceed. Do not start 5A-1 until the user confirms the trial.

---

## Parallelization Guide

```
1A-1 ─> 1A-2 ┐
        1A-3 ├─> 2A-1 ─> 2A-2 ─┬─> 2A-3 ─> 4A-2
        1A-4 ┘                 ├─> 2A-4
                               ├─> 3A-1 ─┬─> 3B-1
                               │         └─> 3B-2
                               ├─> 3B-3 ─> 5A-1 ─> 5A-2   (5A-1 also gated on SEQ-001)
                               └─> 4A-1
                                              └──> 6A-1 ─> 6A-2  (after all above)
```

| Tag | Meaning |
|-----|---------|
| `[seq]` | Must complete before next task starts |
| `[parallel-after:X]` | Can run parallel with siblings after task X |
| `[x]` | Completed |
| `[ ]` | Not started |

**Parallel opportunities:**
- 1A-2 + 1A-3 + 1A-4 (after 1A-1)
- 2A-3 + 2A-4 + 3A-1 + 3B-3 + 4A-1 (after 2A-2)
- 3B-1 + 3B-2 (after 3A-1)

Trim (2A-1, 2A-2) is sequential and sits between fixes and features because it touches the same 13 skill files as both.

---

## Phase 1: Verified defect fixes (v5 §3)

### [1A-1] [seq] [x] P1: Remove the deprecated Task `mode` parameter from delegation
**Files**: `skills/session-delegation/SKILL.md:58`, `:67`, `:73`

**Instructions**:
- Read v5 spec §3.1 and §6.2 first
- Delete `mode: "bypassPermissions"` from both dispatch examples (lines 58, 67)
- Delete the stale fallback note at line 73
- Add one sentence after the dispatch patterns: subagents inherit the parent session's permission mode (Task `mode` was deprecated in Claude Code v2.1.212)

**Accept**: No `bypassPermissions` reference remains in the file; the inheritance note is present.

**Test**: `! grep -q "bypassPermissions" skills/session-delegation/SKILL.md && grep -q "inherit the parent session's permission mode" skills/session-delegation/SKILL.md`

---

### [1A-2] [parallel-after:1A-1] [x] P1: De-hardcode `_devdocs` from update-architecture
**Files**: `skills/update-architecture/SKILL.md`

**Instructions**:
- Read v5 spec §3.2 first
- Rewrite the "Architecture Doc Discovery" section (lines ~24–40) to resolve `paths.architecture` from `.session-flow.json`, falling back to detection (`architecture/`, `_devdocs/architecture/`, `docs/architecture/`) — the same order every other skill uses
- Replace all prescriptive `_devdocs/architecture/` occurrences (17 in the file) with `{architecture}` placeholders; `_devdocs` may survive only inside illustrative example blocks
- Delete the anti-pattern "Using ambiguous documentation roots" or rewrite it to say "resolve from config, never hardcode"

**Accept**: The skill operates on any configured root; a project initialized with `docs/` is no longer rejected.

**Test**: `! grep -q "only architecture documentation location" skills/update-architecture/SKILL.md && [ "$(grep -c '_devdocs' skills/update-architecture/SKILL.md)" -le 3 ]`

---

### [1A-3] [parallel-after:1A-1] [x] P1: Replace phantom `paths.design` in verify and release
**Files**: `skills/session-verify/SKILL.md:35`, `skills/session-release/SKILL.md:44`

**Instructions**:
- Read v5 spec §3.3 first
- In verify Step 1, change design-doc resolution to `paths.plans` first, `paths.research` second, then directory detection (`plans/`, `_devdocs/plans/`, `docs/plans/`); remove `paths.design` and `_devdocs/design/`
- In release Step 1.4, key the verification pre-flight off `paths.plans` (or detected `plans/`) instead of `paths.design` / `_devdocs/design/`

**Accept**: Neither skill references a config key or directory that `session-init` doesn't create; release's verification gate can actually fire on an init'd project.

**Test**: `! grep -rq "paths.design\|_devdocs/design" skills/session-verify/SKILL.md skills/session-release/SKILL.md`

---

### [1A-4] [parallel-after:1A-1] [x] P1: Fix plugin-relative reference paths in dispatch payloads
**Files**: `skills/session-post-implementation/SKILL.md:112`, `agents/security-auditor.md`

**Instructions**:
- Read v5 spec §3.4 first
- In post-implementation Step 3 Mode A, change the dispatch prompt to instruct the *loading skill* to resolve its own plugin location and pass absolute reference-file paths in the payload (anchor on `${CLAUDE_PLUGIN_ROOT}` where available)
- Apply the same to Mode B's two Read steps
- In `agents/security-auditor.md`, replace the bare relative paths and the "(resolve path relative to the session-flow plugin directory)" parenthetical with: expect absolute reference paths in the dispatch payload; if absent, proceed with the checklist summaries in this file

**Accept**: A subagent dispatched from an arbitrary project CWD receives usable reference paths or an explicit degraded mode; no bare repo-relative path remains in a dispatch prompt.

**Test**: `! grep -q '"Audit the recent code changes.*skills/security-liability-audit' skills/session-post-implementation/SKILL.md`

---

## Phase 2: Prescriptiveness trim (v5 §10) — one commit per task for bisectability

### [2A-1] [seq] [x] P2: Remove Workflow Integration sections from all 13 skills
**Files**: `skills/*/SKILL.md` (13 files — deliberately over the 5-file guideline: one mechanical deletion, one category commit)

**Instructions**:
- Read v5 spec §10 first
- Delete each skill's trailing "## Workflow Integration" section (heading, diagram, prose)
- Append one line in its place: `Chain context: see references/workflow-overview.md.`
- Do not touch `references/workflow-overview.md` itself

**Accept**: Zero `## Workflow Integration` headings remain under `skills/`; each skill ends with the pointer line.

**Test**: `! grep -rq "^## Workflow Integration" skills/ && [ "$(grep -rl 'references/workflow-overview.md' skills/ | wc -l)" -eq 13 ]`

---

### [2A-2] [seq] [x] P2: Prune duplicate anti-patterns and template placeholder prose
**Files**: `skills/*/SKILL.md` (13 files — same rationale as 2A-1)

**Instructions**:
- Read v5 spec §10 first
- In each Anti-Patterns section, delete entries that restate a Non-Negotiable verbatim (e.g. add-task "Reused ids", groom "Implementing during groom"); keep entries whose BAD case is non-obvious (e.g. task-planning's secretly-dependent-parallel)
- In `session-research-design`, deflate the report/plan template placeholder prose to bare section lists; keep every section heading (they are the interop contract with verify and task-planning)
- Keep all Non-Negotiables, format contracts, and `**Announce:**` lines untouched

**Accept**: Each surviving anti-pattern adds information beyond its skill's Non-Negotiables; research-design templates keep all headings with placeholders reduced to one line each.

**Test**: `grep -rq "Announce:" skills/session-research-design/SKILL.md && grep -c "^### " skills/session-research-design/SKILL.md | xargs test 7 -le`

---

### [2A-3] [parallel-after:2A-2] [x] P2: Trim code-reviewer checklists and code-simplifier examples
**Files**: `agents/code-reviewer.md`, `agents/code-simplifier.md`

**Instructions**:
- Read v5 spec §10 first
- code-reviewer: delete the Python / React-TypeScript / Go / Java-Kotlin checklist subsections; keep Security, Project Conventions, scope detection, the 80% gate, Falsification Discipline, output format, behavioral rules
- code-simplifier: delete the before/after code examples under Simplification Actions; keep the action names with one-line descriptions, all constraints, the budget, and the output contract

**Accept**: Both agents keep every counter-prior rule and contract; language-knowledge restatements are gone.

**Test**: `! grep -q "Mutable default arguments" agents/code-reviewer.md && ! grep -q "# Before" agents/code-simplifier.md && grep -q "80%" agents/code-reviewer.md`

---

### [2A-4] [parallel-after:2A-2] [x] P2: Fix cross-reference drift; update CONTRIBUTING and README token figure
**Files**: `skills/session-verify/SKILL.md:288`, `references/workflow-overview.md`, `references/customization-guide.md`, `CONTRIBUTING.md`, `README.md`

**Instructions**:
- Read v5 spec §3.5 and §10 first
- verify: change "Step 7.5" to the step's name ("the optional verification step in post-implementation")
- workflow-overview: fix update-architecture "(Step 6)" → reference by name; delete "decision log entries" from the research-design artifact row
- customization-guide: "three agents" → four; "Step 5" test-suite references → by name
- CONTRIBUTING: remove the mandatory "Anti-Patterns section" and "Workflow Integration section" checklist items; add "cross-reference steps by name, not number"
- README: token budget ~1,300 → ~1,500

**Accept**: No literal step-number cross-references remain across the five files; CONTRIBUTING no longer mandates removed ceremony.

**Test**: `! grep -q "Step 7.5" skills/session-verify/SKILL.md && ! grep -q "decision log entries" references/workflow-overview.md && ! grep -q "bundles three agents" references/customization-guide.md`

---

## Phase 3: Agents and rewiring (v5 §4–6)

### [3A-1] [parallel-after:2A-2] [x] P1: Create the three agents and register them
**Files**: `agents/codebase-researcher.md` (new), `agents/external-researcher.md` (new), `agents/test-author.md` (new), `.claude-plugin/plugin.json`

**Instructions**:
- Read v5 spec §5.1–5.3 first — frontmatter and tool lists exactly as specified there
- codebase-researcher: `tools: Read, Grep, Glob`, `model: sonnet`, `maxTurns: 30`; body requires file:line citations, explicit "not found", no recommendations; document the sonnet pin as a deliberate inherit-policy exception
- external-researcher: `tools: WebSearch, WebFetch` — **no Read**; body carries source-validation discipline (primary sources, dates, vendor flagging, conflicts presented not resolved)
- test-author: `tools: Read, Grep, Glob, Write, Edit, Bash`, `model: inherit`, `maxTurns: 40`; body: write acceptance tests from design + public interface + Accept criteria, before implementation; state the Read limitation honestly
- Add all three to the `agents` array in `.claude-plugin/plugin.json`

**Accept**: Three agent files exist matching §5 frontmatter; plugin.json lists 7 agents; each loads standalone via `claude --agent <name>` (user-verifiable).

**Test**: `[ "$(python3 -c "import json;print(len(json.load(open('.claude-plugin/plugin.json'))['agents']))")" -eq 7 ] && ! grep -q "Read" <(grep "^tools:" agents/external-researcher.md)`

---

### [3B-1] [parallel-after:3A-1] [x] P1: Rework research-design — new agents, skip-research path, design re-dispatch, conventions/lessons
**Files**: `skills/session-research-design/SKILL.md`

**Instructions**:
- Read v5 spec §4 and §8–9 first
- Step 2: replace the three ad-hoc Explore-agent prompts with `codebase-researcher` and `external-researcher` dispatches (parallel where both apply; narrow topics reduce to one)
- Relax Non-Negotiable 3 per §4.1: research is skippable given a recent artifact or user-stated understanding; the plan's Context section then names what it relied on; framing (Step 1) is never skipped
- Steps 5–6: permit re-dispatching `codebase-researcher` for targeted lookups mid-design
- Design phase reads `paths.conventions` and `paths.lessons` when present; if unset, say so and proceed on CLAUDE.md plus observed patterns; flag convention departures with reasons, never block

**Accept**: The skill runs end-to-end with research skipped and with it included; no ad-hoc Explore prompts remain; conventions/lessons reads degrade gracefully.

**Test**: `grep -q "codebase-researcher" skills/session-research-design/SKILL.md && grep -q "external-researcher" skills/session-research-design/SKILL.md && ! grep -q "Explore agents" skills/session-research-design/SKILL.md`

---

### [3B-2] [parallel-after:3A-1] [x] P1: Rewire delegation — test-author oracle and Files-as-boundary
**Files**: `skills/session-delegation/SKILL.md`

**Instructions**:
- Read v5 spec §5.3 and §6 first
- Before dispatching a phase's implementers, dispatch `test-author` once with the design artifact, public interface, and each task's Accept criterion; record the produced test paths per task
- Replace Step 4 item 2 and prompt-template item 2 ("write a test…") with: the pre-authored tests are the acceptance oracle — make them pass, never modify a test file; if a test seems wrong, stop and report
- Inject the task's Files field into every dispatch as the write boundary: "only create or modify these paths; anything else, stop and report" — labelled as a constraint, not a security boundary
- Add the red-phase caveat: oracle tests may not collect until dependency tasks land; that is expected, not a blocking failure

**Accept**: Delegation's flow shows oracle-first per phase; no implementer prompt instructs writing tests; every dispatch payload carries the Files boundary.

**Test**: `grep -q "test-author" skills/session-delegation/SKILL.md && grep -q "never modify a test" skills/session-delegation/SKILL.md && ! grep -q "Write a test that validates" skills/session-delegation/SKILL.md`

---

### [3B-3] [parallel-after:2A-2] [x] P2: Document Files globs in the three task templates
**Files**: `skills/session-task-planning/SKILL.md`, `skills/session-add-task/SKILL.md`, `skills/session-groom/SKILL.md`

**Instructions**:
- Read v5 spec §6.1 first
- In each template's Files field documentation, state that entries may be exact paths or directory globs (e.g. `src/lib/governor/**`), and that Files doubles as the dispatch write boundary
- session-next needs no change (v5 §5.3): its small-task self-written-test rule stands

**Accept**: All three templates document glob support and the boundary role; no format grammar changed.

**Test**: `[ "$(grep -rl 'glob' skills/session-task-planning skills/session-add-task skills/session-groom | wc -l)" -eq 3 ]`

---

## Phase 4: Conventions and lessons config (v5 §8–9)

### [4A-1] [parallel-after:2A-2] [x] P2: Add `paths.conventions` and `paths.lessons` to init and the schema docs
**Files**: `skills/session-init/SKILL.md`, `references/customization-guide.md`

**Instructions**:
- Read v5 spec §8–9 first
- init: add both keys to the Step 5 config template, optional, defaulting to `{root}/conventions.md` and `{root}/lessons.md`; add a Step 3d offer (never force) to scaffold `conventions.md` with the `rule — reason` one-liner format, mirroring the PRD-stub pattern
- customization-guide: add both keys to the full schema with one-line purposes and the ~140-char `rule — reason` format note

**Accept**: Init scaffolds or skips gracefully; the documented schema matches what init writes.

**Test**: `grep -q "paths.conventions" skills/session-init/SKILL.md && grep -q "conventions" references/customization-guide.md && grep -q "paths.lessons" skills/session-init/SKILL.md`

---

### [4A-2] [parallel-after:2A-3] [x] P2: code-reviewer enforces `paths.conventions`
**Files**: `agents/code-reviewer.md`

**Instructions**:
- Read v5 spec §8 first
- In Project Conventions, add: when `.session-flow.json` defines `paths.conventions`, read that file and enforce its entries alongside CLAUDE.md

**Accept**: The reviewer's convention source includes the new file when configured; behaviour unchanged when it isn't.

**Test**: `grep -q "paths.conventions" agents/code-reviewer.md`

---

## Phase 5: Intake features — GATED on SEQ-001 (v5 §7)

### [5A-1] [parallel-after:3B-3] [ ] P3: `[auto]` provenance marker in add-task and gatekeeper
**Files**: `skills/session-add-task/SKILL.md`, `skills/session-gatekeeper/SKILL.md`

**Instructions**:
- **Do not start until the user confirms the SEQ-001 gatekeeper trial**
- Read v5 spec §7.3 first
- add-task: accept an auto-provenance flag; when set, entries render as `- [ ] SEQ-NNN P3 [auto]: …`
- gatekeeper: pass the flag when enqueuing triaged items
- Note in both bodies: session-scribe parses SEQUENCE.md by convention — the user must verify its parser against `[auto]` lines before relying on the Notion mirror

**Accept**: Gatekeeper-enqueued entries carry `[auto]`; manual add-task entries don't; the scribe caveat is documented.

**Test**: `grep -q "\[auto\]" skills/session-add-task/SKILL.md && grep -q "\[auto\]" skills/session-gatekeeper/SKILL.md`

---

### [5A-2] [parallel-after:5A-1] [ ] P3: Teach groom, next, and session-status to read `[auto]`
**Files**: `skills/session-groom/SKILL.md`, `skills/session-next/SKILL.md`, `commands/session-status.md`

**Instructions**:
- Read v5 spec §7.3 first
- groom: treat `[auto]` entries as normal groom targets but surface provenance in the pass summary
- next: `[auto]` never outranks a same-priority manual entry; mention provenance in the close-out report
- session-status: add an `auto` count to the sequence backlog line

**Accept**: All three consumers parse `[auto]` without breaking on unmarked entries.

**Test**: `[ "$(grep -rl '\[auto\]' skills/session-groom skills/session-next commands/session-status.md | wc -l)" -eq 3 ]`

---

## Phase 6: Docs and release

**Release scope:** 1.3.0 ships Phases 1–4. Phase 5 (`[auto]` intake) is still gated on SEQ-001 and is deliberately absent from the 1.3.0 README and CHANGELOG — when it lands, it needs its own entry (1.4.0) rather than an edit to 1.3.0.

### [6A-1] [seq] [x] P1: README overhaul
**Files**: `README.md`

**Instructions**:
- Read v5 spec §12.9 first
- Update: agents badge and table (7), bundled-agents section (researcher pins documented), conventions/lessons in the config example and customization section, claude-mem recommendation with the SessionEnd-coexistence caveat phrased as "test both hooks together" (no issue citation), Files-glob note in the sequence section

**Accept**: README matches shipped behaviour; no stale counts.

**Test**: `grep -q "Agents-7" README.md && grep -q "claude-mem" README.md && grep -q "conventions" README.md`

---

### [6A-2] [seq] [x] P1: CHANGELOG 1.3.0 and version bump
**Files**: `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

**Instructions**:
- Draft the 1.3.0 entry from this phase file's completed tasks, grouped Fixed / Changed / Added
- Bump `version` in both manifests to `1.3.0`
- Grep the repo for `1.2.1` — nothing should remain outside CHANGELOG history

**Accept**: Both manifests read 1.3.0; CHANGELOG entry covers every completed task.

**Test**: `grep -q '"version": "1.3.0"' .claude-plugin/plugin.json && grep -q "## 1.3.0" CHANGELOG.md`

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| All four §3 defects fixed | Tests for 1A-1..1A-4 pass |
| Trim is bisectable | One commit per Phase-2 task; `git log --oneline` shows four trim commits |
| Agents load | `claude --agent codebase-researcher` / `external-researcher` / `test-author` each start (user-run) |
| external-researcher has no repo read | `tools:` line contains no `Read` |
| Oracle flow documented end-to-end | 3B-2 test passes; session-next unchanged for small tasks |
| No format breakage | session-scribe parses a SEQUENCE.md containing one `[auto]` entry (user-run before enabling Phase 5) |
| Release consistent | 6A-2 test passes; old version grep clean |
