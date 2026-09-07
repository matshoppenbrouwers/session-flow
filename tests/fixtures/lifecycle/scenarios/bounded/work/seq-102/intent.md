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
    "fingerprint": "sha256:8639f81ed95467cfb6c53f5fbd1f2c3b58f85bd7799a07cc4574ee6e535b7c4c",
    "scope": "implement"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "2b7c0f16-9d4a-4c31-8f52-6a1e7d3c5b08",
  "order": 20,
  "priority": "P2",
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
  "scope_fingerprint": "sha256:8639f81ed95467cfb6c53f5fbd1f2c3b58f85bd7799a07cc4574ee6e535b7c4c",
  "seq": "SEQ-102",
  "title": "Report an unversioned work root"
}
```
<!-- /session-flow:meta -->

## Original request

> tell me when the work root is not a git repo

<!-- session-flow:scope -->
doctor names an unversioned work root as a limitation and says backup and restore are
unavailable.
<!-- /session-flow:scope -->
