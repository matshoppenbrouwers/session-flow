# session-flow — Claude Code plugin for session workflow orchestration

**session-flow** is a [Claude Code](https://claude.com/claude-code) plugin that orchestrates the full software development lifecycle — a chain of **13 skills** and **7 agents** covering research, design, task planning, agent delegation, post-implementation, evidence-based verification, and release. It adds dependency-aware parallelization, a standing task backlog, collaborative brainstorming, and a security & liability audit, with user gates at every critical decision.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Skills: 13](https://img.shields.io/badge/Skills-13-green)
![Agents: 7](https://img.shields.io/badge/Agents-7-orange)

> **Install in Claude Code:** `/plugin marketplace add matshoppenbrouwers/session-flow` then `/plugin install session-flow@session-flow`

## The Chain

```
session-init ──> gatekeeper ──> research-design ──> task-planning ──> delegation ──> post-impl ──> verify ──> release
 (one-time)       (triage          (collaborative      (break into       (dispatch      (simplify,     (evidence-   (version bump,
                   intake)          brainstorming)      session tasks)    agents)        review,        based proof) package, verify)
                                                                                         audit, test)   (optional,
                                                                                            │            heavy)
                                                                                      update-architecture

sequence layer:  gatekeeper / add-task / task-planning ──> SEQUENCE.md ──> groom ──> next
```

Each skill produces artifacts that feed into the next. Start anywhere in the chain based on what you already have. The **sequence layer** runs alongside the chain: a standing backlog (`todo/SEQUENCE.md`) that gatekeeper/add-task fill, groom prepares, and next works through.

## Install

**Step 1** — Register the marketplace:
```
/plugin marketplace add matshoppenbrouwers/session-flow
```

**Step 2** — Install the plugin:
```
/plugin install session-flow@session-flow
```

Works on macOS, Linux, and Windows.

## Getting Started

1. Install session-flow (see above)
2. Run `/session-init` in Claude Code to set up your project's documentation structure
3. Start building: `/session-research-design` for new features, `/session-task-planning` if you already have a plan

## Skills

| Skill | Trigger | Produces |
|-------|---------|----------|
| **session-init** | `/session-init` | Directory structure, `SEQUENCE.md`, `.session-flow.json` config |
| **session-gatekeeper** | `/session-gatekeeper` | Triaged issues routed to the sequence or to research-design |
| **session-research-design** | `/session-research-design` | Research report + implementation plan |
| **session-task-planning** | `/session-task-planning` | Task file with dependency tags `[seq]`, `[parallel-after:X]` |
| **session-add-task** | `/session-add-task` | Sequence entry + per-task breakdown file |
| **session-groom** | `/session-groom` | Researched breakdowns attached to raw backlog entries |
| **session-next** | `/session-next` | The next backlog task implemented and marked done |
| **session-delegation** | `/session-delegation` | Completed implementations via parallel agent dispatch |
| **session-post-implementation** | `/session-post-implementation` | Refined code, security audit, test plan, updated docs |
| **session-verify** | `/session-verify` | Evidence-based verification artifact proving implementation matches design spec |
| **session-release** | `/session-release` | Versioned artifacts, updated satellite content |
| **update-architecture** | `/update-architecture` | Surgical architecture doc updates |
| **security-liability-audit** | `/security-liability-audit` | Technical security + legal liability findings |

## Entry Points

You don't have to start at step 1:

| You have... | Start with |
|-------------|------------|
| Incoming issues or ideas to triage | `/session-gatekeeper` — route them to the backlog or a design session |
| A running backlog | `/session-next` — implement the next ready task |
| A vague idea | `/session-research-design` — collaborative brainstorming refines it |
| A plan or spec | `/session-task-planning` — break it into session-sized tasks |
| A task list | `/session-delegation` — dispatch agents to execute |
| Working code that needs polish | `/session-post-implementation` — simplify, review, audit, test |
| A completed feature/plan that needs proof it works | `/session-verify` — falsification-based evidence artifact |
| Tested code ready to ship | `/session-release` — bump version, package, verify |
| A specific security concern | `/security-liability-audit` — standalone security + liability scan |

## The Chain in Practice

A typical session might look like:

```
You: /session-research-design
Claude: "What problem are we solving?" → one question at a time →
        dispatches codebase-researcher + external-researcher in parallel →
        proposes 3 approaches → presents design section by section →
        writes research report + implementation plan

You: /session-task-planning
Claude: Reads the plan → breaks into 8 tasks with dependency tags →
        identifies 3 parallel opportunities → saves to todo/

You: /session-delegation
Claude: Parses dependency graph → dispatches test-author for the phase's
        acceptance tests → dispatches 2 implementers in parallel against
        those tests → marks tasks [x] as they complete → reports progress

You: /session-post-implementation
Claude: Simplifies code → reviews for bugs → sanitizes dead code →
        runs full test suite → updates architecture docs →
        generates manual test plan

You: /session-verify   (optional — for plans/features with a design doc)
Claude: Reads design + plan → writes falsifiable hypotheses →
        runs structural audit → executes full tests → writes defect probes →
        produces evidence artifact with PASS/FAIL verdict

You: /session-release
Claude: Bumps version → waits for build → packages artifacts →
        scans docs site, website, changelog for stale content →
        presents checklist → commits release
```

## Task Sequence / Backlog

Beyond per-feature task files, session-flow keeps a standing **backlog** at `todo/SEQUENCE.md` — a flat list of one-line entries, each linking to a detailed breakdown:

```
- [ ] SEQ-007 P2: Add rate limiting to the API → todo/tasks/0007-add-rate-limit.md
- [ ] SEQ-008 P3: Investigate caching layer (needs breakdown)
- [ ] SEQ-009 P3 [auto]: Retry failed webhook deliveries → todo/tasks/0009-retry-webhooks.md
- [x] SEQ-006 P1: Fix login redirect loop → todo/tasks/0006-fix-login-redirect.md
```

`[auto]` marks an entry a skill enqueued on your behalf — `/session-gatekeeper` triage is the one shipped caller — rather than one you added yourself. It is the veto handle: marked entries sit in the backlog and can be struck on sight, so unattended intake never needs your approval up front. `/session-groom` reports them separately, `/session-next` never lets one outrank a manual entry of the same priority, and `/session-status` counts them.

Each linked breakdown in `todo/tasks/` is a self-contained, bite-sized prompt (Files / Instructions / Accept / Test) ready for an agent to execute. **Files** entries may be exact paths (`src/api/routes.py`) or directory globs (`src/lib/governor/**`) when a task owns a whole subtree — and the field doubles as the write boundary: `/session-delegation` injects it into every dispatch as "you may only create or modify these paths."

| Want to... | Use |
|------------|-----|
| Capture something for later | `/session-add-task` — adds an entry + breakdown |
| Implement the next item | `/session-next` — or just say "implement the next task" |
| Prepare raw one-liners | `/session-groom` — researches and attaches breakdowns |

`session-init` wires a `<!-- session-flow:sequence -->` block into your `CLAUDE.md` and `AGENTS.md` so "implement the next task" works without naming a file. Pair grooming with the built-in `/loop` for hands-off upkeep:

```
/loop 30m /session-groom
```

### Gatekeeper / Intake

`/session-gatekeeper` is the front-of-chain funnel for incoming work — GitHub issues, feature requests, or ideas that surface mid-session. It grounds each item in your architecture docs and product direction (a `PRD.md` in the docs root by default, configurable via `paths.direction`), then routes it:

- **Touches database schema or a spine / canonical status field** → back to you regardless of size.
- **Unknown alignment** → escalated. If the direction could not be established, nothing is auto-added.
- **Trivial, aligned, and clear** → straight into the sequence via `session-add-task`, marked `[auto]`.
- **Significant, divergent, or unclear** → escalated to a cowork `/session-research-design` session with you.
- **Off-direction** → flagged for your explicit decision.

Escalation is an act, not an annotation: an escalated batch produces a named session proposal — the question to answer, the items it covers, near-duplicates merged — addressed to you in the run's output. A question the code can answer gets answered and cited before it is routed, every cited path is existence-checked before a breakdown is written, and each run leaves a dated record at `{todo}/YYYY-MM-DD-gatekeeper-run.md`.

It triages only — it never implements, and it treats issue text as untrusted data rather than instructions. It pairs with `/loop` for periodic issue intake, queuing anything significant for you rather than auto-processing it.

## Post-Implementation Workflow

`/session-post-implementation` runs up to 9 steps. At the start, it asks which scope to use:

| Step | Full | Standard | Quick |
|------|------|----------|-------|
| 1. Simplify | yes | yes | yes |
| 2. Code review | yes | yes | yes |
| 3. Security & liability audit | yes | - | - |
| 4. Commit checkpoint | yes | yes | yes |
| 5. Sanitize | yes | yes | - |
| 6. Test suite | yes | yes | - |
| 7. Architecture docs | yes | - | - |
| 8. Manual test plan | yes | - | - |
| 9. Final commit | yes | yes | - |

Standard and Quick scopes can add individual steps as extras (e.g., Quick + architecture docs). Verification (`/session-verify`) is always optional and can be invoked after Full completion.

When the security audit is included, you choose how it runs:
- **Sub-agent** — dispatches an agent (faster, lower cost)
- **Inline** — runs in the main conversation with your current model (more thorough)

### Security & Liability Audit

The audit covers two dimensions:

**Technical security** — LLM/AI security (prompt injection, unsanitized output, tool validation), OWASP Top 10, secrets detection, agentic security (Lethal Trifecta), desktop app security, dependency supply chain, webhook/integration security. Findings use confidence-based filtering (80% gate) to avoid noise.

**Legal liability** — ToS/EULA coverage gaps, GDPR compliance (privacy policy, DPAs, data retention, user rights), EU AI Act obligations (risk classification, transparency), Digital Content Directive (conformity, updates), consumer protection (withdrawal, pricing, cancellation), AI output disclaimers, cross-border data transfer requirements. Designed for EU-based developers with a worldwide userbase.

The audit can also run standalone via `/security-liability-audit`.

## Bundled Agents

| Agent | Used By | Purpose |
|-------|---------|---------|
| **codebase-researcher** | research-design (research + design phases) | Answer one question about the existing code, with file:line citations. Read-only |
| **external-researcher** | research-design (research phase) | Research docs, specs, and prior art outside the repo, with source validation. No repo access |
| **test-author** | delegation (once per phase, before implementers) | Write the acceptance tests that become the implementers' oracle |
| **code-simplifier** | post-impl step 1 | Simplify recently changed code |
| **code-reviewer** | post-impl step 2 | Find bugs, security issues, convention violations |
| **security-auditor** | post-impl step 3 | Technical security + legal liability audit |
| **code-sanitizer** | post-impl step 5 | Detect dead code and temporary artifacts |

Bundled agents inherit the parent session's model — an Opus 4.7 session gets Opus 4.7 subagents, a Sonnet session gets Sonnet. Two deliberate exceptions: `codebase-researcher` and `external-researcher` pin `model: sonnet`, because both do bounded read-and-report work where the frontier tier buys nothing and the dispatch count is high. Override either by placing your own version in `.claude/agents/`.

Subagents also inherit the parent session's permission mode. `external-researcher` has no `Read` tool at all — it cannot see your repository, only the sources it fetches.

If you have the marketplace `code-simplifier:code-simplifier` plugin installed, session-post-implementation uses it automatically instead of the bundled agent.

## Customization

session-flow adapts to your project via `.session-flow.json` (created by `/session-init`):

```json
{
  "root": "_devdocs",
  "paths": {
    "research": "_devdocs/research",
    "plans": "_devdocs/plans",
    "todo": "_devdocs/todo",
    "tasks": "_devdocs/todo/tasks",
    "sequence": "_devdocs/todo/SEQUENCE.md",
    "testing": "_devdocs/testing",
    "architecture": "_devdocs/architecture",
    "direction": "_devdocs/PRD.md",
    "conventions": "_devdocs/conventions.md",
    "lessons": "_devdocs/lessons.md"
  }
}
```

`paths.direction` points `/session-gatekeeper` at your product-direction doc. It defaults to a `PRD.md` inside the docs root (e.g. `_devdocs/PRD.md`) — let `/session-init` scaffold it, or set this to an existing PRD/vision file anywhere in the repo.

`paths.conventions` and `paths.lessons` are optional one-line-entry files, both in the same `rule — reason` format (~140 characters, reason mandatory):

```
Repository methods return domain objects, never ORM rows — keeps persistence swappable and out of the service layer.
```

**Conventions** are house rules: `/session-research-design` loads them at design time and `code-reviewer` enforces them alongside `CLAUDE.md`. **Lessons** are conclusions drawn after the fact, read as a one-line index by research-design and delegation. Both are kept out of `CLAUDE.md` on purpose — that file costs tokens on every turn of every session, while these matter only at design and review time. If a rule doesn't fit on one line it's an architecture decision, and `/update-architecture` owns those. When a key is unset or the file is missing, the consuming skills say so and fall back to `CLAUDE.md` plus observed patterns rather than inventing a house style.

Override agents by placing custom versions at `~/.claude/agents/` (user) or `.claude/agents/` (project). See [references/customization-guide.md](references/customization-guide.md) for details.

## Token Budget

Only 1-2 skills are loaded at a time (triggered by description matching):

| Component | Est. Tokens |
|-----------|-------------|
| All 13 skill metadata (always loaded) | ~1,500 |
| Largest single skill body (research-design) | ~2,500 |
| Typical active session | ~3,400 |

Security audit reference files (~900 lines total) are only loaded when the audit runs.

## Companion Plugins

### session-scribe — Notion and GitHub Issues mirror

[**session-scribe**](https://github.com/matshoppenbrouwers/session-scribe) bridges the same workflow into Notion, GitHub Issues, or both: ended sessions become dated Agent log entries on a mapped Notion project page or comments on a dedicated GitHub log issue, and the `SEQUENCE.md` backlog is mirrored out to a Notion Tasks database with project relations or to GitHub Issues. Work marked ready on either side — a `scribe:ready` label, a `Scribe ready` checkbox — pulls back into `SEQUENCE.md` as a `(needs breakdown)` entry. Since 0.3.0 it also captures: `/scribe code` appends one entry to `SEQUENCE.md`, `/scribe task` and `/scribe note` file straight into Notion. session-flow produces the work and the backlog; session-scribe makes both reviewable outside the terminal, and gives you a one-line way in when a thought arrives mid-session.

```
/plugin marketplace add matshoppenbrouwers/session-scribe
/plugin install session-scribe@session-scribe
```

The two integrate by convention — session-scribe reads the `SEQUENCE.md` format, neither depends on the other's code, and either works standalone. The one convention they share as writers is the ` ⇄ <url>` provenance annotation: whichever tool files an entry **from an outside item** writes it, so no two writers file the same work twice.

That qualifier is load-bearing now that `/scribe code` also writes to `SEQUENCE.md`. A capture has no outside item behind it — it is a thought typed into the terminal — so it is filed unannotated on purpose, and the annotation is written later by whichever mirror first files it outward. An unannotated entry means *not yet mirrored*, never *not yet checked for duplicates*. Both plugins allocate `SEQ-NNN` from the highest id already in the file; count `[DEFERRED]` entries when you do, since they hold retired ids that no active-only scan will see.

### claude-mem — cross-session recall

session-flow deliberately ships no memory system. If you want recall across sessions, use [**claude-mem**](https://github.com/thedotmack/claude-mem): it observes your sessions and makes what it saw searchable later. It pairs naturally with `paths.lessons` — periodically ask it to propose lessons entries from what it observed, then prune hard by hand. Observations are its job; conclusions are yours.

**Caveat before you install both:** claude-mem and session-scribe each register a `SessionEnd` hook. Test the two together on a throwaway session and confirm both actually fire before relying on either — don't assume they coexist.

## References

- [Workflow Overview](references/workflow-overview.md) — Full chain diagram, artifact flow, skip patterns
- [Customization Guide](references/customization-guide.md) — Override agents, paths, test runners, release tooling

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for skill quality checklists and guidelines.

## License

[MIT](LICENSE)

## Links

- **Repository:** https://github.com/matshoppenbrouwers/session-flow
- **Author:** [matshoppenbrouwers (hoponthestack)](https://github.com/matshoppenbrouwers)
- **Install:** `/plugin marketplace add matshoppenbrouwers/session-flow`

<sub>Keywords: Claude Code plugin · Claude Code skills · Claude Code agents · agentic workflow · development lifecycle automation · task planning · code review · evidence-based verification</sub>
