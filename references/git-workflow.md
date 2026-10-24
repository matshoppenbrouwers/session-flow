# Task workspaces and Git handoff

Use this procedure before editing source and when reporting work for integration. It uses
existing runtime records and Git commands. The checks are instructions for cooperating sessions,
not runtime enforcement of Git state. Resolve the helper through
[runtime integration](runtime-integration.md).

## Resolve the session context

Read the project runbook from `paths.runbook` in `.session-flow.json`, falling back to the
runbook named by CLAUDE.md or AGENTS.md. Before source edits, resolve these values from that
runbook and the current assignment. If a value is missing or contradictory, report it for
correction before proceeding:

| Value | Check |
| --- | --- |
| Canonical runtime project root | Absolute project directory passed explicitly as `--project-root` on every runtime call. This is `$PROJECT_ROOT`, even when the shell is in a task worktree. |
| Physical work root and namespace | Run `doctor` against that project root. Resolve `storage.work_root` to its physical path, following symlinks, and compare it and `storage.namespace` with the recorded coordination home. |
| Source repository and remote/default branch | Check the source repository's Git identity and remote URL against the runbook. Confirm the target branch explicitly; do not infer it from the task branch or assume `main`. |
| Source checkout, branch and base SHA | Record the absolute task checkout, its branch and full base commit, and verify them with Git. Distinguish this checkout from the canonical integration checkout. |
| Actor | Use a distinct session identity for each independent writer. Delegated assignments retain the coordinator's task-specific claim actor. |

A copied `.session-flow.json` or copied record directory does not establish a live backlog.
Matching namespaces in two directories are insufficient: all sessions must resolve the same
physical work root. Reject a copied root or an unexpected namespace and report both observed
and expected locations. Do not initialize or mutate the copy to make it appear current.

## Start or resume a source workspace

Each writer gets one isolated task branch and worktree. Independent clones are an alternative
when tooling cannot use worktrees, with the same runtime root and reporting contract. The
canonical integration checkout is not a task workspace. Read-only review of another writer's
checkout does not grant permission to edit it.

For new work, use freshly fetched canonical history and record the exact base commit. Linked
worktrees share refs and configuration: coordinate fetching and repository-wide maintenance
with the integration owner. If a fresh base cannot be obtained, report that limitation before
starting. When work intentionally starts on a prerequisite branch, record that dependency and
base explicitly. Its unfinished ancestors are not independently publishable merely because
the new task's diff is small.

For resume, use the recorded checkout and actor. Verify the repository, remote/default branch,
physical runtime root, namespace, branch, base commit and current HEAD against the assignment
and checkpoint. Preserve staged, unstaged and untracked contents. Do not reset, clean, stash,
rebase or replace the workspace as a startup step. A mismatch or unknown owner stops edits
until corrected; elapsed time does not transfer ownership. Record an intentional change of
base or workspace before continuing and preserve the previous assignment as history.

Claim the accepted task before source edits, using its existing `allowed_paths`. Isolation
does not relax overlap restrictions or widen allowed paths: the execution skill's dependency,
overlap and approval rules still apply. Paths remain relative to the assigned source repository
where that is how the task defines them; switching checkouts never grants additional files.

After claiming, use `show` and `schema revise` to append an assignment note to the record's
`body` through `revise`. Preserve its existing body and scope. The note names the claim actor,
worker/session identity, source repository, remote/default branch, absolute checkout, branch,
base SHA, canonical runtime project root, physical work root and namespace. Include any
prerequisite branch. Use the current expected revision and check that acceptance still applies
after the write. Do not change accepted scope or write claim/result fields through `revise`.

Independent sessions claim and report their own assignments. A delegated worker instead
receives this context and its write boundary from the claiming coordinator, then reports back
to that claim holder. It must not impersonate an independent holder or create a second claim.
The coordinator writes the assignment note and result under the task's recorded actor.

## Materialize acceptance tests in the assigned workspace

Before an implementer starts, the coordinator makes the test-author's oracle available in that
writer's workspace. Record the oracle's source revision or content digests, original and
materialized paths, required fixtures, test command and working directory in the assignment.
Copy the pinned files unchanged into the expected test layout, or use an external immutable
oracle whose supported target-root option explicitly selects the assigned source checkout.
Do not assume a fresh worktree contains tests authored after its base commit.

Oracle files remain coordinator-owned and outside the implementer's write boundary, including
any directory globs. Preserve existing files when materializing them. If the layout conflicts
with that boundary or needs additional write authority, stop and coordinate the adjustment
through the execution skill's approval/revise/reclaim procedure. Never silently widen scope or
ask the implementer to copy, adapt or edit the oracle.

Validate test discovery and the resolved source/import/fixture paths before dispatch. Running
an absolute test path from a different working directory is insufficient: a test deriving its
repository from `__file__` can still inspect the coordinator checkout. Materialize such tests
in the assigned checkout's corresponding layout and verify their resolved repository is that
checkout. If the oracle cannot target it unchanged, return the issue to the test-author through
the existing oracle-correction process. Expected red assertions are acceptable; testing a
different checkout is not. Recheck the pinned oracle files on resume and after execution, and
include their identity and the actual source checkout in check evidence.

## Record an exact-commit handoff

Before declaring readiness, commit the authorized task changes under the project's commit
rules and run the applicable checks against that exact commit. Commit only the assigned files
and authorized tests; retain any unrelated work. If committing is outside the current authority
or checks cannot run, report the local result and limitation without claiming readiness.

Use `schema record-result` and record through the canonical runtime project root:

- `result.outcome` is `passed` only when the reported checks passed.
- `result.evidence.revision` is the full tested commit SHA, not a branch name or a dirty HEAD.
  Evidence also names criteria, environment and limitations; retain commands and observed
  results in `result.checks`.
- `result.summary` names the source repository, absolute checkout, branch, base commit,
  submitted head and whether this exact commit is ready for integration. State any outstanding
  dependency or uncommitted work explicitly.

Only the claim holder calls `record-result`. A locally passed task may be `done` while parent
delivery remains pending. A failed, unchecked or uncommitted result is not a ready handoff.
Readiness grants no integration, push or deployment authority.

An integrator started later reads current assignments and results through the shared runtime;
it needs no worker conversation, polling service or continuously running coordinator. Before
using a handoff, check the applicable passed evidence and commands, locate the submitted
commit in the named repository, and compare the recorded submitted head, branch HEAD and
`result.evidence.revision`. They must agree. Review the full proposed history for unfinished
ancestors and check any uncommitted work is excluded and preserved.

If the submitted head or code changed after checks, or the commit, checks or assignment are
missing, refuse readiness and report the discrepancy to the holder. A stale result does not
cover a newer HEAD. Obtain a fresh checked handoff through the runtime's normal correction
and reopening rules where needed; never overwrite a done task's result to disguise new work.

## Claim integration ownership

Every delivery or release that integrates source uses an ordinary bounded integration task.
Its accepted scope names the input task identities, target repository/branch, canonical
integration directory and authorized actions. If that assignment is absent, obtain it before
integration. A source task's passed result does not create integration or publication authority.

Resolve the integration directory to the same absolute physical path for every batch for this
repository. Include that directory's `/**` scope in both the assignment and `claim.allowed_paths`.
Do not substitute task-relative paths, a symlink alias or a different clean clone: the runtime
compares path strings and directory prefixes, not Git repository identities. A clean build clone
still belongs to this integration assignment. Use a unique actor for each independent session.

Before any integration Git mutation, use `show`, `schema claim` and `claim` against the canonical
runtime project root. Re-read the result: the task must be active, its acceptance applicable,
its claim held by this actor with the shared directory scope, and its result unset. Another
task's overlapping live claim returns `invalid-request`; another holder of the same task returns
`missing-authority`. Report the holder and stop. Never narrow away the common directory to bypass
the refusal. A short runtime write lock serializes claims, but is not held during Git operations.

Keep this claim live through all authorized effects and their receipts. Write progress and
intermediate commit IDs as body notes through `revise`, preserving scope and prior notes. Do not
call `record-result` as a progress update: **any recorded result releases overlap exclusion**,
including `failed` or `unknown` while the task remains active. Before each consequential effect,
re-read the claim and action authority. A claim coordinates cooperating sessions on one machine;
it does not prevent unrelated Git commands or replace remote branch protection.

## Validate and integrate submitted work

With the live integration claim, perform these checks before merging or publishing:

1. Verify the canonical checkout's repository, target branch and remote against the runbook.
   Inspect status and in-progress merge/rebase/cherry-pick state. An unexplained dirty checkout
   or interrupted operation stops normal execution. Preserve its index, working files and refs
   for the recorded owner; do not reset, stash, clean or abort it as routine preflight.
2. Fetch the authorized target remote and record the full target SHA. Confirm the clean
   integration checkout starts from the agreed canonical history. A diverged or unexplained
   local tip requires a separately bounded recovery decision, not an automatic reset.
3. Read each current source assignment and passed result. Apply the exact-commit handoff checks
   above: submitted head, source branch HEAD and tested evidence revision must agree, checks
   must be present and applicable, and dependencies must be accounted for. A changed head or
   incomplete handoff stops that input pending a fresh checked result from its holder.
4. Review every commit that the candidate would add to the target, including ancestors inherited
   from dependency branches and any existing local commits. Each must be publishable under this
   assignment. An unfinished ancestor stops integration; a small final diff is not evidence that
   its history is ready. Leave the source branches and other writers' unfinished work intact.
5. Integrate only the validated commits and run the combined checks. Prefer ancestry-preserving
   merges. If the repository requires squash or rebase, perform it in the integration workspace,
   preserve the submitted heads, and record their mapping to the canonical result commits.
   Never rewrite another writer's active branch. Record the integrated head and tested revision.

Before an authorized push, refresh the target observation. If the remote advanced, stop using
the old candidate, incorporate the new canonical history under the assignment, and revalidate
the new candidate and full publishable ancestry. Record the replacement SHA and checks. A normal
push rejection follows the same path, never a force-push fallback. If publication's outcome is
uncertain, inspect the remote and receipts before deciding whether any retry is needed.

## Pin release sources and settle receipts

A release builds the recorded canonical integrated SHA, including approved release metadata,
in CI or a clean checkout verified at that exact revision. Do not reconstruct a release from
dirty task files or a moving branch name. Record the build source SHA with the artifact/check
results. Any later source or release-metadata commit creates a new candidate: revalidate it and
build/package that revision before declaring it ready. Existing build and publication authority
gates still apply.

Append receipts through `revise` while ownership is live. Name the integration task and actor,
repository/target, submitted heads, integrated head, observed published head (or explicitly
unpublished/unknown), commands and check results, build source SHA where relevant, and remaining
work. Keep the existing delivery receipt on its parent item under the execution skill's rules;
do not replace its required target fields. The integrated or published canonical result is the
completion reference for squash/rebase, where source-head reachability is not a valid test.

Only after authorized effects have stopped and receipts are saved does the holder record the
integration task's result. `passed` requires its accepted criteria and checks to hold; missing
publication or reconciliation required by that scope stays outstanding. Report successful
publication separately from unfinished reconciliation. A preparation-only assignment can finish
without publication when its scope says so, with the unpublished SHA explicit.

For interruption or failure, preserve commit IDs, Git status, known effects, unknown outcomes
and the exact next action in the assignment before reporting the result. The next owner must
inspect these notes, the checkout and remote state even if the previous result released exclusion.
Resume with the recorded holder. Reassignment uses `takeover_claim` with explicit user authority
resolved through `schema claim`; a closed terminal or elapsed time grants none. Reclaim before
further effects to clear a recorded result and restore exclusion, and transition a blocked task
to active through the normal runtime rules. Do not blindly repeat a push or deployment.

Retire a source workspace only after integration is confirmed, its owner has stopped writing,
and all remaining staged, unstaged, untracked and unpublished work is accounted for. Record the
canonical result mapping before retirement, especially after squash/rebase. Cleanup needs its
own applicable authority. New tasks start from freshly fetched canonical history; active tasks
keep their workspaces and update only under their owners' control.
