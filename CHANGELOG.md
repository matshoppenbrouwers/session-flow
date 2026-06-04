# Changelog

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
