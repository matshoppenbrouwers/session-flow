# session-flow - Claude Code plugin for session workflow orchestration

**session-flow** is a [Claude Code](https://claude.com/claude-code) plugin with **16 skills** and **6 agents** covering research, design, task planning, agent delegation, post-implementation, evidence-based verification, work-root repair, and release. Version 2 stores work as persistent records with stable identities, accepted scope, dependencies, claims, and outcomes. Skills guide the AI through the workflow; a Python runtime validates and stores work-item changes. See [enforcement limits](#what-the-runtime-enforces) for the distinction.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Skills: 16](https://img.shields.io/badge/Skills-16-green)
![Agents: 6](https://img.shields.io/badge/Agents-6-orange)

> **Install in Claude Code:** `/plugin marketplace add matshoppenbrouwers/session-flow` then `/plugin install session-flow@session-flow`

## Requirements

**Python 3.9 or newer, reachable as `python3`.** Work-item operations use `scripts/session-flow.py`, which needs only the Python standard library. Hand-editing records is not a supported substitute. If Python is missing, install it before running the plugin: even `doctor` needs an interpreter. A version guard reports `unsupported-runtime` on older Python versions that can parse the entrypoint.

Linux, WSL and macOS are the supported platforms. Use WSL on Windows; native Windows is outside the supported runtime contract. The following configurations are unsupported:

- A work root on a network or cloud-synchronized filesystem.
- Editing one work root from another operating system at the same time.
- Mutating one work root from more than one host.

## The Chain

```
session-init ──> gatekeeper ──> research-design ──> task-planning ──> delegation ──> post-impl ──> verify ──> release
 (one-time)       (triage          (collaborative      (break into       (dispatch      (simplify,     (evidence-   (version bump,
                   intake)          brainstorming)      session tasks)    agents)        review,        based proof) package, verify)
                                                                                         audit, test)
                                                                                            │
                                                                                      update-architecture

work layer:  gatekeeper / add-task / task-planning ──> work root ──> groom ──> next
                                                        └──> SEQUENCE.md (generated view)
```

Each skill produces artifacts that feed into the next. Start where your work fits, subject to that step's prerequisites. Small jobs can stay in a single work record; they do not need every step. Releasing a feature with a design document requires applicable verification evidence.

The **work layer** runs alongside the chain. One outcome is one **work item**, stored under the **work root** (`_devdocs/work/` by default); gatekeeper and add-task capture items, groom prepares them, and next works through them. The backlog you read, `_devdocs/SEQUENCE.md`, is generated from those items. A repository coming from an earlier version of session-flow enters this layout through `/session-repair`.

## Install

**Step 1** - Register the marketplace:
```
/plugin marketplace add matshoppenbrouwers/session-flow
```

**Step 2** - Install the plugin:
```
/plugin install session-flow@session-flow
```

Python 3.9+ must be on the host. See [Requirements](#requirements).

To update an existing Claude Code installation, run these in your terminal, then restart Claude Code:

```bash
claude plugin marketplace update session-flow
claude plugin update session-flow@session-flow --scope user
```

Use the installation's actual scope if it is project or local rather than user.

### Codex packaging

This repository ships Claude Code plugin manifests. It does not ship a Codex manifest or a Codex marketplace. Using it in Codex requires a separately maintained package with `.codex-plugin/plugin.json` and host-appropriate skill/agent setup. That package must include the v2 runtime (`scripts/`), `skills/`, `references/`, and `.claude-plugin/plugin.json`, which the runtime reads for its version. Copying only the skills is insufficient.

Update the adapted package's source and refresh its installation through your Codex marketplace, then start a new session. Updating the Claude Code marketplace does not update a separate Codex package. The repository's `install.sh` targets Claude Code.

## Getting Started

1. Install session-flow (see above), and confirm `python3 --version` reports 3.9 or newer
2. Run `/session-init` in Claude Code to create the work root with its namespace and the rest of the documentation structure. If the repository already carries a `todo/SEQUENCE.md` and task files from an earlier version, run `/session-repair` instead - it is the only supported way into the work-root layout
3. Use `/session-add-task` to capture a small job, or `/session-research-design` to develop a feature. Approve the outcome and scope before execution. For an accepted item needing multiple tasks, use `/session-task-planning`, approve its breakdown, then `/session-next` or `/session-delegation` with explicit task identities

Repair can survey a legacy backlog before its work root or namespace exists. Its plan includes any
required setup; after approval it creates the namespace and commits setup before importing. An ignored
work root gets a separate local Git repository with no remote, preserving the project's ignore rules.
Existing namespaces are reused. No setup or migration writes happen during the survey.

## Skills

| Skill | Trigger | Produces |
|-------|---------|----------|
| **session-init** | `/session-init` | Work root with its namespace, docs directories, `.session-flow.json` config |
| **session-repair** | `/session-repair` | A per-item plan for migrating a legacy layout or reconciling a drifted work root, applied only on confirmation |
| **session-brainstorm** | `/session-brainstorm` | An approved short design for an idea that is not yet a task |
| **session-gatekeeper** | `/session-gatekeeper` | Triaged issues routed to the sequence or to research-design |
| **session-research-design** | `/session-research-design` | A work item's design, with research and optional specification/plan documents as needed |
| **session-task-planning** | `/session-task-planning` | Task records under an accepted item's identity, with `depends_on` identities, `allowed_paths`, and acceptance criteria |
| **session-add-task** | `/session-add-task` | A captured work item, identity allocated by the runtime, and the regenerated sequence entry |
| **session-groom** | `/session-groom` | Verified breakdowns recorded against captured work items |
| **session-next** | `/session-next` | One bounded unit of accepted work claimed, executed, and its outcome recorded |
| **session-delegation** | `/session-delegation` | Completed implementations via parallel agent dispatch |
| **session-post-implementation** | `/session-post-implementation` | Refined code, security audit, test plan, updated docs |
| **session-verify** | `/session-verify` | A verification verdict supported by checks, probes, and recorded evidence gaps |
| **session-release** | `/session-release` | Versioned artifacts, updated satellite content |
| **update-architecture** | `/update-architecture` | Surgical architecture doc updates |
| **security-liability-audit** | `/security-liability-audit` | Technical security + legal liability findings |
| **session-debug** | `/session-debug` | A root cause found and fixed, one hypothesis at a time |

## Entry Points

You don't have to start at step 1:

| You have... | Start with |
|-------------|------------|
| Incoming issues or ideas to triage | `/session-gatekeeper` - route them to the backlog or a design session |
| A running backlog | `/session-next` - implement the next ready task |
| A repository from an earlier version, or a work root that has drifted | `/session-repair` - survey, plan, then apply on your confirmation |
| An idea, not yet a task | `/session-brainstorm` - shape it into a design you approve |
| A vague idea | `/session-research-design` - collaborative brainstorming refines it |
| A plan or spec attached to an accepted work item | `/session-task-planning` - break it into session-sized tasks |
| Accepted tasks with explicit identities | `/session-delegation` - dispatch agents for the named set |
| Working code that needs polish | `/session-post-implementation` - simplify, review, audit, test |
| A completed feature/plan that needs proof it works | `/session-verify` - falsification-based evidence artifact |
| Tested code ready to ship | `/session-release` - bump version, package, verify |
| A specific security concern | `/security-liability-audit` - standalone security + liability scan |
| A bug or failing test | `/session-debug` - find the cause before changing anything |

## The Chain in Practice

A typical session might look like:

```
You: /session-research-design
Claude: "What problem are we solving?" → one question at a time →
        dispatches codebase-researcher + external-researcher in parallel →
        proposes 3 approaches → presents design section by section →
        captures or reuses a work item, writes its intent and any needed
        research, specification and plan -> asks you to accept its scope

You: /session-task-planning
Claude: Reads the accepted scope and plan -> breaks into tasks with
        depends_on identities and allowed_paths ->
        identifies 3 parallel opportunities → writes one task record
        per task under the work item's identity -> asks you to approve
        the breakdown before accepting tasks for execution

You: /session-delegation SEQ-042/A1 SEQ-042/A2
Claude: Checks the named tasks' dependencies -> dispatches test-author for their
        acceptance tests → dispatches 2 implementers in parallel against
        those tests → records each task's outcome against the claimed
        identity → regenerates the sequence → reports progress

You: /session-post-implementation
Claude: Simplifies code and removes leftovers → reviews for bugs →
        runs full test suite → updates architecture docs →
        generates manual test plan

You: /session-verify   (required evidence before releasing a designed feature)
Claude: Reads design + plan → writes falsifiable hypotheses →
        runs structural audit → executes full tests → writes defect probes →
        produces evidence artifact with PASS/FAIL verdict

You: /session-release
Claude: Bumps version → waits for build → packages artifacts →
        scans docs site, website, changelog for stale content →
        presents checklist -> commits release
        Tags, pushes and publishes only when those actions are authorized.
```

## Work Items and the Sequence

One outcome is one **work item**: a directory under the **work root** (`_devdocs/work/` by default) holding `intent.md` and, when the work warrants them, `spec.md`, `plan.md`, and `tasks/`. A `namespace.json` at the root carries the **namespace** - the identity scope within which `SEQ-NNN` numbers are unique - and its repository bindings, so several repositories can share one root.

The default layout is:

```text
_devdocs/
  SEQUENCE.md              Generated backlog
  work/
    namespace.json         Identity scope and repository bindings
    .state/                Local runtime state, excluded from Git
    seq-042/
      intent.md            The outcome, scope, status and evidence
      spec.md              Optional detailed requirements
      plan.md              Optional implementation approach
      tasks/               Optional breakdown for multi-step work
        A1.md              A task record: SEQ-042/A1
        _index.md          Generated task index
  research/                Shared research reports
  plans/                   Shared plans and existing plan documents
  testing/                 Manual test plans and test results
  architecture/            Current architecture documentation
  todo/                    Earlier-version archive, when present
```

A small job can use only `intent.md`. Larger jobs keep their specification, plan and tasks beside it, so the next session can find the context from the same identity. Shared documentation remains available across items. Existing `todo/` files keep their names and locations after import; new work goes into `work/`. Paths are configurable, including a work root outside the repository.

`/session-verify` separately writes its reports, logs and probes under `_verification/` at the project root (`verification/` if the project prefers).

The **sequence** at `_devdocs/SEQUENCE.md` is the backlog you read: one line per work item in stored display order. Selection for execution separately considers readiness and priority.

```
- [ ] SEQ-007 P2: Add rate limiting to the API → work/seq-007/tasks/_index.md
- [ ] SEQ-008 P3: Investigate caching layer (needs breakdown)
- [ ] SEQ-009 P3 [auto]: Retry failed webhook deliveries → work/seq-009/tasks/_index.md
- [x] SEQ-006 P1: Fix login redirect loop → work/seq-006/tasks/_index.md
- [DEFERRED] SEQ-005 P3: Rewrite the importer
```

**The sequence is generated output, not a file you edit.** Change its underlying work item through the plugin. Editing the sequence does not update stored records, and a later render replaces those edits. `/session-repair` reports a hand-edited sequence as drift before applying repairs. The line grammar is in [references/sequence-grammar.md](references/sequence-grammar.md).

`[DEFERRED]` represents a deferred or cancelled item; its identity stays taken. No `SEQ-NNN` is ever reused: the runtime reserves new identities under the work-root lock, against both stored items and the tombstone index.

`[auto]` marks an entry captured on your behalf by `/session-gatekeeper`. You can ask the plugin to retire it. Capture alone does not authorize implementation. `/session-groom` reports these items separately, `/session-next` prefers a ready manual entry of the same priority, and `/session-status` counts them.

When an item needs a breakdown, each task is a self-contained prompt with files, instructions, acceptance criteria and a test. Dependencies use identities such as `SEQ-042/A1`. Declared `allowed_paths` can be exact paths (`src/api/routes.py`) or directory globs (`src/lib/governor/**`). Delegation includes those boundaries in the agent's instructions.

| Want to... | Use |
|------------|-----|
| Capture something for later | `/session-add-task` - captures a work item |
| Implement the next item | `/session-next` - or just say "implement the next task" |
| Prepare raw one-liners | `/session-groom` - researches and records verified breakdowns |
| See current work without starting it | `/session-status` - refreshes generated views and reports status without changing work records |

### What the Runtime Enforces

The runtime checks record revisions, lifecycle transitions and claim ownership. Before assigning work, it rejects unknown, cyclic or unfinished dependencies and overlapping declared write scopes held by different actors. Completion checks reject recorded contradictions such as stale evidence, child tasks still open or deferred, or a missing receipt for required delivery.

These checks do not establish that a feature works. Verification still needs tests and evidence about the accepted outcome. Recording a passing task result also does not automatically close its parent item.

Declared paths are coordination checks, not a filesystem sandbox: the runtime does not intercept an agent's file writes. Instructions also govern reviewing changed scope, judging stale claims, checking remaining session capacity and deciding when to continue. `/session-next` defaults to one bounded unit; further work needs authority covering continuation. See the [work-item contract](references/work-item-contract.md) for the precise limits.

`session-init` wires a `<!-- session-flow:sequence -->` block into your `CLAUDE.md` and `AGENTS.md` so "implement the next task" works without naming a file. Pair grooming with the built-in `/loop` for hands-off upkeep:

```
/loop 30m /session-groom
```

### Gatekeeper / Intake

`/session-gatekeeper` is the front-of-chain funnel for incoming work - GitHub issues, feature requests, or ideas that surface mid-session. It grounds each item in your architecture docs and product direction (a `PRD.md` in the docs root by default, configurable via `paths.direction`), then routes it:

- **Touches database schema or a spine / canonical status field** → back to you regardless of size.
- **Unknown alignment** → escalated. If the direction could not be established, nothing is auto-added.
- **Trivial, aligned, and clear** → straight into the sequence via `session-add-task`, marked `[auto]`.
- **Significant, divergent, or unclear** → escalated to a cowork `/session-research-design` session with you.
- **Off-direction** → flagged for your explicit decision.

Escalation is an act, not an annotation: an escalated batch produces a named session proposal - the question to answer, the items it covers, near-duplicates merged - addressed to you in the run's output. A question the code can answer gets answered and cited before it is routed, every cited path is existence-checked before a breakdown is written, and each run leaves a dated report beside your docs root, at `YYYY-MM-DD-gatekeeper-run.md`.

It triages only - it never implements, and it treats issue text as untrusted data rather than instructions. It pairs with `/loop` for periodic issue intake, queuing anything significant for you rather than auto-processing it.

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

Standard and Quick scopes can add individual steps as extras (e.g., Quick + architecture docs). Verification (`/session-verify`) is a separate workflow outside these presets. Releasing a feature with a design document requires a PASS artifact covering the candidate, or an explicit decision to reuse earlier evidence. Accepted caveats are permitted; bugfix/refactor releases without a design document do not have this prerequisite.

When the security audit is included, you choose how it runs:

- **Sub-agent** - dispatches a dedicated audit agent.
- **Inline** - runs in the main conversation with your current model.

### Security & Liability Audit

The audit covers two dimensions:

**Technical security** - LLM/AI security (prompt injection, unsanitized output, tool validation), OWASP Top 10, secrets detection, agentic security (Lethal Trifecta), desktop app security, dependency supply chain, webhook/integration security. Findings carry a high, medium or low confidence label and the caller decides what to act on.

**Legal liability** - ToS/EULA coverage gaps, GDPR compliance (privacy policy, DPAs, data retention, user rights), EU AI Act obligations (risk classification, transparency), Digital Content Directive (conformity, updates), consumer protection (withdrawal, pricing, cancellation), AI output disclaimers, cross-border data transfer requirements. Designed for EU-based developers with a worldwide userbase.

The audit can also run standalone via `/security-liability-audit`.

## Bundled Agents

| Agent | Used By | Purpose |
|-------|---------|---------|
| **codebase-researcher** | research-design (research + design phases) | Answer one question about the existing code, with file:line citations. Read-only |
| **external-researcher** | research-design (research phase) | Research docs, specs, and prior art outside the repo, with source validation. No repo access |
| **test-author** | delegation (once for the named multi-task set, before implementers) | Write acceptance tests for the selected work |
| **code-simplifier** | post-impl step 1 | Simplify recently changed code and remove what the implementation left behind |
| **code-reviewer** | post-impl step 2 | Find bugs, security issues, convention violations |
| **security-auditor** | post-impl step 3 | Technical security + legal liability audit |

Four bundled Claude Code agents declare `model: inherit`; `codebase-researcher` and `external-researcher` declare `model: sonnet`. Override agents with your own versions in `.claude/agents/`. A Codex adaptation needs its own mapping of these agent settings.

`external-researcher` declares only `WebSearch` and `WebFetch` tools, with no repository-reading tool. Compact work through `/session-next` does not require a separate test-author dispatch.

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

`paths.work` is where the runtime stores work items and `paths.sequence` is the generated view of them; every session-flow command resolves both from this file through `--project-root`. A repository that adopted session-flow before 2.0.0 also keeps `todo` and `tasks` keys pointing at its archived files, so links into them still resolve - nothing new is written there.

`paths.direction` points `/session-gatekeeper` at your product-direction doc. It defaults to a `PRD.md` inside the docs root (e.g. `_devdocs/PRD.md`) - let `/session-init` scaffold it, or set this to an existing PRD/vision file anywhere in the repo.

`paths.conventions` and `paths.lessons` are optional one-line-entry files, both in the same `rule - reason` format (~140 characters, reason mandatory):

```
Repository methods return domain objects, never ORM rows - keeps persistence swappable and out of the service layer.
```

**Conventions** are house rules: `/session-research-design` loads them at design time and `code-reviewer` enforces them alongside `CLAUDE.md`. **Lessons** are conclusions drawn after the fact, read as a one-line index by research-design and delegation. Both are kept out of `CLAUDE.md` on purpose - that file costs tokens on every turn of every session, while these matter only at design and review time. If a rule doesn't fit on one line it's an architecture decision, and `/update-architecture` owns those. When a key is unset or the file is missing, the consuming skills say so and fall back to `CLAUDE.md` plus observed patterns rather than inventing a house style.

Override agents by placing custom versions at `~/.claude/agents/` (user) or `.claude/agents/` (project). See [references/customization-guide.md](references/customization-guide.md) for details.

## Context Usage

Skill descriptions support discovery; selected skills direct the host to load their instructions and relevant references. Actual context use depends on the host, selected workflow, repository and conversation. This release does not establish a measured typical token budget or a fixed limit on how many skills a host loads.

## Companion Plugins

### session-scribe - Notion and GitHub Issues mirror

[**session-scribe**](https://github.com/matshoppenbrouwers/session-scribe) provides session logging and work mirroring to Notion and GitHub Issues. Integration with v2 work records requires a compatible session-scribe adapter that calls the session-flow runtime. An older integration that appends lines directly to `SEQUENCE.md` cannot create v2 work items.

```
/plugin marketplace add matshoppenbrouwers/session-scribe
/plugin install session-scribe@session-scribe
```

Lifecycle-dependent companion commands check the runtime's protocol version and refuse incompatible installations. Standalone features such as session logging and direct Notion capture do not require flow's lifecycle runtime. See [Runtime Integration](references/runtime-integration.md) for the protocol contract.

The generated sequence can carry a ` ⇄ <url>` provenance annotation linking an item to its external counterpart. Integration writes provenance to the underlying record, then regenerates the view. A locally captured thought has no external link until it is mirrored.

For new work, `/session-add-task` uses the runtime's new-record transition to allocate an identity under the work-root lock. The lower-level `capture` command requires an explicit identity; it is not the allocator. Companion integrations must use the supported record protocol and must not scan the generated sequence for the next free number.

### claude-mem - cross-session recall

session-flow stores work records and curated lessons; it does not bundle conversation-memory software. [claude-mem](https://github.com/thedotmack/claude-mem) is a separate project. Its installation, hooks and compatibility with other plugins are outside this release's verification.

## References

- [Workflow Overview](references/workflow-overview.md) - Full chain diagram, artifact flow, skip patterns
- [Adoption Note](references/adoption-note.md) - What happens on a machine that has never run it, step by step
- [Work Item Contract](references/work-item-contract.md) - Record shape, identity, lifecycle, and what each command may change
- [Sequence Grammar](references/sequence-grammar.md) - What `render` emits, token by token
- [Runtime Integration](references/runtime-integration.md) - Protocol, error codes, measured limitations
- [Customization Guide](references/customization-guide.md) - Override agents, paths, test runners, release tooling

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
