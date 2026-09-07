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
    "fingerprint": "sha256:69637466466cb62b212553217e900cbeab130dd7b069931f7983dddbd882c9ea",
    "scope": "implement and verify"
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
  "scope_fingerprint": "sha256:69637466466cb62b212553217e900cbeab130dd7b069931f7983dddbd882c9ea",
  "seq": "SEQ-101",
  "title": "Serialize local record transitions"
}
```
<!-- /session-flow:meta -->

## Original request

> two sessions keep clobbering the same record

## Interpreted intent

Serialize the writers rather than merging their output.

<!-- session-flow:scope -->
Two coordinators writing one record must not overwrite each other: the second write is
refused with the named stale-revision error, before any file is replaced.
<!-- /session-flow:scope -->
