---
name: session-research-design
description: Deep research and design workflow for complex features. Use before /session-task-planning when a feature requires exploring implementation approaches, analyzing existing code, and designing an architecture before breaking into tasks. Attaches to a work item by identity and produces a research report plus the spec and plan that work warrants. Triggers on "/session-research-design" or when user says "research this", "explore approaches for", or "design this feature".
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
6. **Everything attaches to a work item.** Design for a `SEQ` that already exists, or capture one first. Never write a dated design document that no work item names -- an artifact with no identity is one nobody can select, claim, verify, or supersede.

## Core Principle

Complex features require understanding before planning. What this skill produces belongs to one work item, addressed by its identity:

1. **Research report** -- the project's research directory, `YYYY-MM-DD-{topic}.md`. It explores the problem space, is reusable beyond this item, and is therefore linked from the item rather than copied into it. Skippable when the understanding already exists (Step 2).
2. **`spec.md`** in the item directory -- desired behaviour and design. Only when the work warrants a separate specification.
3. **`plan.md`** in the item directory -- execution approach and order. Only when the work warrants a separate plan.

A small clear item gets neither companion file: its approach goes into `intent.md` beside the intent, and that one record is the whole design output. Never write an empty `spec.md` or `plan.md` to complete a set.

Read `paths.research`, `paths.plans`, and `paths.work` from `.session-flow.json`. Paths may point outside the repo; resolve them relative to the repo root. If the config or the work root is missing, suggest running `/session-init`.

Research direction and design both go through user review. The accepted item feeds `/session-task-planning` by identity, not by filename.

## Workflow

### Step 0: Resolve the Runtime and the Work Item

Every record change goes through the helper at `<package-root>/scripts/session-flow.py`. Resolve it by the one rule for this host (`references/runtime-integration.md`): the plugin root in `${CLAUDE_PLUGIN_ROOT}` for a native plugin, the discovered installed package location under Codex, the `session-flow-runtime.json` descriptor beside this `SKILL.md` for a standalone copy. Confirm it answers, with absolute paths for interpreter and entrypoint:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
```

Report what is missing and stop when it cannot answer. There is no hand-editing path.

Then settle which work item this design belongs to:

- The caller named a `SEQ`: read it and design against what it already says.

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-042
```

- The caller named none: run `select` to see whether a captured item already covers this topic, and ask before designing against it.
- Nothing covers it: capture one through the runtime before writing any artifact, then design against that identity.

Read the item's `original_request` before its interpretation, and design for the request. Where the two differ, say so and let the user settle it -- an interpretation you inherit unexamined is the failure this record exists to prevent.

**Capture is not acceptance and neither is this skill.** A `captured` item stays unexecutable while it is designed; writing `spec.md` grants nothing. Acceptance is one explicit decision in Step 7.

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

**Output:** A clear topic name (kebab-case, for file naming), a 2-3 sentence scope statement, and the `SEQ` this work belongs to.

### Step 2: Research

**Skip check, first.** Research is skippable when either holds:

- A recent research artifact for this topic exists in the research directory, still matches the framing from Step 1, and the user agrees it stands.
- The user states the problem is already understood and does not want it re-researched.

If skipping, say so explicitly ("Skipping research — relying on `{path}` / your description of X"), go to Step 5, and name that basis in whichever artifact Step 5 produces -- the plan's Context section, or `intent.md` when the item stays compact. When in doubt, research; skipping on a stale artifact is worse than a short second pass.

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

The report stays where it is. Do not copy it into the item; link it in Step 7 with role `research`, so one report can serve several items and a correction reaches all of them.

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

### Step 5: Design Artifacts

After the user approves the research direction (or immediately after Step 1, if research was skipped), decide what this item needs and write only that.

**Load the house rules first.** Read `paths.conventions` and `paths.lessons` from `.session-flow.json` when they are set and the files exist:

- **Conventions** are one-line `rule — reason` entries. Design to them. Where the design departs from one, say so in the plan with the reason — a departure is a decision to record, never a blocker.
- **Lessons** are a one-line index. Read the lines; load nothing further unless a line looks relevant to this topic.
- **If either key is unset or the file is missing, say so** ("No conventions file configured — designing against CLAUDE.md and observed patterns") and proceed on `CLAUDE.md` plus the patterns the research actually found. Never silently invent a house style.

**Targeted lookups are allowed here.** If a design decision turns on a detail the research didn't cover — an exact signature, whether a helper already exists, how an existing caller behaves — re-dispatch `codebase-researcher` with that narrow question and continue. Do not make the user exit and re-run the skill, and do not guess. The same applies while iterating in Step 6.

**Decide compact or expanded, and say which you chose.** The item grows the artifacts its responsibility needs and no others:

| What the work is | What you write |
|------------------|----------------|
| One clear change, cause and approach understood, one repository, provable by a check that already exists | Nothing new. Carry the approach and the next action into `intent.md` through `revise`; that record is the design. |
| Behaviour or design needs settling on its own -- a contract, a schema, several consumers, a decision someone will re-read | `spec.md` in the item directory |
| Execution spans phases, sessions, or repositories, so order, boundaries, and checks need their own home | `plan.md` in the item directory |

A task that grows after investigation **keeps its `SEQ`**. Add the artifact the expanded responsibility needs; never re-capture the work under a second identity.

Both files are ordinary Markdown in `{work}/seq-NNN/`, carrying no metadata fence -- identity lives in `intent.md`, which links them. Link shared research, architecture docs, and decision records instead of copying them; a copy is the revision that quietly goes stale.

**`spec.md` template:**

```markdown
# {Topic} Specification

**Item**: SEQ-NNN
**Research**: `{path-to-research-report}` — or `skipped: {basis}`

## Desired Behaviour
{What the system must do, stated from the consumer's side and observable. Not implementation.}

## Design
{The structure that delivers it, the decisions that shaped it, and the alternatives rejected.}

## Constraints and Non-Goals
{What bounds the design, and what it deliberately does not do.}
```

**`plan.md` template:**

```markdown
# {Topic} Plan

**Item**: SEQ-NNN
**Spec**: `spec.md` — omit this line when there is none
**Research**: `{path-to-research-report}` — or `skipped: {basis}` when Step 2 was skipped

## Context
{Problem and chosen approach; the research doc carries the full analysis. If research was skipped, name what this plan relied on instead — the prior artifact and its date, or the user's stated understanding.}

### Architecture Decision
{The key architectural choice and why.}

## Module Structure
{File tree for new modules, if applicable.}

### Integration Points
{Where new code connects to existing code — files and locations.}

## Phase N: {Phase Name}
**Files created:** `path/to/file.py` -- {purpose}

**Files modified:** `path/to/existing.py` -- {what changes}

**Design notes:** {schema changes, API contracts}

**Accept**: {observable outcome proving this phase works}

**Commit**: `{conventional commit message}`

{Repeat per phase; each phase independently deployable and testable.}

## Success Criteria
| Criterion | Measurement |
|-----------|-------------|
```

Write no status header in either file. Lifecycle state lives in `intent.md`, where the runtime maintains it; a `Status: Planned` line in a design document is the stale field that made date-based selection unreliable.

A design spanning several work items stays one dated document in the plans directory, and each item references it at its commit. Do not fragment it into per-item copies.

### Artifact Precedence and Acceptance

One rule per question, so no later consumer has to guess which document to believe:

- **Accepted behaviour is the scope region of `intent.md`.** Acceptance criteria derive from that text and from the documents it pins under `references` -- never from whichever plan is newest, and never from a Success Criteria table alone. A plan's table restates the accepted criteria for execution; it cannot add accepted behaviour.
- **`spec.md` prevails over `plan.md` on desired behaviour and design.** `plan.md` prevails on execution approach, order, and boundaries. A plan that contradicts the spec on behaviour is wrong: correct the plan, and never verify against it.
- **When there is no `spec.md`, the scope region is the specification.** Nothing is promoted into that role by being the newest file.
- **A referenced document is identified by its work-root commit**, as `{"path": ..., "commit": ..., "role": ...}` in the item's `references`. A filename alone cannot say which revision was accepted. Those entries are part of the acceptance fingerprint, so pinning them is Step 7's job, not a formality.
- **Re-pinning a changed `spec.md` is a scope change.** It moves the fingerprint, which invalidates acceptance and the applicability of evidence gathered against the old one. Take that deliberately: a reworded spec that means the same thing is a `revise` carrying a `same_meaning` decision, which records both fingerprints in one step and keeps acceptance; a spec that means something else needs a fresh decision.

### Step 6: User Review (Design)

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

### Step 7: Link, Pin, Accept

Once the user approves the design:

1. Confirm what exists: the research report unless Step 2 was skipped, and whichever of `spec.md` and `plan.md` the work warranted. Nothing else.
2. Land the item's links through `transition`, which commits the work root with those new files in it and reports the commit under `result.commit`:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" transition --input links.json
```

```json
{"operation": "<uuid4>",
 "changes": [{"seq": "SEQ-042", "expect_revision": 3,
   "metadata": {"links": [{"role": "specification", "target": "spec.md"},
                          {"role": "plan", "target": "plan.md"},
                          {"role": "research", "target": "_devdocs/research/2026-09-07-topic.md"}]}}]}
```

3. Pin every behaviour or criteria document the acceptance depends on, at the commit that transition reported:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" revise --seq SEQ-042 --input references.json
```

```json
{"expected_revision": 4,
 "metadata": {"references": [{"path": "spec.md", "commit": "<work-root commit>", "role": "specification"}]}}
```

   When `result.commit.committed` is false the work root is unversioned: say so, list nothing under `references`, and state plainly that acceptance then covers the scope text alone. Do not invent a commit.

4. Ask the user to accept, and accept only what they said. Name the actor and the authority their decision rests on -- the direction doc at its commit, or their approval and when it was given. Approving a design is not acceptance until this runs, and no file you wrote is acceptance:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" accept --seq SEQ-042 --input accept.json
```

```json
{"expected_revision": 5, "actor": "<who decided>",
 "authority": {"source": "_devdocs/PRD.md", "revision": "<commit or approval timestamp>"},
 "scope": "implement and verify; delivery needs its own authority"}
```

   The `scope` names which actions the decision covers. Investigate, implement, create PR, merge, deploy, and external posting stay separate: an acceptance that says "implement and verify" authorizes neither a merge nor a deployment.

5. Suggest: "SEQ-042 is designed and accepted. Run `/session-task-planning` for SEQ-042 to break it into task records" -- or, for a small item that stayed compact, "/session-next will pick it up."

## File Naming

The research report follows the `YYYY-MM-DD-label.md` convention with today's date and a lowercase kebab-case label. Item files do not: `spec.md` and `plan.md` are named by their role inside `{work}/seq-NNN/`, because the directory already carries the identity and the date.

## Anti-Patterns

**Over-researching:**
- BAD: 10 reference implementations with exhaustive analysis for a simple feature
- GOOD: Scale research depth to feature complexity. Simple features need 1-2 references.

**Vague plans:**
- BAD: "Phase 2: Implement the feature"
- GOOD: "Phase 2: Hybrid search pipeline with FTS5 + vector scoring, temporal decay, MMR re-ranking"

**Orphan design documents:**
- BAD: A dated plan in `plans/` that no work item references, found later by date and assumed current
- GOOD: The design lives in the item, or is linked from it and pinned at a commit

**Filling the set:**
- BAD: `spec.md` and `plan.md` for a one-file fix, each three lines long
- GOOD: The approach in `intent.md`, and nothing else written

Chain context: see `references/workflow-overview.md`.
