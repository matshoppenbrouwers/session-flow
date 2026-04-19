# Changelog

## Unreleased

### Added
- **session-verify** skill — evidence-based verification workflow for completed features and plans. Produces a falsifiable proof artifact at `_verification/YYYY-MM-DD-{label}-verification.md` with fixed H2 section contract (hypotheses, structural audit, test results, defect probes, integration probes, spec-vs-reality gap, findings ledger). Runs between `/session-post-implementation` and `/session-release`; also invokable standalone.
- `/session-post-implementation` gains an optional Step 7.5 suggesting `/session-verify` after feature/plan completions.
- `/session-release` pre-flight Step 1 now checks for a PASS verification artifact when shipping features with a design doc.
- `references/customization-guide.md` Model Selection subsection documenting the inherit-by-default policy for bundled agents.

### Changed
- Bundled agents (`code-reviewer`, `code-sanitizer`, `code-simplifier`) no longer pin `model: sonnet`. They inherit the user's session model so users running Opus 4.7 (or any other tier) get subagents on the same tier automatically. Override per-agent via project-level `.claude/agents/` if you need to pin.
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
