# Changelog

## 1.6.0 (2026-08-14)

1.5.0 taught session-flow to **write** the ` ⇄ <url>` provenance key; this release teaches it to **read** it first. A key only one side checks is not a dedup key — it is a label. Closes conflicts C1, C2 and C5 of the three-plugin alignment review, which measured the drift across the three plugins that parse `SEQUENCE.md`.

### Added

- **Dedup on enqueue.** `/session-add-task` scans `SEQUENCE.md` for the caller's source URL among existing ` ⇄ ` annotations *before* allocating an id: on a hit it stops, names the existing `SEQ-NNN`, and appends nothing. `/session-gatekeeper` runs the same grep before handing an item off, recording a hit as already-enqueued in the run record. This is the exclusion `/scribe-pull` already ran from the other side; run from both, the key is symmetric.
  Two double-intake paths are the reason it exists: a reopened, previously-imported issue re-triaging in CI (ops-triage skips only `scribe:mirror` and `ops-dashboard`, not `scribe:imported`), and a `scribe:ready` issue that triage *escalates* — still a `/scribe-pull` candidate, so the import files it and a later dashboard box-tick enqueues the same work again.
- **A no-title-matching anti-pattern in both skills.** Triage rewrites raw issue titles into task phrasing, so an entry's title never matches its source's — while near-matches across unrelated entries do. The URL is the only key.
- **`[DEFERRED]` is in the grammar.** It joins `/session-add-task`'s marker table, and the id rule now scans every line carrying a `SEQ` id — `[ ]`, `[x]`, and `[DEFERRED]` alike. The highest id ever used is the floor, not the highest open one; `README.md` and session-scribe already worked this way, no session-flow skill said so.
- **Id allocation's concurrency discipline is written down** in `/session-add-task`'s Provenance section and `README.md`. Four writers append with no locking: safety is at most one scheduled writer per repo, and pulling before any local edit. Both halves are load-bearing — a second bot writer, or an append to a stale local copy, reintroduces a collision no code catches.
- **`/session-init`'s starter legend covers the whole grammar** — `[DEFERRED]`, `[auto]`, and ` ⇄ <url>` alongside the checkbox states — so a new project's in-file legend matches what siblings parse.
- **A stated enqueue priority:** everything `/session-gatekeeper` enqueues is P3. Triage established that work is aligned and trivial, not that it is urgent; anything higher is a claim only the user can make. Priorities are never carried through from an issue label.

### Changed

- **`/session-groom` records escalation below the entry, not on it.** The entry line is left untouched and the escalation goes on its own HTML comment line: `<!-- session-flow: SEQ-NNN escalated to research-design YYYY-MM-DD -->`. The old `(needs research-design)` trailing tag collided with the one-trailing-token grammar session-scribe parses by — a second, unknown tag blocks its strip and hides the ` ⇄ ` annotations behind it, defeating the very key this release hardens. Comment lines are invisible to all three parsers, and `/scribe-pull` already writes its divergence markers the same way.
- **Groom skips entries carrying an escalation comment.** They are waiting on a `/session-research-design` session; re-researching them every pass broke idempotence.

### Notes

- The entry-line marker table in `/session-add-task` is now the whole grammar — every token any shipped writer emits — and states the rule the others were only implying: an entry ends in **exactly one** trailing status token (` → <link>` *or* `(needs breakdown)`), and anything that doesn't fit goes below it as an HTML comment.
- Still convention, not code. No plugin imports another's parser; the contract is documented on both sides and each works standalone.

## 1.5.0 (2026-08-14)

Closes the duplicate-entry hole that opens as soon as session-flow is not the only thing writing to `SEQUENCE.md`. 1.4.0 taught the gatekeeper to enqueue from an issue tracker; this release makes those entries recognisable to the other writers, so the same issue cannot be filed twice under two ids.

### Added

- **` ⇄ <url>` provenance annotation.** `/session-add-task` takes an optional source URL and renders it immediately before the entry's trailing status token — before the ` → ` link, or before `(needs breakdown)` in mode C. The position is load-bearing in both directions: after the link it breaks path readers, after the token it is invisible to annotation readers.
- `/session-gatekeeper` passes the item's source URL on every enqueue, alongside the `[auto]` flag and the reason. No URL means `[auto]` alone — it never invents one.
- `/session-groom` preserves annotations when it swaps `(needs breakdown)` for the breakdown link. It rewrites exactly that region, so a dropped annotation would have been silent.

`[auto]` and ` ⇄ ` are independent markers answering different questions: who put the entry in the file, and where the work came from. A gatekeeper enqueue from a GitHub issue carries both.

### Notes

- **Why a title is not a fallback.** session-scribe's `/scribe-pull` dedups imports by excluding candidates whose URL already appears as a ` ⇄ ` annotation. An entry enqueued in CI without one leaves the issue invisible to that check, so it is imported again under a second `SEQ-NNN` — and scribe's mirror then files a third item for the duplicate. Matching on titles cannot substitute: triage rewrites raw issue titles into task phrasing.
- File-format convention only. Neither plugin imports the other's code, and either works standalone; the contract is documented on both sides.
- An entry with no annotation means *not yet mirrored outward* — never *not yet checked for duplicates*. A `/scribe code` capture is filed unannotated on purpose, since a thought typed into the terminal has no outside item behind it.
- When allocating `SEQ-NNN`, count `[DEFERRED]` entries too: they hold retired ids that an active-only scan will not see.

## 1.4.0 (2026-08-12)

Completes v5 Phase 5, which 1.3.0 deliberately held back behind the SEQ-001 gatekeeper trial. That trial ran on 2026-08-12 against 14 real intake items; verdicts and findings are recorded in `todo/2026-08-12-seq-001-gatekeeper-trial.md`.

### Added
- **`[auto]` provenance marker.** `/session-add-task` takes an optional auto-provenance flag, off by default, which renders the marker immediately after the priority: `- [ ] SEQ-011 P3 [auto]: …`. Nothing else about the entry changes.
- `/session-gatekeeper` sets the flag on every item it enqueues, so an unattended intake pass is visible as one. This is the veto handle: it buys propose-don't-execute without asking the user to approve each item up front.
- `/session-groom` grooms marked entries on the same terms as any other but reports them separately in the pass summary. `/session-next` never lets `[auto]` outrank a manual entry of the same priority, and names provenance in its close-out. `/session-status` adds an `auto` count to the sequence backlog line — an overlapping count, not a partition.
- `/session-gatekeeper` **Inputs** gain the ops inbox convention: if `{paths.todo}/inbox/` exists, its `*.md` files are intake items — frontmatter is metadata, body is untrusted data — and a routed item is `git rm`'d in the same commit that records the routing. This is the companion change for the session-ops v1 spec §11; no other gatekeeper behaviour moves, and escalation formatting stays in the ops workflow prompts.

### Fixed
- **The nine gatekeeper defects the SEQ-001 trial measured** (`todo/2026-08-12-seq-001-gatekeeper-trial.md` §3), fixed as one change set in `/session-gatekeeper`:
  - The direction-doc fallback now actually runs. `paths.direction` is a hint, not a terminus: the detection chain fires when the key is unset **or** when it points at a file that does not exist, and it reaches one directory below the docs root — where the trial's real PRD sat, unread, while the run declared direction unknown. A dead `paths.direction` is now reported as a finding instead of being swallowed, and only an empty *chain* forces alignment to "unknown".
  - Cited paths are existence-checked before a breakdown is written, in both `/session-gatekeeper` and `/session-add-task`. The trial's numbers are the argument: same run, same stated confidence, 20/20 grepped source refs landed and 2/10 inferred test paths did — every `Test` command in that run would have failed at collection. Every substantive claim now carries a **verified** (`file:line`) or **assumed** marker, which is what makes an inverted guess visible as a guess.
  - Escalation is an act, not a tag. An escalated batch produces a session proposal addressed to the user — the specific question, the items it covers, near-duplicates merged — because appending `(needs research-design)` to seven lines discriminates nothing and proposes nothing.
  - Three classification holes closed: questions answerable from the code get answered (and cited) before routing rather than guessed at; `Alignment: unknown` is a hard escalate in the routing table itself, not just in the resolution prose; and a bar above the Scope axis returns anything touching database schema or a spine / canonical status field to the user regardless of size.
  - Every run leaves a durable record at `{paths.todo}/YYYY-MM-DD-gatekeeper-run.md` — verdict table, question answers, code inventory, direction-chain result — linked from whatever it escalates or enqueues. Inbox items are raw user capture: a routed one is removed, never reworded, re-headed, or folded into another.

### Notes
- `[auto]` changes the `SEQUENCE.md` line format that **session-scribe** parses by convention rather than by shared code. Both `session-add-task` and `session-gatekeeper` carry the caveat in-body: verify scribe's parser against a marked line before trusting the Notion mirror. session-scribe itself needs no changes.
- The gatekeeper fixes above are SEQ-008, broken down in `todo/2026-08-12-seq-008-gatekeeper-defects.md`. `/session-groom` and `/session-task-planning` were deliberately left out of scope: they write breakdowns too, so the path-existence rule likely belongs there as well, but that is a separate entry rather than a quiet widening of this one.

## 1.3.0 (2026-08-09)

Implements the v5 spec (`plans/2026-08-09-session-flow-v5-spec.md`): four verified defect fixes, three new agents with the workflows rewired around them, the Files field as a write boundary, conventions/lessons config, and a prescriptiveness trim across skills and agents. No breaking changes — existing artifacts, formats, and scripts keep working.

### Added
- **codebase-researcher** agent — answers one specific question about an existing codebase with `file:line` citations, explicit "not found" when it isn't there, and no recommendations. `tools: Read, Grep, Glob`, pinned to `model: sonnet` (a deliberate exception to the inherit-by-default policy, documented in the agent file).
- **external-researcher** agent — researches docs, specs, and prior art outside the repo with source-validation discipline: primary sources, publication dates, vendor claims flagged, conflicts presented rather than resolved. `tools: WebSearch, WebFetch` — no `Read`, so it cannot see the repository at all. Also pinned to `model: sonnet`.
- **test-author** agent — writes a phase's acceptance tests from the design artifact, public interface, and each task's Accept criterion **before** the implementers run, so the tests act as an external oracle rather than a post-hoc rationalization. `model: inherit`.
- `/session-delegation` dispatches `test-author` once per phase before that phase's implementers and records the produced test paths per task. Implementer prompts now say the pre-authored tests are the acceptance oracle: make them pass, never modify a test file, and stop and report if a test looks wrong. Documents the red-phase caveat — oracle tests may not collect until dependency tasks land, which is expected, not a blocking failure.
- Every delegation dispatch carries the task's **Files** field as a write boundary ("only create or modify these paths; anything else, stop and report"). It is a scoping constraint, not a security boundary. `session-task-planning`, `session-add-task`, and `session-groom` document that Files entries may be exact paths or directory globs (`src/lib/governor/**`).
- `.session-flow.json` gains optional `paths.conventions` and `paths.lessons`, defaulting to `{root}/conventions.md` and `{root}/lessons.md`. Both use one-line `rule — reason` entries (~140 chars, reason mandatory). `/session-init` offers — never forces — to scaffold `conventions.md` with the format note and no invented rules.
- `/session-research-design` reads conventions and lessons at design time and `code-reviewer` enforces conventions alongside `CLAUDE.md`. When a key is unset or the file is missing, both say so and fall back to `CLAUDE.md` plus observed patterns rather than inventing a house style. Convention departures are flagged with reasons, never blocked.
- `/session-delegation` includes the conventions file in implementer payloads when it exists, and reads lessons as a one-line index.
- README documents the seven bundled agents, the researcher model pins, the conventions/lessons schema, the Files-glob write boundary, and recommends **claude-mem** for cross-session recall — with the caveat that claude-mem and session-scribe each register a `SessionEnd` hook, so test the two together before relying on either.

### Changed
- `/session-research-design` Step 2 dispatches `codebase-researcher` and `external-researcher` (in parallel where both apply) instead of the previous ad-hoc Explore-agent prompts, and may re-dispatch `codebase-researcher` for targeted lookups mid-design.
- Research is now skippable given a recent research artifact or user-stated understanding; the plan's Context section then names what it relied on. Framing is never skipped.
- **Prescriptiveness trim**, one commit per category so anything load-bearing can be bisected back:
  - The repeated "Workflow Integration" chain diagram is gone from all 13 skills, replaced by a single pointer to `references/workflow-overview.md`. It was loaded on every invocation, carried no mid-skill decision value, and was the most drift-prone content in the repo.
  - Anti-pattern entries that merely restated a Non-Negotiable are removed; entries whose BAD case is non-obvious (e.g. task-planning's secretly-dependent-parallel) are kept.
  - `code-reviewer`'s per-language checklists (Python / React-TypeScript / Go / Java-Kotlin) are removed — current models know this material, and the lists anchored reviews to their own contents. Scope detection, the 80% confidence gate, falsification discipline, and the output contract are unchanged.
  - `code-simplifier`'s before/after code examples are removed; the action names, constraints, budget, and output contract stay.
  - `session-research-design`'s template placeholder prose is deflated to bare section lists. Every section heading survives — they are the interop contract with verify and task-planning.
  - Every format contract, `**Announce:**` line, tool budget, and prior-fighting Non-Negotiable is deliberately retained.
- `CONTRIBUTING.md` no longer mandates Anti-Patterns and Workflow Integration sections in new skills (which would have regrown the ceremony) and now asks for cross-references by step name rather than step number.
- Cross-reference drift fixed across `session-verify`, `references/workflow-overview.md`, and `references/customization-guide.md`; the README token-budget figure corrected from ~1,300 to the measured ~1,500.

### Fixed
- `/session-delegation` no longer passes the deprecated Task `mode: "bypassPermissions"` parameter (removed in Claude Code v2.1.212), which had been silently ignored. Subagents inherit the parent session's permission mode.
- `/update-architecture` resolves the architecture root from `paths.architecture` with detection fallback (`architecture/`, `_devdocs/architecture/`, `docs/architecture/`) instead of hardcoding `_devdocs/architecture/`. Projects initialized with a `docs/` root are no longer rejected.
- `/session-verify` and `/session-release` no longer key off `paths.design` — a config key `session-init` never wrote, which meant release's verification pre-flight could not fire on an initialized project. Both now resolve `paths.plans`, then `paths.research`, then detect.
- `/session-post-implementation` and `security-auditor` no longer pass plugin-relative reference paths in dispatch payloads, which did not resolve from an arbitrary project CWD. The loading skill now resolves its own plugin location and passes absolute paths; the auditor falls back to its in-file checklist summaries when they are absent.

## 1.2.1 (2026-07-16)

### Changed
- `session-next` Step 3 softens the per-task test mandate: instead of "write a test for the acceptance criteria (TDD)", it now bounds scope to the test(s) the acceptance criterion needs, prefers extending an existing test module over forking a new one, targets the pure/decision layer (not the framework, mocks, or trivial pass-throughs), and defers to the project's root `CLAUDE.md` "Test with altitude" principle where present. Keeps TDD (test as external oracle) while removing wording that drove test volume.

## 1.2.0 (2026-06-04)

### Added
- **Task sequence (backlog) layer** — a standing list of one-line task entries at `todo/SEQUENCE.md`, each linked to a self-contained breakdown in `todo/tasks/`. Say "implement the next task" and the agent picks up the next ready item. Four new skills:
  - **session-add-task** — capture a task into the sequence with a full breakdown (Files/Instructions/Accept/Test), a hand-off to `/session-task-planning` for multi-task work, or a quick `(needs breakdown)` capture.
  - **session-next** — read `SEQUENCE.md`, implement the next ready entry (or hand a multi-task entry to `/session-delegation`), and mark it `[x]`. Triggers on "implement the next task".
  - **session-groom** — research raw `(needs breakdown)` entries, verify feasibility, and attach ready-to-run breakdowns; escalates significant items to research-design. Safe to run periodically via `/loop`.
  - **session-gatekeeper** — front-of-chain intake that triages incoming issues/ideas grounded in architecture and product direction (`PRD.md`), routing trivial aligned work into the sequence and significant or divergent work to a cowork `/session-research-design` session. Triage only — never implements; treats issue text as untrusted input.
- `/session-init` now creates `todo/tasks/` and `todo/SEQUENCE.md`, optionally scaffolds a `PRD.md` direction stub in the docs root (e.g. `_devdocs/PRD.md`), and wires an idempotent `<!-- session-flow:sequence -->` block into the project's `CLAUDE.md` and `AGENTS.md` so "implement the next task" works without naming a file.
- `.session-flow.json` gains `paths.tasks`, `paths.sequence`, and `paths.direction` (defaults to a `PRD.md` in the docs root, overridable to an existing direction file).
- `/session-status` now reports sequence backlog stats (done / ready / needs-breakdown) and recommends `/session-next` or `/session-groom` accordingly.

### Changed
- `/session-task-planning` gains a "Sequence integration" step to optionally register phase tasks as backlog entries.
- `/session-delegation` documents being invoked by `/session-next` for multi-task entries and marking the source sequence entry `[x]` when its phase completes.
- Plugin manifest now lists all 13 skills; README and `references/workflow-overview.md` document the sequence layer and gatekeeper funnel.
- Corrected stale `.session-flow.json` documentation in `references/customization-guide.md` and `references/workflow-overview.md` to the actual nested `paths` schema (previously documented obsolete flat `todoDir`/`memoryDir` keys and a non-existent `memory/` layout).

## 1.1.1 (2026-04-20)

### Fixed
- Bundled agents (`code-reviewer`, `code-sanitizer`, `code-simplifier`, `security-auditor`) now declare `model: inherit` in their frontmatter so they actually run on the parent session's model. In 1.1.0 the `model` field was removed entirely on the assumption that omission caused inheritance — Claude Code instead defaults to Sonnet when the field is absent, so users on Opus 4.7 were getting Sonnet 4.6 subagents. The correct magic value is `model: inherit` (as used by e.g. the superpowers plugin).
- `CONTRIBUTING.md` agent checklist and `references/customization-guide.md` Model Selection section corrected to document the `model: inherit` requirement.

## 1.1.0 (2026-04-19)

### Added
- **session-verify** skill — evidence-based verification workflow for completed features and plans. Produces a falsifiable proof artifact at `_verification/YYYY-MM-DD-{label}-verification.md` with fixed H2 section contract (hypotheses, structural audit, test results, defect probes, integration probes, spec-vs-reality gap, findings ledger). Runs between `/session-post-implementation` and `/session-release`; also invokable standalone.
- **security-liability-audit** skill — combined technical security (LLM/AI, OWASP Top 10, secrets, agentic risks, desktop app, supply chain) and legal liability (GDPR, EU AI Act, ToS/EULA, consumer protection, cross-border data transfers) audit. Integrates into `/session-post-implementation` as optional Step 3 and runs standalone.
- **security-auditor** bundled agent — dispatched by the security & liability audit.
- `/session-post-implementation` gains a scope selector (Full / Standard / Quick) with optional add-ons, plus an optional Step 8.5 suggesting `/session-verify` after feature/plan completions.
- `/session-release` pre-flight Step 1 now checks for a PASS verification artifact when shipping features with a design doc.
- `references/customization-guide.md` Model Selection subsection documenting the inherit-by-default policy for bundled agents.
- Plugin manifest (`.claude-plugin/plugin.json`) now lists all 9 skills and 4 agents.

### Changed
- Bundled agents (`code-reviewer`, `code-sanitizer`, `code-simplifier`, `security-auditor`) no longer pin `model: sonnet`. They inherit the user's session model so users running Opus 4.7 (or any other tier) get subagents on the same tier automatically. Override per-agent via project-level `.claude/agents/` if you need to pin.
- Applied Opus 4.7 prompting patterns across existing skills and agents: non-negotiables blocks, evidence-first language, phase gates with explicit exit criteria, structured output contracts, falsification mindset for reviewers.
- `CONTRIBUTING.md` updated with new-skill checklist reflecting the Opus 4.7 patterns and revised agent frontmatter policy (do not pin `model` unless the agent has a task-specific capability requirement).

## 1.0.0 (2026-03-25)

Initial release.

### Skills
- **session-init** - Bootstrap project documentation structure
- **session-research-design** - Collaborative research and design with brainstorming
- **session-task-planning** - Dependency-aware task breakdown with parallelization
- **session-delegation** - Parallel agent dispatch from task plans
- **session-post-implementation** - Simplify, review, sanitize, test, document
- **session-release** - Version bump, artifact packaging, satellite content verification
- **update-architecture** - Surgical architecture documentation updates

### Agents
- **code-reviewer** - Finds bugs, security issues, convention violations
- **code-sanitizer** - Dead code detection and cleanup
- **code-simplifier** - Simplifies recently changed code

### Commands
- **session-status** - Check workflow progress and next steps
