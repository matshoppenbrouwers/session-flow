<!-- session-flow:meta -->
```json
{
  "format": 1,
  "lifecycle": "captured",
  "links": {
    "breakdown": "todo/tasks/0201-fix-retry-backoff.md"
  },
  "namespace": "8c3a1f6e-2d47-4b19-9a05-7e6b1c4d2f80",
  "order": 1,
  "priority": "P1",
  "provenance": {
    "auto": false,
    "imported_from": "todo/SEQUENCE.md"
  },
  "revision": 1,
  "seq": "SEQ-201",
  "title": "Fix the retry backoff on the upload queue"
}
```
<!-- /session-flow:meta -->

A linked breakdown exists; no acceptance does.

<!-- session-flow:scope -->
Fix the retry backoff on the upload queue so a failed upload retries with a growing delay.
<!-- /session-flow:scope -->
