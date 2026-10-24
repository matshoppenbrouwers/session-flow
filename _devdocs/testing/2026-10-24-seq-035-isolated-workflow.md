# SEQ-035 isolated workflow manual test plan

**Date:** 2026-10-24
**Branch:** `main`
**Implementation:** `bb0b04c`
**Tester:** _______________
**Status:** Manual cases below are unexecuted. Existing fixture results are recorded separately.

## How to use

Use [the workflow reference](../../references/git-workflow.md) and a disposable project with
local bare remotes for cases 1-6. Load the skill files from the implementation revision in the
host being tested; an older installed plugin does not test these changes. Record host, resolved
skill/package path, Python/Git versions, full source SHA and each observed runtime root.

Mark every case PASS, FAIL or SKIP and attach commands, outputs and relevant SHA/file digests.
A skipped live check remains unverified. These instructions do not authorize operations in
lat-lamp, lamp-badger or production. Case 7 requires its own accepted execution scope, named
owners and action-specific authority before any mutation.

The existing local baseline is 825 passing tests, with 12 Git/runtime fixtures and 13 acceptance
checks. Reuse unchanged evidence. To reproduce the focused baseline when a change warrants it,
run from a disposable checkout containing both committed `_verification/seq-035-*.md` reports:

```bash
python3 -B -m unittest discover -s tests -p 'test_git_workflow.py' -v
python3 -B -m unittest discover -s tests -p 'test_seq035_acceptance.py' -v
```

The Git fixtures use temporary repositories and local bare remotes. They do not exercise actual
host skill invocation, remote protection, deployment or the live recovery cycle.

## 1. Host context and oracle targeting

- [ ] Invoke `session-next` in each of two disposable task workspaces. Confirm each assignment
  records a distinct actor, source checkout/branch/base and the same physical runtime root and
  namespace, with explicit canonical `--project-root` on runtime calls.
- [ ] Present copied configuration resolving to a second physical root with the same namespace.
  Confirm the session stops before edits or runtime writes and reports the mismatch.
- [ ] Invoke delegation with a pinned independent oracle authored after the worker's base.
  Confirm the coordinator materializes required files unchanged, checks discovery/import/fixture
  paths against the worker checkout, and keeps oracle paths outside the implementer's write scope.
- [ ] Resume with staged, unstaged and untracked files. Compare their bytes/index before and after
  startup; confirm no reset, clean, stash or rebase occurs.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## 2. Integration ownership and readiness

- [ ] Have two distinct actors request bounded integration tasks with the same absolute physical
  integration-directory scope. Confirm one holds a live claim and the other stops with the holder
  identified. A second clean clone must not bypass that scope.
- [ ] Start a later integrator without worker conversation history. Confirm it reads assignments
  and applicable passed results from the canonical runtime and checks exact submitted/tested HEADs.
- [ ] Supply changed HEAD, missing checks, stale evidence after reacceptance, and unfinished
  ancestors. Confirm each input is refused without changing integration or published history.
- [ ] Confirm progress uses `revise`, with the result unset through effects and receipts. For an
  interrupted merge, confirm resumption preserves state and takeover needs explicit authority.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## 3. Preservation, release source and subsequent work

- [ ] Leave task B with staged, unstaged and untracked changes, recording its HEAD, index entries,
  patches and file digests. Integrate/publish ready task A only to the disposable local remote.
- [ ] Compare all B observations unchanged. Verify all newly published ancestors were reviewed
  and the receipts name submitted, integrated and observed published SHAs.
- [ ] Exercise release preparation. Verify the clean build checkout selects the recorded canonical
  SHA including release metadata. A later metadata commit requires new validation and a new build.
- [ ] Start another independent task from fetched canonical history. Verify its recorded base equals
  that revision. If testing a squash/rebase policy, record submitted-to-canonical mappings and
  account for every remaining file before any separately authorized workspace retirement.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## 4. State, generated views and backup

- [ ] Record integration HEAD/status, then make disposable runtime transitions and render views.
  Verify only the canonical state history advances and integration stays clean at the same SHA.
- [ ] Inspect the runbook's state remote, owner, cadence and visibility choice. Test backup only
  against the disposable own-repository state root; check missing/diverged remote and uncommitted
  state outcomes, plus omitted ignored journals, other branches and outside generated views.
- [ ] Present records tracked in an enclosing source repository. Confirm routine backup is refused
  as a publication route and the session hands publishable history to the integration owner.
- [ ] For any proposed migration, confirm the plan preserves namespace, history and pinned
  commit/path references and names hosted consumers and snapshot ownership before moving anything.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## 5. Remote advancement

- [ ] Advance the disposable remote after candidate validation. Confirm a rejected normal push
  triggers fetch, full-history review and validation of a replacement SHA, with no force push.
- [ ] Simulate an uncertain publication response. Confirm the session inspects remote state and
  receipts before deciding whether to retry, retaining a live claim until authorized effects stop.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## 6. Protection and Windows/WSL modes

- [ ] On an authorized target, inspect actual branch protection and bypass settings. Record the
  observed rules and scope. Do not attempt a destructive force push as a test or infer protection
  from an ordinary non-fast-forward rejection.
- [ ] In a disposable checkout on each relevant host, inspect `git config --show-origin --get
  core.fileMode`, `git ls-files --stage` and `git diff --summary`. Distinguish working-tree mode
  noise from committed execute-bit changes. Verify linked worktrees share configuration effects.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## 7. Authorized recovery and live cycle

- [ ] Before execution, resolve exact coordination/integration paths, active owners and each allowed
  action. Refresh remote, local and deployed revisions. Resolve Badger's absent local work-root
  configuration without creating a replacement namespace. Treat the A5 inventory as dated evidence.
- [ ] At a coordinated writer pause, capture committed history and staged, unstaged, untracked and
  required ignored work. Establish preservation evidence for SEQ-957 work and deployed SEQ-855 changes.
- [ ] Execute only the separately approved recovery plan. Record before/after ancestry and file
  evidence, published history and any incomplete reconciliation with its owner and next action.
- [ ] Complete one authorized real release and subsequent local work. Verify released history is
  reachable from integration, reviewed publishable history remains on origin, deployed/build SHAs
  match the intended release and unfinished work remains intact. Retain every unknown as unverified.

**Result:** [ ] PASS / FAIL / SKIP. **Evidence and notes:** _______________

## Debugging reference

Use runtime `doctor`, `show` and `schema <command>` with the resolved absolute entrypoint and
canonical project root. Keep raw output beside the case evidence. Consult
[fixture observations](../../_verification/seq-035-workflow.md) and
[recovery inventory](../../_verification/seq-035-recovery-inventory.md) for existing limits.
Instruction checks coordinate cooperating sessions; they do not enforce an OS boundary.

## Verdict

| Area | Cases | Pass | Fail | Skip |
| --- | ---: | --- | --- | --- |
| Host context and oracle | 1 | | | |
| Integration ownership/readiness | 1 | | | |
| Preservation/release/new work | 1 | | | |
| State/views/backup | 1 | | | |
| Remote advancement | 1 | | | |
| Protection/modes | 1 | | | |
| Recovery/live cycle | 1 | | | |
| Total | 7 | | | |

**Overall verdict:** [ ] READY FOR RELEASE / NEEDS FIXES / INCOMPLETE
**Blocking issues:** _______________
**Non-blocking issues:** _______________
**Tester sign-off and date:** _______________

Parent SEQ-035 stays open until its live-cycle criterion has applicable evidence. A local fixture
pass or a completed checklist with live cases skipped cannot close it.
