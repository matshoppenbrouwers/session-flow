---
name: session-repair
description: Transform a legacy layout into the work root, or reconcile a work root that has drifted. Surveys read-only, refuses unsafe ground, prints the per-item plan, applies only on explicit confirmation, then verifies the result entry by entry. Triggers on "/session-repair" or when user says "migrate the backlog to the work root", "the sequence and the records disagree", "reconcile the work root", or "repair session-flow state".
---

# Session Repair

Bring an existing repository into the work-root contract, or bring a drifted work root back to consistency.

Open with one sentence saying what you are about to do and what it will produce.

## Two Entry Conditions, One Code Path

- **Migrate** — a legacy layout: `_devdocs/todo/SEQUENCE.md`, per-task and phase files, old `paths` keys. Happens once.
- **Reconcile** — a current layout that has drifted: a hand-edited generated sequence, an item with no sequence row or a row with no item, an unapplied journal operation, a stale claim, a missing tombstone. Drift recurs, which is why this is a durable skill and not a one-off script.

The survey decides which, not the user's wording: a work root holding `namespace.json` and `seq-NNN/` directories is reconcile, anything else is migrate. Both run the same five stages.

## Non-Negotiables

1. **Five stages, always in this order, never skipped**: survey, refuse, plan, apply, verify. No entry condition, no user instruction, and no "it is obviously fine" shortens the list. Stages 1 to 3 write nothing.
2. **There is no `--force`.** A Stage 2 refusal is cleared by fixing the named condition and re-running, never by overriding it. Do not offer an override, and do not work around one by editing records or the sequence by hand.
3. **Plan is the default.** Stage 4 runs only after the user says apply in this session, having seen the Stage 3 plan.
4. **No ID is ever reused.** Every SEQ ever allocated is retired in `tombstones` — open, done, `[DEFERRED]`, cancelled, and identities surviving only in a historical file. Scribe mirrors address work by SEQ, so a reallocated ID silently re-targets a live GitHub issue or Notion task.
5. **Annotations are load-bearing.** ` ⇄ <url>` is the only dedup key spanning writers, so a dropped one produces a duplicate remote issue on the next mirror run; `[auto]` is the veto handle. Both survive verbatim or the run fails.
6. **Nothing external, nothing completed.** No issue is created, closed, or commented on. No item becomes `done` that was not already `done`. Lifecycle state is carried across, never inferred.
7. **Nothing is deleted.** Historical files are never moved, renamed, split, or renumbered; the new records link them where they lie. The pre-import sequence stays an ordinary Git object.
8. **Success is never declared from an exit code.** Stage 5 reads `result.verification.verified` from the response body.

## Stage 0: Resolve the Runtime

Resolve the entrypoint by the one rule for this host — `${CLAUDE_PLUGIN_ROOT}` natively, the discovered installed location under Codex, the `session-flow-runtime.json` descriptor beside this `SKILL.md` for a standalone copy (`references/runtime-integration.md`). Then read the ground:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
```

Write down `storage.work_root`, `storage.sequence_path`, `storage.namespace`, `storage.bootstrap`, `storage.versioned`, `storage.locked`, `storage.pending_operations`, and `storage.reserved`. A missing namespace with `storage.bootstrap.eligible: true` is a migration setup requirement; continue the read-only survey. A malformed namespace, or a missing namespace alongside existing records or runtime state, requires restoration of the original namespace. Never allocate a replacement identity for those records. A missing runtime or an unrelated named error means report it and stop.

## Stage 1: Survey, Read-Only

The survey is `import` in its default mode, which writes nothing. Resolve the source as `SEQUENCE.md` under configured `paths.todo`, falling back to `_devdocs/todo/SEQUENCE.md`. Omit `historical` to use configured `paths.todo` and `paths.tasks`; when neither is configured, explicitly name the existing legacy directories. Do not replace configured historical paths with hardcoded examples. Pass the resolved source in the payload:

```json
{"source": "_devdocs/todo/SEQUENCE.md"}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" \
  import --input "$PAYLOAD"
```

The survey uses an existing namespace when present. Without one, item metadata has no namespace and `items[].text` is null; these are previews, never records to write. Save `result.survey_fingerprint` with the approved plan. A source that equals the generated output path is refused: correct `paths.sequence` before retrying. Read the response and report, in the session:

- every SEQ the survey saw — `result.items` for the live rows, `result.tombstones` for the full set, where `state: "historical"` marks an identity surviving only in a pre-import file;
- every ` ⇄ <url>` annotation and every `[auto]` marker, per item, as they were found;
- every breakdown link and phase anchor, and which of them resolve — `result.unresolved_links` names the ones that do not;
- the configured paths the run resolved: work root, sequence, and each historical root actually scanned;
- `result.unclassified`: the lines the survey cannot classify, with their line numbers and text.

Report what was found and what could not be classified. Mutate nothing here, including a `render`.

## Stage 2: Refuse Unsafe Ground

Stop before any write when any condition below holds. Name the exact condition and the command that clears it, then stop — the user re-runs `/session-repair` after clearing it.

| Condition | Detected by | Clear it with |
|---|---|---|
| An existing record store has no Git history | `storage.versioned` is `false` and `storage.bootstrap.eligible` is not `true` | `git -C "$WORK_ROOT" init -b main`, then commit the current records |
| The project tree has uncommitted changes | `git -C "$PROJECT_ROOT" status --porcelain`, excluding the work root and the generated sequence | Commit or stash them: `git -C "$PROJECT_ROOT" status` |
| An existing versioned work root has uncommitted changes | `git -C "$WORK_ROOT" status --porcelain`, excluding `.state/`; skip this command while the root is absent | Commit or stash them: `git -C "$WORK_ROOT" status` |
| A prior repair operation sits unapplied in the journal | `storage.pending_operations` is non-empty | `python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" reconcile` |
| Another coordinator holds the lock | `storage.locked` is `true`, or a `root-busy` error | Wait for that coordinator, or once `error.detail.liveness` reports its process gone, run `reconcile` and take the lock over explicitly with `takeover` in the payload |
| The survey found a shape it cannot classify | `result.unclassified` is non-empty | Rewrite those lines to the grammar in `references/sequence-grammar.md` |
| An entry links a file that is not there | `result.unresolved_links` is non-empty | Restore or correct each named target |
| Two rows claim one identity | `invalid-identity` naming both line numbers | Resolve the duplicate in the source before importing |

The runtime refuses the same ground again at apply time. That is a backstop, not the check: refusing here is what keeps Stage 3 read-only.

For an absent or empty work root, Git setup belongs in the plan. Inspect the nearest existing ancestor to locate enclosing Git history, and use `git check-ignore` from that repository to check the planned work-root path without creating it. Reuse enclosing history when it covers that path. Otherwise plan `git init -b main` inside the work root, preserving all existing ignore rules and creating no remote. Verify Git is available and a commit identity is configured before setup; for a new nested repository, check the identity it will actually inherit, not only the outer repository's local configuration. Never invent a Git identity. Unrelated project changes still refuse setup.

An empty directory containing only Git metadata is eligible. Other unexplained contents, including journals or reservations without a namespace, require recovery. A valid existing namespace is always preserved; committed setup from an interrupted run can proceed directly to import. Uncommitted partial setup must be reviewed and committed or stashed explicitly before retrying, never silently included in a new setup commit.

## Stage 3: Plan, the Default

Print the per-item transformation from the Stage 1 response, one line per item:

- which SEQ becomes which directory (`result.items[].path`), and its carried lifecycle, priority, and title;
- which historical files that record links, where they lie;
- which annotations and markers carry across, verbatim;
- which IDs become tombstones, split into `imported` and `historical`.

Then state the totals: items to write, identities to retire, and files to be moved - always zero. Include any directory/Git setup, the repository that will hold history, and namespace creation with the current repository binding. Derive the binding name from the project directory name and its path relative to the work root; preserve existing bindings and escalate name conflicts. First-time setup produces a setup commit before the import commit. Write nothing in this stage and ask for explicit confirmation covering both setup and import. If the user does not confirm, stop here and say the plan was not applied.

## Stage 4: Apply

Re-run doctor, the survey, and Stage 2 checks before writing. The fingerprint and planned paths must match the approved plan; otherwise stop for review. For approved setup only:

1. Create the work directory if absent, then perform the planned local Git initialization if needed. Check every command's result; stop on failure.
2. Call `bind-namespace` through the resolved runtime with `{"repository": {"name": "<project directory name>", "path": "<project path relative to work root>"}, "coordinator": "session-repair"}` in a JSON input file. This creates the UUID, binding and local-state ignore rule and commits setup. Never hand-write `namespace.json`.
3. Require `result.commit.committed: true` for changed setup, record its commit ID, then require doctor to report the returned namespace and a versioned root. Check the project and work root are clean. A failed commit stops before import; report any partial setup for explicit recovery. A retry after successful setup reuses the namespace and commit.
4. Re-run the survey using the bound namespace and compare its fingerprint with the approved one. Namespace creation does not change the fingerprint. Changed source content or discovered identities requires a new plan, even if setup already committed.

Do not call render during setup. Now run one `import` operation under the root lock, through the existing prepared-operation journal, ending in the import commit. Reuse the Stage 1 payload and add the operation identity, the approved fingerprint and the confirmation:

```json
{"operation": "repair-<short unique id>", "coordinator": "session-repair", "apply": true,
 "source": "_devdocs/todo/SEQUENCE.md", "expected_survey_fingerprint": "<approved fingerprint>"}
```

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" --namespace "$NAMESPACE" \
  import --input "$PAYLOAD"
```

- A second run over the same source finds nothing to do and reports `changed: false` with the reason. That is the expected result of running twice, not a failure.
- An interrupted run resumes from the journal: re-send the **same** `operation` id with the same payload and the runtime finishes the prepared operation rather than planning it again. A different payload under that id is refused — issue a new operation id instead.
- `invalid-identity` naming a stored record that differs means import will not overwrite it. Escalate with both versions; do not delete either.

## Stage 5: Verify, or Fail

`import --apply` re-derives the sequence from the stored records and compares it against the source entry by entry: every ID present, in the same order, every annotation and marker intact, every link resolving. Read `result.verification.verified` and report the entry count it compared.

On a mismatch the run fails with `invalid-identity`, and `error.detail.mismatch` names the first difference and `error.detail.commit` the commit to revert:

```bash
git -C "$WORK_ROOT" revert <commit>
```

Report the mismatch, the revert command, and stop. Never report an import as successful because the process exited, and never re-run apply over a failed verification.

## Reconcile Mode

Same five stages. The differences are what the survey reads and what may be repaired.

Stage 1 additionally compares the generated sequence at `storage.sequence_path` with the records under the work root, runs `select` to read each item's eligibility reasons, and reads `storage.reserved` and the `tombstones` index. Report each drift as one of two classes.

**Unambiguous — repairable in Stage 4:**

| Drift | Repair |
|---|---|
| A derived view disagrees with the records (a hand-edited sequence, an item with no row) | `render` |
| A journal entry is half-applied | `reconcile`, which finishes known partial applications and stops on unexplained divergence |
| An identity is missing from `tombstones` | Re-run the same `import` over the same source: only the allocation-index write is planned, and any stored record that differs refuses instead |

**Needs judgement — escalate, never correct:**

- Two records claiming one identity.
- A hand-edit to generated output carrying information the items do not: Stage 2 guarantees a committed tree, so after Stage 4 `git -C "$PROJECT_ROOT" diff -- "$SEQUENCE_PATH"` shows both versions exactly. Show both and let the user decide what belongs on the record.
- A row with no item, a stale claim held by another actor, or a reserved identity whose record was never written.

Report drift; do not silently correct it. For each escalation show both versions and name what a decision would change. A stale claim is reassigned only when the user says so, through `claim` with `takeover_claim` — not here.

## Report

1. The entry condition the survey decided, and why.
2. What the survey found: identities, annotations, markers, links, and anything unclassifiable.
3. Whether Stage 2 refused, which condition, and the command that clears it.
4. What was applied, the setup commit when needed, the import commit, and the verification result with its entry count. Report a local root without a remote as having local history only.
5. What was escalated and still stands unrepaired.

Chain context: see `references/workflow-overview.md`.
