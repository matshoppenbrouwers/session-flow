---
name: session-status
description: Check session-flow workflow progress. Reports the active work item, its tasks, and the backlog from session-flow's generated views, and suggests the next skill to run. Triggers on "/session-status" or when user says "where are we", "what's next", or "session progress".
allowed-tools: Bash, Read, Grep
---

# Session Status

Report where the work stands and recommend the next action. Everything here is reporting: status
selects nothing to run, claims nothing, and completes nothing.

## Step 1: Resolve the Runtime

Every number reported here comes from the helper at `<package-root>/scripts/session-flow.py`.
Resolve it by the one rule for this host (`references/runtime-integration.md`):

- Native Claude plugin: the plugin root the host supplies in `${CLAUDE_PLUGIN_ROOT}`.
- Codex: the discovered installed skill and package location.
- Standalone copy: the `session-flow-runtime.json` descriptor beside the installed entry file;
  resolve its `entrypoint` against the descriptor's own directory.

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" doctor
```

Read `result.storage`. On `unsupported-runtime`, report `error.detail.install` and stop. When
`work_root_present` is false, report `work_root` and `storage.limitations`, recommend
`/session-init`, and stop.

Never fall back to finding the newest file in a directory. A dated Markdown file is a historical
document, not a work item, and its age is not a state.

## Step 2: Regenerate the Derived Views

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" render
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" select
```

`render` rewrites `paths.sequence` and one `tasks/_index.md` per item that has task records, so what
you report is current. It changes no record. `select` returns one `candidate` and a `considered`
entry for every work item — its `seq`, `lifecycle`, `eligible`, and the reasons it is not — plus an
`eligible` count. Neither command starts anything: reading a candidate is not a claim.

## Step 3: Resolve One Work Item by Identity

Pick exactly one, in this order:

1. The `SEQ-NNN` the user named.
2. The one `considered` entry whose `lifecycle` is `active` — work already claimed. If two are
   active, list both and ask which; report neither as *the* active item.
3. `result.candidate` — what `/session-next` would select next. Say so: it is a proposal, not work
   in progress.
4. Neither exists: report the backlog alone, with "no active work item".

An item is addressed by `SEQ-NNN` and nothing else. A newer dated report cannot displace the active
item, because it has no identity to displace it with.

An item reaches `active` only under a claim, so claimed work always sorts ahead of a candidate. If
the resolved item's task view shows an `active` task while the item itself is still `accepted`,
report that mismatch rather than smoothing it over — the claim and the parent state disagree.

Take `lifecycle` and the eligibility reasons from that item's `considered` entry, and title,
priority, links, and provenance from its record:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-NNN
```

## Step 4: Read That Item's Tasks

Task counts come from the generated task view at `<work root>/seq-NNN/tasks/_index.md` — one row per
task, each naming its identity and lifecycle. Never count checkboxes in a Markdown file.

No `tasks/` directory means a compact item: `intent.md` is the whole record. Report
`Tasks: compact record`, not `0/0`.

For each row that is not `done`:

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" show --seq SEQ-NNN --task A2
```

Read `lifecycle`, `depends_on`, `claim`, and `allowed_paths`. A task is **ready to dispatch** when
every identity in `depends_on` is `done` and it carries no live claim. Report those identities so
the user can name them — `/session-delegation` re-resolves prerequisites, write scopes, and claims
before it runs anything, and this report authorizes none of it.

## Step 5: Count the Backlog

From `select`'s `considered`, one entry per work item: count by `lifecycle`, and read
`result.eligible`. Count `[auto]` items from the generated sequence view — those entries arrived via
unattended intake and are the ones a user may want to strike on sight.

An open `[ ]` in the sequence view covers `captured`, `accepted`, `active`, and `blocked` alike, so
count states from `considered`, never from the markers.

## Step 6: Report Status

Output exactly this structure. Fixed fields, no substitutions.

```
## Session Status

**Work item:** {SEQ-NNN — title, or "none active"}
**Selected by:** {"named by you" | "the active claim" | "select's candidate"}
**State:** {lifecycle} · {"accepted scope applies" or the reason it does not}
**Tasks:** {done}/{total} done, or "compact record"
**Blocked:** {task identities whose lifecycle is blocked, or "none"}
**Ready to dispatch:** {task identities with all prerequisites done and no live claim, or "none"}
**Backlog:** {total} items · {eligible} eligible · {active} active · {captured} captured · {auto} auto
**Work root:** {storage.work_root}
**Sequence file:** {storage.sequence_path}

**Next:** {recommended action — see Step 7}
```

Every field is required. If a field has no data, use "none", "n/a", or "0" — do not omit the field.
Naming the work root and the sequence path is what makes a wrong path resolution visible.

## Step 7: Recommend Next Action

Read down the table and take the first row that matches.

| State | Recommendation |
|-------|---------------|
| No work root | "Run `/session-init` to create the work root and its namespace." |
| Backlog empty | "Run `/session-add-task` to capture work, or `/session-gatekeeper` to triage incoming items." |
| Reported item's acceptance no longer applies | "The scope changed after acceptance. Re-accept it, or record the edit as a same-meaning decision, before any dependent work." |
| Reported item is `blocked` | "Resolve the recorded blocker before dispatching anything under this identity." |
| Item active, tasks ready to dispatch | "Run `/session-delegation` with the task IDs listed above." |
| Item active, every task `done` | "Tasks passing is not delivery. Run `/session-verify` for evidence against the accepted scope, then `/session-release` if the outcome is delivered." |
| Item active, compact record | "Finish it under this identity and record the result against it." |
| A candidate exists, nothing active | "Run `/session-next` to claim the candidate and work it." |
| Every open item is `captured` | "Nothing is accepted yet. Capture is not acceptance and grants no permission to implement — accept one item first." |
| Open items marked `(needs breakdown)` only | "Run `/session-groom` to research and break down the open entries." |
