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
    "fingerprint": "sha256:ec32b9ec9beecdfbacca0b79986cfefcaeb56e57025ad47b6359353b7d186025",
    "scope": "implement and verify"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "9f2e6d41-3b87-4c50-a61d-7e4b8c25f309",
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
  "scope_fingerprint": "sha256:ec32b9ec9beecdfbacca0b79986cfefcaeb56e57025ad47b6359353b7d186025",
  "seq": "SEQ-703",
  "title": "Bind the configured account before a mirror is created"
}
```
<!-- /session-flow:meta -->

## Original request

> a mirror landed under the wrong account

## Interpreted intent

Resolve and bind the account and the full target before any remote effect.

<!-- session-flow:scope -->
A mirror is created only after the configured account and full target are resolved and bound
to the outgoing intent.
<!-- /session-flow:scope -->
