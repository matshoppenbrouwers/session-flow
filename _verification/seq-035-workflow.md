# SEQ-035 local workflow verification

Observed 2026-10-24. The 12 disposable Git/runtime fixtures pass. This supports A4's local
workflow criteria, not parent completion or live recovery.

## Revision and environment

Source baseline: `47c0d9e51979445fca76c5816b55cf225d504171`, with uncommitted A1-A3 workflow
instructions and this A4 test file (SHA-256
`106e27645dcc450ea18f43f1bcc72bb8d0084ba05075aaa096046eb132367123`). The checks used the repository's `scripts/session-flow.py`,
not an installed plugin. This is working-tree evidence, not an exact committed release handoff.

Environment: Python 3.12.3, Git 2.43.0, Linux 6.6.87.2-microsoft-standard-WSL2. Fixtures use
`StoreCase` temporary directories under `/tmp`, independent task worktrees, a separate state
repository and local bare remotes. No external remote, live checkout or production mutation ran.

## Commands and results

| Command | Observed result |
| --- | --- |
| `python3 -B -m unittest discover -s tests -p 'test_git_workflow.py' -v` | 12 passed in 47.269 seconds |
| `python3 -B -m unittest discover -s tests -p 'test_seq031_runtime.py'` | 30 passed in 9.630 seconds |
| `python3 -B -m unittest discover -s tests -p 'test_store.py'` | 192 passed in 97.045 seconds |
| `PYTHONPATH=tests python3 -B -m unittest test_seq035_acceptance.A4FixtureTest` | 2 passed |

## Coverage

| Fixture | Observed behavior |
| --- | --- |
| Independent contexts and later integrator | Commands launched from two task worktrees resolve the same physical work root and namespace. Distinct actors claim separate tasks. The later integrator reads A's exact passed commit from the shared record while B remains unfinished. |
| Owned integration and preservation | A merges and pushes through a live integration claim. B's HEAD, index entries, staged patch, unstaged patch, tracked bytes and untracked binary bytes remain unchanged. The claim has no result until receipts are written, then settles to done. |
| Fresh canonical base and release source | A clean detached build checkout equals the recorded integrated/published SHA. A subsequent task worktree starts at fetched `origin/main`. No actual application package or deployment is built. |
| State and view isolation | Runtime writes advance the separate state repository, render a sequence outside the state root, and leave the application integration checkout clean and at its expected revision. |
| Copied state root | A copied root retains the same namespace but fails the procedure's physical-path comparison. The runtime itself can read that copy. |
| Concurrent integration claim race | Two separate processes wait at a stdin barrier and attempt the same physical directory scope with distinct actors. Exactly one succeeds. After both exit, a bounded retry of the loser is refused for the winner's overlapping claim. No timing sleep controls correctness. |
| Actor and result limitations | Reusing one actor bypasses cross-task overlap exclusion. Distinct actors are therefore required by the instructions. Any recorded result releases exclusion, including unknown while lifecycle remains active. |
| Takeover and interruption | A second actor cannot claim the same task without explicit takeover authority. Authorized takeover retains prior receipts and conflicted index/files. The procedure's preflight detects dirty state and an in-progress merge without changing either. |
| Handoff refusal | Test-only procedure checks reject missing passed results, missing checks, stale or missing applicable pass evidence, differing submitted/evidence revisions, a changed source HEAD and an unfinished ancestor outside the reviewed publishable set. Integration and remote history remain unchanged in refusal cases. |
| Reaccepted scope | Actual runtime revise/reopen/reaccept calls retain an old passed result at the same submitted SHA, but its evidence is stale. The handoff check refuses it. Separate negative cases reject absent evidence, a non-passing entry, and applicable evidence for another SHA. |
| Remote advancement | A normal push of the old candidate is rejected after another publisher advances the local bare remote. Fetch, merge and renewed content/ancestry checks produce a new candidate preserving both histories; its normal push succeeds. |
| Backup omissions and failures | Backup pushes only the state repository's current branch. Uncommitted state is reported incomplete. Ignored journals and an uncommitted outside sequence are absent from the pushed tree even when `complete` later becomes true. Missing remote and divergent remote state are reported without rewriting either history. |

## Limits and remaining verification

The tests exercise actual Git operations, runtime claims/results and backup responses. The
`context_matches`, `handoff_problems` and `integration_problems` helpers are test-only executions
of checks written in the workflow reference. They are not shipped runtime guards. A session can
bypass these instructions, reuse an actor or operate outside the shared root; these tests do not
provide an operating-system security boundary.

The handoff fixture uses JSON inside the existing summary string for unambiguous test data.
The product contract remains prose plus existing fields, with no new schema or automated parser.
The reviewed publishable commit set is explicit fixture input; a real integrator must determine
it from accepted work and inspect all candidate history. Synthetic content assertions do not
substitute for a project's build and application checks.

Manual checks remain for host skill invocation, owner identity, actual runbook locations, hosted
visibility, branch protection/bypass configuration, Windows file-mode behavior and migration of
pinned references. Squash/rebase mapping is documented but this fixture uses ancestry-preserving
integration. Ignored application files, other state branches and a real backup cadence are not
restored or tested as a disaster-recovery exercise.

A5 supplies read-only recovery evidence. Phase 4 still needs authorized initial recovery, a live
release and subsequent local work proving deployed history and unfinished work are preserved.
Neither these fixtures nor the passing task results close SEQ-035.
