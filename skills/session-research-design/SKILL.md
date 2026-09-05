---
name: session-research-design
description: Deep research and design workflow for complex features. Use before /session-task-planning when a feature requires exploring implementation approaches, analyzing existing code, and designing an architecture before breaking into tasks. Produces a research report and an implementation plan that feeds into session-task-planning. Triggers on "/session-research-design" or when user says "research this", "explore approaches for", or "design this feature".
---

# Session Research & Design

Conduct deep research and produce a design plan before task planning.

Open with one sentence saying what you are about to do and what it will produce.

## Non-Negotiables

1. **Never guess scope.** If the user's ask is ambiguous, ask a clarifying question. Do not assume.
2. **Always propose alternatives.** Present 2-3 approaches with explicit trade-offs. Do not ship a single-option "recommendation" — the user cannot make an informed choice without alternatives.
3. **Research before planning, unless it is already done.** The research report is normally a prerequisite to the plan, and the two are never compressed into one step. Research may be skipped only when a recent research artifact for this topic exists, or the user states the problem is already understood — in which case the plan's Context section names what it relied on instead. **Framing (Step 1) is never skipped**; it is the cheapest gate in the chain.
4. **User approves section-by-section.** Do not dump the full plan and ask "looks good?". Present in sections and get feedback on each.
5. **Cite the codebase.** Every claim about "what exists" must reference files/line numbers. "The auth module handles tokens" is not acceptable without a citation.

## Core Principle

Complex features require understanding before planning. This skill produces two artifacts:

1. **Research report** (saved to the project's research directory) -- explores the problem space. Skippable when the understanding already exists (Step 2).
2. **Implementation plan** (saved to the project's plans directory) -- defines the build path. Always produced.

Both use the `YYYY-MM-DD-{topic}.md` naming convention. Directory paths are read from `.session-flow.json` config, or auto-detected by looking for `research/`, `_devdocs/research/`, `docs/research/` (and `plans/`, `_devdocs/plans/`, `docs/plans/` respectively). Paths may point outside the repo; resolve them relative to the repo root. If no matching directory is found, suggest running `/session-init`.

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

**Skip check, first.** Research is skippable when either holds:

- A recent research artifact for this topic exists in the research directory, still matches the framing from Step 1, and the user agrees it stands.
- The user states the problem is already understood and does not want it re-researched.

If skipping, say so explicitly ("Skipping research — relying on `{path}` / your description of X"), go to Step 5, and name that basis in the plan's Context section. When in doubt, research; skipping on a stale artifact is worse than a short second pass.

Otherwise, dispatch the research agents:

```
codebase-researcher — one dispatch, or two with different questions
  "{Specific question about the existing code for {topic}: which modules,
   schemas, APIs, and integration points exist, and how does the current
   flow work?} Cite file:line on every claim. Report 'not found' explicitly.
   No recommendations."

  Split into two dispatches when the questions are genuinely different —
  e.g. one mapping the current architecture, one on how comparable features
  are already structured (conventions, protocols, abstractions to match).

external-researcher — when the approach is not obvious from the codebase
  "{Question about prior art for {topic}.} Find 3-5 reference
   implementations with concrete architecture details."

  It has no repository access by design. Put any repo context it needs
  — the framing, relevant interfaces, constraints — in the payload.
```

Send the dispatches in a **single message** for parallel execution.

**If the topic is narrow** (single module, clear approach): drop `external-researcher` and reduce to one `codebase-researcher` dispatch.

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
{What the codebase already has, cited file:line.}

### Architecture
{Current architecture relevant to this topic.}

### Gaps
| Gap | Impact |
|-----|--------|

---

## 2. Reference Implementations

### 2.1 {Reference Name}
**Source:** {link} — **Architecture:** {how it works} — **Relevance:** {what to borrow}

{Repeat per reference, 3-5 typical.}

---

## 3. Comparative Analysis
| Dimension | Approach A | Approach B | Approach C |
|-----------|-----------|-----------|-----------|

---

## 4. Recommendation
**Recommended approach:** {name} — {rationale, referencing the comparison}

**Key design decisions to resolve:** {list}

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

After the user approves the research direction (or immediately after Step 1, if research was skipped), write an implementation plan to the project's plans directory as `YYYY-MM-DD-{topic}-implementation.md`.

**Load the house rules first.** Read `paths.conventions` and `paths.lessons` from `.session-flow.json` when they are set and the files exist:

- **Conventions** are one-line `rule — reason` entries. Design to them. Where the design departs from one, say so in the plan with the reason — a departure is a decision to record, never a blocker.
- **Lessons** are a one-line index. Read the lines; load nothing further unless a line looks relevant to this topic.
- **If either key is unset or the file is missing, say so** ("No conventions file configured — designing against CLAUDE.md and observed patterns") and proceed on `CLAUDE.md` plus the patterns the research actually found. Never silently invent a house style.

**Targeted lookups are allowed here.** If a design decision turns on a detail the research didn't cover — an exact signature, whether a helper already exists, how an existing caller behaves — re-dispatch `codebase-researcher` with that narrow question and continue. Do not make the user exit and re-run the skill, and do not guess. The same applies while iterating in Step 6.

**Plan template:**

```markdown
# {Topic} Implementation

**Date**: YYYY-MM-DD
**Status**: Planned
**Goal**: {one sentence}
**Research**: `{path-to-research-report}` — or `skipped: {basis}` when Step 2 was skipped

---

## Context
{Problem and chosen approach; the research doc carries the full analysis. If research was skipped, name what this plan relied on instead — the prior artifact and its date, or the user's stated understanding.}

### Architecture Decision
{The key architectural choice and why.}

---

## Module Structure
{File tree for new modules, if applicable.}

### Integration Points
{Where new code connects to existing code — files and locations.}

---

## Phase N: {Phase Name}
**Files created:** `path/to/file.py` -- {purpose}

**Files modified:** `path/to/existing.py` -- {what changes}

**Design notes:** {schema changes, API contracts}

**Accept**: {observable outcome proving this phase works}

**Commit**: `{conventional commit message}`

{Repeat per phase; each phase independently deployable and testable.}

---

## Success Criteria
| Criterion | Measurement |
|-----------|-------------|

---

## References
- Research report: `{path-to-research-report}`
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

1. Confirm the artifacts are saved:
   - Research report in the project's research directory (unless Step 2 was skipped)
   - Implementation plan in the project's plans directory
2. Suggest: "Plan is ready. Run `/session-task-planning` to break this into executable tasks."

## File Naming

Follow the `YYYY-MM-DD-label.md` convention. Use today's date for both the research report and implementation plan. Label should be lowercase kebab-case.

## Anti-Patterns

**Over-researching:**
- BAD: 10 reference implementations with exhaustive analysis for a simple feature
- GOOD: Scale research depth to feature complexity. Simple features need 1-2 references.

**Vague plans:**
- BAD: "Phase 2: Implement the feature"
- GOOD: "Phase 2: Hybrid search pipeline with FTS5 + vector scoring, temporal decay, MMR re-ranking"

Chain context: see `references/workflow-overview.md`.
