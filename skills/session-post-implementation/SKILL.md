---
name: session-post-implementation
description: Post-implementation refinement workflow. Use after completing a major feature or plan implementation to simplify, review, sanitize, and document the code. Triggers on "/session-post-implementation" or when user says "run the iteration workflow" or "polish this implementation".
---

# Post-Implementation Refinement

Execute this sequential workflow after completing a major feature or plan implementation.

**Announce:** "Using session-post-implementation to simplify, review, sanitize, and test the implementation."

## Workflow Configuration

Before starting, use **AskUserQuestion** to let the user configure the workflow. Present both questions together at the start (not between steps).

**Question 1: Pipeline scope**

Use AskUserQuestion:
- question: "How thorough should post-implementation be?"
- header: "Scope"
- multiSelect: false
- options:
  - A) label: "Full pipeline (Recommended)", description: "All steps: simplify, review, security & liability audit, sanitize, test suite, architecture docs, and manual test plan. Best after completing a major feature."
  - B) label: "Standard", description: "Simplify, review, sanitize, test suite, and commit. Skips security audit, architecture docs, and manual test plan."
  - C) label: "Quick", description: "Simplify, review, and commit only. Fastest option for minor changes."

**Scope reference:**

| Step | Full | Standard | Quick |
|------|------|----------|-------|
| 1. Simplify | yes | yes | yes |
| 2. Review | yes | yes | yes |
| 3. Security & Liability Audit | yes | - | - |
| 4. Commit checkpoint | yes | yes | yes |
| 5. Sanitize | yes | yes | - |
| 6. Test suite | yes | yes | - |
| 7. Architecture docs | yes | - | - |
| 8. Manual test plan | yes | - | - |
| 9. Final commit | yes | yes | - |

Verification (`/session-verify`) is always optional — offered after Step 8 on Full completions only; see Step 8.5 below.

**Question 2: Add-ons** (only ask if user chose Standard or Quick)

Show the steps NOT included in their chosen scope as add-on options.

Use AskUserQuestion:
- question: "Want to add any extra steps?"
- header: "Add-ons"
- multiSelect: true
- options (pick from the table above — only show steps marked "-" for the chosen scope, max 4):
  - If **Standard**: "Security & Liability Audit", "Architecture docs", "Manual test plan"
  - If **Quick**: "Security & Liability Audit", "Test suite", "Architecture docs", "Manual test plan"

The user can select multiple, or choose "Other" and type "none" to proceed without extras.

**Question 3: Security audit mode** (only ask if security audit is included — via Full pipeline or as an add-on)

Use AskUserQuestion:
- question: "How should the security & liability audit run?"
- header: "Audit mode"
- multiSelect: false
- options:
  - A) label: "Sub-agent (Recommended)", description: "Dispatch as a subagent (inherits the parent session's model). Faster and cheaper. Good for routine changes."
  - B) label: "Inline", description: "Run in the main conversation using your current model. More thorough. Better for security-sensitive or high-risk changes."

Store the user's choices and apply them throughout the workflow. Merge the base scope with any selected add-ons to determine which steps to run.

## Workflow Steps

### Step 1: Simplify

Run the code-simplifier agent to elegantly simplify the implementation without losing functionality.

Try dispatching code-simplifier in this order:
1. Marketplace plugin: `subagent_type="code-simplifier:code-simplifier"` (if installed)
2. Bundled agent: `subagent_type="code-simplifier"` (from session-flow package)

If neither is available, skip this step and proceed to Step 2.

```
Task tool: subagent_type=[resolved from above]
prompt: "Simplify and refine the recently modified code for clarity, consistency, and maintainability while preserving all functionality. Do not run the full test suite at this stage (but you can run individual tests)"
```

Wait for completion. Review the changes made.

### Step 2: Review

Run the code-reviewer agent to identify issues.

```
Task tool: subagent_type="code-reviewer"
prompt: "Review the recent code changes for bugs, logic errors, security vulnerabilities, and code quality issues. Do not run the full test suite at this stage"
```

If issues are found:
1. Present findings to the user
2. Fix each identified issue
3. Re-run the code-reviewer to verify fixes

Loop until the reviewer passes with no significant issues, but do not yet run the full test suite at this stage (you can run individual tests)

### Step 3: Security & Liability Audit

**Skip if:** user chose Standard or Quick scope in workflow configuration.

**Resolve the reference paths first (both modes).** The subagent starts in the project CWD and cannot resolve paths relative to the plugin, so *this* skill resolves them and passes absolute paths:

- Use `${CLAUDE_PLUGIN_ROOT}` when it is set — the references are at `${CLAUDE_PLUGIN_ROOT}/skills/security-liability-audit/references/`.
- Otherwise derive the plugin root from this file's own absolute path (`.../skills/session-post-implementation/SKILL.md` → two levels up), or locate the installed plugin (e.g. `~/.claude/plugins/**/session-flow/`).
- If neither resolves, say so and continue in degraded mode: the auditor works from its own built-in checklist summaries.

**Mode A — Sub-agent (default):**

```
Task tool: subagent_type="security-auditor"
prompt: "Audit the recent code changes for technical security vulnerabilities and legal/liability risk. Produce findings and recommendations only — do not modify code.
Reference files (absolute paths, read them for detailed patterns):
- <RESOLVED_PLUGIN_ROOT>/skills/security-liability-audit/references/technical-security.md
- <RESOLVED_PLUGIN_ROOT>/skills/security-liability-audit/references/legal-liability.md
If a path is missing or unreadable, proceed with your built-in checklist summaries and say so in your report."
```

Substitute the resolved absolute paths into the prompt — never dispatch the placeholder or a repo-relative path.

**Mode B — Inline:**

Read the reference files directly and perform the audit in the main conversation, using the same resolved absolute root:
1. Read `<RESOLVED_PLUGIN_ROOT>/skills/security-liability-audit/references/technical-security.md`
2. Read `<RESOLVED_PLUGIN_ROOT>/skills/security-liability-audit/references/legal-liability.md`
3. Apply Part A (technical) and Part B (liability) checks from `<RESOLVED_PLUGIN_ROOT>/skills/security-liability-audit/SKILL.md`
4. Report findings using the same output format

**After audit (either mode):**

If findings are reported:
1. Present findings to the user
2. **Technical CRITICAL/HIGH**: fix before proceeding
3. **Legal/Liability HIGH**: note for follow-up (may require ToS/privacy policy updates, not code fixes)
4. **MEDIUM and below**: track, proceed

### Step 4: Commit (Checkpoint)

Commit the simplified and reviewed code:

```bash
git add -A && git commit -m "refactor: simplify and address review feedback"
```

This creates a checkpoint before the sanitization phase.

### Step 5: Sanitize

Run the code-sanitizer agent for final cleanup.

```
Task tool: subagent_type="code-sanitizer", max_turns=20
prompt: "Analyze recent commits for cleanup opportunities: dead code and temporary functions. Stay within ~15 tool calls. Use Grep/Glob/Read tools instead of Bash for searches."
```

Apply any recommended cleanups. This catches:
- Dead code that can be removed
- Temporary test functions left behind
- Complexity hotspots

### Step 6: Run Test Suite

Run the project's full test suite to verify all changes work correctly.

Detect and use the project's test runner:
- Check CLAUDE.md for test instructions
- Look for `scripts/run_tests.sh` or `scripts/run_tests_wsl.sh`
- Fall back to: `pytest` / `npm test` / `cargo test` / `go test` as appropriate

**If tests fail:**
1. Fix the failing tests
2. Re-run until all pass
3. Do NOT proceed to documentation until tests are green

**Phase exit criterion:** full test suite returns zero failures. The exact command + pass/fail counts must be captured in the final commit message or a note to the user. "Tests probably pass" is not acceptable — show the output.

### Step 7: Update Architecture Docs

If the project has architecture documentation (detect via `.session-flow.json` config or scan for `architecture/`, `_devdocs/architecture/`, `docs/architecture/`, `ARCHITECTURE.md`), use the `/update-architecture` skill for surgical, token-efficient documentation updates.

1. Identify which layer docs need updating based on changed files
2. Make surgical edits (update counts, signatures, entries -- not rewrites)
3. Update the architecture index if needed
4. Check doc health -- split any docs exceeding 1500 lines

Skip this step if the project has no architecture docs.

### Step 8: Generate Manual Test Plan

Generate a manual test plan for the feature that was just implemented.

1. Analyze the feature from recent commits and changed files
2. Determine a short kebab-case feature label (e.g. `banner`, `mcp`, `credentials`)
3. Save to the project's testing directory (from `.session-flow.json` or detect `testing/`, `_devdocs/testing/`, `docs/testing/`)
4. Populate sections with test cases covering the feature's user-facing behavior

**Template:**

```markdown
# {Feature Name} Manual Test Plan

**Date:** YYYY-MM-DD
**Branch:** `{branch}`
**Tester:** _______________

---

## How to Use

1. Build and run the app using the project's standard build/run commands
2. Work through each test in order -- some tests create data used by later tests
3. Mark each test: `[PASS]`, `[FAIL]`, or `[SKIP]` with notes
4. The "Verdict" section at the bottom summarizes overall status

---

## N. {Area}

### N.1 {Test case}
- [ ] Step 1
- [ ] Step 2

**Result:** `[ ]` PASS / FAIL
**Notes:** _______________

---

## Debugging Quick Reference

{Include relevant log locations, commands, or dev tools tips if applicable}

---

## Verdict

| Area | Tests | Pass | Fail | Skip |
|------|-------|------|------|------|
| 1. {Area} | N | | | |
| **Total** | **N** | | | |

**Overall Verdict:** `[ ]` READY FOR RELEASE / NEEDS FIXES

**Blocking Issues:**
1. _______________

**Non-blocking Issues:**
1. _______________

**Tester Sign-off:** _______________ Date: _______________
```

Skip this step if the implementation is purely internal (no user-facing behavior to test).

### Step 8.5: Verification (optional, for feature/plan completions)

If this session closed out an implementation plan (not just a bugfix or small change), consider running `/session-verify` before the final commit. Verification produces an evidence artifact proving the implementation matches the design doc and plan via falsifiable hypotheses, structural audit, defect probes, and integration probes.

**Run when:**
- A `/session-research-design` plan was implemented
- A multi-task `/session-task-planning` was completed
- Behaviour is user-visible and risk-prone
- Prior code review flagged critical or high-severity defects that should be independently confirmed fixed

**Skip when:**
- Bugfixes, refactors, single-file features
- Internal polish with no design doc
- Small changes where the test suite in Step 6 is sufficient evidence

Do not run automatically. Present the option to the user; proceed to Step 9 if they decline.

### Step 9: Final Commit

Commit the sanitization, documentation updates, and test plan:

```bash
git add -A && git commit -m "chore: sanitize code, update docs, and add manual test plan"
```

## Quick Variant

For smaller changes, use `/quick-post-implementation` (equivalent to choosing "Quick" scope):
- Steps 1, 2, 4 only (simplify, review, commit)
- Skips security audit, sanitize, test suite, doc updates, and test plan generation
- Faster iteration for minor features
- Skips the workflow configuration questions entirely

## Execution Notes

- Run each step sequentially -- each depends on the previous
- If any step reveals significant issues, address them before proceeding
- The two commits create clear checkpoints: one for the refined implementation, one for cleanup/docs
- Tests run once after all code changes (Step 6) to minimize test suite execution time
- Step 3 (security audit) can be skipped for trivial changes (typos, docs-only)
- Step 8 generates a manual test plan for QA -- skip if the feature has no user-facing behavior
- Step 8.5 (verification) is always optional -- present but do not auto-run
- If no changes are made in steps 5-8, skip the final commit

## Anti-Patterns

**Running full suite between every step:**
- BAD: Run the full test suite after simplify, again after review, again after sanitize
- GOOD: Run individual tests during the simplify/review/audit/sanitize steps, full suite once at the test-suite step

Chain context: see `references/workflow-overview.md`.
