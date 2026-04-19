# session-flow

Session workflow orchestration for Claude Code. A development lifecycle chain from research through release, with dependency-aware task planning, agent dispatch, and evidence-based verification.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Skills: 9](https://img.shields.io/badge/Skills-9-green)
![Agents: 4](https://img.shields.io/badge/Agents-4-orange)

## The Chain

```
session-init ──> research-design ──> task-planning ──> delegation ──> post-impl ──> verify ──> release
 (one-time)       (collaborative      (break into       (dispatch      (simplify,     (evidence-   (version bump,
                   brainstorming)      session tasks)    agents)        review,        based proof) package, verify)
                                                                        audit, test)   (optional,
                                                                           │            heavy)
                                                                     update-architecture
```

Each skill produces artifacts that feed into the next. Start anywhere in the chain based on what you already have.

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
| **session-init** | `/session-init` | Directory structure + `.session-flow.json` config |
| **session-research-design** | `/session-research-design` | Research report + implementation plan |
| **session-task-planning** | `/session-task-planning` | Task file with dependency tags `[seq]`, `[parallel-after:X]` |
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
        proposes 3 approaches → presents design section by section →
        writes research report + implementation plan

You: /session-task-planning
Claude: Reads the plan → breaks into 8 tasks with dependency tags →
        identifies 3 parallel opportunities → saves to todo/

You: /session-delegation
Claude: Parses dependency graph → dispatches 2 agents in parallel →
        marks tasks [x] as they complete → reports progress

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
| **code-simplifier** | post-impl step 1 | Simplify recently changed code |
| **code-reviewer** | post-impl step 2 | Find bugs, security issues, convention violations |
| **security-auditor** | post-impl step 3 | Technical security + legal liability audit |
| **code-sanitizer** | post-impl step 5 | Detect dead code and temporary artifacts |

Bundled agents inherit the parent session's model — an Opus 4.7 session gets Opus 4.7 subagents, a Sonnet session gets Sonnet. If you have the marketplace `code-simplifier:code-simplifier` plugin installed, session-post-implementation uses it automatically instead of the bundled agent.

## Customization

session-flow adapts to your project via `.session-flow.json` (created by `/session-init`):

```json
{
  "root": "_devdocs",
  "paths": {
    "research": "_devdocs/research",
    "plans": "_devdocs/plans",
    "todo": "_devdocs/todo",
    "testing": "_devdocs/testing",
    "architecture": "_devdocs/architecture"
  }
}
```

Override agents by placing custom versions at `~/.claude/agents/` (user) or `.claude/agents/` (project). See [references/customization-guide.md](references/customization-guide.md) for details.

## Token Budget

Only 1-2 skills are loaded at a time (triggered by description matching):

| Component | Est. Tokens |
|-----------|-------------|
| All 9 skill metadata (always loaded) | ~900 |
| Largest single skill body (research-design) | ~2,500 |
| Typical active session | ~3,400 |

Security audit reference files (~900 lines total) are only loaded when the audit runs.

## References

- [Workflow Overview](references/workflow-overview.md) — Full chain diagram, artifact flow, skip patterns
- [Customization Guide](references/customization-guide.md) — Override agents, paths, test runners, release tooling

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for skill quality checklists and guidelines.

## License

[MIT](LICENSE)
