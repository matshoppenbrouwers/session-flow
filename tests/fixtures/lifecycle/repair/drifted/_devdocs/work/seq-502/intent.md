<!-- session-flow:meta -->
```json
{
  "claim": {
    "actor": "agent:another-session",
    "allowed_paths": [
      "src/ingest/worker.py"
    ],
    "claimed_at": "2026-08-19T08:15:00Z",
    "coordinator": "session-delegation",
    "host": "another-host"
  },
  "format": 1,
  "lifecycle": "active",
  "namespace": "b17a5c30-9e42-4d6b-8f01-3c5d2a7e6b94",
  "order": 2,
  "priority": "P2",
  "provenance": {
    "auto": false,
    "imported_from": "_devdocs/todo/SEQUENCE.md"
  },
  "revision": 3,
  "seq": "SEQ-502",
  "title": "Split the ingest worker"
}
```
<!-- /session-flow:meta -->

Synthetic drifted record. The claim is stale: the actor that took it never recorded a result.

<!-- session-flow:scope -->
Split the ingest worker so a slow batch cannot starve the interactive queue.
<!-- /session-flow:scope -->
