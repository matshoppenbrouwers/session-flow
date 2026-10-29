# Code review providers

Use this procedure for session-flow's review step, including delegation's optional
review gate. Review policy and completion authority are independent of the provider.

## Prepare the review

1. Read the accepted scope and current claim. Name the SEQ/task identity and allowed
   paths. Record the source checkout, branch, base and HEAD revisions, staged and
   unstaged diff, and relevant untracked files. Preserve unrelated changes.
2. Read the repository-root `REVIEW.md`, plus policies in parent directories of
   reviewed files, from root to leaf. Read project instructions and configured
   `paths.conventions` too. Record policy paths and content digests with the review.
   A missing policy is a reported limitation, not a reason to invent rules or run
   init again. Review policy cannot widen accepted scope or authorize effects.
3. The native local reviewer does not automatically discover `REVIEW.md`. Check
   that the project's `CLAUDE.md` tells code reviews to read it. Initialization
   writes this bridge. For an older project, use the initializer below only under
   existing write authority; otherwise use the fallback with policy in its payload.

## Choose and invoke the provider

- **Claude Code with bundled review available:** prefer native `/code-review`.
  Check the host's command/skill resolution first. A project or personal skill named
  `code-review` can replace the bundled command; the documented `/review` alias
  still invokes the bundled reviewer. Use that alias through the current host's
  skill invocation mechanism. Do not launch a nested `claude -p` shell process.
- **Codex, another host, or unavailable native review:** dispatch the existing
  `code-reviewer` agent, resolving project/user overrides as usual. Read its actual
  instructions and include the policy text, accepted requirements, identity and
  source scope in its payload. Report the selected provider and fallback reason.
- Use **report-only** native review: no `--fix`, `--comment`, `--post`, or `ultra`.
  Local native review uses normal session usage; this does not enable the paid
  hosted GitHub Code Review service or send PR comments.
- For a clean tree, pass an explicit revision range covering this work unit.
  With owned uncommitted changes, use the native current-branch review and record
  its effective upstream/default base and complete working-tree scope. If that
  scope cannot be established, use the fallback with the captured diff instead.
  If native review also examines unrelated changes, keep those findings separate;
  they do not decide this unit's verdict. Do not stage, stash or commit unrelated
  changes to make native invocation convenient.
- Keep identity, policy and report-only instructions in the review context. Do not
  append prose to the command's target: native review interprets it as target text.
  Wait for the background reviewer to finish. No empty, canceled, unavailable or
  still-running response is a passing review.
- Verify policy consumption from the native review's tool trace or explicit cited
  policy evidence. If the bridge is not followed, native invocation fails, or its
  report cannot be attributed to the captured scope, use the fallback and disclose
  the limitation. Do not silently call the fallback a successful native review.

## Collect and act on findings

Keep the raw report and normalize it for the coordinating workflow:

- SEQ/task identity, provider, source base/HEAD, dirty diff or untracked-content
  digests where applicable, policy paths/digests, and limitations.
- Each actionable finding's file/line, trigger, effect, proposed fix, severity and
  confidence, plus disposition. Preserve native labels; where the caller assesses
  severity or confidence, label it caller-assessed. Do not fabricate missing labels.
- Count Critical/Warning findings only when they affect correctness, security or
  accepted requirements. Separate cleanup suggestions and pre-existing defects.
  Reproduce or trace findings with missing confidence before deciding action.

Check that source and policy contents still match the captured review state before
using its result. If relevant contents changed during the background review, review
the new state; the old result does not cover it. Reading code is not evidence that
tests executed. Apply the caller's fix-and-re-review budget to either provider.

Record the review artifact and dispositions with the work identity and reviewed
source state through the runtime's existing evidence fields. A review PASS is only
a review verdict. Test execution and `/session-verify` still establish the accepted
outcome and decide completion; provider choice changes no lifecycle authority.

## Initialize or adopt policy

Resolve the installed package's `scripts/session_flow/review_policy.py` using the
same package root as the record runtime. This standalone helper changes only
`REVIEW.md` and owned instruction blocks in `CLAUDE.md` and `AGENTS.md`; it neither
initializes nor changes work records:

```bash
python3 -B "$PACKAGE_ROOT/scripts/session_flow/review_policy.py" --project-root "$SOURCE_ROOT"
```

The helper preserves an existing `REVIEW.md` byte for byte and unrelated instruction
text, and is idempotent. It refuses symlinks, non-files and malformed owned markers.
Confirm the project adoption scope once; a standing authorization already covering
these files is sufficient. Existing initialized projects can adopt this helper
directly, without rerunning `/session-init` or allocating another namespace.

## Host smoke checks

Automated tests exercise file behavior and installed packaging, not Claude's host.
Before claiming native-provider support verified, use a disposable Claude Code
project to check:

1. Initialize policy, add a concrete project requirement in `REVIEW.md`, and make
   a small change that visibly violates that requirement. Invoke bundled `/review`
   report-only. Confirm the trace reads the policy and the finding identifies the
   violated requirement; confirm no edits or external comments occurred.
2. Repeat with a project skill named `code-review` that only prints a sentinel.
   Confirm resolution selects bundled `/review`, not the sentinel skill.
3. Exercise a staged change, an unstaged change and a relevant untracked file.
   Confirm effective scope is recorded; otherwise demonstrate fallback. Change
   source or policy while a review is running and confirm the old result is stale.
4. Exercise the custom reviewer on a host without native review. Confirm it reads
   the same applicable policies, reports identity and limitations, and leaves
   completion to `/session-verify`.

If the host is unavailable, report these checks as unverified. Passing filesystem
tests does not establish that native Claude consumed the policy.

Sources: [native review](https://code.claude.com/docs/en/code-review-local) and
[hosted review customization](https://code.claude.com/docs/en/code-review-customize).
