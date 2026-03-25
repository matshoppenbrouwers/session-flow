---
name: session-research-design
description: Deep research and design workflow for complex features. Use before /session-task-planning when a feature requires exploring implementation approaches, analyzing existing code, and designing an architecture before breaking into tasks. Produces a research report and an implementation plan that feeds into session-task-planning. Triggers on "/session-research-design" or when user says "research this", "explore approaches for", or "design this feature".
---

# Session Research & Design

Conduct deep research and produce a design plan before task planning.

**Announce:** "Using session-research-design to research approaches and design an implementation plan."

## Core Principle

Complex features require understanding before planning. This skill produces two artifacts:

1. **Research report** (saved to the project's research directory) -- explores the problem space
2. **Implementation plan** (saved to the project's plans directory) -- defines the build path

Both use the `YYYY-MM-DD-{topic}.md` naming convention. Directory paths are read from `.session-flow.json` config, or auto-detected by looking for `research/`, `_devdocs/research/`, `docs/research/` (and `plans/`, `_devdocs/plans/`, `docs/plans/` respectively). If no matching directory is found, suggest running `/session-init`.

Both go through user review before proceeding. The implementation plan feeds directly into `/session-task-planning`.

## Workflow

### Step 1: Scope

Clarify the research topic through a **collaborative dialogue** with the user. Ask questions **one at a time**, not all at once. Prefer **multiple choice** when possible -- it is easier to answer.

Focus on understanding:

- **Purpose:** What is the feature or problem? (one sentence)
- **Existing landscape:** What exists in the codebase already? (modules, tables, APIs)
- **Scope boundary:** What is new vs. extending existing work?
- **Constraints:** Performance, compatibility, dependencies?
- **Decision points:** What decisions need to be made?

Start with purpose, then follow up based on the answer. Let each response inform the next question. Do not present this as a checklist -- have a conversation.

**If ambiguous:** Ask the user before proceeding. Do not guess scope.

**Output:** A clear topic name (kebab-case, for file naming) and 2-3 sentence scope statement.

### Step 2: Research

Dispatch up to 3 parallel Explore agents to gather information:

```
Agent 1: Codebase analysis
  "Analyze the existing codebase for {topic}. Find all relevant modules,
   schemas, APIs, and integration points. Map the current architecture."

Agent 2: Existing patterns
  "Search the codebase for patterns similar to {topic}. How are related
   features structured? What conventions, protocols, and abstractions exist?"

Agent 3: External approaches (if applicable)
  Use WebSearch to find how other projects solve this problem.
  Focus on 3-5 reference implementations with concrete architecture details.
```

Send all agents in a **single message** for parallel execution.

**If the topic is narrow** (single module, clear approach): skip Agent 3 and reduce to 1-2 agents.

Gather all findings before proceeding.

### Step 3: Research Report

Write a structured report to the project's research directory as `YYYY-MM-DD-{topic}.md`.

**Report template:**

```markdown
# {Topic} Research Report

**Date:** YYYY-MM-DD
**Status:** Research complete, pending discussion
**Scope:** {scope statement from Step 1}

---

## 1. Current State

### What Exists

{Describe what the codebase already has. Reference specific files and line numbers.}

### Architecture

{Diagram or description of the current architecture relevant to this topic.}

### Gaps

| Gap | Impact |
|-----|--------|
| {gap} | {impact} |

---

## 2. Reference Implementations

### 2.1 {Reference Name}

**Source:** {link or citation}

**Architecture:** {how it works}

**Relevance to this project:** {what we can learn or borrow}

{Repeat for each reference (3-5 typical)}

---

## 3. Comparative Analysis

{Compare approaches across dimensions: complexity, performance, maintainability, fit with existing codebase.}

| Dimension | Approach A | Approach B | Approach C |
|-----------|-----------|-----------|-----------|
| {dim} | {value} | {value} | {value} |

---

## 4. Recommendation

**Recommended approach:** {name}

**Rationale:** {why this approach, referencing the comparison}

**Key design decisions to resolve:**
1. {decision}
2. {decision}

---

## 5. Open Questions

- {question for user discussion}
```

### Step 4: User Review (Research)

**Propose 2-3 approaches** with trade-offs. Lead with your recommended option and explain why.

Present to the user:

1. Summary of current state (1-2 sentences)
2. **Recommended approach** -- what it is, why you recommend it, and its trade-offs
3. **Alternative approach(es)** -- 1-2 other viable options with their trade-offs
4. Open questions that need user input

**Wait for user feedback.** The user may:
- Approve the recommendation
- Pick an alternative approach
- Ask for deeper research on a specific approach
- Change the scope or constraints
- Resolve open questions

**Iterate** on the report if needed before proceeding.

### Step 5: Implementation Plan

After the user approves the research direction, write an implementation plan to the project's plans directory as `YYYY-MM-DD-{topic}-implementation.md`.

**Plan template:**

```markdown
# {Topic} Implementation

**Date**: YYYY-MM-DD
**Status**: Planned
**Goal**: {one sentence}
**Research**: `{path-to-research-report}`

---

## Context

{1-2 paragraphs summarizing the problem and chosen approach. Reference the research doc for full analysis.}

### Architecture Decision

{Key architectural choice and why. Keep brief -- details are in the research report.}

---

## Module Structure

{If applicable. Show the file tree for new modules/packages.}

### Integration Points

{Where the new code connects to existing code. List files and approximate locations.}

---

## Phase N: {Phase Name}

{Each phase should be independently deployable and testable.}

**Files created:**
- `path/to/file.py` -- {purpose}

**Files modified:**
- `path/to/existing.py` -- {what changes}

**Design notes:**
{Key implementation details, schema changes, API contracts.}

**Accept**: {Observable outcome proving this phase works}

**Commit**: `{conventional commit message}`

---

{Repeat for each phase}

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| {criterion} | {how to verify} |

---

## References

- Research report: `{path-to-research-report}`
- {Other relevant docs}
```

### Step 6: User Review (Plan)

Present the design **section by section**. Ask after each section whether it looks right so far. Scale each section to its complexity: a few sentences if straightforward, more detail if nuanced.

Suggested presentation order:

1. Context and architecture decision
2. Module structure and integration points
3. Phases (one at a time if complex, grouped if simple)
4. Success criteria

**Wait for user approval.** The user may:
- Approve the plan
- Request changes to phasing or scope
- Add or remove phases
- Adjust architectural decisions

**Iterate** on the plan if needed.

### Step 7: Handoff

Once the user approves the plan:

1. Confirm both artifacts are saved:
   - Research report in the project's research directory
   - Implementation plan in the project's plans directory
2. Suggest: "Plan is ready. Run `/session-task-planning` to break this into executable tasks."

## File Naming

Follow the `YYYY-MM-DD-label.md` convention. Use today's date for both the research report and implementation plan. Label should be lowercase kebab-case.

## Anti-Patterns

**Skipping research:**
- BAD: Jump straight to an implementation plan without understanding the problem space
- GOOD: Research first, even if the approach seems obvious -- you may discover constraints

**Over-researching:**
- BAD: 10 reference implementations with exhaustive analysis for a simple feature
- GOOD: Scale research depth to feature complexity. Simple features need 1-2 references.

**No user checkpoints:**
- BAD: Write research report AND plan, then present both at once
- GOOD: Get user approval on research direction before writing the plan

**Vague plans:**
- BAD: "Phase 2: Implement the feature"
- GOOD: "Phase 2: Hybrid search pipeline with FTS5 + vector scoring, temporal decay, MMR re-ranking"

**Dumping the whole design at once:**
- BAD: Present the entire 500-word plan and ask "looks good?"
- GOOD: Present architecture first, get approval, then data flow, get approval, then phases.

## Workflow Integration

This skill is an early step in the session workflow chain:

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
  (setup project)       (this skill)               (break into tasks)          (execute tasks)           (refine and test)                  (version & publish)
```
