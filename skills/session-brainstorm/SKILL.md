---
name: session-brainstorm
description: Use when the user says "let's brainstorm" or "let's think about", or brings an idea that is not yet a task. Explores intent and options in conversation, ends with a short design the user approves, then routes to implementation or to /session-research-design.
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

## Three paths

Classify the request before the first question, and say the classification.

- **Spike.** A feasibility question: "can we", "is it possible", "quick and dirty is fine". The
  output is an answer, not code to keep. Say what you will try in two or three sentences, get a
  nod, find out as cheaply as correctness allows, and report a recommendation. Anything built is
  labelled throwaway.
- **Bounded.** A well-scoped change to a flow that already exists in the repo: a flag, a small
  endpoint, a one-file fix. Ask the questions that matter, present a short design in chat
  (approach, files touched, how it will be tested), and stop until the user says yes. Then
  implement, or capture it with `/session-add-task` if it is for later.
- **Architectural.** A new subsystem, a new project, or a change to how components fit together.
  Do not design it here. Frame the problem with the user, then hand off to
  `/session-research-design`, which produces the research report and the plan.

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

## Handoff

- Spike: report the recommendation. Done.
- Bounded, approved: implement directly, or `/session-add-task` for later.
- Architectural: `/session-research-design`.

Derived from the `brainstorming` skill in superpowers by Jesse Vincent (MIT); see
`THIRD_PARTY_NOTICES.md`. Chain context: `references/workflow-overview.md`.
