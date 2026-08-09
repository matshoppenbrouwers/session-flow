# session-flow v5 — specification

Draft for implementation, 9 August 2026. Written against repo state v1.2.1 (commit `8addfa3`): 13 skills, 4 agents, the `todo/SEQUENCE.md` sequence layer, `.session-flow.json` with eight configured paths.

Supersedes v4. Differences from v4 come from an independent review against the actual repo and the Claude Code changelog, with decisions confirmed by Mats: the research-design split is dropped, test-author moves from post-hoc to up-front oracle, the `[scope:]` tag is replaced by the existing Files field, and four verified repo defects are fixed before anything new is built. Runtime claims below were checked against the Claude Code changelog; where something could not be verified, that is stated.

---

## 1. Summary

| Change | Type | Rationale |
|---|---|---|
| Fix four verified defects (§3) | Fix, ships first | Cheaper and higher-value than any new feature |
| Keep `session-research-design` as one skill; add skip-research path | Non-breaking | Split's benefits come from the agents, not the split; two lookalike skills worsen routing |
| Add `codebase-researcher` agent | Additive | Enforced read-only containment; replaces the skill's ad-hoc Explore agents |
| Add `external-researcher` agent — **no repo `Read`** | Additive | v4's tool list (Read + WebSearch + WebFetch) was itself the lethal trifecta |
| Add `test-author` agent — up-front oracle, per phase | Additive + rewiring | Independent test authorship with TDD preserved; delegation/next rewired to use it |
| Files field becomes the write boundary; no `[scope:]` tag | Non-breaking | Uses existing format; injected at dispatch; prompt-level, honestly labelled |
| Remove `mode: "bypassPermissions"` from delegation | Fix | Task tool `mode` param deprecated and ignored since Claude Code v2.1.212 |
| Add `paths.conventions` + `conventions.md`, wired to design **and** code-reviewer | Additive, optional | A conventions store the reviewer never reads splits the source of truth |
| Prescriptiveness trim across skill bodies | Cleanup | Remove instructions that restate default model behaviour; keep contracts and counter-prior rules |
| Recommend `claude-mem`; define a lessons file home | Docs + config | Recall solved externally; lessons get a path and a producer |

Skills: 13 → 13. Agents: 4 → 7.

**Prerequisite, gating the whole spec: run `/session-gatekeeper` against real items first.** It has never executed, and §7 builds on its routing behaviour. One run may change more of this document than the v4→v5 revision did.

---

## 2. The chain (unchanged shape)

```
session-init
    │
    ├─> session-gatekeeper ──> (sequence, or escalate to research-design)
    │
    ├─> session-research-design ──> session-task-planning
    │      research phase (skippable)      │
    │      └ codebase-researcher /         │
    │        external-researcher           │
    │      design phase                    │
    │      └ re-dispatches researcher ◄────┘ iteration
    │                                      │
    └────────────────────> session-delegation ──> session-post-implementation
                              │                            │
                        test-author (once,           session-verify
                        per phase, up front)               │
                              │                      session-release
                        implementers
                        (oracle: the tests)

sequence layer:  gatekeeper / add-task / task-planning ──> SEQUENCE.md ──> groom ──> next
```

Gatekeeper escalations go to `session-research-design`, exactly as today. No renaming anywhere.

---

## 3. Step 0 — verified defects, fixed before anything else ships

These were confirmed against the repo and the Claude Code changelog. They ship as their own commit(s) ahead of the feature work.

1. **Dead dispatch parameter.** `session-delegation` (SKILL.md:58, 67, 73) instructs `mode: "bypassPermissions"` on Task dispatches. Claude Code v2.1.212 deprecated the Task tool's `mode` parameter — it is now ignored; subagents inherit the parent session's permission mode. Remove the parameter and the stale fallback note. (Same edit site as §6's boundary injection.)
2. **`update-architecture` hardcodes `_devdocs/`.** SKILL.md:29–30 requires `paths.architecture` to equal `_devdocs/architecture` and forbids other roots — contradicting `session-init` (which offers `docs/`), init's own anti-pattern list, post-implementation Step 7's detection, and CONTRIBUTING's grep check. Fix: resolve `paths.architecture` from config like every other skill; drop the seventeen hardcoded occurrences.
3. **Phantom `paths.design`.** `session-verify` (SKILL.md:35) and `session-release` (SKILL.md:44) read `.session-flow.json.paths.design` and scan `_devdocs/design/`; no skill writes that key and nothing creates that directory. Consequence: release's verification pre-flight can silently never fire. Fix: repoint both to `paths.plans` (the implementation plan is the design doc) with `paths.research` as secondary; delete the `design` references.
4. **Plugin-relative reference paths in dispatch payloads.** Post-implementation Step 3 (SKILL.md:112) tells the dispatched security-auditor to read `skills/security-liability-audit/references/…` — relative to nothing the subagent knows. Fix: the loading skill resolves its own location and passes absolute paths in the payload (or anchors on `${CLAUDE_PLUGIN_ROOT}`).
5. **Cross-reference drift** (folded into the §10 trim): verify says post-impl "Step 7.5" (actual 8.5); workflow-overview puts update-architecture at "Step 6" (actual 7) and claims research-design produces "decision log entries" (it doesn't); customization-guide says "three agents" and "Step 5". Rule going forward: cross-reference steps by name, not number.

---

## 4. `session-research-design` stays one skill

Three changes, all internal:

1. **Skip-research path.** Non-negotiable 3 ("Research before planning… Do not compress both into one step") relaxes to: research may be skipped when a recent research artifact for this topic exists, or the user states the problem is understood — in which case the plan's Context section names what it relied on instead. The framing conversation (Step 1) is never skipped; framing is the cheapest gate in the chain.
2. **Step 2 dispatches the new agents.** The ad-hoc "Explore agent" prompts are replaced by `codebase-researcher` (agents 1–2 collapse into one dispatch, or two with different questions) and `external-researcher` (former agent 3), in parallel where both apply. Narrow topics still reduce to one dispatch.
3. **Design-phase iteration.** During Steps 5–6, the skill may re-dispatch `codebase-researcher` for targeted lookups rather than making the user exit and re-run. Iteration happens inside the step. (The best idea from v4 §2, kept without the split.)

Research findings keep the discipline v4 §4 described: claims carry file:line or URL provenance; "the codebase does X" belongs in research, "the codebase should do X" belongs in design. Gatekeeper escalations arrive with framing partly done — don't re-interview from zero.

---

## 5. Agents

### 5.1 `codebase-researcher` — as v4 specified

```yaml
---
name: codebase-researcher
description: Maps an existing codebase to answer a specific research question. Read-only.
tools: Read, Grep, Glob
model: sonnet
maxTurns: 30
---
```

No network, no Bash, no Write/Edit. Repo read + network egress + a return channel is the lethal trifecta the plugin's own security reference defines; keeping this agent airtight is the reason it is an agent rather than inline grep. Body requires file:line on every claim, explicit "not found", no recommendations. `model: sonnet` is a deliberate, documented exception to the inherit-by-default policy (mapping is high-volume pattern matching); note that in the agent body so the CONTRIBUTING checklist doesn't get it "fixed". (`maxTurns` and model aliases in plugin-agent frontmatter are confirmed supported; `CLAUDE_CODE_SUBAGENT_MODEL` overrides session-wide.)

### 5.2 `external-researcher` — corrected from v4

```yaml
---
name: external-researcher
description: Researches external sources — docs, specs, prior art — with source validation.
tools: WebSearch, WebFetch
model: sonnet
maxTurns: 30
---
```

**No `Read`.** V4 gave it Read + WebSearch + WebFetch, which is itself the full trifecta by the plugin's own definition (technical-security.md §2): unrestricted repo read (private data, including `.env`), web pages (untrusted content), and outbound fetches (exfiltration — a URL can carry data out). The dispatcher passes the research question and any needed repo context *in the payload*; the agent never touches the filesystem. If a future need for reading local files appears, scope Read to the research directory via permission rules rather than restoring blanket access.

Body carries the v4 source-validation discipline unchanged: primary sources, publication dates, vendors flagged, conflicts presented not resolved, documented vs asserted.

### 5.3 `test-author` — up-front oracle, per phase

```yaml
---
name: test-author
description: Writes acceptance tests from a design specification and public interface, before implementation. Never reads or modifies implementation code that already exists for the tasks under test.
tools: Read, Grep, Glob, Write, Edit, Bash
model: inherit
maxTurns: 40
---
```

**Timing is the design decision, and it inverts v4.** V4 had tests written after implementation, which loses the external-oracle role the current workflow (and the 1.2.1 change) deliberately preserves. Instead:

- `session-delegation`, before dispatching a phase's implementers, dispatches `test-author` **once for the phase**, with the design artifact, the public interface (signatures, types, contracts), and each task's Accept criterion. It writes the acceptance tests — red, since the code doesn't exist yet — and reports the test paths per task.
- Implementer dispatch prompts change from "write a test that validates the acceptance criteria" to: "the tests at {paths} are your acceptance oracle — make them pass; **never modify a test file**; if a test seems wrong, stop and report."
- One extra dispatch per phase, not per task. Independence and TDD, at marginal cost.

**Rewiring (this is the work v4 omitted):**

- `session-delegation` Step 4 item 2 and the agent prompt template item 2: replaced as above.
- `session-next`: small single-file backlog tasks **keep** the softened 1.2.1 self-written-test rule — dispatching a second agent for a 20-minute task is pure overhead. When the entry links to a phase file, delegation's flow (and therefore test-author) applies.
- Breakdown/task templates: the `Test` field is unchanged — it remains the exact command; test-author is now its producer for phase work.

**Stated limitation, kept honest from v4:** `Read` means the agent *can* open pre-existing implementation; enforcement is by prompt and by what the dispatcher puts in the payload. For greenfield phase work the code doesn't exist yet, which is the strongest containment available. The implementer-side "never modify tests" rule is likewise prompt-level; §6's Files boundary excludes test paths from implementer allowlists for free, and the Appendix hook can harden it.

### 5.4 No implementer agent

Unchanged from v4 §6.4: a named implementer buys nothing over vanilla dispatch; the write boundary is injected at dispatch time (§6).

### 5.5 Unchanged

`code-simplifier`, `code-reviewer` (gains one line in §8), `security-auditor`, `code-sanitizer`.

---

## 6. Write scoping — the Files field is the boundary

No `[scope:]` tag. Rationale, verified: the Task tool's permission-affecting parameter was deprecated (v2.1.212) and nothing in the changelog supports injecting `permissions.deny` rules per dispatch — so any tag would be prompt-level anyway, while adding a new token to a format that `session-scribe` parses by convention. The existing task format already carries the boundary.

1. **Files may contain directory globs.** `**Files**: src/lib/governor/**` is now valid alongside exact paths, in task-planning, add-task, and groom templates. One line of documentation; no parser anywhere breaks, because nothing parses Files structurally.
2. **Delegation injects Files as an explicit write constraint** in every dispatch payload: "You may only create or modify these paths: {Files}. If the task requires touching anything else, stop and report — do not proceed." Same edit removes the dead `mode:` parameter (§3.1).
3. **Honest labelling.** This is a hint, not a boundary. Its value: agents that wander now stop and report instead of writing, violations become visible, and parallel batches whose Files sets are disjoint (already checked by task-planning non-negotiable 5) stay inside their declared footprint. It does **not** make wrongly-parallelised tasks safe — disjoint write sets don't remove semantic dependencies — so the dependency analysis keeps its current weight.
4. **Enforced version: Appendix A**, built only if an agent is ever observed writing outside its lane. Same evidence discipline as everything else here.

---

## 7. Gatekeeper and the ops boundary — v4 §3, with three corrections

The division of labour stands: session-flow owns routing and judgement; the ops plugin owns the feed and the clock; intake enqueues and never executes; the coupling degrades rather than breaks (raw items dropped into a known location, routed if gatekeeper is installed, inert if not). The `[auto]` provenance marker stands.

Corrections, all verified against the Claude Code changelog:

1. **Headless sessions can invoke slash commands directly.** V4's claim that a scheduler "doesn't invoke slash commands — it runs `claude -p` headless, and skills are discovered by description matching" is wrong in its premise: known slash commands run in headless/SDK mode (unknown ones now error rather than silently no-op). The conclusion is unchanged and stronger — the scheduler runs `claude -p "/session-gatekeeper …"` by name, no description-matching lottery, no port, no rebuild.
2. **Check native scheduling before building an ops scheduler.** Claude Code has `/loop`, session-scoped cron tools (`CronCreate`/`CronList`), scheduled tasks that `--resume` resurrects, and webhook trigger deliveries. Session-scoped crons don't cover the no-session-running case, so the ops plugin's role likely survives — but verify the webhook path first; it may already be most of the feed.
3. **The `[auto]` marker's writer is `session-add-task`** (gatekeeper hands enqueuing to it), so add-task gains the parameter — not just "gatekeeper's enqueue path". And because `[auto]` changes the SEQUENCE.md line format that session-scribe mirrors into Notion, test the scribe parser against marked lines before shipping; that plugin integrates by file-format convention, which makes this a cross-plugin change even though no code is shared.

`/loop 30m /session-gatekeeper` covers periodic intake while a session is live, as v4 credited.

---

## 8. Conventions — separate file, with consumers actually wired

`paths.conventions` is added to `.session-flow.json`, optional, defaulting to `{root}/conventions.md`. Kept out of `CLAUDE.md` deliberately: CLAUDE.md content costs tokens on every turn of every session, while conventions matter at design and review time.

Format as v4 §8: one-line entries, `rule — reason`, ~140-character limit, reasons mandatory (without the reason, design either treats the rule as gospel or ignores it). The discriminator stands: if it doesn't fit on one line it's an architecture decision, and `/update-architecture`'s `decisions.md` owns those.

**The wiring v4 omitted — a conventions store only design reads splits the source of truth:**

- `session-research-design` (design phase) loads it; if unset or missing, says so and proceeds on `CLAUDE.md` plus observed patterns — never silently invents a house style. Departures are flagged with reasons, not blocked.
- `code-reviewer` gains one line: alongside CLAUDE.md conventions, read `paths.conventions` from `.session-flow.json` when present and enforce its entries.
- `session-init` offers (never forces) to scaffold the file, same pattern as the PRD stub.
- Optionally, delegation includes the file in implementer payloads when it exists and is short — it's designed to be short.

Populate by having `codebase-researcher` draft one from the existing code, then prune hard; the highest-value entries are the negatives — what was tried and rejected — because that evidence was deleted from the codebase and nothing else records it.

---

## 9. Memory — recommend, don't build; give lessons a home

Recommend `claude-mem` in the README rather than reimplementing recall. Verification status from review: its worker service and `SessionEnd` hook are confirmed from its README; the specific port claim (37777) and the cited claude-code issue number for hook coexistence could **not** be verified — before recommending it alongside session-scribe, test both plugins' `SessionEnd` hooks together directly rather than citing the issue.

Lessons (conclusions, not observations) get what v4 left undefined: `paths.lessons`, optional, defaulting to `{root}/lessons.md`; same one-line format as conventions; produced by periodically asking claude-mem to propose entries from what it observed, pruned by hand. `session-research-design` (design phase) and `session-delegation` read it as a one-line index, loading nothing further unless a line looks relevant.

---

## 10. The trim

Applied across skill bodies in this version, one commit per category so anything load-bearing that breaks can be bisected back in.

**Remove:**

- The **Workflow Integration chain diagram** repeated at the bottom of all 13 skills — replaced by one line pointing at `references/workflow-overview.md`. Loaded on every invocation, zero decision value mid-skill, and the most drift-prone content in the repo.
- **Anti-pattern entries that restate a non-negotiable** (roughly half of them — e.g. add-task's "Reused ids", groom's "Implementing during groom"). Keep only those whose BAD case is non-obvious, like task-planning's secretly-dependent-parallel example.
- **code-reviewer's per-language checklists** (Python/React/Go/Java sections). Current models know mutable default arguments and hook dependency arrays; the checklist costs tokens and anchors the review to listed items. Keep: scope detection, the 80% confidence gate, falsification discipline, the output contract, and the don't-touch-unchanged-code rules — those counteract model priors.
- **code-simplifier's before/after transform examples**; keep the constraints, budget, and output contract.
- **Placeholder prose inside research-design's templates**; keep the section lists (they're the artifact interop contract with verify and task-planning).

**Keep, explicitly:** every format contract (SEQUENCE line, Files/Instructions/Accept/Test, dependency tags, verify's artifact contract, agent output tables — other skills and session-scribe parse these); every non-negotiable that fights a model prior (triage-only, never overwrite breakdowns, mark `[x]` immediately, parallel-means-one-message, stop-on-blocking-failure, untrusted issue text, release's build gate, verify's never-edit-source); tool budgets and the Grep-not-Bash rule; the `**Announce:**` lines — they are the routing telemetry that makes a wrong skill load visible.

**Follow-through:** CONTRIBUTING.md currently mandates Anti-Patterns and Workflow Integration sections; edit the checklist to match, or every future skill regrows the ceremony. Fix the README token-budget figure while there (measured ~1.5k tokens of always-loaded metadata, not ~1,300).

---

## 11. The argument against this spec

Three honest risks. First, the up-front oracle serialises each phase behind one test-author dispatch, and tests written before code may not even collect until dependencies land — normal red-phase TDD, but a new failure surface in delegation's error handling; if it drags, the fallback is per-batch rather than per-phase authoring. Second, prompt-level write scoping will eventually be violated by some agent in some session; the spec accepts this knowingly, and Appendix A is the answer if it happens more than rarely. Third, the trim removes text that was added deliberately for Opus 4.7; some of it may have been quietly load-bearing — hence one commit per category, and if a skill's behaviour degrades, bisect before concluding the trim was wrong wholesale.

And the standing one: gatekeeper has still never run. Nothing in §7 is real until it has.

---

## 12. Migration

1. **Run `/session-gatekeeper` against real items.** Gates everything below.
2. Ship §3 fixes (defects 1–4) as standalone commits. Patch release.
3. Trim pass (§10), one commit per category; update CONTRIBUTING and the README token figure.
4. Create `codebase-researcher` and `external-researcher`; test standalone via `claude --agent <name>`; swap them into research-design Step 2; add the skip-research path and design-phase re-dispatch.
5. Create `test-author`; rewire delegation (oracle dispatch per phase, implementer prompt change, `mode:` removal already done in step 2's edit); leave session-next's small-task rule intact.
6. Files-as-boundary: document globs in the three templates; add the injection line to delegation.
7. Conventions + lessons: config keys, init scaffolding offer, design/read wiring, the one-line code-reviewer addition.
8. `[auto]` marker in add-task; teach groom, next, and session-status to read it; test session-scribe's parser against marked lines before enabling.
9. README: chain diagram, agents table (7), conventions/lessons docs, claude-mem recommendation with the coexistence caveat.
10. Bump minor. No breaking changes for existing artifacts or scripts.

---

## 13. Deliberately excluded

- **The research/design skill split** — its benefits ship via the agents and the skip-research path; two near-identical descriptions in a description-matched router is a cost with no remaining payer.
- **The `[scope:]` tag** — §6 gets the same behaviour from the existing Files field with no format change.
- **Post-hoc test authoring** — inverts the oracle; §5.3 explains the replacement.
- **Per-dispatch permission injection** — the mechanism class Claude Code deprecated; Appendix A is the version that exists.
- **Implementer, validator, story-writer, project-manager agents; backend/frontend split; memory skill; scheduling, event sources, metrics** — as v4 §12, unchanged reasoning.

---

## Appendix A — hook-enforced write boundary (optional, build on evidence)

If an agent is observed writing outside its Files boundary: a project- or plugin-level `PreToolUse` hook that denies `Edit`/`Write`/`NotebookEdit` when the target path falls outside the declared scopes. Verified mechanism: PreToolUse hooks can block tool calls, hook events carry `agent_id`/`agent_type` for subagents, and plugins can ship hooks anchored on `${CLAUDE_PLUGIN_ROOT}`. Known limitation to accept up front: the dispatcher cannot know an agent's id before dispatch, so the hook enforces the **batch's combined footprint** (union of the batch's Files sets, written by delegation to a known location before dispatch), not per-agent lanes. Within a batch, disjointness remains the planner's job — which task-planning already checks against the file-modification graph. The hook also gives "implementers never modify test files" real teeth by excluding test-author's paths from the union.
