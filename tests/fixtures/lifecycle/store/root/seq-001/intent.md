<!-- session-flow:meta -->
```json
{
  "format": 1,
  "namespace": "6f1d4a02-3c58-4a1e-9b77-0c2f8d5e4411",
  "seq": "SEQ-001",
  "revision": 1,
  "title": "Serialize competing local writers on one work root",
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
      "path": "."
    }
  ]
}
```
<!-- /session-flow:meta -->

# SEQ-001 — Serialize competing local writers on one work root

<!-- session-flow:scope -->
One coordinator at a time mutates the work root: the second writer is refused rather than
merged, and no applied operation is ever repeated.
<!-- /session-flow:scope -->

## Approach

Take the root lock, compare expected revisions, journal the operation, then replace records.
