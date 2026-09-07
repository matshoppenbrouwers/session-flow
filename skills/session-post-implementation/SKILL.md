---
name: session-post-implementation
description: Post-implementation refinement workflow. Use after completing a major feature or plan implementation to simplify, review, and document the code. Triggers on "/session-post-implementation" or when user says "run the iteration workflow" or "polish this implementation".
---

# Post-Implementation Refinement

Execute this sequential workflow after completing a major feature or plan implementation.

Open with one sentence saying what you are about to do and what it will produce.

## Workflow Configuration

Before starting, use **AskUserQuestion** to let the user configure the workflow. Present both questions together at the start (not between steps).

**Question 1: Pipeline scope**

Use AskUserQuestion:
- question: "How thorough should post-implementation be?"
- header: "Scope"
- multiSelect: false
- options:
  - A) label: "Full pipeline (Recommended)", description: "All steps: simplify, review, security & liability audit, test suite, architecture docs, and manual test plan. Best after completing a major feature."
  - B) label: "Standard", description: "Simplify, review, test suite, and commit. Skips security audit, architecture docs, and manual test plan."
  - C) label: "Quick", description: "Simplify, review, and commit only. Fastest option for minor changes."

**Preset seed:** the chosen preset seeds the step set; it is not consulted again once the set is
resolved.

| Step | Full | Standard | Quick |
|------|------|----------|-------|
| 1. Simplify | yes | yes | yes |
| 2. Review | yes | yes | yes |
| 3. Security & Liability Audit | yes | - | - |
| 4. Commit checkpoint | yes | yes | yes |
| 5. Test suite | yes | yes | - |
| 6. Architecture docs | yes | - | - |
| 7. Manual test plan | yes | - | - |
| 8. Final commit | yes | yes | - |

Verification (`/session-verify`) is never part of the step set. Step 7.5 offers it on its own
criteria.

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

**Resolve the step set now.** Take the step numbers marked "yes" in the preset's column, add every
step the user selected as an add-on, and write the result out as one explicit list, for example
`resolved steps: 1, 2, 3, 4`. Show that list to the user before Step 1.

The resolved set is the only thing later steps consult. Do not re-read the preset name after this
point, and do not drop a selected add-on because the preset excluded it — a selected audit runs
under Quick exactly as it does under Full. Also carry the audit mode from Question 3 when Step 3 is
in the set.

## Ownership Snapshot

Take this snapshot before Step 1, whatever the scope was configured to be. Both commits stage from
it, and nothing outside it may enter them.

1. Record the worktree as it stands:

```bash
git status --porcelain=v1 --untracked-files=all
git diff --cached --name-only
```

2. Split every path the snapshot reports into two lists and show both to the user:
   - **In scope** — the implementation this run refines.
   - **Unrelated** — everything else: files the user was editing, files they had already staged,
     untracked scratch files.

   When a path's side is not obvious from this session's own work, ask with **AskUserQuestion**
   instead of guessing. A path stays unrelated until the user says it is in scope.

3. If any unrelated path appears in `git diff --cached --name-only`, stop here. Name those paths and
   ask the user to commit or unstage them before the run continues — a flow commit taken while
   unrelated content sits in the index carries that content.

4. The **authorized set** is the in-scope list plus the paths this workflow's own steps write later
   (review fixes, architecture docs, the manual test plan). Add a path when a step writes it. Never
   add a path from the unrelated list.

### The staging rule

Step 4 and Step 8 both commit this way, substituting the authorized paths and their own message:

```bash
git add -- <authorized paths>
git diff --cached --name-only
git commit --only -- <authorized paths> -m "<message>"
```

- Stage explicit paths only. Never `git add -A`, never `git add .`, and never a directory pathspec
  that would sweep in neighbouring files.
- Read the staged diff before committing. If it names a path this run did not author, stop, report
  those paths, and commit nothing.
- Untracked files outside the authorized set are never staged, at either commit.
- `--only` keeps index content outside the named paths out of the commit.

## Workflow Steps

### Step 1: Simplify

Run the code-simplifier agent to elegantly simplify the implementation without losing functionality.

Try dispatching code-simplifier in this order:
1. Marketplace plugin: `subagent_type="code-simplifier:code-simplifier"` (if installed)
2. Bundled agent: `subagent_type="code-simplifier"` (from session-flow package)

If neither is available, skip this step and proceed to Step 2.

```
Task tool: subagent_type=[resolved from above]
prompt: "Simplify and refine the recently modified code for clarity, consistency, and maintainability while preserving all functionality, and remove what the implementation left behind: dead code, temporary helpers, debug output, scratch files. Do not run the full test suite at this stage; individual tests are fine."
```

Wait for completion. Review the changes made.

### Step 2: Review

Run the code-reviewer agent to identify issues.

```
Task tool: subagent_type="code-reviewer"
prompt: "Review the recent code changes for bugs, logic errors, security vulnerabilities, and code quality issues. Do not run the full test suite at this stage"
```

If issues are found:
1. Present the findings, high confidence first.
2. Fix Critical and Warning findings labelled high or medium confidence.
3. List low-confidence findings for the user with one line each; do not act on them unless the
   user asks.
4. Re-run the reviewer once on the fixes.

Loop until the reviewer passes with no significant issues, but do not yet run the full test suite at this stage (you can run individual tests)

### Step 3: Security & Liability Audit

**Run when:** 3 is in the resolved step set.

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
1. Present the findings, high confidence first.
2. Fix technical Critical and High findings labelled high or medium confidence.
3. Note Legal/Liability High findings for follow-up; they may need ToS or privacy policy updates
   rather than code fixes.
4. List low-confidence and Medium findings for the user with one line each; do not act on them
   unless the user asks.

### Step 4: Commit (Checkpoint)

Commit the simplified and reviewed code, following the staging rule with the authorized paths the
snapshot and Steps 1-3 produced:

```bash
git add -- <authorized paths>
git diff --cached --name-only
git commit --only -- <authorized paths> -m "refactor: simplify and address review feedback"
```

This creates a checkpoint before the test suite and documentation steps.

### Step 5: Run Test Suite

**Run when:** 5 is in the resolved step set.

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

### Step 6: Update Architecture Docs

**Run when:** 6 is in the resolved step set.

If the project has architecture documentation (detect via `.session-flow.json` config or scan for `architecture/`, `_devdocs/architecture/`, `docs/architecture/`, `ARCHITECTURE.md`), use the `/update-architecture` skill for surgical, token-efficient documentation updates. Paths may point outside the repo; resolve them relative to the repo root.

1. Identify which layer docs need updating based on changed files
2. Make surgical edits (update counts, signatures, entries -- not rewrites)
3. Update the architecture index if needed
4. Check doc health -- split any docs exceeding 1500 lines

Skip this step if the project has no architecture docs.

### Step 7: Generate Manual Test Plan

**Run when:** 7 is in the resolved step set.

Generate a manual test plan for the feature that was just implemented.

1. Analyze the feature from recent commits and changed files
2. Determine a short kebab-case feature label (e.g. `banner`, `mcp`, `credentials`)
3. Save to the project's testing directory (from `.session-flow.json` or detect `testing/`, `_devdocs/testing/`, `docs/testing/`). Paths may point outside the repo; resolve them relative to the repo root.
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

### Step 7.5: Verification (optional, for feature/plan completions)

If this session closed out an implementation plan (not just a bugfix or small change), consider running `/session-verify` before the final commit. Verification produces an evidence artifact proving the implementation matches the design doc and plan via falsifiable hypotheses, structural audit, defect probes, and integration probes.

**Run when:**
- A `/session-research-design` plan was implemented
- A multi-task `/session-task-planning` was completed
- Behaviour is user-visible and risk-prone
- Prior code review flagged critical or high-severity defects that should be independently confirmed fixed

**Skip when:**
- Bugfixes, refactors, single-file features
- Internal polish with no design doc
- Small changes where the test suite in Step 5 is sufficient evidence

Do not run automatically. Present the option to the user; proceed to Step 8 if they decline.

### Step 8: Final Commit

**Run when:** 8 is in the resolved step set and Steps 5-7 left something to commit.

Commit the documentation updates and test plan, again by the staging rule — the authorized paths
here are the docs and test-plan files Steps 5-7 wrote, plus any test fixes they required:

```bash
git add -- <authorized paths>
git diff --cached --name-only
git commit --only -- <authorized paths> -m "chore: update docs and add manual test plan"
```

## Execution Notes

- Run each step sequentially -- each depends on the previous
- If any step reveals significant issues, address them before proceeding
- The two commits create clear checkpoints: one for the refined implementation, one for docs and the test plan
- Both commits stage the explicit authorized paths from the ownership snapshot; neither uses `git add -A`
- Tests run once after all code changes (Step 5) to minimize test suite execution time
- For trivial changes (typos, docs-only), leave the audit out of the step set at configuration time rather than skipping Step 3 once it is in the set
- Step 7 generates a manual test plan for QA -- skip if the feature has no user-facing behavior
- Step 7.5 (verification) is always optional -- present but do not auto-run
- If Steps 5-7 changed nothing, there is nothing for Step 8 to stage

## Anti-Patterns

**Staging everything at a checkpoint:**
- BAD: `git add -A && git commit` — the user's unrelated edits and stray untracked files ride along
- GOOD: stage the authorized paths from the ownership snapshot, read the staged diff, then commit

**Re-deriving a step's applicability from the preset:**
- BAD: Step 3 checks whether the user chose Standard or Quick, after they added the audit as an add-on
- GOOD: Step 3 checks whether 3 is in the resolved step set, which the add-on already put there

**Running full suite between every step:**
- BAD: Run the full test suite after simplify, again after review, again after the audit
- GOOD: Run individual tests during the simplify/review/audit steps, full suite once at the test-suite step

Chain context: see `references/workflow-overview.md`.
