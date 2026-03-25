---
name: session-post-implementation
description: Post-implementation refinement workflow. Use after completing a major feature or plan implementation to simplify, review, sanitize, and document the code. Triggers on "/session-post-implementation" or when user says "run the iteration workflow" or "polish this implementation".
---

# Post-Implementation Refinement

Execute this sequential workflow after completing a major feature or plan implementation.

**Announce:** "Using session-post-implementation to simplify, review, sanitize, and test the implementation."

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

### Step 3: Commit (Checkpoint)

Commit the simplified and reviewed code:

```bash
git add -A && git commit -m "refactor: simplify and address review feedback"
```

This creates a checkpoint before the sanitization phase.

### Step 4: Sanitize

Run the code-sanitizer agent for final cleanup.

```
Task tool: subagent_type="code-sanitizer", max_turns=20
prompt: "Analyze recent commits for cleanup opportunities: dead code and temporary functions. Stay within ~15 tool calls. Use Grep/Glob/Read tools instead of Bash for searches."
```

Apply any recommended cleanups. This catches:
- Dead code that can be removed
- Temporary test functions left behind
- Complexity hotspots

### Step 5: Run Test Suite

Run the project's full test suite to verify all changes work correctly.

Detect and use the project's test runner:
- Check CLAUDE.md for test instructions
- Look for `scripts/run_tests.sh` or `scripts/run_tests_wsl.sh`
- Fall back to: `pytest` / `npm test` / `cargo test` / `go test` as appropriate

**If tests fail:**
1. Fix the failing tests
2. Re-run until all pass
3. Do NOT proceed to documentation until tests are green

### Step 6: Update Architecture Docs

If the project has architecture documentation (detect via `.session-flow.json` config or scan for `architecture/`, `_devdocs/architecture/`, `docs/architecture/`, `ARCHITECTURE.md`), use the `/update-architecture` skill for surgical, token-efficient documentation updates.

1. Identify which layer docs need updating based on changed files
2. Make surgical edits (update counts, signatures, entries -- not rewrites)
3. Update the architecture index if needed
4. Check doc health -- split any docs exceeding 1500 lines

Skip this step if the project has no architecture docs.

### Step 7: Generate Manual Test Plan

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

### Step 8: Final Commit

Commit the sanitization, documentation updates, and test plan:

```bash
git add -A && git commit -m "chore: sanitize code, update docs, and add manual test plan"
```

## Quick Variant

For smaller changes, use `/quick-post-implementation`:
- Steps 1-3 only (simplify, review, commit)
- Skips sanitize, test suite, doc updates, and test plan generation
- Faster iteration for minor features

## Execution Notes

- Run each step sequentially -- each depends on the previous
- If any step reveals significant issues, address them before proceeding
- The two commits create clear checkpoints: one for the refined implementation, one for cleanup/docs
- Tests run once after all code changes (Step 5) to minimize test suite execution time
- Step 7 generates a manual test plan for QA -- skip if the feature has no user-facing behavior
- If no changes are made in steps 4-7, skip the final commit

## Anti-Patterns

**Skipping the test suite:**
- BAD: Commit sanitized code without running the full test suite
- GOOD: Always run the full test suite (Step 5) before the final commit

**Committing without review:**
- BAD: Run simplifier and immediately commit without code review
- GOOD: Simplify -> Review -> Fix issues -> Commit checkpoint, then sanitize

**Running full suite between every step:**
- BAD: Run the full test suite after simplify, again after review, again after sanitize
- GOOD: Run individual tests during steps 1-4, full suite once at Step 5

## Workflow Integration

This skill is part of the session workflow chain:

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
  (bootstrap)       (research & design)             (break into tasks)          (execute tasks)           (this skill)                       (package & ship)
```
