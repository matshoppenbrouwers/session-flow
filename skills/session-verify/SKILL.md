---
name: session-verify
description: Evidence-based verification workflow for completed features and plans. Produces a falsifiable proof artifact that implementation matches design spec, identifying defects, stubs, and spec-vs-reality gaps. Triggers on "/session-verify" or when user says "verify this feature", "prove this works", "run verification", or "confirm the implementation".
---

# Session Verify

Produce evidence-based proof that a completed implementation matches its design and plan, or a falsification artifact identifying gaps. This is a heavy skill — expect hours, not minutes.

Open with one sentence saying what you are about to do and what it will produce.

## Core Principle

**Never assume. Always cite.** Every claim in the output must cite a file path + line number, command output, test name, or log excerpt. Statements like "should work", "appears correct", or "likely functions as intended" are forbidden.

The skill treats absence of evidence as failure, not as "probably fine". It runs tests, writes probes, inspects real state, and produces a structured evidence artifact. Fixing defects is out of scope — document them, don't patch.

## Non-Negotiables

1. **Verify the accepted outcome, not the newest document.** The behaviour under verification is the work item's accepted scope, identified by its acceptance fingerprint and by the work-root commit of each document that scope references. A plan file that happens to be newest is not the specification.
2. **Evidence-first.** Run the probe before writing the verdict. No conclusion without cited evidence.
3. **Falsify, don't confirm.** For every spec claim, design a test intended to disprove it. A claim only survives if the falsification attempt fails.
4. **Run the code.** Passing unit tests are necessary but insufficient. Execute real flows, inspect real state, validate real round-trips.
5. **Never edit source to make tests pass.** New verification scripts belong under `_verification/` (or `verification/` if the project prefers). Do not modify production code or existing tests to paper over defects.
6. **Report defects, don't silently fix.** Document each defect with a failing probe or reproducible trace. Escalate to the user; do not patch without explicit authorization.
7. **Every task passing is not a delivered outcome.** Tasks can pass while the parent still needs integration or delivery. Completion is judged in *Completion and Evidence* below, against the accepted outcome, and never inferred from task results.
8. **Cite on every line.** Format: `path/to/file:LINE` for code, `$ command` + output for execution, `MEMORY #id` for memory citations.

## Workflow

### Step 0: Resolve the Runtime and the Accepted Outcome

Resolve the helper by the one rule for this host (`references/runtime-integration.md`) and confirm it answers with `doctor`. Then read the work item under verification:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-042
```

Take from the record:

- **The accepted scope region** — the behaviour being verified, and the text the acceptance fingerprint covers.
- **`acceptance.fingerprint` against the record's current `scope_fingerprint`** — when they differ, the accepted scope was edited after acceptance. Stop and report it: verifying against text nobody accepted proves nothing. Re-acceptance or a recorded same-meaning decision comes first.
- **`references`** — each behaviour or criteria document as `path@commit`. Read each one **at that work-root commit**, not at whatever the file says today:

  ```bash
  git -C "$WORK_ROOT" show <commit>:<path>
  ```

- **`delivery`** — the delivery target the accepted outcome requires, if any.
- **`tasks/`** — each task's `result` and `lifecycle`, which are inputs to the verdict and not the verdict.

When the item has no accepted scope, or there is no work item at all, say so and stop: capture and acceptance come first, through `/session-add-task` or `/session-gatekeeper`. There is nothing here to verify against.

**Which artifact prevails.** The accepted scope region is the specification. `spec.md` elaborates the behaviour it references and is read at the referenced commit; `plan.md` carries approach and order and never supplies acceptance criteria. When `spec.md` and `plan.md` disagree, the accepted scope decides, and the disagreement is itself a finding.

### Step 1: Scope

Collect the remaining inputs through a **brief collaborative dialogue**. Ask one question at a time. Prefer multiple choice.

Required inputs:

- **Work item identity** — `SEQ-NNN`, resolved in Step 0. Everything else hangs off it.
- **Scope label** — kebab-case, used for artifact naming (e.g. `banner-redesign`, `hybrid-search`).
- **Memory source (optional)** — claude-mem MCP, session transcripts, or PR list that captures implementation history and any flagged defects.
- **Verification ambition** — multiple choice: (A) structural-only, (B) structural + functional, (C) exhaustive (structural + functional + integration + spec-vs-reality gap). Default C unless the user picks otherwise.

Confirm these inputs before proceeding. Do not guess.

### Step 2: Scope Matrix

Produce and confirm with the user a 6-row matrix that defines what "working" means for this verification. Present as a table. Adjust rows to match the ambition chosen in the Scope step.

| Row | Dimension | What must be true |
|-----|-----------|-------------------|
| 1 | **Structural** | Every module, class, and symbol in the plan exists with the documented signature |
| 2 | **Functional** | The full test suite passes; claimed test counts are present; migrations apply cleanly |
| 3 | **Defect regression** | Every defect flagged in prior reviews or memories is verified fixed — not claimed fixed |
| 4 | **Integration** | End-to-end flows (IPC, RPC, UI↔backend) complete without silent failures |
| 5 | **Frontend / UX** | New UI surface compiles, lints, and is actually reachable (not dead code) |
| 6 | **Spec-vs-reality gap** | Every spec feature is classified: IMPLEMENTED / PARTIAL / STUB / NOT-IMPLEMENTED |

The matrix is a contract. You cannot change it mid-verification. If a row does not apply (e.g. backend-only change), mark it `N/A` with a one-line justification.

### Step 3: Required Reading

Before running anything, read:

1. The accepted scope region and each referenced document at its recorded commit (Step 0)
2. The item's `plan.md` and task records, for what was attempted and in which order
3. The project's architecture index if present (`architecture_index.md`, `ARCHITECTURE.md`, or equivalent per `.session-flow.json.paths.architecture`)
4. The project's `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` for conventions
5. Any testing guide (`TESTING.md`, `_devdocs/guides/TESTING.md`) — **note if it is stale**; outdated testing docs are themselves a finding
6. If memory source provided: query for relevant observations and extract any pre-flagged defects

Produce a written **hypothesis list** — one falsifiable hypothesis per non-trivial claim in the plan. Example: *"H1: The SQL wildcard injection flagged in review is still present because commit X did not touch history.py."* Hypotheses should be specific enough that you can design a single probe to kill each.

**Phase exit criterion**: hypothesis list exists, written down, shared with the user.

### Step 4: Structural Audit

Walk the claimed module surface with `Grep` and `Read`. For each claimed symbol, confirm it exists with the documented signature. Build an inventory table:

```
| Claimed symbol | File:line | Signature matches? | Notes |
|----------------|-----------|--------------------|-------|
```

**Phase exit criterion**: every symbol in the plan has a verdict row. No "I think it's there" entries.

### Step 5: Functional Test Execution

Detect the project's test runner:
- Check `CLAUDE.md` / `AGENTS.md` for test instructions
- Look for `scripts/run_tests.sh`, `scripts/run_tests_wsl.sh`, `Makefile` targets
- Fall back to: `pytest` / `npm test` / `cargo test` / `go test` / `mvn test` as appropriate

Run:

1. The full suite, with output captured to `_verification/{date}-{label}-tests.log`
2. Narrower runs targeting the new modules/packages (list them explicitly)
3. Test-count verification: if the plan claims N tests, run the collector and assert the count. If the delta is non-zero, report it as a finding.
4. Migration replay (if applicable): run any new migration against both a fresh database and a database with prior migrations. Confirm idempotency.

If a test fails, **do not fix it**. Record the failure, its symptom, and your root-cause hypothesis. Fixing is the user's call, not yours.

**Environment reality**: If the project has a WSL/Windows or Linux/macOS split, and a test cannot run in your current environment, mark it `DEFERRED-TO-{target}` and prepare an executable command for the user to run themselves. Do not silently skip.

**Phase exit criterion**: test log captured, test-count delta reported, all failures enumerated with root-cause hypotheses.

### Step 6: Defect Regression Probes

For each defect flagged in prior reviews (from memory source, PR comments, or the plan itself), write a **targeted probe** — a short script or pytest test under `_verification/probes/` that would fail if the defect were present.

Each probe has exactly one job: falsify one fix claim. Keep probes small (<40 lines each). Run each probe. Record:

- `VERIFIED-FIXED` — probe runs green, defect is provably absent
- `CLAIMED-BUT-NOT-VERIFIED` — fix exists in code but probe cannot reach the relevant path (explain why)
- `NOT-FIXED` — probe reproduces the defect
- `REGRESSED` — fix existed and has been removed or bypassed

**Phase exit criterion**: one probe per flagged defect, all executed, all classified.

### Step 7: Integration Probes

Live end-to-end checks. Examples (adapt to the project):

- **RPC round-trip**: spawn the sidecar/server, issue a real RPC call, assert the response shape
- **Error paths**: call with invalid input, verify well-formed errors (not crashes or silent success)
- **Data persistence**: write → read → verify round-trip through the real storage backend
- **Cross-component flow**: emit an event from one module, confirm it lands in the subscriber
- **Idempotency**: run migrations/initializers twice, verify no duplicate rows or errors
- **Frontend compile**: `tsc --noEmit`, ESLint, `pnpm build` (or project equivalent) on new files only
- **Frontend reachability**: grep for the new component's mount site; if none, it is dead code → finding

Probes live under `_verification/probes/`. Each probe captures stdout/stderr and writes a one-line summary to `_verification/{date}-{label}-integration.log`.

**Phase exit criterion**: at least one integration probe executed, or each skipped probe has a cited reason + a user-executable alternative.

### Step 8: Spec-vs-Reality Gap

For every feature in the design spec, classify:
- `IMPLEMENTED` — present and verified in prior phases
- `PARTIAL` — some sub-features work, others don't; list exactly which
- `STUB` — code exists but does nothing meaningful (e.g. `pass`, `return None`, raises `NotImplementedError`)
- `NOT-IMPLEMENTED` — no code for it

If the plan has a "Not covered in this plan" or "Out of scope" section, do **not** flag those as missing. Verify they are genuinely not half-done.

**Phase exit criterion**: every spec feature has a status + citation.

### Step 9: Write Evidence Artifact

Write the final report to `_verification/{date}-{label}-verification.md`, following the structured output contract below. Fixed sections, fixed headings. No substitutions.

### Step 10: Present Verdict

Summarize to the user with:
- Overall verdict: `PASS` | `PASS-WITH-CAVEATS` | `FAIL`
- The completion decision from *Completion and Evidence*, stated separately from the verdict
- Top 3 risks (1 line each)
- Path to the artifact
- Any defects that require user decision (ship / fix / defer)

Do not recommend fixes unless the user asks.

## Completion and Evidence

A verdict is a judgement about probes. Completion is a lifecycle transition on the work item, and it
is allowed only when applicable evidence covers the **accepted outcome** — not when the probes were
green, and not when every task passed.

### Record the evidence

Each check that survived falsification becomes one evidence entry on the record, named against the
fingerprint it was gathered at:

```json
{"expected_revision": 7,
 "metadata": {"evidence": [
   {"criteria": "<the accepted criterion this covers>",
    "fingerprint": "<the record's current scope_fingerprint>",
    "revision": "<code or artifact revision the check ran against>",
    "environment": "<where it ran>", "result": "pass | fail",
    "limitations": ["<what this check does not cover>"]}]}}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" revise --seq SEQ-042 --input "$PAYLOAD"
```

The response reports each entry's `applies`. An entry that does not apply is not evidence about this
outcome, whatever its `result` says. Append entries — never overwrite the ones already recorded.

### The completion gate

Re-resolve the acceptance and its authority immediately before this decision, and check every row
before calling for a transition. The runtime records a transition; it does not judge whether the
evidence covers the accepted outcome. That judgement is this step's, which is why the gate is
checked first.

| Completion is refused when | Named error | What to do |
|----------------------------|-------------|------------|
| The accepted scope names a required delivery target that is not delivered — however many tasks passed | `inapplicable-evidence` | Leave the item `active`, name the target and what is missing, and say which authority the delivery needs. Merging is a separate action from implementing |
| Stale evidence: an entry names a fingerprint the record no longer carries | `inapplicable-evidence` | Re-run that check against the current fingerprint, or record a same-meaning decision if the edit changed no meaning. A stored verdict is evidence about the revision it was recorded against |
| A task result is `unknown` or `blocked`, or a required check could not run | `inapplicable-evidence` | Report the unknown as unknown. An outcome nobody observed is not evidence, and defaulting it to a pass is how a run becomes untruthful |
| Acceptance no longer names the record's current scope fingerprint | `missing-authority` | Stop. Re-acceptance or a recorded same-meaning decision comes before any completion |
| A closure is reopened without a correction record | `missing-authority` | Supply the correction naming why the closure was premature — see below |

When every row passes, transition the item:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" revise --seq SEQ-042 --input "$PAYLOAD"
```

with `{"metadata": {"lifecycle": "done"}, "expected_revision": <current>, "actor": "<claim holder>"}`.
The acting identity must hold the claim; take or reassign the claim before changing lifecycle.
`revise` also refuses an illegal transition and, for a reopening, refuses without a correction.
Use `transition` instead when one operation must change several records together.

### Reopening and successor work

- **Premature closure**: reopen under the **same identity**. Send `{"expected_revision": <current>, "actor": "<claim holder>",
  "metadata": {"lifecycle": "active"}, "correction": {"reason": "<why the closure was premature>",
  "actor": "<who decided>"}}`. The correction appends to the record's `corrections`; nothing already
  recorded is rewritten.
- **An incident after valid delivery**: capture linked successor work under a new `SEQ`, referencing
  the delivered item. Do not reopen a delivered outcome to hold new work — the delivery happened, and
  the record has to keep saying so.

## Evidence Artifact Contract

The artifact at `_verification/{date}-{label}-verification.md` must use exactly these H2 sections, in order:

```markdown
# {Label} Verification Report

**Verifier:** {model or agent id}
**Date:** YYYY-MM-DD
**Work item:** {SEQ-NNN} — accepted fingerprint {scope_fingerprint}
**Scope:** Commits {sha_first}..{sha_last} on branch {branch}
**Verdict:** PASS | PASS-WITH-CAVEATS | FAIL
**Completion:** done | not yet — {the gate row that refused it}

## Executive Summary
<=150 words. Headline finding + top 3 risks.

## Hypotheses and Results
| # | Hypothesis | Predicted | Observed | Evidence | Status |

## Scope Matrix Status
Row 1..6 from the Scope Matrix with PASS/FAIL/N/A + one-line justification.

## Structural Audit
Inventory table from the Structural Audit.

## Test Results
- Full suite: pass/fail counts, duration, command
- Targeted subsets: same
- Test-count delta (if applicable)
- Migration replay (if applicable)

## Defect Probe Results
For each prior-flagged defect: status + probe location + raw output excerpt.

## Integration Probe Results
Per-probe: command, outcome, evidence.

## Spec-vs-Reality Gap
Feature -> status -> citation.

## Findings Ledger
### Critical (blocks ship)
### High (must fix before next release)
### Medium (fix when convenient)
### Low / Informational
Each finding: unique ID (`V-001`...), title, evidence, reproduction command, suggested remediation (one sentence).

## Out-of-Scope / Explicitly Deferred
Features the plan marked as future phases and that you confirmed are not half-implemented.

## Cross-Environment Smoke-Test Checklist (if applicable)
Executable commands for environments you couldn't reach (e.g. Windows-only, production-only).

## Documentation Drift
Places where architecture docs, testing guides, or the index are stale. List only — do not fix.

## Appendix A — Commands Executed
Full command transcript with one-line results. Enables reproducibility.

## Appendix B — Probe Source
Paths to all verification probes added under `_verification/probes/`.
```

## Definition of Done

You are done when **all** are true:

1. Artifact at `_verification/{date}-{label}-verification.md` exists and follows the contract exactly.
2. Every row in the Hypotheses table has PASS or FAIL with cited evidence.
3. All defect probes have been run; raw output is captured in Appendix A.
4. The full test suite has been executed at least once with complete output preserved.
5. At least one integration probe has executed, **or** each skipped probe has a cited reason and a user-executable alternative.
6. The verdict line is one of the three allowed values and is consistent with the Findings Ledger (a FAIL ledger with PASS verdict is not allowed).
7. Each surviving check is recorded as an evidence entry against the current fingerprint, and the response confirms it applies.
8. The completion line states the decision and, when completion was refused, which gate row refused it.
9. No source file outside `_verification/` has been modified, and no record outside the item under verification.

## Performance Budget

This is a heavy skill. Expected cost: hours, not minutes. Not appropriate for:

- Bug fixes (just run the tests)
- Single-file refactors
- Small features with no design doc
- Internal polish without user-facing behavior

Appropriate for:

- Plans completed via `/session-research-design` → `/session-task-planning` → `/session-delegation`
- Pre-release gates where ship blockers must be caught
- Large refactors touching multiple architecture layers
- Features where prior code review flagged critical or high defects

## Anti-Patterns

**Spot-checking instead of exhaustive coverage:**
- BAD: Verify 3 of 11 event types exist; assume the other 8 do.
- GOOD: Inventory all 11 in a table with file:line citations.

**Treating compilation as correctness:**
- BAD: "TypeScript compiles clean — the UI wiring is correct."
- GOOD: "TS compiles. The component is mounted at `CaptureFooter.tsx:42` per grep. Runtime path verified by {probe}."

**Reading a task board as a delivered outcome:**
- BAD: "All six tasks are `passed`, so the item is done."
- GOOD: "All six tasks are `passed`. The accepted scope requires a merged pull request; PR #58 is open, so the item stays `active`."

**Rewriting the plan to match broken code:**
- BAD: Discover a missing feature; quietly update the plan to say it was out of scope.
- GOOD: Report it as NOT-IMPLEMENTED in the Spec-vs-Reality Gap section.

**Hand-waving environment limits:**
- BAD: "I couldn't run the integration tests in my environment."
- GOOD: "Integration tests require Windows + Tauri (not available in WSL). User must run `pnpm tauri dev` on Windows and execute checklist §9.3."

Chain context: see `references/workflow-overview.md`.
