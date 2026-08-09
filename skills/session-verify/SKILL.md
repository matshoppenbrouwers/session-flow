---
name: session-verify
description: Evidence-based verification workflow for completed features and plans. Produces a falsifiable proof artifact that implementation matches design spec, identifying defects, stubs, and spec-vs-reality gaps. Triggers on "/session-verify" or when user says "verify this feature", "prove this works", "run verification", or "confirm the implementation".
---

# Session Verify

Produce evidence-based proof that a completed implementation matches its design and plan, or a falsification artifact identifying gaps. This is a heavy skill — expect hours, not minutes.

**Announce:** "Using session-verify to produce evidence-based verification of the implementation."

## Core Principle

**Never assume. Always cite.** Every claim in the output must cite a file path + line number, command output, test name, or log excerpt. Statements like "should work", "appears correct", or "likely functions as intended" are forbidden.

The skill treats absence of evidence as failure, not as "probably fine". It runs tests, writes probes, inspects real state, and produces a structured evidence artifact. Fixing defects is out of scope — document them, don't patch.

## Non-Negotiables

1. **Evidence-first.** Run the probe before writing the verdict. No conclusion without cited evidence.
2. **Falsify, don't confirm.** For every spec claim, design a test intended to disprove it. A claim only survives if the falsification attempt fails.
3. **Run the code.** Passing unit tests are necessary but insufficient. Execute real flows, inspect real state, validate real round-trips.
4. **Never edit source to make tests pass.** New verification scripts belong under `_verification/` (or `verification/` if the project prefers). Do not modify production code or existing tests to paper over defects.
5. **Report defects, don't silently fix.** Document each defect with a failing probe or reproducible trace. Escalate to the user; do not patch without explicit authorization.
6. **Cite on every line.** Format: `path/to/file:LINE` for code, `$ command` + output for execution, `MEMORY #id` for memory citations.

## Workflow

### Step 1: Scope

Collect verification inputs through a **brief collaborative dialogue**. Ask one question at a time. Prefer multiple choice.

Required inputs:

- **Design doc path** — the spec this implementation targets (the implementation plan produced by `/session-research-design` *is* the design doc). Look in `.session-flow.json.paths.plans` first, then `.paths.research`; otherwise scan `plans/`, `_devdocs/plans/`, `docs/plans/`. If none exists, offer: (a) run `/session-research-design` first, or (b) proceed in **code-as-spec** mode (verify against recent commits + architecture docs + CHANGELOG).
- **Implementation plan path** — the `YYYY-MM-DD-{topic}-implementation.md` that was executed. Same auto-detection from `.session-flow.json.paths.plans`.
- **Scope label** — kebab-case, used for artifact naming (e.g. `banner-redesign`, `hybrid-search`).
- **Memory source (optional)** — claude-mem MCP, session transcripts, or PR list that captures implementation history and any flagged defects.
- **Verification ambition** — multiple choice: (A) structural-only, (B) structural + functional, (C) exhaustive (structural + functional + integration + spec-vs-reality gap). Default C unless the user picks otherwise.

Confirm these inputs before proceeding. Do not guess.

### Step 2: Scope Matrix

Produce and confirm with the user a 6-row matrix that defines what "working" means for this verification. Present as a table. Adjust rows to match ambition chosen in Step 1.

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

1. The design doc (or the "code-as-spec" sources if no design doc exists)
2. The implementation plan
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
- Top 3 risks (1 line each)
- Path to the artifact
- Any defects that require user decision (ship / fix / defer)

Do not recommend fixes unless the user asks.

## Evidence Artifact Contract

The artifact at `_verification/{date}-{label}-verification.md` must use exactly these H2 sections, in order:

```markdown
# {Label} Verification Report

**Verifier:** {model or agent id}
**Date:** YYYY-MM-DD
**Scope:** Commits {sha_first}..{sha_last} on branch {branch}
**Verdict:** PASS | PASS-WITH-CAVEATS | FAIL

## Executive Summary
<=150 words. Headline finding + top 3 risks.

## Hypotheses and Results
| # | Hypothesis | Predicted | Observed | Evidence | Status |

## Scope Matrix Status
Row 1..6 from Step 2 with PASS/FAIL/N/A + one-line justification.

## Structural Audit
Inventory table from Step 4.

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
7. No source file outside `_verification/` has been modified.

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

**Claiming green without evidence:**
- BAD: "The test suite passes — I confirmed this is working."
- GOOD: "`$ pytest tests/ -v` returned `143 passed in 12.4s`. Log at `_verification/2026-04-18-x-tests.log`."

**Spot-checking instead of exhaustive coverage:**
- BAD: Verify 3 of 11 event types exist; assume the other 8 do.
- GOOD: Inventory all 11 in a table with file:line citations.

**Skipping phases:**
- BAD: Skip defect probes because "the tests passed anyway".
- GOOD: Run every probe — the whole point is that passing tests are not the same as correct behavior.

**Treating compilation as correctness:**
- BAD: "TypeScript compiles clean — the UI wiring is correct."
- GOOD: "TS compiles. The component is mounted at `CaptureFooter.tsx:42` per grep. Runtime path verified by {probe}."

**Rewriting the plan to match broken code:**
- BAD: Discover a missing feature; quietly update the plan to say it was out of scope.
- GOOD: Report it as NOT-IMPLEMENTED in the Spec-vs-Reality Gap section.

**Fixing defects silently:**
- BAD: Find a bug, edit the code, report the feature as passing.
- GOOD: Report the bug as a finding with a failing probe; ask the user how to proceed.

**Hand-waving environment limits:**
- BAD: "I couldn't run the integration tests in my environment."
- GOOD: "Integration tests require Windows + Tauri (not available in WSL). User must run `pnpm tauri dev` on Windows and execute checklist §9.3."

## Workflow Integration

This skill sits between post-implementation polish and release:

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-verify  -->  /session-release
  (bootstrap)       (research & design)             (break into tasks)          (execute tasks)           (simplify, review, test)          (this skill)           (package & ship)
```

- `/session-post-implementation` can optionally suggest this skill in its Step 7.5 for feature/plan completions.
- `/session-release` pre-flight checks for a PASS verification artifact when shipping a feature that had a design doc.
- Standalone: invoke directly when auditing a completed but un-verified implementation, or when prior code review flagged significant defects that need independent confirmation.

Not appropriate to run for every session — use it when the cost of shipping broken code is high.
