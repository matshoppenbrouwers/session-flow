# Changelog

## Unreleased

### Fixed

- `/session-repair` can survey a legacy backlog without a work root or namespace. Approved migration
  now includes Git and namespace setup before the existing import transaction, with separate commits.
  Ignored work roots retain their ignore rules and use local Git history without creating a remote.
- Import rejects a conflicting namespace, a source that is also the generated output, and changes
  to a supplied approved survey fingerprint. Missing namespaces beside existing state require recovery.
- Added migration coverage starting without a namespace; the previous legacy fixture already had one.

## 2.0.0 (2026-09-08)

Work items, their state, and the sequence are now owned by a local runtime instead of by
hand-edited Markdown. That breaks every existing installation: the plugin needs a Python
interpreter, the configuration keys change, and `SEQUENCE.md` stops being a file you edit.
`/session-repair` is the only supported way from an existing repository into the new layout.
Run it before anything else.

### Breaking

- **Python 3.9+ is a hard prerequisite.** Every record read or written goes through
  `scripts/session-flow.py`; there is no hand-editing path beside it and no legacy mode to fall
  back to. Without an interpreter the plugin does not run — `doctor` fails with an install
  instruction rather than a traceback. Machines without Python, chiefly native Windows outside
  WSL, cannot run this release.
- **`paths.work` is new.** `.session-flow.json` gains a work root, `_devdocs/work/` by default.
  One work item is one directory under it, holding `intent.md` and, when the work warrants them,
  `spec.md`, `plan.md`, and `tasks/`. `namespace.json` at the root carries the namespace identity
  and its repository bindings, so several repositories can share one root.
- **`paths.sequence` moves to `_devdocs/SEQUENCE.md`.** It used to live inside `_devdocs/todo/`,
  which is now an archive; leaving the live sequence there would misdescribe both.
- **`SEQUENCE.md` is generated output.** It is rendered from the work items and must not be
  hand-edited. An edit changes no record and the next render drops it. `/session-repair` in
  reconcile mode reports a hand-edited sequence as drift instead of silently overwriting it.
- **The legacy execution path is removed, not deprecated.** There is no dual-format mutation
  path, no mixed-version negotiation, and no rollback to the old layout. The plugin had no
  active installed users to preserve one for.
- **`_devdocs/todo/` is a pre-import archive.** Historical phase and task files keep their names
  and stay where they are; import links them where they lie rather than moving, renaming, or
  renumbering them. Nothing new is written there, and `/session-init` no longer creates the
  directory.

### Upgrading

`/session-repair` is the only supported path from an existing repository into the work-root
contract, and it is the sixteenth skill in the package. It runs five stages in order: survey
read-only, refuse unsafe ground, plan, apply, verify.

Planning is the default. The plan prints the per-item transformation — which SEQ becomes which
directory, which files are linked, which IDs become tombstones, which annotations carry across —
and writes nothing. Applying takes explicit confirmation. Repair refuses to write at all when the
work root is not a Git repository, when the project tree or work root has uncommitted changes,
when a prior operation sits unapplied in the journal, when another coordinator holds the lock, or
when the survey found a shape it cannot classify. Each refusal names the condition and the
command that clears it. There is no `--force`.

Apply is one journalled operation under the root lock, ending in a single commit. Every SEQ ever
seen is retired in `tombstones`, including identities surviving only in an archived file, so no
ID is ever reused against a live scribe mirror. The ` ⇄ <url>` annotations and `[auto]` markers
carry across verbatim. Nothing is deleted, nothing external is created, and nothing becomes done
that was not already done. The run then re-derives the sequence from the stored records and
compares it entry by entry against the original; any mismatch fails the run and leaves a commit
to revert. Success is never declared from an exit code. A second run is a no-op, and an
interrupted run resumes from the journal.

The same skill's second entry condition is reconciliation: a current layout that has drifted — a
hand-edited sequence, an item with no row or a row with no item, an unapplied operation, a stale
claim, a missing tombstone. It repairs only what is unambiguous and escalates anything needing
judgement with both versions shown. Migration happens once; drift recurs, which is why this is a
skill and not a one-off script.

### Added

- **A local transition runtime.** `scripts/session-flow.py` and the `session_flow` package
  provide `doctor`, `show`, `capture`, `revise`, `accept`, `select`, `claim`, `record-result`,
  `transition`, `render`, `import`, `reconcile`, and `backup`/`restore`. Identity is immutable,
  scope is bound by a normalized fingerprint with an explicit `--same-meaning` decision for
  reflows, the root lock is an exclusive directory creation, IDs are reserved against tombstones,
  and every mutation is a journalled prepared operation with idempotent retry and atomic replace
  writes. Reconciliation finishes a known partial application and stops on unexplained divergence
  rather than overwriting it. History is Git's: an applied transition ends in a commit, restore is
  a checkout, backup is a push. `doctor` reports an integer protocol version, which is what the
  companion plugins check rather than the release number.
- **Bounded dispatch and truthful completion.** `/session-next` selects, claims, and works one
  bounded unit; `/session-delegation` dispatches exactly the named task IDs plus their permitted
  prerequisite closure and stops before dispatch on a missing or ambiguous ID, an unknown
  prerequisite, a cycle, an overlapping write scope, a stale claim, or changed accepted scope.
  `/session-verify` targets the accepted scope by fingerprint and work-root commit. A parent whose
  tasks all pass but whose required delivery is unmerged is not reported as complete, and stale
  evidence or an unknown outcome does not authorize completion. Most of those refusals are the
  runtime's rather than the skills': `claim` refuses an unknown, cyclic, or unfinished prerequisite
  and a write scope overlapping another actor's live claim, and `done` is refused while evidence is
  inapplicable, a required delivery has no receipt, or a task is still open. A claim on an identity
  with no record is refused too. An ambiguous ID, a stale claim, and changed accepted scope stay
  skill-level judgements. See **Where enforcement lives** below for the boundary.
- **The work-root versioning question.** `/session-init` asks once whether the work root is
  tracked in the repository or gets its own private repository, and acts on the answer, including
  running the private-repository setup. The answer decides a capability and not only privacy: a
  hosted ops job can read only committed files, so ignoring the work root keeps execution local.
  Declining every option is allowed; `doctor` then reports the unversioned root as a limitation.
- **A test suite.** `python3 -B -m unittest discover -s tests -v` covers the records, store,
  views, dispatch scope, installation, repair, scenario, continuation, and release-metadata
  checks. The project had
  no test command before this release. It does not exercise host invocation.

### Continuation

Continuation over several units is off unless something outside the run authorizes it: an
invocation naming the further units, or a `continuation` policy in `.session-flow.json` naming
authority, capacity, scope, and stop conditions. A block missing a key, or naming a stop
condition the skill does not define, authorizes nothing. Authority is re-resolved before every
dispatch. A unit already claimed finishes and records its result even when the policy is
withdrawn mid-run — revocation blocks the next dispatch, it does not erase an effect that already
happened. Six named stops say why a run ended. A bounded request from ops is a candidate, not an
assignment: with no standing policy covering that identity it starts nothing.

That limit is prose-enforced, not code-enforced. The capacity and stop-condition checks live in
`skills/session-next/SKILL.md` prose, and `tests/test_continuation.py` verifies that the text says
the right thing and that a runner following it stops where the scenario expects. Nothing in the
runtime blocks an agent that reads the instruction and keeps going anyway.

### Where enforcement lives

Continuation is not the only thing enforced in prose, and a pre-release hand-check found the
boundary wider than the design text implied. Most of it has since been moved into the runtime. Read
this before relying on any guarantee in the two sections above.

**The runtime enforces record integrity.** Identity allocation against the tombstone index, the
exclusive root lock, expected-revision checks, atomic writes, the prepared-operation journal and
its idempotent replay, scope fingerprints, and the round-trip comparison in `import` are all real,
tested, and hold against a caller that ignores every instruction.

**The runtime also enforces work governance, on the records it mutates.** These refusals happen
before any write, and hold against a caller driving `scripts/session-flow.py` directly:

- A lifecycle change outside the legal transition table is refused, on every planned change and not
  only on `revise` and `accept`. Reopening still needs its recorded correction.
- A lifecycle change from an actor that does not hold the record's claim is refused, and an
  unclaimed record cannot change lifecycle at all. `captured → accepted`, which precedes any claim,
  is the one exemption.
- `done` is refused while an evidence entry belongs to a fingerprint the record no longer carries,
  while a required delivery has no receipt, or while the item owns a task that is neither `done` nor
  `cancelled`. Each refusal names the clause and what would satisfy it.
- `claim` is refused when the record's `depends_on` names an identity with no record, closes on
  itself in a cycle, or names work that is not `done` — over the whole transitive closure, not the
  direct entries, bounded at 64 records deep. Only `done` satisfies a prerequisite; `cancelled` does
  not.
- `claim` is refused when its `allowed_paths` overlap those of a live claim held by another actor.
- A delivery receipt is outside the scope fingerprint by construction, so recording a delivery
  cannot invalidate the acceptance that required it.

**One boundary does not close.** `allowed_paths` guarantees that the live claims of two different
actors do not overlap. It does not guarantee that an agent writes only where it said it would: the
runtime never sees an agent's file writes, so an accepted claim bounds the assignment and not the
behaviour. Confining a process to a path is the harness's job, not this runtime's, and no wording
of the field changes that.

`revise` and `accept` use the same claim-ownership guard as planned transitions. Initial
acceptance and edits that leave lifecycle unchanged need no claim. The continuation limit
remains in the skills, as the section above says.

Work-root commits exclude `.state`, including the lock held during the commit. Binding a
versioned root adds `/.state/` to its `.gitignore`, preserving existing rules, so local journals
also stay out of Git status after the lock is released.

None of this compromises the record store — nothing here can corrupt a record, lose an identity, or
produce an unrecoverable work root.

### Fixed

- **A complete standalone install.** `install.sh` copies each skill's whole resource tree plus the
  shared `references/` tree and `THIRD_PARTY_NOTICES.md`, and activates an entry file only once
  its declared resources verify present. The nested `skills/security-liability-audit/references/`
  and `skills/session-debug/references/` trees were being dropped.
- **Bounded phase dispatch.** A phase anchor used to stand in for a whole task file, so a request
  for one task could run its siblings. Selection now carries one explicit target scope, and a
  completion marker states which tasks it covers.
- **Scoped refinement commits.** `/session-post-implementation`'s two `git add -A` checkpoints
  became an ownership snapshot taken before the first change and an explicit staged-path list.
  Unrelated modified, staged, or untracked files cannot enter a flow commit; the skill stops and
  names them.
- **Resolved audit selection.** The step list resolves once at configuration time, so a selected
  audit add-on runs under Standard and Quick scope instead of being skipped by a second gate.
- **Evidence freshness at release.** `/session-release` compares the verification report's
  recorded commit range against the release candidate revision and releases on older evidence only
  through a recorded reuse-or-rerun decision.
- **Installed packages are verified.** The core fixtures now run under the source, native-plugin,
  and standalone layouts through both invocation routes, with spaced paths, upgrade and uninstall
  survival of the work root, and a restore into an empty root. An interpreter that is missing or
  too old reports as an interpreter problem with an install instruction, not as an incomplete
  package.
- **Stale guidance.** `references/workflow-overview.md` described save gates and sequential
  research dispatch that the skills do not do, `references/customization-guide.md` counted three
  bundled agents where the manifest registers six, and `CONTRIBUTING.md` still required a retired
  Announce marker.

### Notes

- **No measured improvement in maintainer effort is claimed.** No baseline of the previous system
  was captured, by decision, so no reduction can be demonstrated. What this release claims is that
  the designed behaviour is present and correct. Several of its acceptance criteria are
  hand-checked by the maintainer rather than asserted by a test, and are labelled that way in the
  phase files.
- Supported and measured on Linux/WSL and macOS. Native Windows is out of scope while Python is a
  hard prerequisite. A network or cloud-synchronized work root, simultaneous editing from another
  operating system, and mutation from more than one host are outside the coordination guarantee
  and are unsupported rather than defended against.
- session-scribe and session-ops carry their own halves of this work and release on their own
  version numbers. Nothing from those repositories ships in this package.

## 1.7.1 (2026-09-05)

Finishes what 1.7.0 started. The confidence rewrite reached the lines the plan named and left
three numeric gates standing in the security audit chain, including one that still told the
reporter to withhold.

### Fixed

- **The last withholding gate.** `references/technical-security.md` defined severity in confidence
  numbers and closed with "Below 7: Do not report", which is the behaviour 1.7.0 removed
  everywhere else. Severity is now defined by what a finding costs if it is real, confidence is
  stated as the separate axis it is, and nothing is dropped for being uncertain.
- **`security-auditor` groups by severity, not by a score.** Its High and Medium sections keyed off
  "8/10+ confidence" and "lower-confidence", so the agent labelled findings one way and sorted them
  another. Its per-finding output now carries the confidence label it is told to apply.
- **The audit skill's output table** showed a `Conf` column of `9/10` and `8/10` against a rule
  asking for high, medium or low. It shows labels.
- The `TENTATIVE` finding status no longer keys off a confidence number, and the two headings that
  still read "Confidence Filtering" now say what they do.

## 1.7.0 (2026-09-05)

Aligns the skill and agent text with current Claude prompting guidance, adds two conversational
skills, and lets several repos share one backlog.

### Added

- **`/session-brainstorm`.** A design conversation for an idea that is not yet a task. It
  classifies the request as a spike, a bounded change, or an architectural one; asks one question
  at a time; presents options with a recommendation; and gets an explicit yes on a short design
  before anything is built. Bounded work is implemented or captured with `/session-add-task`;
  architectural work hands to `/session-research-design`.
- **`/session-debug`.** A four-phase debugging discipline: investigate, compare, hypothesise,
  fix. One hypothesis and one change at a time; after three failed fixes it stops and questions
  the design. Ships with a root-cause-tracing reference.
  Both skills are derived from superpowers by Jesse Vincent (MIT); see `THIRD_PARTY_NOTICES.md`.
- **Shared backlogs.** `.session-flow.json` paths may point outside the repo, so several repos in
  one parent folder can share a `SEQUENCE.md`. `/session-init` asks; every path-resolving skill
  honours it; `/session-status` says which file it read.
- **`references/sequence-grammar.md`.** The entry-line grammar and the cross-writer contract in
  one place. The skills keep the rules and point here for the reasoning.

### Changed

- **Reporters report; callers filter.** `code-reviewer`, `security-auditor` and the security
  audit skill label every finding high, medium or low confidence instead of withholding below a
  threshold. Callers act on high and medium and list the rest. Current models follow "be
  conservative" literally and under-report. `code-simplifier`'s duplication heuristic now reads
  "substantially identical" rather than a percentage, so it is not mistaken for a confidence gate.
- **Sanitize folded into simplify.** `code-simplifier` now also removes dead code, temporary
  helpers and debug output; `code-sanitizer` is gone and post-implementation has one step fewer.
  Two agents were hunting the same leftovers. The security vocabulary for unsanitized input and
  missing sanitization stays where it belongs, in the reviewer and the audit references.
- **Test framing.** Delegation keeps its independent test oracle and drops the test-first
  language: the oracle exists so a different agent writes the test, not because design happens
  through tests. `test-author` writes one test per Accept criterion plus boundaries the design
  names. `/session-next` implements, then adds the regression test, deferring to the project's
  own testing rule.
- **Skip rule.** The overview no longer says "when in doubt, run it".
- **Openers.** Skills ask for one sentence of your own on what is about to happen, in place of a
  canned announce line.
- **Shorter add-task, gatekeeper and groom.** Rationale moved to the grammar reference.

### Removed

- The dead `/quick-post-implementation` reference. The "Quick" scope option covers it.

## 1.6.0 (2026-08-14)

1.5.0 taught session-flow to **write** the ` ⇄ <url>` provenance key; this release teaches it to **read** it first. A key only one side checks is not a dedup key — it is a label. Closes conflicts C1, C2 and C5 of the three-plugin alignment review, which measured the drift across the three plugins that parse `SEQUENCE.md`.

### Added

- **Dedup on enqueue.** `/session-add-task` scans `SEQUENCE.md` for the caller's source URL among existing ` ⇄ ` annotations *before* allocating an id: on a hit it stops, names the existing `SEQ-NNN`, and appends nothing. `/session-gatekeeper` runs the same grep before handing an item off, recording a hit as already-enqueued in the run record. This is the exclusion `/scribe-pull` already ran from the other side; run from both, the key is symmetric.
  Two double-intake paths are the reason it exists: a reopened, previously-imported issue re-triaging in CI (ops-triage skips only `scribe:mirror` and `ops-dashboard`, not `scribe:imported`), and a `scribe:ready` issue that triage *escalates* — still a `/scribe-pull` candidate, so the import files it and a later dashboard box-tick enqueues the same work again.
- **A no-title-matching anti-pattern in both skills.** Triage rewrites raw issue titles into task phrasing, so an entry's title never matches its source's — while near-matches across unrelated entries do. The URL is the only key.
- **`[DEFERRED]` is in the grammar.** It joins `/session-add-task`'s marker table, and the id rule now scans every line carrying a `SEQ` id — `[ ]`, `[x]`, and `[DEFERRED]` alike. The highest id ever used is the floor, not the highest open one; `README.md` and session-scribe already worked this way, no session-flow skill said so.
- **Id allocation's concurrency discipline is written down** in `/session-add-task`'s Provenance section and `README.md`. Four writers append with no locking: safety is at most one scheduled writer per repo, and pulling before any local edit. Both halves are load-bearing — a second bot writer, or an append to a stale local copy, reintroduces a collision no code catches.
- **`/session-init`'s starter legend covers the whole grammar** — `[DEFERRED]`, `[auto]`, and ` ⇄ <url>` alongside the checkbox states — so a new project's in-file legend matches what siblings parse.
- **A stated enqueue priority:** everything `/session-gatekeeper` enqueues is P3. Triage established that work is aligned and trivial, not that it is urgent; anything higher is a claim only the user can make. Priorities are never carried through from an issue label.

### Changed

- **`/session-groom` records escalation below the entry, not on it.** The entry line is left untouched and the escalation goes on its own HTML comment line: `<!-- session-flow: SEQ-NNN escalated to research-design YYYY-MM-DD -->`. The old `(needs research-design)` trailing tag collided with the one-trailing-token grammar session-scribe parses by — a second, unknown tag blocks its strip and hides the ` ⇄ ` annotations behind it, defeating the very key this release hardens. Comment lines are invisible to all three parsers, and `/scribe-pull` already writes its divergence markers the same way.
- **Groom skips entries carrying an escalation comment.** They are waiting on a `/session-research-design` session; re-researching them every pass broke idempotence.

### Notes

- The entry-line marker table in `/session-add-task` is now the whole grammar — every token any shipped writer emits — and states the rule the others were only implying: an entry ends in **exactly one** trailing status token (` → <link>` *or* `(needs breakdown)`), and anything that doesn't fit goes below it as an HTML comment.
- Still convention, not code. No plugin imports another's parser; the contract is documented on both sides and each works standalone.

## 1.5.0 (2026-08-14)

Closes the duplicate-entry hole that opens as soon as session-flow is not the only thing writing to `SEQUENCE.md`. 1.4.0 taught the gatekeeper to enqueue from an issue tracker; this release makes those entries recognisable to the other writers, so the same issue cannot be filed twice under two ids.

### Added

- **` ⇄ <url>` provenance annotation.** `/session-add-task` takes an optional source URL and renders it immediately before the entry's trailing status token — before the ` → ` link, or before `(needs breakdown)` in mode C. The position is load-bearing in both directions: after the link it breaks path readers, after the token it is invisible to annotation readers.
- `/session-gatekeeper` passes the item's source URL on every enqueue, alongside the `[auto]` flag and the reason. No URL means `[auto]` alone — it never invents one.
- `/session-groom` preserves annotations when it swaps `(needs breakdown)` for the breakdown link. It rewrites exactly that region, so a dropped annotation would have been silent.

`[auto]` and ` ⇄ ` are independent markers answering different questions: who put the entry in the file, and where the work came from. A gatekeeper enqueue from a GitHub issue carries both.

### Notes

- **Why a title is not a fallback.** session-scribe's `/scribe-pull` dedups imports by excluding candidates whose URL already appears as a ` ⇄ ` annotation. An entry enqueued in CI without one leaves the issue invisible to that check, so it is imported again under a second `SEQ-NNN` — and scribe's mirror then files a third item for the duplicate. Matching on titles cannot substitute: triage rewrites raw issue titles into task phrasing.
- File-format convention only. Neither plugin imports the other's code, and either works standalone; the contract is documented on both sides.
- An entry with no annotation means *not yet mirrored outward* — never *not yet checked for duplicates*. A `/scribe code` capture is filed unannotated on purpose, since a thought typed into the terminal has no outside item behind it.
- When allocating `SEQ-NNN`, count `[DEFERRED]` entries too: they hold retired ids that an active-only scan will not see.

## 1.4.0 (2026-08-12)

Completes v5 Phase 5, which 1.3.0 deliberately held back behind the SEQ-001 gatekeeper trial. That trial ran on 2026-08-12 against 14 real intake items; verdicts and findings are recorded in `todo/2026-08-12-seq-001-gatekeeper-trial.md`.

### Added
- **`[auto]` provenance marker.** `/session-add-task` takes an optional auto-provenance flag, off by default, which renders the marker immediately after the priority: `- [ ] SEQ-011 P3 [auto]: …`. Nothing else about the entry changes.
- `/session-gatekeeper` sets the flag on every item it enqueues, so an unattended intake pass is visible as one. This is the veto handle: it buys propose-don't-execute without asking the user to approve each item up front.
- `/session-groom` grooms marked entries on the same terms as any other but reports them separately in the pass summary. `/session-next` never lets `[auto]` outrank a manual entry of the same priority, and names provenance in its close-out. `/session-status` adds an `auto` count to the sequence backlog line — an overlapping count, not a partition.
- `/session-gatekeeper` **Inputs** gain the ops inbox convention: if `{paths.todo}/inbox/` exists, its `*.md` files are intake items — frontmatter is metadata, body is untrusted data — and a routed item is `git rm`'d in the same commit that records the routing. This is the companion change for the session-ops v1 spec §11; no other gatekeeper behaviour moves, and escalation formatting stays in the ops workflow prompts.

### Fixed
- **The nine gatekeeper defects the SEQ-001 trial measured** (`todo/2026-08-12-seq-001-gatekeeper-trial.md` §3), fixed as one change set in `/session-gatekeeper`:
  - The direction-doc fallback now actually runs. `paths.direction` is a hint, not a terminus: the detection chain fires when the key is unset **or** when it points at a file that does not exist, and it reaches one directory below the docs root — where the trial's real PRD sat, unread, while the run declared direction unknown. A dead `paths.direction` is now reported as a finding instead of being swallowed, and only an empty *chain* forces alignment to "unknown".
  - Cited paths are existence-checked before a breakdown is written, in both `/session-gatekeeper` and `/session-add-task`. The trial's numbers are the argument: same run, same stated confidence, 20/20 grepped source refs landed and 2/10 inferred test paths did — every `Test` command in that run would have failed at collection. Every substantive claim now carries a **verified** (`file:line`) or **assumed** marker, which is what makes an inverted guess visible as a guess.
  - Escalation is an act, not a tag. An escalated batch produces a session proposal addressed to the user — the specific question, the items it covers, near-duplicates merged — because appending `(needs research-design)` to seven lines discriminates nothing and proposes nothing.
  - Three classification holes closed: questions answerable from the code get answered (and cited) before routing rather than guessed at; `Alignment: unknown` is a hard escalate in the routing table itself, not just in the resolution prose; and a bar above the Scope axis returns anything touching database schema or a spine / canonical status field to the user regardless of size.
  - Every run leaves a durable record at `{paths.todo}/YYYY-MM-DD-gatekeeper-run.md` — verdict table, question answers, code inventory, direction-chain result — linked from whatever it escalates or enqueues. Inbox items are raw user capture: a routed one is removed, never reworded, re-headed, or folded into another.

### Notes
- `[auto]` changes the `SEQUENCE.md` line format that **session-scribe** parses by convention rather than by shared code. Both `session-add-task` and `session-gatekeeper` carry the caveat in-body: verify scribe's parser against a marked line before trusting the Notion mirror. session-scribe itself needs no changes.
- The gatekeeper fixes above are SEQ-008, broken down in `todo/2026-08-12-seq-008-gatekeeper-defects.md`. `/session-groom` and `/session-task-planning` were deliberately left out of scope: they write breakdowns too, so the path-existence rule likely belongs there as well, but that is a separate entry rather than a quiet widening of this one.

## 1.3.0 (2026-08-09)

Implements the v5 spec (`plans/2026-08-09-session-flow-v5-spec.md`): four verified defect fixes, three new agents with the workflows rewired around them, the Files field as a write boundary, conventions/lessons config, and a prescriptiveness trim across skills and agents. No breaking changes — existing artifacts, formats, and scripts keep working.

### Added
- **codebase-researcher** agent — answers one specific question about an existing codebase with `file:line` citations, explicit "not found" when it isn't there, and no recommendations. `tools: Read, Grep, Glob`, pinned to `model: sonnet` (a deliberate exception to the inherit-by-default policy, documented in the agent file).
- **external-researcher** agent — researches docs, specs, and prior art outside the repo with source-validation discipline: primary sources, publication dates, vendor claims flagged, conflicts presented rather than resolved. `tools: WebSearch, WebFetch` — no `Read`, so it cannot see the repository at all. Also pinned to `model: sonnet`.
- **test-author** agent — writes a phase's acceptance tests from the design artifact, public interface, and each task's Accept criterion **before** the implementers run, so the tests act as an external oracle rather than a post-hoc rationalization. `model: inherit`.
- `/session-delegation` dispatches `test-author` once per phase before that phase's implementers and records the produced test paths per task. Implementer prompts now say the pre-authored tests are the acceptance oracle: make them pass, never modify a test file, and stop and report if a test looks wrong. Documents the red-phase caveat — oracle tests may not collect until dependency tasks land, which is expected, not a blocking failure.
- Every delegation dispatch carries the task's **Files** field as a write boundary ("only create or modify these paths; anything else, stop and report"). It is a scoping constraint, not a security boundary. `session-task-planning`, `session-add-task`, and `session-groom` document that Files entries may be exact paths or directory globs (`src/lib/governor/**`).
- `.session-flow.json` gains optional `paths.conventions` and `paths.lessons`, defaulting to `{root}/conventions.md` and `{root}/lessons.md`. Both use one-line `rule — reason` entries (~140 chars, reason mandatory). `/session-init` offers — never forces — to scaffold `conventions.md` with the format note and no invented rules.
- `/session-research-design` reads conventions and lessons at design time and `code-reviewer` enforces conventions alongside `CLAUDE.md`. When a key is unset or the file is missing, both say so and fall back to `CLAUDE.md` plus observed patterns rather than inventing a house style. Convention departures are flagged with reasons, never blocked.
- `/session-delegation` includes the conventions file in implementer payloads when it exists, and reads lessons as a one-line index.
- README documents the seven bundled agents, the researcher model pins, the conventions/lessons schema, the Files-glob write boundary, and recommends **claude-mem** for cross-session recall — with the caveat that claude-mem and session-scribe each register a `SessionEnd` hook, so test the two together before relying on either.

### Changed
- `/session-research-design` Step 2 dispatches `codebase-researcher` and `external-researcher` (in parallel where both apply) instead of the previous ad-hoc Explore-agent prompts, and may re-dispatch `codebase-researcher` for targeted lookups mid-design.
- Research is now skippable given a recent research artifact or user-stated understanding; the plan's Context section then names what it relied on. Framing is never skipped.
- **Prescriptiveness trim**, one commit per category so anything load-bearing can be bisected back:
  - The repeated "Workflow Integration" chain diagram is gone from all 13 skills, replaced by a single pointer to `references/workflow-overview.md`. It was loaded on every invocation, carried no mid-skill decision value, and was the most drift-prone content in the repo.
  - Anti-pattern entries that merely restated a Non-Negotiable are removed; entries whose BAD case is non-obvious (e.g. task-planning's secretly-dependent-parallel) are kept.
  - `code-reviewer`'s per-language checklists (Python / React-TypeScript / Go / Java-Kotlin) are removed — current models know this material, and the lists anchored reviews to their own contents. Scope detection, the 80% confidence gate, falsification discipline, and the output contract are unchanged.
  - `code-simplifier`'s before/after code examples are removed; the action names, constraints, budget, and output contract stay.
  - `session-research-design`'s template placeholder prose is deflated to bare section lists. Every section heading survives — they are the interop contract with verify and task-planning.
  - Every format contract, `**Announce:**` line, tool budget, and prior-fighting Non-Negotiable is deliberately retained.
- `CONTRIBUTING.md` no longer mandates Anti-Patterns and Workflow Integration sections in new skills (which would have regrown the ceremony) and now asks for cross-references by step name rather than step number.
- Cross-reference drift fixed across `session-verify`, `references/workflow-overview.md`, and `references/customization-guide.md`; the README token-budget figure corrected from ~1,300 to the measured ~1,500.

### Fixed
- `/session-delegation` no longer passes the deprecated Task `mode: "bypassPermissions"` parameter (removed in Claude Code v2.1.212), which had been silently ignored. Subagents inherit the parent session's permission mode.
- `/update-architecture` resolves the architecture root from `paths.architecture` with detection fallback (`architecture/`, `_devdocs/architecture/`, `docs/architecture/`) instead of hardcoding `_devdocs/architecture/`. Projects initialized with a `docs/` root are no longer rejected.
- `/session-verify` and `/session-release` no longer key off `paths.design` — a config key `session-init` never wrote, which meant release's verification pre-flight could not fire on an initialized project. Both now resolve `paths.plans`, then `paths.research`, then detect.
- `/session-post-implementation` and `security-auditor` no longer pass plugin-relative reference paths in dispatch payloads, which did not resolve from an arbitrary project CWD. The loading skill now resolves its own plugin location and passes absolute paths; the auditor falls back to its in-file checklist summaries when they are absent.

## 1.2.1 (2026-07-16)

### Changed
- `session-next` Step 3 softens the per-task test mandate: instead of "write a test for the acceptance criteria (TDD)", it now bounds scope to the test(s) the acceptance criterion needs, prefers extending an existing test module over forking a new one, targets the pure/decision layer (not the framework, mocks, or trivial pass-throughs), and defers to the project's root `CLAUDE.md` "Test with altitude" principle where present. Keeps TDD (test as external oracle) while removing wording that drove test volume.

## 1.2.0 (2026-06-04)

### Added
- **Task sequence (backlog) layer** — a standing list of one-line task entries at `todo/SEQUENCE.md`, each linked to a self-contained breakdown in `todo/tasks/`. Say "implement the next task" and the agent picks up the next ready item. Four new skills:
  - **session-add-task** — capture a task into the sequence with a full breakdown (Files/Instructions/Accept/Test), a hand-off to `/session-task-planning` for multi-task work, or a quick `(needs breakdown)` capture.
  - **session-next** — read `SEQUENCE.md`, implement the next ready entry (or hand a multi-task entry to `/session-delegation`), and mark it `[x]`. Triggers on "implement the next task".
  - **session-groom** — research raw `(needs breakdown)` entries, verify feasibility, and attach ready-to-run breakdowns; escalates significant items to research-design. Safe to run periodically via `/loop`.
  - **session-gatekeeper** — front-of-chain intake that triages incoming issues/ideas grounded in architecture and product direction (`PRD.md`), routing trivial aligned work into the sequence and significant or divergent work to a cowork `/session-research-design` session. Triage only — never implements; treats issue text as untrusted input.
- `/session-init` now creates `todo/tasks/` and `todo/SEQUENCE.md`, optionally scaffolds a `PRD.md` direction stub in the docs root (e.g. `_devdocs/PRD.md`), and wires an idempotent `<!-- session-flow:sequence -->` block into the project's `CLAUDE.md` and `AGENTS.md` so "implement the next task" works without naming a file.
- `.session-flow.json` gains `paths.tasks`, `paths.sequence`, and `paths.direction` (defaults to a `PRD.md` in the docs root, overridable to an existing direction file).
- `/session-status` now reports sequence backlog stats (done / ready / needs-breakdown) and recommends `/session-next` or `/session-groom` accordingly.

### Changed
- `/session-task-planning` gains a "Sequence integration" step to optionally register phase tasks as backlog entries.
- `/session-delegation` documents being invoked by `/session-next` for multi-task entries and marking the source sequence entry `[x]` when its phase completes.
- Plugin manifest now lists all 13 skills; README and `references/workflow-overview.md` document the sequence layer and gatekeeper funnel.
- Corrected stale `.session-flow.json` documentation in `references/customization-guide.md` and `references/workflow-overview.md` to the actual nested `paths` schema (previously documented obsolete flat `todoDir`/`memoryDir` keys and a non-existent `memory/` layout).

## 1.1.1 (2026-04-20)

### Fixed
- Bundled agents (`code-reviewer`, `code-sanitizer`, `code-simplifier`, `security-auditor`) now declare `model: inherit` in their frontmatter so they actually run on the parent session's model. In 1.1.0 the `model` field was removed entirely on the assumption that omission caused inheritance — Claude Code instead defaults to Sonnet when the field is absent, so users on Opus 4.7 were getting Sonnet 4.6 subagents. The correct magic value is `model: inherit` (as used by e.g. the superpowers plugin).
- `CONTRIBUTING.md` agent checklist and `references/customization-guide.md` Model Selection section corrected to document the `model: inherit` requirement.

## 1.1.0 (2026-04-19)

### Added
- **session-verify** skill — evidence-based verification workflow for completed features and plans. Produces a falsifiable proof artifact at `_verification/YYYY-MM-DD-{label}-verification.md` with fixed H2 section contract (hypotheses, structural audit, test results, defect probes, integration probes, spec-vs-reality gap, findings ledger). Runs between `/session-post-implementation` and `/session-release`; also invokable standalone.
- **security-liability-audit** skill — combined technical security (LLM/AI, OWASP Top 10, secrets, agentic risks, desktop app, supply chain) and legal liability (GDPR, EU AI Act, ToS/EULA, consumer protection, cross-border data transfers) audit. Integrates into `/session-post-implementation` as optional Step 3 and runs standalone.
- **security-auditor** bundled agent — dispatched by the security & liability audit.
- `/session-post-implementation` gains a scope selector (Full / Standard / Quick) with optional add-ons, plus an optional Step 8.5 suggesting `/session-verify` after feature/plan completions.
- `/session-release` pre-flight Step 1 now checks for a PASS verification artifact when shipping features with a design doc.
- `references/customization-guide.md` Model Selection subsection documenting the inherit-by-default policy for bundled agents.
- Plugin manifest (`.claude-plugin/plugin.json`) now lists all 9 skills and 4 agents.

### Changed
- Bundled agents (`code-reviewer`, `code-sanitizer`, `code-simplifier`, `security-auditor`) no longer pin `model: sonnet`. They inherit the user's session model so users running Opus 4.7 (or any other tier) get subagents on the same tier automatically. Override per-agent via project-level `.claude/agents/` if you need to pin.
- Applied Opus 4.7 prompting patterns across existing skills and agents: non-negotiables blocks, evidence-first language, phase gates with explicit exit criteria, structured output contracts, falsification mindset for reviewers.
- `CONTRIBUTING.md` updated with new-skill checklist reflecting the Opus 4.7 patterns and revised agent frontmatter policy (do not pin `model` unless the agent has a task-specific capability requirement).

## 1.0.0 (2026-03-25)

Initial release.

### Skills
- **session-init** - Bootstrap project documentation structure
- **session-research-design** - Collaborative research and design with brainstorming
- **session-task-planning** - Dependency-aware task breakdown with parallelization
- **session-delegation** - Parallel agent dispatch from task plans
- **session-post-implementation** - Simplify, review, sanitize, test, document
- **session-release** - Version bump, artifact packaging, satellite content verification
- **update-architecture** - Surgical architecture documentation updates

### Agents
- **code-reviewer** - Finds bugs, security issues, convention violations
- **code-sanitizer** - Dead code detection and cleanup
- **code-simplifier** - Simplifies recently changed code

### Commands
- **session-status** - Check workflow progress and next steps
