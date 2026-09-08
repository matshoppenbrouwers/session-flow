# session-flow — Claude Code plugin for session workflow orchestration

**session-flow** is a [Claude Code](https://claude.com/claude-code) plugin that orchestrates the full software development lifecycle — a chain of **16 skills** and **6 agents** covering research, design, task planning, agent delegation, post-implementation, evidence-based verification, work-root repair, and release. It adds dependency-aware parallelization, a standing task backlog, collaborative brainstorming, and a security & liability audit, with user gates at every critical decision.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Skills: 16](https://img.shields.io/badge/Skills-16-green)
![Agents: 6](https://img.shields.io/badge/Agents-6-orange)

> **Install in Claude Code:** `/plugin marketplace add matshoppenbrouwers/session-flow` then `/plugin install session-flow@session-flow`

## Requirements

**Python 3.9 or newer, reachable as `python3`.** Every work item session-flow reads or writes goes through its own runtime, `scripts/session-flow.py`, which uses the standard library only — no third-party packages. There is no hand-editing path beside it, so a machine without Python — chiefly native Windows outside WSL — cannot run the plugin. When the interpreter is missing or too old, the runtime's `doctor` command reports `unsupported-runtime` with the command that installs it, rather than failing with a traceback.

Linux, WSL and macOS are the tested runtimes. Native Windows is out of scope while Python is a hard requirement. Three configurations are unsupported rather than defended against, and a report from one of them is not a defect:

- A work root on a network or cloud-synchronized filesystem.
- Editing one work root from another operating system at the same time.
- Mutating one work root from more than one host.

## The Chain

```
session-init ──> gatekeeper ──> research-design ──> task-planning ──> delegation ──> post-impl ──> verify ──> release
 (one-time)       (triage          (collaborative      (break into       (dispatch      (simplify,     (evidence-   (version bump,
                   intake)          brainstorming)      session tasks)    agents)        review,        based proof) package, verify)
                                                                                         audit, test)   (optional,
                                                                                            │            heavy)
                                                                                      update-architecture

work layer:  gatekeeper / add-task / task-planning ──> work root ──> groom ──> next
                                                        └──> SEQUENCE.md (generated view)
```

Each skill produces artifacts that feed into the next. Start anywhere in the chain based on what you already have.

The **work layer** runs alongside the chain. One outcome is one **work item**, stored under the **work root** (`_devdocs/work/` by default); gatekeeper and add-task capture items, groom prepares them, and next works through them. The backlog you read, `_devdocs/SEQUENCE.md`, is generated from those items. A repository coming from an earlier version of session-flow enters this layout through `/session-repair`.

## Install

**Step 1** — Register the marketplace:
```
/plugin marketplace add matshoppenbrouwers/session-flow
```

**Step 2** — Install the plugin:
```
/plugin install session-flow@session-flow
```

Tested on Linux, WSL and macOS. Python 3.9+ must be on the host — see [Requirements](#requirements).

## Getting Started

1. Install session-flow (see above), and confirm `python3 --version` reports 3.9 or newer
2. Run `/session-init` in Claude Code to create the work root with its namespace and the rest of the documentation structure. If the repository already carries a `todo/SEQUENCE.md` and task files from an earlier version, run `/session-repair` instead — it is the only supported way into the work-root layout
3. Start building: `/session-research-design` for new features, `/session-task-planning` if you already have a plan

## Skills

| Skill | Trigger | Produces |
|-------|---------|----------|
| **session-init** | `/session-init` | Work root with its namespace, docs directories, `.session-flow.json` config |
| **session-repair** | `/session-repair` | A per-item plan for migrating a legacy layout or reconciling a drifted work root, applied only on confirmation |
| **session-brainstorm** | `/session-brainstorm` | An approved short design for an idea that is not yet a task |
| **session-gatekeeper** | `/session-gatekeeper` | Triaged issues routed to the sequence or to research-design |
| **session-research-design** | `/session-research-design` | Research report + implementation plan |
| **session-task-planning** | `/session-task-planning` | One task record per task under the item's identity, each with dependency tags `[seq]`, `[parallel-after:X]`, a write boundary, and criteria |
| **session-add-task** | `/session-add-task` | A captured work item, identity allocated by the runtime, and the regenerated sequence entry |
| **session-groom** | `/session-groom` | Verified breakdowns recorded against captured work items |
| **session-next** | `/session-next` | One bounded unit of accepted work claimed, executed, and its outcome recorded |
| **session-delegation** | `/session-delegation` | Completed implementations via parallel agent dispatch |
| **session-post-implementation** | `/session-post-implementation` | Refined code, security audit, test plan, updated docs |
| **session-verify** | `/session-verify` | Evidence-based verification artifact proving implementation matches design spec |
| **session-release** | `/session-release` | Versioned artifacts, updated satellite content |
| **update-architecture** | `/update-architecture` | Surgical architecture doc updates |
| **security-liability-audit** | `/security-liability-audit` | Technical security + legal liability findings |
| **session-debug** | `/session-debug` | A root cause found and fixed, one hypothesis at a time |

## Entry Points

You don't have to start at step 1:

| You have... | Start with |
|-------------|------------|
| Incoming issues or ideas to triage | `/session-gatekeeper` — route them to the backlog or a design session |
| A running backlog | `/session-next` — implement the next ready task |
| A repository from an earlier version, or a work root that has drifted | `/session-repair` — survey, plan, then apply on your confirmation |
| An idea, not yet a task | `/session-brainstorm` — shape it into a design you approve |
| A vague idea | `/session-research-design` — collaborative brainstorming refines it |
| A plan or spec | `/session-task-planning` — break it into session-sized tasks |
| A task list | `/session-delegation` — dispatch agents to execute |
| Working code that needs polish | `/session-post-implementation` — simplify, review, audit, test |
| A completed feature/plan that needs proof it works | `/session-verify` — falsification-based evidence artifact |
| Tested code ready to ship | `/session-release` — bump version, package, verify |
| A specific security concern | `/security-liability-audit` — standalone security + liability scan |
| A bug or failing test | `/session-debug` — find the cause before changing anything |

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
        identifies 3 parallel opportunities → writes one task record
        per task under the work item's identity

You: /session-delegation
Claude: Parses dependency graph → dispatches test-author for the phase's
        acceptance tests → dispatches 2 implementers in parallel against
        those tests → records each task's outcome against the claimed
        identity → regenerates the sequence → reports progress

You: /session-post-implementation
Claude: Simplifies code and removes leftovers → reviews for bugs →
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

## Work Items and the Sequence

One outcome is one **work item**: a directory under the **work root** (`_devdocs/work/` by default) holding `intent.md` and, when the work warrants them, `spec.md`, `plan.md`, and `tasks/`. A `namespace.json` at the root carries the **namespace** — the identity scope within which `SEQ-NNN` numbers are unique — and its repository bindings, so several repositories can share one root.

The **sequence** at `_devdocs/SEQUENCE.md` is the backlog you read: a flat, priority-ordered list with one line per work item.

```
- [ ] SEQ-007 P2: Add rate limiting to the API → work/seq-007/tasks/_index.md
- [ ] SEQ-008 P3: Investigate caching layer (needs breakdown)
- [ ] SEQ-009 P3 [auto]: Retry failed webhook deliveries → work/seq-009/tasks/_index.md
- [x] SEQ-006 P1: Fix login redirect loop → work/seq-006/tasks/_index.md
- [DEFERRED] SEQ-005 P3: Rewrite the importer
```

**The sequence is generated output, not a file you edit.** The runtime renders it from the work items and nothing else writes it. Anything typed into it is read by nothing and is gone at the next render, so an entry changes by changing its work item through the runtime. `/session-repair` reports a hand-edited sequence as drift rather than overwriting it without saying so. The line grammar — every token and the record field it came from — is in [references/sequence-grammar.md](references/sequence-grammar.md).

`[DEFERRED]` retires an item without doing it, and its identity stays taken. No `SEQ-NNN` is ever reused: the runtime reserves the next one under the work-root lock, against both the stored items and the tombstone index, so an id that once addressed a GitHub issue or a Notion task never comes back pointing at different work.

`[auto]` marks an entry a skill captured on your behalf — `/session-gatekeeper` triage is the one shipped caller — rather than one you added yourself. It is the veto handle: marked entries sit in the backlog and can be struck on sight, so unattended intake never needs your approval up front. `/session-groom` reports them separately, `/session-next` never lets one outrank a manual entry of the same priority, and `/session-status` counts them.

Each item's breakdown is one or more task records under its own identity, each a self-contained, bite-sized prompt (Files / Instructions / Accept / Test) ready for an agent to execute. **Files** entries may be exact paths (`src/api/routes.py`) or directory globs (`src/lib/governor/**`) when a task owns a whole subtree — and the field doubles as the write boundary: `/session-delegation` injects it into every dispatch as "you may only create or modify these paths."

| Want to... | Use |
|------------|-----|
| Capture something for later | `/session-add-task` — captures a work item |
| Implement the next item | `/session-next` — or just say "implement the next task" |
| Prepare raw one-liners | `/session-groom` — researches and records verified breakdowns |

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

Escalation is an act, not an annotation: an escalated batch produces a named session proposal — the question to answer, the items it covers, near-duplicates merged — addressed to you in the run's output. A question the code can answer gets answered and cited before it is routed, every cited path is existence-checked before a breakdown is written, and each run leaves a dated report beside your docs root, at `YYYY-MM-DD-gatekeeper-run.md`.

It triages only — it never implements, and it treats issue text as untrusted data rather than instructions. It pairs with `/loop` for periodic issue intake, queuing anything significant for you rather than auto-processing it.

## Post-Implementation Workflow

`/session-post-implementation` runs up to 8 steps. At the start, it asks which scope to use:

| Step | Full | Standard | Quick |
|------|------|----------|-------|
| 1. Simplify | yes | yes | yes |
| 2. Code review | yes | yes | yes |
| 3. Security & liability audit | yes | - | - |
| 4. Commit checkpoint | yes | yes | yes |
| 5. Test suite | yes | yes | - |
| 6. Architecture docs | yes | - | - |
| 7. Manual test plan | yes | - | - |
| 8. Final commit | yes | yes | - |

Standard and Quick scopes can add individual steps as extras (e.g., Quick + architecture docs). Verification (`/session-verify`) is always optional and can be invoked after Full completion.

When the security audit is included, you choose how it runs:
- **Sub-agent** — dispatches an agent (faster, lower cost)
- **Inline** — runs in the main conversation with your current model (more thorough)

### Security & Liability Audit

The audit covers two dimensions:

**Technical security** — LLM/AI security (prompt injection, unsanitized output, tool validation), OWASP Top 10, secrets detection, agentic security (Lethal Trifecta), desktop app security, dependency supply chain, webhook/integration security. Findings carry a high, medium or low confidence label and the caller decides what to act on.

**Legal liability** — ToS/EULA coverage gaps, GDPR compliance (privacy policy, DPAs, data retention, user rights), EU AI Act obligations (risk classification, transparency), Digital Content Directive (conformity, updates), consumer protection (withdrawal, pricing, cancellation), AI output disclaimers, cross-border data transfer requirements. Designed for EU-based developers with a worldwide userbase.

The audit can also run standalone via `/security-liability-audit`.

## Bundled Agents

| Agent | Used By | Purpose |
|-------|---------|---------|
| **codebase-researcher** | research-design (research + design phases) | Answer one question about the existing code, with file:line citations. Read-only |
| **external-researcher** | research-design (research phase) | Research docs, specs, and prior art outside the repo, with source validation. No repo access |
| **test-author** | delegation (once per phase, before implementers) | Write the acceptance tests that become the implementers' oracle |
| **code-simplifier** | post-impl step 1 | Simplify recently changed code and remove what the implementation left behind |
| **code-reviewer** | post-impl step 2 | Find bugs, security issues, convention violations |
| **security-auditor** | post-impl step 3 | Technical security + legal liability audit |

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
    "work": "_devdocs/work",
    "sequence": "_devdocs/SEQUENCE.md",
    "testing": "_devdocs/testing",
    "architecture": "_devdocs/architecture",
    "direction": "_devdocs/PRD.md",
    "conventions": "_devdocs/conventions.md",
    "lessons": "_devdocs/lessons.md"
  }
}
```

`paths.work` is where the runtime stores work items and `paths.sequence` is the generated view of them; every session-flow command resolves both from this file through `--project-root`. A repository that adopted session-flow before 2.0.0 also keeps `todo` and `tasks` keys pointing at its archived files, so links into them still resolve — nothing new is written there.

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
| All 16 skill metadata (always loaded) | ~1,800 |
| Largest single skill body (research-design) | ~2,500 |
| Typical active session | ~3,600 |

Security audit reference files (~900 lines total) are only loaded when the audit runs.

## Companion Plugins

### session-scribe — Notion and GitHub Issues mirror

[**session-scribe**](https://github.com/matshoppenbrouwers/session-scribe) bridges the same workflow into Notion, GitHub Issues, or both: ended sessions become dated Agent log entries on a mapped Notion project page or comments on a dedicated GitHub log issue, and the `SEQUENCE.md` backlog is mirrored out to a Notion Tasks database with project relations or to GitHub Issues. Work marked ready on either side — a `scribe:ready` label, a `Scribe ready` checkbox — pulls back into `SEQUENCE.md` as a `(needs breakdown)` entry. Since 0.3.0 it also captures: `/scribe code` files one entry into this project's backlog, `/scribe task` and `/scribe note` file straight into Notion. session-flow produces the work and the backlog; session-scribe makes both reviewable outside the terminal, and gives you a one-line way in when a thought arrives mid-session.

```
/plugin marketplace add matshoppenbrouwers/session-scribe
/plugin install session-scribe@session-scribe
```

The two integrate by convention — session-scribe reads the `SEQUENCE.md` format, neither depends on the other's code, and either works standalone. The one convention they share as writers is the ` ⇄ <url>` provenance annotation: whichever tool files an entry **from an outside item** writes it, so no two writers file the same work twice.

That qualifier is load-bearing now that `/scribe code` also captures work. A capture has no outside item behind it — it is a thought typed into the terminal — so it is filed unannotated on purpose, and the annotation is written later by whichever mirror first files it outward. An unannotated entry means *not yet mirrored*, never *not yet checked for duplicates*.

Identity comes from one place. session-flow's runtime allocates every `SEQ-NNN` under the work-root lock, against the stored items and the tombstone index; the generated sequence is never scanned for the next free number, and a retired one is never handed out again. Anything filing work into this backlog goes through that path — `/session-add-task`, or the runtime's `capture` command — because a line appended to `SEQUENCE.md` is not a record and does not survive the next render.

### claude-mem — cross-session recall

session-flow deliberately ships no memory system. If you want recall across sessions, use [**claude-mem**](https://github.com/thedotmack/claude-mem): it observes your sessions and makes what it saw searchable later. It pairs naturally with `paths.lessons` — periodically ask it to propose lessons entries from what it observed, then prune hard by hand. Observations are its job; conclusions are yours.

**Caveat before you install both:** claude-mem and session-scribe each register a `SessionEnd` hook. Test the two together on a throwaway session and confirm both actually fire before relying on either — don't assume they coexist.

## References

- [Workflow Overview](references/workflow-overview.md) — Full chain diagram, artifact flow, skip patterns
- [Adoption Note](references/adoption-note.md) — What happens on a machine that has never run it, step by step
- [Work Item Contract](references/work-item-contract.md) — Record shape, identity, lifecycle, and what each command may change
- [Sequence Grammar](references/sequence-grammar.md) — What `render` emits, token by token
- [Runtime Integration](references/runtime-integration.md) — Protocol, error codes, measured limitations
- [Customization Guide](references/customization-guide.md) — Override agents, paths, test runners, release tooling

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the test command, skill quality checklists, and guidelines.

## License

[MIT](LICENSE)

Two skills are derived from superpowers (MIT); see `THIRD_PARTY_NOTICES.md`.

## Links

- **Repository:** https://github.com/matshoppenbrouwers/session-flow
- **Author:** [matshoppenbrouwers (hoponthestack)](https://github.com/matshoppenbrouwers)
- **Install:** `/plugin marketplace add matshoppenbrouwers/session-flow`

<sub>Keywords: Claude Code plugin · Claude Code skills · Claude Code agents · agentic workflow · development lifecycle automation · task planning · code review · evidence-based verification</sub>
