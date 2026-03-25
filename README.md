# session-flow

Session workflow orchestration for Claude Code. A complete development lifecycle chain — from research through release — with dependency-aware parallelization and collaborative brainstorming at every stage.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Skills: 7](https://img.shields.io/badge/Skills-7-green)
![Agents: 3](https://img.shields.io/badge/Agents-3-orange)

## The Chain

```
session-init ──> research-design ──> task-planning ──> delegation ──> post-impl ──> release
 (one-time)       (collaborative      (break into       (dispatch      (simplify,     (version bump,
                   brainstorming)      session tasks)    agents)        review, test)  package, verify)
                                                                           │
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

That's it. Works on macOS, Linux, and Windows.

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
| **session-post-implementation** | `/session-post-implementation` | Refined code, test plan, updated architecture docs |
| **session-release** | `/session-release` | Versioned artifacts, updated satellite content |
| **update-architecture** | `/update-architecture` | Surgical architecture doc updates |

## Entry Points

You don't have to start at step 1:

| You have... | Start with |
|-------------|------------|
| A vague idea | `/session-research-design` — collaborative brainstorming refines it |
| A plan or spec | `/session-task-planning` — break it into session-sized tasks |
| A task list | `/session-delegation` — dispatch agents to execute |
| Working code that needs polish | `/session-post-implementation` — simplify, review, test |
| Tested code ready to ship | `/session-release` — bump version, package, verify |

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

You: /session-release
Claude: Bumps version → waits for build → packages artifacts →
        scans docs site, website, changelog for stale content →
        presents checklist → commits release
```

## Bundled Agents

session-flow includes 3 agents dispatched by the session skills:

| Agent | Used By | Purpose |
|-------|---------|---------|
| **code-simplifier** | post-impl step 1 | Simplify recently changed code |
| **code-reviewer** | post-impl step 2 | Find bugs, security issues, convention violations |
| **code-sanitizer** | post-impl step 4 | Detect dead code and temporary artifacts |

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
    "testing": "_devdocs/testing",
    "architecture": "_devdocs/architecture"
  }
}
```

Override agents by placing custom versions at `~/.claude/agents/` (user) or `.claude/agents/` (project). See [references/customization-guide.md](references/customization-guide.md) for details.

## Comparison

| Feature | session-flow | superpowers | everything-claude-code |
|---------|-------------|-------------|----------------------|
| Research + design | Collaborative brainstorming | Brainstorming skill | No |
| Task planning | Dependency-aware parallelization | No | Planner agent |
| Agent delegation | Parallel dispatch from task graph | No | No |
| Post-implementation | Simplify + review + sanitize + test | TDD focus | Code reviewer |
| Release workflow | Version + package + satellite scan | No | No |
| Full lifecycle chain | Yes (7 connected skills) | Partial (individual skills) | Partial (agents) |

## Token Budget

Only 1-2 skills are loaded at a time (triggered by description matching):

| Component | Est. Tokens |
|-----------|-------------|
| All 7 skill metadata (always loaded) | ~700 |
| Largest single skill body (research-design) | ~2,500 |
| Typical active session | ~3,200 |

## References

- [Workflow Overview](references/workflow-overview.md) — Full chain diagram, artifact flow, skip patterns
- [Customization Guide](references/customization-guide.md) — Override agents, paths, test runners, release tooling

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for skill quality checklists and guidelines.

## License

[MIT](LICENSE)
