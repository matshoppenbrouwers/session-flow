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
    "fingerprint": "sha256:dfd985a25f52b4bfab2c5c4ff58b4baf974d099c32f93ad41d8fb3348113f7b8",
    "scope": "implement and verify"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "2d8f7b61-4c03-4e95-9a17-6b5d0e83c274",
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
  "scope_fingerprint": "sha256:dfd985a25f52b4bfab2c5c4ff58b4baf974d099c32f93ad41d8fb3348113f7b8",
  "seq": "SEQ-705",
  "title": "Reconcile an ambiguous remote create"
}
```
<!-- /session-flow:meta -->

## Original request

> a timed-out create may or may not have made an issue

## Interpreted intent

Reconcile against the remote before a second create is attempted.

<!-- session-flow:scope -->
An ambiguous create is reconciled against the remote; an unproved absence stays unknown and
no second create is attempted.
<!-- /session-flow:scope -->
