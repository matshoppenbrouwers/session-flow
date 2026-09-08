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
    "fingerprint": "sha256:b25fd73b0c99882cda83cb61d76c7afba6c2e67c7c46c8f81507e4a448129182",
    "scope": "implement and verify"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "5a3d1c78-2e64-4b09-91f7-8c0d6e42a1b3",
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
  "scope_fingerprint": "sha256:b25fd73b0c99882cda83cb61d76c7afba6c2e67c7c46c8f81507e4a448129182",
  "seq": "SEQ-701",
  "title": "Regenerate the sequence view from the records"
}
```
<!-- /session-flow:meta -->

## Original request

> the backlog view keeps drifting from the records

## Interpreted intent

Derive every entry from the records and treat the view as replaceable output.

<!-- session-flow:scope -->
The generated sequence carries one entry per work item, derived from that item's record; a
hand edit to the view is discarded at the next render.
<!-- /session-flow:scope -->
