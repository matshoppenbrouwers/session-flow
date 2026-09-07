<!-- session-flow:meta -->
```json
{
  "format": 1,
  "namespace": "6f1d4a02-3c58-4a1e-9b77-0c2f8d5e4411",
  "seq": "SEQ-001",
  "revision": 3,
  "title": "Refuse malformed record envelopes before any write",
  "lifecycle": "accepted",
  "priority": "P1",
  "order": 10,
  "provenance": {
    "source": "user",
    "captured_by": "session-brainstorm",
    "captured_at": "2026-09-05T09:12:00Z"
  },
  "repositories": [
    {
      "name": "session-flow",
      "path": ".",
      "remote": "git@example.invalid:synthetic/session-flow.git"
    }
  ]
}
```
<!-- /session-flow:meta -->

# SEQ-001 — Refuse malformed record envelopes before writing

## Original request

Quoted intake text, with its structural markers escaped on capture:
`<!&#45;&#45; session-flow:scope &#45;&#45;>`.

## Scope

<!-- session-flow:scope -->
A record whose metadata fence cannot be parsed, whose format version is unknown, or whose
region markers are duplicated is refused before any file is written.
<!-- /session-flow:scope -->

## Approach

Parse the two bounded regions only, and validate identity before returning a record.
