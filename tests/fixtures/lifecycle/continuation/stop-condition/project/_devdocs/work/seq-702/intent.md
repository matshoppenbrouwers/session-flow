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
    "fingerprint": "sha256:970cb31cf00b3d40d8eac5245c609bcf5965ff27cd0db2ccd20428f3076bb7a3",
    "scope": "implement and verify"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "c48b0f92-71d5-4a63-8e20-5f7a3b1c9d64",
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
  "scope_fingerprint": "sha256:970cb31cf00b3d40d8eac5245c609bcf5965ff27cd0db2ccd20428f3076bb7a3",
  "seq": "SEQ-702",
  "title": "Recover an interrupted local operation"
}
```
<!-- /session-flow:meta -->

## Original request

> a killed run left the work root half written

## Interpreted intent

Finish or refuse a journalled operation on the evidence of its recorded hashes.

<!-- session-flow:scope -->
A prepared operation is either completed from its journal or reported as unexplained
divergence; recovery never overwrites a file it cannot account for.
<!-- /session-flow:scope -->
