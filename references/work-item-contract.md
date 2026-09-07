# Work-Item Contract

The normative record format for work items and tasks: which fields exist, who owns them, how the
envelope is delimited, which lifecycle transitions are legal, and what acceptance binds to. Skills
state a rule in a line and point here; the runtime in `scripts/session_flow/` enforces what is
written below. Read this before writing a record by hand or building a consumer of one.

Generated output — the sequence view at `paths.sequence`, task indexes, portfolio renderings — is a
projection of these records. It is read-only and never an authority: a change made only in a
generated file is lost at the next `render`.

## The directory is the item

`paths.work` (default `_devdocs/work/`) holds one directory per work item, named `seq-NNN` in lower
case for identity `SEQ-NNN`.

| Path | Role | When it exists |
|------|------|----------------|
| `seq-042/intent.md` | Original request, interpreted intent, canonical metadata and scope | Always — it carries the item's identity |
| `seq-042/spec.md` | Desired behaviour and design | Only when a separate specification is useful |
| `seq-042/plan.md` | Approach and order | Only when a separate plan is useful |
| `seq-042/tasks/A1.md` | One session-sized execution unit, identity `SEQ-042/A1` | Only when work spans tasks or sessions |
| `namespace.json` | Namespace UUID, format version, repository bindings, at the root | Always — it is created with the work root |

There is **no `item.md` requirement**. For small clear work `intent.md` is the whole record: it
carries intent, the short approach, progress, and the verification result. As work grows, that file
keeps intent and the canonical lifecycle metadata and the other roles move into their own files,
linked rather than copied.

Empty optional sections and companion files are **never generated**. No command creates `spec.md`,
`plan.md`, or a `tasks/` directory to hold a placeholder, and no command writes a metadata field
whose stage the work has not reached. A field group appears when the work reaches it.

## The envelope

Each current record opens with one JSON metadata region and carries one scope region. Both are
delimited by explicit `session-flow` comments:

````markdown
<!-- session-flow:meta -->
```json
{
  "format": 1,
  "namespace": "8f14e45f-ceea-467a-9ba4-1e6f2b1c9a70",
  "seq": "SEQ-042",
  "revision": 3
}
```
<!-- /session-flow:meta -->

Ordinary Markdown prose. Never parsed as a field.

<!-- session-flow:scope -->
The acceptance-bearing intent and criteria text.
<!-- /session-flow:scope -->
````

Parsing rules, all enforced before any write:

- Only the two bounded regions are read as machine-owned content. No field is inferred from prose, a
  checkbox, a heading, or a file name.
- Exactly one opening and one closing marker per region, in that order. Zero, duplicated, or crossed
  markers are `unsupported-format`.
- The metadata region holds exactly one ` ```json ` fence and nothing else. Its content must be a
  JSON object.
- `format` must be an integer this runtime reads. An unknown version is `unsupported-format` and the
  instruction is to upgrade session-flow, never to edit the record.
- Region position is not load-bearing when reading; `render` writes the canonical order metadata,
  body, scope.
- Captured source text is escaped so it cannot open or close a region: `<!--`, `-->`, and the `&#45;`
  entity are replaced reversibly on write and restored on read. Escaping happens to the text the
  helper stores; it never rewrites what the reader sees.
- No record content is executed, in any command. Tests, Git, and delivery stay explicit harness and
  project operations.

## Field groups and owners

"Home" below means the record itself is authoritative for that group. The helper owns envelope
values and revisions; the agent owns the prose and invokes the helper.

| Field group | Owner and behaviour |
|-------------|---------------------|
| `format`, `namespace`, `seq`, `revision`, `repositories` | Helper. Identity and version. `format`, `namespace`, and `seq` are immutable; a changed record increments `revision`. |
| `title`, `lifecycle`, `priority`, `order`, `provenance` | Home. Stable sort by priority, then order, then identity. |
| `source`, `capture_id`, `original_request`, `corrections` | Home. The original request stays distinguishable from the agent's interpretation; corrections append, never overwrite. |
| Scope region, `scope_fingerprint`, `acceptance` | Home. See *Acceptance and fingerprints*. |
| `approach`, `next_action`, `decisions`, `evidence`, `links` | Home for small work; moves to `plan.md` and evidence files when they exist. |
| `parent`, `task`, `depends_on`, `allowed_paths`, `claim`, `result` | Task records. Parent counts and indexes are derived, never stored. |

### Identity

| Field | Type | Rule |
|-------|------|------|
| `format` | integer | The record format version. Current value `1`. |
| `namespace` | string | The UUID from the work root's `namespace.json`. Immutable. A record addressed under another namespace is `invalid-identity`. |
| `seq` | string | `SEQ-NNN`, three to six digits. Immutable. Retired IDs stay taken; nothing is ever reused. |
| `revision` | integer | Starts at 1. Every mutation passes the revision it expects; a mismatch is `stale-revision`. |
| `repositories` | list | Bindings, each `{"name": ..., "path": ...}`. A shared root's bindings are validated on every mutation. |
| `task` | string | Task records only. Alphanumeric segments joined by hyphens, such as `A1`. Full identity is `SEQ-042/A1`. |

### Lifecycle, ordering, and provenance

| Field | Type | Rule |
|-------|------|------|
| `title` | string | One line. Excluded from the fingerprint, so a retitle never invalidates acceptance. |
| `lifecycle` | string | One of `captured`, `accepted`, `active`, `blocked`, `done`, `deferred`, `cancelled`. |
| `priority` | string | `P1`, `P2`, or `P3`, as in [sequence-grammar.md](sequence-grammar.md). |
| `order` | integer | Tiebreaker within one priority. Ordering fields are excluded from the fingerprint. |
| `provenance` | object | `{"origin": "user"` or `"auto"`, `"actor": ..., "captured_at": ...}`. `[auto]` in a generated view maps to `origin: "auto"` — provenance, never authority. |
| `source`, `capture_id` | string | The external item this record mirrors and the intake key that deduplicates it. |

## Lifecycle states and legal transitions

Capture, acceptance, and action eligibility are three separate things. A new work item grants no
implementation permission, and neither does a linked breakdown file.

| State | Meaning |
|-------|---------|
| `captured` | Recorded and identified. Not accepted, never eligible for execution. |
| `accepted` | An authority accepted a named scope revision. Eligible to be claimed. |
| `active` | Claimed and being worked. |
| `blocked` | Work started and stopped for a recorded reason. |
| `done` | Applicable evidence covers the accepted outcome. |
| `deferred` | Retired without being done. The ID stays taken. |
| `cancelled` | Retired and not to be resumed under this identity. |

Every other transition is `invalid-identity` and fails before any write.

| From | To | Requires |
|------|----|----------|
| `captured` | `accepted` | An acceptance record: fingerprint plus authority provenance |
| `captured` | `deferred`, `cancelled` | A decision actor |
| `accepted` | `active` | A claim naming the coordinator and the expected revision |
| `accepted` | `blocked`, `deferred`, `cancelled` | A recorded reason |
| `active` | `blocked` | A recorded blocker |
| `active` | `done` | Evidence applicable to the accepted fingerprint |
| `active` | `deferred`, `cancelled` | A recorded reason; an existing claim is released |
| `blocked` | `active` | The blocker resolved and a current claim |
| `blocked` | `deferred`, `cancelled` | A recorded reason |
| `done` | `active` | A correction record naming the premature closure. Reopening keeps the same identity |
| `deferred` | `accepted` | Re-acceptance against the current fingerprint. The old acceptance is not carried forward |

`cancelled` is terminal. An incident found after valid delivery becomes linked successor work under a
new `SEQ`, not a reopening of the delivered one.

Task records use the same state names. Tasks can reach `done` while the parent still needs
integration or delivery: completing every task does not by itself move the parent to `done`, which
needs applicable evidence for the accepted outcome.

## Acceptance and fingerprints

Acceptance binds to a normalized fingerprint of what was accepted, not to a file name and not to a
revision number.

**What is fingerprinted**, in this order:

1. The scope region text, normalized.
2. The repository bindings, as `name=path` pairs sorted by name.
3. The required delivery target, or the empty string when none is required.
4. Each explicitly referenced behaviour or criteria document as `path@commit`, using its work-root
   commit, sorted by path. A mutable file name alone is not sufficient.

**What is excluded**: `title`, `lifecycle`, `priority`, `order`, `revision`, progress and next-action
fields, evidence, links, claims, and results. A status-only edit therefore retains acceptance.

**Normalization**, applied to the scope text before hashing:

- Line endings to `\n`.
- Unicode NFC.
- Markdown list markers to a single form.
- Runs of whitespace collapsed to one space; trailing spaces stripped.

Reflowing a paragraph produces the same fingerprint and does not invalidate acceptance.

The value is written with its algorithm named, `"scope_fingerprint": "sha256:<64 hex>"`, so a later
change of algorithm is detectable rather than silent.

**The acceptance record** names that fingerprint plus trusted authority provenance:

```json
"acceptance": {
  "fingerprint": "sha256:4f2c1b90a7d3e5f6082a4c1d9e7b3f5a2c8d0e1f4a6b8c9d0e2f4a6b8c9d0e1f",
  "decided_by": "maintainer",
  "authority": {"source": "_devdocs/PRD.md", "revision": "9829a5b"},
  "scope": "implement and verify; delivery needs its own authority",
  "decided_at": "2026-09-07T10:14:00Z"
}
```

Re-resolve that authority before dispatch and before any consequential effect. Revocation blocks new
dependent actions; effects already completed stay recorded, and rolling one back needs its own
authority.

**Changed scope.** A meaning-changing scope edit invalidates dependent acceptance and the
applicability of evidence gathered against the old fingerprint. The runtime detects that content
changed; it does not decide semantic equivalence. Two paths follow from that:

- `revise --same-meaning` records the actor, the authority, and both fingerprints in one step and
  keeps acceptance, without opening a review cycle. Benign re-invalidation is the common case, and
  this is its answer.
- A meaning-changing edit takes the full applicability path: acceptance is invalidated and a new
  decision is required.

Task preparation changes may proceed under accepted intent or standing authority when they preserve
the outcome, with the scope check recorded on the task.

## Worked example: a compact item

`_devdocs/work/seq-042/intent.md`, the whole record for a small clear fix. No `spec.md`, no
`plan.md`, no `tasks/`.

````markdown
<!-- session-flow:meta -->
```json
{
  "acceptance": {
    "authority": {"revision": "9829a5b", "source": "_devdocs/PRD.md"},
    "decided_at": "2026-09-07T10:14:00Z",
    "decided_by": "maintainer",
    "fingerprint": "sha256:4f2c1b90a7d3e5f6082a4c1d9e7b3f5a2c8d0e1f4a6b8c9d0e2f4a6b8c9d0e1f",
    "scope": "implement and verify; no delivery"
  },
  "evidence": [
    {"check": "python3 -B -m unittest -v tests.test_records", "criteria": "stale writes fail",
     "environment": "WSL2 ext4", "result": "pass", "revision": "62ede10"}
  ],
  "format": 1,
  "lifecycle": "done",
  "namespace": "8f14e45f-ceea-467a-9ba4-1e6f2b1c9a70",
  "order": 10,
  "priority": "P2",
  "provenance": {"actor": "maintainer", "captured_at": "2026-09-06T18:02:00Z", "origin": "user"},
  "repositories": [{"name": "session-flow", "path": "/home/m/repositories/session-flow"}],
  "revision": 4,
  "scope_fingerprint": "sha256:4f2c1b90a7d3e5f6082a4c1d9e7b3f5a2c8d0e1f4a6b8c9d0e2f4a6b8c9d0e1f",
  "seq": "SEQ-042",
  "title": "Reject a stale expected revision instead of overwriting"
}
```
<!-- /session-flow:meta -->

## Original request

> revise keeps clobbering my edits when I have two sessions open

## Interpreted intent

Two coordinators write the same record; the second write wins silently. A mutation must carry the
revision it expects and fail when the stored record has moved on.

## Approach

Compare the expected revision under the root lock, before the prepared operation is written.

## Result

`stale-revision` is raised before any write. Regression test added.

<!-- session-flow:scope -->
A mutation that names an expected revision must fail with the named stale-revision error when the
stored record carries a different revision, and must not write any file. A mutation that names no
expected revision is rejected as a malformed request rather than applied.
<!-- /session-flow:scope -->
````

## Worked example: an expanded item

`_devdocs/work/seq-043/` holds `intent.md`, `spec.md`, `plan.md`, and `tasks/A1.md`, `tasks/A2.md`.
`intent.md` keeps identity, lifecycle, and the accepted scope, and links the rest rather than
repeating it. Its metadata region alone, with the prose and the scope region omitted here:

````markdown
<!-- session-flow:meta -->
```json
{
  "format": 1,
  "lifecycle": "active",
  "links": [
    {"role": "specification", "target": "spec.md"},
    {"role": "plan", "target": "plan.md"},
    {"backend": "github", "observed_revision": "2026-09-07T09:00:00Z", "role": "mirror",
     "target": "https://github.com/o/r/issues/58"}
  ],
  "namespace": "8f14e45f-ceea-467a-9ba4-1e6f2b1c9a70",
  "priority": "P1",
  "revision": 7,
  "seq": "SEQ-043",
  "title": "Serialize local record transitions"
}
```
<!-- /session-flow:meta -->
````

`spec.md` and `plan.md` are ordinary Markdown, reached through those links. They carry no envelope,
because the runtime addresses records by identity and resolves exactly two paths per item —
`intent.md` for `SEQ-043` and `tasks/<task>.md` for `SEQ-043/A1`. Acceptance-bearing text therefore
lives in `intent.md` and in each task record, nowhere else. A task record adds the task group:

````markdown
<!-- session-flow:meta -->
```json
{
  "allowed_paths": ["scripts/session_flow/store.py", "tests/test_store.py"],
  "claim": {"coordinator": "local-1", "expected_revision": 2, "host": "wsl-dev",
            "taken_at": "2026-09-07T11:00:00Z"},
  "depends_on": ["SEQ-043/A1"],
  "format": 1,
  "lifecycle": "active",
  "namespace": "8f14e45f-ceea-467a-9ba4-1e6f2b1c9a70",
  "parent": "SEQ-043",
  "repositories": [{"name": "session-flow", "path": "/home/m/repositories/session-flow"}],
  "revision": 2,
  "scope_fingerprint": "sha256:9d1a7e4c30b8f2a5610d3c9e8b7f4a2d5c0e1f3a6b9c8d0e2f4a6b8c9d0e1f37",
  "seq": "SEQ-043",
  "task": "A2",
  "title": "Add crash reconciliation"
}
```
<!-- /session-flow:meta -->

## Task

Reconcile prepared operations on start-up: finish known partial applications, stop on unexplained
divergence.

<!-- session-flow:scope -->
Every interrupted operation either completes or remains explicitly blocked. Unexplained divergence
between a prepared operation's before-hashes and the files on disk stops reconciliation instead of
overwriting them.
<!-- /session-flow:scope -->
````

The task's `scope_fingerprint` covers its own scope region, so a parent scope edit and a task scope
edit invalidate different things. `depends_on` names full task identities; unknown prerequisites,
cycles, overlapping `allowed_paths`, a stale claim, or changed accepted parent scope stop dependent
dispatch.
