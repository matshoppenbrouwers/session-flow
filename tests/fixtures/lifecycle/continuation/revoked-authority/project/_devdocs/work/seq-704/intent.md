<!-- session-flow:meta -->
```json
{
  "acceptance": {
    "accepted_at": "2026-09-07T10:06:00Z",
    "actor": "maintainer",
    "authority": {
      "revision": "2026-09-07T10:04:00Z",
      "source": "user-request"
    },
    "fingerprint": "sha256:1f6831eaa1af3a8e692af0ca89cf7efec4653c87034e25091a7678a9f2183808",
    "scope": "implement and verify"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "7c5a4e30-8d19-4f26-b073-2a9e6b1d4f85",
  "order": 10,
  "priority": "P1",
  "provenance": {
    "actor": "maintainer",
    "captured_at": "2026-09-06T17:40:00Z",
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
  "scope_fingerprint": "sha256:1f6831eaa1af3a8e692af0ca89cf7efec4653c87034e25091a7678a9f2183808",
  "seq": "SEQ-704",
  "title": "Escape structural markers in captured source text"
}
```
<!-- /session-flow:meta -->

## Original request

> a pasted issue body broke the record envelope

## Interpreted intent

Escape the region markers in captured text so quoted source cannot close a region.

<!-- session-flow:scope -->
Captured source text carrying a region marker is escaped on write and restored on read, and
the record still parses as one metadata region and one scope region.
<!-- /session-flow:scope -->
