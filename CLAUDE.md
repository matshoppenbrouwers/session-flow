<!-- session-flow:sequence -->
## Task Sequence

Before starting unprompted work, consult the backlog at `_devdocs/SEQUENCE.md`. It is generated
output: read it to find work, and never edit it. When asked to "implement the next task", run
`/session-next`, which selects one open item, claims it, and records the outcome against its
identity. Use `/session-add-task` to capture new work, `/session-groom` to fill in missing
breakdowns, `/session-gatekeeper` to triage incoming issues, and `/session-repair` to survey and
reconcile the work root when the sequence and the items disagree.

`_devdocs/todo/` is the pre-import archive. Its files keep their names and stay where they are;
write nothing new there.
<!-- /session-flow:sequence -->
