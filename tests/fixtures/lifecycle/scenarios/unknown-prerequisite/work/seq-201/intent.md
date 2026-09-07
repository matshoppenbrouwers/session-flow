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
    "fingerprint": "sha256:3fffc47c53eb286681c87655abc7a05a72180e5d3b71296e59885a47fafd551a",
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
  "scope_fingerprint": "sha256:3fffc47c53eb286681c87655abc7a05a72180e5d3b71296e59885a47fafd551a",
  "seq": "SEQ-201",
  "title": "Recover an interrupted operation"
}
```
<!-- /session-flow:meta -->

## Original request

> a crash left half a transition behind

<!-- session-flow:scope -->
An interrupted operation is finished or left explicitly blocked; unexplained divergence
stops reconciliation instead of overwriting it.
<!-- /session-flow:scope -->
