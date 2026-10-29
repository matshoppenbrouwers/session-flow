# Review policy

Report actionable bugs, security vulnerabilities, logic errors, and failures to
meet accepted requirements available in the repository or supplied review scope.
Do not invent requirements from unavailable private documents.

- Read surrounding code before flagging a problem. Trace a concrete input, state,
  or execution path that could cause the failure.
- Cite the file and line, the trigger, the effect, and a concrete fix for each
  finding. Distinguish severity from confidence; label uncertainty honestly.
- Focus on changed behavior. Separate pre-existing defects from defects introduced
  by the change.
- Report a convention or performance issue only when it breaks correctness or an
  accepted requirement. Avoid formatting, naming, simplification, and refactoring
  suggestions without such an effect.
- Follow project instructions and applicable project conventions. More specific
  review policies in parent directories of reviewed files add local checks.
- Explain the evidence behind a finding. Reading code is not execution evidence;
  never claim a test or real flow ran unless it actually ran.

A review verdict concerns only the reviewed changes. It is an input to testing
and acceptance verification, not permission to edit, publish, merge, or mark work
complete.
