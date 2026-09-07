---
name: session-brainstorm
description: Use when the user says "let's brainstorm" or "let's think about", or brings an idea that is not yet a task. Explores intent and options in conversation, ends with a short design the user approves, captures it as a work item, then routes to implementation or to /session-research-design.
---

# Session Brainstorm

Turn an idea into a decision the user has approved, before anything is built.

Open with one sentence saying what you are about to do and what it will produce.

## Rules

1. **Nothing is implemented until the user has approved a design.** This holds for a two-sentence
   change as much as for a subsystem. The size of the design scales with the task; the approval
   does not.
2. **One question per message.** Prefer multiple choice when the options are known. Let each
   answer shape the next question.
3. **Options come with a recommendation.** Present two or three approaches with their trade-offs
   and say which one you recommend and why.
4. **Classify out loud.** Say which path the request is on, so the user can override it.
5. **Nothing leaves this skill without a captured work item.** Every path that continues past a
   spike allocates identity first, through `/session-add-task`, which writes the record with the
   runtime. Capture is not permission: the item lands in `captured`, `select` refuses it by name,
   and the user's approval of the design is what makes it acceptable — not the fact that a record
   now exists.

## Three paths

Classify the request before the first question, and say the classification.

- **Spike.** A feasibility question: "can we", "is it possible", "quick and dirty is fine". The
  output is an answer, not code to keep. Say what you will try in two or three sentences, get a
  nod, find out as cheaply as correctness allows, and report a recommendation. Anything built is
  labelled throwaway.
- **Bounded.** A well-scoped change to a flow that already exists in the repo: a flag, a small
  endpoint, a one-file fix. Ask the questions that matter, present a short design in chat
  (approach, files touched, how it will be tested), and stop until the user says yes. Then capture
  it with `/session-add-task` — the design becomes the record's interpreted intent and the
  approved behaviour becomes its scope — and implement against that identity, or leave it
  captured if it is for later.
- **Architectural.** A new subsystem, a new project, or a change to how components fit together.
  Do not design it here. Frame the problem with the user, capture the framed problem with
  `/session-add-task` so the work has an identity before anyone researches it, then hand that
  identity to `/session-research-design`, which produces the research report and the plan against
  it.

When in doubt between two paths, take the larger one. Complexity found mid-task moves the work up
a path; say so when it happens.

## Understanding the idea

- Read the current state first: files, docs, recent commits.
- If the request describes several independent pieces, say so before refining any of them, and
  help the user decide which piece comes first.
- Focus on purpose, constraints, and what success looks like.
- Remove features that do not serve the purpose from every option you present.

## Presenting a design

- Scale each part to its difficulty: a few sentences where it is straightforward, a short
  paragraph where it is not.
- Cover the approach, the files touched, how it will be tested, and what it deliberately leaves
  out.
- Where existing code has a problem the work must touch, include the targeted fix in the design.
  Do not propose unrelated refactoring.
- Ask whether the design looks right, and wait for the answer.

## Capturing what came out

`/session-add-task` writes the record; this skill supplies what goes in it, and the distinction it
must preserve is the one this conversation is uniquely able to make:

- **`original_request`** — the user's own words that opened the brainstorm, verbatim. Not the
  refined version you arrived at together.
- **Interpreted intent** — what you understood, including what you removed from the idea and why.
- **Scope** — the approved behaviour, in terms the user would recognize as what they asked for.
- **Provenance** — `origin: "user"`, the actor, and the capture time. No `[auto]`: the user was
  here for this.
- **Open questions** — anything the design left unsettled, in the body. A brainstorm that ended in
  agreement can still have them.

Report the allocated `SEQ-NNN` and say plainly that it is captured, not accepted.

## Handoff

- Spike: report the recommendation. Done — a throwaway answer is not a work item. Capture only the
  follow-up work the answer revealed, if any.
- Bounded, approved: capture with `/session-add-task`, then implement against that identity, or
  leave it captured for later.
- Architectural: capture with `/session-add-task`, then `/session-research-design` against that
  identity.

Derived from the `brainstorming` skill in superpowers by Jesse Vincent (MIT); see
`THIRD_PARTY_NOTICES.md`. Chain context: `references/workflow-overview.md`.
