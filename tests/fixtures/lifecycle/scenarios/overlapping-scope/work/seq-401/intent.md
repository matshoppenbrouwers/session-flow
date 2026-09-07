<!-- session-flow:meta -->
```json
{
  "acceptance": {
    "authority": {
      "revision": "2026-09-07T09:12:00Z",
      "source": "user-request"
    },
    "decided_at": "2026-09-07T09:14:00Z",
    "decided_by": "maintainer",
    "fingerprint": "sha256:3f8bfdbea53d1a3a1225d5adb839d7e1ba5c0476a9bb08f3b1c069ca4793bd6d",
    "scope": "implement"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "2b7c0f16-9d4a-4c31-8f52-6a1e7d3c5b08",
  "order": 10,
  "priority": "P1",
  "provenance": {
    "actor": "maintainer",
    "captured_at": "2026-09-06T18:02:00Z",
    "origin": "user"
  },
  "repositories": [
    {
      "name": "session-flow",
      "path": ".",
      "remote": "git@example.invalid:synthetic/session-flow.git"
    }
  ],
  "revision": 3,
  "scope_fingerprint": "sha256:3f8bfdbea53d1a3a1225d5adb839d7e1ba5c0476a9bb08f3b1c069ca4793bd6d",
  "seq": "SEQ-401",
  "title": "Normalize acceptance text"
}
```
<!-- /session-flow:meta -->

## Original request

> re-wrapping a paragraph should not cost me my acceptance

<!-- session-flow:scope -->
Reflowing acceptance-bearing text leaves the fingerprint unchanged; changing what it asks
for does not.
<!-- /session-flow:scope -->
