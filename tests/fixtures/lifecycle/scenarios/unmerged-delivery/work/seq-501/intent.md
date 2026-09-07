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
    "fingerprint": "sha256:c0035ce98f346f70e7faa62b806d53742f8b2fc961bcb674b4b580b3aaafc430",
    "scope": "implement and merge"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "active",
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
  "scope_fingerprint": "sha256:c0035ce98f346f70e7faa62b806d53742f8b2fc961bcb674b4b580b3aaafc430",
  "seq": "SEQ-501",
  "title": "Install complete skill resources"
}
```
<!-- /session-flow:meta -->

## Original request

> the installed skills cannot find their own references

## Interpreted intent

Copy the nested reference trees, and ship the fix.

<!-- session-flow:scope -->
A standalone installation carries every reference its instructions load, and the release
that ships it is merged into the default branch.
<!-- /session-flow:scope -->
