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
    "fingerprint": "sha256:109b866c4895169729a808a399002c4767b59939600e8f3b47cfad90c8be2c14",
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
  "scope_fingerprint": "sha256:109b866c4895169729a808a399002c4767b59939600e8f3b47cfad90c8be2c14",
  "seq": "SEQ-301",
  "title": "Split the parser from the store"
}
```
<!-- /session-flow:meta -->

## Original request

> the parser and the store keep dragging each other in

<!-- session-flow:scope -->
Record parsing and record storage are separable: parsing answers about text, storage
answers about the work root.
<!-- /session-flow:scope -->
