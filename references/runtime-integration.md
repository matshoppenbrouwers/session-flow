# Runtime Integration

How a skill, a command, or a companion plugin reaches the session-flow record runtime: where the
package lives on each host, the versioned request/response protocol, the named errors, and the
limitations the runtime does not defend against. Record fields and lifecycle rules are in
[work-item-contract.md](work-item-contract.md).

The runtime is a hard requirement, not an optional layer. There is no hand-editing path and no
legacy mode: when the helper or its interpreter is missing, mutation fails closed.

## Resolving the package

The entrypoint is `<package-root>/scripts/session-flow.py`, invoked with an absolute path by an
absolute interpreter path. Three host cases, one rule each — and no fourth:

| Host | Resolution |
|------|------------|
| Native Claude plugin | Use the plugin root the host supplies in `${CLAUDE_PLUGIN_ROOT}`. |
| Codex | Use the discovered installed skill and package location for the installed entry file. |
| Standalone copy | Read the runtime descriptor the installer wrote beside the entry file. |

The descriptor is `session-flow-runtime.json`, written into each installed skill directory next to
its `SKILL.md`. Its paths are relative to that directory, so a moved installation still resolves:

```json
{
  "package": "session-flow",
  "version": "2.0.2",
  "protocol": 1,
  "python_minimum": "3.9",
  "entrypoint": "../../scripts/session-flow.py",
  "package_root": "../..",
  "references": "../../references"
}
```

Resolve `entrypoint` and `references` against the descriptor's own directory and use the absolute
results. It is generated output, rewritten on every install, so never edit it and never treat its
`version` as authoritative — ask `doctor` for `protocol`.

**Never scan the filesystem for an installed copy.** A found-by-search package may be any version,
and picking one silently is how two protocols end up mixed in one session.

When the descriptor, the entrypoint, or a named support file is missing, fail with what is missing
and where it was expected. Do not fall back to a different copy, a bundled snippet, or hand-editing.

## Invoking a command

```bash
python3 /abs/path/to/scripts/session-flow.py doctor --project-root /abs/path/to/repo
python3 /abs/path/to/scripts/session-flow.py revise --project-root /abs/path/to/repo \
  --seq SEQ-042 --input /abs/path/to/payload.json
```

| Option | Meaning |
|--------|---------|
| `--project-root` | The repository whose `.session-flow.json` resolves `paths.work` and `paths.sequence`. Defaults to the working directory. |
| `--namespace` | The namespace UUID the addressed records must belong to. A mismatch is `invalid-identity`. |
| `--seq` | Work-item identity, `SEQ-NNN`. |
| `--task` | Task identity within that item, such as `A1`. |
| `--input` | Path to the JSON payload of a mutation. |

Every mutation payload carries the expected record revisions, the requested changes, and
provenance. `transition`, `claim` and `record-result` may omit the operation ID, and the runtime
then generates one ([Operation IDs](#operation-ids)). **No option accepts interpolated issue text or a shell fragment**, no argument is
passed to a shell, and no record content is executed by any command. Free text reaches the runtime
only as JSON through `--input`.

Paths resolve from `.session-flow.json`: `paths.work` (default `_devdocs/work`) and `paths.sequence`
(default `_devdocs/SEQUENCE.md`).

## Canonical state, views and backup

Use [Task workspaces and Git handoff](git-workflow.md) for source workspaces, session identities
and integration ownership. The project runbook names one canonical runtime project root and its
physical work root. Pass that project root explicitly on every runtime call, even from a task
worktree. Compare `doctor`'s resolved work root and namespace with the runbook. A copied config or
record directory is not a second live root: matching namespaces alone do not establish identity.
Refuse writes to a copied root and resolve the intended location before continuing.

Independent sessions claim and report through this same root under distinct actors. Delegated
workers report to their claim holder. Serialize runtime mutations; the short root lock does not
own source checkouts or integration Git operations.

Choose the state layout before moving records or generated views:

| Layout | History and publication behavior |
| --- | --- |
| Work root with its own Git repository | Runtime commits advance only state history. Keep its coordination home separate from the clean application integration checkout. Choose its visibility and backup destination explicitly. |
| Records tracked in an enclosing source repository | Runtime commits advance that repository's current branch. Keep the live coordination checkout distinct from integration and bring publishable state history through the owned integration path. `backup` would push the containing source branch, not a records-only branch. |
| Generated sequence outside the work root | `render` writes `paths.sequence`, but operation commits exclude paths outside the work root, even when an enclosing repository tracks them. Give that view an explicit home and publication owner; it must not dirty the clean integration checkout. |

Task views are generated inside the work root. Prefer local sequence views alongside the state
repository when no hosted consumer needs them. If hosted ops needs committed records or views,
inspect its actual paths and visibility requirements before choosing a private or relocated root.
Define a deliberate snapshot publication path through normal integration, with its source state
revision and owner. A published snapshot is read-only output, not another live backlog. Do not
silently remove hosted access or add a competing synchronization path.

Migration needs a reviewed inventory of current physical paths, Git history, namespace and
repository bindings, pinned references, generated outputs and their consumers. Coordinate a pause
with active writers, preserve unfinished files and existing history, and verify that pinned
commit/path references still resolve in the destination. Copying current Markdown or initializing
a fresh namespace is not a history-preserving migration. Keep old locations recoverable until
the new canonical context and view routes are verified; do not let both copies accept writes.

Record the backup repository, remote URL/branch, owner, cadence and applicable push authority in
the runbook. An own-repository work root separates state history; it does not configure backup.
A root without a remote has local history only. Resolve the intended destination and authority
before configuring or publishing it; a missing remote is no permission to create one automatically.

For a work root with its own state repository, the named owner runs authorized `backup` after a
completed session and integration handoff. First confirm `storage.own_repository` is true and the
reported repository, branch and remote match the agreed state destination. The command pushes the
containing repository's current branch, without fetching, merging or resolving divergence. Inspect
`pushed`, `complete`, `reason` and `uncommitted`: a successful push can still report incomplete
backup. Report failures and the remaining action, never fall back to a force push.

For records tracked in an enclosing application repository, do not run routine `backup` from the
coordination checkout: it would push that source branch and bypass canonical integration. Hand off
the publishable state history to the integration owner, who uses the live integration claim,
history checks and authorized publication path in [Task workspaces and Git handoff](git-workflow.md).
Record state history still awaiting integration or publication as outstanding backup coverage.
The runtime's ability to push an enclosing branch does not grant an alternate publication route.

`complete` covers only the command's check for uncommitted paths under the work root. It does not
mean a whole-workspace snapshot: application worktrees, ignored journals and other ignored files,
uncommitted views outside the work root, and commits on other branches are not included. A view
outside the root is carried only if already committed on the branch being pushed. List these
omissions in the backup receipt and account separately for any preservation the project requires.

## Request and response protocol

stdout carries exactly one JSON object; diagnostics go to stderr. Parse stdout, never stderr. The one exception is `--help` (or `-h`), which prints usage text and exits 0.

Success, exit code 0:

```json
{
  "protocol": 1,
  "command": "show",
  "ok": true,
  "result": {}
}
```

Failure, exit code 1:

```json
{
  "protocol": 1,
  "command": "revise",
  "ok": false,
  "error": {
    "code": "stale-revision",
    "message": "record SEQ-042 holds revision 5; the request expected 4",
    "detail": {"seq": "SEQ-042"}
  }
}
```

`protocol`, `command`, and `ok` are always present. `result` and `error` are mutually exclusive.
`error.detail` is an object whose keys depend on the code; treat unknown keys as informational.

Argument errors answer in JSON too. A stray positional word, an unknown option or a missing command writes one JSON object to stdout with `ok: false` and `error.code` `invalid-request`, and the exit code is 2, not 1. In that answer `command` is the first non-option word when it names a command, and `null` otherwise. The usage text from the argument parser may still go to stderr as the diagnostic.

`--help` and `-h` are the exception. They print the usage text and exit 0, and that is the one answer that is not JSON.
An unsupported interpreter answers on the same protocol with `command: null` — the guard runs before
any package module is imported, so a too-old interpreter receives JSON and an install instruction
rather than a `SyntaxError`.

### The `protocol` version

`protocol` is a single integer, reported by `doctor` and echoed in every response. It is
**independent of the plugin's semantic version**: the release number moves with every shipped
change, the protocol only when this contract changes.

Consumers check `protocol`, never the release number. Each companion declares the minimum and
maximum protocol it accepts in its own configuration, alongside its explicit path to the flow
installation. When flow is absent or the protocol falls outside that range, the lifecycle-dependent
commands refuse and name what to install, while the companion's standalone features — session
logging, Notion capture, portfolio rendering — keep working. Nothing degrades to editing records by
hand.

### Command families

| Command | Effect |
|---------|--------|
| `doctor` | Report runtime, protocol, storage, command availability, and error codes. Never mutates. |
| `schema` | Print a mutating command's required fields, optional fields and an example payload. Never mutates. |
| `show` | Return one record's identity, metadata, scope, `body`, `fingerprint`, `acceptance` and `evidence`. |
| `capture` | Create a work item in `captured`. |
| `revise` | Change a record under an expected revision. A `same_meaning` decision in the payload records both fingerprints. |
| `accept` | Bind an acceptance record to the current fingerprint and authority. |
| `select` | Return one candidate and its eligibility reasons. It never starts execution. |
| `claim` | Record a bounded assignment and move an `accepted` record to `active`. It does not run or schedule that assignment. |
| `record-result` | Record a scoped result. On a task, `passed` closes it and `blocked` blocks it. |
| `transition` | Apply a lifecycle transition. |
| `render` | Regenerate the sequence view and task views. Output is read-only, never an authority. |
| `import` | One-way transformation of an existing `SEQUENCE.md` into work items. There is no dual-format mutation path. |
| `reconcile` | Finish known partial operations; stop on unexplained divergence. |
| `backup` | Verify the configured work-root remote and push. |
| `restore` | Check the work root out from that remote. |

### Payloads: `schema`

`session-flow.py schema <command>` prints a command's payload description, so a caller does not
need a copy of it. It covers `capture`, `accept`, `revise`, `transition`, `claim` and
`record-result`, and returns three keys: `required` (the fields the command refuses to run
without), `optional` (the other keys it accepts) and `example` (one minimal payload the command
accepts). An unknown command name is an error that lists the valid ones. Skills and companions
should run `schema <command>` rather than hard-code payload shapes.

### `show`

`show` returns the record's identity, metadata and scope, plus four fields that callers
otherwise had to rebuild: `body` (the record text), `fingerprint` (the current scope
fingerprint), `acceptance` (whether the recorded acceptance still applies to that fingerprint)
and `evidence` (the status of each evidence entry). These only add to the earlier result.

### Operation IDs

`transition`, `claim` and `record-result` take an optional `operation`. When the payload has none,
the runtime generates one of the form `op-<uuid4>` and returns it under `operation` in the result.
A call interrupted before it returns never delivers the generated id. If you may need to retry
after an interruption, send your own `operation` id in the first call, then re-send the same payload
with that id: the runtime replays the earlier result and marks it `replayed: true`. Without your own
id, run `show` (and `reconcile` if the runtime reports a pending operation) before re-sending,
because `expect_revision` makes a blind retry fail with `stale-revision`. A retry without the id is
a new operation. An id reused with a different payload is refused.

`capture`, `accept` and `revise` carry no operation id. `import` still requires one, because its
resume path is keyed on it. `reconcile` takes none.

### Claiming and results

A successful `claim` on an `accepted` record also moves it to `active`, in the same operation, for
items and tasks. The legality and claim-holder checks still apply, and a claim that fails leaves
the record `accepted`. A direct `accepted` to `done` transition stays illegal.

`record-result` on a **task** settles only when the task is `active`, and then acts on the outcome:

- `passed` records the result, appends one evidence entry, and moves the task to `done` when the
  completion check passes. The entry takes `criteria`, `revision`, `environment` and `limitations`
  from `result.evidence`, and adds the current `fingerprint`, `result: pass`, `source:
  "record-result"`, the claiming `actor` and `recorded_at`. `result.evidence` is optional, but when
  it is present on a `passed` result for an `active` task its `criteria` must be a non-empty string;
  otherwise the call is refused and nothing is recorded. Other outcomes, and tasks that are not
  `active`, store `result.evidence` as sent. Leaving `evidence` out closes the task only when an applicable evidence entry is already recorded on it; otherwise the result is recorded, the task stays `active` and `not_closed` says why.
- If the completion check refuses, the result and the evidence entry are still recorded, the task
  stays `active`, and the response has `result.not_closed` with the reason. Fix the cause:
  re-accept with `"lifecycle": "active"` in the accept payload (a bare `accept` fails on an active
  task), or record a same-meaning decision (the `same_meaning` key in a `revise` payload) when the
  meaning did not change, or add the missing evidence; then record the result again.
- `blocked` records the result and moves the task to `blocked`.
- `failed` and `unknown` record the result and leave the lifecycle unchanged.
- When the task is not `active`, the result is recorded without an evidence entry and without a
  lifecycle move, and a `passed` result returns `not_closed` saying so. The remedy depends on the
  lifecycle. For `accepted`, claim the task, then record the result again. For `blocked`, the claim
  holder sends a `transition` to `active`, then records the result again. For `done`, nothing needs
  to happen: the task is already closed. For `captured`, `deferred` and `cancelled`, the task needs
  acceptance, or a reopening with a correction, before a result can close it.

`record-result` decides task versus item by the record's path. A new record created by `capture` or
`transition` gets `task` only from its path (a `task` in the supplied metadata is dropped), and
`revise` and `transition` patches cannot set or change a record's `task` or `seq`.

### Field ownership

In a `revise` metadata edit and in a `transition` change to an existing record, three fields belong to their own commands. `claim` and `result` are written only by `claim` and `record-result`, and `corrections` only grows through the `correction` key. A value that differs from the stored one is refused as `invalid-request`, and the message names the command to use. Sending the stored value unchanged is allowed, so a payload built from `show`'s `metadata` still works. The top-level `evidence` view in `show` adds an `applies` key per entry, so it cannot be sent back as `metadata.evidence`.

`evidence` is append-only in `revise` and `transition`: the stored entries must come first, unchanged and in order, with new entries after them. Removing, editing or reordering an entry, or sending `null`, is refused as `invalid-request`.

`format`, `namespace`, `seq` and `task` are identity fields, and `revision`, `acceptance` and `scope_checks` are runtime fields. In a `revise` edit or a `transition` change to an existing record, a value equal to the stored one is a no-op and a different value is refused: `invalid-identity` for `format`, `namespace`, `seq` and `task`, `invalid-request` for the rest. The message names what to use instead, such as `accept` for acceptance. `evidence: null` in a `revise` or `transition` patch is refused as `invalid-request`, whether or not entries are stored. An entry appended through `revise` or `transition` may not carry `source: "record-result"`. That marker is reserved for the entries the runtime builds in `record-result`, so an agent cannot append one, and a patch that tries is refused as `invalid-request`.

**New records.** A `transition` change with `new: true` handles metadata the same way `capture` does. The lifecycle is always `captured`, whatever the payload says. `claim`, `result`, `evidence`, `corrections`, `acceptance`, `scope_checks` and a delivery receipt (`delivery.delivered_at`) are dropped. A new record therefore starts without any claim, result, evidence or acceptance, and cannot be written with an invalid lifecycle.

**Completion is judged on the record as written.** A move to `done` through `revise` or `transition` is checked by the completion gate against the record as it would be after the write, with its new scope, delivery and evidence, not against the stored record. A `revise` that changes the scope and sets `done` in the same payload is refused as `inapplicable-evidence`, whether the acceptance no longer applies or the evidence does not. `record-result` is judged the same way.

**A claim needs an open lifecycle and applicable acceptance.** `claim` is refused as `missing-authority` unless the record is `accepted`, `active` or `blocked`. `captured`, `deferred`, `cancelled` and `done` records are refused before any write, so a stored result on a closed task is never cleared. To claim a `captured` record, accept it first. To work on a closed one, reopen it with a correction. `claim` is also refused as `missing-authority` when the record's acceptance does not name its current scope fingerprint. Accept the record again, or record a same-meaning decision, first.

On an **item**, `record-result` never changes the lifecycle, whatever the outcome. A result does
not close an item: item completion stays with `/session-verify` and the completion gate.

### Import surveys before namespace creation

`import` without `apply: true` is read-only and accepts an omitted `--namespace`. It uses the stored
namespace when one exists, rejecting an explicitly conflicting UUID. With an absent or empty work
root, it returns unbound previews: `items[].metadata` omits `namespace`, and `items[].text` is null.
These previews cannot be written as records. Missing namespaces alongside existing work state and
malformed namespaces are refused; the original namespace must be restored.

The survey includes `source`, `work_root`, `sequence_path`, `historical` (the directories actually
scanned), `namespace` (nullable), and `survey_fingerprint`, alongside the existing item and tombstone
lists. The fingerprint covers source text, resolved paths, discovered tombstones, and unresolved
links. It excludes namespace creation, so it remains stable across approved setup. It does not
attest to the contents of linked documents beyond identities discovered in the historical scan.
`source` must differ from the generated sequence path.

Applying still requires `--namespace` matching the stored UUID. Repair passes the approved
fingerprint as `expected_survey_fingerprint` in its apply payload; a mismatch is `invalid-identity`
before import writes. Existing callers may omit this optional field. The protocol and record format
versions are unchanged.

`doctor` reports `storage.bootstrap.eligible` and a reason. A missing work directory or an empty
directory containing only Git metadata is eligible for namespace setup. Existing namespaces are
preserved; malformed namespaces and unexplained contents require recovery. For eligible legacy
repositories, `/session-repair` plans Git setup and calls `bind-namespace` after approval. Setup
and import have separate commits. This is skill orchestration using existing commands, not a new
runtime command or automatic setup inside `import`.

`backup` and `restore` are thin wrappers over Git and define no archive format. The work root is an
ordinary Git repository: it owns history, and each mutation ends in a commit there.

### Locking and commits

Every command that writes under the work root takes the work-root lock: `capture`, `revise`,
`accept`, `transition`, `claim`, `record-result`, `reconcile`, `import` with `apply: true`,
`bind-namespace` and `render`. `render` takes the lock so that it does not race a write, but it does
not commit. While another holder has the lock, the command is refused with `root-busy`.

The locked commands accept `coordinator` (the name recorded as the lock owner) and `takeover` (an
object with a `reason`, to take over a lock whose owner process is gone). This holds for `capture`,
`revise` and `accept` as for the others. `bind-namespace` accepts `coordinator` only. Commands that
check payload keys (`capture`, `revise`, `accept`, `transition`, `claim`, `record-result`) do so
before the lock is taken, so an unknown key is refused without touching the lock.

Each operation commits only its own paths: the records it wrote and the generated views it changed
inside the work root. It runs `git add -- <paths>` and then `git commit -m <message> -- <paths>`,
with literal pathspecs, so a path is never read as a glob or magic pathspec. Another session's
staged or unstaged changes in the work root are not committed, and a staged change stays staged.
New records and views are part of the commit. Two kinds of path are left out: paths outside the
work root and `.state/`, and paths that Git does not track and a `.gitignore` rule ignores, because
`git add` refuses them. If every path is left out, nothing is committed and the result says so. If a
file in the set no longer holds what the operation wrote when the commit runs, nothing is committed
and the result names the file.

After a write, the runtime renders the sequence view and the task views of the items the operation
touched. A view whose text is unchanged is not rewritten. `render` still re-renders every view.

A commit that fails does not undo the write. The records and views stay on disk, and the result
carries `committed: false` and a `reason`. When Git rejects the add or the commit, or a file changed,
it also carries `paths` and `command`. This is the result when `intent.md` was edited after the
operation wrote it:

```json
{
  "committed": false,
  "reason": "these files changed after the operation wrote them, so nothing was committed; review the changed files, then run the command to commit all of the operation's files as they are now",
  "paths": ["seq-042/intent.md", "seq-042/tasks/A1.md"],
  "command": "git -C /abs/work-root --literal-pathspecs add -- seq-042/intent.md seq-042/tasks/A1.md && git -C /abs/work-root --literal-pathspecs commit -m 'session-flow: transition op-1' -- seq-042/intent.md seq-042/tasks/A1.md",
  "changed": ["seq-042/intent.md"]
}
```

`paths` and `command` cover all of the operation's files, not only the ones that changed. `command`
commits exactly `paths` and nothing else. Run it once the cause is cleared. A held `index.lock` is
retried after 0.2, 0.5 and 1 second before it is reported.

Other `reason` texts name the cause, such as `git commit failed: <first line of Git's error>`. A
work root that is not versioned, or an operation with nothing to commit, returns `committed: false`
and a `reason` without `paths` or `command`.

When the result has a `changed` key, an agent must not run `command` without review. A file was
edited after the operation wrote it, and `command` commits the files as they are now. Read the
changed files first.

A command whose handler has not landed in this build is still reachable and answers
`not-implemented` naming its handler. `doctor`'s `commands` map reports each family's handler and
whether it is available, so a consumer can check before invoking rather than after failing.

## Named errors

| Code | Meaning |
|------|---------|
| `unsupported-format` | Envelope missing, duplicated, malformed, or of an unknown format version. |
| `stale-revision` | The expected record revision does not match the stored one. |
| `root-busy` | The work root is locked by another writer or needs reconciliation. |
| `invalid-identity` | Identity, immutable field (a `revise` or `transition` edit that changes `format`, `namespace`, `seq` or `task`), illegal transition, or resolved path is not valid. |
| `missing-authority` | The requested change needs authority that was not supplied. |
| `inapplicable-evidence` | The evidence does not apply to the accepted scope revision. |
| `not-implemented` | The command family is reachable but its handler has not landed. |
| `unsupported-runtime` | The interpreter is older than the supported floor. |
| `invalid-request` | The request itself is malformed: an argument error (exit code 2), an unreadable input file, or an edit to a field only another command writes. |
| `internal` | Unexpected failure; the diagnostic on stderr carries the traceback. |

Every rejection happens before any file is written. A failed commit is not a rejection: it is a
result with `committed: false`, and the write stands. Dispatch on `error.code`, never on the message
text, which is written for a person and may be reworded.

## `doctor`

`doctor` is the one command a consumer may call before it trusts anything else. Its result carries:

- `protocol` — the integer above.
- `plugin_version` — the semantic release, for reporting only.
- `record_format` — the record format version this build reads.
- `runtime` — `python`, `minimum_python`, `executable`, `package_root`, `install_instruction`.
- `storage` — `work_root`, `work_root_present`, `sequence_path`, `commit_readiness`, and
  `limitations`.
- `commands` — per family, its handler and whether it is available.
- `errors` — the code-to-description map above.

The runtime floor is **Python 3.9 with the standard library only**. Below it, `doctor` returns
`unsupported-runtime` with an explicit install instruction rather than a traceback. Machines without
Python — chiefly native Windows outside WSL — cannot run the plugin, and that is the whole
compatibility story.

`storage.commit_readiness` reports what the runtime observes about committing, and predicts nothing
about sandboxes or approvals: `versioned`, `git_dir`, `git_dir_writable`, `hooks_path` (the
effective hooks directory, after `core.hooksPath`), and `non_executable_hooks` (hook files without
the executable bit, ignoring `*.sample`). Git skips a non-executable hook, so a commit still
succeeds, and any check the user expects from that hook silently does not run. `doctor` lists such
hooks for that reason. Only a Git directory the runtime cannot write, or an executable hook that
fails, makes a commit fail, so check `git_dir_writable` when a result says `committed: false`.

An unversioned work root appears in `storage.limitations` as a named limitation stating that backup
and restore are unavailable.

## Limitations

These are limitations of the runtime, not guarantees it makes. They were measured on 2026-09-07 on
the primary development path (`/mnt/c`, a 9p/DrvFs mount) and on native ext4; what held is stated as
holding, and what did not is stated as a limit rather than engineered around.

- **9p and DrvFs write caching can lose recently written records on a hard power loss.** Replacement
  itself is sound: 3000 concurrent reads during repeated replacement produced no torn read on either
  filesystem, and directory `fsync` and hardlink exclusivity both work on both. Durability after
  power loss on a 9p mount is what is not promised.
- **No POSIX lock coordinates with a Windows-side process editing the same files.** The root lock
  serializes participating local writers only. It cannot stop another permitted tool, or an editor
  on the Windows side, from writing into the work root.
- **Multiple replacements are not collectively atomic.** Each individual `os.replace` is atomic; a
  transition that rewrites several records is made recoverable by the operation journal, not by the
  filesystem.
- **Enforcement stops at the CLI boundary.** The runtime rejects invalid calls and detects unexpected
  revisions. It cannot constrain other permitted tools. Host permissions must constrain external
  actions; no acceptance field and no model-generated policy is a credential. `actor` is
  self-declared: the runtime does not authenticate it. `revise` and `transition` metadata patches
  refuse changes to `claim`, `result`, `corrections`, identity and acceptance fields, and only append
  to `evidence`. A hostile caller can still edit the files directly. Because `actor` is self-declared,
  the claim-holder rule and acceptance authority also assume honest actors: they stop mistakes and
  agents that skip a step, not someone who names another actor. The guarantees hold for agents that
  use the commands, not for anything that bypasses them. Evidence built by `record-result` carries
  `source: "record-result"`, a marker that agents cannot append themselves, and is the claiming
  agent's own report, not independent verification.
- **Host plugin storage is not authoritative.** Records live in the configured work root only.
  Host plugin caches and host-managed plugin data are replaceable, and a documented uninstall can
  remove the latter; never keep state there.
- **Local recovery has no external effects.** A crash leaves a reconcilable operation, never an
  instruction to repeat its effects. `reconcile` stops on unexplained divergence instead of
  overwriting it, and never performs an external side effect.

### Supported setup

Several sessions on one machine may share one work root. Every write is serialized by the root
lock, including `render`, and each operation commits only its own paths, so sessions do not commit
each other's work. A second session that finds the lock held gets `root-busy` and retries later.

### Unsupported configurations

Outside the coordination guarantee. These are documented as **unsupported** rather than defended
against, and a report from one of them is not a defect:

- Several machines using one work root.
- Network or cloud-synchronized work roots.
- Records edited outside the runtime, by hand or by another tool.
- Simultaneous editing of one work root from another operating system.
- Concurrent runtime mutations rather than serialized calls through the root lock. Independent
  sessions may share the canonical root and report their own tasks; a caller receiving `root-busy`
  must wait or follow the documented recovery path, never bypass the lock.

Linux/WSL and macOS are the tested runtimes. Native Windows is out of scope while Python is a hard
requirement.
