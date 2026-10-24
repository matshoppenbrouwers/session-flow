# SEQ-035 recovery inventory

Read-only observations on 2026-10-24, 17:52-17:55 UTC. The earlier divergence snapshot no longer
matches local checkout state. This inventory does not establish current remote or deployed state,
perform recovery, or satisfy the parent's live-cycle criterion.

## Observations

Paths were located from the named umbrella in SEQ-035's intent and the umbrella `CLAUDE.md`
Repos table. Both repositories' `AGENTS.md` and `CLAUDE.md` were read before inspection.

| Repository | Absolute path | Local branch and HEAD | Cached tracking ref |
| --- | --- | --- | --- |
| Umbrella | `/mnt/c/Users/matsh/Desktop/repositories/lat-lamp` | `main`, `87fa5c3c654c0cd5cc5ebda83bc139b32f34b192` | `origin/main`, `591fdf4ea317149ab12a02030ea044c4dddb0be0` |
| Badger | `/mnt/c/Users/matsh/Desktop/repositories/lat-lamp/lamp-badger` | `master`, `8ce740463234f58f9c6c61e2afee264530c90220` | `origin/master`, same SHA as local HEAD |

The umbrella was clean and 37 commits ahead, zero behind its cached tracking ref. Badger was
zero ahead/behind its cached ref, with five unstaged tracked modifications, no staged changes
and no untracked files reported. These comparisons do not establish equality with GitHub now.

Evidence: `git -C <path> rev-parse --show-toplevel`, `branch --show-current`, `rev-parse HEAD`,
`rev-parse origin/<branch>`, `rev-list --left-right --count HEAD...origin/<branch>`,
`status --porcelain=v1 --untracked-files=all`, `diff --cached --name-status`,
`diff --name-status`, and `ls-files --others --exclude-standard`. The umbrella snapshot began
17:52:09 UTC and the Badger snapshot began 17:52:50 UTC. Queries used `GIT_OPTIONAL_LOCKS=0`.
The later explicit index/worktree lists ran from 17:54 UTC. This is a series of observations,
not an atomic snapshot or a confirmed writer pause.

`remote get-url origin` identified GitHub repositories
`Laterite-Analytics/project-0-lamp-umbrella` and `Laterite-Analytics/project-0-internal-badger`.
`symbolic-ref refs/remotes/origin/HEAD` names `main` and `master` respectively. At 17:53:10 UTC,
`git ls-remote --symref origin HEAD refs/heads/<branch>` failed for both with
`Could not resolve host: github.com`. No fetch ran. The connected GitHub `search_branches` tool
listed `main` and `master` at 17:53:35 UTC but supplied no head SHAs or protection settings.

State layout was inspected through each `.session-flow.json` and the installed 3.0.0 runtime's
read-only `doctor --project-root <path>` at 17:52:33 UTC:

- Umbrella namespace: `ffd7a5a5-f675-4a87-a4f5-669c8f7e36ad`. Physical work root:
  `/mnt/c/Users/matsh/Desktop/repositories/lat-lamp/_devdocs/work`. It is tracked in the enclosing
  umbrella repository (`own_repository: false`), with generated sequence at
  `/mnt/c/Users/matsh/Desktop/repositories/lat-lamp/_devdocs/SEQUENCE.md`, outside the work root.
  Doctor reported no held root lock or pending operations. This says nothing about active editors.
- Badger's config has no `paths.work`; doctor resolves the absent
  `lamp-badger/_devdocs/work`, returns no namespace, and points its sequence at the umbrella's
  old `_devdocs/todo/SEQUENCE.md`. Its instructions require shared umbrella state. Resolve that
  mismatch before using the app directory as a runtime project root. Do not initialize a second
  namespace merely because doctor reports the app-local root absent.

At 17:54 UTC, read-only enumeration with the installed runtime's `records.read_record` and
`store.live_claim` found these claims still counted for exclusion: `SEQ-855/A10` (`agent:A10`,
active, claimed October 21), `SEQ-859` (`mats`, deferred), `SEQ-870` (`codex-seq870-park`, deferred),
`SEQ-888/D1` (`session-delegation:SEQ-960`, accepted), and `SEQ-905` (`mats`, deferred).
Recorded actors and lifecycle labels are not evidence that their sessions are running or that
one owns Badger's five modified files. No takeover or cleanup is inferred from their age.

Historical identifiers were checked locally at 17:54:50 UTC using `rev-parse --verify <sha>^{commit}`
and `merge-base --is-ancestor <full-sha> HEAD`:

| Historical report | Current local observation |
| --- | --- |
| Umbrella merge `4cb6b79` | Object `4cb6b797a6f46bedbebc63ac3c09ec593abd588b` exists and is an ancestor of umbrella HEAD. |
| SEQ-957 work `adf2fe2e` | Object `adf2fe2ebbe1fc14997b6242a3e312af615908d0` exists in Badger, but is not an ancestor of local HEAD. Its replacement/content mapping is unverified. |
| Reported deployed SEQ-855-era `5cce49ab` | Object `5cce49ab5fa38fdc690bbb0f316ba1199b9184f8` is an ancestor of local Badger HEAD. This does not prove current production contains or runs it. |

Runtime `show` at 17:52:58 UTC reports umbrella `SEQ-957` revision 11 as `done` and `SEQ-855`
revision 40 as `cancelled`. Those are current record observations in the umbrella namespace,
not this repository's SEQ namespace and not independent deployment verification. The earlier
68-commit umbrella and 10-behind/1-ahead Badger counts remain historical user-reported evidence.

Both repositories return local `.git/config` `core.fileMode=false` from
`git config --show-origin --get core.fileMode`. Badger has `core.hooksPath=hooks`; its executable
`hooks/pre-push` checks build-stamp ancestry/freshness, not remote force-push protection.
The umbrella has no configured hooksPath and no `.git/hooks/pre-push` file. No hook was executed.
`git worktree list --porcelain` also lists two umbrella and four Badger registrations marked
prunable because their `/tmp` paths are absent. Nothing was pruned. Linked worktrees share Git
configuration, and `core.fileMode=false` does not reconcile mode differences already committed.

## Unknowns

Current remote head SHAs, branch protection, ruleset coverage and bypass permissions are unknown.
No available connected read tool exposed protection settings, and local network lookup failed.
A local hook is not proof that GitHub will reject a force update or branch deletion.

Current `badger-uplink` and `core-ui-uplink` deployed SHAs and service health were not queried.
The umbrella instructions identify `/opt/badger/app` and `/opt/badger-ui/app` on the shared droplet
and say restarts reset to `origin/master`; that is runbook evidence, not a live observation.
No SSH, Anvil command, restart or production mutation ran.

Owners of the five modified Badger files, unpublished umbrella commits, historical scratch
clones and recorded claims need confirmation. No process-name inference was used. The intended
integration checkout, backup owner/cadence, state migration destination and hosted consumers of
records/views have not been approved. The historical SEQ-957 commit's canonical replacement
also needs content/history review before it can be retired.

## Preservation

Preserve the full umbrella local history, including its 37 commits beyond the cached ref,
and the old SEQ-957 object until its mapping is resolved. Publication eligibility must be checked
commit by commit; cleanliness does not authorize publishing all local commits.

Badger file bytes observed at 17:54:50 UTC, using `hashlib.sha256(Path.read_bytes())`:

| Unstaged tracked path | SHA-256 |
| --- | --- |
| `_devdocs/architecture/module-dashboards.md` | `79716298632f18b242282ab05caf8ddb754d55e6babb5f80316e26a7662b0567` |
| `_devdocs/architecture/module-project-detail-financials.md` | `05b4e17734992a088a1f95d775ab28f5072cc7057a72069409afd71bf1050279` |
| `_devdocs/decisions/0903-separate-proposal-project-channels.md` | `9c1d33a2643488edd20799eece18e2176341c493416e5c8436c0b090720a8846` |
| `client_code/MCFRequestDetail/_render_hero.py` | `985efaee9123e4dc5752cd2c1718ebe2bfa576f7ee23f11680e4c15cb08b370a` |
| `client_code/OperationsReview/__init__.py` | `6bb91a0eda10850c6fb382a58bbc92714563fa594d61b88bb6d25c24636ad705` |

Before recovery, each owner must pause writing and approve preservation of committed refs,
index/staged state, unstaged patches and bytes, untracked files, and required ignored files.
Re-inventory even the currently empty staged/untracked categories. Record recovery copies and
checksums in an approved location and verify restoration in a disposable directory before any
checkout replacement or deletion. This inventory records hashes only; it did not make backups.
Keep current checkouts and old locations recoverable until owners confirm their work is retained.
Do not reset, stash, clean, rebase, delete worktrees or prune registrations as routine preflight.

## Recovery proposal

These are proposed bounded tasks, not captured assignments or authorization to execute them.

| Proposed task | Scope and owner/authority needed | Completion and rollback boundary |
| --- | --- | --- |
| Confirm owners and refresh evidence | Mats names the umbrella/Badger writers and integration owner, confirms a pause, and authorizes remote/deployed read checks. Inspect current default-branch SHAs, protection/bypasses and both deployed revisions. | Timestamped receipts and preservation inventory. No source or service mutation. |
| Establish canonical context | Use the existing umbrella directory as the proposed canonical runtime project root and retain namespace `ffd7a5a5-f675-4a87-a4f5-669c8f7e36ad`. Under configuration authority, correct Badger's shared-root/view routing and record one physical context in its runbook. | All sessions resolve the same root/namespace. Preserve prior config for rollback, never create a competing live root. |
| Prepare owned integration homes | Proposed separate clean checkouts: `/mnt/c/Users/matsh/Desktop/repositories/lat-lamp-integration` and `/mnt/c/Users/matsh/Desktop/repositories/lamp-badger-integration`. Owner must confirm these paths are available and approve creation. Each repository gets an accepted integration task claiming its agreed physical directory. | Fresh canonical bases and no copied live state/views in clean integration. Keep existing source checkouts untouched. No publication at this stage. |
| Reconcile publishable history | Integration owner reviews the 37 umbrella local commits against freshly observed remote history and maps historical `adf2fe2e` to its accepted canonical result. Preserve deployed ancestry and the five Badger edits under their owners. Merge only approved history in the isolated integration checkout. | Combined checks, submitted-to-canonical SHA mapping and preservation comparison. Abort work in the isolated candidate if checks fail; no rewriting another writer's branch. |
| Separate state history and backup | State owner inspects hosted record/view consumers and pinned references before proposing an exact migration destination, remote, owner and cadence. Until migration, publish umbrella state history through owned integration, never routine backup-push from coordination. | Preserve namespace, full history, bindings and pinned references. Old locations stay recoverable but cannot remain parallel writers. Generated view publication has a named owner. |
| Protect and prove delivery | Repository administrator approves protection/bypass changes. Integration owner separately obtains push/release authority; service owner separately approves deployment. No force-push fallback. Existing fileMode settings need no speculative rewrite. | Exact integrated/published/build/deployed SHAs, normal remote update, approved rollback to a retained known-good revision. Any service rollback requires its own operational authority. |

The proposed integration paths have not been created or confirmed as canonical. Do not start a
recovery task until its exact paths, claim scope, owners, preservation location and action authority
are recorded. Cleanup of old registrations and workspaces follows confirmed integration and
accounting for all remaining work, under separate cleanup authority.

## Remaining verification

The local A4 fixtures passed, as recorded in `seq-035-workflow.md`. Live acceptance still requires
an authorized initial reconciliation, one real release, and subsequent local work. Record before
and after refs, deployed revision receipts, preserved staged/unstaged/untracked state, and a new
task starting from fresh canonical history. Confirm reviewed publishable history remains on
origin and released history is reachable from integration. Observe both Badger services where
the released surface requires them, without touching Profit.

Host skill invocation, actual protection/bypass settings, mode differences in committed history,
hosted visibility, backup restoration and active-owner handoff remain manual verification.
Unknowns above are inventory limits, not successful live verification. No external checkout,
remote configuration, runtime record or production state was mutated by A5.
